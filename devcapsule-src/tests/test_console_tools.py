"""The runtime CLI delegates decision tools to the capsule's console interpreter."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from devcapsule import cli
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.console_tools import DECISIONS_MODULE, console_decisions_command
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime import console as console_child
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan

pytestmark = pytest.mark.legacy


CLI_PREFIX = ["project", "checkout", "decisions"]


def runtime_plan(source: str | None) -> RuntimePlan:
    """None omits the console; an empty source selects its installed package."""
    plan = RuntimePlan.for_component(pycharm_runtime_template(), project_path="/workspace/p", home="/home/devcapsule",
                                     identity=Identity(1000, 1000, "developer"))
    if source is None:
        return plan
    return plan.with_console(ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token", source_path=source))


@pytest.mark.parametrize("environ", [{}, {"DEVCAPSULE_CONTAINER_NAME": ""}])
def test_outside_a_capsule_the_command_names_the_module_to_run_instead(tmp_path: Path, environ) -> None:
    with pytest.raises(ProjectConfigurationError, match=f"python -m {DECISIONS_MODULE}"):
        console_decisions_command(["check", "x.json"], environ=environ, console_python=tmp_path / "python")


def test_a_base_without_the_console_is_named(tmp_path: Path) -> None:
    with pytest.raises(ProjectConfigurationError, match="no web console at /opt/devcapsule-webconsole"):
        console_decisions_command(["check", "x.json"], environ={"DEVCAPSULE_CONTAINER_NAME": "c"},
                                  console_python=tmp_path / "absent", runtime_plan_path=tmp_path / "plan.json")


@pytest.mark.parametrize("plan_kind", ["missing", "malformed", "non-utf8", "directory", "no-console", "installed"])
def test_the_installed_console_runs_when_the_plan_has_no_usable_source(tmp_path: Path, plan_kind: str) -> None:
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
    command = console_decisions_command(["hand-off", "d/x.json", "--token-file", "t"],
                                        environ={"DEVCAPSULE_CONTAINER_NAME": "c"}, console_python=python,
                                        runtime_plan_path=plan)
    assert command == (str(python), "-m", "devcapsule_webconsole.decisions", "hand-off", "d/x.json", "--token-file", "t")


@pytest.mark.parametrize("status", [0, 3])
def test_cli_preserves_argument_boundaries_streams_and_exit_status(tmp_path: Path, capfd, monkeypatch, status: int) -> None:
    fake = tmp_path / "fake-console-python"
    fake.write_text(f"#!{sys.executable}\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n"
                    f"print('console diagnostic', file=sys.stderr)\nsys.exit({status})\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setattr(console_child, "CONSOLE_PYTHON", str(fake))
    monkeypatch.setattr("devcapsule.recursive_dogfood.RUNTIME_PLAN_PATH", tmp_path / "no-plan.json")
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "capsule-fixture")
    monkeypatch.chdir(tmp_path)
    arguments = ["from-table", "table with spaces.md", "--id", "pass", "--title", "A title", "--context", "a\nb", "", "--"]
    assert cli.main([*CLI_PREFIX, *arguments]) == status
    output = capfd.readouterr()
    assert json.loads(output.out) == ["-m", "devcapsule_webconsole.decisions", *arguments]
    assert output.err == "console diagnostic\n"


@pytest.mark.parametrize("inside", [False, True])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_wrapper_help_needs_no_console(tmp_path: Path, capsys, monkeypatch, inside: bool, flag: str) -> None:
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "capsule-fixture" if inside else "")
    monkeypatch.setattr(console_child, "CONSOLE_PYTHON", str(tmp_path / "absent"))
    monkeypatch.chdir(tmp_path)
    assert cli.main([*CLI_PREFIX, flag]) == 0
    output = capsys.readouterr()
    assert "from-table, check or hand-off" in output.out
    assert output.err == ""


@pytest.mark.parametrize("arguments, status, expected", [
    ([], 2, "the following arguments are required: command"),
    (["from-table", "--help"], 0, "--asked-by"),
    (["check", "--help"], 0, "decision"),
    (["hand-off", "--help"], 0, "--token-file"),
])
def test_module_owns_empty_arguments_and_subcommand_help(tmp_path: Path, capfd, monkeypatch,
                                                       arguments: list[str], status: int, expected: str) -> None:
    source = Path(__file__).resolve().parents[2] / "devcapsule-webconsole"
    plan = tmp_path / "plan.json"
    plan.write_text(runtime_plan(str(source)).to_json(), encoding="utf-8")
    monkeypatch.setattr(console_child, "CONSOLE_PYTHON", sys.executable)
    monkeypatch.setattr("devcapsule.recursive_dogfood.RUNTIME_PLAN_PATH", plan)
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "capsule-fixture")
    monkeypatch.chdir(tmp_path)
    assert cli.main([*CLI_PREFIX, *arguments]) == status
    output = capfd.readouterr()
    assert "devcapsule-webconsole decisions" in output.out + output.err
    assert expected in (output.err if status else output.out)
    assert (output.out if status else output.err) == ""


@pytest.mark.parametrize("arguments", [[], ["check", "x.json"]])
@pytest.mark.parametrize("inside", [False, True])
def test_cli_reports_environment_refusals(tmp_path: Path, capsys, monkeypatch, arguments: list[str], inside: bool) -> None:
    monkeypatch.setattr(console_child, "CONSOLE_PYTHON", str(tmp_path / "absent"))
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "capsule-fixture" if inside else "")
    monkeypatch.chdir(tmp_path)
    assert cli.main([*CLI_PREFIX, *arguments]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert ("no web console" if inside else "runs inside a capsule") in output.err


def test_cli_reports_an_interpreter_that_cannot_start(tmp_path: Path, capsys, monkeypatch) -> None:
    python = tmp_path / "not-executable"
    python.touch(mode=0o600)
    monkeypatch.setattr(console_child, "CONSOLE_PYTHON", str(python))
    monkeypatch.setattr("devcapsule.recursive_dogfood.RUNTIME_PLAN_PATH", tmp_path / "no-plan.json")
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "capsule-fixture")
    monkeypatch.chdir(tmp_path)
    assert cli.main([*CLI_PREFIX, "check", "x.json"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "cannot run the console's decision tools" in output.err
    assert str(python) in output.err
