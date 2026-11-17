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
    """In-memory Playwright page double recording captured bytes and wait calls."""

    def __init__(self, *, fail_jpeg_at: int | None = None, fail_png_at: int | None = None) -> None:
        self.fail_jpeg_at = fail_jpeg_at
        self.fail_png_at = fail_png_at
        self.jpeg_calls = 0
        self.png_calls = 0
        self.captured_jpeg_bytes = bytearray()
        self.waits: list[int] = []

    def screenshot(self, *, type: str = "png", quality: int | None = None, path: str | None = None) -> bytes:
        del quality
        if path is None:
            self.jpeg_calls += 1
            if self.fail_jpeg_at is not None and self.jpeg_calls >= self.fail_jpeg_at:
                raise RuntimeError("page disconnected during frame capture")
            assert type == "jpeg"
            chunk = f"FRAME-{self.jpeg_calls}:".encode("ascii")
            self.captured_jpeg_bytes.extend(chunk)
            return chunk
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
        "sys.stderr.write(f'bytes={len(data)}\\n'); "
        f"pathlib.Path(sys.argv[-1]).write_bytes(b'WEBM:' + data) if {write_video!r} else None; "
        f"sys.exit({exit_code})"
    )
    return (sys.executable, "-I", "-S", "-c", program)


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


def test_recording_finish_writes_aligned_deck_and_media_for_passing_run(tmp_path: Path) -> None:
    """Finishing a complete multi-action run encodes captured bytes and aligns chapters to frame boundaries."""
    # Precondition: record a complete two-step run (two actions in step 1, one in step 2).
    evidence = tmp_path / "run-pass"
    page = _StubPage()
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="  Example  ",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Navigate to page", lambda: None)
    recording.action(page, 1, "Confirm heading", lambda: None)
    recording.action(page, 2, "Reload page", lambda: None)

    # Action: finalize the recording.
    manifest = recording.finish()

    # Postcondition: logs record increasing frame boundaries, deck aligns to them, and encoder gets captured bytes.
    result = json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))
    actions = json.loads((evidence / "action-log.json").read_text(encoding="utf-8"))
    boundaries = [entry["frames_after"] for entry in actions]
    deck = json.loads(manifest.read_text(encoding="utf-8"))
    assert result == {"status": "passed", "error": "", "steps_reached": 2, "steps_planned": 2}
    assert len(boundaries) == 3 and 0 < boundaries[0] < boundaries[1] < boundaries[2]
    assert deck["title"] == "Example"
    assert deck["video"]["file"] == "scenario-video.webm"
    assert deck["video"]["poster"] == "poster.png"
    assert deck["video"]["duration"] > 0
    step1, step2 = deck["steps"]
    assert (step1["screenshot"], step2["screenshot"]) == ("step-002.png", "step-003.png")
    assert step1["start"] == 0.0
    assert 0.0 < step1["end"] == step2["start"] < step2["end"] == deck["video"]["duration"]
    assert [c["text"] for c in step1["captions"]] == ["Navigate to page", "Confirm heading"]
    assert [c["text"] for c in step2["captions"]] == ["Reload page"]
    assert step1["captions"][0]["start"] == step1["start"]
    assert step1["captions"][0]["end"] == step1["captions"][1]["start"]
    assert step1["captions"][1]["end"] == step1["end"]
    assert step2["captions"][0]["start"] == step2["start"] and step2["captions"][0]["end"] == step2["end"]
    assert (evidence / "poster.png").read_bytes() == (evidence / "step-001.png").read_bytes()
    assert (evidence / "scenario-video.webm").read_bytes() == b"WEBM:" + bytes(page.captured_jpeg_bytes)
    assert f"bytes={len(page.captured_jpeg_bytes)}\n" in (evidence / "ffmpeg.log").read_text(encoding="utf-8")


def test_recording_action_reraises_callback_failure_and_records_failed_state(tmp_path: Path) -> None:
    """A failing action callback propagates its exception while preserving failed logs and screenshot."""
    # Precondition: step 1 succeeded.
    evidence = tmp_path / "run-fail-action"
    page = _StubPage()
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open app", lambda: None)

    def fail_reload() -> None:
        raise AssertionError("heading missing")

    # Action: execute a failing callback in step 2.
    with pytest.raises(AssertionError, match="heading missing"):
        recording.action(page, 2, "Reload app", fail_reload)

    # Postcondition: failure state, action log and failure screenshot are recorded on disk.
    result = json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))
    actions = json.loads((evidence / "action-log.json").read_text(encoding="utf-8"))
    assert result == {
        "status": "failed",
        "error": "AssertionError: heading missing",
        "steps_reached": 2,
        "steps_planned": 2,
    }
    assert actions[1]["status"] == "failed" and actions[1]["error"] == "AssertionError: heading missing"
    assert (evidence / "step-002.png").is_file()


