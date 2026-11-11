"""Unit tests of ``devcapsule/container_runtime/filesystem.py``: persistent home, slot, and XDG runtime planning."""

from __future__ import annotations

import os
from pathlib import Path
import stat

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import Identity, RuntimePlan
from devcapsule.container_runtime.filesystem import FilesystemPlan, plan_filesystem, prepare_filesystem

DEVELOPER = Identity(1000, 1001, "developer")


def sandboxed_plan(tmp_path: Path) -> RuntimePlan:
    """Construct a ``RuntimePlan`` whose home and declared state slots all live beneath ``tmp_path``."""
    base = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path=str(tmp_path / "project"),
        home=str(tmp_path / "home"),
        identity=DEVELOPER,
    )
    document = base.to_mapping()
    document["state_slots"] = [
        {"name": slot.name, "path": str(tmp_path / "slots" / slot.name.replace("/", "-"))}
        for slot in base.state_slots
    ]
    return RuntimePlan.from_mapping(document)


def filesystem_under(root: Path) -> FilesystemPlan:
    """A ``FilesystemPlan`` whose home, ``.ssh`` and runtime directory all lie beneath ``root``."""
    home = root / "home"
    runtime_directory = root / "runtime" / "devcapsule-runtime-1000"
    return FilesystemPlan(
        directories=(str(home), str(home / ".ssh"), str(runtime_directory)),
        environment={"HOME": str(home), "XDG_RUNTIME_DIR": str(runtime_directory)},
    )


def record_ownership_changes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, int, int]]:
    """Replace ``os.chown`` for the test and return the list its calls are appended to."""
    changes: list[tuple[Path, int, int]] = []
    monkeypatch.setattr(os, "chown", lambda path, uid, gid: changes.append((Path(path), uid, gid)))
    return changes


def test_plan_filesystem_derives_the_session_directories_from_the_home_the_user_and_the_slots(
    tmp_path: Path,
) -> None:
    """``plan_filesystem`` names the runtime directory after the uid under /tmp and lists it, the home and every state slot."""
    runtime = sandboxed_plan(tmp_path)

    plan = plan_filesystem(runtime)

    runtime_directory = "/tmp/devcapsule-runtime-1000"
    assert plan.environment["HOME"] == str(tmp_path / "home")
    assert plan.environment["XDG_RUNTIME_DIR"] == runtime_directory
    assert {str(tmp_path / "home"), runtime_directory} <= set(plan.directories)
    assert {slot.path for slot in runtime.state_slots} <= set(plan.directories)


def test_prepare_filesystem_creates_every_directory_and_keeps_ssh_and_runtime_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For a caller that is not root, ``prepare_filesystem`` creates each directory, sets ``0700`` on ``.ssh`` and the runtime directory, and changes no owner."""
    filesystem = filesystem_under(tmp_path)
    with monkeypatch.context() as process:
        process.setattr(os, "geteuid", lambda: 1000)
        changes = record_ownership_changes(process)
        prepare_filesystem(filesystem, DEVELOPER)

    assert all(Path(directory).is_dir() for directory in filesystem.directories)
    assert stat.S_IMODE((tmp_path / "home" / ".ssh").stat().st_mode) == 0o700
    assert stat.S_IMODE(Path(filesystem.environment["XDG_RUNTIME_DIR"]).stat().st_mode) == 0o700
    assert changes == []


def test_prepare_filesystem_gives_the_capsule_user_only_the_directories_it_created_when_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """For root, ``prepare_filesystem`` hands each directory it created to the capsule user, outermost first, and leaves an existing one alone."""
    filesystem = filesystem_under(tmp_path)
    (tmp_path / "home").mkdir()
    with monkeypatch.context() as process:
        process.setattr(os, "geteuid", lambda: 0)
        changes = record_ownership_changes(process)
        prepare_filesystem(filesystem, DEVELOPER)

    assert changes == [
        (tmp_path / "home" / ".ssh", 1000, 1001),
        (tmp_path / "runtime", 1000, 1001),
        (tmp_path / "runtime" / "devcapsule-runtime-1000", 1000, 1001),
    ]
