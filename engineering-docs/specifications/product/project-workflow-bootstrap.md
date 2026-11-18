# Project Workflow Bootstrap

Status: implemented

Requirements: `R-PRODUCT-003`, `R-PRODUCT-004`, `R-PRODUCT-005`,
`R-PRODUCT-006`, `R-PROC-001`

## Purpose

DevCapsule distributes its human/agent workflow as product functionality. The
distribution must distinguish reusable protocol from the state of any one
project, including the DevCapsule repository itself.

## Asset Boundary

Reusable workflow definitions are packaged beneath
`devcapsule.assets.project_workflow/definition/`:

- `AGENTS.md` is the concise agent entry point;
- `WORKFLOW.md` is the complete workflow protocol.

Project-instance templates are packaged separately beneath
`devcapsule.assets.project_workflow/templates/`. They initialize files whose
content belongs to the adopting repository:

- `CURRENT-STATUS.md`;
- `REQUIREMENTS.md`;
- `index.md`;
- the bug template and engineering-record directories;
- in multiple-streams mode, the root registry and reserved
  `project-management` handoff, intake, and disposition log.

Definition files say how collaboration works. Instance files say what this
project is, what it has accepted, what is happening now, what evidence exists,
and what happens next. DevCapsule's own root `CURRENT-STATUS.md`, declaration,
and WIP records are an instance, not reusable defaults.

## Installation Contract

`devcapsule bootstrap [--project DIR]` and its explicit
`devcapsule bootstrap project [--project DIR]` form read `[workflow].mode` from
`.devcapsule/devcapsule.toml`, falling back to the older `workflow-type` field.
An absent mode means `single-stream`. Any value
other than `single-stream` or `multiple-streams` fails before files are written.
Without `--project`, both forms use the process's current directory and do not
redirect through an ambient container `PROJECT_PATH`.

The command:

1. installs missing `AGENTS.md` and `WORKFLOW.md` from packaged definition
   bytes;
2. initializes only missing project-owned files and directories, including
   the project's `WORKFLOW-LOCAL.md` rendered once from its template;
3. preserves existing project-owned files;
4. migrates an older final README `Current State And Next Step` section into a
   newly created single-stream `CURRENT-STATUS.md` without deleting the README
   section;
5. initializes the two reserved workstreams, `project-management` and
   `maintenance`, when multiple-streams mode lacks them;
6. appends only missing standard development ignore entries; and
7. installs missing complete recording skill kits in
   `.agents/skills/devcapsule-recorded-e2e/` and
   `.claude/skills/devcapsule-recorded-e2e/`.

Each kit contains `SKILL.md`, `kit-version.json` with the supplying package
version, and `presentation_tools/` with the guide, producer, recorder, and example.
An existing skill directory or symlinked destination/parent is preserved.
A new kit is staged beside its destination before publication; a failed write
does not leave a partial kit at that destination. The two locations are installed
independently. Setup does not execute tests or provision browser automation.
`project wrap` installs the same kits in its wrapper repository.
See the [installed guide](../../../devcapsule-src/devcapsule/presentation_tools/README.md)
for manual migration of an older customized kit.

Running bootstrap again is idempotent. It must reuse the existing immutable
start date of each reserved workstream and must not create a second instance
of either. If an existing multiple-streams registry has no reserved
project-management handoff, bootstrap reports the instance as incompletely
initialized before writing anything; repairing workflow state requires
deliberate human judgment. A project that has `project-management` but
predates the `maintenance` workstream is not incomplete in that sense:
bootstrap adds `maintenance` with the current date as its start date, which
is the adoption exception `WORKFLOW.md` defines for it.

## Definition Refresh

Existing definition files are preserved by default because `AGENTS.md` may
contain project-specific additions. The explicit
`--refresh-workflow-definition` option replaces only `AGENTS.md` and
`WORKFLOW.md` with the packaged definition. It never replaces project state,
requirements, the documentation index, workstream records, or existing skill kits.

## Distribution And Verification

The workflow asset package is package data and therefore travels inside the
self-contained PEX. Source tests keep the packaged `WORKFLOW.md` byte-identical
to the root reusable definition. Packaging integration executes the built PEX
against an empty adopter directory and verifies that `WORKFLOW.md` and a valid
single-stream `CURRENT-STATUS.md` are created without consulting the source
checkout at runtime.
