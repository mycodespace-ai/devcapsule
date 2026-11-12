"""Software approvals: new versions of vendor software approved before are one question at launch.

The owner's direction of 2026-10-22. The fixtures are the upgrade-recovery
module's: a resolved checkout of the fixture project, driven through the
real command line.
"""

from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import json
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from devcapsule import runtime_configuration, version_sets
from devcapsule.commands import _software_approvals as offer
from devcapsule.configuration.approvals import pending_software_approvals, render_software_approvals
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.storage import interrupted_activation, load_toml, manifest_for
from tests.test_upgrade_recovery import checkout, install_external_fakes, invoke, review  # noqa: F401

pytestmark = pytest.mark.legacy

CLAUDE_TERMS = "https://www.anthropic.com/legal/commercial-terms"
ANTIGRAVITY_TERMS = "https://antigravity.google/terms/"
GUIDE = "https://devcapsule.mycodespace.ai/docs/current/configuration/software-approvals/"


def lock_path(project: Path) -> Path:
    return project / ".devcapsule" / "devcapsule.linux-amd64.lock"


def pin(project: Path, component: str, authorization: str, terms: str, version: str) -> None:
    """Pin a vendor component in the lock at ``version``, replacing an earlier pin."""
    path = lock_path(project)
    lock = tomllib.loads(path.read_text())
    lock["components"][component] = {
        "version": version, "acquisition-authorization": authorization, "terms-url": terms,
        "delivery-policy": "local-materialization",
        "artifacts": {"linux-amd64": {"url": f"https://example.test/{component}-{version}", "sha256": "e" * 64}},
    }
    if component == "antigravity-cli":
        lock["components"][component]["artifacts"]["linux-amd64"]["archive-member"] = "bin/antigravity"
    from devcapsule.configuration.file_formats import render_toml
    path.write_text(render_toml(lock))


def approved_then_bumped(project: Path, record: Path) -> None:
    """A checkout that approved Claude Code 1.0.0 and whose lock now pins 1.1.0."""
    pin(project, "claude-code", "claude-code-download", CLAUDE_TERMS, "1.0.0")
    assert invoke(project, "config", "authorize", "base-image", "default") == 0
    assert invoke(project, "config", "authorize", "claude-code-download", "true") == 0
    assert run_until_prepared(project) == 0
    pin(project, "claude-code", "claude-code-download", CLAUDE_TERMS, "1.1.0")
    assert review(project, record).ready is False


def pending(project: Path, record: Path):
    _root, manifest = manifest_for(project)
    return pending_software_approvals(manifest, load_toml(lock_path(project)), load_toml(record))


def test_a_bumped_approved_download_is_a_software_approval(checkout) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    approvals = pending(project, record)
    assert approvals is not None and [a.name for a in approvals] == ["claude-code-download"]
    approval = approvals[0]
    assert (approval.component, approval.vendor, approval.version, approval.previous_version) == (
        "claude-code", "Anthropic", "1.1.0", None,
    )
    assert approval.change == "1.1.0"
    lines = render_software_approvals(approvals)
    assert lines[1] == f"- Claude Code 1.1.0, downloaded from Anthropic under {CLAUDE_TERMS} (claude-code-download)"


def test_trusted_vendor_suppresses_the_version_approval_offer(checkout, monkeypatch) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    from tests.test_trust import accept
    assert accept(project, "claude-code") == 0
    _, manifest = manifest_for(project)
    assert offer.pending_for(project, manifest) == ()
    monkeypatch.setattr(offer, "confirmation_key", lambda: pytest.fail("trusted vendor asked again"))
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert invoke(project, "run", "--authorize", "host-x11", "true", "--no-update-check") == 0
    assert launch.call_count == 1
    assert invoke(project, "config", "authorize", "claude-code-download", "false") == 0
    assert offer.pending_for(project, manifest) is None


