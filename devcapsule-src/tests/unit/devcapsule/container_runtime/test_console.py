"""Unit tests of ``devcapsule/container_runtime/console.py``: package precedence and supervised child construction."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.console import (
    CONSOLE_CHILD,
    CONSOLE_PYTHON,
    CONSOLE_READY_TIMEOUT_SECONDS,
    CONSOLE_ROOT,
    LAUNCHER_CONSOLE_SOURCE,
    RUNTIME_CLI,
    console_child,
    console_package_path,
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


def launcher_bundle(path: Path) -> Path:
    pkg = path / "devcapsule_webconsole"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return path


def test_runtime_and_base_recipe_agree_on_console_paths() -> None:
    """``console.py`` constants match the base image's web-console root, venv interpreter, launcher bundle path, and CLI path."""
    assert CONSOLE_ROOT == WEBCONSOLE_ROOT
    assert CONSOLE_PYTHON == WEBCONSOLE_VENV_PYTHON
    assert LAUNCHER_CONSOLE_SOURCE == LAUNCHER_WEBCONSOLE_PATH
    assert RUNTIME_CLI == ENTRYPOINT_CONTRACT[0]


def test_console_package_path_prefers_the_plans_checkout_source(tmp_path: Path) -> None:
    """A non-empty ``console.source_path`` wins over an installed launcher package."""
    bundled = launcher_bundle(tmp_path / "launcher-webconsole")

    assert console_package_path(CHECKOUT_SOURCE, bundled) == CHECKOUT_SOURCE


def test_console_package_path_selects_the_launcher_package_when_installed(tmp_path: Path) -> None:
    """Without a checkout source, the launcher package directory is selected when it holds the package."""
    bundled = launcher_bundle(tmp_path / "launcher-webconsole")

    assert console_package_path("", bundled) == str(bundled)


def test_console_package_path_is_empty_when_only_the_base_copy_exists(tmp_path: Path) -> None:
    """Without a checkout source or an installed launcher package, the empty result leaves the base copy to the import."""
    absent = tmp_path / "launcher-webconsole"

    assert console_package_path("", absent) == ""


def test_console_child_runs_the_launcher_package_on_the_base_interpreter(tmp_path: Path) -> None:
    """With an empty ``console.source_path`` and an installed launcher package, ``PYTHONPATH`` selects that package."""
    python = tmp_path / "python"
    python.touch()
    bundled = launcher_bundle(tmp_path / "launcher-webconsole")
    plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))

    child = console_child(
        plan,
        lambda command: ("as-user", *command),
        console_python=python,
        launcher_source=bundled,
    )

    assert child is not None
    assert child.name == CONSOLE_CHILD
    assert child.foreground is False
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
    assert child.ready is not None
    assert child.ready_timeout_seconds == CONSOLE_READY_TIMEOUT_SECONDS


def test_console_child_runs_the_base_copy_without_a_launcher_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """With neither a checkout source nor a launcher package, the command carries no ``PYTHONPATH`` and nothing is announced."""
    python = tmp_path / "python"
    python.touch()
    plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))

    child = console_child(
        plan,
        lambda command: ("as-user", *command),
        console_python=python,
        launcher_source=tmp_path / "absent-launcher-webconsole",
    )

    assert child is not None
    assert child.command == (
        "as-user",
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
    assert capsys.readouterr().err == ""


def test_console_child_runs_the_mounted_checkout_source_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """With ``console.source_path`` set beside a launcher package, ``PYTHONPATH`` selects the checkout and stderr announces it."""
    python = tmp_path / "python"
    python.touch()
    bundled = launcher_bundle(tmp_path / "launcher-webconsole")
    plan = runtime_plan(
        tmp_path,
        console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token", source_path=CHECKOUT_SOURCE),
    )

    child = console_child(plan, lambda command: command, console_python=python, launcher_source=bundled)

    assert child is not None
    assert child.command[:3] == ("env", f"PYTHONPATH={CHECKOUT_SOURCE}", str(python))
    assert f"running the mounted checkout's source at {CHECKOUT_SOURCE}" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("listen", "expected_probe"),
    [
        ("0.0.0.0", "127.0.0.1"),
        ("::", "::1"),
        ("127.0.0.1", "127.0.0.1"),
        ("::1", "::1"),
    ],
)
def test_console_readiness_probes_loopback_of_listener_address_family(
    tmp_path: Path, listen: str, expected_probe: str,
) -> None:
    """``child.ready`` connects to the matching IPv4/IPv6 loopback address with a 0.2s timeout and closes the socket."""
    python = tmp_path / "python"
    python.touch()
    seen: list[tuple[tuple[str, int], float, str]] = []

    @contextmanager
    def fake_connect(target: tuple[str, int], timeout: float) -> Iterator[object]:
        seen.append((target, timeout, "enter"))
        try:
            yield object()
        finally:
            seen.append((target, timeout, "exit"))

    plan = runtime_plan(tmp_path, console=ConsolePlan(listen, 45678, "/run/devcapsule-console-token"))
    child = console_child(
        plan,
        lambda command: command,
        console_python=python,
        launcher_source=tmp_path / "absent",
        connect=fake_connect,
    )

    assert child is not None and child.ready is not None
    assert child.ready() is True
    assert seen == [((expected_probe, 45678), 0.2, "enter"), ((expected_probe, 45678), 0.2, "exit")]


def test_console_readiness_returns_false_when_probe_connection_fails(tmp_path: Path) -> None:
    """``child.ready`` returns ``False`` when the TCP connection attempt raises ``OSError``."""
    python = tmp_path / "python"
    python.touch()

    @contextmanager
    def refused(_target: tuple[str, int], _timeout: float) -> Iterator[object]:
        raise OSError("connection refused")
        yield  # pragma: no cover

    plan = runtime_plan(tmp_path, console=ConsolePlan("127.0.0.1", 45678, "/run/devcapsule-console-token"))
    child = console_child(
        plan,
        lambda command: command,
        console_python=python,
        launcher_source=tmp_path / "absent",
        connect=refused,
    )

    assert child is not None and child.ready is not None
    assert child.ready() is False


def test_console_child_is_none_when_plan_omits_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Without a ``console`` section in ``RuntimePlan``, ``console_child`` returns ``None`` silently."""
    child = console_child(runtime_plan(tmp_path, console=None), lambda command: command)

    assert child is None
    assert capsys.readouterr().err == ""


def test_console_child_warns_and_returns_none_when_interpreter_is_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """When the base image lacks ``CONSOLE_PYTHON``, ``console_child`` prints a degradation notice and returns ``None``."""
    plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))

    child = console_child(
        plan,
        lambda command: command,
        console_python=tmp_path / "absent",
        launcher_source=tmp_path / "absent-bundle",
    )

    assert child is None
    assert "this base has no web console (base recipe 10 adds it" in capsys.readouterr().err
