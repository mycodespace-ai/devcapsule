"""Unit tests of ``devcapsule/platforms.py``: the capsule platforms, the host operating systems, and what each host runs.

A test of a particular host names it with ``on_host`` and carries ``own_host_patches``.
"""
from __future__ import annotations

import pytest

from devcapsule import platforms
from devcapsule.platforms import HostOs, Platform, UnsupportedPlatformError


def on_host(monkeypatch: pytest.MonkeyPatch, system: str, machine: str) -> None:
    """Make this host the one ``platform.system()`` and ``platform.machine()`` would name."""
    monkeypatch.setattr(platforms.host_platform, "system", lambda: system)
    monkeypatch.setattr(platforms.host_platform, "machine", lambda: machine)


def test_platform_values_are_the_wire_format() -> None:
    """Each platform's value is its wire format, and the member formats as that value in a lock's name."""
    assert Platform.LINUX_AMD64.value == "linux-amd64"
    # StrEnum: the member formats as its value wherever locks and filenames
    # interpolate it.
    assert f"devcapsule.{Platform.LINUX_AMD64}.lock" == "devcapsule.linux-amd64.lock"
    assert Platform.LINUX_ARM64.value == "linux-arm64"


@pytest.mark.own_host_patches
@pytest.mark.parametrize("system,machine,runnable,created", [
    ("Linux", "x86_64", ("linux-amd64",), "linux-amd64"),
    ("Linux", "aarch64", ("linux-arm64",), "linux-arm64"),
    ("Darwin", "x86_64", ("linux-amd64",), "linux-amd64"),
    ("Darwin", "arm64", ("linux-arm64", "linux-amd64"), "linux-arm64"),
])
def test_each_host_runs_its_platforms_and_creates_projects_for_one(monkeypatch, system, machine, runnable, created) -> None:
    """Each supported host runs its capsule platforms, native first, and creates new projects for its native one."""
    # A Mac runs Linux capsules. Apple Silicon runs linux-arm64 natively and
    # linux-amd64 under emulation; a new project defaults to the native one.
    on_host(monkeypatch, system, machine)
    assert tuple(str(platform) for platform in Platform.runnable()) == runnable
    assert Platform.current() is Platform.parse(created)


def test_emulation_is_the_daemons() -> None:
    """A daemon of another architecture is told the platform, as an option or a value; a native daemon is told nothing."""
    # Docker Desktop on Apple Silicon is an arm64 daemon, whatever runs the launcher.
    assert Platform.LINUX_AMD64.emulated_docker_platform("arm64") == "linux/amd64"
    assert Platform.LINUX_ARM64.emulated_docker_platform("arm64") is None
    assert Platform.LINUX_AMD64.docker_platform_args("arm64") == ["--platform=linux/amd64"]
    assert Platform.LINUX_AMD64.docker_platform_args("amd64") == []
    assert Platform.LINUX_ARM64.docker_platform_args("arm64") == []


@pytest.mark.own_host_patches
@pytest.mark.parametrize("system,machine,message", [
    ("Linux", "riscv64", "supported platforms: linux-amd64, linux-arm64"),
    ("Darwin", "ppc", "supported platforms: linux-amd64, linux-arm64"),
    ("Windows", "AMD64", "supported: linux, darwin"),
])
def test_current_refuses_a_host_without_a_capsule_platform(monkeypatch, system, machine, message) -> None:
    """A host with no capsule platform is refused, naming the supported ones."""
    on_host(monkeypatch, system, machine)
    with pytest.raises(UnsupportedPlatformError, match=message):
        Platform.current()


def test_an_elf_machine_names_its_platform() -> None:
    """An ELF machine value names the platform its executables run on, and another architecture none."""
    assert Platform.of_elf_machine(0x3E) is Platform.LINUX_AMD64
    assert Platform.of_elf_machine(0xB7) is Platform.LINUX_ARM64
    assert Platform.of_elf_machine(0xF3) is None


def test_docker_desktop_facts_are_the_macos_hosts() -> None:
    """Docker Desktop's conventions are the macOS host's properties, and none of them the Linux host's."""
    assert HostOs.DARWIN.docker_socket_gid == 0 and HostOs.LINUX.docker_socket_gid is None
    assert not HostOs.DARWIN.host_network_reachable and HostOs.LINUX.host_network_reachable
    assert not HostOs.DARWIN.binds_unix_sockets and HostOs.LINUX.binds_unix_sockets
    assert not HostOs.DARWIN.chown_reaches_bind_mounts and HostOs.LINUX.chown_reaches_bind_mounts


def test_docker_spelling_and_architecture() -> None:
    """Each platform has Docker's spelling of it and its CPU architecture."""
    assert Platform.LINUX_AMD64.docker_platform == "linux/amd64"
    assert Platform.LINUX_AMD64.architecture == "amd64"
    assert Platform.LINUX_ARM64.docker_platform == "linux/arm64"
    assert Platform.LINUX_ARM64.architecture == "arm64"


@pytest.mark.own_host_patches
def test_host_os_names_linux_and_macos_only(monkeypatch) -> None:
    """The host operating system is Linux or macOS; any other host is refused."""
    on_host(monkeypatch, "Darwin", "arm64")
    assert HostOs.current() is HostOs.DARWIN
    on_host(monkeypatch, "Linux", "x86_64")
    assert HostOs.current() is HostOs.LINUX
    on_host(monkeypatch, "Windows", "AMD64")
    with pytest.raises(UnsupportedPlatformError, match="'windows'"):
        HostOs.current()
