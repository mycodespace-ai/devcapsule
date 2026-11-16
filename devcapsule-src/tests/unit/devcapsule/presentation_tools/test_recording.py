"""Recorder preconditions require no browser, clock or external process."""
from pathlib import Path

import pytest

from devcapsule.presentation_tools.producer import PresentationError, Script, ScriptStep
from devcapsule.presentation_tools.recording import Recording


@pytest.mark.parametrize("steps", [(), (ScriptStep("Open", "Open the app", "The heading appears"),)])
def test_recording_rejects_invalid_setup_before_creating_evidence(tmp_path: Path, steps: tuple[ScriptStep, ...]) -> None:
    """An empty script or absent encoder is refused before an evidence folder exists."""
    with pytest.raises(PresentationError):
        Recording(tmp_path / "run", script=Script("Goal", (), (), steps), scenario_id="example",
                  title="Example", summary="Example run", ffmpeg=())

    assert not (tmp_path / "run").exists()


def test_recording_preserves_existing_evidence(tmp_path: Path) -> None:
    """A recording cannot overwrite a prior attempt, even if that directory is empty."""
    with pytest.raises(FileExistsError):
        Recording(tmp_path, script=Script("Goal", (), (), (ScriptStep("Open", "Open", "Visible"),)),
                  scenario_id="example", title="Example", summary="Example run", ffmpeg=("encoder",))

    assert list(tmp_path.iterdir()) == []
