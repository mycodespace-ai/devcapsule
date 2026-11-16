# Owner Decision: Upgrades Gate The First Release After 0.3.1

To: component-upgrades, maintenance
From: project-management
Date: 2026-11-16

The owner has decided this scope; it is not a proposal. Component-upgrades owns
the upgrade work and must reconcile the current implementation and propose
bounded closure criteria and acceptance evidence before implementation.
Maintenance must retain the obligation for the successor release's driver.
This does not request a workstream switch or an upgrade change to 0.3.1.

The canonical decision is on ws-project-management/coordination at
engineering-docs/wip/2026-08-09-project-management/2026-11-16-decision-upgrades-next-release.md.
It and the release-checklist change reach main through ordinary integration;
the complete decision below carries the obligation meanwhile. Relative links
in the copied text resolve from the canonical decision's location.

# Upgrades In The First Release After 0.3.1

Date: 2026-11-16
Status: accepted
Decided by: product owner, in the project-management intake review

## Decision

The upgrade experience is required scope for the first release after 0.3.1,
whether that release is numbered 0.3.2 or 0.4.0. Its eventual number does not
change the commitment. This adds no upgrade gate to 0.3.1.

That successor must not ship without the agreed upgrade experience and its
acceptance evidence, unless the product owner explicitly changes this decision.
Version selection, a new release branch, or a scope-at-cut inventory must not
silently drop the obligation. Record any amendment as a new dated decision.

Component-upgrades owns the upgrade work; project-management owns scope,
sequencing and checking that the release driver carries this commitment.
Maintenance receives the obligation as the current release driver and must
preserve it in the handoff to the successor's driver.

## Rationale

The owner's concrete concern is embedded Codex and Antigravity prompting for
upgrades during use, while the suggested in-capsule update may fail or fail to
survive a later DevCapsule launch. Merely refreshing pins at release time does
not settle that user experience. These are owner-reported symptoms, not new
observations from a reproduction in this session. Distinguish a restart of a
retained container from recreation when establishing the actual behavior.

The earlier September 3 intake committed the broader upgrade experience to V1.
The owner now chooses the immediate successor to 0.3.1 instead of leaving its
release placement open. Waiting until an unspecified V1 release was the prior
alternative; it leaves this recurring user frustration unresolved.

## Scope And Next Task

Reconcile the original intake's three strands (helpful upgrade messages,
obsolescence warnings, and the process for advancing versions and retiring
superseded artifacts) with the integrated R-UPGRADE-001 implementation.
The original intake is retained in Git at 7f81fa92 under
`engineering-docs/wip/2026-08-09-project-management/intake/2026-09-03-component-catalog-upgrade-experience-as-a-v1-feature.md`.

The first scoping task must cover the embedded-agent case: an actionable,
supported upgrade path, clear treatment of vendor self-update prompts, and
persistence of the chosen version across the relevant subsequent launch and
container-recreation paths. Repeated advice to perform an ineffective update
is not an acceptable outcome. Verify existing behavior before choosing an
implementation; this decision chooses neither an auto-update policy nor a
storage mechanism. Component-upgrades must propose bounded closure criteria
and acceptance evidence for owner review before implementation.

Related requirements do not all become gates by association: R-UPGRADE-002's
separate operational-reliability follow-up keeps its recorded priority unless
the owner changes it. Detailed scope questions remain visible and cannot serve
as an implicit deferral of this decision.

## Release Checkpoints

At successor scope selection and before its branch is cut, the release driver
must include this obligation in the release overview, name its implementation
owner and closure criteria, and link this decision. Before final acceptance,
record the delivered behavior and evidence, or an explicit owner amendment.
The [release operator checklist](../../implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md)
carries both checkpoints.

The generic workflow permits decisions and gating priorities but does not
specify a release-relative target or automatic propagation to a future release.
Under topic 3, project-management records this ordinal target and explicit
checkpoints in its existing records and release policy. This is a procedural
gate, not an automated publication check. The reusable gap is sent to
workflow-improvements; no generic definition or version declaration is changed.

## Original Intake

# Intake: The Upgrade Experience Is A V1 Feature

Delivered 2026-09-03 by `component-catalog`, at the product owner's
direction, given during the v0.2.9 validation session: "we need to
flush out upgrade-friendly messages and warning of obsolescence as
well as the project of upgrading. It's an important feature for v1."

## What Is Being Handed Over

Design and ownership of the developer-facing upgrade story, three
strands the owner named:

1. **Upgrade-friendly messages**: when a newer pinned component, base,
   or matrix exists, the tool should say so helpfully — today the only
   voice is a refusal after the fact.
2. **Obsolescence warnings**: a checkout whose lock, base, or
   components have fallen behind should learn it gently and early, not
   discover it as a hard error at the next `--regenerate`.
3. **The project of upgrading**: the process and tooling by which pins
   advance — who verifies, what evidence gates the advance, how
   adopters are moved along, and what happens to superseded artifacts.

## Why It Belongs To `project-management`

The owner's earlier statement of the narrower "component update
mechanism" (2026-08-31, recorded in the `component-catalog` handoff's
open threads) already assigned it to project-wide planning:
advancing pins spans the resolution matrix, the CLI's message surface,
the release process, and every workstream that owns a component. The
broader feature the owner has now named subsumes it and crosses the
same boundaries; `component-catalog` can host the matrix data changes
but cannot own the product surface.

## Evidence

The 2026-09-02/03 v0.2.9 validation stretch is a complete case study,
recorded in the `component-catalog` handoff and bug records:

- A checkout whose lock predated the current matrix failed loudly
  ("unsupported recipe … expects …") with `--regenerate` as the only
  remedy — correct, but the obsolescence was knowable long before the
  refusal.
- The matrix advanced five times in two days (`embedded-4` →
  `embedded-9`), each advance hand-edited; the sustainability of that
  is already a recorded backlog item in the `component-catalog`
  handoff (resolution-matrix cleanup), and the update *process* is the
  missing other half.
- The claude-code pin advance to 2.1.236 (Fable 5.1) worked and the
  owner confirmed it, but it was performed entirely by hand: discover
  the stable version, download, checksum against the vendor manifest,
  edit the pin, re-verify edges provisionally. Every future component
  release implies the same manual round.
- Superseded multi-GB canonical images accumulate with no lifecycle
  (the 2026-09-02 formation-identity bug record) — the disposal half
  of upgrading.
- `init --unverified` (owner-ruled 2026-09-03) now lets a sophisticated
  user run ahead of the matrix with a gentle warning; the upgrade
  story is its complement — moving the matrix itself forward so the
  escape hatch stays rare.

## What Accepting Would Mean

Owning the feature's shape for V1: where upgrade/obsolescence messages
surface (init, run, config list, a dedicated verb), what the pin-advance
process is (evidence gates, provisional edges, who smokes), and how
superseded artifacts age out. The owner has stated it is an important
V1 feature; sequencing against the rest of V1 is the receiving
workstream's judgment, per protocol.
