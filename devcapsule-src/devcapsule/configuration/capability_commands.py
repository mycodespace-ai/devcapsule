"""Capability command adapters: validate first, then promote owned documents.

Project replacement has one commit point (the manifest) and an undo/redo
journal. Local replacement changes one checkout file atomically. Neither path
answers host-access or acquisition questions on the developer's behalf.
Project initialization is one path, in :mod:`operations`; the owner's edits
of the shared contract are in :mod:`owner_commands`, over ``promote`` here.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any, Mapping, Sequence

from devcapsule.platforms import Platform, UnsupportedPlatformError
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix
from .capabilities import CapabilityPolicy, LocalCapabilities, capability_notes, resolution_recommendations
from .capability_selection import compose_lock, effective_lock, generate_lock, local_pins, usable_lock, matrix_for, pin_selection
from .file_formats import ConfigurationFileKind, ProjectConfigurationError, table, validate_file_format, render_checkout, render_toml, selected_version_lock
from .manifest import current_manifest
from .manifest_document import capability_reasons, capability_table, manifest_preamble, render_manifest
from .manifest_schemas import ManifestV2
from .nodes import build_node_registry
from .storage import (
    atomic_write, checkout_record_paths, discover_project, load_toml, locked_platforms, platform_lock_path,
    project_platform, require_settled,
)


def paths(root: Path) -> tuple[Path, Path, Path]:
    """Return manifest, current-platform lock and recovery-journal paths.

    ``root`` is the project directory. This only constructs paths.
    """
    directory = root / ".devcapsule"
    return (directory / "devcapsule.toml", platform_lock_path(root, project_platform(root)),
            directory / ".capability-transaction.toml")


def recover(root: Path) -> None:
    """Finish an interrupted shared edit, or do nothing if no journal exists.

    The manifest chooses the before or after side of every lock the journal
    holds. Refuse malformed journals or independent edits with
    ProjectConfigurationError. Successful recovery removes the journal.
    Callers must exclude concurrent writers. Filesystem errors propagate.
    """
    manifest_path, _, journal = paths(root)
    if not journal.exists():
        return
    transaction = load_toml(journal)
    locks = _journaled_locks(root, transaction)
    current = manifest_path.read_bytes().decode("utf-8") if manifest_path.exists() else ""
    for lock_path, (before, after) in locks.items():
        current_lock = lock_path.read_bytes().decode("utf-8") if lock_path.exists() else ""
        if current_lock not in {before, after}:
            raise ProjectConfigurationError("Lock changed outside the pending transaction; refusing to overwrite it.")
    if current == transaction["after-manifest"]:
        committed = True
    elif current == transaction["before-manifest"]:
        committed = False
    else:
        raise ProjectConfigurationError("Configuration changed outside the pending transaction; refusing to overwrite it.")
    for lock_path, (before, after) in locks.items():
        restored = after if committed else before
        # Manifest-only edits preserve even an absent or empty lock.
        if before != after:
            if restored:
                atomic_write(lock_path, restored, mode=0o644)
            else:
                lock_path.unlink(missing_ok=True)
    journal.unlink()


def _journaled_locks(root: Path, transaction: Mapping[str, Any]) -> dict[Path, tuple[str, str]]:
    """Each lock path the journal holds, with its before and after text.

    A journal holds every platform lock under ``before-locks`` and
    ``after-locks``; one written by a launcher of a single platform holds
    that platform's lock as ``before-lock`` and ``after-lock``.
    """
    malformed = ProjectConfigurationError("Malformed capability transaction; preserve it for recovery.")
    manifests = (transaction.get("before-manifest"), transaction.get("after-manifest"))
    if not all(isinstance(value, str) for value in manifests):
        raise malformed
    if set(transaction) == {"before-manifest", "after-manifest", "before-lock", "after-lock"}:
        sides = {str(project_platform(root)): (transaction["before-lock"], transaction["after-lock"])}
    elif set(transaction) == {"before-manifest", "after-manifest", "before-locks", "after-locks"}:
        before, after = transaction["before-locks"], transaction["after-locks"]
        if not isinstance(before, dict) or not isinstance(after, dict) or set(before) != set(after):
            raise malformed
        sides = {key: (before[key], after[key]) for key in before}
    else:
        raise malformed
    locks: dict[Path, tuple[str, str]] = {}
    for key, (before_text, after_text) in sides.items():
        if not isinstance(before_text, str) or not isinstance(after_text, str):
            raise malformed
        try:
            platform = Platform.parse(key)
        except UnsupportedPlatformError:
            raise malformed from None
        locks[platform_lock_path(root, platform)] = (before_text, after_text)
    return locks


def promote(root: Path, manifest: dict[str, Any], locks: Mapping[Platform, dict[str, Any]] | None = None) -> None:
    """Persist an already-validated manifest, and the locks when given, with a recovery journal.

    Call ``check_documents`` first and exclude concurrent writers. Write the
    locks before the manifest; attempt recovery on OSError. Failures
    propagate. A pending journal raises ProjectConfigurationError. This
    updates shared files only; it neither writes nor resolves a developer's
    checkout.

    The manifest is written by the one manifest writer: bare keys, the
    owner's table order, the leading comment block of the existing file
    kept, and the supplied schema version. ``locks`` of ``None`` keeps every
    lock file's bytes exactly, for an edit that changes the manifest alone.
    """
    manifest_path, _, journal = paths(root)
    ManifestV2.read(manifest, manifest_path)  # The one writer writes schema 2 and nothing else.
    require_settled(root)
    before_manifest = manifest_path.read_bytes().decode("utf-8") if manifest_path.exists() else ""
    after_manifest = render_manifest(manifest, preamble=manifest_preamble(before_manifest))
    before_locks: dict[str, str] = {}
    after_locks: dict[str, str] = {}
    for platform, lock in (locks or {}).items():
        lock_path = platform_lock_path(root, platform)
        before_locks[str(platform)] = lock_path.read_bytes().decode("utf-8") if lock_path.exists() else ""
        after_locks[str(platform)] = render_toml(lock)
    atomic_write(journal, render_toml({"before-manifest": before_manifest, "after-manifest": after_manifest,
                                       "before-locks": before_locks, "after-locks": after_locks}))
    try:
        for platform, lock in (locks or {}).items():
            atomic_write(platform_lock_path(root, platform), after_locks[str(platform)], mode=0o644)
        atomic_write(manifest_path, after_manifest, mode=0o644)
    except OSError:
        recover(root)
        raise
    journal.unlink()


def project_locks(root: Path) -> dict[Platform, dict[str, Any]]:
    """Every platform lock the project carries, by platform.

    An edit of the shared contract regenerates them all, so a lock committed
    for another platform never falls behind the manifest (R-COMPAT-001). A
    project with none fails as reading this host's lock does.
    """
    platforms = locked_platforms(root) or (project_platform(root),)
    return {platform: load_toml(platform_lock_path(root, platform)) for platform in platforms}


def regenerate_locks(policy: CapabilityPolicy, locks: Mapping[Platform, dict[str, Any]], *,
                     recommendations: Mapping[str, str], allow_unverified: bool = False) -> dict[Platform, dict[str, Any]]:
    """Each of ``locks`` regenerated for ``policy`` from its own platform's matrix.

    A lock that cannot follow refuses the whole edit; with several, the
    error names the platform.
    """
    generated: dict[Platform, dict[str, Any]] = {}
    for platform, lock in locks.items():
        try:
            generated[platform] = generate_lock(policy, MATRICES[platform], previous=lock,
                                                allow_unverified=allow_unverified, recommendations=recommendations)
        except ProjectConfigurationError as exc:
            if len(locks) == 1:
                raise
            raise ProjectConfigurationError(f"The project's {platform} lock cannot follow this edit: {exc}") from exc
    return generated


def check_documents(manifest: dict[str, Any], lock: dict[str, Any], *, check_resolutions: bool = True) -> tuple[str, ...]:
    """Validate shared documents offline and return optional-omission warnings.

    Check schemas, required capabilities, minimum versions and usable artifact
    metadata. Invalid configuration raises CliError or its configuration
    subclass. This does not change inputs or files, download artifacts, or
    grant host access.
    """
    manifest = current_manifest(manifest, Path("manifest")).document()
    validate_file_format(lock, ConfigurationFileKind.lock, "platform lock")
    policy = CapabilityPolicy.read(manifest)
    matrix = matrix_for(lock)
    minimums = {matrix.canonical_name(name): version for name, version in policy.minimums}
    for name, component in (resolution_recommendations(manifest) if check_resolutions else {}).items():
        matrix.resolve_provider(name, minimums.get(matrix.canonical_name(name)), recommended=component)
    usable, notices = usable_lock(policy, lock)
    check_formation(manifest, usable)
    return notices


def check_formation(manifest: dict[str, Any], usable: dict[str, Any]) -> None:
    """Check artifact metadata and declarations in an already-selected lock.

    ``usable`` must contain only supported components, as returned by
    ``usable_lock``. Raise CliError for invalid metadata or declarations.
    No artifacts are downloaded and no launch permissions are granted.
    """
    from devcapsule.components.catalog import COMPONENTS
    from devcapsule.materialization import parse_locked_environment, validate_locked_artifact
    from .authorization import locked_base_reference, authorization_declarations
    if "base" in usable:
        locked_base_reference(usable)
        if usable.get("components", {}).get("interactive-surface"):
            parse_locked_environment(usable)
        else:
            for name, metadata in usable.get("components", {}).items():
                for artifact in COMPONENTS[name].locked_artifacts(metadata, str(usable["platform"])):
                    validate_locked_artifact(artifact)
    authorization_declarations(manifest, usable)
    if usable.get("components", {}).get("interactive-surface"):
        build_node_registry(manifest, usable)


def check(start: Path, *, manifest_path: Path | None = None, lock_path: Path | None = None) -> str:
    """Return an offline validation report for the project containing ``start``.

    Candidate paths override the shared manifest/current-platform lock paths.
    A pending edit must be recovered first. Invalid documents raise CliError;
    filesystem errors propagate. This reads only: it does not register a
    checkout, recover an edit, download artifacts or test launch permissions.
    """
    root = discover_project(start)
    default_manifest, default_lock, _ = paths(root)
    require_settled(root)
    manifest = load_toml(manifest_path or default_manifest)
    lock = load_toml(lock_path or default_lock)
    notices = check_documents(manifest, lock)
    return "\n".join((*(f"Note: {note}" for note in capability_notes(manifest)),
                      "Configuration contract valid (offline; launch permissions and downloads are not tested).",
                      *(f"Warning: {notice}" for notice in notices)))


def configure(start: Path, *, required: Sequence[str] | None = None,
              optional: Sequence[str] | None = None,
              local: Sequence[str] | None = None, without: Sequence[str] | None = None,
              preview: bool = False, allow_unverified: bool = False,
              providers: Mapping[str, str] | None = None) -> str:
    """Replace project capability declarations or this checkout's local choices.

    ``start`` locates the project. Supply one group: shared ``required``,
    ``optional``; or local ``local``, ``without``. Name sequences
    replace the corresponding lists.
    None retains a field; an empty sequence clears it. IDE/agent additions
    belong in ``local``. Host decisions are retained and never answered here.

    Validate before writing and return a human-readable result. ``preview``
    performs the same validation without writes. ``allow_unverified`` permits
    catalog combinations lacking compatibility evidence. Invalid edits raise
    CliError; I/O errors propagate. A successful edit still needs an explicit
    configuration resolution before launch when local inputs have changed.
    """
    root = discover_project(start)
    require_settled(root)
    manifest_path, lock_path, _ = paths(root)
    manifest, lock = current_manifest(load_toml(manifest_path), manifest_path).document(), load_toml(lock_path)
    check_documents(manifest, lock)
    project_edit = any(value is not None for value in (required, optional))
    local_edit = local is not None or without is not None or providers is not None
    if project_edit == local_edit:
        raise ProjectConfigurationError("Choose either project flags (--required/--optional) or local flags (--local/--without).")
    matrix = MATRICES[project_platform(root)]
    if project_edit:
        locks = project_locks(root)
        for other in locks.values():
            check_documents(manifest, other)
        return configure_project(root, manifest, locks, required=required, optional=optional,
                                 preview=preview, allow_unverified=allow_unverified)
    return configure_local(root, manifest, lock, matrix, local=local, without=without, providers=providers,
                           preview=preview, allow_unverified=allow_unverified)


def configure_project(root: Path, manifest: dict[str, Any], locks: Mapping[Platform, dict[str, Any]], *,
                      required: Sequence[str] | None, optional: Sequence[str] | None,
                      preview: bool, allow_unverified: bool) -> str:
    """Replace the shared policy and regenerate every platform lock; see ``configure``.

    ``manifest`` and ``locks`` are the validated current shared documents and
    are not changed; ``manifest`` is used as the candidate's template.
    """
    policy = CapabilityPolicy.read(manifest)
    candidate_manifest = deepcopy(manifest)
    declarations: dict[str, Any] = {
        "required": list(policy.requirements() if required is None else required),
        "optional": list(policy.optional if optional is None else optional),
    }
    candidate_manifest["capabilities"] = declarations
    candidate = CapabilityPolicy.read(candidate_manifest)
    candidate_manifest["capabilities"] = capability_table(candidate, capability_reasons(manifest), previous=manifest["capabilities"])
    generated = regenerate_locks(candidate, locks, allow_unverified=allow_unverified,
                                 recommendations=resolution_recommendations(candidate_manifest))
    for lock in generated.values():
        check_documents(candidate_manifest, lock)
    if not preview:
        promote(root, candidate_manifest, generated)
    return ("Preview; no files changed.\n" if preview else "Updated shared capability policy and lock.\n") + render_toml(candidate_manifest["capabilities"])


def configure_local(root: Path, manifest: dict[str, Any], shared: dict[str, Any], matrix: ResolutionMatrix, *,
                    local: Sequence[str] | None, without: Sequence[str] | None,
                    preview: bool, allow_unverified: bool, providers: Mapping[str, str] | None = None) -> str:
    """Replace this checkout's selections and omissions; see ``configure``.

    Only the checkout record changes. Its persistent selection (an explicit
    version set when present) keeps every pin that an omission merely hides;
    omissions take effect when the selection is projected for execution.
    Provider pins for the new selection come from ``pin_selection``, and an
    explicit version set drops only providers that no capability needs anymore.
    """
    policy = CapabilityPolicy.read(manifest)
    input_path, _ = checkout_record_paths(manifest, root)
    if input_path.with_suffix(".activation.toml").exists():
        raise ProjectConfigurationError("A local version-set activation needs recovery; run 'project run' first.")
    if input_path.exists():
        checkout = load_toml(input_path)
    else:
        checkout = tomllib.loads(render_checkout(manifest, root, {}, {}))
    validate_file_format(checkout, ConfigurationFileKind.checkout, input_path)
    previous = LocalCapabilities.read(checkout)
    selection = LocalCapabilities.read({"capabilities": {
        "selected": list(previous.selected if local is None else local),
        "without": list(previous.without if without is None else without),
        "providers": dict(previous.providers if providers is None else providers)}})
    selection.validate(policy)
    matrix.normalize(list(selection.selected))
    previous_pins = local_pins(checkout)
    version_lock = selected_version_lock(checkout)
    version_record = checkout.pop("version-set", None)
    source = deepcopy(version_lock if version_lock is not None else shared)
    if version_lock is not None:
        release_deselected(source, matrix, policy, previous, selection, recommendations=resolution_recommendations(manifest))
    pins = pin_selection(matrix, policy, selection, source, previous, previous_pins, allow_unverified=allow_unverified,
                         recommendations=resolution_recommendations(manifest))
    checkout["capabilities"] = {"selected": list(selection.selected), "without": list(selection.without), "lock": render_toml(pins),
                                **({"providers": selection.providers} if selection.providers else {})}
    composed = compose_lock(manifest, source, checkout, reset_providers=tuple(set(previous.providers) - set(selection.providers)))
    if version_record is not None:
        version_record["lock"] = render_toml(composed)
        checkout["version-set"] = version_record
    check_formation(manifest, effective_lock(manifest, composed, checkout, warn=False))
    if not preview:
        atomic_write(input_path, render_toml(checkout))
    return ("Preview; no files changed." if preview else
            "Updated local capability selection; shared files unchanged. The next 'devcapsule project run' uses it.")


def release_deselected(source: dict[str, Any], matrix: ResolutionMatrix, policy: CapabilityPolicy,
                       previous: LocalCapabilities, selection: LocalCapabilities, *,
                       recommendations: Mapping[str, str] | None = None) -> None:
    """Remove providers of deselected capabilities from ``source`` in place.

    A provider stays when a required, known optional or still-selected
    capability needs it. Removing the IDE also clears the IDE selector and
    materialization. Capabilities this launcher does not know are left alone.
    """
    minimums = dict(policy.minimums)
    needed: set[str] = set()
    for capability in (*policy.required, *policy.optional, *selection.selected):
        try:
            matrix.canonical_name(capability)
        except ProjectConfigurationError:
            continue
        name = matrix.canonical_name(capability)
        needed.update(matrix.component_closure(capability, minimums.get(capability),
                      choice=selection.providers.get(name), recommended=(recommendations or {}).get(name)))
    table(source, "components")
    components: dict[str, Any] = source.setdefault("components", {})
    for capability in set(previous.selected) - set(selection.selected):
        try:
            matrix.canonical_name(capability)
        except ProjectConfigurationError:
            continue
        for component in matrix.component_closure(capability, lock=source):
            if component in needed:
                continue
            components.pop(component, None)
            if components.get("interactive-surface") == component:
                del components["interactive-surface"]
                source["materialization"] = {}


def parse_tool_names(matrix: ResolutionMatrix, names: Sequence[str]) -> tuple[str, ...]:
    """Read rc4 command arguments as capability names; version syntax is not CLI syntax yet."""
    return tuple(sorted({canonical_tool_name(matrix, name) for name in names}))


def canonical_tool_name(matrix: ResolutionMatrix, name: str) -> str:
    """The capability name for a name or its unambiguous sole provider alias."""
    try:
        return matrix.canonical_name(name.strip())
    except ProjectConfigurationError:
        raise ProjectConfigurationError(
            f"Unknown tool {name.strip()!r}; this launcher knows: " + ", ".join(matrix.capabilities()) + "."
        ) from None
