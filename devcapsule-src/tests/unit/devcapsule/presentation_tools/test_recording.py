"""Unit tests for ``devcapsule.presentation_tools.recording``."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from devcapsule.presentation_tools.producer import PresentationError, Script, ScriptStep
from devcapsule.presentation_tools.recording import Recording

SCRIPT = Script(
    goal="Verify the application flow.",
    stack=(("Browser", "Chromium"),),
    illustrates=("A passing and failing check.",),
    steps=(
        ScriptStep("Open", "Open the app", "The heading appears"),
        ScriptStep("Reload", "Reload the page", "The heading stays"),
    ),
)


class _StubPage:
    """In-memory Playwright page double recording screenshot and wait calls."""

    def __init__(self, *, fail_jpeg_at: int | None = None, fail_png_at: int | None = None) -> None:
        self.fail_jpeg_at = fail_jpeg_at
        self.fail_png_at = fail_png_at
        self.jpeg_calls = 0
        self.png_calls = 0
        self.waits: list[int] = []

    def screenshot(self, *, type: str = "png", quality: int | None = None, path: str | None = None) -> bytes:
        del quality
        if path is None:
            self.jpeg_calls += 1
            if self.fail_jpeg_at is not None and self.jpeg_calls >= self.fail_jpeg_at:
                raise RuntimeError("page disconnected during frame capture")
            assert type == "jpeg"
            return b"FRAME:"
        self.png_calls += 1
        if self.fail_png_at is not None and self.png_calls >= self.fail_png_at:
            raise RuntimeError("page disconnected during step screenshot")
        Path(path).write_bytes(f"PNG-{self.png_calls}".encode("ascii"))
        return b""

    def wait_for_timeout(self, ms: int) -> None:
        self.waits.append(ms)


def _encoder_command(*, exit_code: int = 0, write_video: bool = True) -> tuple[str, ...]:
    program = (
        "import pathlib, sys; "
        "data = sys.stdin.buffer.read(); "
        "sys.stderr.write(f'frames={len(data)}\\n'); "
        f"pathlib.Path(sys.argv[-1]).write_bytes(b'WEBM:' + data) if {write_video!r} else None; "
        f"sys.exit({exit_code})"
    )
    return (sys.executable, "-c", program)


@pytest.mark.parametrize(
    ("steps", "ffmpeg"),
    [
        ((), ("encoder",)),
        ((ScriptStep("Open", "Open the app", "The heading appears"),), ()),
        ((ScriptStep("Open", "Open the app", "The heading appears"),), "ffmpeg"),
    ],
)
def test_recording_rejects_invalid_setup_before_creating_evidence(
    tmp_path: Path, steps: tuple[ScriptStep, ...], ffmpeg: tuple[str, ...] | str,
) -> None:
    """An empty script, absent encoder or unsplit string encoder is refused before an evidence folder exists."""
    with pytest.raises(PresentationError):
        Recording(tmp_path / "run", script=Script("Goal", (), (), steps), scenario_id="example",
                  title="Example", summary="Example run", ffmpeg=ffmpeg)

    assert not (tmp_path / "run").exists()


def test_recording_preserves_existing_evidence(tmp_path: Path) -> None:
    """A recording cannot overwrite a prior attempt, even if that directory is empty."""
    with pytest.raises(FileExistsError):
        Recording(tmp_path, script=SCRIPT, scenario_id="example", title="Example",
                  summary="Example run", ffmpeg=("encoder",))

    assert list(tmp_path.iterdir()) == []


def test_recording_completes_passing_run_with_repeated_steps_and_timing(tmp_path: Path) -> None:
    """A passing multi-action run writes logs, poster, video and presentation timed by captured frames."""
    evidence = tmp_path / "run-pass"
    page = _StubPage()
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="  Example  ",
                          summary="Example run", ffmpeg=_encoder_command())

    recording.action(page, 1, "Navigate to page", lambda: None)
    recording.action(page, 1, "Confirm heading", lambda: None)
    recording.action(page, 2, "Reload page", lambda: None)
    manifest = recording.finish()

    result = json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))
    actions = json.loads((evidence / "action-log.json").read_text(encoding="utf-8"))
    deck = json.loads(manifest.read_text(encoding="utf-8"))
    assert result == {"status": "passed", "error": "", "steps_reached": 2, "steps_planned": 2}
    assert [entry["frames_after"] for entry in actions] == [8, 16, 24]
    assert deck["title"] == "Example"
    assert deck["video"] == {"file": "scenario-video.webm", "poster": "poster.png", "duration": 2.0}
    assert [(s["screenshot"], s["start"], s["end"], len(s["captions"])) for s in deck["steps"]] == [
        ("step-002.png", 0.0, 1.333, 2),
        ("step-003.png", 1.333, 2.0, 1),
    ]
    assert (evidence / "poster.png").read_bytes() == (evidence / "step-001.png").read_bytes()
    assert (evidence / "scenario-video.webm").read_bytes() == b"WEBM:" + (b"FRAME:" * 24)
    assert "frames=144\n" in (evidence / "ffmpeg.log").read_text(encoding="utf-8")


def test_recording_keeps_failed_outcome_and_reached_steps_when_callback_fails(tmp_path: Path) -> None:
    """A failing assertion re-raises, blocks later actions and writes a FAILED deck for reached steps."""
    evidence = tmp_path / "run-fail"
    page = _StubPage()
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="  Example  ",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open app", lambda: None)

    def fail_reload() -> None:
        raise AssertionError("heading missing")

    with pytest.raises(AssertionError, match="heading missing"):
        recording.action(page, 2, "Reload app", fail_reload)

    with pytest.raises(PresentationError, match="finished or failed"):
        recording.action(page, 2, "Retry reload", lambda: None)

    manifest = recording.finish()
    result = json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))
    deck = json.loads(manifest.read_text(encoding="utf-8"))
    assert result == {
        "status": "failed",
        "error": "AssertionError: heading missing",
        "steps_reached": 2,
        "steps_planned": 2,
    }
    assert deck["title"] == "Example (FAILED)"
    assert len(deck["steps"]) == 2
    assert (evidence / "step-002.png").is_file()


def test_recording_labels_incomplete_run_with_only_reached_steps(tmp_path: Path) -> None:
    """Finishing before all script steps run keeps an incomplete status and an INCOMPLETE deck."""
    evidence = tmp_path / "run-incomplete"
    page = _StubPage()
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open app", lambda: None)

    manifest = recording.finish()

    result = json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))
    deck = json.loads(manifest.read_text(encoding="utf-8"))
    assert result == {"status": "incomplete", "error": "", "steps_reached": 1, "steps_planned": 2}
    assert deck["title"] == "Example (INCOMPLETE)"
    assert len(deck["steps"]) == 1


@pytest.mark.parametrize(("step", "caption"), [(0, "Open"), (True, "Open"), (2, "Skipped"), (1, "   ")])
def test_recording_refuses_invalid_step_order_or_empty_caption(
    tmp_path: Path, step: int | bool, caption: str,
) -> None:
    """Out-of-order steps, boolean steps and blank captions are refused before capturing frames."""
    page = _StubPage()
    recording = Recording(tmp_path / "run", script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())

    with pytest.raises(PresentationError):
        recording.action(page, step, caption, lambda: None)

    assert page.jpeg_calls == 0


def test_recording_refuses_repeated_finish_and_action_after_finish(tmp_path: Path) -> None:
    """Once finished, a recording refuses both a second finish and any further action."""
    page = _StubPage()
    recording = Recording(tmp_path / "run", script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open", lambda: None)
    recording.finish()

    with pytest.raises(PresentationError, match="already been finished"):
        recording.finish()
    with pytest.raises(PresentationError, match="finished or failed"):
        recording.action(page, 2, "Reload", lambda: None)


def test_recording_refuses_presentation_when_visual_evidence_is_missing(tmp_path: Path) -> None:
    """Missing screenshots or zero actions keep the result log and refuse writing a presentation."""
    empty_evidence = tmp_path / "empty"
    empty_recording = Recording(empty_evidence, script=SCRIPT, scenario_id="example", title="Example",
                                summary="Example run", ffmpeg=_encoder_command())
    with pytest.raises(PresentationError, match="no complete visual evidence"):
        empty_recording.finish()
    assert json.loads((empty_evidence / "scenario-result.json").read_text(encoding="utf-8"))["status"] == "incomplete"
    assert not (empty_evidence / "presentation.json").exists()

    broken_evidence = tmp_path / "broken-capture"
    broken_page = _StubPage(fail_png_at=1)
    broken_recording = Recording(broken_evidence, script=SCRIPT, scenario_id="example", title="Example",
                                 summary="Example run", ffmpeg=_encoder_command())

    def fail_callback() -> None:
        raise AssertionError("original test assertion")

    with pytest.raises(AssertionError, match="original test assertion"):
        broken_recording.action(broken_page, 1, "Open", fail_callback)

    with pytest.raises(PresentationError, match="no complete visual evidence"):
        broken_recording.finish()
    assert json.loads((broken_evidence / "scenario-result.json").read_text(encoding="utf-8"))["status"] == "failed"
    assert not (broken_evidence / "presentation.json").exists()


def test_recording_preserves_logs_and_withholds_deck_on_encoder_failure(tmp_path: Path) -> None:
    """A failing or empty video encode leaves logs intact and writes neither poster nor presentation."""
    failing = tmp_path / "encode-fail"
    rec_fail = Recording(failing, script=SCRIPT, scenario_id="example", title="Example",
                         summary="Example run", ffmpeg=_encoder_command(exit_code=1, write_video=False))
    rec_fail.action(_StubPage(), 1, "Open", lambda: None)

    with pytest.raises(subprocess.CalledProcessError):
        rec_fail.finish()
    assert json.loads((failing / "scenario-result.json").read_text(encoding="utf-8"))["status"] == "incomplete"
    assert (failing / "ffmpeg.log").is_file()
    assert not (failing / "presentation.json").exists()
    assert not (failing / "poster.png").exists()

    no_output = tmp_path / "encode-empty"
    rec_empty = Recording(no_output, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command(exit_code=0, write_video=False))
    rec_empty.action(_StubPage(), 1, "Open", lambda: None)

    with pytest.raises(PresentationError, match="scenario-video.webm"):
        rec_empty.finish()
    assert not (no_output / "presentation.json").exists()
