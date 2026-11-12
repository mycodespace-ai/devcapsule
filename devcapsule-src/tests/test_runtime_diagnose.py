from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
from typing import Any, Callable, Iterator

import pytest

from devcapsule.container_runtime import entrypoint
from devcapsule.container_runtime.diagnose import (
    probe_http_get,
    probe_rfb_unix,
    probe_websocket_rfb,
    read_cgroup_v2,
    scan_processes,
)

pytestmark = pytest.mark.legacy

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


@contextmanager
def _unix_rfb_server(handler: Callable[[socket.socket], None]) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="dc-rfb-", dir="/tmp") as raw_dir:
        runtime_dir = Path(raw_dir)
        sock_path = runtime_dir / "display" / "rfb.sock"
        sock_path.parent.mkdir(parents=True, exist_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(sock_path))
        server.listen(4)
        stop_event = threading.Event()

        def _serve() -> None:
            server.settimeout(0.05)
            while not stop_event.is_set():
                try:
                    conn, _ = server.accept()
                except TimeoutError:
                    continue
                except OSError:
                    break
                with conn:
                    handler(conn)

        worker = threading.Thread(target=_serve, daemon=True)
        worker.start()
        try:
            yield sock_path
        finally:
            stop_event.set()
            server.close()
            worker.join(timeout=2.0)


@contextmanager
def _tcp_server(handler: Callable[[socket.socket], None]) -> Iterator[int]:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(8)
    port = int(server.getsockname()[1])
    stop_event = threading.Event()

    def _serve() -> None:
        server.settimeout(0.05)
        while not stop_event.is_set():
            try:
                conn, _ = server.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=_handle_one, args=(conn,), daemon=True).start()

    def _handle_one(conn: socket.socket) -> None:
        with conn:
            try:
                handler(conn)
            except OSError:
                pass

    worker = threading.Thread(target=_serve, daemon=True)
    worker.start()
    try:
        yield port
    finally:
        stop_event.set()
        server.close()
        worker.join(timeout=2.0)


def _read_http_request(conn: socket.socket) -> tuple[str, dict[str, str]]:
    conn.settimeout(1.0)
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
    head = bytes(data).split(b"\r\n\r\n", 1)[0].decode("iso-8859-1", errors="replace")
    lines = head.split("\r\n")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return (lines[0] if lines else ""), headers


def _ws_upgrade_response(ws_key: str) -> bytes:
    accept = base64.b64encode(hashlib.sha1((ws_key + _WS_GUID).encode("ascii")).digest()).decode("ascii")
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "Sec-WebSocket-Protocol: binary\r\n\r\n"
    ).encode("ascii")


def _write_proc_entry(
    proc_root: Path,
    *,
    pid: int,
    ppid: int,
    name: str,
    state: str,
    argv: list[str],
    uid: int = 1000,
    rss_kb: int = 4096,
) -> None:
    entry = proc_root / str(pid)
    entry.mkdir(parents=True, exist_ok=True)
    status = (
        f"Name:\t{name}\n"
        f"State:\t{state}\n"
        f"PPid:\t{ppid}\n"
        f"Uid:\t{uid}\t{uid}\t{uid}\t{uid}\n"
        "Threads:\t2\n"
        f"VmRSS:\t{rss_kb} kB\n"
    )
    (entry / "status").write_text(status, encoding="utf-8")
    cmdline = b"\x00".join(token.encode("utf-8") for token in argv) + (b"\x00" if argv else b"")
    (entry / "cmdline").write_bytes(cmdline)


