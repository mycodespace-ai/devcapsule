"""Unit tests of ``devcapsule/container_runtime/console.py``: package precedence, the supervised child and its readiness probe."""

from __future__ import annotations

from pathlib import Path
import socket

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.console import (
    CONSOLE_CHILD,
    CONSOLE_PYTHON,
    CONSOLE_READY_TIMEOUT_SECONDS,
    CONSOLE_ROOT,
    LAUNCHER_CONSOLE_SOURCE,
    RUNTIME_CLI,
    ConsoleInstallation,
    probe_address,
)
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan
from devcapsule.images.tooling import WEBCONSOLE_ROOT, WEBCONSOLE_VENV_PYTHON
from devcapsule.materialization import ENTRYPOINT_CONTRACT
from devcapsule.webconsole_bundle import LAUNCHER_WEBCONSOLE_PATH

CHECKOUT_SOURCE = "/workspace/project/devcapsule-webconsole"


def runtime_plan(tmp_path: Path, *, console: ConsolePlan | None) -> RuntimePlan:
    plan = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home=str(tmp_path / "home"),
        identity=Identity(1000, 1000, "developer"),
    )
    return plan if console is None else plan.with_console(console)


def base_installation(tmp_path: Path) -> ConsoleInstallation:
    """An installation as a base image alone provides it: an interpreter file, and no launcher package.

    The interpreter is an empty file. ``child`` only checks that it exists;
    no test here executes it.
    """
    python = tmp_path / "base-python"
    python.touch()
    return ConsoleInstallation(python, tmp_path / "launcher-webconsole")


def with_launcher_package(installation: ConsoleInstallation) -> ConsoleInstallation:
    """Put the console package at the installation's launcher source, as materialization does."""
    package = installation.launcher_source / "devcapsule_webconsole"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    return installation


def test_runtime_and_base_recipe_agree_on_console_paths() -> None:
    """``console.py`` constants match the base image's web-console root, venv interpreter, launcher bundle path, and CLI path."""
    assert CONSOLE_ROOT == WEBCONSOLE_ROOT
    assert CONSOLE_PYTHON == WEBCONSOLE_VENV_PYTHON
    assert LAUNCHER_CONSOLE_SOURCE == LAUNCHER_WEBCONSOLE_PATH
    assert RUNTIME_CLI == ENTRYPOINT_CONTRACT[0]


def test_of_image_names_the_images_interpreter_and_launcher_package() -> None:
    """``ConsoleInstallation.of_image`` is the installation at ``CONSOLE_PYTHON`` and ``LAUNCHER_CONSOLE_SOURCE``."""
    assert ConsoleInstallation.of_image() == ConsoleInstallation(
        Path("/opt/devcapsule-webconsole/venv/bin/python"), Path("/opt/devcapsule/webconsole"),
    )


def test_package_path_prefers_the_plans_checkout_source(tmp_path: Path) -> None:
    """A non-empty ``console.source_path`` wins over an installed launcher package."""
    installation = with_launcher_package(base_installation(tmp_path))

    assert installation.package_path(CHECKOUT_SOURCE) == CHECKOUT_SOURCE


def test_package_path_selects_the_launcher_package_when_installed(tmp_path: Path) -> None:
    """Without a checkout source, the launcher package directory is selected when it holds the package."""
    installation = with_launcher_package(base_installation(tmp_path))

    assert installation.package_path("") == str(installation.launcher_source)


def test_package_path_is_empty_when_only_the_base_copy_exists(tmp_path: Path) -> None:
    """Without a checkout source or an installed launcher package, the empty result leaves the base copy to the import."""
    assert base_installation(tmp_path).package_path("") == ""


def test_child_runs_the_launcher_package_on_the_base_interpreter(tmp_path: Path) -> None:
    """With an empty ``console.source_path`` and an installed launcher package, ``PYTHONPATH`` selects that package."""
    installation = with_launcher_package(base_installation(tmp_path))
    plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))

    child = installation.child(plan, lambda command: ("as-user", *command))

    assert child is not None
    assert child.name == CONSOLE_CHILD
    assert child.foreground is False
    assert child.command == (
        "as-user",
        "env",
        f"PYTHONPATH={installation.launcher_source}",
        str(installation.python),
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
    assert child.ready is not None
    assert child.ready_timeout_seconds == CONSOLE_READY_TIMEOUT_SECONDS


def test_child_runs_the_base_copy_without_a_launcher_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """With neither a checkout source nor a launcher package, the command carries no ``PYTHONPATH`` and nothing is announced."""
    installation = base_installation(tmp_path)
    plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))

    child = installation.child(plan, lambda command: ("as-user", *command))

    assert child is not None
    assert child.command == (
        "as-user",
        str(installation.python),
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
    assert capsys.readouterr().err == ""


def test_child_runs_the_mounted_checkout_source_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """With ``console.source_path`` set beside a launcher package, ``PYTHONPATH`` selects the checkout and stderr announces it."""
    installation = with_launcher_package(base_installation(tmp_path))
    plan = runtime_plan(
        tmp_path,
        console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token", source_path=CHECKOUT_SOURCE),
    )

    child = installation.child(plan, lambda command: command)

    assert child is not None
    assert child.command[:3] == ("env", f"PYTHONPATH={CHECKOUT_SOURCE}", str(installation.python))
    assert f"running the mounted checkout's source at {CHECKOUT_SOURCE}" in capsys.readouterr().err


def test_child_is_none_when_plan_omits_console(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Without a ``console`` section in ``RuntimePlan``, ``child`` returns ``None`` silently."""
    child = base_installation(tmp_path).child(runtime_plan(tmp_path, console=None), lambda command: command)

    assert child is None
    assert capsys.readouterr().err == ""


def test_child_warns_and_returns_none_when_interpreter_is_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """On an image without the console interpreter, ``child`` prints a degradation notice and returns ``None``."""
    installation = ConsoleInstallation(tmp_path / "absent-python", tmp_path / "launcher-webconsole")
    plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))

    child = installation.child(plan, lambda command: command)

    assert child is None
    assert "this base has no web console (base recipe 10 adds it" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("listen", "expected"),
    [
        ("0.0.0.0", "127.0.0.1"),
        ("::", "::1"),
        ("127.0.0.1", "127.0.0.1"),
        ("::1", "::1"),
        ("192.0.2.7", "192.0.2.7"),
    ],
)
def test_probe_address_is_the_loopback_of_a_wildcard_listener_and_the_address_of_any_other(
    listen: str, expected: str,
) -> None:
    """``probe_address`` maps each wildcard to the loopback of its family and leaves a named address as it is."""
    assert probe_address(listen) == expected


def test_child_is_ready_once_its_port_accepts_a_connection(tmp_path: Path) -> None:
    """For a console planned on every IPv4 interface, ``child.ready`` is true while a listener on loopback holds its port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", port, "/run/devcapsule-console-token"))
        child = base_installation(tmp_path).child(plan, lambda command: command)
        assert child is not None and child.ready is not None

        ready = child.ready()

    assert ready is True


def test_child_is_not_ready_while_nothing_listens_on_its_port(tmp_path: Path) -> None:
    """``child.ready`` is false when the planned port refuses the connection."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        # Bound and never listening: the port refuses, and no other process can take it meanwhile.
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        plan = runtime_plan(tmp_path, console=ConsolePlan("127.0.0.1", port, "/run/devcapsule-console-token"))
        child = base_installation(tmp_path).child(plan, lambda command: command)
        assert child is not None and child.ready is not None

        ready = child.ready()

    assert ready is False
