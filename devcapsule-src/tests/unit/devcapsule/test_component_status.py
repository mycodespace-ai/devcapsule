"""Unit tests of ``devcapsule/component_status.py``: where the compatibility feed is read from and what the
lookup falls back to.

Every feed here is constructed by ``a_feed``; no test touches the network, the cache home or the package's
resources except through the monkeypatched seams named in each test.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from devcapsule import component_status as status
from devcapsule.component_status import CompatibilityLookup, StatusFeed


def a_feed(*, generated: datetime, advisory_reviewed: datetime | None = None, fixed_in: str = "0.9.9") -> dict:
    """A format-1 feed generated at ``generated``, valid two days, with one Codex advisory reviewed at
    ``advisory_reviewed`` (default: ``generated``) that applies to CLI 0.2.14 on linux-amd64 for 30 days."""
    reviewed = advisory_reviewed or generated
    return {"format": 1, "generated_at": generated.isoformat(), "expires_at": (generated + timedelta(days=2)).isoformat(),
            "advisories": [{"id": "endpoint-change", "component": "codex", "adapters": ["codex-v1"],
                            "cli_versions": ["0.2.14"], "platforms": ["linux-amd64"], "status": "cli-update-required",
                            "message": "Vendor endpoint changed.", "issue_url": status.REPOSITORY + "/issues/123",
                            "fixed_in": fixed_in, "reviewed_at": reviewed.isoformat(),
                            "expires_at": (reviewed + timedelta(days=30)).isoformat()}]}


def unreachable(url: str, **kwargs: object) -> bytes:
    """A fetch that fails the way a missing publication fails."""
    raise OSError(f"unreachable: {url}")


def test_feed_url_is_the_website_unless_the_variable_names_another() -> None:
    """With no variable, or an empty one, the feed is the website's; a nonempty ``DEVCAPSULE_STATUS_URL`` wins."""
    assert status.feed_url({}) == status.FEED_URL
    assert status.feed_url({"DEVCAPSULE_STATUS_URL": ""}) == status.FEED_URL
    assert status.FEED_URL.startswith("https://devcapsule.mycodespace.ai/")
    assert status.feed_url({"DEVCAPSULE_STATUS_URL": "https://test.example/feed.json"}) == "https://test.example/feed.json"


def test_cache_lives_in_the_cache_home_not_the_project() -> None:
    """The cache is one file under the user's cache home, so every project shares the newest fetched feed."""
    path = status.cache_path({"HOME": "/home/someone", "XDG_CACHE_HOME": "/caches"})
    assert path == Path("/caches/devcapsule/compatibility-v1.json")
    assert status.cache_path({"DEVCAPSULE_CONFIG_HOME": "/tmp/chosen"}) == Path("/tmp/chosen/cache/compatibility-v1.json")


def test_lookup_fetches_the_given_url_once_and_caches_the_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One fetch of the URL the lookup was given serves every explanation, and its bytes land in the cache."""
    now = datetime.now(timezone.utc)
    payload = json.dumps(a_feed(generated=now)).encode()
    calls: list[str] = []

    def fetch(url: str, **kwargs: object) -> bytes:
        calls.append(url)
        return payload

    monkeypatch.setattr(status, "read_metadata", fetch)
    cache = tmp_path / "cache" / "compatibility-v1.json"
    lookup = CompatibilityLookup(cache, "0.2.14", "https://test.example/feed.json")
    assert "Update DevCapsule to 0.9.9" in lookup.explain("codex", "codex-v1", "linux-amd64")
    lookup.explain("claude-code", "claude-code-v1", "linux-amd64")
    assert calls == ["https://test.example/feed.json"]
    assert cache.read_bytes() == payload


def test_lookup_without_a_url_reads_the_variable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A lookup constructed without a URL fetches the one ``DEVCAPSULE_STATUS_URL`` names."""
    monkeypatch.setenv("DEVCAPSULE_STATUS_URL", "https://test.example/other.json")
    seen: list[str] = []

    def record(url: str, **kwargs: object) -> bytes:
        seen.append(url)
        return unreachable(url)

    monkeypatch.setattr(status, "read_metadata", record)
    CompatibilityLookup(tmp_path / "cache.json", "0.2.14").explain("codex", "codex-v1", "linux-amd64")
    assert seen == ["https://test.example/other.json"]


