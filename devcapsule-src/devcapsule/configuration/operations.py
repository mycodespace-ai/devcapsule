"""Checkout-facing operations: one function per user-visible operation.

Command modules translate parsed arguments into exactly one call here and
print the returned report; policy, validation, and artifact writes live on
this side of the boundary.  This is the operation layer the first-run design
requires: the write half and the read half of each artifact contract sit in
the same module instead of being split between a command callback and a
library loader.

Reports render themselves (`render()`), so the exact user-facing wording of
an operation's outcome is owned here alongside the operation, not composed
ad hoc at each call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import tomllib
from pathlib import Path
import re
import sys
from typing import Any, Mapping, TextIO

from devcapsule.components.antigravity_cli import DEFINITION as ANTIGRAVITY_CLI
from devcapsule.elicitation import SOURCE_EXISTING_RECORD, SOURCE_COMMAND_LINE, SOURCE_PROMPT, AnswerKey, Elicitor
from devcapsule.environment_realization import required_local_image
from devcapsule.materialization import validate_base_image
from devcapsule.project import sanitize_name
from devcapsule.platforms import Platform, UnsupportedPlatformError
from devcapsule.resolution_matrix import MATRICES, ResolutionMatrix

from .trust import HomeTrust
from .authorization import (
    AuthorizationDeclaration,
    CURATED_HOST_RECOMMENDATIONS,
    authorization_declarations,
    authorized_base_selection,
    immutable_registry_reference,
    normalize_authorization_value,
    render_authorization_value,
)
from .capabilities import CapabilityPolicy, LocalCapabilities, requirement
from .capability_commands import check_documents, pin_selection
from .capability_selection import compose_lock, effective_lock, generate_lock, local_pins
from .file_formats import (
    AuthorizationScalar,
    ConfigurationFileKind,
    ProjectConfigurationError,
    quote_toml,
    render_checkout,
    render_toml,
    render_toml_scalar,
    validate_file_format,
)
from .freshness import stale_resolution_inputs
from .manifest import current, current_manifest
from .manifest_schemas import ManifestV1, read_manifest
from .manifest_document import CURRENT_MANIFEST_SCHEMA_VERSION, Recommendations, capability_table, manifest_preamble, render_manifest
from .model import Configuration
from .nodes import (
    CARRIER_FAMILY_AUTHORIZE,
    CARRIER_FAMILY_BIND,
    CARRIER_FAMILY_SET,
    PROVIDER_HOST_DIRECTORY,
    build_node_registry,
)
from .storage import (
    platform_lock_path,
    project_platform,
    atomic_write,
    checkout_record_paths,
    load_checkout,
    load_resolution,
    load_toml,
    load_settings,
    lock_for,
    manifest_for,
    manifest_source_digest,
    require_settled,
)
from .values import checkout_omitted_values, normalize_configuration_value


def _project_matrix(root: Path) -> ResolutionMatrix:
    """The resolution matrix of the platform this host runs the project at ``root`` as."""

    return MATRICES[project_platform(root)]

__all__ = [
    "CheckoutRecord",
    "InitializeReport",
    "InitializeRequest",
    "ProvidedAnswer",
    "ResolveReport",
    "initialize_project",
    "resolve_checkout",
]


@dataclass(frozen=True)
class ResolveReport:
    """Outcome of one successful resolution."""

    resolution_path: Path
    lock_name: str
    registered_checkout: Path | None

    def render(self) -> str:
        lines = []
        if self.registered_checkout is not None:
            lines.append(f"Registered checkout: {self.registered_checkout}")
        lines.append(f"Resolved {self.resolution_path} from {self.lock_name}")
        return "\n".join(lines)


class CheckoutRecord:
    """One checkout record loaded for mutation and written back atomically.

    Every mutating operation (set, bind, authorize, adopt) edits the same
    developer-owned record through this class, so the ownership check and the
    table validation exist exactly once.
    """

    def __init__(self, manifest: Mapping[str, Any], root: Path) -> None:
        input_path, _resolution_path = checkout_record_paths(manifest, root)
        document = (
            load_checkout(input_path, manifest, root) if input_path.is_file()
            else tomllib.loads(render_checkout(manifest, root, {}, {}))
        )
        self._load(input_path, document)

    @classmethod
    def staged(cls, input_path: Path, document: Mapping[str, Any]) -> CheckoutRecord:
        """Edit an owned copy without reading or writing a checkout record."""
        record = cls.__new__(cls)
        record._load(input_path, deepcopy(dict(document)))
        return record

    def _load(self, input_path: Path, document: dict[str, Any]) -> None:
        self.input_path = input_path
        self.document = document
        self._original = deepcopy(self.document)
        # Each editable collection belongs to the retained document. No
        # projection/serialization pair can drop an unrelated answer.
        self.state = self.document.setdefault("state", {}).setdefault("adopted", {})
        self.host = self.document.setdefault("host", {})
        self.authorization = self.document.setdefault("authorization", {})
        configuration = self.document.setdefault("configuration", {})
        self.values = configuration.setdefault("values", {})
        self.omitted_values = set(checkout_omitted_values(self.document))
        bindings = configuration.setdefault("bindings", {})
        self.directory_bindings = bindings.setdefault("host-directory", {})
        self.environment_bindings = bindings.setdefault("host-environment", {})

    def omit_value(self, name: str) -> None:
        """Record the explicit 'none' answer: keep the node absent at runtime."""

        self.values.pop(name, None)
        self.omitted_values.add(name)

    def set_value(self, name: str, value: Any) -> None:
        """Record a value answer, clearing any standing omission."""

        self.omitted_values.discard(name)
        self.values[name] = value

    def authorize(self, declaration: AuthorizationDeclaration, value: str | bool, image_identity: str | None = None) -> None:
        """Replace one logical decision, including its obsolete legacy spelling."""
        name = declaration.name
        self.host.pop(name, None)
        if name == "base-image":
            answer = {"reference": value, "lock-digest": declaration.recommendation_digest}
            if image_identity is not None:
                answer["image-id"] = image_identity
        else:
            value = normalize_authorization_value(declaration, value)
            answer = {"value": value, "recommendation-digest": declaration.recommendation_digest}
        self.authorization[name] = answer

    def export(self) -> dict[str, Any]:
        """Return the document that write would publish, without new empty tables."""
        if self.omitted_values:
            self.document["configuration"]["omitted-values"] = sorted(self.omitted_values)
        else:
            self.document["configuration"].pop("omitted-values", None)
        def without_new_empty_tables(value: dict[str, Any], original: Mapping[str, Any]) -> dict[str, Any]:
            result = {}
            for key, item in value.items():
                if isinstance(item, dict):
                    prior = original.get(key, {})
                    item = without_new_empty_tables(item, prior if isinstance(prior, dict) else {})
                    if not item and key not in original:
                        continue
                result[key] = item
            return result
        return without_new_empty_tables(self.document, self._original)

    def write(self) -> None:
        atomic_write(self.input_path, render_toml(self.export()))


def resolve_checkout(start_path: Path) -> ResolveReport:
    """Validate one checkout's combined inputs and write its fresh resolution.

    This is the explicit "my configuration choices are complete" step: it
    validates completeness and consistency across manifest, lock, and the
    developer-owned record, then writes the inspectable generated resolution
    whose source digests reveal later drift.  It creates the checkout record
    on a first resolution — record creation belongs to this path, which is
    the first persistent developer-owned act.
    """

    root, manifest = manifest_for(start_path)
    lock_path, lock = lock_for(root, manifest)
    input_path, output = checkout_record_paths(manifest, root)
    registered: Path | None = None
    if not input_path.is_file():
        atomic_write(input_path, render_checkout(manifest, root, {}, {}))
        registered = input_path
    checkout = load_checkout(input_path, manifest, root)
    home = load_settings()
    configuration = Configuration(manifest, lock, checkout, home)
    configuration.review().require_ready(root)
    resolution = configuration.resolve()
    base_selection = (authorized_base_selection(lock, checkout, trust=HomeTrust.read(home))
                      if "base" in lock else None)
    if base_selection is not None and base_selection.local_image_identity is not None:
        local_base = required_local_image(base_selection.reference)
        validate_base_image(local_base, platform=str(lock["platform"]),
                            expected_identity=base_selection.local_image_identity)
    atomic_write(output, render_toml(resolution.document()))
    return ResolveReport(
        resolution_path=output,
        lock_name=lock_path.name,
        registered_checkout=registered,
    )


@dataclass(frozen=True)
class ProvidedAnswer:
    """One configuration answer supplied on the command line."""

    family: str
    name: str
    value: str
    justification: str | None = None


@dataclass(frozen=True)
class InitializeRequest:
    """Everything ``devcapsule project init`` collected from its command line.

    ``require`` and ``offer`` are the project's: the tools every checkout
    must have (``TOOL``) and the tools a
    developer may leave out. ``ide`` and ``agents`` are the owner's own
    checkout's choices, recorded in the owner's checkout record and never in
    the manifest (R-CONFIG-001, refinement of 2026-10-06).
    """

    directory: Path
    require: tuple[str, ...] = ()
    offer: tuple[str, ...] = ()
    ide: str | None = None
    agents: tuple[str, ...] = ()
    project_name: str | None = None
    slug: str | None = None
    creator: str | None = None
    project_mount: str | None = None
    answers: tuple[ProvidedAnswer, ...] = ()
    regenerate: bool = False
    # Skip consent solicitations for explicitly supplied values (today: a
    # base-image selection); validation and recording are unchanged.
    less_pedantic: bool = False
    # Let resolution fall back past missing verified edges with a gentle
    # warning (owner ruling 2026-09-03: the matrix may be stale or wrong);
    # the generated lock names every unverified combination.
    allow_unverified: bool = False
    # None: decide from whether stdin is a terminal.
    interactive: bool | None = None
    # The platform whose lock to write; None: the one the project runs as
    # here, or, for a new project on a host of several platforms, asked.
    platform: Platform | None = None


@dataclass(frozen=True)
class InitializeReport:
    """Outcome of one successful initialization, in owner order."""

    manifest_path: Path
    manifest_action: str
    project_name: str
    creator: str
    slug: str
    project_mount: str
    required: tuple[str, ...]
    offered: tuple[str, ...]
    lock_path: Path
    lock_action: str
    base_display: str
    # (name, rendered value, justification) for every recommendation the
    # manifest carries after this init.
    recommendations: tuple[tuple[str, str, str], ...]
    # The owner's own checkout: the IDE and the agents selected for it.
    ide: str | None
    agents: tuple[str, ...]
    # Authorization nodes by how this invocation settled them: answered
    # here (a flag or a prompt), carried forward from the existing checkout
    # record because their digest still matched, or explicitly accepted by
    # this developer while authoring/reviewing the project recommendation. The report says which,
    # so a re-run never reads as if it granted what already stood.
    answered: tuple[str, ...]
    carried: tuple[str, ...]
    recommended: tuple[str, ...]
    checkout_record: Path
    # None when the owner's checkout has no IDE yet: nothing to resolve.
    resolve: ResolveReport | None

    def render(self) -> str:
        required = " ".join(self.required) or "none"
        lines = [
            f"Migrated {self.manifest_path} to schema 2; the leading comment block is kept, other comments are not."
            if self.manifest_action == "Migrated" else f"{self.manifest_action} {self.manifest_path}",
            f"Project: {self.project_name} — {self.creator}/{self.slug}",
            f"Project mount: {self.project_mount}",
            f"Requires: {required}",
        ]
        if self.offered:
            lines.append(f"Offers: {' '.join(self.offered)}")
        lines.append(f"{self.lock_action} {self.lock_path} (base {self.base_display})")
        for name, value, justification in self.recommendations:
            line = f"Recommended {name} = {value} for every checkout"
            lines.append(f"{line} ({justification})." if justification else f"{line}.")
        selection = [self.ide] if self.ide else []
        selection.extend(self.agents)
        lines.append("Your checkout: " + (" ".join(selection) if selection else "no IDE or personal capability selected yet"))
        lines.extend(_authorization_lines(self.answered, self.carried, self.recommended))
        lines.append(f"Checkout record: {self.checkout_record}")
        if self.resolve is not None:
            lines.append(self.resolve.render())
            lines.append("Project initialized; 'devcapsule project run' starts it.")
        else:
            lines.append(
                "Project initialized. Choose your IDE with 'devcapsule project config ide IDE' "
                "(python-ide, frontend-ide, vscode-ide, java-ide, eclipse-ide or dotnet-ide), then 'devcapsule project run'."
            )
        return "\n".join(lines)


def _authorization_lines(
    answered: tuple[str, ...], carried: tuple[str, ...], recommended: tuple[str, ...]
) -> list[str]:
    lines = []
    if answered:
        lines.append("Answered for this checkout: " + ", ".join(answered) + ".")
    if carried:
        lines.append(
            "Standing from the existing checkout record: " + ", ".join(carried) + "."
        )
    if recommended:
        lines.append(
            "Project recommendations applied to this checkout: "
            + ", ".join(recommended)
            + "."
        )
    return lines


@dataclass(frozen=True)
class _Authorizations:
    """Authorization nodes settled by one elicitation, by how they were settled."""

    answered: list[str] = field(default_factory=list)
    carried: list[str] = field(default_factory=list)

    def settle(self, name: str, source: str) -> None:
        (self.carried if source == SOURCE_EXISTING_RECORD else self.answered).append(name)


def initialize_project(
    request: InitializeRequest,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> InitializeReport:
    """Bring the owned artifacts into existence, in owner order.

    The settled postcondition (*Initializing A New Project* in the
    v1-user-experience design note): a valid manifest and a platform lock for
    this platform exist, the owner's checkout record is registered with the
    owner's IDE and agents, and, when an IDE is chosen, a fresh resolution
    stands — achieved by invoking the same resolution the standalone command
    runs.  The manifest holds the project's requirements and offers in the
    ``required`` form of schema 2; the lock is project-only (no IDE), and the
    IDE and agents are pinned in the owner's checkout record, as for every
    other developer.  The three entry states are handled in order: nothing
    initialized (author everything), partially initialized (honor what exists,
    complete what is missing — repair is init's own job), and fully initialized
    (fail loudly naming ``--regenerate``).
    """

    root = request.directory.expanduser().resolve()
    if not root.is_dir():
        raise ProjectConfigurationError(f"Project directory does not exist: {root}")
    require_settled(root)
    manifest_path = root / ".devcapsule" / "devcapsule.toml"
    elicitor = Elicitor(
        _init_command_line(request),
        interactive=request.interactive,
        input_stream=input_stream,
        output_stream=output_stream,
    )
    # The platform comes first: its matrix answers every later question.
    platform = _elicit_platform(elicitor, root)
    lock_path = platform_lock_path(root, platform)
    matrix = MATRICES[platform]

    existing_manifest: dict[str, Any] | None = None
    existing_lock: dict[str, Any] | None = None
    legacy = migrate = False
    if manifest_path.is_file():
        # A hand-authored or carried-over manifest is the ordinary form of
        # partial initialization, not an error: honor it and generate what
        # follows from it.
        written = read_manifest(load_toml(manifest_path), manifest_path)
        # The owner's regeneration writes a schema-1 file as schema 2; every
        # other path reads the upgraded form and leaves the file alone.
        legacy = isinstance(written, ManifestV1)
        migrate = legacy and request.regenerate
        existing_manifest = current(written, manifest_path).document()
        if lock_path.is_file():
            existing_lock = load_toml(lock_path)
            validate_file_format(existing_lock, ConfigurationFileKind.lock, lock_path)
        input_path, output_path = checkout_record_paths(existing_manifest, root)
        if input_path.is_file():
            load_checkout(input_path, existing_manifest, root)
        if output_path.is_file():
            load_resolution(output_path)

    if existing_manifest is not None and lock_path.is_file() and not request.regenerate:
        if _fully_initialized(root, existing_manifest):
            if request.answers:
                # A repeated init carrying --authorize/--set/--bind must not
                # silently drop the developer's expressed answers (bug of
                # 2026-09-01): they are "individual answers" in the design's
                # own vocabulary, applied here through the same primitives
                # the config family uses, then resolved afresh so the init
                # postcondition — 'project run' starts it — holds.
                return _apply_answers_to_standing_checkout(
                    root, manifest_path, lock_path, platform, request
                )
            raise ProjectConfigurationError(
                f"{root} is already fully initialized: manifest, platform lock, "
                "checkout record, and a fresh resolution all stand. 'devcapsule "
                "project init --regenerate' rewrites the derived platform lock; "
                "the 'config' family changes individual answers."
            )

    identity = _elicit_identity(elicitor, root, existing_manifest, matrix)
    authored = frozenset(answer.name for answer in request.answers if answer.justification is not None)
    # Fail now if identity or requirements are unanswered: the lock cannot be
    # generated without them, so later questions are unreachable and their
    # supplied answers must not be misreported as unknown.
    if elicitor.missing():
        elicitor.finish(require_all_consumed=False)

    # The lock, in memory first, project-only: the IDE and the agents are
    # each developer's and pinned in their checkout record. Every name a
    # supplied answer may use is fixed by the requirements, the owner's own
    # selection and the lock, all known here, so a misspelled or wrong-family
    # name is rejected before the first question is asked and before anything
    # is written.
    if lock_path.is_file() and not request.regenerate:
        lock_action = "Kept"
        shared_lock = load_toml(lock_path)
    else:
        lock_action = "Regenerated" if lock_path.is_file() else "Created"
        from .capabilities import resolution_recommendations
        shared_lock = generate_lock(identity.policy, matrix, previous=existing_lock,
                                    recommendations=resolution_recommendations(existing_manifest or {}),
                                    allow_unverified=request.allow_unverified)
        _report_unverified(shared_lock)
    # A manifest written before 0.3.0 rc4 may require the IDE itself; then
    # the lock carries it and the owner's checkout has no IDE question.
    lock_has_ide = bool(shared_lock.get("components", {}).get("interactive-surface"))
    existing_selection = _existing_selection(root, existing_manifest)
    # A schema-1 file required its IDE for everyone and the lock pinned it;
    # read as schema 2 it recommends it. The owner's checkout keeps that IDE
    # as its default, so regenerating the project-only lock leaves the owner
    # able to run. A schema-2 recommendation is applied at run (decision 24),
    # not here: init's own contract since rc4 is that a project needs no IDE.
    selection = _elicit_owner_selection(elicitor, request, matrix, existing_selection,
                                        ask_ide=not lock_has_ide, fresh=existing_manifest is None,
                                        pinned=Recommendations.read(existing_manifest or {}).ide if legacy else None)
    runnable = lock_has_ide or selection.ide is not None
    preview_manifest = existing_manifest if existing_manifest is not None else _preview_manifest(identity)
    if existing_manifest is None:
        # A bad mount path or slug is refused here, before the first write.
        read_manifest(preview_manifest, manifest_path)
    authoring = frozenset(CURATED_HOST_RECOMMENDATIONS) if existing_manifest is None else authored
    if runnable:
        preview_lock = _preview_effective_lock(preview_manifest, shared_lock, selection, matrix)
        _reject_undeclared_answers(request.answers, preview_manifest, preview_lock, authoring=authoring)
    else:
        _reject_answers_needing_an_ide(request.answers, preview_manifest, shared_lock, authoring=authoring)

    recommendations = _elicit_recommendations(
        elicitor, existing_manifest, authored=authored,
    )
    # A recommendation answered without its justification is unanswered:
    # report it now rather than authoring an incomplete block.
    if elicitor.missing():
        elicitor.finish(require_all_consumed=False)

    manifest_action, manifest_text = _prepare_manifest(
        manifest_path, existing_manifest, identity, recommendations, migrate=migrate
    )
    if legacy and manifest_action == "Updated":
        raise ProjectConfigurationError(
            "Adding a shared recommendation to a schema-1 manifest requires 'project init --regenerate'; "
            "nothing was written."
        )
    manifest = current_manifest(tomllib.loads(manifest_text), manifest_path).document()
    check_documents(manifest, shared_lock)
    # All artifacts stay in memory until every answer is accepted. A batch
    # failure must leave shared files and the private record untouched.
    record = CheckoutRecord(manifest, root)
    _stage_owner_selection(record, manifest, shared_lock, matrix, selection, request.allow_unverified)

    def persist() -> None:
        if manifest_action != "Honored existing":
            atomic_write(manifest_path, manifest_text, mode=0o644)
        if lock_action != "Kept":
            atomic_write(lock_path, render_toml(shared_lock), mode=0o644)
        record.write()

    if not runnable:
        # Nothing to resolve without an IDE: the owner's checkout waits for
        # that one choice, and the report says so. Host answers given on the
        # command line are still recorded.
        _elicit_host_answers(elicitor, manifest, shared_lock, record)
        elicitor.finish()
        persist()
        return _initialize_report(
            manifest_path, manifest_action, identity, lock_path, lock_action,
            base_display=_base_display(shared_lock), recommendations=recommendations,
            selection=selection, answered=(), carried=(), recommended=(),
            checkout_record=record.input_path, resolve=None,
        )
    lock = effective_lock(manifest, compose_lock(manifest, shared_lock, record.document), record.document, warn=False)
    declarations = authorization_declarations(manifest, lock)
    settled = _elicit_acquisitions(
        elicitor,
        declarations,
        record,
        platform=str(platform),
        less_pedantic=request.less_pedantic,
    )
    accepted_recommendations = _elicit_host_answers(elicitor, manifest, lock, record)
    _elicit_extra_answers(elicitor, request.answers, manifest, lock, record)
    elicitor.finish()
    persist()

    resolve_report = resolve_checkout(root)
    base_declaration = declarations.get("base-image")
    base_display = (
        base_declaration.display_value or str(base_declaration.recommended_value)
        if base_declaration is not None else _base_display(lock)
    )
    return _initialize_report(
        manifest_path, manifest_action, identity, lock_path, lock_action,
        base_display=base_display, recommendations=recommendations, selection=selection,
        answered=tuple(settled.answered), carried=tuple(settled.carried),
        recommended=accepted_recommendations, checkout_record=record.input_path,
        resolve=resolve_report,
    )


def _elicit_platform(elicitor: Elicitor, root: Path) -> Platform:
    """The platform whose lock init writes, asked when this host runs several.

    A project with a lock this host runs keeps that platform unless
    ``--platform`` names another; otherwise a host of one platform takes it,
    and a host of several asks, its native platform the default and the
    unattended answer. Init completes the checkout for the lock it writes, so
    the platform must be the one the project runs as once that lock exists.
    """
    runnable = Platform.runnable()
    native = runnable[0]
    locked = next((platform for platform in runnable if platform_lock_path(root, platform).is_file()), None)
    choices = " or ".join(
        f"{platform} ({'native' if platform is native else 'emulated'})" for platform in runnable
    )
    answer = elicitor.seek(
        "platform",
        description=f"Capsule platform for this project: {choices}",
        remedy="--platform PLATFORM",
        existing=str(locked) if locked is not None else None,
        default=str(native) if len(runnable) == 1 else None,
        empty_answer=str(native),
        omitted_answer=str(native),
        validate=_platform_validator(runnable),
    )
    if answer is None:  # Input ended at the question.
        elicitor.finish(require_all_consumed=False)
        raise AssertionError("an unanswered platform question must fail the elicitation")
    platform = Platform.parse(answer.value)
    runs_as = next(candidate for candidate in runnable
                   if candidate is platform or platform_lock_path(root, candidate).is_file())
    if runs_as is not platform:
        raise ProjectConfigurationError(
            f"On this host the project runs as {runs_as}, which it has a lock for, "
            f"so init cannot add a {platform} lock here."
        )
    return platform


def _platform_validator(runnable: tuple[Platform, ...]) -> Any:
    def validate(value: str) -> str:
        try:
            candidate = Platform.parse(value.strip())
        except UnsupportedPlatformError as exc:
            raise ProjectConfigurationError(str(exc)) from exc
        if candidate not in runnable:
            names = ", ".join(str(platform) for platform in runnable)
            raise ProjectConfigurationError(f"This host runs {names} capsules, not {candidate}.")
        return str(candidate)

    return validate


def _initialize_report(
    manifest_path: Path, manifest_action: str, identity: _ProjectIdentity, lock_path: Path, lock_action: str,
    *, base_display: str, recommendations: list[tuple[str, str]], selection: _OwnerSelection,
    answered: tuple[str, ...], carried: tuple[str, ...], recommended: tuple[str, ...],
    checkout_record: Path, resolve: ResolveReport | None,
) -> InitializeReport:
    return InitializeReport(
        manifest_path=manifest_path,
        manifest_action=manifest_action,
        project_name=identity.name,
        creator=identity.creator,
        slug=identity.slug,
        project_mount=identity.mount,
        required=identity.policy.requirements(),
        offered=identity.policy.optional,
        lock_path=lock_path,
        lock_action=lock_action,
        base_display=base_display,
        recommendations=tuple(
            (name, render_authorization_value(CURATED_HOST_RECOMMENDATIONS[name][1]), justification)
            for name, justification in recommendations
        ),
        ide=selection.ide,
        agents=selection.agents,
        answered=answered,
        carried=carried,
        recommended=recommended,
        checkout_record=checkout_record,
        resolve=resolve,
    )


def _base_display(lock: Mapping[str, Any]) -> str:
    base = lock.get("base")
    if isinstance(base, dict) and isinstance(base.get("reference"), str):
        contract = base.get("contract")
        return f"{contract} — {base['reference']}" if isinstance(contract, str) else str(base["reference"])
    return str(lock.get("image", {}).get("reference", "image lock"))


def _report_unverified(lock: Mapping[str, Any]) -> None:
    """Name what a generated lock or selection runs as an experiment, the owner's 2026-09-06 ruling.

    The matrix records the unvalidated combinations in the lock it renders,
    so everyone who uses the lock reads the same fact.
    """
    unverified = lock.get("unverified-combinations")
    if isinstance(unverified, str) and unverified:
        print(
            "Running as an experiment. Not yet validated: "
            + unverified
            + ".\nThe lock records this for everyone who uses it; if it works, "
            "let the DevCapsule maintainers know so the matrix can learn.",
            file=sys.stderr,
        )


@dataclass(frozen=True)
class _OwnerSelection:
    """The owner's own checkout choices: one IDE capability or none, and agent capabilities."""

    ide: str | None
    agents: tuple[str, ...]

    @property
    def selected(self) -> tuple[str, ...]:
        return tuple(sorted(({self.ide} if self.ide else set()) | set(self.agents)))


def _existing_selection(root: Path, manifest: Mapping[str, Any] | None) -> _OwnerSelection:
    """What the owner's checkout record already selects, when it exists."""
    if manifest is None:
        return _OwnerSelection(None, ())
    input_path, _ = checkout_record_paths(manifest, root)
    if not input_path.is_file():
        return _OwnerSelection(None, ())
    local = LocalCapabilities.read(load_toml(input_path))
    matrix = _project_matrix(root)
    surfaces = set(matrix.ide_capabilities())
    ide = next((name for name in local.selected if name in surfaces), None)
    return _OwnerSelection(ide, tuple(name for name in local.selected if name not in surfaces))


def _elicit_owner_selection(
    elicitor: Elicitor, request: InitializeRequest, matrix: ResolutionMatrix, existing: _OwnerSelection,
    *, ask_ide: bool = True, fresh: bool = True, pinned: str | None = None,
) -> _OwnerSelection:
    """Ask the owner's own IDE and agents, for the owner's checkout alone.

    The IDE is asked interactively with Enter meaning "decide later": a
    project does not need an IDE to be initialized, a checkout needs one to
    run. Personal capabilities join through ``--with``, ``config add`` or
    the default-agent offer. With
    ``ask_ide`` false the lock already carries the IDE (a manifest from
    before 0.3.0 rc4) and only an explicit ``--ide`` is taken.  ``pinned``
    is the IDE a schema-1 manifest required, the default for the owner's
    checkout when its record names none, applied and disclosed, not asked.
    """
    surfaces = list(matrix.ide_capabilities())
    answer = elicitor.seek(
        "ide",
        description=f"Your IDE for this checkout ({', '.join(surfaces)}; Enter to decide later)",
        remedy="--ide IDE",
        existing=existing.ide,
        default=pinned if ask_ide else None,
        empty_answer="none",
        omitted_answer="none",
        mandatory=ask_ide,
        validate=_ide_validator(matrix, surfaces),
    )
    ide = None if answer is None or answer.value == "none" else answer.value
    additions = {matrix.canonical_name(name) for name in request.agents}
    if any(matrix.is_ide(name) for name in additions):
        raise ProjectConfigurationError("Use init --ide for an IDE choice; --with adds other capabilities.")
    agents = tuple(sorted(additions | set(existing.agents)))
    agents = _with_default_agent(elicitor, agents, offer=fresh and not existing.selected, matrix=matrix)
    return _OwnerSelection(ide, agents)


def _ide_validator(matrix: ResolutionMatrix, surfaces: list[str]) -> Any:
    by_component = {matrix.resolve_provider(name): name for name in surfaces}

    def validate(value: str) -> str:
        candidate = value.strip()
        if candidate.lower() == "none":
            return "none"
        candidate = by_component.get(candidate, candidate)
        if candidate not in surfaces:
            raise ProjectConfigurationError(f"Unknown IDE {value!r}; choose one of {', '.join(surfaces)}.")
        return candidate

    return validate


def _preview_effective_lock(
    manifest: Mapping[str, Any], shared_lock: Mapping[str, Any], selection: _OwnerSelection, matrix: ResolutionMatrix,
) -> dict[str, Any]:
    """The lock the owner's checkout will run, before anything is written: the shared lock with the owner's pins."""
    if not selection.selected:
        return dict(shared_lock)
    policy = CapabilityPolicy.read(manifest)
    local = LocalCapabilities(selected=selection.selected)
    from .capabilities import resolution_recommendations
    pins = pin_selection(matrix, policy, local, shared_lock, LocalCapabilities(), {}, allow_unverified=True,
                         recommendations=resolution_recommendations(manifest))
    checkout = {"devcapsule-checkout-schema-version": 1,
                "capabilities": {"selected": list(selection.selected), "without": [], "lock": render_toml(pins)}}
    return effective_lock(manifest, compose_lock(manifest, shared_lock, checkout), checkout, warn=False)


def _stage_owner_selection(
    record: CheckoutRecord, manifest: Mapping[str, Any], shared_lock: Mapping[str, Any], matrix: ResolutionMatrix,
    selection: _OwnerSelection, allow_unverified: bool,
) -> None:
    """Put the owner's IDE and agents, with their pins, into the staged checkout record.

    The same pins ``config ide`` and ``config add`` record; nothing is
    written here. An empty selection leaves whatever the record selects.
    """
    if not selection.selected:
        return
    policy = CapabilityPolicy.read(manifest)
    previous = LocalCapabilities.read(record.document)
    local = LocalCapabilities(selected=selection.selected, without=previous.without, providers=previous.providers)
    local.validate(policy)
    from .capabilities import resolution_recommendations
    pins = pin_selection(matrix, policy, local, shared_lock, previous, local_pins(record.document),
                         allow_unverified=allow_unverified, recommendations=resolution_recommendations(manifest))
    _report_unverified(pins)
    record.document["capabilities"] = {"selected": list(local.selected), "without": list(local.without),
                                       "lock": render_toml(pins), **({"providers": local.providers} if local.providers else {})}


@dataclass(frozen=True)
class _ProjectIdentity:
    name: str
    slug: str
    creator: str
    mount: str
    policy: CapabilityPolicy


def _init_command_line(request: InitializeRequest) -> dict[AnswerKey, str]:
    """Map init's dedicated flags and --authorize carriers to elicitation keys.

    Values and bindings use a separate elicitation namespace once the lock
    establishes their registry. Ordinary names may coincide with identity
    names; the owning question, not its spelling alone, selects the answer.
    """

    command_line: dict[AnswerKey, str] = {}
    for entry in (*request.require, *request.offer):
        if entry.strip().lower() != "none":
            requirement(entry)
    if request.require:
        command_line[("require", "value")] = " ".join(request.require)
    if request.offer:
        command_line[("offer", "value")] = " ".join(request.offer)
    if request.ide is not None:
        command_line[("ide", "value")] = request.ide
    if request.platform is not None:
        command_line[("platform", "value")] = str(request.platform)
    for key, value in (
        ("name", request.project_name),
        ("slug", request.slug),
        ("creator", request.creator),
        ("project-mount", request.project_mount),
    ):
        if value is not None:
            command_line[(key, "value")] = value
    for answer in request.answers:
        if answer.family != "authorize":
            continue
        command_line[(answer.name, "value")] = answer.value
        if answer.justification is not None:
            command_line[(answer.name, "justification")] = answer.justification
    return command_line


def _preview_manifest(identity: _ProjectIdentity) -> dict[str, Any]:
    """The manifest a fresh init is about to author, as a mapping, before any write.

    Only what the node registry reads: the requirements and the identity.
    Recommendations are absent because they are asked after this preview is
    used; see ``authoring`` in :func:`_reject_undeclared_answers`.
    """

    return {
        "devcapsule-schema-version": CURRENT_MANIFEST_SCHEMA_VERSION,
        "project": {
            "name": identity.name,
            "slug": identity.slug,
            "creator": identity.creator,
            "mount": identity.mount,
        },
        "capabilities": capability_table(identity.policy),
    }


def _reject_undeclared_answers(
    answers: tuple[ProvidedAnswer, ...],
    manifest: Mapping[str, Any],
    lock: Mapping[str, Any],
    *,
    authoring: frozenset[str],
) -> None:
    """Fail on a misspelled or wrong-family answer name before anything is asked or written.

    The names an init can answer are fixed by the requirements, the owner's
    selection and the lock, all known before the first prompt, so
    ``--authorize docker host`` for ``docker-daemon`` is reported then, with
    nothing on disk and no prompt consumed. Until 2026-09-26 this check ran
    last, after every prompt and after the manifest and lock were written,
    and its failure discarded every answer the owner had just given.

    ``authoring`` names the curated host recommendations this invocation may
    still record. Such a name is an authorization node only once the project
    recommends it (``network`` has no home default), and the
    recommendation question consumes the answer that authors it, so an
    ``--authorize`` under one of these names is admitted here.
    """

    registry = build_node_registry(manifest, lock)
    for answer in answers:
        if (
            answer.family == CARRIER_FAMILY_AUTHORIZE
            and answer.name in authoring
            and registry.get(answer.name) is None
        ):
            continue
        registry.answerable(answer.name, answer.family)


def _reject_answers_needing_an_ide(
    answers: tuple[ProvidedAnswer, ...], manifest: Mapping[str, Any], lock: Mapping[str, Any],
    *, authoring: frozenset[str],
) -> None:
    """Without an IDE there are no set or bind nodes yet; only host answers can be recorded."""
    declarations = authorization_declarations(manifest, lock)
    for answer in answers:
        if answer.family != CARRIER_FAMILY_AUTHORIZE:
            raise ProjectConfigurationError(
                f"--{answer.family} {answer.name} needs the checkout's IDE first: add --ide IDE, "
                "or record the answer later with the config family."
            )
        if answer.name not in declarations and answer.name not in authoring:
            raise ProjectConfigurationError(
                f"Authorization {answer.name!r} is not declared by this project; declared: "
                + ", ".join(sorted(declarations)) + "."
            )


def _elicit_identity(
    elicitor: Elicitor, root: Path, existing_manifest: Mapping[str, Any] | None, matrix: ResolutionMatrix,
) -> _ProjectIdentity:
    from .capabilities import capability_notes
    for note in capability_notes(existing_manifest or {}):
        print(f"Note: {note}", file=sys.stderr)
    project = (existing_manifest or {}).get("project", {})
    existing_policy = CapabilityPolicy.read(existing_manifest) if existing_manifest is not None else None

    def existing_field(key: str) -> str | None:
        value = project.get(key)
        return str(value) if value else None

    name = elicitor.seek(
        "name",
        description="Project name",
        remedy="--name NAME",
        existing=existing_field("name"),
        default=root.name,
    )
    slug = elicitor.seek(
        "slug",
        description="Project slug",
        remedy="--slug SLUG",
        existing=existing_field("slug"),
        default=sanitize_name(root.name).lower(),
    )
    creator = elicitor.seek(
        "creator",
        description="Project creator (URL or email address)",
        remedy="--creator CREATOR",
        existing=existing_field("creator"),
        validate=_normalize_creator,
    )
    assert slug is not None  # a default always answers it
    mount = elicitor.seek(
        "project-mount",
        description="In-container project mount path",
        remedy="--project-mount PATH",
        existing=existing_field("mount"),
        default=f"/workspace/{slug.value}",
    )
    tools = list(matrix.capabilities())
    existing_require = " ".join(existing_policy.requirements()) if existing_policy is not None else None
    require = elicitor.seek(
        "require",
        description=(
            "Capabilities the project requires, optionally NAME>=VERSION, space-separated "
            f"({', '.join(tools)}; Enter for none)"
        ),
        remedy="--require CAPABILITY [--require CAPABILITY ...]",
        existing=existing_require if existing_require is not None else None,
        empty_answer="none",
        omitted_answer="none",
        validate=_require_validator(matrix, required=True),
    )
    offer = elicitor.seek(
        "offer",
        description="Capabilities the project offers",
        remedy="--offer CAPABILITY [--offer CAPABILITY ...]",
        mandatory=False,
        existing=" ".join(existing_policy.optional) if existing_policy is not None and existing_policy.optional else None,
        validate=_require_validator(matrix, required=False),
    )
    required_names = _split_capabilities(matrix, require.value if require else "none", required=True)
    offered_names = _split_capabilities(matrix, offer.value if offer else "none", required=False)
    if existing_policy is not None and require is not None and require.source == SOURCE_EXISTING_RECORD:
        if offer is not None and offer.source == SOURCE_EXISTING_RECORD:
            offered_names = existing_policy.optional
        policy = CapabilityPolicy(existing_policy.required, offered_names, existing_policy.minimums)
    else:
        policy = CapabilityPolicy.read({"capabilities": {"required": list(required_names), "optional": list(offered_names)}})
    return _ProjectIdentity(
        name=name.value if name else "",
        slug=slug.value,
        creator=creator.value if creator else "",
        mount=mount.value if mount else "",
        policy=policy,
    )


def _require_validator(matrix: ResolutionMatrix, *, required: bool) -> Any:
    def validate(value: str) -> str:
        if value.strip().lower() == "none":
            return "none"
        return " ".join(_split_capabilities(matrix, value, required=required))

    return validate


def _split_capabilities(matrix: ResolutionMatrix, value: str, *, required: bool) -> tuple[str, ...]:
    """Use the shared requirement grammar for initialization answers."""
    if value.strip().lower() == "none":
        return ()
    entries = value.split()
    policy = CapabilityPolicy.read({"capabilities": {
        "required": entries if required else [], "optional": [] if required else entries,
    }})
    for name in (*policy.required, *policy.optional):
        matrix.canonical_name(name)
    return policy.requirements() if required else policy.optional


def _with_default_agent(
    elicitor: Elicitor,
    agents: tuple[str, ...],
    *,
    offer: bool,
    matrix: ResolutionMatrix,
) -> tuple[str, ...]:
    """Offer the default-selected agent for the owner's checkout when none was named.

    Per the component-catalog delivery contract (2026-08-30), the Antigravity
    CLI is default-selected: "available by default" without living in any
    base. Concretely: an interactive init whose fresh checkout names no agent
    asks once, with Enter meaning yes; a noninteractive init keeps its
    existing selection unchanged, and
    a re-init over an existing checkout selection never grows it behind the
    owner's back.
    """

    default_capability = ANTIGRAVITY_CLI.capability
    if agents or not offer:
        return agents
    grown = tuple(sorted((*agents, default_capability)))
    try:
        # Only offer a default that resolves: while the matrix lacks verified
        # edges for the agent, the default silently does not apply rather
        # than failing the init.
        matrix.resolve(grown, project_only=True)
    except ProjectConfigurationError:
        return agents
    answer = elicitor.seek(
        "default-agent",
        description=(
            f"Select the default agent component ({default_capability}) for your checkout? (yes/no)"
        ),
        remedy=f"devcapsule project config add {default_capability}",
        empty_answer="yes",
        omitted_answer="no",
        validate=_yes_no_validator("default-agent"),
    )
    if answer is not None and answer.value == "yes":
        return grown
    return agents


def _yes_no_validator(name: str) -> Any:
    def validate(value: str) -> str:
        candidate = value.strip().lower()
        if candidate in {"yes", "y"}:
            return "yes"
        if candidate in {"no", "n"}:
            return "no"
        raise ProjectConfigurationError(f"Question {name!r} accepts yes or no.")

    return validate


def _elicit_recommendations(
    elicitor: Elicitor, existing_manifest: Mapping[str, Any] | None,
    *, authored: frozenset[str] = frozenset(),
) -> list[tuple[str, str]]:
    """Ask curated project-authoring questions, separately from local consent.

    Interactively each is asked with Enter meaning "none"; noninteractively
    an unflagged question records no recommendation — settled by the product
    owner on 2026-08-24.  A command-line answer that contradicts what the
    manifest already declares is a conflict, not an override: the manifest is
    authored content, so changing it is a manifest edit, never a silent init
    side effect.
    """

    recommendations: list[tuple[str, str]] = []
    host = (existing_manifest or {}).get("host", {})
    for name, (path, supported) in CURATED_HOST_RECOMMENDATIONS.items():
        rendered = render_authorization_value(supported)
        declared = _declared_recommendation(host, path)
        existing_value = (
            render_authorization_value(declared["value"])
            if declared is not None and isinstance(declared.get("value"), (str, bool))
            else None
        )
        if existing_manifest is not None and name not in authored:
            # Existing repository content is read-only advice. Host carriers
            # answer this checkout below. A justification explicitly requests
            # recommendation authoring; otherwise no owner question is asked.
            if declared is not None:
                recommendations.append((name, str(declared.get("justification", ""))))
            continue
        answer = elicitor.seek(
            name,
            description=f"Recommend {name} = {rendered} for every checkout? ({rendered}/none)",
            remedy=f"--authorize {name} {rendered}",
            existing=existing_value,
            empty_answer="none",
            omitted_answer="none",
            validate=_recommendation_validator(name, rendered),
        )
        if answer is None:
            continue
        if existing_value is not None and answer.value != existing_value:
            raise ProjectConfigurationError(
                f"The manifest already recommends {name} = {existing_value}; init never "
                "rewrites an authored recommendation. Edit the manifest to change it."
            )
        if answer.value == "none":
            continue
        justification = elicitor.seek(
            name,
            facet="justification",
            description=f"Justification recorded beside the {name} recommendation",
            remedy=f'--authorize {name} {rendered} "JUSTIFICATION"',
            existing=(
                str(declared.get("justification"))
                if declared is not None and declared.get("justification")
                else None
            ),
        )
        recommendations.append((name, justification.value if justification else ""))
    return recommendations


def _declared_recommendation(
    host: Mapping[str, Any], path: tuple[str, ...]
) -> Mapping[str, Any] | None:
    node: object = host
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return None
        node = node[key]
    return node if isinstance(node, Mapping) else None


def _recommendation_validator(name: str, rendered: str) -> Any:
    def validate(value: str) -> str:
        candidate = value.strip().lower()
        if candidate == "default":
            candidate = rendered
        if rendered == "true" and candidate == "false":
            candidate = "none"
        if candidate not in {"none", rendered}:
            raise ProjectConfigurationError(
                f"Recommendation {name!r} accepts exactly {rendered!r} or 'none'."
            )
        return candidate

    return validate


def _elicit_acquisitions(
    elicitor: Elicitor,
    declarations: Mapping[str, Any],
    record: CheckoutRecord,
    *,
    platform: str,
    less_pedantic: bool = False,
) -> _Authorizations:
    """Elicit the owner's own executable and vendor-terms authorizations.

    These have no safe omission — executing an artifact and accepting vendor
    acquisition terms must be answered — so a noninteractive run without their
    flags batch-fails rather than inferring authorization.  Interactively
    each is asked with Enter meaning yes, because the owner just chose the
    inputs that derived them.

    The base-image answer additionally accepts an image reference — a
    developer-owned base selection for this checkout (product-owner ruling
    2026-09-03): the image is read from the local daemon, its identity and
    metadata are presented, and consent is solicited; ``less_pedantic``
    records the selection without the solicitation.
    """

    settled = _Authorizations()
    base = declarations.get("base-image")
    if base is None:
        # A legacy image-reference lock has no formation base to authorize.
        return _elicit_component_acquisitions(elicitor, declarations, record, settled)
    reference = str(base.recommended_value)
    existing_base = record.authorization.get("base-image")
    # Consent binds to the image: the recommended digest, or a local image
    # by ID, is an existing answer whatever the lock has done around it.
    fresh = (
        isinstance(existing_base, dict)
        and isinstance(existing_base.get("reference"), str)
        and (
            existing_base.get("reference") == reference
            or isinstance(existing_base.get("image-id"), str)
        )
    )
    existing_answer = (
        "default" if existing_base.get("reference") == reference else existing_base.get("reference")
    ) if fresh and isinstance(existing_base, dict) else None
    answer = elicitor.seek(
        "base-image",
        description=(
            f"Authorize this checkout to execute {base.display_value or reference}? "
            "(Enter accepts; 'no' declines; or name a locally built/pulled image)"
        ),
        remedy=f"--authorize base-image {reference}",
        existing=existing_answer,
        empty_answer="default",
        validate=_base_answer_validator("base-image", reference),
    )
    if answer is not None:
        if answer.source == SOURCE_EXISTING_RECORD:
            settled.settle("base-image", answer.source)
            return _elicit_component_acquisitions(elicitor, declarations, record, settled)
        if answer.value == "no":
            raise ProjectConfigurationError(
                "Initialization needs the base authorization to reach a fresh resolution; "
                "declined. Authorize later with 'devcapsule project config authorize "
                f"base-image {reference}' and run 'devcapsule project run'."
            )
        if answer.value != "default":
            _record_base_selection(
                elicitor,
                record,
                base,
                selection=answer.value,
                recommended=reference,
                platform=platform,
                less_pedantic=less_pedantic,
            )
            settled.settle("base-image", answer.source)
            return _elicit_component_acquisitions(elicitor, declarations, record, settled)
        record.authorize(base, reference)
        settled.settle("base-image", answer.source)
    return _elicit_component_acquisitions(elicitor, declarations, record, settled)


def _elicit_component_acquisitions(
    elicitor: Elicitor,
    declarations: Mapping[str, Any],
    record: CheckoutRecord,
    settled: _Authorizations,
) -> _Authorizations:
    """Ask every component acquisition the lock's formation requires.

    The declarations derive from the locked components' vendor contracts
    (Claude Code, Antigravity CLI, …), one authorization node each; the
    question wording and the persistence shape are uniform so a new curated
    component never needs its own elicitation code.
    """

    for declaration in declarations.values():
        if declaration.kind != "acquisition":
            continue
        existing = record.authorization.get(declaration.name)
        fresh = (
            isinstance(existing, dict)
            and existing.get("recommendation-digest") == declaration.recommendation_digest
        )
        answer = elicitor.seek(
            declaration.name,
            description=f"{declaration.description} Authorize? (yes/no)",
            remedy=f"--authorize {declaration.name} true",
            existing=("yes" if existing.get("value") is True else "no")
            if fresh and isinstance(existing, dict) else None,
            empty_answer="yes",
            validate=_acquisition_validator(declaration.name, "true"),
        )
        if answer is None:
            continue
        if answer.value == "no":
            raise ProjectConfigurationError(
                f"Initialization needs the {declaration.subject} acquisition answered; "
                f"declined. Remove {declaration.capability!r} from the project's required capabilities or "
                f"authorize with 'devcapsule project config authorize "
                f"{declaration.name} true'."
            )
        record.authorize(declaration, True)
        settled.settle(declaration.name, answer.source)
    return settled


def _acquisition_validator(name: str, accepted_value: str) -> Any:
    # Boolean consent questions: yes/no is prompt vocabulary, the stored
    # value is the accepted one; 'default' accepts the recommendation like
    # everywhere else (owner ruling 2026-09-03).
    def validate(value: str) -> str:
        candidate = value.strip().lower()
        if candidate in {"yes", "y", "default", accepted_value.lower()}:
            return "yes"
        if candidate in {"no", "n", "none"}:
            # 'none' is the deny keyword; for a consent question denying is
            # declining.
            return "no"
        raise ProjectConfigurationError(
            f"Authorization {name!r} accepts yes, no, 'default', or the exact value "
            f"{accepted_value!r}."
        )

    return validate


def _looks_like_image_reference(value: str) -> bool:
    """A candidate the daemon could plausibly resolve: a tag/digest reference
    or a bare image ID — anything the developer might name a base by."""

    if not value or any(character.isspace() for character in value):
        return False
    if re.fullmatch(r"(sha256:)?[0-9a-f]{12,64}", value):
        return True
    return "/" in value or ":" in value or "@" in value


def _base_answer_validator(name: str, recommended: str) -> Any:
    """Authorization values are values (owner ruling 2026-09-03): the exact
    recommended digest, the reserved keyword ``default`` accepting it, or a
    reference-shaped developer base selection.  ``no`` declines; ``yes`` is
    not a value and was retired the same day it stopped making sense."""

    def validate(value: str) -> str:
        candidate = value.strip()
        if candidate.lower() == "default" or candidate == recommended:
            return "default"
        if candidate.lower() == "none":
            raise ProjectConfigurationError(
                f"Authorization {name!r} is mandatory and has no deny state; 'none' "
                "cannot apply. Accept the recommendation with 'default' (Enter) or "
                "name a locally built/pulled image to select instead."
            )
        if candidate.lower() in {"no", "n"}:
            return "no"
        if _looks_like_image_reference(candidate):
            return candidate
        raise ProjectConfigurationError(
            f"Authorization {name!r} takes a value: the base the resolution "
            f"matrix selected from the project's requirements ({recommended}), accepted "
            "as-is with the reserved keyword 'default' (interactively, Enter), "
            "or a locally built or pulled image (tag or image ID) to run on "
            "this checkout instead — DevCapsule reads its digest and metadata "
            "and asks you to confirm the selection. "
            f"'no' declines. {value!r} is neither a value "
            "nor an image reference."
        )

    return validate


def _record_base_selection(
    elicitor: Elicitor,
    record: CheckoutRecord,
    declaration: Any,
    *,
    selection: str,
    recommended: str,
    platform: str,
    less_pedantic: bool,
) -> None:
    """Record a developer-owned base selection with informed consent.

    The selection must be daemon-local: trust binds to the inspected image
    ID (D-0004 — never to a mutable tag), and init resolves offline, so a
    reference the daemon cannot produce is refused with the pull remedy.
    """

    try:
        immutable_registry_reference(selection)
    except ProjectConfigurationError:
        pass
    else:
        # D-0004: a different *published* digest needs its own
        # project-reviewed metadata; only a daemon-local selection is exempt.
        raise ProjectConfigurationError(
            f"Published base {selection!r} is not the lock-recommended digest; "
            "a different published artifact requires distinct project-reviewed "
            "metadata. A locally built or pulled image (named by tag or image "
            "ID) can be selected for this checkout instead."
        )
    local_base = required_local_image(selection)
    validate_base_image(local_base, platform=platform, expected_identity=None)
    if not less_pedantic:
        base_labels = "\n".join(
            f"  {key} = {value}"
            for key, value in sorted(local_base.labels.items())
            if key.startswith("devcapsule.")
        )
        presentation = (
            f"The lock recommends base {recommended}.\n"
            f"You selected local base {selection}:\n"
            f"  Image ID: {local_base.identity}\n"
            f"  Platform: {local_base.operating_system}/{local_base.architecture}\n"
            + (f"{base_labels}\n" if base_labels else "")
            + "This developer-owned selection overrides the recommendation for "
            "this checkout only; trust binds to the image ID above.\n"
            f"Authorize {selection}? (yes/no)"
        )
        consent = elicitor.seek(
            "base-image",
            facet="confirmation",
            description=presentation,
            remedy=f"devcapsule project config authorize base-image {selection}",
            empty_answer="yes",
            validate=_acquisition_validator("base-image (confirmation)", "yes"),
        )
        if consent is None:
            return
        if consent.value == "no":
            raise ProjectConfigurationError(
                f"Base selection {selection!r} declined; re-run with the "
                "recommended base or a different selection."
            )
    record.authorize(declaration, selection, local_base.identity)


def _elicit_host_answers(
    elicitor: Elicitor, manifest: Mapping[str, Any], lock: Mapping[str, Any], record: CheckoutRecord,
) -> tuple[str, ...]:
    """Only developer answers enter the authorization table; advice never does."""
    accepted: list[str] = []
    for name, declaration in authorization_declarations(manifest, lock).items():
        if declaration.required:
            continue
        answer = elicitor.seek(
            name, description=declaration.description,
            remedy=f"--authorize {name} VALUE", mandatory=False,
        )
        if answer is None or answer.source not in {SOURCE_COMMAND_LINE, SOURCE_PROMPT}:
            continue
        value = normalize_authorization_value(declaration, answer.value)
        if declaration.project_recommended and value == declaration.recommended_value:
            accepted.append(name)
        record.authorize(declaration, value)

    return tuple(accepted)


def _elicit_extra_answers(
    elicitor: Elicitor, answers: tuple[ProvidedAnswer, ...], manifest: Mapping[str, Any],
    lock: Mapping[str, Any], record: CheckoutRecord,
) -> None:
    """Use the registry for every ordinary/binding question, including required ones.

    Identity fields and configuration nodes can share a spelling; they must
    never share an answer cache. Every supplied name was checked against the
    registry by :func:`_reject_undeclared_answers` before the first question.
    """
    registry = build_node_registry(manifest, lock)
    supplied = {(answer.name, "value"): answer.value for answer in answers
                if answer.family in (CARRIER_FAMILY_SET, CARRIER_FAMILY_BIND)}
    questions = elicitor.child(supplied)
    for family in (CARRIER_FAMILY_SET, CARRIER_FAMILY_BIND):
        for node in registry.family(family):
            existing = None
            if family == CARRIER_FAMILY_SET:
                if node.name in record.values and (node.name, "value") not in supplied:
                    value = normalize_configuration_value(manifest, node.name, record.values[node.name])
                    existing = value if isinstance(value, str) else render_toml_scalar(value)
                elif node.name in record.omitted_values:
                    existing = "none"
            else:
                for provider, bindings in ((PROVIDER_HOST_DIRECTORY, record.directory_bindings),
                                            ("host-environment", record.environment_bindings)):
                    if node.name in bindings:
                        existing = f"{provider}:{bindings[node.name]}"
            def validate(value: str, name: str = node.name, kind: str = family) -> str:
                # Stage on a copy: rejected prompt attempts cannot partially
                # edit the real record or consume an earlier valid answer.
                candidate = deepcopy(record)
                apply_configuration_answers((ProvidedAnswer(kind, name, value),), manifest, lock, candidate)
                return value
            answer = questions.seek(
                node.name, description=f"{node.name}: {node.description or 'configuration value'}",
                remedy=f"--{family} {node.name} VALUE", mandatory=node.required,
                existing=existing, validate=validate,
            )
            if answer is not None:
                apply_configuration_answers((ProvidedAnswer(family, node.name, answer.value),), manifest, lock, record)
                if family == CARRIER_FAMILY_BIND and answer.source != SOURCE_EXISTING_RECORD:
                    provider, value = registry.split_bind_value(node.name, answer.value)
                    if provider == PROVIDER_HOST_DIRECTORY:
                        print(f"WARNING: exposing host directory read-write for {node.name}: {value} -> "
                              f"{node.declaration.container_path}; sensitivity: {node.declaration.sensitivity}; "
                              f"concurrent sharing: {node.declaration.concurrent}.", file=sys.stderr)
                    else:
                        print(f"WARNING: {value} will be visible to capsule processes and Docker inspection.",
                              file=sys.stderr)
    elicitor.include_missing(questions)
    if not questions.missing():
        questions.finish()


def apply_configuration_answers(
    answers: tuple[ProvidedAnswer, ...],
    manifest: Mapping[str, Any],
    lock: Mapping[str, Any],
    record: CheckoutRecord,
) -> None:
    """Stage set/bind answers using the same rules for init and individual edits."""

    registry = build_node_registry(manifest, lock)
    for answer in answers:
        if answer.family not in (CARRIER_FAMILY_SET, CARRIER_FAMILY_BIND):
            raise ProjectConfigurationError(f"Use the authorization operation for {answer.name!r}.")
        registry.answerable(answer.name, answer.family)
        if answer.family == CARRIER_FAMILY_SET:
            if answer.value.strip().lower() == "none":
                # The explicit-absence answer (owner ruling 2026-09-03): a
                # recorded decision to keep the node out of the runtime
                # config. A mandatory node has no absent state to choose.
                if registry.node(answer.name).required:
                    raise ProjectConfigurationError(
                        f"Configuration value {answer.name!r} is mandatory and cannot "
                        "be 'none'; record a value instead."
                    )
                record.omit_value(answer.name)
            else:
                record.set_value(
                    answer.name,
                    normalize_configuration_value(manifest, answer.name, answer.value),
                )
        elif answer.family == CARRIER_FAMILY_BIND:
            provider, value = registry.split_bind_value(answer.name, answer.value)
            if answer.name in record.state:
                raise ProjectConfigurationError(f"State resource {answer.name!r} was already adopted.")
            if provider == PROVIDER_HOST_DIRECTORY:
                source = Path(value).expanduser().resolve()
                if not source.is_dir():
                    raise ProjectConfigurationError(
                        f"Binding source is not an existing directory: {source}"
                    )
                record.directory_bindings[answer.name] = str(source)
            else:
                declaration = registry.node(answer.name).declaration
                if value != declaration.environment_variable:
                    raise ProjectConfigurationError(
                        f"Secret input {answer.name!r} must use host environment variable "
                        f"{declaration.environment_variable!r}."
                    )
                record.environment_bindings[answer.name] = value


def _fully_initialized(root: Path, manifest: Mapping[str, Any]) -> bool:
    """Whether all four owned artifacts stand with a fresh resolution.

    Partial and stale states stay init's own repair job; only this state
    makes a plain re-init meaningless.
    """

    input_path, output_path = checkout_record_paths(manifest, root)
    if not input_path.is_file() or not output_path.is_file():
        return False
    try:
        _path, lock = lock_for(root, manifest)
    except ProjectConfigurationError:
        # No IDE selected yet, or an unreadable selection: not fully initialized.
        return False
    checkout = load_checkout(input_path, manifest, root)
    resolution = load_resolution(output_path)
    if resolution.get("status") == "unresolved":
        return False
    if stale_resolution_inputs(manifest, lock, checkout, resolution, source_digest=manifest_source_digest(root)):
        return False
    return True


def _apply_answers_to_standing_checkout(
    root: Path,
    manifest_path: Path,
    lock_path: Path,
    platform: Platform,
    request: InitializeRequest,
) -> InitializeReport:
    """Apply a repeated init's carried answers to the standing checkout.

    Init stays non-idempotent over authored artifacts — identity flags on a
    standing manifest are not re-authored here — but the invocation's
    authorization, set, and bind answers are applied exactly as the config
    family would apply them, and the resolution is refreshed so 'project
    run' works immediately afterward.
    """

    manifest = current_manifest(load_toml(manifest_path), manifest_path).document()
    _, lock = lock_for(root, manifest)
    _reject_undeclared_answers(request.answers, manifest, lock, authoring=frozenset())
    declarations = authorization_declarations(manifest, lock)
    record = CheckoutRecord(manifest, root)
    authorize_answers = {
        (answer.name, "value"): answer.value
        for answer in request.answers
        if answer.family == "authorize"
    }
    elicitor = Elicitor(authorize_answers, interactive=False)
    settled = _elicit_acquisitions(
        elicitor,
        declarations,
        record,
        platform=str(platform),
        less_pedantic=request.less_pedantic,
    )
    _elicit_host_answers(elicitor, manifest, lock, record)
    _elicit_extra_answers(elicitor, request.answers, manifest, lock, record)
    elicitor.finish()
    record.write()
    resolve_report = resolve_checkout(root)

    project = manifest["project"]
    base_declaration = declarations.get("base-image")
    if base_declaration is not None:
        base_display = base_declaration.display_value or str(
            base_declaration.recommended_value
        )
    else:
        base_display = _base_display(lock)
    identity = _ProjectIdentity(
        name=str(project["name"]), slug=str(project["slug"]), creator=str(project["creator"]),
        mount=str(project["mount"]), policy=CapabilityPolicy.read(manifest),
    )
    return _initialize_report(
        manifest_path, "Kept", identity, lock_path, "Kept",
        base_display=base_display, recommendations=[], selection=_existing_selection(root, manifest),
        answered=tuple(settled.answered), carried=tuple(settled.carried), recommended=(),
        checkout_record=record.input_path, resolve=resolve_report,
    )


def _normalize_creator(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ProjectConfigurationError("The project creator must not be empty.")
    return candidate if ":" in candidate else f"mailto:{candidate}"


def _prepare_manifest(
    manifest_path: Path,
    existing_manifest: Mapping[str, Any] | None,
    identity: _ProjectIdentity,
    recommendations: list[tuple[str, str]],
    *,
    migrate: bool = False,
) -> tuple[str, str]:
    """Prepare a fresh manifest, or append only what an existing one lacks, without IO writes.

    An existing manifest is authored content: it is never rewritten from its
    parsed form, which would destroy comments and fields init does not model.
    The one exception is ``migrate``, the owner's ``--regenerate`` on a
    schema-1 file: ``existing_manifest`` is then the upgraded schema-2
    mapping, written by the one writer with the file's leading comment block
    kept; comments elsewhere are not, which the report says.
    """

    if existing_manifest is None or migrate:
        document = dict(_preview_manifest(identity)) if existing_manifest is None else deepcopy(dict(existing_manifest))
        existing_host = document.get("host", {})
        for name, justification in recommendations:
            path, supported = CURATED_HOST_RECOMMENDATIONS[name]
            if migrate and _declared_recommendation(existing_host if isinstance(existing_host, Mapping) else {}, path) is not None:
                continue
            node: dict[str, Any] = document.setdefault("host", {})
            for key in path:
                node = node.setdefault(key, {})
            node["value"] = supported
            node["justification"] = justification
        if migrate:
            preamble = manifest_preamble(manifest_path.read_text(encoding="utf-8"))
            return "Migrated", render_manifest(document, preamble=preamble)
        return "Created", render_manifest(document)

    host = existing_manifest.get("host", {})
    appended = False
    content = manifest_path.read_text(encoding="utf-8")
    for name, justification in recommendations:
        path = CURATED_HOST_RECOMMENDATIONS[name][0]
        if _declared_recommendation(host if isinstance(host, Mapping) else {}, path) is not None:
            continue
        content = content.rstrip("\n") + "\n" + "\n".join(
            _recommendation_block(name, justification)
        ) + "\n"
        appended = True
    if appended:
        return "Updated", content
    return "Honored existing", content


def _recommendation_block(name: str, justification: str) -> list[str]:
    path, supported = CURATED_HOST_RECOMMENDATIONS[name]
    value: AuthorizationScalar = supported
    return [
        "",
        f"[host.{'.'.join(path)}]",
        f"value = {render_toml_scalar(value)}",
        f"justification = {quote_toml(justification)}",
    ]
