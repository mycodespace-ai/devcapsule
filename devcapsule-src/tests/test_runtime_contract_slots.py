"""State-slot shape rules ruled 2026-09-02: the home overlay stays, overlay
slots are direct children of home, no slot overlaps another component's, and
nothing may leave the container runtime creating root-owned entries under the
developer's home. See
engineering-docs/design-notes/devcapsule/state-slots-home-overlay-and-ownership.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from devcapsule.components.catalog import COMPONENTS
from devcapsule.launch.pycharm._launcher import prepare_home_mount_points
from devcapsule.container_runtime.contract import (
    ComponentRuntimeTemplate,
    Identity,
    RuntimePlan,
    RuntimePlanError,
)

pytestmark = pytest.mark.legacy


def template_mapping(component_id: str, container_path: str, *, overlay: bool = True) -> dict:
    return {
        "version": 1,
        "component": {
            "id": component_id,
            "adapter": "ancillary",
            "configuration": {},
            "persistence": {
                "home": "required",
                "xdg": "home-relative",
                "state_slots": [
                    {
                        "name": "home",
                        "container_path": container_path,
                        "kind": "durable",
                        "sensitivity": "credentials",
                        "default_scope": "checkout",
                        "storage": "directory",
                        "concurrent": False,
                        "owner": "runtime-user",
                        "permissions": "0700",
                        "reconstructable": False,
                        "deletion_effect": "Removes test state.",
                        "home_overlay": overlay,
                    }
                ],
            },
        },
    }


def test_overlay_slot_deeper_than_one_level_is_rejected() -> None:
    with pytest.raises(RuntimePlanError, match="direct child of home"):
        ComponentRuntimeTemplate.from_mapping(
            template_mapping("deep-tool", "/home/devcapsule/.gemini/antigravity-cli")
        )


def test_slot_claiming_home_itself_is_rejected() -> None:
    with pytest.raises(RuntimePlanError, match="may not claim the home directory"):
        ComponentRuntimeTemplate.from_mapping(
            template_mapping("greedy-tool", "/home/devcapsule")
        )


def test_slot_inside_another_components_slot_is_rejected() -> None:
    outer = ComponentRuntimeTemplate.from_mapping(
        template_mapping("outer", "/home/devcapsule/.shared")
    )
    inner = ComponentRuntimeTemplate.from_mapping(
        # Outside home, so the direct-child rule does not pre-empt the
        # formation-wide overlap rule under test.
        template_mapping("surface", "/opt/surface-state", overlay=False)
    )
    nested = ComponentRuntimeTemplate.from_mapping(
        template_mapping("intruder", "/opt/surface-state/nested", overlay=False)
    )
    with pytest.raises(RuntimePlanError, match="overlapping container paths"):
        RuntimePlan.for_component(
            inner,
            project_path="/workspace/p",
            home="/home/devcapsule",
            identity=Identity(1000, 1000, "devcapsule"),
            ancillary_templates=(outer, nested),
        )


def test_every_catalog_component_satisfies_the_slot_rules() -> None:
    for definition in COMPONENTS.values():
        definition.runtime_template()  # from_mapping validates


@dataclass
class _MountConfig:
    """The slice of PycharmRunConfig that prepare_home_mount_points reads."""

    persistent_home: Path
    interactive_state_mounts: tuple[tuple[str, str, str], ...] = ()
    additional_state_mounts: tuple[tuple[str, str, str], ...] = ()
    tool_cache: Path | None = None


def test_home_mount_points_are_pre_created_user_owned(tmp_path: Path) -> None:
    home_source = tmp_path / "home"
    home_source.mkdir()
    config = _MountConfig(
        persistent_home=home_source,
        interactive_state_mounts=(
            ("codium/cache", str(tmp_path / "cache-src"), "/home/devcapsule/.cache"),
            ("codium/user-data", str(tmp_path / "ud-src"), "/ide-user-data"),
        ),
        additional_state_mounts=(
            ("antigravity-cli/home", str(tmp_path / "agy-src"), "/home/devcapsule/.gemini"),
        ),
    )
    prepare_home_mount_points(config)  # type: ignore[arg-type]
    for name in (".cache", ".gemini"):
        mount_point = home_source / name
        assert mount_point.is_dir()
        assert mount_point.stat().st_uid == os.getuid()
    assert not (home_source / "ide-user-data").exists()


def test_legacy_tool_cache_mount_point_is_pre_created(tmp_path: Path) -> None:
    home_source = tmp_path / "home"
    home_source.mkdir()
    config = _MountConfig(persistent_home=home_source, tool_cache=tmp_path / "cache-src")
    prepare_home_mount_points(config)  # type: ignore[arg-type]
    assert (home_source / ".cache").is_dir()
