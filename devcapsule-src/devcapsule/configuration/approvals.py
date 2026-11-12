"""Software approvals: new versions of vendor software the developer approved before.

A vendor download is consented to per pinned version (the acquisition
consent of ``authorization.py``), so a lock change that brings a new version
of an agent the developer already approved asks again, once per component.
Typically that lock change arrives with a sync of the project from its
remote, and the developer has nothing new to decide: the vendor and its terms
are those of the earlier consent. The owner's direction of 2026-10-22: when
the only pending decisions are of that kind, ``project run`` offers them as
one list to approve with one answer, and ``project config approve`` records
the same approvals from the command line.

What qualifies is strict. Every pending decision must be an acquisition
consent whose recorded answer is yes and whose recommendation changed; the
component must be in the lock under the contract its code declares, so the
vendor and the terms URL are the earlier consent's. A missing consent, a
denial, a host-access decision or a base decision in the list means the
list is not a software approval: those are decided one by one, as before.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from devcapsule.components.catalog import COMPONENTS

from .authorization import (
    AuthorizationDeclaration,
    authorization_declarations,
    review_authorizations,
)
from .file_formats import ProjectConfigurationError


@dataclass(frozen=True)
class SoftwareApproval:
    """One vendor download to approve again, with what changed."""

    name: str
    """The authorization name, ``claude-code-download`` for instance."""
    component: str
    """The component id in the lock."""
    display_name: str
    vendor: str
    version: str
    """The version the lock pins now."""
    previous_version: str | None
    """The version last launched, when a known-good record says; None otherwise."""
    terms_url: str
    declaration: AuthorizationDeclaration

    @property
    def change(self) -> str:
        if self.previous_version and self.previous_version != self.version:
            return f"{self.previous_version} to {self.version}"
        return self.version


def pending_software_approvals(
    manifest: Mapping[str, Any],
    lock: Mapping[str, Any],
    checkout: Mapping[str, Any],
    *,
    previous_versions: Mapping[str, str] | None = None,
    trust: Mapping[str, Any] | None = None,
) -> tuple[SoftwareApproval, ...] | None:
    """The approvals a launch may ask for in one question.

    Returns an empty tuple when nothing is pending, the approvals when every
    pending decision is one, and None when any pending decision is of another
    kind, in which case the review's own refusal applies.
    """

    from .trust import HomeTrust
    reviews = review_authorizations(manifest, lock, checkout, HomeTrust.read(trust or {}))
    pending = [item for item in reviews if item.problem is not None]
    if not pending:
        return ()
    declarations = authorization_declarations(manifest, lock)
    # review_authorizations has already validated this table.
    records = checkout.get("authorization", {})
    components = lock.get("components", {})
    approvals: list[SoftwareApproval] = []
    for item in pending:
        declaration = declarations.get(item.name)
        if declaration is None or declaration.kind != "acquisition" or item.status != "stale":
            return None
        record = records.get(item.name)
        if not isinstance(record, dict) or record.get("value") is not True:
            return None
        component_id = _component_for(item.name)
        metadata = components.get(component_id) if isinstance(components, dict) else None
        if component_id is None or not isinstance(metadata, dict):
            return None
        contract = COMPONENTS[component_id].acquisition()
        assert contract is not None  # _component_for found it by this contract
        approvals.append(SoftwareApproval(
            name=item.name,
            component=component_id,
            display_name=contract.display_name,
            vendor=contract.vendor,
            version=str(metadata.get("version", "")),
            previous_version=(previous_versions or {}).get(component_id),
            terms_url=contract.terms_url,
            declaration=declaration,
        ))
    return tuple(sorted(approvals, key=lambda approval: approval.display_name))


def _component_for(authorization: str) -> str | None:
    for component_id, definition in COMPONENTS.items():
        contract = definition.acquisition()
        if contract is not None and contract.authorization == authorization:
            return component_id
    return None


def render_software_approvals(approvals: tuple[SoftwareApproval, ...]) -> list[str]:
    """The list as the developer reads it before answering."""

    lines = [
        "The project's lock brings new versions of software you approved before; "
        "the vendors and their terms are unchanged:"
    ]
    for approval in approvals:
        lines.append(
            f"- {approval.display_name} {approval.change}, downloaded from {approval.vendor} "
            f"under {approval.terms_url} ({approval.name})"
        )
    return lines


def select_software_approvals(
    approvals: tuple[SoftwareApproval, ...], names: tuple[str, ...]
) -> tuple[SoftwareApproval, ...]:
    """The approvals the given authorization names select; every name must be pending."""

    by_name = {approval.name: approval for approval in approvals}
    unknown = [name for name in names if name not in by_name]
    if unknown:
        pending = ", ".join(sorted(by_name)) or "none"
        raise ProjectConfigurationError(
            f"No software approval is pending for {', '.join(unknown)}; pending: {pending}."
        )
    return tuple(by_name[name] for name in dict.fromkeys(names))
