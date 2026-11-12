"""Integration tests of the runtime entrypoint: real sessions, in a process whose environment the test builds.

``run`` is the layer that reads the process and acts on the host. These
tests start it as the program it is, with a plan whose every path lies under
the test's directory and a stand-in program where the IDE or the job would
be, and observe what that program was given and what the session left.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Sequence

import pytest

pytestmark = pytest.mark.integration

STAND_IN_STATUS = 7
SLOTS = ("config", "system", "plugins", "log")


@dataclass(frozen=True)
class FinishedSession:
    """One session that ran to its end: the entrypoint's process, and what the stand-in program saw."""

    completed: subprocess.CompletedProcess[str]
    arguments: list[str]
    environment: dict[str, str]
    directory: str


def stand_in_program(tmp_path: Path) -> Path:
    """Write the program that stands where the IDE is installed, and return its path.

    It records its arguments, environment and working directory in
    ``tmp_path / "report.json"``, prints one line, and exits
    ``STAND_IN_STATUS``. ``-I`` keeps it away from the Python settings of
    the environment it is started in.
    """
    program = tmp_path / "ide" / "bin" / "ide.sh"
    program.parent.mkdir(parents=True)
    program.write_text(
        f"#!{sys.executable} -I\n"
        "import json, os, sys\n"
        f"with open({str(tmp_path / 'report.json')!r}, 'w') as report:\n"
        "    json.dump({'arguments': sys.argv[1:], 'environ': dict(os.environ), 'cwd': os.getcwd()}, report)\n"
        "print('stand-in output')\n"
        f"sys.exit({STAND_IN_STATUS})\n",
        encoding="utf-8",
    )
    program.chmod(0o755)
    return program


def write_plan(tmp_path: Path, logs: dict[str, object]) -> Path:
    """Write a JetBrains runtime plan under ``tmp_path`` whose IDE is the stand-in program, and return its path.

    The capsule user of the plan is the user that runs the test, since only
    root may prepare a session for another user.
    """
    (tmp_path / "project").mkdir()
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({
        "version": 1,
        "project_path": str(tmp_path / "project"),
        "home": str(tmp_path / "home"),
        "identity": {"uid": os.getuid(), "gid": os.getgid(), "user": "developer"},
        "state_slots": [{"name": f"jetbrains/{name}", "path": str(tmp_path / "slots" / name)} for name in SLOTS],
        "component": {
            "id": "jetbrains",
            "adapter": "jetbrains",
            "configuration": {
                "installation_path": str(tmp_path / "ide"),
                "launcher": "bin/ide.sh",
                "properties_path": str(tmp_path / "idea.properties"),
                "properties_environment_variable": "PYCHARM_PROPERTIES",
                "recover_stale_directory_lock": True,
                "state_slot_mapping": {name: name for name in SLOTS},
            },
        },
        "logs": logs,
    }), encoding="utf-8")
    return plan


