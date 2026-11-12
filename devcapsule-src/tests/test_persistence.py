from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.components.pycharm import runtime_template
from devcapsule.container_runtime.contract import Identity, RuntimePlanError
from devcapsule.persistence import StateRoots, plan_component_persistence, prepare_persistence_directories

pytestmark = pytest.mark.legacy


def test_component_state_uses_lifecycle_roots_and_declared_destinations(tmp_path: Path) -> None:
    roots = StateRoots(tmp_path / "data", tmp_path / "state", tmp_path / "cache")
    plan = plan_component_persistence(
        runtime_template(),
        roots=roots,
        checkout_namespace=Path("projects/example/checkout"),
    )
    mounts = {mount.logical_name: mount for mount in plan.mounts}

    assert mounts["home"].source == str(tmp_path / "data/projects/example/checkout/home")
    assert mounts["pycharm/config"].source == str(
        tmp_path / "data/projects/example/checkout/components/pycharm/config"
    )
    assert mounts["pycharm/log"].source == str(
        tmp_path / "state/projects/example/checkout/components/pycharm/log"
    )
    assert mounts["pycharm/system"].source == str(
        tmp_path / "cache/projects/example/checkout/components/pycharm/system"
    )
    assert mounts["pycharm/cache"].destination == "/home/devcapsule/.cache"
    assert plan.mounts.index(mounts["home"]) < plan.mounts.index(mounts["pycharm/cache"])

    runtime = plan.runtime_plan(project_path="/workspace/project", identity=Identity(123, 456))
    assert runtime.component.id == "pycharm"
    assert runtime.slots_by_name()["pycharm/plugins"] == "/ide-plugins"


def test_component_state_accepts_only_explicit_slot_bindings(tmp_path: Path) -> None:
    adopted_config = tmp_path / "existing-config"
    plan = plan_component_persistence(
        runtime_template(),
        roots=StateRoots(tmp_path / "data", tmp_path / "state", tmp_path / "cache"),
        checkout_namespace=Path("checkout"),
        adopted={"pycharm/config": adopted_config},
    )
    mounts = {mount.logical_name: mount for mount in plan.mounts}
    assert mounts["pycharm/config"].source == str(adopted_config)
    assert mounts["pycharm/plugins"].source.endswith("components/pycharm/plugins")


def test_planning_has_no_filesystem_side_effect_until_prepared(tmp_path: Path) -> None:
    plan = plan_component_persistence(
        runtime_template(),
        roots=StateRoots(tmp_path / "data", tmp_path / "state", tmp_path / "cache"),
        checkout_namespace=Path("checkout"),
    )
    assert not tmp_path.joinpath("data").exists()
    prepare_persistence_directories(plan)
    assert all(Path(mount.source).is_dir() for mount in plan.mounts if mount.storage == "directory")


def test_state_binding_rejects_relative_host_directory(tmp_path: Path) -> None:
    with pytest.raises(RuntimePlanError, match="absolute host directory"):
        plan_component_persistence(
            runtime_template(),
            roots=StateRoots(tmp_path / "data", tmp_path / "state", tmp_path / "cache"),
            checkout_namespace=Path("checkout"),
            adopted={"pycharm/config": Path("relative")},
        )
