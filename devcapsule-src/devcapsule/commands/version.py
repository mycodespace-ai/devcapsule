"""Inspect the source identity embedded in this DevCapsule distribution."""

from __future__ import annotations

import argparse

from devcapsule.build_info import build_info_json, current_build_info
from devcapsule.commands.framework import Command

__all__ = ["COMMAND", "VersionCommand"]


class VersionCommand(Command):
    name = "version"
    help = "Show this DevCapsule distribution's version and public source identity."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--json",
            dest="as_json",
            action="store_true",
            help="Emit stable machine-readable JSON.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        info = current_build_info()
        if arguments.as_json:
            print(build_info_json(info))
            return 0
        print(f"DevCapsule {info.build_mnemonic} (package {info.version})")
        print(f"Source repository: {info.source_repository}")
        print(f"Source revision: {info.source_revision}")
        print(f"Source URL: {info.source_url}")
        return 0


COMMAND = VersionCommand
