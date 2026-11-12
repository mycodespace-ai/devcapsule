"""Unit tests of ``devcapsule/components/linux_arm64_pins.py``: the arm64 builds of the amd64 matrix's pins.

The tables are data; each test reads them, and the amd64 matrix where it compares.
"""
from __future__ import annotations

import json
import re
from typing import Any

from devcapsule.components.linux_arm64_pins import COMPONENT_LOCK_TABLES, LINUX_ARM64_ECLIPSE_NATIVE_PACKAGES
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

AMD64 = MATRICES[Platform.LINUX_AMD64]
AMD64_MARKERS = re.compile(r"x86[_-]64|[_-]x64|amd64|linux64/|cft/[^/]+/linux64|ffmpeg-linux\.zip")
"""How amd64 archives name themselves in their URLs."""


def artifacts(value: Any) -> list[dict[str, Any]]:
    """Every table at any depth that names a download by ``url``."""
    if isinstance(value, dict):
        own = [value] if "url" in value else []
        return own + [found for item in value.values() for found in artifacts(item)]
    if isinstance(value, (list, tuple)):
        return [found for item in value for found in artifacts(item)]
    return []


def test_every_arm64_pin_is_a_version_the_amd64_matrix_pins() -> None:
    """Each table is the arm64 build of a version the amd64 matrix pins; the converse fails at import."""
    assert all(AMD64.component_pin(component, version) is not None for component, version in COMPONENT_LOCK_TABLES)


def test_no_arm64_pin_names_an_amd64_artifact() -> None:
    """No artifact URL names an amd64 archive."""
    urls = [str(artifact["url"]) for table in COMPONENT_LOCK_TABLES.values() for artifact in artifacts(table)]
    assert [url for url in urls if AMD64_MARKERS.search(url)] == []


def test_every_arm64_artifact_is_hash_pinned() -> None:
    """Every artifact carries a SHA-256."""
    hashes = [artifact.get("sha256") for table in COMPONENT_LOCK_TABLES.values() for artifact in artifacts(table)]
    assert all(re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in hashes)


def test_arm64_artifacts_are_not_amd64_bytes() -> None:
    """Every artifact differs from amd64's, except architecture-independent ones: Codex's JavaScript
    package, pure-Python wheels and Ubuntu ``_all`` packages."""
    shared = {artifact["sha256"] for (component, version) in COMPONENT_LOCK_TABLES
              for artifact in artifacts(AMD64.component_pin(component, version))}
    same = [(version, str(artifact["url"])) for (_, version), table in COMPONENT_LOCK_TABLES.items()
            for artifact in artifacts(table) if artifact["sha256"] in shared]
    assert all(url.endswith(("_all.deb", "-none-any.whl", f"codex-{version}.tgz")) for version, url in same)


def test_platform_fields_and_artifact_keys_name_arm64() -> None:
    """Every table that names a platform names linux-arm64, and none names linux-amd64."""
    assert "linux-amd64" not in json.dumps(list(COMPONENT_LOCK_TABLES.values()))
    assert {table["platform"] for table in COMPONENT_LOCK_TABLES.values() if "platform" in table} == {"linux-arm64"}
    assert all(list(table["artifacts"]) == ["linux-arm64"] for (component, _), table in COMPONENT_LOCK_TABLES.items()
               if component in {"codex", "claude-code", "antigravity-cli"})


def test_eclipse_native_closure_is_arm64_or_architecture_independent() -> None:
    """Eclipse's native packages are amd64's plus libunwind8, each an arm64 package of ports.ubuntu.com
    or an architecture-independent one."""
    amd64 = AMD64.component_pin("eclipse", "2026-09-R")
    assert amd64 is not None
    assert set(LINUX_ARM64_ECLIPSE_NATIVE_PACKAGES) - set(amd64["native-packages"]) == {"libunwind8"}
    assert all(entry["url"].endswith("_all.deb") or (
        entry["url"].startswith("https://ports.ubuntu.com/ubuntu-ports/pool/") and entry["url"].endswith("_arm64.deb"))
        for entry in LINUX_ARM64_ECLIPSE_NATIVE_PACKAGES.values())