def test_probe_rfb_unix_distinguishes_missing_silent_accept_and_valid_greeting(tmp_path: Path) -> None:
    missing = probe_rfb_unix(tmp_path / "absent.sock", timeout=0.2)
    assert missing["status"] == "socket-missing"
    assert missing["healthy"] is False
    assert missing["accepted"] is False

    regular = tmp_path / "regular-file"
    regular.write_text("not a socket\n", encoding="utf-8")
    not_sock = probe_rfb_unix(regular, timeout=0.2)
    assert not_sock["status"] == "not-a-socket"
    assert not_sock["healthy"] is False

    # Accepted Unix socket that hangs without sending an RFB greeting must fail within timeout.
    with _unix_rfb_server(lambda _conn: time.sleep(0.4)) as hung_sock:
        started = time.monotonic()
        stalled = probe_rfb_unix(hung_sock, timeout=0.15)
        elapsed = time.monotonic() - started
    assert elapsed < 1.5
    assert stalled["accepted"] is True
    assert stalled["healthy"] is False
    assert stalled["timed_out"] is True
    assert stalled["status"] == "greeting-timeout"

    with _unix_rfb_server(lambda conn: conn.sendall(b"NOT_RFB_000\n")) as bad_sock:
        bad = probe_rfb_unix(bad_sock, timeout=0.5)
    assert bad["accepted"] is True
    assert bad["healthy"] is False
    assert bad["status"] == "invalid-greeting"

    with _unix_rfb_server(lambda conn: conn.sendall(b"RFB 003.008\n")) as good_sock:
        good = probe_rfb_unix(good_sock, timeout=0.5)
    assert good["accepted"] is True
    assert good["healthy"] is True
    assert good["timed_out"] is False
    assert good["status"] == "ok"
    assert good["greeting"] == "RFB 003.008"


def test_probe_http_and_websocket_rfb_distinguish_http_200_from_stalled_or_healthy_bridge() -> None:
    secret_token = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    observed_requests: list[tuple[str, dict[str, str]]] = []
    mode = {"ws": "stall"}

    def _bridge_handler(conn: socket.socket) -> None:
        req_line, headers = _read_http_request(conn)
        observed_requests.append((req_line, headers))
        if req_line.startswith("GET /vnc.html "):
            body = b"<html>noVNC</html>"
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: "
                + str(len(body)).encode("ascii")
                + b"\r\nConnection: close\r\n\r\n"
                + body
            )
            return
        if req_line.startswith("GET /websockify?token="):
            ws_key = headers["sec-websocket-key"]
            if mode["ws"] == "reject":
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
                return
            conn.sendall(_ws_upgrade_response(ws_key))
            if mode["ws"] == "stall":
                time.sleep(0.4)
                return
            if mode["ws"] == "close":
                payload = struct.pack(">H", 1011) + b"upstream rfb closed"
                conn.sendall(bytes([0x88, len(payload)]) + payload)
                return
            greeting = b"RFB 003.008\n"
            conn.sendall(bytes([0x82, len(greeting)]) + greeting)

    with _tcp_server(_bridge_handler) as port:
        http_res = probe_http_get(
            "127.0.0.1",
            port,
            "/vnc.html",
            timeout=0.5,
            user_agent="devcapsule-diagnose/test",
        )
        assert http_res["healthy"] is True
        assert http_res["http_status"] == 200
        assert observed_requests[0][1]["user-agent"] == "devcapsule-diagnose/test"
        assert observed_requests[0][1]["x-devcapsule-diagnostic"] == "1"

        # HTTP 200 + WS 101 upgrade succeeds, yet Xvnc never delivers RFB greeting -> FAIL!
        started = time.monotonic()
        stalled_ws = probe_websocket_rfb(
            "127.0.0.1",
            port,
            token=secret_token,
            timeout=0.15,
            user_agent="devcapsule-diagnose/test",
        )
        assert time.monotonic() - started < 1.5
        assert stalled_ws["accepted"] is True
        assert stalled_ws["upgraded"] is True
        assert stalled_ws["healthy"] is False
        assert stalled_ws["timed_out"] is True
        assert stalled_ws["status"] == "rfb-greeting-timeout"
        assert secret_token not in json.dumps(stalled_ws)

        mode["ws"] = "close"
        closed_ws = probe_websocket_rfb(
            "127.0.0.1",
            port,
            token=secret_token,
            timeout=0.5,
            user_agent="devcapsule-diagnose/test",
        )
        assert closed_ws["healthy"] is False
        assert closed_ws["upgraded"] is True
        assert closed_ws["status"] == "websocket-closed"
        assert closed_ws["close_code"] == 1011
        assert secret_token not in json.dumps(closed_ws)

        mode["ws"] = "healthy"
        healthy_ws = probe_websocket_rfb(
            "127.0.0.1",
            port,
            token=secret_token,
            timeout=0.5,
            user_agent="devcapsule-diagnose/test",
        )
        assert healthy_ws["healthy"] is True
        assert healthy_ws["upgraded"] is True
        assert healthy_ws["status"] == "ok"
        assert healthy_ws["rfb_greeting"] == "RFB 003.008"
        assert secret_token not in json.dumps(healthy_ws)


