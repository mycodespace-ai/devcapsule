"""The presentation page: its routes, its static files, the search for presentations, and what it reads through the raw route."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
import pytest

from conftest import with_token
from devcapsule_webconsole.security import find_project_folders


@pytest.mark.parametrize(
    "route",
    [
        "/presentations",
        "/presentations/",
        "/presentations/e2e/evidence/todo-fastapi-postgres-react",
        "/presentations/e2e/evidence/todo%20run",
    ],
)
def test_presentation_routes_serve_the_presentation_page(client: TestClient, route: str) -> None:
    """GET /presentations and GET /presentations/<folder> serve the one page, which loads the console and its own script and stylesheet."""
    response = with_token(client).get(route)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-page="presentation"' in response.text
    assert '<script src="/static/console.js" defer></script>' in response.text
    assert '<script src="/static/presentation.js" defer></script>' in response.text
    assert '<link rel="stylesheet" href="/static/presentation.css">' in response.text


def test_presentation_page_is_refused_without_the_token(client: TestClient) -> None:
    """The token gate covers the presentation page as it covers every route."""
    response = client.get("/presentations/e2e/evidence/todo-fastapi-postgres-react")

    assert response.status_code == 403


@pytest.mark.parametrize("name", ["presentation.js", "presentation.css"])
def test_presentation_static_files_are_served(client: TestClient, name: str) -> None:
    """The page's script and stylesheet are static files of the console."""
    response = with_token(client).get(f"/static/{name}")

    assert response.status_code == 200
    assert response.text.strip() != ""


def test_a_presentation_folder_is_read_through_the_raw_route(client: TestClient, project: Path) -> None:
    """The page needs nothing but the raw route: the document as JSON, and any range of the recording as video."""
    folder = project / "e2e" / "evidence" / "sample"
    folder.mkdir(parents=True)
    document = {"schema_version": 1, "title": "Sample"}
    (folder / "presentation.json").write_text(json.dumps(document), encoding="utf-8")
    recording = bytes(range(200))
    (folder / "scenario-video.webm").write_bytes(recording)
    authorized = with_token(client)

    read = authorized.get("/api/project/raw", params={"path": "e2e/evidence/sample/presentation.json"})
    part = authorized.get(
        "/api/project/raw", params={"path": "e2e/evidence/sample/scenario-video.webm"}, headers={"Range": "bytes=50-99"},
    )

    assert read.status_code == 200
    assert read.headers["content-type"].startswith("application/json")
    assert read.json() == document
    assert part.status_code == 206
    assert part.headers["content-type"] == "video/webm"
    assert part.content == recording[50:100]


def test_every_page_navigation_offers_presentations_after_files(client: TestClient) -> None:
    """Every console page places Presentations after Files in the navigation bar, and Home has a Presentations card."""
    authorized = with_token(client)

    pages = {route: authorized.get(route).text for route in (
        "/", "/configuration", "/versions", "/project", "/processes", "/records", "/files", "/presentations",
        "/decisions", "/notifications",
    )}

    for route, html in pages.items():
        assert '<a href="/files">Files</a><a href="/presentations">Presentations</a>' in html, route
    assert pages["/"].count('href="/presentations"') == 2


def presentation_folder(root: Path, relative: str) -> Path:
    """A folder of ``root`` that holds a presentation document."""
    folder = root / relative
    folder.mkdir(parents=True)
    (folder / "presentation.json").write_text("{}", encoding="utf-8")
    return folder


def test_find_project_folders_finds_every_folder_holding_the_marker_below_the_root(tmp_path: Path) -> None:
    """The folders holding a regular marker file are found at any depth, sorted, and the root itself is not one of them."""
    presentation_folder(tmp_path, "tests/e2e/evidence/todo")
    presentation_folder(tmp_path, "docs/demo")
    (tmp_path / "docs" / "plain").mkdir()
    (tmp_path / "presentation.json").write_text("{}", encoding="utf-8")

    found = find_project_folders(tmp_path, "presentation.json")

    assert found == {"folders": ["docs/demo", "tests/e2e/evidence/todo"], "complete": True}


def test_find_project_folders_does_not_enter_hidden_package_or_linked_directories(tmp_path: Path) -> None:
    """A directory whose name starts with a dot, a node_modules directory and a symbolic link to a directory are not searched."""
    presentation_folder(tmp_path, ".nox/session/site")
    presentation_folder(tmp_path, "web/node_modules/package")
    outside = presentation_folder(tmp_path.parent / f"{tmp_path.name}-outside", "recorded")
    (tmp_path / "linked").symlink_to(outside.parent, target_is_directory=True)
    presentation_folder(tmp_path, "web/demo")

    found = find_project_folders(tmp_path, "presentation.json")

    assert found == {"folders": ["web/demo"], "complete": True}


def test_find_project_folders_counts_only_a_regular_marker_file(tmp_path: Path) -> None:
    """A marker that is a directory or a symbolic link does not make its folder a result."""
    (tmp_path / "as-directory" / "presentation.json").mkdir(parents=True)
    target = tmp_path / "elsewhere.json"
    target.write_text("{}", encoding="utf-8")
    (tmp_path / "as-link").mkdir()
    (tmp_path / "as-link" / "presentation.json").symlink_to(target)

    found = find_project_folders(tmp_path, "presentation.json")

    assert found == {"folders": [], "complete": True}


def test_find_project_folders_stops_at_its_budget_and_says_so(tmp_path: Path) -> None:
    """A search that runs out of its budget of directories returns what it found, in name order, marked incomplete."""
    presentation_folder(tmp_path, "a")
    presentation_folder(tmp_path, "b")
    presentation_folder(tmp_path, "c")

    found = find_project_folders(tmp_path, "presentation.json", budget=3)

    assert found == {"folders": ["a", "b"], "complete": False}


def test_presentations_route_lists_the_projects_presentation_folders(client: TestClient, project: Path) -> None:
    """GET /api/project/presentations answers with the folders of the project that hold a presentation.json."""
    presentation_folder(project, "e2e/evidence/sample")

    response = with_token(client).get("/api/project/presentations")

    assert response.status_code == 200
    assert response.json() == {"folders": ["e2e/evidence/sample"], "complete": True}


def test_presentation_script_shows_slides_plays_steps_and_refuses_broken_documents() -> None:
    """The page script renders the overview and each step, plays one step or the whole recording with captions, follows the keys, lists the project's presentations, and refuses a folder without a valid presentation.json."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is a development-only script test dependency")
    subprocess.run([node, str(Path(__file__).with_name("presentation-script.cjs"))], check=True)
