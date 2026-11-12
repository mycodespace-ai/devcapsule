"""Unit tests of ``devcapsule/configuration/owner_commands.py`` on a project locked for two platforms.

Each test initializes its project under ``tmp_path`` on an Apple Silicon host the test sets up.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule import cli
from devcapsule.configuration import owner_commands
from devcapsule.configuration.capability_commands import paths, recover
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.storage import load_toml
from tests.unit.devcapsule.test_platforms import on_host


@pytest.fixture
def two_platform_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project on Apple Silicon with a linux-amd64 lock and a linux-arm64 lock added beside it."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    on_host(monkeypatch, "Darwin", "arm64")
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--platform", "linux-amd64", "--require", "python",
                     "--creator", "mailto:owner@example.test"]) == 0
    assert cli.main(["project", "--path", str(root), "init", "--platform", "linux-arm64"]) == 0
    return root


def _locked_components(root: Path) -> dict[str, set[str]]:
    return {path.name: set(load_toml(path).get("components", {}))
            for path in sorted((root / ".devcapsule").glob("devcapsule.*.lock"))}


@pytest.mark.own_host_patches
def test_an_owner_edit_regenerates_every_platform_lock(two_platform_project: Path, capsys) -> None:
    """An owner's edit of the shared policy regenerates every lock the project carries."""
    # Edited on the Mac, the committed linux-amd64 lock follows the manifest too.
    assert cli.main(["project", "--path", str(two_platform_project), "config", "require", "dotnet", "--unverified"]) == 0
    assert "the manifest and its locks are updated" in capsys.readouterr().out
    assert _locked_components(two_platform_project) == {
        "devcapsule.linux-amd64.lock": {"dotnet-sdk"}, "devcapsule.linux-arm64.lock": {"dotnet-sdk"},
    }


@pytest.mark.own_host_patches
def test_an_edit_one_lock_cannot_follow_changes_nothing(two_platform_project: Path) -> None:
    """An edit one platform's lock cannot follow is refused, naming that platform, and no file changes."""
    # The .NET SDK has no linux-arm64 validation yet; linux-amd64 alone would accept it.
    before = {path: path.read_bytes() for path in (two_platform_project / ".devcapsule").iterdir() if path.is_file()}
    with pytest.raises(ProjectConfigurationError, match="linux-arm64 lock cannot follow this edit"):
        owner_commands.require_tools(two_platform_project, ["dotnet"])
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.own_host_patches
@pytest.mark.parametrize("committed", [False, True])
def test_an_interrupted_edit_recovers_every_lock_to_one_side(two_platform_project: Path, committed: bool) -> None:
    """Recovery of an interrupted edit puts the manifest and every lock on the same side of the edit."""
    devcapsule = two_platform_project / ".devcapsule"
    manifest, locks = paths(two_platform_project)[0], sorted(devcapsule.glob("devcapsule.*.lock"))
    before = {path: path.read_text() for path in (manifest, *locks)}
    owner_commands.require_tools(two_platform_project, ["dotnet"], allow_unverified=True)
    after = {path: path.read_text() for path in (manifest, *locks)}
    assert all(before[path] != after[path] for path in locks)
    journal = {"before-manifest": before[manifest], "after-manifest": after[manifest],
               "before-locks": {path.name.split(".")[1]: before[path] for path in locks},
               "after-locks": {path.name.split(".")[1]: after[path] for path in locks}}
    paths(two_platform_project)[2].write_text(render_toml(journal))
    if not committed:
        manifest.write_text(before[manifest])
    locks[0].write_text(before[locks[0]])  # Interrupted between the two lock writes.
    recover(two_platform_project)
    expected = after if committed else before
    assert {path: path.read_text() for path in (manifest, *locks)} == expected
    assert not paths(two_platform_project)[2].exists()
