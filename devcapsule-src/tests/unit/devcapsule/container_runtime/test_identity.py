"""Unit tests of ``devcapsule/container_runtime/identity.py``: what the capsule user is given when root prepares the session."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.container_runtime.contract import Identity
from devcapsule.container_runtime.identity import CapsuleUser

DEVELOPER = Identity(1000, 1001, "developer")
ROOT = Identity(0, 0, "root")
PREPARED_BY_ROOT = CapsuleUser(DEVELOPER, caller_uid=0)
PREPARED_BY_THE_USER = CapsuleUser(DEVELOPER, caller_uid=1000)
ROOTLESS_ROOT = CapsuleUser(ROOT, caller_uid=0)


def test_command_drops_to_the_capsule_user_when_the_caller_is_root() -> None:
    """For a root caller, ``command`` prefixes the command with ``gosu`` and the capsule user's ``uid:gid``."""
    assert PREPARED_BY_ROOT.command(("ide", "--wait")) == ("gosu", "1000:1001", "ide", "--wait")


def test_command_leaves_the_command_alone_when_the_caller_is_not_root() -> None:
    """For any caller but root, ``command`` returns the command unchanged."""
    assert PREPARED_BY_THE_USER.command(("ide", "--wait")) == ("ide", "--wait")


@pytest.mark.parametrize("user", [PREPARED_BY_ROOT, PREPARED_BY_THE_USER, ROOTLESS_ROOT])
def test_command_refuses_an_empty_command(user: CapsuleUser) -> None:
    """An empty command raises ``ValueError``, whoever the caller is."""
    with pytest.raises(ValueError, match="must not be empty"):
        user.command(())


def test_owner_changes_give_each_created_path_to_the_capsule_user_when_the_caller_is_root() -> None:
    """For a root caller, ``owner_changes`` names the capsule user's uid and gid for every path, in the given order."""
    created = (Path("/home/developer/.ssh"), Path("/run/user"), Path("/run/user/1000"))

    assert PREPARED_BY_ROOT.owner_changes(created) == (
        (Path("/home/developer/.ssh"), 1000, 1001),
        (Path("/run/user"), 1000, 1001),
        (Path("/run/user/1000"), 1000, 1001),
    )


def test_owner_changes_are_none_when_the_caller_is_not_root() -> None:
    """For any caller but root, ``owner_changes`` is empty: what that caller creates is its own."""
    assert PREPARED_BY_THE_USER.owner_changes((Path("/home/developer/.ssh"),)) == ()


def test_command_does_not_wrap_root_identity_in_gosu() -> None:
    """When both the caller and the target identity are ``0:0`` (rootless Docker), ``command`` omits ``gosu``."""
    assert ROOTLESS_ROOT.command(("ide", "--wait")) == ("ide", "--wait")


def test_owner_changes_are_none_when_the_target_identity_is_root() -> None:
    """When the caller and target identity are both ``0:0``, ``owner_changes`` avoids redundant ``chown`` calls."""
    assert ROOTLESS_ROOT.owner_changes((Path("/home/devcapsule/.ssh"),)) == ()


@pytest.mark.parametrize("uid,gid", [(0, 1001), (1000, 0)])
def test_root_caller_switches_when_one_target_id_differs(uid: int, gid: int) -> None:
    """A target with only one zero ID still requires gosu; only 0:0 bypasses it."""
    user = CapsuleUser(Identity(uid, gid, "developer"), caller_uid=0)
    assert user.command(("ide",)) == ("gosu", f"{uid}:{gid}", "ide")


def test_non_root_caller_keeps_a_root_target_command() -> None:
    """A non-root caller does not try to elevate itself even for a root target."""
    assert CapsuleUser(ROOT, caller_uid=1000).command(("ide",)) == ("ide",)
