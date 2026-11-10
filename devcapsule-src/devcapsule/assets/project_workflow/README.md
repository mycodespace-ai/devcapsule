# Packaged Project Workflow Assets

These assets deliberately separate two layers that coexist in the DevCapsule
repository but have different ownership:

- `definition/` contains reusable protocol files. DevCapsule distributes these
  bytes and `devcapsule bootstrap project` installs them as `AGENTS.md`, `WORKFLOW.md`,
  `INFORMATION-MODEL.md` and `PREAMBLE.md` in adopter repositories; the last
  two are marked *for humans*.
- `templates/` contains initial project-memory instances. Bootstrap renders
  these into files such as `CURRENT-STATUS.md`, `REQUIREMENTS.md`, `index.md`,
  `WORKFLOW-LOCAL.md` (the project's own half of the workflow, never refreshed),
  and, for multiple-stream projects, the reserved `project-management`
  workstream records.

Definition files describe how work is performed. Instantiated files describe
one project's purpose, accepted requirements, live state, branches, evidence,
and next step. Updating a reusable definition must not overwrite project state.
Bootstrap therefore installs missing definitions by default and refreshes
existing definitions only with `--refresh-workflow-definition`.

The root DevCapsule repository is itself an instance of this workflow, but its
`WORKFLOW.md` serves the needs of developing DevCapsule and need not be
byte-identical to the general-purpose definition shipped to adopters.
The two files marked *for humans*, `PREAMBLE.md` and `INFORMATION-MODEL.md`,
have no root copy in this repository: the packaged ones under `definition/`
are the only source, and the root `WORKFLOW.md` and `AGENTS.md` link there
instead of beside themselves, which is the one place their links differ from
the packaged copies. Packaging
coverage verifies that a built PEX installs the definition selected from this
asset directory. The root `CURRENT-STATUS.md`, `.devcapsule/` declaration, and
`engineering-docs/wip/` records are also DevCapsule-specific instance state.

The 0.3.0 packaged workflow includes the Pair Review Loop under its own
heading, matching root topic 9.11. The rest of the packaged document keeps
its existing organization; this terminology slice does not refresh the
whole definition. The root humane companion explains the same loop rules.

The 0.3.1 packaged workflow gains the pile of ideas the same way: its own
heading, *Pile Of Ideas*, with the rules of root topic 12.13, the glossary
entry, the directory's role, and one sentence under the reserved
`project-management` workstream.
