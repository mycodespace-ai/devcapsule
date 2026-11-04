"""Shared host-side realization of one resolved project environment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from python_on_whales import docker
from python_on_whales.exceptions import DockerException

from devcapsule.compat import CliError
from devcapsule.host_daemon import daemon_architecture
from devcapsule.platforms import Platform
from devcapsule.images.build import BuildxImageBuilder, ImageBuildSpec
from devcapsule.images.metadata import inspect_local_image
from devcapsule.materialization import (
    ImageDetails,
    LockedEnvironment,
    cache_root,
    ensure_materialized_surface,
    parse_locked_environment,
    validate_base_image,
)
from devcapsule.configuration.storage import (
    ResolvedProject,
)
from devcapsule.configuration.authorization import (
    authorized_base_selection,
    review_authorizations,
)
from devcapsule.configuration.trust import HomeTrust
from devcapsule.runtime_artifact import runtime_artifact
from devcapsule.runtime_command import RuntimeCommand


@dataclass(frozen=True)
class RealizedEnvironment:
    """Verified canonical image and formation inputs selected for one run."""

    image: ImageDetails
    base: ImageDetails
    base_reference: str
    locked: LockedEnvironment
    cache: Path
    created: bool
    explicit_base_override: bool


ImageLookup = Callable[[str], ImageDetails | None]
ImageRequirement = Callable[[str], ImageDetails]
ImageBuild = Callable[[ImageBuildSpec], None]
Materialize = Callable[..., tuple[str, bool]]


def realize_environment(
    selected: ResolvedProject,
    *,
    base_override: str | None = None,
    root: Path | None = None,
    obtain_image: ImageRequirement | None = None,
    inspect_image: ImageLookup | None = None,
    require_image: ImageRequirement | None = None,
    build: ImageBuild | None = None,
    materialize: Materialize | None = None,
    report: Callable[[str], None] | None = None,
    prepare_base: Callable[[ImageDetails], None] | None = None,
    trust: HomeTrust | None = None,
) -> RealizedEnvironment:
    """Strictly reuse or materialize the canonical image for one resolved project."""

    from devcapsule.configuration.capabilities import CapabilityPolicy
    if (base_override is not None and "capabilities" in selected.manifest
            and CapabilityPolicy.read(selected.manifest).departing(selected.departures).minimums):
        if base_override != selected.lock.get("base", {}).get("reference"):
            raise CliError("A base override cannot establish the project's minimum-version guarantee; use its pinned compatible base.")
    locked = parse_locked_environment(selected.lock)
    capsule_platform = Platform.parse(locked.platform)
    from devcapsule.configuration.storage import load_settings
    if trust is None:
        trust = HomeTrust.read(load_settings())
    reviews = review_authorizations(selected.manifest, selected.lock, selected.checkout, trust)
    problems = [
        item for item in reviews if item.problem is not None
        and not (item.name == "base-image" and base_override is not None)
    ]
    if problems:
        raise CliError("Configuration needs authorization decisions:\n" + "\n".join(
            item.render(selected.root) for item in problems
        ))
    runtime = selected.resolution.get("runtime", {})
    if not isinstance(runtime, dict) or runtime.get("component") != locked.component_id:
        component = runtime.get("component") if isinstance(runtime, dict) else None
        raise CliError(
            f"Fresh resolution selects component {component!r}, "
            f"but the lock formation selects {locked.component_id!r}."
        )

    local_authorization = False
    if base_override is not None:
        explicit_override = True
        base_reference = base_override
        expected_base_identity = None
    else:
        selection = authorized_base_selection(selected.lock, selected.checkout, trust=trust)
        if selection is None:  # pragma: no cover - required selection raises instead.
            raise CliError("The checkout has no base-image authorization.")
        local_authorization = selection.is_local
        explicit_override = local_authorization
        base_reference = selection.reference
        expected_base_identity = (
            selection.local_image_identity if local_authorization else locked.base_identity
        )

    if obtain_image is not None:
        obtain = obtain_image
    elif local_authorization:
        obtain = required_local_image
    else:
        obtain = lambda reference: ensure_local_image(reference, capsule_platform)
    inspect = inspect_image or optional_local_image
    require = require_image or required_local_image
    base = obtain(base_reference)
    validate_base_image(
        base,
        platform=locked.platform,
        expected_identity=expected_base_identity,
    )
    if report is not None and local_authorization:
        report(
            f"Base selection: local override {base_reference} ({base.identity}); "
            f"the project recommends {locked.base_reference}."
        )
    # Display capability is a property of the verified base. Explain and
    # validate it before any component acquisition or environment build.
    if prepare_base is not None:
        prepare_base(base)

    selected_cache = (root or cache_root()).expanduser().resolve()
    if build is None:
        # One context root for every build: BuildKit's incremental transfer of
        # the IDE trees is keyed on this path, see BuildxImageBuilder.
        builder = BuildxImageBuilder(context_root=selected_cache / "build-contexts" / "context")
        build = lambda spec: builder.build(spec, network="none", platform=capsule_platform)
    materialize_environment = materialize or ensure_materialized_surface
    # Explanation/reporting hooks ride only the real materializer; injected
    # test materializers keep their narrower signature.
    narration: dict[str, Any] = (
        {}
        if materialize is not None
        else {
            "runtime_pex": runtime_artifact(capsule_platform),
            "runtime_command": RuntimeCommand(runtime.get("devcapsule-command", RuntimeCommand.STANDARD)),
            "report": report,
            "list_formations": lambda: component_formations(locked.component_id),
        }
    )
    canonical, created = materialize_environment(
        base_reference=base_reference,
        base_identity=base.identity,
        platform=locked.platform,
        artifact=locked.artifact,
        ancillary_artifacts=locked.ancillary_artifacts,
        cache_root=selected_cache,
        inspect_image=inspect,
        build=build,
        recipe_id=locked.recipe_id,
        recipe_version=locked.recipe_version,
        component_id=locked.component_id,
        **narration,
    )
    image = require(canonical)
    return RealizedEnvironment(
        image=image,
        base=base,
        base_reference=base_reference,
        locked=locked,
        cache=selected_cache,
        created=created,
        explicit_base_override=explicit_override,
    )


def ensure_local_image(reference: str, platform: Platform) -> ImageDetails:
    """The local image at ``reference``, pulled for the lock's ``platform`` when absent."""
    try:
        if not docker.image.exists(reference):
            docker.image.pull(reference, platform=platform.emulated_docker_platform(daemon_architecture()))
    except DockerException as exc:
        raise CliError(f"Cannot obtain Docker image {reference!r}: {exc}") from exc
    return required_local_image(reference)


