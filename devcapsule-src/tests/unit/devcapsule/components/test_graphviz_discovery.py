"""Graphviz discovery consumes release values supplied by its caller."""
from __future__ import annotations

from typing import Any

import pytest

from devcapsule.compat import CliError
from devcapsule.components.graphviz_discovery import GraphvizDiscovery


@pytest.mark.parametrize("platform", ["linux-amd64", "linux-arm64"])
def test_a_newer_stable_release_is_available_on_both_capsule_platforms(platform: str) -> None:
    """A newer stable source release is an update candidate for either supported architecture."""
    channel = GraphvizDiscovery(lambda: {"tag_name": "17.0.0", "upcoming_release": False})
    report = channel.check("16.1.1", platform)
    assert [x.version for x in report.candidates] == ["17.0.0"]
    assert report.current.status == "unknown"


@pytest.mark.parametrize("current", ["17.0.0", "18.0.0"])
def test_an_equal_or_older_upstream_release_does_not_offer_a_downgrade(current: str) -> None:
    """Discovery offers only releases newer than the exact installed version."""
    channel = GraphvizDiscovery(lambda: {"tag_name": "17.0.0"})
    assert channel.check(current, "linux-amd64").candidates == ()


@pytest.mark.parametrize("release", [
    {}, {"tag_name": "17.0.0-rc1"}, {"tag_name": "17.0.0", "upcoming_release": True},
])
def test_missing_prerelease_or_upcoming_metadata_is_inconclusive(release: dict[str, Any]) -> None:
    """Malformed or not-yet-stable release metadata must not become an upgrade suggestion."""
    channel = GraphvizDiscovery(lambda: release)
    with pytest.raises(CliError, match="Graphviz discovery unavailable"):
        channel.check("16.1.1", "linux-amd64")


def test_a_network_failure_is_not_reported_as_up_to_date() -> None:
    """A failed metadata read produces a visible unavailable check."""
    def unavailable() -> dict[str, Any]:
        raise OSError("offline")
    with pytest.raises(CliError, match="offline"):
        GraphvizDiscovery(unavailable).check("16.1.1", "linux-amd64")


def test_an_unsupported_platform_is_refused_without_reading_metadata() -> None:
    """Only supported Linux capsule architectures may reach Graphviz's release reader."""
    def forbidden() -> dict[str, Any]:
        raise AssertionError("metadata was read")
    with pytest.raises(CliError, match="No Graphviz discovery adapter"):
        GraphvizDiscovery(forbidden).check("16.1.1", "unsupported")
