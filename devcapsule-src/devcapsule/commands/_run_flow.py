"""What ``project run`` does before it launches: derive, report, ask.

Principle 2 of the CLI UX redesign work order of 2026-10-24: what follows
from the project and the home is derived and shown; what encodes the
developer's intent is asked, once, in the settled order (the command line,
an earlier answer, the record, a derivable default, and only then a prompt);
every question has a flag. Section 3.4: without a terminal nothing is
asked; a missing answer ends the command with exit status 3, naming each
decision with its flag or command, and nothing is written. Answer 12: every
``run`` flag applies to this launch only; ``--save`` records the flags given
as the checkout's answers before launching.

The decisions come from the listing (:mod:`devcapsule.configuration.listing`),
so what ``run`` asks is exactly what ``config check`` reports. The IDE, a
required environment variable, a consent, an invalid host answer,
a required value and a required secret block the
launch until answered; so does a vendor's or DevCapsule's channel the
home has not accepted yet (D-0011, once per home); a host access
the project recommends and the developer never answered is asked, and "not
now" launches with the secure default; so is a widening the console asked
for during an earlier run, kept until applied or discarded here.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import getpass
from pathlib import Path
import shlex
import sys
from typing import Any, Callable, Mapping, TextIO

from devcapsule.compat import DecisionPending
from devcapsule.configuration.authorization import HOME_CAPABILITY_DEFAULTS, authorization_declarations, normalize_authorization_value
from devcapsule.configuration.capabilities import IDE_REQUIREMENT, CapabilityPolicy, LocalCapabilities, RequirementDeparture
from devcapsule.configuration.derivation import CheckoutState, Selection, derive_plan, load_state, register_checkout
from devcapsule.configuration.docker_arguments import arguments_path, read_environment, update_environment, validate_name, validate_value
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.manifest_document import Recommendations
from devcapsule.configuration.listing import Decision
from devcapsule.configuration.operations import CheckoutRecord, apply_configuration_answers, ProvidedAnswer
from devcapsule.configuration.storage import ResolvedProject, atomic_write, checkout_name_for, manifest_for, write_settings
from devcapsule.configuration.trust import Channel, HomeTrust, channels_for
from devcapsule.configuration.values import legacy_memory_names, memory_size_bytes, normalize_launcher_value

__all__ = ["Prepared", "RunFlags", "prepare_launch"]

BLOCKING_KINDS = {"ide", "env", "renew", "trust", "consent", "value", "secret"}


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


def load_launch_state(start: Path, flags: RunFlags) -> CheckoutState:
    """Load the launch inputs and reject invalid IDE requests before any approval review.

    Departures are applied in memory. The staged launch review still checks
    consent, trust, dependencies and host access for the requested environment.
    """
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
    root, manifest = manifest_for(start)
    state = load_state(root, manifest)
    if flags.ide is not None:
        _requested_ide(state, flags)
    return state


def prepare_launch(
    start: Path,
    flags: RunFlags,
    *,
    interactive: bool | None = None,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    print_only: bool = False,
    check_display: bool = True,
) -> Prepared:
    """Review in memory, then save answers and the plan after every blocking decision.

    ``print_only`` never asks or writes. Without a terminal, an unanswered
    blocking decision raises :class:`DecisionPending` before any write.
    """
    interactive = sys.stdin.isatty() if interactive is None else interactive
    output = output_stream if output_stream is not None else sys.stdout
    state = load_launch_state(start, flags)
    root, manifest = state.root, state.manifest
    input_path = register_checkout(state, write=False)
    record = CheckoutRecord.staged(input_path, state.checkout)
    original = deepcopy(record.document)
    from devcapsule.configuration.capabilities import capability_notes
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
            print(f"Run-once authorization: {node} = {value}", file=sys.stderr)

    def launch_checkout() -> dict[str, Any]:
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

    asked: set[tuple[str, str]] = set()
    reader = input_stream.readline if input_stream is not None else lambda: sys.stdin.readline()
    while True:
        checkout = launch_checkout()
        for channel_id in flags.trust:
            if channel_id not in accepted:
                _stage_trust(state, checkout, channel_id, accepted)
        decisions = list(state.listing(checkout, check_display=check_display).decisions)
        blocking = [d for d in decisions if d.kind in BLOCKING_KINDS]
        if blocking and (print_only or not interactive):
            raise DecisionPending(_render_pending(blocking, root))
        pending = [d for d in decisions if (d.kind, d.name) not in asked]
        if not pending or print_only or not interactive:
            if blocking:
                raise DecisionPending(_render_pending(blocking, root))
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
        _settle(state, record, checkout, decision, host_overrides, environment, accepted, flags, reader, output)

    # Validation can still refuse (for example, an invalid binding). Derive
    # first so neither --save nor a terminal answer escapes on that path.
    selected = derive_plan(state, checkout, write=False)
    for row in state.listing(checkout, check_display=check_display).rows:
        if row.kind == "access" and "(kept;" in row.source:
            notes.append(f"Host access {row.name}: {row.effective}; {row.source}.")
    if not print_only:
        if environment:
            read_environment(arguments_path(input_path))  # Refuse ambiguous saved tokens before any write.
        if not state.registered:
            notes.append(f"Registered this checkout: {checkout_name_for(manifest, input_path)} ({root}).")
        if not state.registered or record.document != original:
            record.write()
        for name, saved_value in environment.items():
            update_environment(arguments_path(input_path), name, saved_value, from_host=saved_value is None)
        atomic_write(selected.resolution_path, render_toml(selected.resolution))
        if accepted:
            write_settings({"trust": HomeTrust.read(state.home).document()})
            notes.extend(f"Accepted the channel {channel_id} for this home." for channel_id in accepted)
        if flags.save:
            notes.insert(0, "Recorded the flags given for this checkout.")
            environment_tokens = []
            memory_override = cpus_override = None
    return Prepared(selected, host_overrides, memory_override, cpus_override, environment_tokens, notes, state.home)


def _resource_answers(record: CheckoutRecord, manifest: Mapping[str, Any], flags: RunFlags) -> None:
    for name, value in (("memory", flags.memory), ("cpus", flags.cpus)):
        if value is not None:
            record.set_value(name, normalize_launcher_value(name, value))
            if name == "memory":
                for alias in legacy_memory_names(manifest):
                    record.values.pop(alias, None)
                    record.omitted_values.discard(alias)


def _selected_checkout(state: CheckoutState, document: dict[str, Any], flags: RunFlags) -> dict[str, Any]:
    if flags.ide is None and not flags.capabilities and not flags.providers:
        return document
    selection = Selection(LocalCapabilities.read(document), state.surfaces)
    if flags.ide is not None:
        selection.ide = _requested_ide(state, flags)
    for capability in flags.capabilities:
        name = state.matrix.canonical_name(capability)
        if state.matrix.is_ide(name):
            raise ProjectConfigurationError(f"Choose an IDE with '--ide {name}'.")
        selection.without = {item for item in selection.without if state.matrix.canonical_name(item) != name}
        selection.extra.add(name)
    for capability, component in flags.providers:
        selection.use(state.matrix, CapabilityPolicy.read(state.manifest), Recommendations.read(state.manifest), capability, component)
    return state.with_selection(selection, checkout=document, allow_unverified=flags.allow_unverified)


def _requested_ide(state: CheckoutState, flags: RunFlags) -> str:
    """The IDE capability ``--ide`` names, checked against the project's required IDE.

    A component name (``codium``) or a capability name (``frontend-ide``)
    selects the same surface. Another IDE than the project requires is
    refused with the explicit override named; with ``--force`` it is one
    named departure of this launch (:data:`IDE_REQUIREMENT`), and the plan
    derives from the policy without that requirement. ``--force`` with
    nothing to set aside is refused: it never selects a replacement itself.
    """
    assert flags.ide is not None
    requested = _capability(flags.ide, state.surfaces, "IDE")
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


def launch_listing_document(selected: ResolvedProject) -> dict[str, Any]:
    """The ``config show --json`` document of the launch's checkout, for the capsule's own inspection."""
    from devcapsule.configuration.storage import checkout_name_for
    state = load_state(selected.root, selected.manifest)
    for departure in selected.departures:
        state.depart(departure)
    listing = state.listing(selected.checkout)
    document = listing.document()
    declarations = authorization_declarations(selected.manifest, selected.lock)
    for row in document["rows"]:
        if row["kind"] == "access" and row["name"] in HOME_CAPABILITY_DEFAULTS:
            row["exposure"] = HOME_CAPABILITY_DEFAULTS[row["name"]][1]
            declaration = declarations[row["name"]]
            row["reason"] = declaration.description if declaration.project_recommended else ""
    identity = selected.manifest["project"]
    return {
        **document,
        "context": "at launch",
        "project": {"creator": identity["creator"], "slug": identity["slug"]},
        "checkout": {"name": checkout_name_for(selected.manifest, selected.checkout_path),
                     "launcher-path": str(selected.root), "input": str(selected.checkout_path)},
    }


def project_channel(root: Path, manifest: dict[str, Any], channel_id: str) -> Channel:
    """The channel ``channel_id`` of this project's lock; refused with the project's channels when unknown."""
    state = load_state(root, manifest)
    return _channel_for(state.composed_lock(), channel_id)


def _channel_for(lock: Mapping[str, Any], channel_id: str) -> Channel:
    channels = channels_for(lock)
    channel = channels.get(channel_id)
    if channel is None:
        raise ProjectConfigurationError(
            f"No channel {channel_id!r} on this project; its channels: " + (", ".join(sorted(channels)) or "none") + "."
        )
    return channel


def accept_channel(root: Path, manifest: dict[str, Any], channel_id: str) -> Path:
    """Record the user's acceptance of one channel for this home now; return the record's path."""
    from devcapsule.configuration.storage import load_trust
    channel = project_channel(root, manifest, channel_id)
    return write_settings({"trust": HomeTrust.read(load_trust()).with_channel(channel).document()})


def _stage_trust(state: CheckoutState, checkout: Mapping[str, Any], channel_id: str, accepted: list[str]) -> None:
    """Stage the acceptance of ``channel_id`` on the state's home document; written with the answers."""
    channel = _channel_for(state.composed_lock(checkout), channel_id)
    trust = HomeTrust.read(state.home).with_channel(channel)
    state.home = {**state.home, "trust": trust.document()}
    if channel_id not in accepted:
        accepted.append(channel_id)