def required_local_image(reference: str) -> ImageDetails:
    image = inspect_local_image(reference)
    return image_details(reference, image)


def optional_local_image(reference: str) -> ImageDetails | None:
    try:
        if not docker.image.exists(reference):
            return None
    except DockerException as exc:
        raise CliError(f"Cannot query local Docker image {reference!r}: {exc}") from exc
    return required_local_image(reference)


def image_details(reference: str, image: Any) -> ImageDetails:
    return ImageDetails(
        reference=reference,
        identity=str(image.id),
        labels=dict(image.config.labels or {}),
        operating_system=str(image.os),
        architecture=str(image.architecture),
        entrypoint=tuple(image.config.entrypoint or ()),
        command=tuple(image.config.cmd or ()),
        size_bytes=int(image.size or 0),
    )


def component_formations(component_id: str) -> tuple[ImageDetails, ...]:
    """Every local canonical formation image for one surface component.

    Best-effort by design: this feeds explanation and reporting, which must
    never be the reason a realization fails.
    """

    repository = f"devcapsule-local-{component_id}"
    try:
        images = docker.image.list(filters={"reference": repository})
    except DockerException:
        return ()
    details = []
    for image in images:
        for tag in image.repo_tags:
            if tag.startswith(f"{repository}:"):
                details.append(image_details(tag, image))
    return tuple(details)


def omit_unavailable_optional(selected: ResolvedProject, url: str) -> ResolvedProject | None:
    """Derive a smaller run after a download failure, preserving mandatory closure.

    No file changes and no integrity exception is caught. Returning None means
    the failed artifact is mandatory (including developer-selected tools).
    """
    from copy import deepcopy
    from dataclasses import replace
    from devcapsule.components.catalog import COMPONENTS
    from devcapsule.configuration.capabilities import CapabilityPolicy, LocalCapabilities
    from devcapsule.configuration.capability_selection import matrix_for, usable_lock
    from devcapsule.configuration.model import Configuration
    policy = CapabilityPolicy.read(selected.manifest).departing(selected.departures)
    if not policy.optional:
        return None
    matrix = matrix_for(selected.lock)
    local = LocalCapabilities.read(selected.checkout)
    failed = {name for name, metadata in selected.lock["components"].items()
              if isinstance(metadata, dict) and name in COMPONENTS
              and any(artifact.url == url for artifact in COMPONENTS[name].locked_artifacts(metadata, str(selected.lock["platform"])))}
    mandatory = {component for capability in (*policy.required, *local.selected) for component in matrix.component_closure(capability)}
    if not failed or failed & mandatory:
        return None
    omitted = {capability for capability in policy.optional if capability in matrix.capabilities()
               and failed & set(matrix.component_closure(capability))}
    if not omitted:
        return None
    choice = LocalCapabilities(local.selected, tuple(sorted(set(local.without) | omitted)))
    lock, _ = usable_lock(policy, selected.lock, choice)
    checkout = deepcopy(selected.checkout)
    checkout.setdefault("capabilities", {})["without"] = list(choice.without)
    from devcapsule.configuration.storage import load_settings
    configuration = Configuration(selected.manifest, lock, checkout, load_settings(), departures=selected.departures)
    configuration.review().require_ready(selected.root)
    return replace(selected, lock=lock, checkout=checkout, resolution=configuration.resolve().document())
