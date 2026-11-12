"""The home's trust record: vendors and channels accepted once per configuration home, for every project.

D-0011 (2026-10-01), as the owner refined it for 0.3.0 rc4 (answer 3 of
the CLI UX redesign work order): the user accepts a vendor's terms and
trusts its channel once per home, "in all its versions and
incarnations", not per project, checkout or version. A channel is a vendor,
an origin and an integrity method: DevCapsule's own base images from
``docker.io/mycodespaceai/devcapsule-base``, content-addressed by the
digest the launcher pins; each vendor product from the origins its locked
artifacts name, verified by the pinned SHA-256. Anything resolved through
an accepted channel is approved without a question; anything that leaves
it asks: a local image, a different origin, changed terms.

The record lives under the launcher's config root, in ``settings.toml`` under ``trust``, beside
the checkout records; it is the user's, never the project's. Older clients
never read it and keep their per-checkout consents, which remain honored.

This module is pure: it defines channels from a lock and reads and renders
the record. Reading and writing the file belongs to :mod:`storage`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urlparse

from devcapsule.components.catalog import COMPONENTS, INTERACTIVE_SURFACES
from devcapsule.compat import CliError

from .file_formats import ProjectConfigurationError, table

__all__ = ["BASE_CHANNEL", "BASE_REPOSITORY", "Channel", "HomeTrust", "base_channel", "channels_for",
           "component_channel"]

BASE_CHANNEL = "devcapsule-base"
BASE_REPOSITORY = "docker.io/mycodespaceai/devcapsule-base"
BASE_ORIGIN = "https://devcapsule.mycodespace.ai"


@dataclass(frozen=True)
class Channel:
    """One vendor product and the way it reaches this home, as the lock names it."""

    id: str
    vendor: str
    product: str
    origins: tuple[str, ...]
    integrity: str
    terms_url: str = ""
    # The authorization node this channel covers: ``base-image`` or a component's ``*-download``.
    authorization: str = ""
    note: str = ""

    def statement(self, home: Path | None = None) -> str:
        """The product, channel boundary, terms and account scope the user accepts."""
        location = f", `{home}`" if home is not None else ""
        origins = ", ".join(self.origins)
        terms = f" Accept the terms at {self.terms_url}." if self.terms_url else ""
        return (f"Trust {self.vendor} to supply {self.product} from {origins}, verified by {self.integrity}."
                f"{terms} This covers every version and every project launched from this DevCapsule home{location}. "
                "Anyone who uses this home uses this acceptance. Changed terms or a different channel require another decision.")


def base_channel() -> Channel:
    """The published base channel needs no project pin."""
    return Channel(
        BASE_CHANNEL, "DevCapsule", "the base images", (BASE_REPOSITORY, BASE_ORIGIN),
        "the SHA-256 digest the launcher pins", authorization="base-image",
        note=("A launcher you downloaded already carries these digests; this makes the trust explicit. "
              "You trust the mycodespace-ai/devcapsule GitHub account and the mycodespaceai Docker Hub account."),
    )


def channels_for(lock: Mapping[str, Any]) -> dict[str, Channel]:
    """The channels a lock's base and vendor components come through, keyed by channel id.

    The base is a channel only when it is DevCapsule's published repository;
    a local or foreign base is a departure that keeps asking per checkout.
    A component's channel is its acquisition contract plus the HTTPS origins
    of its checksum-pinned artifacts on this platform. Invalid artifacts
    establish no channel; their existing lock validation still applies.
    """
    channels: dict[str, Channel] = {}
    base = lock.get("base")
    reference = base.get("reference") if isinstance(base, dict) else None
    if (isinstance(reference, str) and reference.partition("@")[0] == BASE_REPOSITORY
            and re.fullmatch(r"sha256:[0-9a-f]{64}", reference.partition("@")[2])):
        channels[BASE_CHANNEL] = base_channel()
    components = lock.get("components", {})
    platform = str(lock.get("platform", ""))
    if not isinstance(components, dict):
        return channels
    for component_id, metadata in components.items():
        definition = COMPONENTS.get(component_id) if isinstance(component_id, str) else None
        if definition is None or not isinstance(metadata, dict):
            continue
        channel = component_channel(component_id, metadata, platform)
        if channel is not None:
            channels[component_id] = channel

    return channels


def component_channel(component_id: str, metadata: Mapping[str, Any], platform: str) -> Channel | None:
    """One contract and pinned artifact table, shared by locks and the matrix."""
    definition = COMPONENTS.get(component_id)
    if definition is None:
        return None
    contract = definition.acquisition()
    if contract is None:
        return None
    origins: list[str] = []
    try:
        artifacts = definition.locked_artifacts(metadata, platform)
        candidates = (
            [(metadata.get("url"), metadata.get("sha256"))]
            if component_id in INTERACTIVE_SURFACES and not artifacts
            else [(artifact.url, artifact.sha256) for artifact in artifacts]
        )
        for raw_url, raw_sha256 in candidates:
            if not isinstance(raw_url, str) or not isinstance(raw_sha256, str):
                raise ValueError("missing artifact url or sha256")
            url = urlparse(raw_url)
            if (any(character.isspace() for character in raw_url)
                    or url.scheme != "https" or not url.hostname
                    or url.username is not None or url.password is not None):
                raise ProjectConfigurationError(f"Channel {component_id!r} requires an HTTPS artifact origin without credentials.")
            if re.fullmatch(r"[0-9a-fA-F]{64}", raw_sha256) is None:
                raise ProjectConfigurationError(f"Channel {component_id!r} requires a pinned SHA-256 for every artifact.")
            origin = f"https://{url.hostname}" + (f":{url.port}" if url.port not in (None, 443) else "")
            if origin not in origins:
                origins.append(origin)
    except (CliError, ValueError):
        # The lock's validation reports the malformed artifact. It must
        # never become an empty channel that an existing acceptance covers.
        return None
    if not origins:
        return None
    note = ""
    if component_id == "antigravity-cli":
        note = ("Trust applies to the named deployment and its publishing credentials; "
                "the lock's URL alone does not prove Google owns it.")
    return Channel(
        str(component_id), contract.vendor, contract.display_name, tuple(origins),
        "the SHA-256 the launcher pins", contract.terms_url, contract.authorization, note,
    )



@dataclass(frozen=True)
class HomeTrust:
    """The channels this home's user has accepted, by channel id."""

    channels: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def read(cls, document: Mapping[str, Any]) -> HomeTrust:
        """Read a trust table, or the ``trust`` table of the settings document."""
        source = document.get("trust", document) if "trust" in document else document
        if not isinstance(source, Mapping):
            raise ProjectConfigurationError("The home trust record must be a table.")
        channels = table(source, "channels")
        result: dict[str, dict[str, Any]] = {}
        for channel_id, entry in channels.items():
            if not isinstance(channel_id, str) or not channel_id or not isinstance(entry, dict):
                raise ProjectConfigurationError("The home trust record's channels must be tables keyed by channel id.")
            vendor = entry.get("vendor")
            origins = entry.get("origins", [])
            if not isinstance(vendor, str) or not vendor:
                raise ProjectConfigurationError(f"Trust channel {channel_id!r} must name its vendor.")
            if not isinstance(origins, list) or not all(isinstance(item, str) for item in origins):
                raise ProjectConfigurationError(f"Trust channel {channel_id!r} origins must be an array of strings.")
            terms = entry.get("terms-url", "")
            if not isinstance(terms, str):
                raise ProjectConfigurationError(f"Trust channel {channel_id!r} terms-url must be a string.")
            integrity = entry.get("integrity", "")
            if not isinstance(integrity, str):
                raise ProjectConfigurationError(f"Trust channel {channel_id!r} integrity must be a string.")
            result[channel_id] = {"vendor": vendor, "origins": list(origins), "terms-url": terms,
                                  "integrity": integrity, "product": str(entry.get("product", "")), "accepted": str(entry.get("accepted", ""))}
        return cls(result)

    def covers(self, channel: Channel) -> bool:
        """Same vendor, terms and integrity method, with no new origin; an unknown method never grants trust."""
        entry = self.channels.get(channel.id)
        if entry is None:
            return False
        if (entry["vendor"] != channel.vendor or entry["terms-url"] != channel.terms_url
                or not channel.integrity or entry.get("integrity") != channel.integrity):
            return False
        return bool(channel.origins) and set(channel.origins) <= set(entry["origins"])

    def with_channel(self, channel: Channel, *, accepted_at: datetime | None = None) -> HomeTrust:
        if self.covers(channel):
            return self
        moment = (accepted_at or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
        channels = dict(self.channels)
        origins = set(channel.origins)
        previous = channels.get(channel.id)
        if (previous and previous["vendor"] == channel.vendor and previous["terms-url"] == channel.terms_url
                and previous.get("integrity") == channel.integrity):
            origins.update(previous["origins"])
        channels[channel.id] = {"vendor": channel.vendor, "origins": sorted(origins), "integrity": channel.integrity,
                               "terms-url": channel.terms_url, "product": channel.product, "accepted": moment}
        return HomeTrust(channels)

    def without(self, channel_id: str) -> HomeTrust:
        if channel_id not in self.channels:
            return self
        channels = dict(self.channels)
        del channels[channel_id]
        return HomeTrust(channels)

    def document(self) -> dict[str, Any]:
        return {"channels": {channel_id: dict(entry) for channel_id, entry in sorted(self.channels.items())}}

