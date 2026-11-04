"""Unit tests of ``devcapsule/configuration/storage.py``: which capsule platform a project runs as on a host.

Each test writes its project's lock files under ``tmp_path`` and names its host with ``on_host``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.configuration.storage import locked_platforms, project_platform
from devcapsule.platforms import Platform
from tests.unit.devcapsule.test_platforms import on_host


def project_locked_for(root: Path, *platforms: str) -> Path:
    """A project directory at ``root`` with an empty lock file for each of ``platforms``."""
    (root / ".devcapsule").mkdir(parents=True)
    for platform in platforms:
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
    """Apple Silicon runs a project natively when it has an arm64 lock, else as its amd64 lock under
    emulation; a project without a lock runs as the native platform."""
    on_host(monkeypatch, "Darwin", "arm64")
    assert project_platform(project_locked_for(tmp_path / "project", *locked)) is Platform.parse(expected)


@pytest.mark.own_host_patches
def test_a_host_runs_a_project_only_as_a_platform_it_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An amd64 Linux host runs an arm64-only project as its own platform; reading that lock reports it missing."""
    on_host(monkeypatch, "Linux", "x86_64")
    assert project_platform(project_locked_for(tmp_path / "project", "linux-arm64")) is Platform.LINUX_AMD64


def test_locked_platforms_names_every_lock_on_any_host(tmp_path: Path) -> None:
    """A project's locked platforms are all those it has a lock for, including ones this host cannot run."""
    project = project_locked_for(tmp_path / "project", "linux-arm64", "linux-amd64")
    assert locked_platforms(project) == (Platform.LINUX_AMD64, Platform.LINUX_ARM64)
