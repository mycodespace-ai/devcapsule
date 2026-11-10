"""Unit tests of ``devcapsule/components/npm_channel.py``: abbreviated check metadata and exact version selection."""

from __future__ import annotations

import base64
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from email.message import Message
import io
import json
from typing import BinaryIO
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from devcapsule.compat import CliError
from devcapsule.components.channels import ChannelNotice, ChannelVersion
from devcapsule.components.npm_channel import (
    ABBREVIATED_METADATA_ACCEPT,
    MAX_METADATA_BYTES,
    METADATA_TIMEOUT_SECONDS,
    NpmChannel,
    UrlOpener,
)

PACKAGE = "@openai/codex"
ALIASES = {"linux-amd64": "@openai/codex-linux-x64", "linux-arm64": "@openai/codex-linux-arm64"}
REGISTRY_URL = "https://registry.npmjs.org/@openai%2Fcodex"
SAMPLE_INTEGRITY = "sha512-" + base64.b64encode(b"a" * 64).decode("ascii")


def abbreviated_document(
    *,
    latest: str = "0.167.0",
    versions: Mapping[str, Mapping[str, object]] | None = None,
) -> bytes:
    """Serialize an npm ``application/vnd.npm.install-v1+json`` response carrying only install-v1 fields."""
    entries = (
        {
            "0.166.0": {"name": PACKAGE, "version": "0.166.0", "dist": {"tarball": f"{REGISTRY_URL}/-/0.166.0.tgz"}},
            "0.167.0": {"name": PACKAGE, "version": "0.167.0", "dist": {"tarball": f"{REGISTRY_URL}/-/0.167.0.tgz"}},
        }
        if versions is None
        else {key: dict(value) for key, value in versions.items()}
    )
    return json.dumps(
        {
            "name": PACKAGE,
            "dist-tags": {"latest": latest},
            "versions": entries,
        }
    ).encode("utf-8")


def recording_opener(responses: Mapping[str, bytes]) -> tuple[UrlOpener, list[tuple[str, dict[str, str], float]]]:
    """Return an ``UrlOpener`` backed by ``responses`` and a log of ``(url, headers, timeout)`` calls."""
    calls: list[tuple[str, dict[str, str], float]] = []

    @contextmanager
    def open_url(target: str | Request, *, timeout: float) -> Iterator[BinaryIO]:
        if isinstance(target, Request):
            url = target.full_url
            headers = {key.lower(): value for key, value in target.header_items()}
        else:
            url = target
            headers = {}
        calls.append((url, headers, timeout))
        if url != REGISTRY_URL and headers.get("accept") == ABBREVIATED_METADATA_ACCEPT:
            raise HTTPError(url, 406, "Not Acceptable", Message(), None)
        yield io.BytesIO(responses[url])

    return open_url, calls


def test_check_requests_abbreviated_install_metadata_and_reports_newer_latest() -> None:
    """``check`` sends ``Accept: application/vnd.npm.install-v1+json`` and reports both ``current`` and newer ``latest``."""
    opener, calls = recording_opener({REGISTRY_URL: abbreviated_document()})
    channel = NpmChannel(PACKAGE, dict(ALIASES), opener=opener)

    report = channel.check("0.166.0", "linux-amd64")

    assert calls == [(REGISTRY_URL, {"accept": ABBREVIATED_METADATA_ACCEPT}, METADATA_TIMEOUT_SECONDS)]
    assert report.source == REGISTRY_URL
    assert report.current == ChannelVersion("0.166.0", "available")
    assert report.candidates == (ChannelVersion("0.167.0", "available"),)


def test_check_omits_candidates_when_current_version_is_already_latest() -> None:
    """When ``current`` matches ``dist-tags.latest``, ``check`` returns an empty ``candidates`` tuple."""
    opener, _calls = recording_opener({REGISTRY_URL: abbreviated_document(latest="0.167.0")})
    channel = NpmChannel(PACKAGE, dict(ALIASES), opener=opener)

    report = channel.check("0.167.0", "linux-arm64")

    assert report.current == ChannelVersion("0.167.0", "available")
    assert report.candidates == ()


