---
id: D-0010
title: Developer-Owned Component Version Sets And Recovery
status: accepted
date-proposed: 2026-09-21
date-decided: 2026-09-21
decided-by: Costin Cozianu
requirements: [R-UPGRADE-001, R-COMPAT-001, R-PRODUCT-002]
supersedes: portions of D-0001 and D-0008 identified below
superseded-by:
---

# D-0010: Developer-Owned Component Version Sets And Recovery

## Context

This records the owner's settled direction in the
[component-upgrades work order](../../work-orders/2026-09-21-component-upgrades.md),
not a new adoption by the implementing agent. Vendor update notices need a
DevCapsule path that lets a developer try an upgrade without changing everyone
else's environment, and return to software that worked locally.

## Options Considered

1. Update the committed platform lock for every experiment. This is easy to
   share, but makes personal exploration a project recommendation prematurely.
2. Keep a floating component override over the latest project lock. Small local
   records, but an upstream change silently changes the rest of the selected set.
3. Save a complete developer-owned version set. More explicit local state and
   retention, but selection and recovery preserve the exact environment inputs.

## Decision

The owner chose complete **version sets** in developer-owned checkout
configuration. A version set names its platform, immutable base, component
versions and artifact identities, and materialization recipe. The project's
committed lock remains its recommendation. Local selection persists until an
explicit choice to follow that recommendation again; divergence is disclosed.
Successful local use may support an optional, reviewable upstream proposal.
Preparing that proposal does not commit, open a PR, publish or merge it.

Components declare optional distribution channels. Omission requires a
contributor-facing explanation. Channels disclose upstream availability and
status independently of DevCapsule's accumulated validation and local success.
An explicitly unvalidated choice is permitted, while platform, structural
compatibility, declared dependencies and acquisition integrity remain mandatory.
No generic orchestration special-cases the first consumer, Codex.

Preparation does not replace a usable selection until it succeeds and does not
change running sessions. A zero-exit ordinary launch records the exact inputs
captured before it started. Failed or merely prepared selections are never
known-good. Recovery retains exact software resources and applies the selected
software with **current** host decisions, state and credential bindings; it does
not restore old permissions or personal-state snapshots. Vendor state migrations
cannot be promised reversible by downgrading software.

This refines D-0001's lock-update journey: a personal component upgrade writes
checkout configuration, not the committed recommendation. It refines D-0008's
snapshot/restore consequences: operational software recovery uses complete
pre-launch version sets, while existing configuration snapshots remain readable.
D-0008's zero-exit trigger and D-0007's accumulated validation model stand.
Accepted Decision and Rationale text in earlier records is preserved.

### Owner refinement: critical upgrade decisions during launch

On 2026-09-21, after reviewing the first implementation, the owner directed that
security and end-of-support upgrades use DevCapsule's interactive prompting
apparatus during launch, so the developer need not navigate a command sequence
after a warning. The launcher offers review/upgrade, remembered later/keep, and
stop; an approved upgrade is prepared and used in that launch. Validation gaps
and new acquisition consent remain explicit, with current host boundaries intact.

The initial implementation consumes explicit notices from component channels,
with daily best-effort interactive discovery and cached offline fallback.
Noninteractive launch reports cached notices without prompting, checking online
or selecting software. Absence of a notice is not a security assurance. An
independent vulnerability feed is outside this refinement; npm vendor deprecation
is the first real support signal. This paragraph records the later refinement,
not an implication that the original command-driven implementation included it.

### Owner refinement: runtime configuration introspection

On 2026-09-21 the owner reported `versions show` failing inside dogfood because
it sought the launcher-owned checkout record in the container's home. The owner
approved explicit runtime/launcher adaptation and a read-only configuration-tree
mount, with a captured running version set distinguished from the current
next-launch selection. Runtime inspection must not reinterpret host paths or
perform recovery writes; configuration changes remain launcher operations.
The existing project record-directory layout, including sibling checkout records
where present, is mounted read-only and documented. This implements introspection,
not an in-capsule broker that changes the host's selection.

## Rationale

Personal experimentation should be useful before the developer decides to
contribute it. A complete selection prevents accidental mixing with upstream
changes. Distinguishing availability, validation and local success permits
informed experiments without presenting an untested combination as proven.
Software recovery is useful only if the next normal launch consumes it and
cannot resurrect permissions the developer revoked.

### Owner refinement, 2026-10-01: the upgrade prompt is a scheduling choice

The owner ruled that the launch-time prompt of the refinement above stops
asking the developer to authorize the newer version. The question is when
to move: upgrade now, remind me later, or keep what is installed. If
DevCapsule has not validated the newer version together with the rest of
the selected set, the prompt says so once, plainly, before the choice;
the developer may still choose now. Vendor trust is not asked here at
all; it is given once per configuration home under [D-0011](d-0011-vendor-trust-once-per-configuration-home.md). The "changed
acquisition consent" clause of the 2026-09-21 refinement is superseded
accordingly. Targeted at 0.2.16 with the consent slice in
`component-upgrades`.

## Consequences

The implementation needs a channel contract, explicit preparation/activation,
retained resources, bounded remembered reminders, an operational rollback path,
and tests across the production CLI/configuration/materialization boundary.
Serialized configuration access remains the existing owner precondition.
Launcher self-update, base/IDE upgrade delivery and personal-state migration
are outside this work order.
