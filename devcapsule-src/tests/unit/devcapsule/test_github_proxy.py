"""Unit tests of ``devcapsule.github_proxy``: pure gating decisions of ``github_ssh_bridge``.

No sockets are bound and no subprocesses start; every outcome follows from the
explicit arguments passed to ``github_ssh_bridge``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.github_proxy import SOCKET_DESTINATION, SOCKET_ENV, github_ssh_bridge
from devcapsule.github_transport import GitHubTransportError


def test_disabled_bridge_yields_none_regardless_of_host_capabilities() -> None:
    """When github-ssh is denied, the bridge yields no socket even on unsupported or containerized hosts."""
    with github_ssh_bridge({}, enabled=False, containerized=True, binds_unix_sockets=False) as path:
        assert path is None


def test_docker_desktop_bridge_is_refused_when_enabled() -> None:
    """Enabling github-ssh on a host that cannot bind Unix sockets fails loudly instead of degrading."""
    with pytest.raises(GitHubTransportError, match="Docker Desktop"):
        with github_ssh_bridge({}, enabled=True, containerized=False, binds_unix_sockets=False):
            pass


@pytest.mark.parametrize("environment", [{}, {SOCKET_ENV: "/tmp/forged.sock"}])
def test_containerized_bridge_requires_an_inherited_canonical_socket(environment: dict[str, str]) -> None:
    """An inner capsule cannot enable github-ssh without the launcher's canonical socket variable."""
    assert str(SOCKET_DESTINATION) != "/tmp/forged.sock"
    with pytest.raises(GitHubTransportError, match="outside launcher"):
        with github_ssh_bridge(environment, enabled=True, containerized=True, binds_unix_sockets=True):
            pass


def test_host_bridge_requires_openssh_on_path(tmp_path: Path) -> None:
    """Enabling github-ssh on the host fails clearly when OpenSSH is absent from an empty PATH directory."""
    with pytest.raises(GitHubTransportError, match="OpenSSH"):
        with github_ssh_bridge({"PATH": str(tmp_path)}, enabled=True, containerized=False, binds_unix_sockets=True):
            pass
