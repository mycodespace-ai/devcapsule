"""Unit tests of ``devcapsule/container_runtime/console.py``: launcher package precedence and base fallback."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.console import RUNTIME_CLI, console_child
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan


def _plan(*, source_path: str = "") -> RuntimePlan:
    base = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000, "developer"),
    )
    return base.with_console(
        ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token", source_path=source_path)
    )


def _python_stub(path: Path, *, has_psutil: bool) -> Path:
    code = 0 if has_psutil else 1
    path.write_text(f"#!/bin/sh\nexit {code}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _launcher_bundle(path: Path) -> Path:
    pkg = path / "devcapsule_webconsole"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return path


def test_console_child_runs_launcher_package_when_present_and_compatible(tmp_path: Path) -> None:
    """When ``console.source_path`` is empty and the launcher package is installed on a recipe-11+ base, ``PYTHONPATH`` selects it."""
    python = _python_stub(tmp_path / "python", has_psutil=True)
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    child = console_child(
        _plan(),
        lambda command: ("as-user", *command),
        console_python=python,
        launcher_source=bundled,
    )

    assert child is not None
    assert child.command == (
        "as-user",
        "env",
        f"PYTHONPATH={bundled}",
        str(python),
        "-m",
        "devcapsule_webconsole",
        "--project",
        "/workspace/project",
        "--cli",
        RUNTIME_CLI,
        "--token-file",
        "/run/devcapsule-console-token",
        "--listen",
        "0.0.0.0",
        "--port",
        "6081",
    )


def test_console_child_prefers_explicit_checkout_source_over_launcher_package(tmp_path: Path) -> None:
    """When ``console.source_path`` is set alongside a launcher package, ``PYTHONPATH`` selects the checkout source."""
    python = _python_stub(tmp_path / "python", has_psutil=True)
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    child = console_child(
        _plan(source_path="/workspace/project/devcapsule-webconsole"),
        lambda command: command,
        console_python=python,
        launcher_source=bundled,
    )

    assert child is not None
    assert child.command[:3] == (
        "env",
        "PYTHONPATH=/workspace/project/devcapsule-webconsole",
        str(python),
    )


def test_console_child_falls_back_to_base_copy_when_base_lacks_psutil(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When the base interpreter lacks ``psutil`` (recipe 10), ``console_child`` skips the launcher package and runs the base copy."""
    python = _python_stub(tmp_path / "python", has_psutil=False)
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    child = console_child(
        _plan(),
        lambda command: command,
        console_python=python,
        launcher_source=bundled,
    )

    assert child is not None
    assert child.command[:3] == (str(python), "-m", "devcapsule_webconsole")
    assert not any("PYTHONPATH" in item for item in child.command)
    assert "running the base image's console instead of the launcher's package" in capsys.readouterr().err
