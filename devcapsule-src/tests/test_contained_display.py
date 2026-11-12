"""The contained display: plan contract, per-run files, and declared children."""

from __future__ import annotations

import json
from pathlib import Path
import re
import struct

import pytest

from devcapsule.container_runtime.contract import DisplayPlan, RuntimePlan, RuntimePlanError
from devcapsule.container_runtime.display import (
    NOVNC_CHILD,
    PANEL_CHILD,
    WINDOW_MANAGER_CHILD,
    XVNC_CHILD,
    openbox_configuration_text,
    panel_configuration_text,
    prepare_contained_display,
    read_token,
    select_display_number,
    write_xauthority,
    x_socket_path,
)
from devcapsule.container_runtime.entrypoint import run

from tests.test_runtime_entrypoint import SupervisorCapture, captured_supervisor, runtime_document

pytestmark = pytest.mark.legacy

_ = captured_supervisor  # re-exported fixture


def contained_document(tmp_path: Path, token: str = "a1b2c3") -> dict[str, object]:
    token_path = tmp_path / "display-token"
    token_path.write_text(token + "\n", encoding="utf-8")
    document = runtime_document(tmp_path)
    document["display"] = {
        "transport": "contained",
        "listen_address": "0.0.0.0",
        "port": 6080,
        "token_path": str(token_path),
    }
    return document


def test_contract_round_trips_both_transports(tmp_path: Path) -> None:
    contained = RuntimePlan.from_mapping(contained_document(tmp_path))
    assert contained.display is not None and contained.display.is_contained
    assert contained.display_transport() == "contained"
    assert RuntimePlan.from_json(contained.to_json()) == contained
    assert json.loads(contained.to_json())["display"]["port"] == 6080

    passthrough = RuntimePlan.from_mapping(runtime_document(tmp_path)).with_display(DisplayPlan.host_x11())
    assert passthrough.display_transport() == "host-x11"
    assert json.loads(passthrough.to_json())["display"] == {"transport": "host-x11"}
    assert RuntimePlan.from_json(passthrough.to_json()) == passthrough

    # Plans from before the section existed keep meaning passthrough.
    assert RuntimePlan.from_mapping(runtime_document(tmp_path)).display_transport() == "host-x11"


@pytest.mark.parametrize(
    ("display", "message"),
    [
        ({"transport": "xephyr"}, "display.transport must be one of"),
        ({"transport": "host-x11", "port": 1}, "must not carry port"),
        ({"transport": "contained", "listen_address": "0.0.0.0", "port": 0, "token_path": "/t"}, "display.port"),
        ({"transport": "contained", "listen_address": "0.0.0.0", "port": 6080, "token_path": "t"}, "token_path"),
        ({"transport": "contained", "listen_address": "", "port": 6080, "token_path": "/t"}, "listen_address"),
        ("contained", "display must be an object"),
    ],
)
def test_contract_rejects_malformed_display(tmp_path: Path, display: object, message: str) -> None:
    document = runtime_document(tmp_path)
    document["display"] = display
    with pytest.raises(RuntimePlanError, match=message):
        RuntimePlan.from_mapping(document)


def test_xauthority_entry_is_a_wildcard_cookie_for_the_display(tmp_path: Path) -> None:
    path = tmp_path / "Xauthority"
    write_xauthority(path, 1, b"\x01" * 16)
    body = path.read_bytes()
    assert path.stat().st_mode & 0o777 == 0o600
    family, = struct.unpack(">H", body[:2])
    assert family == 0xFFFF
    # address (empty), number "1", protocol name, 16-byte cookie
    assert body[2:] == b"\x00\x00" + b"\x00\x011" + b"\x00\x12MIT-MAGIC-COOKIE-1" + b"\x00\x10" + b"\x01" * 16


def test_token_must_be_one_clean_line(tmp_path: Path) -> None:
    good = tmp_path / "good"
    good.write_text("  f00d\n", encoding="utf-8")
    assert read_token(str(good)) == "f00d"
    for content in ("", "two words", "colon:here"):
        bad = tmp_path / "bad"
        bad.write_text(content, encoding="utf-8")
        with pytest.raises(RuntimePlanError, match="empty or malformed"):
            read_token(str(bad))
    with pytest.raises(RuntimePlanError, match="cannot read the display token"):
        read_token(str(tmp_path / "missing"))


