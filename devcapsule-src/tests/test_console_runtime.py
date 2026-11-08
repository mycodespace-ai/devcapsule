"""The web console as the runtime sees it: the plan section and the child."""
from __future__ import annotations

from pathlib import Path
import re
from unittest.mock import MagicMock, patch

import pytest

from devcapsule.container_runtime.console import (
    CONSOLE_CHILD, CONSOLE_PYTHON, CONSOLE_ROOT, RUNTIME_CLI, console_child,
)
from devcapsule.container_runtime.contract import ConsolePlan, RuntimePlan, RuntimePlanError
from devcapsule.container_runtime.display import NOVNC_CHILD, XVNC_CHILD
from devcapsule.container_runtime.entrypoint import run
from devcapsule.images.tooling import WEBCONSOLE_ROOT, WEBCONSOLE_VENV_PYTHON
from devcapsule.materialization import ENTRYPOINT_CONTRACT
from tests.test_contained_display import contained_document
from tests.test_runtime_entrypoint import SupervisorCapture, captured_supervisor, runtime_document  # noqa: F401

pytestmark = pytest.mark.legacy

CONSOLE = {"listen_address": "0.0.0.0", "port": 6081, "token_path": "/run/devcapsule-console-token"}


def test_the_runtime_and_the_base_recipe_agree_on_the_console_location() -> None:
    assert CONSOLE_ROOT == WEBCONSOLE_ROOT
    assert CONSOLE_PYTHON == WEBCONSOLE_VENV_PYTHON
    assert RUNTIME_CLI == ENTRYPOINT_CONTRACT[0]


def test_contract_round_trips_the_console_section(tmp_path: Path) -> None:
    document = runtime_document(tmp_path)
    document["console"] = dict(CONSOLE)
    plan = RuntimePlan.from_mapping(document)
    assert plan.console == ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token")
    assert plan.to_mapping()["console"] == CONSOLE
    with_source = RuntimePlan.from_mapping({**document, "console": {**CONSOLE, "source_path": "/workspace/project/devcapsule-webconsole"}})
    assert with_source.console is not None and with_source.console.source_path == "/workspace/project/devcapsule-webconsole"
    assert with_source.to_mapping()["console"] == {**CONSOLE, "source_path": "/workspace/project/devcapsule-webconsole"}
    assert RuntimePlan.from_mapping(plan.to_mapping()) == plan
    assert RuntimePlan.from_mapping(runtime_document(tmp_path)).console is None
    assert "console" not in RuntimePlan.from_mapping(runtime_document(tmp_path)).to_mapping()
    assert RuntimePlan.from_mapping({**document, "console": None}).console is None
    assert plan.with_console(ConsolePlan("127.0.0.1", 40000, "/run/t")).console == ConsolePlan("127.0.0.1", 40000, "/run/t")


@pytest.mark.parametrize("console, message", [
    ("text", "console must be an object"),
    ({**CONSOLE, "extra": 1}, "console must not carry extra"),
    ({**CONSOLE, "listen_address": "not a host/"}, "console.listen_address must be a host address"),
    ({**CONSOLE, "port": 0}, "console.port must be a TCP port number"),
    ({**CONSOLE, "port": True}, "console.port must be a TCP port number"),
    ({**CONSOLE, "port": 65536}, "console.port must be a TCP port number"),
    ({**CONSOLE, "port": "6081"}, "console.port must be a TCP port number"),
    ({**CONSOLE, "listen_address": ""}, "console.listen_address must be a non-empty string"),
    ({**CONSOLE, "token_path": "/run/../secret"}, "console.token_path must be an absolute normalized container path"),
    ({**CONSOLE, "token_path": "relative"}, "console.token_path must be an absolute normalized container path"),
    ({**CONSOLE, "source_path": "../escape"}, "console.source_path must be an absolute normalized container path"),
    ({**CONSOLE, "source_path": 5}, "console.source_path must be a non-empty string"),
])
def test_contract_rejects_a_malformed_console(tmp_path: Path, console: object, message: str) -> None:
    with pytest.raises(RuntimePlanError, match=re.escape(message)):
        RuntimePlan.from_mapping({**runtime_document(tmp_path), "console": console})


@pytest.mark.parametrize("field", ["listen_address", "port", "token_path"])
def test_console_contract_requires_each_listener_field(tmp_path: Path, field: str) -> None:
    console = {key: value for key, value in CONSOLE.items() if key != field}
    with pytest.raises(RuntimePlanError, match=rf"console\.{field}"):
        RuntimePlan.from_mapping({**runtime_document(tmp_path), "console": console})


