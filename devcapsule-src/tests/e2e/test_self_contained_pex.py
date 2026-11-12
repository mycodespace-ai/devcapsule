from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

import tomllib

pytestmark = pytest.mark.legacy

# CI supplies the tag-derived version; local builds use the source baseline.
PACKAGE_VERSION = os.environ.get("DEVCAPSULE_EXPECTED_RELEASE_VERSION") or tomllib.loads(
    (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
)["project"]["version"]

DEFAULT_CLEAN_MACHINE_IMAGE = "ubuntu:24.04"


def command(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


@pytest.mark.e2e
def test_self_contained_pex_runs_without_python_or_network(built_pex: Path) -> None:
    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI is required for the clean-machine PEX proof"
    command(docker, "version")

    base_image = os.environ.get(
        "DEVCAPSULE_PEX_CLEAN_MACHINE_IMAGE", DEFAULT_CLEAN_MACHINE_IMAGE
    )
    inspected = command(docker, "image", "inspect", base_image, check=False)
    assert inspected.returncode == 0, (
        f"Clean-machine image {base_image!r} is not available locally; pull it explicitly "
        "or set DEVCAPSULE_PEX_CLEAN_MACHINE_IMAGE"
    )

    script = """
set -eu
for candidate in python python3 python3.12; do
    if command -v "${candidate}" >/dev/null 2>&1; then
        echo "unexpected host interpreter: ${candidate}" >&2
        exit 1
    fi
done
/devcapsule.pex --help >/tmp/devcapsule-help.txt
/devcapsule.pex version --json
"""
    created = command(
        docker,
        "create",
        "--network",
        "none",
        "--entrypoint",
        "/bin/sh",
        base_image,
        "-c",
        script,
    )
    container = created.stdout.strip()
    assert container

    try:
        command(docker, "cp", str(built_pex), f"{container}:/devcapsule.pex")
        completed = command(docker, "start", "--attach", container, check=False)
        assert completed.returncode == 0, completed.stderr
        version = json.loads(completed.stdout)
        assert version["schema_version"] == 2
        assert version["version"] == PACKAGE_VERSION
        assert version["build_mnemonic"] == os.environ.get(
            "DEVCAPSULE_EXPECTED_BUILD_MNEMONIC",
            f"v{PACKAGE_VERSION}-local-{os.environ.get('DEVCAPSULE_SCIE_PLATFORM', 'linux-x86_64')}",
        )
    finally:
        command(docker, "rm", "--force", container, check=False)
