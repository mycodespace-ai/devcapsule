# Workstream Current Status: Project Management

Mnemonic: `project-management`

Start date: 2026-08-09

State: active 2026-11-12; permanent coordination; resumed at owner direction

Definition read: WORKFLOW.md@89de30622697, WORKFLOW-LOCAL.md@d92bdcbb0a01

Branch association: `ws-project-management/coordination`

Integration target: `main`

Delivery method: pull request for deliverables; records published on coordination

Requirements: `R-PRODUCT-003`, `R-PRODUCT-005`, `R-PRODUCT-006`

## Goal

Own project-wide priorities, sequencing, dependencies and lifecycle decisions.
This reserved workstream remains open for the lifetime of multiple-stream mode.

## Current State

### Resumed 2026-11-12

The owner requested project management first. In the console answer at
`2026-11-12T02:20:44+00:00`, the owner selected `preserve-and-switch`,
authorizing stashing all local edits, including website configuration, and
switching this checkout. The checkout now selects this workstream. The
preservation facts are below. No product scope was chosen by this switch.

Fetched `origin` and read the live workstream list, this workstream's handoff,
all intake and both ideas in the pile. No open bug on fetched `origin/main`
is owned by `project-management`. The workflow declaration still says
`0.2.14.dev0` while the root definition says `0.3.2.dev0`; this known mismatch
is retained. No configuration or definition refresh is part of this task.

Synchronization was required because the definition and local workflow changed.
Fast-forwarded to `origin/ws-project-management/coordination` at `31ca4474`,
then merged fetched `origin/main` (`bb824693`) at `d2c4f51d`. The workstream-list
conflict retained this workstream's own row and mainline's other rows; the index
conflict retained both sets of bug links. Product source equals fetched mainline.
Read the new pile-of-ideas rules and the changed local validation, test,
release-evidence, GitHub and review-partner rules. No new implementation starts.

### Delivery and scheduling reconciled

Took five waiting messages and committed their receipt at `68e514c0`.
Three October 31 release notices are acknowledged in `intake-dispositions.md`:

- **0.3.0 is delivered.** Fetched tag `v0.3.0` identifies `475427da`.
  The [release record](../../releases/v0.3.0/README.md),
  [final verification](../../releases/v0.3.0/final-verification.json) and
  [website verification](../../releases/v0.3.0/website-verification.json)
  retain the final download and owner-confirmed production promotion evidence.
  This resumption checks the tag and repository records; it does not repeat
  download, browser or provider acceptance tests.
- **C17 and the nine September 28 documentation proposals moved to 0.3.1
  planning by the owner's October 31 decision.** They do not gate 0.3.0.
  The nine proposals still need individual decisions. C17 retains
  `workflow-improvements`; the October 25 documentation order retains
  `maintenance`. The [0.3.1 scope at the cut](../../releases/v0.3.1/README.md)
  subsequently leaves these outside that release unless the owner pulls them in.
  A scheduling acknowledgement is not approval of their implementation.
- **0.3.1 is already in its candidate cycle.** Fetched `v0.3.1-rc2` identifies
  `be0140ca`. The release record and maintenance's live publication describe
  candidate 2 and the remaining release work. The older preparation and
  pending-PR statements in the historical handoff must not restart 0.3.0 work.

There are 17 undecided intake items after these acknowledgements. They include
all prior unresolved requests, the test-session timing design request and the
request to open `test-improvements`. Receipt alone assigns no priority or pair.
The [test-improvements order](../../work-orders/2026-11-08-test-improvements.md)
is on mainline, but no workstream is registered for it yet. Maintenance also has
newer overlapping test work on `ws-maintenance/host-inputs-at-source`; read its
live state before defining the new workstream's boundary. No source work or
other workstream's records are edited here.

The two November 10 ideas, removing dogfood machinery from the adopter package
and a tiling desktop, remain in `engineering-docs/pile-of-ideas/`. They need
product and scope choices; neither is silently adopted or assigned a release.