def test_scan_processes_and_cgroup_v2_classify_workers_stopped_zombies_and_redact_secrets(
    tmp_path: Path,
) -> None:
    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    scope = cgroup_root / "capsule.scope"
    scope.mkdir(parents=True)

    _write_proc_entry(
        proc_root,
        pid=1,
        ppid=0,
        name="python3",
        state="S (sleeping)",
        argv=["/opt/devcapsule/bin/devcapsule.pex", "runtime", "/etc/devcapsule/runtime-plan.json"],
        uid=0,
    )
    (proc_root / "1" / "cgroup").write_text("0::/capsule.scope\n", encoding="utf-8")
    _write_proc_entry(
        proc_root,
        pid=20,
        ppid=1,
        name="Xvnc",
        state="T (stopped)",
        argv=["/usr/bin/Xvnc", ":99", "-rfbunixpath", "/tmp/devcapsule-runtime-1000/display/rfb.sock"],
    )
    _write_proc_entry(proc_root, pid=30, ppid=1, name="openbox", state="S (sleeping)", argv=["openbox"])
    _write_proc_entry(proc_root, pid=31, ppid=1, name="tint2", state="S (sleeping)", argv=["tint2"])
    _write_proc_entry(
        proc_root,
        pid=40,
        ppid=1,
        name="websockify",
        state="S (sleeping)",
        argv=["/usr/bin/python3", "/usr/bin/websockify", "127.0.0.1:6080"],
    )
    _write_proc_entry(
        proc_root,
        pid=41,
        ppid=40,
        name="websockify",
        state="S (sleeping)",
        argv=["/usr/bin/python3", "/usr/bin/websockify", "127.0.0.1:6080"],
    )
    _write_proc_entry(proc_root, pid=42, ppid=40, name="websockify", state="Z (zombie)", argv=[])
    _write_proc_entry(
        proc_root,
        pid=50,
        ppid=1,
        name="python3",
        state="S (sleeping)",
        argv=["/opt/devcapsule/webconsole/bin/python", "-m", "devcapsule_webconsole"],
    )
    _write_proc_entry(
        proc_root,
        pid=60,
        ppid=1,
        name="codium",
        state="R (running)",
        argv=[
            "/opt/codium/bin/codium",
            "--token",
            "live-secret-token-value",
            "CUSTOM_INLINE_KEY=top-secret-custom-val",
            "http://127.0.0.1:6080/vnc.html?token=0123456789abcdef0123456789abcdef",
        ],
    )

    (scope / "cpu.stat").write_text(
        "usage_usec 950000\nnr_periods 120\nnr_throttled 7\nthrottled_usec 44000\n",
        encoding="utf-8",
    )
    (scope / "cpu.max").write_text("200000 100000\n", encoding="utf-8")
    (scope / "memory.current").write_text(str(512 * 1024 * 1024) + "\n", encoding="utf-8")
    (scope / "memory.max").write_text(str(2048 * 1024 * 1024) + "\n", encoding="utf-8")
    (scope / "memory.peak").write_text(str(768 * 1024 * 1024) + "\n", encoding="utf-8")
    (scope / "memory.stat").write_text("anon 400000000\nfile 100000000\n", encoding="utf-8")
    (scope / "memory.events").write_text("low 0\nhigh 0\nmax 3\noom 2\noom_kill 1\n", encoding="utf-8")
    (scope / "pids.current").write_text("28\n", encoding="utf-8")
    (scope / "pids.max").write_text("4096\n", encoding="utf-8")
    (scope / "pids.events").write_text("max 0\n", encoding="utf-8")

    cgroup = read_cgroup_v2(cgroup_root, proc_root=proc_root)
    assert cgroup["available"] is True
    assert cgroup["memory"]["current_bytes"] == 512 * 1024 * 1024
    assert cgroup["memory"]["max_bytes"] == 2048 * 1024 * 1024
    assert cgroup["memory"]["events"]["oom_kill"] == 1
    assert cgroup["cpu"]["quota_usec"] == 200000
    assert cgroup["cpu"]["nr_throttled"] == 7
    assert cgroup["pids"]["current"] == 28

    procs = scan_processes(
        proc_root,
        self_pid=999999,
        component_id="codium",
        secrets_to_scrub=("extra-in-memory-secret",),
        env_names={"CUSTOM_INLINE_KEY"},
    )
    assert procs["available"] is True
    assert set(procs["components"]) >= {
        "supervisor",
        "xvnc",
        "window-manager",
        "panel",
        "novnc",
        "console",
        "codium",
    }
    assert procs["components"]["xvnc"]["state"] == "T"
    assert [item["pid"] for item in procs["stopped"]] == [20]
    assert [item["pid"] for item in procs["zombies"]] == [42]
    assert [item["pid"] for item in procs["novnc_workers"]] == [41]

    serialized = json.dumps(procs)
    assert "live-secret-token-value" not in serialized
    assert "top-secret-custom-val" not in serialized
    assert "0123456789abcdef0123456789abcdef" not in serialized


