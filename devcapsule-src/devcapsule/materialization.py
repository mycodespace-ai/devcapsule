"""Host-side acquisition and home-local component materialization."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import base64
import binascii
import tarfile
from typing import Any, Callable, Iterator, Mapping
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from devcapsule.compat import CliError
from devcapsule.runtime_command import RuntimeCommand
from devcapsule.build_info import read_pex_build_info
from devcapsule.platforms import XdgHomes
from devcapsule.components.catalog import (
    ComponentCatalogError,
    selected_component_definitions,
)
from devcapsule.components import LockedArtifactDeclaration
from devcapsule.components.directory_artifacts import extract_tar_directory
from devcapsule.components.browser_artifacts import extract_zip, wheel_install_step, wheel_name
from devcapsule.components.catalog import INTERACTIVE_SURFACES
from devcapsule.images.build import (
    CommandComponent,
    ContributionComponent,
    DirectoryComponent,
    EntrypointComponent,
    EnvComponent,
    ExecComponent,
    FileComponent,
    ImageBuildSpec,
    LabelComponent,
    normalize_archive_directory,
    shell_quote,
)
from devcapsule.images.metadata import (
    BASE_KIND,
    CANONICAL_NAME_LABEL,
    IMAGE_KIND_LABEL,
    MANAGED_LABEL,
    MATERIALIZED_KIND,
    METADATA_VERSION,
    METADATA_VERSION_LABEL,
    managed_labels,
)

__all__ = [
    "ARTIFACT_FORMATS",
    "Acquisition",
    "ArtifactSpec",
    "ArtifactUnavailable",
    "COMPONENT_TEMPLATE_PATH",
    "ENTRYPOINT_CONTRACT",
    "FORMATION_SCHEMA_NAME",
    "FORMATION_SCHEMA_VERSION",
    "ImageDetails",
    "LockedEnvironment",
    "MATERIALIZATION_RECIPE_ID",
    "MATERIALIZATION_RECIPE_VERSION",
    "NPM_CACHE_PATH",
    "NPM_INSTALL_OPTIONS",
    "NpmProject",
    "RUNTIME_COMMAND_PATH",
    "RUNTIME_PLAN_PATH",
    "SURFACE_MATERIALIZATIONS",
    "SurfaceMaterialization",
    "UNPACKED_DIRECTORY",
    "UNPACKED_MARKER",
    "acquire_artifact",
    "cache_root",
    "canonical_image_name",
    "canonical_json",
    "component_runtime_template",
    "descriptor_differences",
    "ensure_materialized_surface",
    "formation_descriptor",
    "formation_identity",
    "npm_install_step",
    "parse_locked_environment",
    "runtime_config_drift",
    "runtime_enforcement_spec",
    "sha256_file",
    "surface_materialization_spec",
    "surface_profile",
    "unpacked_tree",
    "validate_base_image",
    "validate_locked_artifact",
    "verify_materialized_image",
]


@dataclass(frozen=True)
class ArtifactSpec:
    version: str
    url: str
    sha256: str
    # Surfaces without a lock-recorded variant (VSCodium) carry None; the
    # ancillary-acquisition path reuses this field as a cache discriminator.
    variant: str | None = "professional"
    integrity: str | None = None


@dataclass(frozen=True)
class Acquisition:
    path: Path
    downloaded: bool


@dataclass(frozen=True)
class ImageDetails:
    reference: str
    identity: str
    labels: Mapping[str, str]
    operating_system: str
    architecture: str
    # The image's actual boot configuration and size; () / 0 when the caller
    # has no daemon answer (e.g. synthetic details in tests). Verification
    # compares the boot configuration against the descriptor's claim.
    entrypoint: tuple[str, ...] = ()
    command: tuple[str, ...] = ()
    size_bytes: int = 0


@dataclass(frozen=True)
class LockedEnvironment:
    platform: str
    base_reference: str
    base_identity: str | None
    component_id: str
    artifact: ArtifactSpec
    ancillary_artifacts: tuple[LockedArtifactDeclaration, ...]
    recipe_id: str
    recipe_version: str


FORMATION_SCHEMA_NAME = "devcapsule-formation"
FORMATION_SCHEMA_VERSION = 1
MATERIALIZATION_RECIPE_ID = "jetbrains-local-materialization"
MATERIALIZATION_RECIPE_VERSION = "1"


@dataclass(frozen=True)
class SurfaceMaterialization:
    """One interactive surface's archive-to-image materialization contract."""

    component_id: str
    family: str
    recipe_id: str
    # Versions advance per recipe when a recipe's steps change; a lock made
    # against an older recipe fails loudly instead of building an image the
    # recorded version no longer describes.
    recipe_version: str
    installation_path: str
    # Relative paths that must exist in the unpacked archive before it is
    # trusted as this surface's installation.
    archive_probes: tuple[str, ...]
    # PyCharm locks record an edition variant; other surfaces do not.
    requires_variant: bool
    # Root-run build steps after the installation directory is copied in.
    post_install: tuple[ExecComponent, ...]


