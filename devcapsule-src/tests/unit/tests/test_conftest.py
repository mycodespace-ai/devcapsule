"""Unit tests of ``tests/conftest.py``: the shared fixtures, the marker sets they key on, the repository-input guard and the network guard."""
from __future__ import annotations

import socket
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests import conftest
from tests.conftest import (
    DOCKER_MARKERS,
    OUTSIDE_ANY_TEST,
    NetworkGuard,
    RepositoryInputGuard,
    install_network_guard,
    install_repository_input_guard,
    is_this_machine,
    load_python_route_inputs,
    outcome_counts,
)

_PYPROJECT = Path(__file__).resolve().parents[3] / "pyproject.toml"

NON_DOCKER_MARKERS = frozenset({"integration", "flaky", "legacy", "own_host_patches"})
"""The registered markers that never need Docker: process-boundary tests, visibility runs, legacy files,
and unit tests that set up their host themselves."""


def test_every_registered_marker_is_a_docker_marker_unless_it_is_a_known_non_docker_one() -> None:
    """Precondition: ``pyproject.toml`` registers the suite's markers. Action: read
    the registered names. Postcondition: ``DOCKER_MARKERS`` is exactly the registered
    set minus the four non-Docker markers, so a Docker suite cannot be registered
    without the isolation fixture learning that it keeps the developer's homes."""
    registered = {entry.split(":", 1)[0] for entry in tomllib.loads(_PYPROJECT.read_text())["tool"]["pytest"]["ini_options"]["markers"]}
    assert set(DOCKER_MARKERS) == registered - NON_DOCKER_MARKERS


def _inputs_file(directory: Path, text: str) -> Path:
    """A filter file with the given text, in the test's own directory."""
    path = directory / "ci-python-inputs.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_route_inputs_are_the_listed_entries_in_order(tmp_path: Path) -> None:
    """Precondition: a filter file listing a directory tree and a file under ``python``.
    Action: load it. Postcondition: both entries, in the order written."""
    listed = _inputs_file(tmp_path, "python:\n  - 'package/**'  # the package\n  - 'docs/versions.yaml'\n")
    assert load_python_route_inputs(listed) == ("package/**", "docs/versions.yaml")


@pytest.mark.parametrize("text", [
    "python: []\n",
    "docs:\n  - 'package/**'\n",
    "- 'package/**'\n",
    "python:\n  - 'package/*.py'\n",
    "python:\n  - 'docs/**/*.md'\n",
    "python:\n  - '!package/**'\n",
    "python:\n  - '/package/**'\n",
    "python:\n  - '**'\n",
    "python:\n  - 7\n",
])
def test_a_list_the_guard_cannot_read_as_the_filter_does_is_refused(tmp_path: Path, text: str) -> None:
    """Precondition: a filter file with no ``python`` list, or with an entry that is neither a
    file path nor ``DIRECTORY/**``. Action: load it. Postcondition: ``ValueError``, so the guard
    never matches a pattern differently from the hosted filter."""
    with pytest.raises(ValueError):
        load_python_route_inputs(_inputs_file(tmp_path, text))


def _guard(root: Path) -> RepositoryInputGuard:
    """A guard over ``root`` whose inputs are one directory tree and one file."""
    return RepositoryInputGuard(root, ("package/**", "docs/versions.yaml"))


@pytest.mark.parametrize(("path", "expected"), [
    ("package/module.py", None),
    ("package/assets/definition/WORKFLOW.md", None),
    ("package", None),
    ("docs/versions.yaml", None),
    (".git/HEAD", None),
    (".git", None),
    ("docs/guide.md", "docs/guide.md"),
    ("docs", "docs"),
    ("package-notes/idea.md", "package-notes/idea.md"),
    ("engineering-docs/bugs/a.md", "engineering-docs/bugs/a.md"),
    (".github/workflows/tests.yml", ".github/workflows/tests.yml"),
    ("", "."),
])
def test_a_repository_path_is_unlisted_exactly_when_no_entry_covers_it(tmp_path: Path, path: str, expected: str | None) -> None:
    """Precondition: a repository root and the two inputs of ``_guard``. Action: ask about an
    absolute path under the root. Postcondition: ``None`` under an input or under ``.git``;
    otherwise the repository-relative path, with ``.`` for the root itself. A directory whose
    name merely begins like an input's is not covered by it."""
    assert _guard(tmp_path).unlisted(tmp_path / path) == expected


