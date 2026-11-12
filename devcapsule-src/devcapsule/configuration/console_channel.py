"""The configuration channel between a running capsule's console and its launcher.

Answer 7 of the CLI UX work order (2026-10-24): the launcher is the only
writer of the user's records; the console reaches it through a directory
the launcher mounts into the capsule for the run. Answer 16: the launcher
writes the listing it computed at launch into the same directory, so
inspection inside the capsule prints the truth with its time.

The files are JSON and complete when visible: each is written as a
temporary name in the directory, then published by rename (launcher) or
exclusive hard link (console).

- ``listing.json``, launcher to capsule, once, at launch: ``{"format": 1,
  "at": <ISO time>, "listing": <the config show --json document>}``.
- ``NNNNNN-VERB-UUID.request.json``, console to launcher: ``{"format": 1,
  "requested": <ISO time>, "arguments": [<config tokens>]}``. The console
  numbers the names and adds a random UUID; the launcher handles them in
  name order. Legacy names without a UUID remain readable.
- ``NNNNNN-VERB-UUID.result.json``, launcher to console, beside the request:
  ``{"format": 1, "status": "recorded" | "refused" | "deferred", "text":
  <what happened>, "at": <ISO time>}``.

What the launcher does with a request depends on its verb. A verb that
keeps the checkout's own choices, or narrows what the next launch reaches,
is applied at once with the command's own validation: ``ide``, ``add``, ``omit``, ``restore``, ``use``, ``set``, ``deny``, literal ``env set``, ``env unset``, ``unbind``,
``trust withdraw``, ``docker-args clear``. A verb that widens what the
next launch may reach is deferred: ``authorize``, ``trust accept``,
``bind``, ``forget``, ``env set --from-host``, ``docker-args set``. Forgetting
a vendor-download denial can restore home trust. Anything running inside the capsule can
write to the mounted directory, not only the console, so a widening is
never taken from it unconfirmed: the launcher keeps it as the console's
request beside the checkout record, and the user confirms or discards it
on the host, at the next ``run`` or with ``config console``. Every other
verb is refused with the reason.

This module is pure: the contract, its documents and the classification.
Reading the directory, running commands and keeping the deferred requests
belong to the launcher's adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import re
import shlex
import stat
import tempfile
from typing import Any, Mapping, Sequence

from .file_formats import ProjectConfigurationError

__all__ = ["CHANNEL_FORMAT", "DeferredRequest", "Disposition", "LISTING_FILE", "REQUEST_SUFFIX",
           "RESULT_SUFFIX", "classify", "listing_document", "parse_deferred", "parse_listing", "parse_request",
           "read_document", "render_deferred", "request_id", "result_document", "statement", "write_complete"]

CHANNEL_FORMAT = 1
LISTING_FILE = "listing.json"
REQUEST_SUFFIX = ".request.json"
RESULT_SUFFIX = ".result.json"
REQUEST_ID = re.compile(r"[0-9]{6}-[a-z][a-z0-9-]{0,39}(?:-[0-9a-f]{32})?")
MAXIMUM_DOCUMENT_BYTES = 256 * 1024
MAXIMUM_TOKENS = 64
MAXIMUM_TOKEN_LENGTH = 4096

APPLIED_VERBS = {"ide", "add", "omit", "restore", "use", "set", "deny", "unbind"}
APPLIED_SUBVERBS = {("env", "set"), ("env", "unset"), ("trust", "withdraw"), ("docker-args", "clear")}
DEFERRED_VERBS = {"authorize", "bind", "forget"}
DEFERRED_SUBVERBS = {("trust", "accept"), ("docker-args", "set")}
SECURE_AUTHORIZATIONS = {
    "network": {"bridge", "none"}, "docker-daemon": {"none"},
    "development-sudo": {"false", "none"}, "host-browser": {"false", "none"}, "host-x11": {"false", "none"},
}
READ_ONLY_VERBS = {"show", "check", "console"}
READ_ONLY_SUBVERBS = {("env", "list"), ("trust", "list"), ("docker-args", "list")}


class Disposition(Enum):
    """What the launcher does with a request: at once, after the user's confirmation, or not at all."""

    APPLY = "apply"
    DEFER = "defer"
    REFUSE = "refuse"