SURFACE_MATERIALIZATIONS: dict[str, SurfaceMaterialization] = {
    "eclipse": SurfaceMaterialization(
        component_id="eclipse", family="eclipse",
        recipe_id="eclipse-local-materialization", recipe_version="3",
        installation_path="/opt/eclipse",
        archive_probes=("eclipse", "eclipse.ini", "configuration/config.ini"),
        requires_variant=True, post_install=(),
    ),
    "rider": SurfaceMaterialization(
        component_id="rider", family="jetbrains",
        recipe_id=MATERIALIZATION_RECIPE_ID, recipe_version=MATERIALIZATION_RECIPE_VERSION,
        installation_path="/opt/jetbrains/rider", archive_probes=("bin/rider.sh",),
        requires_variant=False, post_install=(),
    ),
    "intellij": SurfaceMaterialization(
        component_id="intellij", family="jetbrains",
        recipe_id=MATERIALIZATION_RECIPE_ID, recipe_version=MATERIALIZATION_RECIPE_VERSION,
        installation_path="/opt/jetbrains/intellij", archive_probes=("bin/idea.sh",),
        requires_variant=True, post_install=(),
    ),
    "pycharm": SurfaceMaterialization(
        component_id="pycharm",
        family="jetbrains",
        recipe_id=MATERIALIZATION_RECIPE_ID,
        recipe_version=MATERIALIZATION_RECIPE_VERSION,
        installation_path="/opt/jetbrains/pycharm",
        archive_probes=("bin/pycharm.sh",),
        requires_variant=True,
        post_install=(),
    ),
    "codium": SurfaceMaterialization(
        component_id="codium",
        family="vscode",
        recipe_id="vscode-local-materialization",
        # Version 2 (product-owner ruling 2026-09-02): the version-1 step
        # marking chrome-sandbox root-owned mode 4755 is removed — renderers
        # run --no-sandbox, so canonical images carry no setuid-root binary;
        # see engineering-docs/design-notes/devcapsule/renderer-sandboxing.md.
        recipe_version="2",
        installation_path="/opt/codium",
        archive_probes=("codium", "bin/codium", "chrome-sandbox"),
        requires_variant=False,
        post_install=(),
    ),
    "vscode": SurfaceMaterialization(
        component_id="vscode",
        family="vscode",
        recipe_id="vscode-local-materialization",
        recipe_version="2",
        installation_path="/opt/vscode",
        archive_probes=("code", "bin/code", "chrome-sandbox"),
        requires_variant=False,
        post_install=(),
    ),
}
COMPONENT_TEMPLATE_PATH = "/etc/devcapsule/component-runtime-template.json"
RUNTIME_PLAN_PATH = "/etc/devcapsule/runtime-plan.json"
RUNTIME_COMMAND_PATH = "/usr/local/bin/devcapsule"
ENTRYPOINT_CONTRACT = (
    "/opt/devcapsule/bin/devcapsule.pex",
    "runtime",
)


UNPACKED_DIRECTORY = "unpacked"
UNPACKED_MARKER = ".devcapsule-unpacked.json"


def unpacked_tree(cache_root: Path, sha256: str, unpack: Callable[[Path], Path]) -> Path:
    """Return the cached installation tree of an already verified archive.

    ``sha256`` identifies the archive. Callers of the same key must use the
    same extraction layout. ``unpack`` receives a nonexistent destination
    and returns an existing directory inside it. Its exceptions propagate.

    A per-digest lock covers inspection, recovery, extraction and publication,
    including cache hits: no caller may remove another's completed tree after
    observing an earlier miss. The marker is written last, then the directory
    is renamed into place. A failed extraction is cleaned up; an abrupt exit
    leaves a fixed staging path that the next caller recovers under the lock.
    Completed trees stay at stable paths and are treated as immutable by users
    of this cache. Marker validation checks structure, not file-content hashes.
    """
    sha256 = _validated_sha256(sha256, "Unpacked archive SHA-256")
    home = cache_root / UNPACKED_DIRECTORY / sha256
    marker = home / UNPACKED_MARKER
    with _exclusive_lock(cache_root / "locks" / "unpacked" / f"{sha256}.lock"):
        recorded = _unpacked_root(marker, sha256)
        if recorded is not None:
            return home / recorded
        _remove_unpacked_entry(home)
        partial = home.with_name(f"{home.name}.partial")
        _remove_unpacked_entry(partial)
        # Extractors create the destination themselves; prepare only its parent.
        partial.parent.mkdir(parents=True, exist_ok=True)
        try:
            root = unpack(partial)
            relative = root.relative_to(partial).as_posix()
            (partial / UNPACKED_MARKER).write_text(
                json.dumps({"schema_version": 1, "sha256": sha256, "root": relative}) + "\n",
                encoding="utf-8",
            )
            if _unpacked_root(partial / UNPACKED_MARKER, sha256) is None:
                raise CliError("Archive extractor did not return a directory inside its destination.")
            partial.rename(home)
        finally:
            _remove_unpacked_entry(partial)
        return home / relative


def _remove_unpacked_entry(path: Path) -> None:
    """Remove an owned cache entry without traversing a replaced root symlink."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _unpacked_root(marker: Path, sha256: str) -> str | None:
    """Read a supported completion record whose root still exists inside the entry."""
    try:
        if marker.parent.is_symlink():
            return None
        document = json.loads(marker.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("schema_version") != 1 or document.get("sha256") != sha256:
            return None
        root = document["root"]
        if not isinstance(root, str) or not root or Path(root).is_absolute() or ".." in Path(root).parts:
            return None
        directory = marker.parent / root
        if not directory.is_dir() or not directory.resolve().is_relative_to(marker.parent.resolve()):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return root


def cache_root(env: Mapping[str, str] | None = None) -> Path:
    return XdgHomes.from_environment(env).cache


class ArtifactUnavailable(CliError):
    """A pinned URL could not be reached; integrity failures are a different error."""
    def __init__(self, url: str, reason: object) -> None:
        self.url = url
        super().__init__(f"Cannot download locked artifact {url!r}: {reason}")


def acquire_artifact(spec: ArtifactSpec, root: Path) -> Acquisition:
    algorithm = "sha256"
    expected = spec.sha256
    if not expected and spec.integrity is not None:
        try:
            prefix, encoded = spec.integrity.split("-", 1)
            decoded = base64.b64decode(encoded, validate=True)
            if prefix != "sha512" or len(decoded) != 64:
                raise ValueError("requires SHA-512")
            algorithm, expected = "sha512", decoded.hex()
        except (ValueError, binascii.Error) as exc:
            raise CliError("Invalid artifact integrity; expected SHA-512 SRI.") from exc
    else:
        expected = _validated_sha256(expected, "Artifact SHA-256")
    destination = root / "artifacts" / algorithm / expected
    lock = root / "locks" / "artifacts" / f"{expected}.lock"
    with _exclusive_lock(lock):
        if destination.is_file():
            if _file_digest(destination, algorithm) == expected:
                return Acquisition(destination, False)
            destination.unlink()

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        digest = hashlib.new(algorithm)
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{destination.name}.", suffix=".download", dir=destination.parent, delete=False
            ) as output:
                temporary_path = Path(output.name)
                with urlopen(spec.url, timeout=60) as response:  # noqa: S310 - project-lock-pinned URL
                    while chunk := response.read(1024 * 1024):
                        digest.update(chunk)
                        output.write(chunk)
            actual = digest.hexdigest()
            if actual != expected:
                raise CliError(f"Artifact digest mismatch: expected {expected}, received {actual}.")
            temporary_path.replace(destination)
        except URLError as exc:
            raise ArtifactUnavailable(spec.url, exc) from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return Acquisition(destination, True)


def _file_digest(path: Path, algorithm: str) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Mapping[str, Any]) -> str:
    """Serialize the JSON-native formation schema canonically for V1."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def surface_profile(component_id: str) -> SurfaceMaterialization:
    profile = SURFACE_MATERIALIZATIONS.get(component_id)
    if profile is None:
        supported = ", ".join(sorted(SURFACE_MATERIALIZATIONS))
        raise CliError(
            f"V1 environment materialization supports no interactive surface "
            f"{component_id!r}; supported surfaces: {supported}."
        )
    return profile


