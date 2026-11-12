"""The console's side of its contracts with the launcher, checked against the launcher itself.

The console talks to the launcher twice: it runs the runtime CLI for its
pages, and it forwards configuration requests through the mounted channel.
Both are contracts the two packages keep in their own files. These tests
import the launcher, installed into this session without its Docker
dependency, so a command or verb retired on one side fails here, in the
build gate, before it fails on a configuration page.
"""
from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

import pytest

from devcapsule import cli as launcher_cli
from devcapsule.commands._console_channel import _config_command
from devcapsule.configuration import console_channel as launcher_channel
from devcapsule.configuration.listing import ListingRow
from devcapsule_webconsole import configuration as console_channel
from devcapsule_webconsole.cli import READ_COMMANDS

CONTRACT = Path(__file__).resolve().parents[1] / "CONFIGURATION-CHANNEL.md"


def _help(*arguments: str) -> tuple[int, str]:
    """The launcher's parser on ``ARGUMENTS --help``: status and the help text."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        status = launcher_cli.main([*arguments, "--help"])
    return status, out.getvalue()


@pytest.mark.parametrize("name", sorted(READ_COMMANDS))
def test_every_command_the_console_runs_exists_and_takes_json(name: str) -> None:
    status, text = _help("project", *READ_COMMANDS[name])
    assert status == 0, f"the launcher no longer has 'project {' '.join(READ_COMMANDS[name])}'"
    assert "--json" in text, f"'project {' '.join(READ_COMMANDS[name])}' no longer takes --json"


def test_the_console_forwards_exactly_the_verbs_the_launcher_classifies() -> None:
    parents = {verb for verb, _ in (*launcher_channel.APPLIED_SUBVERBS, *launcher_channel.DEFERRED_SUBVERBS)}
    expected = launcher_channel.APPLIED_VERBS | launcher_channel.DEFERRED_VERBS | parents
    assert set(console_channel.VERBS) == expected
    assert len(set(console_channel.VERBS)) == len(console_channel.VERBS)


def test_the_console_names_the_same_widenings_and_secure_values() -> None:
    deferred = launcher_channel.DEFERRED_VERBS | {" ".join(pair) for pair in launcher_channel.DEFERRED_SUBVERBS}
    assert set(console_channel.WIDENING) == deferred
    assert console_channel.SECURE_AUTHORIZATIONS == launcher_channel.SECURE_AUTHORIZATIONS


@pytest.mark.parametrize("verb", sorted(
    (*launcher_channel.APPLIED_VERBS, *launcher_channel.DEFERRED_VERBS, *launcher_channel.READ_ONLY_VERBS),
))
def test_every_classified_verb_is_a_config_command(verb: str) -> None:
    assert _help("project", "config", verb)[0] == 0, f"'config {verb}' is classified but the launcher has no such command"


@pytest.mark.parametrize("pair", sorted(
    (*launcher_channel.APPLIED_SUBVERBS, *launcher_channel.DEFERRED_SUBVERBS, *launcher_channel.READ_ONLY_SUBVERBS),
))
def test_every_classified_subverb_routes_to_a_launcher_command(pair: tuple[str, str]) -> None:
    # The wire tokens stay stable when a command moves from project to home.
    arguments = _config_command(Path("/project"), pair)[3:]  # Strip Python, -m, devcapsule.
    assert _help(*arguments)[0] == 0, f"request {' '.join(pair)!r} routes to a missing launcher command"


def _tokens(bullet: str) -> set[str]:
    """The first word or word pair of each backticked token in one bullet of the contract."""
    text = CONTRACT.read_text(encoding="utf-8")
    start = text.index(f"- **{bullet}**")
    end = text.find("\n- **", start + 1)
    section = text[start:end if end > 0 else None]
    result: set[str] = set()
    for token in re.findall(r"`([^`]+)`", section):
        words = token.split()
        if words and words[0] in set(console_channel.VERBS) | launcher_channel.READ_ONLY_VERBS:
            result.add(" ".join(words[:2]) if len(words) > 1 and (words[0], words[1]) in (
                launcher_channel.APPLIED_SUBVERBS | launcher_channel.DEFERRED_SUBVERBS) else words[0])
    return result


def test_the_written_contract_lists_the_launchers_verbs() -> None:
    applied = launcher_channel.APPLIED_VERBS | {" ".join(pair) for pair in launcher_channel.APPLIED_SUBVERBS}
    deferred = launcher_channel.DEFERRED_VERBS | {" ".join(pair) for pair in launcher_channel.DEFERRED_SUBVERBS}
    assert _tokens("Recorded at once") >= applied
    assert _tokens("Deferred") >= deferred


def test_the_listing_rows_carry_the_fields_the_page_reads() -> None:
    document = ListingRow("capability", "node", "supplied by the base", "project (required)").document()
    assert set(document) >= {"kind", "name", "effective", "source", "pending", "command"}
