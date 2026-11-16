"""The capsule user as the preparing process sees it; gosu owns the security-sensitive switch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .contract import Identity

__all__ = ["CapsuleUser"]


@dataclass(frozen=True)
class CapsuleUser:
    """The capsule's user, and the effective uid of the process that prepares the session.

    The entrypoint reads that uid once and builds this value. Everything
    below asks it, and never the operating system, whether the caller is
    root: root must hand each child and each new directory to the capsule
    user, and any other caller already is that user.
    """

    identity: Identity
    caller_uid: int

    @property
    def caller_is_root(self) -> bool:
        return self.caller_uid == 0

    def command(self, command: tuple[str, ...]) -> tuple[str, ...]:
        """``command`` as a supervised child runs it: behind ``gosu`` when the caller is root.

        Every supervised child, infrastructure included, is wrapped the same
        way, so no display or IDE process ever runs as root. When the caller
        is root and the target identity is already ``0:0`` (as under rootless
        Docker, where host UID/GID map to container root), return ``command``
        unchanged rather than invoking ``gosu 0:0``, which ``--cap-drop ALL``
        refuses.
        """

        if not command:
            raise ValueError("foreground command must not be empty")
        if self.caller_is_root and (self.identity.uid != 0 or self.identity.gid != 0):
            return ("gosu", f"{self.identity.uid}:{self.identity.gid}", *command)
        return command

    def owner_changes(self, created: Iterable[Path]) -> tuple[tuple[Path, int, int], ...]:
        """The ``(path, uid, gid)`` changes that give ``created`` to the capsule user.

        One per path, in the given order, when the caller is root and the
        target identity is non-root; none otherwise, since the caller owns them
        already.
        """

        if not self.caller_is_root or (self.identity.uid == 0 and self.identity.gid == 0):
            return ()
        return tuple((path, self.identity.uid, self.identity.gid) for path in created)
