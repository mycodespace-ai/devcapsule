"""Exercise cross-image contribution reuse on the actual Docker builder."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import uuid

import pytest

from devcapsule.environment_realization import optional_local_image
from devcapsule.images.build import (
    BuildxImageBuilder, ContributionComponent, ExecComponent,
    FileComponent, ImageBuildSpec,
)
from devcapsule.materialization import ArtifactSpec, ensure_materialized_surface
from devcapsule.platforms import Platform
from devcapsule.runtime_command import RuntimeCommand

pytestmark = pytest.mark.e2e


def docker(*args: str) -> str:
    completed = subprocess.run(["docker", *args], check=False, text=True, capture_output=True)
    if completed.returncode != 0:
        # Keep the command's own output: a bare CalledProcessError hides it.
        raise AssertionError(
            f"docker {' '.join(args)} exited {completed.returncode}\n"
            f"--- stdout ---\n{completed.stdout[-4000:]}\n--- stderr ---\n{completed.stderr[-4000:]}"
        )
    return completed.stdout.strip()


def test_installation_is_reused_across_images_and_invalidated_by_recipe(tmp_path: Path) -> None:
    """A component's installation layer is reused by every image built on the same base and recipe,
    whatever else the images contain, and runs again when the recipe changes."""
    base_reference = os.environ.get("DEVCAPSULE_E2E_BASE_IMAGE", "ubuntu:24.04")
    if expected_base := os.environ.get("DEVCAPSULE_E2E_BUILT_BASE"):
        assert json.loads(docker("image", "inspect", base_reference))[0]["Id"] == expected_base
    token = uuid.uuid4().hex
    images = [f"devcapsule-cache-test:{token}-{index}" for index in range(3)]
    builder = BuildxImageBuilder()
    runtime = tmp_path / "runtime"
    observed = []
    # Random output proves that the install did not execute a second time.
    # The per-test token prevents borrowing a cache hit from an earlier test.
    def contribution(version: str) -> ContributionComponent:
        return ContributionComponent("jdk", (ExecComponent((
            "sh", "-c", f"mkdir -p /opt/jdk/{version} && "
            f"cat /proc/sys/kernel/random/uuid > /opt/jdk/{version}/installed-{token} && "
            f"ln -s {version} /opt/jdk/current",
        )),), ("/opt/jdk",))

    try:
        for index, image in enumerate(images):
            runtime.write_text(f"launcher-{index}")
            version = "1" if index < 2 else "2"
            sibling = ContributionComponent("another-component", (
                ExecComponent(("sh", "-c", f"mkdir -p /opt/other && echo {index} > /opt/other/version")),
            ), ("/opt/other",))
            stages = (contribution(version), sibling) if index == 0 else (sibling, contribution(version))
            builder.build(ImageBuildSpec(image, base_reference, (
                *stages, FileComponent(runtime, "/runtime"),
            )), platform=Platform.current(), network="none")
            observed.append(docker("run", "--rm", "--network=none", image,
                                   "cat", f"/opt/jdk/current/installed-{token}"))
            assert docker("run", "--rm", image, "cat", "/runtime") == f"launcher-{index}"
        assert observed[0] == observed[1]
        assert observed[2] != observed[1]
    finally:
        subprocess.run(["docker", "image", "rm", *images], capture_output=True)


@pytest.mark.parametrize("surface", ["pycharm", "codium"])
@pytest.mark.parametrize("command", list(RuntimeCommand))
def test_formation_receives_exact_launcher_on_runtime_free_base(
    tmp_path: Path, built_pex: Path, surface: str, command: RuntimeCommand,
) -> None:
    """A materialized surface on a base without a runtime carries the exact executable under test,
    labelled with its digest, and reaches it through each public command as an ordinary user."""
    archive_path = tmp_path / "surface.tar.gz"
    names = ("bin/pycharm.sh",) if surface == "pycharm" else ("codium", "bin/codium", "chrome-sandbox")
    with tarfile.open(archive_path, "w:gz") as archive:
        for name in names:
            data = b"#!/bin/sh\nexit 0\n"
            member = tarfile.TarInfo(f"fixture/{name}")
            member.size, member.mode = len(data), 0o755
            archive.addfile(member, io.BytesIO(data))
    image = None
    try:
        base_reference = os.environ.get("DEVCAPSULE_E2E_BASE_IMAGE", "ubuntu:24.04")
        base = json.loads(docker("image", "inspect", base_reference))[0]
        if expected_base := os.environ.get("DEVCAPSULE_E2E_BUILT_BASE"):
            assert base["Id"] == expected_base
        image, created = ensure_materialized_surface(
            base_reference=base_reference, base_identity=base["Id"],
            platform=f"{base['Os']}-{base['Architecture']}",
            artifact=ArtifactSpec("fixture", archive_path.as_uri(),
                                  hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                                  "professional" if surface == "pycharm" else None),
            cache_root=tmp_path / "cache", inspect_image=optional_local_image,
            build=lambda spec: BuildxImageBuilder().build(spec, platform=Platform.current(), network="none"),
            recipe_id="jetbrains-local-materialization" if surface == "pycharm" else "vscode-local-materialization",
            recipe_version="1" if surface == "pycharm" else "2",
            component_id=surface, runtime_pex=built_pex, runtime_command=command,
        )
        assert created
        digest = docker("run", "--rm", "--entrypoint=sha256sum", image,
                        "/opt/devcapsule/bin/devcapsule.pex").split()[0]
        assert digest == hashlib.sha256(built_pex.read_bytes()).hexdigest()
        labels = json.loads(docker("image", "inspect", image))[0]["Config"]["Labels"]
        assert labels["devcapsule.pex.sha256"] == digest
        assert "usage: devcapsule runtime" in docker("run", "--rm", "--network=none", image, "--help")
        # Exercise the user's public command as a non-root user with the image's
        # ordinary PATH, not the internal absolute path used by the supervisor.
        actual = json.loads(docker("run", "--rm", "--network=none", "--user=1000:1000",
                                   "--env=HOME=/tmp", "--entrypoint=sh", image,
                                   "-ec", f"{command} version --json"))
        expected = json.loads(subprocess.check_output([str(built_pex), "version", "--json"], text=True))
        assert actual == expected
        assert "Usage: devcapsule" in docker(
            "run", "--rm", "--network=none", "--user=1000:1000", "--env=HOME=/tmp",
            "--entrypoint=sh", image, "-ec", f"{command} --help",
        )
        # The reported blocked task must work too; install only in this disposable
        # container, never in the owner's checkout or persisted IDE state.
        docker("run", "--rm", "--network=none", "--user=1000:1000", "--env=HOME=/tmp",
               "--entrypoint=sh", image, "-ec", f"""
            mkdir /tmp/workflow-project
            {command} bootstrap project --project /tmp/workflow-project
            test -s /tmp/workflow-project/WORKFLOW.md
            test -s /tmp/workflow-project/AGENTS.md
            test -s /tmp/workflow-project/CURRENT-STATUS.md
        """)
        if command is RuntimeCommand.DEVELOPMENT:
            # No shipped fallback can mask a missing development installation.
            # An independently installed command owns the usual spelling while
            # the stable alias still reaches the original runtime.
            actual = docker("run", "--rm", "--network=none", "--user=1000:1000", "--env=HOME=/tmp",
                            "--entrypoint=sh", image, "-ec", """
                if command -v devcapsule; then exit 1; fi
                mkdir -p /tmp/development/bin
                printf '#!/bin/sh\\necho development-build\\n' > /tmp/development/bin/devcapsule
                chmod +x /tmp/development/bin/devcapsule
                export PATH=/tmp/development/bin:$PATH
                test "$(devcapsule)" = development-build
                devcapsule0 version --json
            """)
            assert json.loads(actual) == expected
    finally:
        if image:
            subprocess.run(["docker", "image", "rm", image], capture_output=True)
