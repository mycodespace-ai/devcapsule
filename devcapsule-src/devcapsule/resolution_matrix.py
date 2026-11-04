"""The resolution matrix: capability needs × platform → a verified formation.

The capability table is the one place the launcher learns what a capability
is. Its keys are capability names. Each Capability lists alternative providing
components in catalog order and an ide flag for the single IDE role. Empty
providers mean the base supplies it. Dependencies belong to components, not
to this table. Base pins declare supplied versions; None means unpinned.

The user expresses capability needs; this module looks up component versions
that satisfy those needs on a platform, constrained by what has been tested
(D-0007). Verification is a fact about a combination and does not expire:
the matrix accumulates **verified edges** — (component version, base
version, platform) with the evidence that verified them — plus **declared
couplings** for component pairs with an integration surface, which need
jointly verified version pairs. Components without a declared coupling
compose freely on a shared verified base (default orthogonality). New
releases append rows; removal is explicit retirement, never an implicit
effect of newer versions arriving.

Resolution selects the newest verified combination and is a pure offline
derivation: same need, same matrix ⇒ identical lock bytes. It needs no
network and never probes the container daemon, because the daemon is
exactly the capability that requires explicit authorization.

The generated lock follows the scoped-digest principle: it records a digest
of exactly the inputs it derives from — the normalized capability set — and
nothing more. The recorded ``resolution-matrix-version`` is informational
per ``R-COMPAT-001``: a newer client's matrix changes what would be
*generated next time*, never the validity of a lock that stands.

The public surface is deliberately minimal (Parnas): ``MATRICES`` keyed by
``Platform``, ``ResolutionMatrix`` with ``capabilities``/``normalize``/
``resolve``, the ``Formation`` a resolution returns, and
``ResolutionError``. Everything else — the capability taxonomy, the pins,
the selection policy, the evidence, the lock rendering — is this module's
secret.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from devcapsule.images.contract import (
    CONTAINED_DISPLAY,
    EMBEDDED_RUNTIME,
    HOST_X11_ONLY_DISPLAY,
    LAUNCHER_SUPPLIED_RUNTIME,
    LEGACY_RECIPE_SOURCE_PATH,
    RECIPE_SOURCE_PATH,
    BaseContract,
    BaseImage,
    Provenance,
)
from devcapsule.images.tooling import NODE_VERSION, TEMURIN_VERSION, MAVEN_VERSION
from devcapsule.configuration.capabilities import meets_minimum, requirement
from devcapsule.platforms import Platform
from devcapsule.components.catalog import COMPONENTS
from devcapsule.components.playwright_pin import PIN as PLAYWRIGHT_PIN
from devcapsule.components.eclipse_native_pin import PACKAGES as ECLIPSE_NATIVE_PACKAGES
from devcapsule.components.linux_arm64_pins import COMPONENT_LOCK_TABLES as LINUX_ARM64_LOCK_TABLES
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
    canonical_digest,
    quote_toml,
    render_toml_scalar,
)

__all__ = [
    "MATRICES",
    "Formation",
    "ResolutionError",
    "ResolutionMatrix",
]


class ResolutionError(ProjectConfigurationError):
    """The need cannot be satisfied by any verified combination.

    The message is complete and displayable; callers show it verbatim.
    """


_MATRIX_VERSION = "embedded-31"


# --------------------------------------------------------------------------
# The internal model: pins carry their lock fragment verbatim (the literal
# stays visually diffable against the generated lock), the typed wrappers
# carry what resolution needs to know about them.


@dataclass(frozen=True)
class Capability:
    """Alternative providers in catalog order, and whether this is the IDE."""

    providers: tuple[str, ...] = ()
    ide: bool = False


@dataclass(frozen=True)
class _BasePin:
    """One base image and the capabilities it ships."""

    mnemonic: str
    # The family of base releases this pin belongs to — see _VerifiedEdge:
    # a validation is recorded against the family, so every release in it
    # (rebuilds that vary only DevCapsule's own layer, such as the embedded
    # runtime PEX) inherits the validation instead of demanding a fresh
    # smoke. Opening a new family is a deliberate act for a substantial
    # change — a new OS release, a toolchain overhaul, or a runtime-plan
    # vocabulary older releases cannot execute (owner rulings 2026-09-02
    # and 2026-09-06, amending D-0007).
    base_family: str
    satisfies: Mapping[str, str | None]
    lock_table: Mapping[str, Any]
    # The contract's compatible-evolution version and the promises the
    # labels of that recipe carry; see base_contract. The family above is
    # the contract's incompatible-change line.
    recipe: int = 0
    display: str = HOST_X11_ONLY_DISPLAY
    runtime: str = LAUNCHER_SUPPLIED_RUNTIME
    source_revision: str | None = None
    # A clean public-source builder need not have a release tag.
    # False while the reference names an image its registry does not hold
    # yet: only a locally built base of the same recipe stands in for it.
    published: bool = True

    @property
    def contract(self) -> BaseContract:
        return BaseContract(
            family=self.base_family, recipe=self.recipe, services=frozenset(self.satisfies),
            display=self.display, runtime=self.runtime,
        )

    @property
    def image(self) -> BaseImage:
        return BaseImage(
            contract=self.contract,
            reference=str(self.lock_table["reference"]),
            built=Provenance(
                builder=str(self.lock_table.get("build-mnemonic", "unknown")),
                source_revision=self.source_revision,
                recipe_path=str(self.lock_table.get("recipe-source", LEGACY_RECIPE_SOURCE_PATH)),
            ),
        )


@dataclass(frozen=True)
class _VerifiedEdge:
    """One validated (component version, base family) pair and its evidence.

    ``base_family`` names the family of base releases the validation holds
    for, not one base: a smoke establishes that the component runs on that
    OS and toolchain surface, and every base pin declaring the same family
    inherits the result. ``evidence`` says what established it — which
    smoke, on which concrete base, when — or that the entry is provisional
    and what would convert it.
    """

    component_id: str
    component_version: str
    base_family: str
    evidence: str


@dataclass(frozen=True)
class _ComponentPin:
    """One component version and its lock fragment."""

    component_id: str
    version: str
    lock_table: Mapping[str, Any]


@dataclass(frozen=True)
class _Coupling:
    """Two components with an integration surface needing joint verification."""

    first_id: str
    second_id: str
    verified: frozenset[tuple[str, str]]
    evidence: str


@dataclass(frozen=True)
class Formation:
    """One resolved formation, ready to be committed as a lock.

    ``resolved`` maps capabilities to selected providers (None for base services).
    It is derivation metadata; it does not change the rendered lock format.

    ``unverified`` is empty for a fully verified formation; otherwise it
    names the combinations the matrix has no evidence for — resolution
    proceeded past them at the caller's explicit request (owner ruling
    2026-09-03: the matrix may be stale or wrong, so a sophisticated user
    goes through with a gentle warning, not a brutal refusal).
    """

    capabilities: tuple[str, ...]
    provenance: str
    resolved: Mapping[str, str | None] = field(default_factory=dict)
    unverified: tuple[str, ...] = ()
    _document: Mapping[str, Any] = field(repr=False, default_factory=dict)
    _header: str = field(repr=False, default="")

    def render_lock(self) -> str:
        """The exact platform-lock bytes to write and commit."""

        return self._header + _render_document(self._document)


class ResolutionMatrix:
    """One platform's accumulated verified combinations.

    Clients know three operations: ``capabilities()`` (the askable
    vocabulary), ``normalize()`` (canonical, vocabulary-checked form of a
    need), and ``resolve()`` (a ``Formation`` or a ``ResolutionError``).
    """

    def __init__(
        self,
        *,
        platform: Platform,
        matrix_version: str,
        bases: tuple[_BasePin, ...],
        components: Mapping[str, tuple[_ComponentPin, ...]],
        edges: tuple[_VerifiedEdge, ...],
        couplings: tuple[_Coupling, ...],
        capability_table: Mapping[str, Capability],
        materialization: Mapping[str, Mapping[str, Any]],
    ) -> None:
        # Bases and per-component pins are append-only, newest last;
        # resolution prefers the newest verified combination.
        self._platform = platform
        self._matrix_version = matrix_version
        self._bases = bases
        self._components = components
        self._verified = {
            (edge.component_id, edge.component_version, edge.base_family): edge
            for edge in edges
        }
        self._couplings = couplings
        self._capability_table = dict(capability_table)
        self._materialization = materialization

    def base_family(self, lock: Mapping[str, Any]) -> str | None:
        reference = lock.get("base", {}).get("reference")
        return next((base.base_family for base in self._bases
                     if base.lock_table.get("reference") == reference), None)

    def base_unpublished(self, reference: str) -> bool:
        """Whether the pinned base at ``reference`` is not in its registry yet."""
        return any(base.lock_table.get("reference") == reference and not base.published for base in self._bases)

    def base_image(self, reference: str) -> BaseImage | None:
        """The pinned base at ``reference``, described by its contract."""
        return next((base.image for base in self._bases
                     if base.lock_table.get("reference") == reference), None)

    def base_images(self) -> tuple[BaseImage, ...]:
        return tuple(base.image for base in self._bases)

    def compatibility_report(self, lock: Mapping[str, Any]) -> tuple[str, ...]:
        """Say which locked components are validated for the lock's base, and why.

        The rule is the contract's: a component validated on a family runs on
        every base of that family whose recipe is at least the one it was
        validated on, because recipes only add within a family; a new family
        is an incompatible change and inherits nothing.
        """
        reference = lock.get("base", {}).get("reference")
        image = self.base_image(str(reference)) if reference else None
        if image is None:
            return (f"Base {reference} is not pinned by this DevCapsule's matrix; compatibility is not tracked for it.",)
        lines = [
            f"Compatibility: components validated on family {image.contract.family} run on "
            f"{image.contract.identity}, because a newer recipe of a family only adds services; "
            "a new family would be an incompatible change and would need fresh validation.",
        ]
        evidence, missing = self.validation_evidence(lock)
        lines.extend(f"  validated: {item}" for item in evidence)
        lines.extend(f"  not validated: {item}" for item in missing)
        return tuple(lines)

    def validation_evidence(self, lock: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Describe accumulated evidence, without inventing whole-set testing."""
        family = self.base_family(lock)
        evidence, missing = [], []
        components = lock.get("components", {})
        for name, metadata in components.items():
            if not isinstance(metadata, dict):
                continue
            version = metadata.get("version")
            edge = self._verified.get((name, str(version), family)) if family is not None else None
            pins = self._components.get(name, ())
            # Version text alone cannot certify different executable bytes.
            pin = next((pin for pin in pins if pin.version == version), None)
            def identity(value: Mapping[str, Any]) -> dict[str, Any]:
                return {key: identity(item) if isinstance(item, dict) else item
                        for key, item in value.items() if key not in {"url", "integrity"}}
            if edge is not None and pin is not None and identity(metadata) == identity(pin.lock_table):
                evidence.append(f"{name} {version}: {edge.evidence}")
            else:
                missing.append(f"{name} {version} on base {lock.get('base', {}).get('reference')}")
        for coupling in self._couplings:
            if coupling.first_id in components and coupling.second_id in components:
                pair = (components[coupling.first_id]["version"], components[coupling.second_id]["version"])
                if pair in coupling.verified:
                    evidence.append(coupling.evidence)
                else:
                    missing.append(f"{coupling.first_id} {pair[0]} with {coupling.second_id} {pair[1]}")
        return tuple(evidence), tuple(missing)

    def capabilities(self) -> tuple[str, ...]:
        """The capability vocabulary, defined only by the capability table."""
        return tuple(sorted(self._capability_table))

    def canonical_name(self, name: str) -> str:
        """Accept a component name when it unambiguously names one capability."""
        if name in self._capability_table:
            return name
        matches = [key for key, entry in self._capability_table.items() if entry.providers == (name,)]
        if not matches:
            matches = [key for key, entry in self._capability_table.items() if name in entry.providers]
        if len(matches) == 1:
            return matches[0]
        raise ResolutionError(f"The embedded resolution matrix does not know {name!r}; supported capabilities: "
                              + ", ".join(self.capabilities()) + ".")

    def is_ide(self, capability: str) -> bool:
        return self._capability_table[self.canonical_name(capability)].ide

    def ide_capabilities(self) -> tuple[str, ...]:
        return tuple(name for name in self.capabilities() if self.is_ide(name))

    def providers(self, capability: str) -> tuple[str, ...]:
        """Alternative components in catalog order; empty for a base service."""
        return self._capability_table[self.canonical_name(capability)].providers

    def resolve_provider(self, capability: str, minimum: str | None = None,
                         lock: Mapping[str, Any] | None = None, *,
                         choice: str | None = None, recommended: str | None = None) -> str | None:
        """Resolve one capability; this is the only provider-selection function.

        Filter by the minimum first. An explicit checkout choice wins, then
        the project's recommendation, then the first eligible catalog provider.
        A named choice that cannot meet the minimum is an error, not permission
        to substitute software. A lock establishes an already resolved choice
        and exact versions; it never requests newer pins or other providers.
        Base services return None and are version-checked during base selection.
        Inputs are unchanged. Invalid names or unavailable choices raise ResolutionError.
        """
        providers = self.providers(capability)
        requested = choice if choice is not None else recommended
        if requested is not None and requested not in providers:
            raise ResolutionError(f"{requested!r} does not provide {capability!r}; providers: "
                                  + (", ".join(providers) or "the base") + ".")
        if not providers:
            return None
        if lock is not None:
            evidence = lock.get("capability-providers", {})
            recorded = evidence.get(capability, evidence.get(self.canonical_name(capability), []))
            choices = tuple(component for component in providers if component in recorded)
            if len(choices) > 1:
                raise ResolutionError(f"Lock names multiple providers for {capability!r}.")
            if choices:
                providers = choices
        eligible = list(providers)
        if minimum is not None:
            eligible = []
            for component in providers:
                versions: tuple[str | None, ...]
                if lock is not None:
                    metadata = lock.get("components", {}).get(component, {})
                    versions = (metadata.get("version"),) if isinstance(metadata, Mapping) else ()
                else:
                    versions = tuple(pin.version for pin in self._components.get(component, ()))
                if any(version is not None and meets_minimum(version, minimum) for version in versions):
                    eligible.append(component)
        requirement_text = capability if minimum is None else f"{capability}>={minimum}"
        if choice is not None:
            if choice not in eligible:
                raise ResolutionError(f"Provider {choice!r} cannot supply {requirement_text}; "
                                      "choose a compatible provider.")
            return choice
        if recommended is not None:
            if recommended not in eligible:
                raise ResolutionError(f"Provider {recommended!r} cannot supply {requirement_text}; "
                                      "choose a compatible provider.")
            return recommended
        if eligible:
            return eligible[0]
        if lock is not None:
            raise ResolutionError("missing supported providers: " + ", ".join(providers))
        available = ", ".join(f"{component} {pin.version}" for component in providers
                              for pin in self._components.get(component, ()))
        raise ResolutionError(f"No provider supplies {capability} {minimum or ''} or newer; catalog supplies {available or 'none'}.")

    def component_pins(self) -> dict[str, Mapping[str, Any]]:
        """The latest embedded table for each component on this platform."""
        return {name: pins[-1].lock_table for name, pins in self._components.items() if pins}

    @property
    def platform(self) -> Platform:
        return self._platform

    def component_pin(self, component: str, version: object) -> Mapping[str, Any] | None:
        """This platform's embedded table for one component version, or None."""
        return next((pin.lock_table for pin in self._components.get(component, ()) if pin.version == version), None)

    def component_closure(self, capability: str, minimum: str | None = None,
                          lock: Mapping[str, Any] | None = None, *,
                          choice: str | None = None, recommended: str | None = None) -> tuple[str, ...]:
        """The chosen provider and its transitive component dependencies."""
        component = self.resolve_provider(capability, minimum, lock, choice=choice, recommended=recommended)
        result = [component] if component else []
        for name in result:
            definition = COMPONENTS.get(name)
            if definition is not None:
                result.extend(item for item in definition.required_components() if item not in result)
        return tuple(sorted(result))

    def supplied_version(self, capability: str, lock: Mapping[str, Any]) -> str | None:
        """The version established by the exact base reference or locked provider."""
        name = self.canonical_name(capability)
        if self.providers(name):
            component = self.resolve_provider(name, lock=lock)
            return lock.get("components", {}).get(component, {}).get("version")
        reference = lock.get("base", {}).get("reference")
        base = next((item for item in self._bases if item.lock_table.get("reference") == reference), None)
        return base.satisfies.get(name) if base else None

    def normalize(self, need: object) -> tuple[str, ...]:
        """Normalize a list of capability names: sorted, unique, known."""

        if not isinstance(need, Sequence) or isinstance(need, (str, bytes)):
            raise ResolutionError("The capability requirements must be an array of capability names.")
        names: set[str] = set()
        for item in need:
            if not isinstance(item, str) or not item:
                raise ResolutionError(
                    "Capability requirement entries must be non-empty strings."
                )
            names.add(self.canonical_name(item))
        return tuple(sorted(names))

    def resolve(self, need: object, *, allow_unverified: bool = False, project_only: bool = False,
                choices: Mapping[str, str] | None = None, recommendations: Mapping[str, str] | None = None) -> Formation:
        """Derive one complete formation from a capability set, offline.

        Fully verified resolution is always tried first, so the escape hatch
        never degrades a need the matrix can satisfy.  Only when that fails
        and ``allow_unverified`` is set does resolution fall back to the base
        with the fewest unverified combinations (newest on ties), naming each
        one in the formation for the caller's gentle warning and the lock.
        """

        if not isinstance(need, Sequence) or isinstance(need, (str, bytes)):
            raise ResolutionError("The capability requirements must be an array of capability names.")
        if any(not isinstance(item, str) or not item for item in need):
            raise ResolutionError("Capability requirement entries must be non-empty strings.")
        declarations = [requirement(item) for item in need]
        capabilities = self.normalize([name for name, _ in declarations])
        minimums = {self.canonical_name(name): minimum for name, minimum in declarations if minimum is not None}
        choices = {self.canonical_name(name): value for name, value in (choices or {}).items()}
        recommendations = {self.canonical_name(name): value for name, value in (recommendations or {}).items()}
        resolved = {name: self.resolve_provider(name, minimums.get(name),
                    choice=choices.get(name), recommended=recommendations.get(name)) for name in capabilities}
        ide_names = [name for name in capabilities if self.is_ide(name)]
        surface_id = (None if project_only and not ide_names else self._selected_surface(capabilities, resolved))
        required = [surface_id] if surface_id else []
        for name in capabilities:
            provider = resolved[name]
            if provider is not None and provider not in required:
                required.append(provider)
        for component in required:
            definition = COMPONENTS.get(component)
            if definition is not None:
                required.extend(item for item in definition.required_components() if item not in required)
        component_minimums = {resolved[name]: minimum
                              for name, minimum in minimums.items() if self.providers(name)}
        candidates = {component: tuple(pin for pin in self._components[component]
                                      if component not in component_minimums
                                      or meets_minimum(pin.version, component_minimums[component]))
                      for component in required}
        base_needs = {name for name in capabilities if not self.providers(name)}
        bases = tuple(base for base in self._bases if not base_needs - set(base.satisfies)
                      and all(meets_minimum(base.satisfies.get(name), minimums[name])
                              for name in base_needs if name in minimums))
        if not bases:
            for name in sorted(base_needs & minimums.keys()):
                versions = ", ".join(dict.fromkeys(base.satisfies.get(name) or "unknown" for base in self._bases))
                families = ", ".join(dict.fromkeys(base.base_family.replace("ubuntu-", "Ubuntu ") for base in self._bases))
                if not any(meets_minimum(base.satisfies.get(name), minimums[name]) for base in self._bases):
                    raise ResolutionError(f"no base supplies {name} {minimums[name]} or newer; the {families} bases supply {versions}")

        for base in reversed(bases):
            chosen = self._verified_selection(required, base, candidates)
            if chosen is not None:
                return self._formation(capabilities, surface_id, base, chosen, minimums=minimums, resolved=resolved)

        # Nothing fully validated. What the user reads from here on is the
        # owner's 2026-09-06 ruling: a missing validation is a fact about
        # the matrix's knowledge, not about the request, so the message
        # names the exact elements the experiment would run — components,
        # versions, base; never the model's own vocabulary — and offers the
        # experiment. Only a base that does not ship a needed toolchain is a
        # refusal on grounds, and it says that --unverified cannot help.
        fallback = self._unverified_selection(required, bases, candidates)
        if fallback is None:
            gaps = [
                f"{base.mnemonic}: does not ship "
                + ", ".join(sorted(base_needs - set(base.satisfies)))
                for base in reversed(self._bases)
            ]
            raise ResolutionError(
                "No base ships everything this project needs:\n  "
                + "\n  ".join(gaps)
                + "\n--unverified cannot help here: a base that does not ship a "
                "needed toolchain is a hard refusal."
            )
        base, chosen, unverified = fallback
        if allow_unverified:
            return self._formation(
                capabilities, surface_id, base, chosen, unverified=unverified, minimums=minimums, resolved=resolved
            )
        raise ResolutionError(
            "Not yet validated: "
            + "; ".join(unverified)
            + ".\nRun it as an experiment with --unverified; the lock will record "
            "what is unvalidated for everyone who uses it."
        )

    def _selected_surface(self, capabilities: tuple[str, ...], resolved: Mapping[str, str | None]) -> str:
        interactive = sorted(set(capabilities) & set(self.ide_capabilities()))
        if not interactive:
            choices = ", ".join(self.ide_capabilities())
            raise ResolutionError(
                "The V1 environment needs an interactive-surface capability to select "
                f"its surface; select exactly one of {choices}."
            )
        if len(interactive) > 1:
            raise ResolutionError(
                "A V1 platform lock holds exactly one interactive surface, but "
                f"the requirements select {', '.join(interactive)}; keep exactly one."
            )
        provider = resolved[interactive[0]]
        assert provider is not None
        return provider

    def _verified_selection(
        self, required: list[str], base: _BasePin, candidates: Mapping[str, tuple[_ComponentPin, ...]]
    ) -> dict[str, _ComponentPin] | None:
        """The newest verified pin of every required component on this base,
        or None when some component or coupling lacks verification there."""

        chosen: dict[str, _ComponentPin] = {}
        for component_id in required:
            pin = next(
                (
                    candidate
                    for candidate in reversed(candidates[component_id])
                    if (component_id, candidate.version, base.base_family) in self._verified
                ),
                None,
            )
            if pin is None:
                return None
            chosen[component_id] = pin
        for coupling in self._couplings:
            if coupling.first_id in chosen and coupling.second_id in chosen:
                pair = (
                    chosen[coupling.first_id].version,
                    chosen[coupling.second_id].version,
                )
                if pair not in coupling.verified:
                    return None
        return chosen

    def _unverified_selection(
        self, required: list[str], bases: tuple[_BasePin, ...], candidates: Mapping[str, tuple[_ComponentPin, ...]]
    ) -> tuple[_BasePin, dict[str, _ComponentPin], tuple[str, ...]] | None:
        """The capability-satisfying base with the fewest unverified pairs.

        Base capabilities stay a hard constraint — a base that does not ship
        a needed toolchain cannot be forced.  Verification is the only rule
        relaxed: components keep their newest verified pin where one exists
        in the base's family and fall back to their newest pin otherwise,
        with every such fallback (and every unverified coupling) named in
        the words the user reads: component, version, base.
        """

        best: tuple[_BasePin, dict[str, _ComponentPin], tuple[str, ...]] | None = None
        for base in reversed(bases):
            chosen: dict[str, _ComponentPin] = {}
            unverified: list[str] = []
            for component_id in required:
                pins = candidates[component_id]
                verified_pin = next(
                    (
                        candidate
                        for candidate in reversed(pins)
                        if (component_id, candidate.version, base.base_family)
                        in self._verified
                    ),
                    None,
                )
                if verified_pin is not None:
                    chosen[component_id] = verified_pin
                    continue
                newest = pins[-1]
                chosen[component_id] = newest
                unverified.append(f"{component_id} {newest.version} on base {base.mnemonic}")
            for coupling in self._couplings:
                if coupling.first_id in chosen and coupling.second_id in chosen:
                    pair = (
                        chosen[coupling.first_id].version,
                        chosen[coupling.second_id].version,
                    )
                    if pair not in coupling.verified:
                        unverified.append(
                            f"{coupling.first_id} {pair[0]} with "
                            f"{coupling.second_id} {pair[1]} (integration not validated)"
                        )
            if best is None or len(unverified) < len(best[2]):
                best = (base, chosen, tuple(unverified))
        return best

    def _formation(
        self,
        capabilities: tuple[str, ...],
        surface_id: str | None,
        base: _BasePin,
        chosen: Mapping[str, _ComponentPin],
        unverified: tuple[str, ...] = (),
        minimums: Mapping[str, str] | None = None,
        resolved: Mapping[str, str | None] | None = None,
    ) -> Formation:
        components: dict[str, Any] = {}
        if surface_id is not None:
            components.update({"interactive-surface": surface_id,
                               surface_id: dict(chosen[surface_id].lock_table)})
        for component_id, pin in chosen.items():
            if component_id != surface_id:
                components[component_id] = dict(pin.lock_table)
        document: dict[str, Any] = {
            "devcapsule-lock-format-version": 1,
            "resolution-matrix-version": self._matrix_version,
            "platform": self._platform.value,
            # The scoped digest: the one derivation input beside the platform,
            # which the filename already carries.
            "capabilities-digest": canonical_digest({"need": [f"{name}>={minimums[name]}" if minimums and name in minimums else name
                                                       for name in capabilities]}),
            "base": dict(base.lock_table),
            "components": components,
            "materialization": dict(self._materialization[surface_id]) if surface_id else {},
        }
        header = (
            "# Generated by 'devcapsule project init' from the embedded resolution "
            f"matrix {self._matrix_version}.\n"
            "# Commit this file: it pins the exact environment collaborators receive.\n"
        )
        provenance = (
            f"embedded resolution matrix {self._matrix_version}: "
            + (f"{surface_id} {chosen[surface_id].version} on base {base.mnemonic}"
             if surface_id else f"project tools on base {base.mnemonic}")
        )
        if unverified:
            # The lock shape is scalars and tables, so the list travels as one
            # scalar; collaborators regenerating the lock see the same warning.
            document["unverified-combinations"] = "; ".join(unverified)
            header += (
                "# WARNING: an experiment. Not yet validated: "
                + "; ".join(unverified)
                + ".\n"
            )
            provenance += f" (experiment; not yet validated: {'; '.join(unverified)})"
        return Formation(
            capabilities=capabilities,
            provenance=provenance,
            resolved=dict(resolved or {}),
            unverified=unverified,
            _document=document,
            _header=header,
        )


