"""Local notifications: what one checkout's DevCapsule environment tells its human.

A notification is one JSON file in the checkout's state, written by an agent
or a tool inside the capsule, or by the ``project checkout notifications``
commands from the host. The web console shows them under a bell; the human
reads or dismisses them there or with the same commands. Nothing here is a
record: the directory is never committed, and the owner's decision of
2026-10-09 keeps notifications local to one checkout. Project-wide
notifications, a coordinator reaching every collaborator, are a later source
merged into the same listing, not a change to this store.

The directory, format 1:

```text
$XDG_STATE_HOME/devcapsule/notifications/<id>.json
```

Each document carries ``format`` (the integer 1), ``id`` (the file's stem:
lowercase letters, digits and hyphens, starting with a letter or digit, at
most 100 characters), ``kind`` (lowercase letters, digits and hyphens, at
most 32 characters, a vocabulary the console renders by; ``decision`` is
reserved), ``title``, ``posted-by``, ``posted-at`` (ISO 8601), and the
optional ``summary`` (markdown), ``link`` (a console path such as
``/records/README.md``, starting with ``/``) and ``read-at`` (ISO 8601 or
``null``). Documents are regular UTF-8 files of at most 64 KiB; the reader
never follows a symbolic link.

The listing merges the sibling ``decisions`` directory, the web console's
decision pages: an unanswered decision appears as an unread notification of
kind ``decision`` linking to its page, and an answered one does not appear.
A decision is never copied here; it is read or dismissed only by answering
it or by its asking agent deleting it.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Any, Iterator, Mapping

from devcapsule.configuration.bindings import configuration_binding_declarations, managed_binding_path
from devcapsule.configuration.storage import (
    discover_project, find_checkout_record, load_checkout, lock_for, manifest_for,
)
from devcapsule.platforms import XdgHomes
from devcapsule.recursive_dogfood import CONTAINER_NAME_ENV

FORMAT = 1
NOTIFICATIONS_ENV = "DEVCAPSULE_NOTIFICATIONS"
"""Names the notifications directory outright; for tests and host-side tooling."""
DECISIONS_ENV = "DEVCAPSULE_CONSOLE_DECISIONS"
"""The web console's own override of its decisions directory; honored so both agree."""
PERSISTENT_HOME_ENV = "DEVCAPSULE_HOME_DIR"
"""The launcher's override of a checkout's persistent home; honored on the host."""
DECISION_KIND = "decision"
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,99}")
KIND_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
MAXIMUM_DOCUMENT_BYTES = 64 * 1024
MAXIMUM_DECISION_BYTES = 1024 * 1024
"""The sibling decision contract permits larger documents than notifications."""
MAXIMUM_LINK_LENGTH = 1000


class NotificationError(ValueError):
    """A notification document or request does not follow the contract; the message says where."""


@dataclass(frozen=True)
class Notification:
    """One notification as the store holds it; ``read_at`` is empty while unread."""

    id: str
    kind: str
    title: str
    posted_by: str
    posted_at: str
    summary: str = ""
    link: str = ""
    read_at: str = ""

    @property
    def unread(self) -> bool:
        return not self.read_at

    def to_mapping(self) -> dict[str, Any]:
        return {
            "format": FORMAT, "id": self.id, "kind": self.kind, "title": self.title, "summary": self.summary,
            "link": self.link, "posted-by": self.posted_by, "posted-at": self.posted_at,
            "read-at": self.read_at or None,
        }


@dataclass(frozen=True)
class ListingError:
    """A file in the directory that is not a notification; listed so it is not silently hidden."""

    id: str
    kind: str
    error: str

    def to_mapping(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "error": self.error}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value: object, where: str, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise NotificationError(f"{where} must be a {'non-empty ' if required else ''}string")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise NotificationError(f"{where} must contain valid Unicode text")
    return value


def _timestamp(value: object, where: str, *, required: bool = False) -> str:
    text = _text(value, where, required=required)
    if text:
        try:
            datetime.fromisoformat(text)
            if len(text) <= 10:
                raise ValueError("a date alone is not a timestamp")
        except ValueError as error:
            raise NotificationError(f"{where} must be an ISO 8601 timestamp") from error
    return text


def _key(value: object, where: str, pattern: re.Pattern[str]) -> str:
    text = _text(value, where, required=True)
    if pattern.fullmatch(text) is None:
        raise NotificationError(f"{where} must be lowercase letters, digits and hyphens, starting with a letter or digit")
    return text


