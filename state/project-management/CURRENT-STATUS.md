# Workstream Current Status: Project Management

Mnemonic: `project-management`

Start date: 2026-08-09

State: active 2026-11-25; resumed on ws-project-management/coordination; 3 intake items taken and 3 pile-of-ideas items pending triage

Definition read: WORKFLOW.md@781c9e39df58, WORKFLOW-LOCAL.md@94a29cb6eedb

Branch association: `ws-project-management/coordination`

Integration target: `main`

Delivery method: pull request for deliverables; records published on coordination

Requirements: `R-PRODUCT-003`, `R-PRODUCT-005`, `R-PRODUCT-006`

## Goal

Own project-wide priorities, sequencing, dependencies and lifecycle decisions.
This reserved workstream remains open for the lifetime of multiple-stream mode.

## Current State

### Dispatched `gh`, `gcloud`, and version-upgrades sweep to `component-catalog`, 2026-11-25

By owner direction on 2026-11-25, delivered three `release-0.3.1` tasks to `component-catalog` on `upstream/coordination`:
- `2026-11-25-project-management-gh-cli-component.md` (`4b79f034b446`) — implement `gh` (GitHub CLI) as an available component, superseding the November 17 manual-only deferral.
- `2026-11-25-project-management-gcloud-cli-component.md` (`f8937ecd8833`) — implement `gcloud` (Google Cloud CLI) as an available component (separate from unselected Gemini CLI).
- `2026-11-25-project-management-component-version-upgrades-sweep.md` (`3967e9e0264c`) — check all existing catalog components for version upgrades and deliver updated pins/outcome table for `release-0.3.1`.

Three taken intake items (`2026-11-17-presentations-launcher-base-requirements.md`, `2026-11-18-component-catalog-localize-ide-additions.md`, `2026-11-24-maintenance-optimize-no-change-builds.md`) and three `pile-of-ideas/` items await triage/disposition.

### Intake review complete; switch to rc3, 2026-11-17

The owner answered the final two questions at 2026-11-17T01:17:38Z: finish the
existing website documentation-check fix after 0.3.1, and retain chat progress
updates without building product agent-supervision features. Delivered those
outcomes to website and workflow-improvements; the backlog and disposition log
record them. Intake and mailbox are empty. All 18 original items are decided,
including the upgrade commitment decided before the 17-question page.

The owner now asks to cut 0.3.1 rc3 and tally remaining release work. Pause this
workstream deliberately and switch the clean checkout to maintenance's
release-0.3.1 branch. The current canonical release tip is a464088d; SSH proxy
is merged, presentations PR #43 is still open, and main is dac6b9d4. These are
freshly fetched/read facts, not a claim that candidate prerequisites are met.
No project-management questionnaire remains pending. The two question/answer
pairs may be removed from capsule state after this outcome commit is durable.


### Fifteen decisions recorded; two rewritten questions, 2026-11-17

The owner's console response of 2026-11-17T00:48:36Z decides 15 items. Their
scope, routing, sequencing and note refinements are recorded in the
[coordination backlog](coordination-backlog.md), November 17 section. Removed
those 15 intake files in the same commit as their disposition entries. Original
intake text remains at 9443bdc6. Only the website documentation check and agent
progress-monitoring questions remain pending; they are rewritten in plain English.

The owner added two obligations: review every component before every release,
with upgraded/no-update-needed/open-next-release-bug outcomes; and create a
sample-project release check with real end-to-end runs, project updates and
videos/presentations. The release guide carries the review rule and the pending
sample-check obligation. The [sample-project work order](../../work-orders/2026-11-17-sample-project-release-gate.md)
assigns implementation/design work; it does not claim the check already exists
or select its first enforcing release. Maintenance received both obligations.

The init/config item is assigned to component-upgrades with component-catalog
support, with further owner discussion before behavior changes. The owner chose
manual gh documentation, and its Miniconda consent explanation must describe
that installation route, not assert that gh has no other installation methods.

