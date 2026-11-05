"""Unit tests of ``devcapsule/component_status_publisher.py``: the feed generated without asking any vendor.

The policy is constructed here with one probe per catalog component, as the publisher requires.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from devcapsule import component_status_publisher as publisher
from devcapsule.component_status import StatusFeed
from devcapsule.components.catalog import COMPONENTS


def a_policy() -> dict[str, Any]:
    """A format-1 policy with no advisories and one linux-amd64 probe per catalog component."""
    return {"format": 1, "advisories": [],
            "probes": [{"component": name, "platform": "linux-amd64", "version": "1.0.0"} for name in COMPONENTS]}


def test_generation_without_probes_asks_no_vendor_and_records_no_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    """With ``probe=False`` no discovery channel is consulted, the feed parses as format 1, and it carries the
    policy's advisories with an empty observation list."""
    def forbidden(self: object, *args: object, **kwargs: object) -> object:
        raise AssertionError("a vendor was asked")

    for definition in COMPONENTS.values():
        monkeypatch.setattr(type(definition), "discovery_channel", forbidden, raising=False)
    now = datetime(2026, 11, 5, tzinfo=timezone.utc)
    feed = publisher.generate(a_policy(), {}, revision="abc123", now=now, probe=False)
    assert feed["observations"] == [] and feed["advisories"] == []
    assert feed["generated_at"] == now.isoformat() and feed["source_revision"] == "abc123"
    assert StatusFeed.parse(feed).generated_at == now


def test_generation_without_probes_still_requires_a_probe_per_component() -> None:
    """The policy's probe list is validated whether or not it is used, so a snapshot cannot hide a missing probe."""
    policy = a_policy()
    policy["probes"].pop()
    with pytest.raises(ValueError, match="every catalog component needs a probe"):
        publisher.generate(policy, {}, revision="abc123", probe=False)
