"""Tests for the host/platform friction module (D-0006)."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule import platforms
from devcapsule.platforms import HostOs, Platform, UnsupportedPlatformError, XdgHomes

pytestmark = pytest.mark.legacy


def test_platform_values_are_the_wire_format() -> None:
    assert Platform.LINUX_AMD64.value == "linux-amd64"
    # StrEnum: the member formats as its value wherever locks and filenames
    # interpolate it.
    assert f"devcapsule.{Platform.LINUX_AMD64}.lock" == "devcapsule.linux-amd64.lock"
    assert Platform.LINUX_ARM64.value == "linux-arm64"


def test_parse_accepts_every_member_and_only_members() -> None:
    for member in Platform:
        assert Platform.parse(member.value) is member
    with pytest.raises(UnsupportedPlatformError) as failure:
        Platform.parse("windows-arm64")
    message = str(failure.value)
    assert "'windows-arm64'" in message
    assert "linux-amd64" in message


def test_current_returns_a_member_on_a_supported_host() -> None:
    # The test suite only runs on supported platforms, so detection must
    # succeed and agree with parse().
    current = Platform.current()
    assert current in Platform
    assert Platform.parse(current.value) is current


def on_host(monkeypatch: pytest.MonkeyPatch, system: str, machine: str) -> None:
    """Make this host the one ``platform.system()`` and ``platform.machine()`` would name."""
    monkeypatch.setattr(platforms.host_platform, "system", lambda: system)
    monkeypatch.setattr(platforms.host_platform, "machine", lambda: machine)


@pytest.mark.own_host_patches
@pytest.mark.parametrize("system,machine,runnable,created", [
    ("Linux", "x86_64", ("linux-amd64",), "linux-amd64"),
    ("Linux", "aarch64", ("linux-arm64",), "linux-arm64"),
    ("Darwin", "x86_64", ("linux-amd64",), "linux-amd64"),
    ("Darwin", "arm64", ("linux-arm64", "linux-amd64"), "linux-arm64"),
])
def test_each_host_runs_its_platforms_and_creates_projects_for_one(monkeypatch, system, machine, runnable, created) -> None:
    # A Mac runs Linux capsules. Apple Silicon runs linux-arm64 natively and
    # linux-amd64 under emulation; a new project defaults to the native one.
    on_host(monkeypatch, system, machine)
    assert tuple(str(platform) for platform in Platform.runnable()) == runnable
    assert Platform.current() is Platform.parse(created)


def test_emulation_is_the_daemons() -> None:
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
    on_host(monkeypatch, system, machine)
    with pytest.raises(UnsupportedPlatformError, match=message):
        Platform.current()


def test_an_elf_machine_names_its_platform() -> None:
    assert Platform.of_elf_machine(0x3E) is Platform.LINUX_AMD64
    assert Platform.of_elf_machine(0xB7) is Platform.LINUX_ARM64
    assert Platform.of_elf_machine(0xF3) is None


def test_docker_desktop_facts_are_the_macos_hosts() -> None:
    assert HostOs.DARWIN.docker_socket_gid == 0 and HostOs.LINUX.docker_socket_gid is None
    assert not HostOs.DARWIN.host_network_reachable and HostOs.LINUX.host_network_reachable
    assert not HostOs.DARWIN.binds_unix_sockets and HostOs.LINUX.binds_unix_sockets
    assert not HostOs.DARWIN.chown_reaches_bind_mounts and HostOs.LINUX.chown_reaches_bind_mounts


def test_docker_spelling_and_architecture() -> None:
    assert Platform.LINUX_AMD64.docker_platform == "linux/amd64"
    assert Platform.LINUX_AMD64.architecture == "amd64"
    assert Platform.LINUX_ARM64.docker_platform == "linux/arm64"
    assert Platform.LINUX_ARM64.architecture == "arm64"


@pytest.mark.own_host_patches
def test_host_os_names_linux_and_macos_only(monkeypatch) -> None:
    on_host(monkeypatch, "Darwin", "arm64")
    assert HostOs.current() is HostOs.DARWIN
    on_host(monkeypatch, "Linux", "x86_64")
    assert HostOs.current() is HostOs.LINUX
    on_host(monkeypatch, "Windows", "AMD64")
    with pytest.raises(UnsupportedPlatformError, match="'windows'"):
        HostOs.current()


def test_xdg_homes_honor_explicit_overrides() -> None:
    homes = XdgHomes.from_environment(
        {
            "HOME": "/home/dev",
            "XDG_CONFIG_HOME": "/elsewhere/config",
            "XDG_DATA_HOME": "/elsewhere/data",
            "XDG_STATE_HOME": "/elsewhere/state",
            "XDG_CACHE_HOME": "/elsewhere/cache",
        }
    )

    assert homes.config == Path("/elsewhere/config/devcapsule")
    assert homes.data == Path("/elsewhere/data/devcapsule")
    assert homes.state == Path("/elsewhere/state/devcapsule")
    assert homes.cache == Path("/elsewhere/cache/devcapsule")


def test_xdg_homes_fall_back_to_the_specified_defaults() -> None:
    homes = XdgHomes.from_environment({"HOME": "/home/dev"})

    assert homes.config == Path("/home/dev/.config/devcapsule")
    assert homes.data == Path("/home/dev/.local/share/devcapsule")
    assert homes.state == Path("/home/dev/.local/state/devcapsule")
    assert homes.cache == Path("/home/dev/.cache/devcapsule")


def test_xdg_empty_override_means_unset() -> None:
    # The XDG spec treats an empty variable as unset; the derivation must
    # fall back rather than produce a relative path.
    homes = XdgHomes.from_environment({"HOME": "/home/dev", "XDG_CACHE_HOME": ""})

    assert homes.cache == Path("/home/dev/.cache/devcapsule")


@pytest.mark.parametrize("value", ["chosen", "~/chosen", ""])
def test_named_configuration_home(value: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    env = {"HOME": str(tmp_path), "DEVCAPSULE_CONFIG_HOME": value}
    homes = XdgHomes.from_environment(env)
    if not value:
        assert homes == XdgHomes.from_environment({"HOME": str(tmp_path)})
    else:
        root = tmp_path / "chosen"
        assert homes == XdgHomes(root, root / "data", root / "state", root / "cache")


def test_notifications_keep_named_state_directory_no_follow(tmp_path: Path) -> None:
    from devcapsule.notifications import NotificationError, store_in_environment
    root = tmp_path / "chosen"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / "state").symlink_to(elsewhere, target_is_directory=True)
    store = store_in_environment({"DEVCAPSULE_CONFIG_HOME": str(root)})
    assert store.directory == root / "state" / "notifications"
    with pytest.raises(NotificationError):
        store.list()
