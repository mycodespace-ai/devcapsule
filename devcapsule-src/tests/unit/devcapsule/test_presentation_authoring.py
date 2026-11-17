"""Export and hand-off contracts independent of the installed capsule."""
import json
from pathlib import Path

import pytest

from devcapsule.presentation_authoring import KIT_ASSETS, export_tools, install_project_skills, install_skill, presentation_link


def kit() -> dict[str, bytes]:
    return {name: f"packaged {name}".encode() for name in KIT_ASSETS}


def test_project_install_supplies_both_discovery_locations(tmp_path: Path) -> None:
    """Project setup supplies the same skill for Codex/Antigravity and Claude Code."""
    report = install_project_skills(tmp_path, kit(), version="test-build")

    expected = (
        Path(".agents/skills/devcapsule-recorded-e2e/SKILL.md"),
        Path(".claude/skills/devcapsule-recorded-e2e/SKILL.md"),
    )
    assert report.created == expected
    assert report.preserved == ()
    assert all((tmp_path / path).read_bytes() == kit()["SKILL.md"] for path in expected)
    for skill in expected:
        directory = tmp_path / skill.parent
        assert json.loads((directory / "kit-version.json").read_text()) == {
            "package": "devcapsule", "version": "test-build",
        }
        assert {p.name: p.read_bytes() for p in (directory / "presentation_tools").iterdir()} == {
            name: data for name, data in kit().items() if name != "SKILL.md"
        }


def test_project_install_preserves_custom_skill_and_adds_missing_copy(tmp_path: Path) -> None:
    """An existing customized skill is kept while the other agent receives its missing copy."""
    existing = Path(".agents/skills/devcapsule-recorded-e2e")
    (tmp_path / existing).mkdir(parents=True)
    skill = tmp_path / existing / "SKILL.md"
    skill.write_bytes(b"local instructions")

    report = install_project_skills(tmp_path, kit(), version="test-build")

    assert report.preserved == (existing,)
    assert report.created == (Path(".claude/skills/devcapsule-recorded-e2e/SKILL.md"),)
    assert skill.read_bytes() == b"local instructions"
    assert list(skill.parent.iterdir()) == [skill]


def test_project_install_preserves_linked_skill_root(tmp_path: Path) -> None:
    """Automatic setup never writes into a shared skills location outside the project."""
    project = tmp_path / "project"
    project.mkdir()
    shared = tmp_path / "shared"
    shared.mkdir()
    (project / ".agents").symlink_to(shared, target_is_directory=True)

    report = install_project_skills(project, kit(), version="test-build")

    assert report.preserved == (Path(".agents/skills/devcapsule-recorded-e2e"),)
    assert list(shared.iterdir()) == []


def test_install_skill_creates_parents_and_preserves_content(tmp_path: Path) -> None:
    """A fresh project receives only the supplied skill in the requested nested folder."""
    destination = tmp_path / ".agents" / "skills" / "devcapsule-recorded-e2e"
    content = b"---\nname: devcapsule-recorded-e2e\n---\nRead the installed guide.\n"

    skill = install_skill(destination, content)

    assert skill == destination / "SKILL.md"
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == {"SKILL.md": content}


def test_install_skill_preserves_an_existing_installation(tmp_path: Path) -> None:
    """Reinstallation refuses an existing directory and preserves the engineer's edits."""
    skill = tmp_path / "SKILL.md"
    skill.write_bytes(b"engineer's instructions")

    with pytest.raises(FileExistsError):
        install_skill(tmp_path, b"replacement")

    assert skill.read_bytes() == b"engineer's instructions"


def test_install_skill_refuses_a_symlink_destination(tmp_path: Path) -> None:
    """A linked installation cannot redirect writes into another skill folder."""
    target = tmp_path / "other-skill"
    target.mkdir()
    destination = tmp_path / "linked-skill"
    destination.symlink_to(target, target_is_directory=True)

    with pytest.raises(FileExistsError):
        install_skill(destination, b"replacement")

    assert list(target.iterdir()) == []


def test_export_keeps_the_supplied_bytes(tmp_path: Path) -> None:
    """The kit preserves the supplied instructions and Python source verbatim."""
    assets = {"README.md": b"agent instructions\n", "recording.py": b"# recorder\n"}

    package = export_tools(tmp_path / "kit", assets)

    assert {file.name: file.read_bytes() for file in package.iterdir()} == assets


