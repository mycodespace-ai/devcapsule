"""The Files page, the directory tree listing, and the hardened raw file route."""

from __future__ import annotations

import errno
import os
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
import pytest

from conftest import with_token
from devcapsule_webconsole.security import PathRefused, list_project_directory, open_project_file


def test_list_project_directory_lists_root_including_dotfiles_git_and_links(project: Path) -> None:
    """Listing the project root includes dotfiles, .git, directories, files and symbolic links without following links."""
    (project / ".git").mkdir()
    (project / ".env").write_text("KEY=1\n", encoding="utf-8")

    listing = list_project_directory(project)

    assert listing["path"] == ""
    by_name = {entry["name"]: entry for entry in listing["entries"]}
    assert [entry["name"] for entry in listing["entries"]] == [
        ".devcapsule",
        ".git",
        "docs",
        ".env",
        "escape.md",
        "image.bin",
    ]
    assert by_name[".git"]["kind"] == "directory"
    assert by_name[".git"]["size"] is None
    assert by_name[".env"] == {
        "name": ".env",
        "kind": "file",
        "size": 6,
        "modified": by_name[".env"]["modified"],
    }
    assert by_name["escape.md"]["kind"] == "link"
    assert by_name["escape.md"]["size"] is None


def test_list_project_directory_lists_nested_directory_with_sort_and_kinds(project: Path) -> None:
    """A nested directory listing sorts directories before other entries by case-folded name and classifies directories, files, links and FIFOs."""
    nested = project / "docs" / "nested"
    nested.mkdir()
    (nested / "Zeta").mkdir()
    (nested / "alpha").mkdir()
    beta = nested / "Beta.txt"
    beta.write_bytes(b"hello")
    os.utime(beta, (1794132672, 1794132672))
    (nested / "apple.txt").write_bytes(b"ab")
    (nested / "arrow").symlink_to("Beta.txt")
    (nested / "broken").symlink_to("does-not-exist")
    os.mkfifo(nested / "pipe")

    listing = list_project_directory(project, "docs/nested")

    assert listing["path"] == "docs/nested"
    assert [(entry["name"], entry["kind"], entry["size"]) for entry in listing["entries"]] == [
        ("alpha", "directory", None),
        ("Zeta", "directory", None),
        ("apple.txt", "file", 2),
        ("arrow", "link", None),
        ("Beta.txt", "file", 5),
        ("broken", "link", None),
        ("pipe", "other", None),
    ]
    by_name = {entry["name"]: entry for entry in listing["entries"]}
    assert by_name["Beta.txt"]["modified"] == "2026-11-08T10:11:12Z"


