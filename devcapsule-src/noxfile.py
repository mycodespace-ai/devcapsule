from __future__ import annotations

import os
import json
import hashlib
import uuid
import argparse
import shutil
from pathlib import Path

import nox


nox.options.sessions = ["build"]
nox.options.default_venv_backend = "venv"
nox.options.reuse_existing_virtualenvs = True

PROJECT_ROOT = Path(__file__).parent
REPO_ROOT = PROJECT_ROOT.parent
TEST_PEX_PATH = PROJECT_ROOT / "dist" / "devcapsule-local.pex"
PUBLIC_PEX_PATH = PROJECT_ROOT / "dist" / "devcapsule.pex"
PUBLIC_PEX_REPOSITORY_ENV = "DEVCAPSULE_PUBLIC_PEX_SOURCE_REPOSITORY"
PEX_UNDER_TEST_ENV = "DEVCAPSULE_PEX_UNDER_TEST"
VERSION_SCRIPT = PROJECT_ROOT / "scripts" / "bump-version.py"
WEBCONSOLE_ROOT = REPO_ROOT / "devcapsule-webconsole"


def install_locked(session: nox.Session) -> None:
    session.install("-r", str(PROJECT_ROOT / "dev-requirements.txt"))
    session.install("-e", str(PROJECT_ROOT), "--no-deps")


def check_python_syntax(session: nox.Session) -> None:
    session.run("python", "-m", "compileall", "-q", str(PROJECT_ROOT / "devcapsule"))


def check_distribution_version(session: nox.Session) -> None:
    session.run("python", str(VERSION_SCRIPT), "--check")


def check_shell_syntax(session: nox.Session) -> None:
    scripts = [
        *sorted((REPO_ROOT / "docker4pycharm").glob("*.sh")),
        *sorted((PROJECT_ROOT / "scripts").glob("*.sh")),
        *sorted((PROJECT_ROOT / "devcapsule" / "assets").rglob("*.sh")),
    ]
    for script in scripts:
        session.run("bash", "-n", str(script), external=True)


def run_tests(session: nox.Session) -> None:
    session.run("python", "-m", "pytest", str(PROJECT_ROOT / "tests"))


def check_test_conventions(session: nox.Session) -> None:
    """Hold the suite to *Unit Tests* in WORKFLOW-LOCAL.md; legacy files are compared with the diff base."""
    session.run("python", str(PROJECT_ROOT / "scripts" / "validate_unittests_follow_conventions.py"))


def run_packaging_tests(session: nox.Session) -> None:
    session.run(
        "python",
        "-m",
        "pytest",
        "--no-cov",
        "-m",
        "integration",
        str(PROJECT_ROOT / "tests" / "integration"),
    )


def select_e2e_pex(session: nox.Session) -> bool:
    """Use an explicitly selected executable, or build the local smoke artifact."""
    selected = session.env.get(PEX_UNDER_TEST_ENV) or os.environ.get(PEX_UNDER_TEST_ENV)
    if not selected:
        build_test_pex(session)
        session.env[PEX_UNDER_TEST_ENV] = str(TEST_PEX_PATH)
        return False
    path = Path(selected).expanduser().resolve(strict=True)
    output = session.run(str(path), "version", "--json", external=True, silent=True)
    assert isinstance(output, str), "Selected PEX must report its build identity"
    identity = json.loads(output)
    for name, key in (("DEVCAPSULE_EXPECTED_RELEASE_VERSION", "version"),
                      ("DEVCAPSULE_EXPECTED_BUILD_MNEMONIC", "build_mnemonic")):
        actual = identity[key]
        expected = session.env.get(name) or os.environ.get(name)
        if expected and expected != actual:
            session.error(f"Selected PEX {key} is {actual!r}, expected {expected!r}")
        session.env[name] = actual
    session.env[PEX_UNDER_TEST_ENV] = str(path)
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    session.log(f"E2E executable: {path}; {identity['build_mnemonic']}; source {identity['source_revision']}; sha256 {checksum}")
    return True


