"""Interactive controller and deterministic replayer for the FastAPI + PostgreSQL + React Todo scenario.

Builds on ``tests.e2e.ide_session``, ``tests.e2e.browser_session``, and
``tests.e2e.scenario_recorder``, adding disposable PostgreSQL 17 orchestration,
offline/pre-recording dependency installation, cursor overlay visualization,
and outside-in HTTP + ``psql`` postcondition verification.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterator
import urllib.request

from tests.e2e.browser_session import smoke_browser
from tests.e2e.ide_session import (
    IdeSurface,
    SessionFacts,
    command,
    desktop_page_answers,
    initialize_project,
    launched_ide,
    remove_project_records,
    top_level_windows,
    wait_for_ide_window,
    workspace_root,
)
from tests.e2e.scenario_recorder import (
    EVIDENCE_DIR,
    SCENARIOS_DIR,
    VIDEO_FRAMES_PER_SECOND,
    BurstFrameRecorder,
    ControllerQueue,
    send_controller_command,
    start_controller_server,
    write_json_atomically,
)
from tests.e2e.scenario_presentation import plan_for_scenario, write_presentation
from tests.e2e.todo_seed import (
    API_PORT,
    DB_URL,
    PG_PORT,
    VITE_PORT,
    write_seed_project,
)

__all__ = [
    "DEMO_SCENARIO_ID",
    "DEMO_SURFACE",
    "DemoStep",
    "apply_demo_step",
    "main",
    "replay_mode",
    "serve_mode",
]

DEMO_SCENARIO_ID = "todo-fastapi-postgres-react"

DEMO_SURFACE = IdeSurface(
    name="codium",
    needs=("frontend-ide", "python", "node", "postgresql-client", "browser-automation"),
    window_class="codium",
    ready_timeout=240.0,
)

CURSOR_OVERLAY_JS = """
(() => {
  const install = () => {
    if (document.getElementById('__pitch_cursor')) return;
    const dot = document.createElement('div');
    dot.id = '__pitch_cursor';
    dot.style.cssText =
      'position:fixed;left:-40px;top:-40px;width:20px;height:20px;' +
      'margin:-10px 0 0 -10px;border-radius:50%;' +
      'background:rgba(59,130,246,0.45);border:2px solid #ffffff;' +
      'box-shadow:0 0 0 2px rgba(15,23,42,0.65), 0 0 12px rgba(59,130,246,0.8);' +
      'pointer-events:none;z-index:2147483647;transition:transform 0.08s ease;';
    document.documentElement.appendChild(dot);
    window.addEventListener('mousemove', (e) => {
      dot.style.left = e.clientX + 'px';
      dot.style.top = e.clientY + 'px';
    }, true);
    window.addEventListener('mousedown', () => {
      dot.style.transform = 'scale(1.65)';
      dot.style.background = 'rgba(16,185,129,0.65)';
    }, true);
    window.addEventListener('mouseup', () => {
      dot.style.transform = 'scale(1)';
      dot.style.background = 'rgba(59,130,246,0.45)';
    }, true);
  };
  if (document.documentElement) install();
  window.addEventListener('DOMContentLoaded', install);
})();
"""


@dataclass(frozen=True)
class DemoStep:
    """One mouse, keyboard, bounded wait, or capsule browser launch step."""

    action: str
    x: int = 0
    y: int = 0
    text: str = ""
    ms: int = 0
    reason: str = ""

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> DemoStep:
        valid = ("click", "double_click", "right_click", "type", "press", "wait", "launch_browser")
        action = str(raw.get("action", ""))
        if action not in valid:
            raise ValueError(f"Unsupported DemoStep action: {action!r}")
        x = raw.get("x", 0)
        y = raw.get("y", 0)
        ms = raw.get("ms", 0)
        if type(x) is not int or not (0 <= x <= 1599):
            raise ValueError(f"Invalid DemoStep x coordinate: {x!r}")
        if type(y) is not int or not (0 <= y <= 999):
            raise ValueError(f"Invalid DemoStep y coordinate: {y!r}")
        if type(ms) is not int or ms < 0:
            raise ValueError(f"Invalid DemoStep ms: {ms!r}")
        text = str(raw.get("text", ""))
        if action in ("type", "press", "launch_browser") and not text:
            raise ValueError(f"DemoStep action {action!r} requires non-empty text")
        return cls(
            action=action,
            x=x,
            y=y,
            text=text,
            ms=ms,
            reason=str(raw.get("reason", "")),
        )


@contextmanager
def _postgres_container(run_id: str) -> Iterator[str]:
    """Run disposable PostgreSQL 17 container bound to ``127.0.0.1:PG_PORT``."""
    name = f"devcapsule-pitch-pg-{run_id}"
    command("docker", "rm", "-f", name, check=False)
    command(
        "docker", "run", "-d", "--rm",
        "--name", name,
        "-p", f"127.0.0.1:{PG_PORT}:5432",
        "-e", "POSTGRES_USER=devcapsule",
        "-e", "POSTGRES_PASSWORD=devcapsule",
        "-e", "POSTGRES_DB=tododb",
        "postgres:17-alpine",
        timeout=60.0,
    )
    try:
        deadline = time.monotonic() + 30.0
        while True:
            probe = command(
                "docker", "exec", name,
                "pg_isready", "-U", "devcapsule", "-d", "tododb",
                check=False, timeout=10.0,
            )
            if probe.returncode == 0:
                break
            if time.monotonic() > deadline:
                raise RuntimeError(f"PostgreSQL did not become ready: {probe.stdout} {probe.stderr}")
            time.sleep(0.4)
        yield name
    finally:
        command("docker", "rm", "-f", name, check=False, timeout=30.0)


def _bootstrap_capsule_deps(container: str, project_path: str, evidence: Path) -> None:
    """Install FastAPI/psycopg venv and Vite/React packages inside the capsule before recording."""
    script = f"""
