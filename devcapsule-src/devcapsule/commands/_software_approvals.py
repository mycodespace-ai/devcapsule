"""The launch-time offer of software approvals, and the prompt it shares with bulk authorization.

``project run`` asks before anything else whether the pending decisions are
software approvals only (``devcapsule.configuration.approvals``). If they
are, the list is shown and one key approves it, the answers are written to
the checkout record and the resolution is regenerated, and the launch goes
on. Any other key, or no terminal, ends the launch with the command that
approves later and the guide's address. Nothing is written on a refusal.
"""

from __future__ import annotations

import math
import shlex
import sys
import termios
import tomllib
import tty
from pathlib import Path
from typing import Any

from devcapsule import version_sets
from devcapsule.compat import CliError
from devcapsule.configuration.approvals import (
    SoftwareApproval,
    pending_software_approvals,
    render_software_approvals,
)
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.operations import CheckoutRecord, resolve_checkout
from devcapsule.configuration.storage import (
    checkout_record_paths,
    find_checkout_record,
    interrupted_activation,
    manifest_for,
)

SOFTWARE_APPROVALS_GUIDE_URL = "https://devcapsule.mycodespace.ai/docs/current/configuration/software-approvals/"


def approve_command(root: Path, names: tuple[str, ...] = ()) -> str:
    """The command that records the approvals outside the launch."""

    return shlex.join(
        ["devcapsule", "project", "--path", str(root), "config", "approve", *(names or ["--all"])]
    )


def previous_versions(root: Path) -> dict[str, str]:
    """The component versions of the last successful launch, from the newest known-good record.

    Best effort: a missing or unreadable record means no earlier version is
    shown, never a refusal.
    """

    newest: tuple[float, dict[str, str]] | None = None
    try:
        directory = version_sets.state_directory(root) / "known-good"
        candidates = list(directory.glob("*.toml"))
    except (OSError, RuntimeError):
        return {}
    for path in candidates:
        try:
            record = tomllib.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record.get("lock"), str):
                continue
            lock = tomllib.loads(record["lock"])
            moment = float(record["last-success"])
        except (OSError, KeyError, TypeError, ValueError, OverflowError):
            continue
        components = lock.get("components", {})
        if not math.isfinite(moment) or not isinstance(components, dict):
            continue
        if newest is None or moment > newest[0]:
            newest = (moment, {
                component_id: metadata["version"]
                for component_id, metadata in components.items()
                if isinstance(metadata, dict) and isinstance(metadata.get("version"), str)
            })
    return newest[1] if newest is not None else {}


def pending_for(root: Path, manifest: dict[str, Any]) -> tuple[SoftwareApproval, ...] | None:
    """The approvals pending on a resolved checkout; () with none, None when other decisions pend."""

    input_path, _output_path = checkout_record_paths(manifest, root)
    if not input_path.is_file():
        return ()  # Not yet resolved: the launch reports what is missing.
    # Both lock_for and load_checkout can recover an activation by writing
    # the resolution. Inspection and refusal must leave these files alone.
    if interrupted_activation(input_path):
        command = shlex.join(["devcapsule", "project", "--path", str(root), "run"])
        raise ProjectConfigurationError(
            f"Interrupted activation; finish recovery before reviewing software approvals: {command}"
        )
    from devcapsule.configuration.derivation import load_state
    state = load_state(root, manifest)
    lock, checkout = state.composed_lock(), state.checkout
    # The old offer inspected authorizations only. An IDE, value or input
    # question must join run's staged review before an approval is saved.
    if any(decision.kind in {"ide", "env", "value", "secret"}
           for decision in state.listing(check_display=False).decisions):
        return None
    return pending_software_approvals(manifest, lock, checkout, previous_versions=previous_versions(root),
                                      trust=state.home)


def approve(root: Path, manifest: dict[str, Any], approvals: tuple[SoftwareApproval, ...]) -> None:
    """Record the approvals in the checkout; regenerate the resolution once nothing is pending."""

    record = CheckoutRecord(manifest, root)
    for approval in approvals:
        record.authorize(approval.declaration, True)
    record.write()
    print(f"Approved {len(approvals)} software {'update' if len(approvals) == 1 else 'updates'} for this checkout.")
    try:
        remaining = pending_for(root, manifest)
        if remaining:
            names = ", ".join(approval.name for approval in remaining)
            print(f"Still pending: {names}. The resolution is unchanged; approve the remaining updates to regenerate it.")
            return
        print(resolve_checkout(root).render())
    except (CliError, OSError) as exc:
        command = shlex.join(["devcapsule", "project", "--path", str(root), "run"])
        raise ProjectConfigurationError(
            f"Approvals were saved, but resolution failed: {exc}\n"
            f"Resolve the reported problem, then run: {command}"
        ) from exc


def offer_software_approvals(start: Path) -> bool:
    """Offer the pending software approvals before a launch; return whether the launch may go on.

    True when nothing of the kind is pending, when other decisions pend (the
    launch's own loading reports them), or when the developer approved.
    False when the developer declined or no terminal could ask.
    """

    root, manifest = manifest_for(start)
    if find_checkout_record(manifest, root) is None:
        return True  # A new path has its own decisions; run will register it.
    input_path, _output_path = checkout_record_paths(manifest, root)
    if interrupted_activation(input_path):
        # The ordinary launch loader owns recovery. Do not offer approvals
        # against an unsettled activation, or recover it while inspecting.
        return True
    approvals = pending_for(root, manifest)
    if not approvals:
        return True
    for line in render_software_approvals(approvals):
        print(line)
    later = (
        f"Approve them later with: {approve_command(root)}\n"
        f"Software approvals: {SOFTWARE_APPROVALS_GUIDE_URL}"
    )
    if not sys.stdin.isatty():
        print(f"No terminal to ask; the launch stops here.\n{later}")
        return False
    print("Approve all of them? Press y; any other key cancels: ", end="", flush=True)
    try:
        accepted = confirmation_key() == "y"
    except EOFError:
        accepted = False
    except (OSError, termios.error) as exc:
        print("")
        raise ProjectConfigurationError(f"Cannot read the approval key: {exc}") from exc
    print("")
    if not accepted:
        print(f"Not approved; nothing written.\n{later}")
        return False
    approve(root, manifest, approvals)
    return True


def confirmation_key() -> str:
    """Read one raw keypress without echo or a newline.

    A single keypress, so a stray Enter in a paste cannot accept; callers
    check for a terminal first, so stdin is a tty here.
    """

    descriptor = sys.stdin.fileno()
    saved = termios.tcgetattr(descriptor)
    try:
        tty.setraw(descriptor)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, saved)
