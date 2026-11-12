"""Unit tests for the E2E scenario recorder, action parser, and catalog."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import types
from typing import Any
from unittest.mock import Mock
import urllib.error
import urllib.request

import pytest

import noxfile
from tests.e2e import scenario_recorder
from tests.e2e.ai_driver import DriverError
from tests.e2e.scenario_recorder import (
    ActionStep,
    BurstFrameRecorder,
    ControllerQueue,
    ScenarioSpec,
    list_scenarios,
    load_scenario,
    main,
    seed_scenario_workspace,
    send_controller_command,
    serve_interactive_controller,
    start_controller_server,
    write_json_atomically,
)

pytestmark = pytest.mark.legacy


def test_eclipse_hello_time_debug_scenario_is_registered_and_valid(tmp_path: Path) -> None:
    assert "eclipse-hello-time-debug" in list_scenarios()
    spec = load_scenario("eclipse-hello-time-debug")
    assert spec.id == "eclipse-hello-time-debug"
    assert spec.surface == "eclipse"
    assert set(spec.seed_files) == {".project", ".classpath", "src/HelloTime.java"}
    assert "LocalDateTime.now()" in spec.seed_files["src/HelloTime.java"]
    assert any(step.action == "press" and step.text == "F11" for step in spec.actions)
    assert sum(1 for step in spec.actions if step.action == "press" and step.text == "F6") >= 3

    written = seed_scenario_workspace(tmp_path, spec)
    assert len(written) == 3
    assert (tmp_path / "src/HelloTime.java").is_file()


def test_action_step_substitution_and_validation() -> None:
    step = ActionStep.parse(
        {"action": "type", "text": "${PROJECT_PATH}/src", "reason": "import root"}
    ).substitute({"PROJECT_PATH": "/workspace/demo"})
    assert step.text == "/workspace/demo/src"

    wait_step = ActionStep.parse({"action": "wait", "seconds": 2})
    assert wait_step.ms == 2000
    assert ActionStep.parse({"action": "wait", "seconds": 30}).ms == 30_000
    assert ActionStep.parse({"action": "wait", "ms": 0}).ms == 0
    assert ActionStep.parse({"action": "click", "x": 1599, "y": 999}).ms == 0


@pytest.mark.parametrize(
    "payload",
    [
        "not-a-dict",
        {"action": "exec"},
        {"action": "click", "x": -1, "y": 10},
        {"action": "click", "x": 1600, "y": 10},
        {"action": "click", "x": 10, "y": 1000},
        {"action": "wait", "ms": 35_000},
        {"action": "wait", "ms": -1},
        {"action": "wait", "ms": "2000"},
        {"action": "wait", "ms": True},
        {"action": "wait", "seconds": "2"},
        {"action": "wait", "seconds": 2.5},
        {"action": "wait", "seconds": True},
        {"action": "wait", "seconds": [2]},
        {"action": "wait", "seconds": -1},
        {"action": "wait", "seconds": 31},
        {"action": "wait", "ms": 2000, "seconds": 2},
        {"action": "click", "x": True, "y": 10},
        {"action": "click", "x": 10, "y": 1.0},
        {"action": "click", "x": "10", "y": 10},
        {"action": "click", "text": 5},
        {"action": "click", "reason": None},
        {"action": "press"},
        {"action": "press", "text": ""},
        {"action": "type", "text": ""},
    ],
)
def test_invalid_action_step_is_rejected(payload: Any) -> None:
    with pytest.raises(DriverError):
        ActionStep.parse(payload)


def test_wait_step_with_both_ms_and_seconds_names_the_ambiguity() -> None:
    with pytest.raises(DriverError, match="not both"):
        ActionStep.parse({"action": "wait", "ms": 1000, "seconds": 1})


def test_scenario_spec_rejects_traversal_and_unknown_surface() -> None:
    with pytest.raises(DriverError, match="not a registered IDE surface"):
        ScenarioSpec.from_dict({"id": "x", "surface": "vim", "title": "t"})

    with pytest.raises(DriverError, match="relative"):
        ScenarioSpec.from_dict(
            {
                "id": "x",
                "surface": "eclipse",
                "title": "t",
                "seed_files": {"../escape.txt": "bad"},
            }
        )


@pytest.mark.parametrize(
    "rel",
    ["", "   ", " src/x.java", "src/x.java ", "src/", "./", ".", "/etc/passwd", "src/../x", "a/..", ".."],
)
def test_scenario_spec_rejects_seed_paths_that_do_not_name_a_file_inside_the_workspace(rel: str) -> None:
    with pytest.raises(DriverError, match="seed_files path"):
        ScenarioSpec.from_dict(
            {"id": "x", "surface": "eclipse", "title": "t", "seed_files": {rel: "content"}}
        )


def test_scenario_spec_accepts_dotted_relative_seed_path() -> None:
    spec = ScenarioSpec.from_dict(
        {"id": "x", "surface": "eclipse", "title": "t", "seed_files": {"./src/x.java": "class X {}"}}
    )
    assert spec.seed_files == {"./src/x.java": "class X {}"}


def spec_with_seeds(seed_files: dict[str, str]) -> ScenarioSpec:
    """A spec built directly, as code may, bypassing ``from_dict``'s path checks."""
    return ScenarioSpec(id="x", surface="eclipse", title="t", description="", seed_files=seed_files, actions=())