set -euo pipefail
cd "{project_path}"
python3 -m venv backend/.venv
backend/.venv/bin/pip install -q fastapi uvicorn "psycopg[binary]"
npm --prefix frontend install --no-audit --no-fund --loglevel=error
"""
    res = subprocess.run(
        ["docker", "exec", "--user", f"{os.getuid()}:{os.getgid()}", container, "bash", "-lc", script],
        capture_output=True, text=True, check=False, timeout=300.0,
    )
    (evidence / "bootstrap-deps.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"Dependency bootstrap failed:\n{res.stdout}\n{res.stderr}")


def _launch_capsule_browser(container: str, url: str) -> None:
    """Launch headed Chromium on the child capsule's X11 display positioned alongside VSCodium."""
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
  --user-data-dir=/tmp/pitch-chrome-profile \\
  --window-position=470,46 \\
  --window-size=1105,910 \\
  --app="{url}" </dev/null >/tmp/pitch-chrome.log 2>&1 &
"""
    res = subprocess.run(
        ["docker", "exec", "-d", "--user", f"{os.getuid()}:{os.getgid()}", container, "bash", "-lc", script],
        capture_output=True, text=True, check=False, timeout=30.0,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Failed to launch browser in capsule: {res.stdout}\n{res.stderr}")


def apply_demo_step(page: Any, recorder: BurstFrameRecorder, container: str, step: DemoStep) -> None:
    """Execute one ``DemoStep`` while capturing smooth burst frames."""
    kind = step.action
    if kind in ("click", "double_click", "right_click"):
        page.mouse.move(step.x, step.y, steps=8)
        recorder.record_frames(page, count=2, interval_ms=55)
        if kind == "click":
            page.mouse.click(step.x, step.y)
            recorder.record_frames(page, count=5, interval_ms=110)
        elif kind == "double_click":
            page.mouse.dblclick(step.x, step.y)
            recorder.record_frames(page, count=6, interval_ms=110)
        else:
            page.mouse.click(step.x, step.y, button="right")
            recorder.record_frames(page, count=5, interval_ms=110)
    elif kind == "type":
        parts = step.text.split("\n")
        for idx, line in enumerate(parts):
            if line:
                chunk = max(4, len(line) // 5)
                for start in range(0, len(line), chunk):
                    page.keyboard.type(line[start : start + chunk], delay=18)
                    recorder.record_frames(page, count=1, interval_ms=35)
            if idx < len(parts) - 1:
                page.keyboard.press("Enter")
                recorder.record_frames(page, count=1, interval_ms=45)
        recorder.record_frames(page, count=4, interval_ms=100)
    elif kind == "press":
        page.keyboard.press(step.text)
        recorder.record_frames(page, count=5, interval_ms=110)
    elif kind == "wait":
        slices = max(1, step.ms // 150)
        recorded = min(slices, 24)
        recorder.record_frames(page, count=recorded, interval_ms=150)
        rem = step.ms - recorded * 150
        if rem > 0:
            page.wait_for_timeout(rem)
    elif kind == "launch_browser":
        url = step.text or f"http://127.0.0.1:{VITE_PORT}"
        _launch_capsule_browser(container, url)
        recorder.record_frames(page, count=16, interval_ms=160)


@contextmanager
def _demo_environment(executable: Path, evidence: Path) -> Iterator[tuple[SessionFacts, dict[str, int], str]]:
    """Bring up PostgreSQL 17 and a disposable DevCapsule with VSCodium, Python, Node, psql, and Playwright."""
    run_id = f"{int(time.time()) % 100000:05d}"
    slug = f"pitch-todo-{run_id}"
    container = f"devcapsule-{slug}"
    evidence.mkdir(parents=True, exist_ok=True)
    os.environ["DEVCAPSULE_SMOKE_COMPONENT_BROWSER"] = "1"

    with tempfile.TemporaryDirectory() as tmp_str:
        workspace = workspace_root(Path(tmp_str)) / slug
        shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True)
        try:
            with _postgres_container(run_id) as pg_name:
                initialize_project(executable, DEMO_SURFACE, workspace, evidence, slug)
                edit_info = write_seed_project(workspace)
                with launched_ide(executable, DEMO_SURFACE, workspace, evidence, container) as session:
                    assert desktop_page_answers(session.desktop_url) == 200
                    wait_for_ide_window(session)
                    _bootstrap_capsule_deps(
                        session.container,
                        session.project_path or str(session.workspace),
                        evidence,
                    )
                    yield session, edit_info, pg_name
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
            remove_project_records(slug)


def _verify_outside_postconditions(pg_container: str) -> dict[str, Any]:
    """Independently verify FastAPI HTTP responses and PostgreSQL 17 rows from outside."""
    with urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/api/todos", timeout=10) as resp:
        api_todos = json.loads(resp.read().decode("utf-8"))
    sql = command(
        "docker", "exec", pg_container,
        "psql", "-U", "devcapsule", "-d", "tododb", "-t", "-A", "-F", "|",
        "-c", "SELECT id, category, completed, title FROM todos ORDER BY id ASC;",
        timeout=15.0,
    ).stdout.strip().splitlines()
    return {"api_todos": api_todos, "psql_rows": sql}


def serve_mode(executable: Path, evidence: Path) -> int:
    """Start interactive discovery controller for the FastAPI + PostgreSQL + React Todo scenario."""
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found,unused-ignore]

    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "controller.json").unlink(missing_ok=True)
    recorder = BurstFrameRecorder(evidence / "video-frames")
    action_log: list[dict[str, Any]] = []
    step_counter = 0

    with _demo_environment(executable, evidence) as (session, edit_info, pg_name):
        with sync_playwright() as pw, smoke_browser(pw, session, evidence) as browser:
            viewport = {"width": 1600, "height": 1000}
            context = browser.new_context(
                viewport=viewport,
                record_video_dir=str(evidence),
                record_video_size=viewport,
            )
            context.add_init_script(CURSOR_OVERLAY_JS)
            page = context.new_page()
            video = page.video
            page.goto(session.desktop_url, wait_until="load")
            page.locator("canvas").first.wait_for(state="visible", timeout=60_000)
            page.wait_for_timeout(3500)
            recorder.record_frames(page, count=8, interval_ms=120)

            queue = ControllerQueue()
            server = start_controller_server(queue)
            info = {
                "port": server.server_address[1],
                "container": session.container,
                "pg_container": pg_name,
                "workspace": str(session.workspace),
                "project_path": session.project_path,
                "edit_lines": edit_info,
                "db_url": DB_URL,
                "api_port": API_PORT,
                "vite_port": VITE_PORT,
            }
            write_json_atomically(evidence / "controller.json", info)
            print(f"CONTROLLER_READY port={info['port']} container={session.container}", flush=True)

            stopped = False
            verification: dict[str, Any] = {}
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
                            for raw in payload.get("actions", []):
                                step = DemoStep.parse(raw)
                                apply_demo_step(page, recorder, session.container, step)
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
                        elif cmd == "exec":
                            proc = subprocess.run(
                                [
                                    "docker", "exec",
                                    "--user", f"{os.getuid()}:{os.getgid()}",
                                    session.container,
                                    "bash", "-lc", str(payload.get("shell", "true")),
                                ],
                                capture_output=True, text=True, check=False, timeout=60.0,
                            )
                            response.update(
                                ok=(proc.returncode == 0),
                                returncode=proc.returncode,
                                stdout=proc.stdout,
                                stderr=proc.stderr,
                            )
                        elif cmd == "verify":
                            verification = _verify_outside_postconditions(pg_name)
                            response.update(ok=True, **verification)
                        elif cmd == "stop":
                            try:
                                verification = _verify_outside_postconditions(pg_name)
                            except Exception as ver_exc:
                                verification = {"verify_error": str(ver_exc)}
                            step_counter += 1
                            final_shot = evidence / f"step-{step_counter:03d}.png"
                            page.screenshot(path=str(final_shot))
                            shutil.copyfile(final_shot, evidence / "poster.png")
                            recorder.record_frames(page, count=14, interval_ms=120)
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
                                verification=verification,
                            )
                            stopped = True
                        else:
                            response.update(ok=False, error=f"Unknown cmd: {cmd!r}")
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
                (evidence / "verification.json").write_text(
                    json.dumps(verification, indent=2) + "\n", encoding="utf-8"
                )
                context.close()
                if video is not None:
                    video.save_as(str(evidence / "agent-desktop-raw.webm"))
                    video.delete()
    return 0


def replay_mode(executable: Path, scenario_file: Path, evidence: Path) -> int:
    """Deterministically replay a saved scenario JSON with zero LLM calls and assert PostgreSQL state."""
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found,unused-ignore]

    spec = json.loads(scenario_file.read_text(encoding="utf-8"))
    steps = [DemoStep.parse(item) for item in spec["actions"]]
    # Before anything is recorded: a script that does not join the scenario fails here.
    presentation = plan_for_scenario(spec)
    recorder = BurstFrameRecorder(evidence / "video-frames")
    shots: list[str] = []
    frames_after_actions: list[int] = []

    with _demo_environment(executable, evidence) as (session, _, pg_name):
        with sync_playwright() as pw, smoke_browser(pw, session, evidence) as browser:
            viewport = {"width": 1600, "height": 1000}
            context = browser.new_context(
                viewport=viewport,
                record_video_dir=str(evidence),
                record_video_size=viewport,
            )
            context.add_init_script(CURSOR_OVERLAY_JS)
            page = context.new_page()
            video = page.video
            try:
                page.goto(session.desktop_url, wait_until="load")
                page.locator("canvas").first.wait_for(state="visible", timeout=60_000)
                page.wait_for_timeout(3500)
                recorder.record_frames(page, count=8, interval_ms=120)

                for idx, step in enumerate(steps, start=1):
                    apply_demo_step(page, recorder, session.container, step)
                    frames_after_actions.append(recorder.frame_count)
                    shot = evidence / f"step-{idx:03d}.png"
                    page.screenshot(path=str(shot))
                    shots.append(shot.name)

                if shots:
                    shutil.copyfile(evidence / shots[-1], evidence / "poster.png")
                recorder.record_frames(page, count=14, interval_ms=120)
                encoded = recorder.encode_webm(
                    page,
                    evidence / "scenario-video.webm",
                    container=session.container,
                )
                verification = _verify_outside_postconditions(pg_name)
            finally:
                context.close()
                if video is not None:
                    video.save_as(str(evidence / "agent-desktop-raw.webm"))
                    video.delete()

    presented = encoded and presentation is not None
    if encoded and presentation is not None:
        write_presentation(evidence, presentation.timed(
            frames_after_actions, recorder.frame_count, VIDEO_FRAMES_PER_SECOND,
            video="scenario-video.webm", poster="poster.png", screenshots=shots,
        ))
    todos = verification.get("api_todos", [])
    passed = encoded and len(todos) >= 4 and any(t.get("completed") for t in todos)
    result = {
        "scenario_id": spec.get("id"),
        "status": "passed" if passed else "failed",
        "steps_executed": len(steps),
        "frames_recorded": recorder.frame_count,
        "pause_free_webm": "scenario-video.webm" if encoded else None,
        "presentation": "presentation.json" if presented else None,
        "todos_verified": todos,
        "psql_rows": verification.get("psql_rows", []),
    }
    (evidence / "scenario-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tests.e2e.todo_demo_controller")
    sub = parser.add_subparsers(dest="cmd", required=True)

    default_evidence = EVIDENCE_DIR / DEMO_SCENARIO_ID
    default_scenario = SCENARIOS_DIR / f"{DEMO_SCENARIO_ID}.json"

    s_p = sub.add_parser("serve")
    s_p.add_argument("--pex", type=Path, required=True)
    s_p.add_argument("--evidence", type=Path, default=default_evidence)

    c_p = sub.add_parser("ctl")
    c_p.add_argument("--evidence", type=Path, default=default_evidence)
    c_p.add_argument("payload", nargs="?", default='{"cmd":"screenshot"}')

    r_p = sub.add_parser("replay")
    r_p.add_argument("--pex", type=Path, required=True)
    r_p.add_argument("--scenario", type=Path, default=default_scenario)
    r_p.add_argument("--evidence", type=Path, default=default_evidence)

    args = parser.parse_args(argv)
    if args.cmd == "serve":
        return serve_mode(args.pex, args.evidence)
    if args.cmd == "ctl":
        res = send_controller_command(args.evidence, json.loads(args.payload), timeout=300.0)
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    return replay_mode(args.pex, args.scenario, args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
