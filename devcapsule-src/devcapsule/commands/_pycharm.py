"""PyCharm image utilities and the retired launch-command diagnostic."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Mapping, Sequence

from devcapsule.commands.framework import Command, Group, UsageError
from devcapsule.compat import run_script

from devcapsule.launch.pycharm._image_build import build_pycharm_image, parse_pycharm_build_options


class PycharmBuildCommand(Command):
    name = "build"
    help = "Build the current Dockerized PyCharm image with pinned Node.js/npm tooling."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--pycharm",
            type=Path,
            required=True,
            help="PyCharm .tar.gz archive or unpacked PyCharm directory.",
        )
        parser.add_argument(
            "--image", default="pycharm-isolated:latest", help="Docker image tag to create."
        )
        parser.add_argument(
            "--base-image",
            default="ubuntu:24.04",
            help="Base OCI image used for the IDE image (default: ubuntu:24.04).",
        )
        parser.add_argument(
            "--network",
            default="default",
            help="Build network mode passed to docker buildx (default: default).",
        )
        parser.add_argument(
            "--extra-apt-package",
            action="append",
            default=[],
            help="Extra apt package to install into the image. Repeat as needed.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        options = parse_pycharm_build_options(
            pycharm=arguments.pycharm,
            image=arguments.image,
            base_image=arguments.base_image,
            network=arguments.network.lower(),
            extra_apt_packages=tuple(arguments.extra_apt_package),
        )
        return build_pycharm_image(options)


class PycharmCheckRuntimeCommand(Command):
    name = "check-runtime"
    help = "Run the current PyCharm runtime dependency check."

    # The dependency-check script owns its own argument surface; forward every
    # token untouched rather than modeling it here.
    @classmethod
    def invoke(cls, prog: str, argv: Sequence[str], context: object | None = None) -> int:
        if "--help" in argv or "-h" in argv:
            return super().invoke(prog, ["--help"], context)
        return run_script("docker4pycharm/check-runtime-deps.sh", list(argv))


class PycharmConfiguration(Group):
    """Retained image utilities; project launch owns running the IDE."""

    name = "pycharm"
    help = "Build a PyCharm image or check runtime dependencies."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {
            PycharmBuildCommand.name: PycharmBuildCommand,
            PycharmCheckRuntimeCommand.name: PycharmCheckRuntimeCommand,
        }

    @classmethod
    def invoke(cls, prog: str, argv: Sequence[str], context: object | None = None) -> int:
        # Reject even old --help/options before parsing or preparing any launch.
        # This diagnostic is not a command alias and is absent from group help.
        if argv and argv[0] == "run":
            raise UsageError(
                "'devcapsule pycharm run' was retired. "
                "Use 'devcapsule project run' in a configured checkout, or "
                "'devcapsule project --path DIRECTORY run'. "
                "Initialize an unconfigured directory with "
                "'devcapsule project --path DIRECTORY init'. "
                "Legacy image and profile options are not translated."
            )
        return super().invoke(prog, argv, context)
