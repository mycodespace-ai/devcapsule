"""Integration tests of the network guard in ``tests/conftest.py``: a real pytest session held to it.

``tests/unit/tests/test_conftest.py`` tests the guard's judgment from values.
These tests prove the wiring: that the interpreter's audit hook is installed,
that the guard attends unit tests and no others, and that a session with a
breach fails. Each runs pytest as a program on a suite it writes, with a copy
of the real ``conftest.py``.

Nothing here uses the network. The inner tests name 192.0.2.1, an address
reserved for documentation, and are stopped before anything is sent. The
lookups of that address are of a literal, which no name server is asked about
even where the guard stands down.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration

CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"


def run_suite(tmp_path: Path, tests: str) -> subprocess.CompletedProcess[str]:
    """Run pytest on one test file with the given source, under a copy of the real conftest.

    The suite lies two directories deep so that the copy finds no repository
    above it and starts the network guard alone. The process gets a search
    path and a home under ``tmp_path``, and nothing else of the caller's
    environment.
    """
    suite = tmp_path / "checkout" / "package" / "tests"
    suite.mkdir(parents=True)
    (suite / "conftest.py").write_text(CONFTEST.read_text(encoding="utf-8"), encoding="utf-8")
    (suite / "pytest.ini").write_text("[pytest]\nmarkers =\n    integration: a heavier suite\n", encoding="utf-8")
    (suite / "test_inner.py").write_text(tests, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-m", "", "-q", str(suite)],
        cwd=suite,
        env={"PATH": os.defpath, "HOME": str(tmp_path / "home"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=120, check=False,
    )


def test_a_session_fails_the_unit_tests_that_use_the_network_and_no_others(tmp_path: Path) -> None:
    """A unit test that connects to another machine fails, and so does one that swallows the failure of a
    lookup; a loopback lookup passes, and a test marked ``integration`` is not held to the rule."""
    completed = run_suite(tmp_path, '''
import socket
import pytest

def test_connects_to_another_machine():
    with socket.socket() as peer:
        peer.settimeout(0.5)
        peer.connect(("192.0.2.1", 9))

def test_swallows_a_refused_lookup():
    try:
        socket.getaddrinfo("192.0.2.1", 9)
    except Exception:
        pass

def test_looks_up_this_machine():
    assert socket.getaddrinfo("127.0.0.1", 9)

@pytest.mark.integration
def test_of_a_heavier_suite_looks_up_another_machine():
    assert socket.getaddrinfo("192.0.2.1", 9)
''')

    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "2 failed, 2 passed" in completed.stdout
    assert "test_connects_to_another_machine tries to reach '192.0.2.1'" in completed.stdout
    assert "test_swallows_a_refused_lookup tries to look up '192.0.2.1'" in completed.stdout


def test_a_session_fails_for_a_network_attempt_that_failed_no_test(tmp_path: Path) -> None:
    """An attempt made in another thread fails no test; the session still ends with a failing status and names the test."""
    completed = run_suite(tmp_path, '''
import socket
import threading

def test_looks_up_in_a_thread():
    worker = threading.Thread(target=socket.getaddrinfo, args=("192.0.2.1", 9))
    worker.start()
    worker.join()
''')

    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "1 passed" in completed.stdout
    assert "Unit tests that tried to use the network" in completed.stdout
    assert "look up '192.0.2.1'  by test_inner.py::test_looks_up_in_a_thread" in completed.stdout
