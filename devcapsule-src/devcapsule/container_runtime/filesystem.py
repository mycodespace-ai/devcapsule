"""Generic persistent filesystem and XDG preparation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path

from .contract import Identity, RuntimePlan

__all__ = ["ChownFunc", "FilesystemPlan", "plan_filesystem", "prepare_filesystem"]

ChownFunc = Callable[[Path, int, int], None]


@dataclass(frozen=True)
class FilesystemPlan:
    directories: tuple[str, ...]
    environment: dict[str, str]


def plan_filesystem(runtime: RuntimePlan, *, runtime_root: Path = Path("/tmp")) -> FilesystemPlan:
    home = Path(runtime.home)
    slots = tuple(slot.path for slot in runtime.state_slots)
    environment = {
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_RUNTIME_DIR": str(runtime_root / f"devcapsule-runtime-{runtime.identity.uid}"),
    }
    directories = (str(home), str(home / ".ssh"), str(home / "xtras" / "bin"),
                   *environment.values(), *slots)
    return FilesystemPlan(tuple(dict.fromkeys(directories)), environment)


def prepare_filesystem(
    plan: FilesystemPlan,
    identity: Identity,
    *,
    caller_uid: int | None = None,
    chown: ChownFunc | None = None,
) -> None:
    effective_uid = os.geteuid() if caller_uid is None else caller_uid
    apply_chown: ChownFunc = os.chown if chown is None else chown
    for directory in plan.directories:
        path = Path(directory)
        missing: list[Path] = []
        cursor = path
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        path.mkdir(parents=True, exist_ok=True)
        if effective_uid == 0:
            for created in reversed(missing):
                apply_chown(created, identity.uid, identity.gid)
    Path(plan.environment["XDG_RUNTIME_DIR"]).chmod(0o700)
    Path(plan.environment["HOME"], ".ssh").chmod(0o700)
