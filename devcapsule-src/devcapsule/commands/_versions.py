"""Discoverable project version-set commands; effects live in version_sets."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping

from devcapsule.commands.framework import Command, Group, STABLE_JSON_HELP
from devcapsule import version_sets
from devcapsule.runtime_configuration import CapsuleAccess
from devcapsule.compat import CliError
from typing import Sequence


def _start(context: object | None) -> Path:
    start = getattr(context, "start_path", None)
    if start is None:
        raise AssertionError("versions requires project context")
    result = start()
    assert isinstance(result, Path)
    return result


class VersionsCommand(Command):
    name = "show"
    help = "Inspect the effective version set, its origin and validation evidence."

    @classmethod
    def invoke(cls, prog: str, argv: Sequence[str], context: object | None = None) -> int:
        try:
            return super().invoke(prog, argv, context)
        except OSError as exc:
            raise CliError(f"Version-set operation could not finish: {exc}. Inspect 'project versions show'; retry after resolving the storage or network failure.") from exc

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        if cls.name == "show":
            parser.add_argument("--json", dest="as_json", action="store_true", help=STABLE_JSON_HELP)
        if cls.name == "check":
            parser.add_argument("--status-url", metavar="URL",
                                help="Read the DevCapsule compatibility feed from URL for this check, as DEVCAPSULE_STATUS_URL does for every check.")
        if cls.name in {"select", "rollback", "follow-project"}:
            parser.add_argument("--authorize", action="append", nargs=2, default=[], metavar=("NAME", "VALUE"),
                                help="Answer a vendor acquisition question for the target set; never changes host permissions.")
        if cls.name == "preview":
            parser.add_argument("component")
            parser.add_argument("version", help="Exact version or channel label, resolved to immutable artifacts.")
        elif cls.name == "select":
            parser.add_argument("preview", help="Full preview identity printed by preview.")
            parser.add_argument("--unvalidated", action="store_true", help="Explicitly try a set without DevCapsule validation.")
        elif cls.name == "rollback":
            parser.add_argument("identity", nargs="?", help="Known-good set; defaults to the most recently successful other set.")
            parser.add_argument("--reacquire", action="store_true", help="Attempt exact downloads if local recovery resources are missing.")
        elif cls.name == "follow-project":
            parser.add_argument("--apply", action="store_true", help="Prepare and follow the current project recommendation.")
        elif cls.name == "propose":
            parser.add_argument("output", type=Path, help="New patch file to review and optionally contribute upstream.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        start = _start(context)
        if cls.name == "show":
            print(version_sets.inspection_json(start) if arguments.as_json else version_sets.inspect(start))
        elif cls.name == "check":
            print(version_sets.check(start, status_url=arguments.status_url))
        elif cls.name == "preview":
            version_sets.preview(start, arguments.component, arguments.version)
        elif cls.name == "select":
            version_sets.select(start, arguments.preview, unvalidated=arguments.unvalidated, acquisitions=arguments.authorize)
        elif cls.name == "history":
            print(version_sets.history(start))
        elif cls.name == "rollback":
            version_sets.rollback(start, arguments.identity, reacquire=arguments.reacquire, acquisitions=arguments.authorize)
        elif cls.name == "follow-project":
            version_sets.follow_project(start, apply=arguments.apply, acquisitions=arguments.authorize)
        elif cls.name == "propose":
            print(version_sets.proposal(start, arguments.output))
        elif cls.name in {"dismiss", "defer"}:
            print(version_sets.reminder(start, action=cls.name))
        return 0


class VersionsGroup(Group):
    name = "versions"
    help = "Inspect, try and recover checkout-local component version sets."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        descriptions = {
            "show": VersionsCommand.help,
            "check": "Check component distribution channels explicitly; never update a selection.",
            "preview": "Preview one component change without downloading executables or changing selection.",
            "select": "Prepare a preview and select it for the next ordinary launch.",
            "history": "List exact version sets with locally observed successful launches.",
            "rollback": "Prepare and select a known-good set using current host permissions.",
            "follow-project": "Compare with the project recommendation and explicitly follow it again.",
            "propose": "Export a reviewable upstream lock patch after successful local use.",
            "dismiss": "Silence the checked candidate versions until different candidates appear.",
            "defer": "Silence checked candidates for seven days.",
        }
        return {name: type("Versions_" + name, (VersionsCommand,), {
            "name": name, "help": help,
            # Only `show` answers inside a capsule; every other operation writes.
            "capsule_access": CapsuleAccess.INSPECTS if name == "show" else CapsuleAccess.MUTATES,
        })
                for name, help in descriptions.items()}