def build_e2e_base(session: nox.Session, *, network: str = "default") -> None:
    """Build the real base with the selected release CLI and test its exact image ID."""
    executable = session.env[PEX_UNDER_TEST_ENV]
    assert executable, "Select the release executable before building its base"
    output = session.run(executable, "version", "--json", external=True, silent=True)
    assert isinstance(output, str)
    identity = json.loads(output)
    tag = f"devcapsule-base-e2e:{identity['build_mnemonic']}-{uuid.uuid4().hex[:12]}"
    session.run(executable, "images", "build", "--type", "base", "--recipe", "ubuntu-24.04",
                "--tag", tag, "--network", network, "--source-revision", identity["source_revision"], external=True)
    output = session.run("docker", "image", "inspect", tag, external=True, silent=True)
    assert isinstance(output, str)
    inspection = json.loads(output)[0]
    image_id = inspection["Id"]
    # Dockerfile FROM needs an image reference, not the sha256: image-ID spelling.
    # Keep the unique owned tag for builds and verify it against the captured ID.
    session.env["DEVCAPSULE_E2E_BASE_IMAGE"] = tag
    session.env["DEVCAPSULE_EARLY_EXIT_E2E_IMAGE"] = image_id
    session.env["DEVCAPSULE_E2E_BUILT_BASE"] = image_id
    session.env["DEVCAPSULE_EXPECTED_BASE_SOURCE"] = identity["source_revision"]
    with Path(executable).open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    evidence = PROJECT_ROOT / "dist" / "e2e-base-build.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({"tag": tag, "image-id": image_id,
                                   "builder": identity, "builder-sha256": checksum}, indent=2) + "\n")
    session.log(f"Built base retained for inspection: {tag} ({image_id}); evidence: {evidence}")


def run_e2e_tests(session: nox.Session, *, release_smoke: bool = False) -> None:
    environment: dict[str, str] = {}
    for name in (
        "DEVCAPSULE_E2E_BASE_IMAGE",
        "DEVCAPSULE_EARLY_EXIT_E2E_IMAGE",
        "DEVCAPSULE_CONTRIBUTOR_E2E_IMAGE",
        "DEVCAPSULE_PEX_CLEAN_MACHINE_IMAGE",
        PEX_UNDER_TEST_ENV,
        "DEVCAPSULE_EXPECTED_RELEASE_VERSION",
        "DEVCAPSULE_EXPECTED_BUILD_MNEMONIC",
        "DEVCAPSULE_E2E_BUILT_BASE",
        "DEVCAPSULE_EXPECTED_BASE_SOURCE",
        "DEVCAPSULE_E2E_BUILD_NETWORK",
    ):
        value = session.env.get(name) or os.environ.get(name)
        if value is not None:
            environment[name] = value
    session.run(
        "python",
        "-m",
        "pytest",
        "--no-cov",
        "-m",
        "e2e and not recursive_e2e and not ide_smoke" + (" and not contributor_e2e" if release_smoke else "")
        + ("" if session.env.get("DEVCAPSULE_E2E_BUILT_BASE") else " and not base_build_e2e"),
        str(PROJECT_ROOT / "tests" / "e2e"),
        env=environment,
    )


def run_recursive_e2e_tests(session: nox.Session) -> None:
    session.run(
        "python",
        "-m",
        "pytest",
        "--no-cov",
        "-m",
        "recursive_e2e or contributor_e2e",
        str(PROJECT_ROOT / "tests" / "e2e"),
    )


def run_typecheck(session: nox.Session) -> None:
    session.run(
        "python",
        "-m",
        "mypy",
        str(PROJECT_ROOT / "devcapsule"),
        str(PROJECT_ROOT / "tests"),
        str(PROJECT_ROOT / "noxfile.py"),
        str(VERSION_SCRIPT),
        str(PROJECT_ROOT / "scripts" / "release-manifest.py"),
        str(PROJECT_ROOT / "scripts" / "validate_unittests_follow_conventions.py"),
        str(PROJECT_ROOT / "scripts" / "publish_coverage_numbers_to_pr.py"),
        str(PROJECT_ROOT / "scripts" / "release-protocol.py"),
        str(PROJECT_ROOT / "scripts" / "prepare-promotion.py"),
    )


