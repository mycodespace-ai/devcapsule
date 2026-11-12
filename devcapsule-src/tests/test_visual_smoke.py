"""Failure boundaries for the shared graphical scenario, without paid calls."""
from dataclasses import asdict
from pathlib import Path
import json
import re
import sys
from typing import Any

import pytest

from tests.e2e.ai_driver import CliDriver, Decision, DriverError, cli_identity
from tests.e2e.ide_session import SURFACES, SessionFacts, wait_for_ide_window
from tests.e2e.visual_smoke import drive_scenario

pytestmark = pytest.mark.legacy


def decision(action: str = "done") -> Decision:
    return Decision(action, 0, 0, "", 0, "test observation")


def test_provider_defaults_and_explicit_model_override() -> None:
    assert CliDriver.select("codex").model == "gpt-6-astra"
    assert CliDriver.select("claude").model == "claude-fable-5-1"
    assert CliDriver.select("claude", "custom").model == "custom"
    with pytest.raises(DriverError, match="Unsupported"):
        CliDriver.select("unknown")


@pytest.mark.parametrize("field,value", [("action", "shell"), ("x", -1), ("y", 1000), ("seconds", 11), ("x", True), ("text", None)])
def test_invalid_model_actions_are_rejected(field: str, value: Any) -> None:
    payload = asdict(decision())
    payload[field] = value
    with pytest.raises(DriverError):
        Decision.parse(payload)


class FakePage:
    def screenshot(self, *, path: str) -> None:
        Path(path).write_bytes(b"test frame")

    def wait_for_timeout(self, milliseconds: int) -> None:
        pass


class FakeDriver:
    def __init__(self, answer: Decision) -> None:
        self.answer = answer
        self.calls = 0

    def decide(self, prompt: str, images: tuple[Path, ...], evidence: Path, timeout: float) -> Decision:
        self.calls += 1
        return self.answer


def session(workspace: Path) -> SessionFacts:
    return SessionFacts(SURFACES[-1], "test-child", "http://test", workspace, workspace / "launcher.log")


def test_positive_ai_verdict_cannot_pass_without_saved_edit(tmp_path: Path) -> None:
    driver = FakeDriver(decision())
    recognizer = FakeDriver(decision())
    with pytest.raises(DriverError, match="did not save"):
        drive_scenario(FakePage(), session(tmp_path), tmp_path, driver, recognizer)
    assert recognizer.calls == 0
    assert '"status": "failed"' in (tmp_path / "agent-result.json").read_text()


def test_start_failed_window_is_not_a_live_ide(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tests.e2e.ide_session.top_level_windows",
                        lambda container: [{"class": "jetbrains-idea", "name": "Start Failed"}])
    with pytest.raises(AssertionError, match="startup failure"):
        wait_for_ide_window(session(tmp_path))


def test_action_limit_stops_waiting_model(tmp_path: Path) -> None:
    driver = FakeDriver(decision("wait"))
    with pytest.raises(DriverError, match="action limit"):
        drive_scenario(FakePage(), session(tmp_path), tmp_path, driver, driver, max_actions=2)
    assert driver.calls == 3


def test_missing_cli_fails_explicitly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(DriverError, match="unavailable codex"):
        CliDriver.select("codex").decide("test", (), tmp_path / "evidence", 1)
    assert (tmp_path / "evidence/invocation.json").is_file()


def test_hung_cli_is_killed_and_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = tmp_path / "codex"
    executable.write_text(f"#!{sys.executable}\nimport sys,time\n"
                          "if '--version' in sys.argv: print('fake 1')\n"
                          "else: time.sleep(30)\n")
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    cli_identity.cache_clear()
    try:
        with pytest.raises(DriverError, match="time limit"):
            CliDriver.select("codex").decide("test", (), tmp_path / "evidence", 0.1)
        record = json.loads((tmp_path / "evidence/invocation.json").read_text())
        assert record["timed_out"] is True and record["exit_code"] == -9
    finally:
        cli_identity.cache_clear()


def test_saved_edit_still_requires_visual_acceptance(tmp_path: Path) -> None:
    class SavedEditDriver(FakeDriver):
        def decide(self, prompt: str, images: tuple[Path, ...], evidence: Path, timeout: float) -> Decision:
            marker = re.search(r"DEVCAPSULE_SMOKE_[a-f0-9]+", prompt)
            assert marker is not None
            (tmp_path / "smoke.txt").write_text(marker.group())
            return decision()

    recognizer = FakeDriver(decision("fail"))
    with pytest.raises(DriverError, match="recognizer did not accept"):
        drive_scenario(FakePage(), session(tmp_path), tmp_path, SavedEditDriver(decision()), recognizer)
    assert recognizer.calls == 1
