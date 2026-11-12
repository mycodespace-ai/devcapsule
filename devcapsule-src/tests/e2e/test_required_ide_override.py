"""Smoke: a project that requires PyCharm launches Codium once with ``--force``, then PyCharm again.

Opt-in (``nox -s ide-smoke -- --required-ide``): the acceptance session of the
work order of 2026-10-28, *Explicit IDE requirement override*, run with the
executable under test against an isolated project. It proves from the outside
that the forced launch runs Codium, that the project's files and the checkout's
saved IDE are unchanged by it, that the launch's plan recorded the departure,
and that the next ordinary launch runs PyCharm again. Needs Docker and the base
image the executable recommends; a first run on a machine acquires both IDEs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import tomllib
import uuid
from pathlib import Path

import pytest

from tests.e2e.ide_session import (
    CREATOR, SURFACES, capture_desktop, command, desktop_page_answers, launched_ide, remove_project_records,
    wait_for_ide_window, workspace_root,
)

pytestmark = pytest.mark.legacy

EVIDENCE_ROOT = Path(__file__).resolve().parents[2] / "dist" / "e2e-evidence" / "ide-smoke"
REQUIRED = next(surface for surface in SURFACES if surface.name == "pycharm")
ALTERNATE = next(surface for surface in SURFACES if surface.name == "codium")


@pytest.fixture(scope="session")
def evidence_run() -> Path:
    run = EVIDENCE_ROOT / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:6]}-required-ide"
    run.mkdir(parents=True)
    return run


def _checkout_files(slug: str) -> dict[str, Path]:
    """The checkout record and its derived resolution for the smoke project's slug."""
    records = sorted(Path.home().glob(f".config/devcapsule/projects/*/{slug}/devcapsule.checkout.toml"))
    assert len(records) == 1, records
    return {"record": records[0], "resolution": records[0].with_name("devcapsule.resolved.toml")}


def _session_facts(session, evidence: Path, name: str) -> dict[str, object]:
    assert desktop_page_answers(session.desktop_url) == 200, session.desktop_url
    window = wait_for_ide_window(session)
    pixels = capture_desktop(session, evidence)
    if os.environ.get("DEVCAPSULE_SMOKE_DISPLAY") == "1":
        assert pixels is not None, "Required Playwright browser evidence is unavailable"
    runtime = json.loads(command("docker", "exec", session.container, "cat", "/etc/devcapsule/runtime-plan.json").stdout)
    return {"launch": name, "surface": session.surface.name, "container": session.container,
            "runtime_component": runtime["component"]["id"], "ide_window": window,
            "pixels": pixels if pixels is not None else "not captured: Playwright and its browser are optional"}


