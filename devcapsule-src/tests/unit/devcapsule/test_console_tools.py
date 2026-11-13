"""Unit tests of ``devcapsule/console_tools.py``: capsule decision-tool command selection and execution."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from devcapsule.compat import CliError
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.console_tools import DECISIONS_MODULE, DecisionTools
from devcapsule.container_runtime.console import ConsoleInstallation
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


def capsule_tools(tmp_path: Path, python: Path, *, launcher_package: bool = False) -> DecisionTools:
    """The decision tools inside a capsule whose console interpreter is ``python``.

    The runtime plan is ``tmp_path / "plan.json"``, absent until a test
    writes it. The launcher's package is absent unless ``launcher_package``.
    """
    launcher_source = tmp_path / "launcher-webconsole"
    if launcher_package:
        package = launcher_source / "devcapsule_webconsole"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
    return DecisionTools(
        in_capsule=True,
        console=ConsoleInstallation(python, launcher_source),
        runtime_plan_path=tmp_path / "plan.json",
    )


def interpreter_file(tmp_path: Path) -> Path:
    """An empty file where the console interpreter is; ``command`` checks only that it exists."""
    python = tmp_path / "python"
    python.touch()
    return python


def test_outside_capsule_refuses_and_names_host_module(tmp_path: Path) -> None:
    """Outside a capsule, ``command`` raises ``ProjectConfigurationError`` naming the host module, although an interpreter exists."""
    tools = DecisionTools(
        in_capsule=False,
        console=ConsoleInstallation(interpreter_file(tmp_path), tmp_path / "launcher-webconsole"),
        runtime_plan_path=tmp_path / "plan.json",
    )

    with pytest.raises(ProjectConfigurationError, match=f"python -m {DECISIONS_MODULE}"):
        tools.command(["check", "x.json"])


def test_missing_console_interpreter_refuses_and_names_base_location(tmp_path: Path) -> None:
    """Inside a capsule whose console interpreter does not exist, ``command`` names ``/opt/devcapsule-webconsole``."""
    tools = capsule_tools(tmp_path, tmp_path / "absent")

    with pytest.raises(ProjectConfigurationError, match="no web console at /opt/devcapsule-webconsole"):
        tools.command(["check", "x.json"])


@pytest.mark.parametrize("plan_kind", ["missing", "malformed", "non-utf8", "directory", "no-console", "installed"])
def test_installed_console_runs_when_plan_has_no_usable_source_and_no_launcher_bundle(
    tmp_path: Path, plan_kind: str,
) -> None:
    """Without a readable ``console.source_path`` or launcher package, ``command`` runs the base copy directly."""
    python = interpreter_file(tmp_path)
    tools = capsule_tools(tmp_path, python)
    plan = tools.runtime_plan_path
    if plan_kind == "malformed":
        plan.write_text("{", encoding="utf-8")
    elif plan_kind == "non-utf8":
        plan.write_bytes(b"\xff")
    elif plan_kind == "directory":
        plan.mkdir()
    elif plan_kind in ("no-console", "installed"):
        plan.write_text(runtime_plan(None if plan_kind == "no-console" else "").to_json(), encoding="utf-8")

    command = tools.command(["hand-off", "d/x.json", "--token-file", "t"])

    assert command == (str(python), "-m", DECISIONS_MODULE, "hand-off", "d/x.json", "--token-file", "t")


def test_decisions_command_uses_launcher_package_when_plan_sets_no_checkout_source(tmp_path: Path) -> None:
    """Without ``console.source_path``, ``command`` puts the launcher's console package on ``PYTHONPATH``."""
    python = interpreter_file(tmp_path)
    tools = capsule_tools(tmp_path, python, launcher_package=True)
    tools.runtime_plan_path.write_text(runtime_plan("").to_json(), encoding="utf-8")

    command = tools.command(["check", "decision.json"])

    assert command == (
        "env",
        f"PYTHONPATH={tmp_path / 'launcher-webconsole'}",
        str(python),
        "-m",
        DECISIONS_MODULE,
        "check",
        "decision.json",
    )


def test_mounted_source_takes_precedence_over_launcher_package(tmp_path: Path) -> None:
    """``command`` selects the plan's checkout source ahead of the launcher package, preserving spaces."""
    python = interpreter_file(tmp_path)
    tools = capsule_tools(tmp_path, python, launcher_package=True)
    plan = runtime_plan("/workspace/project with spaces/devcapsule-webconsole")
    tools.runtime_plan_path.write_text(plan.to_json(), encoding="utf-8")

    command = tools.command(["check", "x.json"])

    assert command[:2] == (
        "env",
        "PYTHONPATH=/workspace/project with spaces/devcapsule-webconsole",
    )
    assert command[2:] == (str(python), "-m", DECISIONS_MODULE, "check", "x.json")


@pytest.mark.parametrize("status", [0, 3])
def test_run_preserves_arguments_streams_and_exit_status(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], status: int,
) -> None:
    """Inside a capsule, ``run`` passes argv verbatim to the console interpreter, streams its output, and returns its exit code."""
    fake = tmp_path / "fake-console-python"
    # ``-I`` keeps the stand-in interpreter away from the Python settings of the host's environment.
    fake.write_text(
        f"#!{sys.executable} -I\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n"
        f"print('console diagnostic', file=sys.stderr)\nsys.exit({status})\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    arguments = ["from-table", "table with spaces.md", "--id", "pass", "--title", "A title", "--context", "a\nb", "", "--"]

    result = capsule_tools(tmp_path, fake).run(arguments)

    assert result == status
    output = capfd.readouterr()
    assert json.loads(output.out) == ["-m", DECISIONS_MODULE, *arguments]
    assert output.err == "console diagnostic\n"


def test_run_raises_cli_error_naming_an_interpreter_that_cannot_start(tmp_path: Path) -> None:
    """When the console interpreter cannot be executed, ``run`` raises a ``CliError`` that names it."""
    python = tmp_path / "not-executable"
    python.touch(mode=0o600)

    with pytest.raises(CliError, match="cannot run the console's decision tools") as caught:
        capsule_tools(tmp_path, python).run(["check", "x.json"])

    assert str(python) in str(caught.value)