def test_prepared_display_declares_children_and_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("devcapsule.container_runtime.display.os.geteuid", lambda: 1000)
    monkeypatch.setattr("devcapsule.container_runtime.display.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("devcapsule.container_runtime.display.X_SOCKET_DIRECTORY", str(tmp_path / ".X11-unix"))
    plan = RuntimePlan.from_mapping(contained_document(tmp_path, token="deadbeef"))
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(mode=0o700)

    display = prepare_contained_display(plan, str(runtime_dir), lambda command: ("as-user", *command))

    assert [child.name for child in display.children] == [XVNC_CHILD, WINDOW_MANAGER_CHILD, PANEL_CHILD, NOVNC_CHILD]
    assert not any(child.foreground for child in display.children)
    xvnc, window_manager, panel, novnc = display.children
    assert display.display_number >= 10
    assert xvnc.command[:3] == ("as-user", "Xvnc", f":{display.display_number}")
    # Filesystem socket only: never an abstract socket, never TCP (T2/T4).
    assert xvnc.command[xvnc.command.index("-nolisten"):][:4] == ("-nolisten", "local", "-nolisten", "tcp")
    assert ("-rfbport", "-1") == xvnc.command[xvnc.command.index("-rfbport"):][:2]
    assert ("-rfbunixpath", display.rfb_socket_path) == xvnc.command[xvnc.command.index("-rfbunixpath"):][:2]
    assert ("-auth", display.xauthority_path) == xvnc.command[xvnc.command.index("-auth"):][:2]
    assert xvnc.ready is not None and xvnc.ready() is False  # no X server in the test process
    assert window_manager.command == ("as-user", "openbox", "--config-file", display.openbox_configuration_path)
    assert Path(display.openbox_configuration_path).read_text(encoding="utf-8") == openbox_configuration_text()
    assert panel.command == ("as-user", "tint2", "-c", display.panel_configuration_path)
    assert Path(display.panel_configuration_path).read_text(encoding="utf-8") == panel_configuration_text()
    assert "panel_items = TC" in panel_configuration_text()  # taskbar and clock, nothing else
    assert novnc.command[-1] == "0.0.0.0:6080"
    assert "TokenFile" in novnc.command
    assert novnc.ready is not None and novnc.ready() is False  # nothing listens on 6080 here

    directory = runtime_dir / "display"
    assert directory.stat().st_mode & 0o777 == 0o700
    tokens = directory / "tokens"
    assert tokens.read_text(encoding="utf-8") == f"deadbeef: unix_socket:{display.rfb_socket_path}\n"
    assert tokens.stat().st_mode & 0o777 == 0o600
    # family + empty address + display number + protocol name + 16-byte cookie
    assert Path(display.xauthority_path).stat().st_size == 2 + 2 + (2 + len(str(display.display_number))) + 20 + 18
    assert display.environment == {"DISPLAY": f":{display.display_number}", "XAUTHORITY": display.xauthority_path}
    assert x_socket_path(display.display_number) == f"{tmp_path / '.X11-unix'}/X{display.display_number}"
    # The X socket directory exists before Xvnc starts, sticky and world-writable.
    assert (tmp_path / ".X11-unix").stat().st_mode & 0o7777 == 0o1777


def test_display_number_skips_servers_visible_in_the_namespace_or_socket_directory(tmp_path: Path) -> None:
    # A /proc/net/unix excerpt: the host's :1 (abstract, as seen under host
    # networking) and a filesystem :10 belonging to someone else.
    table = tmp_path / "unix"
    table.write_text(
        "Num RefCount Protocol Flags Type St Inode Path\n"
        "0000000000000000: 00000002 00000000 00010000 0001 01 12345 @/tmp/.X11-unix/X1\n"
        "0000000000000000: 00000002 00000000 00010000 0001 01 12346 /tmp/.X11-unix/X10\n"
        "0000000000000000: 00000002 00000000 00010000 0001 01 12347 /run/other.sock\n",
        encoding="utf-8",
    )
    sockets = tmp_path / ".X11-unix"
    sockets.mkdir()
    (sockets / "X11").touch()
    assert select_display_number(unix_socket_table=str(table), socket_directory=str(sockets)) == 12
    assert select_display_number(first=1, unix_socket_table=str(table), socket_directory=str(sockets)) == 2
    # Unreadable table: only the socket directory counts.
    assert select_display_number(unix_socket_table=str(tmp_path / "missing"), socket_directory=str(sockets)) == 10


def test_prepare_refuses_a_plan_without_the_contained_display(tmp_path: Path) -> None:
    plan = RuntimePlan.from_mapping(runtime_document(tmp_path)).with_display(DisplayPlan.host_x11())
    with pytest.raises(RuntimePlanError, match="does not select the contained display"):
        prepare_contained_display(plan, str(tmp_path), lambda command: command)


def test_panel_is_skipped_and_announced_on_a_base_without_tint2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("devcapsule.container_runtime.display.os.geteuid", lambda: 1000)
    monkeypatch.setattr("devcapsule.container_runtime.display.X_SOCKET_DIRECTORY", str(tmp_path / ".X11-unix"))
    monkeypatch.setattr("devcapsule.container_runtime.display.shutil.which", lambda name: None)
    plan = RuntimePlan.from_mapping(contained_document(tmp_path))
    (tmp_path / "runtime").mkdir(mode=0o700)
    display = prepare_contained_display(plan, str(tmp_path / "runtime"), lambda command: command)
    assert [child.name for child in display.children] == [XVNC_CHILD, WINDOW_MANAGER_CHILD, NOVNC_CHILD]
    assert "no tint2 panel (base recipe 9 adds it)" in capsys.readouterr().err


def test_entrypoint_starts_display_infrastructure_before_the_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_supervisor: type[SupervisorCapture]
) -> None:
    monkeypatch.setattr("devcapsule.container_runtime.display.os.geteuid", lambda: 1000)
    monkeypatch.setattr("devcapsule.container_runtime.display.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("devcapsule.container_runtime.display.X_SOCKET_DIRECTORY", str(tmp_path / ".X11-unix"))
    monkeypatch.delenv("DISPLAY", raising=False)
    plan = RuntimePlan.from_mapping(contained_document(tmp_path))

    assert run(plan) == 42

    (supervisor,) = captured_supervisor.instances
    names = [child.name for child in supervisor.children]
    assert names == [XVNC_CHILD, WINDOW_MANAGER_CHILD, PANEL_CHILD, NOVNC_CHILD, "jetbrains"]
    assert [child.foreground for child in supervisor.children] == [False, False, False, False, True]
    import os

    assert re.fullmatch(r":\d+", os.environ["DISPLAY"])
    assert os.environ["XAUTHORITY"].startswith("/tmp/devcapsule-runtime-1000/display/")


def test_entrypoint_declares_no_display_for_passthrough_or_headless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_supervisor: type[SupervisorCapture]
) -> None:
    passthrough = RuntimePlan.from_mapping(runtime_document(tmp_path)).with_display(DisplayPlan.host_x11())
    assert run(passthrough) == 42
    contained = RuntimePlan.from_mapping(contained_document(tmp_path))
    assert run(contained, job=("pytest",)) == 42

    first, second = captured_supervisor.instances
    assert [child.name for child in first.children] == ["jetbrains"]
    assert [child.name for child in second.children] == ["job"]


