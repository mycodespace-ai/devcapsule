"""Two real capsules share a browser cookie jar without losing authentication.

Run with the PEX/base under test and the ide-smoke environment, explicitly
selecting this file with ``pytest --no-cov -m e2e``. No provider login needed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
import uuid

import pytest

from tests.e2e.ide_session import SURFACES, command, ide_session, wait_for_console_url, wait_for_ide_window

pytestmark = pytest.mark.legacy


def connected(page: Any) -> None:
    page.evaluate("async () => { window.authSmokeUI = (await import('/app/ui.js')).default; }")
    page.wait_for_function("window.authSmokeUI.connected === true", timeout=60_000)
    page.locator("canvas").first.wait_for(state="visible")


@pytest.mark.e2e
@pytest.mark.ide_smoke
def test_two_capsules_share_browser_auth(built_pex: Path, tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found,unused-ignore]

    evidence = Path(__file__).resolve().parents[2] / "dist/e2e-evidence/concurrent-auth" / (
        time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:6]
    )
    surface = next(item for item in SURFACES if item.name == "codium")
    with ide_session(built_pex, surface, tmp_path, evidence / "a") as a, ide_session(
        built_pex, surface, tmp_path, evidence / "b"
    ) as b:
        sessions = [a, b]
        windows = [wait_for_ide_window(s) for s in sessions]
        console_urls = []
        for session in sessions:
            assert session.launcher is not None
            console_urls.append(wait_for_console_url(session.launcher, session.launcher_log))
        origins = [urlunsplit((*urlsplit(url)[:2], "/", "", "")) for url in console_urls]
        ports = [urlsplit(url).port for url in console_urls]
        assert ports[0] != ports[1]
        names = [f"devcapsule-console-token-{port}" for port in ports]
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            consoles = [context.new_page(), context.new_page()]
            desktops = [context.new_page(), context.new_page()]
            for i in range(2):
                response = consoles[i].goto(console_urls[i])
                assert response is not None and response.status == 200
                desktops[i].goto(sessions[i].desktop_url)
                connected(desktops[i])
            cookies = {cookie["name"]: cookie for cookie in context.cookies()}
            assert all(name in cookies for name in names)
            assert cookies[names[0]]["value"] != cookies[names[1]]["value"]
            assert all(cookies[name]["httpOnly"] and cookies[name]["sameSite"] == "Strict" for name in names)
            # Both ports now share the same cookie jar. Use no token in any
            # subsequent console navigation; tokened links would hide the bug.
            for _ in range(2):
                for i in range(2):
                    consoles[i].bring_to_front()
                    response = consoles[i].goto(origins[i])
                    assert response is not None and response.status == 200
                    response = consoles[i].reload()
                    assert response is not None and response.status == 200
                    desktops[i].bring_to_front()
                    desktops[i].reload()
                    connected(desktops[i])
                    desktops[i].evaluate("window.authSmokeUI.disconnect()")
                    desktops[i].wait_for_function("typeof window.authSmokeUI.rfb === 'undefined'")
                    desktops[i].evaluate("window.authSmokeUI.connect()")
                    connected(desktops[i])
            # A sibling token under this port's cookie name must be refused.
            for i in range(2):
                context.add_cookies([{**cookies[names[i]], "value": cookies[names[1-i]]["value"]}])
                assert context.request.get(origins[i]).status == 403
                context.add_cookies([cookies[names[i]]])
                assert context.request.get(origins[i]).status == 200
            anonymous = browser.new_context()
            for i in range(2):
                assert anonymous.request.get(origins[i]).status == 403
                sibling_token = parse_qs(urlsplit(console_urls[1-i]).query)["token"][0]
                assert anonymous.request.get(origins[i], params={"token": sibling_token}).status == 403
                # noVNC uses a WebSocket token. A token from the other capsule
                # must close without delivering even the RFB handshake bytes.
                parts = urlsplit(sessions[i].desktop_url)
                path = parse_qs(parts.query)["path"][0]
                sibling_path = parse_qs(urlsplit(sessions[1-i].desktop_url).query)["path"][0]
                wrong = parse_qs(urlsplit(sibling_path).query)["token"][0]
                websocket = urlunsplit(("ws", parts.netloc, "/" + urlsplit(path).path, urlencode({"token": wrong}), ""))
                result = desktops[i].evaluate("""url => new Promise(resolve => {
                    const socket = new WebSocket(url);
                    const timer = setTimeout(() => { socket.close(); resolve('timeout'); }, 10000);
                    socket.onmessage = () => { clearTimeout(timer); socket.close(); resolve('data'); };
                    socket.onclose = () => { clearTimeout(timer); resolve('closed'); };
                })""", websocket)
                assert result == "closed", "Sibling desktop token was not refused"
                connected(desktops[i])
                desktops[i].locator("canvas").first.screenshot(path=str(evidence / f"desktop-{i}.png"))
                consoles[i].screenshot(path=str(evidence / f"console-{i}.png"))
            anonymous.close()
            context.close()
            browser.close()
        identities = [json.loads(command("docker", "inspect", "--format", "{{json .Image}}", s.container).stdout) for s in sessions]
        (evidence / "facts.json").write_text(json.dumps({
            "pex_sha256": hashlib.sha256(built_pex.read_bytes()).hexdigest(),
            "builder": json.loads(command(str(built_pex), "version", "--json").stdout),
            "console_ports": ports, "cookie_names": names, "ide_windows": windows,
            "environment_images": identities,
            "shared_browser_context": True, "tokenless_navigation_and_reload": True,
            "desktop_reload_and_reconnect": True, "sibling_credentials_refused": True,
        }, indent=2) + "\n", encoding="utf-8")
