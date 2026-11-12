from __future__ import annotations

import json
from pathlib import Path

import pytest

from devcapsule.components.catalog import (
    COMPONENTS,
    INTERACTIVE_SURFACES,
    ComponentCatalogError,
    selected_component_definitions,
)
from devcapsule.components.codium import DEFINITION, logical_state_slots, runtime_template
from devcapsule.container_runtime.components.vscode import plan as plan_vscode
from devcapsule.container_runtime.contract import (
    ComponentRuntimeTemplate,
    Identity,
    RuntimePlan,
    RuntimePlanError,
)

pytestmark = pytest.mark.legacy


def component_runtime() -> RuntimePlan:
    return RuntimePlan.for_component(
        runtime_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000),
    )


def test_component_is_registered_as_an_interactive_surface() -> None:
    assert COMPONENTS["codium"] is DEFINITION
    assert INTERACTIVE_SURFACES["codium"] is DEFINITION
    assert DEFINITION.capability == "frontend-ide"


def test_component_declares_no_state_environment_or_secret_inputs() -> None:
    assert DEFINITION.state_environment() == ()
    assert DEFINITION.secret_inputs() == ()
    assert DEFINITION.locked_artifacts({}, "linux-amd64") == ()


def test_runtime_template_round_trips_through_the_contract() -> None:
    template = ComponentRuntimeTemplate.from_json(json.dumps(runtime_template().to_mapping()))

    assert template.component.id == "codium"
    assert template.component.adapter == "vscode"
    # Renderers run unsandboxed (product-owner ruling 2026-09-02); the flag
    # is template data so the frozen v0.2.8 runtime appends it unchanged.
    assert template.component.configuration["additional_arguments"] == ["--no-sandbox"]
    assert "sandbox" not in template.component.configuration
    assert template.component.configuration["shared-memory-size"] == "640m"
    assert template.persistence.home == "required"
    assert template.persistence.xdg == "home-relative"
    assert logical_state_slots() == ("codium/user-data", "codium/extensions", "codium/cache")


def test_shared_memory_declaration_reaches_the_launcher() -> None:
    """The declared /dev/shm size flows to --shm-size; Docker's 64MB default
    intermittently SIGTRAPs Chromium renderers under software rendering
    (owner-confirmed 2026-09-02; see the relaunch-renderer-crash bug record).
    """

    from dataclasses import dataclass

    from devcapsule.launch.pycharm._launcher import (
        PycharmRunError,
        declared_shared_memory_size,
    )

    @dataclass
    class _Config:
        runtime_plan: RuntimePlan | None

    assert declared_shared_memory_size(_Config(component_runtime())) == "640m"  # type: ignore[arg-type]
    assert declared_shared_memory_size(_Config(None)) is None  # type: ignore[arg-type]

    mapping = runtime_template().to_mapping()
    mapping["component"]["configuration"]["shared-memory-size"] = "lots"  # type: ignore[index]
    malformed = RuntimePlan.for_component(
        ComponentRuntimeTemplate.from_mapping(mapping),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000),
    )
    with pytest.raises(PycharmRunError, match="shared-memory-size"):
        declared_shared_memory_size(_Config(malformed))  # type: ignore[arg-type]


def test_durable_editor_state_persists_outside_the_home_overlay() -> None:
    slots = {slot.name: slot for slot in runtime_template().persistence.state_slots}

    assert slots["user-data"].kind == "durable"
    assert slots["user-data"].container_path == "/ide-user-data"
    assert slots["extensions"].kind == "durable"
    assert slots["extensions"].container_path == "/ide-extensions"
    assert slots["cache"].home_overlay is True
    assert slots["cache"].reconstructable is True


def test_lock_selecting_codium_resolves_through_the_catalog() -> None:
    lock = {
        "components": {
            "interactive-surface": "codium",
            "codium": {"version": "1.104.3"},
            "claude-code": {"version": "2.1.227"},
        }
    }

    interactive, ancillary = selected_component_definitions(lock)

    assert interactive.id == "codium"
    assert [component.id for component in ancillary] == ["claude-code"]


def test_lock_naming_a_second_interactive_surface_is_rejected() -> None:
    lock = {
        "components": {
            "interactive-surface": "codium",
            "codium": {"version": "1.104.3"},
            "pycharm": {"version": "2026.2.0.1"},
        }
    }

    with pytest.raises(ComponentCatalogError, match="interactive surface"):
        selected_component_definitions(lock)


def test_lock_selecting_an_unknown_surface_is_rejected() -> None:
    lock = {"components": {"interactive-surface": "emacs", "emacs": {}}}

    with pytest.raises(ComponentCatalogError, match="interactive component 'emacs'"):
        selected_component_definitions(lock)


def test_vscode_adapter_reproduces_the_proven_foreground_command() -> None:
    launch = plan_vscode(component_runtime())

    assert launch.command == (
        "/opt/codium/codium",
        "--user-data-dir=/ide-user-data",
        "--extensions-dir=/ide-extensions",
        "--no-sandbox",
        "/workspace/project",
    )


def test_vscode_adapter_appends_validated_additional_arguments() -> None:
    document = component_runtime().to_mapping()
    document["component"]["configuration"]["additional_arguments"] = [  # type: ignore[index]
        "--no-sandbox",
        "--verbose",
    ]

    launch = plan_vscode(RuntimePlan.from_mapping(document))

    assert launch.command[-3:] == ("--no-sandbox", "--verbose", "/workspace/project")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda config: config.pop("state_slot_mapping"),
            "state_slot_mapping must be an object",
        ),
        (
            lambda config: config["state_slot_mapping"].update({"user-data": "missing"}),
            "user-data mapping must name a declared state slot",
        ),
        (
            lambda config: config.update(launcher="/usr/bin/codium"),
            "launcher must be relative",
        ),
        (
            lambda config: config.update(additional_arguments=["--flag\nrm"]),
            "one-line strings",
        ),
        (
            lambda config: config.update(additional_arguments="--flag"),
            "additional_arguments must be an array",
        ),
        (
            lambda config: config.update(sandbox="setuid-helper"),
            "renderer sandboxing is retired",
        ),
        (
            lambda config: config.update(additional_arguments=["--verbose"]),
            "must include --no-sandbox",
        ),
    ],
)
def test_vscode_adapter_rejects_invalid_configuration(change: object, message: str) -> None:
    document = component_runtime().to_mapping()
    change(document["component"]["configuration"])  # type: ignore[index,operator]

    with pytest.raises(RuntimePlanError, match=message):
        plan_vscode(RuntimePlan.from_mapping(document))
