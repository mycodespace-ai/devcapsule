"""Unit tests of ``devcapsule/configuration/storage.py``: which capsule platform a project runs as on a host, the
admission of a settings file by its minimum launcher version, and the document a settings write merges onto.

Each test writes its project's lock files under ``tmp_path`` and names its host with ``on_host``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule import cli
from devcapsule.configuration import storage
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.storage import load_toml, locked_platforms, project_platform, settings_path, write_settings
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


def named_home(directory: Path) -> dict[str, str]:
    """The environment of a process whose DevCapsule home is named: ``directory / "home"``, which does not exist yet."""
    return {"DEVCAPSULE_CONFIG_HOME": str(directory / "home"), "HOME": str(directory)}


def test_a_settings_write_merges_onto_the_document_it_is_given(tmp_path: Path) -> None:
    """``write_settings`` given the home's current settings writes those with the changed table laid over them,
    and does not read the home's file: a table that only the file holds is not in the result."""
    env = named_home(tmp_path)
    write_settings({"defaults": {"cpus": 4}}, env)
    held = {key: value for key, value in load_toml(settings_path(env)).items() if key != "defaults"}

    write_settings({"trust": {"channels": {}}}, env, current=held)

    assert load_toml(settings_path(env)) == {**held, "trust": {"channels": {}}}


def test_a_settings_write_onto_an_empty_document_starts_a_new_file(tmp_path: Path) -> None:
    """Given an empty current document, the write creates the home's file with the changed table and the two
    header fields a settings file carries."""
    env = named_home(tmp_path)

    path = write_settings({"defaults": {"cpus": 2}}, env, current={})

    written = load_toml(path)
    assert path == settings_path(env)
    assert written["defaults"] == {"cpus": 2}
    assert set(written) == {"defaults", "devcapsule-settings-schema-version", "minimum-devcapsule"}


def test_a_settings_write_that_changes_nothing_of_the_given_document_writes_no_file(tmp_path: Path) -> None:
    """When the changed table equals the one in the current document given, nothing is written, although the
    home has no file."""
    env = named_home(tmp_path)
    write_settings({"defaults": {"cpus": 2}}, env)
    held = load_toml(settings_path(env))
    settings_path(env).unlink()

    write_settings({"defaults": {"cpus": 2}}, env, current=held)

    assert not settings_path(env).exists()
