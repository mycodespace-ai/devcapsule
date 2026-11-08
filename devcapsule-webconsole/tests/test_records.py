"""Records: the raw file route, the records pages, and the vendored renderers."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO
import re
import tomllib

from fastapi.testclient import TestClient

import devcapsule_webconsole

import pytest

from conftest import with_token
from devcapsule_webconsole.app import raw_content_type

STATIC = Path(devcapsule_webconsole.__file__).parent / "static"


@pytest.mark.parametrize("path, expected", [
    ("docs/guide.md", "text/markdown; charset=utf-8"),
    ("README", "application/octet-stream"),
    ("notes.txt", "text/plain; charset=utf-8"),
    ("config.toml", "text/plain; charset=utf-8"),
    ("data.json", "application/json"),
    ("diagram.svg", "image/svg+xml"),
    ("shot.PNG", "image/png"),
    ("clip.webm", "video/webm"),
    ("sound.mp3", "audio/mpeg"),
    ("document.xhtml", "application/octet-stream"),
    ("diagram.svgz", "image/svg+xml"),
    ("page.html", "text/plain; charset=utf-8"),
    ("script.js", "text/plain; charset=utf-8"),
    ("archive.tar.gz", "application/octet-stream"),
    ("dir.v2/file", "application/octet-stream"),
])
def test_raw_content_types(path: str, expected: str) -> None:
    assert raw_content_type(path) == expected


def test_the_raw_route_serves_bytes_inside_the_project_and_refuses_outside(client, project: Path):
    assert client.get("/api/project/raw", params={"path": "image.bin"}).status_code == 403  # no token yet
    client = with_token(client)
    image = client.get("/api/project/raw", params={"path": "image.bin"})
    assert image.status_code == 200
    assert image.content == b"\xff\xfe\x00binary"
    assert image.headers["content-type"] == "application/octet-stream"
    (project / "docs" / "shot.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    shot = client.get("/api/project/raw", params={"path": "docs/shot.png"})
    assert shot.status_code == 200 and shot.headers["content-type"] == "image/png"
    (project / "docs" / "page.html").write_text("<script>alert(1)</script>", encoding="utf-8")
    page = client.get("/api/project/raw", params={"path": "docs/page.html"})
    assert page.status_code == 200 and page.headers["content-type"] == "text/plain; charset=utf-8"
    guide = client.get("/api/project/raw", params={"path": "docs/guide.md"})
    assert guide.status_code == 200 and guide.headers["content-type"] == "text/markdown; charset=utf-8"
    assert client.get("/api/project/raw", params={"path": "../outside.txt"}).status_code == 403
    assert client.get("/api/project/raw", params={"path": "escape.md"}).status_code == 403
    assert client.get("/api/project/raw", params={"path": "/etc/hostname"}).status_code == 403
    assert client.get("/api/project/raw", params={"path": "docs/missing.png"}).status_code == 404
    assert client.get("/api/project/raw", params={"path": "docs"}).status_code == 404
    assert client.get("/api/project/raw").status_code == 422


@pytest.mark.parametrize("route", ["/records", "/records/", "/records/index.md", "/records/engineering-docs/wip/x/CURRENT-STATUS.md",
                                   "/records/docs/guide.md#section"])
def test_every_records_path_serves_the_records_page(client, route):
    assert client.get(route).status_code == 403
    response = with_token(client).get(route)
    assert response.status_code == 200
    assert 'data-page="records"' in response.text
    assert '<script src="/static/vendor/markdown-it-15.0.2.umd.min.js" defer></script>' in response.text
    assert '<script src="/static/vendor/viz-3.31.0.global.js" defer></script>' in response.text


def test_the_navigation_and_the_home_page_name_records(client):
    home = with_token(client).get("/").text
    assert home.count('href="/records"') == 2  # navigation and card
    for route in ("/configuration", "/versions", "/project", "/processes", "/records"):
        assert 'href="/records"' in with_token(client).get(route).text


def test_vendored_renderers_match_their_recorded_digests():
    """VENDORED.md is the provenance record; the files must be the ones it names."""
    table = (STATIC / "vendor" / "VENDORED.md").read_text(encoding="utf-8")
    rows = [line for line in table.splitlines() if line.startswith("| `")]
    assert len(rows) == 2
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        name = cells[0].strip("`")
        digest = cells[-1].strip("`")
        assert re.fullmatch(r"[0-9a-f]{64}", digest), row
        assert hashlib.sha256((STATIC / "vendor" / name).read_bytes()).hexdigest() == digest, name
    served = {path.name for path in (STATIC / "vendor").iterdir()}
    assert {"markdown-it-15.0.2.umd.min.js", "viz-3.31.0.global.js", "VENDORED.md", "markdown-it-LICENSE"} <= served


@pytest.mark.parametrize("name", ["markdown-it-15.0.2.umd.min.js", "viz-3.31.0.global.js"])
def test_vendored_files_are_served_behind_the_token(client: TestClient, name: str) -> None:
    route = "/static/vendor/" + name
    assert client.get(route).status_code == 403
    response = with_token(client).get(route)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.content == (STATIC / "vendor" / name).read_bytes()


@pytest.mark.parametrize("name, content_type", [
    ("attack.svg", "image/svg+xml"),
    ("attack.svgz", "image/svg+xml"),
    ("attack.html", "text/plain; charset=utf-8"),
    ("attack.xhtml", "application/octet-stream"),
    ("attack.js", "text/plain; charset=utf-8"),
    ("attack.png", "image/png"),
    ("attack", "application/octet-stream"),
])
def test_raw_project_content_is_isolated_even_when_opened_as_a_document(
    client: TestClient, project: Path, name: str, content_type: str,
) -> None:
    # Include SVG active content and a misleading extension. The policy must
    # protect every raw response, independently of MIME guessing or file bytes.
    payload = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>alert(2)</script></svg>'
    (project / name).write_bytes(payload)
    response = with_token(client).get("/api/project/raw", params={"path": name})
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"] == content_type
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == "sandbox; default-src 'none'; style-src 'unsafe-inline'"


def test_raw_route_reports_a_read_permission_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A read the operating system refuses is a 403 that names the path and not the host's reason."""
    from contextlib import contextmanager

    from devcapsule_webconsole import app

    @contextmanager
    def denied(root: Path, requested: str) -> Iterator[tuple[BinaryIO, int]]:
        raise PermissionError("private host detail")
        yield  # pragma: no cover - the generator form is what open_project_file's callers expect

    monkeypatch.setattr(app, "open_project_file", denied)
    response = with_token(client).get("/api/project/raw", params={"path": "docs/guide.md"})
    assert response.status_code == 403
    assert response.text == "cannot read 'docs/guide.md' in the project\n"


