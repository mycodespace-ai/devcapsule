"""End-to-end live diagnosis, Xvnc hang fault injection, and sanitized post-mortem export.

Launches a real contained-display session with the PEX under test, verifies
live ``project diagnose`` probes, injects a bounded ``SIGSTOP`` hang on
``Xvnc`` to prove that HTTP ``200`` on ``/vnc.html`` and accepted Unix/TCP
connections are not mistaken for health, resumes ``Xvnc``, interrupts the
session cleanly (Ctrl+C), and verifies post-mortem ``--export`` permissions,
``--rm`` degradation, ``browser_evidence`` honesty, and token/secret redaction.
"""

from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import tarfile
import time
from urllib.parse import parse_qs, urlsplit
import uuid

import pytest

from tests.e2e.ide_session import (
    SURFACES,
    command,
    initialize_project,
    launched_ide,
    remove_project_records,
    wait_for_console_url,
    workspace_root,
)

pytestmark = pytest.mark.legacy

EVIDENCE_ROOT = Path(__file__).resolve().parents[2] / "dist" / "e2e-evidence" / "diagnostics"
CODIUM = next(surface for surface in SURFACES if surface.name == "codium")
EXIT_TIMEOUT = 120.0


def _extract_token(url: str) -> str:
    query = parse_qs(urlsplit(url).query)
    tokens = query.get("token", [])
    if not tokens:
        for nested in query.get("path", []):
            tokens = parse_qs(urlsplit(nested).query).get("token", [])
            if tokens:
                break
    assert tokens and len(tokens[0]) >= 16, f"expected run token in URL: {url}"
    return tokens[0]


