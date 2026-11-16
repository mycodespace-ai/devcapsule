"""Launcher-owned GitHub transport broker and capsule client.

``GitHubBroker`` owns a private Unix socket and bounded concurrent SSH children.
``relay_git`` connects Git's byte streams to it. Only the launcher creates the
broker; neither side reads private keys. The wire begins with a bounded JSON
request. Client input then streams unchanged, with a write-half close for EOF.
Server replies are frames: O stdout, E stderr, X unsigned exit status.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import os
from pathlib import Path
import selectors
import shutil
import signal
import socket
import struct
import subprocess
import tempfile
import threading
import time
from typing import BinaryIO

from devcapsule.github_transport import GitHubRequest, GitHubTransportError, decode_request

__all__ = ["GitHubBroker", "relay_git", "github_ssh_bridge", "SOCKET_ENV", "SOCKET_DESTINATION",
           "GIT_SSH_COMMAND", "MAX_REQUEST", "MAX_FRAME"]

SOCKET_ENV = "DEVCAPSULE_GITHUB_SOCKET"
SOCKET_DESTINATION = Path("/run/devcapsule-github.sock")
GIT_SSH_COMMAND = "/opt/devcapsule/bin/devcapsule.pex github-ssh --"
MAX_REQUEST = 4096
MAX_FRAME = 65536


def _read_exact(connection: socket.socket, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        chunk = connection.recv(length - len(chunks))
        if not chunk:
            raise GitHubTransportError("GitHub proxy connection ended unexpectedly.")
        chunks.extend(chunk)
    return bytes(chunks)


class GitHubBroker:
    """One session's GitHub bridge. Close cancels active children and removes its socket.

    ``ssh`` and ``environment`` come from the launcher, never from a request.
    Explicit deadlines bound idle handshakes, blocked consumers and Git operations.
    """

    def __init__(self, path: Path, *, ssh: str, environment: Mapping[str, str],
                 operation_timeout: float = 3600, io_timeout: float = 10) -> None:
        self.path = path
        self.ssh = ssh
        self.environment = dict(environment)
        self.operation_timeout = operation_timeout
        self.io_timeout = io_timeout
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._connections: set[socket.socket] = set()
        self._threads: list[threading.Thread] = []
        self._slots = threading.BoundedSemaphore(8)
        self._server: socket.socket | None = None
        self._listener: threading.Thread | None = None
        self._bound = False

    def __enter__(self) -> GitHubBroker:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(self.path))  # Never unlink or replace someone else's socket.
            self._bound = True
            self.path.chmod(0o600)
            server.listen(8)
            server.settimeout(0.2)
        except BaseException:
            server.close()
            if self._bound:
                self.path.unlink(missing_ok=True)
            raise
        self._server = server
        self._listener = threading.Thread(target=self._serve, daemon=True, name="github-proxy")
        self._listener.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        if self._server is not None:
            self._server.close()
        if self._listener is not None:
            self._listener.join()
        with self._lock:
            for connection in self._connections:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        for thread in self._threads:
            thread.join()
        if self._bound:
            self.path.unlink(missing_ok=True)

    def _serve(self) -> None:
        assert self._server is not None
        while not self._stop.is_set():
            try:
                connection, _ = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            if not self._slots.acquire(blocking=False):
                connection.close()
                continue
            with self._lock:
                self._connections.add(connection)
            thread = threading.Thread(target=self._handle, args=(connection,), daemon=True)
            # Retain only active workers; completed Thread objects need not accumulate.
            self._threads = [item for item in self._threads if item.is_alive()]
            self._threads.append(thread)
            thread.start()

    def _handle(self, connection: socket.socket) -> None:
        try:
            with connection:
                connection.settimeout(self.io_timeout)
                length = struct.unpack("!I", _read_exact(connection, 4))[0]
                if not 0 < length <= MAX_REQUEST:
                    raise GitHubTransportError("GitHub request exceeds its size limit.")
                request = decode_request(_read_exact(connection, length))
                self._transfer(connection, request)
        except (OSError, GitHubTransportError, subprocess.SubprocessError):
            # An invalid or disconnected caller gets EOF, never a host command.
            pass
        finally:
            with self._lock:
                self._connections.discard(connection)
            self._slots.release()

    def _transfer(self, connection: socket.socket, request: GitHubRequest) -> None:
        # Timeout sockets use O_NONBLOCK. Child stdin must be a blocking stream.
        # dup shares file flags, so restore blocking and use send timeouts via
        # a separate connection wrapper only while transmitting output below.
        connection.setblocking(True)
        with subprocess.Popen(request.ssh_command(self.ssh), stdin=connection.fileno(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=self.environment, cwd="/", start_new_session=True) as child:
            assert child.stdout is not None and child.stderr is not None
            started = time.monotonic()
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ, b"O")
                    selector.register(child.stderr, selectors.EVENT_READ, b"E")
                    while selector.get_map():
                        if self._stop.is_set() or time.monotonic() - started > self.operation_timeout:
                            raise GitHubTransportError("GitHub transfer stopped or timed out.")
                        for key, _ in selector.select(0.2):
                            data = os.read(key.fd, MAX_FRAME)
                            if not data:
                                selector.unregister(key.fileobj)
                            else:
                                self._send(connection, key.data, data)
                    while child.poll() is None:
                        if self._stop.wait(0.1) or time.monotonic() - started > self.operation_timeout:
                            raise GitHubTransportError("GitHub transfer stopped or timed out.")
                    self._send(connection, b"X", struct.pack("!I", child.returncode if child.returncode >= 0 else 255))
            finally:
                # SSH may have started a host-configured ProxyCommand. Reap the
                # whole private process group even after the leader exits.
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()

    def _send(self, connection: socket.socket, kind: bytes, payload: bytes) -> None:
        # MSG_DONTWAIT avoids altering the shared file flags of child stdin.
        data = memoryview(kind + struct.pack("!I", len(payload)) + payload)
        deadline = time.monotonic() + self.io_timeout
        with selectors.DefaultSelector() as selector:
            selector.register(connection, selectors.EVENT_WRITE)
            while data:
                if self._stop.is_set() or time.monotonic() > deadline:
                    raise GitHubTransportError("GitHub proxy output stalled.")
                if not selector.select(0.2):
                    continue
                try:
                    count = connection.send(data, socket.MSG_DONTWAIT)
                except BlockingIOError:
                    continue
                if count == 0:
                    raise GitHubTransportError("GitHub proxy output disconnected.")
                data = data[count:]


def relay_git(path: Path, request: GitHubRequest, *, stdin: BinaryIO,
              stdout: BinaryIO, stderr: BinaryIO) -> int:
    """Relay binary Git data, separate diagnostics and the host SSH exit status."""
    payload = request.encode()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(str(path))
        connection.sendall(struct.pack("!I", len(payload)) + payload)
        connection.settimeout(None)

        def send_input() -> None:
            try:
                while chunk := os.read(stdin.fileno(), MAX_FRAME):
                    connection.sendall(chunk)
                connection.shutdown(socket.SHUT_WR)
            except (OSError, ValueError):
                pass  # The server can finish before Git closes stdin.

        threading.Thread(target=send_input, daemon=True, name="github-git-input").start()
        while True:
            kind = _read_exact(connection, 1)
            length = struct.unpack("!I", _read_exact(connection, 4))[0]
            if length > MAX_FRAME:
                raise GitHubTransportError("GitHub proxy frame exceeds its size limit.")
            data = _read_exact(connection, length)
            if kind == b"X" and length == 4:
                return min(struct.unpack("!I", data)[0], 255)
            if kind not in {b"O", b"E"}:
                raise GitHubTransportError("Unknown GitHub proxy response.")
            output = stdout if kind == b"O" else stderr
            output.write(data)
            output.flush()


@contextmanager
def github_ssh_bridge(environment: Mapping[str, str], *, enabled: bool,
                      containerized: bool, binds_unix_sockets: bool) -> Iterator[Path | None]:
    """Create an authorized physical-host broker, or reuse an inherited one.

    Docker Desktop needs a separate transport. An explicit enable there fails
    with an explanation instead of silently mounting keys or exposing an agent.
    """
    if not enabled:
        yield None
        return
    if containerized:
        inherited = environment.get(SOCKET_ENV)
        if inherited != str(SOCKET_DESTINATION) or not SOCKET_DESTINATION.is_socket():
            raise GitHubTransportError("GitHub proxy unavailable: authorize github-ssh on the outside launcher first.")
        yield SOCKET_DESTINATION
        return
    if not binds_unix_sockets:
        raise GitHubTransportError("github-ssh currently requires Linux/WSL with native Docker; Docker Desktop transport is not implemented.")
    executable = shutil.which("ssh", path=environment.get("PATH", os.defpath))
    if executable is None:
        raise GitHubTransportError("github-ssh requires OpenSSH on the host.")
    with tempfile.TemporaryDirectory(prefix="devcapsule-github-", dir="/tmp") as directory:
        path = Path(directory) / "ssh.sock"
        with GitHubBroker(path, ssh=executable, environment=environment):
            yield path