Future workstreams are scheduled, not registered early: compatibility and
launcher-recovery after 0.3.1; capsule-storage after the successor upgrade slice;
test-improvements after the successor release. The selected integration-test
comparison waits for test-improvements; timing-history design follows its
reconciliation. The adopter pilot/article plan waits until after the successor
upgrade release. No invitations or publication are authorized by that plan.

Sent decisions to component-upgrades (6dce079afb48), component-catalog
(29bb5a51c034), maintenance (b0c544148b62), website (3ea0dae53824), user-docs
(7ee926005bd2), sample-projects (e86fdba50f8c), and presentations (9d2e979ee557).
Recipients own acknowledgement and implementation at the recorded positions.
This checkout remains on project-management; no product implementation starts.

Follow-up questionnaire: `2026-11-17-two-intake-questions-plain-english`, in
capsule state only. It contains original items 10 and 14; all other choices
are already acted on as coordination decisions. Keep the original 17-item page
and its answer while these two outcomes remain unresolved. The new page is the
one to present; do not ask the owner to repeat the other 15 choices. Tokened
links and raw questionnaire/answer files remain outside Git.

Workflow status reports zero commits behind main and no definition change;
no synchronization is needed. The owner-authorized document-only validation
exception remains in force. The generic future-release targeting gap remains
with workflow-improvements; where a deferred-update bug's exact next version
is unknown, preserve the ordinal obligation until its target can be bound.


### Seventeen-item decision questionnaire, 2026-11-16

The owner replaced the sequential intake presentation with one console
questionnaire covering all 17 remaining items, with 1–5 options each and
free-text decisions or discussion. Reviewed every intake and relevant current
contracts/source; the questionnaire uses 2–3 options per item and distinguishes
old observations from current evidence. The existing successor upgrade gate
stands; additional release gates are options awaiting the owner, not decisions.

Questionnaire ID: `2026-11-16-project-management-17-intake-decisions`.
The document, drafting inputs and any answers live only in capsule state under
`$XDG_STATE_HOME/devcapsule/`; no tokened link or questionnaire content is in Git.
The console supports per-item notes with no selected option and partial answers.
All 17 items remain in intake until their individual outcomes are recorded.

On reply, read the corresponding answer document and prefer newer chat rulings
for the same item. Record and route unambiguous choices or free-text decisions
without reconfirmation. Keep unanswered items, requests for discussion and
conflicts pending; continue only those. A decision to commission design settles
routing/scope, not the later product-design choices. Do not delete the decision
or answer until all outcomes are recorded. If useful, issue a follow-up page
containing only unresolved questions; never silently discard a submitted answer.


### Upgrade release commitment, 2026-11-16

The owner decided the first intake item: upgrades are required in the first
release after 0.3.1, whether 0.3.2 or 0.4.0. The
[accepted scope decision](2026-11-16-decision-upgrades-next-release.md) and
[coordination backlog](coordination-backlog.md) retain the obligation, owner,
release checkpoints and next scoping task. This does not gate 0.3.1.
The embedded Codex/Antigravity update prompts and persistence across later
launch/recreation are the owner's motivating case; no reproduction is claimed.

Delivered the acknowledged intake to component-upgrades and maintenance at
coordination b07446bce231 for successor handoff. The generic gap was delivered
to workflow-improvements at coordination 43fbafb0a8fb. Seventeen intake items remain;
continue reviewing one at a time. Do not advance to the second without the human.

Workflow topic 3 judgment: the definition permits formal scope decisions and
gates but has no release-relative target propagation procedure. Use an explicit
ordinal target, the existing backlog and release checklist checkpoints; send
the generic gap to workflow-improvements. No automatic enforcement is claimed,
and no generic definition is edited. This branch is zero commits behind main;
no synchronization is needed. Planning validation remains document-only under
the owner's standing exception.


