"""Narrow URL-only bridge from a DevCapsule to the physical host desktop."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time
from typing import Any
from urllib.parse import urlsplit

from devcapsule.host_daemon import in_container
from devcapsule.platforms import HostOs


HOST_OPEN_SOCKET_ENV = "DEVCAPSULE_HOST_OPEN_SOCKET"
HOST_OPEN_SOCKET_DESTINATION = Path("/run/devcapsule-host-open.sock")
HOST_OPEN_BROWSER = "/opt/devcapsule/bin/devcapsule.pex host-open"
HOST_OPEN_INTEGRATION = "browser-open"
MAX_URL_BYTES = 16 * 1024
MAX_FRAME_BYTES = MAX_URL_BYTES + 1024
MAX_RESPONSE_BYTES = 4096
DEFAULT_TIMEOUT_SECONDS = 10.0
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60.0
_UNIX_PATH_LIMIT = 100
HOST_OPEN_UNAVAILABLE_ON_MACOS = (
    "Warning: host-browser is unavailable on macOS: Docker Desktop does not carry the "
    "host's Unix sockets into a capsule. Links open in the capsule's own browser instead."
)


class HostOpenError(Exception):
    """The host URL bridge is unavailable or rejected a request."""


def validate_host_url(value: str) -> str:
    """Return a URL that is safe for the bridge's deliberately small protocol."""

    if not value or len(value.encode("utf-8")) > MAX_URL_BYTES:
        raise HostOpenError("URL is empty or exceeds the host-open size limit")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise HostOpenError("URL contains a control character")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise HostOpenError("host-open accepts only absolute http:// or https:// URLs")
    return value


