"""The capsule web console as a supervised child of the entrypoint.

When the runtime plan carries a console section, the entrypoint starts the
console beside the display infrastructure, or alone in a headless capsule,
ahead of the foreground child. The base image supplies the hash-pinned virtual
environment and baseline package under ``/opt/devcapsule-webconsole`` (base
recipe 10+); under ``D-0017``, environment materialization installs the
launcher's own ``devcapsule_webconsole`` package at ``/opt/devcapsule/webconsole``,
which runs on the base interpreter ahead of the base copy whenever the base
satisfies its dependencies. See ``R-CONSOLE-001`` and ``D-0017``.
"""

from __future__ import annotations

from pathlib import Path
import socket
import subprocess
import sys
from typing import Callable

from devcapsule.webconsole_bundle import LAUNCHER_WEBCONSOLE_PATH

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


def console_child(
    plan: RuntimePlan,
    run_as_identity: CommandWrapper,
    *,
    console_python: Path | None = None,
    launcher_source: Path | None = None,
) -> SupervisedChild | None:
    """The console child for ``plan``, or ``None`` when there is none to start.

    ``None`` when the plan carries no console section, and, announced, when
    the base predates the console (recipe 9 and earlier): the runtime is
    launcher-supplied and runs on any base carrying the display label, so an
    absent console is a known degradation rather than a failed start.
    """

    console = plan.console
    if console is None:
        return None
    python = console_python if console_python is not None else Path(CONSOLE_PYTHON)
    if not python.is_file():
        print(
            f"devcapsule console: this base has no web console (base recipe 10 adds it at {CONSOLE_ROOT}); "
            "the capsule runs without one",
            file=sys.stderr,
            flush=True,
        )
        return None
    command: tuple[str, ...] = (
        str(python), "-m", "devcapsule_webconsole",
        "--project", plan.project_path,
        "--cli", RUNTIME_CLI,
        "--token-file", console.token_path,
        "--listen", console.listen_address,
        "--port", str(console.port),
    )
    bundled = launcher_source if launcher_source is not None else Path(LAUNCHER_CONSOLE_SOURCE)
    if console.source_path:
        compatible = (
            _monitor_dependency_available()
            if console_python is None
            else _python_has_monitor_dependency(python)
        )
        if compatible:
            # The checkout's own console source, ahead of any installed copy:
            # the same interpreter and dependencies, the mounted package.
            command = ("env", f"PYTHONPATH={console.source_path}", *command)
            print(
                f"devcapsule console: running the mounted checkout's source at {console.source_path}",
                file=sys.stderr,
                flush=True,
            )
        else:
            print(
                "devcapsule console: the base cannot import psutil (base recipe 11 adds it); "
                "running the installed console instead of the mounted source",
                file=sys.stderr,
                flush=True,
            )
    elif (bundled / "devcapsule_webconsole" / "__init__.py").is_file():
        compatible = (
            _monitor_dependency_available()
            if console_python is None
            else _python_has_monitor_dependency(python)
        )
        if compatible:
            command = ("env", f"PYTHONPATH={bundled}", *command)
        else:
            print(
                "devcapsule console: the base cannot import psutil (base recipe 11 adds it); "
                "running the base image's console instead of the launcher's package",
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


def _monitor_dependency_available() -> bool:
    """Check the base interpreter, without the checkout or ambient PYTHONPATH.

    Recipe 10 has the console but lacks psutil. Its installed console still
    works; mounting slice-5+ source over it would fail at import time.
    """
    return _python_has_monitor_dependency(Path(CONSOLE_PYTHON))


def _python_has_monitor_dependency(python: Path) -> bool:
    try:
        subprocess.run(
            [str(python), "-I", "-c", "import psutil"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def _accepts_connections(address: str, port: int) -> bool:
    try:
        with socket.create_connection((address, port), timeout=0.2):
            return True
    except OSError:
        return False
