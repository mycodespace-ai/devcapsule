"""Unit tests of ``devcapsule/console_tools.py``: capsule decision-tool command selection and execution."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from devcapsule.compat import CliError
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.console_tools import DECISIONS_MODULE, console_decisions_command, run_console_decisions
from devcapsule.container_runtime.console import console_child
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan


def runtime_plan(source: str | None) -> RuntimePlan:
    plan = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/p",
        home="/home/devcapsule",
        identity=Identity(1000, 1000, "developer"),
    )
    if source is None:
        return plan
    return plan.with_console(ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token", source_path=source))


@pytest.mark.parametrize("environ", [{}, {"DEVCAPSULE_CONTAINER_NAME": ""}])
def test_outside_capsule_refuses_and_names_host_module(tmp_path: Path, environ: dict[str, str]) -> None:
    """Outside a capsule, ``console_decisions_command`` raises ``ProjectConfigurationError`` naming the host module."""
    with pytest.raises(ProjectConfigurationError, match=f"python -m {DECISIONS_MODULE}"):
        console_decisions_command(["check", "x.json"], environ=environ, console_python=tmp_path / "python")


def test_missing_console_interpreter_refuses_and_names_base_location(tmp_path: Path) -> None:
    """When ``console_python`` does not exist, ``console_decisions_command`` names ``/opt/devcapsule-webconsole``."""
    with pytest.raises(ProjectConfigurationError, match="no web console at /opt/devcapsule-webconsole"):
        console_decisions_command(
            ["check", "x.json"],
            environ={"DEVCAPSULE_CONTAINER_NAME": "c"},
            console_python=tmp_path / "absent",
            runtime_plan_path=tmp_path / "plan.json",
        )


@pytest.mark.parametrize("plan_kind", ["missing", "malformed", "non-utf8", "directory", "no-console", "installed"])
def test_installed_console_runs_when_plan_has_no_usable_source(tmp_path: Path, plan_kind: str) -> None:
    """Without a readable ``console.source_path``, ``console_decisions_command`` runs the base interpreter directly."""
    python = tmp_path / "python"
    python.touch()
    plan = tmp_path / "plan.json"
    if plan_kind == "malformed":
        plan.write_text("{", encoding="utf-8")
    elif plan_kind == "non-utf8":
        plan.write_bytes(b"\xff")
    elif plan_kind == "directory":
        plan.mkdir()
    elif plan_kind in ("no-console", "installed"):
        plan.write_text(runtime_plan(None if plan_kind == "no-console" else "").to_json(), encoding="utf-8")

    command = console_decisions_command(
        ["hand-off", "d/x.json", "--token-file", "t"],
        environ={"DEVCAPSULE_CONTAINER_NAME": "c"},
        console_python=python,
        runtime_plan_path=plan,
    )

    assert command == (str(python), "-m", DECISIONS_MODULE, "hand-off", "d/x.json", "--token-file", "t")


def test_mounted_source_uses_same_pythonpath_prefix_as_console_child(tmp_path: Path) -> None:
    """When ``console.source_path`` is set, ``console_decisions_command`` matches ``console_child``'s ``PYTHONPATH`` prefix."""
    python = tmp_path / "python"
    python.touch()
    plan = runtime_plan("/workspace/project with spaces/devcapsule-webconsole")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(plan.to_json(), encoding="utf-8")

    child = console_child(plan, lambda command: command, console_python=python)
    command = console_decisions_command(
        ["check", "x.json"],
        environ={"DEVCAPSULE_CONTAINER_NAME": "c"},
        console_python=python,
        runtime_plan_path=plan_path,
    )

    assert child is not None
    assert command[:2] == child.command[:2] == (
        "env",
        "PYTHONPATH=/workspace/project with spaces/devcapsule-webconsole",
    )
    assert command[2:] == (str(python), "-m", DECISIONS_MODULE, "check", "x.json")


@pytest.mark.parametrize("status", [0, 3])
def test_run_console_decisions_preserves_arguments_streams_and_exit_status(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], status: int,
) -> None:
    """``run_console_decisions`` passes argv verbatim to ``console_python``, streams output, and returns its exit code."""
    fake = tmp_path / "fake-console-python"
    fake.write_text(
        f"#!{sys.executable}\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n"
        f"print('console diagnostic', file=sys.stderr)\nsys.exit({status})\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    arguments = ["from-table", "table with spaces.md", "--id", "pass", "--title", "A title", "--context", "a\nb", "", "--"]

    result = run_console_decisions(
        arguments,
        environ={"DEVCAPSULE_CONTAINER_NAME": "capsule-fixture"},
        console_python=fake,
        runtime_plan_path=tmp_path / "no-plan.json",
    )

    assert result == status
    output = capfd.readouterr()
    assert json.loads(output.out) == ["-m", DECISIONS_MODULE, *arguments]
    assert output.err == "console diagnostic\n"


def test_run_console_decisions_raises_cli_error_when_interpreter_cannot_start(tmp_path: Path) -> None:
    """When executing ``console_python`` raises ``OSError``, ``run_console_decisions`` wraps it in ``CliError``."""
    python = tmp_path / "not-executable"
    python.touch(mode=0o600)

    with pytest.raises(CliError, match="cannot run the console's decision tools"):
        run_console_decisions(
            ["check", "x.json"],
            environ={"DEVCAPSULE_CONTAINER_NAME": "capsule-fixture"},
            console_python=python,
            runtime_plan_path=tmp_path / "no-plan.json",
        )
