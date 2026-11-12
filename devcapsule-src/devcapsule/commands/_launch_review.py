"""The review of a launch: what ``project run`` decides, in memory, from what was read.

``project run`` prepares a launch in three phases, and
:func:`devcapsule.commands._run_flow.prepare_launch` shows them in order:

1. Read. The project, the home and the checkout's record become a
   :class:`~devcapsule.configuration.derivation.CheckoutState`; the command
   line becomes a :class:`RunFlags`.
2. Decide. :func:`review_launch`, here: the state and the flags in, a
   :class:`LaunchReview` out, or a refusal. Answers are staged on copies in
   memory. Nothing is written.
3. Write. ``_run_flow.save_launch`` writes what the review staged.

A test of a decision builds a state from documents it writes as values, calls
:func:`review_launch`, and reads the result. It needs no project directory and
no home.

Nothing in this phase reads the machine it runs on. What a decision needs of
it is a value or a function the phase is given: the state's
:class:`~devcapsule.configuration.derivation.Host` carries the shell's
environment, looks up a bound directory and a local base image, and tells
the time; ``ask`` puts a decision to the developer; ``announce`` shows a
line at once.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
import shlex
from typing import Any, Callable, Mapping

from devcapsule.compat import DecisionPending
from devcapsule.configuration.authorization import (
    authorization_declarations, normalize_authorization_value, render_authorization_value,
)
from devcapsule.configuration.capabilities import (
    IDE_REQUIREMENT, CapabilityPolicy, LocalCapabilities, RequirementDeparture, capability_notes,
)
from devcapsule.configuration.derivation import CheckoutState, Selection, derive_plan
from devcapsule.configuration.docker_arguments import validate_name, validate_value
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.listing import Decision
from devcapsule.configuration.manifest_document import Recommendations
from devcapsule.configuration.operations import CheckoutRecord
from devcapsule.configuration.storage import ResolvedProject
from devcapsule.configuration.trust import Channel, HomeTrust, channels_for
from devcapsule.configuration.values import legacy_memory_names, memory_size_bytes, normalize_launcher_value

__all__ = [
    "BLOCKING_KINDS", "Ask", "LaunchReview", "Prepared", "RunFlags", "capability", "channel_for",
    "flags_after_upgrade", "refuse_contradictory_flags", "render_pending", "requested_ide", "review_launch",
    "stage_trust",
]

BLOCKING_KINDS = {"ide", "env", "renew", "trust", "consent", "value", "secret"}
"""The kinds of decision a launch cannot go on without."""


@dataclass(frozen=True)
class RunFlags:
    """Run-once choices unless ``save``; trust is saved after the complete review, even without ``save``."""

    ide: str | None = None
    capabilities: tuple[str, ...] = ()
    providers: tuple[tuple[str, str], ...] = ()
    memory: str | None = None
    cpus: str | None = None
    environment: tuple[str, ...] = ()  # NAME=VALUE saved for this run, or NAME taken from the host
    authorize: tuple[tuple[str, str], ...] = ()  # (node, value)
    trust: tuple[str, ...] = ()  # channel ids, recorded only after every blocking decision is settled
    save: bool = False
    allow_unverified: bool = False
    # Launch with the IDE given by ``ide`` although the project requires
    # another: one named departure from the project's contract, for this
    # launch only, warned and recorded, never saved (work order of 2026-10-28).
    force: bool = False


@dataclass
class Prepared:
    """What the launch runs with: the derived plan and this run's overrides."""

    selected: ResolvedProject
    host_overrides: dict[str, Any] = field(default_factory=dict)
    memory_override: int | None = None
    cpus_override: int | None = None
    environment_tokens: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    home: dict[str, Any] = field(default_factory=dict)


@dataclass
class LaunchReview:
    """What the review decided and staged. None of it is written yet."""

    state: CheckoutState
    """The state the review worked on, with the home's trust and the saved environment as the answers left them."""
    record: CheckoutRecord
    """The checkout's record with every recorded answer staged on it."""
    original: dict[str, Any]
    """The record's document as the review found it; the record is written only when it differs."""
    environment: dict[str, str | None]
    """The variables to save with the checkout's Docker arguments; None for one taken from the host."""
    accepted: list[str]
    """The channels accepted for the home during this review, in the order accepted."""
    selected: ResolvedProject
    """The derived plan."""
    host_overrides: dict[str, Any]
    memory_override: int | None
    cpus_override: int | None
    environment_tokens: list[str]
    notes: list[str]
    saved: bool
    """Whether ``--save`` was given: the flags then became the checkout's answers, not this run's overrides."""

    def prepared(self) -> Prepared:
        """The launch as the review leaves it, for a caller that writes nothing (``--print-command``)."""
        return Prepared(self.selected, self.host_overrides, self.memory_override, self.cpus_override,
                        self.environment_tokens, self.notes, self.state.home)