def _capability(value: str, names: Mapping[str, str], kind: str) -> str:
    candidate = value.strip()
    by_component = {component: name for name, component in names.items()}
    candidate = by_component.get(candidate, candidate)
    if candidate not in names:
        raise ProjectConfigurationError(f"Unknown {kind} {value!r}; choose one of {', '.join(sorted(names))}.")
    return candidate


def _render_pending(decisions: list[Decision], root: Path) -> str:
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


def _settle(
    state: CheckoutState, record: CheckoutRecord, checkout: dict[str, Any], decision: Decision,
    host_overrides: dict[str, Any], environment: dict[str, str | None], accepted: list[str], flags: RunFlags,
    reader: Callable[[], str], output: TextIO,
) -> None:
    """Stage one answer. Reassess before the next question; an IDE can add consents."""
    root, manifest = state.root, state.manifest
    if decision.kind == "ide":
        output.write("The project leaves the IDE to you. Choose one:\n")
        for index, (name, version) in enumerate(decision.choices, start=1):
            output.write(f"  {index}. {name:<13} {version}\n")
        choice = _ask(output, reader, f"IDE [1-{len(decision.choices)}]: ")
        names = [name for name, _ in decision.choices]
        picked = names[int(choice) - 1] if choice.isdecimal() and 1 <= int(choice) <= len(names) else _capability(choice, state.surfaces, "IDE")
        selection = Selection(LocalCapabilities.read(record.document), state.surfaces)
        selection.ide = picked
        selected = state.with_selection(selection, checkout=record.document, allow_unverified=flags.allow_unverified)
        record.document["capabilities"] = selected["capabilities"]
        if "version-set" in selected:
            record.document["version-set"] = selected["version-set"]
        output.write("IDE selected. Answers will be recorded when the review is complete.\n")
    elif decision.kind == "env":
        output.write(f"The project needs {decision.name}" + (f": {decision.reason}" if decision.reason else "") + "\n")
        value = _hidden(output, reader, f"{decision.name} [hidden, kept in this home]: ")
        validate_value(value)
        environment[decision.name] = value
        state.saved_environment[decision.name] = value
    elif decision.kind == "console":
        # A widening the console asked for in an earlier run: the user's "apply"
        # is the command 'config console apply ID', run now, as that command would.
        from devcapsule.commands._console_channel import apply_deferred, discard_deferred
        output.write(f"The console asked at {decision.reason}: {decision.description}\n")
        answer = _ask(output, reader, "[a]pply it now, as 'config console apply' would, [d]iscard it, Enter = keep it for later: ").lower()
        if answer in {"a", "apply"}:
            before = load_state(root, state.manifest)
            status, text = apply_deferred(root, record.input_path, decision.name)
            output.write((text or ("Recorded." if status == 0 else "The command failed; the request remains pending.")) + "\n")
            if status == 0:
                after = load_state(root, state.manifest)
                # Keep answers staged by this run, and overlay only what the
                # explicitly confirmed command changed on disk.
                def changed(target: dict[str, Any], old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
                    result = deepcopy(target)
                    for key in old.keys() | new.keys():
                        if key in old and key in new and old[key] == new[key]:
                            continue
                        if key not in new:
                            result.pop(key, None)
                        elif isinstance(old.get(key, {}), dict) and isinstance(new[key], dict) and isinstance(result.get(key), dict):
                            result[key] = changed(result[key], old.get(key, {}), new[key])
                        else:
                            result[key] = deepcopy(new[key])
                    return result
                record._load(record.input_path, changed(record.export(), before.checkout, after.checkout))
                state.checkout = record.export()
                state.home = changed(state.home, before.home, after.home)
                state.saved_environment = {**after.saved_environment, **environment}
        elif answer in {"d", "discard"}:
            discard_deferred(record.input_path, decision.name)
            output.write("Discarded.\n")
        else:
            output.write(f"Kept. Apply or discard later: {decision.command}\n")
    elif decision.kind == "trust":
        output.write(f"{decision.description}\n")
        if decision.reason:
            output.write(f"  {decision.reason}\n")
        answer = _ask(output, reader, "Accept for this DevCapsule home? [y/N]: ").lower()
        if answer in {"y", "yes"}:
            _stage_trust(state, checkout, decision.name, accepted)
            output.write(f"Accepted for this review. Trust will be saved when all required answers are complete. "
                         f"Withdraw: devcapsule home trust withdraw {decision.name}\n")
        else:
            output.write(f"Not accepted. Accept later: {decision.command}\n")
            raise DecisionPending(_render_pending([decision], root))
    elif decision.kind in {"access", "renew", "consent"}:
        declaration = authorization_declarations(manifest, state.composed_lock(checkout))[decision.name]
        if decision.kind in {"access", "renew"}:
            output.write(HOME_CAPABILITY_DEFAULTS[decision.name][1] + "\n")
        if decision.kind == "access":
            output.write(f"The project asks for {decision.description}: {decision.reason}\n")
            answer = _ask(output, reader, "[a]llow for this checkout, allow [o]nce, [d]eny for this checkout, Enter = not now: ").lower()
        elif decision.kind == "renew":
            output.write(f"Your answer for {decision.name} predates the project's current recommendation: {decision.reason}\n")
            answer = _ask(output, reader, f"[a]llow {decision.name} {decision.value} for this checkout, or [d]eny: ").lower()
        else:
            output.write(f"{decision.description}\n")
            answer = _ask(output, reader, "Accept? [y/N]: ").lower()
        if answer in ({"y", "yes"} if decision.kind == "consent" else {"a", "allow"}):
            record.authorize(declaration, normalize_authorization_value(declaration, decision.value))
        elif answer in {"d", "deny"} and decision.kind != "consent":
            record.authorize(declaration, normalize_authorization_value(declaration, decision.deny))
        elif answer in {"o", "once"} and decision.kind == "access":
            host_overrides[decision.name] = normalize_authorization_value(declaration, decision.value)
        elif decision.kind == "access":
            output.write(f"Not now; the secure default applies. Allow or deny later: {decision.command}\n")
        else:
            raise DecisionPending(_render_pending([decision], root))
    elif decision.kind == "value":
        value = _ask(output, reader, f"{decision.name} ({decision.description}): ")
        apply_configuration_answers((ProvidedAnswer("set", decision.name, value),), manifest, state.composed_lock(checkout), record)
    elif decision.kind == "secret":
        output.write(f"{decision.description}\n")
        answer = _ask(output, reader, f"Bind {decision.name} to the host's variable {decision.variable}? [y/N]: ").lower()
        if answer in {"y", "yes"}:
            apply_configuration_answers((ProvidedAnswer("bind", decision.name, f"host-environment:{decision.variable}"),),
                                        manifest, state.composed_lock(checkout), record)
        else:
            raise DecisionPending(_render_pending([decision], root))


def _ask(output: TextIO, reader: Callable[[], str], prompt: str) -> str:
    output.write(prompt)
    output.flush()
    line = reader()
    if line == "":
        raise DecisionPending("the terminal closed before the answer; nothing was written")
    return line.rstrip("\n").strip()


def _hidden(output: TextIO, reader: Callable[[], str], prompt: str) -> str:
    if sys.stdin.isatty() and reader is not None and reader.__name__ == "<lambda>":
        try:
            return getpass.getpass(prompt)
        except (EOFError, getpass.GetPassWarning):
            raise DecisionPending("the terminal closed before the answer; nothing was written") from None
    return _ask(output, reader, prompt)