@pytest.mark.parametrize("path", [7, None, b"elsewhere"])
def test_what_is_not_a_repository_path_is_never_unlisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: Any) -> None:
    """Precondition: a repository root, and the current directory outside it. Action: ask about a
    file descriptor, a missing path that stands for the current directory, and a bytes path
    relative to that directory. Postcondition: ``None`` each time."""
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    assert _guard(tmp_path / "repository").unlisted(path) is None


def test_a_relative_path_is_taken_from_the_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Precondition: the current directory is ``docs`` inside the repository. Action: ask about
    the relative path ``guide.md``, as bytes. Postcondition: ``docs/guide.md``, where the read
    itself would look."""
    (tmp_path / "docs").mkdir()
    monkeypatch.chdir(tmp_path / "docs")
    assert _guard(tmp_path).unlisted(b"guide.md") == "docs/guide.md"


def test_a_counted_readers_unlisted_access_is_a_recorded_breach(tmp_path: Path) -> None:
    """Precondition: a guard attending a test whose outcome counts. Action: report its access to
    an unlisted path. Postcondition: a message naming the test, the path and the filter file,
    and the breach on record."""
    guard = _guard(tmp_path)
    guard.attend("tests/test_a.py::test_reads_docs", counted=True)
    message = guard.breach(tmp_path / "docs" / "guide.md")
    assert message is not None
    assert "tests/test_a.py::test_reads_docs" in message and "docs/guide.md" in message
    assert ".github/ci-python-inputs.yml" in message
    assert guard.breaches == [("tests/test_a.py::test_reads_docs", "docs/guide.md")]


@pytest.mark.parametrize(("path", "counted"), [("docs/guide.md", False), ("package/module.py", True)])
def test_an_uncounted_reader_and_a_listed_path_are_no_breach(tmp_path: Path, path: str, counted: bool) -> None:
    """Precondition: a guard attending a test. Action: report an unlisted path read by a test
    whose outcome does not count, and a listed path read by one whose outcome does.
    Postcondition: no message and nothing on record."""
    guard = _guard(tmp_path)
    guard.attend("tests/test_a.py::test_one", counted=counted)
    assert guard.breach(tmp_path / path) is None
    assert guard.breaches == []


def test_what_is_read_outside_any_test_counts(tmp_path: Path) -> None:
    """Precondition: a guard that attended an uncounted test and left it. Action: report an
    unlisted path. Postcondition: a breach, read by ``OUTSIDE_ANY_TEST``: a module that reads
    the repository while it is imported is held to the rule."""
    guard = _guard(tmp_path)
    guard.attend("tests/test_a.py::test_expected_to_fail", counted=False)
    guard.leave()
    assert guard.breach(tmp_path / "README.md") is not None
    assert guard.breaches == [(OUTSIDE_ANY_TEST, "README.md")]


@pytest.mark.parametrize(("event", "arguments"), [
    ("open", ("docs/guide.md", "r", 0)),
    ("os.listdir", ("docs",)),
    ("os.scandir", ("docs",)),
    ("os.listdir", (None,)),
])
def test_opening_or_listing_an_unlisted_path_fails_where_it_happens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, event: str, arguments: tuple[Any, ...],
) -> None:
    """Precondition: the current directory is the repository root, which is not an input.
    Action: deliver the audit event of an open, of a listing, and of a listing of the current
    directory. Postcondition: ``pytest.fail``'s exception, which ``except Exception`` does not
    catch, and one breach on record."""
    monkeypatch.chdir(tmp_path)
    guard = _guard(tmp_path)
    with pytest.raises(pytest.fail.Exception) as failure:
        guard.audit(event, arguments)
    assert not isinstance(failure.value, Exception)
    assert len(guard.breaches) == 1


@pytest.mark.parametrize(("event", "arguments"), [
    ("open", ("package/module.py", "r", 0)),
    ("os.remove", ("docs/guide.md", -1)),
    ("import", ("docs", None, None, None, None)),
    ("open", ()),
])
def test_other_events_and_listed_paths_pass_the_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, event: str, arguments: tuple[Any, ...],
) -> None:
    """Precondition: the current directory is the repository root. Action: deliver an open of a
    listed path, two events the guard does not watch, and an event without arguments.
    Postcondition: nothing is raised and nothing is recorded."""
    monkeypatch.chdir(tmp_path)
    guard = _guard(tmp_path)
    guard.audit(event, arguments)
    assert guard.breaches == []


def _item(**markers: Any) -> Any:
    """A stand-in for a test item carrying the given markers by name."""
    return SimpleNamespace(get_closest_marker=markers.get)


def _mark(*args: Any, **kwargs: Any) -> Any:
    """A stand-in for a marker with the given arguments."""
    return SimpleNamespace(args=args, kwargs=kwargs)


@pytest.mark.parametrize(("item", "counts"), [
    (_item(), True),
    (_item(legacy=_mark()), True),
    (_item(integration=_mark()), False),
    (_item(docker=_mark()), False),
    (_item(xfail=_mark(reason="known")), False),
    (_item(xfail=_mark(reason="known", strict=False)), False),
    (_item(xfail=_mark(reason="known", strict=True)), True),
    (_item(xfail=_mark(True, reason="only in a capsule")), True),
])
def test_an_outcome_counts_unless_the_job_skips_the_test_or_passes_whatever_it_does(item: Any, counts: bool) -> None:
    """Precondition: a test item with no marker, a marker of a heavier suite, or an
    expected-to-fail mark in each of its forms. Action: ask whether its outcome counts, with
    ``integration`` and ``docker`` as the heavier suites. Postcondition: it does not for a
    heavier suite or an unconditional, non-strict expected failure; it does otherwise,
    because a strict mark can fail the job and a conditional one holds on some machines only."""
    assert outcome_counts(item, ("integration", "docker")) is counts


def test_the_first_guard_installed_stays_in_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Precondition: a process in which a guard is already installed, set here by the test.
    Action: install another. Postcondition: the first is returned and the second is not kept,
    since an audit hook cannot be removed."""
    first, second = _guard(tmp_path / "first"), _guard(tmp_path / "second")
    monkeypatch.setattr(conftest, "_installed_guard", first)
    assert install_repository_input_guard(second) is first