def test_recording_action_refuses_calls_after_failure(tmp_path: Path) -> None:
    """Once an action fails, any subsequent action call is refused before capturing frames."""
    # Precondition: step 1 failed.
    page = _StubPage()
    recording = Recording(tmp_path / "run-after-fail", script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    with pytest.raises(AssertionError):
        recording.action(page, 1, "Open app", lambda: (_ for _ in ()).throw(AssertionError("boom")))
    calls_before = page.jpeg_calls

    # Action: attempt another action on the failed recording.
    with pytest.raises(PresentationError, match="finished or failed"):
        recording.action(page, 2, "Reload app", lambda: None)

    # Postcondition: no further frames were captured.
    assert page.jpeg_calls == calls_before


def test_recording_finish_writes_failed_deck_for_reached_steps(tmp_path: Path) -> None:
    """Finishing a failed run keeps the failed result and labels the presentation FAILED."""
    # Precondition: step 1 passed and step 2 failed with visual evidence intact.
    evidence = tmp_path / "run-finish-fail"
    page = _StubPage()
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="  Example  ",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open app", lambda: None)
    with pytest.raises(AssertionError):
        recording.action(page, 2, "Reload app", lambda: (_ for _ in ()).throw(AssertionError("heading missing")))

    # Action: finalize the failed recording.
    manifest = recording.finish()

    # Postcondition: result remains failed and presentation is labelled FAILED for the two reached steps.
    result = json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))
    deck = json.loads(manifest.read_text(encoding="utf-8"))
    assert result["status"] == "failed" and result["error"] == "AssertionError: heading missing"
    assert deck["title"] == "Example (FAILED)"
    assert len(deck["steps"]) == 2


def test_recording_labels_incomplete_run_with_only_reached_steps(tmp_path: Path) -> None:
    """Finishing before all script steps run keeps an incomplete status and an INCOMPLETE deck."""
    # Precondition: only step 1 of 2 ran.
    evidence = tmp_path / "run-incomplete"
    page = _StubPage()
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open app", lambda: None)

    # Action: finalize the partial recording.
    manifest = recording.finish()

    # Postcondition: result stays incomplete and deck contains only the reached step.
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


def test_recording_finish_refuses_second_call(tmp_path: Path) -> None:
    """Finishing an already finished recording raises PresentationError."""
    # Precondition: recording is already finished.
    page = _StubPage()
    recording = Recording(tmp_path / "run", script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open", lambda: None)
    recording.finish()

    # Action: call finish a second time.
    with pytest.raises(PresentationError, match="already been finished"):
        recording.finish()


def test_recording_action_refuses_calls_after_finish(tmp_path: Path) -> None:
    """Calling action after finish raises PresentationError without capturing frames."""
    # Precondition: recording is already finished.
    page = _StubPage()
    recording = Recording(tmp_path / "run", script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    recording.action(page, 1, "Open", lambda: None)
    recording.finish()
    calls_before = page.jpeg_calls

    # Action: attempt another action after finish.
    with pytest.raises(PresentationError, match="finished or failed"):
        recording.action(page, 2, "Reload", lambda: None)

    assert page.jpeg_calls == calls_before


def test_recording_finish_refuses_run_with_no_actions(tmp_path: Path) -> None:
    """Finishing with zero actions writes an incomplete result and refuses writing a presentation."""
    evidence = tmp_path / "empty"
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())

    with pytest.raises(PresentationError, match="no complete visual evidence"):
        recording.finish()

    assert json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))["status"] == "incomplete"
    assert not (evidence / "presentation.json").exists()


def test_recording_finish_refuses_run_with_missing_step_screenshot(tmp_path: Path) -> None:
    """Finishing when a failed action could not save a screenshot keeps the failed result and writes no deck."""
    # Precondition: step 1 callback failed and screenshot capture also failed.
    evidence = tmp_path / "broken-capture"
    page = _StubPage(fail_png_at=1)
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command())
    with pytest.raises(AssertionError, match="original test assertion"):
        recording.action(page, 1, "Open", lambda: (_ for _ in ()).throw(AssertionError("original test assertion")))

    # Action: finalize the recording without complete screenshots.
    with pytest.raises(PresentationError, match="no complete visual evidence"):
        recording.finish()

    assert json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))["status"] == "failed"
    assert not (evidence / "presentation.json").exists()


def test_recording_finish_preserves_logs_when_encoder_fails(tmp_path: Path) -> None:
    """A non-zero encoder exit leaves result and encoder logs intact and writes neither poster nor presentation."""
    # Precondition: step 1 succeeded with an encoder configured to exit 1.
    evidence = tmp_path / "encode-fail"
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command(exit_code=1, write_video=False))
    recording.action(_StubPage(), 1, "Open", lambda: None)

    # Action: finalize the recording.
    with pytest.raises(subprocess.CalledProcessError):
        recording.finish()

    assert json.loads((evidence / "scenario-result.json").read_text(encoding="utf-8"))["status"] == "incomplete"
    assert (evidence / "ffmpeg.log").is_file()
    assert not (evidence / "presentation.json").exists()
    assert not (evidence / "poster.png").exists()


def test_recording_finish_withholds_deck_when_encoder_writes_no_video(tmp_path: Path) -> None:
    """An encoder that exits zero without writing scenario-video.webm raises PresentationError and writes no deck."""
    # Precondition: step 1 succeeded with an encoder that exits 0 without producing video output.
    evidence = tmp_path / "encode-empty"
    recording = Recording(evidence, script=SCRIPT, scenario_id="example", title="Example",
                          summary="Example run", ffmpeg=_encoder_command(exit_code=0, write_video=False))
    recording.action(_StubPage(), 1, "Open", lambda: None)

    # Action: finalize the recording.
    with pytest.raises(PresentationError, match="scenario-video.webm"):
        recording.finish()

    assert (evidence / "ffmpeg.log").is_file()
    assert not (evidence / "presentation.json").exists()
    assert not (evidence / "poster.png").exists()
