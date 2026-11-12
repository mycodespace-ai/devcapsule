"""Host side of the contained display: port, URL, readiness, opener choice."""

from __future__ import annotations

import socket
from threading import Event
from unittest.mock import patch

import pytest

from devcapsule.compat import CliError
from devcapsule.display_client import (
    accepts_connections,
    allocate_loopback_port,
    default_opener,
    display_url,
    new_display_token,
    watch_display_ready,
)
from devcapsule.host_open import HOST_OPEN_SOCKET_ENV, HostOpenError

pytestmark = pytest.mark.legacy


def test_token_and_port_are_fresh_and_usable() -> None:
    token = new_display_token()
    assert len(token) == 48 and token != new_display_token()
    port = allocate_loopback_port()
    assert 0 < port < 65536
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))  # still free a moment later


def test_display_url_autoconnects_through_the_token_path() -> None:
    url = display_url(6080, "abc123")
    assert url == "http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=remote&path=websockify%3Ftoken%3Dabc123"


@pytest.mark.parametrize("label", ["Contained display", "Web console"])
def test_watcher_opens_once_the_port_answers_and_reports_opener_failure(
    capsys: pytest.CaptureFixture[str], label: str,
) -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)  # each probe leaves one accepted-but-unread connection behind
    port = listener.getsockname()[1]
    opened: list[str] = []
    try:
        assert accepts_connections(port)
        watch_display_ready(port, "http://u", opened.append, Event()).join(timeout=10)
        assert opened == ["http://u"]
        assert capsys.readouterr().err == ""  # the opener, not the watcher, reports what it did

        def failing(url: str) -> None:
            raise HostOpenError("no browser")

        watch_display_ready(port, "http://u", failing, Event(), label=label).join(timeout=10)
        assert f"{label} is ready but could not be opened (no browser); open it yourself: http://u" in capsys.readouterr().err
    finally:
        listener.close()


@pytest.mark.parametrize("label", ["Contained display", "Web console"])
def test_watcher_gives_up_on_timeout_or_stop(capsys: pytest.CaptureFixture[str], label: str) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    assert not accepts_connections(port)
    opened: list[str] = []
    watch_display_ready(port, "http://u", opened.append, Event(), timeout=0.3, label=label).join(timeout=10)
    assert opened == []
    assert f"{label} did not answer on port {port} within 0.3s" in capsys.readouterr().err
    stop = Event()
    thread = watch_display_ready(port, "http://u", opened.append, stop, timeout=60)
    stop.set()
    thread.join(timeout=10)
    assert not thread.is_alive() and opened == []


@pytest.mark.parametrize("label", ["Contained display", "Web console"])
def test_default_opener_prefers_the_host_bridge_inside_a_capsule(capsys: pytest.CaptureFixture[str], label: str) -> None:
    with patch("devcapsule.display_client.in_container", return_value=True):
        default_opener({}, label=label)("http://u")
        assert f"{label} is ready; open it in a browser: http://u" in capsys.readouterr().err
        with patch("devcapsule.display_client.open_host_url") as bridge:
            default_opener({HOST_OPEN_SOCKET_ENV: "/run/bridge.sock"}, label=label)("http://u")
        bridge.assert_called_once()
        assert bridge.call_args.args == ("http://u",)
        assert f"{label} is ready; opened through the host-browser bridge" in capsys.readouterr().err
    with (
        patch("devcapsule.display_client.in_container", return_value=False),
        patch("devcapsule.display_client.webbrowser.open", return_value=False) as browser,
    ):
        with pytest.raises(HostOpenError, match="no browser could be started"):
            default_opener({}, label=label)("http://u")
        browser.assert_called_once_with("http://u", new=2)
    with (
        patch("devcapsule.display_client.in_container", return_value=False),
        patch("devcapsule.display_client.webbrowser.open", return_value=True),
    ):
        default_opener({}, label=label)("http://u")
        assert f"{label} is ready; opened in your browser" in capsys.readouterr().err


def test_transport_selection_is_shared_and_stage_aware() -> None:
    from devcapsule.display_client import select_display_transport

    contained = {"devcapsule.base.display": "contained"}
    assert select_display_transport({}, host_x11_answer=None)[0] == "host-x11"
    with pytest.raises(CliError, match="Host X11 is explicitly denied"):
        select_display_transport({}, host_x11_answer=False)
    assert select_display_transport(contained, host_x11_answer=True)[0] == "host-x11"
    assert select_display_transport(contained, host_x11_answer=False) == (
        "contained",
        "Display: contained desktop, reached through your browser; no host X session is shared.",
    )
    # Unanswered means the contained desktop: adopters do nothing to get the safe default.
    assert select_display_transport(contained, host_x11_answer=None)[0] == "contained"


def test_console_url_carries_the_token_once_in_the_query() -> None:
    from devcapsule.display_client import CONSOLE_TOKEN_DESTINATION, CONTAINER_CONSOLE_PORT, console_url, new_run_token

    token = new_run_token()
    assert console_url(45678, token) == f"http://127.0.0.1:45678/?token={token}"
    assert console_url(1, "a b/c") == "http://127.0.0.1:1/?token=a%20b%2Fc"
    assert CONSOLE_TOKEN_DESTINATION != "/run/devcapsule-display-token"
    assert CONTAINER_CONSOLE_PORT != 6080


def test_print_only_opener_names_what_it_announces(capsys) -> None:
    from devcapsule.display_client import print_only_opener

    print_only_opener("Web console")("http://127.0.0.1:1/?token=x")
    assert capsys.readouterr().err == "Web console is ready; open it in a browser: http://127.0.0.1:1/?token=x\n"
