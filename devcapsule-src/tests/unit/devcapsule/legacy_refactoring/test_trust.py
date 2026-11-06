"""Legacy tests of ``tests/test_trust.py`` marked expected to fail on 2026-11-04, moved verbatim.

Mirror of ``devcapsule/legacy_refactoring/trust.py``, a temporary target that holds no code.
Each test here reads a precondition from outside itself, against *Unit Tests* rule 2; the
maintenance workstream rewrites each against its real unit and this file shrinks to nothing.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import pytest
from devcapsule import cli
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.compat import DecisionPending
from devcapsule.configuration.file_formats import render_toml
from devcapsule.configuration.storage import checkout_record_paths, load_toml, load_trust, manifest_for, settings_path
from devcapsule.configuration.trust import BASE_CHANNEL, HomeTrust
from tests.test_trust import accept, config, lock_path, pin_claude_code, project, reviews, withdraw
from devcapsule.runtime_configuration import CONTEXT_PATH

IN_CAPSULE = CONTEXT_PATH.is_file()
"""The marker holds only inside a capsule, where these tests inherit its state; elsewhere they are the tests they were."""


@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_trust_list_accept_and_withdraw(project: Path, capsys) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    assert config(project, "ide", "python-ide") == 0
    assert config(project, "check") == 3
    assert config(project, "trust", "list") == 0
    out = capsys.readouterr().out
    assert "devcapsule-base" in out and "not yet" in out and str(settings_path()) in out
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "Trust DevCapsule to supply the base images" in out and "Recorded for this DevCapsule home" in out
    assert load_toml(settings_path())["trust"]["channels"]["devcapsule-base"]["vendor"] == "DevCapsule"
    assert config(project, "show") == 0
    assert "home trust (devcapsule-base)" in capsys.readouterr().out
    assert config(project, "check") == 0
    capsys.readouterr()
    assert config(project, "trust", "list", "--json") == 0
    listed = json.loads(capsys.readouterr().out)
    assert [(row["channel"], row["trusted"]) for row in listed["channels"]] == [("devcapsule-base", True)]
    assert withdraw("devcapsule-base") == 0
    assert config(project, "check") == 3
    assert withdraw("devcapsule-base") == 0
    assert accept(project, "codex") == 2
    assert "its channels: devcapsule-base" in capsys.readouterr().err



@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_run_trust_flag_records_the_channel_before_the_questions(project: Path) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    with pytest.raises(DecisionPending, match="--trust devcapsule-base"):
        prepare_launch(project, RunFlags(ide="python-ide"), interactive=False)
    assert not settings_path().exists()
    prepared = prepare_launch(project, RunFlags(ide="python-ide", trust=("devcapsule-base",)), interactive=False)
    assert prepared.selected.resolution["authorization"]["base-image"]["reference"].startswith("docker.io/mycodespaceai/devcapsule-base@")
    assert "devcapsule-base" in load_toml(settings_path())["trust"]["channels"]
    assert "Accepted the channel devcapsule-base for this home." in prepared.notes
    # Printing the command stages the acceptance for the plan and writes nothing.
    assert withdraw("devcapsule-base") == 0
    prepare_launch(project, RunFlags(ide="python-ide", trust=("devcapsule-base",)), print_only=True)
    assert not HomeTrust.read(load_trust()).channels
    # With another decision pending and no terminal, the flag's acceptance is staged with the other answers: nothing is written.
    with pytest.raises(DecisionPending, match="Nothing was written"):
        prepare_launch(project, RunFlags(trust=("devcapsule-base",)), interactive=False)  # the IDE is still unchosen
    assert not HomeTrust.read(load_trust()).channels
    # Declined at the prompt: nothing recorded, the launch is still pending.
    assert config(project, "ide", "python-ide") == 0
    prompts = io.StringIO()
    with pytest.raises(DecisionPending):
        prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO("n\n"), output_stream=prompts)
    assert "Not accepted. Accept later:" in prompts.getvalue()
    assert not HomeTrust.read(load_trust()).channels



@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_changed_artifact_origin_asks_and_lists_the_previous_acceptance(project: Path, capsys) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    pin_claude_code(project, "1.0.0")
    assert accept(project, "claude-code") == 0
    lock = load_toml(lock_path(project))
    lock["components"]["claude-code"]["artifacts"]["linux-amd64"]["url"] = "https://mirror.example.test/claude"
    lock_path(project).write_text(render_toml(lock))
    assert reviews(project)["claude-code-download"].status == "missing-required"
    capsys.readouterr()
    assert config(project, "trust", "list") == 0
    text = capsys.readouterr().out
    assert "not covered" in text and "https://mirror.example.test" in text
    assert "Accepted origins: https://downloads.example.test" in text
    assert "SHA-256" in text and "Anyone who uses this home uses this acceptance" in text
    assert accept(project, "claude-code") == 0
    assert reviews(project)["claude-code-download"].status == "trusted"
    pin_claude_code(project, "1.1.0")
    assert reviews(project)["claude-code-download"].status == "trusted"



@pytest.mark.parametrize("via", ["flag", "terminal"])
@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_acceptance_uses_the_checkout_version_set_not_the_shared_lock(project: Path, via: str, capsys) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    from devcapsule.configuration.derivation import load_state
    from devcapsule.configuration.file_formats import canonical_digest
    assert config(project, "ide", "python-ide") == 0
    assert accept(project, BASE_CHANNEL) == 0
    pin_claude_code(project, "1.0.0")
    _, manifest = manifest_for(project)
    manifest["capabilities"]["required"].append("claude-code-agent")
    (project / ".devcapsule/devcapsule.toml").write_text(render_toml(manifest))
    state = load_state(project, manifest)
    selected = state.composed_lock()
    selected["components"]["claude-code"]["artifacts"]["linux-amd64"]["url"] = "https://selected.example.test/claude"
    record_path = checkout_record_paths(manifest, project)[0]
    record = load_toml(record_path)
    record["version-set"] = {"format": 1, "lock": render_toml(selected), "recommendation-digest": canonical_digest(state.shared_lock)}
    record_path.write_text(render_toml(record))
    capsys.readouterr()
    assert config(project, "trust", "list", "--json") == 0
    listed = json.loads(capsys.readouterr().out)
    channel = next(row for row in listed["channels"] if row["channel"] == "claude-code")
    assert channel["origins"] == ["https://selected.example.test"]
    flags, interactive = RunFlags(trust=("claude-code",) if via == "flag" else ()), via == "terminal"
    output = io.StringIO()
    prepared = prepare_launch(project, flags, interactive=interactive, input_stream=io.StringIO("y\n"), output_stream=output)
    assert prepared.selected.resolution["authorization"]["claude-code-download"] is True
    if via == "terminal":
        assert "https://selected.example.test" in output.getvalue()
        assert "https://downloads.example.test" not in output.getvalue()
    assert load_trust()["channels"]["claude-code"]["origins"] == ["https://selected.example.test"]



@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_run_does_not_replay_trust_flags_after_an_upgrade_changes_the_channel(project: Path, monkeypatch) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    assert config(project, "ide", "python-ide") == 0
    pin_claude_code(project, "1.0.0")
    _, manifest = manifest_for(project)
    manifest["capabilities"]["required"].append("claude-code-agent")
    (project / ".devcapsule/devcapsule.toml").write_text(render_toml(manifest))
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    def upgrade(root: Path, *, refresh: bool) -> bool:
        lock = load_toml(lock_path(root))
        lock["components"]["claude-code"]["artifacts"]["linux-amd64"]["url"] = "https://unaccepted.example.test/claude"
        lock_path(root).write_text(render_toml(lock))
        return True
    monkeypatch.setattr("devcapsule.commands.project.offer_upgrades", upgrade)
    assert invoke(project, "run", "--trust", BASE_CHANNEL, "--trust", "claude-code", "--no-update-check") == 3
    launch.assert_not_called()
    assert load_trust()["channels"]["claude-code"]["origins"] == ["https://downloads.example.test"]
