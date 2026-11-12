"""Compatibility guidance must remain useful when either metadata service fails."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import subprocess
import textwrap
from urllib.error import HTTPError

import pytest

from devcapsule import component_status as status
from devcapsule.component_status_publisher import generate, render_page
from devcapsule.components import discovery
from devcapsule.components.catalog import COMPONENTS
from devcapsule.components.channels import ChannelReport, ChannelVersion
from devcapsule.compat import CliError

pytestmark = pytest.mark.legacy


@pytest.fixture
def feed():
    now = datetime.now(timezone.utc)
    return {"format": 1, "generated_at": now.isoformat(), "expires_at": (now + timedelta(days=2)).isoformat(),
            "advisories": [{"id": "fixture-endpoint-change", "component": "codex", "adapters": ["codex-v1"],
                            "cli_versions": ["0.2.14"], "platforms": ["linux-amd64"], "status": "cli-update-required",
                            "message": "Vendor endpoint changed.", "issue_url": status.REPOSITORY + "/issues/123",
                            "fixed_in": "0.2.15", "reviewed_at": now.isoformat(),
                            "expires_at": (now + timedelta(days=30)).isoformat()}]}


def test_guidance_matches_adapter_cli_and_platform_without_claiming_component_health(feed):
    parsed = status.StatusFeed.parse(feed)
    now = datetime.now(timezone.utc)
    guidance = parsed.guidance("codex", "codex-v1", "0.2.14", "linux-amd64", now=now)
    assert "Update DevCapsule to 0.2.15" in guidance
    assert "does not itself upgrade" in guidance and "/issues/123" in guidance
    for component, adapter, cli, platform in [("codex", "codex-v2", "0.2.14", "linux-amd64"),
                                             ("codex", "codex-v1", "0.2.15", "linux-amd64"),
                                             ("codex", "codex-v1", "0.2.14", "linux-arm64"),
                                             ("claude-code", "codex-v1", "0.2.14", "linux-amd64")]:
        assert "no matching diagnosis" in parsed.guidance(component, adapter, cli, platform, now=now)


def test_known_issue_and_expired_review_never_recommend_upgrade(feed):
    item = feed["advisories"][0]
    item.update(status="known-issue", fixed_in=None, cli_versions=["*"], platforms=["*"])
    parsed = status.StatusFeed.parse(feed)
    now = datetime.now(timezone.utc)
    assert "cannot reliably report" in parsed.guidance("codex", "codex-v1", "0.2.14.dev0", "linux-arm64", now=now)
    item["reviewed_at"] = (now - timedelta(days=2)).isoformat()
    item["expires_at"] = (now - timedelta(days=1)).isoformat()
    assert "needs review" in status.StatusFeed.parse(feed).guidance("codex", "codex-v1", "x", "x", now=now)


@pytest.mark.parametrize("change", ["format", "issue", "control", "ttl", "duplicate", "fixed"])
def test_malformed_feed_is_not_actionable(feed, change):
    item = feed["advisories"][0]
    if change == "format":
        feed["format"] = 2
    elif change == "issue":
        item["issue_url"] = "https://elsewhere.test/issues/123"
    elif change == "control":
        item["message"] = "hello\x1b[2J"
    elif change == "ttl":
        feed["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    elif change == "duplicate":
        feed["advisories"].append(deepcopy(item))
    elif change == "fixed":
        item["fixed_in"] = "latest"
    with pytest.raises(ValueError):
        status.StatusFeed.parse(feed)


def test_fallback_single_request_cache_offline_stale_and_unknown_format(tmp_path, monkeypatch, feed):
    calls = []
    def download(url, **kwargs):
        calls.append(url)
        return json.dumps(feed).encode()
    monkeypatch.setattr(status, "read_metadata", download)
    cache = tmp_path / "status.json"
    lookup = status.CompatibilityLookup(cache, "0.2.14")
    assert "Update DevCapsule" in lookup.explain("codex", "codex-v1", "linux-amd64")
    lookup.explain("claude-code", "claude-code-v1", "linux-amd64")
    assert calls == [status.FEED_URL]  # no project path, version or credentials sent
    def offline(*args, **kwargs):
        raise HTTPError(status.FEED_URL, 404, "missing", None, None)
    monkeypatch.setattr(status, "read_metadata", offline)
    text = status.CompatibilityLookup(cache, "0.2.14").explain("codex", "codex-v1", "linux-amd64")
    assert "cached" in text and "Update DevCapsule" in text
    now = datetime.now(timezone.utc)
    feed.update(generated_at=(now-timedelta(days=4)).isoformat(), expires_at=(now-timedelta(days=1)).isoformat())
    cache.write_text(json.dumps(feed))
    text = status.CompatibilityLookup(cache, "0.2.14").explain("codex", "codex-v1", "linux-amd64")
    assert "stale" in text and "Update DevCapsule" not in text
    cache.write_text('{"format":2}')
    text = status.CompatibilityLookup(cache, "0.2.14").explain("codex", "codex-v1", "linux-amd64")
    assert "remains unknown" in text and status.STATUS_PAGE in text


def test_future_feed_and_expired_advisories_do_not_gain_freshness_from_publication(feed):
    now = datetime.now(timezone.utc)
    feed.update(generated_at=(now+timedelta(days=1)).isoformat(), expires_at=(now+timedelta(days=2)).isoformat())
    text = status.StatusFeed.parse(feed).guidance("codex", "codex-v1", "0.2.14", "linux-amd64", now=now)
    assert "future" in text and "Update DevCapsule" not in text


def test_metadata_transport_bounds_and_json_parsing(monkeypatch):
    monkeypatch.setattr(discovery, "urlopen", lambda *a, **k: io.BytesIO(b"x" * 20))
    with pytest.raises(ValueError, match="size limit"):
        discovery.read_metadata("https://example.test", limit=10)
    with pytest.raises(ValueError):
        discovery.read_json("https://example.test")


def test_truncated_status_response_cannot_break_the_original_check(tmp_path, monkeypatch):
    def truncated(*args, **kwargs):
        raise IncompleteRead(b"{", 400)
    monkeypatch.setattr(status, "read_metadata", truncated)
    text = status.CompatibilityLookup(tmp_path / "missing-cache", "0.2.14").explain("codex", "codex-v1", "linux-amd64")
    assert "IncompleteRead" in text and "remains unknown" in text


@pytest.mark.parametrize("name,document", [
    ("intellij", {"IIU": [{"type": "release", "version": "2026.2.3", "downloads": {"linux": {"link": "url", "checksumLink": "checksum"}}}]}),
    ("playwright", {"info": {"version": "1.63.0"}, "urls": [{"packagetype": "bdist_wheel", "yanked": False}]}),
    ("pycharm", {"PCP": [{"type": "release", "version": "2026.2.3", "downloads": {"linux": {"link": "url", "checksumLink": "checksum"}}}]}),
    ("codium", {"tag_name": "1.135.06055", "draft": False, "prerelease": False, "assets": [{"name": "VSCodium-linux-x64-1.135.06055.tar.gz"}]}),
    ("claude-code", {"version": "2.1.278", "platforms": {"linux-x64": {"checksum": "digest"}}}),
    ("antigravity-cli", {"version": "1.2.7", "url": "url", "sha512": "digest"}),
])
def test_vendor_release_signals_are_discovery_only(monkeypatch, name, document):
    monkeypatch.setattr(discovery, "read_json", lambda url: document)
    monkeypatch.setattr(discovery, "read_metadata", lambda *a, **k: b"2.1.278")
    channel = COMPONENTS[name].discovery_channel()
    assert channel is not None
    report = channel.check("1.0.0", "linux-amd64")
    assert report.candidates and report.current.status == "unknown" and not report.current.notices
    assert not hasattr(channel, "select")
    assert channel.check("9999.0.0", "linux-amd64").candidates == ()
    monkeypatch.setattr(discovery, "read_json", lambda url: {"changed": "schema"})
    with pytest.raises(CliError, match="unavailable"):
        channel.check("1.0.0", "linux-amd64")


def test_postgresql_major_only_lock_does_not_invent_a_missing_minor(monkeypatch):
    rows = [{"major": "16", "latestMinor": "15", "supported": True, "eolDate": "2028-11-09"}]
    monkeypatch.setattr(discovery, "read_json", lambda url: rows)
    channel = discovery.PostgresqlDiscovery()
    report = channel.check("16", "linux-amd64")
    assert not report.candidates and "installed minor is not recorded" in report.current.detail
    assert "16.15" in report.current.detail
    assert channel.check("16.12", "linux-amd64").candidates[0].version == "16.15"
    rows[0].update(supported=False, eolDate="2020-01-01")
    report = channel.check("16", "linux-amd64")
    assert report.current.notices[0].kind == "end-of-support" and not report.candidates


def test_publisher_partial_failure_preserves_evidence_without_inventing_diagnosis(monkeypatch, feed):
    policy = json.loads((Path(__file__).parents[2] / "component-status/policy-v1.json").read_text())
    class Channel:
        def check(self, current, platform):
            return ChannelReport("fixture source", ChannelVersion(current, "available"), ())
    for component in COMPONENTS.values():
        monkeypatch.setattr(component, "discovery_channel", lambda: Channel())
    before = generate(policy, {}, revision="abc")
    class Broken:
        def check(self, current, platform):
            raise RuntimeError("<script>bad</script> | new schema")
    monkeypatch.setattr(COMPONENTS["codex"], "discovery_channel", lambda: Broken())
    after = generate(policy, before, revision="abc")
    row = next(row for row in after["observations"] if row["component"] == "codex")
    assert row["result"] == "inconclusive" and row["consecutive_failures"] == 1
    assert row["last_success_at"] == before["generated_at"]
    assert after["advisories"] == []
    page = render_page(after)
    assert "<script>" not in page and "&#60;script&#62;" in page
    assert "No maintained diagnoses" in page and "stale" in page
    policy["advisories"] = feed["advisories"]
    after = generate(policy, after, revision="abc")
    assert after["advisories"] == feed["advisories"]  # scheduled job never renews reviews
    assert "Issue and workarounds" in render_page(after)


def test_all_catalog_definitions_have_discovery_and_stable_adapter_ids():
    for name, definition in COMPONENTS.items():
        assert definition.discovery_channel() is not None
        assert definition.discovery_adapter_id() == name + "-v1"


def test_workflow_publication_creates_and_advances_only_status_branch(tmp_path):
    """Execute the actual workflow shell against a local bare Git remote."""
    workflow = (Path(__file__).parents[2] / ".github/workflows/component-status.yml").read_text()
    read_step = workflow.split("      - name: Read previous publication\n", 1)[1].split("      - name: Probe vendors", 1)[0]
    publish_step = workflow.split("      - name: Publish together without changing main or the website\n", 1)[1]
    read_script = textwrap.dedent(read_step.split("        run: |\n", 1)[1])
    publish_script = textwrap.dedent(publish_step.split("        run: |\n", 1)[1])
    source, remote, runner = (tmp_path / name for name in ("source", "remote.git", "runner"))
    source.mkdir()
    runner.mkdir()
    def git(*args):
        return subprocess.check_output(["git", *map(str, args)], cwd=source, text=True).strip()
    git("init", "--bare", remote)
    git("init", "-b", "main")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.test")
    git("commit", "--allow-empty", "-m", "source")
    git("remote", "add", "origin", remote)
    git("push", "origin", "main")
    original = git("rev-parse", "HEAD")
    output = runner / "component-status"
    output.mkdir()
    (output / "README.md").write_text("First page\n")
    (output / "compatibility-v1.json").write_text('{"first":true}\n')
    env = {**os.environ, "RUNNER_TEMP": str(runner), "GITHUB_STEP_SUMMARY": str(runner / "summary")}
    for content in ("First page\n", "Second page\n"):
        subprocess.run(["bash", "-e", "-o", "pipefail", "-c", read_script], cwd=source, env=env, check=True)
        (output / "README.md").write_text(content)
        subprocess.run(["bash", "-e", "-o", "pipefail", "-c", publish_script], cwd=source, env=env, check=True)
    assert git("--git-dir", remote, "show", "component-status:README.md") == "Second page"
    assert git("--git-dir", remote, "rev-list", "--count", "component-status") == "2"
    assert git("--git-dir", remote, "rev-parse", "main") == original
    assert git("branch", "--show-current") == "main" and git("status", "--porcelain") == ""
