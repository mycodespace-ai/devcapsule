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
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
import os
from pathlib import Path
import sys
from typing import Callable, MutableMapping, Protocol, Sequence

from . import contract as rtcontract
from .. import logs

from .components import eclipse, jetbrains, vscode
from .console import CommandWrapper, console_child
from .contract import RuntimePlan, RuntimePlanError
from .display import ContainedDisplay, prepare_contained_display
from .filesystem import plan_filesystem, prepare_filesystem
from .graphics import environment as graphics_environment
from .identity import foreground_command
from .supervisor import SupervisedChild, Supervisor, SupervisorError

__all__ = [
    "SUPERVISOR_LOG_COMPONENT",
    "USAGE",
    "log_rotation",
    "logged_children",
    "main",
    "run",
]

USAGE = (
    "usage: devcapsule runtime RUNTIME_PLAN.json [-- COMMAND [ARGUMENT...]]\n"
    "       devcapsule runtime diagnose-probe [--plan RUNTIME_PLAN.json] [--probe-timeout SECONDS]"
)


SUPERVISOR_LOG_COMPONENT = "supervisor"


class SupervisorRunner(Protocol):
    def run(self) -> int: ...


SupervisorFactory = Callable[..., SupervisorRunner]
DisplayPreparer = Callable[[RuntimePlan, str, CommandWrapper], ContainedDisplay]
ConsoleBuilder = Callable[[RuntimePlan, CommandWrapper], SupervisedChild | None]


def run(
    plan: rtcontract.RuntimePlan,
    job: tuple[str, ...] | None = None,
    *,
    environ: MutableMapping[str, str] | None = None,
    prepare_display: DisplayPreparer | None = None,
    build_console_child: ConsoleBuilder | None = None,
    supervisor_factory: SupervisorFactory | None = None,
) -> int:
    target_env: MutableMapping[str, str] = os.environ if environ is None else environ
    make_display = prepare_contained_display if prepare_display is None else prepare_display
    make_console = console_child if build_console_child is None else build_console_child
    make_supervisor: SupervisorFactory = Supervisor if supervisor_factory is None else supervisor_factory

    owner = (plan.identity.uid, plan.identity.gid)
    log_directory = None if plan.logs is None else plan.logs.directory
    segment_bytes, rotations = log_rotation(plan)
    logs.configure(SUPERVISOR_LOG_COMPONENT, log_directory, owner=owner, segment_bytes=segment_bytes, rotations=rotations)
    filesystem = plan_filesystem(plan)
    prepare_filesystem(filesystem, plan.identity)
    target_env.update(filesystem.environment)
    target_env.update(plan.component_environment())
    target_env.update(graphics_environment(target_env))
    if plan.component.adapter == "jetbrains":
        launch = jetbrains.plan(plan)
        Path(launch.properties_path).write_text(launch.properties, encoding="utf-8")
        target_env[launch.properties_environment_variable] = launch.properties_path
        command = launch.command
    elif plan.component.adapter == "vscode":
        command = vscode.plan(plan).command
    elif plan.component.adapter == "eclipse":
        command = eclipse.plan(plan).command
    else:
        raise RuntimePlanError(f"unsupported component adapter: {plan.component.adapter}")

    def as_capsule_user(child_command: tuple[str, ...]) -> tuple[str, ...]:
        return foreground_command(child_command, plan.identity)

    infrastructure: tuple[SupervisedChild, ...] = ()
    if job is None and plan.display is not None and plan.display.is_contained:
        contained = make_display(plan, filesystem.environment["XDG_RUNTIME_DIR"], as_capsule_user)
        target_env.update(contained.environment)
        infrastructure = contained.children
    console = make_console(plan, as_capsule_user)
    if console is not None:
        infrastructure = (*infrastructure, console)
    if job is None:
        child = SupervisedChild(
            name=plan.component.id,
            command=foreground_command(command, plan.identity),
            foreground=True,
        )
    else:
        # Headless mode: the same distinguished slot with no GUI. The job runs
        # in the project it was launched against, not the image's workdir.
        child = SupervisedChild(
            name="job",
            command=foreground_command(job, plan.identity),
            foreground=True,
            working_directory=plan.project_path,
        )
    guard = jetbrains.session_lock(plan) if plan.component.adapter == "jetbrains" and job is None else nullcontext()
    with guard:
        return make_supervisor(
            logged_children((*infrastructure, child), log_directory),
            log_owner=owner, segment_bytes=segment_bytes, rotations=rotations,
        ).run()


def log_rotation(plan: rtcontract.RuntimePlan) -> tuple[int, int]:
    """The segment and rotation count every writer of this session uses.

    The plan's logs section carries them when the launcher derived them from
    the budget; a plan from before they existed gets the defaults.
    """

    if plan.logs is not None and plan.logs.rotates:
        return plan.logs.segment_bytes, plan.logs.rotations
    return logs.MAXIMUM_SEGMENT_BYTES, logs.ROTATIONS


def logged_children(
    children: tuple[SupervisedChild, ...], log_directory: str | None
) -> tuple[SupervisedChild, ...]:
    """Give every child its own log file, ``devcapsule-<name>.log``, when logging is on."""

    if log_directory is None:
        return children
    return tuple(replace(child, log_path=str(logs.log_path(log_directory, child.name))) for child in children)


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
