"""The configuration channel: the launcher's listing at launch, and the console's requests for the next launch.

Answer 7 of the CLI UX redesign work order (2026-10-24): the launcher is
the only writer of the user's records. The console reaches it through a
directory the launcher mounts into the capsule for the run, by default
``/run/devcapsule-configuration``; the contract is ``CONFIGURATION-CHANNEL.md``
beside this package. The console writes a request as ``NNNNNN-VERB-UUID.request.json``,
complete before it is visible: a temporary file, then an exclusive hard link. The
launcher answers beside it with ``NNNNNN-VERB-UUID.result.json``. The launcher
wrote ``listing.json`` there at launch: the table ``config show`` printed,
with its time.

A request is the argument tokens of one ``devcapsule project config``
command. The console checks the verb against the launcher's vocabulary so
a typo is refused here, with the reason; the launcher validates the whole
command again and the result says what it did: recorded, refused, or
deferred to the user's confirmation on the host, for a request that widens
what the next launch reaches.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import stat
import tempfile
import uuid
from typing import Any, Mapping, Sequence

FORMAT = 1
CHANNEL_ENV = "DEVCAPSULE_CONSOLE_CONFIGURATION"
DEFAULT_CHANNEL = Path("/run/devcapsule-configuration")
LISTING_FILE = "listing.json"
REQUEST_SUFFIX = ".request.json"
RESULT_SUFFIX = ".result.json"
REQUEST_ID = re.compile(r"([0-9]{6})-([a-z][a-z0-9-]{0,39})(?:-[0-9a-f]{32})?")
MAXIMUM_DOCUMENT_BYTES = 256 * 1024
MAXIMUM_COMMAND_BYTES = 16 * 1024
MAXIMUM_TOKENS = 64
# The launcher's config vocabulary a request may name; anything else is a typo or not the console's to ask.
VERBS = ("ide", "add", "omit", "restore", "use", "set", "deny", "forget", "unbind", "env", "trust", "docker-args", "authorize", "bind")
# ``github-ssh`` is the retired name of ``ssh-proxy``; a launcher earlier than
# the rename knows only that one.
SECURE_AUTHORIZATIONS = {
    "network": {"bridge", "none"}, "docker-daemon": {"none"},
    "ssh-proxy": {"false", "none"}, "github-ssh": {"false", "none"},
    "development-sudo": {"false", "none"}, "host-browser": {"false", "none"}, "host-x11": {"false", "none"},
}
WIDENING = ("authorize", "bind", "forget", "trust accept", "docker-args set")
"""Verbs the launcher keeps for the user's confirmation on the host instead of recording at once."""


class ChannelError(ValueError):
    """A request or a channel file does not follow the contract; the message says where."""


def default_channel(environ: Mapping[str, str] = os.environ) -> Path:
    named = environ.get(CHANNEL_ENV)
    return Path(named) if named else DEFAULT_CHANNEL