def test_entrypoint_diagnose_probe_cli_round_trip_with_zero_token_leakage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    display_token = "disp_token_99887766554433221100aabbccddeeff"
    console_token = "cons_token_ffeeddccbbaa00112233445566778899"
    display_token_file = tmp_path / "display.token"
    console_token_file = tmp_path / "console.token"
    display_token_file.write_text(display_token + "\n", encoding="utf-8")
    console_token_file.write_text(console_token + "\n", encoding="utf-8")

    proc_root = tmp_path / "proc"
    cgroup_root = tmp_path / "cgroup"
    cgroup_root.mkdir()
    _write_proc_entry(proc_root, pid=1, ppid=0, name="python3", state="S (sleeping)", argv=["devcapsule.pex"])
    net_dir = proc_root / "net"
    net_dir.mkdir(parents=True)
    # 0100007F:17C0 -> 127.0.0.1:6080 in LISTEN (0A)
    (net_dir / "tcp").write_text(
        "  sl  local_address rem_address   st tx_queue rx_queue\n"
        "   0: 0100007F:17C0 00000000:0000 0A 00000000:00000000\n",
        encoding="utf-8",
    )
    (net_dir / "unix").write_text(
        "Num RefCount Protocol Flags Type St Inode Path\n"
        "0000: 0002 0000 00010000 0001 01 12345 @/tmp/.X11-unix/X99\n",
        encoding="utf-8",
    )

    def _display_handler(conn: socket.socket) -> None:
        req_line, headers = _read_http_request(conn)
        if req_line.startswith("GET /vnc.html "):
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            return
        assert f"token={display_token}" in req_line
        conn.sendall(_ws_upgrade_response(headers["sec-websocket-key"]))
        greeting = b"RFB 003.008\n"
        conn.sendall(bytes([0x82, len(greeting)]) + greeting)

    def _console_handler(conn: socket.socket) -> None:
        _req_line, headers = _read_http_request(conn)
        if headers.get("x-devcapsule-token") == console_token:
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        else:
            conn.sendall(
                b"HTTP/1.1 403 Forbidden\r\nContent-Length: 52\r\nConnection: close\r\n\r\n"
                b"devcapsule web console: missing or invalid run token\n"
            )

    with (
        _unix_rfb_server(lambda conn: conn.sendall(b"RFB 003.008\n")) as rfb_sock,
        _tcp_server(_display_handler) as display_port,
        _tcp_server(_console_handler) as console_port,
    ):
        runtime_dir = rfb_sock.parent.parent
        plan_doc: dict[str, Any] = {
            "version": 1,
            "project_path": "/workspace/project",
            "home": str(tmp_path / "home"),
            "identity": {"uid": 1000, "gid": 1000, "user": "devcapsule"},
            "state_slots": [],
            "component": {
                "id": "codium",
                "adapter": "vscode",
                "configuration": {
                    "installation_path": "/opt/codium",
                    "launcher": "bin/codium",
                    "state_slot_mapping": {},
                },
            },
            "display": {
                "transport": "contained",
                "listen_address": "127.0.0.1",
                "port": display_port,
                "token_path": str(display_token_file),
            },
            "console": {
                "listen_address": "127.0.0.1",
                "port": console_port,
                "token_path": str(console_token_file),
            },
        }
        plan_path = tmp_path / "runtime-plan.json"
        plan_path.write_text(json.dumps(plan_doc), encoding="utf-8")

        exit_code = entrypoint.main(
            [
                "diagnose-probe",
                "--plan",
                str(plan_path),
                "--proc-root",
                str(proc_root),
                "--cgroup-root",
                str(cgroup_root),
                "--runtime-dir",
                str(runtime_dir),
                "--x-socket-dir",
                str(tmp_path / "x11"),
                "--probe-timeout",
                "0.5",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert display_token not in captured.out
    assert console_token not in captured.out

    payload = json.loads(captured.out)
    assert payload["plan"]["available"] is True
    assert payload["sockets"]["tcp_listeners"] == [{"address": "127.0.0.1", "family": "tcp", "port": 6080}]
    assert payload["sockets"]["abstract_x11_sockets"] == ["@/tmp/.X11-unix/X99"]
    assert payload["probes"]["rfb_unix"]["healthy"] is True
    assert payload["probes"]["display_http"]["healthy"] is True
    assert payload["probes"]["display_websocket_rfb"]["healthy"] is True
    assert payload["probes"]["console_http"]["healthy"] is True


@pytest.mark.parametrize("length", [12, 126, 65536])
def test_websocket_ping_and_split_frames_preserve_greeting(length: int) -> None:
    def handler(conn: socket.socket) -> None:
        _, headers = _read_http_request(conn)
        payload = b"RFB 003.008\n" + b"x" * (length - 12)
        frame_header = b"\x82" + (
            bytes([length]) if length < 126 else
            b"\x7e" + struct.pack(">H", length) if length < 65536 else
            b"\x7f" + struct.pack(">Q", length)
        )
        # Upgrade, ping and an empty binary message share the same TCP write.
        conn.sendall(_ws_upgrade_response(headers["sec-websocket-key"]) + b"\x89\x01p\x82\x00" + frame_header[:1])
        conn.sendall(frame_header[1:] + payload)
        conn.settimeout(1)
        pong = conn.recv(7)
        assert pong[:2] == b"\x8a\x81"

    with _tcp_server(handler) as port:
        result = probe_websocket_rfb("127.0.0.1", port, token="test-token", timeout=1)
    assert result["healthy"] is True
    assert result["rfb_greeting"] == "RFB 003.008"


def test_http_dribble_uses_total_deadline() -> None:
    def handler(conn: socket.socket) -> None:
        _read_http_request(conn)
        for byte in b"HTTP/1.1 200 OK\r\n\r\n":
            conn.sendall(bytes([byte]))
            time.sleep(0.03)

    with _tcp_server(handler) as port:
        started = time.monotonic()
        result = probe_http_get("127.0.0.1", port, "/", timeout=0.12)
        elapsed = time.monotonic() - started
    assert result["timed_out"] is True
    assert elapsed < 0.45


def test_rfb_eof_and_refused_are_distinct() -> None:
    with _unix_rfb_server(lambda conn: None) as path:
        result = probe_rfb_unix(path, timeout=0.2)
    assert result["status"] == "closed-before-greeting"
    assert result["accepted"] is True
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        path = Path(directory) / "rfb.sock"
        with socket.socket(socket.AF_UNIX) as sock:
            sock.bind(str(path))
        result = probe_rfb_unix(path, timeout=0.2)
    assert result["status"] == "connect-error"
    assert result["accepted"] is False


def test_proc_exit_and_parentheses_in_name(tmp_path: Path) -> None:
    _write_proc_entry(tmp_path, pid=5, ppid=1, name="(Web Content)", state="S (sleeping)", argv=["browser"])
    (tmp_path / "6").mkdir()  # Process exited before its status could be read.
    (tmp_path / "5" / "cmdline").unlink()  # Process exited after status was read.
    result = scan_processes(tmp_path, self_pid=99)
    assert result["total_processes"] == 1
    assert result["processes"][0]["name"] == "(Web Content)"
    assert result["processes"][0]["argv"] == []


@pytest.mark.parametrize("frame", [b"\xc2\x00", b"\x82\x80", b"\x09\x00", b"\x89\x7e", b"\x83\x00"])
def test_websocket_rejects_invalid_frames(frame: bytes) -> None:
    def handler(conn: socket.socket) -> None:
        _, headers = _read_http_request(conn)
        conn.sendall(_ws_upgrade_response(headers["sec-websocket-key"]) + frame)

    with _tcp_server(handler) as port:
        result = probe_websocket_rfb("127.0.0.1", port, token="test-token", timeout=0.3)
    assert result["status"] == "websocket-error"
    assert result["healthy"] is False
