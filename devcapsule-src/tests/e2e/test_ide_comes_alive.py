"""Smoke: each IDE surface the product offers comes alive in a fresh project.

Opt-in (``nox -s ide-smoke``): a run initializes a project per surface with
the executable under test, launches it, and proves the IDE is up from the
outside. A first run on a machine acquires the IDE and builds its environment,
which takes minutes; later runs reuse both. Needs Docker and the base image
the executable recommends; runs inside a capsule as well as on a host.
"""

from __future__ import annotations

import json
import hashlib
import os
import time
import uuid
from pathlib import Path

import pytest

from devcapsule.platforms import HostOs
from devcapsule.runtime_artifact import RUNTIME_PEX_ENV, executable_platform
from tests.e2e.ide_session import SURFACES, IdeSurface, capture_desktop, command, desktop_page_answers, ide_session, launched_ide, stop_session, wait_for_console_url, wait_for_ide_window

pytestmark = pytest.mark.legacy

EVIDENCE_ROOT = Path(__file__).resolve().parents[2] / "dist" / "e2e-evidence" / "ide-smoke"


@pytest.fixture(scope="session")
def evidence_run() -> Path:
    """One directory per test run under the evidence root, never overwritten.

    Named by the UTC time and a short id; holds a subdirectory per surface and
    ``run.json``, which each test writes with the executable it used.
    """
    run = EVIDENCE_ROOT / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:6]}"
    run.mkdir(parents=True)
    return run