def test_unreachable_feed_falls_back_to_the_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the fetch fails and a valid cached feed exists, its advice is given and the text says it is cached."""
    now = datetime.now(timezone.utc)
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps(a_feed(generated=now - timedelta(hours=1))))
    monkeypatch.setattr(status, "read_metadata", unreachable)
    text = CompatibilityLookup(cache, "0.2.14", "https://test.example/feed.json").explain("codex", "codex-v1", "linux-amd64")
    assert "unavailable (OSError)" in text and "Using cached status metadata." in text
    assert "Update DevCapsule to 0.9.9" in text


def test_unreachable_feed_and_no_cache_fall_back_to_the_embedded_feed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no fetch and no cache, the feed built into the launcher answers, and the text says so."""
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(status, "read_metadata", unreachable)
    monkeypatch.setattr(status, "embedded_feed", lambda: json.dumps(a_feed(generated=now - timedelta(hours=1))).encode())
    text = CompatibilityLookup(tmp_path / "absent.json", "0.2.14", "https://test.example/feed.json").explain(
        "codex", "codex-v1", "linux-amd64")
    assert "Using the status metadata built into this launcher." in text
    assert "Update DevCapsule to 0.9.9" in text


def test_embedded_feed_advises_by_the_advisory_window_not_the_feed_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A feed built in weeks ago is past its two-day validity, yet its advisory still applies within the advisory's
    own 30-day review window; the same feed read from the cache is stale, as a publication must be."""
    now = datetime.now(timezone.utc)
    old = json.dumps(a_feed(generated=now - timedelta(days=20))).encode()
    monkeypatch.setattr(status, "read_metadata", unreachable)
    monkeypatch.setattr(status, "embedded_feed", lambda: old)
    embedded = CompatibilityLookup(tmp_path / "absent.json", "0.2.14", "u").explain("codex", "codex-v1", "linux-amd64")
    assert "Update DevCapsule to 0.9.9" in embedded and "stale" not in embedded
    cache = tmp_path / "cache.json"
    cache.write_bytes(old)
    cached = CompatibilityLookup(cache, "0.2.14", "u").explain("codex", "codex-v1", "linux-amd64")
    assert "stale" in cached and "Update DevCapsule" not in cached


def test_embedded_feed_past_its_advisory_window_gives_no_advice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An embedded advisory reviewed 40 days ago is outside its 30-day window: the launcher says the diagnosis
    needs review instead of advising from it."""
    now = datetime.now(timezone.utc)
    feed = a_feed(generated=now - timedelta(days=40), advisory_reviewed=now - timedelta(days=40))
    monkeypatch.setattr(status, "read_metadata", unreachable)
    monkeypatch.setattr(status, "embedded_feed", lambda: json.dumps(feed).encode())
    text = CompatibilityLookup(tmp_path / "absent.json", "0.2.14", "u").explain("codex", "codex-v1", "linux-amd64")
    assert "needs review" in text and "Update DevCapsule" not in text


def test_nothing_reachable_cached_or_embedded_still_explains(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With the fetch failing, no cache and no embedded feed, ``explain`` returns text and raises nothing."""
    monkeypatch.setattr(status, "read_metadata", unreachable)
    monkeypatch.setattr(status, "embedded_feed", lambda: None)
    text = CompatibilityLookup(tmp_path / "absent.json", "0.2.14", "u").explain("codex", "codex-v1", "linux-amd64")
    assert "No maintained diagnosis is available" in text and status.STATUS_PAGE in text


@pytest.mark.parametrize("broken", [b"not json", b'{"format": 2}', b"x" * (status.FEED_LIMIT + 1)])
def test_a_broken_embedded_feed_is_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, broken: bytes) -> None:
    """An embedded resource that is not a format-1 feed, or exceeds the size bound, counts as absent."""
    monkeypatch.setattr(status, "read_metadata", unreachable)
    monkeypatch.setattr(status, "embedded_feed", lambda: broken)
    text = CompatibilityLookup(tmp_path / "absent.json", "0.2.14", "u").explain("codex", "codex-v1", "linux-amd64")
    assert "No maintained diagnosis is available" in text


def test_embedded_feed_is_absent_in_a_source_run() -> None:
    """A source checkout packages no snapshot: the resource lookup answers ``None`` rather than raising."""
    assert status.embedded_feed() is None


def test_published_guidance_honours_the_feed_window() -> None:
    """A published feed past its validity gives no advice, while the same feed read as a snapshot does."""
    now = datetime.now(timezone.utc)
    feed = StatusFeed.parse(a_feed(generated=now - timedelta(days=3)))
    assert "stale" in feed.guidance("codex", "codex-v1", "0.2.14", "linux-amd64", now=now)
    assert "Update DevCapsule" in feed.guidance("codex", "codex-v1", "0.2.14", "linux-amd64", now=now, published=False)
