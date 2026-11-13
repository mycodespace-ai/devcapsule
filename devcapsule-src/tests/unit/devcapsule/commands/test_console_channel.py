"""Unit tests of ``devcapsule/commands/_console_channel.py``: the launcher's side of the console's channel.

The launcher answers a request file by running ``project config`` as a
process. Here that runner is a value of the test, ``Runner``, which notes
what it was asked to run and answers as the test says, so the tests of what
is applied, kept or refused start no program. The channel directory, the
checkout's record and the home are the test's own, under its directory.

Two operations are about a process itself, ``run_command`` and
``child_environment``; their tests start one small Python program whose
whole text is in the test.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, Sequence

import pytest

from devcapsule.commands._console_channel import (
    ChannelView, ChannelWatcher, apply_deferred, child_environment, discard_deferred, handle_request, read_channel,
    render_running_listing, run_command, running_listing_document, sweep,
)
from devcapsule.configuration.console_channel import DeferredRequest, listing_document, read_document, write_complete
from devcapsule.configuration.console_requests import deferred_requests, write_deferred
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.listing import Listing, ListingRow
from devcapsule.configuration.storage import config_root

ASKED_AT = "2026-10-24T10:00:00+00:00"
ROOT = Path("/projects/order")
"""The project's directory, as the runner is told it; no test opens it."""


class Runner:
    """Stands where ``run_config`` is: notes each command it is asked to run, and answers ``status`` and ``output``."""

    def __init__(self, status: int = 0, output: str = "the command's own output") -> None:
        self.status, self.output = status, output
        self.calls: list[tuple[Path, tuple[str, ...], bool]] = []
        self.called = threading.Event()

    def __call__(self, root: Path, arguments: Sequence[str], *, host_confirmed: bool = False) -> tuple[int, str]:
        self.calls.append((root, tuple(arguments), host_confirmed))
        self.called.set()
        return self.status, self.output


@pytest.fixture
def channel(tmp_path: Path) -> Path:
    """The directory the launcher mounts into the capsule for one run, empty."""
    directory = tmp_path / "channel"
    directory.mkdir()
    return directory


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """The record, in the test's home, of a checkout of ``owner/order`` that lies under the test's directory."""
    path = config_root() / "projects" / "owner" / "order" / "devcapsule.checkout.toml"
    path.parent.mkdir(parents=True)
    path.write_text(render_toml({"checkout": {"path": str(tmp_path / "order")}}), encoding="utf-8")
    return path


def ask(channel: Path, identifier: str, *arguments: str) -> Path:
    """Put one request in the channel as the console writes it, asked at ``ASKED_AT``."""
    return write_complete(channel / f"{identifier}.request.json",
                          {"format": 1, "requested": ASKED_AT, "arguments": list(arguments)})


def result(channel: Path, identifier: str) -> dict[str, Any]:
    """The launcher's answer to the request ``identifier``."""
    return read_document(channel / f"{identifier}.result.json")


def test_a_request_applied_at_once_runs_its_command_and_reports_the_commands_output(channel: Path, record: Path) -> None:
    """A request for the checkout's own choice is run as its tokens, not as confirmed on the host. When the
    command succeeds the result is ``recorded``, with the command's output and the note that the running
    capsule is unchanged."""
    run = Runner(0, "Your IDE for this checkout: python-ide (pycharm).")

    answer = handle_request(ROOT, record, ask(channel, "000001-ide", "ide", "python-ide"), run=run)

    assert run.calls == [(ROOT, ("ide", "python-ide"), False)]
    assert answer == result(channel, "000001-ide")
    assert answer["status"] == "recorded"
    assert answer["text"] == ("Recorded for the next launch. This running capsule is unchanged.\n"
                              "Your IDE for this checkout: python-ide (pycharm).")


def test_a_command_that_fails_makes_its_request_refused_in_the_commands_words(channel: Path, record: Path) -> None:
    """When the command exits with another status than 0, the result is ``refused`` and its text is what the
    command printed; a command that printed nothing is named with its status."""
    spoken = handle_request(ROOT, record, ask(channel, "000001-ide", "ide", "no-such-ide"), run=Runner(2, "Unknown IDE 'no-such-ide'"))
    silent = handle_request(ROOT, record, ask(channel, "000002-ide", "ide", "no-such-ide"), run=Runner(2, ""))

    assert (spoken["status"], spoken["text"]) == ("refused", "Unknown IDE 'no-such-ide'")
    assert (silent["status"], silent["text"]) == ("refused", "config ide no-such-ide exited with status 2")