def open_host_url(
    url: str,
    *,
    socket_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Ask the owning physical-host broker to open one validated URL."""

    selected_url = validate_host_url(url)
    env = os.environ if environ is None else environ
    path = socket_path
    if path is None:
        configured = env.get(HOST_OPEN_SOCKET_ENV)
        if not configured:
            raise HostOpenError("this capsule has no authorized host-browser bridge")
        path = Path(configured)
    if not path.is_absolute() or ".." in path.parts:
        raise HostOpenError("host-browser socket path is not absolute and normalized")
    if not _is_socket(path):
        raise HostOpenError("authorized host-browser socket is absent")

    request = _encode_frame({"schema_version": 1, "url": selected_url})
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout)
            connection.connect(str(path))
            connection.sendall(request)
            connection.shutdown(socket.SHUT_WR)
            response = _read_frame(connection, MAX_RESPONSE_BYTES)
    except (OSError, TimeoutError) as exc:
        raise HostOpenError("host-browser broker is unavailable") from exc
    result = _decode_mapping(response, "host-browser response")
    if result.get("ok") is not True:
        error = result.get("error")
        detail = error if isinstance(error, str) and error else "request rejected"
        raise HostOpenError(f"host-browser broker rejected the request: {detail}")


class HostOpenBroker:
    """Small same-user Unix-socket server that invokes the host desktop opener."""

    def __init__(
        self,
        socket_path: Path,
        *,
        environ: Mapping[str, str] | None = None,
        opener: Sequence[str] = ("xdg-open",),
        opener_timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.socket_path = socket_path
        self.environ = dict(os.environ if environ is None else environ)
        self.opener = tuple(opener)
        self.opener_timeout = opener_timeout
        self._server: socket.socket | None = None
        self._thread: Thread | None = None
        self._stop = Event()
        self._requests: deque[float] = deque()
        self._bound = False

    def __enter__(self) -> HostOpenBroker:
        if not self.opener:
            raise HostOpenError("host-browser opener command is empty")
        if self.socket_path.exists() or self.socket_path.is_symlink():
            raise HostOpenError("host-browser socket path already exists")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(self.socket_path))
            self._bound = True
            self.socket_path.chmod(0o600)
            server.listen(8)
            server.settimeout(0.2)
        except OSError as exc:
            server.close()
            self._remove_socket()
            raise HostOpenError("cannot create the host-browser broker socket") from exc
        self._server = server
        self._thread = Thread(target=self._serve, name="devcapsule-host-open", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self._stop.set()
        if self._server is not None:
            self._server.close()
        if self._thread is not None:
            self._thread.join(timeout=self.opener_timeout + 1.0)
        self._remove_socket()

    def _serve(self) -> None:
        assert self._server is not None
        while not self._stop.is_set():
            try:
                connection, _address = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with connection:
                connection.settimeout(DEFAULT_TIMEOUT_SECONDS)
                self._handle(connection)

    def _handle(self, connection: socket.socket) -> None:
        try:
            if _peer_uid(connection) != os.getuid():
                raise HostOpenError("peer user does not own this broker")
            request = _decode_mapping(
                _read_frame(connection, MAX_FRAME_BYTES),
                "host-browser request",
            )
            if set(request) != {"schema_version", "url"} or request.get("schema_version") != 1:
                raise HostOpenError("request protocol is malformed or unsupported")
            url = request.get("url")
            if not isinstance(url, str):
                raise HostOpenError("request URL is not a string")
            selected_url = validate_host_url(url)
            self._check_rate_limit()
            try:
                completed = subprocess.run(
                    [*self.opener, selected_url],
                    check=False,
                    env=self.environ,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=self.opener_timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise HostOpenError("host opener timed out") from exc
            except OSError as exc:
                raise HostOpenError("host opener could not be executed") from exc
            if completed.returncode != 0:
                raise HostOpenError("host opener returned a failure status")
            connection.sendall(_encode_frame({"ok": True}))
        except (HostOpenError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            detail = str(exc) or "request rejected"
            try:
                connection.sendall(_encode_frame({"ok": False, "error": detail}))
            except OSError:
                pass

    def _check_rate_limit(self) -> None:
        now = time.monotonic()
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        if len(self._requests) >= RATE_LIMIT_REQUESTS:
            raise HostOpenError("request rate limit exceeded")
        self._requests.append(now)

    def _remove_socket(self) -> None:
        if not self._bound:
            return
        try:
            if _is_socket(self.socket_path):
                self.socket_path.unlink()
        finally:
            self._bound = False


@contextmanager
def host_open_bridge(
    environ: Mapping[str, str],
    *,
    enabled: bool,
    opener: Sequence[str] = ("xdg-open",),
) -> Iterator[Path | None]:
    """Reuse an inherited broker or own one for a physical-host launch."""

    if not enabled:
        yield None
        return
    containerized = in_container()
    inherited = environ.get(HOST_OPEN_SOCKET_ENV)
    if inherited:
        path = Path(inherited)
        if not containerized:
            raise HostOpenError(
                "a physical-host launch cannot inherit a pre-existing host-browser socket"
            )
        if (
            path != HOST_OPEN_SOCKET_DESTINATION
            or not path.is_absolute()
            or ".." in path.parts
            or not _is_socket(path)
        ):
            raise HostOpenError("inherited host-browser socket is absent or unsafe")
        yield path
        return
    if containerized:
        # A container cannot manufacture access to its physical host desktop.
        # It may only propagate a bridge explicitly inherited from its owner.
        yield None
        return
    if not HostOs.current().binds_unix_sockets:
        # The broker is a host Unix socket bound into the capsule. Docker
        # Desktop refuses that bind source, so the optional integration is
        # unavailable rather than fatal.
        print(HOST_OPEN_UNAVAILABLE_ON_MACOS, file=sys.stderr)
        yield None
        return

    parent = _runtime_parent(environ)
    with _broker_socket_path(parent) as path:
        with HostOpenBroker(path, environ=environ, opener=opener):
            yield path


def _runtime_parent(environ: Mapping[str, str]) -> str | None:
    configured = environ.get("XDG_RUNTIME_DIR")
    if not configured:
        return None
    parent = Path(configured)
    if parent.is_dir() and os.access(parent, os.W_OK | os.X_OK):
        return str(parent)
    return None


@contextmanager
def _broker_socket_path(parent: str | None) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="devcapsule-host-open.", dir=parent) as directory:
        root = Path(directory)
        root.chmod(0o700)
        path = root / "broker.sock"
        if len(os.fsencode(path)) <= _UNIX_PATH_LIMIT:
            yield path
            return
        if parent is None:
            raise HostOpenError("temporary path is too long for a Unix socket")
        # Deep test/workspace runtime paths can exceed Linux's sockaddr_un
        # limit. /tmp is safe here because mkdtemp creates a private 0700
        # directory and the socket itself is 0600.
        with tempfile.TemporaryDirectory(
            prefix=f"devcapsule-host-open-{os.getuid()}.",
            dir="/tmp",
        ) as fallback_directory:
            fallback_root = Path(fallback_directory)
            fallback_root.chmod(0o700)
            fallback_path = fallback_root / "broker.sock"
            if len(os.fsencode(fallback_path)) > _UNIX_PATH_LIMIT:
                raise HostOpenError("temporary path is too long for a Unix socket")
            yield fallback_path


def _peer_uid(connection: socket.socket) -> int:
    if not hasattr(socket, "SO_PEERCRED"):
        raise HostOpenError("peer credentials are unavailable on this platform")
    credentials = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", credentials)
    return uid


def _is_socket(path: Path) -> bool:
    try:
        return stat.S_ISSOCK(path.stat().st_mode)
    except OSError:
        return False


def _encode_frame(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _read_frame(connection: socket.socket, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = connection.recv(min(4096, limit + 1 - size))
        if not chunk:
            raise HostOpenError("protocol frame ended before its newline")
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise HostOpenError("protocol frame exceeds its size limit")
        if b"\n" in chunk:
            frame = b"".join(chunks)
            line, separator, trailing = frame.partition(b"\n")
            if not separator or trailing:
                raise HostOpenError("protocol frame contains trailing data")
            return line


def _decode_mapping(value: bytes, field: str) -> dict[str, Any]:
    try:
        decoded = value.decode("utf-8")
        document = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HostOpenError(f"{field} is not valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise HostOpenError(f"{field} is not an object")
    return document
