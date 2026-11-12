"""Launch a real IDE session with the executable under test, and ask the capsule
whether the IDE came alive.

The smoke test for an IDE surface is deliberately shallow and deterministic:
initialize a fresh project that needs the surface, run it exactly as an adopter
would, and establish three facts from the outside, in this order:

1. the launcher published a desktop URL and the page behind it answers;
2. inside the container, an X11 top-level window of the IDE's class exists on
   the capsule's own display, read through a minimal X client so the image
   needs no X tools;
3. optionally, the desktop as a browser renders it holds more than a bare
   desktop: a pixel capture through Playwright, kept as evidence.

Everything the session leaves behind is removed on exit: the container, the
project directory, and the checkout records the executable wrote for the
project's slug.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IdeSurface:
    """One IDE the product offers, as the smoke test needs to know it."""

    name: str
    """The component name, used for the project slug and the evidence directory."""
    needs: tuple[str, ...]
    """The capabilities and IDE used to initialize the smoke project."""
    window_class: str
    """A case-insensitive fragment of the IDE's X11 ``WM_CLASS``."""
    ready_timeout: float
    """Seconds to wait for the IDE window after the desktop URL appeared."""
    consents: tuple[tuple[str, str], ...] = ()
    """Per-checkout answers given at initialization, as ``(node, value)`` pairs:
    a vendor download the surface needs, which a fresh home has not trusted."""


SURFACES: tuple[IdeSurface, ...] = (
    IdeSurface("eclipse", ("eclipse-ide", "java", "browser-automation"), "eclipse", ready_timeout=420.0),
    IdeSurface("codium", ("frontend-ide", "node"), "codium", ready_timeout=180.0),
    IdeSurface("vscode", ("vscode-ide", "node"), "code", ready_timeout=180.0,
               consents=(("vscode-download", "true"),)),
    IdeSurface("pycharm", ("python-ide", "python"), "jetbrains-pycharm", ready_timeout=420.0),
    IdeSurface("rider", ("dotnet-ide", "browser-automation"), "jetbrains-rider", ready_timeout=420.0),
    IdeSurface("intellij", ("java-ide", "java", "browser-automation"), "jetbrains-idea", ready_timeout=420.0),
)

CREATOR = "e2e@devcapsule.test"
DESKTOP_READY = re.compile(
    r"Contained display is ready; (?:open it in a browser: (http://127\.0\.0\.1:\d+/vnc\.html\?\S+)"
    r"|opened in your browser\.|opened through the host-browser bridge\.)"
)
"""The launcher's readiness line. It also announces the URL earlier, before the
bridge listens; only the ready line means the page answers. Inside a capsule
without a bridge the ready line names the URL. Elsewhere the launcher opens it,
which the smoke's ``BROWSER=true`` makes a no-op, and the URL is the earlier
announcement's."""
DESKTOP_ANNOUNCED = re.compile(r"Contained display: (http://127\.0\.0\.1:\d+/vnc\.html\?\S+)")
"""The launcher's first mention of the desktop URL, printed before it answers."""
CONSOLE_READY = re.compile(r"Web console is ready; open it in a browser: (http://127\.0\.0\.1:\d+/\?token=\S+)")
"""The launcher's console readiness line; printed once the console answered its port."""
LAUNCH_TIMEOUT = 600.0
"""Seconds for the launcher to publish the desktop URL; a first run may acquire an IDE."""


@dataclass(frozen=True)
class SessionFacts:
    """What one launched session established, kept as evidence by the test."""

    surface: IdeSurface
    container: str
    desktop_url: str
    workspace: Path
    launcher_log: Path
    launcher: subprocess.Popen[bytes] | None = None
    project_path: str | None = None


