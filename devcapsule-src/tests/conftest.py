from __future__ import annotations

from collections.abc import Iterable, Iterator
import ipaddress
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from typing import Any, Protocol

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROUTE_INPUTS = REPOSITORY_ROOT / ".github" / "ci-python-inputs.yml"
"""The list the hosted workflow routes the Python job by, and the list the suite is held to."""


def pytest_configure(config: pytest.Config) -> None:
    """Start the two guards, and give a macOS run a short temporary root.

    The repository-input guard fails a test that opens or lists a repository
    path the hosted Python job is not routed by; see ``RepositoryInputGuard``.
    The network guard fails a unit test that reaches another host or asks a
    name server; see ``NetworkGuard``.

    macOS limits a Unix socket path to 104 bytes, and its per-user temporary
    directory under /var/folders leaves too little of that for the sockets
    the tests bind beneath tmp_path. An explicit --basetemp still wins.
    """

    # A copy of this file run outside the repository, as tests/test_isolation.py runs one, guards nothing.
    if PYTHON_ROUTE_INPUTS.parent.is_dir():
        guard = RepositoryInputGuard(REPOSITORY_ROOT, load_python_route_inputs(PYTHON_ROUTE_INPUTS))
        config.stash[_INPUT_GUARD] = install_repository_input_guard(guard)
    config.stash[_NETWORK_GUARD] = install_network_guard(NetworkGuard())
    if sys.platform == "darwin" and not config.option.basetemp:
        config.option.basetemp = tempfile.mkdtemp(prefix="dcpt-", dir="/tmp")
        config.stash[_SHORT_BASETEMP] = Path(config.option.basetemp)


_SHORT_BASETEMP = pytest.StashKey[Path]()
_INPUT_GUARD = pytest.StashKey["RepositoryInputGuard"]()
_NETWORK_GUARD = pytest.StashKey["NetworkGuard"]()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Iterator[None]:
    """Tell each guard which test runs: whether its outcome counts, and whether it is a unit test."""

    guard = item.config.stash.get(_INPUT_GUARD, None)
    network = item.config.stash.get(_NETWORK_GUARD, None)
    if guard is not None:
        guard.attend(item.nodeid, counted=outcome_counts(item, HEAVIER_SUITE_MARKERS))
    # A test of a heavier suite may use the network: an integration test builds an executable, an end-to-end test pulls an image.
    if network is not None and not any(item.get_closest_marker(marker) for marker in HEAVIER_SUITE_MARKERS):
        network.attend(item.nodeid)
    yield
    if guard is not None:
        guard.leave()
    if network is not None:
        network.leave()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail a session with breaches of either guard, and remove the short temporary root of a passed one.

    A breach fails its test where it happens. This is the second hold: a
    breach recorded although no test failed, because something caught the
    failure or it happened in another thread, still ends the session with a
    failing status.

    pytest prunes its own default roots, but not one it was given, so a root
    per session would otherwise outlive every run and fill the disk; a failed
    session keeps its root, and its path, for inspection.
    """

    guard = session.config.stash.get(_INPUT_GUARD, None)
    breaches = guard.breaches if guard is not None else []
    if breaches:
        print("\nRepository paths read outside the hosted Python job's inputs, .github/ci-python-inputs.yml:")
        for reader, path in sorted(set(breaches)):
            print(f"  {path}  read by {reader}")
        if exitstatus == pytest.ExitCode.OK:
            session.exitstatus = exitstatus = pytest.ExitCode.TESTS_FAILED
    network = session.config.stash.get(_NETWORK_GUARD, None)
    attempts = network.breaches if network is not None else []
    if attempts:
        print("\nUnit tests that tried to use the network (Unit Tests, rule 9, in WORKFLOW-LOCAL.md):")
        for test, attempt in sorted(set(attempts)):
            print(f"  {attempt}  by {test}")
        if exitstatus == pytest.ExitCode.OK:
            session.exitstatus = exitstatus = pytest.ExitCode.TESTS_FAILED
    created = session.config.stash.get(_SHORT_BASETEMP, None)
    if created is not None and exitstatus == 0:
        shutil.rmtree(created, ignore_errors=True)
    elif created is not None:
        print(f"\nTemporary files of this failed session: {created}")


@pytest.fixture(autouse=True)
def host_launch_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make launcher tests behave as if they run on the host.

    The launcher translates bind sources when it detects that it is running
    inside a container against an external Docker daemon. That is correct in
    production but would otherwise make the suite depend on where it runs:
    identical tests would take different paths on a laptop and inside a
    DevCapsule dogfood container. Tests that exercise translation opt in by
    overriding this in the test body.
    """

    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.requires_translation",
        lambda _env: False,
    )


