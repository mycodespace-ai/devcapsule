"""Unit tests of ``devcapsule/container_runtime/contract.py``: component templates, and the runtime plan with its ``console`` and ``logs`` sections."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Callable

import pytest

from devcapsule.container_runtime.contract import (
    ComponentRuntimeTemplate,
    ConsolePlan,
    Identity,
    LogsPlan,
    RuntimePlan,
    RuntimePlanError,
)

CONSOLE = {"listen_address": "0.0.0.0", "port": 6081, "token_path": "/run/devcapsule-console-token"}


def state_slot(name: str, container_path: str, kind: str, **more: object) -> dict[str, object]:
    """One state slot of a component template, with every field the contract requires."""
    return {
        "name": name,
        "container_path": container_path,
        "kind": kind,
        "sensitivity": "ordinary",
        "default_scope": "checkout",
        "storage": "directory",
        "concurrent": False,
        "owner": "runtime-user",
        "permissions": "0700",
        "reconstructable": kind == "cache",
        "deletion_effect": f"Removes the tool's {name}.",
        **more,
    }


def tool_template(*slots: dict[str, object]) -> dict[str, object]:
    """A component template document for a component named ``tool`` that persists its home and ``slots``."""
    return {
        "version": 1,
        "component": {
            "id": "tool",
            "adapter": "fixture",
            "configuration": {},
            "environment": {"TOOL_OPTIONS": "-quiet"},
            "persistence": {"home": "required", "xdg": "home-relative", "state_slots": list(slots)},
        },
    }


def base_runtime_document(tmp_path: Path) -> dict[str, object]:
    """Construct a valid ``RuntimePlan`` mapping rooted under ``tmp_path``."""
    return {
        "version": 1,
        "project_path": "/workspace/project",
        "home": str(tmp_path / "home"),
        "identity": {"uid": 1000, "gid": 1000, "user": "developer"},
        "component": {"id": "fixture", "adapter": "fixture", "configuration": {}},
        "state_slots": [{"name": "fixture/config", "path": str(tmp_path / "config")}],
    }


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


def test_runtime_plan_parses_a_versioned_document(tmp_path: Path) -> None:
    """``RuntimePlan.from_json`` reads the identity, the component and the state slots of a version 1 document."""
    document = base_runtime_document(tmp_path)

    plan = RuntimePlan.from_json(json.dumps(document))

    assert plan.identity == Identity(1000, 1000, "developer")
    assert plan.home == str(tmp_path / "home")
    assert plan.component.adapter == "fixture"
    assert plan.state_slots[0].name == "fixture/config"
    assert plan.state_slots[0].path == str(tmp_path / "config")


def test_component_template_parses_its_persistence_declaration() -> None:
    """``ComponentRuntimeTemplate.from_json`` reads the home, the XDG layout and each state slot, and prefixes a slot's name with the component's."""
    document = tool_template(state_slot("config", "/tool-config", "durable"))

    template = ComponentRuntimeTemplate.from_json(json.dumps(document))

    assert template.persistence.home == "required"
    assert template.persistence.xdg == "home-relative"
    assert [(slot.name, slot.kind) for slot in template.persistence.state_slots] == [("config", "durable")]
    assert template.logical_slot_name("config") == "tool/config"


def test_for_component_places_each_declared_slot_at_its_container_path() -> None:
    """``RuntimePlan.for_component`` names each slot ``<component>/<slot>`` at the path the template declares, a home overlay included."""
    template = ComponentRuntimeTemplate.from_mapping(tool_template(
        state_slot("config", "/tool-config", "durable"),
        state_slot("cache", "/home/devcapsule/.cache", "cache", home_overlay=True),
    ))

    plan = RuntimePlan.for_component(
        template, project_path="/workspace/project", home="/home/devcapsule", identity=Identity(1000, 1000),
    )

    assert plan.slots_by_name() == {"tool/config": "/tool-config", "tool/cache": "/home/devcapsule/.cache"}


def test_for_component_carries_the_components_environment() -> None:
    """``RuntimePlan.for_component`` gives the plan's component the variables its template declares."""
    template = ComponentRuntimeTemplate.from_mapping(tool_template())

    plan = RuntimePlan.for_component(
        template, project_path="/workspace/project", home="/home/devcapsule", identity=Identity(1000, 1000),
    )

    assert plan.component.environment == {"TOOL_OPTIONS": "-quiet"}
    assert plan.component_environment() == {"TOOL_OPTIONS": "-quiet"}


def test_for_component_gives_a_home_only_component_no_state_slot() -> None:
    """A template that declares a home and no state slot yields a plan with no state slot."""
    template = ComponentRuntimeTemplate.from_mapping(tool_template())

    plan = RuntimePlan.for_component(
        template, project_path="/workspace/project", home="/home/devcapsule", identity=Identity(1000, 1000),
    )

    assert plan.state_slots == ()


def test_component_template_requires_a_slot_under_the_home_to_declare_home_overlay() -> None:
    """A state slot whose path lies under the home and omits ``home_overlay`` is refused."""
    document = tool_template(state_slot("cache", "/home/devcapsule/.cache", "cache"))

    with pytest.raises(RuntimePlanError, match="must declare home_overlay"):
        ComponentRuntimeTemplate.from_mapping(document)


def unsupported_version(document: dict[str, object]) -> None:
    document["version"] = 2


def boolean_uid(document: dict[str, object]) -> None:
    document["identity"] = {"uid": True, "gid": 1}


def duplicate_slot(document: dict[str, object]) -> None:
    document["state_slots"] = [{"name": "same", "path": "/a"}, {"name": "same", "path": "/b"}]