def command(*args: str, check: bool = True, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    """Run a command with captured streams; ``check`` raises with both streams shown."""
    completed = subprocess.run(list(args), check=False, text=True, capture_output=True, timeout=timeout)
    if check and completed.returncode != 0:
        raise AssertionError(f"{args!r} exited {completed.returncode}\n{completed.stdout}\n{completed.stderr}")
    return completed


def workspace_root(tmp_path: Path) -> Path:
    """Where the project may live so that the Docker daemon can bind-mount it.

    Outside a capsule any directory works. Inside one, only host-backed paths
    reach the daemon, and the persistent home is the one the launcher
    translates; the recursive preflight names this workspace for the purpose.
    """
    if Path("/etc/devcapsule/runtime-plan.json").exists():
        root = Path.home() / ".local" / "share" / "devcapsule" / "e2e-workspaces"
        root.mkdir(parents=True, exist_ok=True)
        return root
    return tmp_path


def remove_project_records(slug: str) -> list[Path]:
    """Remove the records the executable wrote for a project slug; return what was removed.

    The slug is unique per session, so a glob on it cannot reach anyone
    else's records. Managed state lives under the XDG data, state and cache
    trees by ``<hash>-<slug>``; the checkout record under config by
    ``<creator>/<slug>``. Patterns are globbed relative to the home directory,
    since a wildcard inside a ``Path`` is a literal name, not a pattern.
    """
    home = Path.home()
    removed: list[Path] = []
    for pattern in (
        f".config/devcapsule/projects/*/{slug}",
        f".local/share/devcapsule/projects/by-path/*-{slug}",
        f".local/state/devcapsule/projects/by-path/*-{slug}",
        f".cache/devcapsule/projects/by-path/*-{slug}",
    ):
        for path in home.glob(pattern):
            shutil.rmtree(path, ignore_errors=True)
            removed.append(path)
    return removed


@contextmanager
def ide_session(executable: Path, surface: IdeSurface, tmp_path: Path, evidence: Path) -> Iterator[SessionFacts]:
    """Initialize and run a fresh project for ``surface``; stop and clean up on exit.

    The project consents to the recommended base, or to the locally built
    base ``DEVCAPSULE_E2E_BASE_IMAGE`` names, as an unverified experiment,
    and to local-test host networking. The launcher's output goes to a log
    kept with the evidence; the desktop and console URLs are read from it.
    """
    run_id = uuid.uuid4().hex[:8]
    slug = f"e2e-ide-{surface.name}-{run_id}"
    container = f"devcapsule-e2e-ide-{surface.name}-{run_id}"
    workspace = workspace_root(tmp_path) / slug
    workspace.mkdir(parents=True)
    (workspace / "smoke.txt").write_text("DevCapsule graphical smoke fixture.\n", encoding="utf-8")
    if surface.name == "rider":
        (workspace / "Smoke.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
            '<TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>\n')
        (workspace / "Program.cs").write_text('System.Console.WriteLine("DevCapsule .NET smoke passed");\n')
        (workspace / "NuGet.Config").write_text('<configuration><packageSources><clear /></packageSources></configuration>\n')
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        initialize_project(executable, surface, workspace, evidence, slug)
        with launched_ide(executable, surface, workspace, evidence, container) as facts:
            yield facts
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        (evidence / "removed-records.json").write_text(
            json.dumps([str(path) for path in remove_project_records(slug)], indent=2) + "\n", encoding="utf-8"
        )


def initialize_project(executable: Path, surface: IdeSurface, workspace: Path, evidence: Path, slug: str) -> None:
    """``project init`` the workspace for ``surface`` as an adopter would; the log goes with the evidence.

    The project consents to the recommended base, or to the locally built
    base ``DEVCAPSULE_E2E_BASE_IMAGE`` names, as an unverified experiment,
    to local-test host networking, and to the surface's own consents: a
    vendor download the launcher would otherwise stop for, since the smoke
    runs non-interactively and trusts nothing in the home.
    """
    environment = dict(os.environ, BROWSER="true")  # webbrowser runs `true URL`: no tab opens
    built_base = os.environ.get("DEVCAPSULE_E2E_BASE_IMAGE")
    # DEVCAPSULE_SMOKE_PLATFORM creates the project for that capsule platform,
    # such as linux-arm64 on Apple Silicon, whose new projects are linux-amd64.
    platform = os.environ.get("DEVCAPSULE_SMOKE_PLATFORM")
    init = subprocess.run(
        [str(executable), "project", "init", *(["--platform", platform] if platform else []),
         *(flag for need in surface.needs for flag in ("--ide" if need.endswith("-ide") else "--require", need)),
         "--creator", CREATOR, "--slug", slug,
         "--authorize", "base-image", "default",
         "--authorize", "network", "host", "Local graphical smoke requires host networking.",
         *(flag for node, value in surface.consents for flag in ("--authorize", node, value)),
         *(["--unverified"] if built_base else [])],
        cwd=workspace, env=environment, text=True, capture_output=True, stdin=subprocess.DEVNULL,
        check=False, timeout=300.0,
    )
    (evidence / "init.log").write_text(init.stdout + init.stderr, encoding="utf-8")
    assert init.returncode == 0, f"project init failed for {surface.name}:\n{init.stdout}\n{init.stderr}"
    if built_base:
        selected = subprocess.run(
            [str(executable), "project", "config", "authorize", "base-image", built_base],
            cwd=workspace, env=environment, text=True, capture_output=True, stdin=subprocess.DEVNULL,
            check=False, timeout=300.0,
        )
        (evidence / "select-base.log").write_text(selected.stdout + selected.stderr, encoding="utf-8")
        assert selected.returncode == 0, selected.stderr


def stop_session(facts: SessionFacts) -> None:
    command("docker", "stop", "--time", "30", facts.container, check=False, timeout=60.0)
    if facts.launcher is not None:
        try:
            facts.launcher.wait(timeout=90.0)
        except subprocess.TimeoutExpired:
            facts.launcher.kill()
            facts.launcher.wait(timeout=30.0)
    command("docker", "rm", "--force", facts.container, check=False, timeout=60.0)


@contextmanager
def launched_ide(executable: Path, surface: IdeSurface, workspace: Path,
                 evidence: Path, container: str, *, own_session: bool = False,
                 run_arguments: tuple[str, ...] = ()) -> Iterator[SessionFacts]:
    """Launch an initialized project, also used for a bounded persistence relaunch.

    With ``own_session`` the launcher leads its own process group, as it
    does in a terminal, so that a test can deliver SIGINT to the group the
    way Ctrl+C does, launcher and docker client alike. ``run_arguments``
    are given to ``project run`` as an adopter would type them, for a
    launch that departs from the project's saved selection; ``surface`` is
    then the IDE that launch is expected to run.
    """
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = evidence / "launcher.log"
    with log_path.open("wb") as log:
        launcher = subprocess.Popen(
            [str(executable), "project", "run", "--no-update-check", "--name", container, *run_arguments],
            cwd=workspace, env=dict(os.environ, BROWSER="true"), stdout=log,
            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=own_session,
        )
    facts = SessionFacts(surface, container, "", workspace, log_path, launcher)
    try:
        url = wait_for_desktop_url(launcher, log_path)
        runtime = json.loads(command("docker", "exec", container, "cat", "/etc/devcapsule/runtime-plan.json").stdout)
        assert runtime["component"]["id"] == surface.name
        yield SessionFacts(surface, container, url, workspace, log_path, launcher, runtime["project_path"])
    finally:
        stop_session(facts)
        absent = command("docker", "inspect", container, check=False).returncode != 0
        (evidence / "cleanup.json").write_text(json.dumps({"container_removed": absent}) + "\n", encoding="utf-8")
        assert absent, f"Test-owned container remains: {container}"


def wait_for_desktop_url(launcher: subprocess.Popen[bytes], launcher_log: Path) -> str:
    """Return the desktop URL once the launcher prints it; fail if it exits first."""
    return _wait_for_ready_url(launcher, launcher_log, DESKTOP_READY, "desktop", announced=DESKTOP_ANNOUNCED)


def wait_for_console_url(launcher: subprocess.Popen[bytes], launcher_log: Path) -> str:
    """Return the web console URL once the launcher says the console answers."""
    return _wait_for_ready_url(launcher, launcher_log, CONSOLE_READY, "web console", timeout=120.0)


def _wait_for_ready_url(launcher: subprocess.Popen[bytes], launcher_log: Path, pattern: re.Pattern[str],
                        what: str, timeout: float = LAUNCH_TIMEOUT,
                        announced: re.Pattern[str] | None = None) -> str:
    deadline = time.monotonic() + timeout
    while True:
        text = launcher_log.read_text(encoding="utf-8", errors="replace")
        found = pattern.search(text)
        if found and found.group(1):
            return found.group(1)
        if found and announced and (earlier := announced.search(text, 0, found.start())):
            return earlier.group(1)
        if found:
            raise AssertionError(f"the {what} became ready without a URL announced before it:\n{text[-4000:]}")
        if launcher.poll() is not None:
            raise AssertionError(f"launcher exited {launcher.returncode} before publishing a {what} URL:\n{text}")
        if time.monotonic() > deadline:
            raise AssertionError(f"no {what} URL within {timeout:.0f}s:\n{text[-4000:]}")
        time.sleep(1.0)


WINDOW_PROBE = r'''
import glob, json, os, socket, struct

def x_windows(display_number, xauthority):
    # A minimal X11 client: the setup handshake, InternAtom and GetProperty,
    # enough to list the top-level windows the window manager tracks and read
    # each one's class and title. The image needs no X tools for this.
    cookie = open(xauthority, "rb").read()
    def field(buf, off):
        n = struct.unpack(">H", buf[off:off + 2])[0]
        return buf[off + 2:off + 2 + n], off + 2 + n
    off = 2
    _, off = field(cookie, off); _, off = field(cookie, off)
    proto, off = field(cookie, off); data, off = field(cookie, off)
    pad = lambda b: b + b"\0" * ((4 - len(b) % 4) % 4)
    s = socket.socket(socket.AF_UNIX); s.settimeout(5); s.connect(f"/tmp/.X11-unix/X{display_number}")
    def recv_exact(n):
        out = b""
        while len(out) < n:
            chunk = s.recv(n - len(out))
            if not chunk:
                raise RuntimeError("X connection closed")
            out += chunk
        return out
    s.sendall(struct.pack("<BxHHHHxx", 0x6C, 11, 0, len(proto), len(data)) + pad(proto) + pad(data))
    head = recv_exact(8)
    if head[0] != 1:
        raise RuntimeError("X setup refused")
    body = recv_exact(struct.unpack("<H", head[6:8])[0] * 4)
    vendor_len = struct.unpack("<H", body[16:18])[0]
    nformats = body[21]
    root = struct.unpack("<I", body[32 + len(pad(b"x" * vendor_len)) + 8 * nformats:][:4])[0]
    def intern(name):
        s.sendall(struct.pack("<BBHHxx", 16, 0, 2 + len(pad(name)) // 4, len(name)) + pad(name))
        return struct.unpack("<I", recv_exact(32)[8:12])[0]
    def get_property(window, atom):
        s.sendall(struct.pack("<BBHIIIII", 20, 0, 6, window, atom, 0, 0, 1024))
        reply = recv_exact(32)
        fmt = reply[1]
        length = struct.unpack("<I", reply[4:8])[0] * 4
        count = struct.unpack("<I", reply[16:20])[0]
        payload = recv_exact(length)
        if fmt == 8:
            return payload[:count].decode(errors="replace")
        if fmt == 32:
            return list(struct.unpack("<%dI" % count, payload[:4 * count]))
        return None
    windows = get_property(root, intern(b"_NET_CLIENT_LIST")) or []
    facts = []
    for window in windows:
        facts.append({
            "id": window,
            "class": (get_property(window, intern(b"WM_CLASS")) or "").replace("\0", " ").strip(),
            "name": get_property(window, intern(b"_NET_WM_NAME")) or get_property(window, intern(b"WM_NAME")) or "",
        })
    s.close()
    return facts

display = sorted(os.listdir("/tmp/.X11-unix"))[0][1:]
xauthority = sorted(glob.glob("/tmp/devcapsule-runtime-*/display/Xauthority"))[0]
print(json.dumps({"display": display, "windows": x_windows(display, xauthority)}))
'''


def top_level_windows(container: str) -> list[dict[str, object]]:
    """The X11 top-level windows on the capsule's display, with class and title."""
    probe = command("docker", "exec", container, "python3", "-c", WINDOW_PROBE, check=False, timeout=30.0)
    if probe.returncode != 0:
        return []
    windows = json.loads(probe.stdout)["windows"]
    assert isinstance(windows, list)
    return windows


def wait_for_ide_window(facts: SessionFacts) -> dict[str, object]:
    """Poll the display until a window of the surface's class exists; return it."""
    deadline = time.monotonic() + facts.surface.ready_timeout
    seen: list[dict[str, object]] = []
    while True:
        seen = top_level_windows(facts.container)
        for window in seen:
            if facts.surface.window_class.lower() in str(window["class"]).lower():
                if str(window.get("name", "")).lower() == "start failed":
                    raise AssertionError(f"{facts.surface.name} displayed a startup failure dialog")
                return window
        if time.monotonic() > deadline:
            raise AssertionError(
                f"no {facts.surface.window_class!r} window within {facts.surface.ready_timeout:.0f}s; "
                f"windows seen: {seen}\nlauncher log tail:\n"
                f"{facts.launcher_log.read_text(encoding='utf-8', errors='replace')[-3000:]}"
            )
        time.sleep(2.0)


def desktop_page_answers(desktop_url: str, *, patience: float = 30.0) -> int:
    """The HTTP status of the desktop page behind the URL the launcher printed.

    The launcher prints the ready line once the bridge answered it, so a
    refused connection here is a race with the port forward, not a verdict;
    retry within ``patience`` and let the last error speak if it persists.
    """
    import http.client
    from urllib.parse import urlsplit

    parts = urlsplit(desktop_url)
    deadline = time.monotonic() + patience
    while True:
        connection = http.client.HTTPConnection(parts.hostname or "127.0.0.1", parts.port or 80, timeout=10)
        try:
            connection.request("GET", f"{parts.path}?{parts.query}")
            return connection.getresponse().status
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1.0)
        finally:
            connection.close()