def component_runtime_template(component_id: str = "pycharm") -> dict[str, Any]:
    """Return formation-owned component data without checkout/runtime choices."""

    definition = INTERACTIVE_SURFACES.get(component_id)
    if definition is None:
        raise CliError(f"No interactive surface component {component_id!r} is in the catalog.")
    return definition.runtime_template().to_mapping()


def formation_descriptor(
    *,
    platform: str,
    base_identity: str,
    artifact: ArtifactSpec,
    ancillary_artifacts: tuple[LockedArtifactDeclaration, ...] = (),
    recipe_id: str = MATERIALIZATION_RECIPE_ID,
    recipe_version: str = MATERIALIZATION_RECIPE_VERSION,
    component_id: str = "pycharm",
    runtime_sha256: str | None = None,
    runtime_command: RuntimeCommand = RuntimeCommand.STANDARD,
) -> dict[str, Any]:
    operating_system, architecture = _split_platform(platform)
    profile = surface_profile(component_id)
    template_digest = hashlib.sha256(
        canonical_json(component_runtime_template(component_id)).encode()
    ).hexdigest()
    return {
        "schema": {"name": FORMATION_SCHEMA_NAME, "version": FORMATION_SCHEMA_VERSION},
        "platform": {"os": operating_system, "architecture": architecture},
        "base": {"identity": base_identity},
        "components": [
            {
                "id": component_id,
                "version": artifact.version,
                "artifact": {"sha256": _validated_sha256(artifact.sha256, "Artifact SHA-256")},
                # Only variant-carrying surfaces record one, keeping earlier
                # PyCharm formation identities byte-stable.
                **({"variant": artifact.variant} if artifact.variant is not None else {}),
            },
            *[
                {
                    "id": item.component_id,
                    "version": item.version,
                    "artifact": {
                        "sha256": _validated_sha256(
                            item.sha256, f"{item.component_id} artifact SHA-256"
                        )
                    },
                    "installation": {
                        "format": item.artifact_format,
                        "destination": item.destination,
                        **(
                            {"archive-member": item.archive_member}
                            if item.archive_member is not None
                            else {}
                        ),
                        **(
                            {"npm-package": item.npm_package}
                            if item.npm_package is not None
                            else {}
                        ),
                    },
                }
                for item in ancillary_artifacts
            ],
        ],
        "recipe": {
            "id": recipe_id,
            "version": recipe_version,
            "parameters": {"installation-path": profile.installation_path},
        },
        "runtime": {
            "xtras-layout": "home-symlink-v1",
            # The public command is part of image identity: a cached image with
            # the same PEX but without its command link cannot satisfy this plan.
            **({"pex-sha256": _validated_sha256(runtime_sha256, "Runtime PEX SHA-256"),
                "public-command": f"/usr/local/bin/{runtime_command}"}
               if runtime_sha256 is not None else {}),
            "component-template-sha256": template_digest,
            "entrypoint": list(ENTRYPOINT_CONTRACT),
            "command": [RUNTIME_PLAN_PATH],
        },
    }


def formation_identity(descriptor: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(descriptor).encode()).hexdigest()


def canonical_image_name(descriptor: Mapping[str, Any], component_id: str = "pycharm") -> str:
    return f"devcapsule-local-{component_id}:{formation_identity(descriptor)[:20]}"


def validate_locked_artifact(locked_artifact: LockedArtifactDeclaration) -> None:
    """Validate one component artifact without acquisition or filesystem effects."""
    _validated_sha256(
        locked_artifact.sha256,
        f"Locked {locked_artifact.component_id} artifact SHA-256",
    )
    if locked_artifact.artifact_format not in ARTIFACT_FORMATS:
        raise CliError(
            f"Locked {locked_artifact.component_id} artifact format must be one of "
            + ", ".join(repr(name) for name in ARTIFACT_FORMATS)
            + "."
        )
    if (
        locked_artifact.artifact_format == "tar-gz-member"
        and not locked_artifact.archive_member
    ):
        raise CliError(
            f"Locked {locked_artifact.component_id} tar-gz-member artifact must name "
            "an archive member."
        )
    if locked_artifact.artifact_format == "python-wheel":
        wheel_name(locked_artifact.url)
    if locked_artifact.artifact_format == "npm-package":
        if not locked_artifact.npm_package:
            raise CliError(
                f"Locked {locked_artifact.component_id} npm-package artifact must "
                "name its npm package."
            )
        # Fail at lock-reading time, not mid-build, when the URL
        # cannot name the tarball inside the image.
        _npm_tarball_name(locked_artifact)
    if not Path(locked_artifact.destination).is_absolute():
        raise CliError(
            f"Locked {locked_artifact.component_id} destination must be absolute."
        )