def test_seed_scenario_workspace_refuses_traversal_before_writing_anything(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    with pytest.raises(DriverError, match="escapes the workspace"):
        seed_scenario_workspace(workspace, spec_with_seeds({"ok.txt": "fine", "../escape.txt": "bad"}))
    assert not (tmp_path / "escape.txt").exists()
    assert not (workspace / "ok.txt").exists()


def test_seed_scenario_workspace_refuses_a_symbolic_link_out_of_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DriverError, match="escapes the workspace"):
        seed_scenario_workspace(workspace, spec_with_seeds({"link/file.txt": "bad"}))
    assert not (outside / "file.txt").exists()


def test_seed_scenario_workspace_refuses_the_workspace_itself(tmp_path: Path) -> None:
    with pytest.raises(DriverError, match="escapes the workspace"):
        seed_scenario_workspace(tmp_path, spec_with_seeds({".": "bad"}))


class FakeMouse:
    def __init__(self) -> None:
        self.events: list[tuple[str, int, int]] = []

    def move(self, x: int, y: int, steps: int = 1) -> None:
        self.events.append(("move", x, y))

    def click(self, x: int, y: int, button: str = "left") -> None:
        self.events.append((f"click:{button}", x, y))

    def dblclick(self, x: int, y: int) -> None:
        self.events.append(("dblclick", x, y))


class FakeKeyboard:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def type(self, text: str, delay: int = 0) -> None:
        self.events.append(("type", text))

    def press(self, key: str) -> None:
        self.events.append(("press", key))


class FakeCanvasPage:
    def __init__(self) -> None:
        self.mouse = FakeMouse()
        self.keyboard = FakeKeyboard()
        self.waits: list[int] = []

    def screenshot(self, *, path: str) -> None:
        Path(path).write_bytes(b"PNG")

    def wait_for_timeout(self, ms: int) -> None:
        self.waits.append(ms)

    def evaluate(self, script: str, png_b64: str) -> str:
        """Stand in for the canvas transcode: tag the bytes instead of encoding them."""
        return base64.b64encode(b"JPEG:" + base64.b64decode(png_b64)).decode("ascii")


class FailingCanvasPage(FakeCanvasPage):
    def evaluate(self, script: str, png_b64: str) -> str:
        raise RuntimeError("canvas lost")


def test_burst_frame_recorder_records_frames_only_during_active_steps(tmp_path: Path) -> None:
    page = FakeCanvasPage()
    recorder = BurstFrameRecorder(tmp_path / "frames")
    recorder.apply_step(page, ActionStep(action="click", x=100, y=200))
    recorder.apply_step(page, ActionStep(action="double_click", x=150, y=250))
    recorder.apply_step(page, ActionStep(action="right_click", x=150, y=250))
    recorder.apply_step(page, ActionStep(action="type", text="HelloTime"))
    recorder.apply_step(page, ActionStep(action="press", text="F11"))
    recorder.apply_step(page, ActionStep(action="wait", ms=500))

    assert recorder.frame_count > 20
    assert len(list((tmp_path / "frames").glob("frame-*.png"))) == recorder.frame_count
    assert ("press", "F11") in page.keyboard.events
    assert ("click:left", 100, 200) in page.mouse.events
    assert ("dblclick", 150, 250) in page.mouse.events
    assert ("click:right", 150, 250) in page.mouse.events