### Resumption after SSH proxy delivery, 2026-11-16

The owner selected project-management after SSH proxy PR #47 merged into
release-0.3.1 at `a464088d`. The SSH proxy workstream is paused and published;
its local merge-handoff checkpoint is `e65ef398`. Its remote branches were deleted
by GitHub. Its local branches and retained evidence remain until main propagation.
No deleted remote branch was recreated for the records-only pause checkpoint.

This checkout now selects `ws-project-management/coordination`, from a clean tree.
Fetched canonical upstream: this branch is zero commits behind main and its
workflow files match main, so no synchronization is needed. The live workstream
list, local status, intake and three ideas in the pile were reviewed. No waiting
mail was found and no open bug record is owned by project-management.

Verified hosted delivery: presentations PR #43 is still open against release-0.3.1,
with Pair Review complete according to its live status. SSH proxy PR #47 is merged
into that release. Its work is not yet in remote main. Maintenance owns release-to-main
propagation, including preservation of main's development version and main-only
documents, handed over in `2026-11-16-github-auth-release-delivery.md`.

The older presentation-registration and no-release-target statements below are
historical. The 18 undecided intake items remain pending; this selection does not
choose another implementation slice or dispose of those requests. Record-only
validation follows the owner's existing planning exception: whitespace and changed
record review, no repeated product gate or environment provisioning.

### Presentations creation and handoff, 2026-11-16

The owner requested an existing presentations workstream, or creation if absent.
Checked canonical mainline, live publications, open/archive directories and remote branches.
There is no standalone presentations workstream. The merged viewer branch belonged to capsule-webconsole.
Create `presentations` on `ws-presentations/authoring`, from current canonical main `dac6b9d4`.
The use case is its goal; creation starts no design or implementation work.
Delivered `2026-11-16-project-management-presentation-authoring.md` through coordination mail, with the use case and original source revisions.
Dispositioned the two presentation messages as delivered onward; 18 intake items remain.
The source messages remain in Git at `cac3861e`, linked from the use-case document.
Pause project-management to register the new workstream on its own branch under WORKFLOW.md 7.5.
No unrelated state is carried to that branch. Records checked for whitespace and link targets; no product code changed.
The owner-authorized planning validation rule remains in force.


### Presentation excellence selected, 2026-11-16

The owner selected presentation excellence as the next project-management slice.
This resolves the previous next-slice decision to `presentations`; the other queue items remain pending.
The owner explicitly permits project-management work despite local unit-test failures.
The owner reports that those tests pass on GitHub's agents; this session did not independently verify that report.
Use record review and relevant document checks for this planning work. Do not rerun the full gate for each planning checkpoint.
The known local Docker-group failure remains recorded, but does not block this workstream's planning.

The owner clarified the use case and explicitly deferred design work.
In another DevCapsule/codebase, the engineer asks the agent to run E2E with recording and presentation.
The scenario comes from an existing Markdown file or inline plain English.
The agent executes the scenario, records it, creates the presentation and returns its web-console link.
The [use-case definition](2026-11-16-design-presentation-excellence.md) now states that flow without architecture or packaging design.
Its historical filename is retained so existing references keep resolving.

The owner reports this recording capability already worked in another project after pointing its agent at this repository.
The existing viewer has human acceptance, including Florin's test and enthusiastic response.
The gap is making the proven instructions and supporting Python/Playwright code available to adopter agents.
No new process, viewer-quality exercise or external-project selection is needed to define the use case.
The earlier proposal to do packaging/interface design here is superseded by the owner's explicit direction.

Both audiences remain in scope. Implementation design, assignment and release placement are later work.
The two presentation intake items remain pending until the agreed work is routed.


### Mainline synchronized again, 2026-11-16

