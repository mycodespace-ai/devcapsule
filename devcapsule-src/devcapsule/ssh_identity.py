"""The ``ssh-proxy`` authorization: which host key the launcher's SSH proxy offers.

An answer to ``ssh-proxy`` is a denial or one of four grants:

``false``
    Denied. The capsule gets no proxy.
``true``
    Host OpenSSH chooses, from its configuration, its agent and its default
    key files, as it does for the developer's own ``ssh``.
``default``
    The one private key named ``id_*`` in the developer's ``~/.ssh``. No
    such key, or several, is an error that asks for a name.
a name, with no ``/`` in it
    That file in ``~/.ssh``.
a path, with a ``/`` in it
    That file. It is absolute or begins with ``~/``: a recorded answer
    outlives the directory it was given in, so a relative path has no
    meaning.

``normalize_selection`` checks an answer's spelling and ``selected_identity``
turns a grant into the key file to offer. Both are functions of their
arguments; neither reads the host. The key stays on the host: the proxy names
it to host OpenSSH and nothing of it enters a capsule.

The release candidate 0.3.1-rc3, and no release before or after it, called the
authorization ``github-ssh`` and took ``true`` or ``false``.
``RETIRED_AUTHORIZATION`` is that name, still read wherever an answer is, so
that those answers keep their meaning.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

__all__ = ["AUTHORIZATION", "RETIRED_AUTHORIZATION", "SINGLE_KEY", "SshIdentityError",
           "normalize_selection", "selected_identity"]

AUTHORIZATION = "ssh-proxy"
RETIRED_AUTHORIZATION = "github-ssh"
SINGLE_KEY = "default"

_PUBLIC_KEY_SUFFIX = ".pub"
_SINGLE_KEY_PREFIX = "id_"
# OpenSSH expands %-tokens and ${VARIABLE} in the name of an identity file.
# A key path that holds either character would not name the file it spells.
_EXPANDED_BY_OPENSSH = "%$"


class SshIdentityError(ValueError):
    """An ``ssh-proxy`` answer is misspelled, or names no single key."""


def normalize_selection(value: object) -> bool | str:
    """The answer as it is recorded: a bool, ``default``, or a key's name or path.

    The words ``true``, ``false`` and ``default`` are read in any letter
    case. Every other string is a key and is returned unchanged. Whether the
    key exists is the launching host's to say, at launch.
    """
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        raise SshIdentityError(f"expected true, false, {SINGLE_KEY!r}, a key name or a key path; found {value!r}.")
    word = value.lower()
    if word in {"true", "false"}:
        return word == "true"
    if word == SINGLE_KEY:
        return SINGLE_KEY
    _require_key_spelling(value)
    return value


def _require_key_spelling(key: str) -> None:
    if not key or key != key.strip() or any(ord(character) < 32 or ord(character) == 127 for character in key):
        raise SshIdentityError(f"a key name or path cannot be empty, begin or end with a space, or hold a control character; found {key!r}.")
    if any(character in key for character in _EXPANDED_BY_OPENSSH):
        raise SshIdentityError(f"a key name or path cannot hold '%' or '$', which OpenSSH expands; found {key!r}.")
    if "/" not in key:
        if key in {".", ".."}:
            raise SshIdentityError(f"{key!r} names a directory, not a key.")
        return
    if not key.startswith(("/", "~/")):
        raise SshIdentityError(
            f"a key path is absolute or begins with '~/'; found {key!r}. A name without '/' is a file in ~/.ssh."
        )
    parts = key.split("/")[1:]
    if not parts[-1] or any(part in {".", ".."} for part in parts):
        raise SshIdentityError(f"a key path names a file and holds no '.' or '..' step; found {key!r}.")


def selected_identity(selection: bool | str, *, home: Path,
                      key_files: Callable[[], Sequence[str]]) -> Path | None:
    """The key file a granted ``selection`` names, or None when host OpenSSH chooses.

    ``selection`` is a grant as ``normalize_selection`` returns it; a denial
    selects no key and is refused. ``home`` is the developer's home directory
    on the launching host. ``key_files`` gives the names of the regular files
    in its ``.ssh`` directory and is called only for ``default``.
    """
    if selection is False:
        raise SshIdentityError("a denied ssh-proxy selects no key.")
    if selection is True:
        return None
    directory = home / ".ssh"
    if selection == SINGLE_KEY:
        identity = directory / _single_key(sorted(key_files()), directory)
    elif "/" not in selection:
        identity = directory / selection
    elif selection.startswith("~/"):
        identity = home / selection[1:].lstrip("/")
    else:
        identity = Path(selection)
    if any(character in str(identity) for character in _EXPANDED_BY_OPENSSH):
        raise SshIdentityError(f"the key path {str(identity)!r} holds '%' or '$', which OpenSSH expands; give another path.")
    return identity


def _single_key(names: Sequence[str], directory: Path) -> str:
    keys = [name for name in names
            if name.startswith(_SINGLE_KEY_PREFIX) and not name.endswith(_PUBLIC_KEY_SUFFIX)]
    if len(keys) == 1:
        return keys[0]
    if not keys:
        raise SshIdentityError(
            f"{SINGLE_KEY!r} expects one private key named {_SINGLE_KEY_PREFIX}* in {directory} and found none. "
            "Authorize ssh-proxy with the key's name or path, or with true to let host OpenSSH choose."
        )
    raise SshIdentityError(
        f"{SINGLE_KEY!r} expects one private key named {_SINGLE_KEY_PREFIX}* in {directory} and found "
        f"{', '.join(keys)}. Authorize ssh-proxy with the name of the one to use."
    )