def classify(arguments: Sequence[str]) -> tuple[Disposition, str]:
    """The disposition of the config tokens ``arguments`` and, for a refusal, the reason."""
    if not arguments:
        return Disposition.REFUSE, "an empty request names no command"
    if (len(arguments) == 3 and arguments[0] == "authorize"
            and arguments[2] in SECURE_AUTHORIZATIONS.get(arguments[1], set())):
        return Disposition.APPLY, ""
    verb = arguments[0]
    pair = (verb, arguments[1]) if len(arguments) > 1 else (verb, "")
    # Removing a denial can expose a home grant. Host environment
    # bindings can expose secrets. Only a literal env value is safe here;
    # argparse also accepts abbreviated options such as --from-h.
    if pair == ("env", "set") and not (
        len(arguments) == 4 and all(not token.startswith("-") for token in arguments[2:])
    ):
        return Disposition.DEFER, ""
    if verb in APPLIED_VERBS or pair in APPLIED_SUBVERBS:
        return Disposition.APPLY, ""
    if verb in DEFERRED_VERBS or pair in DEFERRED_SUBVERBS:
        return Disposition.DEFER, ""
    if verb in READ_ONLY_VERBS or pair in READ_ONLY_SUBVERBS:
        return Disposition.REFUSE, f"config {verb} is read-only; the console shows what it reports"
    if verb == "default":
        return Disposition.REFUSE, "home default sets a home default; run it on the host"
    if verb in {"require", "offer", "drop", "recommend", "promote", "capabilities", "need"}:
        return Disposition.REFUSE, f"config {verb} edits the project's shared files; run it on the host, in the project"
    return Disposition.REFUSE, f"config {verb!r} is not a request the launcher takes from the console"


def statement(arguments: Sequence[str]) -> str:
    """The request as the command it stands for, without the project path."""
    return shlex.join(["config", *arguments])


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def listing_document(listing: Mapping[str, Any], at: str | None = None) -> dict[str, Any]:
    return {"format": CHANNEL_FORMAT, "at": at or now(), "listing": dict(listing)}


def result_document(status: str, text: str, at: str | None = None) -> dict[str, Any]:
    assert status in {"recorded", "refused", "deferred"}
    if len(text) > 16384:
        text = text[:16384] + "\n[Output truncated; inspect configuration on the host.]"
    return {"format": CHANNEL_FORMAT, "status": status, "text": text, "at": at or now()}


def request_id(path: Path) -> str:
    """The request's id from its file name; refused when the name is not the contract's."""
    name = path.name
    if not name.endswith(REQUEST_SUFFIX):
        raise ProjectConfigurationError(f"{name} is not a request file ({REQUEST_SUFFIX}).")
    identifier = name[: -len(REQUEST_SUFFIX)]
    if REQUEST_ID.fullmatch(identifier) is None:
        raise ProjectConfigurationError(f"{name}: a request is named NNNNNN-VERB.")
    return identifier


