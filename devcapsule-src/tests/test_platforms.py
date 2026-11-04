"""Tests for the host/platform friction module (D-0006)."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule import platforms
from devcapsule.platforms import Platform, UnsupportedPlatformError, XdgHomes

pytestmark = pytest.mark.legacy


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