def parse_locked_environment(lock: Mapping[str, Any]) -> LockedEnvironment:
    platform = _required_string(lock, "platform", "platform lock")
    base = _required_mapping(lock, "base", "platform lock")
    components = _required_mapping(lock, "components", "platform lock")
    component_id = _required_string(components, "interactive-surface", "components")
    profile = surface_profile(component_id)
    component = _required_mapping(components, component_id, "components")
    try:
        _interactive, ancillary_definitions = selected_component_definitions(lock)
    except ComponentCatalogError as exc:
        raise CliError(str(exc)) from exc
    materialization = _required_mapping(lock, "materialization", "platform lock")
    policy = _required_string(component, "delivery-policy", f"components.{component_id}")
    if policy != "local-materialization":
        raise CliError(
            f"Locked {component_id} delivery-policy must be 'local-materialization'."
        )
    artifact = ArtifactSpec(
        version=_required_string(component, "version", f"components.{component_id}"),
        url=_required_string(component, "url", f"components.{component_id}"),
        sha256=_required_string(component, "sha256", f"components.{component_id}"),
        variant=(
            _required_string(component, "variant", f"components.{component_id}")
            if profile.requires_variant
            else None
        ),
    )
    _validated_sha256(artifact.sha256, "Locked component SHA-256")
    ancillary_artifacts: list[LockedArtifactDeclaration] = []
    for definition in (_interactive, *ancillary_definitions):
        metadata = _required_mapping(components, definition.id, "components")
        for locked_artifact in definition.locked_artifacts(metadata, platform):
            validate_locked_artifact(locked_artifact)
            ancillary_artifacts.append(locked_artifact)
    recipe_id = _required_string(materialization, "recipe", "materialization")
    recipe_version = _required_string(materialization, "recipe-version", "materialization")
    if recipe_id != profile.recipe_id or recipe_version != profile.recipe_version:
        raise CliError(
            f"Unsupported materialization recipe {recipe_id!r}@{recipe_version}; "
            f"the {component_id} surface expects "
            f"{profile.recipe_id!r}@{profile.recipe_version}."
        )
    identity_value = base.get("identity")
    if identity_value is not None and not isinstance(identity_value, str):
        raise CliError("platform lock base.identity must be a string when present.")
    return LockedEnvironment(
        platform=platform,
        base_reference=_required_string(base, "reference", "base"),
        base_identity=identity_value,
        component_id=component_id,
        artifact=artifact,
        ancillary_artifacts=tuple(ancillary_artifacts),
        recipe_id=recipe_id,
        recipe_version=recipe_version,
    )


def validate_base_image(
    details: ImageDetails,
    *,
    platform: str,
    expected_identity: str | None,
) -> None:
    operating_system, architecture = _split_platform(platform)
    if (details.operating_system, details.architecture) != (operating_system, architecture):
        raise CliError(
            f"Selected base {details.reference!r} is {details.operating_system}-{details.architecture}, "
            f"but the lock targets {platform}."
        )
    labels = details.labels
    if (
        labels.get(MANAGED_LABEL) != "true"
        or labels.get(METADATA_VERSION_LABEL) != METADATA_VERSION
        or labels.get(IMAGE_KIND_LABEL) != BASE_KIND
    ):
        raise CliError(
            f"Selected base {details.reference!r} is not a DevCapsule metadata-v1 base image."
        )
    if expected_identity is not None and details.identity != expected_identity:
        raise CliError(
            f"Selected base identity mismatch: expected {expected_identity}, received {details.identity}."
        )


def surface_materialization_spec(
    *,
    base_reference: str,
    base_identity: str,
    image: str,
    surface_root: Path,
    component_template: Path,
    artifact: ArtifactSpec,
    ancillary_files: tuple[tuple[Path, LockedArtifactDeclaration], ...] = (),
    npm_projects: tuple[NpmProject, ...] = (),
    native_package_directory: Path | None = None,
    platform: str,
    recipe_id: str = MATERIALIZATION_RECIPE_ID,
    recipe_version: str = MATERIALIZATION_RECIPE_VERSION,
    component_id: str = "pycharm",
    runtime_pex: Path | None = None,
    runtime_command: RuntimeCommand = RuntimeCommand.STANDARD,
) -> ImageBuildSpec:
    profile = surface_profile(component_id)
    descriptor = formation_descriptor(
        platform=platform,
        base_identity=base_identity,
        artifact=artifact,
        ancillary_artifacts=tuple(declaration for _path, declaration in ancillary_files),
        recipe_id=recipe_id,
        recipe_version=recipe_version,
        component_id=component_id,
        runtime_sha256=sha256_file(runtime_pex) if runtime_pex is not None else None,
        runtime_command=runtime_command,
    )
    identity = formation_identity(descriptor)
    environment = _ancillary_environment(
        tuple(declaration for _path, declaration in ancillary_files)
    )
    runtime_labels: tuple[tuple[str, str], ...] = ()
    if runtime_pex is not None:
        info = read_pex_build_info(runtime_pex)
        runtime_labels = (
            ("devcapsule.pex.sha256", descriptor["runtime"]["pex-sha256"]),
            ("devcapsule.pex.build-mnemonic", info.build_mnemonic),
            ("devcapsule.source.repository", info.source_repository),
            ("devcapsule.source.revision", info.source_revision),
            ("devcapsule.source.url", info.source_url),
            ("org.opencontainers.image.source", info.source_repository),
            ("org.opencontainers.image.revision", info.source_revision),
            ("org.opencontainers.image.version", info.build_mnemonic),
        )
    return ImageBuildSpec(
        image=image,
        base_image=base_reference,
        components=(
            ContributionComponent(
                component_id,
                (DirectoryComponent(surface_root, profile.installation_path), *profile.post_install),
                (profile.installation_path,),
            ),
            FileComponent(component_template, COMPONENT_TEMPLATE_PATH, permissions=0o644),
            *_native_package_components(ancillary_files, native_package_directory),
            *_ancillary_contributions(ancillary_files, npm_projects),
            # The image supplies the alias; the runtime creates its writable
            # target in the persistent home as the capsule user. Never replace
            # pre-existing content in a custom base to establish this mapping.
            ExecComponent(("sh", "-ec",
                'if [ -e /opt/xtras ] || [ -L /opt/xtras ]; then '
                '[ "$(readlink /opt/xtras)" = /home/devcapsule/xtras ] || '
                '{ echo "Cannot reserve /opt/xtras: base contains another path" >&2; exit 1; }; '
                'else ln -s /home/devcapsule/xtras /opt/xtras; fi; '
                'mkdir -p /etc/profile.d; '
                "printf '%s\\n' 'export PATH=\"/opt/xtras/bin:$PATH\"' "
                '> /etc/profile.d/devcapsule-xtras.sh')),
            # Keep the shipped executable available to ordinary shells/scripts.
            # Development checkouts reserve 'devcapsule' for their source build;
            # clear only our canonical link if their base inherited one.
            *((ExecComponent(("sh", "-c",
                f'if [ "$(readlink {shell_quote(RUNTIME_COMMAND_PATH)})" = '
                f'{shell_quote(ENTRYPOINT_CONTRACT[0])} ]; then '
                f'rm -f {shell_quote(RUNTIME_COMMAND_PATH)}; fi')),)
              if runtime_pex is not None and runtime_command is RuntimeCommand.DEVELOPMENT else ()),
            *((FileComponent(runtime_pex, ENTRYPOINT_CONTRACT[0], permissions=0o755),
               ExecComponent(("ln", "-sfn", ENTRYPOINT_CONTRACT[0], descriptor["runtime"]["public-command"])))
              if runtime_pex is not None else ()),
            *( (EnvComponent(environment),) if environment else () ),
            EnvComponent((("PATH", "/opt/xtras/bin:${PATH}"),)),
            LabelComponent(
                managed_labels(MATERIALIZED_KIND, image)
                + runtime_labels
                + (
                    ("devcapsule.materialization.descriptor", canonical_json(descriptor)),
                    ("devcapsule.materialization.identity", identity),
                    ("devcapsule.materialization.recipe-version", recipe_version),
                    ("devcapsule.materialization.base-identity", base_identity),
                    ("devcapsule.component.id", component_id),
                    ("devcapsule.component.version", artifact.version),
                    *(
                        (("devcapsule.component.variant", artifact.variant),)
                        if artifact.variant is not None
                        else ()
                    ),
                    ("devcapsule.component.sha256", artifact.sha256.lower()),
                    (f"devcapsule.component.{profile.family}.version", artifact.version),
                    (f"devcapsule.component.{profile.family}.sha256", artifact.sha256.lower()),
                )
            ),
            # The recipe enforces the descriptor's boot contract (owner ruling
            # 2026-09-05): a derived image's ENTRYPOINT/CMD override the
            # base's, so the claim is true on every base, tini-wrapped v026
            # included.
            EntrypointComponent(tuple(descriptor["runtime"]["entrypoint"])),
            CommandComponent(tuple(descriptor["runtime"]["command"])),
        ),
    )