def parse_request(document: Any, name: str = "request") -> list[str]:
    """The config tokens of a request document, validated; the reason when they are not."""
    if not isinstance(document, dict) or document.get("format") != CHANNEL_FORMAT:
        raise ProjectConfigurationError(f"{name}: not a format-{CHANNEL_FORMAT} request document.")
    requested = document.get("requested")
    if requested is not None:
        try:
            if not isinstance(requested, str) or len(requested) > 64:
                raise ValueError("not a time string")
            if datetime.fromisoformat(requested).tzinfo is None:
                raise ValueError("missing time zone")
        except ValueError as exc:
            raise ProjectConfigurationError(f"{name}: 'requested' must be an ISO time with a time zone.") from exc
    arguments = document.get("arguments")
    if not isinstance(arguments, list) or not arguments or len(arguments) > MAXIMUM_TOKENS:
        raise ProjectConfigurationError(f"{name}: 'arguments' must be a list of 1 to {MAXIMUM_TOKENS} tokens.")
    for token in arguments:
        if not isinstance(token, str) or not token or len(token) > MAXIMUM_TOKEN_LENGTH:
            raise ProjectConfigurationError(f"{name}: every token is a non-empty string of at most {MAXIMUM_TOKEN_LENGTH} characters.")
        try:
            token.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ProjectConfigurationError(f"{name}: every token must contain valid Unicode text.") from exc
        if any(ord(character) < 0x20 for character in token):
            raise ProjectConfigurationError(f"{name}: a token holds no control characters.")
        if token == "--path":
            raise ProjectConfigurationError(f"{name}: the launcher names the project; '--path' is not a request's to give.")
    return [str(token) for token in arguments]


def parse_listing(document: Any) -> tuple[str, dict[str, Any]]:
    """The time and the listing of a launcher-written ``listing.json``."""
    if not isinstance(document, dict) or document.get("format") != CHANNEL_FORMAT:
        raise ProjectConfigurationError(f"{LISTING_FILE}: not a format-{CHANNEL_FORMAT} listing document.")
    at, listing = document.get("at"), document.get("listing")
    if not isinstance(at, str) or not isinstance(listing, dict) or not isinstance(listing.get("rows"), list):
        raise ProjectConfigurationError(f"{LISTING_FILE}: 'at' and a listing with rows are required.")
    return at, listing


@dataclass(frozen=True)
class DeferredRequest:
    """A widening the console asked for, kept until the user confirms or discards it on the host."""

    id: str
    requested: str
    arguments: tuple[str, ...]

    def document(self) -> dict[str, Any]:
        return {"id": self.id, "requested": self.requested, "arguments": list(self.arguments)}

    @property
    def statement(self) -> str:
        return statement(self.arguments)


def render_deferred(requests: Sequence[DeferredRequest]) -> str:
    return json.dumps({"format": CHANNEL_FORMAT, "requests": [item.document() for item in requests]},
                      indent=2, sort_keys=True) + "\n"


def parse_deferred(document: Any, name: str = "console requests") -> list[DeferredRequest]:
    if not isinstance(document, dict) or document.get("format") != CHANNEL_FORMAT:
        raise ProjectConfigurationError(f"{name}: not a format-{CHANNEL_FORMAT} document.")
    items = document.get("requests")
    if not isinstance(items, list):
        raise ProjectConfigurationError(f"{name}: 'requests' must be a list.")
    result: list[DeferredRequest] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or REQUEST_ID.fullmatch(item["id"]) is None:
            raise ProjectConfigurationError(f"{name}: every request has an id named NNNNNN-VERB.")
        requested = item.get("requested", "")
        if not isinstance(requested, str):
            raise ProjectConfigurationError(f"{name}: 'requested' is a time string.")
        arguments = parse_request({"format": CHANNEL_FORMAT, "arguments": item.get("arguments")}, f"{name} {item['id']}")
        result.append(DeferredRequest(item["id"], requested, tuple(arguments)))
    return result


def read_document(path: Path, limit: int = MAXIMUM_DOCUMENT_BYTES) -> Any:
    """A JSON document from a bounded regular file, never through a symbolic link."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise ProjectConfigurationError(f"{path.name}: cannot open: {exc.strerror}.") from exc
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ProjectConfigurationError(f"{path.name}: not a regular file.")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ProjectConfigurationError(f"{path.name}: larger than {limit} bytes.")
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise ProjectConfigurationError(f"{path.name}: not a JSON document: {exc}.") from exc


def write_complete(path: Path, document: Mapping[str, Any]) -> Path:
    """Write ``document`` so that ``path`` is only ever seen complete: a temporary name, then one rename."""
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    data = json.dumps(dict(document), indent=2, sort_keys=True) + "\n"
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path