# --------------------------------------------------------------------------
# The validated data. Pins below are lock fragments verbatim; edges record
# what validated each (component version, base family) pair; advancing the
# generated formation advances _MATRIX_VERSION.

# Base families (owner rulings 2026-09-02 and 2026-09-06, amending D-0007):
# validations are recorded per family, so base releases in the same family
# share them. One family exists today. The older one — ubuntu-24.04 bases
# up to v026, whose embedded runtime predated the vscode-adapter runtime
# plans — was retired on 2026-09-06 together with the v026 pin
# (docker.io/mycodespaceai/devcapsule-base@sha256:695f9eb6…3ec07394a) and
# the validations recorded only against it, once no need selected it any
# more; D-0007 makes retirement an explicit act, recorded here.
_BASE_FAMILY_UBUNTU_24_04 = "ubuntu-24.04"

# The v0.2.8 base (recipe version 5) ships CPython, the Docker CLI suite,
# Node.js, the Temurin JDK plus Maven, and the PostgreSQL client; these
# capabilities are satisfied by the base and never a lock entry. Its
# embedded runtime PEX understands the vscode adapter.
_V0_2_8_BASE = _BasePin(
    mnemonic="v0.2.8",
    base_family=_BASE_FAMILY_UBUNTU_24_04,
    satisfies={"python": "3.12", "docker-cli": None, "node": NODE_VERSION, "java": TEMURIN_VERSION, "maven": MAVEN_VERSION},
    recipe=5,
    display=HOST_X11_ONLY_DISPLAY,
    runtime=EMBEDDED_RUNTIME,
    lock_table={
        "reference": (
            "docker.io/mycodespaceai/devcapsule-base"
            "@sha256:8be27a7773bdb58e8d4d2f05283752736d12c2062e4c566d33d7f2e71ef336db"
        ),
        "build-mnemonic": "v0.2.8",
        "contract": "ubuntu-24.04@5",
    },
)

