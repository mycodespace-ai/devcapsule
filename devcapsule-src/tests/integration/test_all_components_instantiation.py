"""Upgrade verification: initialize and instantiate a DevCapsule project with all supported components.

This integration module provides two levels of verification for catalog version upgrades:

1. ``test_all_supported_components_initialize_and_prepare_instantiation`` (offline, runs without Docker):
   verifies that a single DevCapsule project declaring every non-IDE capability in the catalog resolves
   without unverified combinations across every IDE surface, initializes cleanly through the CLI with all
   vendor acquisition consents, passes ``project config check``, and prepares its container launch plan via
   ``project run --print-command --no-update-check`` with every component pinned at its newest catalog version.
2. ``test_all_supported_components_instantiate_live_capsule`` (marked ``docker``, opt-in):
   initializes a fresh workspace declaring every non-IDE capability in the catalog plus an interactive
   surface, instantiates the live capsule container with ``project run``, verifies desktop/console/window
   readiness, and probes every materialized component and base service inside the running container.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import uuid

import pytest

from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.configuration.execution import ExecutionConfiguration
from devcapsule.configuration.storage import checkout_record_paths, lock_for
from devcapsule.materialization import parse_locked_environment
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES
from tests.e2e.ide_session import (
    CREATOR,
    SURFACES,
    IdeSurface,
    command,
    desktop_page_answers,
    launched_ide,
    remove_project_records,
    wait_for_console_url,
    wait_for_ide_window,
    workspace_root,
)

pytestmark = pytest.mark.integration

AMD64 = MATRICES[Platform.LINUX_AMD64]

EXPECTED_NON_IDE_CAPABILITIES: tuple[str, ...] = (
    "antigravity-agent",
    "browser-automation",
    "claude-code-agent",
    "codex-agent",
    "docker-cli",
    "dotnet",
    "graphviz",
    "java",
    "maven",
    "node",
    "postgresql-client",
    "python",
)

EXPECTED_NON_IDE_COMPONENTS: tuple[str, ...] = (
    "antigravity-cli",
    "claude-code",
    "codex",
    "dotnet-sdk",
    "graphviz",
    "playwright",
    "postgresql-client",
)

ALL_VENDOR_CONSENTS: tuple[tuple[str, str], ...] = (
    ("antigravity-download", "true"),
    ("claude-code-download", "true"),
    ("vscode-download", "true"),
)


def _all_non_ide_capabilities() -> tuple[str, ...]:
    """Every non-IDE capability in the linux-amd64 resolution matrix."""
    ide_set = set(AMD64.ide_capabilities())
    return tuple(name for name in AMD64.capabilities() if name not in ide_set)


def test_all_supported_components_initialize_and_prepare_instantiation(tmp_path: Path) -> None:
    """A project declaring all supported non-IDE capabilities resolves cleanly across every IDE surface,
    initializes with the latest catalog pins, passes ``config check``, and prepares its launch command."""
    non_ide = _all_non_ide_capabilities()
    assert non_ide == EXPECTED_NON_IDE_CAPABILITIES
    latest_pins = AMD64.component_pins()

    # 1. Every IDE surface composes with the full non-IDE capability set without unverified combinations.
    for ide_capability in AMD64.ide_capabilities():
        formation = AMD64.resolve([*non_ide, ide_capability])
        assert formation.unverified == (), f"{ide_capability} had unverified combinations: {formation.unverified}"
        rendered_lock = tomllib.loads(formation.render_lock())
        assert "unverified-combinations" not in rendered_lock
        for component_id in EXPECTED_NON_IDE_COMPONENTS:
            assert rendered_lock["components"][component_id]["version"] == latest_pins[component_id]["version"]

    # 2. Initialize a real project checkout declaring all non-IDE capabilities through the CLI.
    project = tmp_path / "all-components-project"
    project.mkdir()
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": os.environ["HOME"],
        "XDG_CONFIG_HOME": os.environ["XDG_CONFIG_HOME"],
        "XDG_DATA_HOME": os.environ["XDG_DATA_HOME"],
        "XDG_STATE_HOME": os.environ["XDG_STATE_HOME"],
        "XDG_CACHE_HOME": os.environ["XDG_CACHE_HOME"],
    }

    init_args = [
        sys.executable,
        "-m",
        "devcapsule",
        "project",
        "--path",
        str(project),
        "init",
        "--platform",
        Platform.LINUX_AMD64.value,
        "--ide",
        "frontend-ide",
        "--creator",
        CREATOR,
        *(flag for capability in non_ide for flag in ("--require", capability)),
        "--authorize",
        "base-image",
        "default",
        "--authorize",
        "host-x11",
        "false",
        "--authorize",
        "antigravity-download",
        "true",
        "--authorize",
        "claude-code-download",
        "true",
    ]
    init = subprocess.run(init_args, cwd=project, env=environment, text=True, capture_output=True, timeout=60)
    assert init.returncode == 0, f"project init failed:\n{init.stdout}\n{init.stderr}"

    manifest = tomllib.loads((project / ".devcapsule" / "devcapsule.toml").read_text(encoding="utf-8"))
    assert tuple(manifest["capabilities"]["required"]) == non_ide

    shared_lock = tomllib.loads((project / ".devcapsule" / "devcapsule.linux-amd64.lock").read_text(encoding="utf-8"))
    assert "unverified-combinations" not in shared_lock
    for component_id in EXPECTED_NON_IDE_COMPONENTS:
        assert shared_lock["components"][component_id]["version"] == latest_pins[component_id]["version"]

    # 3. Verify ``project config check`` and dry-run launch preparation (``project run --print-command``).
    check = subprocess.run(
        [sys.executable, "-m", "devcapsule", "project", "--path", str(project), "config", "check"],
        cwd=project,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert check.returncode == 0, f"config check failed:\n{check.stdout}\n{check.stderr}"
    assert "Configuration contract valid" in check.stdout

    record_path, resolved_path = checkout_record_paths(manifest, project)
    assert record_path.is_file()
    assert resolved_path.is_file()
    _, effective_lock = lock_for(project, manifest)
    assert effective_lock["components"]["interactive-surface"] == "codium"
    assert effective_lock["components"]["codium"]["version"] == latest_pins["codium"]["version"]
    for component_id in EXPECTED_NON_IDE_COMPONENTS:
        assert effective_lock["components"][component_id]["version"] == latest_pins[component_id]["version"]

    prepared = prepare_launch(project, RunFlags(), interactive=False, print_only=True)
    assert prepared.selected.resolution["runtime"]["component"] == "codium"
    execution = ExecutionConfiguration.load(project)
    assert execution.project.resolution["runtime"]["component"] == "codium"
    locked_env = parse_locked_environment(effective_lock)
    assert locked_env.component_id == "codium"
    ancillary_ids = {item.component_id for item in locked_env.ancillary_artifacts}
    assert ancillary_ids == {
        "antigravity-cli",
        "claude-code",
        "codex",
        "dotnet-sdk",
        "graphviz",
        "playwright",
    }


@pytest.mark.docker
def test_all_supported_components_instantiate_live_capsule(built_pex: Path, tmp_path: Path) -> None:
    """Create a DevCapsule project declaring all supported non-IDE components plus an IDE surface,
    instantiate the live container, and verify every component inside the running capsule."""
    surface_name = os.environ.get("DEVCAPSULE_ALL_COMPONENTS_SURFACE", "xfce4-terminal")
    base_surface = next(item for item in SURFACES if item.name == surface_name)
    non_ide = _all_non_ide_capabilities()
    surface = IdeSurface(
        name=base_surface.name,
        needs=(base_surface.needs[0], *non_ide),
        window_class=base_surface.window_class,
        ready_timeout=base_surface.ready_timeout,
        consents=tuple(dict((*base_surface.consents, *ALL_VENDOR_CONSENTS)).items()),
    )

    run_id = uuid.uuid4().hex[:8]
    slug = f"e2e-all-components-{surface.name}-{run_id}"
    container = f"devcapsule-e2e-all-components-{surface.name}-{run_id}"
    workspace = workspace_root(tmp_path) / slug
    workspace.mkdir(parents=True)
    evidence = tmp_path / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    latest_pins = AMD64.component_pins()

    environment = dict(os.environ, BROWSER="true")
    try:
        init = subprocess.run(
            [
                str(built_pex),
                "project",
                "init",
                "--platform",
                Platform.LINUX_AMD64.value,
                "--ide",
                surface.needs[0],
                *(flag for need in non_ide for flag in ("--require", need)),
                "--creator",
                CREATOR,
                "--slug",
                slug,
                "--authorize",
                "base-image",
                "default",
                "--authorize",
                "network",
                "host",
                "All-components upgrade instantiation smoke requires host networking.",
                *(flag for node, value in surface.consents for flag in ("--authorize", node, value)),
            ],
            cwd=workspace,
            env=environment,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            check=False,
            timeout=300.0,
        )
        assert init.returncode == 0, f"project init failed:\n{init.stdout}\n{init.stderr}"

        with launched_ide(built_pex, surface, workspace, evidence, container) as session:
            assert desktop_page_answers(session.desktop_url) == 200, session.desktop_url
            window = wait_for_ide_window(session)
            assert window
            assert session.launcher is not None
            console_url = wait_for_console_url(session.launcher, session.launcher_log)
            assert desktop_page_answers(console_url) == 200, console_url

            user_spec = f"{os.getuid()}:{os.getgid()}"
            probes = {
                "codex": ("codex", "--version"),
                "claude-code": ("claude", "--version"),
                "antigravity-cli": ("antigravity", "--version"),
                "dotnet-sdk": ("dotnet", "--info"),
                "graphviz": ("/opt/graphviz/bin/dot", "-V"),
                "postgresql-client": ("psql", "--version"),
                "python": ("python3", "--version"),
                "node": ("node", "--version"),
                "java": ("java", "-version"),
                "maven": ("mvn", "--version"),
                "docker-cli": ("docker", "--version"),
            }
            outputs: dict[str, str] = {}
            for name, probe_cmd in probes.items():
                result = command("docker", "exec", "--user", user_spec, session.container, *probe_cmd)
                outputs[name] = (result.stdout + result.stderr).strip()

            assert latest_pins["codex"]["version"] in outputs["codex"]
            assert latest_pins["claude-code"]["version"] in outputs["claude-code"]
            assert latest_pins["antigravity-cli"]["version"] in outputs["antigravity-cli"]
            assert latest_pins["dotnet-sdk"]["version"] in outputs["dotnet-sdk"]
            assert latest_pins["graphviz"]["version"] in outputs["graphviz"]
            assert latest_pins["postgresql-client"]["version"] in outputs["postgresql-client"]

            browser = command(
                "docker",
                "exec",
                "-e",
                "PLAYWRIGHT_BROWSERS_PATH=/opt/playwright/browsers",
                session.container,
                "/opt/playwright/venv/bin/python",
                "-c",
                "import json, playwright._repo_version as v; "
                "from playwright.sync_api import sync_playwright; "
                "p=sync_playwright().start(); b=p.chromium.launch(); page=b.new_page(); "
                "page.set_content('<h1>all-components browser alive</h1>'); "
                "print(json.dumps({'playwright':v.version,'browser':b.version,'text':page.locator('h1').inner_text()})); "
                "b.close(); p.stop()",
            )
            browser_payload = json.loads(browser.stdout)
            assert browser_payload["playwright"] == latest_pins["playwright"]["version"]
            assert browser_payload["text"] == "all-components browser alive"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        remove_project_records(slug)
