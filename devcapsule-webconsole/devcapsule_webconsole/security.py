"""The two boundaries of the console: the run token and the project mount.

Every request carries the token or is refused; the token arrives in the URL
the launcher prints and is kept in a port-scoped cookie from then on. Every
file or directory the console reads lies inside the project mount; a path that
escapes it is refused before its contents are read. Public operations on the
project mount are ``confine``, ``find_project_folders``, ``list_project_directory``,
``open_project_file``, ``read_project_bytes`` and ``read_project_text``.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import errno
import os
from pathlib import Path
import secrets
import stat
from typing import Any, BinaryIO
from urllib.parse import parse_qs, urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = [
    "PathRefused",
    "REFUSAL_BODY",
    "TOKEN_COOKIE",
    "TOKEN_HEADER",
    "TOKEN_QUERY_PARAMETER",
    "TokenGate",
    "confine",
    "find_project_folders",
    "list_project_directory",
    "open_project_file",
    "read_project_bytes",
    "read_project_text",
    "token_cookie_name",
]

TOKEN_QUERY_PARAMETER = "token"
TOKEN_COOKIE = "devcapsule-console-token"
TOKEN_HEADER = "x-devcapsule-token"
TOKEN_HEADER_BYTES = TOKEN_HEADER.encode("ascii")
REFUSAL_BODY = b"devcapsule web console: missing or invalid run token\n"
# Where find_project_folders does not look: a directory whose name starts with
# a dot (version control, environments, caches), and the package trees named
# here. They hold other people's files by the tens of thousands.
UNSEARCHED_DIRECTORIES = frozenset({"node_modules"})
# The most directories one search visits before it reports itself incomplete.
FOLDER_SEARCH_BUDGET = 20_000


def token_cookie_name(port: int | None = None) -> str:
    """Cookie name for ``port``, or ``TOKEN_COOKIE`` when the origin carries no port.

    RFC 6265 §8.5 shares cookies across every port of ``127.0.0.1``. Naming the
    cookie after the browser-facing port keeps concurrent capsules' consoles
    from overwriting one another's credential in the same browser profile.
    """
    if port is not None and not isinstance(port, bool) and 0 < port < 65536:
        return f"{TOKEN_COOKIE}-{port}"
    return TOKEN_COOKIE


def _scope_port(scope: Scope) -> int | None:
    raw_headers: Sequence[tuple[bytes, bytes]] = scope.get("headers", ())
    hosts = [value.decode("latin-1").strip() for name, value in raw_headers if name.lower() == b"host"]
    if len(hosts) == 1:
        host = hosts[0]
        if not host or any(ord(c) <= 0x20 or ord(c) >= 0x7F or c in ";,\\\"'" for c in host):
            return None
        try:
            parsed = urlsplit(f"//{host}")
            if (
                parsed.hostname
                and parsed.username is None
                and parsed.password is None
                and not parsed.path
                and not parsed.query
                and not parsed.fragment
            ):
                return parsed.port
        except ValueError:
            return None
        return None
    if not hosts:
        server = scope.get("server")
        if (
            isinstance(server, (tuple, list))
            and len(server) == 2
            and isinstance(server[1], int)
            and not isinstance(server[1], bool)
            and server[1] not in (80, 443)
        ):
            return server[1]
    return None


def _cookie_values(raw_headers: Sequence[tuple[bytes, bytes]], cookie_name: str) -> list[str]:
    """Values of ``cookie_name`` across ``Cookie`` headers, isolated from neighbor cookies.

    Browsers send every cookie stored for ``127.0.0.1`` to every port on
    ``127.0.0.1`` (RFC 6265 §8.5). ``http.cookies.SimpleCookie.load`` aborts on
    JSON or bracketed cookies set by unrelated local applications, discarding
    later credentials in the same header; console tokens are unquoted RFC 6265
    cookie-octets (``settings.read_token``), so reading ``;`` pairs directly
    keeps ``cookie_name`` working alongside arbitrary neighbor cookies.
    """
    values: list[str] = []
    for name, raw_value in raw_headers:
        if name.lower() != b"cookie":
            continue
        for chunk in raw_value.decode("latin-1").split(";"):
            if "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            if key.strip() == cookie_name:
                values.append(value.strip())
    return values


class TokenGate:
    """ASGI middleware: admit a request that carries the token, refuse the rest.

    A valid token in the query string is answered with the port-scoped cookie,
    so a page opened from the printed URL can follow its own links without
    clobbering another capsule's console on ``127.0.0.1``. A valid cookie or
    header is accepted as is. Comparison is constant-time.
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    def _matches(self, candidate: str | None) -> bool:
        return candidate is not None and secrets.compare_digest(candidate.encode(), self.token.encode())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        raw_headers: Sequence[tuple[bytes, bytes]] = scope.get("headers", ())
        cookie_name = token_cookie_name(_scope_port(scope))
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        from_query = query.get(TOKEN_QUERY_PARAMETER, [None])[0]
        if self._matches(from_query):
            await self.app(scope, receive, _setting_cookie(send, cookie_name, self.token))
            return
        if any(self._matches(candidate) for candidate in _cookie_values(raw_headers, cookie_name)):
            await self.app(scope, receive, send)
            return
        header_tokens = [value.decode("latin-1") for name, value in raw_headers if name.lower() == TOKEN_HEADER_BYTES]
        if len(header_tokens) == 1 and self._matches(header_tokens[0]):
            await self.app(scope, receive, send)
            return
        await _refuse(send)