def test_a_sweep_answers_each_request_once_in_the_order_of_their_names(channel: Path, record: Path) -> None:
    """A sweep answers every request that has no result, lowest name first, and says how many. A second sweep
    finds them answered: it answers none and runs nothing."""
    ask(channel, "000002-deny", "deny", "network")
    ask(channel, "000001-ide", "ide", "python-ide")
    run = Runner()

    assert sweep(channel, ROOT, record, run=run) == 2
    assert sweep(channel, ROOT, record, run=run) == 0

    assert [arguments for _, arguments, _ in run.calls] == [("ide", "python-ide"), ("deny", "network")]


@pytest.mark.parametrize("tokens", [
    ("authorize", "network", "host"), ("forget", "docker-daemon"),
    ("env", "set", "HOST_SECRET", "--from-host"), ("env", "set", "HOST_SECRET", "--from-h"),
])
def test_a_request_that_can_widen_is_kept_for_the_host_and_no_command_is_run(channel: Path, record: Path, tokens: tuple[str, ...]) -> None:
    """A widening is not run. It is kept for the checkout with its tokens and the time the console asked, and
    the result is ``deferred``, carrying that time and naming the command that applies it on the host."""
    run = Runner()
    ask(channel, "000001-change", *tokens)

    assert sweep(channel, ROOT, record, run=run) == 1

    assert run.calls == []
    assert deferred_requests(record) == [DeferredRequest("000001-change", ASKED_AT, tokens)]
    answer = result(channel, "000001-change")
    assert (answer["status"], answer["at"]) == ("deferred", ASKED_AT)
    assert "This command can widen access. Nothing has been applied." in answer["text"]
    assert "devcapsule project config console apply 000001-change" in answer["text"]


def test_a_request_the_launcher_does_not_take_is_refused_with_the_reason_and_nothing_is_kept(channel: Path, record: Path) -> None:
    """A read-only command asked through the channel is refused with the classification's reason; no command is
    run and nothing is kept for the host."""
    run = Runner()

    answer = handle_request(ROOT, record, ask(channel, "000001-show", "show"), run=run)

    assert (answer["status"], answer["text"]) == ("refused", "config show is read-only; the console shows what it reports")
    assert run.calls == [] and deferred_requests(record) == []


def test_a_request_whose_document_is_not_the_contracts_is_refused(channel: Path, record: Path) -> None:
    """A request file with a well-formed name and a document of another format is answered ``refused``, naming
    the file."""
    path = write_complete(channel / "000001-ide.request.json", {"format": 2, "arguments": ["ide", "python-ide"]})

    answer = handle_request(ROOT, record, path, run=Runner())

    assert answer["status"] == "refused" and "000001-ide.request.json: not a format-1 request document" in answer["text"]


@pytest.mark.parametrize("kind", ["link", "pipe", "huge", "partial"])
def test_a_request_file_that_cannot_be_read_is_refused_and_does_not_keep_the_next_one_waiting(
    channel: Path, record: Path, kind: str,
) -> None:
    """Anything in the capsule can write to the channel. A request that is a link, a named pipe, larger than a
    document may be, or cut short is answered ``refused``, and the request after it is still run. A file
    whose name is not a request's is left unanswered."""
    bad = channel / "000001-ide.request.json"
    if kind == "link":
        bad.symlink_to(record)
    elif kind == "pipe":
        os.mkfifo(bad)
    elif kind == "huge":
        bad.write_bytes(b" " * (256 * 1024 + 1))
    else:
        bad.write_text('{"format":')
    (channel / "outside.request.json").write_text("{}")
    ask(channel, "000002-deny", "deny", "network")
    run = Runner()

    assert sweep(channel, ROOT, record, run=run) == 2

    assert result(channel, "000001-ide")["status"] == "refused"
    assert result(channel, "000002-deny")["status"] == "recorded"
    assert [arguments for _, arguments, _ in run.calls] == [("deny", "network")]
    assert not (channel / "outside.result.json").exists()


