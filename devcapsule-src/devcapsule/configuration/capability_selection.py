"""Offline generation and tolerant consumption of capability locks.

Shared bytes are never changed by consumption. Two steps are kept apart:
``compose_lock`` builds the persistent selection (shared lock plus personal
pins, or an explicit version set) and ``usable_lock`` projects it for one
execution, checking mandatory providers first and admitting optional provider
closures only as whole units. Only the projection applies omissions, so a
persisted selection never loses what an omission merely hides.
"""
from __future__ import annotations

from copy import deepcopy
import sys
import tomllib
from typing import Any, Mapping

from devcapsule.components.catalog import COMPONENTS, INTERACTIVE_SURFACES
from devcapsule.platforms import Platform, UnsupportedPlatformError
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix
from .capabilities import CapabilityPolicy, LocalCapabilities, names, meets_minimum, resolution_recommendations
from .file_formats import ProjectConfigurationError, legacy_lock, table


def lock_platform(lock: Mapping[str, Any]) -> Platform:
    """Return the lock's declared platform.

    Raise ProjectConfigurationError if that platform is absent or unsupported.
    """
    try:
        return Platform.parse(str(lock.get("platform")))
    except UnsupportedPlatformError:
        raise ProjectConfigurationError(f"Unsupported lock platform {lock.get('platform')!r}.") from None


def matrix_for(lock: Mapping[str, Any]) -> ResolutionMatrix:
    """Return this launcher's catalog for the lock's declared platform.

    Raise ProjectConfigurationError if that platform is absent or unsupported.
    """
    return MATRICES[lock_platform(lock)]


def known_policy_names(policy: CapabilityPolicy, matrix: ResolutionMatrix) -> dict[str, str]:
    """Canonical names for the shared policy; unknown offers stay opaque."""
    result = {name: matrix.canonical_name(name) for name in policy.required}
    for name in policy.optional:
        try:
            result[name] = matrix.canonical_name(name)
        except ProjectConfigurationError:
            continue
    return result