def _setting_cookie(send: Send, cookie_name: str, token: str) -> Send:
    cookie = f"{cookie_name}={token}; Path=/; HttpOnly; SameSite=Strict"

    async def send_with_cookie(message: Message) -> None:
        if message["type"] == "http.response.start":
            message = {**message, "headers": [*message.get("headers", []), (b"set-cookie", cookie.encode("latin-1"))]}
        await send(message)

    return send_with_cookie


async def _refuse(send: Send) -> None:
    await send({
        "type": "http.response.start", "status": 403,
        "headers": [(b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(REFUSAL_BODY)).encode())],
    })
    await send({"type": "http.response.body", "body": REFUSAL_BODY})


class PathRefused(ValueError):
    """The requested path does not lie inside the project mount."""


def confine(root: Path, requested: str) -> Path:
    """The file ``requested`` names inside ``root``, or ``PathRefused``.

    ``requested`` is relative, with no ``..`` component. The result is
    resolved, so a symbolic link that leaves the mount is refused too.
    """
    candidate = Path(requested)
    if not requested or candidate.is_absolute() or ".." in candidate.parts or "\x00" in requested:
        raise PathRefused(f"path {requested!r} is not a relative path inside the project")
    base = root.resolve()
    try:
        resolved = (base / candidate).resolve()
    except (OSError, RuntimeError) as error:
        raise PathRefused(f"cannot resolve path {requested!r} inside the project") from error
    if not resolved.is_relative_to(base):
        raise PathRefused(f"path {requested!r} leaves the project")
    return resolved


def read_project_text(root: Path, requested: str) -> str:
    """``read_project_bytes`` decoded as UTF-8; a ``UnicodeDecodeError`` says it is not text."""
    return read_project_bytes(root, requested).decode("utf-8")


@contextmanager
def open_project_file(root: Path, requested: str) -> Iterator[tuple[BinaryIO, int]]:
    """Resolve inside the mount, open without following replacement links, and yield ``(stream, size)``.

    A pathname check alone is insufficient: an editor or agent can replace
    the file or a parent directory between resolution and open. Directory
    descriptors anchor each lookup; O_NOFOLLOW refuses a substituted symlink,
    and parent descriptors close before the file stream is yielded. Internal
    symlinks still work because confine resolves them first.
    """
    base = root.resolve()
    resolved = confine(base, requested)
    parts = resolved.relative_to(base).parts
    if not parts:
        raise FileNotFoundError(requested)
    with ExitStack() as file_opened:
        with ExitStack() as directories:
            try:
                directory = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                directories.callback(os.close, directory)
                for part in parts[:-1]:
                    directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    directories.callback(os.close, directory)
                # Do not block if a regular file was replaced by a FIFO.
                descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except OSError as error:
                if error.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise PathRefused(f"path {requested!r} changed during the read") from error
                raise
            file_opened.callback(os.close, descriptor)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise FileNotFoundError(requested)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            yield stream, info.st_size


def read_project_bytes(root: Path, requested: str) -> bytes:
    """Resolve inside the mount, then read all bytes without following replacement links."""
    with open_project_file(root, requested) as (stream, _):
        return stream.read()


