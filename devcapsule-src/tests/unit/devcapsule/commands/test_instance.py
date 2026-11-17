"""Unit tests for ``devcapsule.commands.instance``."""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.commands.instance import content_link


def test_filesystem_paths_always_select_files_and_resolve_from_cwd(tmp_path: Path) -> None:
    """Relative paths resolve from ``cwd``, always open Files, and percent-encode special characters."""
    project = tmp_path / "project"
    subdirectory = project / "evidence" / "My run #1"
    subdirectory.mkdir(parents=True)
    (subdirectory / "presentation.json").write_text("{}", encoding="utf-8")

    link = content_link(
        "My run #1",
        project=project,
        cwd=project / "evidence",
        console_url="http://127.0.0.1:8787",
        token="run-token",
    )

    assert link == "http://127.0.0.1:8787/files/evidence/My%20run%20%231?token=run-token"


def test_symlinked_project_root_is_resolved_for_valid_content(tmp_path: Path) -> None:
    """A symlinked ``project`` path resolves before checking containment of project content."""
    real_project = tmp_path / "real"
    real_project.mkdir()
    (real_project / "doc.md").write_text("hello", encoding="utf-8")
    symlink_project = tmp_path / "link"
    symlink_project.symlink_to(real_project, target_is_directory=True)

    link = content_link(
        "doc.md",
        project=symlink_project,
        cwd=symlink_project,
        console_url="http://127.0.0.1:8787",
        token="run-token",
    )

    assert link == "http://127.0.0.1:8787/files/doc.md?token=run-token"


@pytest.mark.parametrize("route", ["files", "records", "presentations"])
def test_current_console_urls_retain_viewer_fragment_and_replace_token(tmp_path: Path, route: str) -> None:
    """Same-origin HTTP(S) URLs retain their viewer and fragment while replacing any query token."""
    (tmp_path / "notes.md").write_text("hi", encoding="utf-8")

    link = content_link(
        f"HTTP://LOCALHOST:80/{route}/notes.md?token=stale#section-2",
        project=tmp_path,
        cwd=tmp_path,
        console_url="http://localhost",
        token="fresh-token",
    )

    assert link == f"http://localhost/{route}/notes.md?token=fresh-token#section-2"


@pytest.mark.parametrize(
    ("console_url", "target_url", "expected_prefix"),
    [
        ("http://localhost", "http://localhost:80/files/notes.md", "http://localhost"),
        ("http://localhost:80", "http://localhost/files/notes.md", "http://localhost:80"),
        ("https://localhost", "https://localhost:443/files/notes.md", "https://localhost"),
        ("https://localhost:443", "https://localhost/files/notes.md", "https://localhost:443"),
    ],
)
def test_omitted_and_explicit_default_ports_are_equivalent(
    tmp_path: Path, console_url: str, target_url: str, expected_prefix: str,
) -> None:
    """Omitted and explicit scheme-default ports (80/443) match as the same origin."""
    (tmp_path / "notes.md").write_text("hi", encoding="utf-8")

    link = content_link(target_url, project=tmp_path, cwd=tmp_path, console_url=console_url, token="run-token")

    assert link == f"{expected_prefix}/files/notes.md?token=run-token"


@pytest.mark.parametrize(
    ("console_url", "target_url"),
    [
        ("http://localhost", "http://localhost:0/files/notes.md"),
        ("http://localhost:80", "http://localhost:0/files/notes.md"),
        ("http://localhost:0", "http://localhost/files/notes.md"),
        ("http://localhost:0", "http://localhost:80/files/notes.md"),
        ("https://localhost", "https://localhost:0/files/notes.md"),
        ("https://localhost:443", "https://localhost:0/files/notes.md"),
        ("https://localhost:0", "https://localhost/files/notes.md"),
        ("https://localhost:0", "https://localhost:443/files/notes.md"),
    ],
)
def test_explicit_zero_port_is_rejected_against_omitted_or_default_port(
    tmp_path: Path, console_url: str, target_url: str,
) -> None:
    """Explicit port 0 never matches an omitted or scheme-default port in either direction."""
    (tmp_path / "notes.md").write_text("hi", encoding="utf-8")

    with pytest.raises(ValueError, match="current console origin"):
        content_link(target_url, project=tmp_path, cwd=tmp_path, console_url=console_url, token="run-token")


def test_empty_token_omits_query_parameter(tmp_path: Path) -> None:
    """An empty token omits the query string so the browser session cookie applies."""
    link = content_link(
        ".",
        project=tmp_path,
        cwd=tmp_path,
        console_url="https://console.example:443",
        token="",
    )

    assert link == "https://console.example:443/files"


@pytest.mark.parametrize(
    "console_url",
    ["", "file:///tmp", "http://localhost:bad", "http://user@127.0.0.1:8787", "http://127.0.0.1:8787\\bad"],
)
def test_invalid_console_url_is_refused(tmp_path: Path, console_url: str) -> None:
    """Missing or non-HTTP(S) or credentialed console origins raise ``ValueError``."""
    with pytest.raises(ValueError):
        content_link(".", project=tmp_path, cwd=tmp_path, console_url=console_url, token="run-token")


@pytest.mark.parametrize(
    "value",
    [
        "http://other.example/files",
        "http://127.0.0.1:9999/files",
        "http://user@127.0.0.1:8787/files",
        "//other.example/files",
        "http://127.0.0.1:8787/decisions",
        "http://127.0.0.1:8787/files/%2e%2e/outside",
        "http://127.0.0.1:8787/files/node_modules/pkg",
        "http://127.0.0.1:8787/files/.hidden",
        ".hidden",
        "node_modules",
        "../",
        "escape",
        "missing",
    ],
)
def test_invalid_targets_are_refused(tmp_path: Path, value: str) -> None:
    """External origins, unsupported viewers, hidden or escaping paths, and missing targets raise ``ValueError``."""
    (tmp_path / ".hidden").write_text("secret", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "escape").symlink_to(tmp_path.parent, target_is_directory=True)

    with pytest.raises(ValueError):
        content_link(
            value,
            project=tmp_path,
            cwd=tmp_path,
            console_url="http://127.0.0.1:8787",
            token="run-token",
        )