def run_smoke(session: nox.Session) -> None:
    session.run("python", "-m", "devcapsule", "--help")
    session.run("python", "-m", "devcapsule", "version", "--json")
    session.run("python", "-m", "devcapsule", "runtime", success_codes=[2])
    session.run("python", "-m", "devcapsule", "runtime", "diagnose-probe", "--help")
    session.run("python", "-m", "devcapsule", "host-open", "--help")
    session.run("python", "-m", "devcapsule", "pycharm", "run", "--help", success_codes=[2])
    session.run("python", "-m", "devcapsule", "project", "--help")
    session.run("python", "-m", "devcapsule", "project", "diagnose", "--help")
    session.run("python", "-m", "devcapsule", "project", "list", "--help")
    session.run("python", "-m", "devcapsule", "project", "config", "show", "--help")
    session.run("python", "-m", "devcapsule", "project", "run", "--help")
    session.run("python", "-m", "devcapsule", "project", "config", "set", "--help")
    session.run("python", "-m", "devcapsule", "project", "config", "bind", "--help")
    session.run("python", "-m", "devcapsule", "project", "config", "authorize", "--help")
    session.run("python", "-m", "devcapsule", "project", "run", "--help")
    session.run("python", "-m", "devcapsule", "project", "run-image", "--help", success_codes=[2])
    session.run("python", "-m", "devcapsule", "project", "recursive-e2e", "preflight", "--help")
    session.run("python", "-m", "devcapsule", "project", "recursive-e2e", "run", "--help")
    session.run("python", "-m", "devcapsule", "project", "recursive-e2e", "launch-successor", "--help")
    session.run("python", "-m", "devcapsule", "project", "recursive-e2e", "inspect-successor", "--help")
    session.run("python", "-m", "devcapsule", "images", "list", "--help")
    session.run("python", "-m", "devcapsule", "images", "build", "--help")
    session.run("python", "-m", "devcapsule", "pycharm", "build", "--help")
    session.run(str(REPO_ROOT / "docker4pycharm" / "run-pycharm-container.sh"), "--help", external=True)


def build_test_pex(session: nox.Session) -> None:
    session.run(
        str(PROJECT_ROOT / "scripts" / "build-pex.sh"),
        "--output",
        str(TEST_PEX_PATH),
        "--allow-local-source",
        env={"PYTHON": "python"},
        external=True,
    )


def build_public_pex_if_clean(session: nox.Session) -> bool:
    status = session.run(
        "git",
        "-C",
        str(REPO_ROOT),
        "status",
        "--porcelain",
        external=True,
        silent=True,
    )
    if str(status).strip():
        session.log(
            "Not building dist/devcapsule.pex: the repository has uncommitted "
            "changes. Any existing file at that path is unchanged and may be "
            "stale. The local validation artifact is dist/devcapsule-local.pex."
        )
        return False

    build_environment = {"PYTHON": "python"}
    explicit_repository = os.environ.get(PUBLIC_PEX_REPOSITORY_ENV)
    if explicit_repository:
        build_environment["DEVCAPSULE_SOURCE_REPOSITORY"] = explicit_repository
    session.run(
        str(PROJECT_ROOT / "scripts" / "build-pex.sh"),
        "--output",
        str(PUBLIC_PEX_PATH),
        "--allow-unpublished-revision",
        env=build_environment,
        external=True,
    )
    return True


