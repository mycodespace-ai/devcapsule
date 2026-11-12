"""Integration tests of ``devcapsule project checkout decisions``: the real command line, in a process whose environment the test builds.

What the command does inside a capsule depends on two fixed paths of the
image, the console interpreter and the runtime plan, which a test cannot
build. ``tests/unit/devcapsule/test_console_tools.py`` covers those
decisions from values, and ``tests/e2e/test_console_answers.py`` runs the
command in a real capsule.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def checkout_decisions(
    tmp_path: Path, *arguments: str, container_name: str | None,
) -> subprocess.CompletedProcess[str]:
    """Run ``devcapsule project checkout decisions`` in a new process.

    The process gets a search path, a home and a DevCapsule configuration
    home under ``tmp_path``, and ``DEVCAPSULE_CONTAINER_NAME`` only when
    ``container_name`` is given; nothing of the caller's environment.
    """
    environment = {
        "PATH": os.defpath,
        "HOME": str(tmp_path / "home"),
        "DEVCAPSULE_CONFIG_HOME": str(tmp_path / "config"),
    }
    if container_name is not None:
        environment["DEVCAPSULE_CONTAINER_NAME"] = container_name
    return subprocess.run(
        [sys.executable, "-m", "devcapsule", "project", "checkout", "decisions", *arguments],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=120, check=False,
    )


@pytest.mark.parametrize("container_name", [None, "capsule-fixture"], ids=["on a host", "in a capsule"])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_wrapper_help_succeeds_without_running_console_interpreter(
    tmp_path: Path, container_name: str | None, flag: str,
) -> None:
    """``project checkout decisions -h/--help`` prints the wrapper's help and exits 0, on a host and in a capsule alike."""
    completed = checkout_decisions(tmp_path, flag, container_name=container_name)

    assert completed.returncode == 0
    assert "from-table, check or hand-off" in completed.stdout
    assert completed.stderr == ""


@pytest.mark.parametrize("container_name", [None, ""], ids=["no variable", "empty variable"])
@pytest.mark.parametrize("arguments", [(), ("check", "x.json")], ids=["no arguments", "check"])
def test_cli_reports_outside_capsule_refusal_with_usage_exit_code(
    tmp_path: Path, container_name: str | None, arguments: tuple[str, ...],
) -> None:
    """Without a container name in the environment, the command prints the ``runs inside a capsule`` refusal on stderr and exits 2."""
    completed = checkout_decisions(tmp_path, *arguments, container_name=container_name)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "runs inside a capsule" in completed.stderr


def test_cli_does_not_give_the_hosts_refusal_inside_a_capsule(tmp_path: Path) -> None:
    """With a container name in the environment, the command gets past the refusal that belongs to a host.

    What it does next depends on the image: without a console it names the
    missing base, with one it runs the console's own ``check``. Either way
    ``x.json`` is not checked, so it fails, and not with the host's words.
    """
    completed = checkout_decisions(tmp_path, "check", "x.json", container_name="capsule-fixture")

    assert completed.returncode != 0
    assert "runs inside a capsule" not in completed.stderr