def generate_lock(policy: CapabilityPolicy, matrix: ResolutionMatrix, *,
                  previous: Mapping[str, Any] | None = None,
                  allow_unverified: bool = False,
                  recommendations: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Build a shared lock for a validated policy, without writing files.

    Resolve known capabilities using ``matrix``; a project need not choose an
    IDE. Unknown optional names can survive only when ``previous`` supplies
    their provider lists and nonconflicting metadata. Otherwise raise
    ProjectConfigurationError, as for unsupported requirements or minimum versions.
    ``allow_unverified`` permits catalog combinations without recorded
    compatibility evidence. Inputs are unchanged; the returned lock is new.
    """
    matrix.normalize(list(policy.required))
    accepted = list(known_policy_names(policy, matrix))
    requirements = [*policy.requirements(), *(name for name in accepted if name not in policy.required)]
    formation = matrix.resolve(requirements, project_only=True,
                               allow_unverified=allow_unverified, recommendations=recommendations)
    lock = tomllib.loads(formation.render_lock())
    providers = {name: list(matrix.component_closure(name, choice=formation.resolved[matrix.canonical_name(name)]))
                 for name in accepted}
    for capability in set(policy.optional) - set(accepted):
        old_providers = table(previous or {}, "capability-providers")
        if capability not in old_providers:
            raise ProjectConfigurationError(f"Cannot author unknown capability {capability!r}; use a launcher that supports it.")
        opaque = names(old_providers[capability], f"providers for {capability}")
        for component in opaque:
            metadata = table(previous or {}, "components").get(component)
            if metadata is None or component in lock["components"] and lock["components"][component] != metadata:
                raise ProjectConfigurationError(f"Cannot preserve optional {capability!r} safely; its provider {component!r} conflicts or is missing.")
            lock["components"][component] = deepcopy(metadata)
        providers[capability] = list(opaque)
    lock["capability-providers"] = providers
    check_minimums(policy, lock, matrix)
    return lock


def check_minimums(policy: CapabilityPolicy, lock: Mapping[str, Any], matrix: ResolutionMatrix) -> None:
    """Require the exact selected pins to establish every minimum before launch."""
    for capability, minimum in policy.minimums:
        actual = matrix.supplied_version(capability, lock)
        if not meets_minimum(actual, minimum):
            raise ProjectConfigurationError(
                f"Required {capability}>={minimum}; selected lock supplies {actual or 'an unknown version'}. "
                "Select a compatible version set with 'versions follow-project --apply'; "
                "the project minimum cannot be overridden locally."
            )


def local_pins(checkout: Mapping[str, Any]) -> dict[str, Any]:
    """Return the checkout's personal provider pins as a parsed lock document.

    The pins are the TOML text in ``capabilities.lock``, written by the local
    capability command. A missing field means no pins: an empty dict. Raise
    ProjectConfigurationError for a field that is not a string or not TOML.
    The checkout is unchanged; the result is new.
    """
    encoded = table(checkout, "capabilities").get("lock")
    if encoded is None:
        return {}
    if not isinstance(encoded, str):
        raise ProjectConfigurationError("Local capabilities.lock must contain a TOML lock.")
    try:
        return tomllib.loads(encoded)
    except tomllib.TOMLDecodeError as exc:
        raise ProjectConfigurationError(f"Invalid local capability pins: {exc}") from exc


def pins_for_platform(pins: Mapping[str, Any], matrix: ResolutionMatrix) -> dict[str, Any]:
    """Return personal pins with every component's artifacts for ``matrix``'s platform.

    A checkout keeps one set of personal pins, and a project may run as two
    platforms: Apple Silicon runs linux-arm64 and linux-amd64. A component
    table that is exactly another platform's embedded table for its version
    is that platform's pin, whatever the pins' label says, and takes this
    platform's table for the version; one that matches no embedded table is a
    record this launcher did not write, kept as it stands on the platform its
    pins name. Everything else is returned unchanged. A component written for
    another platform at a version this platform does not pin raises
    ProjectConfigurationError naming how to choose again. The input is unchanged.
    """
    if not pins:
        return {}
    platform = str(matrix.platform)
    labelled = str(pins.get("platform"))
    repinned = deepcopy(dict(pins))
    components = repinned.get("components")
    surface = components.get("interactive-surface") if isinstance(components, dict) else None
    if isinstance(components, dict):
        for component, metadata in components.items():
            if not isinstance(metadata, dict):
                continue
            written_for = _embedded_platform_of(component, metadata) or labelled
            if written_for == platform:
                continue
            matrix_table = matrix.component_pin(component, metadata.get("version"))
            if matrix_table is None:
                remedy = (f"'devcapsule project config ide {component}'" if component == surface
                          else f"'devcapsule project config use CAPABILITY {component}'")
                raise ProjectConfigurationError(
                    f"This checkout's {component} {metadata.get('version')} is pinned for {written_for}, "
                    f"and {platform} has no pin for that version; choose it again with {remedy}."
                )
            components[component] = deepcopy(dict(matrix_table))
    if "platform" in repinned:
        repinned["platform"] = platform
    return repinned


def _embedded_platform_of(component: str, table: Mapping[str, Any]) -> str | None:
    """The platform whose embedded table for this component version ``table`` is, if any."""
    for platform, embedded in MATRICES.items():
        candidate = embedded.component_pin(component, table.get("version"))
        if candidate is not None and dict(candidate) == dict(table):
            return str(platform)
    return None


def pin_selection(matrix: ResolutionMatrix, policy: CapabilityPolicy, selection: LocalCapabilities,
                  source: Mapping[str, Any], previous: LocalCapabilities, previous_pins: Mapping[str, Any], *,
                  allow_unverified: bool, recommendations: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return the pins document for ``selection``: a lock holding exactly its providers.

    Each provider's metadata comes from the first document that has it: the
    ``source`` selection the pins will be laid over, then ``previous_pins``
    for a capability that ``previous`` already selected, then a fresh catalog
    resolution of the project's required and the selected capabilities. The IDE
    selector and materialization follow the IDE component's document. Catalog
    resolution failures raise ProjectConfigurationError. Inputs are unchanged.
    """
    previous_pins = pins_for_platform(previous_pins, matrix)
    active_names = set(known_policy_names(policy, matrix).values()) | {matrix.canonical_name(name) for name in selection.selected}
    reset = (set(previous.providers) - set(selection.providers)) & active_names
    capabilities = tuple(dict.fromkeys((*selection.selected, *selection.providers, *sorted(reset))))
    active = sorted(set(policy.requirements()) | (set(capabilities) - set(policy.required)))
    formation = matrix.resolve(active, project_only=True, allow_unverified=allow_unverified,
                               choices=selection.providers, recommendations=recommendations)
    fresh = tomllib.loads(formation.render_lock())
    pins = {key: deepcopy(value) for key, value in fresh.items() if key != "components"}
    pins["components"] = {}
    pins["materialization"] = {}
    pins["capability-providers"] = {}
    surface = fresh["components"].get("interactive-surface")
    retained = (set(previous.selected) | set(previous.providers)) & set(capabilities)
    for capability in capabilities:
        closure = matrix.component_closure(capability, choice=formation.resolved[matrix.canonical_name(capability)])
        pins["capability-providers"][capability] = list(closure)
        for component in closure:
            documents = (source, *((previous_pins,) if capability in retained else ()), fresh)
            document = next((item for item in documents if table(item, "components").get(component) is not None), None)
            if document is None:
                raise ProjectConfigurationError(f"The catalog resolved {capability!r} without pinning its provider {component!r}.")
            pins["components"][component] = deepcopy(table(document, "components")[component])
            if component == surface:
                pins["components"]["interactive-surface"] = surface
                materialization = document if table(document, "components").get("interactive-surface") == surface else fresh
                pins["materialization"] = deepcopy(table(materialization, "materialization"))
    return pins



def compose_lock(manifest: Mapping[str, Any], shared: Mapping[str, Any],
                 checkout: Mapping[str, Any], *, reset_providers: tuple[str, ...] = (),
                 policy: CapabilityPolicy | None = None) -> dict[str, Any]:
    """Return the checkout's persistent software selection, before any filtering.

    An explicit version set is that selection and is returned as a copy.
    Otherwise the result is ``shared`` with the checkout's personal pins laid
    over it: exactly the providers of each locally selected capability, and
    the IDE selector with its materialization when a selected capability
    supplies the IDE. A selected IDE that conflicts with a required project
    IDE raises ProjectConfigurationError, as do missing or malformed pins,
    pins that disagree with a recorded provider choice, and
    an omission of something the project does not list as optional.
    ``reset_providers`` names choices explicitly returned to the project or
    catalog while editing a saved version set. They do not add capabilities.
    ``policy`` is the launch's view of the manifest's policy when a launch
    departs from a requirement (``CapabilityPolicy.departing``); by default
    the manifest's policy as declared.
    This reader never derives new pins or removes superseded components.
    Omissions are not applied here; ``usable_lock`` filters for execution.
    Input documents are unchanged.
    """
    from .file_formats import selected_version_lock
    local = LocalCapabilities.read(checkout)
    local.validate(CapabilityPolicy.read(manifest))
    selected = selected_version_lock(checkout)
    if selected is not None:
        return selected
    lock = deepcopy(dict(shared))
    if not local.selected and not local.providers and not reset_providers:
        return lock
    pins = local_pins(checkout)
    if not pins and local.providers:
        name, choice = next(iter(local.providers.items()))
        raise ProjectConfigurationError(f"Local capability pins are missing; choose it again with 'project config use {name} {choice}'.")
    if not pins:
        raise ProjectConfigurationError("Local capability pins are missing; choose it again with 'project config ide IDE'.")
    matrix = matrix_for(lock)
    pins = pins_for_platform(pins, matrix)
    if policy is None:
        policy = CapabilityPolicy.read(manifest)
    canonical = {**known_policy_names(policy, matrix), **{name: matrix.canonical_name(name) for name in local.selected}}
    active_names = set(canonical.values())
    capabilities = tuple(dict.fromkeys((*local.selected, *local.providers, *(name for name in reset_providers if name in active_names))))
    for name, choice in local.providers.items():
        if matrix.resolve_provider(name, lock=pins) != choice:
            raise ProjectConfigurationError(
                f"Local provider pins for {name!r} do not match {choice!r}; "
                f"choose it again with 'project config use {name} {choice}'."
            )
    pinned = table(pins, "components")
    overlaid: set[str] = set()
    for capability in capabilities:
        for component in matrix.component_closure(capability, lock=pins):
            metadata = pinned.get(component)
            if metadata is None:
                raise ProjectConfigurationError(f"Local selection is missing provider {component!r}; select local capabilities again.")
            lock.setdefault("components", {})[component] = deepcopy(metadata)
            overlaid.add(component)
        closure = list(matrix.component_closure(capability, lock=pins))
        evidence = lock.setdefault("capability-providers", {})
        evidence[capability] = closure
        for name, canonical_name in canonical.items():
            if canonical_name == matrix.canonical_name(capability):
                evidence[name] = closure
    surface = pinned.get("interactive-surface")
    if surface in overlaid:
        shared_surface = lock["components"].get("interactive-surface")
        required_ide = next((name for name in policy.required if matrix.is_ide(name)), None)
        selected_ide = next((name for name in local.selected if matrix.is_ide(name)), None)
        changes_surface = bool(shared_surface and shared_surface != surface)
        selects_required_ide = (selected_ide is not None and required_ide is not None
                                and matrix.canonical_name(selected_ide) == matrix.canonical_name(required_ide))
        chooses_ide_provider = any(matrix.is_ide(name) for name in local.providers)
        if changes_surface and required_ide and not selects_required_ide and not chooses_ide_provider:
            # An explicit schema-2 IDE requirement remains mandatory even
            # though migrated schema-1 IDEs are only recommendations. The
            # one way past it is the explicit launch departure, named here.
            raise ProjectConfigurationError(
                f"Local IDE {selected_ide!r} conflicts with the project's required IDE {required_ide!r}. "
                f"Choose the required IDE with 'project config ide {required_ide}', or launch {selected_ide} once, "
                f"setting the requirement aside for that launch only: 'project run --ide {selected_ide} --force'."
            )
        lock["components"]["interactive-surface"] = surface
        lock["materialization"] = deepcopy(table(pins, "materialization"))
    return lock


def effective_lock(manifest: Mapping[str, Any], composed: Mapping[str, Any],
                   checkout: Mapping[str, Any], *, warn: bool = True,
                   policy: CapabilityPolicy | None = None) -> dict[str, Any]:
    """Return the execution projection of a composed selection.

    Apply ``usable_lock`` with the manifest's policy, or the launch's
    ``policy`` when a launch departs from a requirement, and the checkout's
    local choices. ``warn`` prints optional omissions to stderr; False
    suppresses that output, not validation. Inputs are unchanged.
    """
    usable, notices = usable_lock(CapabilityPolicy.read(manifest) if policy is None else policy,
                                  composed, LocalCapabilities.read(checkout))
    if warn:
        for notice in notices:
            print(f"Warning: {notice}", file=sys.stderr)
    return usable


def selected_lock(manifest: Mapping[str, Any], shared: Mapping[str, Any],
                  checkout: Mapping[str, Any], *, warn: bool = True) -> dict[str, Any]:
    """Return the checkout's effective lock without changing input documents.

    This is ``effective_lock`` of ``compose_lock``: the persistent selection
    (explicit version set, or ``shared`` plus personal pins) filtered by the
    policy and local omissions. Errors and ``warn`` behave as in those two.
    """
    return effective_lock(manifest, compose_lock(manifest, shared, checkout), checkout, warn=warn)


def usable_lock(policy: CapabilityPolicy, source: Mapping[str, Any],
                local: LocalCapabilities = LocalCapabilities()) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Return an effective lock and warning strings for omitted enhancements.

    ``policy`` and ``local`` must be validated values; ``source`` supplies
    pinned component metadata. Required and locally selected capabilities,
    including their dependencies, must be available or this raises
    ProjectConfigurationError. Optional omissions never remove those providers.
    Unsupported or missing optional providers are skipped with a warning.

    The returned lock is a filtered copy for execution, not a replacement for
    persisted version pins. Inputs remain unchanged. A lock generated before
    provider evidence (``legacy_lock``), under a policy without optional or
    minimum capabilities, returns an unfiltered copy: its base cannot vouch
    for the services the catalog expects of it, and what the checkout
    selected is already laid over it.
    This checks provider availability; artifact integrity and host permissions
    are checked by later admission stages.
    """
    lock = deepcopy(dict(source))
    if legacy_lock(source) and not policy.optional and not policy.minimums:
        return lock, ()  # Old locks remain records, not requests to re-resolve.
    local.validate(policy)
    matrix = matrix_for(lock)
    components = table(lock, "components")
    base = matrix.base_image(str(table(lock, "base").get("reference")))
    keep: set[str] = set()
    needed_by: dict[str, str] = {}  # component -> the first capability whose closure needs it
    notices: list[str] = []

    def supply(capability: str) -> tuple[str, ...]:
        try:
            name = matrix.canonical_name(capability)
        except ProjectConfigurationError:
            raise ProjectConfigurationError("this launcher does not support it") from None
        providers = matrix.component_closure(name, lock=lock)
        if not providers and (base is None or name not in base.contract.services):
            raise ProjectConfigurationError("the selected base cannot establish that it supplies this capability")
        missing = [name for name in providers if name not in COMPONENTS or not isinstance(components.get(name), dict)]
        if missing:
            raise ProjectConfigurationError("missing supported providers: " + ", ".join(missing))
        for provider in providers:
            needed_by.setdefault(provider, capability)
        return providers

    for role, capabilities in (("Required", policy.required), ("Selected", local.selected)):
        for capability in capabilities:
            try:
                keep.update(supply(capability))
            except ProjectConfigurationError as exc:
                raise ProjectConfigurationError(f"{role} capability {capability!r} is unavailable: {exc}. Upgrade the launcher or select compatible components.") from exc
    # The pinned IDE is a selection, never an optional to omit: a lock written
    # when the project required its IDE stands for every checkout that chose
    # none, and a checkout's own choice already replaced the surface.
    pinned = components.get("interactive-surface")
    if (isinstance(pinned, str) and isinstance(components.get(pinned), dict)
            and any(pinned in matrix.providers(capability) for capability in matrix.ide_capabilities())):
        closure = [pinned]
        for name in closure:
            definition = COMPONENTS.get(name)
            if definition is not None:
                closure.extend(item for item in definition.required_components() if item not in closure)
        missing = [name for name in sorted(closure) if name not in COMPONENTS or not isinstance(components.get(name), dict)]
        if missing:
            raise ProjectConfigurationError("missing supported providers: " + ", ".join(missing))
        keep.update(closure)
    check_minimums(policy, lock, matrix)
    for capability in policy.optional:
        if capability in local.without:
            notices.append(f"Optional {capability!r} omitted by local choice; that enhancement is unavailable.")
            continue
        try:
            keep.update(supply(capability))
        except ProjectConfigurationError as exc:
            notices.append(f"Optional {capability!r} omitted: {exc}; that enhancement is unavailable.")
    surface = components.get("interactive-surface")
    # One surface per launch. A second IDE that a remaining capability's
    # closure needs is a real dependency, explained here, not an internal
    # catalog error at template selection.
    for component in sorted(keep):
        if component != surface and component in INTERACTIVE_SURFACES and surface in keep:
            raise ProjectConfigurationError(
                f"Capability {needed_by.get(component, component)!r} needs {component}, an IDE that cannot "
                f"accompany the selected IDE {surface}; this environment is impossible as requested."
            )
    lock["components"] = {name: deepcopy(value) for name, value in components.items() if name in keep}
    if surface in keep:
        lock["components"]["interactive-surface"] = surface
    else:
        lock["materialization"] = {}
    # Evidence is reconstructed by this reader, never trusted from a newer
    # writer. The pure configuration core uses it for optional-only freshness.
    lock["capability-providers"] = {capability: list(matrix.component_closure(capability, lock=lock))
                                    for capability in (*policy.required, *local.selected)}
    return lock, tuple(notices)


def inspection_capabilities(manifest: Mapping[str, Any], lock: Mapping[str, Any],
                            checkout: Mapping[str, Any], *,
                            policy: CapabilityPolicy | None = None) -> tuple[Mapping[str, Any], dict[str, str | None]]:
    """Catalog facts for a listing, retaining inspectability of an invalid contract.

    Consent concerns only the execution projection, including local omissions.
    Check and run remain responsible for reporting a mandatory contract error.
    ``policy`` is the launch's view when a launch departs from a requirement.
    """
    if policy is None:
        policy = CapabilityPolicy.read(manifest)
    try:
        access_lock, _ = usable_lock(policy, lock, LocalCapabilities.read(checkout))
    except ProjectConfigurationError:
        access_lock = dict(lock)
    versions: dict[str, str | None] = {}
    for name, _ in policy.minimums:
        try:
            versions[name] = matrix_for(lock).supplied_version(name, lock)
        except ProjectConfigurationError:
            versions[name] = None
    return access_lock, versions


def inspection_providers(manifest: Mapping[str, Any], lock: Mapping[str, Any],
                         checkout: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    """Provider and preference source for each declared or selected capability."""
    from .manifest_document import Recommendations
    matrix = matrix_for(lock)
    policy = CapabilityPolicy.read(manifest)
    local = LocalCapabilities.read(checkout)
    recommendations = resolution_recommendations(manifest)
    ide = Recommendations.read(manifest).ide
    result = {}
    for name in dict.fromkeys((*policy.required, *policy.optional, *local.selected, *((ide,) if ide else ()))):
        try:
            canonical = matrix.canonical_name(name)
            # Locks are the exact selection. An unpinned recommended IDE is
            # shown prospectively, without acquiring or authorizing it.
            component = matrix.resolve_provider(name, lock=lock) if name in lock.get("capability-providers", {}) else matrix.resolve_provider(
                name, dict(policy.minimums).get(name), choice=local.providers.get(canonical), recommended=recommendations.get(canonical))
            source = "checkout" if canonical in local.providers else "project recommends" if canonical in recommendations else "catalog"
            result[name] = (component, source) if component else ("", "")
        except ProjectConfigurationError:
            result[name] = ("unavailable", "catalog")
    return result
