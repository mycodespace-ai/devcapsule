"""Unit tests of ``devcapsule/configuration/storage.py``: which capsule platform a project runs as on a host, and the
admission of a settings file by its minimum launcher version.

Each test writes its project's lock files under ``tmp_path`` and names its host with ``on_host``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule import cli
from devcapsule.configuration import storage
from devcapsule.configuration.file_formats import ProjectConfigurationError
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


def test_minimum_refusal_precedes_content_and_command_diagnoses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A settings file whose minimum exceeds this launcher is refused before its schema or the command is
    judged: the refusal names the home, both versions and the organization's releases page, and the file
    stays untouched."""
    monkeypatch.setattr("importlib.metadata.version", lambda name: "0.3.0")
    monkeypatch.setenv("DEVCAPSULE_CONFIG_HOME", str(tmp_path))
    path = storage.settings_path()
    path.write_text('minimum-devcapsule = "9.0.0"\ndevcapsule-settings-schema-version = 2\ndefaults = false\n')
    before = path.read_bytes(), path.stat().st_mtime_ns
    assert cli.main(["project", "config", "default", "cpus", "2"]) == 2
    message = capsys.readouterr().err
    assert all(value in message for value in (str(tmp_path), "9.0.0", "0.3.0", "https://github.com/mycodespace-ai/devcapsule/releases"))
    assert "unsupported schema" not in message
    with pytest.raises(ProjectConfigurationError, match="requires DevCapsule 9.0.0"):
        storage.write_settings({"defaults": {"cpus": 2}})
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert list(tmp_path.iterdir()) == [path]
