"""Unit tests of ``devcapsule/container_runtime/filesystem.py``: persistent home, slot, and XDG runtime planning."""

from __future__ import annotations

from pathlib import Path
import stat

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import Identity, RuntimePlan
from devcapsule.container_runtime.filesystem import (
    FilesystemPlan,
    create_directories,
    plan_filesystem,
    prepare_filesystem,
)
from devcapsule.container_runtime.identity import CapsuleUser

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


def test_plan_filesystem_derives_the_session_directories_from_the_home_the_user_and_the_slots(
    tmp_path: Path,
) -> None:
    """``plan_filesystem`` puts the XDG directories under the home, names the runtime directory after the uid under /tmp, and lists them with every state slot."""
    runtime = sandboxed_plan(tmp_path)

    plan = plan_filesystem(runtime)

    runtime_directory = "/tmp/devcapsule-runtime-1000"
    assert plan.environment["HOME"] == str(tmp_path / "home")
    assert plan.environment["XDG_CONFIG_HOME"] == str(tmp_path / "home" / ".config")
    assert plan.environment["XDG_RUNTIME_DIR"] == runtime_directory
    assert {str(tmp_path / "home"), str(tmp_path / "home" / ".config"), runtime_directory} <= set(plan.directories)
    assert {slot.path for slot in runtime.state_slots} <= set(plan.directories)


def test_create_directories_creates_every_directory_and_keeps_ssh_and_runtime_private(tmp_path: Path) -> None:
    """``create_directories`` creates each directory of the plan and sets ``0700`` on ``.ssh`` and the runtime directory."""
    filesystem = filesystem_under(tmp_path)

    create_directories(filesystem)

    assert all(Path(directory).is_dir() for directory in filesystem.directories)
    assert stat.S_IMODE((tmp_path / "home" / ".ssh").stat().st_mode) == 0o700
    assert stat.S_IMODE(Path(filesystem.environment["XDG_RUNTIME_DIR"]).stat().st_mode) == 0o700


def test_create_directories_returns_only_what_it_created_a_parent_before_its_child(tmp_path: Path) -> None:
    """``create_directories`` returns each directory it made, missing parents included and first, and leaves out one that existed."""
    filesystem = filesystem_under(tmp_path)
    (tmp_path / "home").mkdir()

    created = create_directories(filesystem)

    assert created == (
        tmp_path / "home" / ".ssh",
        tmp_path / "runtime",
        tmp_path / "runtime" / "devcapsule-runtime-1000",
    )


def test_create_directories_returns_nothing_when_every_directory_exists(tmp_path: Path) -> None:
    """Run again on a prepared filesystem, ``create_directories`` creates nothing and says so."""
    filesystem = filesystem_under(tmp_path)
    create_directories(filesystem)

    assert create_directories(filesystem) == ()


def test_prepare_filesystem_creates_the_directories_for_a_caller_that_is_not_root(tmp_path: Path) -> None:
    """For a caller that is not root, ``prepare_filesystem`` creates the plan's directories without failing on an owner it may not set."""
    filesystem = filesystem_under(tmp_path)

    prepare_filesystem(filesystem, CapsuleUser(DEVELOPER, caller_uid=1000))

    assert all(Path(directory).is_dir() for directory in filesystem.directories)
