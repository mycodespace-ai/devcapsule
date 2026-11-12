"""The web console answers in a fresh capsule, with and without a display.

Deliverable 1 of the capsule web console work order, as the smoke the
acceptance evidence asks for: ``project run`` prints a console URL, the
console answers on it, a tokenless request is refused, and a path outside
the mount is refused. Deliverable 3 adds the monitor: the processes and
the cgroup reading answer from inside the capsule. The headless case runs
the same materialized image through the runtime's job mode, which starts
no display at all.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import quote, urlsplit
import uuid

import pytest

from devcapsule.host_daemon import current_container, requires_translation, translate_bind_sources
from tests.e2e.ide_session import SURFACES, command, ide_session, wait_for_console_url, workspace_root

pytestmark = pytest.mark.legacy

EVIDENCE_ROOT = Path(__file__).resolve().parents[2] / "dist" / "e2e-evidence" / "console-smoke"
SURFACE = next(surface for surface in SURFACES if surface.name == "codium")


def fetch(url: str, *, headers: dict[str, str] | None = None, patience: float = 30.0) -> tuple[int, str]:
    """Status and body of ``url``; retries a refused connection within ``patience``."""
    parts = urlsplit(url)
    deadline = time.monotonic() + patience
    while True:
        connection = http.client.HTTPConnection(parts.hostname or "127.0.0.1", parts.port or 80, timeout=10)
        try:
            target = parts.path + (f"?{parts.query}" if parts.query else "")
            connection.request("GET", target, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.read().decode("utf-8", errors="replace")
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)
        finally:
            connection.close()


def check_console(url: str, evidence: Path, label: str) -> dict[str, object]:
    """The four facts of deliverable 1 against a live console at ``url``."""
    token = urlsplit(url).query.removeprefix("token=")
    base = url.split("/?", 1)[0]
    headers = {"X-DevCapsule-Token": token}
    home_status, home = fetch(url)
    configuration_status, configuration = fetch(f"{base}/api/configuration", headers=headers)
    page_status, _ = fetch(f"{base}/configuration", headers=headers)
    refused_status, refused = fetch(f"{base}/api/configuration")
    traversal_status, _ = fetch(f"{base}/api/project/file?path={quote('../../etc/passwd', safe='')}", headers=headers)
    absolute_status, _ = fetch(f"{base}/api/project/file?path={quote('/etc/passwd', safe='')}", headers=headers)
    # The smoke workspace's one file; see ide_session.
    inside_status, inside = fetch(f"{base}/api/project/file?path=smoke.txt", headers=headers)
    processes_status, processes = fetch(f"{base}/api/processes", headers=headers)
    resources_status, resources = fetch(f"{base}/api/resources", headers=headers)
    # Deliverable 4: the records page for any path, and a raw file with its isolation headers.
    records_status, records_page = fetch(f"{base}/records/smoke.txt", headers=headers)
    raw_status, raw = fetch(f"{base}/api/project/raw?path=smoke.txt", headers=headers)
    vendor_status, _ = fetch(f"{base}/static/vendor/viz-3.31.0.global.js", headers=headers)
    # Deliverable 5: the decisions list answers, empty or not.
    decisions_status, decisions_listing = fetch(f"{base}/api/decisions", headers=headers)
    facts = {
        "label": label, "home_status": home_status, "configuration_page_status": page_status,
        "configuration_api_status": configuration_status, "tokenless_status": refused_status,
        "traversal_status": traversal_status, "absolute_status": absolute_status, "inside_status": inside_status,
        "processes_status": processes_status, "resources_status": resources_status,
        "records_page_status": records_status, "raw_status": raw_status, "vendor_status": vendor_status,
        "decisions_status": decisions_status,
    }
    (evidence / f"{label}-facts.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    (evidence / f"{label}-configuration.json").write_text(configuration, encoding="utf-8")
    assert home_status == 200 and "DevCapsule console" in home, home[:400]
    assert page_status == 200
    assert configuration_status == 200, configuration[:400]
    assert json.loads(configuration)["schema-version"] == 1
    assert refused_status == 403 and "run token" in refused
    assert traversal_status == 403 and absolute_status == 403
    assert inside_status == 200 and inside == "DevCapsule graphical smoke fixture.\n"
    # Deliverable 3: the capsule's own processes and its cgroup, from inside.
    assert processes_status == 200, processes[:400]
    listing = json.loads(processes)
    assert listing["count"] >= 1 and any("devcapsule_webconsole" in row["command"] for row in listing["processes"])
    assert resources_status == 200, resources[:400]
    reading = json.loads(resources)
    facts["resources_available"] = reading["available"]
    assert reading["available"] is True and reading["memory"]["current-bytes"] > 0
    (evidence / f"{label}-resources.json").write_text(resources, encoding="utf-8")
    assert records_status == 200 and 'data-page="records"' in records_page
    assert raw_status == 200 and raw == "DevCapsule graphical smoke fixture.\n"
    assert vendor_status == 200
    assert decisions_status == 200 and json.loads(decisions_listing) == {"decisions": []}
    return facts


def check_decision_round_trip(url: str, container: str, evidence: Path) -> None:
    """Deliverable 5 inside a real capsule: an agent's decision file, the human's answer.

    The decision is written where the console's default directory is, through
    the capsule itself; the answer is posted as the page would post it; the
    file the agent would read is read back through the capsule.
    """
    token = urlsplit(url).query.removeprefix("token=")
    base = url.split("/?", 1)[0]
    decision = {"format": 1, "id": "smoke-decision", "title": "Smoke decision", "asked-by": "smoke",
                "asked-at": "2026-10-09T00:00:00+00:00", "context": "One question.",
                "items": [{"key": "go", "title": "Go?", "records": ["smoke.txt"],
                           "options": [{"key": "yes", "label": "Yes"}, {"key": "no", "label": "No"}]}]}
    directory = "/home/devcapsule/.local/state/devcapsule/decisions"
    written_in = subprocess.run(
        ["docker", "exec", "-i", container, "sh", "-c", f"mkdir -p {directory} && cat > {directory}/smoke-decision.json"],
        input=json.dumps(decision), text=True, capture_output=True, timeout=60.0, check=False,
    )
    assert written_in.returncode == 0, written_in.stderr
    listing_status, listing = fetch(f"{base}/api/decisions", headers={"X-DevCapsule-Token": token})
    assert listing_status == 200 and [entry["id"] for entry in json.loads(listing)["decisions"]] == ["smoke-decision"], listing
    parts = urlsplit(base)
    connection = http.client.HTTPConnection(parts.hostname or "127.0.0.1", parts.port or 80, timeout=10)
    try:
        connection.request("POST", "/api/decisions/smoke-decision/answer",
                           body=json.dumps({"answers": {"go": {"chosen": ["yes"], "note": "from the smoke"}}, "note": "ok"}),
                           headers={"X-DevCapsule-Token": token, "Content-Type": "application/json", "Origin": base})
        response = connection.getresponse()
        answered = response.read().decode("utf-8")
        assert response.status == 200, answered
    finally:
        connection.close()
    written = command("docker", "exec", container, "cat", f"{directory}/smoke-decision.answer.json").stdout
    (evidence / "decision-answer.json").write_text(written, encoding="utf-8")
    assert json.loads(written)["answers"] == {"go": {"chosen": ["yes"], "note": "from the smoke"}}
    refused_status, _ = fetch(f"{base}/api/decisions")
    assert refused_status == 403


@pytest.mark.e2e
@pytest.mark.ide_smoke
def test_console_answers_with_and_without_a_display(built_pex: Path, tmp_path: Path) -> None:
    evidence = EVIDENCE_ROOT / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:6]}"
    evidence.mkdir(parents=True)
    staging = workspace_root(tmp_path) / f"console-headless-{uuid.uuid4().hex[:8]}"
    staging.mkdir(parents=True)
    with ide_session(built_pex, SURFACE, tmp_path, evidence / "with-display") as session:
        # With a display: project run printed the console URL beside the desktop's.
        assert session.launcher is not None
        console = wait_for_console_url(session.launcher, session.launcher_log)
        (evidence / "with-display" / "console-url.txt").write_text(console + "\n", encoding="utf-8")
        check_console(console, evidence / "with-display", "with-display")
        check_decision_round_trip(console, session.container, evidence / "with-display")
        runtime = json.loads(command("docker", "exec", session.container, "cat", "/etc/devcapsule/runtime-plan.json").stdout)
        assert runtime["console"]["token_path"] == "/run/devcapsule-console-token"
        # Slice 8: the console's host-side origin is in the capsule's environment, without the token.
        inside_origin = command("docker", "exec", session.container, "printenv", "DEVCAPSULE_CONSOLE_URL").stdout.strip()
        assert inside_origin == console.split("/?", 1)[0], inside_origin
        assert "token" not in inside_origin
        image = command("docker", "inspect", "--format", "{{.Config.Image}}", session.container).stdout.strip()
        plan = dict(runtime)
        # The headless project: the session's project declaration and its one
        # file, copied before the session removes its workspace.
        shutil.copytree(session.workspace / ".devcapsule", staging / "project" / ".devcapsule")
        shutil.copy2(session.workspace / "smoke.txt", staging / "project" / "smoke.txt")

    # Without a display: the same image, the runtime's job mode, no display
    # section at all; the console still runs and still needs the token. The
    # staging files live where the daemon can see them, translated as the
    # launcher translates its own binds.
    headless_dir = evidence / "headless"
    headless_dir.mkdir()
    token = uuid.uuid4().hex
    token_file = staging / "console-token"
    token_file.write_text(token + "\n", encoding="utf-8")
    token_file.chmod(0o644)
    plan.pop("display", None)
    plan["console"] = {"listen_address": "0.0.0.0", "port": 6081, "token_path": "/run/devcapsule-console-token"}
    plan_file = staging / "runtime-plan.json"
    plan_file.write_text(json.dumps(plan) + "\n", encoding="utf-8")
    container = f"devcapsule-console-smoke-{uuid.uuid4().hex[:8]}"
    port = _free_port()
    docker_args = [
        "docker", "run", "--rm", "--name", container, "--entrypoint", "/opt/devcapsule/bin/devcapsule.pex",
        "--publish", f"127.0.0.1:{port}:6081",
        "--mount", f"type=bind,src={token_file},dst=/run/devcapsule-console-token,ro",
        "--mount", f"type=bind,src={plan_file},dst=/etc/devcapsule/runtime-plan.json,ro",
        "--mount", f"type=bind,src={staging / 'project'},dst={plan['project_path']},ro",
        image, "runtime", "/etc/devcapsule/runtime-plan.json", "--", "sleep", "300",
    ]
    if requires_translation(os.environ):
        docker_args = translate_bind_sources(docker_args, current_container(os.environ))
    (headless_dir / "docker-run-args.json").write_text(json.dumps(docker_args, indent=2) + "\n", encoding="utf-8")
    started = subprocess.Popen(docker_args, stdout=(headless_dir / "docker-run.log").open("wb"), stderr=subprocess.STDOUT)
    try:
        facts = check_console(f"http://127.0.0.1:{port}/?token={token}", headless_dir, "headless")
        assert facts["home_status"] == 200
    finally:
        command("docker", "stop", "--time", "10", container, check=False, timeout=60.0)
        started.wait(timeout=60.0)
        shutil.rmtree(staging, ignore_errors=True)


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])
