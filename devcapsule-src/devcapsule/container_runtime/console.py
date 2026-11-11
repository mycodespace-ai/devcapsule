"""The capsule web console as a supervised child of the entrypoint.

When the runtime plan carries a console section, the entrypoint starts the
console beside the display infrastructure, or alone in a headless capsule,
ahead of the foreground child. The base image supplies the hash-pinned virtual
environment and baseline package under ``/opt/devcapsule-webconsole`` (base
recipe 10+); under ``D-0017``, environment materialization installs the
launcher's own ``devcapsule_webconsole`` package at ``/opt/devcapsule/webconsole``,
which runs on the base interpreter ahead of the base copy. The launcher plans
a console only on a base whose recipe is ``WEBCONSOLE_RECIPE`` or later
(``devcapsule.images.contract``), so the interpreter satisfies the package's
third-party dependencies by construction; a console dependency added later
advances the base recipe and that constant together. See ``R-CONSOLE-001``
and ``D-0017``.
"""

from __future__ import annotations

from pathlib import Path
import socket
import sys
from typing import Callable

from devcapsule.webconsole_bundle import LAUNCHER_WEBCONSOLE_PATH, PACKAGE_NAME

from .contract import RuntimePlan
from .supervisor import SupervisedChild

__all__ = [
    "CONSOLE_CHILD",
    "CONSOLE_PYTHON",
    "CONSOLE_READY_TIMEOUT_SECONDS",
    "CONSOLE_ROOT",
    "CommandWrapper",
    "LAUNCHER_CONSOLE_SOURCE",
    "RUNTIME_CLI",
    "console_child",
    "console_package_path",
]

CONSOLE_CHILD = "console"
CONSOLE_ROOT = "/opt/devcapsule-webconsole"
"""Where the base image installs the console: a hash-pinned venv and the package."""
CONSOLE_PYTHON = f"{CONSOLE_ROOT}/venv/bin/python"
LAUNCHER_CONSOLE_SOURCE = LAUNCHER_WEBCONSOLE_PATH
"""Where materialization installs the launcher's bundled ``devcapsule_webconsole`` package."""
RUNTIME_CLI = "/opt/devcapsule/bin/devcapsule.pex"
"""The launcher-supplied runtime executable the console calls for its documents."""
# FastAPI's import and uvicorn's bind take a few seconds on a cold, loaded
# host; the display's default margin is tuned for an X server.
CONSOLE_READY_TIMEOUT_SECONDS = 60.0

CommandWrapper = Callable[[tuple[str, ...]], tuple[str, ...]]


def console_child(plan: RuntimePlan, run_as_identity: CommandWrapper) -> SupervisedChild | None:
    """The console child for ``plan``, or ``None`` when there is none to start.

    ``None`` when the plan carries no console section, and, announced, when
    the base predates the console (recipe 9 and earlier): the runtime is
    launcher-supplied and runs on any base carrying the display label, so an
    absent console is a known degradation rather than a failed start. The
    package the child imports is :func:`console_package_path`'s choice.
    """

    console = plan.console
    if console is None:
        return None
    if not Path(CONSOLE_PYTHON).is_file():
        print(
            f"devcapsule console: this base has no web console (base recipe 10 adds it at {CONSOLE_ROOT}); "
            "the capsule runs without one",
            file=sys.stderr,
            flush=True,
        )
        return None
    command: tuple[str, ...] = (
        CONSOLE_PYTHON, "-m", PACKAGE_NAME,
        "--project", plan.project_path,
        "--cli", RUNTIME_CLI,
        "--token-file", console.token_path,
        "--listen", console.listen_address,
        "--port", str(console.port),
    )
    package_path = console_package_path(console.source_path, Path(LAUNCHER_CONSOLE_SOURCE))
    if package_path:
        # ``env`` replaces any ambient PYTHONPATH: the same interpreter and
        # dependencies, the selected package ahead of the base's installed copy.
        command = ("env", f"PYTHONPATH={package_path}", *command)
    if console.source_path:
        print(
            f"devcapsule console: running the mounted checkout's source at {console.source_path}",
            file=sys.stderr,
            flush=True,
        )
    probe_address = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(console.listen_address, console.listen_address)
    return SupervisedChild(
        name=CONSOLE_CHILD,
        command=run_as_identity(command),
        ready=lambda: _accepts_connections(probe_address, console.port),
        ready_timeout_seconds=CONSOLE_READY_TIMEOUT_SECONDS,
    )


def console_package_path(source_path: str, launcher_source: Path) -> str:
    """The directory to put first on ``PYTHONPATH``, or empty for the base's copy.

    Precedence under ``D-0017``: the runtime plan's ``console.source_path``
    when it names a mounted checkout, else ``launcher_source`` when
    materialization installed the launcher's package there, else empty, and
    the base image's installed copy answers the import.
    """

    if source_path:
        return source_path
    if (launcher_source / PACKAGE_NAME / "__init__.py").is_file():
        return str(launcher_source)
    return ""


def _accepts_connections(address: str, port: int) -> bool:
    try:
        with socket.create_connection((address, port), timeout=0.2):
            return True
    except OSError:
        return False