Ask = Callable[
    [CheckoutState, CheckoutRecord, dict[str, Any], Decision, dict[str, Any], dict[str, "str | None"], list[str], RunFlags],
    None,
]
"""Put one decision to the developer and stage the answer.

The arguments are the state, the staged record, the checkout document the
decision was assessed on, the decision, and the three collections an answer
can add to: the run-once host overrides, the variables to save, and the
channels accepted. It raises :class:`DecisionPending` when the developer
declines a decision the launch cannot go on without.
"""


def flags_after_upgrade(flags: RunFlags, host_overrides: Mapping[str, Any]) -> RunFlags:
    """The flags of a launch's second review, made after an upgrade may have changed what the checkout selects.

    The first review is complete and written. Saved flags are in the record
    now, so they are not given again; flags for this launch only are, and with
    them the host accesses that the developer allowed once at the terminal,
    ``host_overrides``. ``--trust`` is never given again: it accepted the
    channel that the first review showed, and an upgrade can change a
    channel. A channel that changed is then a pending decision.
    """
    again = RunFlags(allow_unverified=flags.allow_unverified) if flags.save else flags
    return replace(again, save=False, trust=(), authorize=tuple(
        (name, render_authorization_value(value)) for name, value in host_overrides.items()
    ))


def refuse_contradictory_flags(flags: RunFlags) -> None:
    """Refuse a command line that contradicts itself. It needs nothing but the flags."""
    if flags.force and flags.ide is None:
        raise ProjectConfigurationError(
            "--force names no departure; give the IDE to run instead of the project's required one: --ide IDE --force."
        )
    if flags.force and flags.save:
        # The owner requires a choice: save an allowed IDE or depart for one launch.
        raise ProjectConfigurationError(
            "--force applies to one launch and cannot be combined with --save. Launch without --save, "
            "or save a choice the project allows without --force."
        )


