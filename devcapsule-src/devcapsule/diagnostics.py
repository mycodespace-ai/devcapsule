"""Live and post-mortem session diagnostics snapshot and sanitized archive export.

Implements ``devcapsule project diagnose`` (Deliverable 4 and the manual browser
evidence contract of Deliverable 5 in
``engineering-docs/work-orders/2026-10-08-persistent-session-diagnostics.md``).
"""

from __future__ import annotations

from contextlib import contextmanager
import gzip
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import tarfile
import time
from typing import Any, BinaryIO, Callable, Iterable, Iterator, Mapping
import zlib

from devcapsule import logs, runtime_configuration
from devcapsule._redaction import redact_json_value, redact_text
from devcapsule.build_info import BuildInfoError, current_build_info
from devcapsule.compat import CliError
from devcapsule.configuration.bindings import ConfigurationBindingDeclaration, configuration_binding_declarations, managed_binding_path
from devcapsule.configuration.docker_arguments import read_arguments, read_environment
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.storage import (
    checkout_name_for,
    config_root,
    find_checkout_record,
    load_checkout,
    lock_for,
    manifest_for,
)
from devcapsule.container_runtime.contract import (
    CONTAINED_DISPLAY_TRANSPORT,
    INFRASTRUCTURE_FAILURE_EXIT_CODE,
    RuntimePlan,
    RuntimePlanError,
)
from devcapsule.container_runtime.diagnose import (
    DEFAULT_PROBE_TIMEOUT_SECONDS,
    DEFAULT_RUNTIME_PLAN_PATH,
    collect_runtime_probe,
    default_user_agent,
    probe_http_get,
)
from devcapsule.docker_arguments import inline_environment_names
from devcapsule.launch.session_logs import SESSION_LOG_DESTINATION, session_logs_root
from devcapsule.materialization import ENTRYPOINT_CONTRACT

SNAPSHOT_SCHEMA_VERSION = 1
DEFAULT_DOCKER_INSPECT_TIMEOUT_SECONDS = 3.0
DEFAULT_DOCKER_EXEC_TIMEOUT_SECONDS = 5.0
MAX_EXPORT_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_IDE_LOG_ENTRIES = 4096
MAX_SESSION_MANIFEST_BYTES = 1024 * 1024
MAX_SINGLE_EXPORT_FILE_BYTES = 32 * 1024 * 1024
_DECOMPRESS_CHUNK_BYTES = 64 * 1024
_SESSION_ID_SAFE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_ECLIPSE_LOG_NAME_RE = re.compile(r"^\.(?:bak_\d+\.)?log$")

BROWSER_EVIDENCE_MANUAL_CONTRACT: dict[str, Any] = {
    "collected": False,
    "mode": "manual-devtools",
    "guide": "docs/troubleshooting/diagnostics-and-logs.md#browser-evidence",
    "reason": (
        "Host and capsule diagnostics cannot read browser tab state, client-only "
        "WebSocket close codes, or JavaScript console errors; capture DevTools "
        "Console and WebSocket frame details manually when the browser fails."
    ),
}

REDACTION_NOTICE = (
    "Known URL run tokens (?token=), console cookies, authorization headers, "
    "secret flags, and configured inline Docker environment values are redacted; "
    "arbitrary process output and IDE-native logs can still contain credentials "
    "or project content."
)


class DiagnosticsError(CliError):
    """User-facing diagnostics selection or export failure."""


def _utc_stamp(now: float | None = None) -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(time.time() if now is None else now))


def _iso_utc(now: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if now is None else now))


def _validate_session_id(session_id: str) -> str:
    if _SESSION_ID_SAFE_RE.match(session_id) is None or ".." in session_id:
        raise DiagnosticsError(f"Invalid session identifier: {session_id!r}.")
    return session_id


def _is_real_directory(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode)


@contextmanager
def _open_directory(path: Path) -> Iterator[int]:
    """Pin a directory, refusing symlinks in every path component."""

    absolute = Path(os.path.abspath(path))
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _open_regular_file(path: Path) -> Iterator[BinaryIO]:
    """Open a regular file without following links or blocking on a FIFO."""

    with _open_directory(path.parent) as parent_fd:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(f"non-regular file refused: {path}")
        handle = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with handle:
        yield handle


def _read_session_manifest(directory: Path) -> tuple[dict[str, Any], str | None]:
    manifest_path = directory / logs.SESSION_MANIFEST
    try:
        info = manifest_path.lstat()
        if not stat.S_ISREG(info.st_mode):
            return {}, f"{manifest_path} is not a regular file"
        with _open_regular_file(manifest_path) as handle:
            raw = handle.read(MAX_SESSION_MANIFEST_BYTES + 1)
        if len(raw) > MAX_SESSION_MANIFEST_BYTES:
            return {}, "session.json exceeds diagnostic byte limit"
        parsed = json.loads(raw)
    except FileNotFoundError:
        return {}, "session.json is absent"
    except (OSError, ValueError) as error:
        return {}, f"cannot read session.json: {error}"
    if not isinstance(parsed, dict):
        return {}, "session.json is not a JSON object"
    return parsed, None


def select_session_directory(
    logs_root: Path,
    *,
    session_id: str | None = None,
    now: float | None = None,
    is_container_running: Callable[[str], bool] | None = None,
) -> tuple[Path, str]:
    """Select ``--session ID``, else the newest active session, else the newest ended session."""

    if session_id is not None:
        validated = _validate_session_id(session_id)
        candidate = logs_root / validated
        try:
            info = candidate.lstat()
        except FileNotFoundError as exc:
            available = _list_session_names(logs_root)
            suffix = (
                f" Available sessions: {', '.join(available[-5:])}."
                if available
                else f" No session logs exist under {logs_root}."
            )
            raise DiagnosticsError(f"Session {validated!r} was not found under {logs_root}.{suffix}") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise DiagnosticsError(f"Session path {candidate} is not a regular directory.")
        return candidate, "explicit"

    candidates = _list_session_directories(logs_root)
    if not candidates:
        raise DiagnosticsError(
            f"No session logs found under {logs_root}; launch the project first with 'devcapsule project run'."
        )
    # Manifest readers used by retention can follow links and block on FIFOs.
    # Diagnose uses its own bounded, no-follow reader and verifies live state.
    for entry in reversed(candidates):
        manifest_doc, _ = _read_session_manifest(entry)
        if manifest_doc.get("ended-at"):
            continue
        container_name = str(manifest_doc.get("container") or "")
        if is_container_running is not None:
            if container_name and is_container_running(container_name):
                return entry, "active"
        elif manifest_doc:
            return entry, "active"
    return candidates[-1], "latest-ended"


def _list_session_directories(logs_root: Path) -> list[Path]:
    try:
        if not _is_real_directory(logs_root):
            return []
        entries = [entry for entry in logs_root.iterdir() if _is_real_directory(entry)]
    except OSError:
        return []
    entries.sort(key=lambda item: item.name)
    return entries


