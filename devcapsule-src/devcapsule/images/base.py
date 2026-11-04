"""Redistributable DevCapsule development-base image planning."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import urllib.error
import urllib.request

from devcapsule.images.contract import (
    WEBCONSOLE_LABEL,
    CONTAINED_DISPLAY,
    HOST_X11_ONLY_DISPLAY,
    LAUNCHER_SUPPLIED_RUNTIME,
    RECIPE_SOURCE_LABEL,
    RECIPE_SOURCE_PATH,
    SERVICES_LABEL,
    BaseContract,
)
from devcapsule.build_info import BuildInfo, BuildInfoError, current_build_info, read_pex_build_info
from devcapsule.compat import CliError
from devcapsule.launch.pycharm._image_build import BASE_APT_PACKAGES
from devcapsule.platforms import Platform
from devcapsule.images.build import (
    AptPackagesComponent,
    BaseImageComponent,
    BuildComponent,
    BuildxImageBuilder,
    ContributionComponent,
    EnvComponent,
    ImageCopyComponent,
    ImageBuildSpec,
    LabelComponent,
)
from devcapsule.images.tooling import (
    MAVEN_CURRENT,
    MAVEN_CURRENT_BIN,
    MAVEN_VERSION,
    NODE_CURRENT_BIN,
    TEMURIN_CURRENT,
    TEMURIN_CURRENT_BIN,
    TEMURIN_VERSION,
    WEBCONSOLE_ROOT,
    maven_tooling_component,
    node_tooling_component,
    temurin_tooling_component,
    webconsole_tooling_component,
)
from devcapsule.images.metadata import (
    BASE_KIND,
    CONTAINED_DISPLAY_LABEL_VALUE,
    DISPLAY_LABEL,
    managed_labels,
)


DEFAULT_ROOT_IMAGE = "ubuntu:24.04"
NVIDIA_CUDA_ROOT_IMAGE = "nvidia/cuda:12.8.1-devel-ubuntu24.04"
DEFAULT_OUTPUT_IMAGE = "devcapsule-base:latest"
PEX_DESTINATION = "/opt/devcapsule/bin/devcapsule.pex"
# Recipe 8 added the contained display stack (DISPLAY_APT_PACKAGES) and the
# label the launcher reads to select the contained transport; recipe 9 adds
# the tint2 panel so a hidden window is always one click away; recipe 10
# adds the capsule web console under /opt/devcapsule-webconsole, installed
# from the same public revision as the runtime (R-CONSOLE-001); recipe 11
# gives the console its process and resource monitor (psutil).
BASE_RECIPE_VERSION = "11"
# The capabilities a base satisfies by itself; components fill the rest.
# Adding to this set keeps the family; removing from it opens a new one.
BASE_SERVICES = frozenset({"python", "docker-cli", "node", "java", "maven", "postgresql-client"})
DEFAULT_BASE_RECIPE = "ubuntu-24.04"
NVIDIA_CUDA_BASE_RECIPE = "nvidia-cuda-devel"
BASE_RECIPE_NAMES = (DEFAULT_BASE_RECIPE, NVIDIA_CUDA_BASE_RECIPE)
PUBLIC_SOURCE_TIMEOUT_SECONDS = 10

# The contained display: the capsule's own X server with the RFB server built
# in, the core fonts it refuses to start without, the browser client and its
# WebSocket bridge, and a window manager. All redistributable (GPL-2.0,
# MPL-2.0/LGPL, GPL-2.0) and shipped in the published base, so a capsule never
# needs the host's X session. See the contained-display design note.
DISPLAY_APT_PACKAGES = (
    "tigervnc-standalone-server",
    "xfonts-base",
    "novnc",
    "python3-websockify",
    "openbox",
    # The panel: a button per window, so nothing can hide where a browser
    # user cannot reach it with the mouse (owner finding 2026-09-14).
    "tint2",
)
# DISPLAY_LABEL and CONTAINED_DISPLAY_LABEL_VALUE are defined in
# image_metadata and re-exported here for the base build's callers.


@dataclass(frozen=True)
class BaseImageRecipe:
    name: str
    default_root_image: str
    status: str
    labels: tuple[tuple[str, str], ...] = ()


def current_contract(recipe_name: str = DEFAULT_BASE_RECIPE, *, install_display: bool = True) -> BaseContract:
    """The contract a base built from this recipe today would carry."""
    return BaseContract(
        family=recipe_name,
        recipe=int(BASE_RECIPE_VERSION),
        services=BASE_SERVICES,
        display=CONTAINED_DISPLAY if install_display else HOST_X11_ONLY_DISPLAY,
        runtime=LAUNCHER_SUPPLIED_RUNTIME,
    )


BASE_IMAGE_RECIPES = {
    DEFAULT_BASE_RECIPE: BaseImageRecipe(
        name=DEFAULT_BASE_RECIPE,
        default_root_image=DEFAULT_ROOT_IMAGE,
        status="ready",
    ),
    NVIDIA_CUDA_BASE_RECIPE: BaseImageRecipe(
        name=NVIDIA_CUDA_BASE_RECIPE,
        default_root_image=NVIDIA_CUDA_ROOT_IMAGE,
        status="wip",
        labels=(
            ("devcapsule.base.gpu.vendor", "nvidia"),
            ("devcapsule.base.cuda.version", "12.8.1"),
        ),
    ),
}


@dataclass(frozen=True)
class BaseImageBuildOptions:
    pex: Path | None = None
    image: str = DEFAULT_OUTPUT_IMAGE
    root_image: str | None = None
    source_revision: str | None = None
    allow_local_source: bool = False
    install_baseline: bool = True
    # Separate from the baseline so a test can put the display stack on an
    # already-built base without reinstalling everything else.
    install_display: bool = True
    recipe: str = DEFAULT_BASE_RECIPE


def base_image_recipe(name: str) -> BaseImageRecipe:
    try:
        return BASE_IMAGE_RECIPES[name]
    except KeyError as exc:
        choices = ", ".join(BASE_RECIPE_NAMES)
        raise CliError(f"Unsupported DevCapsule base recipe {name!r}; choose one of: {choices}") from exc


def resolved_root_image(options: BaseImageBuildOptions) -> str:
    recipe = base_image_recipe(options.recipe)
    return options.root_image or recipe.default_root_image


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pex_build_info(options: BaseImageBuildOptions) -> BuildInfo:
    try:
        info = (read_pex_build_info(options.pex.expanduser().resolve())
                if options.pex is not None else current_build_info())
    except BuildInfoError as exc:
        raise CliError(str(exc)) from exc
    if options.source_revision is not None and options.source_revision != info.source_revision:
        raise CliError(
            f"Expected source revision {options.source_revision}, but the selected PEX embeds "
            f"{info.source_revision}. Nox writes local-only dist/devcapsule-local.pex; rebuild the "
            "public artifact with 'scripts/build-pex.sh', verify 'dist/devcapsule.pex version --json', "
            "and retry with dist/devcapsule.pex."
        )
    if not options.allow_local_source and options.source_revision is None:
        raise CliError(
            "--source-revision is required for a base build; use --allow-local-source only for an "
            "explicit dirty or unpublished development build."
        )
    if not options.allow_local_source and not info.has_public_revision:
        raise CliError(
            "The selected PEX does not embed a full public GitHub revision. Nox writes local-only "
            "dist/devcapsule-local.pex; after pushing the commit, run 'scripts/build-pex.sh' and "
            "verify 'dist/devcapsule.pex version --json'."
        )
    return info


def verify_public_github_revision(info: BuildInfo) -> None:
    """Fail unless the PEX's exact canonical commit URL is reachable."""

    request = urllib.request.Request(
        info.source_url,
        method="HEAD",
        headers={"User-Agent": "DevCapsule source verification"},
    )
    try:
        with urllib.request.urlopen(request, timeout=PUBLIC_SOURCE_TIMEOUT_SECONDS) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        raise _public_source_error(info, f"GitHub returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise _public_source_error(info, f"GitHub could not be reached ({exc})") from exc
    if not 200 <= status < 300:
        raise _public_source_error(info, f"GitHub returned HTTP {status}")


def _public_source_error(info: BuildInfo, detail: str) -> CliError:
    return CliError(
        f"Source revision {info.source_revision} is not publicly reachable at "
        f"{info.source_url}: {detail}. Push the commit and retry, or use "
        "--allow-local-source only for a deliberately local image."
    )


def build_base_image_spec(options: BaseImageBuildOptions) -> ImageBuildSpec:
    build_info = pex_build_info(options)
    recipe = base_image_recipe(options.recipe)
    root_image = resolved_root_image(options)
    components: list[BuildComponent] = [BaseImageComponent(root_image)]
    if options.install_baseline:
        if not build_info.has_public_revision:
            raise CliError(
                "Base recipes 10 and later install the web console from the runtime's GitHub revision. "
                "The selected runtime has no full GitHub source identity; select a PEX built "
                "from a published commit. --allow-local-source cannot supply the console source."
            )
        components.extend(
            [
                AptPackagesComponent(BASE_APT_PACKAGES),
                ContributionComponent("node", (node_tooling_component(),), ("/opt/node",)),
                ContributionComponent("temurin", (temurin_tooling_component(),), ("/opt/java",)),
                ContributionComponent("maven", (
                    ImageCopyComponent("temurin", "/opt/java", "/opt/java"),
                    maven_tooling_component(),
                ), ("/opt/maven",)),
            ]
        )
        components.append(
            EnvComponent(
                (
                    ("JAVA_HOME", TEMURIN_CURRENT),
                    ("MAVEN_HOME", MAVEN_CURRENT),
                    (
                        "PATH",
                        f"{MAVEN_CURRENT_BIN}:{TEMURIN_CURRENT_BIN}:{NODE_CURRENT_BIN}:${{PATH}}",
                    ),
                )
            )
        )
    if options.install_display:
        components.append(AptPackagesComponent(DISPLAY_APT_PACKAGES))
    if options.install_baseline:
        # The web console needs the baseline's python3-venv; its source is the
        # runtime's own verified revision, so the base and the runtime agree.
        components.append(ContributionComponent(
            "webconsole",
            (webconsole_tooling_component(build_info.source_repository, build_info.source_revision),),
            (WEBCONSOLE_ROOT,),
        ))
    components.extend(
        [
            LabelComponent(
                managed_labels(BASE_KIND, options.image)
                + (
                    ("devcapsule.base.recipe", recipe.name),
                    ("devcapsule.base.recipe-version", BASE_RECIPE_VERSION),
                    ("devcapsule.base.recipe-status", recipe.status),
                    ("devcapsule.base.runtime", "launcher-supplied"),
                    (SERVICES_LABEL, ",".join(sorted(BASE_SERVICES))),
                    (RECIPE_SOURCE_LABEL, RECIPE_SOURCE_PATH),
                )
                + (
                    ((DISPLAY_LABEL, CONTAINED_DISPLAY_LABEL_VALUE),)
                    if options.install_display
                    else ()
                )
                + (((WEBCONSOLE_LABEL, WEBCONSOLE_ROOT),) if options.install_baseline else ())
                + (
                    ("devcapsule.source.repository", build_info.source_repository),
                    ("devcapsule.source.revision", build_info.source_revision),
                    ("devcapsule.source.url", build_info.source_url),
                    ("org.opencontainers.image.source", build_info.source_repository),
                    ("org.opencontainers.image.revision", build_info.source_revision),
                    ("org.opencontainers.image.version", build_info.build_mnemonic),
                )
                + recipe.labels
                + (
                    ("devcapsule.component.temurin.version", TEMURIN_VERSION),
                    ("devcapsule.component.temurin.home", TEMURIN_CURRENT),
                    ("devcapsule.component.temurin.license", "GPL-2.0-with-classpath-exception"),
                    ("devcapsule.component.maven.version", MAVEN_VERSION),
                    ("devcapsule.component.maven.home", MAVEN_CURRENT),
                    ("devcapsule.component.maven.license", "Apache-2.0"),
                    ("devcapsule.component.postgresql-client.license", "PostgreSQL"),
                )
            ),
            # The base carries no real entrypoint (product-owner ruling
            # 2026-09-05): every formation's materialization recipe sets its
            # own ENTRYPOINT/CMD, so a boot contract baked here could only
            # be inherited by accident. Running the base directly drops into
            # the root image's default shell.
        ]
    )
    return ImageBuildSpec(options.image, root_image, tuple(components))


def build_base_image(
    options: BaseImageBuildOptions,
    builder: BuildxImageBuilder | None = None,
    *,
    platform: Platform,
    network: str = "default",
    source_verifier: Callable[[BuildInfo], None] = verify_public_github_revision,
) -> None:
    spec = build_base_image_spec(options)
    if not options.allow_local_source:
        source_verifier(pex_build_info(options))
    (builder or BuildxImageBuilder()).build(spec, network=network, platform=platform)