# The network guard. These tests hand the guard the audit events a socket
# call raises, as values. No test here sends anything: the addresses are the
# ones RFC 5737 and RFC 3849 reserve for documentation, and a ``.test`` name.

UNIT_TEST = "tests/unit/devcapsule/test_thing.py::test_one"
ELSEWHERE_V4 = ("192.0.2.1", 443)
ELSEWHERE_V6 = ("2001:db8::1", 443, 0, 0)


@contextmanager
def _unsent(family: socket.AddressFamily) -> Iterator[socket.socket]:
    """A datagram socket of the given family that is never bound, connected or written to."""
    with socket.socket(family, socket.SOCK_DGRAM) as peer:
        yield peer


@pytest.mark.parametrize("host", [None, "", "localhost", "127.0.0.1", "127.8.9.1", "::1", "0.0.0.0", "::", b"127.0.0.1"])
def test_no_host_localhost_and_loopback_addresses_are_this_machine(host: Any) -> None:
    """``is_this_machine`` is true for an absent host, ``localhost``, and every loopback or unspecified address."""
    assert is_this_machine(host) is True


@pytest.mark.parametrize("host", ["192.0.2.1", "2001:db8::1", "example.test", "build-host-7", b"example.test"])
def test_every_other_address_and_every_other_name_is_not_this_machine(host: Any) -> None:
    """``is_this_machine`` is false for a routable address and for any name but ``localhost``, a bare host name included."""
    assert is_this_machine(host) is False


@pytest.mark.parametrize("event", ["socket.connect", "socket.sendto", "socket.sendmsg"])
@pytest.mark.parametrize(("family", "address"), [(socket.AF_INET, ELSEWHERE_V4), (socket.AF_INET6, ELSEWHERE_V6)])
def test_a_unit_tests_reach_for_another_machine_fails_before_anything_is_sent(
    event: str, family: socket.AddressFamily, address: tuple[Any, ...],
) -> None:
    """While the guard attends a unit test, the audit event of a connect or a send to another machine raises
    ``pytest.fail``'s exception, which ``except Exception`` does not catch, and records the test and the host."""
    guard = NetworkGuard()
    guard.attend(UNIT_TEST)
    with _unsent(family) as peer, pytest.raises(pytest.fail.Exception) as failure:
        guard.audit(event, (peer, address))
    assert not isinstance(failure.value, Exception)
    assert UNIT_TEST in str(failure.value) and "rule 9" in str(failure.value)
    assert guard.breaches == [(UNIT_TEST, f"reach {address[0]!r}")]


