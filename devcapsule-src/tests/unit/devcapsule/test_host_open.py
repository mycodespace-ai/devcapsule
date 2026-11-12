"""Unit tests of ``devcapsule/host_open.py``: the host-browser bridge on a host that cannot carry it.

The host is named by patching ``HostOs.current``; nothing binds a socket.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from devcapsule.host_open import host_open_bridge
from devcapsule.platforms import HostOs


def test_macos_host_bridge_is_unavailable_with_a_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """On a host whose Unix sockets Docker cannot bind into a capsule, the bridge yields no socket,
    warns, and creates nothing: the optional integration degrades instead of failing the launch."""
    with (
        patch("devcapsule.host_open.in_container", return_value=False),
        patch("devcapsule.host_open.HostOs.current", return_value=HostOs.DARWIN),
        host_open_bridge({"XDG_RUNTIME_DIR": str(tmp_path)}, enabled=True) as path,
    ):
        assert path is None
    assert "host-browser is unavailable on macOS" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