def test_ide_smoke_forwards_scenario_flag_to_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    session = Mock()
    session.env = {}
    session.posargs = ["--surface", "eclipse", "--scenario", "eclipse-hello-time-debug"]
    monkeypatch.delenv(noxfile.PEX_UNDER_TEST_ENV, raising=False)
    monkeypatch.setattr(noxfile, "build_test_pex", Mock())
    noxfile.ide_smoke(session)
    session.error.assert_not_called()
    assert session.env["DEVCAPSULE_SMOKE_SCENARIO"] == "eclipse-hello-time-debug"
    assert session.env["DEVCAPSULE_SMOKE_DISPLAY"] == "1"
    assert "-k" in session.run.call_args.args
    assert "eclipse" in session.run.call_args.args



class FakeFfmpeg:
    """Stands in for ``subprocess.Popen`` running ffmpeg: real pipes, no child process.

    ``encode`` answers with ``WEBM`` plus everything it was fed, at ``wait``. ``exit-early``
    has already closed its input and exited 1 before the first frame arrives. ``hang``
    never exits until ``kill``.
    """

    def __init__(self, args: list[str], *, stdin: Any, stdout: Any, stderr: Any, behaviour: str) -> None:
        self.args = args
        self.behaviour = behaviour
        self.returncode: int | None = None
        self.killed = False
        in_read, in_write = os.pipe()
        out_read, out_write = os.pipe()
        self.stdin = os.fdopen(in_write, "wb")
        self.stdout = os.fdopen(out_read, "rb")
        self._input = os.fdopen(in_read, "rb")
        self._output = os.fdopen(out_write, "wb")
        if behaviour == "exit-early":
            stderr.write(b"ffmpeg: bad input\n")
            self._exit(1)

    def _exit(self, code: int) -> None:
        self._input.close()
        self._output.close()
        self.returncode = code

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is None:
            if self.behaviour == "hang":
                raise subprocess.TimeoutExpired(self.args, timeout or 0)
            self._output.write(b"WEBM" + self._input.read())
            self._exit(0)
        assert self.returncode is not None
        return self.returncode

    def kill(self) -> None:
        if self.returncode is None:
            self.killed = True
            self._exit(-9)


def fake_ffmpeg(monkeypatch: pytest.MonkeyPatch, behaviour: str) -> list[FakeFfmpeg]:
    """Route the recorder's ``Popen`` to ``FakeFfmpeg`` and return the list it appends to."""
    started: list[FakeFfmpeg] = []

    def popen(args: list[str], **kwargs: Any) -> FakeFfmpeg:
        started.append(FakeFfmpeg(args, behaviour=behaviour, **kwargs))
        return started[-1]

    monkeypatch.setattr(scenario_recorder.subprocess, "Popen", popen)
    monkeypatch.setattr(BurstFrameRecorder, "_resolve_ffmpeg_cmd", staticmethod(lambda container: ["ffmpeg"]))
    return started


def recorder_with_frames(tmp_path: Path, count: int = 3) -> BurstFrameRecorder:
    recorder = BurstFrameRecorder(tmp_path / "frames")
    for index in range(1, count + 1):
        (recorder.frames_dir / f"frame-{index:05d}.png").write_bytes(f"PNG{index}".encode("ascii"))
    return recorder


