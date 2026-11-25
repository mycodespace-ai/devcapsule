"""Unit tests of ``devcapsule.github_proxy``: pure gating decisions of ``github_ssh_bridge``.

No sockets are bound and no subprocesses start; every outcome follows from the
explicit arguments passed to ``github_ssh_bridge``. A home is a directory the
test makes under ``tmp_path``. The grants that do start a proxy are in
``tests/integration/test_github_proxy.py``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.github_proxy import SOCKET_DESTINATION, SOCKET_ENV, github_ssh_bridge
from devcapsule.github_transport import GitHubTransportError

NO_HOME = Path("/homes/nobody")
"""A home that a refusal must come before any look into."""


def home_with_keys(root: Path, *names: str) -> Path:
    """A home under ``root`` whose ``.ssh`` directory holds an empty file for each of ``names``."""
    directory = root / "home" / ".ssh"
    directory.mkdir(parents=True)
    for name in names:
        (directory / name).touch()
    return directory.parent


def host_with_ssh(root: Path) -> dict[str, str]:
    """The environment of a host whose ``PATH`` holds one program, an ``ssh`` that is never run."""
    programs = root / "programs"
    programs.mkdir()
    ssh = programs / "ssh"
    ssh.write_text("#!/bin/sh\nexit 1\n")
    ssh.chmod(0o700)
    return {"PATH": str(programs)}


def test_disabled_bridge_yields_none_regardless_of_host_capabilities() -> None:
    """When ssh-proxy is denied, the bridge yields no socket even on unsupported or containerized hosts."""
    with github_ssh_bridge({}, selection=False, home=NO_HOME, containerized=True, binds_unix_sockets=False) as path:
        assert path is None


@pytest.mark.parametrize("selection", [True, "default", "id_work"])
def test_docker_desktop_bridge_is_refused_when_enabled(selection: bool | str) -> None:
    """Granting ssh-proxy on a host that cannot bind Unix sockets fails loudly instead of degrading."""
    with pytest.raises(GitHubTransportError, match="ssh-proxy currently requires .* Docker Desktop"):
        with github_ssh_bridge({}, selection=selection, home=NO_HOME, containerized=False, binds_unix_sockets=False):
            pass


@pytest.mark.parametrize("selection", [True, "default", "id_work"])
@pytest.mark.parametrize("environment", [{}, {SOCKET_ENV: "/tmp/forged.sock"}])
def test_containerized_bridge_requires_an_inherited_canonical_socket(environment: dict[str, str], selection: bool | str) -> None:
    """An inner capsule cannot enable ssh-proxy without the launcher's canonical socket variable, whatever
    key the grant names: the refusal is the missing proxy, and no key is looked for inside a capsule."""
    assert str(SOCKET_DESTINATION) != "/tmp/forged.sock"
    with pytest.raises(GitHubTransportError, match="authorize ssh-proxy on the outside launcher"):
        with github_ssh_bridge(environment, selection=selection, home=NO_HOME, containerized=True, binds_unix_sockets=True):
            pass


def test_host_bridge_requires_openssh_on_path(tmp_path: Path) -> None:
    """Granting ssh-proxy on the host fails clearly when OpenSSH is absent from an empty PATH directory."""
    with pytest.raises(GitHubTransportError, match="ssh-proxy requires OpenSSH"):
        with github_ssh_bridge({"PATH": str(tmp_path)}, selection=True, home=NO_HOME, containerized=False, binds_unix_sockets=True):
            pass


@pytest.mark.parametrize("selection,key", [("id_work", ".ssh/id_work"), ("~/keys/deploy", "keys/deploy")])
def test_host_bridge_refuses_a_named_key_that_is_not_a_file(tmp_path: Path, selection: str, key: str) -> None:
    """A named key that the home does not hold stops the launch before any proxy exists, naming the file looked for."""
    home = home_with_keys(tmp_path, "id_ed25519")

    with pytest.raises(GitHubTransportError) as refused:
        with github_ssh_bridge(host_with_ssh(tmp_path), selection=selection, home=home, containerized=False, binds_unix_sockets=True):
            pytest.fail("a proxy was created")

    assert f"ssh-proxy: the key {home / key} is not a file on this computer" in str(refused.value)


def test_host_bridge_refuses_a_named_key_that_is_a_directory(tmp_path: Path) -> None:
    """A directory under the key's name is not a key."""
    home = home_with_keys(tmp_path)
    (home / ".ssh" / "id_work").mkdir()

    with pytest.raises(GitHubTransportError, match="is not a file on this computer"):
        with github_ssh_bridge(host_with_ssh(tmp_path), selection="id_work", home=home, containerized=False, binds_unix_sockets=True):
            pytest.fail("a proxy was created")


@pytest.mark.parametrize("names,complaint", [
    ((), "found none"),
    (("id_ed25519.pub", "known_hosts"), "found none"),
    (("id_ed25519", "id_rsa"), "found id_ed25519, id_rsa"),
])
def test_host_bridge_refuses_default_without_exactly_one_private_key(tmp_path: Path, names: tuple[str, ...], complaint: str) -> None:
    """``default`` in a home with no private ``id_*`` key, or with two, stops the launch and says which it found."""
    home = home_with_keys(tmp_path, *names)

    with pytest.raises(GitHubTransportError, match=f"ssh-proxy: 'default' expects one private key .* {complaint}"):
        with github_ssh_bridge(host_with_ssh(tmp_path), selection="default", home=home, containerized=False, binds_unix_sockets=True):
            pytest.fail("a proxy was created")


def test_host_bridge_refuses_default_in_a_home_without_an_ssh_directory(tmp_path: Path) -> None:
    """A home with no ``.ssh`` directory holds no key: ``default`` finds none and says so."""
    with pytest.raises(GitHubTransportError, match="found none"):
        with github_ssh_bridge(host_with_ssh(tmp_path), selection="default", home=tmp_path / "absent", containerized=False, binds_unix_sockets=True):
            pytest.fail("a proxy was created")