def test_openbox_configuration_removes_the_minimize_trap() -> None:
    """The desktop has nowhere for a window to disappear into (owner finding 2026-09-14)."""

    import xml.etree.ElementTree as ET

    ns = {"ob": "http://openbox.org/3.4/rc"}
    root = ET.fromstring(openbox_configuration_text())
    assert root.findtext("ob:desktops/ob:number", namespaces=ns) == "1"
    layout = root.findtext("ob:theme/ob:titleLayout", namespaces=ns)
    assert layout is not None and "I" not in layout and "S" not in layout and "C" in layout
    # The window list is one click away on the background, both buttons.
    for context in root.findall("ob:mouse/ob:context", ns):
        if context.get("name") == "Root":
            menus = {m.text for m in context.findall("ob:mousebind/ob:action/ob:menu", ns)}
            assert menus == {"client-list-combined-menu"}
        if context.get("name") == "Desktop":
            assert not [a for a in context.findall("ob:mousebind/ob:action", ns) if a.get("name") == "GoToDesktop"]
    # Alt+Tab stays for hosts that let it through; no other chord is promised,
    # because hosts reserve unpredictable keys (GNOME owns Alt+backquote).
    keys = {k.get("key"): [a.get("name") for a in k.findall("ob:action", ns)] for k in root.findall("ob:keyboard/ob:keybind", ns)}
    assert keys["A-Tab"] == ["NextWindow"] and "A-grave" not in keys
    # Ordinary windows (the IDE) start maximized; dialogs are untouched.
    apps = root.findall("ob:applications/ob:application", ns)
    assert [(a.get("type"), a.findtext("ob:maximized", namespaces=ns)) for a in apps] == [("normal", "yes")]
    # No reference to the Debian menu file that is absent from the base.
    assert "debian-menu" not in openbox_configuration_text()


def test_xvnc_logs_status_by_default_and_everything_under_a_debug_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_supervisor: type[SupervisorCapture]
) -> None:
    from devcapsule.container_runtime.display import XVNC_LOG_SETTING, XVNC_VERBOSE_LOG_SETTING, xvnc_log_setting
    from devcapsule.logs import LEVEL_ENV

    monkeypatch.setattr("devcapsule.container_runtime.display.os.geteuid", lambda: 1000)
    monkeypatch.setattr("devcapsule.container_runtime.display.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("devcapsule.container_runtime.display.X_SOCKET_DIRECTORY", str(tmp_path / ".X11-unix"))
    monkeypatch.delenv(LEVEL_ENV, raising=False)
    assert run(RuntimePlan.from_mapping(contained_document(tmp_path))) == 42
    (supervisor,) = captured_supervisor.instances
    xvnc = next(child for child in supervisor.children if child.name == XVNC_CHILD)
    assert xvnc.command[-2:] == ("-Log", XVNC_LOG_SETTING) == ("-Log", "*:stderr:10")
    assert xvnc_log_setting({LEVEL_ENV: "debug"}) == XVNC_VERBOSE_LOG_SETTING == "*:stderr:100"
    assert xvnc_log_setting({LEVEL_ENV: "info"}) == XVNC_LOG_SETTING
    assert xvnc_log_setting({LEVEL_ENV: "loud"}) == XVNC_LOG_SETTING