def test_a_request_named_like_one_already_kept_is_kept_beside_it_under_a_new_id(tmp_path: Path, record: Path) -> None:
    """A console numbers its requests from 1 in every run. A widening whose name was already kept in an earlier
    run does not replace that one: both are kept, the later under an id of the launcher's, which its result names."""
    for name, node, value in (("first-run", "network", "host"), ("second-run", "docker-daemon", "host-socket")):
        directory = tmp_path / name
        directory.mkdir()
        ask(directory, "000001-authorize", "authorize", node, value)
        sweep(directory, ROOT, record, run=Runner())

    first, second = deferred_requests(record)

    assert (first.id, first.arguments) == ("000001-authorize", ("authorize", "network", "host"))
    assert second.id != first.id and second.arguments == ("authorize", "docker-daemon", "host-socket")
    assert f"Saved request {second.id}:" in result(tmp_path / "second-run", "000001-authorize")["text"]


def test_while_the_launcher_stops_a_request_that_would_be_applied_is_kept_instead(channel: Path, record: Path) -> None:
    """Once the launcher is stopping it runs no more commands: a request it would have applied is kept for the
    host, and its result says that the launcher is stopping."""
    run = Runner()

    answer = handle_request(ROOT, record, ask(channel, "000001-set", "set", "cpus", "2"), stopping=True, run=run)

    assert run.calls == []
    assert answer["status"] == "deferred" and "The launcher is stopping." in answer["text"]
    assert deferred_requests(record) == [DeferredRequest("000001-set", ASKED_AT, ("set", "cpus", "2"))]


def test_the_watcher_answers_a_request_while_the_capsule_runs(channel: Path, record: Path) -> None:
    """A started watcher answers a request written after it started, without being asked to."""
    run = Runner()
    watcher = ChannelWatcher(channel, ROOT, record, interval=0.01, run=run)
    watcher.start()
    try:
        ask(channel, "000001-deny", "deny", "network")
        assert run.called.wait(timeout=30), "the watcher did not run the request's command"
    finally:
        watcher.stop()

    assert result(channel, "000001-deny")["status"] == "recorded"


def test_stopping_the_watcher_answers_what_is_waiting_without_running_a_command(channel: Path, record: Path) -> None:
    """``stop`` sweeps once more and returns when the watcher's thread has ended. The requests still waiting
    are answered then, kept for the host and not run, the one that would have been applied included."""
    run = Runner()
    watcher = ChannelWatcher(channel, ROOT, record, interval=3600, run=run)
    watcher.start()
    ask(channel, "000001-ide", "ide", "frontend-ide")
    ask(channel, "000002-authorize", "authorize", "docker-daemon", "host-socket")

    watcher.stop()

    assert not watcher._thread.is_alive()
    assert run.calls == []
    assert [item.arguments[0] for item in deferred_requests(record)] == ["ide", "authorize"]
    assert "The launcher is stopping." in result(channel, "000001-ide")["text"]


def test_applying_a_kept_request_runs_its_exact_tokens_as_confirmed_on_the_host_and_forgets_it(record: Path) -> None:
    """``apply_deferred`` runs the kept request's tokens unchanged, spaces and shell characters included, as a
    command the human confirmed on the host, returns the command's status and output, and forgets the request."""
    tokens = ("docker-args", "set", "--env", "TEXT=a b;$(false)")
    write_deferred(record, [DeferredRequest("000001-docker-args", ASKED_AT, tokens)])
    run = Runner(0, "done")

    assert apply_deferred(ROOT, record, "000001-docker-args", run=run) == (0, "done")

    assert run.calls == [(ROOT, tokens, True)]
    assert deferred_requests(record) == []


def test_a_kept_request_whose_command_fails_stays_kept(record: Path) -> None:
    """When the command of a kept request fails, its status and output are returned and the request still
    awaits the host."""
    kept = DeferredRequest("000001-authorize", ASKED_AT, ("authorize", "quantum", "x"))
    write_deferred(record, [kept])

    assert apply_deferred(ROOT, record, "000001-authorize", run=Runner(2, "Unknown authorization 'quantum'")) == (2, "Unknown authorization 'quantum'")

    assert deferred_requests(record) == [kept]


