"""Generic persistent filesystem and XDG preparation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .contract import Identity, RuntimePlan

__all__ = ["FilesystemPlan", "RUNTIME_ROOT", "plan_filesystem", "prepare_filesystem"]

RUNTIME_ROOT = "/tmp"
"""Where a session's ``XDG_RUNTIME_DIR`` is made: the image's temporary directory."""


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
        "XDG_RUNTIME_DIR": str(Path(RUNTIME_ROOT) / f"devcapsule-runtime-{runtime.identity.uid}"),
    }
    directories = (str(home), str(home / ".ssh"), str(home / "xtras" / "bin"),
                   *environment.values(), *slots)
    return FilesystemPlan(tuple(dict.fromkeys(directories)), environment)


def prepare_filesystem(plan: FilesystemPlan, identity: Identity) -> None:
    for directory in plan.directories:
        path = Path(directory)
        missing: list[Path] = []
        cursor = path
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        path.mkdir(parents=True, exist_ok=True)
        if os.geteuid() == 0:
            for created in reversed(missing):
                os.chown(created, identity.uid, identity.gid)
    Path(plan.environment["XDG_RUNTIME_DIR"]).chmod(0o700)
    Path(plan.environment["HOME"], ".ssh").chmod(0o700)