def test_export_refuses_an_existing_directory(tmp_path: Path) -> None:
    """An existing destination remains unchanged, including user-edited helpers."""
    existing = tmp_path / "README.md"
    existing.write_text("engineer's changes")

    with pytest.raises(FileExistsError):
        export_tools(tmp_path, {"README.md": b"replacement"})

    assert existing.read_text() == "engineer's changes"
    assert not (tmp_path / "presentation_tools").exists()


@pytest.mark.parametrize("name", ["../outside.py", "/absolute.py", ".", "nested/source.py"])
def test_export_refuses_asset_paths(tmp_path: Path, name: str) -> None:
    """Malformed asset names cannot write outside the package directory."""
    with pytest.raises(ValueError, match="filenames"):
        export_tools(tmp_path / "kit", {name: b"untrusted"})

    assert not (tmp_path / "kit").exists()


def test_link_encodes_folder_and_run_token() -> None:
    """The link addresses the project-relative folder and safely carries the token."""
    link = presentation_link(Path("/project/evidence/My run #1"), project=Path("/project"),
                             console_url="https://console.example:9443/?stale=query", token="a&b #")

    assert link == "https://console.example:9443/presentations/evidence/My%20run%20%231?token=a%26b+%23"


def test_link_without_token_uses_existing_browser_session() -> None:
    """No empty authentication query is added when the token is unavailable."""
    link = presentation_link(Path("/project/evidence/run"), project=Path("/project"),
                             console_url="http://localhost:8000", token="")

    assert link == "http://localhost:8000/presentations/evidence/run"


@pytest.mark.parametrize("folder", ["/outside/run", "/project", "/project/.hidden/run",
                                    "/project/node_modules/run", "/project/evidence/../run"])
def test_link_refuses_folders_the_console_cannot_list(folder: str) -> None:
    """A hand-off never knowingly points to a hidden, outside or ambiguous folder."""
    with pytest.raises(ValueError):
        presentation_link(Path(folder), project=Path("/project"),
                          console_url="http://localhost:8000", token="")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "file:///tmp",
        "https:///missing-host",
        "http://:8000",
        "http://@example.org",
        "http://localhost:bad",
        "http://localhost:8000 ",
        "https://user:secret@example.org",
    ],
)
def test_link_refuses_invalid_console_origins(url: str) -> None:
    """The console origin must be HTTP(S) and must not embed user credentials."""
    with pytest.raises(ValueError):
        presentation_link(Path("/project/evidence/run"), project=Path("/project"), console_url=url, token="")


@pytest.mark.parametrize("assets", [{"SKILL.md": b"incomplete"}, {**kit(), "../escape": b"outside"}])
def test_project_install_rejects_incomplete_or_unsafe_kit(tmp_path: Path, assets: dict[str, bytes]) -> None:
    """A bad kit is rejected before either agent location receives partial resources."""
    with pytest.raises(ValueError, match="all packaged assets"):
        install_project_skills(tmp_path, assets, version="test-build")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("version", ["", "   "])
def test_project_install_rejects_blank_version(tmp_path: Path, version: str) -> None:
    """An empty or whitespace-only version is rejected before writing either kit."""
    with pytest.raises(ValueError, match="non-empty version"):
        install_project_skills(tmp_path, kit(), version=version)
    assert list(tmp_path.iterdir()) == []


def test_project_install_succeeds_through_symlinked_project_root(tmp_path: Path) -> None:
    """A symlinked project root still receives both kits when its skill parents are not symlinks."""
    real_project = tmp_path / "real"
    real_project.mkdir()
    linked_project = tmp_path / "linked"
    linked_project.symlink_to(real_project, target_is_directory=True)

    report = install_project_skills(linked_project, kit(), version="test-build")

    assert report.created == (
        Path(".agents/skills/devcapsule-recorded-e2e/SKILL.md"),
        Path(".claude/skills/devcapsule-recorded-e2e/SKILL.md"),
    )
    assert report.preserved == ()
    assert all((real_project / path).is_file() for path in report.created)
