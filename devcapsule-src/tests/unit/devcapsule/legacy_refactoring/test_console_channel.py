"""Legacy tests of ``tests/test_console_channel.py`` marked expected to fail on 2026-11-04, moved verbatim.

Mirror of ``devcapsule/legacy_refactoring/console_channel.py``, a temporary target that holds no code.
Each test here reads a precondition from outside itself, against *Unit Tests* rule 2; the
maintenance workstream rewrites each against its real unit and this file shrinks to nothing.
"""
from __future__ import annotations

import json
import pytest
from devcapsule.commands._console_channel import run_config, sweep
from devcapsule.configuration.console_requests import deferred_requests
from devcapsule.configuration.storage import load_toml
from tests.test_console_channel import config, project, record_path, request, result
from devcapsule.runtime_configuration import CONTEXT_PATH

IN_CAPSULE = CONTEXT_PATH.is_file()
"""The marker holds only inside a capsule, where these tests inherit its state; elsewhere they are the tests they were."""


@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_channel_records_capability_choices_and_preserves_vendor_consent(project, tmp_path, capsys):
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    from devcapsule.configuration.capabilities import LocalCapabilities
    assert config(project, "offer", "browser-automation") == 0
    channel = tmp_path / "channel"
    channel.mkdir()
    def send(identifier, *arguments):
        request(channel, identifier, *arguments)
        assert sweep(channel, project, record_path(project)) == 1
        return result(channel, identifier)
    assert send("000001-add", "add", "claude-code-agent")["status"] == "recorded"
    assert "claude-code-agent" in LocalCapabilities.read(load_toml(record_path(project))).selected
    assert send("000002-omit", "omit", "browser-automation")["status"] == "recorded"
    assert "browser-automation" in LocalCapabilities.read(load_toml(record_path(project))).without
    assert send("000003-restore", "restore", "browser-automation")["status"] == "recorded"
    assert "browser-automation" not in LocalCapabilities.read(load_toml(record_path(project))).without
    assert send("000004-ide", "ide", "frontend-ide")["status"] == "recorded"
    assert send("000005-use", "use", "frontend-ide", "vscode")["status"] == "recorded"
    assert LocalCapabilities.read(load_toml(record_path(project))).providers == {"frontend-ide": "vscode"}
    # Single-provider capabilities still refuse `use` through the same command path.
    for index, (capability, component) in enumerate((("python-ide", "pycharm"), ("vscode-ide", "vscode")), start=6):
        expected_status, expected_text = run_config(project, ["use", capability, component])
        assert expected_status == 2 and "choice" in expected_text
        refused = send(f"00000{index}-use", "use", capability, component)
        assert refused["status"] == "refused" and expected_text.strip() in refused["text"]
    capsys.readouterr()
    assert config(project, "show", "--json") == 0
    listing = json.loads(capsys.readouterr().out)
    assert any(row["name"] == "claude-code-download" and row["pending"] for row in listing["rows"])
    assert any(row["name"] == "vscode-download" and row["pending"] for row in listing["rows"])
    assert deferred_requests(record_path(project)) == []