def review_launch(
    state: CheckoutState,
    flags: RunFlags,
    *,
    ask: Ask | None,
    announce: Callable[[str], None],
    print_only: bool = False,
    check_display: bool = True,
) -> LaunchReview:
    """Phase 2 of a launch's preparation: decide, in memory, from the state and the flags.

    ``ask`` is how a decision reaches the developer; None when there is no
    terminal. ``announce`` shows the developer one line at once, before any
    question. Without ``ask``, and always under ``print_only``, an unanswered
    decision the launch cannot go on without raises :class:`DecisionPending`
    that names each one. An invalid request raises
    :class:`ProjectConfigurationError`. Either way nothing has been written,
    because this function writes nothing.

    The state must name the checkout's record: ``input_path`` is the record
    found or the one the checkout will get. ``_run_flow.read_launch_state``
    sees to that.
    """
    refuse_contradictory_flags(flags)
    if flags.ide is not None:
        # Refused, or noted on the state as this launch's departure, before any approval is reviewed.
        requested_ide(state, flags)
    manifest = state.manifest
    assert state.input_path is not None, "the state names no record for the checkout"
    input_path = state.input_path
    record = CheckoutRecord.staged(input_path, state.checkout)
    original = deepcopy(record.document)
    notes: list[str] = list(capability_notes(manifest))
    # Channels accepted for this home, by flag or at the terminal:
    # staged on the state's home document, written with the record.
    accepted: list[str] = []
    host_overrides: dict[str, Any] = {}
    environment: dict[str, str | None] = {}
    environment_tokens: list[str] = []
    memory_override = None if flags.memory is None else memory_size_bytes(str(normalize_launcher_value("memory", flags.memory)))
    cpus_override = None if flags.cpus is None else int(normalize_launcher_value("cpus", flags.cpus))
    for item in flags.environment:
        name, separator, value = item.partition("=")
        validate_name(name)
        if separator:
            validate_value(value)
        state.saved_environment[name] = value if separator else None
        environment_tokens.extend(["--env", item])
        if flags.save:
            environment[name] = value if separator else None
    if flags.save:
        record.document = _selected_checkout(state, record.export(), flags)
        record = CheckoutRecord.staged(input_path, record.document)
        _resource_answers(record, manifest, flags)
    for node, value in flags.authorize:
        declaration = authorization_declarations(manifest, state.composed_lock(record.document)).get(node)
        if declaration is None or (declaration.required and not flags.save):
            raise ProjectConfigurationError(f"Authorization {node!r} cannot be answered for one run; the host accesses can.")
        normalized = normalize_authorization_value(declaration, value)
        if flags.save:
            record.authorize(declaration, normalized)
        else:
            host_overrides[node] = normalized
            announce(f"Run-once authorization: {node} = {value}")

    def launch_checkout() -> dict[str, Any]:
        """The checkout document this launch runs on: the staged record with the run-once choices laid over it."""
        saved = record.export()
        document = _selected_checkout(state, saved, flags) if not flags.save else saved
        local = Selection(LocalCapabilities.read(document), state.surfaces)
        recommended_ide = Recommendations.read(manifest).ide
        # A lock that still pins an IDE (written when the project required
        # one) stands for every checkout that chose none; the recommended IDE
        # is the default only when the lock is project-only.
        pinned_surface = state.composed_lock(document).get("components", {}).get("interactive-surface")
        if (local.ide is None and recommended_ide is not None and pinned_surface is None
                and not (set(CapabilityPolicy.read(manifest).required) & set(state.surfaces))):
            local.ide = recommended_ide
            document = state.with_selection(local, checkout=document, allow_unverified=flags.allow_unverified)
        transient = CheckoutRecord.staged(input_path, document)
        if not flags.save:
            _resource_answers(transient, manifest, flags)
        declarations = authorization_declarations(manifest, state.composed_lock(document))
        for name, value in host_overrides.items():
            transient.authorize(declarations[name], value)
        return transient.export()

    # Assess, ask one decision, assess again: an answer can add decisions, as an IDE adds its consents.
    asked: set[tuple[str, str]] = set()
    while True:
        checkout = launch_checkout()
        for channel_id in flags.trust:
            if channel_id not in accepted:
                stage_trust(state, checkout, channel_id, accepted)
        decisions = list(state.listing(checkout, check_display=check_display).decisions)
        blocking = [d for d in decisions if d.kind in BLOCKING_KINDS]
        if blocking and (print_only or ask is None):
            raise DecisionPending(render_pending(blocking, state.root))
        pending = [d for d in decisions if (d.kind, d.name) not in asked]
        if not pending or print_only or ask is None:
            if blocking:
                raise DecisionPending(render_pending(blocking, state.root))
            for decision in decisions:
                if decision.kind == "console":
                    notes.append(
                        f"The console's request {decision.name} of {decision.reason} awaits your confirmation: "
                        f"{decision.description}. Apply or discard: {decision.command}"
                    )
                else:
                    notes.append(
                        f"The project asks for {decision.description} ({decision.reason}); not granted this run. "
                        f"Allow or deny: {decision.command}"
                    )
            break
        decision = pending[0]
        asked.add((decision.kind, decision.name))
        ask(state, record, checkout, decision, host_overrides, environment, accepted, flags)

    # Validation can still refuse (for example, an invalid binding). Derive
    # first so neither --save nor a terminal answer escapes on that path.
    selected = derive_plan(state, checkout, write=False)
    for row in state.listing(checkout, check_display=check_display).rows:
        if row.kind == "access" and "(kept;" in row.source:
            notes.append(f"Host access {row.name}: {row.effective}; {row.source}.")
    return LaunchReview(
        state=state, record=record, original=original, environment=environment, accepted=accepted,
        selected=selected, host_overrides=host_overrides, memory_override=memory_override,
        cpus_override=cpus_override, environment_tokens=environment_tokens, notes=notes, saved=flags.save,
    )


def _resource_answers(record: CheckoutRecord, manifest: Mapping[str, Any], flags: RunFlags) -> None:
    """Stage ``--memory`` and ``--cpus`` on a record as the checkout's values."""
    for name, value in (("memory", flags.memory), ("cpus", flags.cpus)):
        if value is not None:
            record.set_value(name, normalize_launcher_value(name, value))
            if name == "memory":
                for alias in legacy_memory_names(manifest):
                    record.values.pop(alias, None)
                    record.omitted_values.discard(alias)