# The v0.2.9 base (a recipe-version-5 rebuild embedding the 0.2.9 runtime,
# pushed 2026-09-02, digest sha256:ca9f7961…734232) was retired on
# 2026-09-06 when the owner withdrew the 0.2.9 release from GitHub and
# Docker Hub, after v0.2.10 below had been pushed and validated: 0.2.9
# shipped codex as a single plucked binary, fixed after its tag. The pin
# leaves with the release, explicitly, per D-0007; the family's
# validations it inherited are unaffected, and the evidence strings below
# that name the v0.2.9 image stay as the record of where each smoke ran.
# Nothing selected v0.2.9 once v0.2.10 was pinned, so no generated
# formation changes and _MATRIX_VERSION does not advance.

# The v0.2.10 base (recipe version 6: no boot contract in the base, the
# formation recipe sets its own) embeds the released 0.2.10 PEX, built
# from the tag revision 2415029; same family, same toolchain, so it
# inherits every validation. A first push (13:50 UTC, digest
# 76a07cb9…d39a45) carried a pre-tag PEX from bd8283b and was replaced
# by the owner's rebuild from the released PEX, pushed 2026-09-06
# 22:48 UTC; the digest below was read from the registry after that
# push. Its evidence is the owner's 2026-09-06 trading-research smoke
# on the locally built twin and the same day's dogfood run (this
# repository's three-agent formation on the first push).
_V0_2_10_BASE = _BasePin(
    mnemonic="v0.2.10",
    base_family=_BASE_FAMILY_UBUNTU_24_04,
    satisfies={"python": "3.12", "docker-cli": None, "node": NODE_VERSION, "java": TEMURIN_VERSION, "maven": MAVEN_VERSION},
    recipe=6,
    display=HOST_X11_ONLY_DISPLAY,
    runtime=LAUNCHER_SUPPLIED_RUNTIME,
    lock_table={
        "reference": (
            "docker.io/mycodespaceai/devcapsule-base"
            "@sha256:4bb691b556a2cb9acffa4c0adddd9ada66864ee3c81f4f00ca35e9df9056bf9c"
        ),
        "build-mnemonic": "v0.2.10",
        "contract": "ubuntu-24.04@6",
    },
)

