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
import getpass
from pathlib import Path
import sys
from typing import Any, Callable, TextIO

from devcapsule.commands._launch_review import (
    LaunchReview, Prepared, RunFlags, capability, channel_for, refuse_contradictory_flags, render_pending,
    requested_ide, review_launch, stage_trust,
)
from devcapsule.compat import DecisionPending
from devcapsule.configuration.authorization import HOME_CAPABILITY_DEFAULTS, authorization_declarations, normalize_authorization_value
from devcapsule.configuration.capabilities import LocalCapabilities
from devcapsule.configuration.console_requests import deferred_rows
from devcapsule.configuration.derivation import CheckoutState, Selection, load_state, register_checkout
from devcapsule.configuration.docker_arguments import arguments_path, read_environment, update_environment, validate_value
from devcapsule.configuration.file_formats import render_toml
from devcapsule.configuration.listing import Decision
from devcapsule.configuration.operations import CheckoutRecord, apply_configuration_answers, ProvidedAnswer
from devcapsule.configuration.storage import ResolvedProject, atomic_write, checkout_name_for, manifest_for, write_settings
from devcapsule.configuration.trust import Channel, HomeTrust

__all__ = ["Prepared", "RunFlags", "prepare_launch"]


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
    """Prepare a launch in three phases: read, decide in memory, write.

    ``print_only`` never asks or writes. Without a terminal, an unanswered
    blocking decision raises :class:`DecisionPending` before any write.
    """
    # A command line that contradicts itself is refused before anything is read.
    refuse_contradictory_flags(flags)

    # Phase 1, read: the project, the home and the checkout's record, and what the terminal is.
    state = read_launch_state(start)
    interactive = sys.stdin.isatty() if interactive is None else interactive
    reader = input_stream.readline if input_stream is not None else lambda: sys.stdin.readline()
    output = output_stream if output_stream is not None else sys.stdout

    # Phase 2, decide: from the state and the flags alone. Nothing is written.
    def ask_at_terminal(
        state: CheckoutState, record: CheckoutRecord, checkout: dict[str, Any], decision: Decision,
        host_overrides: dict[str, Any], environment: dict[str, str | None], accepted: list[str], flags: RunFlags,
    ) -> None:
        _settle(state, record, checkout, decision, host_overrides, environment, accepted, flags, reader, output)

    review = review_launch(state, flags, ask=ask_at_terminal if interactive else None,
                           announce=lambda line: print(line, file=sys.stderr),
                           print_only=print_only, check_display=check_display)

    # Phase 3, write: what the review staged.
    return review.prepared() if print_only else save_launch(review)


def read_launch_state(start: Path) -> CheckoutState:
    """Phase 1 of a launch's preparation: read the project at ``start``, the home and the checkout's record.

    A checkout that has no record yet is given the path its record will have,
    which can mean looking for a free name among the project's checkouts.
    Nothing is written.
    """
    root, manifest = manifest_for(start)
    state = load_state(root, manifest)
    register_checkout(state, write=False)
    return state


def save_launch(review: LaunchReview) -> Prepared:
    """Phase 3 of a launch's preparation: write what the review staged, and say what was written.

    The checkout's record, when new or changed; the variables saved with its
    Docker arguments; the derived plan; the home's trust, when a channel was
    accepted. With ``--save`` the flags are now the checkout's answers, so the
    launch carries no run-once overrides of its own.
    """
    state, record, selected = review.state, review.record, review.selected
    notes = list(review.notes)
    environment_tokens, memory_override, cpus_override = review.environment_tokens, review.memory_override, review.cpus_override
    if review.environment:
        read_environment(arguments_path(record.input_path))  # Refuse ambiguous saved tokens before any write.
    if not state.registered:
        notes.append(f"Registered this checkout: {checkout_name_for(state.manifest, record.input_path)} ({state.root}).")
    if not state.registered or record.document != review.original:
        record.write()
        state.registered = True
    for name, saved_value in review.environment.items():
        update_environment(arguments_path(record.input_path), name, saved_value, from_host=saved_value is None)
    atomic_write(selected.resolution_path, render_toml(selected.resolution))
    if review.accepted:
        write_settings({"trust": HomeTrust.read(state.home).document()})
        notes.extend(f"Accepted the channel {channel_id} for this home." for channel_id in review.accepted)
    if review.saved:
        notes.insert(0, "Recorded the flags given for this checkout.")
        environment_tokens = []
        memory_override = cpus_override = None
    return Prepared(selected, review.host_overrides, memory_override, cpus_override, environment_tokens, notes, state.home)


