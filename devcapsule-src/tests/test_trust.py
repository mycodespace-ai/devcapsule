"""Home trust (D-0011): a vendor's channel accepted once per computer, for every project and version."""

from __future__ import annotations

import io
import json
import sys
from dataclasses import replace
from pathlib import Path
import tomllib

import pytest

from devcapsule import cli
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.compat import DecisionPending
from devcapsule.configuration.authorization import review_authorizations
from devcapsule.configuration.capability_commands import paths
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.storage import checkout_record_paths, load_toml, load_trust, manifest_for, settings_path
from devcapsule.configuration.file_formats import render_toml
from devcapsule.configuration.trust import BASE_CHANNEL, Channel, HomeTrust, channels_for

pytestmark = pytest.mark.legacy

CLAUDE_TERMS = "https://www.anthropic.com/legal/commercial-terms"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--require", "node", "--creator", "mailto:owner@example.test"]) == 0
    return root


def config(root: Path, *arguments: str) -> int:
    return cli.main(["project", "--path", str(root), "config", *arguments])



def accept(root: Path, channel: str) -> int:
    """Seed the project channel for tests of lock-specific acceptance."""
    from devcapsule.commands._run_flow import accept_channel
    try:
        accept_channel(root, manifest_for(root)[1], channel)
    except ProjectConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def withdraw(channel: str) -> int:
    return cli.main(["home", "trust", "withdraw", channel])

def lock_path(root: Path) -> Path:
    return root / ".devcapsule" / "devcapsule.linux-amd64.lock"


def pin_claude_code(root: Path, version: str) -> None:
    lock = tomllib.loads(lock_path(root).read_text())
    lock["components"]["claude-code"] = {
        "version": version, "acquisition-authorization": "claude-code-download", "terms-url": CLAUDE_TERMS,
        "delivery-policy": "local-materialization",
        "artifacts": {"linux-amd64": {"url": f"https://downloads.example.test/claude-{version}", "sha256": "e" * 64}},
    }
    lock_path(root).write_text(render_toml(lock))


def reviews(root: Path) -> dict:
    _root, manifest = manifest_for(root)
    record = load_toml(checkout_record_paths(manifest, root)[0])
    return {item.name: item for item in review_authorizations(manifest, load_toml(lock_path(root)), record,
                                                              HomeTrust.read(load_trust()))}


def test_channels_are_the_locks_base_and_vendor_products(project: Path) -> None:
    channels = channels_for(load_toml(lock_path(project)))
    assert list(channels) == [BASE_CHANNEL]
    base = channels[BASE_CHANNEL]
    assert base.authorization == "base-image" and base.vendor == "DevCapsule"
    assert "docker.io/mycodespaceai/devcapsule-base" in base.statement() and "every version" in base.statement()
    pin_claude_code(project, "1.0.0")
    channels = channels_for(load_toml(lock_path(project)))
    claude = channels["claude-code"]
    assert (claude.vendor, claude.origins, claude.terms_url, claude.authorization) == (
        "Anthropic", ("https://downloads.example.test",), CLAUDE_TERMS, "claude-code-download")
    # A base outside DevCapsule's repository is a departure: no channel, per-checkout consent as before.
    lock = tomllib.loads(lock_path(project).read_text())
    lock["base"]["reference"] = "registry.example.test/other-base@sha256:" + "a" * 64
    assert BASE_CHANNEL not in channels_for(lock)


def test_the_record_round_trips_and_covers_only_what_was_accepted() -> None:
    channel = Channel("claude-code", "Anthropic", "Claude Code", ("downloads.example.test",), "sha", CLAUDE_TERMS)
    trust = HomeTrust().with_channel(channel)
    reloaded = HomeTrust.read(tomllib.loads(render_toml(trust.document())))
    assert reloaded.covers(channel) and reloaded.channels["claude-code"]["accepted"]
    assert HomeTrust.read({"trust": trust.document()}).covers(channel)  # the merged home document
    moved = Channel("claude-code", "Anthropic", "Claude Code", ("downloads.example.test", "cdn.example.test"), "sha", CLAUDE_TERMS)
    assert not reloaded.covers(moved)  # a new origin asks again
    assert not reloaded.covers(Channel("claude-code", "Anthropic", "Claude Code", channel.origins, "sha", "https://other/terms"))
    assert not reloaded.without("claude-code").channels
    assert reloaded.without("codex") == reloaded
    with pytest.raises(ProjectConfigurationError, match="must name its vendor"):
        HomeTrust.read({"channels": {"x": {"origins": []}}})