# The v0.2.12 base (recipe version 9) adds the contained display stack —
# TigerVNC's Xvnc, the core X fonts, noVNC with websockify, Openbox, and
# the tint2 panel — and the label the launcher reads to give the capsule
# its own desktop instead of the host's X session. Same family, same OS
# and toolchain, and the base carries no runtime (the launcher supplies its
# own executable, D-0009), so it inherits every validation below. Built by
# the v0.2.12-rc5 executable from its tag revision 3d09ab4 and pushed on
# 2026-09-14; the digest was read from the registry after the push and the
# registry copy re-inspected (recipe 9, display=contained, tint2 present).
# The recipe-8 predecessor (v0.2.12-rc3, digest 3a6e6eb6…6d7b9c, pushed
# 2026-09-13) is retired here, explicitly per D-0007: only the v0.2.12-rc4
# candidate ever pinned it, and the owner accepted the recipe-9 desktop
# shape on 2026-09-14 after the rc3 desktop proved unrecoverable from a
# browser once a window was minimized. Evidence for the display: the
# owner's 2026-09-13 and 2026-09-14 dogfood sessions of this repository's
# three-agent formation in the contained desktop, on locally built twins
# of both recipes from the same sources, and the recursive successor run
# on the recipe-9 twin.
_V0_2_12_BASE = _BasePin(
    # The 0.2.12 release base, ubuntu-24.04@9, built by the rc5 executable;
    # the mnemonic records the builder, the contract names the base.
    mnemonic="v0.2.12-rc5",
    base_family=_BASE_FAMILY_UBUNTU_24_04,
    satisfies={"python": "3.12", "docker-cli": None, "node": NODE_VERSION, "java": TEMURIN_VERSION, "maven": MAVEN_VERSION},
    recipe=9,
    display=CONTAINED_DISPLAY,
    runtime=LAUNCHER_SUPPLIED_RUNTIME,
    lock_table={
        "reference": (
            "docker.io/mycodespaceai/devcapsule-base"
            "@sha256:8837edd36720763796ab9fe1dbeb66f1aa7ca2db0dabc8d73a58716440f42f7c"
        ),
        "build-mnemonic": "v0.2.12-rc5",
        "contract": "ubuntu-24.04@9",
    },
)

# The v0.3.0-rc6 base (recipe version 11) adds the web console under
# /opt/devcapsule-webconsole over recipe 9: recipe 10 added the console,
# and recipe 11 its process and resource monitor. Same family, same OS
# and toolchain, and the launcher supplies the runtime, so it inherits
# every validation below. Costin Cozianu built it with the published
# v0.3.0-rc6 executable from tag revision 2ed8ecf536b0d653056ac35792cae413a6d6732a
# and pushed it on 2026-10-25 as mycodespaceai/devcapsule-base:v0.3.0.rc6.
# The digest was read from the registry and the copy re-inspected by digest
# (linux/amd64, recipe 11, display=contained, runtime=launcher-supplied,
# all six services and the web console root). Evidence: the owner's
# 2026-10-25 test on the locally built twin of this recipe, with the
# console's configuration page working after PR #281 repaired the rc5
# regression. The recipe-9 pin remains; retirement is explicit under D-0007.
_V0_3_0_RC6_BASE = _BasePin(
    mnemonic="v0.3.0-rc6",
    base_family=_BASE_FAMILY_UBUNTU_24_04,
    satisfies={
        "python": "3.12", "docker-cli": None, "node": NODE_VERSION,
        "java": TEMURIN_VERSION, "maven": MAVEN_VERSION, "postgresql-client": None,
    },
    recipe=11,
    display=CONTAINED_DISPLAY,
    runtime=LAUNCHER_SUPPLIED_RUNTIME,
    lock_table={
        "reference": (
            "docker.io/mycodespaceai/devcapsule-base"
            "@sha256:8c97d308b4ac8172ce91ef4f96406063bfcd85a55efb09d4a23e795b10a834a3"
        ),
        "build-mnemonic": "v0.3.0-rc6",
        "contract": "ubuntu-24.04@11",
        "recipe-source": RECIPE_SOURCE_PATH,
    },
)

# Recipe-11 rebuild from clean public source 12a30fa60322de585810048881ee166fcdb26854,
# published 2026-10-31 before RC9 under the owner's base-first decision. The
# console layer contains #330's browser-port cookie isolation; the other five
# filesystem layers match the rc6 base. The launcher still supplies the runtime.
# The mnemonic is the builder's real identity, not an invented candidate tag.
# Keep the rc6 pin for existing locks; new resolutions select this last pin.
_V0_3_0_COOKIE_FIX_BASE = _BasePin(
    mnemonic="v0.3.0-local-linux-x86_64",
    source_revision="12a30fa60322de585810048881ee166fcdb26854",
    base_family=_BASE_FAMILY_UBUNTU_24_04,
    satisfies={
        "python": "3.12", "docker-cli": None, "node": NODE_VERSION,
        "java": TEMURIN_VERSION, "maven": MAVEN_VERSION, "postgresql-client": None,
    },
    recipe=11,
    display=CONTAINED_DISPLAY,
    runtime=LAUNCHER_SUPPLIED_RUNTIME,
    lock_table={
        "reference": (
            "docker.io/mycodespaceai/devcapsule-base"
            "@sha256:d7047ced8556cd35964fcc058a1101cf2b5b202f7a5daa2fdd434dcda5ed82c9"
        ),
        "build-mnemonic": "v0.3.0-local-linux-x86_64",
        "contract": "ubuntu-24.04@11",
        "recipe-source": RECIPE_SOURCE_PATH,
    },
)

# Vendor release metadata and complete archive checksums verified 2026-10-04.
_DOTNET_SDK_10_0_401 = _ComponentPin(
    component_id="dotnet-sdk", version="10.0.401",
    lock_table={
        "version": "10.0.401", "platform": "linux-amd64",
        "delivery-policy": "local-materialization", "license": "MIT",
        "url": "https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.401/dotnet-sdk-10.0.401-linux-x64.tar.gz",
        "sha256": "137268c8ad939c064ff1ee2a6fdf0899d8725377114ea012fbd1ad5fa2550418",
        "upstream-sha512": "51c8b999af9e8dd9998c9edc5944e19a90788862068acd38694e098889054ce8c23d4f0c5cccfa16bf187d044562359e5ee69a9f8ad0bbe913ba90311fbce25b",
    },
)

_RIDER_2026_2_3_1 = _ComponentPin(
    component_id="rider", version="2026.2.3.1",
    lock_table={
        "version": "2026.2.3.1", "delivery-policy": "local-materialization",
        "license": "Proprietary", "terms-url": "https://www.jetbrains.com/legal/docs/toolbox/license/",
        "url": "https://download.jetbrains.com/rider/JetBrains.Rider-2026.2.3.1.tar.gz",
        "sha256": "fa4b09a5f7cf4b6635b093adc7313991778a8dc74f25614a2b8976b04dee5d4e",
    },
)

_ECLIPSE_2026_09 = _ComponentPin(
    component_id="eclipse", version="2026-09-R",
    lock_table={
        "version": "2026-09-R", "variant": "java",
        "native-packages": ECLIPSE_NATIVE_PACKAGES,
        "delivery-policy": "local-materialization",
        "terms-url": "https://www.eclipse.org/legal/epl-2.0/",
        "url": "https://download.eclipse.org/technology/epp/downloads/release/2026-09/R/eclipse-java-2026-09-R-linux-gtk-x86_64.tar.gz",
        "sha256": "1a836dcedcc353567f164964ecb251bf0477cffb26dec1cc49bcf6ec12d82eca",
        "upstream-sha512": "483af23506520a37e96857dbafc74e36194152b10471c558b1c2a31b34053f5f20af4a5d88509acb7cfa38bd2aff3fa7e6e45159ff827260cdf8838c46bd73a4",
    },
)

_INTELLIJ_2026_2_3 = _ComponentPin(
    component_id="intellij", version="2026.2.3",
    lock_table={
        "version": "2026.2.3", "variant": "unified",
        "delivery-policy": "local-materialization",
        "url": "https://download.jetbrains.com/idea/idea-2026.2.3.tar.gz",
        "sha256": "68751c8ae4d49407251cd197df795fbed91b6fdc85d10c73c4649a99e496ab37",
    },
)

_PYCHARM_2026_2_0_1 = _ComponentPin(
    component_id="pycharm",
    version="2026.2.0.1",
    lock_table={
        "version": "2026.2.0.1",
        "variant": "professional",
        "delivery-policy": "local-materialization",
        "url": "https://download.jetbrains.com/python/pycharm-2026.2.0.1.tar.gz",
        "sha256": "4a37cb2d15703553c61e814d8e014bfa47308508470de5f968c4e9645b771675",
    },
)