def test_list_project_directory_skips_an_entry_removed_during_scan(
    project: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An entry unlinked between readdir and lstat is skipped without failing the directory listing."""
    vanished = project / "docs" / "transient.tmp"
    vanished.write_text("ephemeral", encoding="utf-8")
    real_scandir = os.scandir

    class VanishingScan:
        def __init__(self, target_fd: int) -> None:
            self._inner = real_scandir(target_fd)

        def __enter__(self) -> list[object]:
            entries = list(self._inner.__enter__())
            vanished.unlink()
            return entries

        def __exit__(self, *exc: object) -> bool | None:
            return self._inner.__exit__(*exc)

    monkeypatch.setattr(os, "scandir", VanishingScan)

    listing = list_project_directory(project, "docs")

    assert [entry["name"] for entry in listing["entries"]] == ["guide.md"]


@pytest.mark.parametrize(
    "requested",
    ["../outside", "docs/../../outside", "/etc", "escape-dir", "docs/\x00sub"],
)
def test_list_project_directory_refuses_paths_that_escape_the_project(project: Path, requested: str) -> None:
    """Paths with parent traversal, absolute roots, NUL bytes or symbolic links leaving the project raise PathRefused."""
    outside_dir = project.parent / "outside-dir"
    outside_dir.mkdir(exist_ok=True)
    (project / "escape-dir").symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(PathRefused):
        list_project_directory(project, requested)


@pytest.mark.parametrize(
    ("requested", "expected_error"),
    [
        ("docs/missing", FileNotFoundError),
        ("docs/guide.md", NotADirectoryError),
        ("docs/guide.md/child", FileNotFoundError),
    ],
)
def test_list_project_directory_rejects_missing_or_file_paths(
    project: Path, requested: str, expected_error: type[OSError],
) -> None:
    """Listing a missing path raises FileNotFoundError and listing a regular file raises NotADirectoryError."""
    with pytest.raises(expected_error):
        list_project_directory(project, requested)


@pytest.mark.parametrize("swap_parent", [False, True])
def test_list_project_directory_refuses_a_directory_swapped_for_a_link_after_confinement(
    project: Path, monkeypatch: pytest.MonkeyPatch, swap_parent: bool,
) -> None:
    """Replacing a confined directory with an escaping symbolic link before descriptor open raises PathRefused."""
    outside = project.parent / "outside-tree"
    outside.mkdir()
    (outside / "secret.txt").write_text("outside secret", encoding="utf-8")
    target = project / "docs" / "sub"
    target.mkdir()
    resolve = Path.resolve
    swapped = False

    def resolve_then_swap(path: Path, *args: object, **kwargs: object) -> Path:
        nonlocal swapped
        resolved = resolve(path, *args, **kwargs)  # type: ignore[arg-type]
        if path == target and not swapped:
            swapped = True
            victim = target.parent if swap_parent else target
            victim.rename(project / "displaced")
            victim.symlink_to(outside, target_is_directory=True)
        return resolved

    monkeypatch.setattr(Path, "resolve", resolve_then_swap)

    with pytest.raises(PathRefused):
        list_project_directory(project, "docs/sub")
    assert swapped


def test_open_project_file_streams_bytes_and_closes_its_descriptor(project: Path) -> None:
    """open_project_file yields a seekable binary stream with the file's byte length and closes the descriptor on exit."""
    payload = b"0123456789abcdef" * 4
    (project / "docs" / "sample.bin").write_bytes(payload)

    with open_project_file(project, "docs/sample.bin") as (stream, size):
        descriptor = stream.fileno()
        assert size == len(payload)
        stream.seek(10)
        chunk = stream.read(12)

    assert chunk == payload[10:22]
    with pytest.raises(OSError) as closed:
        os.fstat(descriptor)
    assert closed.value.errno == errno.EBADF


@pytest.mark.parametrize(
    ("params", "expected_path", "expected_names"),
    [
        (None, "", [".devcapsule", "docs", "escape.md", "image.bin"]),
        ({"path": ""}, "", [".devcapsule", "docs", "escape.md", "image.bin"]),
        ({"path": "docs"}, "docs", ["guide.md"]),
    ],
)
def test_tree_route_serves_root_and_nested_listings(
    client: TestClient, params: dict[str, str] | None, expected_path: str, expected_names: list[str],
) -> None:
    """GET /api/project/tree lists the project root when path is absent or empty and a subdirectory when named."""
    response = with_token(client).get("/api/project/tree", params=params)

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == expected_path
    assert [entry["name"] for entry in body["entries"]] == expected_names


@pytest.mark.parametrize(
    ("requested", "expected_status"),
    [
        ("../outside.txt", 403),
        ("/etc/passwd", 403),
        ("escape.md", 403),
        ("docs/missing", 404),
        ("docs/guide.md", 404),
    ],
)
def test_tree_route_refuses_escapes_and_reports_missing_or_file_paths(
    client: TestClient, requested: str, expected_status: int,
) -> None:
    """GET /api/project/tree returns 403 for escaping paths and 404 when the path is missing or names a file."""
    response = with_token(client).get("/api/project/tree", params={"path": requested})

    assert response.status_code == expected_status


def test_tree_route_reports_permission_errors_with_403(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/project/tree returns 403 without leaking host details when reading the directory fails with PermissionError."""
    def denied(_target: int) -> object:
        raise PermissionError("private host detail")

    monkeypatch.setattr(os, "scandir", denied)

    response = with_token(client).get("/api/project/tree", params={"path": "docs"})

    assert response.status_code == 403
    assert response.text == "cannot read 'docs' in the project\n"


@pytest.mark.parametrize(
    "route",
    [
        "/files",
        "/files/",
        "/files/docs",
        "/files/engineering-docs/blog/assets/2026-10-21-eclipse-debug/eclipse-hello-time-debug.webm",
    ],
)
def test_files_routes_serve_the_files_page(client: TestClient, route: str) -> None:
    """GET /files and GET /files/<path> serve files.html behind the token gate."""
    response = with_token(client).get(route)

    assert response.status_code == 200
    assert 'data-page="files"' in response.text


@pytest.mark.parametrize(
    ("route", "expected_location"),
    [
        ("/filetree", "/files"),
        ("/filetree/", "/files"),
        ("/filetree/docs", "/files/docs"),
        ("/filetree/docs/sub%20dir", "/files/docs/sub%20dir"),
        ("/filetree///evil.example", "/files/evil.example"),
    ],
)
def test_filetree_routes_redirect_with_307_to_files(
    client: TestClient, route: str, expected_location: str,
) -> None:
    """GET /filetree and GET /filetree/<path> redirect with 307 to the /files URL on the same origin."""
    response = with_token(client).get(route, follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_every_page_navigation_includes_files_after_records(client: TestClient) -> None:
    """Every console page places Files after Records in the navigation bar, and Home includes a Files card."""
    authed = with_token(client)
    home = authed.get("/").text
    assert home.count('href="/files"') == 2
    for route in ("/", "/configuration", "/versions", "/project", "/processes", "/records", "/files", "/decisions", "/notifications"):
        html = authed.get(route).text
        assert '<a href="/records">Records</a><a href="/files">Files</a>' in html


def test_files_script_behaviour() -> None:
    """The files page script renders breadcrumbs, directory and file links, sizes, empty notices, file redirects and failures."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is a development-only script test dependency")
    subprocess.run([node, str(Path(__file__).with_name("files-script.cjs"))], check=True)