def _selected_checkout(state: CheckoutState, document: dict[str, Any], flags: RunFlags) -> dict[str, Any]:
    """The checkout document with the IDE, capabilities and providers of the flags selected on it."""
    if flags.ide is None and not flags.capabilities and not flags.providers:
        return document
    selection = Selection(LocalCapabilities.read(document), state.surfaces)
    if flags.ide is not None:
        selection.ide = requested_ide(state, flags)
    for name in flags.capabilities:
        canonical = state.matrix.canonical_name(name)
        if state.matrix.is_ide(canonical):
            raise ProjectConfigurationError(f"Choose an IDE with '--ide {canonical}'.")
        selection.without = {item for item in selection.without if state.matrix.canonical_name(item) != canonical}
        selection.extra.add(canonical)
    for name, component in flags.providers:
        selection.use(state.matrix, CapabilityPolicy.read(state.manifest), Recommendations.read(state.manifest), name, component)
    return state.with_selection(selection, checkout=document, allow_unverified=flags.allow_unverified)


def requested_ide(state: CheckoutState, flags: RunFlags) -> str:
    """The IDE capability ``--ide`` names, checked against the project's required IDE.

    A component name (``codium``) or a capability name (``frontend-ide``)
    selects the same surface. Another IDE than the project requires is
    refused with the explicit override named; with ``--force`` it is one
    named departure of this launch (:data:`IDE_REQUIREMENT`), and the plan
    derives from the policy without that requirement. ``--force`` with
    nothing to set aside is refused: it never selects a replacement itself.
    """
    assert flags.ide is not None
    requested = capability(flags.ide, state.surfaces, "IDE")
    required = state.required_ide()
    conflicts = required is not None and state.matrix.canonical_name(required) != state.matrix.canonical_name(requested)
    if conflicts:
        assert required is not None
        required_component = state.shared_lock.get("components", {}).get("interactive-surface") or state.surfaces[required]
        if not flags.force:
            override = shlex.join(["devcapsule", "project", "--path", str(state.root), "run", "--ide", flags.ide.strip(), "--force"])
            raise ProjectConfigurationError(
                f"The project requires {required} ({required_component}); {requested} ({state.surfaces[requested]}) is "
                f"another IDE. To launch it once, setting the requirement aside for that launch only: {override}. "
                "The project's requirement and this checkout's saved IDE stay as they are."
            )
        state.depart(RequirementDeparture(IDE_REQUIREMENT, required, requested))
    elif flags.force:
        raise ProjectConfigurationError(
            f"--force has nothing to set aside: {requested} is the project's required IDE."
            if required is not None else
            f"--force has nothing to set aside: the project requires no IDE; '--ide {flags.ide.strip()}' alone launches {requested}."
        )
    return requested


def channel_for(lock: Mapping[str, Any], channel_id: str) -> Channel:
    """The channel ``channel_id`` of a lock; refused with the lock's channels when unknown."""
    channels = channels_for(lock)
    channel = channels.get(channel_id)
    if channel is None:
        raise ProjectConfigurationError(
            f"No channel {channel_id!r} on this project; its channels: " + (", ".join(sorted(channels)) or "none") + "."
        )
    return channel


def stage_trust(state: CheckoutState, checkout: Mapping[str, Any], channel_id: str, accepted: list[str]) -> None:
    """Stage the acceptance of ``channel_id`` on the state's home document; written with the answers."""
    channel = channel_for(state.composed_lock(checkout), channel_id)
    trust = HomeTrust.read(state.home).with_channel(channel, accepted_at=state.host.now())
    state.home = {**state.home, "trust": trust.document()}
    if channel_id not in accepted:
        accepted.append(channel_id)


def capability(value: str, names: Mapping[str, str], kind: str) -> str:
    """The capability a developer's word names: a capability name, or the component that provides one."""
    candidate = value.strip()
    by_component = {component: name for name, component in names.items()}
    candidate = by_component.get(candidate, candidate)
    if candidate not in names:
        raise ProjectConfigurationError(f"Unknown {kind} {value!r}; choose one of {', '.join(sorted(names))}.")
    return candidate


def render_pending(decisions: list[Decision], root: Path) -> str:
    """The status-3 text: every answer is still staged, including trust."""
    lines = ["the launch of this checkout needs answers:"]
    for decision in decisions:
        flag = {"ide": "--ide IDE", "env": f"--env {decision.name}=VALUE", "consent": f"--authorize {decision.name} {decision.value}" if decision.name == "host-x11" else "",
                "access": f"--authorize {decision.name} {decision.value}", "renew": f"--authorize {decision.name} {decision.value}",
                "trust": f"--trust {decision.name}", "value": "", "secret": "", "console": ""}[decision.kind]
        lines.append(f"  {decision.kind} {decision.name}: {decision.description}" + (f"  ({decision.reason})" if decision.reason else ""))
        lines.append("      " + (f"{flag}  |  " if flag else "") + decision.command)
    lines.append("Nothing was written. Answer on the command line or in a terminal.")
    return "\n".join(lines)
