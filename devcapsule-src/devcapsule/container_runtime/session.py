"""One capsule session's decisions, made from values before anything starts.

The entrypoint reads the process once, builds a :class:`Session`, and performs
what it answers: the directories and variables the session needs, the files
its surface reads, and the children to supervise in their start order.

Nothing here reads the process environment or the caller's uid, starts a
program or writes a file. ``children`` delegates console discovery to the
given installation. That operation checks its paths and can print a notice.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import Mapping

from .. import logs

from .components import eclipse, jetbrains, vscode
from .console import ConsoleInstallation
from .contract import RuntimePlan, RuntimePlanError
from .filesystem import FilesystemPlan, plan_filesystem
from .graphics import environment as graphics_environment
from .identity import CapsuleUser
from .supervisor import SupervisedChild

__all__ = ["JOB_CHILD", "Session", "SurfaceLaunch"]

JOB_CHILD = "job"
"""The name of the foreground child of a headless session."""


@dataclass(frozen=True)
class SurfaceLaunch:
    """How the plan's interactive surface starts, and what must be in place first."""

    command: tuple[str, ...]
    files: Mapping[str, str] = field(default_factory=dict)
    """Text to write, by path, before the surface starts."""
    environment: Mapping[str, str] = field(default_factory=dict)
    """The variables by which the surface finds those files."""


@dataclass(frozen=True)
class Session:
    """The session of ``plan``: interactive, or the headless ``job`` when one is given.

    ``user`` says who prepares the session and for whom; ``console`` says
    where the image keeps the web console.
    """

    plan: RuntimePlan
    job: tuple[str, ...] | None
    user: CapsuleUser
    console: ConsoleInstallation

    @cached_property
    def filesystem(self) -> FilesystemPlan:
        return plan_filesystem(self.plan)

    @cached_property
    def launch(self) -> SurfaceLaunch:
        """The surface's launch, as the adapter of the plan's component plans it.

        A headless session prepares the same files and variables and leaves
        only the command unused.
        """

        adapter = self.plan.component.adapter
        if adapter == "jetbrains":
            planned = jetbrains.plan(self.plan)
            return SurfaceLaunch(
                planned.command,
                files={planned.properties_path: planned.properties},
                environment={planned.properties_environment_variable: planned.properties_path},
            )
        if adapter == "vscode":
            return SurfaceLaunch(vscode.plan(self.plan).command)
        if adapter == "eclipse":
            return SurfaceLaunch(eclipse.plan(self.plan).command)
        raise RuntimePlanError(f"unsupported component adapter: {adapter}")

    def environment(self, existing: Mapping[str, str]) -> dict[str, str]:
        """The variables to set before preparing the surface, given ``existing``.

        The session's paths precede the components' variables. Graphics
        defaults fill only unset names. The entrypoint sets ``launch.environment``
        separately, after writing the surface's files, as in 0.3.0.
        """

        planned = {
            **self.filesystem.environment,
            **self.plan.component_environment(),
        }
        return {**planned, **graphics_environment({**existing, **planned})}

    @property
    def shows_contained_display(self) -> bool:
        """Whether the contained display is prepared: the plan selects it and no job replaces the surface."""

        return self.job is None and self.plan.display is not None and self.plan.display.is_contained

    @property
    def holds_profile_lock(self) -> bool:
        """Whether the session owns a JetBrains profile for as long as its surface runs."""

        return self.job is None and self.plan.component.adapter == "jetbrains"

    @property
    def log_directory(self) -> str | None:
        return None if self.plan.logs is None else self.plan.logs.directory

    @property
    def log_owner(self) -> tuple[int, int]:
        return (self.plan.identity.uid, self.plan.identity.gid)

    @property
    def log_rotation(self) -> tuple[int, int]:
        """The segment size and rotation count every writer of this session uses.

        The plan's logs section carries them when the launcher derived them from
        the budget; a plan from before they existed gets the defaults.
        """

        if self.plan.logs is not None and self.plan.logs.rotates:
            return self.plan.logs.segment_bytes, self.plan.logs.rotations
        return logs.MAXIMUM_SEGMENT_BYTES, logs.ROTATIONS

    def children(self, display_children: tuple[SupervisedChild, ...]) -> tuple[SupervisedChild, ...]:
        """Every child to supervise, in start order.

        ``display_children`` first, as the prepared display gave them; then
        the console, when the plan has one and the image can run it; then the
        one foreground child, the surface or the job. Each runs as the capsule
        user, and each gets its own log file, ``devcapsule-<name>.log``, when
        the plan says where the logs go.
        """

        console = self.console.child(self.plan, self.user.command)
        infrastructure = display_children if console is None else (*display_children, console)
        if self.job is None:
            foreground = SupervisedChild(
                name=self.plan.component.id,
                command=self.user.command(self.launch.command),
                foreground=True,
            )
        else:
            # Headless mode: the same distinguished slot with no GUI. The job runs
            # in the project it was launched against, not the image's workdir.
            foreground = SupervisedChild(
                name=JOB_CHILD,
                command=self.user.command(self.job),
                foreground=True,
                working_directory=self.plan.project_path,
            )
        children = (*infrastructure, foreground)
        directory = self.log_directory
        if directory is None:
            return children
        return tuple(replace(child, log_path=str(logs.log_path(directory, child.name))) for child in children)
