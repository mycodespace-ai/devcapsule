"""Unit tests of ``devcapsule/console_tools.py``: decision CLI source precedence."""

from __future__ import annotations

from pathlib import Path

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.console_tools import DECISIONS_MODULE, console_decisions_command
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan


def _write_plan(path: Path, *, source_path: str = "") -> Path:
    base = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000, "developer"),
    )
    plan = base.with_console(
        ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token", source_path=source_path)
    )
    path.write_text(plan.to_json(), encoding="utf-8")
    return path


def _launcher_bundle(path: Path) -> Path:
    pkg = path / "devcapsule_webconsole"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return path


def test_decisions_command_uses_launcher_package_when_plan_sets_no_checkout_source(tmp_path: Path) -> None:
    """Without ``console.source_path``, ``console_decisions_command`` puts the launcher's console package on ``PYTHONPATH``."""
    python = tmp_path / "python"
    python.touch()
    plan = _write_plan(tmp_path / "plan.json")
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    command = console_decisions_command(
        ["check", "decision.json"],
        environ={"DEVCAPSULE_CONTAINER_NAME": "capsule"},
        console_python=python,
        runtime_plan_path=plan,
        launcher_console_source=bundled,
    )

    assert command == (
        "env",
        f"PYTHONPATH={bundled}",
        str(python),
        "-m",
        DECISIONS_MODULE,
        "check",
        "decision.json",
    )


def test_decisions_command_prefers_checkout_source_over_launcher_package(tmp_path: Path) -> None:
    """When ``console.source_path`` is set in the runtime plan, it takes precedence over the launcher package."""
    python = tmp_path / "python"
    python.touch()
    plan = _write_plan(tmp_path / "plan.json", source_path="/workspace/project/devcapsule-webconsole")
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    command = console_decisions_command(
        ["hand-off", "decision.json"],
        environ={"DEVCAPSULE_CONTAINER_NAME": "capsule"},
        console_python=python,
        runtime_plan_path=plan,
        launcher_console_source=bundled,
    )

    assert command[:2] == ("env", "PYTHONPATH=/workspace/project/devcapsule-webconsole")


def test_decisions_command_runs_the_base_copy_without_a_launcher_package(tmp_path: Path) -> None:
    """Without ``console.source_path`` or an installed launcher package, the command carries no ``PYTHONPATH``."""
    python = tmp_path / "python"
    python.touch()
    plan = _write_plan(tmp_path / "plan.json")

    command = console_decisions_command(
        ["check", "decision.json"],
        environ={"DEVCAPSULE_CONTAINER_NAME": "capsule"},
        console_python=python,
        runtime_plan_path=plan,
        launcher_console_source=tmp_path / "absent-launcher-webconsole",
    )

    assert command == (str(python), "-m", DECISIONS_MODULE, "check", "decision.json")
