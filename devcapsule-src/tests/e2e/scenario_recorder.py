"""Scenario-driven E2E IDE session controller and pause-free WebM video recorder.

Supports two execution modes over the shared ``ide_session`` and ``smoke_browser``
infrastructure:

1. **Interactive agent takeover (``serve`` / ``ctl``):** launches the target IDE
   surface in a disposable DevCapsule, connects Playwright to the desktop canvas,
   and exposes a local HTTP controller (``controller.json``) accepting
   ``screenshot``, batched ``act`` (``click``, ``double_click``, ``right_click``,
   ``type``, ``press``, ``wait``), and ``stop``. Frames are captured only during
   active UI interactions so LLM thinking time between turns never produces frozen
   dead air in the encoded ``scenario-video.webm``.
2. **Deterministic scenario replay (``run_scenario_replay`` / ``replay``):**
   seeds the scenario's project files into ``session.workspace``, executes its
   recorded ``ActionStep`` sequence, and produces ``scenario-video.webm``,
   ``agent-desktop-raw.webm``, ``step-NNN.png`` screenshots, and
   ``scenario-result.json``.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any
import urllib.error
import urllib.request

from tests.e2e.ai_driver import DriverError
from tests.e2e.browser_session import smoke_browser
from tests.e2e.ide_session import (
    SURFACES,
    IdeSurface,
    SessionFacts,
    desktop_page_answers,
    ide_session,
    top_level_windows,
    wait_for_ide_window,
)

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
VALID_STEP_ACTIONS = ("click", "double_click", "right_click", "type", "press", "wait", "launch_browser")
MAX_WAIT_MS = 30_000
"""Longest ``wait`` step; ``seconds`` is accepted up to the same bound."""
CONTROLLER_COMMAND_TIMEOUT = 120.0
"""Seconds one controller command may take before the HTTP server answers with an error."""

SURFACE_SHORTCUTS: dict[str, dict[str, str]] = {
    "eclipse": {
        "open_resource": "Control+Shift+r",
        "open_type": "Control+Shift+t",
        "find_actions": "Control+3",
        "go_to_line": "Control+l",
        "toggle_breakpoint": "Control+Shift+b",
        "debug_last": "F11",
        "run_last": "Control+F11",
        "step_into": "F5",
        "step_over": "F6",
        "step_return": "F7",
        "resume": "F8",
        "save": "Control+s",
    },
    "intellij": {
        "find_action": "Control+Shift+a",
        "open_file": "Control+Shift+n",
        "go_to_line": "Control+g",
        "toggle_breakpoint": "Control+F8",
        "debug": "Shift+F9",
        "run": "Shift+F10",
        "step_into": "F7",
        "step_over": "F8",
        "resume": "F9",
        "save": "Control+s",
    },
    "pycharm": {
        "find_action": "Control+Shift+a",
        "open_file": "Control+Shift+n",
        "go_to_line": "Control+g",
        "toggle_breakpoint": "Control+F8",
        "debug": "Shift+F9",
        "run": "Shift+F10",
        "step_into": "F7",
        "step_over": "F8",
        "resume": "F9",
        "save": "Control+s",
    },
    "codium": {
        "command_palette": "Control+Shift+p",
        "quick_open": "Control+p",
        "go_to_line": "Control+g",
        "toggle_breakpoint": "F9",
        "debug": "F5",
        "step_over": "F10",
        "step_into": "F11",
        "save": "Control+s",
    },
    "rider": {
        "find_action": "Control+Shift+a",
        "open_file": "Control+Shift+n",
        "go_to_line": "Control+g",
        "toggle_breakpoint": "Control+F8",
        "debug": "Shift+F9",
        "run": "Shift+F10",
        "step_over": "F8",
        "resume": "F9",
        "save": "Control+s",
    },
}


def _wait_milliseconds(value: dict[Any, Any]) -> object:
    """Return the step's wait from ``ms``, or from ``seconds`` when only ``seconds`` is given.

    The caller range-checks the result; this only refuses an ambiguous or non-integer source.
    """
    if "ms" in value and "seconds" in value:
        raise DriverError("ActionStep takes either ms or seconds, not both")
    if "seconds" not in value:
        return value.get("ms", 0)
    seconds = value["seconds"]
    if type(seconds) is not int:
        raise DriverError(f"Invalid wait seconds: {seconds!r}")
    return seconds * 1000


def _checked_seed_path(rel: str) -> str:
    """Return ``rel`` when it names a file by a plain relative path; raise otherwise.

    Rejected: empty or padded strings, a trailing slash (a directory, not a file), an
    absolute path, and any ``..`` component. ``seed_scenario_workspace`` re-checks the
    resolved target, so a symbolic link cannot carry a write outside the workspace.
    """
    if not rel.strip() or rel != rel.strip():
        raise DriverError(f"Scenario seed_files path must not be empty or padded: {rel!r}")
    if rel.endswith("/"):
        raise DriverError(f"Scenario seed_files path must name a file, not a directory: {rel!r}")
    path = Path(rel)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise DriverError(f"Scenario seed_files path must be relative: {rel!r}")
    return rel


@dataclass(frozen=True)
class ActionStep:
    """One mouse, keyboard, or bounded wait step in a scenario."""

    action: str
    x: int = 0
    y: int = 0
    text: str = ""
    ms: int = 0
    reason: str = ""

    @classmethod
    def parse(cls, value: object) -> ActionStep:
        if not isinstance(value, dict):
            raise DriverError("ActionStep must be a JSON object")
        action = value.get("action")
        if not isinstance(action, str) or action not in VALID_STEP_ACTIONS:
            raise DriverError(f"Unsupported scenario action: {action!r}")
        x = value.get("x", 0)
        y = value.get("y", 0)
        ms = _wait_milliseconds(value)
        text = value.get("text", "")
        reason = value.get("reason", "")
        if type(x) is not int or not (0 <= x <= 1599):
            raise DriverError(f"Invalid x coordinate: {x!r}")
        if type(y) is not int or not (0 <= y <= 999):
            raise DriverError(f"Invalid y coordinate: {y!r}")
        if type(ms) is not int or not (0 <= ms <= MAX_WAIT_MS):
            raise DriverError(f"Invalid wait ms: {ms!r}")
        if not isinstance(text, str) or not isinstance(reason, str):
            raise DriverError("ActionStep text and reason must be strings")
        if action in ("type", "press", "launch_browser") and not text:
            raise DriverError(f"Scenario action {action!r} requires non-empty text")
        return cls(action=action, x=x, y=y, text=text, ms=ms, reason=reason)

    def substitute(self, variables: dict[str, str]) -> ActionStep:
        text = self.text
        for key, val in variables.items():
            text = text.replace(f"${{{key}}}", val)
        return ActionStep(
            action=self.action,
            x=self.x,
            y=self.y,
            text=text,
            ms=self.ms,
            reason=self.reason,
        )


@dataclass(frozen=True)
class ScenarioSpec:
    """Declarative specification of an E2E IDE scenario and its seed project."""

    id: str
    surface: str
    title: str
    description: str
    seed_files: dict[str, str]
    actions: tuple[ActionStep, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioSpec:
        scenario_id = str(data.get("id") or "").strip()
        surface = str(data.get("surface") or "").strip()
        title = str(data.get("title") or "").strip()
        description = str(data.get("description") or "").strip()
        if not scenario_id or not surface or not title:
            raise DriverError("Scenario requires non-empty id, surface, and title")
        if surface not in {s.name for s in SURFACES}:
            raise DriverError(f"Scenario surface {surface!r} is not a registered IDE surface")
        raw_seeds = data.get("seed_files") or {}
        if not isinstance(raw_seeds, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in raw_seeds.items()
        ):
            raise DriverError("Scenario seed_files must be a string-to-string mapping")
        for rel in raw_seeds:
            _checked_seed_path(rel)
        raw_actions = data.get("actions") or []
        if not isinstance(raw_actions, list):
            raise DriverError("Scenario actions must be a list")
        actions = tuple(ActionStep.parse(item) for item in raw_actions)
        return cls(
            id=scenario_id,
            surface=surface,
            title=title,
            description=description,
            seed_files=dict(raw_seeds),
            actions=actions,
        )


def list_scenarios() -> list[str]:
    """Return sorted scenario IDs available under ``tests/e2e/scenarios/``."""
    if not SCENARIOS_DIR.is_dir():
        return []
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))


def load_scenario(name_or_path: str | Path) -> ScenarioSpec:
    """Load a scenario by its catalog ID or from an explicit JSON file path."""
    candidate = Path(name_or_path)
    if not candidate.is_file():
        candidate = SCENARIOS_DIR / f"{name_or_path}.json"
    if not candidate.is_file():
        raise DriverError(f"Scenario not found: {name_or_path}")
    data = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DriverError(f"Scenario file must contain a JSON object: {candidate}")
    return ScenarioSpec.from_dict(data)


def seed_scenario_workspace(workspace: Path, spec: ScenarioSpec) -> list[Path]:
    """Write ``spec.seed_files`` into ``workspace`` and return the written paths.

    Every target is resolved first and must lie strictly inside ``workspace``; a path
    that escapes it, through ``..`` or a symbolic link, raises ``DriverError`` before
    any file is written.
    """
    root = workspace.resolve()
    targets: list[tuple[Path, str]] = []
    for rel_path, content in spec.seed_files.items():
        target = (root / rel_path).resolve()
        if root not in target.parents:
            raise DriverError(f"Scenario seed_files path escapes the workspace: {rel_path!r}")
        targets.append((target, content))
    written: list[Path] = []
    for target, content in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def _launch_capsule_browser(container: str, url: str) -> None:
    """Launch headed Chromium on the child capsule's X11 display pointing at ``url``."""
    script = f"""
set -euo pipefail
DISP_NUM=$(ls /tmp/.X11-unix | sort | head -n 1 | cut -c2-)
XAUTH=$(ls /tmp/devcapsule-runtime-*/display/Xauthority | sort | head -n 1)
CHROME=$(ls /opt/playwright/browsers/chromium-*/chrome-linux*/chrome | sort | tail -n 1)
export DISPLAY=":$DISP_NUM"
export XAUTHORITY="$XAUTH"
nohup "$CHROME" \\
  --no-sandbox \\
  --disable-dev-shm-usage \\
  --disable-gpu \\
  --no-first-run \\
  --no-default-browser-check \\
  --disable-infobars \\
  --user-data-dir=/tmp/scenario-chrome-profile \\
  --window-position=470,46 \\
  --window-size=1105,910 \\
  --app="{url}" </dev/null >/tmp/scenario-chrome.log 2>&1 &
"""
    res = subprocess.run(
        ["docker", "exec", "-d", "--user", f"{os.getuid()}:{os.getgid()}", container, "bash", "-lc", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=30.0,
    )
    if res.returncode != 0:
        raise DriverError(f"Failed to launch browser in capsule: {res.stdout}\n{res.stderr}")


class BurstFrameRecorder:
    """Captures active UI transition frames to eliminate LLM-thinking dead air."""

    def __init__(self, frames_dir: Path) -> None:
        self.frames_dir = frames_dir
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.frame_count = 0

    def record_frames(self, page: Any, count: int = 4, interval_ms: int = 120) -> None:
        for _ in range(count):
            self.frame_count += 1
            page.screenshot(path=str(self.frames_dir / f"frame-{self.frame_count:05d}.png"))
            if interval_ms > 0:
                page.wait_for_timeout(interval_ms)

    def apply_step(self, page: Any, step: ActionStep, container: str | None = None) -> None:
        kind = step.action
        if kind == "click":
            page.mouse.move(step.x, step.y, steps=6)
            self.record_frames(page, count=2, interval_ms=60)
            page.mouse.click(step.x, step.y)
            self.record_frames(page, count=5, interval_ms=120)
        elif kind == "double_click":
            page.mouse.move(step.x, step.y, steps=6)
            self.record_frames(page, count=2, interval_ms=60)
            page.mouse.dblclick(step.x, step.y)
            self.record_frames(page, count=6, interval_ms=120)
        elif kind == "right_click":
            page.mouse.move(step.x, step.y, steps=6)
            self.record_frames(page, count=2, interval_ms=60)
            page.mouse.click(step.x, step.y, button="right")
            self.record_frames(page, count=5, interval_ms=120)
        elif kind == "type":
            text = step.text
            chunk_size = max(1, len(text) // 6) if text else 1
            for i in range(0, len(text), chunk_size):
                page.keyboard.type(text[i : i + chunk_size], delay=20)
                self.record_frames(page, count=1, interval_ms=40)
            self.record_frames(page, count=4, interval_ms=100)
        elif kind == "press":
            page.keyboard.press(step.text)
            self.record_frames(page, count=6, interval_ms=120)
        elif kind == "wait":
            slices = max(1, step.ms // 150)
            recorded = min(slices, 20)
            self.record_frames(page, count=recorded, interval_ms=150)
            rem = step.ms - recorded * 150
            if rem > 0:
                page.wait_for_timeout(rem)
        elif kind == "launch_browser":
            if not container:
                raise DriverError("Scenario action 'launch_browser' requires an active capsule container")
            _launch_capsule_browser(container, step.text)
            self.record_frames(page, count=16, interval_ms=160)
        else:
            raise DriverError(f"Unsupported action step: {kind}")

    def encode_webm(
        self,
        page: Any,
        output_webm: Path,
        container: str | None = None,
        fps: int = 12,
        timeout: float = 60.0,
    ) -> bool:
        """Encode the recorded PNG frames into a pause-free VP8 WebM through ``ffmpeg``.

        Each frame is transcoded to JPEG in the page's canvas and piped to ``ffmpeg``,
        which writes the WebM to its stdout, because a container-side ``ffmpeg`` cannot
        write a parent-side file. ``ffmpeg``'s stderr goes to ``<output>.ffmpeg.log``, so
        a full stderr pipe can never stall it. Returns False when there are no frames or
        no ``ffmpeg``, when a frame cannot be transcoded, when ``ffmpeg`` fails or exits
        early, or when it has not finished ``timeout`` seconds after the last frame; the
        failure is appended to the log. On every path the child is reaped, the reader
        thread joined, and the pipes closed before this returns.
        """
        frames = sorted(self.frames_dir.glob("frame-*.png"))
        if not frames:
            return False

        ffmpeg_cmd = self._resolve_ffmpeg_cmd(container)
        if ffmpeg_cmd is None:
            return False

        log_path = output_webm.with_name(output_webm.name + ".ffmpeg.log")
        with log_path.open("wb") as log:
            proc = subprocess.Popen(
                [*ffmpeg_cmd, "-y", "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(fps),
                 "-i", "pipe:0", "-c:v", "libvpx", "-b:v", "3M", "-crf", "10", "-f", "webm", "pipe:1"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=log,
            )
        assert proc.stdin is not None
        assert proc.stdout is not None
        stdin, stdout = proc.stdin, proc.stdout
        chunks: list[bytes] = []

        def reader() -> None:
            while data := stdout.read(65536):
                chunks.append(data)

        read_thread = threading.Thread(target=reader, daemon=True)
        read_thread.start()

        encoded = False
        try:
            for frame_path in frames:
                stdin.write(self._transcode_to_jpeg(page, frame_path))
            stdin.close()
            returncode = proc.wait(timeout=timeout)
            read_thread.join(timeout=timeout)
            encoded = returncode == 0 and not read_thread.is_alive() and bool(chunks)
        except Exception as exc:  # a broken pipe, the wait timeout, or a page failure
            with log_path.open("ab") as log:
                log.write(f"\nencode_webm: {exc!r}\n".encode("utf-8"))
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            read_thread.join(timeout=5)
            for stream in (stdin, stdout):
                try:
                    stream.close()
                except OSError:
                    pass
        if encoded:
            output_webm.write_bytes(b"".join(chunks))
        return encoded

    @staticmethod
    def _transcode_to_jpeg(page: Any, frame_path: Path) -> bytes:
        """Return ``frame_path`` as JPEG bytes, converted by a canvas in ``page``."""
        b64 = base64.b64encode(frame_path.read_bytes()).decode("ascii")
        jpeg_b64 = page.evaluate(
            """async (b64) => {
                const img = new Image();
                img.src = "data:image/png;base64," + b64;
                await img.decode();
                const c = document.createElement("canvas");
                c.width = img.width;
                c.height = img.height;
                c.getContext("2d").drawImage(img, 0, 0);
                return c.toDataURL("image/jpeg", 0.95).split(",")[1];
            }""",
            b64,
        )
        return base64.b64decode(jpeg_b64)

    @staticmethod
    def _resolve_ffmpeg_cmd(container: str | None) -> list[str] | None:
        """Return the ``ffmpeg`` command: the host's, else the child container's, else None."""
        local = shutil.which("ffmpeg")
        if local:
            return [local]
        if container:
            try:
                probe = subprocess.run(
                    ["docker", "exec", container, "sh", "-c",
                     "ls /opt/playwright/browsers/ffmpeg-*/ffmpeg-linux 2>/dev/null | head -n 1"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
            except (OSError, subprocess.TimeoutExpired):
                return None
            child_ffmpeg = probe.stdout.strip()
            if probe.returncode == 0 and child_ffmpeg:
                return ["docker", "exec", "-i", container, child_ffmpeg]
        return None


def run_scenario_replay(
    session: SessionFacts,
    evidence: Path,
    spec: ScenarioSpec,
) -> dict[str, Any]:
    """Seed ``spec`` into ``session.workspace``, replay its actions, and record video."""
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found,unused-ignore]

    evidence.mkdir(parents=True, exist_ok=True)
    seed_scenario_workspace(session.workspace, spec)
    recorder = BurstFrameRecorder(evidence / "video-frames")
    variables = {
        "PROJECT_PATH": session.project_path or str(session.workspace),
        "WORKSPACE": str(session.workspace),
    }

    executed: list[dict[str, Any]] = []
    step_screenshots: list[str] = []

    with sync_playwright() as playwright, smoke_browser(playwright, session, evidence) as browser:
        viewport = {"width": 1600, "height": 1000}
        context = browser.new_context(
            viewport=viewport,
            record_video_dir=str(evidence),
            record_video_size=viewport,
        )
        page = context.new_page()
        video = page.video
        encoded = False
        try:
            page.goto(session.desktop_url, wait_until="load")
            page.locator("canvas").first.wait_for(state="visible", timeout=60_000)
            page.wait_for_timeout(3000)
            recorder.record_frames(page, count=8, interval_ms=120)

            for index, raw_step in enumerate(spec.actions, start=1):
                step = raw_step.substitute(variables)
                recorder.apply_step(page, step, container=session.container)
                executed.append(asdict(step))
                shot = evidence / f"step-{index:03d}.png"
                page.screenshot(path=str(shot))
                step_screenshots.append(shot.name)

            recorder.record_frames(page, count=12, interval_ms=120)
            if step_screenshots:
                shutil.copyfile(evidence / step_screenshots[-1], evidence / "poster.png")
            encoded = recorder.encode_webm(
                page,
                evidence / "scenario-video.webm",
                container=session.container,
            )
        finally:
            context.close()
            if video is not None:
                video.save_as(str(evidence / "agent-desktop-raw.webm"))
                video.delete()

    result = {
        "scenario_id": spec.id,
        "surface": spec.surface,
        "title": spec.title,
        "status": "passed",
        "steps_executed": len(executed),
        "frames_recorded": recorder.frame_count,
        "pause_free_webm": "scenario-video.webm" if encoded else None,
        "raw_webm": "agent-desktop-raw.webm",
        "screenshots": step_screenshots,
    }
    (evidence / "action-log.json").write_text(json.dumps(executed, indent=2) + "\n", encoding="utf-8")
    (evidence / "scenario-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


ControllerCommand = tuple[dict[str, Any], threading.Event, dict[str, Any]]
"""A posted payload, the event its HTTP handler waits on, and the answer the loop fills in."""


class ControllerQueue:
    """Commands posted over HTTP, taken one at a time by the Playwright loop."""

    def __init__(self) -> None:
        self._items: list[ControllerCommand] = []
        self._lock = threading.Lock()

    def put(self, payload: dict[str, Any]) -> tuple[threading.Event, dict[str, Any]]:
        done = threading.Event()
        response: dict[str, Any] = {}
        with self._lock:
            self._items.append((payload, done, response))
        return done, response

    def take(self) -> ControllerCommand | None:
        with self._lock:
            return self._items.pop(0) if self._items else None


def start_controller_server(queue: ControllerQueue, timeout: float = CONTROLLER_COMMAND_TIMEOUT) -> HTTPServer:
    """Serve POST commands on a loopback port, in a daemon thread, until ``shutdown``.

    A body that is not a JSON object gets ``400`` and never reaches the queue. A
    queued command that the loop has not answered after ``timeout`` seconds gets
    ``504``; the loop still runs it. Every answer is a JSON object.
    """

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
                if not isinstance(payload, dict):
                    raise ValueError("the command must be a JSON object")
            except ValueError as exc:
                self._reply(400, {"ok": False, "error": f"malformed command: {exc}"})
                return
            done, response = queue.put(payload)
            if not done.wait(timeout=timeout):
                self._reply(504, {"ok": False, "error": f"the controller did not answer within {timeout:g} s"})
                return
            self._reply(200, response)

        def _reply(self, status: int, body: dict[str, Any]) -> None:
            encoded = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def write_json_atomically(path: Path, data: Any) -> None:
    """Write ``data`` as JSON so a concurrent reader sees the old file or the whole new one."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def serve_interactive_controller(
    executable: Path,
    spec: ScenarioSpec,
    evidence: Path,
) -> None:
    """Start an interactive E2E IDE session and HTTP controller for live agent takeover.

    ``controller.json`` under ``evidence`` names the port once the IDE is ready; a stale
    copy from an earlier run is removed first, so a waiting ``ctl`` never dials a dead port.
    """
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found,unused-ignore]

    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "controller.json").unlink(missing_ok=True)
    os.environ["DEVCAPSULE_SMOKE_COMPONENT_BROWSER"] = "1"
    surface: IdeSurface = next(s for s in SURFACES if s.name == spec.surface)
    recorder = BurstFrameRecorder(evidence / "video-frames")
    action_log: list[dict[str, Any]] = []
    step_counter = 0

    with tempfile.TemporaryDirectory() as tmp_str:
        with ide_session(executable, surface, Path(tmp_str), evidence) as session:
            seed_scenario_workspace(session.workspace, spec)
            assert desktop_page_answers(session.desktop_url) == 200
            window = wait_for_ide_window(session)
            variables = {
                "PROJECT_PATH": session.project_path or str(session.workspace),
                "WORKSPACE": str(session.workspace),
            }

            with sync_playwright() as pw, smoke_browser(pw, session, evidence) as browser:
                viewport = {"width": 1600, "height": 1000}
                context = browser.new_context(
                    viewport=viewport,
                    record_video_dir=str(evidence),
                    record_video_size=viewport,
                )
                page = context.new_page()
                video = page.video
                page.goto(session.desktop_url, wait_until="load")
                page.locator("canvas").first.wait_for(state="visible", timeout=60_000)
                page.wait_for_timeout(3000)
                recorder.record_frames(page, count=8, interval_ms=120)

                queue = ControllerQueue()
                server = start_controller_server(queue)
                port = server.server_address[1]

                info = {
                    "port": port,
                    "scenario_id": spec.id,
                    "surface": spec.surface,
                    "shortcuts": SURFACE_SHORTCUTS.get(spec.surface, {}),
                    "container": session.container,
                    "workspace": str(session.workspace),
                    "project_path": session.project_path,
                    "initial_window": window,
                }
                write_json_atomically(evidence / "controller.json", info)
                print(f"CONTROLLER_READY port={port} project_path={session.project_path}", flush=True)

                stopped = False
                try:
                    while not stopped:
                        item = queue.take()
                        if item is None:
                            time.sleep(0.05)
                            continue
                        payload, done, response = item
                        try:
                            cmd = payload.get("cmd", "screenshot")
                            if cmd == "screenshot":
                                step_counter += 1
                                shot = evidence / f"step-{step_counter:03d}.png"
                                page.screenshot(path=str(shot))
                                response.update(
                                    ok=True,
                                    screenshot=str(shot),
                                    windows=top_level_windows(session.container),
                                    frames_recorded=recorder.frame_count,
                                )
                            elif cmd == "act":
                                raw_actions = payload.get("actions", [])
                                for raw in raw_actions:
                                    step = ActionStep.parse(raw).substitute(variables)
                                    recorder.apply_step(page, step, container=session.container)
                                    action_log.append(asdict(step))
                                step_counter += 1
                                shot = evidence / f"step-{step_counter:03d}.png"
                                page.screenshot(path=str(shot))
                                response.update(
                                    ok=True,
                                    screenshot=str(shot),
                                    windows=top_level_windows(session.container),
                                    frames_recorded=recorder.frame_count,
                                )
                            elif cmd == "stop":
                                recorder.record_frames(page, count=12, interval_ms=120)
                                encoded = recorder.encode_webm(
                                    page,
                                    evidence / "scenario-video.webm",
                                    container=session.container,
                                )
                                response.update(
                                    ok=True,
                                    stopping=True,
                                    frames_recorded=recorder.frame_count,
                                    pause_free_webm=encoded,
                                )
                                stopped = True
                            else:
                                response.update(ok=False, error=f"Unknown cmd: {cmd}")
                        except Exception as exc:
                            response.update(ok=False, error=str(exc))
                        finally:
                            done.set()
                finally:
                    server.shutdown()
                    server.server_close()
                    (evidence / "action-log.json").write_text(
                        json.dumps(action_log, indent=2) + "\n", encoding="utf-8"
                    )
                    context.close()
                    if video is not None:
                        video.save_as(str(evidence / "agent-desktop-raw.webm"))
                        video.delete()


def send_controller_command(evidence: Path, payload: dict[str, Any], timeout: float = 180.0) -> dict[str, Any]:
    """Send one JSON command to a running ``serve_interactive_controller`` and return its answer.

    Waits up to ``timeout`` seconds for ``controller.json`` to appear. An error answer from
    the server (``400`` or ``504``) is returned as its JSON body, with ``ok`` false, so the
    caller sees the reason instead of an exception.
    """
    ctrl_file = evidence / "controller.json"
    deadline = time.monotonic() + timeout
    while not ctrl_file.is_file():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"controller.json did not appear in {evidence}")
        time.sleep(0.5)
    info = json.loads(ctrl_file.read_text(encoding="utf-8"))
    port = info["port"]
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=CONTROLLER_COMMAND_TIMEOUT + 5) as resp:
            body = resp.read()
    except urllib.error.HTTPError as error:
        body = error.read()
    result = json.loads(body.decode("utf-8"))
    assert isinstance(result, dict)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tests.e2e.scenario_recorder")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("list", help="List available E2E scenario definitions")

    serve_p = sub.add_parser("serve", help="Start an interactive E2E IDE session controller")
    serve_p.add_argument("--scenario", required=True, help="Scenario ID or path to JSON")
    serve_p.add_argument(
        "--evidence",
        type=Path,
        default=None,
        help="Evidence output directory (default: tests/e2e/evidence/<scenario-id>)",
    )
    serve_p.add_argument("--pex", type=Path, required=True, help="Path to devcapsule PEX executable")

    ctl_p = sub.add_parser("ctl", help="Send a JSON command to a running controller")
    ctl_p.add_argument("--evidence", type=Path, required=True, help="Evidence directory containing controller.json")
    ctl_p.add_argument("payload", nargs="?", default='{"cmd":"screenshot"}', help="JSON command payload")

    replay_p = sub.add_parser("replay", help="Run a scenario deterministically and record video")
    replay_p.add_argument("--scenario", required=True, help="Scenario ID or path to JSON")
    replay_p.add_argument(
        "--evidence",
        type=Path,
        default=None,
        help="Evidence output directory (default: tests/e2e/evidence/<scenario-id>)",
    )
    replay_p.add_argument("--pex", type=Path, required=True, help="Path to devcapsule PEX executable")

    args = parser.parse_args(argv)
    if args.subcommand == "list":
        for name in list_scenarios():
            print(name)
        return 0
    if args.subcommand == "serve":
        spec = load_scenario(args.scenario)
        evidence = args.evidence if args.evidence is not None else EVIDENCE_DIR / spec.id
        serve_interactive_controller(args.pex, spec, evidence)
        return 0
    if args.subcommand == "ctl":
        try:
            payload = json.loads(args.payload)
        except ValueError as exc:
            parser.error(f"payload is not JSON: {exc}")
        if not isinstance(payload, dict):
            parser.error("payload must be a JSON object")
        res = send_controller_command(args.evidence, payload)
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    if args.subcommand == "replay":
        os.environ["DEVCAPSULE_SMOKE_COMPONENT_BROWSER"] = "1"
        spec = load_scenario(args.scenario)
        evidence = args.evidence if args.evidence is not None else EVIDENCE_DIR / spec.id
        surface = next(s for s in SURFACES if s.name == spec.surface)
        with tempfile.TemporaryDirectory() as tmp_str:
            with ide_session(args.pex, surface, Path(tmp_str), evidence) as session:
                assert desktop_page_answers(session.desktop_url) == 200
                wait_for_ide_window(session)
                result = run_scenario_replay(session, evidence, spec)
                print(json.dumps(result, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