@pytest.mark.e2e
@pytest.mark.ide_smoke
def test_session_diagnostics_live_fault_injection_and_postmortem_export(
    built_pex: Path,
    tmp_path: Path,
) -> None:
    run_id = uuid.uuid4().hex[:8]
    slug = f"e2e-diagnose-{run_id}"
    container = f"devcapsule-e2e-diagnose-{run_id}"
    custom_secret = f"custom_e2e_secret_{run_id}_do_not_leak"
    workspace = workspace_root(tmp_path) / slug
    workspace.mkdir(parents=True)
    (workspace / "smoke.txt").write_text("DevCapsule diagnostics fixture.\n", encoding="utf-8")
    evidence = EVIDENCE_ROOT / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{run_id}"
    evidence.mkdir(parents=True, exist_ok=True)

    try:
        initialize_project(built_pex, CODIUM, workspace, evidence, slug)
        command(
            str(built_pex),
            "project",
            "--path",
            str(workspace),
            "config",
            "env",
            "set",
            "CUSTOM_E2E_SECRET",
            custom_secret,
        )

        with launched_ide(built_pex, CODIUM, workspace, evidence, container, own_session=True) as session:
            assert session.launcher is not None
            display_token = _extract_token(session.desktop_url)
            console_url = wait_for_console_url(session.launcher, session.launcher_log)
            console_token = _extract_token(console_url)
            forbidden_secrets = (display_token, console_token, custom_secret)

            # 1. Healthy live session snapshot.
            live_run = command(
                str(built_pex),
                "project",
                "--path",
                str(workspace),
                "diagnose",
                "--json",
                timeout=30.0,
            )
            for secret in forbidden_secrets:
                assert secret not in live_run.stdout
            live_snap = json.loads(live_run.stdout)
            (evidence / "live-healthy.json").write_text(live_run.stdout, encoding="utf-8")

            assert live_snap["schema-version"] == 1
            assert live_snap["summary"]["state"] == "healthy"
            assert live_snap["docker_inspect"]["running"] is True
            assert "CUSTOM_E2E_SECRET" in live_snap["docker_inspect"]["environment_variable_names"]
            assert live_snap["runtime_probe"]["available"] is True
            probes = live_snap["runtime_probe"]["probes"]
            assert probes["rfb_unix"]["healthy"] is True
            assert probes["display_http"]["healthy"] is True
            assert probes["display_websocket_rfb"]["healthy"] is True
            assert probes["console_http"]["healthy"] is True
            assert live_snap["host_probes"]["probes"]["display_host_http"]["healthy"] is True
            assert live_snap["host_probes"]["probes"]["console_host_http"]["healthy"] is True
            assert live_snap["browser_evidence"]["collected"] is False

            # 2. Fault injection: freeze Xvnc (SIGSTOP). websockify still answers HTTP 200 on
            # /vnc.html and accepts WebSocket upgrades, while RFB greeting probes time out boundedly.
            xvnc_proc = live_snap["runtime_probe"]["processes"]["components"]["xvnc"]
            xvnc_pid = int(xvnc_proc["pid"])
            xvnc_user = str(xvnc_proc["uid"])
            command("docker", "exec", "--user", xvnc_user, container, "kill", "-STOP", str(xvnc_pid))
            try:
                started = time.monotonic()
                hung_run = command(
                    str(built_pex),
                    "project",
                    "--path",
                    str(workspace),
                    "diagnose",
                    "--json",
                    timeout=30.0,
                )
                elapsed = time.monotonic() - started
                assert elapsed < 15.0, f"bounded diagnosis took too long ({elapsed:.2f}s) against stopped Xvnc"
                for secret in forbidden_secrets:
                    assert secret not in hung_run.stdout
                hung_snap = json.loads(hung_run.stdout)
                (evidence / "live-xvnc-stopped.json").write_text(hung_run.stdout, encoding="utf-8")

                assert hung_snap["summary"]["state"] == "degraded"
                assert hung_snap["runtime_probe"]["processes"]["components"]["xvnc"]["state"] == "T"
                assert any(
                    entry["role"] == "xvnc"
                    for entry in hung_snap["runtime_probe"]["processes"]["stopped"]
                )
                hung_probes = hung_snap["runtime_probe"]["probes"]
                assert hung_probes["display_http"]["healthy"] is True
                assert hung_probes["rfb_unix"]["accepted"] is True
                assert hung_probes["rfb_unix"]["healthy"] is False
                assert hung_probes["rfb_unix"]["timed_out"] is True
                assert hung_probes["display_websocket_rfb"]["upgraded"] is True
                assert hung_probes["display_websocket_rfb"]["healthy"] is False
                assert hung_probes["display_websocket_rfb"]["timed_out"] is True
            finally:
                command(
                    "docker",
                    "exec",
                    "--user",
                    xvnc_user,
                    container,
                    "kill",
                    "-CONT",
                    str(xvnc_pid),
                    check=False,
                )

            recovered_run = command(
                str(built_pex),
                "project",
                "--path",
                str(workspace),
                "diagnose",
                "--json",
                timeout=30.0,
            )
            assert json.loads(recovered_run.stdout)["summary"]["state"] == "healthy"

            # 3. Clean Ctrl+C shutdown; container is removed by --rm.
            os.killpg(session.launcher.pid, signal.SIGINT)
            exit_code = session.launcher.wait(timeout=EXIT_TIMEOUT)
            assert exit_code == 130
            assert command("docker", "inspect", container, check=False).returncode != 0

        # 4. Post-mortem sanitized export after container removal.
        bundle_path = tmp_path / "postmortem-bundle.tar.gz"
        export_run = command(
            str(built_pex),
            "project",
            "--path",
            str(workspace),
            "diagnose",
            "--json",
            "--export",
            str(bundle_path),
            timeout=30.0,
        )
        for secret in forbidden_secrets:
            assert secret not in export_run.stdout
        export_snap = json.loads(export_run.stdout)
        (evidence / "postmortem-export.json").write_text(export_run.stdout, encoding="utf-8")

        assert export_snap["docker_inspect"]["container_removed"] is True
        assert export_snap["summary"]["state"] == "post-mortem"
        assert export_snap["ide_native_logs"]["included_in_export"] is False
        assert export_snap["browser_evidence"]["collected"] is False
        assert stat.S_IMODE(bundle_path.stat().st_mode) == 0o600

        with tarfile.open(bundle_path, "r:gz") as archive:
            names = archive.getnames()
            assert any(name.endswith("/snapshot.json") for name in names)
            assert any(name.endswith("/session.json") for name in names)
            assert any(name.endswith("/logs/devcapsule-launcher.log") for name in names)
            assert any(name.endswith("/logs/devcapsule-supervisor.log") for name in names)
            assert any(name.endswith("/logs/devcapsule-novnc.log") for name in names)
            assert not any("/ide-logs/" in name for name in names)

            for member in archive.getmembers():
                extracted = archive.extractfile(member)
                assert extracted is not None
                raw = extracted.read()
                text = (
                    gzip.decompress(raw).decode("utf-8", errors="replace")
                    if member.name.endswith(".gz")
                    else raw.decode("utf-8", errors="replace")
                )
                for secret in forbidden_secrets:
                    assert secret not in text, f"live secret leaked in exported {member.name}"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        remove_project_records(slug)
        for docker_arg_dir in Path.home().glob(f".config/devcapsule/docker-arguments/*/{slug}"):
            shutil.rmtree(docker_arg_dir, ignore_errors=True)
