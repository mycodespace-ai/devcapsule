---
description: How several people and agents work on one repository with workstreams, status files, mail, and a coordination branch using DevCapsule's workflow.
aliases:
  - /docs/guides/working-in-workstreams/
weight: 1
updated: 2026-10-30
---
# Work in workstreams with humans and agents

This guide is for a project that uses the DevCapsule workflow in
`multiple-streams` mode: several people and several coding agents, each on
their own workstream, coordinating through Git alone. It explains what a
session looks like and which command does what. The rules themselves live in
the project's `WORKFLOW.md`, which this guide explains and never redefines;
when the two seem to differ, `WORKFLOW.md` governs.

Commands run from any directory inside the repository checkout—inside the
capsule or on the host—on the `ws-<name>/...` branch of the workstream you are
working in (or pass `--project PROJECT_PATH` and `--workstream NAME`
on subcommands that select one workstream, such as `brief` or `claim`).
Every command works identically for a person and for an agent.

## The idea in one paragraph

Your project has a `main` branch that holds the integrated record, and one
shared branch, `coordination`, that holds the live view. Nobody ever merges
`coordination` into `main`, and nobody ever opens a pull request for it. Each
open workstream keeps a status file (`CURRENT-STATUS.md`) and an intake
disposition log (`intake-dispositions.md`) on its working branch; publishing
pushes copies of them to `coordination` so every checkout sees current status
right away. Messages between workstreams travel the same branch as small
Markdown files. Nothing about coordination waits for a pull-request merge, and
everything uses plain Git plumbing and Markdown, so it works against any Git
remote—including a bare directory on a shared disk.

## A session, start to finish

**1. Get your bearings.** One command prints what you need before acting:

```bash
devcapsule workflow brief
```

It shows your workstream's state and next task, who else is working on what
right now, how many messages wait for you, whether `WORKFLOW.md` or
`WORKFLOW-LOCAL.md` changed on `main` since you last read them, and how far
behind `main` your branch is.

**2. Take your mail.** Check waiting items with `devcapsule workflow mail
check`, or copy them into your workstream's `intake/` directory—staged in Git
and removed from `coordination`—with:

```bash
devcapsule workflow mail take
```

Commit the taken items on your working branch. Later, decide each item—either
acknowledging it into your status file or forwarding it to
`project-management`—in one commit that records the disposition in
`intake-dispositions.md` and deletes the file from `intake/`. Items sent by
`project-management` cannot be forwarded; acknowledge them, or raise a genuine
disagreement with the human.

**3. Catch up with `main` when needed.** Synchronizing is mandatory when
`WORKFLOW.md` or `WORKFLOW-LOCAL.md` changed on `main`, and recommended when
`main` touched files your task will edit. Merge `main` into a branch that has
already been pushed; rebase only a branch that has never been pushed.

**4. Say what you are working on.** A soft claim tells other checkouts, human
or agent, which slice you are working on. It expires after twelve hours by
default (`--hours HOURS` changes the duration) and informs without blocking
anyone:

```bash
devcapsule workflow claim "fix the upgrade recovery"
```

**5. Work.** Edit, commit, and run your validation checks on your `ws-<name>/`
branch as usual.

**6. Publish at checkpoints and before you stop.** First update and commit
your status file with the current state, validation, next task, and Open
Threads. Take any waiting mail before pausing. Publishing pushes your working
tree's `CURRENT-STATUS.md` and `intake-dispositions.md` to `state/<name>/` on
`coordination`:

```bash
devcapsule workflow publish
```

Publishing also stamps your status file (`Definition read:`) with the workflow
revision you read, which is how `workflow brief` knows whether the rules
changed before your next session. Commit that stamp too if publishing changed
the file. When a workstream concludes and integrates,
`devcapsule workflow publish --retire` removes its live directory from
`coordination`.

**7. Release your claim when you pause.**

```bash
devcapsule workflow claim --release
```

## Send work to another workstream

Write the intake item as a Markdown file named
`YYYY-MM-DD-<your-workstream>-<slug>.md` outside the repository working tree,
then deliver it:

```bash
devcapsule workflow mail send maintenance /tmp/2026-09-21-alpha-upgrade-bug.md
```

Pass a comma-separated list to reach several recipients, or `all` to send to
every workstream that has published state. Sent mail is never edited in place:
to correct an item, send a new file under a new name stating what it
supersedes. Only the recipient removes an item from `mail/<recipient>/`, by
taking it.

## See everyone at once

```bash
devcapsule workflow status
```

Prints one block per published workstream: its state, branch, commits behind
`main`, whether the workflow definition changed since its last stamp, when it
last published, any active claim, and its planned next step. A workstream that
has never published does not appear until its owner runs `devcapsule workflow
publish` once.

## Where things live

| What | Where | Reaches `main` how |
|---|---|---|
| A workstream's status file, `intake-dispositions.md`, and `intake/` | `engineering-docs/wip/<date>-<name>/` on its working branch | Inside its ordinary pull request |
| The live copy of each status file, disposition log, and claim | `state/<name>/` on `coordination` | Never; it is the live view |
| A message in flight | `mail/<recipient>/` on `coordination` | Never; the recipient takes it |
| The list of open workstreams | Root `CURRENT-STATUS.md` on `main` | Each workstream updates its own row |
| The reusable workflow (`AGENTS.md`, `WORKFLOW.md`) | Repository root, installed by `devcapsule bootstrap project` | Refreshed on explicit request via `devcapsule bootstrap project --refresh-workflow-definition` |
| Your project's own rules | `WORKFLOW-LOCAL.md` in the repository root | Edited and reviewed like any repository file |

The `[workflow]` table in `.devcapsule/devcapsule.toml` declares the workflow
definition, the DevCapsule release version it was installed from, and the mode
(`single-stream` or `multiple-streams`). `WORKFLOW.md` carries that same
version in its frontmatter, and `devcapsule bootstrap` keeps the two aligned.

## Without the CLI

Everything on `coordination` is ordinary Git content, so a contributor on a
machine without `devcapsule` installed can still inspect or participate:

```text
git fetch origin coordination
git show origin/coordination:mail/<your-workstream>/          # waiting mail
git show origin/coordination:state/<name>/CURRENT-STATUS.md   # live status
```

To send or take mail manually, add or remove your file under
`mail/<recipient>/` in a commit on `coordination` and push—never rebase or
force-push the `coordination` branch. Pass `--remote` or `--branch` on any
`devcapsule workflow` subcommand when a repository uses a non-default remote or
coordination branch name.

## If something gets in the way

- **"no workstream given and the current branch is not ws-\<name\>/..."**: you
  are on `main` or a branch without a `ws-<name>/` prefix. Switch to your
  workstream branch or pass `--workstream NAME`.
- **A push is rejected while sending or publishing:** another checkout updated
  `coordination` at the same moment. The CLI automatically fetches and retries
  up to five times; if the branch is still moving, run the command once more.
- **"is already in flight with different content"**: an item with that filename
  is already waiting in the recipient's mailbox with different text. Choose a
  new filename rather than overwriting mail in flight.
- **Your workstream is missing from `workflow status`:** run `devcapsule
  workflow publish` once from its branch.
- **`workflow brief` reports that the definition changed:** read the *Changes*
  section near the top of `WORKFLOW.md` (and any updates in
  `WORKFLOW-LOCAL.md`), newest entry first, and apply any listed migration step
  when you merge `main`.
