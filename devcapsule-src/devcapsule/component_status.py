"""Our durable v1 compatibility contract, independent of vendor metadata schemas.

Only advisory text is consumed. The feed cannot change endpoints, install code,
alter a selection, or certify component health. Unknown formats fail closed to
guidance, not to launching the already selected environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from devcapsule.components.discovery import read_metadata


REPOSITORY = "https://github.com/mycodespace-ai/devcapsule"
STATUS_PAGE = REPOSITORY + "/tree/component-status"
FEED_URL = "https://raw.githubusercontent.com/mycodespace-ai/devcapsule/component-status/compatibility-v1.json"
MAX_AGE = timedelta(days=3)


def text_field(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 2000 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("expected bounded, single-line text")
    return value


def timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(text_field(value).replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamps must use UTC")
    return parsed


def strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("expected a nonempty list")
    return tuple(text_field(item) for item in value)


@dataclass(frozen=True)
class Advisory:
    identity: str
    component: str
    adapters: tuple[str, ...]
    cli_versions: tuple[str, ...]
    platforms: tuple[str, ...]
    status: str
    message: str
    issue_url: str
    fixed_in: str | None
    reviewed_at: datetime
    expires_at: datetime

    @classmethod
    def parse(cls, value: Any) -> Advisory:
        status = text_field(value["status"])
        if status not in {"cli-update-required", "known-issue"}:
            raise ValueError("unknown advisory status")
        issue = text_field(value["issue_url"])
        prefix = REPOSITORY + "/issues/"
        suffix = issue.removeprefix(prefix)
        if not issue.startswith(prefix) or not suffix.isascii() or not suffix.isdigit():
            raise ValueError("expected a DevCapsule GitHub issue URL")
        fixed = value.get("fixed_in")
        if status == "cli-update-required":
            fixed = text_field(fixed)
            if not all(part.isascii() and part.isdigit() for part in fixed.split(".")) or len(fixed.split(".")) != 3:
                raise ValueError("fixed_in must name an exact final CLI release")
        elif fixed is not None:
            raise ValueError("known-issue must not claim a released fix")
        reviewed, expires = timestamp(value["reviewed_at"]), timestamp(value["expires_at"])
        if not timedelta(0) < expires - reviewed <= timedelta(days=90):
            raise ValueError("advisory review must expire within 90 days")
        return cls(text_field(value["id"]), text_field(value["component"]), strings(value["adapters"]),
                   strings(value["cli_versions"]), strings(value["platforms"]), status, text_field(value["message"]),
                   issue, fixed, reviewed, expires)

    def matches(self, component: str, adapter: str, cli_version: str, platform: str) -> bool:
        # Adapter IDs are exact. Wildcards on CLI/platform are explicit operator choices.
        return (component == self.component and adapter in self.adapters
                and ("*" in self.cli_versions or cli_version in self.cli_versions)
                and ("*" in self.platforms or platform in self.platforms))


@dataclass(frozen=True)
class StatusFeed:
    generated_at: datetime
    expires_at: datetime
    advisories: tuple[Advisory, ...]

    @classmethod
    def parse(cls, value: Any) -> StatusFeed:
        if not isinstance(value, dict) or type(value.get("format")) is not int or value["format"] != 1:
            raise ValueError("unsupported compatibility-feed format")
        generated, expires = timestamp(value["generated_at"]), timestamp(value["expires_at"])
        if not timedelta(0) < expires - generated <= MAX_AGE:
            raise ValueError("feed validity must be at most three days")
        rows = value["advisories"]
        if not isinstance(rows, list) or len(rows) > 500:
            raise ValueError("invalid advisory list")
        advisories = tuple(Advisory.parse(row) for row in rows)
        if len({item.identity for item in advisories}) != len(advisories):
            raise ValueError("duplicate advisory IDs")
        return cls(generated, expires, advisories)

    def guidance(self, component: str, adapter: str, cli_version: str, platform: str, *, now: datetime) -> str:
        if self.generated_at > now + timedelta(minutes=5) or now >= self.expires_at:
            return "DevCapsule status feed is stale or has a future timestamp; no current diagnosis is available."
        applicable = [item for item in self.advisories if item.matches(component, adapter, cli_version, platform)]
        current = [item for item in applicable if item.reviewed_at <= now < item.expires_at]
        if not current:
            return ("The matching DevCapsule diagnosis needs review; no current guidance is available." if applicable
                    else "DevCapsule has no matching diagnosis for this check failure; update status remains unknown.")
        lines = []
        for item in current:
            if item.fixed_in:
                lines.append(f"Update DevCapsule to {item.fixed_in} or a later release containing the fix to restore {component} update checks. "
                             f"This does not itself upgrade the component. Release: {REPOSITORY}/releases/tag/v{item.fixed_in}")
            else:
                lines.append(f"DevCapsule cannot reliably report {component} update status with this adapter.")
            lines.append(f"{item.message} Issue and workarounds: {item.issue_url} (reviewed {item.reviewed_at.isoformat()}).")
        return "\n".join(lines)


class CompatibilityLookup:
    """At most one bounded metadata request per check, and cached offline guidance."""

    def __init__(self, cache: Path, cli_version: str):
        self.cache = cache
        self.cli_version = cli_version
        self.feed: StatusFeed | None = None
        self.loaded = False
        self.note = ""

    def _load(self) -> None:
        self.loaded = True
        try:
            payload = read_metadata(FEED_URL, limit=1024 * 1024)
            self.feed = StatusFeed.parse(json.loads(payload))
        except Exception as exc:
            # The fallback itself is optional: transport/protocol/parser failure
            # (including truncated HTTP bodies) must not escape into launch.
            self.note = f"DevCapsule status service unavailable ({type(exc).__name__})."
            try:
                with self.cache.open("rb") as stream:
                    payload = stream.read(1024 * 1024 + 1)
                if len(payload) > 1024 * 1024:
                    raise ValueError("oversized cache")
                self.feed = StatusFeed.parse(json.loads(payload))
                self.note += " Using cached status metadata."
            except Exception:
                return
        else:
            # Cache failure must not invalidate a successful metadata request.
            try:
                self.cache.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.cache.with_suffix(".incoming")
                temporary.write_bytes(payload)
                temporary.replace(self.cache)
            except OSError:
                self.note = "Could not cache DevCapsule status metadata."

    def explain(self, component: str, adapter: str, platform: str) -> str:
        if not self.loaded:
            self._load()
        lines = [self.note] if self.note else []
        if self.feed:
            lines.append(self.feed.guidance(component, adapter, self.cli_version, platform, now=datetime.now(timezone.utc)))
            lines.append(f"Status metadata generated: {self.feed.generated_at.isoformat()}.")
        else:
            lines.append("No maintained diagnosis is available; component update status remains unknown.")
        lines.append("DevCapsule component status: " + STATUS_PAGE)
        return "\n".join(lines)
