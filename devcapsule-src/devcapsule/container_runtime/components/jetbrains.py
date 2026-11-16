"""Parameterized JetBrains product adapter."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterator
from contextlib import contextmanager, ExitStack
import errno
import fcntl
import os
from pathlib import Path
import socket
import stat
import sys
from typing import Mapping

from ..contract import RuntimePlan, RuntimePlanError

__all__ = ["JetBrainsLaunch", "plan", "recover_dead_socket", "session_lock"]


@contextmanager
def session_lock(runtime: RuntimePlan) -> Iterator[None]:
    """Hold profile ownership across the IDE lifetime before recovering stale IPC.

    IntelliJ 2026.2 stores a Unix socket in system/.port and its PID in
    config/.lock. After a container stops, PID reuse can make its vendor
    recovery mistake the new JVM for the previous process. A dead socket is
    the liveness evidence; PID numbers from another namespace are not.
    """
    if runtime.component.configuration.get("recover_stale_directory_lock") is not True:
        yield
        return
    mapping = runtime.component.configuration["state_slot_mapping"]
    assert isinstance(mapping, dict)  # validated by plan() before this hook
    slots = runtime.slots_by_name()
    config = Path(slots[runtime.component.slot_name(str(mapping["config"]))])
    system = Path(slots[runtime.component.slot_name(str(mapping["system"]))])
    with ExitStack() as held:
        for directory in sorted({config, system}):
            fd = os.open(directory / ".devcapsule-session.lock",
                         os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            held.callback(os.close, fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimePlanError("JetBrains profile is already owned by another capsule session") from exc
        recover_dead_socket(config / ".lock", system / ".port")
        yield


def recover_dead_socket(lock: Path, port: Path) -> None:
    """Remove only the verified dead Unix socket and its regular PID file.

    Caller holds both profile-directory guards. Live endpoints, symlinks,
    legacy TCP port files, timeouts and permission failures are left intact.
    """
    try:
        original_port = port.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(original_port.st_mode):
        return
    try:
        original_lock = lock.lstat()
    except FileNotFoundError:
        original_lock = None
    if original_lock is not None and (not stat.S_ISREG(original_lock.st_mode)
                                     or not lock.read_text().strip().isdigit()):
        raise RuntimePlanError("JetBrains PID lock has an unexpected format; leaving it intact")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        probe.settimeout(1)
        try:
            probe.connect(str(port))
        except OSError as exc:
            if exc.errno != errno.ECONNREFUSED:
                raise RuntimePlanError("Cannot prove the JetBrains directory socket is stale; leaving it intact") from exc
        else:
            raise RuntimePlanError("JetBrains directory socket is live; this profile is already in use")
    # An unmanaged process may have replaced an endpoint during the probe.
    def identity(info: os.stat_result) -> tuple[int, ...]:
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

    if identity(port.lstat()) != identity(original_port) or (original_lock is not None and identity(lock.lstat()) != identity(original_lock)):
        raise RuntimePlanError("JetBrains lock changed during recovery; leaving it intact")
    port.unlink()
    if original_lock is not None:
        lock.unlink()
    print("devcapsule: recovered a stale JetBrains directory socket after exclusive profile acquisition", file=sys.stderr)


@dataclass(frozen=True)
class JetBrainsLaunch:
    properties_path: str
    properties_environment_variable: str
    properties: str
    command: tuple[str, ...]


def _string(configuration: Mapping[str, object], key: str) -> str:
    value = configuration.get(key)
    if not isinstance(value, str) or not value or "\x00" in value:
        raise RuntimePlanError(f"JetBrains component {key} must be a non-empty string")
    return value


def plan(runtime: RuntimePlan) -> JetBrainsLaunch:
    config = runtime.component.configuration
    slots = runtime.slots_by_name()
    mapping = config.get("state_slot_mapping")
    if not isinstance(mapping, dict):
        raise RuntimePlanError("JetBrains component state_slot_mapping must be an object")
    properties: list[str] = []
    for property_name in ("config", "system", "plugins", "log"):
        local_slot_name = mapping.get(property_name)
        if not isinstance(local_slot_name, str):
            raise RuntimePlanError(f"JetBrains {property_name} mapping must name a declared state slot")
        slot_name = runtime.component.slot_name(local_slot_name)
        if slot_name not in slots:
            raise RuntimePlanError(f"JetBrains {property_name} mapping must name a declared state slot")
        properties.append(f"idea.{property_name}.path={slots[slot_name]}")
    additional = config.get("additional_properties", {})
    if not isinstance(additional, dict):
        raise RuntimePlanError("JetBrains component additional_properties must be an object")
    managed_properties = {f"idea.{name}.path" for name in ("config", "system", "plugins", "log")}
    for name, value in sorted(additional.items()):
        if (
            not isinstance(name, str)
            or not name
            or any(character in name for character in "\x00\r\n= ")
            or name in managed_properties
        ):
            raise RuntimePlanError("JetBrains additional property names must be safe and unmanaged")
        if not isinstance(value, str) or "\x00" in value or "\r" in value or "\n" in value:
            raise RuntimePlanError(f"JetBrains additional property {name!r} must be one line")
        properties.append(f"{name}={value}")
    installation_path = Path(_string(config, "installation_path"))
    launcher = _string(config, "launcher")
    if Path(launcher).is_absolute() or ".." in Path(launcher).parts:
        raise RuntimePlanError("JetBrains launcher must be relative to installation_path")
    return JetBrainsLaunch(
        properties_path=_string(config, "properties_path"),
        properties_environment_variable=_string(config, "properties_environment_variable"),
        properties="\n".join(properties) + "\n",
        command=(str(installation_path / launcher), runtime.project_path),
    )