def runtime_enforcement_spec(
    *,
    image: str,
    source_reference: str,
    descriptor: Mapping[str, Any],
) -> ImageBuildSpec:
    """A boot-configuration-only rebuild of an existing formation image.

    Building FROM the source with no other components reuses every layer and
    touches only the image configuration — the owner's 2026-09-05 ruling that
    an entrypoint-only rebuild must be almost a no-op. The source is a tag
    (BuildKit cannot address a local image by ID); callers must hold a lock
    that keeps the tag from moving between inspection and this rebuild.
    """

    runtime = descriptor["runtime"]
    return ImageBuildSpec(
        image=image,
        base_image=source_reference,
        components=(
            EntrypointComponent(tuple(runtime["entrypoint"])),
            CommandComponent(tuple(runtime["command"])),
        ),
    )


def ensure_materialized_surface(
    *,
    base_reference: str,
    base_identity: str,
    platform: str,
    artifact: ArtifactSpec,
    ancillary_artifacts: tuple[LockedArtifactDeclaration, ...] = (),
    cache_root: Path,
    inspect_image: Callable[[str], ImageDetails | None],
    build: Callable[[ImageBuildSpec], None],
    recipe_id: str = MATERIALIZATION_RECIPE_ID,
    recipe_version: str = MATERIALIZATION_RECIPE_VERSION,
    component_id: str = "pycharm",
    report: Callable[[str], None] | None = None,
    list_formations: Callable[[], tuple[ImageDetails, ...]] | None = None,
    runtime_pex: Path | None = None,
    runtime_command: RuntimeCommand = RuntimeCommand.STANDARD,
) -> tuple[str, bool]:
    profile = surface_profile(component_id)
    descriptor = formation_descriptor(
        platform=platform,
        base_identity=base_identity,
        artifact=artifact,
        ancillary_artifacts=ancillary_artifacts,
        recipe_id=recipe_id,
        recipe_version=recipe_version,
        component_id=component_id,
        runtime_sha256=sha256_file(runtime_pex) if runtime_pex is not None else None,
        runtime_command=runtime_command,
    )
    image = canonical_image_name(descriptor, component_id)
    identity = formation_identity(descriptor)
    say = report or (lambda _message: None)
    with _exclusive_lock(cache_root / "locks" / "materializations" / f"{identity}.lock"):
        existing = inspect_image(image)
        if existing is not None:
            _verify_materialized_labels(existing, descriptor=descriptor, canonical_name=image)
            drift = runtime_config_drift(existing, descriptor)
            if not drift:
                return image, False
            # The record is right and the image content is right; only the
            # boot configuration predates enforcement. Repair in place with a
            # configuration-only build (owner ruling 2026-09-05) instead of
            # refusing or rebuilding gigabytes.
            say(
                "Enforcing the recorded boot contract on the existing formation "
                f"(configuration-only rebuild): {'; '.join(drift)}"
            )
            # FROM the canonical tag: the materialization lock held here
            # keeps it from moving between the inspection above and this
            # rebuild, and the rebuild then re-tags it.
            build(
                runtime_enforcement_spec(
                    image=image, source_reference=image, descriptor=descriptor
                )
            )
            repaired = inspect_image(image)
            if repaired is None:
                raise CliError(
                    f"Boot-contract enforcement did not produce canonical image {image!r}."
                )
            verify_materialized_image(repaired, descriptor=descriptor, canonical_name=image)
            return image, False

        _explain_materialization(say, descriptor, image, component_id, list_formations)
        acquisition = acquire_artifact(artifact, cache_root)
        ancillary_acquisitions = tuple(
            (
                acquire_artifact(
                    ArtifactSpec(item.version, item.url, item.sha256, item.component_id),
                    cache_root,
                ),
                item,
            )
            for item in ancillary_artifacts
        )
        work_root = cache_root / "work"
        work_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="devcapsule-materialize-", dir=work_root) as temporary_value:
            temporary = Path(temporary_value)
            try:
                surface_root = unpacked_tree(
                    cache_root, artifact.sha256,
                    lambda destination: normalize_archive_directory(acquisition.path, destination),
                )
            except OSError as exc:
                raise CliError(
                    f"Cannot unpack the verified {component_id} archive beneath "
                    f"{cache_root / UNPACKED_DIRECTORY}: {exc}"
                ) from exc
            for probe in profile.archive_probes:
                if not (surface_root / probe).is_file():
                    raise CliError(
                        f"The verified {component_id} archive does not contain {probe}."
                    )
            template_path = temporary / "component-runtime-template.json"
            template_path.write_text(
                canonical_json(component_runtime_template(component_id)) + "\n", encoding="utf-8"
            )
            ancillary_files = tuple(
                (
                    _prepare_locked_artifact(
                        acquired.path,
                        declaration,
                        temporary / f"{declaration.component_id}-{index}",
                        cache_root=cache_root,
                    ),
                    declaration,
                )
                for index, (acquired, declaration) in enumerate(ancillary_acquisitions)
            )
            npm_projects = _npm_projects(ancillary_files, temporary)
            native_packages = _prepare_native_packages(ancillary_files, temporary / "native-packages")
            build(
                surface_materialization_spec(
                    base_reference=base_reference,
                    base_identity=base_identity,
                    image=image,
                    surface_root=surface_root,
                    component_template=template_path,
                    artifact=artifact,
                    ancillary_files=ancillary_files,
                    npm_projects=npm_projects,
                    native_package_directory=native_packages,
                    platform=platform,
                    recipe_id=recipe_id,
                    recipe_version=recipe_version,
                    component_id=component_id,
                    runtime_pex=runtime_pex,
                    runtime_command=runtime_command,
                )
            )
        completed = inspect_image(image)
        if completed is None:
            raise CliError(f"Docker build completed without creating canonical image {image!r}.")
        verify_materialized_image(completed, descriptor=descriptor, canonical_name=image)
        _report_prior_formations(say, image, component_id, list_formations)
        return image, True


