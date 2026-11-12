"""Unit tests of ``devcapsule/container_runtime/contract.py``: the ``console`` section of ``RuntimePlan``."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import ConsolePlan, Identity, RuntimePlan, RuntimePlanError

CONSOLE = {"listen_address": "0.0.0.0", "port": 6081, "token_path": "/run/devcapsule-console-token"}


def base_runtime_document(tmp_path: Path) -> dict[str, object]:
    """Construct a valid ``RuntimePlan`` mapping rooted under ``tmp_path``."""
    plan = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home=str(tmp_path / "home"),
        identity=Identity(1000, 1000, "developer"),
    )
    return plan.to_mapping()


def test_runtime_plan_round_trips_console_section_with_and_without_source_path(tmp_path: Path) -> None:
    """``RuntimePlan`` parses and re-serializes ``console`` with optional ``source_path``."""
    document = {**base_runtime_document(tmp_path), "console": {**CONSOLE, "source_path": "/workspace/project/devcapsule-webconsole"}}

    plan = RuntimePlan.from_mapping(document)

    assert plan.console == ConsolePlan(
        "0.0.0.0", 6081, "/run/devcapsule-console-token", source_path="/workspace/project/devcapsule-webconsole"
    )
    assert plan.to_mapping()["console"] == document["console"]
    assert RuntimePlan.from_mapping(plan.to_mapping()) == plan


def test_runtime_plan_omits_console_when_absent_or_none(tmp_path: Path) -> None:
    """``RuntimePlan`` treats an omitted or ``None`` ``console`` entry as ``None`` and omits it from ``to_mapping``."""
    document = base_runtime_document(tmp_path)

    absent = RuntimePlan.from_mapping(document)
    explicit_none = RuntimePlan.from_mapping({**document, "console": None})

    assert absent.console is None
    assert explicit_none.console is None
    assert "console" not in absent.to_mapping()


def test_with_console_replaces_the_plans_console_section(tmp_path: Path) -> None:
    """``RuntimePlan.with_console`` returns a plan carrying the supplied ``ConsolePlan``."""
    plan = RuntimePlan.from_mapping(base_runtime_document(tmp_path))
    replacement = ConsolePlan("127.0.0.1", 40000, "/run/t")

    updated = plan.with_console(replacement)

    assert updated.console == replacement
    assert updated.to_mapping()["console"] == {"listen_address": "127.0.0.1", "port": 40000, "token_path": "/run/t"}


@pytest.mark.parametrize(
    ("console", "message"),
    [
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
    ],
)
def test_runtime_plan_rejects_malformed_console_section(
    tmp_path: Path, console: object, message: str,
) -> None:
    """``RuntimePlan.from_mapping`` raises ``RuntimePlanError`` when ``console`` violates field types or path invariants."""
    document = {**base_runtime_document(tmp_path), "console": console}
    with pytest.raises(RuntimePlanError, match=re.escape(message)):
        RuntimePlan.from_mapping(document)


@pytest.mark.parametrize("field", ["listen_address", "port", "token_path"])
def test_runtime_plan_requires_each_console_listener_field(tmp_path: Path, field: str) -> None:
    """``RuntimePlan.from_mapping`` refuses a ``console`` mapping missing any required listener field."""
    incomplete = {key: value for key, value in CONSOLE.items() if key != field}
    with pytest.raises(RuntimePlanError, match=rf"console\.{field}"):
        RuntimePlan.from_mapping({**base_runtime_document(tmp_path), "console": incomplete})


@pytest.mark.parametrize("port", [1, 65535])
def test_runtime_plan_accepts_boundary_tcp_ports(tmp_path: Path, port: int) -> None:
    """``RuntimePlan.from_mapping`` accepts valid TCP port boundaries 1 and 65535."""
    plan = RuntimePlan.from_mapping({**base_runtime_document(tmp_path), "console": {**CONSOLE, "port": port}})
    assert plan.console is not None and plan.console.port == port
