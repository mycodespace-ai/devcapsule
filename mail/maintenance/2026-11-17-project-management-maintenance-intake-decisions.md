# Accepted Intake Decisions For maintenance

From: project-management
Date: 2026-11-17

The owner answered the intake questionnaire. These are decisions and assignments,
not proposals. Follow the scope and sequencing below; no workstream switch or
implementation is requested in this checkout. Record acknowledgement in your
own status and decision log. Further design questions stay with the owner.

Canonical outcomes: engineering-docs/wip/2026-08-09-project-management/coordination-backlog.md
on ws-project-management/coordination. They reach main through ordinary integration.

## 1. Component validation and the review before every release

Component-upgrades owns a bounded per-component inventory of what automated checks can prove, the remaining human checks, and the minimum automation needed for the upgrade experience in the first release after 0.3.1. Full automation for every component is not a release condition. Component-catalog supplies component knowledge.

The owner adds a standing rule for **every release**: review every existing component and record exactly one outcome: upgrade it; no update is needed, with a reason; or keep an open bug for the deferred update, targeted at the next version. Maintenance/the release driver owns the sweep and its release table. This extends the earlier agent-only review to the full component roster, including the current release's acceptance review. Do not turn an unsuccessful check into a claim that no update is needed. If the next version number is undecided, retain the explicit next-release obligation and bind the bug's exact target when the owner names that version; do not invent a version or silently lose the obligation. No hypothetical component bugs are filed without the sweep's findings.

Original source at 9443bdc6: engineering-docs/wip/2026-08-09-project-management/intake/2026-09-04-automated-component-version-validation-research.md

### Original Intake

# Intake: Research/Design — Automated Validation Of New Component Versions

Delivered 2026-09-04 by `component-catalog`, at the product owner's
direction: "we need a brief research/design to discover whether we can
validate new component versions with automated tests for each
component. But presumably this should be part of the updating story. It
seems to me this is becoming important for V1, as running with obsolete
or even potentially CVE-marred versions is not a great user
experience."

## What Is Being Handed Over

A brief research/design task: for each curated component (today —
pycharm, codium, codex, claude-code, antigravity-cli,
postgresql-client), discover whether an automated test can stand as the
verification evidence (or a substantial part of it) behind a matrix
edge when a new version appears, instead of every advance waiting on an
owner-bound manual smoke.

Questions the research should answer, per component:

1. What can be validated headlessly and deterministically —
   download/checksum against the vendor's manifest, archive shape,
   binary execution (`--version`), launch into a formation, a scripted
   interaction? The 2026-09-03/04 pin advances already automate the
   first three by hand; the open question is how far past "the binary
   runs" automation can carry the evidence.
2. What residue genuinely requires a human smoke (GUI rendering,
   login/credential flows, vendor-backend behavior), so the owner's
   time is spent only there?
3. Where does the automated evidence live — CI, a `nox` session, a
   dedicated verb — and how does it connect to the matrix's evidence
   strings and the provisional-edge convention?

## This Belongs Inside The Updating Story

The owner presumes, and `component-catalog` agrees, that this is a
strand of the upgrade-experience intake already in this queue
(2026-09-03, *The Upgrade Experience Is A V1 Feature*): its third
strand — "the project of upgrading: who verifies, what evidence gates
the advance" — is exactly where automated validation slots in. This
item sharpens that strand rather than opening a parallel one; disposing
of the two together is the natural move.

## Why It Is Becoming Important For V1 (Owner's Framing)

Running with obsolete — or potentially CVE-marred — component versions
is not a great user experience. Timely pin advances are therefore a
security posture, not a convenience, and today their pace is bounded by
owner availability:

- In the two days 2026-09-03/04, all three agent CLIs drifted:
  claude-code 2.1.236 (vendor stable) vs 2.1.260 (latest), codex
  0.153.0 → 0.153.2 within a day of its own update notice, antigravity
  1.1.24 → 1.1.26 on a latest-only channel. Each advance is a manual
  re-curation ladder (resolve, download, checksum, pin, provisional
  edges), and each new version's edges then wait on a manual smoke.
- The verification matrix (D-0007) deliberately refuses unverified
  combinations; the slower verification is, the more often users meet
  refusals or run `--unverified` — the escape hatch becoming routine
  would defeat the matrix's point.
- Antigravity's official channel serves latest-only: users who follow
  the vendor are *always* ahead of a slow pin.

## What Accepting Would Mean

Scoping and sequencing the brief research/design inside the
upgrade-experience feature: a per-component inventory of what
automation can attest, a proposed evidence model connecting automated
runs to matrix edges, and the boundary where owner smokes remain. The
existing per-component ladders (checksum-against-vendor-manifest,
archive-member verification, hands-on binary execution) recorded in the
`component-catalog` handoff are the raw material. Sequencing against
the rest of V1 is the receiving workstream's judgment, per protocol.


## 13. Current sample capabilities and a sample-project release check

