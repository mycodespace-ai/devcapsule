# Engineering Documentation

This tree contains contributor- and agent-facing artifacts used to design,
implement, validate, and coordinate the project. It is separate from `docs/`,
which is intended for stable product documentation consumed by DevCapsule
users and adopters.

Start with [For developers](../DEVELOPING.md) for the developer brief, local
setup, validation, and release guidance.

The root control files remain at the repository root because every contributor
and agent must discover them immediately:

- `AGENTS.md` — mandatory repository instructions;
- `CURRENT-STATUS.md` — authoritative linear handoff or open-workstream
  registry, as selected by `.devcapsule/devcapsule.toml`;
- `REQUIREMENTS.md` — root requirement overview and index;
- `WORKFLOW.md` — authoritative human/agent workflow; and
- `index.md` — repository-wide Markdown documentation index.

For release preparation and publication, use [Releasing a new DevCapsule
version](implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md),
the canonical operator guide based on v0.2.11.

## Structure

- `requirements/product/` — canonical repository-wide product requirement
  records.
- `requirements/devcapsule/` — canonical requirements for the active Python
  CLI/framework implementation.
- `specifications/` — normative technical contracts, schemas, protocols, and
  invariants.
- `decisions/` — durable accepted, rejected, deferred, or superseded design
  decisions.
- `design-notes/` — proposals, alternatives, design research, and unsettled
  architecture.
- `development/` — how the project is built and tested today: environment,
  source layout, and the unit, integration and end-to-end suites.
- `implementation-notes/` — execution plans, milestone plans, checklists,
  implementation investigations, and validation exercises.
- `wip/YYYY-MM-DD-NAME/` — temporary documentation and the detailed
  `CURRENT-STATUS.md` for an open workstream in `multiple-streams` mode. The
  date is the workstream's immutable ISO start date.
- `archive/YYYY-MM-DD-NAME/` — final status and retained evidence for a
  successfully or unsuccessfully ended workstream; it preserves the WIP
  directory name.
- `bugs/` — active or recently investigated defect evidence and closure
  criteria.
- `pile-of-ideas/` — one file per idea nobody has triaged yet;
  `project-management` triages the pile and removes what it decides.
- `completed-tasks/` — retrospective evidence for completed or retired work.
- `session-records/` — explicitly requested, sanitized historical session
  captures that supplement rather than replace canonical artifacts.

Scope-specific subdirectories such as `devcapsule/` and `docker4pycharm/`
separate active implementation records from historical prototype evidence.
These are documentation scopes, not source-tree paths; the active Python
distribution project lives at `devcapsule-src/`. Repository-wide records use
the `product/` scope where a category needs to distinguish them from
implementation-specific material.

## Placement Rules

Place documents according to their primary audience and authority:

1. Stable, current product guidance for a DevCapsule user or adopter belongs in
   root `docs/`. Workstream drafts never do.
2. Repository-wide startup and control documents remain at the root.
3. Contributor or agent engineering artifacts belong in this tree.
4. Within this tree, normative outcomes are requirements, normative technical
   behavior is a specification, adopted choices are decisions, unsettled
   proposals are design notes, and execution or validation evidence is an
   implementation note.

Historical records retain their original claims and dates, but links and path
references should point to the current repository location. Moving a record
does not change its status, authority, or validation result.

## Multiple-Stream Placement

This repository selects `multiple-streams`. Root `CURRENT-STATUS.md` is the
compact open-workstream registry. Each open workstream owns
`wip/YYYY-MM-DD-NAME/CURRENT-STATUS.md` and keeps every unfinished
engineering record beneath the same directory.

The directory name `docs/` is reserved beneath `engineering-docs/` and is
normally forbidden. The only exceptions are
`wip/YYYY-MM-DD-NAME/docs/` and
`archive/YYYY-MM-DD-NAME/docs/`, where draft user documentation remains
clearly non-authoritative.

On successful completion, new user documents move into root `docs/`, proposals
are applied to existing user documents, and enduring engineering records move
into their normal permanent categories. The archive retains a brief final
status and only useful short notes. On unsuccessful completion, the complete
WIP directory moves into the workstream archive without promoting unfinished
user documentation.

The full beginning, development, documentation, successful completion,
unsuccessful completion, integration, and recovery rules are authoritative in
[WORKFLOW.md](../WORKFLOW.md).