def run_entrypoint(tmp_path: Path, plan: Path, job: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Start the entrypoint on ``plan``, headless when ``job`` is given, and wait for it.

    The process starts in ``tmp_path`` with a search path and one graphics
    setting, and nothing else of the caller's environment.
    """
    if os.getuid() == 0:
        pytest.skip("root starts each child through gosu, which a test host need not have")
    return subprocess.run(
        [sys.executable, "-m", "devcapsule.container_runtime.entrypoint", str(plan), *(("--", *job) if job else ())],
        cwd=tmp_path,
        env={"PATH": os.defpath, "LIBGL_ALWAYS_SOFTWARE": "0"},
        capture_output=True, text=True, timeout=120, check=False,
    )


def finished(tmp_path: Path, completed: subprocess.CompletedProcess[str]) -> FinishedSession:
    report = tmp_path / "report.json"
    assert report.is_file(), f"the stand-in program did not run: {completed.stderr}"
    seen = json.loads(report.read_text(encoding="utf-8"))
    return FinishedSession(completed, seen["arguments"], seen["environ"], seen["cwd"])


@pytest.fixture
def headless(tmp_path: Path) -> FinishedSession:
    """A finished headless session: the stand-in program ran as the job, with the argument ``as-job``."""
    program = stand_in_program(tmp_path)
    plan = write_plan(tmp_path, {"directory": str(tmp_path / "logs")})
    return finished(tmp_path, run_entrypoint(tmp_path, plan, [str(program), "as-job"]))


@pytest.fixture
def interactive(tmp_path: Path) -> FinishedSession:
    """A finished interactive session: the stand-in program ran as the plan's IDE."""
    stand_in_program(tmp_path)
    plan = write_plan(tmp_path, {"directory": str(tmp_path / "logs")})
    return finished(tmp_path, run_entrypoint(tmp_path, plan, []))


def test_a_headless_sessions_exit_status_is_the_jobs(headless: FinishedSession) -> None:
    """The entrypoint runs the job with the job's own arguments and exits with its status."""
    assert headless.arguments == ["as-job"]
    assert headless.completed.returncode == STAND_IN_STATUS


def test_the_job_runs_in_the_project_with_the_sessions_environment(tmp_path: Path, headless: FinishedSession) -> None:
    """The job starts in the plan's project and finds the session's home, runtime directory and properties variable in its environment."""
    assert headless.directory == str(tmp_path / "project")
    assert headless.environment["HOME"] == str(tmp_path / "home")
    assert headless.environment["XDG_RUNTIME_DIR"] == f"/tmp/devcapsule-runtime-{os.getuid()}"
    assert headless.environment["PYCHARM_PROPERTIES"] == str(tmp_path / "idea.properties")


def test_the_job_gets_the_graphics_defaults_and_keeps_the_setting_the_process_had(headless: FinishedSession) -> None:
    """The job's environment has the default the process lacked and the graphics setting the process started with."""
    assert headless.environment["NO_AT_BRIDGE"] == "1"
    assert headless.environment["LIBGL_ALWAYS_SOFTWARE"] == "0"


def test_the_session_prepares_its_directories_and_the_surfaces_properties_file(
    tmp_path: Path, headless: FinishedSession,
) -> None:
    """After the session, the home with a private ``.ssh``, every state slot and the IDE's properties file exist."""
    assert stat.S_IMODE((tmp_path / "home" / ".ssh").stat().st_mode) == 0o700
    assert all((tmp_path / "slots" / name).is_dir() for name in SLOTS)
    properties = (tmp_path / "idea.properties").read_text(encoding="utf-8")
    assert properties.startswith(f"idea.config.path={tmp_path / 'slots' / 'config'}\n")


def test_the_session_logs_the_supervisor_and_the_job_where_the_plan_says(
    tmp_path: Path, headless: FinishedSession,
) -> None:
    """With a logs directory in the plan, the supervisor's log exists there and the job's log holds the job's output."""
    assert (tmp_path / "logs" / "devcapsule-supervisor.log").is_file()
    assert "stand-in output" in (tmp_path / "logs" / "devcapsule-job.log").read_text(encoding="utf-8")


def test_a_childs_log_rotates_at_the_segment_size_of_the_plan(tmp_path: Path) -> None:
    """With a 4 KiB segment in the plan, a job that prints 20 KiB leaves a first rotated segment beside its live log."""
    plan = write_plan(tmp_path, {"directory": str(tmp_path / "logs"), "segment_bytes": 4096, "rotations": 2})
    lines = "import sys\nfor _ in range(200):\n    print('x' * 100)\n    sys.stdout.flush()\n"

    completed = run_entrypoint(tmp_path, plan, [sys.executable, "-I", "-c", lines])

    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "logs" / "devcapsule-job.log.1.gz").is_file()


def test_an_interactive_session_starts_the_surface_on_the_project(tmp_path: Path, interactive: FinishedSession) -> None:
    """Without a job, the entrypoint starts the plan's IDE with the project as its argument, tells it its properties file, and exits with its status."""
    assert interactive.arguments == [str(tmp_path / "project")]
    assert interactive.environment["PYCHARM_PROPERTIES"] == str(tmp_path / "idea.properties")
    assert interactive.completed.returncode == STAND_IN_STATUS
    assert "stand-in output" in (tmp_path / "logs" / "devcapsule-jetbrains.log").read_text(encoding="utf-8")


def test_an_interactive_jetbrains_session_takes_the_profile_lock(tmp_path: Path, interactive: FinishedSession) -> None:
    """For a JetBrains surface that asks for stale-lock recovery, the session leaves its lock file in the config and the system slot."""
    assert (tmp_path / "slots" / "config" / ".devcapsule-session.lock").is_file()
    assert (tmp_path / "slots" / "system" / ".devcapsule-session.lock").is_file()


def test_a_headless_session_takes_no_profile_lock(tmp_path: Path, headless: FinishedSession) -> None:
    """With a job in place of the IDE, the session leaves no lock file in the profile."""
    assert not (tmp_path / "slots" / "config" / ".devcapsule-session.lock").exists()
