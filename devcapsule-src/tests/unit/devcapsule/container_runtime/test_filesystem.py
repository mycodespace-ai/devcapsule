"""Unit tests of ``devcapsule/container_runtime/filesystem.py``: persistent home, slot, and XDG runtime planning."""

from __future__ import annotations

from pathlib import Path
import stat

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import Identity, RuntimePlan
from devcapsule.container_runtime.filesystem import FilesystemPlan, plan_filesystem, prepare_filesystem


def sandboxed_plan(tmp_path: Path) -> RuntimePlan:
    """Construct a ``RuntimePlan`` whose home and declared state slots all live beneath ``tmp_path``."""
    base = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path=str(tmp_path / "project"),
        home=str(tmp_path / "home"),
        identity=Identity(1000, 1001, "developer"),
    )
    document = base.to_mapping()
    document["state_slots"] = [
        {"name": slot.name, "path": str(tmp_path / "slots" / slot.name.replace("/", "-"))}
        for slot in base.state_slots
    ]
    return RuntimePlan.from_mapping(document)


@pytest.mark.parametrize("custom_root", [False, True])
def test_plan_filesystem_places_xdg_runtime_dir_under_the_requested_root(
    tmp_path: Path, custom_root: bool,
) -> None:
    """``plan_filesystem`` places ``XDG_RUNTIME_DIR`` under ``/tmp`` by default or under an explicit ``runtime_root``."""
    runtime = sandboxed_plan(tmp_path)
    expected_root = (tmp_path / "runtime") if custom_root else Path("/tmp")

    plan = (
        plan_filesystem(runtime, runtime_root=expected_root)
        if custom_root
        else plan_filesystem(runtime)
    )

    expected_runtime_dir = str(expected_root / "devcapsule-runtime-1000")
    assert plan.environment["XDG_RUNTIME_DIR"] == expected_runtime_dir
    assert expected_runtime_dir in plan.directories
    assert all(slot.path in plan.directories for slot in runtime.state_slots)


def test_prepare_filesystem_creates_sandboxed_directories_and_private_modes(tmp_path: Path) -> None:
    """For a non-root caller, ``prepare_filesystem`` creates home, XDG, runtime, and slot directories with ``0700`` private modes."""
    runtime = sandboxed_plan(tmp_path)
    filesystem = plan_filesystem(runtime, runtime_root=tmp_path / "runtime")
    chowned: list[tuple[Path, int, int]] = []

    prepare_filesystem(
        filesystem,
        runtime.identity,
        caller_uid=1000,
        chown=lambda path, uid, gid: chowned.append((path, uid, gid)),
    )

    assert chowned == []
    assert all(Path(directory).is_dir() for directory in filesystem.directories)
    ssh_mode = stat.S_IMODE((Path(filesystem.environment["HOME"]) / ".ssh").stat().st_mode)
    runtime_mode = stat.S_IMODE(Path(filesystem.environment["XDG_RUNTIME_DIR"]).stat().st_mode)
    assert ssh_mode == 0o700
    assert runtime_mode == 0o700


def test_prepare_filesystem_assigns_ownership_only_to_newly_created_ancestors_when_root(tmp_path: Path) -> None:
    """When ``caller_uid`` is 0, ``prepare_filesystem`` invokes ``chown`` only on directories that did not already exist."""
    existing = tmp_path / "home"
    existing.mkdir()
    runtime_dir = tmp_path / "runtime" / "devcapsule-runtime-1000"
    plan = FilesystemPlan(
        directories=(str(existing), str(existing / ".ssh"), str(runtime_dir)),
        environment={"HOME": str(existing), "XDG_RUNTIME_DIR": str(runtime_dir)},
    )
    chowned: list[tuple[Path, int, int]] = []

    prepare_filesystem(
        plan,
        Identity(1000, 1001, "developer"),
        caller_uid=0,
        chown=lambda path, uid, gid: chowned.append((path, uid, gid)),
    )

    assert chowned == [
        (existing / ".ssh", 1000, 1001),
        (tmp_path / "runtime", 1000, 1001),
        (runtime_dir, 1000, 1001),
    ]