def _stored_descriptor(details: ImageDetails) -> Mapping[str, Any] | None:
    try:
        parsed = json.loads(details.labels.get("devcapsule.materialization.descriptor", ""))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _explain_materialization(
    say: Callable[[str], None],
    descriptor: Mapping[str, Any],
    image: str,
    component_id: str,
    list_formations: Callable[[], tuple[ImageDetails, ...]] | None,
) -> None:
    """Say why materialization is about to run: first formation, or which
    descriptor fields differ from the nearest existing one — so identity
    churn is visible the day it ships, not months later."""

    if list_formations is None:
        return
    nearest: tuple[int, str, tuple[str, ...]] | None = None
    for candidate in list_formations():
        stored = _stored_descriptor(candidate)
        if stored is None:
            continue
        differences = descriptor_differences(descriptor, stored)
        if nearest is None or len(differences) < nearest[0]:
            nearest = (len(differences), candidate.reference, differences)
    if nearest is None:
        say(f"Materializing {image}: first {component_id} formation on this host.")
        return
    _count, reference, differences = nearest
    named = ", ".join(differences[:6]) + (" …" if len(differences) > 6 else "")
    say(f"Materializing {image}: differs from {reference} in {named}.")


def _report_prior_formations(
    say: Callable[[str], None],
    image: str,
    component_id: str,
    list_formations: Callable[[], tuple[ImageDetails, ...]] | None,
) -> None:
    """Name the prior formation images that remain after a build.

    Reporting is the ruled minimum for the superseded-image lifecycle (the
    2026-09-02 formation-identity record); whether they are reaped or get a
    cleanup verb is an open owner decision. A prior formation may still be
    current for another checkout sharing the surface, so this names rather
    than judges.
    """

    if list_formations is None:
        return
    prior = [details for details in list_formations() if details.reference != image]
    if not prior:
        return
    total = sum(details.size_bytes for details in prior)
    names = ", ".join(sorted(details.reference for details in prior))
    size_note = f" ({total / 1e9:.1f} GB total)" if total else ""
    say(
        f"Prior {component_id} formation images remain{size_note}: {names}. "
        "DevCapsule does not reap superseded canonical images yet."
    )


def _extract_archive_member(archive: Path, member_name: str, destination: Path) -> Path:
    """Extract exactly one regular file from a verified tar archive."""

    try:
        with tarfile.open(archive, mode="r:gz") as package:
            try:
                member = package.getmember(member_name)
            except KeyError as exc:
                raise CliError(
                    f"Verified component artifact does not contain {member_name!r}."
                ) from exc
            if not member.isfile() or member.size <= 0 or member.size > 1024**3:
                raise CliError(f"Locked archive member {member_name!r} is not a regular executable file.")
            source = package.extractfile(member)
            if source is None:
                raise CliError(f"Cannot read locked archive member {member_name!r}.")
            with source, destination.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
    except tarfile.TarError as exc:
        raise CliError(f"Cannot read verified component archive {archive}: {exc}") from exc
    destination.chmod(0o700)
    return destination


def _prepare_locked_artifact(
    acquired: Path,
    declaration: LockedArtifactDeclaration,
    destination: Path,
    *,
    cache_root: Path,
) -> Path:
    # Directory artifacts (IDE trees, browsers) are the large ones; they are
    # unpacked once under the cache by digest, like the surface archive.
    if declaration.artifact_format == "tar-gz-directory":
        return unpacked_tree(cache_root, declaration.sha256,
                             lambda tree: extract_tar_directory(acquired, tree))
    if declaration.artifact_format == "zip-directory":
        return unpacked_tree(cache_root, declaration.sha256,
                             lambda tree: extract_zip(acquired, tree))
    if declaration.artifact_format in {"file", "python-wheel"}:
        shutil.copyfile(acquired, destination)
        destination.chmod(0o700)
        return destination
    if declaration.artifact_format == "tar-gz-member" and declaration.archive_member is not None:
        return _extract_archive_member(acquired, declaration.archive_member, destination)
    if declaration.artifact_format in {"npm-package", "deb-package"}:
        # The verified tarball travels whole; npm unpacks it inside the build.
        shutil.copyfile(acquired, destination)
        destination.chmod(0o600)
        return destination
    raise CliError(
        f"Unsupported locked artifact format {declaration.artifact_format!r} for "
        f"{declaration.component_id}."
    )


# --------------------------------------------------------------------------
# npm-delivered components. The verified tarballs are copied into the
# destination directory next to a generated package.json that names each one
# as a `file:` dependency, and one offline `npm install` lays the tree out
# exactly as the vendor's own npm distribution does — launcher, platform
# package, and the helpers the binary resolves beside itself. Nothing is
# fetched during the build; npm only verifies and unpacks what the host
# already checksummed. The tarballs stay beside the manifest so the recorded
# package-lock.json keeps describing an install npm could repeat.