def test_nothing_pending_is_an_empty_list(checkout) -> None:
    project, record, _ = checkout
    pin(project, "claude-code", "claude-code-download", CLAUDE_TERMS, "1.0.0")
    assert invoke(project, "config", "authorize", "base-image", "default") == 0
    assert invoke(project, "config", "authorize", "claude-code-download", "true") == 0
    assert pending(project, record) == ()


@pytest.mark.parametrize("other", ["missing-consent", "denied-then-bumped", "stale-host-access", "missing-base"])
def test_any_other_pending_decision_disqualifies_the_list(checkout, other: str) -> None:
    """A missing consent, a denial, or a host-access decision in the list is decided one by one."""
    project, record, _ = checkout
    approved_then_bumped(project, record)
    if other == "missing-consent":
        pin(project, "antigravity-cli", "antigravity-download", ANTIGRAVITY_TERMS, "2.0.0")
    elif other == "denied-then-bumped":
        pin(project, "antigravity-cli", "antigravity-download", ANTIGRAVITY_TERMS, "2.0.0")
        assert invoke(project, "config", "authorize", "antigravity-download", "false") == 0
        pin(project, "antigravity-cli", "antigravity-download", ANTIGRAVITY_TERMS, "2.1.0")
    elif other == "missing-base":
        document = load_toml(record)
        del document["authorization"]["base-image"]
        record.write_text(render_toml(document))
    else:
        manifest_path = project / ".devcapsule/devcapsule.toml"
        manifest_path.write_text(manifest_path.read_text() + '\n[host.browser.host-open.recommended]\nvalue = true\njustification = "Open links on the host."\n')
        assert invoke(project, "config", "authorize", "host-browser", "true") == 0
        manifest_path.write_text(manifest_path.read_text().replace('"Open links on the host."', '"Open links on the host, changed."'))
    if other == "stale-host-access":
        # A host answer under a changed recommendation is kept, not pending
        # (D-0012, answer 23): the approvals stay one question.
        approvals = pending(project, record)
        assert approvals is not None and [item.name for item in approvals] == ["claude-code-download"]
    else:
        assert pending(project, record) is None


def test_the_previous_version_comes_from_the_newest_known_good_record(checkout) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    from devcapsule.configuration.file_formats import render_toml
    known_good = version_sets.state_directory(project) / "known-good"
    known_good.mkdir(parents=True, exist_ok=True)
    older = {"components": {"claude-code": {"version": "0.9.0"}}}
    newer = {"components": {"claude-code": {"version": "1.0.0"}}}
    (known_good / "newer.toml").write_text(render_toml({"lock": render_toml(newer), "last-success": 20}))
    (known_good / "older.toml").write_text(render_toml({"lock": render_toml(older), "last-success": 10}))
    (known_good / "broken.toml").write_text("not = [toml")
    # Neither file order nor modification time determines the last launch.
    with patch.object(Path, "glob", return_value=iter([
        known_good / "newer.toml", known_good / "older.toml", known_good / "broken.toml",
    ])):
        assert offer.previous_versions(project) == {"claude-code": "1.0.0"}
    _root, manifest = manifest_for(project)
    approvals = offer.pending_for(project, manifest)
    assert approvals is not None and approvals[0].change == "1.0.0 to 1.1.0"


def test_run_asks_once_and_launches_on_y(checkout, monkeypatch, capsys) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    events: list = []
    launch = install_external_fakes(monkeypatch, events)
    monkeypatch.setattr(offer.sys.stdin, "isatty", lambda: True)
    replacements: list[Path] = []
    original_replace = Path.replace

    def replace(source: Path, destination: Path) -> Path:
        result = original_replace(source, destination)
        if destination in (record, resolution):
            replacements.append(destination)
        return result

    def accept() -> str:
        assert events == [] and replacements == []
        return "y"

    monkeypatch.setattr(Path, "replace", replace)
    with patch.object(offer, "confirmation_key", side_effect=accept) as read_key:
        # The fixture's base has no contained desktop: host X11 by explicit consent, for this launch.
        assert invoke(project, "run", "--no-update-check", "--authorize", "host-x11", "true") == 0
    read_key.assert_called_once_with()
    # Atomic record replacement precedes the resolution; the launch derives the plan again.
    assert replacements[:2] == [record, resolution] and set(replacements) == {record, resolution}
    out = capsys.readouterr().out
    assert "Claude Code 1.1.0, downloaded from Anthropic" in out
    assert "Approve all of them? Press y" in out
    assert "Approved 1 software update for this checkout." in out
    assert launch.call_count == 1
    answer = load_toml(record)["authorization"]["claude-code-download"]
    assert answer["value"] is True
    assert review(project, record).ready is True  # the digest is current and the resolution regenerated