@pytest.mark.parametrize("path", ["", ".", "docs/\x00guide.md", "loop.md"])
def test_raw_route_handles_invalid_paths(client: TestClient, project: Path, path: str) -> None:
    (project / "loop.md").symlink_to("loop.md")
    response = with_token(client).get("/api/project/raw", params={"path": path})
    assert response.status_code == (404 if path == "." else 403)


def test_bytes_reader_preserves_binary_and_newlines_through_an_internal_link(project: Path) -> None:
    from devcapsule_webconsole.security import read_project_bytes

    content = bytes(range(256)) + b"\r\nline\rnext\n"
    (project / "docs" / "data").write_bytes(content)
    (project / "linked").symlink_to("docs/data")
    assert read_project_bytes(project, "linked") == content


def test_distribution_patterns_include_every_vendored_asset() -> None:
    # Editable installs serve source files even when the wheel omits them.
    # Check the package-data selection, including the provenance and license.
    package = STATIC.parent
    config = tomllib.loads((package.parent / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = config["tool"]["setuptools"]["package-data"]["devcapsule_webconsole"]
    selected = {path for pattern in patterns for path in package.glob(pattern) if path.is_file()}
    required = {path for path in (STATIC / "vendor").iterdir() if path.is_file()}
    assert required <= selected, required - selected