def _link(value: object, where: str) -> str:
    text = _text(value, where)
    if not text:
        return ""
    if (not text.startswith("/") or text.startswith("//") or "\\" in text
            or len(text) > MAXIMUM_LINK_LENGTH or any(c.isspace() or ord(c) < 0x20 or c == "\x7f" for c in text)):
        raise NotificationError(f"{where} must be a console path starting with '/' without whitespace or control characters")
    return text


def notification_from_mapping(document: object) -> Notification:
    """Validate a notification document; every refusal names the field."""
    if not isinstance(document, dict):
        raise NotificationError("a notification must be a JSON object")
    if type(document.get("format")) is not int or document["format"] != FORMAT:
        raise NotificationError(f"format must be {FORMAT}")
    kind = _key(document.get("kind"), "kind", KIND_PATTERN)
    if kind == DECISION_KIND:
        raise NotificationError(f"kind {DECISION_KIND!r} is reserved for the decisions directory")
    return Notification(
        _key(document.get("id"), "id", ID_PATTERN),
        kind,
        _text(document.get("title"), "title", required=True),
        _text(document.get("posted-by"), "posted-by", required=True),
        _timestamp(document.get("posted-at"), "posted-at", required=True),
        _text(document.get("summary"), "summary"),
        _link(document.get("link"), "link"),
        _timestamp(document.get("read-at"), "read-at"),
    )


