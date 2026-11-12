"""The recursive successor is launched attached, from a fresh workspace, and leaves nothing behind.

Runs only inside a DevCapsule capsule with host-Docker access (the
``recursive_e2e`` marker). The test first makes itself a fresh workspace
(``fresh_workspace.py``): it refuses a dirty source, clones this
repository's HEAD into an owned run directory under the persistent home,
answers the clone's configuration as this capsule's own checkout was
answered, and resolves it under configuration roots isolated beneath the
run directory. The capsule's own checkout records are never read or
written; the 2026-10-04 record explains why that matters.

It then drives ``launch-successor`` on the clone exactly as a developer
holds ``project run``: it starts the command as a subprocess, waits until
the run manifest says the successor is running, inspects it independently,
stops the container, waits for the command to return, and proves that
Docker removed the container and the run directory kept the evidence. At
the end it removes the workspace, best effort.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest

from devcapsule.configuration.storage import config_root
from devcapsule.recursive_successor import (
    CONTAINER_ID_FILE,
    SUCCESSOR_LOG,
    successor_container_name,
)
from devcapsule.recursive_dogfood import RUNTIME_PLAN_PATH

from tests.e2e.fresh_workspace import FreshWorkspace

pytestmark = pytest.mark.legacy

REPO_ROOT = Path(__file__).resolve().parents[3]
# Realizing the environment may build the formation on first use.
RUNNING_TIMEOUT = 900.0
EXIT_TIMEOUT = 180.0


def _tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _first_json_object(text: str) -> dict[str, object]:
    """The first JSON object printed on a line of its own: the running report.

    Environment realization may print progress before it, so the text is
    scanned from each line that opens an object until one decodes.
    """
    decoder = json.JSONDecoder()
    position = 0
    while (start := text.find("\n{", position)) != -1 or text.startswith("{"):
        start = 0 if text.startswith("{") and position == 0 else start + 1
        try:
            value, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            position = start + 1
            continue
        if isinstance(value, dict):
            return value
        position = start + 1
    raise AssertionError(f"no JSON report in the launcher output:\n{text[-2000:]}")


def _tail(path: Path, lines: int = 40) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


@pytest.mark.e2e
@pytest.mark.recursive_e2e
def test_attached_successor_launch_from_a_fresh_workspace_leaves_nothing_behind(tmp_path: Path) -> None:
    assert RUNTIME_PLAN_PATH.is_file(), "the recursive E2E runs inside a DevCapsule capsule"
    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI is required for the recursive E2E"
    # The capsule's own records, stale or not, are neither read nor written.
    own_records = config_root() / "projects"
    own_before = _tree(own_records) if own_records.is_dir() else {}

    # 0. A fresh workspace: a clean clone of HEAD, configured and resolved
    #    under its own roots. A dirty source fails here, before any launch.
    workspace = FreshWorkspace.create(REPO_ROOT)
    run_id, run_root = workspace.run_id, workspace.run_root
    name = successor_container_name(run_id)
    launcher_log = tmp_path / "launch-successor.log"
    launcher: subprocess.Popen[bytes] | None = None
    try:
        answers = workspace.configure_like_this_capsule()
        assert answers["docker-daemon"] == "host-socket" and answers["network"] == "host", answers
        assert (run_root / "xdg" / "config" / "devcapsule" / "projects").is_dir(), "the clone's record is under the run root"
        _manifest = workspace.manifest  # the launch reads and updates this run's manifest
        assert _manifest()["state"] == "stage-5-resolved"

        with launcher_log.open("wb") as log:
            launcher = subprocess.Popen(
                workspace.cli("recursive-e2e", "launch-successor", "--run-id", run_id, "--json"),
                env=workspace.environment(), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            )

        # 1. The command stays attached while the successor runs, and the
        #    manifest says so before the command prints anything else.
        deadline = time.monotonic() + RUNNING_TIMEOUT
        while _manifest().get("state") != "stage-6-running":
            if launcher.poll() is not None:
                pytest.fail(
                    f"launch-successor exited {launcher.returncode} before the successor ran:\n"
                    f"{_tail(launcher_log)}\n--- successor log ---\n{_tail(run_root / SUCCESSOR_LOG)}"
                )
            assert time.monotonic() < deadline, f"successor not running after {RUNNING_TIMEOUT:g}s:\n{_tail(launcher_log)}"
            time.sleep(1.0)
        assert launcher.poll() is None, "the launcher returned although the successor is running"
        launch = _manifest()["launch"]
        assert isinstance(launch, dict) and launch["lifecycle"] == "attached"
        container_id = str(launch["container_id"])
        assert (run_root / CONTAINER_ID_FILE).read_text(encoding="utf-8").strip() == container_id
        running = subprocess.run([docker, "inspect", "--format", "{{.State.Running}}", container_id],
                                 text=True, capture_output=True, check=False)
        assert running.stdout.strip() == "true", running.stderr

        # 2. The running report was printed, and the independent inspection
        #    passes against the same container.
        report = _first_json_object(launcher_log.read_text(encoding="utf-8", errors="replace"))
        assert report["state"] == "running" and report["container_id"] == container_id
        inspected = subprocess.run(workspace.cli("recursive-e2e", "inspect-successor", "--run-id", run_id, "--json"),
                                   env=workspace.environment(), text=True, capture_output=True, check=False)
        assert inspected.returncode == 0, inspected.stdout + inspected.stderr
        assert json.loads(inspected.stdout)["state"] == "inspection-passed"

        # 3. Stopping the container ends the attached command, Docker removes
        #    the container, and the run directory keeps the evidence.
        subprocess.run([docker, "stop", "--time", "30", name], text=True, capture_output=True, check=False)
        launcher.wait(timeout=EXIT_TIMEOUT)
        final = _manifest()
        assert final.get("state") == "stage-6-exited", final
        finished = final["launch"]
        assert isinstance(finished, dict) and isinstance(finished.get("exit_code"), int) and finished.get("container_removed") is True
        assert subprocess.run([docker, "inspect", container_id], capture_output=True, check=False).returncode != 0, "Docker kept the successor"
        assert (run_root / SUCCESSOR_LOG).is_file()
        # An exited successor is reported as such, not inspected as alive.
        again = subprocess.run(workspace.cli("recursive-e2e", "inspect-successor", "--run-id", run_id, "--json"),
                               env=workspace.environment(), text=True, capture_output=True, check=False)
        assert again.returncode != 0 and "has exited" in (again.stdout + again.stderr)
        # 4. Nothing of the capsule's own configuration was touched, and the
        #    successor's state lived under the run root.
        assert (_tree(own_records) if own_records.is_dir() else {}) == own_before
        assert not os.environ.get("XDG_CONFIG_HOME", "").startswith(str(run_root))
    finally:
        if launcher is not None and launcher.poll() is None:
            subprocess.run([docker, "stop", "--time", "10", name], capture_output=True, check=False)
            try:
                launcher.wait(timeout=60.0)
            except subprocess.TimeoutExpired:
                launcher.kill()
        subprocess.run([docker, "rm", "--force", name], capture_output=True, check=False)
        if not workspace.cleanup():
            print(f"fresh workspace not fully removed, best effort: {run_root}")