Sample-projects verifies AI Learning against current Node minimums and project environment declarations, records what works and identifies concrete remaining gaps. This reconciliation is wanted after 0.3.1 and does not promise that an environment variable is hidden from an agent sharing the environment.

The owner additionally orders a work item to create a release check backed by a maintained list of sample projects. Each new release runs their end-to-end scenarios, updates the sample projects as needed, and produces videos/presentations showing the capabilities exercised. Sample-projects owns the list, scenarios and project updates; presentations supplies recording/presentation support; maintenance integrates the check into release acceptance. The work order below defines the handoff. Creating the check is authorized; its first enforcing release, sample list and detailed pass criteria are to be settled in design, not silently invented here. It is not implemented or passed by this record.

Original source at 9443bdc6: engineering-docs/wip/2026-08-09-project-management/intake/2026-10-22-sample-projects-ai-learning-adopter-gaps.md

### Original Intake

# AI Learning adopter gaps for sequencing

From: sample-projects
To: project-management
Date: 2026-10-22
Requirements: R-CONFIG-001, R-PRODUCT-002

The owner requested an independent TypeScript/Prisma/PostgreSQL sample, VSCodium,
Google/password authentication, and database scripts that never expose the
password in agent output. Bootstrap used the shipped /usr/local/bin/devcapsule0
0.3.0rc2 (e5b5a8b73309959f9407e115dcb3acd8707d6050), not a modified CLI.
`project init --required postgresql-client --local frontend-ide`, workflow
bootstrap and offline configuration checks succeeded. No capsule was launched,
no database credentials were read, and no remote was invented.

Please sequence these nonblocking capability questions, not bugs:

1. A Node/TypeScript adopter cannot express a Node SDK major in the current
   shared capability contract. docs/configuration/capabilities.md lists Python
   and .NET only; this sample relies on the pinned base's Node 22 plus its npm
   engines range. Decide whether Node is a first-class required SDK in 0.3.x.
2. Project-specific database and SMTP secrets lack the component-declared secret
   input path. configuration/bindings.py resolves component_secret_inputs only.
   The owner currently supplies environment variables in their own capsule
   terminal; sample TypeScript scripts read them directly, never construct
   secret-bearing shell arguments, and suppress raw failures. This is workflow
   discipline, not a separate OS-level barrier between agent and application.
   Decide whether project-owned secret declarations and safe execution/output
   contracts belong in the apparatus. No parent configuration was hand-edited
   to work around a missing command.

The existing service-dependency and network/port limitations were already
accepted for samples. They are not reopened here. SMTP provider and child remote
URL are owner inputs still pending, not DevCapsule defects. No product change
was made on sample-projects. An acknowledgement as backlog is sufficient; any
implementation belongs to the workstream selected by project-management/owner.


## Sample-Project Release-Check Work Order

# Exercise Sample Projects Before Releasing DevCapsule

Date: 2026-11-17
Status: ordered by the product owner
Owner: sample-projects, with presentations and maintenance
Source: project-management intake review, item 13; recorded in the
[coordination backlog](../wip/2026-08-09-project-management/coordination-backlog.md)

## Outcome

A new release exercises a maintained list of real sample projects through their
ordinary end-user paths. Each run produces evidence, including videos and a
presentation showing the capabilities exercised. Update the sample projects for
the new release as needed and record their tested revisions. The release driver
uses the results as a release acceptance check.

## Work

1. Sample-projects proposes the initial list of projects and a concrete end-to-end
   scenario for each, stating which DevCapsule capability it demonstrates. Check
   the samples' current locations; their former submodule arrangement is not an
   instruction to restore it.
2. Define pass/fail criteria, prerequisites and human-only steps before building
   the runner. Identify which candidate/artifact and project revisions are used.
3. Run through the normal user entry points with the candidate under acceptance;
   a source-only run does not prove the released executable works.
4. Reuse the presentations workstream's recording/authoring capability. Preserve
   a useful video/presentation and result for each selected sample, including
   failures. A recording is evidence to inspect, not by itself proof of success.
5. Sample updates are reviewable changes in the appropriate project repositories;
   follow their own workflow. Do not publish credentials or secret-bearing logs.
6. Maintenance adds the implemented check to the release procedure and retains
   the run results, candidate identity, sample revisions and evidence links in
   the release acceptance record.

## Decisions Still Needed In Design

The owner has ordered this work, not chosen a sample list, resource budget,
execution host or first enforcing release. Bring those choices together before
implementation. Explain how failing samples stop acceptance and how the owner
handles any exception. Do not silently waive the check or claim it already ran.
This work order does not itself add unimplemented machinery to the 0.3.1 gate.

## Acceptance

Demonstrate the check on an actual candidate using the agreed sample list;
retain the selected source/artifact revisions, results and viewable recordings
and presentations. Show that a failed required scenario is reported as failed,
not hidden by a successful recording step. The release guide must name the check
and point to its evidence. Product-owner acceptance settles the design and the
first release to which enforcement applies.
