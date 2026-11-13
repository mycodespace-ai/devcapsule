"""Generic PID 1 entrypoint for a materialized DevCapsule image.

The entrypoint prepares the capsule from the runtime plan and then stays: it
spawns the one distinguished foreground child — the interactive surface from
the plan, or the headless job given after ``--`` — and supervises it as PID 1
until the session ends. The session's exit code is the child's, honestly.

When the plan selects the contained display, the surface is preceded by the
display's own infrastructure children (X server, window manager, browser
bridge); see ``display.py``. A headless job declares no display at all. When
the plan carries a console section, the web console runs beside either; see
``console.py``.

``session.py`` plans the session from its inputs, with console discovery
delegated to the installation. This module configures logs, prepares and owns
directories, sets session variables, writes launch files, then sets launch
variables. It prepares the display and sets its variables last. It assembles
children, takes the selected profile lock, and runs the supervisor.
"""

from __future__ import annotations

from contextlib import nullcontext
import os
from pathlib import Path
import sys
from typing import Sequence

from .. import logs

from .components import jetbrains
from .console import ConsoleInstallation
from .contract import RuntimePlan, RuntimePlanError
from .display import prepare_contained_display
from .filesystem import prepare_filesystem
from .identity import CapsuleUser
from .session import Session
from .supervisor import SupervisedChild, Supervisor, SupervisorError

__all__ = [
    "SUPERVISOR_LOG_COMPONENT",
    "USAGE",
    "main",
    "run",
]

USAGE = (
    "usage: devcapsule runtime RUNTIME_PLAN.json [-- COMMAND [ARGUMENT...]]\n"
    "       devcapsule runtime diagnose-probe [--plan RUNTIME_PLAN.json] [--probe-timeout SECONDS]"
)


SUPERVISOR_LOG_COMPONENT = "supervisor"


def run(plan: RuntimePlan, job: tuple[str, ...] | None = None) -> int:
    """Prepare the capsule for ``plan`` and supervise its session to the foreground child's exit.

    This is where the runtime meets its host. It reads the process once, its
    effective uid and its environment, and names the image's console; from
    there :class:`Session` decides, and each statement below performs one of
    its answers.
    """

    session = Session(plan, job, CapsuleUser(plan.identity, os.geteuid()), ConsoleInstallation.of_image())
    segment_bytes, rotations = session.log_rotation
    logs.configure(
        SUPERVISOR_LOG_COMPONENT, session.log_directory,
        owner=session.log_owner, segment_bytes=segment_bytes, rotations=rotations,
    )
    prepare_filesystem(session.filesystem, session.user)
    os.environ.update(session.environment(os.environ))
    for path, text in session.launch.files.items():
        Path(path).write_text(text, encoding="utf-8")
    os.environ.update(session.launch.environment)
    display_children: tuple[SupervisedChild, ...] = ()
    if session.shows_contained_display:
        display = prepare_contained_display(
            plan, session.filesystem.environment["XDG_RUNTIME_DIR"], session.user.command,
        )
        os.environ.update(display.environment)
        display_children = display.children
    children = session.children(display_children)
    guard = jetbrains.session_lock(plan) if session.holds_profile_lock else nullcontext()
    with guard:
        return Supervisor(
            children, log_owner=session.log_owner, segment_bytes=segment_bytes, rotations=rotations,
        ).run()


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["diagnose-probe"]:
        from .diagnose import main as diagnose_main

        return diagnose_main(arguments[1:])
    if arguments == ["--help"]:
        print(USAGE)
        return 0
    job: tuple[str, ...] | None = None
    if len(arguments) >= 2 and arguments[1] == "--":
        job = tuple(arguments[2:])
        arguments = arguments[:1]
    if len(arguments) != 1 or job == ():
        print(USAGE, file=sys.stderr)
        return 2
    try:
        return run(RuntimePlan.from_file(arguments[0]), job)
    except RuntimePlanError as error:
        print(f"devcapsule runtime plan error: {error}", file=sys.stderr)
        return 2
    except SupervisorError as error:
        print(f"devcapsule supervisor error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