# VSCodium 1.126.04524 is the latest published release as of 2026-08-31; the
# checksum was recomputed locally from the downloaded archive and matches the
# published .sha256 asset. MIT-licensed free/libre binaries, so caching them
# in local environment images needs no per-developer acquisition terms.
_CODIUM_1_126_04524 = _ComponentPin(
    component_id="codium",
    version="1.126.04524",
    lock_table={
        "version": "1.126.04524",
        "delivery-policy": "local-materialization",
        "license": "MIT",
        "url": (
            "https://github.com/VSCodium/vscodium/releases/download/"
            "1.126.04524/VSCodium-linux-x64-1.126.04524.tar.gz"
        ),
        "sha256": "adf3548df055d18e476cdee887488ba7486b879ad99a31a546c6b5c5ff296c24",
    },
)

# Visual Studio Code 1.143.1 (commit e646868227c3e3a9e3f24277c8c7220be42c0be7),
# queried from Microsoft's official stable update feed on 2026-10-28; the
# downloaded linux-x64 tar.gz matches sha256hash verbatim. Proprietary
# Microsoft binary acquired on the user's machine under vscode-download or
# home trust (vscode), never redistributed in published DevCapsule images.
_VSCODE_1_143_1 = _ComponentPin(
    component_id="vscode",
    version="1.143.1",
    lock_table={
        "version": "1.143.1",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "vscode-download",
        "license": "Proprietary",
        "terms-url": "https://code.visualstudio.com/license",
        "url": (
            "https://vscode.download.prss.microsoft.com/dbazure/download/stable/"
            "e646868227c3e3a9e3f24277c8c7220be42c0be7/code-stable-x64-1792691793.tar.gz"
        ),
        "sha256": "48f658052e54e020a1c1be7b37ac0f9ae39f07e8ccda805c63f053cfda72b2be",
    },
)

# Codex is pinned as npm publishes it (owner direction 2026-09-05, replacing
# the single-binary extraction that dropped the bundled bubblewrap, ripgrep,
# zsh and code-mode host — see the 2026-09-05 bug record): the meta package
# `@openai/codex` at the component level carries the node launcher, and the
# per-platform artifact is the package the meta's optionalDependencies alias
# for that platform. Both tarballs are the exact npm registry artifacts; the
# sha256 values were computed locally from downloads whose sha512 matched
# the registry's integrity fields. The artifact digests below are unchanged
# from the extraction era; only the meta package is new.
_CODEX_0_145_0 = _ComponentPin(
    component_id="codex",
    version="0.145.0",
    lock_table={
        "version": "0.145.0",
        "delivery-policy": "local-materialization",
        "license": "Apache-2.0",
        "npm-package": "@openai/codex",
        "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.145.0.tgz",
        "sha256": "416399796cac371d1a033b17f34b08ba9b25c8f298a5b9d00e10f72c3b128c8d",
        "artifacts": {
            "linux-amd64": {
                "npm-package": "@openai/codex-linux-x64",
                "url": (
                    "https://registry.npmjs.org/@openai/codex/-/"
                    "codex-0.145.0-linux-x64.tgz"
                ),
                "sha256": (
                    "11239480f8e3efd1430f23bbe91c1a397856b8bbe6185ccbaee2382d25e03df2"
                ),
            }
        },
    },
)

# 0.153.0 advances the pin at the owner's direction 2026-09-03 (the CLI's
# own update notice during the demo-project conversions). The platform
# tarball's sha512 was verified against the npm registry integrity and the
# sha256 computed locally from the same download; the binary was executed
# hands-on (`codex-cli 0.153.0`). The former integration/acp-version
# metadata is gone with the coupling removal (see the couplings note
# below): codex is a standalone CLI component, and locks no longer
# advertise a jetbrains-ai-assistant integration DevCapsule does not
# deliver.
_CODEX_0_153_0 = _ComponentPin(
    component_id="codex",
    version="0.153.0",
    lock_table={
        "version": "0.153.0",
        "delivery-policy": "local-materialization",
        "license": "Apache-2.0",
        "npm-package": "@openai/codex",
        "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.153.0.tgz",
        "sha256": "0dc1968cc6075929d70d7ab1421122743a9f8237a8cc9ac69e2e8f2768798fef",
        "artifacts": {
            "linux-amd64": {
                "npm-package": "@openai/codex-linux-x64",
                "url": (
                    "https://registry.npmjs.org/@openai/codex/-/"
                    "codex-0.153.0-linux-x64.tgz"
                ),
                "sha256": (
                    "856f408ea61b44a381b7d6fb7c82365dfcef649ae2a340fc01282cf63c30cd8a"
                ),
            }
        },
    },
)

# 0.153.4 advances the pin at the owner's direction 2026-09-05, together
# with the npm delivery and the seeded configuration: the registry's
# `latest` tag on that day (published 2026-09-04). Both tarballs' sha512
# matched the registry integrity fields, the sha256 values were computed
# from the same downloads, the platform archive's member set is unchanged
# from 0.153.0, and the extracted binary was executed hands-on
# (`codex-cli 0.153.4`) including loading the seeded config.toml.
_CODEX_0_153_4 = _ComponentPin(
    component_id="codex",
    version="0.153.4",
    lock_table={
        "version": "0.153.4",
        "delivery-policy": "local-materialization",
        "license": "Apache-2.0",
        "npm-package": "@openai/codex",
        "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.153.4.tgz",
        "sha256": "fd04263c1adfa1d285c6c0ad86a97cab508d3012ee9eab80a99f773cc4b2fb3a",
        "artifacts": {
            "linux-amd64": {
                "npm-package": "@openai/codex-linux-x64",
                "url": (
                    "https://registry.npmjs.org/@openai/codex/-/"
                    "codex-0.153.4-linux-x64.tgz"
                ),
                "sha256": (
                    "54818cb9fce3360cc6e44cfc5a96952cd5c1243efb43cbe488e11dda84663e08"
                ),
            }
        },
    },
)

_CLAUDE_CODE_2_1_227 = _ComponentPin(
    component_id="claude-code",
    version="2.1.227",
    lock_table={
        "version": "2.1.227",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "claude-code-download",
        "license": "Proprietary",
        "terms-url": "https://www.anthropic.com/legal/commercial-terms",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": (
                    "https://downloads.claude.ai/claude-code-releases/"
                    "2.1.227/linux-x64/claude"
                ),
                "sha256": (
                    "6832dc3f1797b890b71116e5f2dbbf9a83fd3d0498c235b4b0f9cd0e6e499ad6"
                ),
            }
        },
    },
)

# 2.1.236 is the stable channel as of 2026-09-03 (the Fable 5.1 release the
# owner directed the update for). The sha256 was computed locally from the
# downloaded binary the same day and matches the vendor manifest's linux-x64
# checksum; the binary was executed hands-on ("2.1.236 (Claude Code)").
_CLAUDE_CODE_2_1_236 = _ComponentPin(
    component_id="claude-code",
    version="2.1.236",
    lock_table={
        "version": "2.1.236",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "claude-code-download",
        "license": "Proprietary",
        "terms-url": "https://www.anthropic.com/legal/commercial-terms",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": (
                    "https://downloads.claude.ai/claude-code-releases/"
                    "2.1.236/linux-x64/claude"
                ),
                "sha256": (
                    "6c8818fa22187aa555c242be4abbacc44d6b71a32ac9631ee7b2b5d12f51f752"
                ),
            }
        },
    },
)

# 2.1.261 advances the pin at the owner's direction 2026-09-04 (the vendor's
# latest, built the same day). The linux-x64 binary's sha256 and size match
# the vendor manifest, and the binary was executed hands-on
# ("2.1.261 (Claude Code)").
_CLAUDE_CODE_2_1_261 = _ComponentPin(
    component_id="claude-code",
    version="2.1.261",
    lock_table={
        "version": "2.1.261",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "claude-code-download",
        "license": "Proprietary",
        "terms-url": "https://www.anthropic.com/legal/commercial-terms",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": (
                    "https://downloads.claude.ai/claude-code-releases/"
                    "2.1.261/linux-x64/claude"
                ),
                "sha256": (
                    "4ae40dd1784e85753e742e09f267d29ecbb82890361ad3817d27560866d364a6"
                ),
            }
        },
    },
)

# The official Antigravity channel serves latest-only, but the artifacts are
# versioned and immutable in GCS; this pin is a deliberate curation. The
# sha256 was computed locally from the downloaded archive (2026-09-02, and
# re-verified with the archive member name on the same date); upstream-sha512
# is the checksum the vendor manifest published for the same bytes, recorded
# as provenance. See the workstream's license and redistribution analysis.
_ANTIGRAVITY_CLI_1_1_24 = _ComponentPin(
    component_id="antigravity-cli",
    version="1.1.24",
    lock_table={
        "version": "1.1.24",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "antigravity-download",
        "license": "Proprietary",
        "terms-url": "https://antigravity.google/terms/",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": (
                    "https://storage.googleapis.com/antigravity-public/"
                    "antigravity-cli/1.1.24-6130423206641664/linux-x64/"
                    "cli_linux_x64.tar.gz"
                ),
                "sha256": (
                    "cff1fb7ed735da72c35658645a4f916cf74f020d4cd30ab95ebe8c2a49a4d569"
                ),
                "archive-member": "antigravity",
                "upstream-sha512": (
                    "ed4df91ea7ced986aa14507a0ab8225d92985190f7d551010eba0c46c569587e"
                    "602cb36af81c9cde7af0d6b380e8dd3a82131361806cd96012d44a3e47fb369a"
                ),
            }
        },
    },
)

# 2026-09-27 GA refresh: exact downloads verified against vendor checksums.
_CODEX_0_157_1 = _ComponentPin(
    component_id="codex",
    version="0.157.1",
    lock_table={
        "version": "0.157.1",
        "delivery-policy": "local-materialization",
        "license": "Apache-2.0",
        "npm-package": "@openai/codex",
        "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.157.1.tgz",
        "sha256": "813e2a944f4474b7e1826d9ce8bf696ad8d80c68f43f7a7067beec51fa8f5b73",
        "artifacts": {
            "linux-amd64": {
                "npm-package": "@openai/codex-linux-x64",
                "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.157.1-linux-x64.tgz",
                "sha256": "7f12677740f439fe4884c7031d9d703e571cecf5ea9fa3a05abd1bbccc2162a8"
            }
        }
    },
)

