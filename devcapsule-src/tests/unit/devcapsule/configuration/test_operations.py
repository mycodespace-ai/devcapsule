"""Unit tests of ``devcapsule/configuration/operations.py``: which platform's lock ``project init`` writes.

Each test initializes a project under ``tmp_path`` without an IDE, so nothing resolves or reaches
Docker, and names its host with ``on_host`` where it is not the suite's amd64 Linux.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.operations import InitializeRequest, initialize_project
from devcapsule.configuration.storage import load_toml
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES
from tests.unit.devcapsule.test_platforms import on_host

CREATOR = "owner@example.test"


def locks_of(project: Path) -> list[str]:
    return sorted(path.name for path in (project / ".devcapsule").glob("*.lock"))


def init_answering(project: Path, answers: str) -> str:
    """Run an interactive init of ``project``, answering its questions in turn; return what it asked."""
    asked = io.StringIO()
    initialize_project(InitializeRequest(directory=project, creator=CREATOR, interactive=True),
                       input_stream=io.StringIO(answers), output_stream=asked)
    return asked.getvalue()


@pytest.fixture
def amd64_project_on_apple_silicon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project initialized for linux-amd64 on an Apple Silicon host."""
    on_host(monkeypatch, "Darwin", "arm64")
    project = tmp_path / "project"
    project.mkdir()
    initialize_project(InitializeRequest(directory=project, creator=CREATOR, platform=Platform.LINUX_AMD64,
                                         interactive=False))
    return project


@pytest.mark.own_host_patches
def test_init_platform_adds_that_lock_beside_the_projects_other(amd64_project_on_apple_silicon: Path) -> None:
    """Init with a platform writes that platform's lock beside the project's existing one, with that platform's base."""
    initialize_project(InitializeRequest(directory=amd64_project_on_apple_silicon, platform=Platform.LINUX_ARM64,
                                         interactive=False))
    assert locks_of(amd64_project_on_apple_silicon) == ["devcapsule.linux-amd64.lock", "devcapsule.linux-arm64.lock"]
    arm64_lock = load_toml(amd64_project_on_apple_silicon / ".devcapsule" / "devcapsule.linux-arm64.lock")
    (arm64_base,) = MATRICES[Platform.LINUX_ARM64].base_images()
    assert arm64_lock["base"]["reference"] == arm64_base.reference


@pytest.mark.own_host_patches
def test_init_refuses_a_lock_the_project_would_not_run_as(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Init completes the checkout for the lock it writes, so it refuses a lock of a platform the project
    would not run as on this host, and writes nothing."""
    on_host(monkeypatch, "Darwin", "arm64")
    project = tmp_path / "project"
    project.mkdir()
    initialize_project(InitializeRequest(directory=project, creator=CREATOR, platform=Platform.LINUX_ARM64,
                                         interactive=False))
    with pytest.raises(ProjectConfigurationError, match="runs as linux-arm64"):
        initialize_project(InitializeRequest(directory=project, platform=Platform.LINUX_AMD64, interactive=False))
    assert locks_of(project) == ["devcapsule.linux-arm64.lock"]


@pytest.mark.own_host_patches
@pytest.mark.parametrize("answer,expected", [("", "linux-arm64"), ("linux-amd64", "linux-amd64")])
def test_init_asks_a_host_of_two_platforms_the_native_one_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str, expected: str,
) -> None:
    """On a host of two platforms, init asks which a new project is for, the native one by default."""
    on_host(monkeypatch, "Darwin", "arm64")
    project = tmp_path / "project"
    project.mkdir()
    asked = init_answering(project, f"{answer}\n" + "\n" * 8)
    assert "Capsule platform for this project: linux-arm64 (native) or linux-amd64 (emulated) [linux-arm64]:" in asked
    assert locks_of(project) == [f"devcapsule.{expected}.lock"]


@pytest.mark.own_host_patches
def test_init_keeps_the_platform_of_a_lock_the_host_runs_without_asking(amd64_project_on_apple_silicon: Path) -> None:
    """Init of a project with a lock this host runs asks no platform and writes no other lock."""
    assert "Capsule platform" not in init_answering(amd64_project_on_apple_silicon, "\n" * 8)
    assert locks_of(amd64_project_on_apple_silicon) == ["devcapsule.linux-amd64.lock"]


def test_a_host_of_one_platform_is_not_asked(tmp_path: Path) -> None:
    """On a host of one platform, init asks no platform and locks the project for it."""
    project = tmp_path / "project"
    project.mkdir()
    assert "Capsule platform" not in init_answering(project, "\n" * 8)
    assert locks_of(project) == ["devcapsule.linux-amd64.lock"]