@pytest.mark.e2e
@pytest.mark.ide_smoke
@pytest.mark.parametrize("surface", SURFACES, ids=[surface.name for surface in SURFACES])
def test_ide_comes_alive(surface: IdeSurface, built_pex: Path, tmp_path: Path, evidence_run: Path) -> None:
    evidence = evidence_run / surface.name
    (evidence_run / "run.json").write_text(json.dumps({
        "executable": str(built_pex),
        "sha256": hashlib.sha256(built_pex.read_bytes()).hexdigest(),
        "version": command(str(built_pex), "version", "--json").stdout,
    }, indent=2) + "\n", encoding="utf-8")
    with ide_session(built_pex, surface, tmp_path, evidence) as session:
        # 1. The launcher published a desktop and the page behind it answers.
        assert desktop_page_answers(session.desktop_url) == 200, session.desktop_url
        # 2. The IDE owns a top-level window on the capsule's own display.
        window = wait_for_ide_window(session)
        # 2b. The web console answers beside the desktop, and only with the token.
        assert session.launcher is not None
        console_url = wait_for_console_url(session.launcher, session.launcher_log)
        console_answers = desktop_page_answers(console_url)
        assert console_answers == 200, console_url
        assert desktop_page_answers(console_url.split("?", 1)[0]) == 403, "the console admitted a tokenless request"
        # 3. Optional pixel evidence: the desktop renders more than a bare desktop.
        pixels = capture_desktop(session, evidence)
        if os.environ.get("DEVCAPSULE_SMOKE_DISPLAY") == "1":
            assert pixels is not None, "Required Playwright browser evidence is unavailable"
        if pixels is not None:
            distinct = pixels["distinctColours"]
            assert isinstance(distinct, int) and distinct >= 64, pixels
        facts = {
            "surface": surface.name,
            "needs": list(surface.needs),
            "container": session.container,
            "desktop_url_port": session.desktop_url.split(":")[2].split("/")[0],
            "console_url_port": console_url.split(":")[2].split("/")[0],
            "console_answers": console_answers,
            "ide_window": window,
            "pixels": pixels if pixels is not None else "not captured: Playwright and its browser are optional",
        }
        (evidence / "facts.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
        identity = command("docker", "inspect", "--format", '{{json .Id}} {{json .Image}}', session.container)
        (evidence / "container-identity.txt").write_text(identity.stdout, encoding="utf-8")
        child_digest = command("docker", "exec", session.container, "sha256sum", "/opt/devcapsule/bin/devcapsule.pex").stdout.split()[0]
        assert child_digest == hashlib.sha256(delivered_runtime(built_pex, session.workspace).read_bytes()).hexdigest(), \
            "Child runtime differs from the runtime the selected executable delivers"
        if surface.name == "eclipse":
            package = command("docker", "exec", "--user", f"{os.getuid()}:{os.getgid()}",
                              session.container, "python3", "-c",
                              "import json, os; from pathlib import Path; "
                              "root=Path('/opt/eclipse'); "
                              "print(json.dumps({'ini':(root/'eclipse.ini').read_text(), "
                              "'jdt':[p.name for p in (root/'plugins').glob('org.eclipse.jdt.core_*.jar')], "
                              "'installation_writable':os.access(root/'configuration',os.W_OK), "
                              "'user_configurations':[str(p) for p in Path.home().glob('.eclipse/**/configuration')]}))")
            (evidence / "eclipse-package.json").write_text(package.stdout, encoding="utf-8")
            payload = json.loads(package.stdout)
            assert "org.eclipse.epp.package.java.product" in payload["ini"]
            assert payload["jdt"], "Java Development Tools are missing from the package"
            assert not payload["installation_writable"]
            assert payload["user_configurations"], "Eclipse did not create its configuration in persistent home"
        if surface.name == "rider":
            sdk = command("docker", "exec", "--user", f"{os.getuid()}:{os.getgid()}", "--workdir", str(session.project_path),
                          session.container, "dotnet", "--info")
            (evidence / "dotnet-info.txt").write_text(sdk.stdout, encoding="utf-8")
            assert "10.0.401" in sdk.stdout
            build = command("docker", "exec", "--user", f"{os.getuid()}:{os.getgid()}", "--workdir", str(session.project_path),
                            session.container, "dotnet", "build", "Smoke.csproj", "--nologo")
            (evidence / "dotnet-build.txt").write_text(build.stdout + build.stderr, encoding="utf-8")
            run = command("docker", "exec", "--user", f"{os.getuid()}:{os.getgid()}", "--workdir", str(session.project_path),
                          session.container, "dotnet", "run", "--project", "Smoke.csproj", "--no-build")
            (evidence / "dotnet-run.txt").write_text(run.stdout + run.stderr, encoding="utf-8")
            assert run.stdout.strip() == "DevCapsule .NET smoke passed"
        if "browser-automation" in surface.needs:
            browser = command("docker", "exec", "-e", "PLAYWRIGHT_BROWSERS_PATH=/opt/playwright/browsers",
                              session.container, "/opt/playwright/venv/bin/python", "-c",
                              "import json; from playwright.sync_api import sync_playwright; "
                              "p=sync_playwright().start(); b=p.chromium.launch(); page=b.new_page(); "
                              "page.set_content('<h1>component browser alive</h1>'); "
                              "print(json.dumps({'version':b.version,'text':page.locator('h1').inner_text()})); "
                              "b.close(); p.stop()")
            (evidence / "component-browser.json").write_text(browser.stdout, encoding="utf-8")
            assert json.loads(browser.stdout)["text"] == "component browser alive"
        if scenario_name := os.environ.get("DEVCAPSULE_SMOKE_SCENARIO"):
            from tests.e2e.scenario_recorder import load_scenario, run_scenario_replay

            spec = load_scenario(scenario_name)
            assert spec.surface == surface.name, f"Scenario {spec.id} targets {spec.surface}, not {surface.name}"
            run_scenario_replay(session, evidence, spec)
        if os.environ.get("DEVCAPSULE_SMOKE_AGENT") == "1":
            from tests.e2e.visual_smoke import run_visual_smoke

            result = run_visual_smoke(session, evidence)
            if surface.name == "eclipse":
                log = command("docker", "exec", session.container, "cat", "/ide-workspace/.metadata/.log")
                (evidence / "eclipse-workspace.log").write_text(log.stdout, encoding="utf-8")
                assert "no underlying browser available" not in log.stdout
            if os.environ.get("DEVCAPSULE_SMOKE_RELAUNCH") == "1":
                assert surface.name in {"intellij", "rider"}
                before = editor_font_size(session.container)
                assert before == 17, f"IDE did not persist the UI-selected font size: {before}"
                stop_session(session)
                with launched_ide(built_pex, surface, session.workspace, evidence / "relaunch",
                                  session.container + "-relaunch") as resumed:
                    assert desktop_page_answers(resumed.desktop_url) == 200
                    resumed_window = wait_for_ide_window(resumed)
                    pixels = capture_desktop(resumed, evidence / "relaunch")
                    assert pixels is not None
                    after = editor_font_size(resumed.container)
                    assert after == before
                    assert result["marker"] in (resumed.workspace / "smoke.txt").read_text()
                    # A retained file and a window class do not establish a
                    # usable editor: repeat the interaction after relaunch.
                    run_visual_smoke(resumed, evidence / "relaunch")
                    (evidence / "persistence.json").write_text(json.dumps({
                        "editor_font_before": before, "editor_font_after": after,
                        "saved_marker_retained": True, "window": resumed_window,
                    }, indent=2) + "\n", encoding="utf-8")


def delivered_runtime(executable: Path, workspace: Path) -> Path:
    """The executable a launch from ``executable`` should deliver into the capsule.

    Derived independently of the launcher's choice: itself when it is a Linux
    executable; for a macOS launcher, the Linux runtime its environment names,
    from a directory the one for the platform of the one lock the smoke's init wrote.
    """
    if executable_platform(executable) is not HostOs.DARWIN:
        return executable
    named = Path(os.environ[RUNTIME_PEX_ENV]).expanduser().resolve()
    if named.is_dir():
        (lock,) = (workspace / ".devcapsule").glob("devcapsule.*.lock")
        return named / f"devcapsule-{lock.name.split('.')[1]}"
    return named


def editor_font_size(container: str) -> float:
    probe = command("docker", "exec", container, "python3", "-c",
                    "import xml.etree.ElementTree as E; "
                    "root=E.parse('/ide-config/options/editor-font.xml'); "
                    "print(next(x.attrib['value'] for x in root.iter('option') if x.attrib.get('name')=='FONT_SIZE'))")
    return float(probe.stdout.strip())
