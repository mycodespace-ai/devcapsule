"""Derive one checkout's launch plan from its documents: the resolve step, done by ``run``.

Answer 1 of the CLI UX redesign work order of 2026-10-24 and its principle
3: ``project run`` is the first-contact command and the return-to-work
command. It reads the project's manifest and lock, the home's
defaults and the checkout's record, derives the plan, asks only what it
cannot derive, and launches. Nothing derived is the user's to refresh:
the generated resolution is written here, every time, as the launch's own
artifact.

This module is the adapter between the documents on disk and the
in-memory :class:`Configuration`: it registers a checkout that has no record
yet, composes the checkout's selection (with a run-once IDE or agent laid
over it when asked), derives and writes the resolution, and hands the
launch a :class:`ResolvedProject`. Asking the developer is the command's
job; the structured decisions come from the listing.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
import shlex
from typing import Any, Mapping

from devcapsule.compat import DecisionPending
from devcapsule.materialization import validate_base_image
from devcapsule.project import sanitize_name
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix, known_base_image

from .authorization import authorized_base_selection
from .capabilities import CapabilityPolicy, LocalCapabilities, RequirementDeparture, resolution_recommendations
from .capability_commands import pin_selection, release_deselected
from .capability_selection import compose_lock, effective_lock, local_pins, inspection_capabilities, inspection_providers, known_policy_names
from .console_requests import deferred_rows
from .file_formats import ProjectConfigurationError, canonical_digest, render_checkout, render_toml
from .listing import Listing, assess_checkout
from .model import Configuration
from .manifest_document import Recommendations
from .trust import HomeTrust
from .storage import (
    project_platform,
    ResolvedProject,
    atomic_write,
    checkout_record_paths,
    find_checkout_record,
    load_checkout,
    load_toml,
    load_settings, config_root,
    named_checkout_record_paths,
    recommendation_lock_for,
    resolved_record_path,
)
from .file_formats import selected_version_lock
from .docker_arguments import arguments_path, read_arguments, read_environment

__all__ = ["CheckoutState", "Selection", "derive_plan", "load_state", "register_checkout"]


class Selection:
    """A checkout's capability selections, omissions and provider choices, editable in memory."""

    def __init__(self, local: LocalCapabilities, surfaces: Mapping[str, str]) -> None:
        self.surfaces = set(surfaces)
        self._ide = next((name for name in local.selected if name in surfaces), None)
        self.extra = {name for name in local.selected if name not in surfaces}
        self.providers = dict(local.providers)
        self.without = set(local.without)

    @property
    def ide(self) -> str | None:
        return self._ide

    @ide.setter
    def ide(self, value: str | None) -> None:
        self._ide = value
        self.providers = {name: component for name, component in self.providers.items()
                          if name not in self.surfaces or name == value}

    def local(self) -> LocalCapabilities:
        selected = {*self.extra} | ({self.ide} if self.ide else set())
        return LocalCapabilities(tuple(sorted(selected)), tuple(sorted(self.without)), dict(self.providers))

    def use(self, matrix: ResolutionMatrix, policy: CapabilityPolicy, recommendations: Recommendations,
            capability: str, component: str) -> None:
        """Choose a provider without adding or authorizing its capability."""
        name = matrix.canonical_name(capability)
        providers = matrix.providers(name)
        if len(providers) < 2:
            raise ProjectConfigurationError(f"{name!r} has no provider choice; supplied by {', '.join(providers) or 'the base'}.")
        active = set(known_policy_names(policy, matrix).values()) | {matrix.canonical_name(item) for item in self.local().selected}
        if recommendations.ide:
            active.add(matrix.canonical_name(recommendations.ide))
        if name not in active:
            raise ProjectConfigurationError(f"{name!r} is not selected; use 'config add {name}' or 'config ide {name}' first.")
        if component == "default":
            self.providers.pop(name, None)
        else:
            minimums = {matrix.canonical_name(key): minimum for key, minimum in policy.minimums}
            matrix.resolve_provider(name, minimums.get(name), choice=component)
            self.providers[name] = component


