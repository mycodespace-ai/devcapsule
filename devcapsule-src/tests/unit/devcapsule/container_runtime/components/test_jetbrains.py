"""Unit tests of ``devcapsule/container_runtime/components/jetbrains.py``: the properties and the command of a JetBrains launch."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.container_runtime.components.jetbrains import plan
from devcapsule.container_runtime.contract import RuntimePlan, RuntimePlanError


def runtime_document(tmp_path: Path) -> dict[str, object]:
    """A runtime plan document for a JetBrains component whose four state slots lie under ``tmp_path``."""
    return {
        "version": 1,
        "project_path": "/workspace/project",
        "home": str(tmp_path / "home"),
        "identity": {"uid": 1000, "gid": 1001, "user": "developer"},
        "state_slots": [
            {"name": "jetbrains/config", "path": str(tmp_path / "config")},
            {"name": "jetbrains/system", "path": str(tmp_path / "system")},
            {"name": "jetbrains/plugins", "path": str(tmp_path / "plugins")},
            {"name": "jetbrains/log", "path": str(tmp_path / "log")},
        ],
        "component": {
            "id": "jetbrains",
            "adapter": "jetbrains",
            "configuration": {
                "installation_path": "/opt/jetbrains/pycharm",
                "launcher": "bin/pycharm.sh",
                "properties_path": str(tmp_path / "idea.properties"),
                "properties_environment_variable": "PYCHARM_PROPERTIES",
                "state_slot_mapping": {
                    "config": "config",
                    "system": "system",
                    "plugins": "plugins",
                    "log": "log",
                },
            },
        },
    }


def configuration_of(document: dict[str, object]) -> dict[str, object]:
    component = document["component"]
    assert isinstance(component, dict)
    configuration = component["configuration"]
    assert isinstance(configuration, dict)
    return configuration


def test_plan_points_the_ide_at_its_state_slots_and_starts_it_on_the_project(tmp_path: Path) -> None:
    """``plan`` writes one ``idea.<name>.path`` property per mapped slot, names the properties file and its variable, and runs the launcher on the project."""
    launch = plan(RuntimePlan.from_mapping(runtime_document(tmp_path)))

    assert launch.command == ("/opt/jetbrains/pycharm/bin/pycharm.sh", "/workspace/project")
    assert launch.properties_path == str(tmp_path / "idea.properties")
    assert launch.properties_environment_variable == "PYCHARM_PROPERTIES"
    assert launch.properties.splitlines() == [
        f"idea.config.path={tmp_path / 'config'}",
        f"idea.system.path={tmp_path / 'system'}",
        f"idea.plugins.path={tmp_path / 'plugins'}",
        f"idea.log.path={tmp_path / 'log'}",
    ]


def test_plan_appends_the_components_additional_properties(tmp_path: Path) -> None:
    """Each additional property of the configuration follows the four managed paths as ``name=value``, in name order."""
    document = runtime_document(tmp_path)
    configuration_of(document)["additional_properties"] = {
        "ide.no.platform.update": "true",
        "ide.browser.jcef.sandbox.enable": "false",
    }

    launch = plan(RuntimePlan.from_mapping(document))

    assert launch.properties.splitlines()[4:] == [
        "ide.browser.jcef.sandbox.enable=false",
        "ide.no.platform.update=true",
    ]


def test_plan_refuses_a_mapping_to_a_slot_the_plan_does_not_declare(tmp_path: Path) -> None:
    """A ``state_slot_mapping`` entry that names no declared state slot raises ``RuntimePlanError`` naming the mapping."""
    document = runtime_document(tmp_path)
    mapping = configuration_of(document)["state_slot_mapping"]
    assert isinstance(mapping, dict)
    mapping["log"] = "missing"

    with pytest.raises(RuntimePlanError, match="log mapping"):
        plan(RuntimePlan.from_mapping(document))
