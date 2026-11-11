"""Unit tests of ``devcapsule/container_runtime/identity.py``: the privilege drop planned for a supervised child."""

from __future__ import annotations

import os

import pytest

from devcapsule.container_runtime.contract import Identity
from devcapsule.container_runtime.identity import foreground_command

DEVELOPER = Identity(1000, 1001, "developer")


def test_foreground_command_drops_to_the_capsule_user_when_the_caller_is_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Called as root, ``foreground_command`` prefixes the command with ``gosu`` and the capsule user's ``uid:gid``."""
    with monkeypatch.context() as process:
        process.setattr(os, "geteuid", lambda: 0)
        command = foreground_command(("ide", "--wait"), DEVELOPER)

    assert command == ("gosu", "1000:1001", "ide", "--wait")


def test_foreground_command_leaves_the_command_alone_when_the_caller_is_not_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Called as any user but root, ``foreground_command`` returns the command unchanged."""
    with monkeypatch.context() as process:
        process.setattr(os, "geteuid", lambda: 1000)
        command = foreground_command(("ide", "--wait"), DEVELOPER)

    assert command == ("ide", "--wait")


def test_foreground_command_refuses_an_empty_command() -> None:
    """An empty command raises ``ValueError``, whoever the caller is."""
    with pytest.raises(ValueError, match="must not be empty"):
        foreground_command((), DEVELOPER)
