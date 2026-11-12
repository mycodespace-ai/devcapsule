"""Ctrl+C ends a real session with a result and the log paths, not a traceback.

Opt-in with the IDE smoke (``nox -s ide-smoke``; the ``ide_smoke`` marker):
a fresh project for the lightest surface is launched exactly as an adopter
holds ``project run``, in its own process group, and once the desktop
answers the group receives SIGINT the way a terminal delivers Ctrl+C. The
launcher must announce the interrupt, wait for the capsule, print one result
line and every session log file on this computer, and exit 130; the
container must be gone; and the IDE's own output must be in its file, not
in the launcher's terminal output. The two C10 records of 2026-10-22.
"""

from __future__ import annotations

import json
import os
import re
import signal
import time
import uuid
from pathlib import Path

import pytest

from tests.e2e.ide_session import (
    SURFACES,
    command,
    initialize_project,
    launched_ide,
    remove_project_records,
    wait_for_desktop_url,
    workspace_root,
)

pytestmark = pytest.mark.legacy

EVIDENCE_ROOT = Path(__file__).resolve().parents[2] / "dist" / "e2e-evidence" / "ide-smoke"
CODIUM = next(surface for surface in SURFACES if surface.name == "codium")
EXIT_TIMEOUT = 120.0
"""Seconds for the launcher to return after the interrupt: the supervisor's
grace is seconds; the launcher's own daemon fallback is a minute."""


@pytest.mark.e2e
@pytest.mark.ide_smoke
def test_interrupted_launch_ends_with_a_result_and_the_log_paths(built_pex: Path, tmp_path: Path) -> None:
    run_id = uuid.uuid4().hex[:8]
    slug = f"e2e-interrupt-{run_id}"
    container = f"devcapsule-e2e-interrupt-{run_id}"
    workspace = workspace_root(tmp_path) / slug
    workspace.mkdir(parents=True)
    (workspace / "smoke.txt").write_text("DevCapsule interrupt fixture.\n", encoding="utf-8")
    evidence = EVIDENCE_ROOT / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{run_id}" / "interrupt"
    evidence.mkdir(parents=True)
    try:
        initialize_project(built_pex, CODIUM, workspace, evidence, slug)
        with launched_ide(built_pex, CODIUM, workspace, evidence, container, own_session=True) as session:
            assert session.launcher is not None
            wait_for_desktop_url(session.launcher, session.launcher_log)
            # Ctrl+C: the terminal signals the foreground group, launcher and docker client alike.
            os.killpg(session.launcher.pid, signal.SIGINT)
            exit_code = session.launcher.wait(timeout=EXIT_TIMEOUT)
            output = session.launcher_log.read_text(encoding="utf-8", errors="replace")
            (evidence / "facts.json").write_text(json.dumps({"exit_code": exit_code}, indent=2) + "\n", encoding="utf-8")
            assert exit_code == 130, output
            assert "Traceback" not in output and "KeyboardInterrupt" not in output, output
            assert "Interrupted from the terminal (Ctrl+C); the capsule is stopping." in output, output
            assert "Session interrupted from the terminal (Ctrl+C); the capsule stopped." in output, output
            listed = re.findall(r"^  (/\S+)$", output.split("Session logs on this computer:", 1)[1], re.MULTILINE)
            assert listed, output
            assert all(Path(path).is_file() for path in listed), listed
            names = {Path(path).name for path in listed}
            assert {"devcapsule-launcher.log", "devcapsule-supervisor.log", "session.json"} <= names, names
            # The IDE's own output went to its file and not to the terminal.
            ide_log = next(Path(path) for path in listed if Path(path).name == "devcapsule-codium.log")
            ide_lines = [line for line in ide_log.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
            assert ide_lines, ide_log
            assert ide_lines[0].split("Z ", 1)[-1] not in output, ide_lines[0]
            manifest = json.loads((ide_log.parent / "session.json").read_text(encoding="utf-8"))
            assert manifest["exit-code"] == 130 and manifest["ended-at"]
            assert command("docker", "inspect", container, check=False).returncode != 0, "the capsule is still running"
    finally:
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)
        remove_project_records(slug)
