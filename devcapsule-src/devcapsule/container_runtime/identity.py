"""Privilege-drop command planning; gosu owns the security-sensitive switch."""

from __future__ import annotations

import os

from .contract import Identity

__all__ = ["foreground_command"]


def foreground_command(
    command: tuple[str, ...],
    identity: Identity,
    *,
    caller_uid: int | None = None,
) -> tuple[str, ...]:
    """Wrap ``command`` so it runs as the capsule user when the caller is root.

    Named for its first use; every supervised child, infrastructure included,
    is wrapped the same way, so no display or IDE process ever runs as root.
    """

    if not command:
        raise ValueError("foreground command must not be empty")
    effective_uid = os.geteuid() if caller_uid is None else caller_uid
    if effective_uid == 0:
        return ("gosu", f"{identity.uid}:{identity.gid}", *command)
    return command
