# Agent Instructions

## Recorded end-user scenarios

When asked to execute an end-user scenario and capture video or produce a
recorded presentation, read `.agents/skills/devcapsule-recorded-e2e/SKILL.md`
relative to the project root and follow it. Recognize equivalent wording;
the user need not say E2E or name the skill. Workflow bootstrap installs this
skill and a copy in `.claude/skills/` for Claude Code.

## Project workflow

Before starting work, read `README.md`, then read the `[workflow]` table in
`.devcapsule/devcapsule.toml`: `definition` names the workflow, `version` the
DevCapsule release the project's `WORKFLOW.md` came from, and `mode` is
`single-stream` or `multiple-streams`. A missing table falls back to the older
top-level `workflow-type` field; a missing value means `single-stream`. Treat
any other value as invalid. The declared version governs: follow this
repository's `WORKFLOW.md` as it is, whatever newer text you know, and never
refresh it or change the declared version except on explicit instruction.

Read `WORKFLOW.md` for the reusable protocol, starting with its *Vocabulary*;
then `WORKFLOW-LOCAL.md` for this project's own half of the workflow, which
governs wherever `WORKFLOW.md` is silent; then `CURRENT-STATUS.md` for this
project's live state. In single-stream mode, `CURRENT-STATUS.md` is the active
status file. In multiple-streams mode, it is the mainline workstream list: select the one
workstream associated with the user's request and current branch, then read its
`engineering-docs/wip/YYYY-MM-DD-NAME/CURRENT-STATUS.md` and `intake/`.
Read that status file in full and open the documents its index lists only
when the task needs them. Do not mix two workstreams' unfinished state in one
checkout.

After reading, tell the user that you understand the project and state the
recorded next step before proceeding. Explicit user direction may reprioritize
that step without erasing it.

Treat `REQUIREMENTS.md` as the requirements overview and index. Read only the
detailed requirement, decision, bug, or specification records needed for the
selected task.

Keep important requirements, decisions, evidence, open questions, current
state, and next steps in repository files rather than only in chat. Update the
selected status file at meaningful checkpoints and before pausing. In
multiple-streams mode, follow `WORKFLOW.md` for branch routing, synchronization,
intake decisions, publishing, and integration. At session start run
`devcapsule workflow brief`, take your mail with `devcapsule workflow mail
take`, claim your slice with `devcapsule workflow claim "<slice>"` before
editing and release it when you pause, and propose whether to synchronize with
`main` now, from the list's facts: a changed definition or local workflow
file is a must, otherwise weigh it and say why; send items with `devcapsule workflow mail
send`, including a patch for work that turns out to belong to another
workstream, reverted from your checkout rather than committed on your branch; publish your status file with `devcapsule workflow publish` at each
checkpoint and before pausing. Records reach `main` only inside your ordinary
integration; nothing is merged for a record alone. A workstream-list row whose
branch association names a `release-<version>` branch means that workstream is
driving a release: follow *Releases* in `WORKFLOW.md`, and never rebase,
force-push, or cherry-pick release refs. Workstream branches are
`ws-<name>/<sub>`; every ref outside `main` (or the integration branch `WORKFLOW-LOCAL.md`
names instead), `ws-*`, and `release-*`
is the project's own, and you do not create, rename, delete, rebase, or
select one unless `WORKFLOW-LOCAL.md` or the user directs it. Every multiple-streams project has two
reserved workstreams, `project-management` and `maintenance`; report a project
missing either as incompletely initialized. Bug records under
`engineering-docs/bugs/` are routed by their frontmatter `owner` field: list
the open bugs owned by the selected workstream at session start, and file new
ones with `owner` set to the open workstream whose goal covers them, otherwise
`maintenance`. See *Bug Intake* in `WORKFLOW.md`.

The workflow is intentionally incomplete. Where it is silent, use judgment,
record the gap and the action taken in the selected status file, and continue
unless another instruction requires stopping or asking for authority.

Maintain `index.md` when permanent Markdown files are added, removed, renamed,
or moved. Preserve existing project-specific instructions when extending this
file; refresh the reusable definition only when the developer explicitly asks.

`PREAMBLE.md` and `INFORMATION-MODEL.md`, installed beside `WORKFLOW.md`, are
marked *for humans*: explanation, not rules. Skip them in ordinary work; read
the preamble when you must decide something the rules do not settle, alone or
with the human, and the model when the question is what kind a thing is.
