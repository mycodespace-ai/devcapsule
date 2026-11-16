"""Unit tests of ``devcapsule/configuration/console_requests.py``: the requests kept for the host's confirmation.

A checkout's kept requests live under the DevCapsule home, in a file found
from the checkout's record. Each test writes its own record, in the private
home the suite gives every test, and asks the product where that home is.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.configuration.console_channel import DeferredRequest
from devcapsule.configuration.console_requests import (
    console_requests_path, deferred_requests, deferred_rows, request_rows, write_deferred,
)
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.storage import config_root

NETWORK = DeferredRequest("000001-authorize", "2026-10-24T10:00:00+00:00", ("authorize", "network", "host"))
DOCKER = DeferredRequest("000002-authorize", "2026-10-24T11:00:00+00:00", ("authorize", "docker-daemon", "host-socket"))


def a_record(directory: Path, *, name: str = "devcapsule.checkout.toml") -> Path:
    """The record, in the test's home, of a checkout of the project ``owner/order`` that lies at ``directory``."""
    record = config_root() / "projects" / "owner" / "order" / name
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(render_toml({"checkout": {"path": str(directory)}}), encoding="utf-8")
    return record


def test_a_checkout_that_was_asked_nothing_has_no_kept_request(tmp_path: Path) -> None:
    """A registered checkout with no store has no kept request, and so has a checkout with no record at all."""
    assert deferred_requests(a_record(tmp_path / "order")) == []
    assert deferred_requests(tmp_path / "no-such-record.toml") == []


def test_kept_requests_are_read_back_in_the_order_written(tmp_path: Path) -> None:
    """Requests written for a checkout are the checkout's kept requests, in order."""
    record = a_record(tmp_path / "order")

    write_deferred(record, [NETWORK, DOCKER])

    assert deferred_requests(record) == [NETWORK, DOCKER]


def test_the_store_lies_in_the_home_outside_the_directory_of_the_records(tmp_path: Path) -> None:
    """The launcher mounts the records' directory into the capsule. The store of kept requests is under the
    home's ``console-requests`` tree and not under that directory, so the capsule cannot reach it."""
    record = a_record(tmp_path / "order")

    path = write_deferred(record, [NETWORK])

    assert path.is_file() and path.is_relative_to(config_root() / "console-requests")
    assert not path.is_relative_to(record.parent)


def test_writing_no_request_removes_the_store(tmp_path: Path) -> None:
    """When the last kept request is gone the store's file is removed, and the checkout has none again."""
    record = a_record(tmp_path / "order")
    path = write_deferred(record, [NETWORK])

    write_deferred(record, [])

    assert not path.exists() and deferred_requests(record) == []


def test_a_store_that_would_grow_past_its_limit_is_refused_and_keeps_what_it_held(tmp_path: Path) -> None:
    """Writing more than the store may hold is refused as a full queue, and the requests kept before are intact."""
    record = a_record(tmp_path / "order")
    write_deferred(record, [NETWORK])
    huge = ("bind", *(["x" * 4096] * 63))

    with pytest.raises(ProjectConfigurationError, match="queue is full"):
        write_deferred(record, [NETWORK, DeferredRequest("000002-bind", "", huge), DeferredRequest("000003-bind", "", huge)])

    assert deferred_requests(record) == [NETWORK]


def test_the_store_follows_the_checkouts_directory_when_its_record_is_renamed(tmp_path: Path) -> None:
    """A checkout registered under another name keeps its requests: the store is found from the directory the
    record names, not from the record's file name."""
    record = a_record(tmp_path / "order")
    stored = write_deferred(record, [NETWORK])

    renamed = record.rename(record.with_name("renamed.checkout.toml"))

    assert console_requests_path(renamed) == stored
    assert deferred_requests(renamed) == [NETWORK]


def test_another_checkout_that_takes_over_a_records_name_does_not_inherit_its_requests(tmp_path: Path) -> None:
    """A record under the same file name, of a checkout at another directory, has a store of its own: it starts
    with no request, and what is kept for it leaves the first checkout's requests alone."""
    first = a_record(tmp_path / "order")
    write_deferred(first, [NETWORK])
    first = first.rename(first.with_name("first.checkout.toml"))

    second = a_record(tmp_path / "another-copy")

    assert deferred_requests(second) == []
    write_deferred(second, [DOCKER])
    assert deferred_requests(second) == [DOCKER] and deferred_requests(first) == [NETWORK]


def test_a_kept_request_is_a_soft_decision_of_the_listing_with_the_command_that_applies_it() -> None:
    """A kept request becomes a ``console`` row that names the request, when it was asked and what it stands
    for, with the host command that applies it for the project given, and the same as a decision."""
    (row,) = request_rows([NETWORK], Path("/projects/order"))

    command = "devcapsule project --path /projects/order config console apply 000001-authorize"
    assert (row.kind, row.name, row.source, row.pending, row.command) == (
        "console", "000001-authorize", "console request at 2026-10-24T10:00:00+00:00",
        "confirm or discard: config authorize network host", command)
    assert row.decision is not None
    assert (row.decision.kind, row.decision.name, row.decision.description, row.decision.command, row.decision.reason) == (
        "console", "000001-authorize", "config authorize network host", command, "2026-10-24T10:00:00+00:00")


def test_without_a_project_directory_the_command_leaves_the_project_to_the_working_directory() -> None:
    """With no project directory given, the applying command has no ``--path``."""
    (row,) = request_rows([NETWORK], None)

    assert row.command == "devcapsule project config console apply 000001-authorize"


def test_the_rows_of_a_checkout_are_its_kept_requests_and_none_without_a_record(tmp_path: Path) -> None:
    """A checkout's rows are the rows of what its store holds; a checkout with no record has none."""
    record = a_record(tmp_path / "order")
    write_deferred(record, [NETWORK, DOCKER])

    assert deferred_rows(record, tmp_path / "order") == request_rows([NETWORK, DOCKER], tmp_path / "order")
    assert deferred_rows(None, tmp_path / "order") == []


def test_a_store_that_cannot_be_read_is_one_invalid_row_and_not_an_error(tmp_path: Path) -> None:
    """A store whose file is not the contract's document does not stop the listing: it is one row, marked
    invalid, that says to repair or remove the file."""
    record = a_record(tmp_path / "order")
    write_deferred(record, [NETWORK]).write_text("{}", encoding="utf-8")

    (row,) = deferred_rows(record, tmp_path / "order")

    assert (row.kind, row.effective, row.pending) == ("console", "invalid", "repair or remove the console-requests file")
    assert row.decision is None
