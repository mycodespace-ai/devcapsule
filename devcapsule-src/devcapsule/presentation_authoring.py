"""Export the portable authoring kit and form console links from explicit inputs.

Public operations: ``export_tools`` and ``presentation_link``.
"""
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

__all__ = ["export_tools", "presentation_link"]


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