_CLAUDE_CODE_2_1_283 = _ComponentPin(
    component_id="claude-code",
    version="2.1.283",
    lock_table={
        "version": "2.1.283",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "claude-code-download",
        "license": "Proprietary",
        "terms-url": "https://www.anthropic.com/legal/commercial-terms",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": "https://downloads.claude.ai/claude-code-releases/2.1.283/linux-x64/claude",
                "sha256": "1859583ce32920595c61ef868bee52e1b1594f7486db209935e01f1e5e804ae2"
            }
        }
    },
)

_ANTIGRAVITY_CLI_1_2_12 = _ComponentPin(
    component_id="antigravity-cli",
    version="1.2.12",
    lock_table={
        "version": "1.2.12",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "antigravity-download",
        "license": "Proprietary",
        "terms-url": "https://antigravity.google/terms/",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.2.12-5784551402897408/linux-x64/cli_linux_x64.tar.gz",
                "sha256": "26c7c4c661d6c9beda734fcf305031056a6ea46e697c4533e8151179724e2950",
                "archive-member": "antigravity",
                "upstream-sha512": "d5f0fe7433cb7c43ea878c07627a4fdb82d218f3bef5e6436266f5d9fdd2df145523453b9be0c4250391a64a007f5f42f7faff797bc2b2d502e7efb4874e383a"
            }
        }
    },
)

# 2026-10-18 GA refresh for 0.3.0: exact downloads verified against vendor
# checksums (npm SHA-512 integrity, the Claude manifest SHA-256, the
# Antigravity manifest SHA-512) before the SHA-256 values below were recorded.
_CODEX_0_163_0 = _ComponentPin(
    component_id="codex",
    version="0.163.0",
    lock_table={
        "version": "0.163.0",
        "delivery-policy": "local-materialization",
        "license": "Apache-2.0",
        "npm-package": "@openai/codex",
        "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.163.0.tgz",
        "sha256": "1a71db36560bb446d2c2e63ae675c4a3018c38ace38ca533f8d1b25d3e6555b4",
        "artifacts": {
            "linux-amd64": {
                "npm-package": "@openai/codex-linux-x64",
                "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.163.0-linux-x64.tgz",
                "sha256": "30efc97738b975940d78b59a9bea115fa34040b732807d54ec35ae6b7528de94"
            }
        }
    },
)

_CLAUDE_CODE_2_1_302 = _ComponentPin(
    component_id="claude-code",
    version="2.1.302",
    lock_table={
        "version": "2.1.302",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "claude-code-download",
        "license": "Proprietary",
        "terms-url": "https://www.anthropic.com/legal/commercial-terms",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": "https://downloads.claude.ai/claude-code-releases/2.1.302/linux-x64/claude",
                "sha256": "60d7eb7f12fbb28a52533fe8be5884097403562aa02dc73991a021c7067e29a5"
            }
        }
    },
)

_ANTIGRAVITY_CLI_1_4_2 = _ComponentPin(
    component_id="antigravity-cli",
    version="1.4.2",
    lock_table={
        "version": "1.4.2",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "antigravity-download",
        "license": "Proprietary",
        "terms-url": "https://antigravity.google/terms/",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.4.2-4835981233356800/linux-x64/cli_linux_x64.tar.gz",
                "sha256": "6395837ac0e193dd3fe50f1228e1c4aea345ca99636d54404ab7e74397d4091c",
                "archive-member": "antigravity",
                "upstream-sha512": "4a393afc1369cee94e817c1b430c9128d02b12ebd4d5703ace5cd47b2333e216d673fb0097cbf7195f757b110163ba9850e9eea3fdbbaddd4b25668b82c03f05"
            }
        }
    },
)

# 2026-10-31 RC9 refresh: complete downloads verified against vendor integrity.
_CODEX_0_166_0 = _ComponentPin(
    component_id="codex",
    version="0.166.0",
    lock_table={
        "version": "0.166.0",
        "delivery-policy": "local-materialization",
        "license": "Apache-2.0",
        "npm-package": "@openai/codex",
        "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.166.0.tgz",
        "sha256": "67ee6f4069d9328956401f54ac202c20369233159058af9f4ec1af731b87f5b7",
        "artifacts": {
            "linux-amd64": {
                "npm-package": "@openai/codex-linux-x64",
                "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.166.0-linux-x64.tgz",
                "sha256": "cbc00a26d3d0e2ceefc4be8891f8a81ef1e349b3b175bc0ae308762bc001fd93"
            }
        }
    },
)


_CLAUDE_CODE_2_1_314 = _ComponentPin(
    component_id="claude-code",
    version="2.1.314",
    lock_table={
        "version": "2.1.314",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "claude-code-download",
        "license": "Proprietary",
        "terms-url": "https://www.anthropic.com/legal/commercial-terms",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": "https://downloads.claude.ai/claude-code-releases/2.1.314/linux-x64/claude",
                "sha256": "4487042b4c4f5d88d4568f68ae98aae0b1ffae58864cf57fb868641bc5f84594"
            }
        }
    },
)


_ANTIGRAVITY_CLI_1_4_12 = _ComponentPin(
    component_id="antigravity-cli",
    version="1.4.12",
    lock_table={
        "version": "1.4.12",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "antigravity-download",
        "license": "Proprietary",
        "terms-url": "https://antigravity.google/terms/",
        "distribution": "user-acquired-not-redistributed",
        "artifacts": {
            "linux-amd64": {
                "url": "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.4.12-4768735748292608/linux-x64/cli_linux_x64.tar.gz",
                "sha256": "3368d1923fc869f21ec8fce83252a8c96c89283aac9393958ac91fbf7a3949e4",
                "archive-member": "antigravity",
                "upstream-sha512": "ea01c73b772187bca928852cf96235f0d846d6da5ebdac188b9ae719597465737f325540d483ee5f3f62d151029001713344972a187ddfb98cc7b97f7204b7f4"
            }
        }
    },
)


# 2026-10-31 stable IDE updates; prior pins remain readable by existing locks.
_PYCHARM_2026_2_4 = _ComponentPin(
    component_id="pycharm",
    version="2026.2.4",
    lock_table={
        "version": "2026.2.4",
        "variant": "professional",
        "delivery-policy": "local-materialization",
        "url": "https://download.jetbrains.com/python/pycharm-2026.2.4.tar.gz",
        "sha256": "87d39ae1125f7298e8f8c4b96aac836043eb15053f8dc5d7c52356eaab5762a8",
    },
)


_INTELLIJ_2026_2_4 = _ComponentPin(
    component_id="intellij", version="2026.2.4",
    lock_table={
        "version": "2026.2.4", "variant": "unified",
        "delivery-policy": "local-materialization",
        "url": "https://download.jetbrains.com/idea/idea-2026.2.4.tar.gz",
        "sha256": "cc6b29ddb82c7dcc656d5c728cefb2c917ac767eb4b8368f1208732846fbb5bd",
    },
)


_RIDER_2026_2_4 = _ComponentPin(
    component_id="rider", version="2026.2.4",
    lock_table={
        "version": "2026.2.4", "delivery-policy": "local-materialization",
        "license": "Proprietary", "terms-url": "https://www.jetbrains.com/legal/docs/toolbox/license/",
        "url": "https://download.jetbrains.com/rider/JetBrains.Rider-2026.2.4.tar.gz",
        "sha256": "6e5ac7238a5b95f905b9a1404c42eb4d7bc5566d950750b0078f20bd78a3f599",
    },
)


_CODIUM_1_143_17232 = _ComponentPin(
    component_id="codium",
    version="1.143.17232",
    lock_table={
        "version": "1.143.17232",
        "delivery-policy": "local-materialization",
        "license": "MIT",
        "url": "https://github.com/VSCodium/vscodium/releases/download/1.143.17232/VSCodium-linux-x64-1.143.17232.tar.gz",
        "sha256": "ca1895aa040bd91a09c709d79eac7862d8c1aa0237fdc25b503deeb8bcd87efd",
    },
)


_VSCODE_1_144_0 = _ComponentPin(
    component_id="vscode",
    version="1.144.0",
    lock_table={
        "version": "1.144.0",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": "vscode-download",
        "license": "Proprietary",
        "terms-url": "https://code.visualstudio.com/license",
        "url": "https://vscode.download.prss.microsoft.com/dbazure/download/stable/2c33b50b16c472efe58357d1d2a8a5414bc23fbf/code-stable-x64-1793133762.tar.gz",
        "sha256": "17b72a7e6f40a5b5dce9850f10eea13ce734a63052b67fa021cc01e715ad4cf1",
    },
)


_POSTGRESQL_CLIENT_16 = _ComponentPin(
    component_id="postgresql-client",
    version="16",
    lock_table={
        "version": "16",
        "delivery-policy": "base-image",
        "license": "PostgreSQL",
    },
)