def test_encode_webm_writes_ffmpeg_output_and_reaps_the_child(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = fake_ffmpeg(monkeypatch, "encode")
    recorder = recorder_with_frames(tmp_path)
    output = tmp_path / "scenario-video.webm"

    assert recorder.encode_webm(FakeCanvasPage(), output, fps=12) is True

    assert output.read_bytes() == b"WEBM" + b"".join(b"JPEG:PNG%d" % index for index in (1, 2, 3))
    (proc,) = started
    assert proc.args[-1] == "pipe:1" and "12" in proc.args
    assert proc.returncode == 0 and not proc.killed
    assert proc.stdin.closed and proc.stdout.closed
    assert (tmp_path / "scenario-video.webm.ffmpeg.log").is_file()


def test_encode_webm_returns_false_without_frames_or_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = fake_ffmpeg(monkeypatch, "encode")
    assert BurstFrameRecorder(tmp_path / "empty").encode_webm(FakeCanvasPage(), tmp_path / "out.webm") is False

    monkeypatch.setattr(BurstFrameRecorder, "_resolve_ffmpeg_cmd", staticmethod(lambda container: None))
    assert recorder_with_frames(tmp_path).encode_webm(FakeCanvasPage(), tmp_path / "out.webm") is False
    assert started == []
    assert not (tmp_path / "out.webm").exists()


def test_encode_webm_survives_ffmpeg_exiting_before_the_frames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = fake_ffmpeg(monkeypatch, "exit-early")
    output = tmp_path / "scenario-video.webm"

    assert recorder_with_frames(tmp_path).encode_webm(FakeCanvasPage(), output) is False

    (proc,) = started
    assert proc.returncode == 1 and not proc.killed
    assert proc.stdin.closed and proc.stdout.closed
    assert not output.exists()
    log = (tmp_path / "scenario-video.webm.ffmpeg.log").read_text(encoding="utf-8")
    assert "ffmpeg: bad input" in log and "encode_webm: BrokenPipeError" in log


def test_encode_webm_kills_ffmpeg_that_does_not_finish_in_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = fake_ffmpeg(monkeypatch, "hang")
    output = tmp_path / "scenario-video.webm"

    assert recorder_with_frames(tmp_path).encode_webm(FakeCanvasPage(), output, timeout=0.2) is False

    (proc,) = started
    assert proc.killed and proc.returncode == -9
    assert proc.stdin.closed and proc.stdout.closed
    assert not output.exists()
    assert "TimeoutExpired" in (tmp_path / "scenario-video.webm.ffmpeg.log").read_text(encoding="utf-8")


def test_encode_webm_kills_ffmpeg_when_a_frame_cannot_be_transcoded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = fake_ffmpeg(monkeypatch, "encode")
    output = tmp_path / "scenario-video.webm"

    assert recorder_with_frames(tmp_path).encode_webm(FailingCanvasPage(), output) is False

    (proc,) = started
    assert proc.killed and proc.stdin.closed and proc.stdout.closed
    assert not output.exists()
    assert "canvas lost" in (tmp_path / "scenario-video.webm.ffmpeg.log").read_text(encoding="utf-8")


def test_resolve_ffmpeg_cmd_falls_back_to_the_container_and_tolerates_a_missing_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scenario_recorder.shutil, "which", lambda name: None)
    assert BurstFrameRecorder._resolve_ffmpeg_cmd(None) is None

    probe = Mock(return_value=subprocess.CompletedProcess([], 0, stdout="/opt/playwright/browsers/ffmpeg-1/ffmpeg-linux\n", stderr=""))
    monkeypatch.setattr(scenario_recorder.subprocess, "run", probe)
    assert BurstFrameRecorder._resolve_ffmpeg_cmd("capsule") == [
        "docker", "exec", "-i", "capsule", "/opt/playwright/browsers/ffmpeg-1/ffmpeg-linux",
    ]
    assert probe.call_args.args[0][:3] == ["docker", "exec", "capsule"]

    monkeypatch.setattr(scenario_recorder.subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 0, stdout="", stderr="")))
    assert BurstFrameRecorder._resolve_ffmpeg_cmd("capsule") is None

    monkeypatch.setattr(scenario_recorder.subprocess, "run", Mock(side_effect=FileNotFoundError("docker")))
    assert BurstFrameRecorder._resolve_ffmpeg_cmd("capsule") is None

    monkeypatch.setattr(scenario_recorder.subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired(["docker"], 15)))
    assert BurstFrameRecorder._resolve_ffmpeg_cmd("capsule") is None


def test_write_json_atomically_leaves_only_the_target(tmp_path: Path) -> None:
    target = tmp_path / "controller.json"
    write_json_atomically(target, {"port": 4242})
    assert json.loads(target.read_text(encoding="utf-8")) == {"port": 4242}
    assert [p.name for p in tmp_path.iterdir()] == ["controller.json"]


def test_write_json_atomically_keeps_the_old_file_when_the_rename_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "controller.json"
    target.write_text('{"port": 1}\n', encoding="utf-8")
    monkeypatch.setattr(scenario_recorder.os, "replace", Mock(side_effect=OSError("no rename")))
    with pytest.raises(OSError, match="no rename"):
        write_json_atomically(target, {"port": 2})
    assert target.read_text(encoding="utf-8") == '{"port": 1}\n'
    assert [p.name for p in tmp_path.iterdir()] == ["controller.json"]


