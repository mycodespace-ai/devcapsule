"""Unit tests of ``devcapsule.ssh_identity``: the answers to ``ssh-proxy`` and the key each names.

Every home and every list of key files here is a value the test writes. The
paths are names that the functions compose; nothing opens them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from devcapsule.ssh_identity import SshIdentityError, normalize_selection, selected_identity

HOME = Path("/homes/developer")


def no_listing() -> list[str]:
    """The key files of a home whose ``.ssh`` directory must not be read."""
    pytest.fail("the selection listed the key files")


@pytest.mark.parametrize("given,recorded", [
    (True, True), (False, False), ("true", True), ("TRUE", True), ("false", False), ("False", False),
    ("default", "default"), ("Default", "default"),
    ("id_work", "id_work"), ("deploy key", "deploy key"),
    ("/keys/deploy", "/keys/deploy"), ("~/keys/deploy", "~/keys/deploy"),
])
def test_an_answer_is_recorded_as_a_bool_the_default_word_or_the_key_as_given(given: Any, recorded: Any) -> None:
    """``true``, ``false`` and ``default`` are read in any letter case; a key's name or path is kept as given."""
    normalized = normalize_selection(given)

    assert normalized == recorded and type(normalized) is type(recorded)


@pytest.mark.parametrize("given,complaint", [
    ("", "cannot be empty"),
    (" id_work", "begin or end with a space"),
    ("id_work\n", "begin or end with a space"),
    ("id\x07work", "control character"),
    ("id_%h", "OpenSSH expands"),
    ("~/keys/$USER", "OpenSSH expands"),
    (".", "names a directory"),
    ("..", "names a directory"),
    ("keys/deploy", "absolute or begins with '~/'"),
    ("./deploy", "absolute or begins with '~/'"),
    ("~other/keys/deploy", "absolute or begins with '~/'"),
    ("/keys/", "names a file"),
    ("~/", "names a file"),
    ("/keys/../deploy", "no '.' or '..' step"),
    (1, "expected true, false, 'default', a key name or a key path"),
    (None, "expected true, false, 'default', a key name or a key path"),
])
def test_a_misspelled_answer_is_refused_saying_what_is_wrong(given: Any, complaint: str) -> None:
    """An empty, padded, expanding, relative or directory-naming key, and a value of another type, are refused."""
    with pytest.raises(SshIdentityError, match=complaint):
        normalize_selection(given)


def test_true_leaves_the_choice_to_host_openssh() -> None:
    """``true`` selects no key file, and the home's key files are not listed."""
    assert selected_identity(True, home=HOME, key_files=no_listing) is None


def test_a_denial_selects_no_key_and_is_refused() -> None:
    """A denied proxy has no key to select: asking for one is an error, not a choice by host OpenSSH."""
    with pytest.raises(SshIdentityError, match="denied"):
        selected_identity(False, home=HOME, key_files=no_listing)


@pytest.mark.parametrize("selection,identity", [
    ("id_work", HOME / ".ssh" / "id_work"),
    ("deploy key", HOME / ".ssh" / "deploy key"),
    ("id_work.pub", HOME / ".ssh" / "id_work.pub"),
    ("~/keys/deploy", HOME / "keys" / "deploy"),
    ("~//keys/deploy", HOME / "keys" / "deploy"),
    ("/keys/deploy", Path("/keys/deploy")),
])
def test_a_name_is_a_file_in_the_homes_ssh_directory_and_a_path_is_itself(selection: str, identity: Path) -> None:
    """A value without ``/`` names a file in ``~/.ssh``; ``~/`` is the home; an absolute path stands as given."""
    assert selected_identity(selection, home=HOME, key_files=no_listing) == identity


def test_default_is_the_one_private_key_named_id_in_the_homes_ssh_directory() -> None:
    """Among a key pair, a known-hosts file, a configuration and a key of another name, ``default`` is the
    one ``id_*`` file that is not a public key."""
    names = ["known_hosts", "id_ed25519.pub", "config", "id_ed25519", "deploy", "id_ed25519-cert.pub"]

    assert selected_identity("default", home=HOME, key_files=lambda: names) == HOME / ".ssh" / "id_ed25519"


@pytest.mark.parametrize("names", [[], ["known_hosts", "config"], ["id_ed25519.pub"], ["deploy", "deploy.pub"]])
def test_default_with_no_such_key_asks_for_a_name_or_for_true(names: list[str]) -> None:
    """With no private ``id_*`` key in ``~/.ssh``, ``default`` is refused, naming the directory and both ways out."""
    with pytest.raises(SshIdentityError) as refused:
        selected_identity("default", home=HOME, key_files=lambda: names)

    message = str(refused.value)
    assert "found none" in message and str(HOME / ".ssh") in message
    assert "the key's name or path" in message and "true to let host OpenSSH choose" in message


def test_default_with_several_such_keys_names_them_and_asks_for_one() -> None:
    """With two private ``id_*`` keys, ``default`` is refused and lists both in name order."""
    names = ["id_rsa", "id_ed25519", "id_rsa.pub", "id_ed25519.pub"]

    with pytest.raises(SshIdentityError, match="found id_ed25519, id_rsa. Authorize ssh-proxy with the name of the one to use"):
        selected_identity("default", home=HOME, key_files=lambda: names)


@pytest.mark.parametrize("home", [Path("/homes/50%off"), Path("/homes/$developer")])
def test_a_home_whose_path_openssh_would_expand_is_refused(home: Path) -> None:
    """A key under a home directory that holds ``%`` or ``$`` is refused: OpenSSH would not read the file it spells."""
    with pytest.raises(SshIdentityError, match="OpenSSH expands"):
        selected_identity("id_work", home=home, key_files=no_listing)
