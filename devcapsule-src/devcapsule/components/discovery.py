"""Read-only vendor signals. These are maintained adapters, not vendor promises.

No installer is executed and no executable payload is acquired here. A release
pointer establishes availability, never the support/security state of old builds.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import json
import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from devcapsule.compat import CliError
from devcapsule.components.channels import ChannelNotice, ChannelReport, ChannelVersion


def read_metadata(url: str, *, limit: int = 2 * 1024 * 1024) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "DevCapsule-update-check"}), timeout=8) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("metadata size limit exceeded")
    return payload


def read_json(url: str) -> Any:
    return json.loads(read_metadata(url))


def exact_version(value: Any) -> str:
    if not isinstance(value, str) or not 1 < len(value) < 80:
        raise ValueError("expected a dotted release version")
    parts = value.split(".")
    if len(parts) < 2 or any(not part or not part.isascii() or not part.isdigit() for part in parts):
        raise ValueError("expected a dotted release version")
    return value


def _available(source: str, current: str, latest: Any, detail: str = "") -> ChannelReport:
    latest = exact_version(latest)
    current_parts = tuple(map(int, exact_version(current).split(".")))
    latest_parts = tuple(map(int, latest.split(".")))
    return ChannelReport(source, ChannelVersion(current, "available" if latest == current else "unknown",
                         "This release feed does not assess installed-version support."),
                         (ChannelVersion(latest, "available", detail),) if latest_parts > current_parts else ())


class VendorDiscovery:
    source: str

    def check(self, current: str, platform: str) -> ChannelReport:
        if platform not in {"linux-amd64", "linux-arm64"}:
            raise CliError(f"No discovery adapter for {platform}.")
        try:
            return self._check(current, platform)
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
            raise CliError(f"Vendor discovery unavailable at {self.source}: {exc}") from exc

    def _check(self, current: str, platform: str) -> ChannelReport:
        raise NotImplementedError


class JetBrainsDiscovery(VendorDiscovery):
    product_keys: tuple[str, ...] = ("PCP", "PY")
    source = "https://data.services.jetbrains.com/products/releases?code=PY&latest=true&type=release"

    def _check(self, current: str, platform: str) -> ChannelReport:
        document = read_json(self.source)
        # PY currently maps to PCP; admit the two observed product keys explicitly.
        releases = next((document[key] for key in self.product_keys if key in document), None)
        if not isinstance(releases, list) or len(releases) != 1 or releases[0]["type"] != "release":
            raise ValueError("expected one JetBrains release")
        release = releases[0]
        artifact = release["downloads"]["linux" if platform == "linux-amd64" else "linuxARM64"]
        if not artifact.get("link") or not artifact.get("checksumLink"):
            raise ValueError("platform download/checksum missing")
        return _available(self.source, current, release["version"])


class IntelliJDiscovery(JetBrainsDiscovery):
    product_keys = ("IIU",)
    source = "https://data.services.jetbrains.com/products/releases?code=IIU&latest=true&type=release"


class RiderDiscovery(JetBrainsDiscovery):
    product_keys = ("RD",)
    source = "https://data.services.jetbrains.com/products/releases?code=RD&latest=true&type=release"


class EclipseDiscovery(VendorDiscovery):
    source = "https://www.eclipse.org/downloads/packages/"

    def _check(self, current: str, platform: str) -> ChannelReport:
        if re.fullmatch(r"[0-9]{4}-(?:03|06|09|12)-R", current) is None:
            raise ValueError("expected an Eclipse quarterly release such as 2026-09-R")
        arch = "x86_64" if platform == "linux-amd64" else "aarch64"
        document = read_metadata(self.source).decode("utf-8")
        versions = set(re.findall(
            rf"eclipse-java-([0-9]{{4}}-(?:03|06|09|12)-R)-linux-gtk-{arch}\.tar\.gz", document))
        if len(versions) != 1:
            raise ValueError("expected one stable Eclipse Java package for the platform")
        latest = versions.pop()
        return ChannelReport(self.source, ChannelVersion(
            current, "available" if current == latest else "unknown",
            "Package availability does not assess installed-version support."),
            (ChannelVersion(latest, "available", "Requires a reviewed Eclipse Java package pin"),)
            if latest > current else ())


class DotnetDiscovery(VendorDiscovery):
    source = "https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json"

    def _check(self, current: str, platform: str) -> ChannelReport:
        releases = read_json(self.source)["releases-index"]
        stable = [exact_version(row["latest-sdk"]) for row in releases
                  if row["support-phase"] in {"active", "maintenance"}
                  and "-" not in row["latest-sdk"]]
        latest = max(stable, key=lambda version: tuple(map(int, version.split("."))))
        return _available(self.source, current, latest, "Latest supported stable SDK; reviewed pin required")


class PlaywrightDiscovery(VendorDiscovery):
    source = "https://pypi.org/pypi/playwright/json"

    def _check(self, current: str, platform: str) -> ChannelReport:
        release = read_json(self.source)
        if not any(item.get("packagetype") == "bdist_wheel" and not item.get("yanked")
                   for item in release["urls"]):
            raise ValueError("published wheel missing")
        return _available(self.source, current, release["info"]["version"],
                          "Requires a reviewed wheel and matching browser pin update")


class CodiumDiscovery(VendorDiscovery):
    source = "https://api.github.com/repos/VSCodium/vscodium/releases/latest"

    def _check(self, current: str, platform: str) -> ChannelReport:
        release = read_json(self.source)
        if release["prerelease"] is not False or release["draft"] is not False:
            raise ValueError("expected a published stable release")
        latest = exact_version(release["tag_name"])
        arch = "x64" if platform == "linux-amd64" else "arm64"
        name = f"VSCodium-linux-{arch}-{latest}.tar.gz"
        if not any(asset.get("name") == name for asset in release["assets"]):
            raise ValueError("platform archive missing")
        return _available(self.source, current, latest)


class VscodeDiscovery(VendorDiscovery):
    source = "https://update.code.visualstudio.com/api/update/"

    def _check(self, current: str, platform: str) -> ChannelReport:
        arch = "linux-x64" if platform == "linux-amd64" else "linux-arm64"
        source = f"{self.source}{arch}/stable/latest"
        release = read_json(source)
        if not isinstance(release, Mapping):
            raise ValueError("expected a release object")
        url = release.get("url")
        sha256 = release.get("sha256hash")
        if not isinstance(url, str) or not isinstance(sha256, str):
            raise ValueError("platform archive/checksum missing")
        parsed = urlparse(url)
        if (any(character.isspace() for character in url)
                or parsed.scheme != "https" or not parsed.hostname or parsed.port == 0
                or parsed.username is not None or parsed.password is not None
                or not parsed.path.endswith(".tar.gz") or parsed.query or parsed.fragment
                or re.fullmatch(r"[0-9a-fA-F]{64}", sha256) is None):
            raise ValueError("platform archive/checksum missing")
        latest = exact_version(release["productVersion"])
        return _available(source, current, latest)


class ClaudeDiscovery(VendorDiscovery):
    source = "https://downloads.claude.ai/claude-code-releases/latest"

    def _check(self, current: str, platform: str) -> ChannelReport:
        latest = exact_version(read_metadata(self.source, limit=128).decode().strip())
        manifest = read_json(f"https://downloads.claude.ai/claude-code-releases/{latest}/manifest.json")
        arch = "linux-x64" if platform == "linux-amd64" else "linux-arm64"
        if manifest["version"] != latest or not manifest["platforms"][arch].get("checksum"):
            raise ValueError("version/platform manifest mismatch")
        return _available(self.source, current, latest, "Vendor latest channel")


class AntigravityDiscovery(VendorDiscovery):
    source = "https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/"

    def _check(self, current: str, platform: str) -> ChannelReport:
        source = self.source + platform.replace("-", "_") + ".json"
        manifest = read_json(source)
        if not manifest.get("url") or not manifest.get("sha512"):
            raise ValueError("download/checksum missing")
        return _available(source, current, manifest["version"])


class PostgresqlDiscovery(VendorDiscovery):
    source = "https://www.postgresql.org/versions.json"

    def _check(self, current: str, platform: str) -> ChannelReport:
        # Existing base locks record only the major. Do not invent an installed
        # minor version or claim that an upstream minor is missing from the base.
        major_only = current.isascii() and current.isdigit()
        major = current if major_only else exact_version(current).split(".")[0]
        rows = read_json(self.source)
        row = next((row for row in rows if row["major"] == major), None)
        if row is None:
            raise ValueError(f"no support record for PostgreSQL {major}")
        if type(row["supported"]) is not bool:
            raise ValueError("invalid supported flag")
        end = date.fromisoformat(row["eolDate"])
        latest = major + "." + row["latestMinor"]
        report = _available(self.source, current if not major_only else major + ".0", latest,
                            "Requires a reviewed DevCapsule base update")
        supported = row["supported"] and end >= date.today()
        detail = f"Upstream major {major} support ends {end}; distribution backports are not assessed."
        notices = () if supported else (ChannelNotice(f"postgresql-{major}-eol", "end-of-support", detail),)
        # A minor release in an unsupported major is not a remedy for its EOL.
        candidates = report.candidates if supported and not major_only else ()
        if major_only:
            detail += f" Latest upstream minor: {latest}; installed minor is not recorded in this base lock."
        return ChannelReport(self.source, ChannelVersion(current, "available" if supported else "unsupported", detail, notices), candidates)
