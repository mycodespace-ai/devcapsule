"""Unit tests of ``devcapsule/console_tools.py``: capsule decision-tool command selection and execution."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from devcapsule import recursive_dogfood
from devcapsule.compat import CliError
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.console_tools import DECISIONS_MODULE, console_decisions_command, run_console_decisions
from devcapsule.container_runtime import console
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


def launcher_bundle(path: Path) -> Path:
    pkg = path / "devcapsule_webconsole"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return path


def enter_capsule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, console_python: Path) -> None:
    """Make the process a capsule's: its name in the environment, ``console_python`` as the base's console interpreter, no runtime plan and no launcher console package."""
    monkeypatch.setenv(recursive_dogfood.CONTAINER_NAME_ENV, "capsule-fixture")
    monkeypatch.setattr(console, "CONSOLE_PYTHON", str(console_python))
    monkeypatch.setattr(console, "LAUNCHER_CONSOLE_SOURCE", str(tmp_path / "absent-launcher-webconsole"))
    monkeypatch.setattr(recursive_dogfood, "RUNTIME_PLAN_PATH", tmp_path / "no-plan.json")


@pytest.mark.parametrize("environ", [{}, {"DEVCAPSULE_CONTAINER_NAME": ""}])
def test_outside_capsule_refuses_and_names_host_module(tmp_path: Path, environ: dict[str, str]) -> None:
    """Outside a capsule, ``console_decisions_command`` raises ``ProjectConfigurationError`` naming the host module."""
    with pytest.raises(ProjectConfigurationError, match=f"python -m {DECISIONS_MODULE}"):
        console_decisions_command(
            ["check", "x.json"],
            environ=environ,
            console_python=tmp_path / "python",
            launcher_console_source=tmp_path / "absent",
        )


def test_missing_console_interpreter_refuses_and_names_base_location(tmp_path: Path) -> None:
    """When ``console_python`` does not exist, ``console_decisions_command`` names ``/opt/devcapsule-webconsole``."""
    with pytest.raises(ProjectConfigurationError, match="no web console at /opt/devcapsule-webconsole"):
        console_decisions_command(
            ["check", "x.json"],
            environ={"DEVCAPSULE_CONTAINER_NAME": "c"},
            console_python=tmp_path / "absent",
            runtime_plan_path=tmp_path / "plan.json",
            launcher_console_source=tmp_path / "absent-bundle",
        )


@pytest.mark.parametrize("plan_kind", ["missing", "malformed", "non-utf8", "directory", "no-console", "installed"])
def test_installed_console_runs_when_plan_has_no_usable_source_and_no_launcher_bundle(
    tmp_path: Path, plan_kind: str,
) -> None:
    """Without a readable ``console.source_path`` or launcher package, ``console_decisions_command`` runs the base copy directly."""
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
        launcher_console_source=tmp_path / "absent-launcher-webconsole",
    )

    assert command == (str(python), "-m", DECISIONS_MODULE, "hand-off", "d/x.json", "--token-file", "t")


def test_decisions_command_uses_launcher_package_when_plan_sets_no_checkout_source(tmp_path: Path) -> None:
    """Without ``console.source_path``, ``console_decisions_command`` puts the launcher's console package on ``PYTHONPATH``."""
    python = tmp_path / "python"
    python.touch()
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(runtime_plan("").to_json(), encoding="utf-8")
    bundled = launcher_bundle(tmp_path / "launcher-webconsole")

    command = console_decisions_command(
        ["check", "decision.json"],
        environ={"DEVCAPSULE_CONTAINER_NAME": "capsule"},
        console_python=python,
        runtime_plan_path=plan_path,
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


def test_mounted_source_uses_same_pythonpath_prefix_as_console_child_ahead_of_launcher_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``console.source_path`` is set, ``console_decisions_command`` matches ``console_child`` and overrides ``launcher_console_source``."""
    python = tmp_path / "python"
    python.touch()
    bundled = launcher_bundle(tmp_path / "launcher-webconsole")
    plan = runtime_plan("/workspace/project with spaces/devcapsule-webconsole")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(plan.to_json(), encoding="utf-8")
    monkeypatch.setattr(console, "CONSOLE_PYTHON", str(python))
    monkeypatch.setattr(console, "LAUNCHER_CONSOLE_SOURCE", str(bundled))

    child = console_child(plan, lambda command: command)
    command = console_decisions_command(
        ["check", "x.json"],
        environ={"DEVCAPSULE_CONTAINER_NAME": "c"},
        console_python=python,
        runtime_plan_path=plan_path,
        launcher_console_source=bundled,
    )

    assert child is not None
    assert command[:2] == child.command[:2] == (
        "env",
        "PYTHONPATH=/workspace/project with spaces/devcapsule-webconsole",
    )
    assert command[2:] == (str(python), "-m", DECISIONS_MODULE, "check", "x.json")


@pytest.mark.parametrize("status", [0, 3])
def test_run_console_decisions_preserves_arguments_streams_and_exit_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str], status: int,
) -> None:
    """Inside a capsule, ``run_console_decisions`` passes argv verbatim to the base's console interpreter, streams its output, and returns its exit code."""
    fake = tmp_path / "fake-console-python"
    fake.write_text(
        f"#!{sys.executable}\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n"
        f"print('console diagnostic', file=sys.stderr)\nsys.exit({status})\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    arguments = ["from-table", "table with spaces.md", "--id", "pass", "--title", "A title", "--context", "a\nb", "", "--"]
    enter_capsule(tmp_path, monkeypatch, fake)

    result = run_console_decisions(arguments)

    assert result == status
    output = capfd.readouterr()
    assert json.loads(output.out) == ["-m", DECISIONS_MODULE, *arguments]
    assert output.err == "console diagnostic\n"


def test_run_console_decisions_raises_cli_error_naming_an_interpreter_that_cannot_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the base's console interpreter cannot be executed, ``run_console_decisions`` raises a ``CliError`` that names it."""
    python = tmp_path / "not-executable"
    python.touch(mode=0o600)
    enter_capsule(tmp_path, monkeypatch, python)

    with pytest.raises(CliError, match="cannot run the console's decision tools") as caught:
        run_console_decisions(["check", "x.json"])

    assert str(python) in str(caught.value)