_LINUX_AMD64_MATRIX = ResolutionMatrix(
    platform=Platform.LINUX_AMD64,
    matrix_version=_MATRIX_VERSION,
    bases=(_V0_2_8_BASE, _V0_2_10_BASE, _V0_2_12_BASE, _V0_3_0_RC6_BASE, _V0_3_0_COOKIE_FIX_BASE),
    components={
        "pycharm": (_PYCHARM_2026_2_0_1, _PYCHARM_2026_2_4),
        "intellij": (_INTELLIJ_2026_2_3, _INTELLIJ_2026_2_4),
        "eclipse": (_ECLIPSE_2026_09,),
        "rider": (_RIDER_2026_2_3_1, _RIDER_2026_2_4),
        "dotnet-sdk": (_DOTNET_SDK_10_0_401,),
        "playwright": (_ComponentPin("playwright", str(PLAYWRIGHT_PIN["version"]), PLAYWRIGHT_PIN),),
        "codium": (_CODIUM_1_126_04524, _CODIUM_1_143_17232),
        "vscode": (_VSCODE_1_143_1, _VSCODE_1_144_0),
        "codex": (_CODEX_0_145_0, _CODEX_0_153_0, _CODEX_0_153_4, _CODEX_0_157_1, _CODEX_0_163_0, _CODEX_0_166_0),
        "claude-code": (
            _CLAUDE_CODE_2_1_227,
            _CLAUDE_CODE_2_1_236,
            _CLAUDE_CODE_2_1_261,
            _CLAUDE_CODE_2_1_283,
            _CLAUDE_CODE_2_1_302,
            _CLAUDE_CODE_2_1_314,
        ),
        "antigravity-cli": (_ANTIGRAVITY_CLI_1_1_24, _ANTIGRAVITY_CLI_1_2_12, _ANTIGRAVITY_CLI_1_4_2, _ANTIGRAVITY_CLI_1_4_12),
        "postgresql-client": (_POSTGRESQL_CLIENT_16,),
    },
    edges=(
        _VerifiedEdge(
            "vscode", "1.144.0", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window/pixel startup passed on pinned v0.3.0-rc6 "
            "recipe-11 base, 2026-10-31 run 20261031T011314Z-518a42; "
            "welcome/sign-in screen; no saved-edit or persistence check",
        ),
        _VerifiedEdge(
            "codium", "1.143.17232", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window/pixel startup passed on pinned v0.3.0-rc6 "
            "recipe-11 base, 2026-10-31 run 20261031T011008Z-702c9c; "
            "welcome/editor shell; no saved-edit or persistence check",
        ),
        _VerifiedEdge(
            "rider", "2026.2.4", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window/pixel startup passed on pinned v0.3.0-rc6 "
            "recipe-11 base, 2026-10-31 run 20261031T011314Z-518a42; "
            "first-use agreement; SDK fixture built and ran; editor acceptance remains",
        ),
        _VerifiedEdge(
            "intellij", "2026.2.4", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window/pixel startup passed on pinned v0.3.0-rc6 "
            "recipe-11 base, 2026-10-31 run 20261031T011314Z-518a42; "
            "first-use agreement; editor acceptance remains",
        ),
        _VerifiedEdge(
            "pycharm", "2026.2.4", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window/pixel startup passed on pinned v0.3.0-rc6 "
            "recipe-11 base, 2026-10-31 run 20261031T011008Z-702c9c; "
            "first-use agreement; editor acceptance remains",
        ),
        _VerifiedEdge(
            "antigravity-cli", "1.4.12", _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed RC9 refresh 2026-10-31; vendor checksums "
            "verified; pinned v0.3.0-rc6 recipe-11 startup/configuration smoke passed; "
            "interactive "
            "provider acceptance awaits the downloaded candidate",
        ),
        _VerifiedEdge(
            "claude-code", "2.1.314", _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed RC9 refresh 2026-10-31; vendor checksums "
            "verified; pinned v0.3.0-rc6 recipe-11 startup/configuration smoke passed; "
            "interactive "
            "provider acceptance awaits the downloaded candidate",
        ),
        _VerifiedEdge(
            "codex", "0.166.0", _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed RC9 refresh 2026-10-31; vendor checksums "
            "verified; pinned v0.3.0-rc6 recipe-11 startup/configuration smoke passed; "
            "interactive "
            "provider acceptance awaits the downloaded candidate",
        ),
        _VerifiedEdge("eclipse", "2026-09-R", _BASE_FAMILY_UBUNTU_24_04,
                      "Codex/gpt-6-astra noVNC saved-edit smoke passed on v0.2.12-rc5; 2026-10-04 run 20261004T090121Z-ea0a5b; child Playwright browser, WebKitGTK and persistent home configuration verified"),
        _VerifiedEdge("dotnet-sdk", "10.0.401", _BASE_FAMILY_UBUNTU_24_04,
                      "SDK 10.0.401 built and ran a net10.0 console app as the capsule user on v0.2.12-rc5; 2026-10-04 run 20261004T081836Z-932fc8"),
        _VerifiedEdge("rider", "2026.2.3.1", _BASE_FAMILY_UBUNTU_24_04,
                      "noVNC HTTP/window/pixel startup passed on v0.2.12-rc5; 2026-10-04 run 20261004T081836Z-932fc8; editor use requires license activation"),
        _VerifiedEdge("intellij", "2026.2.3", _BASE_FAMILY_UBUNTU_24_04,
                      "Codex/gpt-6-astra saved-edit graphical smoke passed 2026-10-04 on "
                      "v0.2.12-rc5 base; source ada153c; run 20261004T002435Z-d44b57"),
        _VerifiedEdge("playwright", "1.63.0", _BASE_FAMILY_UBUNTU_24_04,
                      "component-installed Chromium 153.0.8010.12 launched and rendered HTML "
                      "2026-10-04 on v0.2.12-rc5 base; source ada153c; run 20261004T002435Z-d44b57"),
        _VerifiedEdge(
            "codex",
            "0.157.1",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed 0.2.15 upgrade 2026-09-27; "
            "pinned v0.2.12-rc5 base startup/configuration smoke passed; "
            "interactive provider acceptance awaits the downloaded candidate",
        ),
        _VerifiedEdge(
            "claude-code",
            "2.1.283",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed 0.2.15 upgrade 2026-09-27; "
            "pinned v0.2.12-rc5 base startup/configuration smoke passed; "
            "interactive provider acceptance awaits the downloaded candidate",
        ),
        _VerifiedEdge(
            "antigravity-cli",
            "1.2.12",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed 0.2.15 upgrade 2026-09-27; "
            "pinned v0.2.12-rc5 base startup/configuration smoke passed; "
            "interactive provider acceptance awaits the downloaded candidate",
        ),
        _VerifiedEdge(
            "codex",
            "0.163.0",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: 0.3.0 agent freshness upgrade 2026-10-18; vendor "
            "checksums verified; startup and seeded-configuration smoke passed "
            "on the local recipe-11 base; interactive provider acceptance "
            "awaits the downloaded candidate",
        ),
        _VerifiedEdge(
            "claude-code",
            "2.1.302",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: 0.3.0 agent freshness upgrade 2026-10-18; vendor "
            "checksums verified; startup and seeded-configuration smoke passed "
            "on the local recipe-11 base; interactive provider acceptance "
            "awaits the downloaded candidate",
        ),
        _VerifiedEdge(
            "antigravity-cli",
            "1.4.2",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: 0.3.0 agent freshness upgrade 2026-10-18; vendor "
            "checksums verified; startup and seeded-configuration smoke passed "
            "on the local recipe-11 base; interactive provider acceptance "
            "awaits the downloaded candidate",
        ),
        # Every entry names the concrete base its evidence came from; the
        # validation holds for the whole family. "provisional" entries were
        # added at the owner's direction ahead of a smoke and say what
        # converts them.
        _VerifiedEdge(
            "pycharm",
            "2026.2.0.1",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner's 2026-09-05 dogfood session on the local "
            "v0.2.9 rebuild (formation e52aa7f4934b232e7972); converts on a "
            "recorded formation run naming a pinned base",
        ),
        _VerifiedEdge(
            "codium",
            "1.126.04524",
            _BASE_FAMILY_UBUNTU_24_04,
            "product-owner smoke 2026-09-02: tictactoe sample on the v0.2.8 "
            "base (config-history 20260902T075529Z)",
        ),
        _VerifiedEdge(
            "vscode",
            "1.143.1",
            _BASE_FAMILY_UBUNTU_24_04,
            "IDE smoke 2026-10-28 from a capsule on the v0.3.0-rc6 base: the "
            "desktop answered, a 'code' X11 window titled 'Visual Studio Code' "
            "owned the display, the recorded desktop kept (maintenance evidence "
            "2026-10-28-vscode); no relaunch or persistence check yet",
        ),
        _VerifiedEdge(
            "codex",
            "0.145.0",
            _BASE_FAMILY_UBUNTU_24_04,
            "product-owner smoke 2026-09-03: five-way formation (codium x "
            "antigravity x claude-code x codex) on the v0.2.9 base",
        ),
        _VerifiedEdge(
            "codex",
            "0.153.0",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed CLI update 2026-09-03, pending the "
            "demo-project three-provider spins",
        ),
        _VerifiedEdge(
            "codex",
            "0.153.4",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed CLI update 2026-09-05 with the npm "
            "delivery and the seeded configuration, pending the owner's "
            "sample-project smokes",
        ),
        _VerifiedEdge(
            "claude-code",
            "2.1.227",
            _BASE_FAMILY_UBUNTU_24_04,
            "product-owner smoke 2026-09-03: five-way formation (codium x "
            "antigravity x claude-code x codex) on the v0.2.9 base",
        ),
        _VerifiedEdge(
            "claude-code",
            "2.1.236",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed CLI update 2026-09-03, pending the "
            "next codium-formation smoke",
        ),
        _VerifiedEdge(
            "claude-code",
            "2.1.261",
            _BASE_FAMILY_UBUNTU_24_04,
            "provisional: owner-directed CLI update 2026-09-04, pending the "
            "demo-project three-provider spins",
        ),
        # A base-shipped component: the validation is that the base carries
        # the package the pin describes. Checked hands-on 2026-09-06 in the
        # v0.2.9 image: psql (PostgreSQL) 16.14, Ubuntu package
        # 16+257build1.1, identical to the retired v026 base's.
        _VerifiedEdge(
            "postgresql-client",
            "16",
            _BASE_FAMILY_UBUNTU_24_04,
            "package identity checked in the v0.2.9 base image 2026-09-06 "
            "(psql 16.14, the same build the retired v026 base shipped)",
        ),
        _VerifiedEdge(
            "antigravity-cli",
            "1.1.24",
            _BASE_FAMILY_UBUNTU_24_04,
            "product-owner smoke 2026-09-02: antigravity working the "
            "tictactoe sample (codium surface, v0.2.8 base)",
        ),
    ),
    # The codex x pycharm coupling is removed until further notice
    # (product-owner ruling 2026-09-03): the jetbrains-ai-assistant
    # integration it stood for is not a delivery we want — the IDE's AI
    # plugin installs its own codex copy and routes usage through the
    # developer's JetBrains-account quota on JetBrains backends, ignoring
    # the logged-in codex already on PATH. DevCapsule ships codex as a
    # standalone CLI component only; the coupling mechanism stays for
    # future jointly-verified integrations.
    couplings=(),
    capability_table={
        "python-ide": Capability(("pycharm",), ide=True),
        "java-ide": Capability(("intellij",), ide=True),
        "eclipse-ide": Capability(("eclipse",), ide=True),
        "dotnet-ide": Capability(("rider",), ide=True),
        "frontend-ide": Capability(("codium", "vscode"), ide=True),
        "vscode-ide": Capability(("vscode",), ide=True),
        "codex-agent": Capability(("codex",)),
        "claude-code-agent": Capability(("claude-code",)),
        "antigravity-agent": Capability(("antigravity-cli",)),
        "postgresql-client": Capability(("postgresql-client",)),
        "browser-automation": Capability(("playwright",)),
        "dotnet": Capability(("dotnet-sdk",)),
        "python": Capability(),
        "node": Capability(),
        "java": Capability(),
        "maven": Capability(),
        "docker-cli": Capability(),
    },
    # The materialization recipe follows the selected surface: each surface
    # family unpacks and fixes up its installation differently.
    materialization={
        "eclipse": {"recipe": "eclipse-local-materialization", "recipe-version": "3"},
        "rider": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
        "intellij": {"recipe": "jetbrains-local-materialization", "recipe-version": "1"},
        "pycharm": {
            "recipe": "jetbrains-local-materialization",
            "recipe-version": "1",
        },
        "codium": {
            "recipe": "vscode-local-materialization",
            # Version 2: the chrome-sandbox 4755 step is removed — renderers
            # run --no-sandbox (product-owner ruling 2026-09-02; see the
            # renderer-sandboxing design note).
            "recipe-version": "2",
        },
        "vscode": {
            "recipe": "vscode-local-materialization",
            "recipe-version": "2",
        },
    },
)