ARTIFACT_FORMATS = ("file", "tar-gz-member", "npm-package", "python-wheel", "zip-directory", "tar-gz-directory", "deb-package")
# Root-run inside the build; node and npm come from the base image. The cache
# is pointed at a scratch path and removed in the same step and log files
# are disabled, so no layer carries npm's working state; scripts are refused
# because the lock verifies tarballs, not code they might run at install
# time.
NPM_CACHE_PATH = "/tmp/devcapsule-npm-cache"
NPM_INSTALL_OPTIONS = (
    "install",
    "--offline",
    "--ignore-scripts",
    "--no-audit",
    "--no-fund",
    "--no-update-notifier",
    "--loglevel=error",
    "--logs-max=0",
)
_NPM_TARBALL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.(tgz|tar\.gz)")


@dataclass(frozen=True)
class NpmProject:
    """One npm install directory inside the image and its generated manifest."""

    component_id: str
    destination: str
    package_json: Path


def _ancillary_contributions(
    files: tuple[tuple[Path, LockedArtifactDeclaration], ...],
    projects: tuple[NpmProject, ...],
) -> tuple[ContributionComponent, ...]:
    files = tuple((path, item) for path, item in files if item.artifact_format != "deb-package")
    contributions = []
    for component_id in sorted({item.component_id for _path, item in files}):
        selected = [(path, item) for path, item in files if item.component_id == component_id]
        npm = [project for project in projects if project.component_id == component_id]
        wheel_destinations = sorted({item.destination for _path, item in selected if item.artifact_format == "python-wheel"})
        destinations = sorted({item.destination for _path, item in selected})
        # A parent export already includes nested browser directories. Copying
        # them again would retain duplicate payloads in the final image layers.
        exports = tuple(destination for destination in destinations
                        if not any(destination != parent and Path(destination).is_relative_to(parent)
                                   for parent in destinations))
        contributions.append(ContributionComponent(
            component_id,
            (
                *((DirectoryComponent(path, item.destination) if item.artifact_format in {"zip-directory", "tar-gz-directory"}
                   else FileComponent(path, _artifact_image_path(item), permissions=item.permissions))
                  for path, item in selected),
                *(ExecComponent(wheel_install_step(destination, tuple(wheel_name(item.url)
                    for _path, item in selected if item.artifact_format == "python-wheel" and item.destination == destination)))
                  for destination in wheel_destinations),
                *(FileComponent(project.package_json, f"{project.destination}/package.json", permissions=0o644)
                  for project in npm),
                *(ExecComponent(npm_install_step(project.destination)) for project in npm),
            ),
            exports,
        ))
    return tuple(contributions)


def _native_package_components(
    files: tuple[tuple[Path, LockedArtifactDeclaration], ...],
    directory: Path | None,
) -> tuple[DirectoryComponent | ExecComponent, ...]:
    """Install checksummed distribution packages in the final image, offline.

    dpkg executes the selected distribution's maintainer scripts, just as apt
    would. Dependencies must all be pinned or already supplied by the base;
    missing dependencies fail the build rather than downloading anything.
    """
    packages = [(path, item) for path, item in files if item.artifact_format == "deb-package"]
    if not packages:
        return ()
    if directory is None:
        raise CliError("Native packages must be staged before image construction.")
    paths = [f"/tmp/devcapsule-native-debs/{item.sha256}.deb" for _path, item in packages]
    quoted = " ".join(shell_quote(path) for path in paths)
    return (
        DirectoryComponent(directory, "/tmp/devcapsule-native-debs"),
        ExecComponent(("sh", "-ec", f"DEBIAN_FRONTEND=noninteractive dpkg --install {quoted}; rm -f {quoted}")),
    )


def _prepare_native_packages(
    files: tuple[tuple[Path, LockedArtifactDeclaration], ...], directory: Path,
) -> Path | None:
    packages = [(path, item) for path, item in files if item.artifact_format == "deb-package"]
    if not packages:
        return None
    directory.mkdir()
    for path, item in packages:
        target = directory / f"{_validated_sha256(item.sha256, 'Native package SHA-256')}.deb"
        shutil.copyfile(path, target)
        target.chmod(0o644)
    return directory


def npm_install_step(destination: str) -> tuple[str, ...]:
    """The exact build step that installs one npm project offline."""

    command = " ".join(
        [
            f"npm_config_cache={NPM_CACHE_PATH}",
            "npm",
            "--prefix",
            shell_quote(destination),
            *NPM_INSTALL_OPTIONS,
            "&&",
            "rm",
            "-rf",
            NPM_CACHE_PATH,
        ]
    )
    return ("sh", "-c", command)


def _npm_tarball_name(declaration: LockedArtifactDeclaration) -> str:
    """The file name the tarball keeps inside the image: its URL's last segment."""

    name = urlsplit(declaration.url).path.rsplit("/", 1)[-1]
    if not _NPM_TARBALL_NAME.fullmatch(name):
        raise CliError(
            f"Locked {declaration.component_id} npm-package URL must end in a tarball "
            f"file name (.tgz or .tar.gz); got {name!r} from {declaration.url!r}."
        )
    return name


def _artifact_image_path(declaration: LockedArtifactDeclaration) -> str:
    """Where the prepared artifact file lands in the image.

    File-shaped formats name the executable itself; an npm-package
    destination is the project directory and the tarball keeps its name.
    """

    if declaration.artifact_format == "python-wheel":
        return f"{declaration.destination}/wheels/{wheel_name(declaration.url)}"
    if declaration.artifact_format == "npm-package":
        return f"{declaration.destination}/{_npm_tarball_name(declaration)}"
    return declaration.destination


def _npm_projects(
    ancillary_files: tuple[tuple[Path, LockedArtifactDeclaration], ...],
    work: Path,
) -> tuple[NpmProject, ...]:
    """Group npm-package artifacts by destination and write each manifest."""

    grouped: dict[str, list[LockedArtifactDeclaration]] = {}
    for _path, declaration in ancillary_files:
        if declaration.artifact_format == "npm-package":
            grouped.setdefault(declaration.destination, []).append(declaration)
    projects: list[NpmProject] = []
    for index, (destination, declarations) in enumerate(grouped.items()):
        component_ids = sorted({item.component_id for item in declarations})
        if len(component_ids) != 1:
            raise CliError(
                f"npm project {destination} is claimed by several components: "
                + ", ".join(component_ids)
                + "."
            )
        dependencies: dict[str, str] = {}
        for item in declarations:
            assert item.npm_package is not None  # validated when the lock was read
            if item.npm_package in dependencies:
                raise CliError(
                    f"Locked {item.component_id} declares npm package {item.npm_package!r} "
                    "twice."
                )
            dependencies[item.npm_package] = f"file:./{_npm_tarball_name(item)}"
        manifest = {
            "name": f"devcapsule-{component_ids[0]}",
            "version": "0.0.0",
            "private": True,
            "dependencies": dependencies,
        }
        package_json = work / f"npm-project-{index}.json"
        package_json.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
        projects.append(NpmProject(component_ids[0], destination, package_json))
    return tuple(projects)