def test_discarding_a_kept_request_forgets_it_and_runs_nothing(record: Path) -> None:
    """``discard_deferred`` removes the one request named and leaves the others."""
    kept = [DeferredRequest("000001-authorize", ASKED_AT, ("authorize", "network", "host")),
            DeferredRequest("000002-bind", ASKED_AT, ("bind", "home", "~/capsule-home"))]
    write_deferred(record, kept)

    discard_deferred(record, "000002-bind")

    assert deferred_requests(record) == kept[:1]


def test_applying_or_discarding_a_request_that_is_not_kept_is_refused(record: Path) -> None:
    """An id that no kept request of the checkout has is refused by both operations, and no command is run."""
    run = Runner()

    with pytest.raises(ProjectConfigurationError, match="No console request '000009-x' awaits confirmation"):
        apply_deferred(ROOT, record, "000009-x", run=run)
    with pytest.raises(ProjectConfigurationError, match="No console request '000009-x' awaits confirmation"):
        discard_deferred(record, "000009-x")

    assert run.calls == []


LAUNCHERS_SHELL = {
    "HOME": "/home/developer", "PATH": "/usr/bin", "LANG": "C.UTF-8", "LC_TIME": "ro_RO.UTF-8", "TMPDIR": "/tmp/own",
    "DEVCAPSULE_CONFIG_HOME": "/homes/developer", "XDG_CONFIG_HOME": "/home/developer/.config",
    "HOST_SECRET": "never expose", "PYTHONPATH": "/somewhere/injected", "DOCKER_HOST": "ssh://host-context.example",
}
"""An environment a launcher could run in: where its records are, the locale, and three things a child must not get."""


def test_a_command_run_for_the_console_inherits_the_record_locations_and_the_locale_only() -> None:
    """The child gets where the home and the records are, the search path, the temporary directory and the
    locale. It gets no other variable: not a secret, not a Python path, not the Docker context."""
    assert child_environment(LAUNCHERS_SHELL) == {
        "HOME": "/home/developer", "PATH": "/usr/bin", "LANG": "C.UTF-8", "LC_TIME": "ro_RO.UTF-8", "TMPDIR": "/tmp/own",
        "DEVCAPSULE_CONFIG_HOME": "/homes/developer", "XDG_CONFIG_HOME": "/home/developer/.config",
    }


def test_a_command_the_human_confirmed_on_the_host_inherits_the_whole_environment() -> None:
    """With ``host_confirmed`` the child is an ordinary command of the human's shell: every variable passes, the
    Docker context among them, in a copy of its own."""
    inherited = child_environment(LAUNCHERS_SHELL, host_confirmed=True)

    assert inherited == LAUNCHERS_SHELL and inherited is not LAUNCHERS_SHELL


PROBE = "import json, os, sys; print(json.dumps([dict(os.environ), os.getsid(0), os.getpid(), sys.stdin.read()]))"
"""A program that reports what it was given: its environment, its session, its process id and its input."""


def test_the_child_runs_in_a_session_of_its_own_with_the_environment_given_and_no_input() -> None:
    """``run_command`` starts the command in a new session, of which the child is the leader, with exactly
    the environment given and an input that is already at its end."""
    status, output = run_command([sys.executable, "-c", PROBE], {"ONLY": "this"}, 30)

    environment, session, process, read = json.loads(output)
    assert status == 0
    assert environment.get("ONLY") == "this" and "PATH" not in environment and "HOME" not in environment
    assert session == process and session != os.getsid(0)
    assert read == ""


def test_the_childs_status_and_both_its_outputs_come_back() -> None:
    """The result is the child's exit status and what it wrote to standard output and standard error, in the
    order written, without the surrounding blank space."""
    program = "import sys; print('to output', flush=True); print('to error', file=sys.stderr, flush=True); sys.exit(3)"

    assert run_command([sys.executable, "-c", program], {}, 30) == (3, "to output\nto error")


