"""Unit tests of ``devcapsule/configuration/console_channel.py``: the contract of the console's channel.

The module is the contract between a capsule's console and the launcher:
which request is applied at once, kept for the host's confirmation or
refused, and the documents the two sides exchange. Each test builds its
tokens and documents as values. The tests of reading and publishing write
their own files under the test's directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from devcapsule.configuration.console_channel import (
    DeferredRequest, Disposition, classify, listing_document, parse_deferred, parse_listing, parse_request,
    read_document, render_deferred, request_id, result_document, statement, write_complete,
)
from devcapsule.configuration.file_formats import ProjectConfigurationError


@pytest.mark.parametrize("arguments", [
    ["ide", "python-ide"], ["add", "claude-code-agent"], ["omit", "browser-automation"],
    ["restore", "browser-automation"], ["use", "frontend-ide", "codium"], ["set", "cpus", "2"],
    ["deny", "network"], ["unbind", "home"], ["env", "set", "X", "1"], ["env", "unset", "X"],
    ["trust", "withdraw", "claude-code"], ["docker-args", "clear"],
])
def test_a_request_that_keeps_or_narrows_the_checkouts_choices_is_applied_at_once(arguments: list[str]) -> None:
    """A verb that records the checkout's own choice, or narrows what the next launch reaches, is applied
    without the host's confirmation, and no reason is given."""
    assert classify(arguments) == (Disposition.APPLY, "")


@pytest.mark.parametrize("arguments", [
    ["authorize", "network", "bridge"], ["authorize", "network", "none"], ["authorize", "docker-daemon", "none"],
    ["authorize", "development-sudo", "false"], ["authorize", "host-browser", "false"], ["authorize", "host-x11", "none"],
])
def test_an_authorization_of_the_secure_value_is_applied_at_once(arguments: list[str]) -> None:
    """``authorize`` with the value that grants nothing, a bridged or absent network, no Docker daemon, no
    sudo, no host browser or display, narrows the launch and is applied like a denial."""
    assert classify(arguments) == (Disposition.APPLY, "")


@pytest.mark.parametrize("arguments", [
    ["authorize", "network", "host"], ["authorize", "docker-daemon", "host-socket"], ["trust", "accept", "claude-code"],
    ["bind", "home", "~/capsule-home"], ["docker-args", "set", "--privileged"], ["forget", "docker-daemon"],
    ["forget", "claude-code-download"],
    ["env", "set", "HOST_SECRET", "--from-host"], ["env", "set", "HOST_SECRET", "--from-h"], ["env", "set", "X"],
])
def test_a_request_that_can_widen_what_the_launch_reaches_is_deferred(arguments: list[str]) -> None:
    """A verb that can widen the next launch is kept for the host's confirmation: an authorization, a trusted
    channel, a binding, Docker arguments, forgetting an answer, which can bring back a grant of the home, and an
    environment variable taken from the host, however its option is abbreviated."""
    assert classify(arguments) == (Disposition.DEFER, "")


@pytest.mark.parametrize(("arguments", "reason"), [
    ([], "an empty request names no command"),
    (["show"], "config show is read-only"),
    (["check"], "config check is read-only"),
    (["env", "list"], "config env is read-only"),
    (["trust", "list"], "config trust is read-only"),
    (["default", "memory", "8G"], "run it on the host"),
    (["require", "java"], "edits the project's shared files"),
    (["recommend", "ide", "python-ide"], "edits the project's shared files"),
    (["run"], "not a request the launcher takes from the console"),
    (["agent", "add", "codex"], "not a request the launcher takes from the console"),
    (["tool", "omit", "browser-automation"], "not a request the launcher takes from the console"),
])
def test_every_other_request_is_refused_with_its_reason(arguments: list[str], reason: str) -> None:
    """A read-only command, a home default, an edit of the project's shared files, an unknown or retired verb
    and an empty request are refused, each with a reason that says why."""
    disposition, given = classify(arguments)

    assert disposition is Disposition.REFUSE
    assert reason in given


def test_a_request_is_stated_as_the_command_it_stands_for_with_its_tokens_quoted() -> None:
    """A request's statement is ``config`` followed by its tokens, quoted as a shell would need them."""
    assert statement(["docker-args", "set", "--env", "TEXT=a b"]) == "config docker-args set --env 'TEXT=a b'"