def _ancillary_environment(
    declarations: tuple[LockedArtifactDeclaration, ...],
) -> tuple[tuple[str, str], ...]:
    environment: dict[str, str] = {}
    for declaration in declarations:
        for name, value in declaration.environment:
            previous = environment.get(name)
            if previous is None or previous == value:
                environment[name] = value
                continue
            # PATH is the one variable several components legitimately share:
            # each contributes a "<bin>:${PATH}" prefix, and Docker resolves
            # the trailing ${PATH} against the base at build time. Chain the
            # prefixes in declaration order; any other collision is a real
            # contract conflict.
            if name == "PATH" and previous.endswith(":${PATH}") and value.endswith(":${PATH}"):
                environment[name] = previous.removesuffix("${PATH}") + value
                continue
            raise CliError(
                f"Materialized components declare conflicting values for environment {name}."
            )
    return tuple(sorted(environment.items()))


def runtime_config_drift(
    details: ImageDetails, descriptor: Mapping[str, Any]
) -> tuple[str, ...]:
    """Differences between the image's actual boot configuration and the
    descriptor's claim. Empty when the claim is true (or when the caller
    supplied no boot configuration to compare)."""

    if not details.entrypoint and not details.command:
        return ()
    runtime = descriptor["runtime"]
    drift: list[str] = []
    if tuple(details.entrypoint) != tuple(runtime["entrypoint"]):
        drift.append(
            f"entrypoint is {list(details.entrypoint)}, "
            f"descriptor claims {runtime['entrypoint']}"
        )
    if tuple(details.command) != tuple(runtime["command"]):
        drift.append(
            f"command is {list(details.command)}, descriptor claims {runtime['command']}"
        )
    return tuple(drift)


def descriptor_differences(
    expected: Any, actual: Any, prefix: str = ""
) -> tuple[str, ...]:
    """Leaf paths on which two JSON-native descriptors differ."""

    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        paths: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            child = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(descriptor_differences(expected.get(key), actual.get(key), child))
        return tuple(paths)
    if (
        isinstance(expected, list)
        and isinstance(actual, list)
        and len(expected) == len(actual)
        and not all(isinstance(item, (str, int, float, bool)) for item in expected + actual)
    ):
        paths = []
        for index, (left, right) in enumerate(zip(expected, actual)):
            paths.extend(descriptor_differences(left, right, f"{prefix}[{index}]"))
        return tuple(paths)
    if expected != actual:
        return (prefix or "<root>",)
    return ()


def verify_materialized_image(
    details: ImageDetails,
    *,
    descriptor: Mapping[str, Any],
    canonical_name: str,
) -> None:
    _verify_materialized_labels(details, descriptor=descriptor, canonical_name=canonical_name)
    drift = runtime_config_drift(details, descriptor)
    if drift:
        raise CliError(
            f"Canonical image {canonical_name!r} boots differently than its formation "
            f"descriptor records: {'; '.join(drift)}. The record cannot be trusted; "
            "inspect and remove or retag the image before retrying."
        )


def _verify_materialized_labels(
    details: ImageDetails,
    *,
    descriptor: Mapping[str, Any],
    canonical_name: str,
) -> None:
    labels = details.labels
    expected_json = canonical_json(descriptor)
    expected_identity = formation_identity(descriptor)
    problem = (
        labels.get(MANAGED_LABEL) != "true"
        or labels.get(METADATA_VERSION_LABEL) != METADATA_VERSION
        or labels.get(IMAGE_KIND_LABEL) != MATERIALIZED_KIND
        or labels.get(CANONICAL_NAME_LABEL) != canonical_name
        or labels.get("devcapsule.materialization.identity") != expected_identity
        or labels.get("devcapsule.materialization.base-identity") != descriptor["base"]["identity"]
        or ("pex-sha256" in descriptor["runtime"]
            and labels.get("devcapsule.pex.sha256") != descriptor["runtime"]["pex-sha256"])
        or labels.get("devcapsule.materialization.recipe-version") != descriptor["recipe"]["version"]
        or labels.get("devcapsule.component.id") != descriptor["components"][0]["id"]
        or labels.get("devcapsule.component.version") != descriptor["components"][0]["version"]
        or labels.get("devcapsule.component.sha256") != descriptor["components"][0]["artifact"]["sha256"]
    )
    stored_descriptor = labels.get("devcapsule.materialization.descriptor")
    try:
        parsed_descriptor = json.loads(stored_descriptor or "")
    except json.JSONDecodeError:
        parsed_descriptor = None
    if (
        problem
        or not isinstance(parsed_descriptor, dict)
        or canonical_json(parsed_descriptor) != expected_json
        or formation_identity(parsed_descriptor) != expected_identity
    ):
        raise CliError(
            f"Canonical image tag {canonical_name!r} exists with conflicting or malformed metadata; "
            "inspect and remove or retag it before retrying."
        )


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _validated_sha256(value: str, label: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise CliError(f"{label} must contain exactly 64 hexadecimal characters.")
    return normalized


def _split_platform(value: str) -> tuple[str, str]:
    try:
        operating_system, architecture = value.split("-", 1)
    except ValueError as exc:
        raise CliError(f"Unsupported platform alias {value!r}; expected OS-ARCHITECTURE.") from exc
    if not operating_system or not architecture:
        raise CliError(f"Unsupported platform alias {value!r}; expected OS-ARCHITECTURE.")
    return operating_system, architecture


def _required_mapping(value: Mapping[str, Any], key: str, context: str) -> Mapping[str, Any]:
    selected = value.get(key)
    if not isinstance(selected, dict):
        raise CliError(f"{context} must define [{key}] formation data.")
    return selected


def _required_string(value: Mapping[str, Any], key: str, context: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected:
        raise CliError(f"{context} must define non-empty {key!r} formation data.")
    return selected