def test_a_command_that_cannot_be_started_is_status_one_with_the_reason(tmp_path: Path) -> None:
    """A command whose program does not exist is reported, not raised: status 1 and a line that names the cause."""
    status, output = run_command([str(tmp_path / "no-such-program")], {}, 30)

    assert status == 1 and output.startswith("cannot run the configuration command: ")


def test_a_command_that_outlives_its_time_is_killed_with_the_processes_it_started(tmp_path: Path) -> None:
    """A child still running at the timeout is killed and reported as status 1 with the timeout. A process it
    started is killed with it: that process had begun, and never reaches the line after its own wait."""
    started, escaped = tmp_path / "started", tmp_path / "escaped"
    grandchild = (f"from pathlib import Path; import time; Path({str(started)!r}).touch(); "
                  f"time.sleep(0.8); Path({str(escaped)!r}).touch()")
    child = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(30)"

    assert run_command([sys.executable, "-c", child], {}, 0.3) == (1, "the command did not finish within 0.3 seconds")

    assert started.exists()
    time.sleep(0.9)  # Longer than the grandchild's own wait: alive, it would have written by now.
    assert not escaped.exists()


LISTING = {
    **Listing((ListingRow("ide", "python-ide", "pycharm 2026.2", "checkout"),)).document(),
    "project": {"creator": "owner", "slug": "order"},
    "checkout": {"name": "default", "launcher-path": "/host/order", "input": "/homes/developer/order.toml"},
}
"""A launch-time listing as the launcher writes it: one row, and whose checkout it is."""

THIS_CAPSULE: dict[str, Any] = {
    "launcher_root": "/host/order", "checkout_name": "default", "project": {"creator": "owner", "slug": "order", "name": "Order"},
    "launcher_command": "devcapsule project --path /host/order config show",
}
"""What a capsule knows of itself: the checkout the launcher started it for, and the host command that shows it."""


def test_a_channel_without_the_launchers_listing_is_an_error_that_sends_to_the_host(channel: Path) -> None:
    """Reading a channel directory in which the launcher wrote no listing is refused, with the advice to inspect
    the configuration on the host."""
    with pytest.raises(ProjectConfigurationError, match="no launch listing; inspect configuration on the host"):
        read_channel(channel)


def test_the_view_of_a_channel_is_the_listing_with_its_time_and_each_request_with_its_answer(channel: Path) -> None:
    """The view carries the launch-time listing and when it was written, then every request in name order with
    its statement and the launcher's result, or None for a request not yet answered."""
    write_complete(channel / "listing.json", listing_document(LISTING, "2026-10-24T12:00:00+00:00"))
    ask(channel, "000001-ide", "ide", "frontend-ide")
    write_complete(channel / "000001-ide.result.json", {"format": 1, "status": "recorded", "text": "done", "at": "t"})
    ask(channel, "000002-authorize", "authorize", "network", "host")

    view = read_channel(channel)

    assert (view.at, view.listing) == ("2026-10-24T12:00:00+00:00", LISTING)
    answered, waiting = view.requests
    assert (answered["id"], answered["statement"], answered["requested"]) == ("000001-ide", "config ide frontend-ide", ASKED_AT)
    assert answered["result"] == {"format": 1, "status": "recorded", "text": "done", "at": "t"}
    assert (waiting["id"], waiting["arguments"], waiting["result"]) == ("000002-authorize", ["authorize", "network", "host"], None)


@pytest.mark.parametrize("planted", ["empty", "without-text", "pipe"])
def test_a_result_that_cannot_be_read_is_shown_as_unknown_and_does_not_fail_the_view(channel: Path, planted: str) -> None:
    """A result file that is not the contract's document, or not a regular file, is shown with the status
    ``unknown`` and a text that says the result cannot be read and to inspect on the host before retrying."""
    write_complete(channel / "listing.json", listing_document(LISTING))
    ask(channel, "000001-ide", "ide", "python-ide")
    path = channel / "000001-ide.result.json"
    if planted == "pipe":
        os.mkfifo(path)
    else:
        write_complete(path, {} if planted == "empty" else {"format": 1, "status": "recorded"})

    (request,) = read_channel(channel).requests

    assert request["result"]["status"] == "unknown"
    assert request["result"]["text"].startswith("Cannot read the launcher result: ")
    assert "Inspect configuration on the host before retrying." in request["result"]["text"]