@pytest.mark.parametrize("port", [1, 65535])
def test_console_contract_accepts_boundary_ports(tmp_path: Path, port: int) -> None:
    plan = plan_with_console(tmp_path, port=port)
    assert plan.console is not None and plan.console.port == port


def plan_with_console(tmp_path: Path, **console: object) -> RuntimePlan:
    return RuntimePlan.from_mapping({**runtime_document(tmp_path), "console": {**CONSOLE, **console}})


def test_console_child_runs_the_installed_console_against_the_runtime_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("devcapsule.container_runtime.console.CONSOLE_PYTHON", str(tmp_path / "python"))
    (tmp_path / "python").write_text("", encoding="utf-8")
    child = console_child(plan_with_console(tmp_path), lambda command: ("as-user", *command))
    assert child is not None
    assert child.name == CONSOLE_CHILD and child.foreground is False
    assert child.command == (
        "as-user", str(tmp_path / "python"), "-m", "devcapsule_webconsole",
        "--project", "/workspace/project", "--cli", RUNTIME_CLI,
        "--token-file", "/run/devcapsule-console-token", "--listen", "0.0.0.0", "--port", "6081",
    )
    assert child.ready is not None
    assert child.ready_timeout_seconds == 60.0


@pytest.mark.parametrize("listen, probe", [
    ("0.0.0.0", "127.0.0.1"), ("::", "::1"),
    ("127.0.0.1", "127.0.0.1"), ("::1", "::1"),
])
def test_console_readiness_probes_the_listener_address_family(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, listen: str, probe: str,
) -> None:
    python = tmp_path / "python"
    python.touch()
    monkeypatch.setattr("devcapsule.container_runtime.console.CONSOLE_PYTHON", str(python))
    child = console_child(plan_with_console(tmp_path, listen_address=listen, port=45678), lambda command: command)
    assert child is not None and child.ready is not None
    connection = MagicMock()
    with patch("devcapsule.container_runtime.console.socket.create_connection", return_value=connection) as connect:
        assert child.ready() is True
        connect.assert_called_once_with((probe, 45678), timeout=0.2)
        connection.__exit__.assert_called_once()
    with patch("devcapsule.container_runtime.console.socket.create_connection", side_effect=OSError):
        assert child.ready() is False


def test_console_child_is_absent_without_a_section_or_on_an_older_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert console_child(RuntimePlan.from_mapping(runtime_document(tmp_path)), lambda command: command) is None
    assert capsys.readouterr().err == ""
    monkeypatch.setattr("devcapsule.container_runtime.console.CONSOLE_PYTHON", str(tmp_path / "absent"))
    assert console_child(plan_with_console(tmp_path), lambda command: command) is None
    assert "this base has no web console (base recipe 10 adds it" in capsys.readouterr().err


def test_entrypoint_starts_the_console_beside_the_display_and_alone_headless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_supervisor: type[SupervisorCapture]  # noqa: F811
) -> None:
    monkeypatch.setattr("devcapsule.container_runtime.display.os.geteuid", lambda: 1000)
    monkeypatch.setattr("devcapsule.container_runtime.display.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("devcapsule.container_runtime.display.X_SOCKET_DIRECTORY", str(tmp_path / ".X11-unix"))
    monkeypatch.setattr("devcapsule.container_runtime.console.CONSOLE_PYTHON", str(tmp_path / "python"))
    (tmp_path / "python").write_text("", encoding="utf-8")
    monkeypatch.delenv("DISPLAY", raising=False)
    with_display = RuntimePlan.from_mapping({**contained_document(tmp_path), "console": dict(CONSOLE)})
    assert run(with_display) == 42
    headless = RuntimePlan.from_mapping({**runtime_document(tmp_path), "console": dict(CONSOLE)})
    assert run(headless, job=("pytest", "-q")) == 42
    passthrough = RuntimePlan.from_mapping({**runtime_document(tmp_path), "console": dict(CONSOLE)})
    assert run(passthrough) == 42
    assert run(with_display, job=("true",)) == 42  # job mode suppresses even a declared display

    first, second, third, fourth = captured_supervisor.instances
    names = [child.name for child in first.children]
    assert names[0] == XVNC_CHILD and names[-3:] == [NOVNC_CHILD, CONSOLE_CHILD, "jetbrains"]
    assert [child.name for child in second.children] == [CONSOLE_CHILD, "job"]
    assert [child.name for child in third.children] == [CONSOLE_CHILD, "jetbrains"]
    assert [child.name for child in fourth.children] == [CONSOLE_CHILD, "job"]
    assert all(not child.foreground for children in (first, second, third, fourth) for child in children.children[:-1])
    assert all(children.children[-1].foreground for children in (first, second, third, fourth))