@pytest.mark.e2e
@pytest.mark.ide_smoke
def test_forced_codium_then_plain_pycharm(built_pex: Path, tmp_path: Path, evidence_run: Path) -> None:
    evidence = evidence_run / "required-ide-override"
    evidence.mkdir(parents=True)
    (evidence_run / "run.json").write_text(json.dumps({
        "executable": str(built_pex),
        "sha256": hashlib.sha256(built_pex.read_bytes()).hexdigest(),
        "version": command(str(built_pex), "version", "--json").stdout,
    }, indent=2) + "\n", encoding="utf-8")
    run_id = uuid.uuid4().hex[:8]
    slug = f"e2e-ide-required-{run_id}"
    container = f"devcapsule-e2e-ide-required-{run_id}"
    workspace = workspace_root(tmp_path) / slug
    workspace.mkdir(parents=True)
    (workspace / "smoke.txt").write_text("DevCapsule required-IDE override smoke fixture.\n", encoding="utf-8")
    environment = dict(os.environ, BROWSER="true")

    def launcher(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(built_pex), "project", *arguments], cwd=workspace, env=environment, text=True,
                              capture_output=True, stdin=subprocess.DEVNULL, check=False, timeout=600.0)

    try:
        # The order's fixture: PyCharm required beside Python, PyCharm saved for the checkout.
        init = launcher("init", "--require", "python", "--require", "python-ide", "--ide", "python-ide",
                        "--creator", CREATOR, "--slug", slug,
                        "--authorize", "base-image", "default",
                        "--authorize", "network", "host", "Local graphical smoke requires host networking.")
        (evidence / "init.log").write_text(init.stdout + init.stderr, encoding="utf-8")
        assert init.returncode == 0, init.stderr
        files = _checkout_files(slug)
        shared = {path.name: path.read_bytes() for path in sorted((workspace / ".devcapsule").iterdir())}
        record = files["record"].read_bytes()
        assert tomllib.loads(record.decode())["capabilities"]["selected"] == ["python-ide"]

        # 1. Without --force the conflicting IDE is refused before anything is materialized.
        refused = launcher("run", "--ide", "codium", "--print-command")
        (evidence / "refused.log").write_text(refused.stdout + refused.stderr, encoding="utf-8")
        assert refused.returncode == 2 and "--ide codium --force" in refused.stderr, refused.stderr

        # 2. With --force, Codium runs; the launcher warns.
        with launched_ide(built_pex, ALTERNATE, workspace, evidence / "forced", container + "-forced",
                          run_arguments=("--ide", "codium", "--force")) as forced:
            forced_facts = _session_facts(forced, evidence / "forced", "forced")
            warning = (evidence / "forced" / "launcher.log").read_text(encoding="utf-8", errors="replace")
            assert "WARNING: --force sets aside the project's required IDE python-ide" in warning
        assert forced_facts["runtime_component"] == "codium"
        assert "codium" in str(forced_facts["ide_window"]).lower()
        # 3. The project's files and the saved IDE are unchanged; the plan recorded the departure.
        assert {path.name: path.read_bytes() for path in sorted((workspace / ".devcapsule").iterdir())} == shared
        assert files["record"].read_bytes() == record
        forced_plan = tomllib.loads(files["resolution"].read_text(encoding="utf-8"))
        assert forced_plan["runtime"]["component"] == "codium"
        assert forced_plan["departures"] == {"ide-requirement": {"required": "python-ide", "launched": "frontend-ide"}}
        shutil.copy(files["resolution"], evidence / "forced" / "devcapsule.resolved.toml")

        # 4. The next ordinary launch runs PyCharm, from the unchanged documents.
        with launched_ide(built_pex, REQUIRED, workspace, evidence / "plain", container + "-plain") as plain:
            plain_facts = _session_facts(plain, evidence / "plain", "plain")
            assert "WARNING: --force" not in (evidence / "plain" / "launcher.log").read_text(encoding="utf-8", errors="replace")
        assert plain_facts["runtime_component"] == "pycharm"
        assert "pycharm" in str(plain_facts["ide_window"]).lower()
        plain_plan = tomllib.loads(files["resolution"].read_text(encoding="utf-8"))
        assert plain_plan["runtime"]["component"] == "pycharm" and "departures" not in plain_plan
        assert files["record"].read_bytes() == record
        assert {path.name: path.read_bytes() for path in sorted((workspace / ".devcapsule").iterdir())} == shared
        shutil.copy(files["resolution"], evidence / "plain" / "devcapsule.resolved.toml")
        shutil.copy(files["record"], evidence / "devcapsule.checkout.toml")
        (evidence / "facts.json").write_text(json.dumps({
            "slug": slug, "required": REQUIRED.name, "alternate": ALTERNATE.name,
            "refusal_exit": refused.returncode, "forced": forced_facts, "plain": plain_facts,
            "record_unchanged": True, "shared_unchanged": True,
        }, indent=2) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        (evidence / "removed-records.json").write_text(
            json.dumps([str(path) for path in remove_project_records(slug)], indent=2) + "\n", encoding="utf-8")
