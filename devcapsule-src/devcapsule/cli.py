"""Command line entry point for DevCapsule.

Dispatch belongs to the argparse-based framework in
``devcapsule.commands.framework``; every command module exports a framework
``COMMAND`` class discovered from the ``devcapsule.commands`` package.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from typing import Sequence

import devcapsule.commands
from devcapsule.commands import framework
from devcapsule.compat import CliError, DecisionPending


PROJECT_NAME = "devcapsule"
DESCRIPTION = "Profile-driven Docker launch tooling for isolated IDEs."

CommandEntry = type[framework.Command] | type[framework.Group]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the DevCapsule CLI and return its exit code."""

    args = list(sys.argv[1:] if argv is None else argv)
    try:
        return _dispatch(args)
    except SystemExit as exc:  # argparse --help exits; translate to a return code.
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    except DecisionPending as exc:
        print(f"{PROJECT_NAME}: {exc}", file=sys.stderr)
        return DecisionPending.EXIT_STATUS
    except CliError as exc:
        print(f"{PROJECT_NAME}: {exc}", file=sys.stderr)
        return 2


def command_names(*, include_hidden: bool = False) -> tuple[str, ...]:
    """Enumerate discoverable top-level command names."""

    names = [
        name
        for name, entry in _discovered_commands().items()
        if include_hidden or not entry.hidden
    ]
    return tuple(sorted(names))


def _dispatch(args: list[str]) -> int:
    if not args or args[0] in ("-h", "--help"):
        print(_top_level_help(), end="")
        return 0
    name = args[0]
    if name.startswith("-"):
        raise framework.UsageError(
            f"unknown option {name!r}; run '{PROJECT_NAME} --help' for usage."
        )
    from devcapsule.configuration.storage import load_settings
    load_settings()  # Admit the home before command-specific diagnoses or writes.
    entry = _load_command(name)
    if entry is None:
        visible = ", ".join(command_names())
        raise framework.UsageError(f"unknown command {name!r}; commands: {visible}.")
    return entry.invoke(f"{PROJECT_NAME} {name}", args[1:])


def _load_command(name: str) -> CommandEntry | None:
    module_name = name.replace("-", "_")
    import_path = f"devcapsule.commands.{module_name}"
    try:
        module = importlib.import_module(import_path)
    except ModuleNotFoundError as exc:
        if exc.name == import_path:
            return None
        raise
    return _command_from_module(module, import_path)


def _discovered_commands() -> dict[str, CommandEntry]:
    commands: dict[str, CommandEntry] = {}
    for module_info in pkgutil.iter_modules(devcapsule.commands.__path__):
        module_name = module_info.name
        if module_name.startswith("_") or module_name == "framework":
            continue
        import_path = f"devcapsule.commands.{module_name}"
        module = importlib.import_module(import_path)
        entry = _command_from_module(module, import_path)
        commands[entry.name] = entry
    return commands


def _command_from_module(module: object, import_path: str) -> CommandEntry:
    entry = getattr(module, "COMMAND", None)
    if entry is None:
        raise CliError(f"Command module {import_path!r} does not define COMMAND.")
    if isinstance(entry, type) and issubclass(entry, (framework.Command, framework.Group)):
        return entry
    raise CliError(f"{import_path}.COMMAND is not a recognized command class.")


def _top_level_help() -> str:
    header = (
        f"Usage: {PROJECT_NAME} [OPTIONS] COMMAND [ARGS]...\n\n  {DESCRIPTION}\n"
    )
    return header + framework.render_command_listing(_discovered_commands())