# The linux-arm64 base, recipe 11: the amd64 recipe-11 recipe built natively
# on an Apple Silicon Mac (Docker Desktop 29.3.1) on 2026-11-04 by
# `images build --type base --recipe ubuntu-24.04` from a launcher built at
# the public main commit b3f10b7d, whose devcapsule-webconsole the image
# installed. Inspected: linux/arm64, recipe 11 ready, display=contained,
# runtime=launcher-supplied, all six services, the web console root.
# Not published yet. The reference is the digest of the OCI image index in
# the builder's containerd store, which a push of this exact image to
# mycodespaceai/devcapsule-base keeps; a rebuild gets another digest and
# must be pinned again. Until the owner pushes it, a checkout selects the
# local image: `project config authorize base-image IMAGE`.
_LINUX_ARM64_RECIPE_11_BASE = _BasePin(
    mnemonic="v0.3.1.dev0-local-macos-aarch64",
    source_revision="b3f10b7d95aec659f268afecc03d0912a2e89d2f",
    base_family=_BASE_FAMILY_UBUNTU_24_04,
    satisfies={
        "python": "3.12", "docker-cli": None, "node": NODE_VERSION,
        "java": TEMURIN_VERSION, "maven": MAVEN_VERSION, "postgresql-client": None,
    },
    recipe=11,
    display=CONTAINED_DISPLAY,
    runtime=LAUNCHER_SUPPLIED_RUNTIME,
    published=False,
    lock_table={
        "reference": (
            "docker.io/mycodespaceai/devcapsule-base"
            "@sha256:7d32268065b60b6ad75139d23c1e6fbb2daa43b3f2c53d2856c5e2e39891652b"
        ),
        "build-mnemonic": "v0.3.1.dev0-local-macos-aarch64",
        "contract": "ubuntu-24.04@11",
        "recipe-source": RECIPE_SOURCE_PATH,
    },
)


def _on_linux_arm64(pin: _ComponentPin) -> _ComponentPin:
    """The arm64 build of a linux-amd64 pin: same version, its own artifacts.

    A base-delivered component carries no artifact and is the same pin on
    both platforms; every other pin must have its arm64 table, so an amd64
    version added without one fails here rather than at a user's launch.
    """

    table = LINUX_ARM64_LOCK_TABLES.get((pin.component_id, pin.version))
    if table is None and pin.lock_table.get("delivery-policy") == "base-image":
        return pin
    if table is None:
        raise AssertionError(f"{pin.component_id} {pin.version} has no linux-arm64 pin in components/linux_arm64_pins.py")
    return _ComponentPin(pin.component_id, pin.version, table)


# linux-arm64 offers the same vocabulary, versions and materialization
# recipes as linux-amd64; its bases, artifacts and verified edges are its
# own, because a validation on one architecture establishes nothing on another.
_LINUX_ARM64_MATRIX = ResolutionMatrix(
    platform=Platform.LINUX_ARM64,
    matrix_version=_MATRIX_VERSION,
    bases=(_LINUX_ARM64_RECIPE_11_BASE,),
    components={
        component: tuple(_on_linux_arm64(pin) for pin in pins)
        for component, pins in _LINUX_AMD64_MATRIX._components.items()
    },
    edges=(
        # Native IDE smokes on Apple Silicon (Docker Desktop 29.3.1) against
        # the local, unpublished arm64 recipe-11 base above. They establish
        # the IDE only: Playwright and the .NET SDK rode along unexercised.
        _VerifiedEdge(
            "codium", "1.143.17232", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window startup passed natively on the local arm64 recipe-11 base, "
            "2026-11-04 run 20261104T120158Z-e8f78f; VSCodium window; no pixel, saved-edit "
            "or persistence check",
        ),
        _VerifiedEdge(
            "vscode", "1.144.0", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window startup passed natively on the local arm64 recipe-11 base, "
            "2026-11-04 run 20261104T120217Z-ee18ce; Visual Studio Code window; no pixel, "
            "saved-edit or persistence check",
        ),
        _VerifiedEdge(
            "eclipse", "2026-09-R", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window startup passed natively on the local arm64 recipe-11 base, "
            "2026-11-04 run 20261104T120256Z-aa127a; workspace window; no pixel, saved-edit "
            "or persistence check",
        ),
        _VerifiedEdge(
            "pycharm", "2026.2.4", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window startup passed natively on the local arm64 recipe-11 base, "
            "2026-11-04 run 20261104T120351Z-38cdd0; splash window; first-use agreement and "
            "editor acceptance remain",
        ),
        _VerifiedEdge(
            "rider", "2026.2.4", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window startup passed natively on the local arm64 recipe-11 base, "
            "2026-11-04 run 20261104T120546Z-c9c1b3; splash window; first-use agreement and "
            "editor acceptance remain",
        ),
        _VerifiedEdge(
            "intellij", "2026.2.4", _BASE_FAMILY_UBUNTU_24_04,
            "noVNC HTTP/window startup passed natively on the local arm64 recipe-11 base, "
            "2026-11-04 run 20261104T121007Z-289109; splash window; first-use agreement and "
            "editor acceptance remain",
        ),
    ),
    couplings=(),
    capability_table=_LINUX_AMD64_MATRIX._capability_table,
    materialization=_LINUX_AMD64_MATRIX._materialization,
)

# The map is the platform authority: its keys are the supported platforms,
# total over the Platform enum (D-0006/D-0007). Clients index it with a
# Platform member, from host detection or a lock, never a key built from parts.
MATRICES: Mapping[Platform, ResolutionMatrix] = MappingProxyType(
    {
        Platform.LINUX_AMD64: _LINUX_AMD64_MATRIX,
        Platform.LINUX_ARM64: _LINUX_ARM64_MATRIX,
    }
)


def known_base_image(reference: str) -> BaseImage | None:
    """The pinned base at ``reference`` on any supported platform, or None."""
    for matrix in MATRICES.values():
        image = matrix.base_image(reference)
        if image is not None:
            return image
    return None


def compatibility_report(lock: Mapping[str, Any]) -> tuple[str, ...]:
    platform = lock.get("platform")
    for key, matrix in MATRICES.items():
        if key.value == platform:
            return matrix.compatibility_report(lock)
    return (f"Platform {platform!r} has no embedded matrix; compatibility is not tracked.",)


# --------------------------------------------------------------------------
# Lock rendering (private): the restricted lock shape — string/int/bool
# scalars and nested tables. Insertion order is preserved so the generated
# file reads in the conventional lock order; generation is deterministic
# because every input table above is built deterministically.


def _render_document(document: Mapping[str, Any]) -> str:
    lines: list[str] = []
    _render_table(None, document, lines)
    return "\n".join(lines) + "\n"


def _render_table(prefix: str | None, table: Mapping[str, Any], lines: list[str]) -> None:
    scalars = {key: value for key, value in table.items() if not isinstance(value, Mapping)}
    subtables = {key: value for key, value in table.items() if isinstance(value, Mapping)}
    if prefix is not None:
        if lines:
            lines.append("")
        lines.append(f"[{prefix}]")
    for key, value in scalars.items():
        if not isinstance(value, (str, int, bool, list)) or isinstance(value, list) and any(not isinstance(item, str) for item in value):
            raise ProjectConfigurationError(
                f"Unsupported lock value type for {key!r}: {type(value).__name__}."
            )
        rendered_key = key if _is_bare_key(key) else quote_toml(key)
        rendered_value = "[" + ", ".join(quote_toml(item) for item in value) + "]" if isinstance(value, list) else render_toml_scalar(value)
        lines.append(f"{rendered_key} = {rendered_value}")
    for key, value in subtables.items():
        component = key if _is_bare_key(key) else quote_toml(key)
        _render_table(component if prefix is None else f"{prefix}.{component}", value, lines)


def _is_bare_key(key: str) -> bool:
    return all(character.isalnum() or character in "-_" for character in key)