def smoke_pex(session: nox.Session, path: Path = TEST_PEX_PATH) -> None:
    session.run(str(path), "--help", external=True)
    session.run(str(path), "version", "--json", external=True)
    session.run(str(path), "runtime", success_codes=[2], external=True)
    session.run(str(path), "runtime", "diagnose-probe", "--help", external=True)
    session.run(str(path), "host-open", "--help", external=True)
    session.run(str(path), "pycharm", "run", "--help", success_codes=[2], external=True)
    session.run(str(path), "project", "--help", external=True)
    session.run(str(path), "project", "diagnose", "--help", external=True)
    session.run(str(path), "project", "list", "--help", external=True)
    session.run(str(path), "project", "config", "show", "--help", external=True)
    session.run(str(path), "project", "run", "--help", external=True)
    session.run(str(path), "project", "config", "set", "--help", external=True)
    session.run(str(path), "project", "config", "bind", "--help", external=True)
    session.run(str(path), "project", "config", "authorize", "--help", external=True)
    session.run(str(path), "project", "run", "--help", external=True)
    session.run(str(path), "project", "run-image", "--help", success_codes=[2], external=True)
    session.run(
        str(path), "project", "recursive-e2e", "preflight", "--help", external=True
    )
    session.run(str(path), "project", "recursive-e2e", "run", "--help", external=True)
    session.run(
        str(path), "project", "recursive-e2e", "launch-successor", "--help", external=True
    )
    session.run(
        str(path), "project", "recursive-e2e", "inspect-successor", "--help", external=True
    )
    session.run(str(path), "images", "list", "--help", external=True)
    session.run(str(path), "images", "build", "--help", external=True)
    session.run(str(path), "pycharm", "build", "--help", external=True)


def run_webconsole_checks(session: nox.Session) -> None:
    """Type-check and test the capsule web console in its own environment.

    The console is a separate distribution with its own hash-pinned
    dependency set, so it never shares the runtime's environment: the base
    image installs it the same way.
    """
    session.install("--require-hashes", "-r", str(WEBCONSOLE_ROOT / "requirements-dev.txt"))
    session.install("-e", str(WEBCONSOLE_ROOT), "--no-deps")
    # The launcher too, with its one runtime dependency, which its command
    # tree imports: the console's contract tests check every command it runs
    # and every verb it forwards against the launcher's own parser and channel
    # tables, so a retirement on one side fails here before it reaches a capsule.
    session.install("-e", str(PROJECT_ROOT))
    session.run("python", "-m", "mypy", "--config-file", str(WEBCONSOLE_ROOT / "pyproject.toml"),
                str(WEBCONSOLE_ROOT / "devcapsule_webconsole"))
    session.run("python", "-m", "pytest", str(WEBCONSOLE_ROOT / "tests"))


def check_docs_contract(session: nox.Session) -> None:
    """Check docs/, the journal and the release notes against the website's contract.

    The pinned website submodule owns the check (``npm run check:content``); this
    runs it against the repository root as the content checkout, so a producer
    change that would break the site fails here first. Skipped with a notice
    when the submodule is not initialized or npm is absent, as on the hosted
    test runner, where the documentation is not built.
    """
    website = REPO_ROOT / "website"
    if not (website / "package.json").exists():
        session.log("docs contract: website submodule not initialized; skipped")
        return
    if shutil.which("npm") is None:
        session.log("docs contract: npm not available; skipped")
        return
    if not (website / "node_modules").exists():
        session.run("npm", "--prefix", str(website), "ci", external=True)
    session.run(
        "npm", "--prefix", str(website), "run", "check:content",
        env={"CONTENT_DIR": str(REPO_ROOT)}, external=True,
    )


def run_clean_machine_pex_test(session: nox.Session) -> None:
    environment: dict[str, str] = {}
    for name in ("DEVCAPSULE_PEX_CLEAN_MACHINE_IMAGE", PEX_UNDER_TEST_ENV):
        value = session.env.get(name) or os.environ.get(name)
        if value is not None:
            environment[name] = value
    session.run(
        "python",
        "-m",
        "pytest",
        "--no-cov",
        "-m",
        "e2e",
        str(PROJECT_ROOT / "tests" / "e2e" / "test_self_contained_pex.py"),
        env=environment,
    )


@nox.session(python="3.12")
def syntax(session: nox.Session) -> None:
    install_locked(session)
    check_python_syntax(session)
    check_shell_syntax(session)


@nox.session(name="bump", python="3.12")
def bump_version(session: nox.Session) -> None:
    """Advance the package version by major/minor/patch or to an explicit version."""

    session.run("python", str(VERSION_SCRIPT), *session.posargs)


@nox.session(python="3.12")
def tests(session: nox.Session) -> None:
    install_locked(session)
    check_python_syntax(session)
    check_test_conventions(session)
    run_tests(session)


