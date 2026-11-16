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