def test_check_marks_unlisted_version_withdrawn_from_abbreviated_metadata() -> None:
    """``check`` classifies a version absent from ``versions`` as ``withdrawn`` with no notices."""
    opener, _calls = recording_opener({REGISTRY_URL: abbreviated_document(latest="0.167.0")})
    channel = NpmChannel(PACKAGE, dict(ALIASES), opener=opener)

    report = channel.check("0.160.0", "linux-amd64")

    assert report.current == ChannelVersion("0.160.0", "withdrawn", "Not listed in the current registry metadata")


def test_check_marks_deprecated_version_unsupported_with_end_of_support_notice() -> None:
    """``check`` classifies a ``deprecated`` entry as ``unsupported`` with an ``npm-deprecation`` notice."""
    payload = abbreviated_document(
        latest="0.167.0",
        versions={
            "0.165.0": {"name": PACKAGE, "version": "0.165.0", "deprecated": "Upgrade to 0.167.0"},
            "0.167.0": {"name": PACKAGE, "version": "0.167.0"},
        },
    )
    opener, _calls = recording_opener({REGISTRY_URL: payload})
    channel = NpmChannel(PACKAGE, dict(ALIASES), opener=opener)

    report = channel.check("0.165.0", "linux-amd64")

    assert report.current == ChannelVersion(
        "0.165.0",
        "unsupported",
        "Upgrade to 0.167.0",
        (ChannelNotice("npm-deprecation", "end-of-support", "Upgrade to 0.167.0"),),
    )


def test_check_refuses_response_exceeding_sixteen_mib_cap() -> None:
    """``check`` raises ``CliError`` naming ``metadata exceeds 16 MiB`` when the response body exceeds ``MAX_METADATA_BYTES``."""
    oversized = b"{" + (b" " * MAX_METADATA_BYTES)
    opener, _calls = recording_opener({REGISTRY_URL: oversized})
    channel = NpmChannel(PACKAGE, dict(ALIASES), opener=opener)

    with pytest.raises(CliError, match="metadata exceeds 16 MiB"):
        channel.check("0.166.0", "linux-amd64")


def test_select_fetches_single_version_documents_without_abbreviated_accept_header() -> None:
    """``select`` omits the install-v1 ``Accept`` header on per-version URLs, where ``registry.npmjs.org`` returns ``406 Not Acceptable``."""
    meta = {
        "name": PACKAGE,
        "version": "0.167.0",
        "engines": {"node": ">=16"},
        "optionalDependencies": {"@openai/codex-linux-x64": "npm:@openai/codex@0.167.0-linux-x64"},
        "dist": {
            "tarball": "https://registry.npmjs.org/@openai/codex/-/codex-0.167.0.tgz",
            "integrity": SAMPLE_INTEGRITY,
        },
    }
    binary = {
        "name": PACKAGE,
        "version": "0.167.0-linux-x64",
        "os": ["linux"],
        "cpu": ["x64"],
        "dist": {
            "tarball": "https://registry.npmjs.org/@openai/codex/-/codex-0.167.0-linux-x64.tgz",
            "integrity": SAMPLE_INTEGRITY,
        },
    }
    meta_url = f"{REGISTRY_URL}/0.167.0"
    binary_url = f"{REGISTRY_URL}/0.167.0-linux-x64"
    opener, calls = recording_opener(
        {
            meta_url: json.dumps(meta).encode("utf-8"),
            binary_url: json.dumps(binary).encode("utf-8"),
        }
    )
    channel = NpmChannel(PACKAGE, dict(ALIASES), opener=opener)

    selection = channel.select("0.167.0", "linux-amd64")

    assert [url for url, _headers, _timeout in calls] == [meta_url, binary_url]
    assert all(headers.get("accept") != ABBREVIATED_METADATA_ACCEPT for _url, headers, _timeout in calls)
    assert selection.metadata["version"] == "0.167.0"
    assert selection.metadata["artifacts"]["linux-amd64"]["npm-package"] == "@openai/codex-linux-x64"