def test_a_request_file_that_cannot_be_read_is_shown_as_refused_under_its_file_name(channel: Path) -> None:
    """A request whose document is not the contract's is listed by its file name, with no statement and a
    refusal that says why."""
    write_complete(channel / "listing.json", listing_document(LISTING))
    write_complete(channel / "000001-ide.request.json", {"format": 2})

    (request,) = read_channel(channel).requests

    assert (request["id"], request["statement"], request["result"]["status"]) == ("000001-ide.request.json", "", "refused")


def a_view(*requests: dict[str, Any]) -> ChannelView:
    """The view of a channel whose listing is ``LISTING``, written at noon, with the requests given."""
    return ChannelView("2026-10-24T12:00:00+00:00", LISTING, tuple(requests))


ANSWERED = {"id": "000001-ide", "arguments": ["ide", "frontend-ide"], "statement": "config ide frontend-ide",
            "requested": ASKED_AT, "result": {"format": 1, "status": "recorded", "text": "done", "at": "t"}}
WAITING = {"id": "000002-authorize", "arguments": ["authorize", "network", "host"],
           "statement": "config authorize network host", "requested": ASKED_AT, "result": None}


def test_inside_a_capsule_the_json_document_is_the_listing_at_launch_with_the_requests_since() -> None:
    """The document keeps the launch-time listing's rows and adds that it is a running capsule's, the time of
    the listing, the console's requests, and the host command that shows the configuration."""
    document = running_listing_document(a_view(ANSWERED, WAITING), **THIS_CAPSULE)

    assert document["rows"] == LISTING["rows"]
    assert document["context"] == "running capsule: the launcher's listing at launch"
    assert document["at"] == "2026-10-24T12:00:00+00:00"
    assert document["console-requests"] == [ANSWERED, WAITING]
    assert document["launcher-command"] == "devcapsule project --path /host/order config show"


def test_inside_a_capsule_the_text_shows_the_listing_then_each_request_with_its_outcome() -> None:
    """The text names the checkout and the time of the listing, renders the listing, then lists each request
    asked since launch with the launcher's answer, or that it waits for the launcher, and ends with how to
    change the next launch."""
    text = render_running_listing(a_view(ANSWERED, WAITING), **THIS_CAPSULE)

    lines = text.splitlines()
    assert lines[:2] == ["Checkout: /host/order (default)", "At launch, 2026-10-24T12:00:00+00:00:"]
    assert any("python-ide" in line and "pycharm 2026.2" in line for line in lines)
    assert "Pending, next launch (asked on the console since launch):" in lines
    assert text.count("  000001-ide: config ide frontend-ide\n      recorded: done") == 1
    assert text.count("  000002-authorize: config authorize network host\n      waiting for the launcher") == 1
    assert lines[-1] == ("To change the next launch: the console's configuration page, or on the host: "
                         "devcapsule project --path /host/order config show")


def test_inside_a_capsule_with_nothing_asked_the_text_says_so() -> None:
    """With no request in the channel the text says that nothing was asked on the console since launch."""
    assert "Nothing asked on the console since launch." in render_running_listing(a_view(), **THIS_CAPSULE).splitlines()


@pytest.mark.parametrize("difference", [{"launcher_root": "/host/another-copy"}, {"checkout_name": "second"},
                                        {"project": {"creator": "owner", "slug": "another"}}])
def test_a_listing_written_for_another_checkout_is_refused_in_both_forms(difference: dict[str, Any]) -> None:
    """A listing whose checkout directory, checkout name or project is not this capsule's cannot stand in for
    this run: the document and the text are both refused, sending the reader to the host."""
    capsule = {**THIS_CAPSULE, **difference}

    with pytest.raises(ProjectConfigurationError, match="belongs to another checkout; inspect configuration on the host"):
        running_listing_document(a_view(), **capsule)
    with pytest.raises(ProjectConfigurationError, match="belongs to another checkout; inspect configuration on the host"):
        render_running_listing(a_view(), **capsule)
