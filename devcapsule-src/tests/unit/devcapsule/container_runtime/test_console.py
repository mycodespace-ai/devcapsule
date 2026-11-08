"""Unit tests of ``devcapsule/container_runtime/console.py``: supervised web-console child construction."""

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
    RUNTIME_CLI,
    console_child,
)
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan
from devcapsule.images.tooling import WEBCONSOLE_ROOT, WEBCONSOLE_VENV_PYTHON
from devcapsule.materialization import ENTRYPOINT_CONTRACT


def runtime_plan(tmp_path: Path, *, console: ConsolePlan | None) -> RuntimePlan:
    plan = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home=str(tmp_path / "home"),
        identity=Identity(1000, 1000, "developer"),
    )
    return plan if console is None else plan.with_console(console)


def test_runtime_and_base_recipe_agree_on_console_paths() -> None:
    """``console.py`` constants match the base image's web-console root, venv interpreter, and entrypoint CLI path."""
    assert CONSOLE_ROOT == WEBCONSOLE_ROOT
    assert CONSOLE_PYTHON == WEBCONSOLE_VENV_PYTHON
    assert RUNTIME_CLI == ENTRYPOINT_CONTRACT[0]


def test_console_child_runs_installed_console_against_runtime_cli(tmp_path: Path) -> None:
    """Without ``source_path``, ``console_child`` runs the base interpreter directly without ``PYTHONPATH``."""
    python = tmp_path / "python"
    python.write_text("", encoding="utf-8")
    plan = runtime_plan(tmp_path, console=ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))

    child = console_child(plan, lambda command: ("as-user", *command), console_python=python)

    assert child is not None
    assert child.name == CONSOLE_CHILD
    assert child.foreground is False
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
    assert child.ready is not None
    assert child.ready_timeout_seconds == CONSOLE_READY_TIMEOUT_SECONDS


def test_console_child_prepends_mounted_source_on_pythonpath(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """When ``console.source_path`` is set, ``console_child`` prepends ``env PYTHONPATH=<source_path>`` and logs it."""
    python = tmp_path / "python"
    python.write_text("", encoding="utf-8")
    plan = runtime_plan(
        tmp_path,
        console=ConsolePlan(
            "0.0.0.0",
            6081,
            "/run/devcapsule-console-token",
            source_path="/workspace/project/devcapsule-webconsole",
        ),
    )

    child = console_child(plan, lambda command: command, console_python=python)

    assert child is not None
    assert child.command[:3] == ("env", "PYTHONPATH=/workspace/project/devcapsule-webconsole", str(python))
    assert "running the mounted checkout's source at /workspace/project/devcapsule-webconsole" in capsys.readouterr().err


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
    child = console_child(plan, lambda command: command, console_python=python, connect=fake_connect)

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
    child = console_child(plan, lambda command: command, console_python=python, connect=refused)

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

    child = console_child(plan, lambda command: command, console_python=tmp_path / "absent")

    assert child is None
    assert "this base has no web console (base recipe 10 adds it" in capsys.readouterr().err
