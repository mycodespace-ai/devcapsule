"""Export the portable authoring kit and form console links from explicit inputs.

Public operations: kit export, direct and project skill installation, and console links.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

__all__ = ["export_tools", "install_skill", "install_project_skills", "SkillInstallReport", "presentation_link"]

PROJECT_SKILL_DIRECTORIES = (
    Path(".agents/skills/devcapsule-recorded-e2e"),
    Path(".claude/skills/devcapsule-recorded-e2e"),
)

KIT_ASSETS = ("__init__.py", "producer.py", "recording.py", "README.md", "example.py", "SKILL.md")


@dataclass(frozen=True)
class SkillInstallReport:
    created: tuple[Path, ...]
    preserved: tuple[Path, ...]


def install_project_skills(project: Path, assets: Mapping[str, bytes], *, version: str) -> SkillInstallReport:
    """Install a complete, versioned kit at both discovery locations; preserve existing folders."""
    missing = set(KIT_ASSETS) - assets.keys()
    if missing or any(Path(name).name != name or name in ("", ".", "..") for name in assets):
        raise ValueError("the recording kit requires all packaged assets with simple filenames")
    created: list[Path] = []
    preserved: list[Path] = []
    for relative in PROJECT_SKILL_DIRECTORIES:
        destination = project / relative
        # Do not follow a project's shared skill-directory symlink and write
        # outside this project; its owner manages that location independently.
        if destination.exists() or any((project / part).is_symlink() for part in (relative, *relative.parents)):
            preserved.append(relative)
            continue
        export_tools(destination, {name: data for name, data in assets.items() if name != "SKILL.md"})
        (destination / "SKILL.md").write_bytes(assets["SKILL.md"])
        (destination / "kit-version.json").write_text(
            json.dumps({"package": "devcapsule", "version": version}, indent=2) + "\n", encoding="utf-8",
        )
        created.append(relative / "SKILL.md")
    return SkillInstallReport(tuple(created), tuple(preserved))


def install_skill(destination: Path, content: bytes) -> Path:
    """Install the skill in a new folder without replacing an existing installation."""
    destination.mkdir(parents=True, exist_ok=False)
    skill = destination / "SKILL.md"
    skill.write_bytes(content)
    return skill


def export_tools(destination: Path, assets: Mapping[str, bytes]) -> Path:
    """Create a new directory with the supplied kit; never overwrite a prior kit."""
    if any(Path(name).name != name or name in ("", ".", "..") for name in assets):
        raise ValueError("kit assets must be simple filenames")
    destination.mkdir(parents=True, exist_ok=False)
    package = destination / "presentation_tools"
    package.mkdir()
    for name, data in assets.items():
        (package / name).write_bytes(data)
    return package


def presentation_link(folder: Path, *, project: Path, console_url: str, token: str) -> str:
    """Link a visible descendant of the console project, preserving no URL query.

    Paths are absolute and resolved by the caller. The token is optional; without
    it the user's browser must already have a console session. Never save a tokened
    link in the evidence or project records.
    """
    relative = folder.relative_to(project)
    if not project.is_absolute() or not relative.parts or any(
        part in ("..", "node_modules") or part.startswith(".") for part in relative.parts
    ):
        raise ValueError("presentation must be in a visible subdirectory of the console project")
    if not console_url or any(ch.isspace() for ch in console_url):
        raise ValueError("supply the capsule's HTTP(S) console URL")
    origin = urlsplit(console_url)
    try:
        _ = origin.port
    except ValueError as error:
        raise ValueError("supply the capsule's HTTP(S) console URL") from error
    if (origin.scheme not in ("http", "https") or not origin.hostname
            or origin.username is not None or origin.password is not None):
        raise ValueError("supply the capsule's HTTP(S) console URL")
    path = "/presentations/" + quote(relative.as_posix(), safe="/")
    return urlunsplit((origin.scheme, origin.netloc, path, urlencode({"token": token}) if token else "", ""))
