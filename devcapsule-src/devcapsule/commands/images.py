"""Build and inspect DevCapsule-managed local images."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Mapping

from python_on_whales import docker
from python_on_whales.exceptions import DockerException

from devcapsule.images.base import (
    BASE_RECIPE_NAMES,
    BASE_RECIPE_VERSION,
    DEFAULT_BASE_RECIPE,
    BaseImageBuildOptions,
    base_image_recipe,
    build_base_image,
    resolved_root_image,
)
from devcapsule.commands.framework import Command, Group, capsule_platform_argument
from devcapsule.compat import CliError
from devcapsule.environment_realization import optional_local_image, realize_environment
from devcapsule.images.metadata import LocalImageRecord, inspect_local_image, list_local_images
from devcapsule.materialization import ImageDetails
from devcapsule.platforms import Platform
from devcapsule.configuration.execution import (
    fresh_resolved_project,
)


class ImagesListCommand(Command):
    name = "list"
    help = "List DevCapsule-managed images from the local Docker store."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--include-legacy",
            action="store_true",
            help="Include transitional images carrying only legacy DevCapsule labels.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        records = list_local_images(include_legacy=arguments.include_legacy)
        if not records:
            print("No DevCapsule images found in the local Docker image store.")
            return 0
        _print_table(records)
        return 0


def _existing_file(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"{value!r} is not an existing file")
    return path


class ImagesBuildCommand(Command):
    name = "build"
    help = "Build a DevCapsule base or materialized environment image."

    @classmethod
    def configure(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--type", dest="image_type", choices=["base", "environment"], required=True
        )
        parser.add_argument("--tag", help="Local output name for a base image.")
        parser.add_argument(
            "--recipe",
            choices=list(BASE_RECIPE_NAMES),
            default=DEFAULT_BASE_RECIPE,
            help=f"Curated base-image recipe to build (default: {DEFAULT_BASE_RECIPE}).",
        )
        parser.add_argument(
            "--from", dest="root_image", help="Override the recipe's default root image."
        )
        parser.add_argument("--pex", type=_existing_file,
                            help="Optional recipe-builder PEX for source provenance; never embedded in the base.")
        parser.add_argument(
            "--source-revision",
            help="Assert the source revision already embedded in the selected PEX.",
        )
        parser.add_argument(
            "--allow-local-source",
            action="store_true",
            help="Allow a PEX built from dirty or unpublished local source.",
        )
        parser.add_argument(
            "--project",
            type=Path,
            help=(
                "Project root or descendant for an environment build; "
                "defaults to current-directory discovery."
            ),
        )
        parser.add_argument(
            "--base",
            dest="base_override",
            help="Explicit local or registry DevCapsule base override for an environment build.",
        )
        parser.add_argument(
            "--alias", help="Optional additional local tag for the canonical environment image."
        )
        parser.add_argument(
            "--network",
            choices=["default", "host", "none"],
            default="default",
            help="Build network mode forwarded to Docker buildx (default: default).",
        )
        parser.add_argument(
            "--platform",
            dest="capsule_platform",
            type=capsule_platform_argument,
            metavar="PLATFORM",
            help="Capsule platform of a base build, such as linux-arm64; default: the one this host "
                 "creates projects for. An environment build is for its project's platform.",
        )

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        if arguments.image_type == "environment":
            if arguments.capsule_platform is not None:
                raise CliError("--platform applies only to base builds; an environment build is for its project's platform.")
            return _build_environment(
                project=arguments.project,
                base_override=arguments.base_override,
                alias=arguments.alias,
            )
        if arguments.tag is None:
            raise CliError("--tag is required for 'images build --type base'.")
        if arguments.source_revision is None and not arguments.allow_local_source:
            raise CliError(
                "--source-revision is required for a base build; use --allow-local-source "
                "only for an explicit dirty or unpublished development build."
            )
        if (
            arguments.project is not None
            or arguments.base_override is not None
            or arguments.alias is not None
        ):
            raise CliError("--project, --base, and --alias apply only to environment builds.")
        selected_pex = (
            arguments.pex.expanduser().resolve() if arguments.pex is not None else None
        )
        selected_recipe = base_image_recipe(arguments.recipe)
        options = BaseImageBuildOptions(
            pex=selected_pex,
            image=arguments.tag,
            root_image=arguments.root_image,
            source_revision=arguments.source_revision,
            allow_local_source=arguments.allow_local_source,
            recipe=arguments.recipe,
        )
        if selected_recipe.status == "wip":
            print(
                f"WARNING: base recipe {arguments.recipe!r} is WIP and still requires "
                "specialized NVIDIA GPU E2E validation before V1 release.",
                file=sys.stderr,
            )
        build_base_image(
            options,
            network=arguments.network,
            platform=arguments.capsule_platform or Platform.current(),
        )
        image = inspect_local_image(arguments.tag)
        labels = dict(image.config.labels or {})
        print(f"Built DevCapsule base image: {arguments.tag}")
        print(f"Image ID: {image.id}")
        print(f"Root image: {resolved_root_image(options)}")
        recipe_name = labels.get("devcapsule.base.recipe", arguments.recipe)
        recipe_version = labels.get("devcapsule.base.recipe-version", BASE_RECIPE_VERSION)
        recipe_status = labels.get("devcapsule.base.recipe-status", selected_recipe.status)
        print(f"Base recipe: {recipe_name}@{recipe_version} ({recipe_status.upper()})")
        print("Runtime: supplied by the launcher when materializing an environment")
        print(f"Source revision: {labels.get('devcapsule.source.revision', 'unknown')}")
        print(f"Source URL: {labels.get('devcapsule.source.url', 'unknown')}")
        verification = (
            "bypassed for explicit local source"
            if arguments.allow_local_source
            else "public GitHub commit reachable"
        )
        print(f"Source verification: {verification}")
        print(f"Build network: {arguments.network}")
        return 0


class ImagesCommand(Group):
    name = "images"
    help = "List and build DevCapsule-managed images."

    @classmethod
    def subcommands(cls) -> Mapping[str, type[Command] | type[Group]]:
        return {
            ImagesListCommand.name: ImagesListCommand,
            ImagesBuildCommand.name: ImagesBuildCommand,
        }


def _print_table(records: tuple[LocalImageRecord, ...]) -> None:
    headers = ("KIND", "CANONICAL", "ALIASES", "IMAGE-ID", "COMPONENT", "RECIPE", "CREATED", "SIZE")
    rows = [
        (
            record.kind,
            record.canonical_name,
            ",".join(record.aliases) or "-",
            record.image_id,
            record.component,
            record.recipe,
            record.created,
            record.size,
        )
        for record in records
    ]
    widths = [max(len(header), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


COMMAND = ImagesCommand


def _build_environment(*, project: Path | None, base_override: str | None, alias: str | None) -> int:
    selected = fresh_resolved_project(project or Path("."))
    realized = realize_environment(selected, base_override=base_override, report=print)
    locked = realized.locked
    canonical_details = realized.image
    if alias is not None:
        _add_alias(canonical_details, alias)

    labels = canonical_details.labels
    action = "Built" if realized.created else "Reused"
    print(f"{action} DevCapsule environment image: {canonical_details.reference}")
    print(f"Image ID: {canonical_details.identity}")
    print(f"Base reference: {realized.base_reference}")
    print(f"Base identity: {realized.base.identity}")
    print(f"Component: {locked.component_id}@{locked.artifact.version} ({locked.artifact.variant})")
    print(f"Component SHA-256: {locked.artifact.sha256.lower()}")
    print(f"Formation identity: {labels['devcapsule.materialization.identity']}")
    print(
        f"Artifact cache: {realized.cache / 'artifacts' / 'sha256' / locked.artifact.sha256.lower()}"
    )
    if realized.explicit_base_override:
        print("Base selection: explicit developer override", file=sys.stderr)
    if alias is not None:
        print(f"Alias: {alias}")
    print("No container was launched.")
    return 0


def _add_alias(canonical: ImageDetails, alias: str) -> None:
    existing = optional_local_image(alias)
    if existing is not None:
        if existing.identity != canonical.identity:
            raise CliError(
                f"Alias {alias!r} already identifies {existing.identity}; remove or retag it before retrying."
            )
        return
    try:
        docker.image.tag(canonical.reference, alias)
    except DockerException as exc:
        raise CliError(f"Cannot add image alias {alias!r}: {exc}") from exc
