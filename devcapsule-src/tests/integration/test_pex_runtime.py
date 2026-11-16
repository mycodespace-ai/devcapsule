"""Integration tests of the built launcher: the one-file executable, run as a developer runs it.

Each test starts the executable that ``built_pex`` names, in an environment
the test builds: the search path, a home directory and a named DevCapsule
home under the test's directory, and the two caches the executable unpacks
itself into, which the suite keeps for the whole run. Nothing else of the
developer's shell reaches it, so the outcome is the same on a plain host and
inside a capsule, where an unnamed home would read the launcher's mounted
settings.

No test here needs Docker or the network.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from importlib.resources import files
from pathlib import Path

import pytest

import tomllib
from devcapsule.host_open import HOST_OPEN_SOCKET_ENV, HostOpenBroker

pytestmark = pytest.mark.integration

# The artifact under test is built from this tree, so compare against the
# authored version, not installed metadata an editable install may have frozen.
PACKAGE_VERSION = os.environ.get("DEVCAPSULE_EXPECTED_RELEASE_VERSION") or tomllib.loads(
    (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
)["project"]["version"]


@pytest.fixture
def environment(tmp_path: Path) -> dict[str, str]:
    """The environment every executable here is started in: a search path, a home and a named DevCapsule home
    under the test's directory, and the executable's own caches."""
    return {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path / "home"),
        "DEVCAPSULE_CONFIG_HOME": str(tmp_path / "devcapsule-home"),
        **{name: os.environ[name] for name in ("PEX_ROOT", "SCIE_BASE") if name in os.environ},
    }


def test_built_pex_dispatches_runtime_help(built_pex: Path, environment: dict[str, str]) -> None:
    """The executable carries the in-capsule runtime: ``runtime --help`` exits 0 with that command's usage."""
    completed = subprocess.run(
        [str(built_pex), "runtime", "--help"],
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    assert "usage: devcapsule runtime RUNTIME_PLAN.json" in completed.stdout


def test_built_pex_exposes_recursive_preflight_help(built_pex: Path, environment: dict[str, str]) -> None:
    """The recursive end-to-end commands are in the executable: ``preflight --help`` offers ``--show-host-paths``
    and ``run --help`` offers ``--keep-on-failure``."""
    completed = subprocess.run(
        [str(built_pex), "project", "recursive-e2e", "preflight", "--help"],
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    assert "read-only" not in completed.stderr.lower()
    assert "--show-host-paths" in completed.stdout

    run_help = subprocess.run(
        [str(built_pex), "project", "recursive-e2e", "run", "--help"],
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )
    assert run_help.returncode == 0, run_help.stderr
    assert "--keep-on-failure" in run_help.stdout


def test_built_pex_bootstraps_packaged_workflow(
    built_pex: Path, tmp_path: Path, environment: dict[str, str],
) -> None:
    """``bootstrap`` in an empty directory writes the workflow definition that the package carries, byte for
    byte, and a status file of a single-stream project."""
    project = tmp_path / "adopter"
    project.mkdir()

    completed = subprocess.run(
        [str(built_pex), "bootstrap"],
        check=False,
        text=True,
        capture_output=True,
        cwd=project,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    packaged_workflow = (
        files("devcapsule.assets.project_workflow")
        .joinpath("definition", "WORKFLOW.md")
        .read_text(encoding="utf-8")
    )
    assert (project / "WORKFLOW.md").read_text(
        encoding="utf-8"
    ) == packaged_workflow
    assert "Workflow type: `single-stream`" in (
        project / "CURRENT-STATUS.md"
    ).read_text(encoding="utf-8")


def test_built_pex_exposes_recursive_host_public_interface(built_pex: Path, environment: dict[str, str]) -> None:
    """Run as an interpreter, the executable imports ``devcapsule.recursive_host`` and its launch context class."""
    completed = subprocess.run(
        [
            str(built_pex),
            "-c",
            "from devcapsule.recursive_host import HostDaemonLaunchContext; "
            "print(HostDaemonLaunchContext.__name__)",
        ],
        check=False,
        text=True,
        capture_output=True,
        env={**environment, "PEX_INTERPRETER": "1"},
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "HostDaemonLaunchContext"


def test_xdg_open_dispatches_through_built_pex_to_exact_host_argument(
    built_pex: Path,
    tmp_path: Path,
    environment: dict[str, str],
) -> None:
    """``xdg-open URL``, with the executable's ``host-open`` as the browser, hands the broker's opener the URL
    exactly as given, shell characters and all."""
    xdg_open = shutil.which("xdg-open")
    if xdg_open is None:
        pytest.skip("xdg-open is unavailable on this packaging-test host")
    socket_path = tmp_path / "host-open.sock"
    captured = tmp_path / "captured-url"
    url = "https://example.test/path?a=one&b=%24%28touch%20nope%29#fragment"
    opener = (
        sys.executable,
        "-c",
        "from pathlib import Path; import sys; Path(sys.argv[1]).write_text(sys.argv[2])",
        str(captured),
    )

    with HostOpenBroker(socket_path, opener=opener):
        completed = subprocess.run(
            [xdg_open, url],
            check=False,
            text=True,
            capture_output=True,
            env={
                **environment,
                "BROWSER": f"{built_pex} host-open",
                HOST_OPEN_SOCKET_ENV: str(socket_path),
                "DISPLAY": "",
                "XDG_CURRENT_DESKTOP": "",
                "DE": "",
            },
        )

    assert completed.returncode == 0, completed.stderr
    assert captured.read_text(encoding="utf-8") == url


def test_built_pex_exposes_self_contained_source_identity(built_pex: Path, environment: dict[str, str]) -> None:
    """``version --json`` gives the six fields of the executable's identity. The version is the one this tree
    declares; a local build has no source revision, a release build names its commit."""
    completed = subprocess.run(
        [str(built_pex), "version", "--json"],
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    value = json.loads(completed.stdout)
    assert value["schema_version"] == 2
    assert value["version"] == PACKAGE_VERSION
    assert value["build_mnemonic"] == os.environ.get(
        "DEVCAPSULE_EXPECTED_BUILD_MNEMONIC",
        f"v{PACKAGE_VERSION}-local-{os.environ.get('DEVCAPSULE_SCIE_PLATFORM', 'linux-x86_64')}",
    )
    if built_pex.name == "devcapsule-local.pex":
        assert value["source_revision"] == "unknown"
        assert value["source_url"] == "unknown"
    else:
        assert built_pex.name == "devcapsule.pex"
        assert re.fullmatch(r"[0-9a-f]{40,64}", value["source_revision"])
        assert value["source_url"].endswith(f"/commit/{value['source_revision']}")
    assert set(value) == {
        "schema_version",
        "version",
        "build_mnemonic",
        "source_repository",
        "source_revision",
        "source_url",
    }


def test_built_pex_authors_shared_policy_and_keeps_personal_selection_local(
    built_pex: Path, tmp_path: Path, environment: dict[str, str],
) -> None:
    """A developer's own choices, an IDE, an omitted offer, an added agent, change no file of the project's
    shared directory. The base then waits for the home's trust: ``config check`` exits 3 until the channel is
    accepted for the home, and 0 after. A requirement in the retired ``TOOL=MAJOR`` form is refused and changes
    nothing shared."""
    project = tmp_path / "capability-project"
    project.mkdir()
    def invoke(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(built_pex), "project", "--path", str(project), *arguments],
                              cwd=project, env=environment, text=True, capture_output=True, check=False)
    created = invoke("init", "--require", "python",
                     "--offer", "browser-automation", "--creator", "mailto:fixture@example.test")
    assert created.returncode == 0, created.stderr
    directory = project / ".devcapsule"
    shared = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert invoke("config", "ide", "python-ide").returncode == 0
    assert invoke("config", "omit", "browser-automation").returncode == 0
    chosen = invoke("config", "add", "codex-agent")
    assert chosen.returncode == 0, chosen.stderr
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == shared
    # The base channel is a home decision since 0.3.0 rc4: until it is
    # trusted, or the base consented to per checkout, 'check' reports it as
    # pending with status 3. The trust record lives in the named home of
    # this test, so accepting it here touches nothing shared.
    pending = invoke("config", "check")
    assert pending.returncode == 3 and "trust accept devcapsule-base" in pending.stderr, pending.stdout
    trusted = subprocess.run([str(built_pex), "home", "trust", "accept", "devcapsule-base", "--yes"],
                             cwd=tmp_path, env=environment, text=True, capture_output=True, check=False)
    assert trusted.returncode == 0, trusted.stderr
    checked = invoke("config", "check")
    assert checked.returncode == 0 and "contract valid" in checked.stdout, checked.stderr
    # The retired TOOL=MAJOR syntax is no longer a capability name. Reject it
    # without changing the shared policy.
    refused = invoke("config", "require", "python=4")
    assert refused.returncode == 2 and "Unsupported requirement form 'python=4'; use NAME or NAME>=VERSION" in refused.stderr
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == shared


def test_built_pex_carries_force_for_a_required_ide_to_the_launch_review(
    built_pex: Path, tmp_path: Path, environment: dict[str, str],
) -> None:
    """``run --ide IDE --force`` reaches preparation through the built executable; the refusals name it.

    The forced launch itself materializes the requested IDE, which needs the
    network and Docker; the unit tests prove the plan, the IDE smoke the launch.
    """
    project = tmp_path / "required-ide"
    project.mkdir()
    def invoke(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(built_pex), "project", "--path", str(project), *arguments],
                              cwd=project, env=environment, text=True, capture_output=True, check=False)
    created = invoke("init", "--require", "python", "--require", "python-ide", "--ide", "python-ide",
                     "--creator", "mailto:fixture@example.test", "--authorize", "base-image", "default")
    assert created.returncode == 0, created.stderr
    records = sorted((tmp_path / "devcapsule-home").rglob("*.toml"))
    assert records, "init registers the checkout and derives its resolution"
    before = {path: path.read_bytes() for path in (*records, *sorted((project / ".devcapsule").iterdir()))}
    helped = invoke("run", "--help")
    assert helped.returncode == 0 and "--force" in helped.stdout and "--force-config" not in helped.stdout
    refused = invoke("run", "--ide", "codium", "--print-command")
    assert refused.returncode == 2, refused.stdout
    assert "The project requires python-ide (pycharm); frontend-ide (codium) is another IDE" in refused.stderr
    assert f"--path {project} run --ide codium --force" in refused.stderr
    nothing = invoke("run", "--force", "--print-command")
    assert nothing.returncode == 2 and "--force names no departure" in nothing.stderr
    same = invoke("run", "--ide", "pycharm", "--force", "--print-command")
    assert same.returncode == 2 and "nothing to set aside: python-ide is the project's required IDE" in same.stderr
    saved = invoke("run", "--ide", "codium", "--force", "--save", "--print-command")
    assert saved.returncode == 2 and "cannot be combined with --save" in saved.stderr
    assert {path: path.read_bytes() for path in before} == before, "no refusal writes anything"
