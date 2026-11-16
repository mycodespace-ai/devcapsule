"""Unit tests of ``devcapsule/configuration/trust_listing.py``: what ``project config trust list`` shows.

Each test builds the channels and the home's trust record as values.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from devcapsule.configuration.trust import Channel, HomeTrust
from devcapsule.configuration.trust_listing import render_trust_rows, trust_rows

ACCEPTED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

EDITOR = Channel("editor", "Example Vendor", "Example Editor", ("https://downloads.example.test",),
                 "the SHA-256 the launcher pins", "https://example.test/terms", "editor-download")
"""A vendor's channel as a lock names it: one origin, pinned checksums, terms."""


def accepting(*channels: Channel) -> HomeTrust:
    """The trust record of a home whose user accepted each of ``channels``, at ``ACCEPTED_AT``."""
    trust = HomeTrust()
    for channel in channels:
        trust = trust.with_channel(channel, accepted_at=ACCEPTED_AT)
    return trust


def test_a_channel_the_home_never_accepted_is_listed_as_not_yet() -> None:
    """A channel of the lock with no entry in the home's record is not trusted and has nothing accepted; its
    line says ``not yet`` with the vendor, the product, the origin, the integrity method and the terms."""
    rows = trust_rows({EDITOR.id: EDITOR}, HomeTrust())

    assert [(row["channel"], row["trusted"], row["accepted"]) for row in rows] == [("editor", False, None)]
    assert render_trust_rows(rows) == [
        "editor             not yet     Example Vendor — Example Editor; from https://downloads.example.test; "
        "integrity the SHA-256 the launcher pins; terms https://example.test/terms",
    ]


def test_a_channel_the_home_accepted_as_the_lock_names_it_is_listed_as_trusted() -> None:
    """A channel accepted with the origin the lock names is trusted, and the row carries the home's entry with
    the time of the acceptance."""
    (row,) = trust_rows({EDITOR.id: EDITOR}, accepting(EDITOR))

    assert row["trusted"] is True
    assert row["accepted"]["accepted"] == "2026-01-02T03:04:05+00:00"
    (line,) = render_trust_rows([row])
    assert line.startswith("editor             trusted     Example Vendor")


def test_a_channel_that_left_what_was_accepted_is_not_covered_and_the_accepted_origins_are_shown() -> None:
    """When the lock names an origin the home did not accept, the channel is not trusted although it has an
    entry: its line says ``not covered`` with the new origin, and a second line gives the origins, integrity
    method and terms that were accepted."""
    moved = replace(EDITOR, origins=("https://mirror.example.test",))

    rows = trust_rows({moved.id: moved}, accepting(EDITOR))

    assert [(row["trusted"], row["accepted"]["origins"]) for row in rows] == [(False, ["https://downloads.example.test"])]
    first, second = render_trust_rows(rows)
    assert first.startswith("editor             not covered Example Vendor") and "from https://mirror.example.test;" in first
    assert second.strip() == ("Accepted origins: https://downloads.example.test; integrity the SHA-256 the launcher pins; "
                              "terms https://example.test/terms")


def test_an_accepted_channel_that_the_checkout_does_not_use_is_listed_after_the_locks_channels() -> None:
    """A channel in the home's record that the checkout's lock does not use is listed last, from the record
    alone, and noted as not used by this checkout."""
    other = Channel("other", "Other Vendor", "Other Tool", ("https://other.example.test",), "the SHA-256 the launcher pins")

    rows = trust_rows({EDITOR.id: EDITOR}, accepting(EDITOR, other))

    assert [(row["channel"], row["trusted"], row["note"]) for row in rows] == [
        ("editor", True, ""), ("other", True, "not used by this checkout"),
    ]
    assert render_trust_rows(rows)[-2:] == [
        "other              trusted     Other Vendor — (not used by this checkout); from https://other.example.test; "
        "integrity the SHA-256 the launcher pins",
        "                   not used by this checkout",
    ]


def test_a_channels_note_is_shown_under_its_line() -> None:
    """A channel that carries a note, as DevCapsule's base channel does, has the note on a line of its own."""
    noted = replace(EDITOR, note="Read this before you accept.")

    lines = render_trust_rows(trust_rows({noted.id: noted}, HomeTrust()))

    assert len(lines) == 2 and lines[1].strip() == "Read this before you accept."