@pytest.mark.parametrize("name", ["000001-ide.request.json", "000042-docker-args-0123456789abcdef0123456789abcdef.request.json"])
def test_a_request_files_id_is_its_name_without_the_suffix(name: str) -> None:
    """A request file named by the contract, a six-digit number, a verb and optionally a UUID, has that name
    without the suffix as its id."""
    assert request_id(Path("/channel") / name) == name.removesuffix(".request.json")


@pytest.mark.parametrize("name", ["x.json", "1-ide.request.json", "000001-Ide.request.json", "000001-ide.result.json"])
def test_a_file_not_named_by_the_contract_has_no_request_id(name: str) -> None:
    """A file with another suffix, a short number or an upper-case verb is refused as a request."""
    with pytest.raises(ProjectConfigurationError):
        request_id(Path("/channel") / name)


def test_a_request_documents_tokens_are_returned_as_given() -> None:
    """A format-1 document with a list of tokens, and optionally the time it was asked, gives those tokens."""
    document = {"format": 1, "requested": "2026-10-24T10:00:00+00:00", "arguments": ["ide", "python-ide"]}

    assert parse_request(document) == ["ide", "python-ide"]
    assert parse_request({"format": 1, "arguments": ["ide", "python-ide"]}) == ["ide", "python-ide"]


@pytest.mark.parametrize("document", [
    [], {"format": 2, "arguments": ["ide"]}, {"format": 1, "arguments": []}, {"format": 1, "arguments": "ide"},
    {"format": 1, "arguments": ["a\nb"]}, {"format": 1, "arguments": ["ide", ""]}, {"format": 1, "arguments": ["ide", 3]},
    {"format": 1, "arguments": ["ide", "--path", "/x"]}, {"format": 1, "arguments": ["x" * 5000]},
    {"format": 1, "arguments": ["ide", "\ud800"]}, {"format": 1, "arguments": ["ide"] * 65},
], ids=["not-a-table", "another-format", "no-token", "not-a-list", "control-character", "empty-token", "not-text",
        "names-the-project", "token-too-long", "not-unicode", "too-many-tokens"])
def test_a_malformed_request_document_is_refused(document: Any) -> None:
    """A document of another format, without tokens, or with a token that is empty, not text, too long, not
    valid Unicode, holding a control character, or ``--path``, which is the launcher's to give, is refused."""
    with pytest.raises(ProjectConfigurationError):
        parse_request(document)


@pytest.mark.parametrize("requested", ["\x1b[2J", "x" * 100000, 4, "2026-10-24", "2026-10-24T10:00:00"])
def test_a_requests_time_must_be_an_iso_time_with_its_zone(requested: Any) -> None:
    """The time a request says it was asked is shown on a terminal and kept in results, so it must be a short
    ISO time with a time zone: terminal controls, an overlong string, a number, a date and a time without a zone
    are refused."""
    with pytest.raises(ProjectConfigurationError, match="ISO time"):
        parse_request({"format": 1, "arguments": ["authorize", "network", "host"], "requested": requested})


def test_a_result_document_carries_the_status_the_text_and_the_time() -> None:
    """A result is a format-1 document with its status, its text and the time given."""
    assert result_document("recorded", "done", "2026-10-24T12:00:00+00:00") == {
        "format": 1, "status": "recorded", "text": "done", "at": "2026-10-24T12:00:00+00:00"}


def test_a_results_text_is_cut_so_that_the_document_stays_readable() -> None:
    """A text longer than a result may hold is cut and says so, and the document stays under the size a reader
    of the channel accepts."""
    document = result_document("refused", "x" * (256 * 1024), "2026-10-24T12:00:00+00:00")

    assert document["text"].endswith("[Output truncated; inspect configuration on the host.]")
    assert len(json.dumps(document).encode()) < 256 * 1024


def test_a_listing_document_gives_back_its_time_and_its_listing() -> None:
    """The launcher's listing document, read back, gives the time it was written with and the listing."""
    listing = {"rows": [{"kind": "ide", "name": "python-ide"}]}

    assert parse_listing(listing_document(listing, "2026-10-24T12:00:00+00:00")) == ("2026-10-24T12:00:00+00:00", listing)