def load_launch_state(start: Path, flags: RunFlags) -> CheckoutState:
    """Read the launch's inputs and refuse an invalid IDE request, before any approval is reviewed.

    For the command that offers software approvals ahead of the launch: the
    same refusals :func:`prepare_launch` gives first, given early. A departure
    is noted on the returned state, in memory.
    """
    refuse_contradictory_flags(flags)
    root, manifest = manifest_for(start)
    state = load_state(root, manifest)
    if flags.ide is not None:
        requested_ide(state, flags)
    return state


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
    return channel_for(state.composed_lock(), channel_id)


def accept_channel(root: Path, manifest: dict[str, Any], channel_id: str) -> Path:
    """Record the user's acceptance of one channel for this home now; return the record's path."""
    from devcapsule.configuration.storage import load_trust
    channel = project_channel(root, manifest, channel_id)
    return write_settings({"trust": HomeTrust.read(load_trust()).with_channel(channel).document()})


def _settle(
    state: CheckoutState, record: CheckoutRecord, checkout: dict[str, Any], decision: Decision,
    host_overrides: dict[str, Any], environment: dict[str, str | None], accepted: list[str], flags: RunFlags,
    reader: Callable[[], str], output: TextIO,
) -> None:
    """Put one decision to the developer at the terminal and stage the answer.

    The review assesses again before the next question, since an IDE can add
    consents. Everything is staged in memory, with one exception: applying or
    discarding a console request runs that command now, which writes, and the
    state is then brought up to date with what the command left.
    """
    root, manifest = state.root, state.manifest
    if decision.kind == "ide":
        output.write("The project leaves the IDE to you. Choose one:\n")
        for index, (name, version) in enumerate(decision.choices, start=1):
            output.write(f"  {index}. {name:<13} {version}\n")
        choice = _ask(output, reader, f"IDE [1-{len(decision.choices)}]: ")
        names = [name for name, _ in decision.choices]
        picked = names[int(choice) - 1] if choice.isdecimal() and 1 <= int(choice) <= len(names) else capability(choice, state.surfaces, "IDE")
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
                # The state is a snapshot; the command just changed what it was read from.
                state.registered, state.deferred = after.registered, after.deferred
        elif answer in {"d", "discard"}:
            discard_deferred(record.input_path, decision.name)
            state.deferred = tuple(deferred_rows(state.input_path, state.root))
            output.write("Discarded.\n")
        else:
            output.write(f"Kept. Apply or discard later: {decision.command}\n")
    elif decision.kind == "trust":
        output.write(f"{decision.description}\n")
        if decision.reason:
            output.write(f"  {decision.reason}\n")
        answer = _ask(output, reader, "Accept for this DevCapsule home? [y/N]: ").lower()
        if answer in {"y", "yes"}:
            stage_trust(state, checkout, decision.name, accepted)
            output.write(f"Accepted for this review. Trust will be saved when all required answers are complete. "
                         f"Withdraw: devcapsule home trust withdraw {decision.name}\n")
        else:
            output.write(f"Not accepted. Accept later: {decision.command}\n")
            raise DecisionPending(render_pending([decision], root))
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
            raise DecisionPending(render_pending([decision], root))
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
            raise DecisionPending(render_pending([decision], root))


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