def capture_desktop(session: SessionFacts, evidence: Path) -> dict[str, object] | None:
    """Record the desktop through a headless browser; return pixel facts.

    Leaves ``desktop.png``, the canvas when the IDE was judged alive, and
    ``desktop.webm``, a recording of the whole browser session from connect
    to capture, both under ``evidence``. Returns ``None`` when Playwright or
    its browser is not installed: the pixel evidence is optional, the X11
    facts are not. The canvas follows the browser size (``resize=remote``),
    so a fixed viewport fixes the framebuffer too.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore[import-not-found,unused-ignore]
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        return None
    from tests.e2e.browser_session import smoke_browser

    viewport = {"width": 1600, "height": 1000}
    try:
        with sync_playwright() as playwright, smoke_browser(playwright, session, evidence) as browser:
            context = browser.new_context(
                viewport=viewport, record_video_dir=str(evidence), record_video_size=viewport
            )
            page = context.new_page()
            page.goto(session.desktop_url, wait_until="load")
            canvas = page.locator("canvas").first
            canvas.wait_for(state="visible", timeout=60_000)
            page.wait_for_timeout(4_000)
            canvas.screenshot(path=str(evidence / "desktop.png"))
            # Count distinct colours on a coarse grid: a bare desktop has a
            # handful, an IDE window has hundreds. Read in-page, so the test
            # needs no image library.
            pixel_facts = canvas.evaluate(
                """(c) => {
                    const ctx = c.getContext('2d');
                    const data = ctx.getImageData(0, 0, c.width, c.height).data;
                    const colours = new Set();
                    for (let y = 0; y < c.height; y += 8) {
                        for (let x = 0; x < c.width; x += 8) {
                            const i = (y * c.width + x) * 4;
                            colours.add((data[i] << 16) | (data[i + 1] << 8) | data[i + 2]);
                        }
                    }
                    return { width: c.width, height: c.height, distinctColours: colours.size };
                }"""
            )
            assert isinstance(pixel_facts, dict)
            video = page.video
            context.close()  # the recording is finalized by closing the context
            if video is not None:
                video.save_as(str(evidence / "desktop.webm"))
                video.delete()
                pixel_facts["video"] = "desktop.webm"
            return pixel_facts
    except PlaywrightError:
        return None
