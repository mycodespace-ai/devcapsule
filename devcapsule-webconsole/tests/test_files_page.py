"""The Files page, the directory tree listing, and the hardened raw file route."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import errno
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
from typing import BinaryIO

from fastapi.testclient import TestClient
import pytest

from conftest import with_token
from devcapsule_webconsole import app as console_app
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


def test_raw_route_serves_full_file_in_chunks_with_accept_ranges(
    client: TestClient, project: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/project/raw streams the file in bounded chunks and advertises Accept-Ranges on 200."""
    payload = bytes(index % 251 for index in range(160 * 1024))
    (project / "docs" / "clip.webm").write_bytes(payload)
    read_sizes: list[int] = []

    @contextmanager
    def observed_open(root: Path, requested: str) -> Iterator[tuple[BinaryIO, int]]:
        with open_project_file(root, requested) as (stream, size):
            class ObservedStream:
                def seek(self, offset: int) -> int:
                    return stream.seek(offset)

                def read(self, count: int = -1) -> bytes:
                    read_sizes.append(count)
                    return stream.read(count)

            yield ObservedStream(), size  # type: ignore[misc]

    monkeypatch.setattr(console_app, "open_project_file", observed_open)

    response = with_token(client).get("/api/project/raw", params={"path": "docs/clip.webm"})

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == str(len(payload))
    assert response.headers["content-security-policy"] == "sandbox; default-src 'none'; style-src 'unsafe-inline'"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-range" not in response.headers
    assert "content-disposition" not in response.headers
    assert len(read_sizes) == 3
    assert max(read_sizes) <= console_app.RAW_CHUNK_BYTES


@pytest.mark.parametrize(
    ("range_header", "expected_status", "expected_body", "expected_content_range"),
    [
        ("bytes=2-5", 206, b"2345", "bytes 2-5/10"),
        ("bytes=2-99", 206, b"23456789", "bytes 2-9/10"),
        ("bytes=6-", 206, b"6789", "bytes 6-9/10"),
        ("bytes=-4", 206, b"6789", "bytes 6-9/10"),
        ("bytes=-99", 206, b"0123456789", "bytes 0-9/10"),
        ("bytes=0-2, 6-8", 200, b"0123456789", None),
    ],
)
def test_raw_route_honours_single_byte_ranges_and_multi_range_fallback(
    client: TestClient,
    project: Path,
    range_header: str,
    expected_status: int,
    expected_body: bytes,
    expected_content_range: str | None,
) -> None:
    """GET /api/project/raw answers single byte ranges with 206 and multiple ranges with the full 200 body."""
    (project / "docs" / "digits.bin").write_bytes(b"0123456789")

    response = with_token(client).get(
        "/api/project/raw",
        params={"path": "docs/digits.bin"},
        headers={"Range": range_header},
    )

    assert response.status_code == expected_status
    assert response.content == expected_body
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == str(len(expected_body))
    assert response.headers["content-security-policy"] == "sandbox; default-src 'none'; style-src 'unsafe-inline'"
    assert response.headers["x-content-type-options"] == "nosniff"
    if expected_content_range is None:
        assert "content-range" not in response.headers
    else:
        assert response.headers["content-range"] == expected_content_range


@pytest.mark.parametrize(
    ("file_bytes", "range_header", "expected_content_range"),
    [
        (b"0123456789", "bytes=10-12", "bytes */10"),
        (b"0123456789", "bytes=10-", "bytes */10"),
        (b"0123456789", "bytes=5-2", "bytes */10"),
        (b"0123456789", "bytes=-0", "bytes */10"),
        (b"0123456789", "bytes=-", "bytes */10"),
        (b"0123456789", "bytes=invalid", "bytes */10"),
        (b"", "bytes=0-0", "bytes */0"),
    ],
)
def test_raw_route_rejects_unsatisfiable_ranges_with_416_and_isolation_headers(
    client: TestClient,
    project: Path,
    file_bytes: bytes,
    range_header: str,
    expected_content_range: str,
) -> None:
    """Unsatisfiable byte ranges return 416 with Content-Range bytes */<size> and keep sandbox and nosniff headers."""
    (project / "docs" / "bounded.bin").write_bytes(file_bytes)

    response = with_token(client).get(
        "/api/project/raw",
        params={"path": "docs/bounded.bin"},
        headers={"Range": range_header},
    )

    assert response.status_code == 416
    assert response.content == b""
    assert response.headers["content-range"] == expected_content_range
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-security-policy"] == "sandbox; default-src 'none'; style-src 'unsafe-inline'"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    ("filename", "download", "expected_disposition"),
    [
        ("guide.md", "1", "attachment; filename=\"guide.md\"; filename*=UTF-8''guide.md"),
        (
            'résumé "2026".txt',
            "1",
            "attachment; filename=\"r_sum_ _2026_.txt\"; filename*=UTF-8''r%C3%A9sum%C3%A9%20%222026%22.txt",
        ),
        ("guide.md", None, None),
        ("guide.md", "0", None),
    ],
)
def test_raw_route_adds_attachment_disposition_only_when_download_is_one(
    client: TestClient,
    project: Path,
    filename: str,
    download: str | None,
    expected_disposition: str | None,
) -> None:
    """download=1 adds Content-Disposition with an ASCII fallback and UTF-8 filename*, while omitting it leaves headers unchanged."""
    target = project / "docs" / filename
    target.write_text("content\n", encoding="utf-8")
    params = {"path": f"docs/{filename}"}
    if download is not None:
        params["download"] = download

    response = with_token(client).get("/api/project/raw", params=params)

    assert response.status_code == 200
    if expected_disposition is None:
        assert "content-disposition" not in response.headers
    else:
        assert response.headers["content-disposition"] == expected_disposition


@pytest.mark.parametrize(
    ("extension", "expected_media_type"),
    [
        (".webm", "video/webm"),
        (".mp4", "video/mp4"),
        (".mkv", "video/x-matroska"),
        (".mp3", "audio/mpeg"),
        (".ogg", "audio/ogg"),
        (".wav", "audio/wav"),
        (".pdf", "application/pdf"),
        (".webp", "image/webp"),
        (".gif", "image/gif"),
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".yaml", "text/plain; charset=utf-8"),
        (".yml", "text/plain; charset=utf-8"),
        (".lock", "text/plain; charset=utf-8"),
        (".cfg", "text/plain; charset=utf-8"),
        (".ini", "text/plain; charset=utf-8"),
        (".py", "text/plain; charset=utf-8"),
        (".js", "text/plain; charset=utf-8"),
        (".mjs", "text/plain; charset=utf-8"),
        (".cjs", "text/plain; charset=utf-8"),
        (".css", "text/plain; charset=utf-8"),
        (".sh", "text/plain; charset=utf-8"),
        (".csv", "text/plain; charset=utf-8"),
        (".log", "text/plain; charset=utf-8"),
        (".xml", "text/plain; charset=utf-8"),
    ],
)
def test_raw_route_serves_well_known_extensions_with_expected_media_types(
    client: TestClient,
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    extension: str,
    expected_media_type: str,
) -> None:
    """GET /api/project/raw serves each documented media, document and source extension with its promised Content-Type even without host mime.types."""
    bare_guess = mimetypes.MimeTypes(filenames=()).guess_type
    filename = f"sample{extension}"
    (project / "docs" / filename).write_bytes(b"sample")

    response = with_token(client).get("/api/project/raw", params={"path": f"docs/{filename}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == expected_media_type

    monkeypatch.setattr(mimetypes, "guess_type", bare_guess)
    assert console_app.raw_content_type(f"docs/{filename}") == expected_media_type