def suggested_arguments(command: str) -> str:
    """The config tokens of a listing row's host command, for the page's prefilled request."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return ""
    if "config" not in tokens:
        return ""
    return shlex.join(tokens[tokens.index("config") + 1:])


def parse_command(text: str) -> list[str]:
    """The tokens of a request typed as ``config`` arguments; refused with the reason when not a request."""
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ChannelError("the request must contain valid Unicode text") from error
    if size > MAXIMUM_COMMAND_BYTES:
        raise ChannelError("the request is too long")
    try:
        tokens = shlex.split(text)
    except ValueError as error:
        raise ChannelError(f"the request does not parse as a command line: {error}") from error
    if tokens and tokens[0] == "config":
        tokens = tokens[1:]
    if not tokens:
        raise ChannelError("the request names no command")
    if len(tokens) > MAXIMUM_TOKENS:
        raise ChannelError(f"the request has more than {MAXIMUM_TOKENS} tokens")
    if tokens[0] not in VERBS:
        raise ChannelError(f"'config {tokens[0]}' is not a request the launcher takes from the console; "
                           f"the verbs are {', '.join(VERBS)}")
    if "--path" in tokens:
        raise ChannelError("the launcher names the project; '--path' is not a request's to give")
    for token in tokens:
        if not token or len(token) > 4096:
            raise ChannelError("every token must contain 1 to 4096 characters")
        if any(ord(character) < 0x20 for character in token):
            raise ChannelError("a request holds no control characters")
    return tokens


def is_widening(tokens: Sequence[str]) -> bool:
    if not tokens:
        return False
    if len(tokens) == 3 and tokens[0] == "authorize" and tokens[2] in SECURE_AUTHORIZATIONS.get(tokens[1], set()):
        return False
    if list(tokens[:2]) == ["env", "set"]:
        return not (len(tokens) == 4 and all(not token.startswith("-") for token in tokens[2:]))
    head = " ".join(tokens[:2])
    return tokens[0] in WIDENING or head in WIDENING


@dataclass(frozen=True)
class ChannelRequest:
    id: str
    requested: str
    arguments: tuple[str, ...]
    result: dict[str, Any] | None

    def to_mapping(self) -> dict[str, Any]:
        return {"id": self.id, "requested": self.requested, "arguments": list(self.arguments),
                "command": shlex.join(["config", *self.arguments]), "widening": is_widening(self.arguments),
                "result": self.result}


@dataclass(frozen=True)
class ConfigurationChannel:
    directory: Path

    @property
    def available(self) -> bool:
        """Whether the launcher mounted the channel for this run: its listing is there."""
        try:
            return self.listing() is not None
        except (ChannelError, OSError):
            return False

    def listing(self) -> dict[str, Any] | None:
        """The launcher's listing at launch, as ``{"at": time, "listing": document}``; ``None`` without the channel."""
        path = self.directory / LISTING_FILE
        if not path.is_file():
            return None
        document = _read_document(path)
        if (not isinstance(document, dict) or document.get("format") != FORMAT
                or not isinstance(document.get("at"), str) or not isinstance(document.get("listing"), dict)
                or not isinstance(document["listing"].get("rows"), list)):
            raise ChannelError(f"{LISTING_FILE} is not a format-{FORMAT} listing")
        return {"at": str(document.get("at", "")), "listing": document["listing"]}

    def requests(self) -> list[ChannelRequest]:
        """Every request in the channel, in name order, each with its result when the launcher has answered."""
        if not self.directory.is_dir():
            return []
        result: list[ChannelRequest] = []
        for path in sorted(self.directory.iterdir()):
            if not path.name.endswith(REQUEST_SUFFIX):
                continue
            identifier = path.name[: -len(REQUEST_SUFFIX)]
            if REQUEST_ID.fullmatch(identifier) is None:
                continue
            try:
                document = _read_document(path)
                if (not isinstance(document, dict) or document.get("format") != FORMAT
                        or not isinstance(document.get("arguments"), list)):
                    raise ChannelError("malformed request")
                tokens = document["arguments"]
                if not tokens or not all(isinstance(token, str) for token in tokens):
                    raise ChannelError("malformed request tokens")
                arguments = tuple(parse_command(shlex.join(tokens)))
                requested = str(document.get("requested", "")) if isinstance(document, dict) else ""
            except (ChannelError, OSError, KeyError, TypeError):
                arguments, requested = (), ""
            result_path = path.with_name(identifier + RESULT_SUFFIX)
            answer: dict[str, Any] | None = None
            if result_path.exists() or result_path.is_symlink():
                try:
                    read = _read_document(result_path)
                    if (not isinstance(read, dict) or read.get("format") != FORMAT
                            or read.get("status") not in ("recorded", "refused", "deferred")
                            or not isinstance(read.get("text"), str)):
                        raise ChannelError("unreadable result; inspect configuration on the host")
                    answer = read
                except (ChannelError, OSError) as error:
                    answer = {"status": "unknown", "text": f"Cannot read the launcher result: {error}. Inspect configuration on the host before retrying."}
            result.append(ChannelRequest(identifier, requested, arguments, answer))
        return result

    def write_request(self, tokens: Sequence[str]) -> ChannelRequest:
        """Write one request, complete before it is visible, under the next sequence number."""
        if not self.available:
            raise ChannelError("the launcher did not mount the configuration channel for this run")
        sequence = 1 + max((int(REQUEST_ID.fullmatch(item.id).group(1)) for item in self.requests()  # type: ignore[union-attr]
                            if REQUEST_ID.fullmatch(item.id)), default=0)
        verb = re.sub(r"[^a-z0-9-]", "-", tokens[0].lower())[:40] or "request"
        # The random suffix prevents collisions between workers and launches.
        # Keep six sequence digits for readable ordering within this run.
        if sequence > 999999:
            raise ChannelError("this run has exhausted its request sequence; use configuration on the host")
        identifier = f"{sequence:06d}-{verb}-{uuid.uuid4().hex}"
        requested = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        document = {"format": FORMAT, "requested": requested, "arguments": list(tokens)}
        path = self.directory / (identifier + REQUEST_SUFFIX)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                             prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
            os.link(temporary, path)  # exclusive: a request name is never reused
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return ChannelRequest(identifier, requested, tuple(tokens), None)


def _read_document(path: Path) -> object:
    """A bounded regular file's JSON, never through a symbolic link."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise ChannelError(f"cannot open {path.name}: {error.strerror}") from error
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ChannelError(f"{path.name} must be a regular file")
        data = stream.read(MAXIMUM_DOCUMENT_BYTES + 1)
    if len(data) > MAXIMUM_DOCUMENT_BYTES:
        raise ChannelError(f"{path.name} is larger than {MAXIMUM_DOCUMENT_BYTES} bytes")
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, RecursionError) as error:
        raise ChannelError(f"{path.name} is not a JSON document: {error}") from error
