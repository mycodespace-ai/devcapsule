from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from devcapsule import cli
from devcapsule.platforms import HostOs
from devcapsule.host_open import (
    HOST_OPEN_SOCKET_ENV,
    MAX_URL_BYTES,
    HostOpenBroker,
    HostOpenError,
    host_open_bridge,
    open_host_url,
    validate_host_url,
)

pytestmark = pytest.mark.legacy


@pytest.mark.skipif(sys.platform != "linux", reason="the broker reads SO_PEERCRED, which only Linux has")
def test_broker_forwards_one_exact_url_without_shell_parsing(tmp_path: Path) -> None:
    path = tmp_path / "host-open.sock"
    run = Mock(return_value=SimpleNamespace(returncode=0))
    url = "https://example.test/path?a=one&b=%24%28touch%20nope%29#fragment"

    with (
        patch("devcapsule.host_open.subprocess.run", run),
        HostOpenBroker(path, opener=("test-host-opener",), environ={"DISPLAY": ":1"}),
    ):
        assert path.stat().st_mode & 0o777 == 0o600
        open_host_url(url, socket_path=path)

    assert not path.exists()
    run.assert_called_once_with(
        ["test-host-opener", url],
        check=False,
        env={"DISPLAY": ":1"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10.0,
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.test/no-scheme",
        "file:///etc/passwd",
        "mailto:developer@example.test",
        "javascript:alert(1)",
        "https://example.test/line\nbreak",
        "https:///missing-host",
    ],
)
def test_url_validation_rejects_everything_outside_absolute_http_https(url: str) -> None:
    with pytest.raises(HostOpenError):
        validate_host_url(url)


def test_url_validation_rejects_oversized_input() -> None:
    with pytest.raises(HostOpenError, match="size limit"):
        validate_host_url("https://example.test/" + "a" * MAX_URL_BYTES)


def test_broker_rejects_malformed_protocol_without_invoking_opener(tmp_path: Path) -> None:
    path = tmp_path / "host-open.sock"
    run = Mock()

    with (
        patch("devcapsule.host_open.subprocess.run", run),
        HostOpenBroker(path),
        socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection,
    ):
        connection.settimeout(2.0)
        connection.connect(str(path))
        connection.sendall(b'{"schema_version":2,"url":"https://example.test"}\n')
        response = b""
        while not response.endswith(b"\n"):
            response += connection.recv(4096)

    assert json.loads(response)["ok"] is False
    run.assert_not_called()


@pytest.mark.skipif(sys.platform != "linux", reason="the broker reads SO_PEERCRED, which only Linux has")
def test_broker_applies_a_bounded_request_rate(tmp_path: Path) -> None:
    path = tmp_path / "host-open.sock"
    run = Mock(return_value=SimpleNamespace(returncode=0))

    with (
        patch("devcapsule.host_open.RATE_LIMIT_REQUESTS", 1),
        patch("devcapsule.host_open.subprocess.run", run),
        HostOpenBroker(path),
    ):
        open_host_url("https://example.test/first", socket_path=path)
        with pytest.raises(HostOpenError, match="rate limit"):
            open_host_url("https://example.test/second", socket_path=path)

    assert run.call_count == 1


def test_broker_rejects_a_different_peer_uid(tmp_path: Path) -> None:
    path = tmp_path / "host-open.sock"
    run = Mock()

    with (
        patch("devcapsule.host_open._peer_uid", return_value=os.getuid() + 1),
        patch("devcapsule.host_open.subprocess.run", run),
        HostOpenBroker(path),
        pytest.raises(HostOpenError, match="does not own"),
    ):
        open_host_url("https://example.test", socket_path=path)

    run.assert_not_called()


@pytest.mark.skipif(sys.platform != "linux", reason="the broker reads SO_PEERCRED, which only Linux has")
def test_broker_reports_host_opener_timeout(tmp_path: Path) -> None:
    path = tmp_path / "host-open.sock"
    run = Mock(side_effect=subprocess.TimeoutExpired(["xdg-open"], 0.1))

    with (
        patch("devcapsule.host_open.subprocess.run", run),
        HostOpenBroker(path, opener_timeout=0.1),
        pytest.raises(HostOpenError, match="timed out"),
    ):
        open_host_url("https://example.test", socket_path=path)


@pytest.mark.skipif(sys.platform != "linux", reason="the broker reads SO_PEERCRED, which only Linux has")
def test_client_reports_missing_and_failed_brokers_without_exposing_url(tmp_path: Path) -> None:
    url = "https://example.test/path?secret=do-not-report"
    with pytest.raises(HostOpenError, match="absent") as missing:
        open_host_url(url, socket_path=tmp_path / "missing.sock")
    assert "do-not-report" not in str(missing.value)

    path = tmp_path / "host-open.sock"
    run = Mock(return_value=SimpleNamespace(returncode=7))
    with (
        patch("devcapsule.host_open.subprocess.run", run),
        HostOpenBroker(path),
        pytest.raises(HostOpenError, match="failure status") as failed,
    ):
        open_host_url(url, socket_path=path)
    assert "do-not-report" not in str(failed.value)


def test_bridge_reuses_only_an_explicit_inherited_socket(tmp_path: Path) -> None:
    path = tmp_path / "inherited.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as inherited:
        inherited.bind(str(path))
        with (
            patch("devcapsule.host_open.in_container", return_value=True),
            patch("devcapsule.host_open.HOST_OPEN_SOCKET_DESTINATION", path),
        ):
            with host_open_bridge(
                {HOST_OPEN_SOCKET_ENV: str(path)}, enabled=True
            ) as selected:
                assert selected == path
            with host_open_bridge({}, enabled=True) as absent:
                assert absent is None
            with host_open_bridge(
                {HOST_OPEN_SOCKET_ENV: str(path)}, enabled=False
            ) as disabled:
                assert disabled is None


@pytest.mark.skipif(sys.platform != "linux", reason="the broker reads SO_PEERCRED, which only Linux has")
def test_physical_host_bridge_owns_and_cleans_broker(tmp_path: Path) -> None:
    run = Mock(return_value=SimpleNamespace(returncode=0))
    env = {"XDG_RUNTIME_DIR": str(tmp_path), "DISPLAY": ":1"}

    with (
        patch("devcapsule.host_open.in_container", return_value=False),
        patch("devcapsule.host_open.HostOs.current", return_value=HostOs.LINUX),
        patch("devcapsule.host_open.subprocess.run", run),
        host_open_bridge(env, enabled=True, opener=("test-opener",)) as path,
    ):
        assert path is not None and path.is_socket()
        root = path.parent
        assert root.stat().st_mode & 0o777 == 0o700
        open_host_url("https://example.test", socket_path=path)

    assert not root.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="the broker reads SO_PEERCRED, which only Linux has")
def test_hidden_host_open_command_uses_authorized_environment(tmp_path: Path, capsys) -> None:
    assert "host-open" not in cli.command_names()
    assert "host-open" in cli.command_names(include_hidden=True)
    path = tmp_path / "host-open.sock"
    with (
        patch("devcapsule.host_open.subprocess.run", return_value=SimpleNamespace(returncode=0)),
        HostOpenBroker(path),
        patch.dict(os.environ, {HOST_OPEN_SOCKET_ENV: str(path)}, clear=False),
    ):
        assert cli.main(["host-open", "https://example.test/docs?a=1&b=2"]) == 0

    assert capsys.readouterr().err == ""
