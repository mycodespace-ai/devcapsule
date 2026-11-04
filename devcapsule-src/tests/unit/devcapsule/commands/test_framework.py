"""Unit tests of ``devcapsule/commands/framework.py``: the ``--platform`` value ``project init`` and ``images build`` take.

The suite's host is amd64 Linux, which runs linux-amd64 only.
"""
from __future__ import annotations

import argparse

import pytest

from devcapsule.commands.framework import capsule_platform_argument
from devcapsule.platforms import Platform


def test_a_platform_this_host_runs_is_accepted() -> None:
    """A platform this host runs parses to its member."""
    assert capsule_platform_argument("linux-amd64") is Platform.LINUX_AMD64


@pytest.mark.parametrize("value,message", [
    ("linux-arm64", "this host runs linux-amd64 capsules, not linux-arm64"),
    ("windows-amd64", "Unsupported platform 'windows-amd64'"),
])
def test_a_platform_this_host_cannot_run_is_a_usage_error(value: str, message: str) -> None:
    """A platform this host does not run, or no platform at all, is a usage error naming why."""
    with pytest.raises(argparse.ArgumentTypeError, match=message):
        capsule_platform_argument(value)