class CheckoutState:
    """One checkout's documents as loaded for a launch, registered or not, writing nothing on load."""

    def __init__(self, root: Path, manifest: dict[str, Any]) -> None:
        self.root = root
        self.manifest = manifest
        self.platform = project_platform(root)
        self.matrix = MATRICES[self.platform]
        self.surfaces = {name: self.matrix.resolve_provider(name) or name for name in self.matrix.ide_capabilities()}
        self.lock_path, self.shared_lock = recommendation_lock_for(root, manifest)
        self.home = load_settings()
        # The named departures of this launch from the project's contract
        # (``project run --ide IDE --force``). In memory only: the manifest,
        # the lock and the record are never written with them.
        self.departures: tuple[RequirementDeparture, ...] = ()
        record = find_checkout_record(manifest, root)
        self.input_path: Path | None = record
        self.checkout: dict[str, Any] = load_checkout(record, manifest, root) if record is not None else tomllib.loads(
            render_checkout(manifest, root, {}, {})
        )
        if record is None:
            try:
                self.input_path, _ = checkout_record_paths(manifest, root)
            except ProjectConfigurationError:
                self.input_path = None  # the default record belongs to another checkout of this project
        self.saved_environment: dict[str, str | None] = {}
        if record is not None:
            read_arguments(arguments_path(record))  # Malformed storage is a refusal.
            try:
                self.saved_environment = read_environment(arguments_path(record))
            except ProjectConfigurationError:
                # Ambiguous Docker tokens remain literal passthrough. They
                # cannot establish answers to declared environment inputs.
                self.saved_environment = {}

    @property
    def registered(self) -> bool:
        return self.input_path is not None and self.input_path.is_file()

    @property
    def policy(self) -> CapabilityPolicy:
        """The policy this launch derives from: the manifest's, with this launch's departures set aside."""
        return CapabilityPolicy.read(self.manifest).departing(self.departures)

    def required_ide(self) -> str | None:
        """The IDE capability the project requires, as declared, or None."""
        return next((name for name in CapabilityPolicy.read(self.manifest).required if self.matrix.is_ide(name)), None)

    def depart(self, departure: RequirementDeparture) -> None:
        """Add one named departure for this launch; adding the same one again changes nothing."""
        if departure not in self.departures:
            self.departures = (*self.departures, departure)

    def composed_lock(self, checkout: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """The shared lock, or the checkout's version set, with the checkout's pins laid over it."""
        document = self.checkout if checkout is None else checkout
        selected = selected_version_lock(document)
        if selected is not None and selected.get("platform") != str(self.platform):
            raise ProjectConfigurationError("Local version set is for another platform; follow the project explicitly.")
        return compose_lock(self.manifest, selected if selected is not None else self.shared_lock, document, policy=self.policy)

    def listing(self, checkout: Mapping[str, Any] | None = None, *, check_display: bool = True) -> Listing:
        document = self.checkout if checkout is None else checkout
        lock = self.composed_lock(document)
        reference = document.get("authorization", {}).get("base-image", {}).get("reference") or lock.get("base", {}).get("reference")
        try:
            selection = authorized_base_selection(lock, document, required=False, trust=HomeTrust.read(self.home))
        except ProjectConfigurationError:
            selection = None  # The listing reports an invalid or stale selection below.
        if selection is not None:
            reference = selection.reference
        base = known_base_image(str(reference))
        access_lock, versions = inspection_capabilities(self.manifest, lock, document, policy=self.policy)
        providers = inspection_providers(self.manifest, lock, document)
        listing = assess_checkout(
            self.manifest, self.shared_lock, lock, document,
            home_path=config_root(), home=self.home, saved_environment=self.saved_environment,
            surfaces=self.surfaces, project=self.root, registered=self.registered,
            access_lock=access_lock, capability_versions=versions,
            capability_providers=providers,
            base_display=base.contract.display if check_display and base is not None else None,
            departures=self.departures,
        )
        return Listing(listing.rows + tuple(deferred_rows(self.input_path, self.root)), listing.notes, listing.departures)

    def with_selection(self, selection: Selection, *, allow_unverified: bool = False,
                       checkout: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """A copy of the checkout document with ``selection`` pinned, for a run-once IDE or agent."""
        document = deepcopy(dict(self.checkout if checkout is None else checkout))
        local = selection.local()
        local.validate(self.policy)
        previous = LocalCapabilities.read(document)
        selected = selected_version_lock(document)
        version_record = document.pop("version-set", None)
        source = deepcopy(selected if selected is not None else self.shared_lock)
        if selected is not None:
            release_deselected(source, self.matrix, self.policy, previous, local,
                               recommendations=resolution_recommendations(self.manifest))
        pins = pin_selection(self.matrix, self.policy, local, source, previous,
                             local_pins(document), allow_unverified=allow_unverified,
                             recommendations=resolution_recommendations(self.manifest))
        document["capabilities"] = {"selected": list(local.selected), "without": list(local.without),
                                    "lock": render_toml(pins), **({"providers": local.providers} if local.providers else {})}
        if version_record is not None:
            version_record["lock"] = render_toml(compose_lock(self.manifest, source, document,
                reset_providers=tuple(set(previous.providers) - set(local.providers)), policy=self.policy))
            document["version-set"] = version_record
        return document


def load_state(root: Path, manifest: dict[str, Any]) -> CheckoutState:
    return CheckoutState(root, manifest)


def register_checkout(state: CheckoutState, *, write: bool = True) -> Path:
    """Give an unregistered checkout its record: the project's default one, or one named after its directory.

    Answer 14 of the work order: ``run`` registers a second checkout of the
    same project by itself, with a name derived from its path; each checkout
    keeps its own record and inherits nothing.
    """
    if state.registered:
        assert state.input_path is not None
        return state.input_path
    if state.input_path is None:
        base = sanitize_name(state.root.name).lower().lstrip("._-") or "checkout"
        for suffix in ("", *(f"-{index}" for index in range(2, 100))):
            candidate, _ = named_checkout_record_paths(state.manifest, f"{base}{suffix}")
            if f"{base}{suffix}" != "default" and not candidate.exists():
                state.input_path = candidate
                break
        else:
            raise ProjectConfigurationError(f"No free checkout name derived from {state.root.name!r}; register one with 'checkout register NAME'.")
    assert state.input_path is not None
    if write:
        atomic_write(state.input_path, render_toml(state.checkout))
    return state.input_path


def derive_plan(state: CheckoutState, checkout: Mapping[str, Any] | None = None, *, write: bool = True) -> ResolvedProject:
    """Derive the launch plan from the state's documents and write it as the checkout's resolution.

    ``checkout`` is the record to derive from when it differs from the one
    on disk, for a run-once IDE or agent. The review must be ready: every
    decision answered; the caller asks or exits 3 before coming here. A
    local base override is validated against the daemon, as the resolve
    step did.
    """
    document = dict(state.checkout if checkout is None else checkout)
    composed = state.composed_lock(document)
    try:
        lock = effective_lock(state.manifest, composed, document, warn=False, policy=state.policy)
    except ProjectConfigurationError as exc:
        if selected_version_lock(document) is None:
            raise
        command = shlex.join(["devcapsule", "project", "--path", str(state.root), "versions"])
        raise DecisionPending(
            f"Saved version set {canonical_digest(composed)[:12]} cannot run this project: {exc}\n"
            f"Follow the project with {command} follow-project --apply, or select a compatible set with "
            f"{command} select SET. Nothing was written."
        ) from exc
    if not lock.get("components", {}).get("interactive-surface"):
        raise ProjectConfigurationError("Choose your IDE for this checkout: devcapsule project config ide IDE.")
    configuration = Configuration(state.manifest, lock, document, state.home, departures=state.departures)
    configuration.review().require_ready(state.root)
    resolution = configuration.resolve()
    trust = HomeTrust.read(state.home)
    base_selection = authorized_base_selection(lock, document, trust=trust) if "base" in lock else None
    if base_selection is not None and base_selection.local_image_identity is not None:
        # Looked up through the operations adapter, the one seam the launch
        # and its tests patch for the local daemon.
        from . import operations
        local_base = operations.required_local_image(base_selection.reference)
        validate_base_image(local_base, platform=str(lock["platform"]), expected_identity=base_selection.local_image_identity)
    assert state.input_path is not None
    resolution_path = resolved_record_path(state.input_path)
    if write:
        atomic_write(resolution_path, render_toml(resolution.document()))
    return ResolvedProject(state.root, state.manifest, state.lock_path, lock, state.input_path, document,
                           resolution_path, resolution.document(), state.departures)