## Planned Next Step

With the owner, select the next project-management slice from the reconciled
queue. The concrete new request is registration and allocation of
`test-improvements`: first reconcile its work order with maintenance's newer
host-input rewrite, then define the boundary and confirm the pair and first
slice. Keep the timing-design request, the nine documentation decisions, C17,
the other intake and the two ideas pending until addressed. This resumption
does not authorize a switch to an implementing workstream.

Done for that next slice means a recorded owner choice, a bounded outcome and
acceptance evidence, and the appropriate registration or intake acknowledgement.
Verification uses current mainline and live recipient state; no test reruns are
needed merely to compare planning records.

## Validation And Checkout State

The required build gate was attempted on the synchronized source with
`PYTEST_ADDOPTS="--basetemp=/var/tmp/pm-resume-20261112/pytest --maxfail=1"`.
After creating the scratch parent directory, version and syntax checks passed,
mypy passed over 333 files, and test conventions reported zero breaches.
The unit phase stopped at
`tests/configuration/test_contract.py::test_second_checkout_cannot_inherit_the_first_checkouts_authority`:
32 passed, 1 failed, 66 deselected. Launch preparation returned 0 rather than
3 and reported `home trust (devcapsule-base)`. This matches the existing
[maintenance-owned mounted-settings bug](../../bugs/devcapsule/2026-11-10-unit-tests-read-the-capsules-mounted-launcher-settings.md).
The full gate is not green; later build phases did not run. The log is local
scratch at `.git/pm-resume-20261112-build.log`. No unrelated fix is made here.
All 37 local links in this handoff resolve, the prior handoff is byte-identical
to its preserved record, and whitespace checks pass. The final mailbox take
found no waiting messages. Release the setup claim when this checkpoint is
published; this checkout remains selected on project management.

The owner's saved edits remain outside project-management commits:

- Parent stash `b7923b4de1078e2cecbc2949c62948f6129ca997`, named
  `pm-switch-2026-11-12-preserve-parent`, holds the IDE edit from
  `release-0.3.1` at `c4bd458b`.
- Website stash `19f0f4e9b0204a7a346a8b82fe978d361b682c32`, named
  `pm-switch-2026-11-12-preserve-website`, holds its tracked and untracked edits
  from branch `website-retro-blueprint-styling-and-dual-nav` at `5560f90e`.
  Its original parent gitlink was `91309a7a`.
  The stash was consumed during concurrent website work; its original object
  was stored again as the same named stash without changing the website files.
- Local recovery metadata is `.git/pm-switch-2026-11-12.json`. Do not apply
  either stash to this workstream. The website returned to its styling branch
  with new edits during resumption; those concurrent edits remain untouched,
  and its gitlink is excluded from this checkpoint.

## Open Threads

- Awaiting the owner: the next project-management slice and the pair/first-slice
  choices for the requested `test-improvements` workstream; no implementation
  starts from this resumption alone.
- Weighed and unresolved: the nine documentation choices, C17 placement,
  test-session timing design, all remaining intake and the two ideas.
  Keep the newer 0.3.1 cut exclusions when considering older scheduling mail.
- The full gate remains blocked by the documented maintenance test-fixture bug.
  Recheck maintenance's live state before treating its overlapping rewrite as delivered.
- Deliberately not preserved: no transcript, new experiment, reminder service,
  container or deployment. The prior handoff is preserved verbatim below.

## Workstream Document Index

- [Prior coordination status, preserved November 12](2026-11-12-record-prior-coordination-status.md): verbatim pre-resumption status and historical open threads; use this file's current state for routing.


- [CI path gating and advisory diff coverage](../../work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md): assigned to maintenance for 0.3.0; owner decisions 1B and 2B, serial execution and advisory coverage.

- [Scope rechecked at RC8, amended October 29](2026-10-27-decision-release-0-3-0-scope-at-rc8.md): current release scope, including the October 25 documentation work deferred to 0.3.1.

