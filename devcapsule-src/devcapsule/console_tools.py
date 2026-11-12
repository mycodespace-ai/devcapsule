"""The web console's command-line tools, run from the runtime CLI inside a capsule.

The console is a separate process and package from the runtime: the base image
supplies the interpreter under ``/opt/devcapsule-webconsole``, materialization
installs the launcher's ``devcapsule_webconsole`` package at
``/opt/devcapsule/webconsole`` (``D-0017``), and source-form or opt-in
launches may mount a checkout as the runtime plan's ``console.source_path``.
Its ``decisions`` module builds, checks and hands off decision documents. This
module locates that interpreter and that source, so ``project checkout
decisions`` runs the same module an agent would otherwise have to find by path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence

from devcapsule.compat import CliError
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.container_runtime.console import CONSOLE_ROOT, ConsoleInstallation
from devcapsule.container_runtime.contract import RuntimePlan, RuntimePlanError

__all__ = [
    "DECISIONS_MODULE",
    "DecisionTools",
]

DECISIONS_MODULE = "devcapsule_webconsole.decisions"


@dataclass(frozen=True)
class DecisionTools:
    """The console's ``decisions`` module as one process can reach it.

    ``in_capsule`` says whether the process runs inside a capsule, ``console``
    where that capsule's image keeps the console, and ``runtime_plan_path``
    where the capsule's runtime plan is. The command that owns the CLI reads
    the three from its process and builds this.
    """

    in_capsule: bool
    console: ConsoleInstallation
    runtime_plan_path: Path

    def command(self, arguments: Sequence[str]) -> tuple[str, ...]:
        """The command that runs the console's ``decisions`` module with ``arguments``.

        Refuses outside a capsule, and inside one whose base predates the console,
        naming what to run instead. The package on ``PYTHONPATH`` is the console
        child's own choice, :meth:`ConsoleInstallation.package_path`: the runtime
        plan's ``console.source_path`` first, else the launcher-delivered package
        when present, else the base copy.
        """
        if not self.in_capsule:
            raise ProjectConfigurationError(
                "project checkout decisions runs inside a capsule, where the web console is installed; "
                f"on a host, run `python -m {DECISIONS_MODULE}` from the devcapsule-webconsole checkout instead."
            )
        if not self.console.python.is_file():
            raise ProjectConfigurationError(
                f"this capsule's base has no web console at {CONSOLE_ROOT} (base recipe 10 adds it); "
                "relaunch on a newer base to hand decisions to the console."
            )
        source_path = ""
        try:
            plan = RuntimePlan.from_file(self.runtime_plan_path)
            source_path = plan.console.source_path if plan.console else ""
        except (RuntimePlanError, UnicodeError):
            pass  # Without a readable plan, the launcher package or the base copy answers.
        command: tuple[str, ...] = (str(self.console.python), "-m", DECISIONS_MODULE, *arguments)
        package_path = self.console.package_path(source_path)
        if package_path:
            command = ("env", f"PYTHONPATH={package_path}", *command)
        return command

    def run(self, arguments: Sequence[str]) -> int:
        """Execute the ``decisions`` module with ``arguments`` and return its exit status."""
        command = self.command(arguments)
        try:
            return subprocess.run(command, check=False).returncode
        except OSError as error:
            raise CliError(f"cannot run the console's decision tools: {error}") from error