@nox.session(python="3.12")
def smoke(session: nox.Session) -> None:
    install_locked(session)
    run_smoke(session)


@nox.session(python="3.12")
def typecheck(session: nox.Session) -> None:
    install_locked(session)
    run_typecheck(session)


@nox.session(python="3.12")
def pex(session: nox.Session) -> None:
    install_locked(session)
    check_shell_syntax(session)
    build_test_pex(session)
    smoke_pex(session)


@nox.session(python="3.12")
def integration(session: nox.Session) -> None:
    install_locked(session)
    build_test_pex(session)
    run_packaging_tests(session)


@nox.session(python="3.12")
def pex_clean_machine(session: nox.Session) -> None:
    """Prove the eager PEX scie on a networkless image with no host Python."""

    install_locked(session)
    selected_pex = session.env.get(PEX_UNDER_TEST_ENV) or os.environ.get(
        PEX_UNDER_TEST_ENV
    )
    if not selected_pex:
        build_test_pex(session)
    run_clean_machine_pex_test(session)


@nox.session(python="3.12")
def e2e(session: nox.Session) -> None:
    install_locked(session)
    parser = argparse.ArgumentParser(prog="nox -s e2e --")
    parser.add_argument("--build-base", action="store_true")
    parser.add_argument("--build-network", choices=("default", "host", "none"), default="default")
    options = parser.parse_args(session.posargs)
    if options.build_network != "default":
        # The runtime-image e2e installs the display stack with apt during
        # its own docker build, so the network choice reaches it too.
        session.env["DEVCAPSULE_E2E_BUILD_NETWORK"] = options.build_network
    if options.build_base and not (
        session.env.get(PEX_UNDER_TEST_ENV) or os.environ.get(PEX_UNDER_TEST_ENV)
    ):
        session.error("--build-base requires DEVCAPSULE_PEX_UNDER_TEST to select a published executable")
    release_smoke = select_e2e_pex(session)
    if options.build_base:
        build_e2e_base(session, network=options.build_network)
    run_e2e_tests(session, release_smoke=release_smoke)


PLAYWRIGHT_VERSION = "1.63.0"
"""Browser automation for the optional pixel evidence of the IDE smoke; pinned here, outside the lock."""