@pytest.mark.parametrize("document", [[], {"format": 2}, {"format": 1, "at": "t", "listing": {}}, {"format": 1, "listing": {"rows": []}}])
def test_a_listing_document_without_its_time_or_its_rows_is_refused(document: Any) -> None:
    """A listing document of another format, without the time, or whose listing has no rows, is refused."""
    with pytest.raises(ProjectConfigurationError):
        parse_listing(document)


def test_deferred_requests_survive_being_written_and_read() -> None:
    """Requests kept for the host, rendered as the store's text and parsed again, are the same requests."""
    kept = [DeferredRequest("000001-authorize", "2026-10-24T10:00:00+00:00", ("authorize", "network", "host")),
            DeferredRequest("000002-bind", "", ("bind", "home", "~/capsule home"))]

    assert parse_deferred(json.loads(render_deferred(kept))) == kept
    assert kept[0].statement == "config authorize network host"


@pytest.mark.parametrize("document", [
    [], {"format": 1, "requests": {}}, {"format": 1, "requests": [{"id": "x", "arguments": ["ide"]}]},
    {"format": 1, "requests": [{"id": "000001-ide", "requested": 4, "arguments": ["ide"]}]},
    {"format": 1, "requests": [{"id": "000001-ide", "arguments": []}]},
])
def test_a_malformed_store_of_deferred_requests_is_refused(document: Any) -> None:
    """A store that is not a format-1 document with a list of requests, or holds a request with an id outside
    the contract, a time that is not text or no tokens, is refused."""
    with pytest.raises(ProjectConfigurationError):
        parse_deferred(document)


def test_a_document_written_complete_is_read_back_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    """``write_complete`` publishes the document under the name given, and the directory then holds that file
    alone."""
    path = write_complete(tmp_path / "000001-ide.result.json", {"format": 1, "text": "done"})

    assert read_document(path) == {"format": 1, "text": "done"}
    assert [item.name for item in tmp_path.iterdir()] == ["000001-ide.result.json"]


def test_publishing_over_a_symbolic_link_replaces_the_link_and_leaves_its_target_alone(tmp_path: Path) -> None:
    """Anything in the capsule can plant a link where the launcher will publish. The published name becomes a
    regular file with the document; the file the link pointed to is unchanged."""
    outside = tmp_path / "outside"
    outside.write_text("unchanged")
    destination = tmp_path / "000001-ide.result.json"
    destination.symlink_to(outside)

    write_complete(destination, {"format": 1, "text": "done"})

    assert not destination.is_symlink() and read_document(destination) == {"format": 1, "text": "done"}
    assert outside.read_text() == "unchanged"


def test_a_document_is_never_read_through_a_symbolic_link(tmp_path: Path) -> None:
    """A link is refused as a document, whether it points to nothing or to a readable file."""
    target = tmp_path / "target.json"
    target.write_text("{}")
    (tmp_path / "dangling.json").symlink_to(tmp_path / "missing")
    (tmp_path / "pointing.json").symlink_to(target)

    for name in ("dangling.json", "pointing.json"):
        with pytest.raises(ProjectConfigurationError, match="cannot open"):
            read_document(tmp_path / name)


def test_a_document_that_is_not_a_regular_file_is_refused_without_waiting_for_it(tmp_path: Path) -> None:
    """A named pipe where a document should be is refused as not a regular file; the read does not block on it."""
    pipe = tmp_path / "000001-ide.result.json"
    os.mkfifo(pipe)

    with pytest.raises(ProjectConfigurationError, match="not a regular file"):
        read_document(pipe)


def test_a_document_larger_than_the_limit_or_not_json_is_refused(tmp_path: Path) -> None:
    """A file over the size limit is refused by its size, and a file that is not JSON by its content."""
    big = tmp_path / "big.json"
    big.write_text("[" + "1," * 200000 + "1]")
    partial = tmp_path / "partial.json"
    partial.write_text('{"format":')

    with pytest.raises(ProjectConfigurationError, match="larger than"):
        read_document(big)
    with pytest.raises(ProjectConfigurationError, match="not a JSON document"):
        read_document(partial)