def post_raw(port: int, body: bytes) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(f"http://127.0.0.1:{port}/", data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_controller_round_trip_and_error_answers(tmp_path: Path) -> None:
    queue = ControllerQueue()
    server = start_controller_server(queue, timeout=0.3)
    port = server.server_address[1]
    try:
        write_json_atomically(tmp_path / "controller.json", {"port": port})

        def answer_one() -> None:
            while (item := queue.take()) is None:
                time.sleep(0.01)
            payload, done, response = item
            response.update(ok=True, echo=payload)
            done.set()

        worker = threading.Thread(target=answer_one)
        worker.start()
        assert send_controller_command(tmp_path, {"cmd": "act", "actions": []}) == {
            "ok": True, "echo": {"cmd": "act", "actions": []},
        }
        worker.join(timeout=5)

        status, answer = post_raw(port, b"{not json")
        assert (status, answer["ok"]) == (400, False) and answer["error"].startswith("malformed command: Expecting")
        assert post_raw(port, b"[1]") == (400, {"ok": False, "error": "malformed command: the command must be a JSON object"})
        status, answer = post_raw(port, b"\xff")
        assert (status, answer["ok"]) == (400, False) and "codec can't decode" in answer["error"]
        assert queue.take() is None, "a malformed command must never reach the Playwright loop"

        assert send_controller_command(tmp_path, {"cmd": "screenshot"}) == {
            "ok": False, "error": "the controller did not answer within 0.3 s",
        }
        assert queue.take() is not None, "the unanswered command stays queued for the loop"
    finally:
        server.shutdown()
        server.server_close()


def test_send_controller_command_times_out_without_controller_json(tmp_path: Path) -> None:
    with pytest.raises(TimeoutError, match="controller.json did not appear"):
        send_controller_command(tmp_path, {"cmd": "screenshot"}, timeout=0)


def test_serve_removes_a_stale_controller_json_before_launching(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = Mock()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    monkeypatch.setenv("DEVCAPSULE_SMOKE_COMPONENT_BROWSER", "0")
    monkeypatch.setattr(scenario_recorder, "ide_session", Mock(side_effect=RuntimeError("no capsule here")))
    stale = tmp_path / "controller.json"
    stale.write_text('{"port": 1}\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="no capsule here"):
        serve_interactive_controller(Path("devcapsule.pex"), load_scenario("eclipse-hello-time-debug"), tmp_path)
    assert not stale.exists()


def test_ctl_rejects_a_payload_that_is_not_a_json_object(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for payload in ("{not json", "[1]"):
        with pytest.raises(SystemExit) as exit_info:
            main(["ctl", "--evidence", str(tmp_path), payload])
        assert exit_info.value.code == 2
    assert "payload" in capsys.readouterr().err


def test_ctl_exit_status_follows_the_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    answers = iter([{"ok": True, "screenshot": "step-001.png"}, {"ok": False, "error": "Unknown cmd: dance"}])
    sent: list[dict[str, Any]] = []

    def fake_send(evidence: Path, payload: dict[str, Any], timeout: float = 180.0) -> dict[str, Any]:
        sent.append(payload)
        return next(answers)

    monkeypatch.setattr(scenario_recorder, "send_controller_command", fake_send)
    assert main(["ctl", "--evidence", str(tmp_path)]) == 0
    assert main(["ctl", "--evidence", str(tmp_path), '{"cmd":"dance"}']) == 1
    assert sent == [{"cmd": "screenshot"}, {"cmd": "dance"}]
    assert "Unknown cmd: dance" in capsys.readouterr().out


@pytest.mark.parametrize(
    "posargs, message",
    [
        (["--scenario", "eclipse-hello-time-debug"], "exactly one --surface"),
        (["--scenario", "eclipse-hello-time-debug", "--surface", "eclipse", "--surface", "intellij"], "exactly one --surface"),
        (["--scenario", "eclipse-hello-time-debug", "--surface", "eclipse", "--agent"], "cannot be combined with --agent"),
        (["--scenario", "eclipse-hello-time-debug", "--surface", "intellij", "--agent", "--relaunch"], "cannot be combined with --agent"),
    ],
)
def test_ide_smoke_refuses_scenario_option_combinations(monkeypatch: pytest.MonkeyPatch, posargs: list[str], message: str) -> None:
    session = Mock()
    session.env = {}
    session.posargs = posargs
    session.error = Mock(side_effect=RuntimeError("nox stopped"))
    monkeypatch.delenv(noxfile.PEX_UNDER_TEST_ENV, raising=False)
    monkeypatch.setattr(noxfile, "build_test_pex", Mock())
    with pytest.raises(RuntimeError, match="nox stopped"):
        noxfile.ide_smoke(session)
    assert message in session.error.call_args.args[0]
    session.run.assert_not_called()
