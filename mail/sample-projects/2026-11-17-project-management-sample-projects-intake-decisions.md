# Accepted Intake Decisions For sample-projects

From: project-management
Date: 2026-11-17

The owner answered the intake questionnaire. These are decisions and assignments,
not proposals. Follow the scope and sequencing below; no workstream switch or
implementation is requested in this checkout. Record acknowledgement in your
own status and decision log. Further design questions stay with the owner.

Canonical outcomes: engineering-docs/wip/2026-08-09-project-management/coordination-backlog.md
on ws-project-management/coordination. They reach main through ordinary integration.

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