def _open_directory_step(parent_fd: int | None, target: Path | str, requested: str, *, is_last: bool) -> int:
    try:
        if parent_fd is None:
            return os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        return os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise PathRefused(f"path {requested!r} changed during the read") from error
        if error.errno == errno.ENOTDIR:
            try:
                mode = (
                    os.lstat(target).st_mode
                    if parent_fd is None
                    else os.stat(target, dir_fd=parent_fd, follow_symlinks=False).st_mode
                )
            except FileNotFoundError:
                raise
            except OSError as stat_error:
                raise PathRefused(f"path {requested!r} changed during the read") from stat_error
            if stat.S_ISLNK(mode):
                raise PathRefused(f"path {requested!r} changed during the read") from error
            if not is_last:
                raise FileNotFoundError(requested) from error
        raise


def _entry_name(raw_name: str) -> str:
    try:
        raw_name.encode("utf-8")
        return raw_name
    except UnicodeEncodeError:
        return raw_name.encode("utf-8", "surrogateescape").decode("utf-8", "replace")


def list_project_directory(root: Path, requested: str = "") -> dict[str, Any]:
    """List one directory inside ``root`` without following entry links.

    ``requested`` is empty for the project root, or a relative directory path
    inside ``root`` checked with ``confine``. Each step from ``root`` opens by
    descriptor with ``O_DIRECTORY | O_NOFOLLOW`` so a directory replaced by a
    symbolic link after resolution is refused with ``PathRefused``. Entries are
    inspected with ``lstat`` and sorted directories first, then non-directories,
    each group by ``name.casefold()``.
    """
    base = root.resolve()
    if requested == "":
        parts: tuple[str, ...] = ()
        clean_path = ""
    else:
        resolved = confine(base, requested)
        parts = resolved.relative_to(base).parts
        clean_path = "/".join(part for part in Path(requested).parts if part != ".")
    entries: list[dict[str, Any]] = []
    with ExitStack() as opened:
        directory = _open_directory_step(None, base, requested, is_last=not parts)
        opened.callback(os.close, directory)
        for index, part in enumerate(parts):
            directory = _open_directory_step(directory, part, requested, is_last=index == len(parts) - 1)
            opened.callback(os.close, directory)
        with os.scandir(directory) as iterator:
            for entry in iterator:
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                mode = info.st_mode
                if stat.S_ISLNK(mode):
                    kind = "link"
                elif stat.S_ISDIR(mode):
                    kind = "directory"
                elif stat.S_ISREG(mode):
                    kind = "file"
                else:
                    kind = "other"
                entries.append({
                    "name": _entry_name(entry.name),
                    "kind": kind,
                    "size": info.st_size if kind == "file" else None,
                    "modified": datetime.fromtimestamp(info.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
    entries.sort(key=lambda item: (item["kind"] != "directory", item["name"].casefold(), item["name"]))
    return {"path": clean_path, "entries": entries}


def find_project_folders(root: Path, marker: str, *, budget: int = FOLDER_SEARCH_BUDGET) -> dict[str, Any]:
    """The folders below ``root`` that hold a regular file named ``marker``.

    The result is ``{"folders": [...], "complete": bool}``: paths relative to
    ``root`` with ``/`` separators, sorted, and whether every directory was
    visited. The root itself is never among them. The walk opens each
    directory by descriptor from its parent and enters no symbolic link, so it
    cannot leave the mount; a ``marker`` that is itself a link or a directory
    does not count. It does not enter a directory whose name starts with a dot
    or is in ``UNSEARCHED_DIRECTORIES``, visits directories in name order, and
    stops after ``budget`` of them with ``complete`` false. A directory that
    cannot be read is passed over.
    """
    base = root.resolve()
    folders: list[str] = []
    visited = 0
    for path, directories, files, descriptor in os.fwalk(base, follow_symlinks=False):
        if visited == budget:
            return {"folders": sorted(folders), "complete": False}
        visited += 1
        directories[:] = sorted(
            name for name in directories if not name.startswith(".") and name not in UNSEARCHED_DIRECTORIES
        )
        if marker not in files or Path(path) == base:
            continue
        try:
            mode = os.stat(marker, dir_fd=descriptor, follow_symlinks=False).st_mode
        except OSError:
            continue
        if stat.S_ISREG(mode):
            folders.append(Path(path).relative_to(base).as_posix())
    return {"folders": sorted(folders), "complete": True}
