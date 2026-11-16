"""Unit tests of container_runtime.identity: privilege switching for explicit identities."""

import pytest

from devcapsule.container_runtime.contract import Identity
from devcapsule.container_runtime.identity import foreground_command


@pytest.mark.parametrize("caller_uid", [0, 1000])
def test_mapped_root_command_needs_no_privilege_switch(caller_uid: int) -> None:
    """A target of 0:0 needs no gosu wrapper, including a rootless Docker root caller."""
    command = ("ide", "--wait")
    assert foreground_command(command, Identity(0, 0, "root"), caller_uid=caller_uid) == command


@pytest.mark.parametrize("uid,gid", [(1000, 1001), (0, 1001), (1000, 0)])
def test_root_caller_switches_when_either_target_id_differs(uid: int, gid: int) -> None:
    """Root still invokes gosu for any target other than 0:0, preserving rootful behavior."""
    assert foreground_command(("ide",), Identity(uid, gid, "developer"), caller_uid=0) == (
        "gosu", f"{uid}:{gid}", "ide",
    )


def test_non_root_caller_keeps_the_command() -> None:
    """A non-root caller does not invoke a privilege switch."""
    assert foreground_command(("ide",), Identity(1000, 1001, "developer"), caller_uid=1000) == ("ide",)


def test_empty_command_is_refused_for_mapped_root() -> None:
    """Skipping gosu does not make an empty foreground command valid."""
    with pytest.raises(ValueError, match="must not be empty"):
        foreground_command((), Identity(0, 0, "root"), caller_uid=0)