def _list_session_names(logs_root: Path) -> list[str]:
    return [entry.name for entry in _list_session_directories(logs_root)]


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _configured_sensitive_env_names(root: Path, manifest: Mapping[str, Any], env: Mapping[str, str]) -> set[str]:
    names: set[str] = set()
    try:
        record = find_checkout_record(dict(manifest), root, env)
        if record is not None:
            cfg_root = config_root(env)
            relative = record.relative_to(cfg_root / "projects")
            checkout_stem = relative.name.removesuffix(".checkout.toml")
            args_file = cfg_root / "docker-arguments" / relative.parent / checkout_stem / "arguments.json"
            if args_file.is_file():
                names.update(inline_environment_names(read_arguments(args_file)))
                names.update(read_environment(args_file).keys())
    except (ProjectConfigurationError, OSError, ValueError):
        pass
    return {name for name in names if name}


def inspect_container(
    container_name: str,
    *,
    env: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_DOCKER_INSPECT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run a bounded ``docker inspect`` and extract non-secret container facts."""

    if not container_name:
        return {
            "available": False,
            "container_removed": False,
            "unavailable_reason": "no container name recorded in session manifest",
        }
    docker = shutil.which("docker", path=(env or os.environ).get("PATH"))
    if docker is None:
        return {
            "available": False,
            "container": container_name,
            "container_removed": False,
            "unavailable_reason": "docker CLI is not installed or not on PATH",
        }
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [docker, "inspect", "--type", "container", container_name],
            env=dict(os.environ if env is None else env),
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "container": container_name,
            "container_removed": False,
            "timed_out": True,
            "unavailable_reason": f"docker inspect timed out after {timeout:g}s",
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except OSError as error:
        return {
            "available": False,
            "container": container_name,
            "container_removed": False,
            "timed_out": False,
            "unavailable_reason": f"cannot execute docker inspect: {error}",
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    duration_ms = round((time.monotonic() - started) * 1000, 1)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        lowered = stderr.lower()
        removed = "no such container" in lowered or "no such object" in lowered
        return {
            "available": False,
            "container": container_name,
            "container_removed": removed,
            "timed_out": False,
            "unavailable_reason": (
                "container is no longer present (removed on exit by --rm)"
                if removed
                else redact_text(stderr or f"docker inspect exited {completed.returncode}")
            ),
            "duration_ms": duration_ms,
        }

    try:
        payload = json.loads(completed.stdout)
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            raise ValueError("unexpected docker inspect JSON payload")
        item = payload[0]
    except ValueError as error:
        return {
            "available": False,
            "container": container_name,
            "container_removed": False,
            "timed_out": False,
            "unavailable_reason": f"invalid docker inspect output: {error}",
            "duration_ms": duration_ms,
        }

    state = _as_dict(item.get("State"))
    host_config = _as_dict(item.get("HostConfig"))
    config = _as_dict(item.get("Config"))
    net_settings = _as_dict(item.get("NetworkSettings"))

    raw_ports = _as_dict(net_settings.get("Ports"))
    published_ports: dict[str, list[dict[str, Any]]] = {}
    for container_port, bindings in sorted(raw_ports.items()):
        if not isinstance(bindings, list):
            continue
        mapped: list[dict[str, Any]] = []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            host_port_raw = binding.get("HostPort", "")
            host_port = int(host_port_raw) if isinstance(host_port_raw, str) and host_port_raw.isdigit() else None
            mapped.append({"host_ip": binding.get("HostIp", ""), "host_port": host_port})
        published_ports[str(container_port)] = mapped

    raw_env = _as_list(config.get("Env"))
    env_names = sorted({
        entry.split("=", 1)[0]
        for entry in raw_env
        if isinstance(entry, str) and entry
    })

    return {
        "available": True,
        "container": container_name,
        "id": item.get("Id"),
        "image_id": item.get("Image"),
        "status": state.get("Status"),
        "running": bool(state.get("Running", False)),
        "paused": bool(state.get("Paused", False)),
        "restarting": bool(state.get("Restarting", False)),
        "oom_killed": bool(state.get("OOMKilled", False)),
        "dead": bool(state.get("Dead", False)),
        "pid": state.get("Pid"),
        "exit_code": state.get("ExitCode"),
        "error": redact_text(str(state.get("Error") or "")),
        "started_at": state.get("StartedAt"),
        "finished_at": state.get("FinishedAt"),
        "resources": {
            "memory_limit_bytes": host_config.get("Memory") or None,
            "memory_swap_bytes": host_config.get("MemorySwap") or None,
            "nano_cpus": host_config.get("NanoCpus") or None,
            "pids_limit": host_config.get("PidsLimit") or None,
            "shm_size_bytes": host_config.get("ShmSize") or None,
            "readonly_rootfs": bool(host_config.get("ReadonlyRootfs", False)),
        },
        "network_mode": host_config.get("NetworkMode"),
        "published_ports": published_ports,
        "environment_variable_names": env_names,
        "duration_ms": duration_ms,
    }


def run_container_probe(
    container_name: str,
    *,
    env: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_DOCKER_EXEC_TIMEOUT_SECONDS,
    probe_timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    user_agent: str | None = None,
    extra_env_names: Iterable[str] = (),
) -> dict[str, Any]:
    """Execute ``runtime diagnose-probe`` inside the running capsule under a hard timeout."""

    docker = shutil.which("docker", path=(env or os.environ).get("PATH"))
    if docker is None:
        return {
            "available": False,
            "timed_out": False,
            "unavailable_reason": "docker CLI is not installed or not on PATH",
        }
    agent = user_agent or default_user_agent()
    cmd = [
        docker,
        "exec",
        container_name,
        ENTRYPOINT_CONTRACT[0],
        ENTRYPOINT_CONTRACT[1],
        "diagnose-probe",
        "--probe-timeout",
        f"{probe_timeout:g}",
        "--user-agent",
        agent,
    ]
    for name in sorted({item for item in extra_env_names if item}):
        cmd.extend(["--redact-env", name])

    started = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            env=dict(os.environ if env is None else env),
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "timed_out": True,
            "unavailable_reason": f"docker exec diagnose-probe timed out after {timeout:g}s",
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except OSError as error:
        return {
            "available": False,
            "timed_out": False,
            "unavailable_reason": f"cannot execute docker exec: {error}",
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    duration_ms = round((time.monotonic() - started) * 1000, 1)
    if completed.returncode != 0:
        stderr = redact_text(completed.stderr.strip())
        if "cannot read runtime plan diagnose-probe" in stderr or "usage: devcapsule runtime" in stderr:
            reason = (
                "container image carries an older runtime PEX without diagnose-probe; "
                "rematerialize or relaunch with the updated launcher"
            )
        else:
            reason = stderr or f"diagnose-probe exited with status {completed.returncode}"
        return {
            "available": False,
            "timed_out": False,
            "unavailable_reason": reason,
            "duration_ms": duration_ms,
        }

    try:
        parsed = json.loads(completed.stdout)
        if not isinstance(parsed, dict):
            raise ValueError("probe output is not a JSON object")
    except ValueError as error:
        return {
            "available": False,
            "timed_out": False,
            "unavailable_reason": f"malformed diagnose-probe JSON: {error}",
            "duration_ms": duration_ms,
        }
    parsed["available"] = True
    parsed["duration_ms"] = duration_ms
    return parsed


def _resolve_host_port(
    manifest: Mapping[str, Any],
    container_info: Mapping[str, Any],
    *,
    section: str,
    default_container_port: str,
) -> int | None:
    section_value = manifest.get(section)
    if isinstance(section_value, dict):
        port = section_value.get("host-port")
        if isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535:
            return port
    published = container_info.get("published_ports")
    if isinstance(published, dict):
        bindings = published.get(default_container_port)
        if isinstance(bindings, list):
            for entry in bindings:
                if isinstance(entry, dict) and isinstance(entry.get("host_port"), int):
                    return int(entry["host_port"])
    return None


def collect_host_loopback_probes(
    manifest: Mapping[str, Any],
    container_info: Mapping[str, Any],
    *,
    probe_timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Probe published host-loopback HTTP endpoints to separate Docker port-forwarding issues."""

    if not container_info.get("running"):
        return {
            "available": False,
            "unavailable_reason": "container is not running",
        }

    agent = user_agent or default_user_agent()
    display_section = manifest.get("display")
    display_transport = (
        display_section.get("transport")
        if isinstance(display_section, dict)
        else None
    )
    display_port = _resolve_host_port(
        manifest,
        container_info,
        section="display",
        default_container_port="6080/tcp",
    )
    console_port = _resolve_host_port(
        manifest,
        container_info,
        section="console",
        default_container_port="6081/tcp",
    )

    probes: dict[str, Any] = {}
    if display_port is not None:
        probes["display_host_http"] = probe_http_get(
            "127.0.0.1",
            display_port,
            "/vnc.html",
            timeout=probe_timeout,
            user_agent=agent,
            healthy_statuses=frozenset({200}),
        )
    elif display_transport and display_transport != CONTAINED_DISPLAY_TRANSPORT:
        probes["display_host_http"] = {
            "status": "not-applicable",
            "healthy": None,
            "reason": f"display transport is {display_transport}",
        }
    else:
        probes["display_host_http"] = {
            "status": "port-unknown",
            "healthy": None,
            "reason": "no published host display port recorded in session.json or docker inspect",
        }

    console_section = manifest.get("console")
    console_enabled = console_section.get("enabled") if isinstance(console_section, dict) else None
    if console_port is not None:
        # Without the per-run token (which is never persisted to disk), a live
        # web console answers 403 with its TokenGate refusal body.
        probes["console_host_http"] = probe_http_get(
            "127.0.0.1",
            console_port,
            "/",
            timeout=probe_timeout,
            user_agent=agent,
            healthy_statuses=frozenset({200, 403}),
        )
    elif console_enabled is False:
        probes["console_host_http"] = {
            "status": "not-configured",
            "healthy": None,
            "reason": "web console was not enabled for this session",
        }
    else:
        probes["console_host_http"] = {
            "status": "port-unknown",
            "healthy": None,
            "reason": "no published host console port recorded in session.json or docker inspect",
        }

    return {
        "available": True,
        "probes": probes,
    }


def _managed_slot_path(
    root: Path,
    declaration: ConfigurationBindingDeclaration,
    env: Mapping[str, str],
) -> Path:
    if dict(env) == dict(os.environ):
        return managed_binding_path(root, declaration).absolute()
    return managed_binding_path(root, declaration, env).absolute()


def _fallback_host_ide_log_specs(
    root: Path,
    manifest: Mapping[str, Any],
    env: Mapping[str, str],
) -> list[dict[str, str]]:
    try:
        _, lock = lock_for(root, dict(manifest))
        record = find_checkout_record(dict(manifest), root, env)
        checkout = load_checkout(record, dict(manifest), root) if record is not None else {}
        configured = dict(checkout.get("state", {}).get("adopted", {}))
        configured.update(checkout.get("configuration", {}).get("bindings", {}).get("host-directory", {}))
        declarations = configuration_binding_declarations(lock)
    except (ProjectConfigurationError, OSError, ValueError):
        return []

    specs: list[dict[str, str]] = []
    for name, declaration in sorted(declarations.items()):
        explicit = configured.get(name)
        backing = (
            Path(str(explicit)).expanduser().absolute()
            if explicit is not None
            else _managed_slot_path(root, declaration, env)
        )
        if declaration.slot_name == "log":
            specs.append({
                "slot": name,
                "family": "jetbrains",
                "host-path": str(backing),
                "container-path": declaration.container_path,
            })
        elif declaration.slot_name == "user-data":
            specs.append({
                "slot": name,
                "family": "vscode",
                "host-path": str(backing / "logs"),
                "container-path": f"{declaration.container_path.rstrip('/')}/logs",
            })
        elif declaration.slot_name == "workspace":
            specs.append({
                "slot": name,
                "family": "eclipse",
                "host-path": str(backing / ".metadata"),
                "container-path": f"{declaration.container_path.rstrip('/')}/.metadata",
            })
    return specs


def _in_capsule_ide_log_specs(plan_path: Path = DEFAULT_RUNTIME_PLAN_PATH) -> list[dict[str, str]]:
    try:
        plan = RuntimePlan.from_file(plan_path)
    except RuntimePlanError:
        return []
    slots = plan.slots_by_name()
    component = plan.component
    config = component.configuration
    if component.adapter == "jetbrains":
        mapping = config.get("state_slot_mapping")
        local_slot = mapping.get("log") if isinstance(mapping, dict) else None
        if isinstance(local_slot, str):
            slot_name = component.slot_name(local_slot)
            if slot_name in slots:
                return [{"slot": slot_name, "family": "jetbrains", "path": slots[slot_name]}]
    elif component.adapter == "vscode":
        mapping = config.get("state_slot_mapping")
        local_slot = mapping.get("user-data") if isinstance(mapping, dict) else None
        if isinstance(local_slot, str):
            slot_name = component.slot_name(local_slot)
            if slot_name in slots:
                return [{"slot": slot_name, "family": "vscode", "path": f"{slots[slot_name].rstrip('/')}/logs"}]
    elif component.adapter == "eclipse":
        local_slot = config.get("workspace_slot")
        if isinstance(local_slot, str):
            slot_name = component.slot_name(local_slot)
            if slot_name in slots:
                return [{"slot": slot_name, "family": "eclipse", "path": f"{slots[slot_name].rstrip('/')}/.metadata"}]
    return []


def _walk_ide_log_files(base: Path, *, family: str) -> tuple[list[tuple[Path, str, int]], list[dict[str, str]]]:
    """Return ``(eligible_files, skipped_entries)`` under ``base`` without following symlinks."""

    eligible: list[tuple[Path, str, int]] = []
    skipped: list[dict[str, str]] = []
    try:
        with _open_directory(base.parent):
            pass
        root_info = base.lstat()
    except FileNotFoundError:
        return eligible, skipped
    except OSError as error:
        skipped.append({"path": str(base), "reason": f"unreadable: {error}"})
        return eligible, skipped
    if stat.S_ISLNK(root_info.st_mode):
        skipped.append({"path": str(base), "reason": "symlink refused"})
        return eligible, skipped
    if stat.S_ISREG(root_info.st_mode):
        eligible.append((base, base.name, root_info.st_size))
        return eligible, skipped
    if not stat.S_ISDIR(root_info.st_mode):
        return eligible, skipped

    stack: list[tuple[Path, Path]] = [(base, Path("."))]
    visited = 0
    while stack:
        current, rel_prefix = stack.pop()
        try:
            with _open_directory(current) as directory_fd:
                # scandir is lazy; do not allocate an unbounded directory listing.
                with os.scandir(directory_fd) as scan:
                    children = []
                    for item in scan:
                        if visited >= MAX_IDE_LOG_ENTRIES:
                            skipped.append({"path": str(base), "reason": "IDE log entry limit reached"})
                            return sorted(eligible, key=lambda item: item[1]), skipped
                        visited += 1
                        children.append(current / item.name)
                children.sort(key=lambda item: item.name)
        except OSError as error:
            skipped.append({"path": str(current), "reason": f"unreadable directory: {error}"})
            continue
        for child in children:
            rel = rel_prefix / child.name if rel_prefix != Path(".") else Path(child.name)
            try:
                info = child.lstat()
            except OSError as error:
                skipped.append({"path": str(child), "reason": f"lstat failed: {error}"})
                continue
            if stat.S_ISLNK(info.st_mode):
                skipped.append({"path": str(child), "reason": "symlink refused"})
                continue
            if family == "eclipse":
                # Only Eclipse's .metadata/.log and .metadata/.bak_*.log files, never workspace plugins.
                if rel_prefix == Path(".") and stat.S_ISREG(info.st_mode) and _ECLIPSE_LOG_NAME_RE.match(child.name):
                    eligible.append((child, rel.as_posix(), info.st_size))
                continue
            if child.name.startswith(".devcapsule-") and child.name.endswith(".lock"):
                continue
            if stat.S_ISDIR(info.st_mode):
                stack.append((child, rel))
            elif stat.S_ISREG(info.st_mode):
                eligible.append((child, rel.as_posix(), info.st_size))
    eligible.sort(key=lambda item: item[1])
    return eligible, skipped


def inspect_ide_native_logs(
    specs: Iterable[Mapping[str, Any]],
    *,
    in_capsule: bool,
    included_in_export: bool,
) -> tuple[dict[str, Any], list[tuple[str, Path, str, int]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    collected_files: list[tuple[str, Path, str, int]] = []
    skipped_all: list[dict[str, str]] = []

    for spec in specs:
        slot = str(spec.get("slot") or "ide")
        family = str(spec.get("family") or "ide")
        raw_path = spec.get("path") if in_capsule else (spec.get("host-path") or spec.get("path"))
        if not isinstance(raw_path, str) or not raw_path:
            continue
        target = Path(raw_path)
        files, skipped = _walk_ide_log_files(target, family=family)
        skipped_all.extend(skipped)
        try:
            exists = not target.is_symlink() and target.exists()
        except OSError:
            exists = False
        entries.append({
            "slot": slot,
            "family": family,
            "path": str(target),
            "exists": exists,
            "file_count": len(files),
            "total_bytes": sum(size for _, _, size in files),
        })
        for file_path, rel_name, size in files:
            collected_files.append((slot, file_path, rel_name, size))

    summary: dict[str, Any] = {
        "included_in_export": included_in_export,
        "entries": entries,
    }
    if not included_in_export:
        summary["exclusion_reason"] = (
            "IDE-native logs are excluded from exports by default because they can "
            "contain project paths and source excerpts; pass --include-ide-logs to include them."
        )
    return summary, collected_files, skipped_all


def inspect_session_log_files(session_dir: Path | None) -> list[dict[str, Any]]:
    if session_dir is None or not _is_real_directory(session_dir):
        return []
    files: list[dict[str, Any]] = []
    try:
        entries = sorted(session_dir.iterdir(), key=lambda item: item.name)
    except OSError:
        return []
    for entry in entries:
        try:
            info = entry.lstat()
        except OSError:
            continue
        files.append({
            "name": entry.name,
            "size_bytes": info.st_size if stat.S_ISREG(info.st_mode) else 0,
            "is_regular": stat.S_ISREG(info.st_mode),
            "is_symlink": stat.S_ISLNK(info.st_mode),
        })
    return files


def summarize_diagnosis(
    *,
    session_manifest_doc: Mapping[str, Any],
    docker_inspect: Mapping[str, Any],
    runtime_probe: Mapping[str, Any],
    host_probes: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive a plain-language verdict without treating TCP/socket presence as health."""

    issues: list[str] = []
    ended_at = session_manifest_doc.get("ended-at")
    exit_code = session_manifest_doc.get("exit-code")

    if docker_inspect.get("oom_killed") is True:
        issues.append("Docker recorded OOMKilled=true for the container.")

    cgroup = _as_dict(runtime_probe.get("cgroup"))
    mem_events = _as_dict(_as_dict(cgroup.get("memory")).get("events"))
    oom_kills = int(mem_events.get("oom_kill") or 0) + int(mem_events.get("oom_group_kill") or 0)
    if oom_kills > 0:
        issues.append(f"Capsule cgroup memory.events recorded {oom_kills} OOM kill(s).")

    procs = _as_dict(runtime_probe.get("processes"))
    stopped = _as_list(procs.get("stopped"))
    for entry in stopped:
        if isinstance(entry, dict):
            issues.append(
                f"Process {entry.get('name')!r} (role={entry.get('role')}, pid={entry.get('pid')}) is stopped (state T)."
            )
    zombies = _as_list(procs.get("zombies"))
    if zombies:
        issues.append(f"{len(zombies)} zombie process(es) present inside capsule.")

    probes = _as_dict(runtime_probe.get("probes"))
    rfb_probe = _as_dict(probes.get("rfb_unix"))
    disp_http = _as_dict(probes.get("display_http"))
    disp_ws = _as_dict(probes.get("display_websocket_rfb"))
    cons_http = _as_dict(probes.get("console_http"))

    if rfb_probe.get("healthy") is False:
        if rfb_probe.get("accepted") is True:
            issues.append(
                f"Xvnc RFB Unix socket accepted connection without RFB greeting ({rfb_probe.get('status')})."
            )
        else:
            issues.append(f"Xvnc RFB Unix socket probe failed ({rfb_probe.get('status')}).")

    if disp_http.get("healthy") is False:
        issues.append(f"In-capsule display HTTP (/vnc.html) probe failed ({disp_http.get('status')}).")

    if disp_ws.get("healthy") is False:
        if disp_http.get("healthy") is True:
            issues.append(
                f"websockify HTTP (/vnc.html) answered 200 while WebSocket-to-RFB bridge failed ({disp_ws.get('status')})."
            )
        else:
            issues.append(f"Authenticated WebSocket-to-RFB bridge probe failed ({disp_ws.get('status')}).")

    if cons_http.get("healthy") is False:
        issues.append(f"In-capsule web console HTTP probe failed ({cons_http.get('status')}).")

    host_probe_map = _as_dict(host_probes.get("probes"))
    if host_probes.get("available") is True and host_probe_map:
        h_disp = _as_dict(host_probe_map.get("display_host_http"))
        if h_disp and h_disp.get("healthy") is False:
            if disp_http.get("healthy") is True:
                issues.append(
                    f"In-capsule display HTTP is healthy while host loopback port {h_disp.get('port')} failed ({h_disp.get('status')})."
                )
            else:
                issues.append(f"Host loopback display HTTP probe failed ({h_disp.get('status')}).")
        h_cons = _as_dict(host_probe_map.get("console_host_http"))
        if h_cons and h_cons.get("healthy") is False:
            issues.append(f"Host loopback web console HTTP probe failed ({h_cons.get('status')}).")

    if runtime_probe.get("available") is False and docker_inspect.get("running") is True:
        issues.append(f"In-capsule probe unavailable: {runtime_probe.get('unavailable_reason')}.")

    if ended_at or (docker_inspect.get("available") is True and not docker_inspect.get("running")):
        if exit_code == INFRASTRUCTURE_FAILURE_EXIT_CODE:
            issues.append(
                f"Session exited with infrastructure failure code {INFRASTRUCTURE_FAILURE_EXIT_CODE} (a supervised component died)."
            )
        elif isinstance(exit_code, int) and exit_code not in (0, 130):
            issues.append(f"Session exited with non-zero code {exit_code}.")
        state = "post-mortem-issues" if issues else "post-mortem"
    elif docker_inspect.get("available") is False and runtime_probe.get("available") is False:
        state = "post-mortem-issues" if issues else "post-mortem"
    elif issues:
        state = "degraded"
    else:
        state = "healthy"

    return {
        "state": state,
        "issue_count": len(issues),
        "issues": issues,
    }


@contextmanager
def _private_output(destination: Path) -> Iterator[BinaryIO]:
    """Replace output atomically within a pinned directory; remove failed scratch."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with _open_directory(destination.parent) as parent_fd:
        try:
            existing = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise DiagnosticsError(f"Refusing non-regular diagnostic output (including symlink): {destination}")
        temp_name = f".{destination.name}.{secrets.token_hex(8)}.tmp"
        fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
        try:
            with os.fdopen(fd, "wb") as handle:
                yield handle
            os.replace(temp_name, destination.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        finally:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass


def _atomic_write_private_bytes(destination: Path, data: bytes) -> None:
    with _private_output(destination) as handle:
        handle.write(data)


def _sanitize_plain_bytes(
    source_path: Path,
    *,
    max_bytes: int,
    env_names: set[str],
) -> tuple[bytes, bool]:
    truncated = False
    chunks: list[bytes] = []
    total = 0
    with _open_regular_file(source_path) as handle:
        while True:
            chunk = handle.read(min(_DECOMPRESS_CHUNK_BYTES, max_bytes - total + 1))
            if not chunk:
                break
            if total + len(chunk) > max_bytes:
                chunks.append(chunk[: max_bytes - total])
                truncated = True
                break
            chunks.append(chunk)
            total += len(chunk)
    raw = b"".join(chunks)
    text = raw.decode("utf-8", errors="replace")
    if source_path.suffix == ".json" and not truncated:
        try:
            document = json.loads(text)
        except ValueError:
            redacted = redact_text(text, env_names=env_names)
        else:
            redacted = json.dumps(redact_json_value(document, env_names=env_names), indent=2) + "\n"
    else:
        redacted = redact_text(text, env_names=env_names)
    if truncated:
        redacted += "\n[devcapsule diagnose: file truncated at export byte cap]\n"
    return redacted.encode("utf-8"), truncated


def _sanitize_gzip_bytes(
    source_path: Path,
    *,
    max_uncompressed_bytes: int,
    env_names: set[str],
) -> tuple[bytes, int, bool]:
    truncated = False
    chunks: list[bytes] = []
    total = 0
    with _open_regular_file(source_path) as raw_in, gzip.GzipFile(fileobj=raw_in, mode="rb") as gz_in:
        while True:
            chunk = gz_in.read(min(_DECOMPRESS_CHUNK_BYTES, max_uncompressed_bytes - total + 1))
            if not chunk:
                break
            if total + len(chunk) > max_uncompressed_bytes:
                chunks.append(chunk[: max_uncompressed_bytes - total])
                truncated = True
                break
            chunks.append(chunk)
            total += len(chunk)
    text = b"".join(chunks).decode("utf-8", errors="replace")
    redacted = redact_text(text, env_names=env_names)
    if truncated:
        redacted += "\n[devcapsule diagnose: compressed segment truncated at export byte cap]\n"
    plain_bytes = redacted.encode("utf-8")
    out_buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=out_buffer, compresslevel=6, mtime=0) as gz_out:
        gz_out.write(plain_bytes)
    return out_buffer.getvalue(), len(plain_bytes), truncated


def _add_tar_bytes(archive: tarfile.TarFile, arcname: str, payload: bytes, *, mtime: int) -> None:
    info = tarfile.TarInfo(name=arcname)
    info.size = len(payload)
    info.mode = 0o600
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = mtime
    archive.addfile(info, io.BytesIO(payload))


def _resolve_export_destination(
    export_path: Path | None,
    *,
    session_id: str,
    stamp: str,
) -> Path:
    default_name = f"devcapsule-diagnostics-{session_id}-{stamp}.tar.gz"
    if export_path is None:
        return Path.cwd() / default_name
    expanded = export_path.expanduser()
    try:
        info = expanded.lstat()
    except FileNotFoundError:
        return expanded.absolute()
    if stat.S_ISLNK(info.st_mode):
        raise DiagnosticsError(f"Refusing to write export archive through symlink: {expanded}")
    if stat.S_ISDIR(info.st_mode):
        candidate = expanded / default_name
        try:
            cand_info = candidate.lstat()
            if stat.S_ISLNK(cand_info.st_mode):
                raise DiagnosticsError(f"Refusing to write export archive through symlink: {candidate}")
        except FileNotFoundError:
            pass
        return candidate.absolute()
    return expanded.absolute()


def _safe_slot_dir(slot: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", slot).strip("_.") or "ide"


def export_diagnostics_bundle(
    destination: Path,
    *,
    session_id: str,
    session_dir: Path | None,
    snapshot: dict[str, Any],
    ide_files: list[tuple[str, Path, str, int]],
    ide_skipped: list[dict[str, str]],
    include_ide_logs: bool,
    current_snapshot_filename: str | None,
    env_names: set[str],
    now: float | None = None,
) -> dict[str, Any]:
    """Write an atomic mode-0600 sanitized ``.tar.gz`` diagnostic bundle."""

    try:
        dest_info = destination.lstat()
    except FileNotFoundError:
        dest_info = None
    if dest_info is not None and stat.S_ISLNK(dest_info.st_mode):
        raise DiagnosticsError(f"Refusing to write export archive through symlink: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    mtime = int(time.time() if now is None else now)
    prefix = f"devcapsule-diagnostics-{_validate_session_id(session_id)}"
    included_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = list(ide_skipped)
    budget_remaining = MAX_EXPORT_UNCOMPRESSED_BYTES
    bundle_truncated = False

    with _private_output(destination) as raw_out:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_out, compresslevel=6, mtime=mtime) as gz_stream:
            with tarfile.open(mode="w", fileobj=gz_stream) as archive:
                if session_dir is not None and _is_real_directory(session_dir):
                    try:
                        dir_entries = sorted(session_dir.iterdir(), key=lambda item: item.name)
                    except OSError as error:
                        skipped_files.append({"path": str(session_dir), "reason": f"unreadable: {error}"})
                        dir_entries = []

                    for entry in dir_entries:
                        if entry.name == current_snapshot_filename or entry.name.endswith(".tmp"):
                            continue
                        try:
                            info = entry.lstat()
                        except OSError as error:
                            skipped_files.append({"path": str(entry), "reason": f"lstat failed: {error}"})
                            continue
                        if stat.S_ISLNK(info.st_mode):
                            skipped_files.append({"path": str(entry), "reason": "symlink refused"})
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            skipped_files.append({"path": str(entry), "reason": "non-regular file skipped"})
                            continue
                        if budget_remaining <= 0:
                            bundle_truncated = True
                            skipped_files.append({"path": str(entry), "reason": "export byte budget reached"})
                            continue

                        cap = min(MAX_SINGLE_EXPORT_FILE_BYTES, budget_remaining)
                        try:
                            if entry.name == logs.SESSION_MANIFEST:
                                arcname = f"{prefix}/session.json"
                                payload, file_trunc = _sanitize_plain_bytes(entry, max_bytes=cap, env_names=env_names)
                                uncompressed_len = len(payload)
                            elif entry.name.startswith("snapshot-") and entry.name.endswith(".json"):
                                arcname = f"{prefix}/snapshots/{entry.name}"
                                payload, file_trunc = _sanitize_plain_bytes(entry, max_bytes=cap, env_names=env_names)
                                uncompressed_len = len(payload)
                            elif entry.name.endswith(".gz"):
                                arcname = f"{prefix}/logs/{entry.name}"
                                payload, uncompressed_len, file_trunc = _sanitize_gzip_bytes(
                                    entry, max_uncompressed_bytes=cap, env_names=env_names
                                )
                            else:
                                arcname = f"{prefix}/logs/{entry.name}"
                                payload, file_trunc = _sanitize_plain_bytes(entry, max_bytes=cap, env_names=env_names)
                                uncompressed_len = len(payload)
                        except (OSError, EOFError, zlib.error) as error:
                            skipped_files.append({"path": str(entry), "reason": f"read failed: {error}"})
                            continue

                        _add_tar_bytes(archive, arcname, payload, mtime=mtime)
                        budget_remaining = max(0, budget_remaining - uncompressed_len)
                        bundle_truncated = bundle_truncated or file_trunc
                        included_files.append({
                            "archive_path": arcname,
                            "bytes": len(payload),
                            "truncated": file_trunc,
                        })

                if include_ide_logs:
                    for slot, file_path, rel_name, _size in ide_files:
                        if budget_remaining <= 0:
                            bundle_truncated = True
                            skipped_files.append({"path": str(file_path), "reason": "export byte budget reached"})
                            continue
                        try:
                            check_info = file_path.lstat()
                        except OSError as error:
                            skipped_files.append({"path": str(file_path), "reason": f"lstat failed: {error}"})
                            continue
                        if stat.S_ISLNK(check_info.st_mode) or not stat.S_ISREG(check_info.st_mode):
                            skipped_files.append({"path": str(file_path), "reason": "symlink or non-regular file refused"})
                            continue

                        cap = min(MAX_SINGLE_EXPORT_FILE_BYTES, budget_remaining)
                        arcname = f"{prefix}/ide-logs/{_safe_slot_dir(slot)}/{rel_name}"
                        try:
                            if file_path.name.endswith(".gz"):
                                payload, uncompressed_len, file_trunc = _sanitize_gzip_bytes(
                                    file_path, max_uncompressed_bytes=cap, env_names=env_names
                                )
                            else:
                                payload, file_trunc = _sanitize_plain_bytes(
                                    file_path, max_bytes=cap, env_names=env_names
                                )
                                uncompressed_len = len(payload)
                        except (OSError, EOFError, zlib.error) as error:
                            skipped_files.append({"path": str(file_path), "reason": f"read failed: {error}"})
                            continue

                        _add_tar_bytes(archive, arcname, payload, mtime=mtime)
                        budget_remaining = max(0, budget_remaining - uncompressed_len)
                        bundle_truncated = bundle_truncated or file_trunc
                        included_files.append({
                            "archive_path": arcname,
                            "bytes": len(payload),
                            "truncated": file_trunc,
                        })

                export_record_in_archive = {
                    "archive_path": str(destination),
                    "mode": "0600",
                    "ide_logs_included": include_ide_logs,
                    "truncated": bundle_truncated,
                    "included_files": included_files,
                    "skipped_files": skipped_files,
                }
                archive_snapshot = dict(snapshot)
                archive_snapshot["export"] = redact_json_value(
                    export_record_in_archive,
                    env_names=env_names,
                )
                snapshot_bytes = (
                    json.dumps(archive_snapshot, indent=2, sort_keys=True) + "\n"
                ).encode("utf-8")
                _add_tar_bytes(archive, f"{prefix}/snapshot.json", snapshot_bytes, mtime=mtime)

    archive_size = destination.stat().st_size
    return redact_json_value(
        {
            "archive_path": str(destination),
            "archive_bytes": archive_size,
            "mode": "0600",
            "ide_logs_included": include_ide_logs,
            "truncated": bundle_truncated,
            "included_file_count": len(included_files) + 1,
            "included_files": [
                *included_files,
                {"archive_path": f"{prefix}/snapshot.json", "bytes": len(snapshot_bytes), "truncated": False},
            ],
            "skipped_files": skipped_files,
        },
        env_names=env_names,
    )


def _select_snapshot_path(session_dir: Path, stamp: str) -> Path:
    candidate = session_dir / f"snapshot-{stamp}.json"
    if not candidate.exists():
        return candidate
    suffix = 2
    while True:
        numbered = session_dir / f"snapshot-{stamp}-{suffix}.json"
        if not numbered.exists():
            return numbered
        suffix += 1


def diagnose_project(
    start_path: Path,
    *,
    runtime_fallback: bool = True,
    session_id: str | None = None,
    export_path: Path | None = None,
    export_requested: bool = False,
    include_ide_logs: bool = False,
    environ: Mapping[str, str] | None = None,
    docker_inspect_timeout: float = DEFAULT_DOCKER_INSPECT_TIMEOUT_SECONDS,
    docker_exec_timeout: float = DEFAULT_DOCKER_EXEC_TIMEOUT_SECONDS,
    probe_timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    """Capture a bounded diagnostic snapshot for a project session and optionally export it."""

    env = dict(os.environ if environ is None else environ)
    stamp = _utc_stamp(now)
    captured_at = _iso_utc(now)
    user_agent = default_user_agent()

    try:
        build = current_build_info()
        tool_info: dict[str, Any] = {
            "version": build.version,
            "source": build.source_revision,
            "mnemonic": build.build_mnemonic,
        }
    except BuildInfoError as error:
        tool_info = {"version": "unknown", "source": "", "mnemonic": "unknown", "error": str(error)}

    runtime_context = runtime_configuration.for_project(start_path, fallback=runtime_fallback)
    sensitive_env_names: set[str] = set()
    session_dir: Path | None
    selection_mode: str

    if runtime_context is not None:
        context_kind = "in-capsule"
        in_capsule_dir = Path(env.get(logs.DIRECTORY_ENV, SESSION_LOG_DESTINATION))
        session_dir = in_capsule_dir if _is_real_directory(in_capsule_dir) else None
        manifest_doc, manifest_error = (
            _read_session_manifest(session_dir)
            if session_dir is not None
            else ({}, f"session log directory is absent at {in_capsule_dir}")
        )
        current_session = str(manifest_doc.get("session") or "in-capsule")
        if session_id is not None:
            requested = _validate_session_id(session_id)
            if requested != current_session:
                launcher_cmd = runtime_context.launcher_command(["diagnose", "--session", requested])
                raise DiagnosticsError(
                    f"Inside a capsule only the current session ({current_session!r}) is mounted; "
                    f"inspect other sessions from the host: {launcher_cmd}"
                )
            selection_mode = "explicit"
        else:
            selection_mode = "in-capsule"
        effective_session_id = _validate_session_id(current_session)
        project_summary = {
            "creator": runtime_context.document["project"]["creator"],
            "slug": runtime_context.document["project"]["slug"],
            "launcher_path": runtime_context.document["launcher-root"],
            "runtime_path": runtime_context.document["runtime-root"],
            "checkout_name": runtime_context.checkout_name,
        }
        docker_inspect: dict[str, Any] = {
            "available": False,
            "container_removed": False,
            "unavailable_reason": "running inside capsule; host Docker inspection requires the host launcher",
        }
        runtime_probe = collect_runtime_probe(
            probe_timeout=probe_timeout,
            user_agent=user_agent,
        )
        runtime_probe["available"] = True
        host_probes: dict[str, Any] = {
            "available": False,
            "unavailable_reason": "running inside capsule; host loopback checks require the host launcher",
        }
        ide_specs: list[Mapping[str, Any]] = list(_in_capsule_ide_log_specs())
    else:
        context_kind = "host"
        root, manifest = manifest_for(start_path)
        sensitive_env_names = _configured_sensitive_env_names(root, manifest, env)
        logs_root = session_logs_root(root, env)
        inspected_cache: dict[str, dict[str, Any]] = {}

        def _container_is_running(name: str) -> bool:
            if name not in inspected_cache:
                inspected_cache[name] = inspect_container(name, env=env, timeout=docker_inspect_timeout)
            return bool(inspected_cache[name].get("running"))

        session_dir, selection_mode = select_session_directory(
            logs_root,
            session_id=session_id,
            now=now,
            is_container_running=_container_is_running,
        )
        manifest_doc, manifest_error = _read_session_manifest(session_dir)
        effective_session_id = _validate_session_id(session_dir.name)
        record = find_checkout_record(manifest, root, env)
        checkout_name = checkout_name_for(manifest, record) if record is not None else "default"
        project_summary = {
            "creator": manifest["project"].get("creator"),
            "slug": manifest["project"].get("slug"),
            "launcher_path": str(root),
            "runtime_path": manifest["project"].get("mount"),
            "checkout_name": checkout_name,
        }
        container_name = str(manifest_doc.get("container") or "")
        docker_inspect = inspected_cache.get(container_name) or inspect_container(
            container_name,
            env=env,
            timeout=docker_inspect_timeout,
        )
        if docker_inspect.get("running") is True:
            runtime_probe = run_container_probe(
                container_name,
                env=env,
                timeout=docker_exec_timeout,
                probe_timeout=probe_timeout,
                user_agent=user_agent,
                extra_env_names=sensitive_env_names,
            )
            host_probes = collect_host_loopback_probes(
                manifest_doc,
                docker_inspect,
                probe_timeout=probe_timeout,
                user_agent=user_agent,
            )
        else:
            reason = (
                "container is no longer present (removed on exit by --rm)"
                if docker_inspect.get("container_removed")
                else "container is not running"
            )
            runtime_probe = {"available": False, "unavailable_reason": reason}
            host_probes = {"available": False, "unavailable_reason": reason}

        raw_ide_specs = manifest_doc.get("ide-logs")
        if isinstance(raw_ide_specs, list) and raw_ide_specs:
            ide_specs = [item for item in raw_ide_specs if isinstance(item, Mapping)]
        else:
            ide_specs = list(_fallback_host_ide_log_specs(root, manifest, env))

    ide_summary, ide_files, ide_skipped = inspect_ide_native_logs(
        ide_specs,
        in_capsule=(context_kind == "in-capsule"),
        included_in_export=bool(export_requested and include_ide_logs),
    )
    session_files = inspect_session_log_files(session_dir)
    summary = summarize_diagnosis(
        session_manifest_doc=manifest_doc,
        docker_inspect=docker_inspect,
        runtime_probe=runtime_probe,
        host_probes=host_probes,
    )

    snapshot: dict[str, Any] = redact_json_value(
        {
            "schema-version": SNAPSHOT_SCHEMA_VERSION,
            "captured-at": captured_at,
            "context": context_kind,
            "tool": tool_info,
            "project": project_summary,
            "session": {
                "id": effective_session_id,
                "selection": selection_mode,
                "log_directory": str(session_dir) if session_dir is not None else None,
                "manifest": manifest_doc,
                "manifest_error": manifest_error,
                "files": session_files,
            },
            "summary": summary,
            "docker_inspect": docker_inspect,
            "host_probes": host_probes,
            "runtime_probe": runtime_probe,
            "ide_native_logs": ide_summary,
            "browser_evidence": dict(BROWSER_EVIDENCE_MANUAL_CONTRACT),
            "redaction": {"applied": True, "notice": REDACTION_NOTICE},
        },
        env_names=sensitive_env_names,
    )

    saved_snapshot_path: Path | None = None
    snapshot_save_error: str | None = None
    if session_dir is not None:
        candidate_snapshot = _select_snapshot_path(session_dir, stamp)
        try:
            _atomic_write_private_bytes(
                candidate_snapshot,
                (json.dumps(snapshot, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )
            saved_snapshot_path = candidate_snapshot
            snapshot["saved_snapshot_path"] = str(saved_snapshot_path)
        except (OSError, DiagnosticsError) as error:
            snapshot_save_error = str(error)
            snapshot["snapshot_save_error"] = redact_text(snapshot_save_error, env_names=sensitive_env_names)

    if export_requested:
        destination = _resolve_export_destination(
            export_path,
            session_id=effective_session_id,
            stamp=stamp,
        )
        export_info = export_diagnostics_bundle(
            destination,
            session_id=effective_session_id,
            session_dir=session_dir,
            snapshot=snapshot,
            ide_files=ide_files,
            ide_skipped=ide_skipped,
            include_ide_logs=include_ide_logs,
            current_snapshot_filename=saved_snapshot_path.name if saved_snapshot_path is not None else None,
            env_names=sensitive_env_names,
            now=now,
        )
        snapshot["export"] = export_info
        if saved_snapshot_path is not None:
            try:
                _atomic_write_private_bytes(
                    saved_snapshot_path,
                    (json.dumps(snapshot, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                )
            except (OSError, DiagnosticsError):
                pass

    return snapshot


def _format_probe_line(label: str, probe: Mapping[str, Any] | None) -> str:
    if not isinstance(probe, Mapping):
        return f"  {label}: unavailable"
    status = probe.get("status", "unknown")
    healthy = probe.get("healthy")
    duration = probe.get("duration_ms")
    timing = f" ({duration} ms)" if isinstance(duration, (int, float)) else ""
    if healthy is True:
        verdict = "PASS"
    elif healthy is False:
        verdict = "FAIL"
    else:
        verdict = "SKIP"
    detail = probe.get("error") or probe.get("reason") or probe.get("rfb_greeting") or probe.get("greeting") or ""
    suffix = f" — {detail}" if detail else ""
    return f"  {label}: {verdict} [{status}]{timing}{suffix}"


def render_diagnosis(snapshot: Mapping[str, Any]) -> str:
    """Render a concise human-readable diagnostic report."""

    project = snapshot["project"]
    session = snapshot["session"]
    summary = snapshot["summary"]
    docker_info = snapshot["docker_inspect"]
    runtime_probe = snapshot["runtime_probe"]
    host_probes = snapshot["host_probes"]
    ide_logs = snapshot["ide_native_logs"]
    browser = snapshot["browser_evidence"]

    lines = [
        f"Project: {project.get('creator')}/{project.get('slug')} (checkout: {project.get('checkout_name')})",
        f"Session: {session['id']} ({session['selection']}; context: {snapshot['context']})",
        f"Verdict: {summary['state']}",
    ]
    if session.get("log_directory"):
        lines.append(f"Session logs: {session['log_directory']}")
    if snapshot.get("saved_snapshot_path"):
        lines.append(f"Saved snapshot: {snapshot['saved_snapshot_path']}")

    lines.append("")
    lines.append("Container:")
    if docker_info.get("available"):
        oom = "yes" if docker_info.get("oom_killed") else "no"
        lines.append(
            f"  {docker_info.get('container')}: status={docker_info.get('status')}, "
            f"running={docker_info.get('running')}, pid={docker_info.get('pid')}, "
            f"exit_code={docker_info.get('exit_code')}, oom_killed={oom}"
        )
    else:
        lines.append(f"  unavailable ({docker_info.get('unavailable_reason')})")

    lines.append("")
    lines.append("Protocol probes (socket/TCP presence alone is not health):")
    if runtime_probe.get("available") and isinstance(runtime_probe.get("probes"), Mapping):
        probes = runtime_probe["probes"]
        lines.append(_format_probe_line("in-capsule RFB Unix greeting", probes.get("rfb_unix")))
        lines.append(_format_probe_line("in-capsule display HTTP (/vnc.html)", probes.get("display_http")))
        lines.append(_format_probe_line("in-capsule WebSocket->RFB bridge", probes.get("display_websocket_rfb")))
        lines.append(_format_probe_line("in-capsule web console HTTP", probes.get("console_http")))
    else:
        lines.append(f"  in-capsule probes: unavailable ({runtime_probe.get('unavailable_reason')})")

    if host_probes.get("available") and isinstance(host_probes.get("probes"), Mapping):
        hprobes = host_probes["probes"]
        lines.append(_format_probe_line("host-loopback display HTTP", hprobes.get("display_host_http")))
        lines.append(_format_probe_line("host-loopback web console HTTP", hprobes.get("console_host_http")))
    else:
        lines.append(f"  host-loopback probes: unavailable ({host_probes.get('unavailable_reason')})")

    if runtime_probe.get("available"):
        cgroup = runtime_probe.get("cgroup")
        if isinstance(cgroup, Mapping) and cgroup.get("available"):
            mem = cgroup.get("memory", {})
            pids = cgroup.get("pids", {})
            events = mem.get("events", {}) if isinstance(mem, Mapping) else {}
            cur_mem = logs.format_size(mem["current_bytes"]) if isinstance(mem.get("current_bytes"), int) else "unknown"
            max_mem = logs.format_size(mem["max_bytes"]) if isinstance(mem.get("max_bytes"), int) else "unlimited"
            lines.append("")
            lines.append(
                f"Cgroup v2: memory {cur_mem} / {max_mem} "
                f"(oom={events.get('oom', 0)}, oom_kill={events.get('oom_kill', 0)}); "
                f"pids {pids.get('current', '?')} / {pids.get('max') or 'unlimited'}"
            )
        procs = runtime_probe.get("processes")
        if isinstance(procs, Mapping) and procs.get("available"):
            components = procs.get("components", {})
            comp_summary = ", ".join(
                f"{role}={info.get('state')}(pid {info.get('pid')})"
                for role, info in sorted(components.items())
                if isinstance(info, Mapping)
            )
            workers = procs.get("novnc_workers", [])
            lines.append(
                f"Processes: {procs.get('total_processes')} total; "
                f"novnc_workers={len(workers) if isinstance(workers, list) else 0}; "
                f"zombies={len(procs.get('zombies', []))}; "
                f"components: {comp_summary or 'none'}"
            )

    if summary.get("issues"):
        lines.append("")
        lines.append("Findings:")
        for issue in summary["issues"]:
            lines.append(f"  - {issue}")

    lines.append("")
    ide_entries = ide_logs.get("entries", [])
    ide_status = "included in export" if ide_logs.get("included_in_export") else "excluded by default (use --include-ide-logs)"
    lines.append(f"IDE-native logs ({ide_status}):")
    if ide_entries:
        for entry in ide_entries:
            lines.append(
                f"  {entry['slot']}: {entry['path']} "
                f"({entry['file_count']} file(s), {logs.format_size(entry['total_bytes'])})"
            )
    else:
        lines.append("  none discovered")

    lines.append(
        f"Browser evidence: collected={browser.get('collected')} ({browser.get('mode')}; see {browser.get('guide')})"
    )

    export_info = snapshot.get("export")
    if isinstance(export_info, Mapping):
        lines.append(
            f"Export bundle: {export_info['archive_path']} "
            f"({logs.format_size(int(export_info['archive_bytes']))}, mode {export_info['mode']}, "
            f"{export_info['included_file_count']} file(s))"
        )
    return "\n".join(lines)
