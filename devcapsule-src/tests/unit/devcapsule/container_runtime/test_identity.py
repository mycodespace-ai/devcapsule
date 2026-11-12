"""Unit tests of ``devcapsule/container_runtime/identity.py``: what the capsule user is given when root prepares the session."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.container_runtime.contract import Identity
from devcapsule.container_runtime.identity import CapsuleUser

DEVELOPER = Identity(1000, 1001, "developer")
PREPARED_BY_ROOT = CapsuleUser(DEVELOPER, caller_uid=0)
PREPARED_BY_THE_USER = CapsuleUser(DEVELOPER, caller_uid=1000)


def test_command_drops_to_the_capsule_user_when_the_caller_is_root() -> None:
    """For a root caller, ``command`` prefixes the command with ``gosu`` and the capsule user's ``uid:gid``."""
    assert PREPARED_BY_ROOT.command(("ide", "--wait")) == ("gosu", "1000:1001", "ide", "--wait")


def test_command_leaves_the_command_alone_when_the_caller_is_not_root() -> None:
    """For any caller but root, ``command`` returns the command unchanged."""
    assert PREPARED_BY_THE_USER.command(("ide", "--wait")) == ("ide", "--wait")


@pytest.mark.parametrize("user", [PREPARED_BY_ROOT, PREPARED_BY_THE_USER])
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
