"""The token gate and the path confinement, through the application."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from conftest import TOKEN, invocations, with_token
from devcapsule_webconsole.app import create_app
from devcapsule_webconsole.security import PathRefused, TokenGate, confine, token_cookie_name
from devcapsule_webconsole.settings import Settings


@pytest.mark.parametrize("path", ["/", "/configuration", "/versions", "/project", "/files", "/files/docs",
                                  "/filetree", "/filetree/docs", "/static/console.css",
                                  "/api/identity", "/api/configuration", "/api/versions", "/api/project",
                                  "/api/project/tree", "/api/project/tree?path=docs",
                                  "/api/project/file?path=docs/guide.md"])
def test_every_route_refuses_a_request_without_the_token(client, path):
    response = client.get(path)
    assert response.status_code == 403
    assert response.text == "devcapsule web console: missing or invalid run token\n"
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("wrong", ["", "x", TOKEN[:-1], TOKEN + "0", TOKEN.upper()])
def test_a_wrong_token_is_refused_in_every_carrier(client, wrong):
    assert client.get("/", params={"token": wrong}).status_code == 403
    assert client.get("/", headers={"X-DevCapsule-Token": wrong}).status_code == 403
    client.cookies.set("devcapsule-console-token", wrong)
    assert client.get("/").status_code == 403


def test_the_query_token_admits_and_sets_the_cookie(client):
    response = client.get("/", params={"token": TOKEN})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"devcapsule-console-token={TOKEN}; Path=/; HttpOnly; SameSite=Strict")
    # The client keeps the cookie; the next request carries no query token.
    assert client.get("/configuration").status_code == 200
    assert client.get("/static/console.css").status_code == 200


def test_the_header_token_admits_without_a_cookie(client):
    response = client.get("/api/configuration", headers={"X-DevCapsule-Token": TOKEN})
    assert response.status_code == 200
    assert "set-cookie" not in response.headers


def test_the_cookie_token_admits_without_a_new_cookie(client):
    response = with_token(client).get("/api/versions")
    assert response.status_code == 200
    assert "set-cookie" not in response.headers


def test_only_get_is_served(client):
    for method in ("post", "put", "delete", "patch"):
        assert getattr(with_token(client), method)("/api/configuration").status_code == 405


def test_confine_accepts_files_inside_the_project(project: Path):
    assert confine(project, "docs/guide.md") == (project / "docs" / "guide.md").resolve()
    assert confine(project, "./docs/guide.md") == (project / "docs" / "guide.md").resolve()


@pytest.mark.parametrize("requested", ["", "/etc/passwd", "../outside.txt", "docs/../../outside.txt",
                                       "docs/../docs/guide.md", "escape.md", "docs/\x00guide.md"])
def test_confine_refuses_paths_that_leave_the_project(project: Path, requested: str):
    with pytest.raises(PathRefused):
        confine(project, requested)


def test_the_file_route_serves_inside_and_refuses_outside(client, project: Path):
    client = with_token(client)
    inside = client.get("/api/project/file", params={"path": "docs/guide.md"})
    assert inside.status_code == 200
    assert inside.text == "# Guide\n\nText.\n"
    assert client.get("/api/project/file", params={"path": "../outside.txt"}).status_code == 403
    assert client.get("/api/project/file", params={"path": "escape.md"}).status_code == 403
    assert client.get("/api/project/file", params={"path": "/etc/hostname"}).status_code == 403
    assert client.get("/api/project/file", params={"path": "docs/missing.md"}).status_code == 404
    assert client.get("/api/project/file", params={"path": "docs"}).status_code == 404
    assert client.get("/api/project/file", params={"path": "image.bin"}).status_code == 415
    assert client.get("/api/project/file").status_code == 422


@pytest.mark.parametrize("authenticated", [False, True])
def test_a_malformed_cookie_does_not_crash_or_hide_a_valid_header(client, authenticated):
    headers = {"Cookie": "other=value; $invalid=attribute"}
    if authenticated:
        headers["X-DevCapsule-Token"] = TOKEN
    assert client.get("/", headers=headers).status_code == (200 if authenticated else 403)


@pytest.mark.parametrize("path", ["/static/console.js", "/missing", "/openapi.json"])
def test_unlisted_paths_also_require_the_token(client, path):
    assert client.get(path).status_code == 403


def test_refusal_never_runs_the_cli(client, fake_cli):
    assert client.get("/api/identity").status_code == 403
    assert invocations(fake_cli[1]) == []


@pytest.mark.parametrize("carrier", ["query", "cookie", "header"])
def test_comparisons_use_compare_digest(client, monkeypatch, carrier):
    from devcapsule_webconsole import security
    compare = security.secrets.compare_digest
    compared = []

    def record(candidate, expected):
        compared.append((candidate, expected))
        return compare(candidate, expected)

    monkeypatch.setattr(security.secrets, "compare_digest", record)
    if carrier == "query":
        response = client.get("/", params={"token": TOKEN})
    elif carrier == "cookie":
        response = with_token(client).get("/")
    else:
        response = client.get("/", headers={"X-DevCapsule-Token": TOKEN})
    assert response.status_code == 200
    assert (TOKEN.encode(), TOKEN.encode()) in compared


def test_an_invalid_query_does_not_replace_a_valid_cookie(client):
    response = with_token(client).get("/", params={"token": "wrong"})
    assert response.status_code == 200
    assert "set-cookie" not in response.headers


def test_two_consoles_on_different_loopback_ports_keep_independent_cookies(project: Path, fake_cli):
    """RFC 6265 §8.5 shares cookies across ports on 127.0.0.1; cookie names isolate each port."""
    token_a = "a" * 48
    token_b = "b" * 48
    app_a = create_app(Settings(project=project, cli=fake_cli[0], token=token_a, port=6081))
    app_b = create_app(Settings(project=project, cli=fake_cli[0], token=token_b, port=6081))

    # Simulate one browser cookie jar for 127.0.0.1 shared across all loopback ports.
    host_cookie_jar: dict[str, str] = {}

    def record_set_cookie(set_cookie_header: str) -> None:
        pair = set_cookie_header.split(";", 1)[0]
        name, value = pair.split("=", 1)
        host_cookie_jar[name] = value

    def browser_cookie_header() -> dict[str, str]:
        return {"Cookie": "; ".join(f"{k}={v}" for k, v in host_cookie_jar.items())}

    with (
        TestClient(app_a, base_url="http://127.0.0.1:41273") as console_a,
        TestClient(app_b, base_url="http://127.0.0.1:41274") as console_b,
    ):
        open_a = console_a.get("/", params={"token": token_a})
        assert open_a.status_code == 200
        assert open_a.headers["set-cookie"] == (
            f"devcapsule-console-token-41273={token_a}; Path=/; HttpOnly; SameSite=Strict"
        )
        record_set_cookie(open_a.headers["set-cookie"])

        # Opening console B in the same browser sends A's cookie and sets B's port-scoped cookie.
        open_b = console_b.get("/", params={"token": token_b}, headers=browser_cookie_header())
        assert open_b.status_code == 200
        assert open_b.headers["set-cookie"] == (
            f"devcapsule-console-token-41274={token_b}; Path=/; HttpOnly; SameSite=Strict"
        )
        record_set_cookie(open_b.headers["set-cookie"])
        assert host_cookie_jar == {
            "devcapsule-console-token-41273": token_a,
            "devcapsule-console-token-41274": token_b,
        }

        # Clear TestClient internal cookies so only the shared host_cookie_jar is sent.
        console_a.cookies.clear()
        console_b.cookies.clear()

        # Both consoles keep answering internal navigation and API calls simultaneously.
        both_cookies = browser_cookie_header()
        assert console_a.get("/configuration", headers=both_cookies).status_code == 200
        assert console_a.get("/api/identity", headers=both_cookies).status_code == 200
        assert console_b.get("/processes", headers=both_cookies).status_code == 200
        assert console_b.get("/api/versions", headers=both_cookies).status_code == 200

        # Neither console accepts the other port's cookie or a bare portless cookie on a ported origin.
        assert console_a.get(
            "/api/identity",
            headers={"Cookie": f"devcapsule-console-token-41274={token_b}; devcapsule-console-token={token_a}"},
        ).status_code == 403
        assert console_b.get(
            "/api/versions",
            headers={"Cookie": f"devcapsule-console-token-41273={token_a}; devcapsule-console-token={token_b}"},
        ).status_code == 403


def test_neighbor_localhost_cookies_and_split_cookie_headers_do_not_break_auth(project: Path, fake_cli):
    """Non-RFC2109 cookies from sibling apps on 127.0.0.1 must not discard the console cookie."""
    app = create_app(Settings(project=project, cli=fake_cli[0], token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1:41273") as ported:
        sibling_cookies = (
            f'g_state={{"i_l":0}}; filter[a]=1; $bad=attr; devcapsule-console-token-41273={TOKEN}'
        )
        assert ported.get("/api/versions", headers={"Cookie": sibling_cookies}).status_code == 200


@pytest.mark.parametrize(
    ("base_url", "expected_cookie"),
    [
        ("http://127.0.0.1:41273", "devcapsule-console-token-41273"),
        ("http://[::1]:41273", "devcapsule-console-token-41273"),
        ("http://[::1]", "devcapsule-console-token"),
        ("http://localhost:8080", "devcapsule-console-token-8080"),
        ("http://localhost", "devcapsule-console-token"),
    ],
)
def test_cookie_name_tracks_explicit_host_port_including_ipv6(project: Path, fake_cli, base_url: str, expected_cookie: str):
    app = create_app(Settings(project=project, cli=fake_cli[0], token=TOKEN))
    with TestClient(app, base_url=base_url) as scoped_client:
        opened = scoped_client.get("/", params={"token": TOKEN})
        assert opened.status_code == 200
        assert opened.headers["set-cookie"].startswith(f"{expected_cookie}={TOKEN}; Path=/; HttpOnly; SameSite=Strict")
        scoped_client.cookies.clear()
        assert scoped_client.get("/api/versions", headers={"Cookie": f"{expected_cookie}={TOKEN}"}).status_code == 200


@pytest.mark.parametrize("bad_host", ["", ":41273", "127.0.0.1:0", "127.0.0.1:99999", "127.0.0.1:abc",
                                      "user@127.0.0.1:41273", "evil;injected=1:41273", "127.0.0.1/path:41273"])
def test_malformed_host_headers_fall_back_safely_without_header_injection(client, bad_host: str):
    assert token_cookie_name(None) == "devcapsule-console-token"
    assert token_cookie_name(0) == "devcapsule-console-token"
    assert token_cookie_name(65536) == "devcapsule-console-token"
    assert token_cookie_name(True) == "devcapsule-console-token"
    response = client.get("/", params={"token": TOKEN}, headers={"Host": bad_host})
    assert response.status_code == 200
    assert response.headers["set-cookie"] == f"devcapsule-console-token={TOKEN}; Path=/; HttpOnly; SameSite=Strict"


def test_asgi_scope_without_host_header_or_with_split_cookie_headers_is_handled():
    import asyncio

    admitted: list[int] = []

    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    gate = TokenGate(inner, TOKEN)

    async def call(headers: list[tuple[bytes, bytes]], server: tuple[str, int] = ("127.0.0.1", 41273)) -> int:
        statuses: list[int] = []

        async def send(message):
            if message["type"] == "http.response.start":
                statuses.append(message["status"])

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        await gate(
            {"type": "http", "headers": headers, "query_string": b"", "server": server},
            receive,
            send,
        )
        return statuses[0]

    admitted.append(
        asyncio.run(
            call([(b"cookie", b"other=1"), (b"cookie", f"devcapsule-console-token-41273={TOKEN}".encode("ascii"))])
        )
    )
    # Duplicate Host headers refuse to trust an ambiguous port and fall back to the bare cookie name.
    admitted.append(
        asyncio.run(
            call([
                (b"host", b"127.0.0.1:41273"),
                (b"host", b"127.0.0.1:41274"),
                (b"cookie", f"devcapsule-console-token-41273={TOKEN}".encode("ascii")),
            ])
        )
    )
    assert admitted == [200, 403]


def test_two_live_loopback_servers_share_one_rfc_cookie_jar_without_collision(project: Path, fake_cli):
    """End-to-end wire check: http.cookiejar stores cookies on 127.0.0.1 without port isolation."""
    import http.cookiejar
    import socket
    import threading
    import time
    import urllib.error
    import urllib.request
    import uvicorn

    try:
        sock_a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_a.bind(("127.0.0.1", 0))
        sock_b.bind(("127.0.0.1", 0))
    except OSError as error:
        pytest.skip(f"loopback bind unavailable: {error}")

    port_a = int(sock_a.getsockname()[1])
    port_b = int(sock_b.getsockname()[1])
    token_a = "c" * 48
    token_b = "d" * 48
    server_a = uvicorn.Server(
        uvicorn.Config(
            create_app(Settings(project=project, cli=fake_cli[0], token=token_a, port=6081)),
            fd=sock_a.fileno(),
            log_level="error",
            log_config=None,
            access_log=False,
        )
    )
    server_b = uvicorn.Server(
        uvicorn.Config(
            create_app(Settings(project=project, cli=fake_cli[0], token=token_b, port=6081)),
            fd=sock_b.fileno(),
            log_level="error",
            log_config=None,
            access_log=False,
        )
    )
    thread_a = threading.Thread(target=server_a.run, kwargs={"sockets": [sock_a]}, daemon=True)
    thread_b = threading.Thread(target=server_b.run, kwargs={"sockets": [sock_b]}, daemon=True)
    thread_a.start()
    thread_b.start()
    try:
        deadline = time.monotonic() + 10.0
        while not (server_a.started and server_b.started):
            assert time.monotonic() < deadline, "uvicorn servers did not start in time"
            time.sleep(0.01)

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        assert opener.open(f"http://127.0.0.1:{port_a}/?token={token_a}", timeout=5).status == 200
        assert opener.open(f"http://127.0.0.1:{port_b}/?token={token_b}", timeout=5).status == 200
        assert opener.open(f"http://127.0.0.1:{port_a}/configuration", timeout=5).status == 200
        assert opener.open(f"http://127.0.0.1:{port_b}/processes", timeout=5).status == 200
        assert {cookie.name for cookie in jar} == {
            f"devcapsule-console-token-{port_a}",
            f"devcapsule-console-token-{port_b}",
        }
        # Without its cookie, each live server still refuses requests with 403.
        with pytest.raises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(f"http://127.0.0.1:{port_a}/configuration", timeout=5)
        assert refused.value.code == 403
    finally:
        server_a.should_exit = True
        server_b.should_exit = True
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)
        sock_a.close()
        sock_b.close()


def test_internal_symlinks_are_readable_but_loops_are_refused(client, project):
    (project / "inside.md").symlink_to("docs/guide.md")
    (project / "loop.md").symlink_to("loop.md")
    client = with_token(client)
    assert client.get("/api/project/file", params={"path": "inside.md"}).text == "# Guide\n\nText.\n"
    assert client.get("/api/project/file", params={"path": "loop.md"}).status_code == 403


@pytest.mark.parametrize("replace_directory", [False, True])
def test_a_symlink_swap_after_resolution_cannot_read_outside(client, project, monkeypatch, replace_directory):
    outside = project.parent / "outside"
    outside.mkdir()
    (outside / "guide.md").write_text("outside secret", encoding="utf-8")
    target = project / "docs" / "guide.md"
    resolve = Path.resolve
    swapped = False

    def resolve_then_swap(path, *args, **kwargs):
        nonlocal swapped
        resolved = resolve(path, *args, **kwargs)
        if path == target and not swapped:
            swapped = True
            if replace_directory:
                target.parent.rename(project / "old-docs")
                target.parent.symlink_to(outside, target_is_directory=True)
            else:
                target.unlink()
                target.symlink_to(outside / "guide.md")
        return resolved

    monkeypatch.setattr(Path, "resolve", resolve_then_swap)
    response = with_token(client).get("/api/project/file", params={"path": "docs/guide.md"})
    assert swapped
    assert response.status_code == 403
    assert "outside secret" not in response.text


@pytest.mark.parametrize("failure", [PermissionError("denied"), FileNotFoundError("removed")])
def test_file_read_errors_have_http_responses(client, project, monkeypatch, failure):
    import os
    original_os_open = os.open

    def fail_descriptor(path, *args, **kwargs):
        if path == "guide.md":
            raise failure
        return original_os_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", fail_descriptor)
    response = with_token(client).get("/api/project/file", params={"path": "docs/guide.md"})
    assert response.status_code == (404 if isinstance(failure, FileNotFoundError) else 403)


def test_the_mount_itself_is_not_a_file(client):
    assert with_token(client).get("/api/project/file", params={"path": "."}).status_code == 404


def test_a_fifo_is_refused_without_waiting_for_a_writer(project):
    import os
    import subprocess
    import sys

    os.mkfifo(project / "pipe")
    # A subprocess timeout makes removal of O_NONBLOCK fail instead of hanging pytest.
    script = """
import sys
from pathlib import Path
from devcapsule_webconsole.security import read_project_text
try:
    read_project_text(Path(sys.argv[1]), "pipe")
except FileNotFoundError:
    sys.exit(0)
sys.exit(1)
"""
    result = subprocess.run([sys.executable, "-c", script, str(project)], timeout=5, capture_output=True)
    assert result.returncode == 0, result.stderr
