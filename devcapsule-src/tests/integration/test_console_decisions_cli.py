"""Integration tests of ``devcapsule project checkout decisions`` against ``devcapsule_webconsole.decisions``."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from devcapsule import cli
from devcapsule.commands.project import CheckoutDecisionsCommand
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan

pytestmark = pytest.mark.integration

CLI_PREFIX = ["project", "checkout", "decisions"]


def runtime_plan_with_source(source: Path) -> RuntimePlan:
    return RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/p",
        home="/home/devcapsule",
        identity=Identity(1000, 1000, "developer"),
    ).with_console(ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token", source_path=str(source)))


@pytest.mark.parametrize("inside", [False, True])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_wrapper_help_succeeds_without_running_console_interpreter(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, inside: bool, flag: str,
) -> None:
    """``devcapsule project checkout decisions -h/--help`` prints wrapper help without requiring a console interpreter."""
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "capsule-fixture" if inside else "")
    monkeypatch.chdir(tmp_path)

    assert cli.main([*CLI_PREFIX, flag]) == 0
    output = capsys.readouterr()
    assert "from-table, check or hand-off" in output.out
    assert output.err == ""


@pytest.mark.parametrize(
    ("arguments", "status", "expected"),
    [
        ([], 2, "the following arguments are required: command"),
        (["from-table", "--help"], 0, "--asked-by"),
        (["check", "--help"], 0, "decision"),
        (["hand-off", "--help"], 0, "--token-file"),
    ],
)
def test_decisions_module_owns_empty_arguments_and_subcommand_help(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    arguments: list[str],
    status: int,
    expected: str,
) -> None:
    """``CheckoutDecisionsCommand`` delegates subcommand ``--help`` and empty-argument errors to ``devcapsule_webconsole.decisions``."""
    source = Path(__file__).resolve().parents[3] / "devcapsule-webconsole"
    plan = tmp_path / "plan.json"
    plan.write_text(runtime_plan_with_source(source).to_json(), encoding="utf-8")

    result = CheckoutDecisionsCommand.invoke(
        "devcapsule project checkout decisions",
        arguments,
        environ={"DEVCAPSULE_CONTAINER_NAME": "capsule-fixture"},
        console_python=Path(sys.executable),
        runtime_plan_path=plan,
    )

    assert result == status
    output = capfd.readouterr()
    assert "devcapsule-webconsole decisions" in output.out + output.err
    assert expected in (output.err if status else output.out)
    assert (output.out if status else output.err) == ""


@pytest.mark.parametrize("arguments", [[], ["check", "x.json"]])
def test_cli_reports_outside_capsule_refusal_with_usage_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, arguments: list[str],
) -> None:
    """Outside a capsule, ``cli.main`` prints the ``runs inside a capsule`` refusal on stderr and returns exit code 2."""
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "")
    monkeypatch.chdir(tmp_path)

    assert cli.main([*CLI_PREFIX, *arguments]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "runs inside a capsule" in output.err
