"""Export and hand-off contracts independent of the installed capsule."""
from pathlib import Path

import pytest

from devcapsule.presentation_authoring import export_tools, presentation_link


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


@pytest.mark.parametrize("url", ["", "file:///tmp", "https:///missing-host", "https://user:secret@example.org"])
def test_link_refuses_invalid_console_origins(url: str) -> None:
    """The console origin must be HTTP(S) and must not embed user credentials."""
    with pytest.raises(ValueError):
        presentation_link(Path("/project/evidence/run"), project=Path("/project"), console_url=url, token="")
