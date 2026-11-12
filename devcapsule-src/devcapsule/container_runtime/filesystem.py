"""Generic persistent filesystem and XDG preparation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .contract import RuntimePlan
from .identity import CapsuleUser

__all__ = ["FilesystemPlan", "create_directories", "plan_filesystem", "prepare_filesystem"]


@dataclass(frozen=True)
class FilesystemPlan:
    directories: tuple[str, ...]
    environment: dict[str, str]


def plan_filesystem(runtime: RuntimePlan) -> FilesystemPlan:
    home = Path(runtime.home)
    slots = tuple(slot.path for slot in runtime.state_slots)
    environment = {
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_RUNTIME_DIR": f"/tmp/devcapsule-runtime-{runtime.identity.uid}",
    }
    directories = (str(home), str(home / ".ssh"), str(home / "xtras" / "bin"),
                   *environment.values(), *slots)
    return FilesystemPlan(tuple(dict.fromkeys(directories)), environment)


def create_directories(plan: FilesystemPlan) -> tuple[Path, ...]:
    """Create every directory of ``plan``; keep ``.ssh`` and the runtime directory private.

    Returns the directories this call created, a parent before its child.
    A directory that existed is not among them, so its owner stays as the
    volume or the image set it.
    """

    created: list[Path] = []
    for directory in plan.directories:
        path = Path(directory)
        missing: list[Path] = []
        cursor = path
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        path.mkdir(parents=True, exist_ok=True)
        created.extend(reversed(missing))
    Path(plan.environment["XDG_RUNTIME_DIR"]).chmod(0o700)
    Path(plan.environment["HOME"], ".ssh").chmod(0o700)
    return tuple(created)


def prepare_filesystem(plan: FilesystemPlan, user: CapsuleUser) -> None:
    """Create the session's directories and give the new ones to the capsule user.

    Which owners change is :meth:`CapsuleUser.owner_changes`' decision; this
    only performs it.
    """

    for path, uid, gid in user.owner_changes(create_directories(plan)):
        os.chown(path, uid, gid)
