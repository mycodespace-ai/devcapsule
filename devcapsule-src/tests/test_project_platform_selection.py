"""The capsule platform a project runs as: the first one this host runs that it has a lock for."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from devcapsule import cli
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.operations import InitializeRequest, initialize_project
from devcapsule.configuration.storage import load_toml, project_platform
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES
from tests.test_platforms import on_host


def _project(root: Path, *locked: str) -> Path:
    (root / ".devcapsule").mkdir(parents=True)
    (root / ".devcapsule" / "devcapsule.toml").write_text("")
    for platform in locked:
        (root / ".devcapsule" / f"devcapsule.{platform}.lock").write_text("")
    return root


@pytest.mark.own_host_patches
@pytest.mark.parametrize("locked,expected", [
    ((), "linux-arm64"),
    (("linux-amd64",), "linux-amd64"),
    (("linux-arm64",), "linux-arm64"),
    (("linux-amd64", "linux-arm64"), "linux-arm64"),
])
def test_apple_silicon_runs_a_project_as_the_platform_it_is_locked_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, locked: tuple[str, ...], expected: str,
) -> None:
    # Natively when the project has an arm64 lock, else its amd64 lock under
    # emulation; a project without a lock is created for the native platform.
    on_host(monkeypatch, "Darwin", "arm64")
    assert project_platform(_project(tmp_path / "project", *locked)) is Platform.parse(expected)


@pytest.mark.own_host_patches
def test_a_host_runs_a_project_only_as_a_platform_it_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # An amd64 Linux host cannot run an arm64-only project; it keeps its own
    # platform, and the missing lock is reported where the lock is read.
    on_host(monkeypatch, "Linux", "x86_64")
    assert project_platform(_project(tmp_path / "project", "linux-arm64")) is Platform.LINUX_AMD64


@pytest.mark.own_host_patches
def test_init_platform_adds_that_lock_and_the_project_runs_as_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    on_host(monkeypatch, "Darwin", "arm64")
    project = tmp_path / "project"
    project.mkdir()
    initialize_project(InitializeRequest(directory=project, creator="owner@example.test",
                                         platform=Platform.LINUX_AMD64, interactive=False))
    initialize_project(InitializeRequest(directory=project, platform=Platform.LINUX_ARM64, interactive=False))
    locks = sorted(path.name for path in (project / ".devcapsule").glob("*.lock"))
    assert locks == ["devcapsule.linux-amd64.lock", "devcapsule.linux-arm64.lock"]
    arm64_lock = load_toml(project / ".devcapsule" / "devcapsule.linux-arm64.lock")
    assert MATRICES[Platform.LINUX_ARM64].base_unpublished(arm64_lock["base"]["reference"])
    assert project_platform(project) is Platform.LINUX_ARM64


@pytest.mark.own_host_patches
def test_init_refuses_a_lock_the_project_would_not_run_as(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Init completes the checkout for the lock it writes; with an arm64 lock
    # the project runs as arm64 here, so an amd64 lock cannot be added here.
    on_host(monkeypatch, "Darwin", "arm64")
    project = _project(tmp_path / "project", "linux-arm64")
    with pytest.raises(ProjectConfigurationError, match="runs as linux-arm64"):
        initialize_project(InitializeRequest(directory=project, platform=Platform.LINUX_AMD64, interactive=False))
    assert not (project / ".devcapsule" / "devcapsule.linux-amd64.lock").exists()


def test_init_platform_refuses_a_platform_this_host_cannot_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    # The suite's host runs linux-amd64 only.
    project = _project(tmp_path / "project", "linux-amd64")
    assert cli.main(["project", "--path", str(project), "init", "--platform", "linux-arm64"]) != 0
    assert "this host runs linux-amd64 capsules, not linux-arm64" in capsys.readouterr().err
    assert cli.main(["project", "--path", str(project), "init", "--platform", "windows-amd64"]) != 0
    assert "Unsupported platform 'windows-amd64'" in capsys.readouterr().err


def _init_answering(project: Path, answers: str) -> str:
    """Run an interactive init of ``project``, answering each question in turn; return what it asked."""
    asked = io.StringIO()
    initialize_project(
        InitializeRequest(directory=project, creator="owner@example.test", interactive=True),
        input_stream=io.StringIO(answers), output_stream=asked,
    )
    return asked.getvalue()


@pytest.mark.own_host_patches
@pytest.mark.parametrize("answer,expected", [("", "linux-arm64"), ("linux-amd64", "linux-amd64")])
def test_init_asks_a_host_of_two_platforms_the_native_one_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str, expected: str,
) -> None:
    on_host(monkeypatch, "Darwin", "arm64")
    project = tmp_path / "project"
    project.mkdir()
    asked = _init_answering(project, f"{answer}\n" + "\n" * 8)
    assert ("Capsule platform for this project: linux-arm64 (native; its base is built locally) "
            "or linux-amd64 (emulated) [linux-arm64]:") in asked
    assert [path.name for path in (project / ".devcapsule").glob("*.lock")] == [f"devcapsule.{expected}.lock"]


@pytest.mark.own_host_patches
def test_init_keeps_the_platform_of_a_lock_the_host_runs_without_asking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    on_host(monkeypatch, "Darwin", "arm64")
    project = tmp_path / "project"
    project.mkdir()
    initialize_project(InitializeRequest(directory=project, creator="owner@example.test",
                                         platform=Platform.LINUX_AMD64, interactive=False))
    assert "Capsule platform" not in _init_answering(project, "\n" * 8)
    assert [path.name for path in (project / ".devcapsule").glob("*.lock")] == ["devcapsule.linux-amd64.lock"]


def test_a_host_of_one_platform_is_not_asked(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    assert "Capsule platform" not in _init_answering(project, "\n" * 8)
    assert (project / ".devcapsule" / "devcapsule.linux-amd64.lock").is_file()