The owner requested the new mainline commit before selecting the next slice.
Fetched `dac6b9d4`, PR #42's merge of the 0.3.1 release work, and merged it at `b081f16c`.
Local `main` now also matches `upstream/main` at `dac6b9d4`.
Resolved two documentation conflicts: retained upstream's newer video bug fix record and both index links.
The two local IDE edits were identical to upstream's result; the merged tree preserves them with no local diff.
A recovery patch remains at `.git/pm-sync-20261116-ide.patch`.
Retained evidence is now ignored by the incoming mainline rules.
Read the incoming workflow changes: build-safe evidence placement, legacy-test signature allowance,
command-line and network test restrictions, and the Host Inputs rules.

The pile now has three ideas. The new November 13 idea proposes packaging proven processes as reusable assets.
It covers pair review, modular unit testing and recorded E2E scenarios, inside and outside DevCapsule.
Read it as input to the pending presentation-authoring scope; no priority, implementation owner or delivery shape is selected.
The 20 intake items and the next-slice decision remain pending.

### Earlier resumption, 2026-11-16

The owner selected project management and authorized `upstream/main` as the baseline.
Local `main` now matches canonical `upstream/main` at `1942f396` and tracks it.
The former local README relocation commit was discarded from `main` with the owner's permission.
The clean github-auth branch was already paused and published; its mailbox was empty and its claim released.
Selected `ws-project-management/coordination` and merged upstream main at `d137c0fb`.
The workflow files already matched upstream; synchronization brings in the four remaining mainline commits.
The known declaration/root-definition version mismatch remains unchanged.

Read the published status, all intake, both ideas, and the current live workstream list.
No open bug is owned by project-management.
Received three messages at `45c2cbd7`; the intake now holds 20 undecided items:

- `2026-11-12-maintenance-compatibility-promise-story-and-packaging.md` carries the owner's post-0.3.1 compatibility-policy request.
  The existing ruling permits dropping compatibility with 0.2.14, 0.2.15 and earlier releases.
  The support window, requirements, user documentation and release evidence still need a coherent design.
- `2026-11-16-presentation-authoring-portability.md` identifies the gap between a shipped viewer and source-only authoring support.
- `2026-11-16-github-auth-presentation-authoring-handoff.md` consolidates that evidence and the owner's successful, laborious reuse in another project.
  It supplements the earlier message; both remain pending together.

Receipt chooses no implementation owner, interface, priority or release target.
The proposed next slice is portable presentation-authoring scope, based on fresh adopter evidence.
The owner can instead choose compatibility, test-improvements reconciliation, or a broader queue review.
The unanswered decision `2026-11-16-project-management-next-slice` lives in capsule state, outside Git.

Maintenance's live publication now reports its mounted-settings bug closed after PR #29.
The older blocked-gate statement below is historical, not the current reason for this checkout's gate failure.
Prior stash and website-recovery statements below describe the November 12 session, not verified state in this checkout.

### Historical resumption, 2026-11-12

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

On owner-directed resumption, follow the accepted backlog and its release
triggers; no intake question remains. Current owner direction selects maintenance
for rc3 preparation and a tally of remaining 0.3.1 work.

## Validation And Checkout State

### Intake outcomes and rewritten questions, 2026-11-17

Checked all local links in changed documents: no missing targets. Reviewed all
15 dispositions against the selected options and qualifying notes. The live
console serves exactly the two remaining intake items, unanswered; the standard
builder and checker accept the new page. No answer was manufactured or submitted.
A reference in the project-owned CI work order now links to the original intake
at its immutable revision. Two maintenance-owned historical links need the same
repair; a patch was delivered at coordination 2c5b25bb26cc, without editing those
records here. Whitespace checks pass. No product code or environment changed;
product tests were not rerun under the standing planning-validation exception.


### Questionnaire checkpoint, 2026-11-16

