"""Entry points for the packaged agent recording instructions and Python helpers."""
import argparse
from importlib.resources import files
import os
from pathlib import Path
from typing import Mapping

from devcapsule.commands.framework import Command, Group
from devcapsule.compat import CliError
from devcapsule.presentation_authoring import export_tools, install_skill, presentation_link

__all__ = ["COMMAND"]

PACKAGE = "devcapsule.presentation_tools"
ASSETS = ("__init__.py", "producer.py", "recording.py", "README.md", "example.py", "SKILL.md")


class GuideCommand(Command):
    name = "guide"
    help = "Read the agent instructions for English-specified E2E recordings."

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        print(files(PACKAGE).joinpath("README.md").read_text(encoding="utf-8"))
        return 0


class ExportCommand(Command):
    name = "export"
    help = "Export the agent skill, instructions and standalone Python helpers to a new directory."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=Path, help="New directory; existing directories are preserved.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        assets = {name: files(PACKAGE).joinpath(name).read_bytes() for name in ASSETS}
        try:
            package = export_tools(arguments.directory, assets)
        except (OSError, ValueError) as error:
            raise CliError(f"cannot export presentation tools: {error}") from error
        print(f"Presentation tools: {package}\nAgent instructions: {package / 'README.md'}")
        return 0


class InstallSkillCommand(Command):
    name = "install-skill"
    help = "Install the recorded-E2E skill directly into a new skill directory."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "directory", type=Path,
            help="New skill folder, e.g. .agents/skills/devcapsule-recorded-e2e; existing paths are preserved.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        content = files(PACKAGE).joinpath("SKILL.md").read_bytes()
        try:
            skill = install_skill(arguments.directory, content)
        except OSError as error:
            raise CliError(f"cannot install recorded-E2E skill: {error}") from error
        print(f"Installed skill: {skill}\nStart a new agent session to discover it.")
        return 0


class HandOffCommand(Command):
    name = "hand-off"
    help = "Print the recorded presentation's console link for the engineer."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("folder", type=Path)
        parser.add_argument("--project", type=Path, help="Console project root; defaults to PROJECT_PATH or cwd.")
        parser.add_argument("--console-url", help="Defaults to DEVCAPSULE_CONSOLE_URL.")
        parser.add_argument("--token-file", type=Path, help="Defaults to the capsule console token file.")

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        root = (arguments.project or Path(os.environ.get("PROJECT_PATH") or ".")).resolve()
        folder = arguments.folder.resolve()
        origin = arguments.console_url or os.environ.get("DEVCAPSULE_CONSOLE_URL", "")
        token_path = arguments.token_file or Path(os.environ.get("DEVCAPSULE_CONSOLE_TOKEN_FILE") or "/run/devcapsule-console-token")
        try:
            token = token_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            token = ""
        try:
            if not (folder / "presentation.json").is_file():
                raise ValueError(f"no presentation.json in {folder}")
            link = presentation_link(folder, project=root, console_url=origin, token=token)
        except (OSError, ValueError) as error:
            raise CliError(str(error)) from error
        if not token:
            print("Open the console first to establish a browser session; no readable run token was found.")
        print(link)
        return 0


class PresentationsCommand(Group):
    name = "presentations"
    help = "Record E2E scenarios and make presentations: agent guide, Python toolkit and console link."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {command.name: command for command in (GuideCommand, ExportCommand, InstallSkillCommand, HandOffCommand)}


COMMAND = PresentationsCommand