- [Release 0.3.0: scope, driver and cut](2026-10-18-decision-release-0-3-0-scope-and-cut.md): the owner's decision of 2026-10-18; open when a scope question returns.
- [Release 0.3.0 work order](../../work-orders/2026-10-18-release-0-3-0.md): what the driver delivers and the gates before the final tag.
- [Project operations for 0.3.0; ecosystem bootstrap for 0.9](2026-10-11-decision-project-operations-and-bootstrap.md): accepted owner decision, default PATH and exceptional project shell direction, and continuing agent responsibility for project instructions.

- [Persistent session diagnostics work order](../../work-orders/2026-10-08-persistent-session-diagnostics.md): C21 assigned to maintenance on 2026-10-11, targeted ready for 0.3.0; bounded scope and acceptance remain.

- [Handoff before intake reconciliation](2026-10-09-record-before-intake-reconciliation.md): verbatim historical status; read for prior decisions and open-thread context.
- [Prior release proposal](2026-10-09-record-prior-release-proposal.md): verbatim 0.2.16-era proposal before the 0.3.0 reconciliation; historical recommendations, not current scope.

- [Work order: the website from the visitor's chair](../../work-orders/2026-09-28-website-visitor-experience.md) and [work order: visitor content and producer migration](../../work-orders/2026-09-28-visitor-content-and-producer-migration.md): issued 2026-09-28.
- [The content–website contract, version 1](../../specifications/product/content-website-contract.md): accepted 2026-09-28, promoted to the specifications on 2026-09-30; the website's `CONTRACT.md` is the authoritative text.
- [Design issue: the documentation is current when a release drops](2026-09-28-design-docs-current-at-release.md): historical design discussion; the contract and work orders record the subsequent decisions.
- [0.3.0 planning proposal](2026-09-27-0216-release-planning.md): current 0.3.0 commitments and remaining release decisions; historical filename retained.
- [Design issue: consent that means something](2026-10-01-design-consent-and-vendor-trust.md): historical problem statement; consent decisions are D-0011 through D-0013 and assigned for 0.3.0.
- [0.2.15 environment discovery work order](../../work-orders/2026-09-27-project-environment-discovery.md): approved xtras/info/agent-defaults scope, guard deferral and acceptance checks.

- [0.2.14 release overview](../../releases/v0.2.14/README.md): maintained release checklist and evidence.
- [0.2.14 bug triage](../../releases/v0.2.14/bugs.md): release dispositions and next actions; canonical bug records remain linked.

- [Prior coordination status](2026-09-22-record-prior-coordination-status.md): full historical handoff, decisions, open-thread context and external-state claims; read when reconciling a specific prior topic.
- [Intake decisions](intake-dispositions.md): append-only outcomes; `intake/` contains eight original undecided items plus the new testing-policy reconciliation, after 29 acknowledgements and the Stage 7 closure.

- [Diagnostic print-command and run-image retirement](2026-09-21-design-editable-project-launch.md): accepted simplified contract and maintenance implementation scope.
- [Design issue: V1 completeness and the WOW experience](2026-09-19-v1-wow-functionality-areas.md)
- [Why try DevCapsule? — promoted to the project README](../../../README.md)
- [Portfolio checkpoint 2026-08-15](2026-08-15-portfolio-checkpoint.md)
- [Portfolio checkpoint 2026-08-16](2026-08-16-portfolio-checkpoint.md)
- [V1 readiness assessment 2026-08-16](2026-08-16-v1-readiness-assessment.md)
- [V1 scope ledger](v1-scope-ledger.md)
- [Competitive comparison: promoted research
  (refreshed 2026-09-12)](../../design-notes/devcapsule/competitive-comparison.md)
- [Display transport options and clipboard policy
  2026-08-19](2026-08-19-display-transport-options.md)
- [The workflow versus Jira and GitHub Issues
  2026-08-19](2026-08-19-workflow-versus-issue-trackers.md)
- [Coordination backlog](coordination-backlog.md)
