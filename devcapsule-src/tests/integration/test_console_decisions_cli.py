"""Integration tests of ``devcapsule project checkout decisions``: the real command line, in a process whose environment the test builds.

What the command does inside a capsule depends on two fixed paths of the
image, the console interpreter and the runtime plan, which a test cannot
build. The forwarding case requires an installed console and skips when
one is absent. It checks a file under its own scratch and does not send
a decision or contact the console server.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from devcapsule.container_runtime.console import ConsoleInstallation

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
        "PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
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


def test_cli_forwards_the_check_subcommand_and_its_path(tmp_path: Path) -> None:
    """With an installed console, the real command checks the named file and reports its invalid JSON."""
    if not ConsoleInstallation.of_image().python.is_file():
        pytest.skip("argument forwarding requires the image's console interpreter")
    decision = tmp_path / "forwarded-argument.json"
    decision.write_text("not JSON", encoding="utf-8")

    completed = checkout_decisions(tmp_path, "check", str(decision), container_name="capsule-fixture")

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "forwarded-argument.json" in completed.stderr
    assert "JSON" in completed.stderr