@pytest.fixture(autouse=True)
def amd64_linux_host_by_default(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make host-dependent tests run on an amd64 Linux host with an amd64 Docker daemon.

    The launcher takes macOS paths for the host-browser bridge, host
    networking, the Docker socket's group and the sudo policy, and an Apple
    Silicon host runs linux-arm64 capsules natively. Tests of the CI's host
    would otherwise depend on where they run; tests of another host patch it
    themselves and carry ``own_host_patches``. Docker-marked tests keep the
    real host.
    """

    if any(request.node.get_closest_marker(marker) for marker in (*DOCKER_MARKERS, "own_host_patches")):
        return
    from devcapsule.platforms import HostOs

    monkeypatch.setattr(HostOs, "current", classmethod(lambda cls: HostOs.LINUX))
    monkeypatch.setattr("devcapsule.platforms.host_architecture", lambda: "amd64")
    for module in ("environment_realization", "images.build", "launch.pycharm._launcher"):
        monkeypatch.setattr(f"devcapsule.{module}.daemon_architecture", lambda: "amd64")


DOCKER_MARKERS = ("e2e", "base_build_e2e", "recursive_e2e", "contributor_e2e", "ide_smoke", "docker")
"""The markers of tests that need the Docker daemon: the end-to-end suites and the integration tests marked
``docker``. They keep the real host and the inherited directories, so builds reuse the real artifact cache."""

HEAVIER_SUITE_MARKERS = ("integration", *DOCKER_MARKERS)
"""The markers of the suites the hosted Python job does not run. Their tests exercise the real repository
and the real tools, so the repository-input guard leaves them alone."""


def inherited_cache_home() -> Path:
    """The cache home the process was started with: ``XDG_CACHE_HOME``, else ``~/.cache``."""
    return Path(os.environ.get("XDG_CACHE_HOME") or Path(os.environ.get("HOME", "~")).expanduser() / ".cache")


@pytest.fixture(autouse=True)
def private_user_directories(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give non-Docker tests private user-directory paths under their tmp_path.

    Override HOME and each XDG directory: changing HOME alone leaves exported
    XDG paths active. This keeps artifact retention and restoration, config,
    state, and launcher runtime files away from the developer's directories.
    Docker-marked tests keep their inherited directories so builds reuse the
    real artifact cache. A test or function-scoped fixture can set its own
    paths after this autouse fixture runs. Leave directory creation to the
    tested code so refusal tests can still assert that nothing was written.
    """

    if any(request.node.get_closest_marker(marker) for marker in DOCKER_MARKERS):
        return
    monkeypatch.delenv("DEVCAPSULE_CONFIG_HOME", raising=False)
    monkeypatch.delenv("DEVCAPSULE_DEV_WEBCONSOLE", raising=False)
    # The build tools' caches are content-addressed and shared by the
    # developer's own builds: pex's under PEX_ROOT, and the scie launcher's
    # unpacked Python under SCIE_BASE. Moving them under the scratch made every
    # clean revision build download the launcher and its Python again and
    # unpack it per case, 250 MB a time. Pin both before the homes move.
    cache = inherited_cache_home()
    monkeypatch.setenv("PEX_ROOT", os.environ.get("PEX_ROOT") or str(cache / "pex"))
    monkeypatch.setenv("SCIE_BASE", os.environ.get("SCIE_BASE") or str(cache / "nce"))
    for variable, leaf in (
        ("HOME", "home"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_RUNTIME_DIR", "runtime"),
    ):
        monkeypatch.setenv(variable, str(tmp_path / "user" / leaf))


@pytest.fixture
def built_pex() -> Path:
    selected = os.environ.get("DEVCAPSULE_PEX_UNDER_TEST")
    path = (
        Path(selected).expanduser().resolve()
        if selected
        else Path(__file__).resolve().parents[1] / "dist" / "devcapsule-local.pex"
    )
    assert path.is_file(), (
        f"Built PEX does not exist: {path}; run the corresponding Nox session"
    )
    return path


# The repository-input guard.
#
# .github/ci-python-inputs.yml lists the repository paths whose change runs
# the hosted Python job; a pull request that changes none of them skips it.
# That is sound only while no test whose outcome counts reads a repository
# path outside the list. The guard fails the test that does, in the pull
# request that introduces the read: such a change is a change to a test or to
# the package, and those always run the suite.
#
# What the guard cannot see: a file read by a program a test starts, and a
# path whose existence alone is tested. Every push to main runs the whole
# suite whatever changed, which is the backstop for both.

OUTSIDE_ANY_TEST = "<collection or session setup>"
"""The reader named while no test runs: modules are being imported, or the session starts or ends."""

_WATCHED_EVENTS = frozenset({"open", "os.listdir", "os.scandir"})
_GLOB_CHARACTERS = frozenset("*?[]{}()!")
_TREE_SUFFIX = "/**"


def load_python_route_inputs(path: Path) -> tuple[str, ...]:
    """The Python route's inputs as the filter file lists them.

    An entry is a repository-relative file path, or ``DIRECTORY/**`` for a
    directory and everything beneath it. Any other pattern is refused: the
    hosted filter and the guard must agree on what an entry matches, and
    these two forms are the ones both read the same way.
    """
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = document.get("python") if isinstance(document, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path}: expected a non-empty list under 'python'")
    for entry in entries:
        literal = entry[: -len(_TREE_SUFFIX)] if isinstance(entry, str) and entry.endswith(_TREE_SUFFIX) else entry
        if not isinstance(literal, str) or not literal or literal.startswith("/") or _GLOB_CHARACTERS & set(literal):
            raise ValueError(f"{path}: {entry!r} is neither a file path nor DIRECTORY/**")
    return tuple(entries)


class _Marked(Protocol):
    def get_closest_marker(self, name: str) -> Any: ...


def outcome_counts(item: _Marked, heavier_suite_markers: Iterable[str]) -> bool:
    """Whether a test's outcome decides the hosted Python job.

    It does not for a test of a heavier suite, which that job does not run,
    nor for a test marked expected to fail without a condition and without
    ``strict``: the job passes whatever such a test does. A mark with a
    condition holds on some machines only, so its test counts. Removing a
    mark makes the outcome count, in a change that runs the suite.
    """
    if any(item.get_closest_marker(marker) for marker in heavier_suite_markers):
        return False
    expected_failure = item.get_closest_marker("xfail")
    if expected_failure is None:
        return True
    return bool(expected_failure.args) or bool(expected_failure.kwargs.get("strict", False))


class RepositoryInputGuard:
    """The rule for one repository: a counted reader opens and lists only the Python route's inputs."""

    def __init__(self, root: Path, inputs: tuple[str, ...]) -> None:
        self._root = os.path.abspath(root)
        self._trees = tuple(entry[: -len(_TREE_SUFFIX)] for entry in inputs if entry.endswith(_TREE_SUFFIX))
        self._files = frozenset(entry for entry in inputs if not entry.endswith(_TREE_SUFFIX))
        self._reader = OUTSIDE_ANY_TEST
        self._counted = True
        self.breaches: list[tuple[str, str]] = []
        """Every unlisted access by a counted reader, as ``(reader, repository-relative path)``."""

    def attend(self, reader: str, *, counted: bool) -> None:
        """Name who reads from now on, a test's node id, and whether its outcome counts."""
        self._reader, self._counted = reader, counted

    def leave(self) -> None:
        """No test reads from now on; what is read outside any test counts."""
        self._reader, self._counted = OUTSIDE_ANY_TEST, True

    def unlisted(self, path: object) -> str | None:
        """The repository-relative form of ``path`` when it lies in the repository outside the inputs.

        ``None`` for a path outside the repository, inside an input, inside
        ``.git``, or not a path at all, such as a file descriptor. A relative
        path is taken from the current directory, as the read itself takes
        it; ``None`` as a path is the current directory, as a listing takes it.
        """
        if path is None:
            path = "."
        if not isinstance(path, (str, bytes, os.PathLike)):
            return None
        try:
            absolute = os.path.abspath(os.fsdecode(path))
        except OSError:  # The current directory is gone; the read fails on its own.
            return None
        if absolute == self._root:
            return "."
        if not absolute.startswith(self._root + os.sep):
            return None
        relative = absolute[len(self._root) + 1:].replace(os.sep, "/")
        if relative in self._files or relative == ".git" or relative.startswith(".git/"):
            return None
        if any(relative == tree or relative.startswith(tree + "/") for tree in self._trees):
            return None
        return relative

    def breach(self, path: object) -> str | None:
        """Record the current reader's access to ``path``; the failure message, or ``None`` when it is allowed."""
        relative = self.unlisted(path)
        if relative is None or not self._counted:
            return None
        self.breaches.append((self._reader, relative))
        return (
            f"{self._reader} opens or lists {relative}, which is not an input of the hosted Python job: "
            "a change to that path would not run this test. Build the input in the test "
            "(Unit Tests, rule 2, in WORKFLOW-LOCAL.md), or list the path in "
            ".github/ci-python-inputs.yml with its reader named."
        )

    def audit(self, event: str, arguments: tuple[Any, ...]) -> None:
        """The interpreter's audit hook: fail the access to a path that is a breach.

        Opening a file and listing a directory are the watched events; every
        other event passes. The failure is ``pytest.fail``'s, an exception no
        ``except Exception`` in the code under test can swallow.
        """
        if event not in _WATCHED_EVENTS or not arguments:
            return
        message = self.breach(arguments[0])
        if message is not None:
            pytest.fail(message)


_installed_guard: RepositoryInputGuard | None = None


def install_repository_input_guard(guard: RepositoryInputGuard) -> RepositoryInputGuard:
    """Watch this process's file access with ``guard`` and return the guard in force.

    An audit hook cannot be removed, so the first guard installed stays in
    force for the life of the process and later calls return it unchanged.
    """
    global _installed_guard
    if _installed_guard is None:
        _installed_guard = guard
        sys.addaudithook(guard.audit)
    return _installed_guard


# The network guard.
#
# A unit test's outcome is a function of the inputs it constructs, and nothing
# on the network is one of them (Unit Tests, rules 2 and 9, in
# WORKFLOW-LOCAL.md). The suite had no hold on that: on 2026-11-12 one test,
# its consent already given in the developer's settings, went on to download
# 1.5 GB of vendor software in every run inside a capsule.
#
# The guard refuses two things while a unit test runs: sending to an address
# that is not this machine's own, and asking for a name or an address to be
# resolved. Loopback stays open, since a test may serve itself on 127.0.0.1.
#
# What the guard cannot see: the network use of a program a test starts,
# unless that program is this Python with this guard.

_REACH_EVENTS = frozenset({"socket.connect", "socket.sendto", "socket.sendmsg"})
"""Audit events of a socket about to reach a peer. Their arguments are ``(socket, address)``."""

_LOOKUP_EVENTS = frozenset({"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"})
"""Audit events of a question to the resolver. Their first argument is the host asked about."""

_INTERNET_FAMILIES = frozenset({socket.AF_INET, socket.AF_INET6})
"""The socket families that can leave the machine. A Unix socket is a path on this machine and passes."""


def is_this_machine(host: object) -> bool:
    """Whether ``host``, as a socket call was given it, can only mean the machine the test runs on.

    True for no host at all, which a listener passes to mean every local
    address; for ``localhost``; and for a loopback or unspecified address such
    as ``127.0.0.1``, ``::1`` or ``0.0.0.0``. False for every other address
    and for every other name, the machine's own host name included: resolving
    a name is a question to a name server.
    """
    if host is None:
        return True
    name = os.fsdecode(host) if isinstance(host, (str, bytes)) else str(host)
    if name in ("", "localhost"):
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:  # Not an address, so a name.
        return False
    return address.is_loopback or address.is_unspecified


class NetworkGuard:
    """The rule for the unit suite: a unit test reaches no machine but its own and asks no name server."""

    def __init__(self) -> None:
        self._test: str | None = None
        self.breaches: list[tuple[str, str]] = []
        """Every refused attempt, as ``(test, what it tried)``."""

    def attend(self, test: str) -> None:
        """Hold the test with this node id to the rule from now on."""
        self._test = test

    def leave(self) -> None:
        """Hold nothing from now on: between tests, and during the tests of heavier suites, the guard stands down."""
        self._test = None

    def attempt(self, event: str, arguments: tuple[Any, ...]) -> str | None:
        """What an audit event tries on the network, in words, or ``None`` when it stays on this machine."""
        if event in _LOOKUP_EVENTS and arguments and not is_this_machine(arguments[0]):
            return f"look up {arguments[0]!r}"
        if event not in _REACH_EVENTS or len(arguments) < 2:
            return None
        peer, address = arguments[0], arguments[1]
        # An internet address is ``(host, port, ...)``. ``sendmsg`` on a connected socket passes no address at all.
        if getattr(peer, "family", None) not in _INTERNET_FAMILIES or not isinstance(address, tuple) or not address:
            return None
        return None if is_this_machine(address[0]) else f"reach {address[0]!r}"

    def audit(self, event: str, arguments: tuple[Any, ...]) -> None:
        """The interpreter's audit hook: fail a unit test's attempt to use the network, before it happens.

        The failure is ``pytest.fail``'s, an exception no ``except Exception``
        in the code under test can swallow, so nothing is sent.
        """
        if self._test is None:
            return
        attempt = self.attempt(event, arguments)
        if attempt is None:
            return
        self.breaches.append((self._test, attempt))
        pytest.fail(
            f"{self._test} tries to {attempt}. A unit test uses no network (Unit Tests, rule 9, in "
            "WORKFLOW-LOCAL.md): pass the unit what it would have fetched, or make this an integration test."
        )


_installed_network_guard: NetworkGuard | None = None


def install_network_guard(guard: NetworkGuard) -> NetworkGuard:
    """Watch this process's sockets with ``guard`` and return the guard in force.

    As for the repository-input guard, the first one installed stays for the
    life of the process, because an audit hook cannot be removed.
    """
    global _installed_network_guard
    if _installed_network_guard is None:
        _installed_network_guard = guard
        sys.addaudithook(guard.audit)
    return _installed_network_guard
