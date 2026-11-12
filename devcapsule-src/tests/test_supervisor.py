"""Fake-children tests for the supervisor's reap/forward/shutdown machine.

The supervisor blocks and waits on signals in the thread that runs it, which
must not happen inside the pytest process. Every behavioral test therefore
runs the supervisor in its own process via ``tests/resources/supervisor_driver.py``
against fake children (exit/sleep/ignore-TERM shell one-liners) and observes
what PID 1 would report: the exit code and the announced evidence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

import pytest

from devcapsule import logs
from devcapsule.container_runtime.supervisor import (
    INFRASTRUCTURE_FAILURE_EXIT_CODE,
    SupervisedChild,
    Supervisor,
    SupervisorError,
)

# The supervisor is the capsule's entry process: it runs only inside Linux
# capsules and relies on Linux signal primitives (sigwaitinfo).
pytestmark = [
    pytest.mark.legacy,
    pytest.mark.skipif(sys.platform != "linux", reason="container-side code; capsules are Linux"),
]

DRIVER = Path(__file__).parent / "resources" / "supervisor_driver.py"
REPO_ROOT = Path(__file__).resolve().parents[1]


def start_supervisor(
    children: list[dict[str, object]], grace_seconds: float = 5.0, log_directory: str | None = None,
) -> subprocess.Popen[str]:
    spec = json.dumps({"children": children, "grace_seconds": grace_seconds, "log_directory": log_directory})
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(REPO_ROOT), environment.get("PYTHONPATH")])
    )
    return subprocess.Popen(
        [sys.executable, str(DRIVER), spec],
        env=environment,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for_marker(marker: Path, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while not marker.exists():
        assert time.monotonic() < deadline, f"marker never appeared: {marker}"
        time.sleep(0.02)


def test_foreground_exit_code_is_the_session_exit_code() -> None:
    process = start_supervisor([{"name": "job", "command": ["sh", "-c", "exit 7"], "foreground": True}])
    assert process.wait(timeout=10) == 7


def test_foreground_death_by_signal_reports_shell_convention() -> None:
    process = start_supervisor(
        [{"name": "job", "command": ["sh", "-c", "kill -KILL $$"], "foreground": True}]
    )
    assert process.wait(timeout=10) == 137


def test_sigterm_is_the_explicit_end_and_propagates_honestly(tmp_path: Path) -> None:
    marker = tmp_path / "ready"
    process = start_supervisor(
        [
            {
                "name": "ide",
                "command": ["sh", "-c", f"touch {marker}; exec sleep 30"],
                "foreground": True,
            }
        ]
    )
    wait_for_marker(marker)
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=10) == 128 + signal.SIGTERM
    stderr = process.stderr.read() if process.stderr else ""
    assert "session end requested (SIGTERM)" in stderr


def test_term_ignoring_child_is_killed_after_the_grace_period(tmp_path: Path) -> None:
    marker = tmp_path / "ready"
    process = start_supervisor(
        [
            {
                "name": "stubborn",
                "command": [
                    "sh",
                    "-c",
                    f'trap "" TERM; touch {marker}; while true; do sleep 0.1; done',
                ],
                "foreground": True,
            }
        ],
        grace_seconds=0.5,
    )
    wait_for_marker(marker)
    started = time.monotonic()
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=10) == 128 + signal.SIGKILL
    assert time.monotonic() - started >= 0.5
    stderr = process.stderr.read() if process.stderr else ""
    assert "grace period over" in stderr


def test_non_foreground_death_fails_the_session_and_names_the_child() -> None:
    process = start_supervisor(
        [
            {"name": "xvnc", "command": ["sh", "-c", "exit 3"]},
            {"name": "ide", "command": ["sleep", "30"], "foreground": True},
        ]
    )
    assert process.wait(timeout=10) == INFRASTRUCTURE_FAILURE_EXIT_CODE
    stderr = process.stderr.read() if process.stderr else ""
    assert "'xvnc' died unexpectedly (exit code 3)" in stderr


def test_foreground_exit_terminates_remaining_children_promptly() -> None:
    process = start_supervisor(
        [
            {"name": "background", "command": ["sleep", "30"]},
            {"name": "job", "command": ["sh", "-c", "exit 0"], "foreground": True},
        ]
    )
    started = time.monotonic()
    assert process.wait(timeout=10) == 0
    assert time.monotonic() - started < 10


def test_supervisor_rejects_malformed_child_sets() -> None:
    job = SupervisedChild("job", ("true",), foreground=True)
    with pytest.raises(SupervisorError, match="at least one child"):
        Supervisor(())
    with pytest.raises(SupervisorError, match="exactly one"):
        Supervisor((SupervisedChild("a", ("true",)),))
    with pytest.raises(SupervisorError, match="exactly one"):
        Supervisor((job, SupervisedChild("b", ("true",), foreground=True)))
    with pytest.raises(SupervisorError, match="unique non-empty names"):
        Supervisor((job, SupervisedChild("job", ("true",))))
    with pytest.raises(SupervisorError, match="non-empty commands"):
        Supervisor((SupervisedChild("job", (), foreground=True),))
    with pytest.raises(SupervisorError, match="grace period"):
        Supervisor((job,), grace_seconds=0)


def test_next_child_starts_only_after_the_readiness_probe_passes(tmp_path: Path) -> None:
    ready = tmp_path / "x-server-ready"
    # The foreground child asserts the marker the infrastructure child creates
    # after a delay; it can only pass if the supervisor waited.
    process = start_supervisor(
        [
            {
                "name": "x-server",
                "command": ["sh", "-c", f"sleep 0.4; touch {ready}; exec sleep 300"],
                "ready_path": str(ready),
            },
            {"name": "ide", "command": ["sh", "-c", f"test -e {ready}"], "foreground": True},
        ]
    )
    assert process.wait(timeout=15) == 0


def test_child_that_never_becomes_ready_fails_the_start(tmp_path: Path) -> None:
    process = start_supervisor(
        [
            {
                "name": "x-server",
                "command": ["sleep", "300"],
                "ready_path": str(tmp_path / "never"),
                "ready_timeout_seconds": 0.5,
            },
            {"name": "ide", "command": ["true"], "foreground": True},
        ]
    )
    assert process.wait(timeout=15) == 2
    assert process.stderr is not None
    assert "'x-server' did not become ready within 0.5s" in process.stderr.read()


def test_child_that_exits_before_ready_fails_the_start(tmp_path: Path) -> None:
    process = start_supervisor(
        [
            {"name": "x-server", "command": ["sh", "-c", "exit 3"], "ready_path": str(tmp_path / "never")},
            {"name": "ide", "command": ["true"], "foreground": True},
        ]
    )
    assert process.wait(timeout=15) == 2
    assert process.stderr is not None
    assert "'x-server' exited before becoming ready" in process.stderr.read()


def test_supervisor_rejects_non_positive_readiness_timeout() -> None:
    with pytest.raises(SupervisorError, match="readiness timeouts must be positive"):
        Supervisor(
            (SupervisedChild("job", ("true",), foreground=True, ready=lambda: True, ready_timeout_seconds=0),)
        )


def test_logged_child_output_reaches_its_file_not_the_console_and_the_supervisor_keeps_a_record(tmp_path: Path) -> None:
    log = tmp_path / "devcapsule-job.log"
    process = start_supervisor(
        [{"name": "job", "command": ["sh", "-c", "echo hello-out; echo hello-err >&2; exit 3"],
          "foreground": True, "log_path": str(log)}],
        log_directory=str(tmp_path),
    )
    assert process.wait(timeout=10) == 3
    stderr = process.stderr.read() if process.stderr else ""
    # The attached terminal carries the supervisor's own statements only; the
    # child's output is in its file (C10, 2026-10-22).
    assert "hello-out" not in stderr and "hello-err" not in stderr
    text = log.read_text(encoding="utf-8")
    assert re.search(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ hello-out$", text, re.MULTILINE)
    assert "hello-err" in text
    record = (tmp_path / "devcapsule-supervisor.log").read_text(encoding="utf-8")
    for event in ("session start: children job", "child 'job' started: pid", "exited: exit code 3", "session end: exit code 3"):
        assert event in record, event
    assert "INFO devcapsule.supervisor.events" in record


def test_announcements_reach_the_supervisor_log_as_warnings(tmp_path: Path) -> None:
    marker = tmp_path / "ready"
    process = start_supervisor(
        [{"name": "ide", "command": ["sh", "-c", f"touch {marker}; exec sleep 30"], "foreground": True}],
        log_directory=str(tmp_path),
    )
    wait_for_marker(marker)
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=10) == 128 + signal.SIGTERM
    record = (tmp_path / "devcapsule-supervisor.log").read_text(encoding="utf-8")
    assert "WARNING devcapsule.supervisor" in record and "session end requested (SIGTERM)" in record
    assert "signal SIGTERM forwarded to ide" in record
    assert "child 'ide' exited: killed by SIGTERM" in record


def test_logged_children_receive_signals_and_exit_status_is_reaped(tmp_path: Path) -> None:
    ready = tmp_path / "ready"
    output = tmp_path / "devcapsule-ide.log"
    process = start_supervisor([
        {"name": "background", "command": ["sleep", "30"], "log_path": str(tmp_path / "background.log")},
        {"name": "ide", "command": [sys.executable, "-c",
            "import pathlib, signal, sys, time; "
            "signal.signal(signal.SIGTERM, lambda *_: sys.exit(23)); "
            "print('ready', flush=True); "
            f"pathlib.Path({str(ready)!r}).touch(); time.sleep(30)"],
         "foreground": True, "log_path": str(output)},
    ], log_directory=str(tmp_path))
    try:
        wait_for_marker(ready)
        process.send_signal(signal.SIGTERM)
        _, stderr = process.communicate(timeout=10)
        assert process.returncode == 23
        assert "ready" not in stderr and "ready" in output.read_text()
        record = (tmp_path / "devcapsule-supervisor.log").read_text()
        assert "child 'background' exited: killed by SIGTERM" in record
        assert "child 'ide' exited: exit code 23" in record
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_grandchild_holding_output_pipe_does_not_delay_supervisor_exit(tmp_path: Path) -> None:
    grandchild_pid = tmp_path / "grandchild"
    log = tmp_path / "job.log"
    process = start_supervisor([
        {"name": "job", "command": [sys.executable, "-c",
            "import pathlib, subprocess, sys; "
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
            f"pathlib.Path({str(grandchild_pid)!r}).write_text(str(child.pid)); "
            "sys.stdout.write('partial line'); sys.stdout.flush(); sys.exit(7)"],
         "foreground": True, "log_path": str(log)},
    ])
    try:
        # The grandchild outlives this timeout and holds the child's pipe open.
        # Output without LF must still be saved before the supervisor returns.
        _, stderr = process.communicate(timeout=5)
        assert process.returncode == 7
        assert "partial line" not in stderr and "partial line" in log.read_text()
    finally:
        if grandchild_pid.exists():
            try:
                os.kill(int(grandchild_pid.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
