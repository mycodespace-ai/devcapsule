"""Unit tests of ``devcapsule/container_runtime/console.py``: which console package the child imports."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.console import RUNTIME_CLI, console_child, console_package_path
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan

CHECKOUT_SOURCE = "/workspace/project/devcapsule-webconsole"


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


def _console_python(path: Path) -> Path:
    path.touch()
    return path


def _launcher_bundle(path: Path) -> Path:
    pkg = path / "devcapsule_webconsole"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return path


def test_console_package_path_prefers_the_plans_checkout_source(tmp_path: Path) -> None:
    """A non-empty ``console.source_path`` wins over an installed launcher package."""
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    assert console_package_path(CHECKOUT_SOURCE, bundled) == CHECKOUT_SOURCE


def test_console_package_path_selects_the_launcher_package_when_installed(tmp_path: Path) -> None:
    """Without a checkout source, the launcher package directory is selected when it holds the package."""
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    assert console_package_path("", bundled) == str(bundled)


def test_console_package_path_is_empty_when_only_the_base_copy_exists(tmp_path: Path) -> None:
    """Without a checkout source or an installed launcher package, the empty result leaves the base copy to the import."""
    absent = tmp_path / "launcher-webconsole"

    assert console_package_path("", absent) == ""


def test_console_child_runs_the_launcher_package_on_the_base_interpreter(tmp_path: Path) -> None:
    """With an empty ``console.source_path`` and an installed launcher package, ``PYTHONPATH`` selects that package."""
    python = _console_python(tmp_path / "python")
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


def test_console_child_runs_the_mounted_checkout_source_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With ``console.source_path`` set beside a launcher package, ``PYTHONPATH`` selects the checkout and stderr announces it."""
    python = _console_python(tmp_path / "python")
    bundled = _launcher_bundle(tmp_path / "launcher-webconsole")

    child = console_child(
        _plan(source_path=CHECKOUT_SOURCE),
        lambda command: command,
        console_python=python,
        launcher_source=bundled,
    )

    assert child is not None
    assert child.command[:3] == ("env", f"PYTHONPATH={CHECKOUT_SOURCE}", str(python))
    assert f"running the mounted checkout's source at {CHECKOUT_SOURCE}" in capsys.readouterr().err


def test_console_child_runs_the_base_copy_without_a_launcher_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With neither a checkout source nor a launcher package, the command carries no ``PYTHONPATH`` and nothing is announced."""
    python = _console_python(tmp_path / "python")

    child = console_child(
        _plan(),
        lambda command: command,
        console_python=python,
        launcher_source=tmp_path / "absent-launcher-webconsole",
    )

    assert child is not None
    assert child.command[:3] == (str(python), "-m", "devcapsule_webconsole")
    assert not any("PYTHONPATH" in item for item in child.command)
    assert capsys.readouterr().err == ""