def unsafe_component_id(document: dict[str, object]) -> None:
    component = document["component"]
    assert isinstance(component, dict)
    component["id"] = "Tool/unsafe"


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        (unsupported_version, "unsupported runtime plan version"),
        (boolean_uid, "identity.uid"),
        (duplicate_slot, "duplicate state slot"),
        (unsafe_component_id, "component.id"),
    ],
)
def test_runtime_plan_rejects_a_document_it_cannot_trust(
    tmp_path: Path, damage: Callable[[dict[str, object]], None], message: str,
) -> None:
    """An unknown version, a boolean uid, a repeated slot name or an unsafe component id each raise ``RuntimePlanError`` naming the fault."""
    document = base_runtime_document(tmp_path)
    damage(document)

    with pytest.raises(RuntimePlanError, match=message):
        RuntimePlan.from_mapping(document)


def test_runtime_plan_round_trips_the_logs_section(tmp_path: Path) -> None:
    """``RuntimePlan`` parses a ``logs`` section into a ``LogsPlan`` and serializes it back unchanged."""
    document = {**base_runtime_document(tmp_path), "logs": {"directory": "/var/log/devcapsule"}}

    plan = RuntimePlan.from_mapping(document)

    assert plan.logs == LogsPlan("/var/log/devcapsule")
    assert plan.to_mapping()["logs"] == {"directory": "/var/log/devcapsule"}
    assert RuntimePlan.from_mapping(plan.to_mapping()) == plan


def test_runtime_plan_omits_logs_when_absent_or_none(tmp_path: Path) -> None:
    """``RuntimePlan`` treats an omitted or ``None`` ``logs`` entry as ``None`` and omits it from ``to_mapping``."""
    document = base_runtime_document(tmp_path)

    absent = RuntimePlan.from_mapping(document)
    explicit_none = RuntimePlan.from_mapping({**document, "logs": None})

    assert absent.logs is None
    assert explicit_none.logs is None
    assert "logs" not in absent.to_mapping()


def test_with_logs_replaces_the_plans_logs_section(tmp_path: Path) -> None:
    """``RuntimePlan.with_logs`` returns a plan carrying the supplied ``LogsPlan``."""
    plan = RuntimePlan.from_mapping({**base_runtime_document(tmp_path), "logs": {"directory": "/var/log/devcapsule"}})

    updated = plan.with_logs(LogsPlan("/elsewhere"))

    assert updated.logs == LogsPlan("/elsewhere")


@pytest.mark.parametrize(
    ("logs_section", "message"),
    [
        ("text", "logs must be an object"),
        ({"directory": "/var/log/devcapsule", "extra": 1}, "logs must not carry extra"),
        ({"directory": "relative"}, "logs.directory must be an absolute normalized container path"),
        ({"directory": "/var/../log"}, "logs.directory must be an absolute normalized container path"),
        ({}, "logs.directory must be"),
    ],
)
def test_runtime_plan_rejects_a_malformed_logs_section(tmp_path: Path, logs_section: object, message: str) -> None:
    """A ``logs`` section that is no object, carries an unknown key, or names no absolute normalized directory is refused."""
    with pytest.raises(RuntimePlanError, match=message):
        RuntimePlan.from_mapping({**base_runtime_document(tmp_path), "logs": logs_section})


def test_runtime_plan_round_trips_the_rotation_of_its_logs(tmp_path: Path) -> None:
    """A ``logs`` section with a segment size and a rotation count parses into a rotating ``LogsPlan`` and serializes back unchanged."""
    logs_section = {"directory": "/var/log/devcapsule", "segment_bytes": 8388608, "rotations": 4}

    plan = RuntimePlan.from_mapping({**base_runtime_document(tmp_path), "logs": logs_section})

    assert plan.logs == LogsPlan("/var/log/devcapsule", 8388608, 4)
    assert plan.logs is not None and plan.logs.rotates
    assert plan.to_mapping()["logs"] == logs_section


def test_logs_plan_without_a_rotation_does_not_rotate() -> None:
    """A ``LogsPlan`` that names only a directory has ``rotates`` false."""
    assert not LogsPlan("/var/log/devcapsule").rotates


def test_logs_plan_reads_a_zero_rotation_as_none() -> None:
    """A segment size and a rotation count that are both zero parse to the plan that names only the directory."""
    parsed = LogsPlan.from_mapping({"directory": "/var/log/devcapsule", "segment_bytes": 0, "rotations": 0}, "logs")

    assert parsed == LogsPlan("/var/log/devcapsule")


@pytest.mark.parametrize(
    ("rotation", "message"),
    [
        ({"segment_bytes": 0}, "go together"),
        ({"rotations": 0}, "go together"),
        ({"segment_bytes": 1}, "go together"),
        ({"rotations": 1}, "go together"),
        ({"segment_bytes": -1, "rotations": 1}, "segment_bytes must be a non-negative integer"),
        ({"segment_bytes": 1, "rotations": True}, "rotations must be a non-negative integer"),
        ({"segment_bytes": "8M", "rotations": 1}, "segment_bytes must be a non-negative integer"),
    ],
)
def test_runtime_plan_rejects_a_rotation_that_is_half_given_or_not_a_count(
    tmp_path: Path, rotation: dict[str, object], message: str,
) -> None:
    """A segment size without a rotation count, or the reverse, and a value that is no non-negative integer, are each refused."""
    logs_section = {"directory": "/var/log/devcapsule", **rotation}

    with pytest.raises(RuntimePlanError, match=message):
        RuntimePlan.from_mapping({**base_runtime_document(tmp_path), "logs": logs_section})