@pytest.mark.parametrize("key", ["n", "", EOFError()])
def test_run_stops_on_any_other_key_and_names_the_command_and_the_guide(checkout, monkeypatch, capsys, key) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    before = record.read_bytes(), resolution.read_bytes()
    events: list = []
    launch = install_external_fakes(monkeypatch, events)
    monkeypatch.setattr(offer.sys.stdin, "isatty", lambda: True)
    def read_key():
        if isinstance(key, EOFError):
            raise key
        return key
    monkeypatch.setattr(offer, "confirmation_key", read_key)
    assert invoke(project, "run", "--no-update-check") == 1
    out = capsys.readouterr().out
    assert "Not approved; nothing written." in out
    assert f"devcapsule project --path {project}" not in out  # the path has spaces: it is quoted
    assert "config approve --all" in out and GUIDE in out
    assert "Launch cancelled; no session was started." in out
    assert (record.read_bytes(), resolution.read_bytes()) == before
    assert events == [] and launch.call_count == 0


def test_run_without_a_terminal_stops_with_the_same_instruction(checkout, monkeypatch, capsys) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    before = record.read_bytes(), resolution.read_bytes()
    events: list = []
    launch = install_external_fakes(monkeypatch, events)
    monkeypatch.setattr(offer.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(offer, "confirmation_key", lambda: pytest.fail("read non-terminal stdin"))
    assert invoke(project, "run", "--no-update-check") == 1
    out = capsys.readouterr().out
    assert "No terminal to ask; the launch stops here." in out
    assert "config approve --all" in out and GUIDE in out
    assert (record.read_bytes(), resolution.read_bytes()) == before
    assert events == [] and launch.call_count == 0


def test_run_with_other_pending_decisions_refuses_as_before(checkout, monkeypatch, capsys) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    pin(project, "antigravity-cli", "antigravity-download", ANTIGRAVITY_TERMS, "2.0.0")  # never answered
    launch = install_external_fakes(monkeypatch, [])
    # Without a terminal: a decision only the developer can take ends the
    # launch with status 3, naming it; with one, the launch would ask it.
    monkeypatch.setattr(offer.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(offer, "confirmation_key", lambda: pytest.fail("asked"))
    assert invoke(project, "run", "--no-update-check") == 3
    captured = capsys.readouterr()
    assert "Approve all of them?" not in captured.out
    # The download's channel is the home's question (D-0011), named by its channel.
    assert "antigravity-cli" in captured.err and "Nothing was written" in captured.err
    assert "--trust antigravity-cli" in captured.err
    assert run_until_prepared(project) == 3
    err = capsys.readouterr().err
    assert "antigravity-cli" in err
    assert launch.call_count == 0


def test_print_command_never_asks_or_writes(checkout, monkeypatch, capsys) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    before = record.read_bytes()
    monkeypatch.setattr(offer.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(offer, "confirmation_key", lambda: pytest.fail("asked"))
    assert invoke(project, "run", "--print-command", "--no-update-check") == 3
    assert "claude-code-download" in capsys.readouterr().err
    assert record.read_bytes() == before


def test_config_approve_lists_then_records_all_or_by_name(checkout, capsys) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    pin(project, "antigravity-cli", "antigravity-download", ANTIGRAVITY_TERMS, "2.0.0")
    assert invoke(project, "config", "authorize", "antigravity-download", "true") == 0
    pin(project, "antigravity-cli", "antigravity-download", ANTIGRAVITY_TERMS, "2.1.0")
    # Listing only: nothing written, the command and the guide named.
    before = record.read_bytes()
    before_resolution = resolution.read_bytes()
    assert invoke(project, "config", "approve") == 1
    out = capsys.readouterr().out
    assert "- Antigravity CLI 2.1.0" in out and "- Claude Code 1.1.0" in out
    assert "config approve --all" in out and GUIDE in out
    assert record.read_bytes() == before
    # By name: only that one, the other stays pending.
    assert invoke(project, "config", "approve", "claude-code-download") == 0
    out = capsys.readouterr().out
    assert "Approved 1 software update" in out and "Still pending: antigravity-download" in out
    assert "The resolution is unchanged" in out
    assert resolution.read_bytes() == before_resolution
    approvals = pending(project, record)
    assert approvals is not None and [a.name for a in approvals] == ["antigravity-download"]
    # The rest with --all; the resolution is regenerated and the review is ready.
    assert invoke(project, "config", "approve", "--all") == 0
    assert "Approved 1 software update" in capsys.readouterr().out
    assert pending(project, record) == () and review(project, record).ready is True
    assert invoke(project, "config", "approve") == 0
    assert "No software approvals are pending" in capsys.readouterr().out


def test_config_approve_refuses_unknown_names_and_mixed_lists(checkout, capsys) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    assert invoke(project, "config", "approve", "antigravity-download") == 2
    assert "No software approval is pending for antigravity-download; pending: claude-code-download" in capsys.readouterr().err
    assert invoke(project, "config", "approve", "--all", "claude-code-download") == 2
    assert "--all cannot be combined with NAME" in capsys.readouterr().err
    pin(project, "antigravity-cli", "antigravity-download", ANTIGRAVITY_TERMS, "2.0.0")  # never answered
    assert invoke(project, "config", "approve", "--all") == 2
    assert "not all software approvals" in capsys.readouterr().err


def test_the_approve_command_is_quoted_for_a_path_with_spaces(tmp_path: Path) -> None:
    root = tmp_path / "a checkout"
    assert offer.approve_command(root) == f"devcapsule project --path '{root}' config approve --all"
    assert offer.approve_command(root, ("claude-code-download",)).endswith("config approve claude-code-download")


@pytest.mark.parametrize("value", [False, "true", "default", 1, None])
def test_only_a_literal_true_answer_qualifies(checkout, value) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    document = load_toml(record)
    document["authorization"]["claude-code-download"]["value"] = value
    _, manifest = manifest_for(project)
    assert pending_software_approvals(manifest, load_toml(lock_path(project)), document) is None


def test_a_malformed_individual_answer_does_not_qualify(checkout) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    document = load_toml(record)
    document["authorization"]["claude-code-download"] = True
    _, manifest = manifest_for(project)
    assert pending_software_approvals(manifest, load_toml(lock_path(project)), document) is None


@pytest.mark.parametrize("field,value", [("terms-url", "https://example.test/new-terms"),
                                         ("acquisition-authorization", "another-download")])
def test_a_changed_acquisition_contract_refuses_before_approval(checkout, field, value) -> None:
    project, record, _ = checkout
    approved_then_bumped(project, record)
    lock = load_toml(lock_path(project))
    lock["components"]["claude-code"][field] = value
    _, manifest = manifest_for(project)
    with pytest.raises(ProjectConfigurationError, match=field):
        pending_software_approvals(manifest, lock, load_toml(record))


@pytest.mark.parametrize("operation", [("run",), ("config", "approve", "--all")])
def test_malformed_authorization_table_is_a_controlled_refusal(checkout, capsys, operation) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    document = load_toml(record)
    document["authorization"] = "not a table"
    record.write_text(render_toml(document))
    before = record.read_bytes(), resolution.read_bytes()
    with pytest.raises(ProjectConfigurationError, match="authorization must be a table"):
        pending(project, record)
    assert invoke(project, *operation) == 2
    assert "authorization must be a table" in capsys.readouterr().err
    assert (record.read_bytes(), resolution.read_bytes()) == before


@pytest.mark.parametrize("operation", [("run",), ("config", "approve", "--all")])
@pytest.mark.parametrize("error", [ProjectConfigurationError("fixture resolution failure"),
                                  OSError("fixture resolution failure")])
def test_resolution_failure_keeps_approvals_and_names_recovery(checkout, monkeypatch, capsys, operation, error) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    before_resolution = resolution.read_bytes()
    capsys.readouterr()
    events: list = []
    install_external_fakes(monkeypatch, events)
    monkeypatch.setattr(offer.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(offer, "confirmation_key", lambda: "y")
    with patch.object(offer, "resolve_checkout", side_effect=error) as resolve:
        assert invoke(project, *operation) == 2
    resolve.assert_called_once_with(project)
    assert pending(project, record) == ()  # approvals survived, with current digests
    assert resolution.read_bytes() == before_resolution
    assert events == []
    err = capsys.readouterr().err
    assert "Approvals were saved, but resolution failed" in err
    assert "fixture resolution failure" in err
    assert f"devcapsule project --path '{project}' run" in err
    assert run_until_prepared(project) == 0  # the printed recovery is sufficient


def test_config_approve_refuses_inside_its_own_capsule(checkout, monkeypatch, tmp_path, capsys) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    _, manifest = manifest_for(project)
    context = tmp_path / "launch-context.json"
    context.write_text(json.dumps({
        "format": 1, "launcher-root": "/host/project with spaces", "runtime-root": str(project),
        "checkout-file": record.name, "project": manifest["project"],
        "running": {"base": {}, "identity": "fixture", "origin": "project recommendation",
                    "lock": load_toml(lock_path(project))},
    }))
    monkeypatch.setattr(runtime_configuration, "CONTEXT_PATH", context)
    before = record.read_bytes(), resolution.read_bytes()
    assert invoke(project, "config", "approve", "--all") == 2
    err = capsys.readouterr().err
    assert "configuration is read-only" in err
    assert "devcapsule project --path '/host/project with spaces' config approve --all" in err
    assert (record.read_bytes(), resolution.read_bytes()) == before


def test_interrupted_activation_checks_only_the_checkout_journal(tmp_path: Path) -> None:
    record = tmp_path / "named.checkout.toml"
    record.write_text("checkout contents")
    unrelated = tmp_path / "other.checkout.activation.toml"
    unrelated.write_text("another checkout's journal")
    assert interrupted_activation(record) is False
    journal = tmp_path / "named.checkout.activation.toml"
    journal.write_text("unfinished activation")
    before = {path: path.read_bytes() for path in (record, unrelated, journal)}
    assert interrupted_activation(record) is True
    assert {path: path.read_bytes() for path in before} == before
    journal.unlink()
    assert interrupted_activation(record) is False


def test_inspecting_approvals_defers_activation_recovery(checkout, monkeypatch, capsys) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    journal = record.with_suffix(".activation.toml")
    journal.write_text(render_toml({
        "before-checkout": record.read_text(), "after-checkout": "not committed",
        "before-resolution": "would overwrite the resolution", "after-resolution": "unused",
    }))
    before = {p: p.read_bytes() for p in (record, resolution, journal)}
    monkeypatch.setattr(offer, "confirmation_key", lambda: pytest.fail("asked before recovery"))
    assert offer.offer_software_approvals(project) is True  # the ordinary launch loader owns recovery
    assert {p: p.read_bytes() for p in before} == before
    assert invoke(project, "config", "approve") == 2
    err = capsys.readouterr().err
    assert "Interrupted activation" in err and f"--path '{project}' run" in err
    assert {p: p.read_bytes() for p in before} == before
    assert run_until_prepared(project) == 3  # recovers, then reports the pending consent
    assert "claude-code-download" in capsys.readouterr().err
    assert not journal.exists()
    assert invoke(project, "config", "approve", "--all") == 0


@pytest.mark.parametrize("failure", [OSError("unreadable history"), RuntimeError("cannot expand home")])
def test_previous_versions_is_best_effort_during_path_discovery(tmp_path, failure) -> None:
    with patch.object(version_sets, "state_directory", side_effect=failure):
        assert offer.previous_versions(tmp_path) == {}


def test_previous_versions_is_best_effort_when_listing_fails(tmp_path) -> None:
    with patch.object(Path, "glob", side_effect=OSError("unreadable directory")):
        assert offer.previous_versions(tmp_path) == {}


@pytest.mark.parametrize("content", [b"\xff", b"not = [toml", b"lock = 1", b"last-success = 20"])
def test_unreadable_history_does_not_block_approvals(tmp_path, content) -> None:
    directory = version_sets.state_directory(tmp_path) / "known-good"
    directory.mkdir(parents=True)
    (directory / "broken.toml").write_bytes(content)
    assert offer.previous_versions(tmp_path) == {}


def test_confirmation_key_restores_the_terminal_on_eof() -> None:
    with (
        patch.object(offer.sys, "stdin") as stdin,
        patch.object(offer.termios, "tcgetattr", return_value=["saved"]) as get,
        patch.object(offer.tty, "setraw") as raw,
        patch.object(offer.termios, "tcsetattr") as restore,
    ):
        stdin.fileno.return_value = 7
        stdin.read.return_value = ""
        assert offer.confirmation_key() == ""
        get.assert_called_once_with(7)
        raw.assert_called_once_with(7)
        stdin.read.assert_called_once_with(1)
        restore.assert_called_once_with(7, offer.termios.TCSADRAIN, ["saved"])


@pytest.mark.parametrize("record", [
    {"lock": "components = 1", "last-success": 30},
    {"lock": "components = {}", "last-success": float("nan")},
    {"lock": "components = {}", "last-success": float("inf")},
    {"lock": "components = {}", "last-success": 10 ** 400},
    {"lock": "bad = [toml", "last-success": 30},
])
def test_broken_newest_history_does_not_hide_a_valid_record(tmp_path, record) -> None:
    directory = version_sets.state_directory(tmp_path) / "known-good"
    directory.mkdir(parents=True)
    bad = directory / "bad.toml"
    good = directory / "good.toml"
    bad.write_text(render_toml(record))
    good.write_text(render_toml({"lock": '[components.claude-code]\nversion = "1.0.0"', "last-success": 20}))
    with patch.object(Path, "glob", return_value=iter([bad, good])):
        assert offer.previous_versions(tmp_path) == {"claude-code": "1.0.0"}


@pytest.mark.parametrize("interactive", [False, True])
def test_software_approval_is_not_saved_while_a_required_input_is_pending(checkout, monkeypatch, interactive: bool) -> None:
    project, record, resolution = checkout
    approved_then_bumped(project, record)
    assert invoke(project, 'config', 'require', 'env', 'NEW_INPUT', '--because', 'new service') == 0
    before = record.read_bytes(), resolution.read_bytes()
    launch = install_external_fakes(monkeypatch, [])
    import io
    from devcapsule.compat import DecisionPending
    monkeypatch.setattr('sys.stdin', io.StringIO('y\n'))
    monkeypatch.setattr(offer.sys.stdin, 'isatty', lambda: interactive)
    monkeypatch.setattr(offer, 'confirmation_key', lambda: 'y' if interactive else pytest.fail('asked without a terminal'))
    def closed_input(*args) -> str:
        raise DecisionPending('terminal closed')
    monkeypatch.setattr('devcapsule.commands._run_flow._hidden', closed_input)
    assert invoke(project, 'run', '--no-update-check') == 3
    assert (record.read_bytes(), resolution.read_bytes()) == before
    launch.assert_not_called()