@contextmanager
def _directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Pin each directory component without following links, including capsule-written parents.

    The host must not follow a link planted in the capsule's persistent home.
    Descriptor-relative operations also survive a directory being replaced during a command.
    """
    descriptor = os.open(path.anchor or ".", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in (path.parts[1:] if path.anchor else path.parts):
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _read_document(path: Path, *, maximum: int = MAXIMUM_DOCUMENT_BYTES) -> tuple[object, float]:
    """Read a bounded regular file and its mtime from one descriptor; missing files pass through."""
    try:
        with _directory(path.parent) as parent:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise NotificationError(f"{path.name} must be a regular file")
            raw = stream.read(maximum + 1)
    except FileNotFoundError:
        raise
    except OSError as error:
        raise NotificationError(f"cannot read {path.name}: {error}") from error
    if len(raw) > maximum:
        raise NotificationError(f"{path.name} is larger than {maximum} bytes")
    try:
        return json.loads(raw.decode("utf-8")), metadata.st_mtime
    except (ValueError, RecursionError) as error:
        raise NotificationError(f"{path.name} is not a JSON document: {error}") from error


def _sort_key(posted_at: str) -> float:
    """Compare validated timestamps as instants, with naive timestamps interpreted as UTC."""
    moment = datetime.fromisoformat(posted_at)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


@dataclass(frozen=True)
class NotificationStore:
    """The notifications directory and the decisions directory it merges into its listing."""

    directory: Path
    decisions: Path

    def path(self, notification_id: str) -> Path:
        return self.directory / f"{notification_id}.json"

    def _document_stems(self, directory: Path) -> list[str]:
        try:
            with _directory(directory) as parent:
                stems = []
                for name in os.listdir(parent):
                    path = Path(name)
                    if path.suffix != ".json" or ID_PATTERN.fullmatch(path.stem) is None:
                        continue
                    try:
                        metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    except FileNotFoundError:
                        continue  # The agent may discard a file during the scan.
                    if not stat.S_ISDIR(metadata.st_mode):
                        stems.append(path.stem)
                return sorted(stems)
        except FileNotFoundError:
            return []
        except OSError as error:
            raise NotificationError(f"cannot list {directory}: {error}") from error

    def read(self, notification_id: str) -> Notification:
        """One notification by id; ``NotificationError`` names a decision or a malformed file."""
        if ID_PATTERN.fullmatch(notification_id) is None:
            raise NotificationError("the id must be lowercase letters, digits and hyphens, starting with a letter or digit")
        path = self.path(notification_id)
        try:
            notification = notification_from_mapping(_read_document(path)[0])
        except FileNotFoundError:
            if notification_id in self._document_stems(self.decisions):
                raise NotificationError(
                    f"{notification_id!r} is a decision: answer it in the web console, or its asking agent deletes it"
                ) from None
            raise NotificationError(f"no notification {notification_id!r} under {self.directory}") from None
        if notification.id != notification_id:
            raise NotificationError(f"{path.name} carries id {notification.id!r}; the file name is the id")
        return notification

    def list(self) -> list[Notification | ListingError]:
        """Every notification and every unanswered decision, newest first; malformed files as errors."""
        entries: list[tuple[float, Notification | ListingError]] = []
        for stem in self._document_stems(self.directory):
            try:
                notification = notification_from_mapping(_read_document(self.path(stem))[0])
                if notification.id != stem:
                    raise NotificationError(f"{stem}.json carries id {notification.id!r}; the file name is the id")
            except FileNotFoundError:
                continue
            except NotificationError as error:
                entries.append((0.0, ListingError(stem, "", str(error))))
                continue
            entries.append((_sort_key(notification.posted_at), notification))
        for stem in self._document_stems(self.decisions):
            try:
                decision = self._decision_entry(stem)
                if self._has_answer(stem):
                    continue
            except FileNotFoundError:
                continue
            except NotificationError as error:
                entries.append((0.0, ListingError(stem, DECISION_KIND, str(error))))
                continue
            entries.append((_sort_key(decision.posted_at), decision))
        entries.sort(key=lambda entry: entry[0], reverse=True)
        return [entry for _, entry in entries]

    def _decision_entry(self, stem: str) -> Notification:
        """A pending decision as the listing shows it: the document's title and asker, or the file's facts."""
        path = self.decisions / f"{stem}.json"
        document, modified = _read_document(path, maximum=MAXIMUM_DECISION_BYTES)
        if not isinstance(document, dict):
            raise NotificationError(f"{path.name} must be a JSON object")
        if type(document.get("format")) is not int or document["format"] != FORMAT:
            raise NotificationError(f"{path.name}: format must be {FORMAT}")
        if document.get("id") != stem:
            raise NotificationError(f"{path.name}: id must be {stem!r}")
        title = _text(document.get("title"), "title")
        asked_by = _text(document.get("asked-by"), "asked-by")
        asked_at = _timestamp(document.get("asked-at"), "asked-at")
        if not asked_at:
            asked_at = datetime.fromtimestamp(modified, timezone.utc).replace(microsecond=0).isoformat()
        return Notification(
            stem, DECISION_KIND,
            title if title.strip() else stem,
            asked_by or "an agent",
            asked_at, link=f"/decisions/{stem}",
        )

    def _has_answer(self, stem: str) -> bool:
        """Check the stored answer envelope; the console owns item and option validation."""
        path = self.decisions / f"{stem}.answer.json"
        try:
            document, _ = _read_document(path, maximum=MAXIMUM_DECISION_BYTES)
        except FileNotFoundError:
            return False
        if not isinstance(document, dict):
            raise NotificationError(f"{path.name} must be a JSON object")
        if type(document.get("format", FORMAT)) is not int or document.get("format", FORMAT) != FORMAT:
            raise NotificationError(f"{path.name}: format must be {FORMAT}")
        if document.get("id", stem) != stem:
            raise NotificationError(f"{path.name}: id must be {stem!r}")
        _timestamp(document.get("answered-at"), f"{path.name}: answered-at", required=True)
        if not isinstance(document.get("answers", {}), dict):
            raise NotificationError(f"{path.name}: answers must be an object keyed by item")
        return True

    def post(self, *, kind: str, title: str, posted_by: str, summary: str = "", link: str = "",
             now: str | None = None) -> Notification:
        """Write a new notification with a fresh id; the document is validated before anything is written."""
        posted_at = _timestamp(now if now is not None else _now(), "posted-at", required=True)
        stamp = datetime.fromisoformat(posted_at).astimezone(timezone.utc).strftime("%Y%m%dt%H%M%S")
        notification = notification_from_mapping({
            "format": FORMAT, "id": f"{stamp}-{secrets.token_hex(3)}", "kind": kind, "title": title,
            "summary": summary, "link": link, "posted-by": posted_by, "posted-at": posted_at, "read-at": None,
        })
        self._write(notification)
        return notification

    def mark_read(self, notification_id: str, *, now: str | None = None) -> Notification:
        """Record the human's reading; a notification already read keeps its first reading."""
        notification = self.read(notification_id)
        if notification.read_at:
            return notification
        updated = replace(notification, read_at=_timestamp(now if now is not None else _now(), "read-at", required=True))
        self._write(updated)
        return updated

    def dismiss(self, notification_id: str) -> None:
        """Remove the notification; the one deletion the human may ask for."""
        self.read(notification_id)
        try:
            with _directory(self.directory) as parent:
                os.unlink(self.path(notification_id).name, dir_fd=parent)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise NotificationError(f"cannot dismiss {notification_id!r}: {error}") from error

    def _write(self, notification: Notification) -> None:
        # Compact UTF-8 avoids expanding an agent-written document when marking it read.
        content = (json.dumps(notification.to_mapping(), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        if len(content) > MAXIMUM_DOCUMENT_BYTES:
            raise NotificationError(f"notification is larger than {MAXIMUM_DOCUMENT_BYTES} bytes")
        name = self.path(notification.id).name
        try:
            with _directory(self.directory, create=True) as parent:
                temporary = f".{name}.{secrets.token_hex(16)}.tmp"
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=parent)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(content)
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                finally:
                    try:
                        os.unlink(temporary, dir_fd=parent)
                    except FileNotFoundError:
                        pass
        except OSError as error:
            raise NotificationError(f"cannot write {name}: {error}") from error


def store_in_environment(environ: Mapping[str, str] = os.environ) -> NotificationStore:
    """The store of the environment this process runs in: inside a capsule, the checkout's own state."""
    named = environ.get(NOTIFICATIONS_ENV)
    if named:
        directory = Path(named).resolve()
        decisions = environ.get(DECISIONS_ENV)
        return NotificationStore(directory, Path(decisions).resolve() if decisions else directory.parent / "decisions")
    # Resolve the environment's base, keeping the application directories no-follow.
    root = XdgHomes.from_environment(environ).state
    state = root.parent.resolve() / root.name
    decisions = environ.get(DECISIONS_ENV)
    return NotificationStore(state / "notifications", Path(decisions).resolve() if decisions else state / "decisions")


def store_for_checkout(start: Path, environ: Mapping[str, str] = os.environ) -> NotificationStore:
    """The store of the checkout enclosing ``start``, seen from the host through its persistent home.

    The home is what the launcher mounts at ``/home/devcapsule``: the
    ``DEVCAPSULE_HOME_DIR`` override, else the checkout's explicit ``home``
    binding, else the managed default under the host's XDG data home, the same
    resolution ``project info`` reports as the home's backing directory. The
    managed default reads the process environment, as ``project info`` does.
    """
    named = environ.get(NOTIFICATIONS_ENV)
    if named:
        return store_in_environment(environ)
    root = discover_project(start)
    override = environ.get(PERSISTENT_HOME_ENV)
    if override:
        home = Path(override).expanduser()
    else:
        _, manifest = manifest_for(root)
        _, lock = lock_for(root, manifest)
        record = find_checkout_record(manifest, root)
        checkout = load_checkout(record, manifest, root) if record is not None else {}
        configured = dict(checkout.get("state", {}).get("adopted", {}))
        configured.update(checkout.get("configuration", {}).get("bindings", {}).get("host-directory", {}))
        explicit = configured.get("home")
        declaration = configuration_binding_declarations(lock)["home"]
        home = (Path(str(explicit)).expanduser() if explicit is not None
                else managed_binding_path(root, declaration))
    state = home.resolve() / ".local" / "state" / "devcapsule"
    return NotificationStore(state / "notifications", state / "decisions")


def store_for(start: Path | None, environ: Mapping[str, str] = os.environ) -> NotificationStore:
    """Inside a capsule, its own state; on the host, the checkout's persistent home."""
    if environ.get(CONTAINER_NAME_ENV):
        return store_in_environment(environ)
    return store_for_checkout(start or Path("."), environ)


def listing_document(store: NotificationStore, *, unread_only: bool = False) -> dict[str, Any]:
    """The ``--json`` form of the listing: a stable document for the web console and for agents."""
    entries = store.list()
    if unread_only:
        entries = [entry for entry in entries if isinstance(entry, ListingError) or entry.unread]
    return {
        "format": FORMAT,
        "directory": str(store.directory),
        "decisions": str(store.decisions),
        "unread": sum(1 for entry in entries if isinstance(entry, Notification) and entry.unread),
        "notifications": [entry.to_mapping() for entry in entries],
    }