@pytest.mark.parametrize(("event", "arguments", "asked"), [
    ("socket.getaddrinfo", ("example.test", 443, 0, 1, 0), "example.test"),
    ("socket.gethostbyname", ("example.test",), "example.test"),
    ("socket.gethostbyaddr", ("192.0.2.1",), "192.0.2.1"),
])
def test_a_unit_tests_question_to_the_resolver_fails_and_is_recorded(
    event: str, arguments: tuple[Any, ...], asked: str,
) -> None:
    """While the guard attends a unit test, the audit event of a lookup of anything but this machine fails and is recorded."""
    guard = NetworkGuard()
    guard.attend(UNIT_TEST)
    with pytest.raises(pytest.fail.Exception):
        guard.audit(event, arguments)
    assert guard.breaches == [(UNIT_TEST, f"look up {asked!r}")]


def test_what_stays_on_this_machine_passes_the_guard(tmp_path: Path) -> None:
    """While the guard attends a unit test, loopback peers, a Unix socket, a send on a connected socket, lookups
    of this machine, an event the guard does not watch and an event without arguments raise nothing and record nothing."""
    guard = NetworkGuard()
    guard.attend(UNIT_TEST)
    with _unsent(socket.AF_INET) as v4, _unsent(socket.AF_INET6) as v6, _unsent(socket.AF_UNIX) as unix:
        guard.audit("socket.connect", (v4, ("127.0.0.1", 8080)))
        guard.audit("socket.sendto", (v6, ("::1", 8080, 0, 0)))
        guard.audit("socket.connect", (unix, str(tmp_path / "service.sock")))
        # The family decides, not the shape of the address: a socket that is not an internet socket cannot leave.
        guard.audit("socket.connect", (unix, ELSEWHERE_V4))
        guard.audit("socket.sendmsg", (v4, None))
        guard.audit("socket.connect", (v4,))
    guard.audit("socket.getaddrinfo", ("localhost", 80, 0, 1, 0))
    guard.audit("socket.getaddrinfo", (None, 80, 0, 1, 0))
    guard.audit("socket.gethostbyaddr", ("127.0.0.1",))
    guard.audit("open", ("192.0.2.1", "r", 0))
    guard.audit("socket.getaddrinfo", ())
    assert guard.breaches == []


def test_the_guard_stands_down_until_it_attends_a_test_and_after_it_leaves_one() -> None:
    """A guard that attends no test, before its first and after ``leave``, lets a reach for another machine pass
    unrecorded: between tests, and during a heavier suite's test, the network is not the unit suite's concern."""
    guard = NetworkGuard()
    with _unsent(socket.AF_INET) as peer:
        guard.audit("socket.connect", (peer, ELSEWHERE_V4))
        guard.attend(UNIT_TEST)
        guard.leave()
        guard.audit("socket.connect", (peer, ELSEWHERE_V4))
    assert guard.breaches == []


def test_the_network_guard_in_force_is_not_replaced_by_a_later_one() -> None:
    """Once a network guard is in force, here whichever one this process has after one install, installing
    another returns the one in force: an audit hook cannot be removed, so a process keeps its first."""
    in_force = install_network_guard(NetworkGuard())
    assert install_network_guard(NetworkGuard()) is in_force


def test_a_test_runs_on_no_capsule_wherever_the_suite_runs(tmp_path: Path) -> None:
    """Under the suite's fixture, each fixed path by which the product knows a capsule lies under the test's own
    directory and does not exist. So the product finds no launcher's settings to read, in a capsule as on a
    plain host."""
    from devcapsule import runtime_configuration

    for name in conftest.CAPSULE_PATHS:
        path = getattr(runtime_configuration, name)
        assert path.is_relative_to(tmp_path) and not path.exists(), name
    assert runtime_configuration.mounted_settings_path() is None