@nox.session(name="ide-smoke", python="3.12")
def ide_smoke(session: nox.Session) -> None:
    """Launch each IDE surface in a fresh project and prove it comes alive.

    Uses DEVCAPSULE_PEX_UNDER_TEST when set, else the local build. Pass
    ``--display`` to install Playwright and Chromium into the session and keep a
    screenshot of each desktop as evidence; without it the X11 facts alone decide.
    ``--scenario`` replays one recorded scenario on its own surface and keeps the
    video; it needs exactly one ``--surface`` and excludes ``--agent``.
    """
    install_locked(session)
    parser = argparse.ArgumentParser(prog="nox -s ide-smoke --")
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--agent", action="store_true", help="require an AI-driven saved edit and visual recognition")
    parser.add_argument("--scenario", help="run a recorded or scripted IDE scenario and record pause-free WebM video")
    parser.add_argument("--component-browser", action="store_true", help="drive the child Playwright component; requires --display, --agent, or --scenario")
    parser.add_argument("--relaunch", action="store_true", help="JetBrains: set editor font size through the UI and verify persistence")
    parser.add_argument("--driver", choices=("codex", "claude"), default="codex")
    parser.add_argument("--model", help="default: gpt-6-astra for Codex, claude-fable-5-1 for Claude")
    parser.add_argument("--recognizer", choices=("codex", "claude"), help="defaults to the action driver")
    parser.add_argument("--recognizer-model")
    parser.add_argument("--max-actions", type=int, default=30)
    parser.add_argument("--agent-timeout", type=int, default=900)
    parser.add_argument("--surface", action="append", default=[], help="limit to a surface name; repeatable")
    parser.add_argument("--platform", help="create each project for this capsule platform, such as linux-arm64")
    parser.add_argument("--required-ide", action="store_true",
                        help="instead of the surfaces: a project requiring PyCharm launches Codium once with "
                             "'run --ide codium --force', then PyCharm again plainly (work order of 2026-10-28)")
    options = parser.parse_args(session.posargs)
    if options.required_ide and (options.surface or options.agent or options.scenario):
        session.error("--required-ide runs its own two launches; it takes no --surface, --agent or --scenario")
    if options.component_browser and not (options.agent or options.display or options.scenario):
        session.error("--component-browser requires --display, --agent, or --scenario")
    if options.component_browser:
        session.env["DEVCAPSULE_SMOKE_COMPONENT_BROWSER"] = "1"
    if options.scenario:
        if options.agent:
            session.error("--scenario cannot be combined with --agent: the scenario leaves the IDE in its final state")
        if len(options.surface) != 1:
            session.error("--scenario requires exactly one --surface, the scenario's own")
    if options.platform:
        session.env["DEVCAPSULE_SMOKE_PLATFORM"] = options.platform
    if options.relaunch:
        if not options.agent or options.surface not in (["intellij"], ["rider"]):
            session.error("--relaunch requires --agent --surface intellij or rider")
        session.env["DEVCAPSULE_SMOKE_RELAUNCH"] = "1"
    select_e2e_pex(session)
    if options.display or options.agent or options.scenario:
        wheels = os.environ.get("DEVCAPSULE_PLAYWRIGHT_WHEELS")
        if wheels:
            session.install("--no-index", "--find-links", wheels, f"playwright=={PLAYWRIGHT_VERSION}")
        else:
            session.install(f"playwright=={PLAYWRIGHT_VERSION}")
            session.run("playwright", "install", "chromium")
        session.env["DEVCAPSULE_SMOKE_DISPLAY"] = "1"
    if options.scenario:
        session.env["DEVCAPSULE_SMOKE_SCENARIO"] = options.scenario
    if options.agent:
        session.env.update({
            "DEVCAPSULE_SMOKE_AGENT": "1", "DEVCAPSULE_SMOKE_DRIVER": options.driver,
            "DEVCAPSULE_SMOKE_MAX_ACTIONS": str(options.max_actions),
            "DEVCAPSULE_SMOKE_TIMEOUT": str(options.agent_timeout),
        })
        for key in ("model", "recognizer", "recognizer_model"):
            if value := getattr(options, key):
                session.env[f"DEVCAPSULE_SMOKE_{key.upper()}"] = value
    session.run(
        "python", "-m", "pytest", "--no-cov", "-m", "ide_smoke",
        *(["-k", " or ".join(options.surface)] if options.surface else []),
        str(PROJECT_ROOT / "tests" / "e2e" / ("test_required_ide_override.py" if options.required_ide else "test_ide_comes_alive.py")),
        env={PEX_UNDER_TEST_ENV: session.env[PEX_UNDER_TEST_ENV]},
    )


@nox.session(python="3.12")
def recursive_dogfood_e2e(session: nox.Session) -> None:
    """Run explicit host-sensitive recursive dogfood checks."""

    install_locked(session)
    session.run(
        "python",
        "-m",
        "devcapsule",
        "project",
        "--path",
        str(REPO_ROOT),
        "recursive-e2e",
        "run",
        "--json",
    )
    run_recursive_e2e_tests(session)


@nox.session(python="3.12")
def webconsole(session: nox.Session) -> None:
    """Checks of the capsule web console, in its own environment."""
    run_webconsole_checks(session)


@nox.session(name="docs-contract", python=False)
def docs_contract(session: nox.Session) -> None:
    """Run only the website content-contract check against this checkout."""
    check_docs_contract(session)


@nox.session(python="3.12")
def build(session: nox.Session) -> None:
    install_locked(session)
    check_distribution_version(session)
    check_python_syntax(session)
    check_shell_syntax(session)
    run_typecheck(session)
    check_test_conventions(session)
    run_tests(session)
    run_smoke(session)
    build_test_pex(session)
    smoke_pex(session)
    run_packaging_tests(session)
    check_docs_contract(session)
    if build_public_pex_if_clean(session):
        smoke_pex(session, PUBLIC_PEX_PATH)
    session.notify("webconsole")