def test_a_trusted_vendor_covers_every_version_and_a_denial_still_wins(project: Path, capsys) -> None:
    pin_claude_code(project, "1.0.0")
    assert reviews(project)["claude-code-download"].status == "missing-required"
    assert accept(project, "claude-code") == 0
    review = reviews(project)["claude-code-download"]
    assert (review.status, review.trusted_channel, review.problem) == ("trusted", "claude-code", None)
    pin_claude_code(project, "1.1.0")  # the software-approval question of D-0012 does not arise
    assert reviews(project)["claude-code-download"].status == "trusted"
    assert config(project, "authorize", "claude-code-download", "false") == 0
    review = reviews(project)["claude-code-download"]
    assert review.trusted_channel is None and review.recorded == "false"
    capsys.readouterr()
    assert config(project, "trust", "list") == 0
    assert "Anthropic" in capsys.readouterr().out


def test_a_real_run_launches_on_the_homes_trust_alone(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every reader of the base selection takes the trust: the realization, the history, the plan."""
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr("sys.stdin", io.StringIO("python-ide\ny\n"))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    assert invoke(project, "run", "--no-update-check") == 0
    assert launch.call_count == 1
    _root, manifest = manifest_for(project)
    assert "base-image" not in load_toml(checkout_record_paths(manifest, project)[0]).get("authorization", {})
    assert "devcapsule-base" in load_toml(settings_path())["trust"]["channels"]
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert invoke(project, "run", "--no-update-check") == 0  # the second launch asks nothing


def test_acceptance_binds_integrity_and_preserves_previously_accepted_origins() -> None:
    channel = Channel("vendor", "Vendor", "Product", ("https://one.test", "https://two.test"), "SHA-256", "https://terms.test")
    trust = HomeTrust.read(tomllib.loads(render_toml(HomeTrust().with_channel(channel).document())))
    assert not trust.covers(replace(channel, integrity="MD5"))
    assert not trust.covers(replace(channel, origins=()))
    assert not trust.covers(replace(channel, vendor="Another vendor"))
    subset = replace(channel, origins=("https://one.test",))
    assert trust.with_channel(subset).document() == trust.document()
    added = replace(channel, origins=("https://three.test",))
    extended = trust.with_channel(added)
    assert extended.covers(channel) and extended.covers(added)
    changed_terms = replace(added, terms_url="https://terms.test/new")
    assert not extended.with_channel(changed_terms).covers(channel)
    document = trust.document()
    del document["channels"]["vendor"]["integrity"]
    assert not HomeTrust.read(document).covers(channel)


@pytest.mark.parametrize("broken", ["http", "file", "credentials", "digest", "artifacts", "terms"])
def test_unverifiable_lock_cannot_create_or_widen_acceptance(project: Path, broken: str, capsys) -> None:
    pin_claude_code(project, "1.0.0")
    assert accept(project, "claude-code") == 0
    before = settings_path().read_bytes()
    lock = load_toml(lock_path(project))
    metadata = lock["components"]["claude-code"]
    artifact = metadata["artifacts"]["linux-amd64"]
    if broken in {"http", "file", "credentials"}:
        artifact["url"] = {"http": "http://downloads.example.test/claude", "file": "file:///local/claude",
                           "credentials": "https://user@downloads.example.test/claude"}[broken]
    elif broken == "digest":
        artifact["sha256"] = "not-a-digest"
    elif broken == "terms":
        metadata["terms-url"] = "https://new.example.test/terms"
    else:
        del metadata["artifacts"]
    lock_path(project).write_text(render_toml(lock))
    assert accept(project, "claude-code") == 2
    assert "No channel 'claude-code'" in capsys.readouterr().err
    assert settings_path().read_bytes() == before


def test_trusted_base_replaces_old_published_consent_through_realization(project: Path, monkeypatch, capsys) -> None:
    from tests.test_upgrade_recovery import OLD_BASE, install_external_fakes, invoke
    assert config(project, "ide", "python-ide") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    assert accept(project, BASE_CHANNEL) == 0
    _, manifest = manifest_for(project)
    input_path, output_path = checkout_record_paths(manifest, project)
    record = load_toml(input_path)
    record["authorization"]["base-image"]["reference"] = OLD_BASE  # This old base would also require host X11.
    input_path.write_text(render_toml(record))
    before = input_path.read_bytes()
    assert config(project, "check") == 0
    prepared = prepare_launch(project, RunFlags(), interactive=False)
    expected = load_toml(lock_path(project))["base"]["reference"]
    assert prepared.selected.resolution["authorization"]["base-image"]["reference"] == expected
    assert load_toml(output_path)["authorization"]["base-image"]["reference"] == expected
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert invoke(project, "run", "--no-update-check") == 0
    assert launch.call_count == 1 and input_path.read_bytes() == before


@pytest.mark.parametrize("value", [False, "false", "none", "invalid"])
def test_trust_never_overrides_a_normalized_denial_or_invalid_answer(project: Path, value: bool | str) -> None:
    pin_claude_code(project, "1.0.0")
    assert accept(project, "claude-code") == 0
    assert config(project, "authorize", "claude-code-download", "true") == 0
    _, manifest = manifest_for(project)
    input_path, _ = checkout_record_paths(manifest, project)
    record = load_toml(input_path)
    record["authorization"]["claude-code-download"]["value"] = value
    input_path.write_text(render_toml(record))
    review = reviews(project)["claude-code-download"]
    assert review.trusted_channel is None and review.problem is not None
    assert review.status == ("invalid" if value == "invalid" else "denied")


def test_foreign_base_still_requires_checkout_consent(project: Path) -> None:
    assert config(project, "drop", "node") == 0
    assert accept(project, BASE_CHANNEL) == 0
    lock = load_toml(lock_path(project))
    lock["base"]["reference"] = "registry.example.test/base@sha256:" + "b" * 64
    lock_path(project).write_text(render_toml(lock))
    with pytest.raises(DecisionPending, match="consent base-image"):
        prepare_launch(project, RunFlags(ide="python-ide"), interactive=False, check_display=False)
    assert reviews(project)["base-image"].trusted_channel is None
    assert config(project, "authorize", "base-image", "default") == 0
    prepared = prepare_launch(project, RunFlags(ide="python-ide"), interactive=False, check_display=False)
    assert prepared.selected.resolution["authorization"]["base-image"]["reference"] == lock["base"]["reference"]


@pytest.mark.parametrize("content", ['bad = [', 'trust = "broken"', 'channels = 4',
                                       '[channels.x]\nvendor = "X"\norigins = 4',
                                       '[channels.x]\nvendor = "X"\nintegrity = 7'])
def test_corrupt_trust_is_reported_and_never_rewritten(project: Path, content: str, capsys) -> None:
    settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_path().write_text(content)
    for arguments in (("trust", "list"), ("show",), ("check",), ("trust", "accept", BASE_CHANNEL), ("trust", "withdraw", BASE_CHANNEL)):
        assert config(project, *arguments) == 2
        assert str(settings_path()) in capsys.readouterr().err
        assert settings_path().read_text() == content


@pytest.mark.parametrize("accepted", [False, True])
def test_inspection_and_pending_trust_leave_all_files_unchanged(project: Path, tmp_path: Path, accepted: bool) -> None:
    from tests.test_run_flow import snapshot
    if accepted:
        assert accept(project, BASE_CHANNEL) == 0
    before = snapshot(tmp_path)
    assert config(project, "trust", "list") == 0
    assert config(project, "show") == 0
    assert config(project, "check") == 3
    with pytest.raises(DecisionPending, match="Nothing was written"):
        prepare_launch(project, RunFlags(trust=(BASE_CHANNEL,)), interactive=False)
    assert snapshot(tmp_path) == before


def test_trust_write_is_private_atomic_and_keeps_previous_record_on_failure(project: Path, monkeypatch) -> None:
    from devcapsule.configuration.storage import write_settings
    assert accept(project, BASE_CHANNEL) == 0
    before = settings_path().read_bytes()
    original = Path.replace
    replacements = []
    def fail_replace(source: Path, target: Path) -> Path:
        if target == settings_path():
            assert source.parent == target.parent and source != target
            assert source.stat().st_mode & 0o777 == 0o600
            assert target.read_bytes() == before
            replacements.append(source)
            raise OSError("replacement failed")
        return original(source, target)
    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement failed"):
        write_settings({"trust": HomeTrust().document()})
    assert len(replacements) == 1 and not replacements[0].exists()
    assert settings_path().read_bytes() == before


def test_withdraw_keeps_saved_plan_and_running_session_but_blocks_next_launch(project: Path, monkeypatch) -> None:
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    assert config(project, "ide", "python-ide") == 0
    prepared = prepare_launch(project, RunFlags(trust=(BASE_CHANNEL,)), interactive=False)
    before = prepared.selected.resolution_path.read_bytes()
    launch = install_external_fakes(monkeypatch, [])
    assert withdraw(BASE_CHANNEL) == 0
    assert launch.call_count == 0 and prepared.selected.resolution_path.read_bytes() == before
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert invoke(project, "run", "--no-update-check") == 3
    assert launch.call_count == 0 and prepared.selected.resolution_path.read_bytes() == before
    # Separate, explicit checkout consent survives withdrawal.
    assert config(project, "authorize", "base-image", "default") == 0
    assert invoke(project, "run", "--no-update-check") == 0
    assert launch.call_count == 1


def test_legacy_reader_without_trust_still_requires_its_checkout_consent(project: Path) -> None:
    from devcapsule.configuration.model import Configuration
    assert config(project, "ide", "python-ide") == 0
    prepared = prepare_launch(project, RunFlags(trust=(BASE_CHANNEL,)), interactive=False)
    selected = prepared.selected
    assert "base-image" not in selected.checkout.get("authorization", {})
    legacy = Configuration(selected.manifest, selected.lock, selected.checkout)
    assert not legacy.review().ready
    with pytest.raises(ProjectConfigurationError, match="incomplete"):
        legacy.resolve()


def test_trusted_channel_does_not_replace_local_image_in_the_plan(project: Path, monkeypatch) -> None:
    from tests.test_environment_realization import base_image
    assert config(project, "ide", "python-ide") == 0
    assert accept(project, BASE_CHANNEL) == 0
    _, manifest = manifest_for(project)
    input_path, _ = checkout_record_paths(manifest, project)
    record = load_toml(input_path)
    identity = "sha256:" + "c" * 64
    record.setdefault("authorization", {})["base-image"] = {"reference": "local/base:mine", "image-id": identity}
    input_path.write_text(render_toml(record))
    seen = []
    def inspect(reference: str):
        seen.append(reference)
        return base_image(reference, identity)
    monkeypatch.setattr("devcapsule.configuration.operations.required_local_image", inspect)
    prepared = prepare_launch(project, RunFlags(), interactive=False, check_display=False)
    assert seen == ["local/base:mine"]
    base = prepared.selected.resolution["authorization"]["base-image"]
    assert base["reference"] == "local/base:mine" and base["image-id"] == identity
    record["authorization"]["base-image"]["image-id"] = "invalid"
    input_path.write_text(render_toml(record))
    with pytest.raises(DecisionPending, match="consent base-image"):
        prepare_launch(project, RunFlags(), interactive=False, check_display=False)


def test_terminal_acceptance_stays_staged_if_a_later_answer_is_missing(project: Path, tmp_path: Path) -> None:
    from tests.test_run_flow import snapshot
    assert config(project, "ide", "python-ide") == 0
    assert config(project, "require", "env", "DATABASE", "--because", "tests need it") == 0
    before = snapshot(tmp_path)
    output = io.StringIO()
    with pytest.raises(DecisionPending, match="nothing was written"):
        prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO("y\n"), output_stream=output)
    assert "Trust will be saved when all required answers are complete" in output.getvalue()
    assert "this DevCapsule home" in output.getvalue()
    assert snapshot(tmp_path) == before
