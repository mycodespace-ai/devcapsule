"""Bounded in-capsule diagnostic probe for ``devcapsule project diagnose``.

Runs inside a capsule (via ``docker exec ... devcapsule.pex runtime
diagnose-probe`` from the host launcher, or directly in-process when
``project diagnose`` runs inside a capsule) using the Python standard library
alone. Every socket operation is bounded by a monotonic wall-clock deadline,
every HTTP/WebSocket probe identifies itself with a diagnostic ``User-Agent``
header, and run tokens read from ``/run/devcapsule-*-token`` stay in memory
and are scrubbed before any output is emitted.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

from .._redaction import redact_argv, redact_json_value, redact_text
from ..build_info import BuildInfoError, current_build_info
from .console import CONSOLE_PYTHON
from .contract import CONTAINED_DISPLAY_TRANSPORT, RuntimePlan, RuntimePlanError
from .display import UNIX_SOCKET_TABLE, X_SOCKET_DIRECTORY

DEFAULT_RUNTIME_PLAN_PATH = Path("/etc/devcapsule/runtime-plan.json")
DEFAULT_PROC_ROOT = Path("/proc")
DEFAULT_CGROUP_ROOT = Path("/sys/fs/cgroup")
DEFAULT_PROBE_TIMEOUT_SECONDS = 2.0
MAX_PROCESS_ENTRIES = 256
_MAX_HTTP_HEADER_BYTES = 16 * 1024
_MAX_WS_FRAME_BYTES = 64 * 1024
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_RFB_GREETING_RE = re.compile(rb"^RFB \d{3}\.\d{3}\n")


def default_user_agent() -> str:
    try:
        version = current_build_info().version
    except BuildInfoError:
        version = "unknown"
    return f"devcapsule-diagnose/{version}"


def _remaining_seconds(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("diagnostic probe timed out")
    return remaining


def _recv_until(sock: socket.socket, marker: bytes, *, deadline: float, limit: int) -> bytes:
    buffer = bytearray()
    while marker not in buffer:
        if len(buffer) >= limit:
            raise ValueError(f"response header exceeded {limit} bytes")
        sock.settimeout(_remaining_seconds(deadline))
        chunk = sock.recv(min(4096, limit - len(buffer)))
        if not chunk:
            break
        buffer.extend(chunk)
    return bytes(buffer)


def _recv_exact(sock: socket.socket, count: int, *, deadline: float, initial: bytes = b"") -> bytes:
    buffer = bytearray(initial[:count])
    while len(buffer) < count:
        sock.settimeout(_remaining_seconds(deadline))
        chunk = sock.recv(count - len(buffer))
        if not chunk:
            raise EOFError(f"socket closed after {len(buffer)} of {count} bytes")
        buffer.extend(chunk)
    return bytes(buffer)


def _sendall_bounded(sock: socket.socket, payload: bytes, *, deadline: float) -> None:
    view = memoryview(payload)
    sent_total = 0
    while sent_total < len(payload):
        sock.settimeout(_remaining_seconds(deadline))
        sent = sock.send(view[sent_total:])
        if sent <= 0:
            raise OSError("socket send made no progress")
        sent_total += sent


def _parse_http_head(head_bytes: bytes) -> tuple[int, str, dict[str, str]]:
    lines = head_bytes.decode("iso-8859-1", errors="replace").split("\r\n")
    status_line = lines[0] if lines else ""
    parts = status_line.split(" ", 2)
    if len(parts) < 2 or not parts[0].startswith("HTTP/") or not parts[1].isdigit():
        raise ValueError(f"malformed HTTP status line: {status_line[:80]!r}")
    code = int(parts[1])
    reason = parts[2] if len(parts) > 2 else ""
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
    return code, reason, headers


def probe_rfb_unix(socket_path: str | Path, *, timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Connect to the Unix RFB socket and read the 12-byte RFB server greeting."""

    target = Path(socket_path)
    started = time.monotonic()
    deadline = started + timeout
    try:
        info = target.lstat()
    except FileNotFoundError:
        return {
            "status": "socket-missing",
            "healthy": False,
            "accepted": False,
            "timed_out": False,
            "socket": str(target),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except OSError as error:
        return {
            "status": "socket-unreadable",
            "healthy": False,
            "accepted": False,
            "timed_out": False,
            "socket": str(target),
            "error": str(error),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    if not stat.S_ISSOCK(info.st_mode):
        return {
            "status": "not-a-socket",
            "healthy": False,
            "accepted": False,
            "timed_out": False,
            "socket": str(target),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    accepted = False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(_remaining_seconds(deadline))
            sock.connect(str(target))
            accepted = True
            greeting = _recv_exact(sock, 12, deadline=deadline)
    except TimeoutError:
        return {
            "status": "greeting-timeout" if accepted else "connect-timeout",
            "healthy": False,
            "accepted": accepted,
            "timed_out": True,
            "socket": str(target),
            "error": (
                "socket accepted connection, timed out waiting for 12-byte RFB greeting"
                if accepted
                else "timed out connecting to Unix RFB socket"
            ),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except EOFError as error:
        return {
            "status": "closed-before-greeting",
            "healthy": False,
            "accepted": True,
            "timed_out": False,
            "socket": str(target),
            "error": str(error),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except OSError as error:
        return {
            "status": "connect-error" if not accepted else "read-error",
            "healthy": False,
            "accepted": accepted,
            "timed_out": False,
            "socket": str(target),
            "error": str(error),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    if _RFB_GREETING_RE.match(greeting) is None:
        return {
            "status": "invalid-greeting",
            "healthy": False,
            "accepted": True,
            "timed_out": False,
            "socket": str(target),
            "greeting": greeting.decode("ascii", errors="replace").strip()[:32],
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    return {
        "status": "ok",
        "healthy": True,
        "accepted": True,
        "timed_out": False,
        "socket": str(target),
        "greeting": greeting.decode("ascii").strip(),
        "duration_ms": round((time.monotonic() - started) * 1000, 1),
    }


def probe_http_get(
    host: str,
    port: int,
    path: str,
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    user_agent: str | None = None,
    extra_headers: Mapping[str, str] | None = None,
    healthy_statuses: frozenset[int] = frozenset({200}),
    secrets_to_scrub: Sequence[str] = (),
) -> dict[str, Any]:
    """Perform a bounded, labeled HTTP/1.1 GET probe without following redirects."""

    agent = user_agent or default_user_agent()
    started = time.monotonic()
    deadline = started + timeout
    accepted = False
    host_header = f"[{host}]:{port}" if ":" in host and not host.startswith("[") else f"{host}:{port}"
    header_lines = [
        f"GET {path} HTTP/1.1",
        f"Host: {host_header}",
        f"User-Agent: {agent}",
        "X-DevCapsule-Diagnostic: 1",
        "Connection: close",
    ]
    if extra_headers:
        for name, value in extra_headers.items():
            header_lines.append(f"{name}: {value}")
    request_bytes = ("\r\n".join(header_lines) + "\r\n\r\n").encode("iso-8859-1")

    try:
        with socket.create_connection((host, port), timeout=_remaining_seconds(deadline)) as sock:
            accepted = True
            _sendall_bounded(sock, request_bytes, deadline=deadline)
            raw = _recv_until(sock, b"\r\n\r\n", deadline=deadline, limit=_MAX_HTTP_HEADER_BYTES)
            if b"\r\n\r\n" not in raw:
                return {
                    "status": "incomplete-http-response",
                    "healthy": False,
                    "accepted": True,
                    "timed_out": False,
                    "host": host,
                    "port": port,
                    "path": redact_text(path, secrets_to_scrub=secrets_to_scrub),
                    "error": "connection closed before HTTP headers completed",
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                }
            head_bytes, body_prefix = raw.split(b"\r\n\r\n", 1)
            if len(body_prefix) < 128:
                try:
                    sock.settimeout(min(0.2, _remaining_seconds(deadline)))
                    body_prefix += sock.recv(128 - len(body_prefix))
                except (TimeoutError, OSError):
                    pass
            code, reason, _headers = _parse_http_head(head_bytes)
    except TimeoutError:
        return {
            "status": "http-timeout" if accepted else "connect-timeout",
            "healthy": False,
            "accepted": accepted,
            "timed_out": True,
            "host": host,
            "port": port,
            "path": redact_text(path, secrets_to_scrub=secrets_to_scrub),
            "error": (
                "TCP connection accepted, timed out waiting for HTTP response"
                if accepted
                else "timed out connecting to TCP endpoint"
            ),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except (OSError, ValueError) as error:
        return {
            "status": "connect-error" if not accepted else "http-error",
            "healthy": False,
            "accepted": accepted,
            "timed_out": False,
            "host": host,
            "port": port,
            "path": redact_text(path, secrets_to_scrub=secrets_to_scrub),
            "error": redact_text(str(error), secrets_to_scrub=secrets_to_scrub),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    healthy = code in healthy_statuses
    result: dict[str, Any] = {
        "status": "ok" if healthy else f"http-{code}",
        "healthy": healthy,
        "accepted": True,
        "timed_out": False,
        "host": host,
        "port": port,
        "path": redact_text(path, secrets_to_scrub=secrets_to_scrub),
        "http_status": code,
        "http_reason": redact_text(reason, secrets_to_scrub=secrets_to_scrub),
        "duration_ms": round((time.monotonic() - started) * 1000, 1),
    }
    if b"devcapsule web console: missing or invalid run token" in body_prefix:
        result["token_gate_active"] = True
    return result


def _read_ws_frame(sock: socket.socket, *, deadline: float, buffered: bytearray) -> tuple[int, bytes]:
    """Read one frame, preserving bytes already received from later frames."""

    def take(count: int) -> bytes:
        initial = bytes(buffered[:count])
        del buffered[:count]
        return _recv_exact(sock, count, deadline=deadline, initial=initial)

    _remaining_seconds(deadline)
    header = take(2)
    opcode = header[0] & 0x0F
    if header[0] & 0x70 or header[1] & 0x80:
        raise ValueError("reserved bits or masked server WebSocket frame")
    length = header[1] & 0x7F
    if opcode >= 8 and (not header[0] & 0x80 or length > 125):
        raise ValueError("invalid WebSocket control frame")
    if length == 126:
        length = struct.unpack(">H", take(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", take(8))[0]
    if length > _MAX_WS_FRAME_BYTES:
        raise ValueError(f"WebSocket frame length {length} exceeds diagnostic limit")
    return opcode, take(length)


def _read_ws_greeting(sock: socket.socket, *, deadline: float, initial: bytes) -> tuple[int, bytes]:
    buffered = bytearray(initial)
    greeting = bytearray()
    while len(greeting) < 12:
        opcode, payload = _read_ws_frame(sock, deadline=deadline, buffered=buffered)
        if opcode == 0x9:
            # Client pong frames must be masked, including an empty pong.
            mask = os.urandom(4)
            masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            _sendall_bounded(sock, bytes([0x8A, 0x80 | len(payload)]) + mask + masked, deadline=deadline)
            continue
        if opcode == 0xA:
            continue
        if opcode == 0x8:
            return opcode, payload
        if opcode not in (0x0, 0x1, 0x2):
            raise ValueError(f"unexpected WebSocket opcode {opcode}")
        greeting.extend(payload[:12 - len(greeting)])
    return 0x2, bytes(greeting)


def _send_ws_close_best_effort(sock: socket.socket, *, deadline: float) -> None:
    # Masked client Close frame with normal-closure code 1000 (0x03e8) and zero mask.
    try:
        remaining = deadline - time.monotonic()
        if remaining > 0.02:
            sock.settimeout(min(0.2, remaining))
            sock.sendall(b"\x88\x82\x00\x00\x00\x00\x03\xe8")
    except OSError:
        pass


def probe_websocket_rfb(
    host: str,
    port: int,
    *,
    token: str,
    timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Upgrade ``/websockify`` with the in-memory run token and verify the RFB greeting frame."""

    agent = user_agent or default_user_agent()
    started = time.monotonic()
    deadline = started + timeout
    accepted = False
    upgraded = False
    ws_key = base64.b64encode(os.urandom(16)).decode("ascii")
    expected_accept = base64.b64encode(
        hashlib.sha1((ws_key + _WS_GUID).encode("ascii")).digest()
    ).decode("ascii")
    host_header = f"[{host}]:{port}" if ":" in host and not host.startswith("[") else f"{host}:{port}"
    request = (
        f"GET /websockify?token={token} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        f"User-Agent: {agent}\r\n"
        "X-DevCapsule-Diagnostic: 1\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {ws_key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Sec-WebSocket-Protocol: binary\r\n"
        "\r\n"
    ).encode("iso-8859-1")

    try:
        with socket.create_connection((host, port), timeout=_remaining_seconds(deadline)) as sock:
            accepted = True
            _sendall_bounded(sock, request, deadline=deadline)
            raw = _recv_until(sock, b"\r\n\r\n", deadline=deadline, limit=_MAX_HTTP_HEADER_BYTES)
            if b"\r\n\r\n" not in raw:
                return {
                    "status": "closed-before-upgrade",
                    "healthy": False,
                    "accepted": True,
                    "upgraded": False,
                    "timed_out": False,
                    "host": host,
                    "port": port,
                    "path": "/websockify?token=<redacted>",
                    "error": "connection closed before WebSocket upgrade response",
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                }
            head_bytes, remainder = raw.split(b"\r\n\r\n", 1)
            code, reason, headers = _parse_http_head(head_bytes)
            if code != 101:
                return {
                    "status": f"upgrade-rejected-{code}",
                    "healthy": False,
                    "accepted": True,
                    "upgraded": False,
                    "timed_out": False,
                    "host": host,
                    "port": port,
                    "path": "/websockify?token=<redacted>",
                    "http_status": code,
                    "http_reason": redact_text(reason, secrets_to_scrub=(token,)),
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                }
            if headers.get("sec-websocket-accept") != expected_accept:
                return {
                    "status": "invalid-websocket-accept",
                    "healthy": False,
                    "accepted": True,
                    "upgraded": False,
                    "timed_out": False,
                    "host": host,
                    "port": port,
                    "path": "/websockify?token=<redacted>",
                    "http_status": code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                }
            upgraded = True
            opcode, payload = _read_ws_greeting(sock, deadline=deadline, initial=remainder)
            _send_ws_close_best_effort(sock, deadline=deadline)
    except TimeoutError:
        stage = (
            "rfb-greeting-timeout"
            if upgraded
            else ("upgrade-timeout" if accepted else "connect-timeout")
        )
        detail = (
            "WebSocket upgraded (101), timed out waiting for RFB greeting frame"
            if upgraded
            else (
                "TCP connection accepted, timed out waiting for WebSocket 101 upgrade"
                if accepted
                else "timed out connecting to WebSocket bridge"
            )
        )
        return {
            "status": stage,
            "healthy": False,
            "accepted": accepted,
            "upgraded": upgraded,
            "timed_out": True,
            "host": host,
            "port": port,
            "path": "/websockify?token=<redacted>",
            "error": detail,
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except EOFError as error:
        return {
            "status": "closed-after-upgrade" if upgraded else "closed-before-upgrade",
            "healthy": False,
            "accepted": accepted,
            "upgraded": upgraded,
            "timed_out": False,
            "host": host,
            "port": port,
            "path": "/websockify?token=<redacted>",
            "error": redact_text(str(error), secrets_to_scrub=(token,)),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except (OSError, ValueError) as error:
        return {
            "status": "connect-error" if not accepted else "websocket-error",
            "healthy": False,
            "accepted": accepted,
            "upgraded": upgraded,
            "timed_out": False,
            "host": host,
            "port": port,
            "path": "/websockify?token=<redacted>",
            "error": redact_text(str(error), secrets_to_scrub=(token,)),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    if opcode == 0x8:
        close_code = struct.unpack(">H", payload[:2])[0] if len(payload) >= 2 else None
        close_reason = payload[2:].decode("utf-8", errors="replace") if len(payload) > 2 else ""
        return {
            "status": "websocket-closed",
            "healthy": False,
            "accepted": True,
            "upgraded": True,
            "timed_out": False,
            "host": host,
            "port": port,
            "path": "/websockify?token=<redacted>",
            "http_status": 101,
            "close_code": close_code,
            "close_reason": redact_text(close_reason, secrets_to_scrub=(token,)),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    if opcode not in (0x1, 0x2) or _RFB_GREETING_RE.match(payload) is None:
        return {
            "status": "invalid-rfb-frame",
            "healthy": False,
            "accepted": True,
            "upgraded": True,
            "timed_out": False,
            "host": host,
            "port": port,
            "path": "/websockify?token=<redacted>",
            "http_status": 101,
            "opcode": opcode,
            "frame_preview": redact_text(
                payload[:24].decode("ascii", errors="replace").strip(),
                secrets_to_scrub=(token,),
            ),
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        }

    return {
        "status": "ok",
        "healthy": True,
        "accepted": True,
        "upgraded": True,
        "timed_out": False,
        "host": host,
        "port": port,
        "path": "/websockify?token=<redacted>",
        "http_status": 101,
        "rfb_greeting": payload[:12].decode("ascii").strip(),
        "duration_ms": round((time.monotonic() - started) * 1000, 1),
    }


def _parse_int_or_none(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw or raw == "max":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_key_values(path: Path) -> dict[str, int]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, int] = {}
    for line in lines:
        parts = line.split()
        if len(parts) == 2:
            try:
                values[parts[0]] = int(parts[1])
            except ValueError:
                continue
    return values


def _parse_cpu_max(path: Path) -> tuple[int | None, int | None]:
    try:
        parts = path.read_text(encoding="utf-8").split()
    except OSError:
        return None, None
    if len(parts) != 2:
        return None, None
    try:
        period = int(parts[1])
        quota = None if parts[0] == "max" else int(parts[0])
    except ValueError:
        return None, None
    return quota, period


def _select_cgroup_directory(cgroup_root: Path, proc_root: Path) -> Path:
    try:
        entries = (proc_root / "1" / "cgroup").read_text(encoding="utf-8").splitlines()
    except OSError:
        return cgroup_root
    for entry in entries:
        if entry.startswith("0::"):
            relative = entry[3:].strip().lstrip("/")
            if relative:
                candidate = cgroup_root / relative
                if candidate.is_dir():
                    return candidate
    return cgroup_root


def read_cgroup_v2(
    cgroup_root: Path = DEFAULT_CGROUP_ROOT,
    *,
    proc_root: Path = DEFAULT_PROC_ROOT,
) -> dict[str, Any]:
    """Read cgroup v2 resource usage, limits, throttling, and OOM counters."""

    target = _select_cgroup_directory(cgroup_root, proc_root)
    try:
        available = (target / "cpu.stat").is_file() and any(
            (target / name).is_file() for name in ("cpu.max", "memory.current", "pids.current")
        )
    except OSError as error:
        return {"available": False, "unavailable_reason": str(error)}
    if not available:
        return {
            "available": False,
            "unavailable_reason": f"no capsule cgroup v2 controller files at {target}",
        }

    cpu_stat = _parse_key_values(target / "cpu.stat")
    quota_usec, period_usec = _parse_cpu_max(target / "cpu.max")
    memory_stat = _parse_key_values(target / "memory.stat")
    memory_events = _parse_key_values(target / "memory.events")
    pids_events = _parse_key_values(target / "pids.events")
    memory_current = _parse_int_or_none(target / "memory.current")
    memory_max = _parse_int_or_none(target / "memory.max")
    memory_peak = _parse_int_or_none(target / "memory.peak")
    pids_current = _parse_int_or_none(target / "pids.current")
    pids_max = _parse_int_or_none(target / "pids.max")

    return {
        "available": True,
        "path": str(target),
        "memory": {
            "current_bytes": memory_current,
            "max_bytes": memory_max,
            "peak_bytes": memory_peak,
            "anon_bytes": memory_stat.get("anon"),
            "file_bytes": memory_stat.get("file"),
            "events": {
                key: memory_events[key]
                for key in ("low", "high", "max", "oom", "oom_kill", "oom_group_kill")
                if key in memory_events
            },
        },
        "cpu": {
            "usage_usec": cpu_stat.get("usage_usec"),
            "quota_usec": quota_usec,
            "period_usec": period_usec,
            "nr_periods": cpu_stat.get("nr_periods"),
            "nr_throttled": cpu_stat.get("nr_throttled"),
            "throttled_usec": cpu_stat.get("throttled_usec"),
        },
        "pids": {
            "current": pids_current,
            "max": pids_max,
            "events": {key: pids_events[key] for key in ("max",) if key in pids_events},
        },
    }


def _read_proc_entry(pid_dir: Path) -> dict[str, Any] | None:
    try:
        status_text = (pid_dir / "status").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        raw_cmdline = (pid_dir / "cmdline").read_bytes()
    except OSError:
        raw_cmdline = b""

    fields: dict[str, str] = {}
    for line in status_text.splitlines():
        if ":\t" in line:
            key, value = line.split(":\t", 1)
            fields[key] = value.strip()

    try:
        pid = int(pid_dir.name)
        ppid = int(fields.get("PPid", "0"))
    except ValueError:
        return None
    uid_parts = fields.get("Uid", "").split()
    uid = int(uid_parts[0]) if uid_parts and uid_parts[0].isdigit() else None
    threads_text = fields.get("Threads", "")
    threads = int(threads_text) if threads_text.isdigit() else None
    state_raw = fields.get("State", "")
    state_code = state_raw[:1] if state_raw else "?"
    rss_bytes: int | None = None
    rss_raw = fields.get("VmRSS", "")
    if rss_raw:
        rss_parts = rss_raw.split()
        if rss_parts and rss_parts[0].isdigit():
            rss_bytes = int(rss_parts[0]) * 1024

    argv = [part.decode("utf-8", errors="replace") for part in raw_cmdline.split(b"\x00") if part]
    return {
        "pid": pid,
        "ppid": ppid,
        "uid": uid,
        "name": fields.get("Name", ""),
        "state": state_code,
        "state_detail": state_raw,
        "threads": threads,
        "rss_bytes": rss_bytes,
        "argv": argv,
    }


def _classify_base_role(entry: Mapping[str, Any], *, component_id: str | None) -> str:
    pid = entry["pid"]
    argv: list[str] = list(entry["argv"])
    basenames = [os.path.basename(token) for token in argv[:5]]
    if pid == 1:
        return "supervisor"
    if "Xvnc" in basenames[:2]:
        return "xvnc"
    if "openbox" in basenames[:2]:
        return "window-manager"
    if "tint2" in basenames[:2]:
        return "panel"
    if "websockify" in basenames:
        return "novnc"
    if "devcapsule_webconsole" in argv:
        return "console"
    if entry["ppid"] == 1:
        return component_id or "foreground"
    return "other"


def scan_processes(
    proc_root: Path = DEFAULT_PROC_ROOT,
    *,
    self_pid: int | None = None,
    component_id: str | None = None,
    secrets_to_scrub: Sequence[str] = (),
    env_names: set[str] | None = None,
) -> dict[str, Any]:
    """Scan ``/proc`` for supervisor, display, bridge worker, console, and IDE state."""

    probe_pid = os.getpid() if self_pid is None else self_pid
    try:
        entries_raw = sorted(
            (entry for entry in proc_root.iterdir() if entry.name.isdigit()),
            key=lambda item: int(item.name),
        )
    except OSError as error:
        return {"available": False, "unavailable_reason": str(error)}

    raw_processes: list[dict[str, Any]] = []
    for pid_dir in entries_raw:
        parsed = _read_proc_entry(pid_dir)
        if parsed is None or parsed["pid"] == probe_pid:
            continue
        raw_processes.append(parsed)

    base_roles = {item["pid"]: _classify_base_role(item, component_id=component_id) for item in raw_processes}
    novnc_pids = {pid for pid, role in base_roles.items() if role == "novnc"}
    console_pids = {pid for pid, role in base_roles.items() if role == "console"}

    state_counts: dict[str, int] = {}
    zombies: list[dict[str, Any]] = []
    stopped: list[dict[str, Any]] = []
    novnc_workers: list[dict[str, Any]] = []
    components: dict[str, dict[str, Any]] = {}
    processes: list[dict[str, Any]] = []

    for item in raw_processes:
        pid = item["pid"]
        ppid = item["ppid"]
        role = base_roles[pid]
        if role == "novnc" and ppid in novnc_pids:
            role = "novnc-worker"
        elif role == "console" and ppid in console_pids:
            role = "console-worker"

        state = item["state"]
        state_counts[state] = state_counts.get(state, 0) + 1
        redacted = {
            "pid": pid,
            "ppid": ppid,
            "uid": item["uid"],
            "role": role,
            "name": item["name"],
            "state": state,
            "state_detail": item["state_detail"],
            "threads": item["threads"],
            "rss_bytes": item["rss_bytes"],
            "argv": redact_argv(item["argv"], secrets_to_scrub=secrets_to_scrub, env_names=env_names),
        }
        if state == "Z":
            zombies.append({"pid": pid, "ppid": ppid, "name": item["name"], "role": role})
        if state in ("T", "t"):
            stopped.append({"pid": pid, "ppid": ppid, "name": item["name"], "role": role})
        if role == "novnc-worker":
            novnc_workers.append(redacted)
        elif role != "other" and role not in components:
            components[role] = redacted
        if len(processes) < MAX_PROCESS_ENTRIES:
            processes.append(redacted)

    return {
        "available": True,
        "probe_pid": probe_pid,
        "total_processes": len(raw_processes),
        "truncated": len(raw_processes) > MAX_PROCESS_ENTRIES,
        "state_counts": state_counts,
        "components": components,
        "novnc_workers": novnc_workers,
        "zombies": zombies,
        "stopped": stopped,
        "processes": processes,
    }


def _socket_entry(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"path": str(path), "exists": False, "is_socket": False}
    except OSError as error:
        return {"path": str(path), "exists": False, "is_socket": False, "error": str(error)}
    return {
        "path": str(path),
        "exists": True,
        "is_socket": stat.S_ISSOCK(info.st_mode),
        "mode": f"0{stat.S_IMODE(info.st_mode):03o}",
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def _parse_tcp_listeners(proc_root: Path) -> list[dict[str, Any]]:
    listeners: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for table_name, ipv6 in (("net/tcp", False), ("net/tcp6", True)):
        try:
            lines = (proc_root / table_name).read_text(encoding="utf-8", errors="replace").splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            parts = line.split()
            if len(parts) < 4 or parts[3] != "0A":
                continue
            local_hex, _, port_hex = parts[1].partition(":")
            try:
                port = int(port_hex, 16)
                raw = bytes.fromhex(local_hex)
                if not ipv6 and len(raw) == 4:
                    address = socket.inet_ntop(socket.AF_INET, raw[::-1])
                elif ipv6 and len(raw) == 16:
                    words = b"".join(raw[idx : idx + 4][::-1] for idx in range(0, 16, 4))
                    address = socket.inet_ntop(socket.AF_INET6, words)
                else:
                    address = local_hex
            except (ValueError, OSError):
                continue
            key = (address, port)
            if key not in seen:
                seen.add(key)
                listeners.append({"address": address, "port": port, "family": "tcp6" if ipv6 else "tcp"})
    listeners.sort(key=lambda item: (int(item["port"]), str(item["address"])))
    return listeners


def inspect_sockets(
    *,
    runtime_dir: Path | None,
    proc_root: Path = DEFAULT_PROC_ROOT,
    x_socket_dir: Path = Path(X_SOCKET_DIRECTORY),
    unix_socket_table: Path | None = None,
) -> dict[str, Any]:
    """Inspect X11 sockets, the RFB Unix socket, and TCP listeners (not end-to-end health)."""

    x_sockets: list[dict[str, Any]] = []
    try:
        if x_socket_dir.is_dir():
            for child in sorted(x_socket_dir.iterdir(), key=lambda item: item.name):
                if child.name.startswith("X"):
                    x_sockets.append(_socket_entry(child))
    except OSError:
        pass

    unix_table = (proc_root / "net" / "unix") if unix_socket_table is None else unix_socket_table
    abstract_x: list[str] = []
    try:
        unix_text = unix_table.read_text(encoding="utf-8", errors="replace")
        abstract_x = sorted(set(re.findall(r"@/tmp/\.X11-unix/X\d+", unix_text)))
    except OSError:
        pass

    rfb_socket = _socket_entry(runtime_dir / "display" / "rfb.sock") if runtime_dir is not None else None
    return {
        "note": "Socket files and TCP listeners show binding only, not end-to-end protocol responsiveness.",
        "x11_sockets": x_sockets,
        "abstract_x11_sockets": abstract_x,
        "rfb_socket": rfb_socket,
        "tcp_listeners": _parse_tcp_listeners(proc_root),
    }


def _read_secret_token(path: str) -> tuple[str | None, str | None]:
    try:
        token = Path(path).read_text(encoding="utf-8").strip()
    except OSError as error:
        return None, f"cannot read token file {path}: {error.strerror or error}"
    if not token or any(ch.isspace() for ch in token):
        return None, f"token file {path} is empty or malformed"
    return token, None


def _loopback_for_listen(listen_address: str) -> str:
    if listen_address == "0.0.0.0":
        return "127.0.0.1"
    if listen_address == "::":
        return "::1"
    return listen_address


def collect_runtime_probe(
    *,
    plan_path: Path = DEFAULT_RUNTIME_PLAN_PATH,
    probe_timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    proc_root: Path = DEFAULT_PROC_ROOT,
    cgroup_root: Path = DEFAULT_CGROUP_ROOT,
    x_socket_dir: Path = Path(X_SOCKET_DIRECTORY),
    runtime_dir: Path | None = None,
    user_agent: str | None = None,
    extra_env_names: Iterable[str] = (),
) -> dict[str, Any]:
    """Collect the complete bounded in-capsule diagnostic probe document."""

    agent = user_agent or default_user_agent()
    env_names = {name for name in extra_env_names if name}
    secrets_in_memory: list[str] = []

    plan: RuntimePlan | None = None
    plan_summary: dict[str, Any]
    try:
        plan = RuntimePlan.from_file(plan_path)
        plan_summary = {
            "available": True,
            "path": str(plan_path),
            "component": plan.component.id,
            "adapter": plan.component.adapter,
            "display_transport": plan.display_transport(),
            "console_configured": plan.console is not None,
        }
    except RuntimePlanError as error:
        plan_summary = {
            "available": False,
            "path": str(plan_path),
            "unavailable_reason": str(error),
        }

    uid = plan.identity.uid if plan is not None else os.getuid()
    effective_runtime_dir = Path(f"/tmp/devcapsule-runtime-{uid}") if runtime_dir is None else runtime_dir
    component_id = plan.component.id if plan is not None else None

    probes: dict[str, Any] = {}
    if plan is not None and plan.display is not None and plan.display.transport == CONTAINED_DISPLAY_TRANSPORT:
        rfb_path = effective_runtime_dir / "display" / "rfb.sock"
        probes["rfb_unix"] = probe_rfb_unix(rfb_path, timeout=probe_timeout)
        display_host = _loopback_for_listen(plan.display.listen_address)
        probes["display_http"] = probe_http_get(
            display_host,
            plan.display.port,
            "/vnc.html",
            timeout=probe_timeout,
            user_agent=agent,
        )
        display_token, token_error = _read_secret_token(plan.display.token_path)
        if display_token is not None:
            secrets_in_memory.append(display_token)
            probes["display_websocket_rfb"] = probe_websocket_rfb(
                display_host,
                plan.display.port,
                token=display_token,
                timeout=probe_timeout,
                user_agent=agent,
            )
        else:
            probes["display_websocket_rfb"] = {
                "status": "token-unavailable",
                "healthy": False,
                "accepted": False,
                "upgraded": False,
                "timed_out": False,
                "error": token_error,
            }
    else:
        transport = plan.display_transport() if plan is not None else "unknown"
        for name in ("rfb_unix", "display_http", "display_websocket_rfb"):
            probes[name] = {
                "status": "not-applicable",
                "healthy": None,
                "reason": f"display transport is {transport}",
            }

    if plan is not None and plan.console is not None:
        if proc_root == DEFAULT_PROC_ROOT and not Path(CONSOLE_PYTHON).is_file():
            probes["console_http"] = {
                "status": "not-installed-in-base",
                "healthy": None,
                "reason": f"web console interpreter absent at {CONSOLE_PYTHON}",
            }
        else:
            console_host = _loopback_for_listen(plan.console.listen_address)
            console_token, console_token_error = _read_secret_token(plan.console.token_path)
            if console_token is not None:
                secrets_in_memory.append(console_token)
                probes["console_http"] = probe_http_get(
                    console_host,
                    plan.console.port,
                    "/",
                    timeout=probe_timeout,
                    user_agent=agent,
                    extra_headers={"X-DevCapsule-Token": console_token},
                    healthy_statuses=frozenset({200}),
                    secrets_to_scrub=(console_token,),
                )
            else:
                probes["console_http"] = {
                    "status": "token-unavailable",
                    "healthy": False,
                    "accepted": False,
                    "timed_out": False,
                    "error": console_token_error,
                }
    else:
        probes["console_http"] = {
            "status": "not-configured",
            "healthy": None,
            "reason": "no web console declared in runtime plan",
        }

    document: dict[str, Any] = {
        "schema_version": 1,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_agent": agent,
        "plan": plan_summary,
        "cgroup": read_cgroup_v2(cgroup_root, proc_root=proc_root),
        "processes": scan_processes(
            proc_root,
            component_id=component_id,
            secrets_to_scrub=secrets_in_memory,
            env_names=env_names,
        ),
        "sockets": inspect_sockets(
            runtime_dir=effective_runtime_dir,
            proc_root=proc_root,
            x_socket_dir=x_socket_dir,
            unix_socket_table=(proc_root / "net" / "unix") if proc_root != DEFAULT_PROC_ROOT else Path(UNIX_SOCKET_TABLE),
        ),
        "probes": probes,
    }
    sanitized: dict[str, Any] = redact_json_value(
        document,
        secrets_to_scrub=secrets_in_memory,
        env_names=env_names,
    )
    return sanitized


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="devcapsule runtime diagnose-probe",
        description="Collect bounded in-capsule process, cgroup, socket, and protocol probe evidence.",
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_RUNTIME_PLAN_PATH)
    parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT_SECONDS)
    parser.add_argument("--proc-root", type=Path, default=DEFAULT_PROC_ROOT)
    parser.add_argument("--cgroup-root", type=Path, default=DEFAULT_CGROUP_ROOT)
    parser.add_argument("--runtime-dir", type=Path, default=None)
    parser.add_argument("--x-socket-dir", type=Path, default=Path(X_SOCKET_DIRECTORY))
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--redact-env", action="append", default=[], dest="redact_env")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.probe_timeout <= 0:
        print("devcapsule runtime diagnose-probe: --probe-timeout must be positive", file=sys.stderr)
        return 2
    report = collect_runtime_probe(
        plan_path=args.plan,
        probe_timeout=args.probe_timeout,
        proc_root=args.proc_root,
        cgroup_root=args.cgroup_root,
        x_socket_dir=args.x_socket_dir,
        runtime_dir=args.runtime_dir,
        user_agent=args.user_agent,
        extra_env_names=args.redact_env,
    )
    print(json.dumps(report, sort_keys=True))
    return 0
