"""The web console's command-line tools, run from the runtime CLI inside a capsule.

The console is a separate process and package from the runtime, installed in
the base image under ``/opt/devcapsule-webconsole`` and, under the
self-hosting exception, mounted from the checkout as the runtime plan's
``console.source_path``. Its ``decisions`` module builds, checks and hands
off decision documents. This module locates that interpreter and that
source, so ``project checkout decisions`` runs the same module an agent
would otherwise have to find by path.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from devcapsule.compat import CliError
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.container_runtime import console as console_child
from devcapsule.container_runtime.contract import RuntimePlan, RuntimePlanError
from devcapsule import recursive_dogfood

__all__ = [
    "DECISIONS_MODULE",
    "console_decisions_command",
    "run_console_decisions",
]

DECISIONS_MODULE = "devcapsule_webconsole.decisions"


def console_decisions_command(arguments: Sequence[str], *, environ: Mapping[str, str] | None = None,
                              console_python: Path | None = None,
                              runtime_plan_path: Path | None = None) -> tuple[str, ...]:
    """The command that runs the console's ``decisions`` module with ``arguments``.

    Refuses outside a capsule, and inside one whose base predates the console,
    naming what to run instead. The mounted source, when the runtime plan
    names one, goes first on ``PYTHONPATH``, as the console child does.
    """
    values = os.environ if environ is None else environ
    python = console_python or Path(console_child.CONSOLE_PYTHON)
    plan_path = runtime_plan_path or recursive_dogfood.RUNTIME_PLAN_PATH
    if not values.get(recursive_dogfood.CONTAINER_NAME_ENV):
        raise ProjectConfigurationError(
            "project checkout decisions runs inside a capsule, where the web console is installed; "
            f"on a host, run `python -m {DECISIONS_MODULE}` from the devcapsule-webconsole checkout instead."
        )
    if not python.is_file():
        raise ProjectConfigurationError(
            f"this capsule's base has no web console at {console_child.CONSOLE_ROOT} (base recipe 10 adds it); "
            "relaunch on a newer base to hand decisions to the console."
        )
    source_path = ""
    try:
        plan = RuntimePlan.from_file(plan_path)
        source_path = plan.console.source_path if plan.console else ""
    except (RuntimePlanError, UnicodeError):
        pass  # Without a readable plan, use the installed console.
    command: tuple[str, ...] = (str(python), "-m", DECISIONS_MODULE, *arguments)
    if source_path:
        command = ("env", f"PYTHONPATH={source_path}", *command)
    return command


def run_console_decisions(
    arguments: Sequence[str],
    *,
    environ: Mapping[str, str] | None = None,
    console_python: Path | None = None,
    runtime_plan_path: Path | None = None,
) -> int:
    """Execute ``devcapsule_webconsole.decisions`` in the capsule's console interpreter."""
    command = console_decisions_command(
        arguments,
        environ=environ,
        console_python=console_python,
        runtime_plan_path=runtime_plan_path,
    )
    try:
        return subprocess.run(command, check=False).returncode
    except OSError as error:
        raise CliError(f"cannot run the console's decision tools: {error}") from error