The standard `decisions from-table` builder created the document; `decisions
check` accepts all 17 questions as unanswered. Verified exact intake coverage,
unique keys, 2–3 options per question and existence of every cited local path.
The running console API serves all 17 items with no answer. Read the console's
submission code: note-only responses and partial submission are supported.
No answers were fabricated or submitted. Whitespace checks pass; no product
code or test environment changed, under the standing planning exception.


### Upgrade commitment checkpoint, 2026-11-16

Reviewed the scope decision, release-checklist change and intake disposition.
All 78 local links in changed documents resolve; whitespace checks pass.
Seventeen intake items remain. No product code changed or product tests ran,
under the owner's standing planning-validation exception.
The decision and checklist remain on the project-management branch until ordinary
integration; coordination mail carries the obligation to its recipients now.


### Current synchronized checkout, 2026-11-16

Ran the required build with `DEVCAPSULE_DIFF_BASE=upstream/main` and the existing `/var/tmp/pm-resume-20261116/pytest` scratch.
The first attempt used the default stale fork `origin/main`; the explicit canonical base removes those comparison-only convention failures.
Version, syntax, mypy (344 files), and test conventions passed.
The unit phase stopped at `tests/test_recursive_orchestrator.py::test_public_dry_run_is_unique_redacted_and_cleans_owned_staging`:
1,438 passed, one skipped, one failed, 175 deselected.
The failure reports `host Docker group ID must be a positive integer` during dry-run preparation.
Later gate phases did not run. The log is `.git/pm-sync-20261116-build.log`.
The prior evidence-script type failures no longer occur on this synchronized source.
The merge also carries an upstream blank line at EOF in `test_derivation.py`; conflict-resolution whitespace checks pass.
No product source was changed to address validation failures. The final tracked working tree is clean.


### Earlier checkout validation, 2026-11-16

Attempted the required build gate with the existing `.venv`.
`/opt/devcapsule-gate` is read-only here, so used the permitted alternative `/var/tmp/pm-resume-20261116/pytest`.
Version and syntax checks passed. Mypy stopped with five errors in two retained github-auth evidence scripts:
`presentation-check/check.py` and `record.py` under `devcapsule-src/tests/e2e/evidence/github-ssh-proxy/20261116T103152Z-af7fa02c/`.
Later gate phases did not run. The log is `.git/pm-resume-20261116-build.log`.
No product source changed, no environment was provisioned, and no container or deployment was started.
The retained evidence directory is untracked on this branch; it stays outside project-management commits.
IDE changes to `.idea/modules.xml` and `.idea/rotated-consensus.iml` appeared after switching and remain untouched.
The website checkout matches the synchronized gitlink.
Release the setup claim after publishing; keep project management selected for the owner's next choice.

### Historical validation and preservation, 2026-11-12

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

- No unanswered intake decision remains; all original 18 items are dispositioned.
- The successor upgrade commitment and all November 17 notes remain binding.
- Future registrations, timing design and adopter planning wait for their
  recorded triggers; detailed designs remain where the owner reserved them.
- The sample release-check work is assigned, not implemented; its initial list,
  pass criteria and first enforcing release remain to be designed.
- Three ideas remain untriaged. No new service, container or environment started.
- Two historical intake-link corrections were delivered to maintenance as a patch.
- Deliberately not preserved in Git: questionnaire/answer JSON, tokened URLs or
  a transcript. The decisions are retained in the normal backlog and logs.

## Workstream Document Index

- [Sample-project release check](../../work-orders/2026-11-17-sample-project-release-gate.md): owner-ordered scenarios, sample updates and video/presentation evidence.

- [Upgrades in the first release after 0.3.1](2026-11-16-decision-upgrades-next-release.md): accepted scope obligation, concrete user problem and release checkpoints.

- [E2E recording and presentation use case](2026-11-16-design-presentation-excellence.md): engineer inputs, agent flow and returned web-console link; design explicitly deferred.

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
- [Intake decisions](intake-dispositions.md): append-only outcomes; `intake/` is empty as of November 17; receipt is not a disposition.

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
