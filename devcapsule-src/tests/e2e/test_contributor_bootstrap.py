"""Bootstrap a first-time contributor in a disposable DevCapsule base.

The same test runs from two places.  On a contributor host, Docker can bind the
owned checkout directly.  From recursive dogfood, the Docker client addresses
the host daemon, so the current container path must first be translated through
an inspected, approved bind mount.  The child sees the same ``/e2e`` layout in
both cases and therefore exercises one bootstrap protocol rather than two.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import time
import tomllib
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

import pytest

from devcapsule.container_runtime.contract import RuntimePlan
from devcapsule.recursive_dogfood import (
    RECURSIVE_E2E_ENABLED_ENV,
    RUNTIME_PLAN_PATH,
    run_recursive_preflight,
)
from devcapsule.recursive_host import (
    HostDaemonLaunchContext,
    PathAccess,
    PathKind,
)
from tests.e2e.test_recursive_local_clone import LocalCloneProtocol, OwnedWorkspace

pytestmark = pytest.mark.legacy


REPO_ROOT = Path(__file__).resolve().parents[3]
PLATFORM_LOCK = REPO_ROOT / ".devcapsule/devcapsule.linux-amd64.lock"
SUCCESSOR_ROOT = Path("/e2e")
IMAGE_OVERRIDE = "DEVCAPSULE_CONTRIBUTOR_E2E_IMAGE"
OWNER_LABEL = "devcapsule.e2e.owner"
RUN_LABEL = "devcapsule.e2e.run-id"
FULL_DOCKER_ID = re.compile(r"sha256:[0-9a-f]{64}")


@dataclass(frozen=True)
class ContributorDockerContext:
    """One Docker daemon plus the correct source-path namespace for that daemon."""

    mode: str
    docker: str
    docker_environment: Mapping[str, str] = field(repr=False)
    image_id: str
    workspace_root: Path
    owner_identity: str
    recursive_host: HostDaemonLaunchContext | None = field(default=None, repr=False)

    @classmethod
    def discover(cls, host_workspace: Path) -> ContributorDockerContext:
        docker = shutil.which("docker")
        assert docker is not None, "Docker CLI is required for contributor bootstrap E2E"
        docker_environment = cls._docker_environment()
        cls._run_docker(
            [docker, "version", "--format", "{{.Server.Version}}"],
            docker_environment,
        )

        # /.dockerenv means direct bind paths would be unsafe guesses.  Only a
        # recursive-ready DevCapsule may translate them through host inspection;
        # an arbitrary container fails instead of masquerading as a host run.
        if Path("/.dockerenv").exists():
            assert os.environ.get(RECURSIVE_E2E_ENABLED_ENV) == "1", (
                "inside-Docker contributor E2E requires a recursive-ready DevCapsule launch"
            )
            return cls._discover_recursive(docker, docker_environment)
        return cls._discover_host(docker, docker_environment, host_workspace)

    @classmethod
    def _discover_recursive(
        cls,
        docker: str,
        docker_environment: Mapping[str, str],
    ) -> ContributorDockerContext:
        report = run_recursive_preflight(REPO_ROOT, environ=os.environ)
        assert report.ready and report.container is not None, (
            "recursive preflight must pass before host-path translation"
        )
        # ContainerInspection comes from the host daemon's exact Docker
        # inspection. Recursive contributor bootstrap deliberately inherits
        # only an already-authorized host-network posture; it never guesses or
        # silently widens a bridge-mode launch.
        assert report.container.network_mode == "host", (
            "inside-container contributor E2E requires Docker-inspected host networking"
        )
        runtime_plan = RuntimePlan.from_file(RUNTIME_PLAN_PATH)
        host_context = HostDaemonLaunchContext.from_requirements(
            report.container,
            persistent_home=Path(runtime_plan.home),
            requirements=(),
        )

        # Bootstrap uses the actual base beneath the current materialized IDE,
        # not the IDE image itself.  This is the closest available simulation of
        # the image a first-time contributor starts from.
        current_image = cls._inspect_image(
            docker,
            report.container.image,
            docker_environment,
        )
        current_labels = cls._image_labels(current_image)
        if current_labels.get("devcapsule.image.kind") == "materialized":
            selected_image = current_labels.get("devcapsule.materialization.base-identity")
            assert isinstance(selected_image, str) and selected_image
        else:
            selected_image = report.container.image
        base = cls._inspect_image(docker, selected_image, docker_environment)
        image_id = cls._validate_base(base)
        return cls(
            mode="recursive-container",
            docker=docker,
            docker_environment=docker_environment,
            image_id=image_id,
            workspace_root=host_context.workspace_root,
            owner_identity=report.container.identity,
            recursive_host=host_context,
        )

    @classmethod
    def _discover_host(
        cls,
        docker: str,
        docker_environment: Mapping[str, str],
        host_workspace: Path,
    ) -> ContributorDockerContext:
        selected_image = os.environ.get(IMAGE_OVERRIDE) or cls._locked_base_reference()
        inspected = cls._inspect_image(docker, selected_image, docker_environment)
        image_id = cls._validate_base(inspected)
        return cls(
            mode="contributor-host",
            docker=docker,
            docker_environment=docker_environment,
            image_id=image_id,
            workspace_root=host_workspace.resolve(strict=True),
            owner_identity=f"host-process-{os.getpid()}",
        )

    def bind_source(self, run_root: Path) -> PurePosixPath:
        selected = run_root.resolve(strict=True)
        if self.recursive_host is None:
            # The pytest process and Docker daemon share the host namespace.
            return PurePosixPath(str(selected))
        translated = self.recursive_host.translate(
            selected,
            access=PathAccess.write,
            kind=PathKind.directory,
        )
        return translated.host_path

    def run_bootstrap(self, workspace: OwnedWorkspace) -> Mapping[str, Any]:
        container_name = f"devcapsule-contributor-e2e-{workspace.run_id}"
        bind_source = self.bind_source(workspace.run_root)
        environment = dict(self.docker_environment)
        forwarded_network_names = self._safe_network_environment(environment)
        command = [
            self.docker,
            "run",
            "--rm",
            "--name",
            container_name,
            "--label",
            f"{OWNER_LABEL}=contributor-bootstrap",
            "--label",
            f"{RUN_LABEL}={workspace.run_id}",
            "--network",
            "host",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,mode=1777",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--mount",
            f"type=bind,src={bind_source},dst={SUCCESSOR_ROOT}",
            "--workdir",
            f"{SUCCESSOR_ROOT}/checkout/devcapsule-src",
            "--env",
            "HOME=/e2e/contributor/home",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
        ]
        for name in forwarded_network_names:
            command.extend(("--env", name))
        command.extend(
            (
                "--entrypoint",
                "/usr/bin/python3.12",
                self.image_id,
                "/e2e/checkout/devcapsule-src/tests/e2e/contributor_bootstrap_driver.py",
                "--run-root",
                str(SUCCESSOR_ROOT),
            )
        )
        try:
            self._run_docker(
                command,
                environment,
                redactions={str(bind_source): "<owned-workspace-host-path>"},
            )
        finally:
            self._remove_owned_container(container_name, workspace.run_id, environment)
        return self._read_evidence(workspace.run_root / "contributor-bootstrap.json")

    def verify_bootstrap(
        self,
        evidence: Mapping[str, Any],
        workspace: OwnedWorkspace,
        clone: Path,
    ) -> None:
        assert evidence.get("schema_version") == 1
        system = self._mapping(evidence.get("system_python"), "system Python")
        venv = self._mapping(evidence.get("venv_python"), "venv Python")
        assert system.get("executable") == "/usr/bin/python3.12"
        assert venv.get("executable") == "/e2e/contributor/venv/bin/python3.12"
        assert venv.get("prefix") == "/e2e/contributor/venv"
        assert venv.get("base_prefix") != venv.get("prefix")

        final_packages = self._mapping(
            evidence.get("final_packages"), "final package inventory"
        )
        for required in ("pip", "wheel", "nox", "pex", "devcapsule"):
            assert isinstance(final_packages.get(required), str), (
                f"contributor environment is missing {required}"
            )
        import_probe = self._mapping(evidence.get("import_probe"), "import probe")
        assert str(import_probe.get("module_file", "")).startswith(
            "/e2e/checkout/devcapsule-src/devcapsule/"
        )

        environment_names = evidence.get("environment_names")
        assert isinstance(environment_names, list)
        forbidden_names = {
            "DOCKER_HOST",
            "GIT_ASKPASS",
            "SSH_AUTH_SOCK",
            "PIP_INDEX_URL",
            "PYTHONPATH",
            "VIRTUAL_ENV",
        }
        assert forbidden_names.isdisjoint(environment_names)
        serialized = json.dumps(evidence, sort_keys=True)
        assert str(REPO_ROOT) not in serialized

        evidence_path = workspace.run_root / "contributor-bootstrap.json"
        assert stat.S_IMODE(evidence_path.stat().st_mode) == 0o600
        assert (workspace.run_root / "contributor/venv/bin/python3.12").is_file()

        # Editable installation may create ignored build metadata, but it must
        # never alter tracked source or staged content in the clean clone.
        git = shutil.which("git")
        assert git is not None
        for arguments in (("diff", "--quiet", "HEAD"), ("diff", "--cached", "--quiet")):
            completed = subprocess.run(
                [git, "-C", str(clone), *arguments],
                check=False,
                capture_output=True,
                text=True,
                env=dict(workspace.git_environment),
            )
            assert completed.returncode == 0

    @staticmethod
    def _docker_environment() -> dict[str, str]:
        environment = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "DOCKER_CONFIG": "/tmp/devcapsule-contributor-e2e-empty-docker-config",
        }
        for name in ("DOCKER_HOST", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"):
            value = os.environ.get(name)
            if value:
                environment[name] = value
        return environment

    @staticmethod
    def _safe_network_environment(environment: dict[str, str]) -> tuple[str, ...]:
        forwarded: list[str] = []
        for canonical in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"):
            value = os.environ.get(canonical) or os.environ.get(canonical.lower())
            if not value:
                continue
            if canonical != "NO_PROXY":
                parsed = urlsplit(value)
                assert parsed.scheme in {"http", "https"} and parsed.hostname
                assert parsed.username is None and parsed.password is None, (
                    f"{canonical} with URL credentials cannot enter contributor bootstrap"
                )
            environment[canonical] = value
            forwarded.append(canonical)
        return tuple(forwarded)

    @classmethod
    def _inspect_image(
        cls,
        docker: str,
        image: str,
        environment: Mapping[str, str],
    ) -> Mapping[str, Any]:
        completed = cls._run_docker(
            [docker, "image", "inspect", image],
            environment,
            check=False,
        )
        assert completed.returncode == 0, (
            f"contributor E2E base {image!r} is unavailable locally; pull it explicitly "
            f"or set {IMAGE_OVERRIDE}"
        )
        value = json.loads(completed.stdout)
        assert isinstance(value, list) and len(value) == 1
        return cls._mapping(value[0], "Docker image inspection")

    @classmethod
    def _validate_base(cls, image: Mapping[str, Any]) -> str:
        image_id = image.get("Id")
        assert isinstance(image_id, str) and FULL_DOCKER_ID.fullmatch(image_id)
        labels = cls._image_labels(image)
        assert labels.get("devcapsule.image.managed") == "true"
        assert labels.get("devcapsule.image.kind") == "base"
        assert labels.get("devcapsule.base.recipe-status") == "ready"
        return image_id

    @classmethod
    def _image_labels(cls, image: Mapping[str, Any]) -> Mapping[str, Any]:
        config = cls._mapping(image.get("Config"), "Docker image configuration")
        return cls._mapping(config.get("Labels"), "Docker image labels")

    @staticmethod
    def _locked_base_reference() -> str:
        with PLATFORM_LOCK.open("rb") as stream:
            value = tomllib.load(stream)
        base = value.get("base")
        assert isinstance(base, dict)
        reference = base.get("reference")
        assert isinstance(reference, str) and "@sha256:" in reference
        return reference

    def _remove_owned_container(
        self,
        name: str,
        run_id: str,
        environment: Mapping[str, str],
    ) -> None:
        inspected = self._run_docker(
            [self.docker, "container", "inspect", name],
            environment,
            check=False,
        )
        if inspected.returncode != 0:
            return
        value = json.loads(inspected.stdout)
        assert isinstance(value, list) and len(value) == 1
        container = self._mapping(value[0], "contributor container inspection")
        config = self._mapping(container.get("Config"), "contributor container configuration")
        labels = self._mapping(config.get("Labels"), "contributor container labels")
        assert labels.get(OWNER_LABEL) == "contributor-bootstrap"
        assert labels.get(RUN_LABEL) == run_id
        removed = self._run_docker(
            [self.docker, "container", "rm", "--force", name],
            environment,
            check=False,
        )
        if removed.returncode != 0:
            remaining = self._run_docker(
                [self.docker, "container", "inspect", name],
                environment,
                check=False,
            )
            if remaining.returncode != 0:
                return
            if "removal of container" not in removed.stderr:
                pytest.fail(
                    f"cannot remove owned contributor container: {removed.stderr.strip()}"
                )
        for _ in range(50):
            remaining = self._run_docker(
                [self.docker, "container", "inspect", name],
                environment,
                check=False,
            )
            if remaining.returncode != 0:
                return
            time.sleep(0.1)
        pytest.fail("owned contributor container removal did not complete within five seconds")

    @staticmethod
    def _read_evidence(path: Path) -> Mapping[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        return ContributorDockerContext._mapping(value, "bootstrap evidence")

    @staticmethod
    def _mapping(value: object, label: str) -> Mapping[str, Any]:
        assert isinstance(value, dict), f"{label} must be an object"
        return value

    @staticmethod
    def _run_docker(
        command: Sequence[str],
        environment: Mapping[str, str],
        *,
        check: bool = True,
        redactions: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            env=dict(environment),
        )
        if check and completed.returncode != 0:
            replacements = redactions or {}

            def redact(value: str) -> str:
                for sensitive, replacement in replacements.items():
                    value = value.replace(sensitive, replacement)
                return value

            rendered = " ".join(redact(part) for part in command)
            pytest.fail(
                f"Docker command failed with exit {completed.returncode}: {rendered}\n"
                f"stdout: {redact(completed.stdout.strip())}\n"
                f"stderr: {redact(completed.stderr.strip())}"
            )
        return completed


@pytest.mark.e2e
@pytest.mark.contributor_e2e
def test_first_time_contributor_bootstrap_from_host_or_recursive_container(
    tmp_path: Path,
) -> None:
    docker_context = ContributorDockerContext.discover(tmp_path)
    clone_protocol = LocalCloneProtocol(REPO_ROOT)
    selection = clone_protocol.select_clean_source()
    workspace = OwnedWorkspace.create_at(
        docker_context.workspace_root,
        owner_identity=docker_context.owner_identity,
    )
    try:
        clone = clone_protocol.clone_without_checkout(selection, workspace)
        clone_protocol.configure_checkout_safety(clone, workspace)
        clone_protocol.checkout_exact_revision(clone, selection.revision, workspace)
        clone_protocol.remove_local_origin(clone, workspace)
        clone_protocol.verify_clone(clone, selection, workspace)

        evidence = docker_context.run_bootstrap(workspace)
        docker_context.verify_bootstrap(evidence, workspace, clone)
    finally:
        workspace.cleanup()
    assert not workspace.run_root.exists()
