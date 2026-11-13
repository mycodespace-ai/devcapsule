"""Integration tests of ``project run --print-command``: the built launcher, with a stand-in where ``docker`` is.

Printing a launch's command brings nothing to the machine. Each test runs the
built executable in an environment it builds: a home and a project under the
test's directory, and a search path whose ``docker`` is a script the test
writes. The script records every call, answers that no image is local, and
refuses any other request, so a launcher that asked Docker to pull or build
would be seen and would fail. The proxy variables send every download to a
closed port of this machine: a launcher that tried one would fail at once and
receive nothing.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess

import pytest

pytestmark = pytest.mark.integration

STAND_IN_DOCKER = """#!/bin/sh
# Stands where docker is. Every call is recorded; only a question about a local image is answered.
echo "$*" >> "$DOCKER_STAND_IN_CALLS"
if [ "$1 $2" = "image inspect" ]; then
    echo "[]"
    echo "Error response from daemon: No such image: $3" >&2
    exit 1
fi
echo "the stand-in for docker was asked to: $*" >&2
exit 97
"""

CLOSED_PORT = "http://127.0.0.1:9"


@pytest.fixture
def launcher(built_pex: Path, tmp_path: Path):
    """Run the built launcher on ``tmp_path / "project"`` in the test's own environment; the calls made to
    ``docker`` are the lines of ``tmp_path / "docker-calls"``."""
    tools = tmp_path / "tools"
    tools.mkdir()
    docker = tools / "docker"
    docker.write_text(STAND_IN_DOCKER, encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    (tmp_path / "project").mkdir()
    environment = {
        "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
        "DEVCAPSULE_CONFIG_HOME": str(tmp_path / "devcapsule-home"),
        "DOCKER_STAND_IN_CALLS": str(tmp_path / "docker-calls"),
        "http_proxy": CLOSED_PORT, "https_proxy": CLOSED_PORT, "HTTP_PROXY": CLOSED_PORT, "HTTPS_PROXY": CLOSED_PORT,
        # The executable unpacks itself once into these caches, which the suite keeps for the whole run.
        **{name: os.environ[name] for name in ("PEX_ROOT", "SCIE_BASE") if name in os.environ},
    }

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(built_pex), "project", "--path", str(tmp_path / "project"), *arguments],
            cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=300, check=False,
        )

    return run


def test_print_command_names_a_base_image_that_is_not_here_and_pulls_nothing(launcher, tmp_path: Path) -> None:
    """On a machine whose Docker has no image, ``run --print-command`` exits 2 and says that a launch pulls the
    base image. It asks Docker only whether the image is local, prints no command, and downloads no file."""
    created = launcher("init", "--require", "python", "--ide", "python-ide",
                       "--creator", "mailto:owner@example.test", "--authorize", "base-image", "default")
    assert created.returncode == 0, created.stderr

    printed = launcher("run", "--print-command", "--no-update-check")

    assert printed.returncode == 2, printed.stdout + printed.stderr
    assert printed.stdout == ""
    assert "is not on this machine. A launch pulls it; nothing was pulled now." in printed.stderr
    assert "--print-command prints the command of an environment that is already here" in printed.stderr
    calls = (tmp_path / "docker-calls").read_text(encoding="utf-8").splitlines()
    assert calls and all(call.startswith("image inspect ") for call in calls), calls
    downloaded = [path for path in (tmp_path / "home").rglob("*") if path.is_file() and "artifacts" in path.parts]
    assert downloaded == []


def test_print_command_with_a_trust_flag_records_no_acceptance(launcher, tmp_path: Path) -> None:
    """A checkout whose base waits for the home's trust: ``run --print-command`` alone ends pending, exit 3.
    With ``--trust devcapsule-base`` the review passes and the command goes on to look for the base image, so
    the flag was taken; and the home still has no settings file, because printing records no acceptance."""
    created = launcher("init", "--require", "python", "--creator", "mailto:owner@example.test")
    assert created.returncode == 0, created.stderr
    chosen = launcher("config", "ide", "python-ide")
    assert chosen.returncode == 0, chosen.stderr
    pending = launcher("run", "--print-command", "--no-update-check")
    assert pending.returncode == 3 and "--trust devcapsule-base" in pending.stderr, pending.stdout + pending.stderr

    printed = launcher("run", "--print-command", "--trust", "devcapsule-base", "--no-update-check")

    assert printed.returncode == 2, printed.stdout + printed.stderr
    assert "is not on this machine. A launch pulls it; nothing was pulled now." in printed.stderr
    assert not (tmp_path / "devcapsule-home" / "settings.toml").exists()
