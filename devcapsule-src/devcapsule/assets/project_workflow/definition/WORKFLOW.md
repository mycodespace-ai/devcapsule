---
definition: devcapsule
version: 0.3.2.dev0
---

# Human / Agent Iteration Workflow

This project treats markdown files in the repository as the durable memory for
human/agent work. Conversation is useful for speed, but project state must
survive model changes, IDE restarts, and future sessions.

Two files beside this one are marked *for humans*: [`PREAMBLE.md`](PREAMBLE.md),
why this workflow is opinionated and for whom, and
[`INFORMATION-MODEL.md`](INFORMATION-MODEL.md), the kinds of thing it stores
and how they relate. They explain; this file rules.

## Purpose And Principles

This document structures how a human and a coding agent build software
together. Its purpose is to make that pair more productive than either would be
alone, and it tries to achieve that by removing specific frictions rather than
by adding process. Every rule below is meant to pay for itself.

The rules follow from a small number of intents. Read a rule against these when
it seems arbitrary, and reason from these when the document is silent.

**Resumability.** A competent human/agent pair should be able to open this
repository cold, discover the current state, and continue — without access to
the conversation that produced it. Sessions end abruptly, models change,
context windows fill, and people forget. So state lives in committed files
rather than in chat, exactly one document is authoritative for each effort, and
the next step is written down rather than remembered. A workflow that only
works while someone remembers the last conversation is not a workflow.

**Low-ceremony coordination.** Coordination should cost as little as it can
while still working. Where several efforts run concurrently, the structure
exists to keep them from colliding — not to schedule them, gate them, or make
them negotiate. Contention is treated as a design failure rather than something
to arbitrate. Prefer conventions that make conflicts impossible over procedures
that resolve them, and prefer a rule an agent can apply alone over one
requiring a round trip.

**No accidental loss of knowledge.** Anything of importance surfaced during
development is recorded in the source tree and is predictably discoverable.
*Predictably* is the operative word: a fact stored somewhere nobody thinks to
look has been lost as surely as one never written. This is why documents have
assigned roles and fixed locations, and why an index exists at all. Knowledge
that only survives in a chat log is one session away from gone.

**Judgment where this document is silent.** The workflow is incomplete and says
so. What it does not expressly deny is allowed, and a pair meeting an
unforeseen situation decides for themselves what best suits it rather than
stalling. The obligations that keep this safe rather than merely permissive are
in *Where This Document Is Silent*.

**Retrospective value, subordinate to the work.** Record enough about how the
project evolved to support later analysis, learning, and rediscovery of
reasoning that would otherwise have to be reconstructed. But the source tree's
first purpose is the software. Process records are placed and structured so
that someone reading the code can ignore them entirely, and so that they never
compete with source for attention or for space in the paths people actually
work in.

**Explicit decision rights.** The pair is not two interchangeable actors.
Mechanical, reversible, and evidently-intended work is the agent's to do
without asking; product intent, ambiguity that changes the outcome, and
irreversible or outward-facing acts are the human's. This document says which
is which at each point rather than leaving each pair to renegotiate it, because
an agent that asks about everything is useless and one that asks about nothing
is dangerous.

**Portability across agents and projects.** The workflow must work for any
capable agent, not one vendor's, and in an adopter's repository, not only this
one. It therefore lives in plain markdown in the source tree, depends on no
tool-specific storage or feature, and keeps project-specific facts separate
from the reusable protocol.

### When These Conflict

They will. Recording everything imaginable serves knowledge and violates low
ceremony. Full retrospective detail competes with a source tree that stays
about the software. Judgment sits in tension with predictability.

Three tiebreaks, in order:

1. **Resumability wins.** If dropping a record would leave the next pair unable
   to continue, or able to continue only by guessing, write it. This is the
   purpose the others serve.
2. **Write what changes future behavior; skip what merely proves work
   happened.** A decision, a constraint, a rejected alternative, or a
   non-obvious reason changes what someone does next. A narrative of activity
   does not. When unsure, ask what a reader would do differently having read it.
3. **Prefer one durable record to several.** Update an existing document rather
   than adding one; link rather than copy; put a fact where its role says it
   belongs even when somewhere else is more convenient today. Duplication is
   how records drift apart and stop being trustworthy.

### How To Read This Document

Humans: `PREAMBLE.md` says why the workflow is what it is, and
`INFORMATION-MODEL.md` draws what it stores; read those first. Here, the *Glossary* names everything in plain words; the *Multiple-Stream
Workflow* and *Markdown Roles* sections carry the structure; the rest is
detail you can consult when it becomes relevant. Explanation and examples
written for people live in the project's user documentation, which explains
these terms and defines none of them.

Agents: read the whole applicable path before acting, treat the numbered
restrictions and procedures as binding, and treat prose as the reasoning that
explains them. Where a rule and this preamble appear to disagree, the rule
governs and the disagreement is a defect worth reporting.

**The *for humans* marker.** A file or section that opens with *For humans*
carries explanation, not rules. An agent skips it in ordinary work. It
returns to the preamble when it must decide something the rules do not
settle, alone or together with the human, and to the model when the
question is what kind a thing is.

### Vocabulary

Where this document needs a precise word for a piece of process, it uses the
vocabulary of the Workflow Patterns initiative (Wil van der Aalst, Arthur ter
Hofstede, Nick Russell and others; <http://www.workflowpatterns.com/>). That
vocabulary was chosen because its base terms are ordinary words that humans
and agents already know, and because its catalogue gives a shared, neutral
name to a shape of process when one is needed. The base terms:

- **Process** — a definition of how a kind of work is carried out. This
  document defines the development process a project runs.
- **Case** — one run of a process. Developing one project is one case of the
  development process.
- **Sub-process** — a process that runs as part of another. A workstream is a
  case of the workstream sub-process. A release is a case of the release
  sub-process; see *Releases*. Sub-processes run inside the development
  process, not inside each other, so this changes nothing about restriction 1.
- **Task** — a unit of work in a process. **Work item** — one occurrence of a
  task once it exists and is assigned to someone.
- **Resource** — who or what performs a work item. Here the resources are the
  pair and, in `multiple-streams` mode, the workstream the pair is working in.
- **Trigger** — the event or decision that makes a task ready to perform.

Three limits keep this useful rather than ceremonial:

1. The vocabulary is a reference, not a modelling obligation. Rules are written
   in plain English. Nothing has to be expressed as a pattern before it is
   allowed, and no formal model of the process is kept.
2. A pattern name appears only where it makes a rule shorter or less ambiguous
   than plain words would, and the sentence must still read correctly to
   someone who does not know the pattern.
3. Where this document already uses a word with its own meaning, this
   document's definition governs inside this document. One known collision:
   **milestone** here is a planning unit, defined in *Release, Milestone,
   Stage, Task, And Checkpoint Terminology*; in the pattern catalogue it is a
   control-flow pattern. The *Glossary* below defines every term this
   document uses with a fixed meaning and ends with the mapping onto the
   reference vocabulary.

### Glossary

Every term this document uses with a fixed meaning, in plain words, once.
Each entry says what the thing is, where it lives when it is a file, and what
it must not be confused with. Terms not listed here mean what they mean in
ordinary English. Older names for some of these, listed under *Changes*,
remain understood as synonyms for one release and are then retired.

**The project and its copies.**

- **Project**: the repository and its history.
- **Remote**: the shared hosted copy where branches meet and `main` is
  authoritative. Not a checkout.
- **Checkout**: one local clone directory where a pair edits files. Not a
  branch: a checkout has a current branch and may change it.
- **Pair**: one human and one agent working together in one checkout.
- **Product owner**: the human who makes product decisions and holds the
  decision rights this document reserves for "the human".
- **Mode**: `single-stream` or `multiple-streams`, declared in
  `.devcapsule/devcapsule.toml`. Not a runtime setting.
- **Declaration**: the `[workflow]` table in `.devcapsule/devcapsule.toml`,
  naming the definition, its version, and the mode.
- **Definition**: this document, installed and versioned. Not the local
  workflow file, which is the project's own.
- **Local workflow file**: `WORKFLOW-LOCAL.md`, the project's own half of the
  workflow, governing where this document is silent.

**Branches.**

- **Integration branch**: `main`, or the branch the local workflow file names
  instead. Every `main` in this document means it.
- **Workstream branch**: `ws-<name>/<sub>`, a branch belonging to one
  workstream. Not every branch: refs the workflow does not name are the
  project's.
- **Coordination branch**: `coordination`, the shared branch on the remote
  that carries mail and published state, never merged into `main`, never
  reset. Not a workstream branch and not a place for work.
- **Mail**: an intake item in flight, as a file under `mail/<recipient>/` on
  the coordination branch. Not an intake item yet: it becomes one when the
  recipient takes it.
- **Claim**: a workstream's `state/<name>/claim` on the coordination branch,
  saying who is working on it, on which branch, on what, until when. It
  informs; it never refuses. Not a lock.
- **Published state**: the live copy of a workstream's status file and
  decision log under `state/<name>/` on the coordination branch, pushed by
  the workstream from its working branch. The truth while the workstream is
  open; the copies on `main` are the record as of its last integration.
- **Release branch**: `release-<version>`, with candidate tags
  `v<version>-rc<n>` and the final tag `v<version>`. Not a workstream branch,
  even while a workstream drives the release.

**Workstreams and their records.**

- **Workstream**: a named, registered effort with one goal and its own status
  file, in `multiple-streams` mode. In the reference vocabulary, a case of the
  workstream sub-process. Not a branch: a workstream may own several.
- **Workstream name**: the unique lowercase identifier of a workstream, used as
  the branch prefix after `ws-` and in its directory name.
- **Reserved workstreams**: `project-management` and `maintenance`, which every
  multiple-stream project has and which end only on migration away from the
  mode.
- **State**: what a workstream is doing: `active`, `paused`, `blocked`, or
  `integrating`. Not a bug's `status`, and not the status file.
- **Workstream list**: the table of open workstreams in root
  `CURRENT-STATUS.md` on `main`, in `multiple-streams` mode. Not a container
  image registry, and not the list of checkouts the `project list` command
  reads; the older name "registry" meant this table.
- **Status file**: a workstream's `CURRENT-STATUS.md` under its open-work
  directory, the one authoritative account of its state, last task, next
  task, and open threads. In `single-stream` mode, root `CURRENT-STATUS.md`
  is the project's status file. Not the workstream list, and not a bug's
  status. The older name was "handoff".
- **Open-work directory**: `engineering-docs/wip/<start-date>-<name>/`,
  holding a workstream's status file, intake, decision log, and dated
  documents by kind; see *The Open-Work Directory*. The directory keeps its
  short name `wip`.
- **Record**: a dated document under the open-work directory holding history
  shed from the status file, a checkpoint, or a custody account. Read for
  retrospection, never required for work.
- **Archive**: `engineering-docs/archive/<start-date>-<name>/`, where an ended
  workstream's directory moves unchanged.
- **Intake**: a workstream's `intake/` directory on its working branch, the
  queue of items it has taken from its mailbox and not yet decided. Not where
  bugs go: a bug is routed by its record's `owner` field.
- **Item**: one file in an intake, one delivered piece of work or one
  question. Not a bug record, and not a task until the recipient decides it.
- **Decision**: what a recipient does with an item, one of exactly two:
  acknowledge it as its own work, or forward it to `project-management`. Not
  a decision record, which records a durable product or design choice.
- **Decision log**: a workstream's `intake-dispositions.md`, listing every item
  it ever received and what it decided. The file keeps its older name.
- **Deliverable**: what a workstream exists to produce; travels its working
  branch and is reviewed as a whole. Not a record.
- **Records**: the files that describe a workstream while it runs: its status
  file, decision log, list row, and intake. Edited on the working branch,
  published live to the coordination branch, and carried to `main` inside
  the deliverable's own integration; never merged for their own sake.

**Work and its units.**

- **Release**: an externally meaningful product version with artifacts,
  documentation, and acceptance evidence. In the reference vocabulary, a case
  of the release sub-process.
- **Candidate**: a versioned set of artifacts under release acceptance, tagged
  `v<version>-rc<n>`. Not a milestone.
- **Task**: a bounded unit of implementation, documentation, investigation, or
  validation.
- **Slice**: the narrow unit selected for one human/agent work cycle.
- **Checkpoint**: a durable snapshot of state, normally an update of the
  status file. Does not imply anything is complete.
- **Milestone** and **stage**: optional planning words for projects that plan
  in outcomes and their ordered subdivisions. No rule in this document depends
  on them. Not the milestone pattern of the reference catalogue.
- **Requirement**: a record of what must be true, under
  `engineering-docs/requirements/`, with a controlled status and priority.
- **Decision record**: a `D-####` record of a durable choice, under
  `engineering-docs/decisions/`. Not an intake decision.
- **Bug record**: a file under `engineering-docs/bugs/` with controlled
  `status`, `severity`, `target`, and `owner` fields. Routed by `owner`, never
  by intake.
- **Backlog entry**: a wanted capability or improvement that is not yet a
  requirement, with a priority, in a living list named for what it is under
  `project-management`'s open-work directory. The everyday word is
  "feature". Not a bug record; see *Bug Or Feature* in
  `INFORMATION-MODEL.md`.
- **Work order**: a scoped hand-over of requirements, decisions and backlog
  entries to a workstream, with finish criteria, under
  `engineering-docs/work-orders/`. An optional kind; delivered by mail like
  any item. Not a requirement, and not the workstream's status file.
- **Priority**: for requirements and backlog items, one of `gating`, the next
  release does not ship without it; `wanted`, high value, the release ships
  without it; `optional`, taken if cheap; `later`, not for this release. Not
  a bug's severity.
- **Exception**: a recorded departure from a rule, with its reason and the
  condition that ends it, in the local workflow file or in the record it
  concerns. Not silence: a rule that does not exist needs no exception.
**Validation.** The kinds of check a project may have, named the same way in
every ecosystem; the local workflow file's *Validation commands* says which
ones this project has and how each runs.

- **Environment**: what must exist on the machine before any check runs,
  the interpreter, the build tool, the dependencies, and how to obtain it.
  Declared first, because every other kind assumes it.
- **Unit test**: exercises code in one process with no network, no
  subprocess and no external service; runs wherever the environment exists,
  in seconds to minutes. Always in the gate.
- **Integration test**: crosses a packaging or process boundary, a built
  artifact, a subprocess, an external tool, a local service the project can
  start itself, and still runs on any developer machine. In the gate when it
  does.
- **End-to-end test**: exercises the delivered software the way a user
  would, with real infrastructure: containers, browsers, services. Opt-in or
  run on a candidate; its evidence is kept.
- **Smoke test**: the smallest end-to-end check that the software starts and
  answers; what "it runs" means for the project. Run on every candidate and
  after every deployment.
- **Gate**: the fixed set of checks a pair runs before a checkpoint and
  before integration; passes or fails as a whole. Not the candidate gate.
- **Candidate gate**: the checks a release candidate must pass before
  acceptance, with the acceptance evidence the release record keeps.
- **Acceptance evidence**: the recorded proof, from a downloaded or deployed
  candidate, that it does what the release claims; kept in the release
  record, never inferred from the gate.

- **Judgment where this document is silent**: the standing permission to
  resolve an uncovered situation and keep working, with the obligation to
  record what was done. The older name was "latitude".

**Mapping to the reference vocabulary.** The development process is the
process; a project is one case of it. A workstream and a release are cases of
its sub-processes. The pair and, in `multiple-streams` mode, the workstream
are the resources. A task or a slice, once selected, is a work item. The
product owner's decisions, and the events named in each procedure, are the
triggers.

### Changes

One entry per DevCapsule release that changed a rule, newest first, each with
the step a project takes to adopt it where one exists. The `version` in this
file's frontmatter names the release this text ships in; see *Workflow
Declaration* for what that version means and who keeps it correct.

#### 0.3.0

Entered on the working branch; the release that ships it stamps this entry
with its version. Rules changed since 0.2.14:

- **Pair Review Loop.** Formerly the review-partner loop; **Pair Review**
  is the short name. A slice is built by an implementor pair and a review
  partner of a different engine through PRn and PRn.1, with a written
  brief, at most three rounds and the human merging PRn. Run it only on
  the human's request for a task or session, or as the local default.
  No migration.

- **Two files for humans.** `PREAMBLE.md`, why the workflow is opinionated
  and for whom, and `INFORMATION-MODEL.md` are installed and refreshed beside
  this file and marked *for humans*: explanation, not rules, which an agent
  skips in ordinary work; *How To Read This Document* says when it returns.
  The model is published as work in progress and says so. No migration.
- **Information model.** `INFORMATION-MODEL.md`, installed beside this
  file, names every kind of thing the workflow stores, its home, its controlled fields, what it may point at,
  and how a thing moves between kinds; *Bug Or Feature* is the test by
  field, and the *Glossary* gains **backlog entry** and **work order**.
  Migration: a bug record that violates no requirement and no promised
  behavior is retired with that reason and reopened as a backlog entry at
  the next triage; nothing else changes shape.
- **Validation commands are required, and the brief prints them.** *The
  Project's Local Workflow* makes the local file's *Validation commands*
  section required: the environment and the commands, runnable as written;
  *Agent Reporting Contract* forbids reporting a check as not runnable
  without having followed it; `workflow brief` prints the section at
  session start. Migration: a local file whose section only points
  elsewhere states the environment inline.
- **Validation vocabulary and the checkpoint that keeps it true.** The
  *Glossary* names the validation kinds, environment, unit, integration,
  end-to-end, smoke, gate, candidate gate, acceptance evidence, the same in
  every ecosystem; `INFORMATION-MODEL.md` says they are declared in the local
  file's *Validation commands*, `none` allowed with a reason; *Checkpoint
  Triggers* gains the change of how the software is built, tested, started
  or smoke-tested; the local file template carries the structure and the
  obligation. Migration: a project fills the kinds it has at its next
  checkpoint.
- **Integration is a merge commit.** *Development And Checkpoints*: one
  merge commit per reviewed deliverable, never fast-forward, never squash;
  `main` is read by first parent; pushed history is never rewritten.
  *Successful Completion* follows in both delivery paths, and *Staying
  Current With `main`* no longer assumes a configurable strategy. A project
  that prefers squash records the exception in its local file with the
  consequence for cited commits. Migration: set the hosting platform's merge
  method to merge commits; nothing already on `main` changes.

#### 0.2.14

Stamped 2026-09-18 by the product owner, ahead of the release that ships it.
There is no 0.2.13. Rules changed since 0.2.12:

- **Reference vocabulary.** *Vocabulary* adopts the Workflow Patterns base
  terms. No migration.
- **Releases.** *Releases* defines release refs and how a workstream takes a
  release over. The product owner may set the version at any point in the
  cycle; the release branch's first commit confirms it rather than owning it.
  No migration for existing refs; the next release follows *Taking A Release
  Over*.
- **The reserved `maintenance` workstream, and bug frontmatter.** *The
  Reserved `maintenance` Workstream* and *Bug Intake*. Migration: create the
  reserved workstream under its adoption exception, and add the controlled
  frontmatter to every bug record; a definition refresh does the first and
  the bug template shows the second.
- **The integration branch may be renamed locally.** `main` in this document
  means the project's integration branch; a project whose branch has another
  name says so under *Integration Branch* in `WORKFLOW-LOCAL.md`. No
  migration.
- **The `ws-` branch form.** *Checkouts, Branches, And Workstreams* and
  restrictions 4, 5, and 13: new workstream branches are
  `ws-<name>/<sub>`, and the workflow claims no other ref. No migration
  is required: a workstream branch under an older name stays that
  workstream's through its workstream-list row. A project that chooses to rename
  does so one workstream at a time, each on its own working branch, and may
  record its schedule under *Exceptions* in `WORKFLOW-LOCAL.md`.
- **The workflow declaration.** *Workflow Declaration*: the `[workflow]`
  table names the definition, its version, and the mode; the frontmatter of
  this file carries the same version. Migration: add the table; a definition
  refresh writes it.
- **The open-work directory has a fixed shape.** *The Open-Work Directory*:
  a bounded status file that sheds history into dated records, dated
  documents by kind, and an index that says when to open each. No
  migration: existing documents keep their names; new ones follow the form.
- **A misplaced change travels as a patch.** *Publishing Before
  Integration*: work found to belong to another workstream is sent to it as
  a diff in an ordinary intake item and reverted from the sender's checkout,
  never committed on the wrong branch; the recipient owns application and
  integration. No migration.
- **Claims and the brief.** *The Coordination Branch*: `workflow claim`
  says who is on what, shown live and expiring, never refusing; `workflow
  brief` prints the session's context in one command; `status` shows when
  each workstream last published. *Resuming* ends with a claim and
  *Pausing* with its release. No migration.
- **The session-start synchronization judgment.** *Resuming* step 2 and
  *Staying Current With `main`*: the agent proposes whether to synchronize,
  from facts the tool reports, and a changed definition or local workflow
  file is a must. `publish` stamps what was read; `list` shows commits
  behind `main` and whether the definition changed; `mail send` accepts a
  comma-separated list of recipients or `all`. No migration; the stamp
  appears at each workstream's next publish.
- **Coordination leaves `main`'s pull-request queue.** *The Coordination
  Branch*: intake items travel one shared `coordination` branch on the
  remote, sent and taken with `devcapsule workflow mail`, and are decided on
  the recipient's working branch. Each workstream's status file and decision
  log are published live to the same branch with `devcapsule workflow
  publish`, read with `devcapsule workflow status`, and reach `main` only
  inside the workstream's ordinary integration. The outbox is retired: its
  one-way flow was right, and it put the buffer under the wrong owner and
  the records behind a pull request nobody reviewed. A workstream edits only
  its own row in the workstream list. Migration: an outbox send in flight is
  folded into its sender's working branch or discarded once its content is
  there; every open workstream publishes once; outbox branches are deleted.
- **The information model.** *Glossary*: every term with a fixed meaning is
  defined once, in plain words, with what it must not be confused with. Six
  terms are renamed in prose and the old names remain understood as synonyms
  for one release: workstream name (was mnemonic), decision and decision log
  (was disposition), status file (was handoff), workstream list (was
  registry), judgment where this document is silent (was latitude), and
  finishing (was finalization). File and directory names do not change:
  `intake-dispositions.md`, `engineering-docs/wip/`, and the decision log's
  `Dispositioned` column keep their names. Milestone and stage become optional
  planning words that no rule depends on. Requirements and backlog items get
  one priority scale, `gating`, `wanted`, `optional`, `later`, replacing
  `MVP`, `current stabilization`, and `later`. No migration for adopters; a
  project's requirement records may keep the old priority values until it
  chooses to map them.
- **The project's local workflow.** *The Project's Local Workflow*:
  `WORKFLOW-LOCAL.md` holds what only one project can decide, permissively,
  with recommended headings. *Releases* now states the development-version
  rule generically and delegates its spelling there. Migration: create the
  file from the template; bootstrap does so where it is missing.

#### 0.2.12 and earlier

Unversioned. The definition shipped in each release is readable at that
release's tag.

## Information Model

The kinds of thing this workflow stores, their homes and controlled fields,
how a thing moves between kinds, the test that tells a bug from a feature,
and where the validation kinds are declared, are in `INFORMATION-MODEL.md`
beside this file, marked *for humans*, installed and refreshed with this
document. The rules here assume it and do not repeat it.

## Checkouts, Branches, And Workstreams

Work means editing files in a **checkout**. Everything this document describes
happens either in a checkout or in the shared remote that checkouts push to.
These terms are used precisely and never interchangeably.

- **Project** — the repository and its history.
- **Remote** — the shared hosted copy, such as a GitHub repository. It is the
  coordination point: where branches meet, where `main` is authoritative, and
  where pull requests and review happen.
- **Checkout** — one local clone directory. Where a pair actually edits files.
- **Branch** — a line of development within the project.
- **Workstream** — a named, registered effort with its own goal and status file.
  A `multiple-streams` concept only; `single-stream` projects have branches and
  no workstreams.
- **Pair** — one human and one agent working together in one checkout.

The relationships, which fix what every "current" in this document means:

- A project has one authoritative remote and any number of checkouts.
- A checkout has exactly one current branch.
- Every `ws-` branch belongs to exactly one workstream. Release refs belong
  to none. Any other ref is outside the workflow; see below.
- A workstream may own several branches.
- A checkout therefore has at most one selected workstream at any moment. The
  *current branch* determines the *current workstream*, not the reverse.

**The workflow claims only the refs it names.** Three kinds, recognizable by
name alone:

- `main`, the integration branch. A project whose integration branch has
  another name, such as `master` or `trunk`, says so under *Integration
  Branch* in `WORKFLOW-LOCAL.md`, and every `main` in this document then
  means that branch;
- `ws-<name>/<sub>`, a workstream branch. `ws` is short for workstream, and
  `<sub>` is the workstream's own choice;
- `release-<version>`, a release branch, with its `v<version>` tags; see
  *Releases*. A project may spell these differently in `WORKFLOW-LOCAL.md`.

Every other ref belongs to the project, not to the workflow: a branch that
predates it, a tooling branch, a collaborator's own naming, an experiment. The
workflow says nothing about such refs, and an agent following it does not
create, rename, delete, rebase, or select one unless the project's local
workflow or the human directs it. A project adopting this workflow, including
an open-source project with its own conventions, keeps its namespace; only
new workstream branches take the `ws-` form. A workstream branch under an
older name is still that workstream's branch through its workstream-list row; the
name is what lets a reader tell without the workstream list, not what makes the
association true.

**Sequential within a checkout, concurrent across checkouts.** One checkout can
work on many workstreams over time by switching branches, but only one at a
time, and only from a clean tree — mixing two workstreams' uncommitted changes
in one directory is what the protocol exists to prevent. Genuine concurrency
comes from several pairs working in several checkouts, integrating through the
remote. It does not come from any local arrangement of directories.

**What is shared and what is local.** The remote carries everything the project
agrees on: branches, `main`, the workstream list, status files, and intake. A checkout
carries only local facts: which one it is, what branch it is on, and what is
uncommitted in it. Nothing about a checkout is registered or coordinated.

This is why two pairs can hold different current workstreams at the same moment
without either being wrong, and why the workstream list is a record rather than a
presence or locking system. A workstream listed as active means someone opened
it and has not concluded it — not that anyone is working on it right now.

**Two pairs may select the same workstream.** Nothing prevents it and no lock
exists. They will contend on one status file, which is a single file both are
expected to keep current, so coordinate outside the protocol before doing it
deliberately. If it happens by accident, the usual result is a conflict in that
status file rather than lost work.

## Where This Document Is Silent

This workflow is incomplete, and for V1 the project says so rather than
pretending otherwise. It was written from real use, and real use keeps
producing situations it does not describe. Adopters should expect to meet them.

**The principle: what this document does not expressly deny is allowed.** A
human/agent pair that reaches a situation the protocol does not cover resolves
it with judgment and keeps working. Being stopped by silence is itself a
failure — the protocol exists to make work possible and legible, not to
authorize each step of it.

**Silence is not the same as a rule you dislike.** Before invoking this,
establish that the protocol is actually silent. A rule that is inconvenient,
costly, or arrived at for reasons no longer visible is still a rule; change it
through the workflow-owning workstream rather than around it.

**Express denials are not silence.** This principle never overrides an
instruction to stop, ask, refrain, or seek authority. Those are decisions
already made, usually because the failure they prevent is expensive or
irreversible. In this document they include, and are not limited to: never
force-pushing `main`; stopping before editing when branch and workstream list
disagree; not inferring permission to update `main` from the mere ability to do
so; the carve-outs in restriction 11; and every explicit instruction to ask the
human. Where such a rule applies, follow it and raise the difficulty.

**Ambiguity and contradiction are defects, not silence.** If two rules conflict,
or one admits several readings that lead to materially different work, that is a
flaw in this document. Choose the reading that best serves the evident intent,
say which reading you chose, and report the defect. Do not treat a contradiction
as permission to pick whichever side is convenient.

**Exercised judgment must be recorded.** This is the obligation that makes the
permission safe. When a pair resolves something the protocol does not cover,
record in the selected status file what was missing, what was done, and why. If the
gap would recur in any project rather than only this one, deliver it to the
workstream that owns the workflow, by mail. Unrecorded
judgment means the gap stays invisible, the next pair re-derives it differently,
and two projects using "the same" workflow quietly diverge. Recorded judgment is
how the next version of this document gets written.

**Scope.** This clause is a V1 position, adopted 2026-08-17. It reflects a
workflow young enough that its gaps outnumber the cost of specifying them in
advance. Revisit it when the gaps become rare enough that discovering one is a
surprise rather than a routine event.

## Workflow Declaration

Before interpreting project status, read the `[workflow]` table in
`.devcapsule/devcapsule.toml`:

```toml
[workflow]
definition = "devcapsule"
version = "0.2.14"
mode = "multiple-streams"
```

- `definition` names the workflow the project runs: `devcapsule` for this one,
  the name or URL of another, or `none`. The product works in every case; the
  workflow is an optional component.
- `version` is the DevCapsule release whose packaged definition the project's
  `WORKFLOW.md` was installed or refreshed from. It is the same value as the
  `version` in that file's frontmatter, and tooling keeps the two equal:
  bootstrap writes both, a refresh updates both, and a mismatch is reported as
  a defect rather than resolved by guessing. The value `unversioned` means the
  definition was installed before versions existed; refresh to adopt one.
- `mode` selects `single-stream` or `multiple-streams`. A missing table, or a
  missing `mode`, falls back to the older top-level `workflow-type` field,
  which means the same thing; a missing value means `single-stream`. Any other
  value is invalid; report it instead of guessing which status protocol
  applies. The mode selects repository workflow, not runtime behavior or live
  contributor presence.

**The declared version governs the project.** A contributor's tool may be
newer than the project's workflow, and a contributor's agent may know a newer
text. Neither changes the rules the project runs. The `WORKFLOW.md` in the
repository, at the version the declaration names, is what everyone follows,
and it changes only when the project deliberately refreshes it and performs
the migration steps in *Changes*. A tool never refreshes the definition or
changes the declared version as a side effect of another action, and a
mechanical action a tool performs on workflow state either follows the
declared version's rules or says plainly that it does not know that version.

**Why the version is the DevCapsule release.** The definition ships inside
each release, and release tags are immutable, so every version of this text is
readable for good at its tag, with no second numbering scheme to maintain. A
release that changes no rule still advances the version; *Changes* says
whether anything changed.

## The Project's Local Workflow

This document is the generic half of a project's workflow: installed by the
tooling, versioned, and the same in every project that runs it, which is what
lets a contributor rely on it. The other half is the project's own, in
`WORKFLOW-LOCAL.md` beside this file: the rules that only make sense for one
project, because they depend on its ecosystem, its hosting, or its history.

**What each file governs.** This document binds wherever it speaks. Where it
is silent, the local file may say whatever the project needs, and that is the
ordinary way to fill the silence rather than an exception to it; *Judgment
Where This Document Is Silent* applies unchanged. A local rule that
contradicts a rule here is not an override. It is recorded under the local
file's *Exceptions* heading with its reason, so the contradiction is visible
and reportable, and it is the signal that this document should have been
silent there.

**What the local file usually settles.** Recommended, not required. The
template a fresh project receives carries these headings with the question
each answers:

- **Integration branch.** Only when it is not `main`. This document says
  `main` throughout and means the project's integration branch, whatever it
  is called; the local file is where a project says it is called something
  else.
- **Version scheme.** How the source names itself between releases and at a
  release, and the command that sets it. A Python project says `0.2.14.dev0`
  and then `0.2.14`; a Maven project says `0.2.14-SNAPSHOT`; each ecosystem
  has its own, and *Releases* only requires that the marker exists and orders
  before the release.
- **Release policy.** Ref spelling if it differs from the default, how a
  candidate is built and published, what the candidate gate checks, what
  acceptance evidence is required, and where the acceptance record lives.
- **Validation commands.** The one heading that is required, not
  recommended: how to obtain the environment the project's ecosystem needs,
  the interpreter, the virtual environment or the build tool, and the
  commands a pair runs before a checkpoint and before integration, each
  runnable as written from a named directory. The section is what lets any
  agent on any project build the software and run its tests without
  guessing; `workflow brief` prints it at session start. An agent that
  cannot run a check follows this section first. "The tool is missing" is a
  finding only after that, reported with the step that failed.
- **Host capabilities.** What the project needs from the machine and the
  hosting service that this document cannot assume: branch permissions,
  runners, credentials, and their declared justifications.
- **Exceptions.** Every recorded departure from this document, each with its
  reason and, where one exists, the condition that ends it.

Nothing else is prescribed. A section the project does not need stays empty
or is deleted. A section the project needs and the template did not foresee
is added.

**Ownership.** The local file is project state. Bootstrap renders it once
from the template and never touches it again; a definition refresh replaces
this document only. Agents read this document first and the local file
second, and treat both as binding in their own territory.

## Single-Stream Workflow

`single-stream` preserves the existing linear process:

- root `CURRENT-STATUS.md` is the detailed active status file;
- it records current state, evidence, and one next resumable slice;
- routine checkpoints update that file; and
- branches remain the unit of work, and how many checkouts exist locally is
  an implementation detail.

The remaining general sections of this document apply as they did before
multiple-stream support was introduced.

## Multiple-Stream Workflow

### Definition And Restrictions

A workstream is a bounded set of changes developed toward one goal. It begins,
develops, and ends successfully or unsuccessfully. Two exceptions exist: the
reserved `project-management` and `maintenance` workstreams, which every
multiple-stream project has and which stay open for as long as the project
uses that mode. See *The Reserved `project-management` Workstream* and *The
Reserved `maintenance` Workstream*.

The following restrictions keep concurrent work understandable:

1. Workstreams are flat. Do not create parent, child, or nested workstreams.
2. Every workstream has one unique lowercase name made from letters,
   numbers, and hyphens. Never reuse an archived name.
3. Every workstream has one immutable ISO start date: the calendar date on
   which its registration is first committed to `main`. Migration exceptions
   record their historically established start date.
4. Every `ws-` branch belongs to exactly one workstream. Release refs belong
   to none. A ref the workflow does not name is the project's, as *Checkouts,
   Branches, And Workstreams* says, and agents leave it alone.
5. Each workstream branch name begins with `ws-<name>/`. A release branch
   does not, because it is not a workstream branch; see *Releases*.
6. A workstream may have more than one branch, but every branch starts from
   `main` and is intended to return to `main` if the workstream succeeds. A
   release branch is not a workstream branch: it starts from `main` or from a
   prior release tag, merges to `main` before every candidate, and is never
   deleted; see *Releases*.
7. `main` belongs to no workstream. It is the shared registration, visibility,
   finishing, and integration branch.
8. Ordinary workstream implementation does not happen directly on `main`.
9. Each open workstream has exactly one detailed status file at
   `engineering-docs/wip/<start-date>-<name>/CURRENT-STATUS.md`.
10. Root `CURRENT-STATUS.md` on `main` lists open workstreams only. An open
   workstream remains listed while active, paused, blocked, or integrating.
11. No workstream holds exclusive editing rights over a file. A workstream may
    edit any file its task genuinely requires, and exclusivity may not be
    inferred from a file's subject, its directory, or which workstream created
    it. Three carve-outs stand: another workstream's open-work directory
    excluding its `intake/` subdirectory, another workstream's row in the
    workstream list, and uncommitted recovery state in another checkout.
    Each is a workstream's account of its own state, which another workstream
    cannot restate accurately; report what you observe about another workstream
    instead of editing its record. Delivering work to another workstream is a
    different act from restating its state, and belongs in its `intake/`; see
    *Workstream Intake*. Wider
    exclusivity applies only where a documented locking protocol exists and is
    actually used for that file. No such protocol exists today.
12. `project-management` and `maintenance` are reserved names. Exactly one
    workstream in the project carries each, no ordinary workstream may take
    either, and neither is archived and recreated while the project stays in
    `multiple-streams` mode.
13. A workstream's records travel its working branch and are published live
    to the coordination branch. No branch exists to carry records alone, and
    nothing is merged to `main` for a record's sake. See *The Coordination
    Branch* and *Publishing Before Integration*.

### Initializing Multiple-Stream Mode

Selecting `multiple-streams` is an act with required structure, whether it
happens when a project is first set up or when an existing single-stream
project adopts the mode later. Both paths produce the same starting shape.

In one commit on `main`:

1. Set `mode = "multiple-streams"` in the `[workflow]` table of
   `.devcapsule/devcapsule.toml`.
2. Convert root `CURRENT-STATUS.md` from a detailed status file into the compact
   workstream list. Detailed state carried over from single-stream
   mode moves into a workstream status file rather than staying at the root.
3. Create the reserved `project-management` and `maintenance` workstreams by
   the procedure in *Beginning A Workstream*, using the initialization date as
   their immutable ISO start date, and register both in the new workstream list.
4. Create `engineering-docs/wip/` and `engineering-docs/archive/`.

A multiple-stream project missing either reserved workstream is incompletely
initialized. Report that rather than working around it.

Initialization creates exactly two workstreams, both reserved. Ordinary
workstreams begin afterwards, separately, and only when there is real work for
them.

### The Reserved `project-management` Workstream

Coordinating a portfolio of workstreams is itself continuing work, and it
belongs to no single bounded effort. Without a reserved home, it either lands
in whichever workstream happens to be selected — distorting that workstream's
scope and its record — or it survives only in conversation. The reserved
workstream gives it a durable owner.

**Scope.** It owns project-wide priorities, sequencing, cross-workstream
dependencies, portfolio-level checkpoints, lifecycle decisions about opening,
pausing, resuming, blocking, and concluding other workstreams, and routing work
that has no owning workstream yet.

Three exclusions keep it from absorbing the project:

- It is not a second workstream list. Root `CURRENT-STATUS.md` on `main` remains the
  single authoritative list of open workstreams. `project-management` records
  reasoning, sequencing, and dependencies, not a parallel copy of the roster.
- It is not an implementation catch-all. Work that fits an open workstream's
  goal belongs to that workstream. Work that fits none is a reason to begin a
  workstream, which is a `project-management` decision to make and hand over,
  not work for it to perform.
- It does not own other workstreams' state. Restriction 11's carve-out binds it
  like anyone else: it reports what it observes about another workstream and
  delivers to that workstream's `intake/`; it does not edit that workstream's
  status file.

Its coordination authority is advisory and recorded, not procedural. It does
not gate other workstreams' commits, integrations, or checkpoints.

**Lifecycle.** It is permanent for the lifetime of `multiple-streams` mode
rather than open-ended by neglect. Restriction 12 reserves its name;
initialization creates it; it has no completion criteria and is never listed as
active-with-a-final-goal. Its workstream-list state reads `active; permanent
coordination`, and paused or blocked are as legitimate for it as for any other
workstream — a project can go a long time with nothing to coordinate.

**Branches, selection, and integration are ordinary.** Its branches are
`ws-project-management/<topic>`, forked from `main`, returning to `main` by the
repository's default delivery method. `ws-project-management/coordination` is the
conventional first branch. Checkout selection, intake, checkpoints, commit
cadence, and integration follow the same rules as any other workstream. Only
its lifecycle is special.

**Retirement.** It ends only when the project leaves `multiple-streams` mode,
never as an ordinary conclusion. Migrating to `single-stream`, in one commit on
`main`:

1. Confirm no ordinary workstream is still open. Migrating with open
   workstreams silently orphans their status files; conclude or archive them first.
   Its own intake and `maintenance`'s must be empty as well, and its own is the
   last queue that can be emptied: once it is gone there is nowhere left to
   forward anything.
2. Fold the coordination state that remains useful into root
   `CURRENT-STATUS.md`, which becomes the detailed single-stream status file again.
3. Move `engineering-docs/wip/<start-date>-project-management/` and
   `engineering-docs/wip/<start-date>-maintenance/` to the matching
   `engineering-docs/archive/` directories unchanged, and record the
   migration, its date, and the resulting mode in each final status.
4. Set `mode = "single-stream"` in the `[workflow]` table.

**Adoption exception.** A project adopting `multiple-streams` that already has
a branch, directory, or bounded workstream named `project-management` records a
migration exception in the reserved workstream's status file, in the same form as
any other adoption exception, rather than renaming history.

### The Reserved `maintenance` Workstream

Software has defects, and a defect found against `main` or against a released
version needs an owner from the moment it is recorded. Without a reserved home,
a bug either waits for a feature workstream that happens to be open on its
subject, and there may be none, or it is filed and nobody is committed to it.
The workstream list cannot show commitment to a bug that nobody owns. The reserved
`maintenance` workstream is that commitment: the permanent owner of last
resort for defects, and the driver of maintenance releases.

**Scope.** It owns the bug records under `engineering-docs/bugs/` whose
`owner` field names it: triaging them, fixing them on `main`, and fixing them
on maintained release lines. It drives maintenance releases of already released
versions under *Releases*. It keeps the bug queue honest: every open bug
carries a controlled status and a severity, and an untriaged one is its work
to triage. See *Bug Intake* for the fields.

Three exclusions keep it from becoming the place work goes to wait:

- It is not a catch-all for defects. A bug inside an open workstream's subject
  is owned and fixed by that workstream, at the source. `maintenance` owns a
  bug when no open workstream's goal covers it, or when the owning workstream
  hands it over with a recorded reason, for example because it is closing or
  its scope is frozen.
- It is not a feature workstream. Work that changes what the product does,
  rather than making it do what it already claims, is a reason to begin an
  ordinary workstream, which is `project-management`'s decision. A fix that
  grows into a feature is handed over, not finished quietly.
- It is not a second bug tracker. The bug records are the durable evidence and
  the queue; its status file holds only what is being fixed now and what is next.
  History goes to the bug record and, on closure, to
  `engineering-docs/completed-tasks/`, never to the status file.

**Its queue is read from `main`**, not from its status file: the bug records whose
`owner` is `maintenance` and whose `status` is neither `closed` nor `retired`.
A pair selecting it lists those at session start, the way any workstream reads
its intake.

**Load is balanced by branches and pairs, not by more workstreams.** Its
branches are `ws-maintenance/<bug-or-release-line>`, one per fix or per
maintained release line, and several pairs may work it at once, as *Two pairs
may select the same workstream* allows. A defect cluster large enough to have
its own goal and its own end is an ordinary bounded workstream, not a second
permanent one.

**Lifecycle.** Permanent for the lifetime of `multiple-streams` mode, like
`project-management`: restriction 12 reserves its name, initialization
creates it, it has no completion criteria, and its workstream-list state reads
`active; permanent maintenance`. Paused is legitimate when its queue is
empty; blocked is legitimate when every open bug it owns waits on something
external.

**Branches, selection, and integration are ordinary**, exactly as for
`project-management`. Only its lifecycle and its default ownership of bugs
are special.

**Retirement.** Together with `project-management`, on migration to
`single-stream`, by the procedure above; its intake must be empty like the
other. Its open bug records stay where they are and their `owner` becomes
`none`, since a single-stream project has no workstreams.

**Adoption exception.** A project that adopted `multiple-streams` before this
workstream existed creates it when it adopts this rule, with that date as the
immutable start date, and records in the new status file that the start date is
later than the mode's initialization.

### Beginning A Workstream

Begin from a clean, current `main` checkout:

1. Choose the goal, unused name, and ISO start date.
2. Create
   `engineering-docs/wip/<start-date>-<name>/CURRENT-STATUS.md` on `main`.
3. Record the start date, goal, state, branch prefix, target branch,
   delivery method or applicable repository default, current task, and next
   resumable task.
4. Create `engineering-docs/wip/<start-date>-<name>/intake/README.md` so the
   workstream can receive work from others, and an empty
   `intake-dispositions.md` beside it so the two halves of the record exist
   from the start; see *Workstream Intake* and *The Decision Log*.
5. Add the workstream to root `CURRENT-STATUS.md`.
6. Commit that registration on the workstream's first `ws-<name>/...`
   branch, forked from `main`, and publish it: `devcapsule workflow publish`
   puts the status file on the coordination branch, which is where every
   checkout reads the live list, so the workstream exists for everyone at
   once. The registration reaches `main` inside the workstream's first
   integration. At initialization, when no working branch exists yet, the
   initializing commit on `main` carries it.
7. Perform workstream changes only on the workstream's branch or branches.

A branch created before the registration commit is not a valid new workstream
branch. Existing branches that predate adoption require an explicit migration
exception in their workstream status. An inactive legacy branch does not become
an open workstream merely because the ref still exists; register and associate
its continuation on `main` before committing new work to it.

### The Open-Work Directory

`engineering-docs/wip/<start-date>-<name>/` is everything a workstream keeps
while it runs. Its contents are fixed in kind, so that a reader knows what to
open and an agent knows what not to load:

- **`CURRENT-STATUS.md`, the status file.** Bounded: what the workstream is,
  its state and branch, what it is doing now, what is next, its open threads,
  and an index of the directory's other documents. It is read in full at
  every session start, so it stays short, roughly what a person reads in ten
  minutes. Anything that has stopped changing leaves it.
- **`intake/` and `intake-dispositions.md`**, the queue and the decision log.
- **Dated documents**, `YYYY-MM-DD-<kind>-<slug>.md`, one per topic, opened
  only when the task needs them. The kinds are **design**, a design
  discussion or spike; **note**, evidence or analysis; and **record**, history
  shed from the status file, a checkpoint, or a custody record. A project may
  add kinds in its local workflow file. A living document with no date, such
  as a backlog or a ledger, is allowed and is named for what it is.
- Nothing else. Deliverable content never lives here; see *Publishing Before
  Integration*.

**The status file sheds history.** At each pause, and whenever a task's
narrative is finished, its account moves verbatim into a dated record and the
status file keeps one line pointing at it. What the status file says about the
past is where to look, not what happened.

**Every document is listed once, with when to open it**, in the status file's
document index. The index is how a reader decides what to load; the documents
are how a workstream's size stays out of every session's context. At
conclusion the directory moves to `engineering-docs/archive/` unchanged.

### Selecting Work At Session Start

Workstream discovery and checkout selection are related but distinct:

- The live workstream list is read from the coordination branch,
  `devcapsule workflow status`, which shows every open workstream's published
  state, branch, and next step as of its last publish. The table in root
  `CURRENT-STATUS.md` on the locally accepted mainline ref is the record as
  of each workstream's last integration and the fallback when the remote
  cannot be reached; a long-lived workstream branch's copy of it is never
  consulted. If mainline candidates have diverged, do not choose silently;
  resolve the divergence under *Verifying Shared Branch State*.
- The current checkout and its branch provide the persistent local
  selection. This first protocol deliberately defines no second untracked
  "current workstream" preference file.

Select exactly one editing workstream for the current checkout:

1. Identify the current checkout, its branch, and its dirty state, then read
   the live workstream list from the coordination branch, falling back to
   the mainline ref's table when offline.
2. If the user explicitly names an open workstream, select it. Explicit intent
   chooses the target but does not reassign the current branch or authorize
   mixing dirty state.
3. Otherwise, when the current branch starts with `ws-<name>/`, select the one
   open workstream-list entry with that name. A documented adoption exception may
   provide the same unique association for a historical branch.
4. Treat a name-prefixed or excepted branch whose workstream is absent from
   the open workstream list, or whose workstream-list association disagrees, as invalid
   routing. Stop before editing and report the inconsistency.
5. `main` belongs to no workstream and therefore has no default editing
   workstream. Workstream list coordination and repository-wide inspection may occur
   there. Workstream changes require an explicit selection followed by a switch
   to that workstream's branch in a clean checkout.
6. The coordination branch is never checked out for work. It is read and
   written through the tool or through plumbing from whatever branch the
   checkout is on; a checkout found on it is on no workstream. Switch to a
   working branch first, and treat uncommitted changes found there as
   recovery material that belongs elsewhere.
7. Detached HEAD, an unregistered branch, or more than one plausible mapping
   has no default. Ask the user only when the desired workstream cannot be
   established from explicit intent and a unique registered association.
8. Follow the selected workstream-list row's status file link. Do not guess its start date
   from branch or commit timestamps. On the selected workstream branch, its
   committed status file is authoritative for the latest track-local state; the
   copy reachable from `main` is the latest published snapshot.
9. Read the selected workstream's `intake/` directory from the locally accepted
   mainline ref before planning the session. Items there are work other
   workstreams have delivered and this workstream has not yet decided;
   see *Workstream Intake*. A status file read without its intake is an incomplete
   picture of what the workstream owns.

If the selected workstream differs from the current branch, switch to that
branch in a clean checkout before editing. Do not combine dirty state from two
workstreams, and do not use a stash as their durable status file boundary.
Different users and clones may select different workstreams independently
because their checked-out branches are local state.

**Local checkout arrangement is an implementation detail.** This protocol is
defined in terms of branches, not directories. One checkout has one branch and
therefore at most one selected workstream; that is the whole rule. How many
checkouts exist on a machine, and whether an extra one is a second clone, a Git
worktree, or a container, is the developer's choice. None of it is workflow
state: nothing about it is registered, recorded, or coordinated, and where
several exist each obeys the selection rules on its own.

Checkouts made for other purposes — running the product against itself,
reproducing a bug, testing a build — are not workstream checkouts and this
document does not govern them.

### Workstream Intake

Every workstream directory carries an `intake/` subdirectory. It is the only
place another workstream may write inside a workstream's open-work directory, and it
exists because a protocol that forbids all such writing has no way to hand work
over. Announcing a status file in the sender's own checkpoint does not deliver it:
the recipient reads its own status file at session start, so an item recorded
anywhere else is invisible to the workstream expected to do it.

**Writing an item.** Any workstream, or the user, may add a file. One item per
file, named `YYYY-MM-DD-<sender-name>-<slug>.md`, where the date is the
delivery date. The file states what is being handed over, why it belongs to the
recipient rather than the sender, the evidence or documents behind it, and what
accepting it would mean. The sender does not assign priority, sequence, or a
release target; those are the receiving workstream's judgment.

**Delivery must reach `main` promptly.** An intake file that waits for the
sender's own integration is invisible for as long as that takes, which
reproduces the failure this mechanism exists to fix. Deliver it by mail, on
the coordination branch, separately from the sender's ordinary work and
without waiting for anyone's integration. See *The Coordination Branch*.

**Ownership is asymmetric.** A sender adds files, and only adds: sent mail is
append-only, so a correction is a new item under a new name that says what it
supersedes. A sender never edits, removes, or reclassifies anything in the
recipient's mailbox or intake. Only the receiving workstream removes or
reclassifies items in its own intake. Its account of itself remains
exclusively its own.

**Decision has exactly two outcomes: acknowledge or forward.** Every item
ends in one of them, and no item may be left alone indefinitely; see *Intake
Gates Completion*.

Scheduling is not a third outcome. An item accepted but not scheduled yet is
acknowledged, with its position recorded. "Later" is a property of work a
workstream owns, not a way to avoid owning it.

**Acknowledge** means the workstream takes the item as its own responsibility
and turns it into work it will actually do. Recording an opinion about an item
is not acknowledging it; converting it into a requirement, backlog entry, task,
or next step is.

1. On the working branch, record it in the status file as a requirement or task,
   with the reasoning that led to accepting it, and place it in the
   workstream's order of work.
2. In one commit on the working branch, add an entry to the decision log and
   delete the intake file.

**Forward** means the workstream is not the right owner. Legitimate reasons
include: the item is not a well-formed requirement; it will not be fixed; it
belongs to a different workstream; it belongs to a later release; or it is out
of this workstream's registered scope. The workstream states the reason but
does not choose a new owner — routing is `project-management`'s decision.

1. Send a new item to `project-management` by mail, following *Writing an
   item*. Include the original item's full text, or its path and the revision
   it can be recovered from, together with the reason for refusing it.
2. In one commit on the working branch, add an entry to the decision log
   naming where the item went, and delete the original item.
3. Record in the status file what was forwarded and why, so the decision is not
   silently reopened later.

**Taking is prompt, deciding is a working-branch commit.** The mailbox is read
from the remote at every session start, so an item still there has not been
taken. Once taken, the item lives in the recipient's `intake/` on its working
branch until the commit that decides it, and reaches `main`, decided, with
that branch's integration. Nobody but the recipient ever writes in its
`intake/`, so that commit never conflicts.

Intake is a queue, not an archive. Git retains every item and every reason.

### The Decision Log

Each workstream keeps one append-only log at
`engineering-docs/wip/<start-date>-<name>/intake-dispositions.md`, recording
what became of every item it received. It is written by the receiving
workstream only, in the same commit that removes the item from the queue, and
published live with the status file; it reaches `main` inside the
workstream's ordinary integration.

**The invariant that makes it useful.** Across the coordination branch and
the recipient's branch, every item ever sent to a workstream is in exactly
one of three places: its mailbox, meaning in flight; its `intake/`, meaning
taken and not yet decided; or its decision log, meaning decided. Never two,
never none. Taking moves an item from the first place to the second in one
operation, and deciding moves it from the second to the third in one commit,
which is why each is one step and not two.

This is the acknowledgement path. A sender does not need to be told what
happened to what it delivered; it looks in three predictable places, the
mailbox, the recipient's intake, and its published decision log, all live on
the coordination branch or the recipient's branch. It is also why no reply is written back into the sender's
intake: a reply is not work, and a queue whose whole meaning is "own this or
forward it" should not carry messages that are neither.

**One entry per item**, appended, newest last, never edited or removed:

| Item | Dispositioned | Outcome | Note |
|---|---|---|---|
| `2026-08-16-sender-some-slug.md` | 2026-08-16 | acknowledged | One line. Full reasoning in the status file. |
| `2026-08-16-sender-other-slug.md` | 2026-08-17 | forwarded | Where it went, so the trail can be followed. |

The note is one line. The reasoning belongs in the status file, which is where a
decision is argued; the log records that it happened and points at it.

**The log is an archive, not a queue.** Unlike `intake/`, it is never pruned,
and it travels with the workstream into `engineering-docs/archive/` at the end.
A concluded workstream's log is the record of what it was asked to do and what
it decided, which is exactly what a later reader reopening one of those
decisions needs.

Because the log is a workstream's account of its own decisions, restriction 11
applies: only the receiving workstream writes it. Anyone may read it, and
reading it is the intended use.

**Items from `project-management` are not forwardable.** That workstream is
authoritative for structuring work — what is worked on, by whom, in what order
— so an item it sends is a routing decision, not a proposal, and forwarding it
back would be a loop. Acknowledge it.

A recipient that believes such an item is genuinely wrong — impossible,
misrouted, or in conflict with its registered scope — raises that with the
human rather than returning it through intake. Until the routing decision
changes, the item stands.

**`project-management`'s own decisions are terminal.** It has nowhere to
forward to, so an item reaching it ends there in one of three ways: assigned to
a workstream by delivering it onward, made the reason to begin a new
workstream, or dropped with recorded reasoning. This is what stops a refused
item from circulating indefinitely.

**Intake gates completion.** A workstream is not complete, successfully or
unsuccessfully, while any item remains in its intake on `main`. An empty intake
is a precondition of concluding, checked as part of the completion sequence.
A workstream ending unsuccessfully still owes its queue a decision: items it
will not do are forwarded to `project-management`, not abandoned with the
workstream. Leaving items behind would silently destroy work other workstreams
handed over in good faith.

**Presence.** The directory carries a `README.md` so that an empty intake is
unambiguous rather than an untracked absence. Intake items are not listed in
`index.md` or in the workstream's own document index; the directory listing is
the queue, and indexing it would create churn for items designed to be
short-lived. The decision log is the opposite case: it is durable, so it
belongs in the workstream's own document index, though not in `index.md`, which
lists workstream status files rather than their internal documents.

### The Coordination Branch

Intake defines where an item lands. The coordination branch is how it
travels. It exists so that a message between workstreams never needs `main`:
no agent commits to `main` for mail, no human opens a pull request whose only
content is somebody's records, and nothing waits for `main` to move.

**One branch, `coordination`, on the remote, never merged into `main`.** It
carries mail, under `mail/<recipient>/<item>.md`, and published state, under
`state/<name>/`, plus a README. Nobody resets or force-pushes it; every
change is an ordinary commit on top. For mail its history is append-only:

- **Senders add.** To deliver an item, add one file under
  `mail/<recipient>/` and push. A sender never edits, renames, or removes a
  file, its own included; an item that needs correcting is sent again under
  a new name.
- **Only the recipient removes, and only after taking.** At session start the
  recipient copies every file addressed to it into its `intake/` on its
  working branch, stages them, and only then removes them from the branch in
  one commit. The party that empties the mailbox is the party that has
  provably received its contents.
- **Nobody resets or force-pushes.** A push that loses a race is retried from
  a fresh fetch. Racing commits touch different files, so the retry never
  conflicts. The host should forbid force-pushes to this one branch; the
  workflow forbids them regardless.

**The tool, and the plain-git equivalent.** `devcapsule workflow mail send
<recipient> <file>`, `check`, and `take` do all of the above through git
plumbing, without switching branches or touching the working tree beyond
writing taken items into `intake/`. `check` and `take` infer the workstream
from a `ws-<name>/...` branch. Without the tool: `git fetch origin
coordination`, `git show origin/coordination:mail/<name>/` to see, and a
commit on that branch adding or removing files to send or take; the rules
above are the same.

**Session start includes the mailbox.** Before selecting work, and again
before pausing, take your mail. A taken item is committed on the working
branch promptly, so that the item is either in the mailbox or in the intake,
never in a checkout alone. Mail is read from the remote, so a checkout that
cannot reach it reads what it last fetched, the same as it does toward
`main`.

**Where an item is, at every moment.** Across the coordination branch and the
recipient's working branch, every item ever sent is in exactly one of three
places: the mailbox, meaning in flight; the recipient's `intake/`, meaning
taken and not yet decided; or its decision log, meaning decided. Never two,
never none. `main` sees an item only when the recipient's working branch
integrates, at which point the item is already in the log or, rarely, still
in the intake; either way nobody else touches that directory, so it merges
without conflict.

**Published state is the live view of every workstream.** `devcapsule
workflow publish` pushes the working tree's current status file and decision
log to `state/<name>/`, without a branch switch, replacing what was there.
`devcapsule workflow status` renders every open workstream's state, branch,
and next step from it. Publish at each checkpoint, before pausing, and at
finish; `publish --retire` removes the directory when the workstream
concludes. What is published is what the pair is looking at, committed or
not, so the live view is never behind the checkout.

**Which copy is authoritative.** While a workstream is open, its published
state is the truth for routing, selection, and resumption, and agents read it
first. The copies on `main` are the record as of the workstream's last
integration and become the permanent record when it concludes. The tool keeps
the two identical whenever it runs, so they can lag but never disagree; if
they ever do, the published copy is newer and the working branch is where to
fix it.

**Claims say who is on what, and never refuse.** `devcapsule workflow claim
"<slice>"` writes who, which branch, which slice, and an expiry, twelve hours
by default, to `state/<name>/claim`; `status` and `brief` show live claims
and mark expired ones; `claim --release` removes it, and so do pausing and
finishing. A claim is information for the other checkouts, human or agent:
a pair about to start on a claimed workstream sees it, tells its human, and
chooses to wait, take another slice, take another workstream, or proceed
knowingly. Nothing is locked, because locking source control is the failure
git exists to end; a crashed session's claim simply expires.

**The brief is the session in one command.** `devcapsule workflow brief`
prints, for the selected workstream, its row and next task, who is working
on what, its waiting mail, the titles of the *Changes* entries it has not
read since its stamp, and the synchronization facts with a suggested
verdict. It is what a session reads first, before the status file; the
judgment it suggests remains the agent's to propose and the human's to
accept.

**Records reach `main` with the deliverable, never alone.** A workstream edits
its status file, decision log, intake, and its own row in the workstream list
on its working branch, and they land on `main` inside its ordinary
integration, the pull request that exists because the deliverable is
reviewed. Nothing is ever merged for a record's sake, and no human is asked
to click for bureaucracy. See *Publishing Before Integration*.


### Publishing Before Integration

A workstream's branch holds its work until integration. Not everything on that
branch is work: some files are how the rest of the project reads the workstream
while it runs, and those are useless where nobody can see them.

**Two kinds of file, and they travel differently.**

- **The deliverable**: changes to shared documents, code, and requirements,
  what the workstream exists to produce. It travels the workstream's own
  branch and reaches `main` by repository policy, because it is reviewed as a
  whole.
- **Records**: the files that describe the workstream itself: its status file,
  its decision log, its intake directory, and its own row in the workstream
  list. Nobody reviews these; they are the project's view of a workstream in
  flight. They are edited on the working branch like everything else, made
  visible at once by publishing, and carried to `main` inside the
  deliverable's integration. No pull request ever exists for a record alone.

**Publish whenever anyone outside the branch might read the workstream.**
Three cases, each observed rather than imagined:

1. **A document refers to a per-workstream path**, as *The Decision Log*
   does. The reference resolves on the coordination branch first, where the
   live copy is, and on `main` as of the last integration.
2. **The workstream pauses or blocks.** Whoever considers resuming it reads
   its published state before checking anything out. A state frozen at the
   last integration describes a workstream that no longer exists.
3. **Another workstream needs it to act.** Anything a recipient must read
   before it can proceed is undelivered until it is published or sent.

**What is published is the branch's current copy, verbatim.** Publishing is
not an occasion to write a different version for others; the tool pushes what
the working tree holds, so the published copy and the branch's copy are
identical at every publish and the copy on `main` is one of them, older. Two
versions of one record is the failure this whole mechanism exists to avoid.

**This is not a way to integrate deliverable content early.** The test is
whether anyone would review it as part of the workstream's work. If yes, it is
deliverable, and it travels the owning workstream's branch under review. Mail
may carry a proposed patch under the recovery rule below; sending a patch is
neither applying it nor integrating anything.

**A misplaced change travels to its owner as a patch.** When a pair finds
that a bounded change it has been making belongs to another workstream, it
stops expanding that work. If the change is separable and uncommitted, the
pair sends the owning workstream an ordinary intake item carrying the diff,
its base revision, the paths affected, new files in full, the reason for the
handoff, and what validation was done or is still missing. The human may
authorize finishing the bounded change first; nothing here permits starting
another workstream's implementation on purpose.

Verify delivery before removing anything, then restore the sender's checkout
by reverting only what the delivered patch represents, preserving unrelated
work, and record the handoff in the sender's status file. Do not switch
workstreams for it, do not commit the source change on the sender's branch,
and do not rewrite shared history to manufacture a clean handoff. If the
change is already committed or cannot be separated safely, ask the human to
choose the recovery, which may be to finish on the current branch.

The recipient decides the item through ordinary intake, reviews the patch,
checks that it applies to its current branch, and owns any application,
validation, source commit, and integration. A patch is a proposal, not
evidence that the recipient accepted or shipped the change. A later patch
supersedes an earlier one by a new item that says so; sent mail stays
append-only.

**The deliverable may still land in slices.** Integrating a finished slice
through an ordinary pull request before the workstream is done is permitted
and often right: a correction other workstreams are waiting on should not sit
behind work that has months to run. The completion sequence concludes a
workstream; it is not the only moment one may deliver. The status file records
what has already landed so a later reader is not misled about what remains.

### Staying Current With `main`

Mail and live state travel the coordination branch, but everything the
project has agreed on travels `main`: the definition, the requirements, the
decisions, and every workstream's records as of its last integration. A
workstream that does not watch `main` works against a project that has
moved on.

Synchronize the working branch with `main` often — at least at every stage
boundary, before beginning a substantial slice, and before integrating — and
at every session start propose whether to synchronize now, by the judgment
in *Resuming*. Two facts feed it and the tool shows both beside every row of
the live list: how many commits behind `main` the workstream's branch is,
and whether the definition or the local workflow file on `main` differs from
what the status file says was last read. `devcapsule workflow publish`
writes that stamp, a `Definition read:` line naming the files' content ids
as of the checkout, so nobody types a hash and a rewritten history cannot
confuse it. A workstream that has never published shows no stamp, which the
list says plainly.

**Method follows publication state.** Rebasing an unpublished branch onto
`main` is clean, and it silently drops commits that already landed, which
matters in a repository whose merge strategy rewrites them. Rebasing a
published branch rewrites shared history and needs a force-push; do that only
when the branch is known to be unshared, and prefer merging `main` in
otherwise. Rebase what only you have; merge what others may have.

**After your own delivery lands, reset rather than rebase.** Under a merge
commit the branch is simply an ancestor of `main` and synchronizing is a
fast-forward. Under the squash or rebase exception, a branch whose pull
request has merged holds no content `main` lacks, but its commits have
different identities from the ones `main` now carries. Rebasing then replays commits one at a time onto a `main` that already
contains their final effect, which conflicts on intermediate states even though
the end states agree. Confirm the branch has nothing unique — comparing trees,
not commit identities, since the identities are guaranteed to differ — and hard
reset it to `main`. Rebase is for carrying unlanded work forward; it is the
wrong tool for a branch with nothing left to carry.

This rule is about keeping a workstream branch current with `main`. How work
is delivered *to* `main` is the merge-commit rule under *Development And
Checkpoints*.

**Conflicts split by kind.** Mechanical conflicts — reformatting, moved
sections, adjacent edits — are ordinary agent work; resolve them and say so.
Semantic conflicts, where two workstreams assert incompatible things, are the
user's decision. Do not let an unresolved conflict of either kind become a
reason to stop synchronizing entirely; that is how a branch drifts far enough
that the conflict becomes unaffordable.

Two practical consequences:

- A stale branch decides against stale rules. Mail arrives on the
  coordination branch whatever the branch's age, but the definition, the
  local workflow file, and the shared documents an item may ask to change
  exist at their current versions only on a synchronized branch. Synchronize
  before planning a session's work, not after.
- A long-lived branch that never rebases accumulates conflicts against work it
  could have absorbed cheaply, and diverges from coordination decisions it is
  expected to be following.

### Development And Checkpoints

The workstream status file—not root `CURRENT-STATUS.md`—records detailed progress,
evidence, the current or last task, and the next resumable task. Routine
workstream commits update only that status file and workstream-owned files.

**Commit often.** Commit each coherent unit of work as it is finished rather
than accumulating many files across a long session. An uncommitted session is
one interruption away from losing not just the changes but the order in which
decisions were made, which is the part no one can reconstruct. Committing is
cheap and local; it is not publication, and it does not require the work to be
complete. A checkpoint is a statement about project state and belongs in the
status file; a commit is a save point. Every checkpoint is committed, but most
commits are not checkpoints.

**Integration is a merge commit.** A workstream reaches `main` through one
merge commit per reviewed deliverable, never a fast-forward and never a
squash. `main`'s first-parent history is then the story, one entry per
delivery, titled as such, and that is how `main` is read: `git log
--first-parent`, `git bisect --first-parent`. The branch's own commits stay
reachable unchanged below that line, so every SHA a record cites remains a
real commit in every clone, and the order of decisions the small commits
preserved survives the moment the work is shared. Pushed history is never
rewritten: synchronize a pushed branch by merging `main` into it, and rebase
only what has never been pushed; see *Staying Current With `main`*. A project
that prefers squash records it in its local file under *Exceptions*, with
the consequence stated: its records may cite pull requests and tags, never
branch commits, because those commits stop existing when the branch does.

Keep all unfinished workstream documentation beneath:

```text
engineering-docs/wip/<start-date>-<name>/
```

The root documentation index lists the workstream `CURRENT-STATUS.md`, not
every internal open-work document. The workstream status must contain a small local
index of its open-work documents. This avoids making `index.md` a routine conflict
point. Permanent documents are added to the root index when finished.

Workstream documentation may be integrated into `main` before source changes
when visibility is useful. Publish documentation-only checkpoints, then
synchronize the workstream branch with the resulting `main` state before
editing the same files again. The branch status file remains authoritative for the
latest track-local state; the copy on `main` is the latest published snapshot.

### Workstream States, Pausing, And Resuming

Every open workstream is in exactly one state, recorded in its workstream-list row and
in its status file.

- **active** — being worked on, or expected to be shortly.
- **paused** — deliberately set down. Nothing external prevents work; the
  project chose to spend attention elsewhere. Resuming is a decision.
- **blocked** — cannot proceed. Something external is required: an answer, a
  dependency, a credential, another workstream's delivery. Resuming is an
  event, not a decision.
- **integrating** — in the completion sequence, not taking new work.

Paused and blocked look alike from outside and behave differently. A paused
workstream needs someone to choose it. A blocked one needs its blocker cleared,
so it must name the blocker and what would clear it, or nobody can tell when it
became resumable.

#### Pausing

Pausing is a deliberate act with a small ceremony, placed where the knowledge
is. Only the pair stopping work knows whether a thread finished or was
suspended, and they know it at the moment they stop; asking on return is
guesswork after the information is gone.

Before leaving a workstream:

1. Commit everything. If anything must stay uncommitted, say in the status file
   what and why.
2. Update the status file: current state, the last task and its status, and the
   next resumable task.
3. Write *Open Threads* — see below. This is the part that does not survive
   any other way.
4. Take your mail, send anything owed, and publish. A paused workstream
   holding unsent mail blocks its recipients without telling them, and one
   whose published state predates the pause tells whoever considers resuming
   it nothing about why it stopped.
5. Record external state that will outlive the session: running containers,
   held ports, manual environment setup, anything that decays.
6. Update the workstream-list row to `paused` or `blocked`, with a short reason. If
   blocked, name the blocker and what would clear it, and tell whoever can
   clear it — through their intake if it is another workstream. A blocked
   workstream nobody was told about is indistinguishable from an abandoned one.
7. Release your claim, and publish once more so the state others read is the
   state you left.

#### Open Threads

A bounded section in the status file, written at pause, holding what state
resumption alone would lose. Three parts:

- **Awaiting the human** — questions that need a decision before the work can
  sensibly continue. Each states what turns on the answer.
- **Weighed and unresolved** — options considered and not settled, with enough
  reasoning that someone can reopen the question intelligently rather than
  rediscover it. Include what was rejected and why; a rejected option with no
  recorded reason gets re-proposed.
- **Deliberately not preserved** — what was let go on purpose. Naming it stops
  a later reader hunting for a conversation that was intentionally dropped.

Roughly ten lines, not a transcript. It is deliberately too small to become a
dumping ground; anything larger belongs in a design note or, on explicit
request, a session record.

**Conversational replay is not a goal.** This document does not try to restore a
dialogue. Context is cleared, models change, and a replayed transcript is
expensive to read and mostly noise. What is worth carrying is the reasoning, not
the exchange that produced it. Depending on any agent's session-resumption
feature would also break portability, so capture is repository-level by
construction.

#### Resuming

1. Take your mail from the coordination branch, read the live workstream
   list from it, then the status file and intake.
2. **Propose the synchronization judgment.** Before planning, say whether
   the branch should synchronize with `main` now, and why, from four facts
   in this order, the first two of which `devcapsule workflow status` reports:
   - the definition or the local workflow file changed on `main` since this
     workstream last read them: **must** synchronize, and read the *Changes*
     entries since; the rules the session is about to follow are the ones
     that changed;
   - files the planned task will touch changed on `main`: **should**
     synchronize, since the cost of the conflict only grows;
   - coordination facts changed, rows, registrations, or decisions that
     affect the plan: **should** synchronize, though the live list already
     shows them;
   - none of the above and the branch is mid-slice: **may** defer, with the
     reason recorded in the status file, never past the next stage boundary
     or integration.
   The judgment is proposed, not executed: the human may say wait. Tooling
   supplies the facts, the agent weighs them, the human decides only when
   the weighing says it matters. `devcapsule workflow brief` prints the
   facts and a suggested verdict.
3. Read *Open Threads* before planning the session, not after. It is the
   difference between knowing what is next and knowing why it is next.
4. Re-verify what the status file asserts about external state. Status Files record
   facts that were true at pause; containers exit, ports are taken, branches
   move. Treat *External State And Risks* as claims to check, not as current
   truth.
5. Put unanswered questions from *Open Threads* to the human early, before
   doing work whose shape depends on the answers.
6. Update the workstream-list row to `active`.
7. Before editing, claim the slice you are about to work on, so other
   checkouts see it; see *The Coordination Branch*.

A workstream resumed without its *Open Threads* read is resumed at the level of
tasks and not of reasoning, which is how a settled question gets reopened and a
rejected option gets proposed again.

### Draft User Documentation

Root `docs/` contains only current user-facing documentation. Workstream drafts
live at:

```text
engineering-docs/wip/<start-date>-<name>/docs/
```

`docs/` is otherwise a reserved directory name beneath `engineering-docs/`.
It is allowed only inside `wip/<start-date>-<name>/` and
`archive/<start-date>-<name>/` workstream directories.

For an entirely new user document, store the actual draft under the workstream
`docs/` directory at its intended relative destination. For example:

```text
engineering-docs/wip/2026-04-12-api/docs/guides/new-guide.md
```

is intended to become:

```text
docs/guides/new-guide.md
```

For a change to an existing root `docs/` file, do not create a divergent copy.
Write a change proposal in the workstream `docs/` directory that identifies:

- the target file;
- why it must change;
- the intended semantic and material wording changes;
- implementation dependencies; and
- final verification.

Apply that proposal to the existing user document only when finishing a
successful workstream.

### Successful Completion And Integration

Successful integration is normally mechanical agent work, but delivery to
`main` follows repository policy. A pull request is the default delivery method
unless the repository or selected status file explicitly permits direct
integration. Do not infer permission to update `main` merely from the ability
to do so.

Before integration begins, the workstream's intake on `main` must be empty. See
*Intake Gates Completion*. Check this first, including the mailbox: a
forwarded item is sent by mail and its decision is a commit on this branch, so
discovering a full queue late in the sequence stalls the integration rather
than merely adding a step.

Before integration begins, the selected status file records:

- the target branch, normally `main`;
- the designated integration branch;
- the delivery method: `pull-request` or `direct-main`;
- the repository's branch-synchronization and merge policy; and
- any known human-only publication, approval, or merge step.

The agent owns routine preparation, synchronization, file movement, conflict
resolution where intent is clear, and validation. Ask the human for help when
a conflict requires a product or documentation decision, repository policy is
unclear, credentials or approval are unavailable, or another condition makes
the intended result ambiguous.

#### 1. Prepare The Integration Candidate

1. Verify the designated integration branch and every checkout holding it are
   clean and all accepted workstream changes are committed. Freeze that branch
   against unrelated work while integration proceeds.
2. Inspect current local and remote `main`, fetching remote refs when network
   access is available. If they have diverged, resolve it under *Verifying
   Shared Branch State*: reset only when every local commit is proven already
   upstream, and otherwise do not discard local commits or choose a side.
3. Synchronize the integration branch with current `main` according to
   repository policy. A project may require rebasing, merging `main`, a hosting
   platform's update-branch operation, or a merge queue. Pull-request delivery
   does not imply rebasing. Direct-main delivery uses the rebase and
   fast-forward procedure below.
4. Resolve mechanical conflicts. When reconciliation requires intent, preserve
   the evidence and ask the human before choosing a result.
5. Run the workstream-specific and shared validation required by the status file.

#### 2. Finish At The Delivery Boundary

The following file changes close the workstream and belong in one finishing
commit. For pull-request delivery, keep the workstream-list entry and open work
status file during ordinary review and add this commit only when the pull request
is otherwise merge-ready. For direct-main delivery, add it after rebasing and
validating the branch and before fast-forwarding local `main`.

1. Apply proposals for existing user documentation and move new user documents
   into root `docs/`.
2. Move enduring engineering records from open work into their normal requirements,
   specifications, decisions, design notes, implementation notes, bugs, or
   other permanent categories.
3. Update links and the root documentation index.
4. Remove the workstream from root `CURRENT-STATUS.md`.
5. Create
   `engineering-docs/archive/<start-date>-<name>/CURRENT-STATUS.md`
   containing a brief successful outcome, evidence, delivery method and
   durable integration reference, residual risks, and links to permanent
   records. Preserve the same start-date-and-name directory name used in
   open work. For a pull request, record its number or URL; the eventual merge
   revision need not be predicted before the hosting platform creates it.
6. Preserve only brief additional archive notes that have lasting value and
   remove the open-work directory.
7. Run the required checks on the complete final tree.

The finishing tree is provisional while it exists only on the workstream
branch or in an open pull request. Root `CURRENT-STATUS.md` on remote `main`
remains the authoritative workstream list until delivery completes.
Never append or merge the workstream status text into that workstream list.

#### 3A. Deliver Through A Pull Request

1. Publish the integration branch and open or update its pull request using the
   repository's normal tools and required base branch.
2. Address review and continuous-integration results. Resynchronize the branch
   only by methods allowed by repository policy; rerun required checks after
   any synchronization or finishing change.
3. Add the finishing commit only when the pull request is otherwise ready to
   merge, then allow any checks or approvals invalidated by that commit to run
   again.
4. Merge through the hosting platform as a merge commit, under *Development
   And Checkpoints*; the platform's squash and rebase options are used only
   when the local file records that exception. The agent may perform this
   action when authorized; otherwise ask the human or designated reviewer.
5. Verify from the updated remote ref that `main` contains the merged final
   tree and that the workstream-list entry and open-work directory are absent.

The pull request and resulting remote history are the durable integration
record. A follow-up commit solely to predict or insert the platform-generated
merge revision is not required.

#### 3B. Deliver Directly To Main

Use this path only when repository policy or the selected status file explicitly
permits direct integration:

1. Bring clean local `main` to the accepted remote `main` by ordinary
   fast-forward. If they have diverged, apply *Verifying Shared Branch State*.
   Reset local `main` only when every local-only commit is proven already
   upstream, reporting that evidence; otherwise stop and ask the human rather
   than choosing or discarding history.
2. Bring the frozen integration branch up to local `main`: merge `main` into
   it if it was ever pushed, rebase it only if it was not; rerun required
   validation. Resolve mechanical conflicts and ask the human when intent is
   required.
3. Merge the branch into local `main` with `git merge --no-ff
   <integration-branch>`, titled as the delivery, so that `main`'s
   first-parent history gains one entry. If `main` moved meanwhile, repeat
   from step 1.
4. Push `main` normally to its integration remote, normally with
   `git push origin main`. Never force-push `main`. If credentials, approval,
   or repository policy prevent publication, ask the human to perform it. If
   remote `main` moved, fetch it and repeat the direct-integration procedure
   without force.
5. Verify that remote `main` contains the finished integration commit.

The workstream is completely done only when remote `main` contains the final
tree produced by either delivery path. Until then, an open integration pull
request or a local `main` ahead of its remote is pending integration, not a
completed workstream. Associated branches may be removed after completion
once their changes are reachable from remote `main`.

### Unsuccessful Completion

Ending unsuccessfully does not discharge the intake queue. Before the sequence
below, decision every remaining item: forward to `project-management`
anything this workstream will not do, with the reason. Work handed over in good
faith must not disappear with the workstream that failed to do it. See *Intake
Gates Completion*.

Do not promote unfinished source or user documentation. On `main`:

1. Publish the workstream branch's final complete open-work documentation checkpoint
   to `main` without integrating unfinished source changes.
2. Remove the workstream from root `CURRENT-STATUS.md`.
3. Move the complete
   `engineering-docs/wip/<start-date>-<name>/` tree to
   `engineering-docs/archive/<start-date>-<name>/` without changing its
   directory name.
4. Update its `CURRENT-STATUS.md` to record the unsuccessful conclusion, the
   last task, and that task's final status.
5. Record the reason for ending, associated branches and revisions, and any
   reconsideration condition when useful.
6. Update links and the root documentation index.

Draft user documentation stays inside the engineering archive and never
appears in root `docs/`.

### Integration And Recovery

Before entering the successful-completion sequence, inspect changes since the
branch point, reconcile overlaps with other open workstreams, and record the
chosen integration branch, delivery method, and applicable repository policy
in the status file. Workstream state in Git and the hosting platform is durable but
not a live lock or presence system.

After interruption, enumerate checkouts and branches, inspect each dirty state
separately, compare local `main` with remote `main`, match branch prefixes to
workstreams, and resume from the selected workstream's last committed status.
An open integration pull request or a local finishing already
fast-forwarded to `main` but not its remote is pending integration, not a new
workstream. Treat newer uncommitted files as recovery material, not canonical
status.

Throughout the rest of this document, **selected status file** means root
`CURRENT-STATUS.md` in `single-stream` mode and
`engineering-docs/wip/<start-date>-<name>/CURRENT-STATUS.md` in
`multiple-streams` mode. General execution-loop rules apply to both modes.

## Core Loop

1. Start each session by reading the repository brief, workflow type, root
   status, and selected status file.
2. Read `REQUIREMENTS.md` for the requirement overview when changing behavior,
   validation scope, or priorities, then open the relevant detailed files under
   `engineering-docs/requirements/product/` as needed.
3. Work from the selected status file's active task or next slice, not from stale
   conversation memory.
4. Keep each cycle narrow enough that the user can validate the result.
5. When the user validates something manually, update the selected status file so
   the same task is not picked up again.
6. When an issue disappears or is deferred, remove it from the active task list
   and preserve the symptoms, logs, and reasoning in the completed-task archive.
7. Commit coherent units of work when asked, or at natural save points when the
   user wants the session state preserved.

## Pair Review Loop

The Pair Review Loop builds one slice with two agent pairs: the
implementor pair, and a review partner, an agent of a different engine with
the human. The human names the slice, the implementor engine and the
review-partner engine. Run the loop only when the human asks for it, for a
task or for a session, or when the local workflow file makes it the default
procedure. A pull request carries every step.
Use **Pair Review** as the short name.

1. The implementor builds one slice on one branch and opens its pull
   request, PRn. A stacked slice targets the previous slice's branch;
   otherwise PRn targets the integration branch. The body of PRn states what
   changed, the judgments taken for the human's review, and the validation
   with its counts and limits.
2. The implementor writes a brief for the review partner as one file. The
   brief states: the goal; the files to read first, in order; what the
   change does; what to look for, in this order: correctness, clarity and
   test coverage of the changed lines; what not to widen; the validation
   commands, verbatim; the commit authorship rule; the delivery commands;
   the forbidden actions; the final line to print. The brief is the review
   partner's only context.
3. The review partner works in its own checkout with its own environment
   and its own scratch. It does not touch the implementor's checkout, the
   status files, the intake, or published state. It does not merge, rebase
   or force-push. It does not build images or start capsules unless the
   brief says so.
4. The review partner delivers PRn.1: a branch off PRn's branch, named
   with the suffix `-review`, and a pull request against PRn's branch. Its
   body lists each finding as what was wrong or unclear, where, what
   changed, and how a test proves it; then what it considered and left
   alone, with the reason; then the proposals it did not implement; then
   its validation with counts and limits. If it changed nothing, it says so
   in its report and opens no empty pull request.
5. The implementor reads the diff of PRn.1, not only its body. It posts one
   assessment comment on PRn.1, labelled with its pair. Then it merges
   PRn.1 into PRn's branch with a merge commit, or it pushes back with a
   round brief that names the change requested and nothing else.
6. At most three rounds per slice. After the third, stop and hand PRn to
   the human with the open findings listed.
7. After the merge of PRn.1, the implementor runs the full gate on PRn's
   branch, records the counts in PRn, and hands PRn to the human. Only the
   human merges PRn.
8. The next slice starts after PRn.1 settles.
9. Record the loop: the status file names each round and its outcome; the
   proposals not implemented become open threads or work items; the
   assessment comments stay on the pull requests; the briefs are kept where
   the local file says.
10. Stop on a blocker: credentials, network, a review partner that cannot
    proceed. Do not work around it. Report it to the human.

## Release, Milestone, Stage, Task, And Checkpoint Terminology

Use these terms consistently so a saved checkpoint is not mistaken for a
product release and a broad release does not become one unbounded task.

- **Release:** an externally meaningful product version with a defined product
  contract, artifacts, documentation, and acceptance evidence. Names such as
  V1 and V2 identify releases, not milestones.
- **Milestone**, optional: a coherent, outcome-based checkpoint on the path
  to a release, with closure criteria and evidence, named for the outcome
  rather than for a date. A project that plans in milestones uses the word
  this way; no rule in this document depends on it.
- **Stage**, optional: a sequential subdivision inside a milestone or an
  execution plan, making order and dependencies clear without creating an
  external commitment. Likewise, no rule depends on it.
- **Task:** a bounded implementation, documentation, investigation, or
  validation unit.
- **Slice:** the narrow unit selected for the current human/agent work cycle.
- **Checkpoint:** a durable state snapshot or status file. It may preserve partial
  progress and does not imply that a task or milestone is complete.
- **Release candidate:** an actual candidate set of versioned artifacts and
  documentation subjected to release acceptance. Do not use it as another name
  for an ordinary milestone.

Requirements, decisions, and bugs are orthogonal records: requirements define
what must be true, decisions explain durable choices, and bugs preserve defect
evidence. A release selects requirements; milestones organize outcomes toward
that release; tasks and slices execute the work.

When planning a release:

1. Record a dated, revision-scoped gap review when the remaining scope needs a
   durable baseline.
2. Group accepted gaps into a small sequence of outcomes, which a project
   that plans in milestones calls milestones.
3. Define closure and evidence before starting on an outcome.
4. In `single-stream` mode, keep `CURRENT-STATUS.md` focused on the active
   release, milestone, and next task. In `multiple-streams` mode, keep that
   detail in the selected status file and only open-workstream discovery in the
   workstream list.
5. When a milestone closes, update the selected status file and gap review or
   successor plan without claiming that the release is complete.
6. Reserve release completion for the product-owner decision after the selected
   artifacts, documentation, and release-level acceptance evidence exist.

## Releases

A release is the moment a project's work becomes an externally meaningful
version: a defined set of artifacts, documentation, and acceptance evidence,
identified by a version and a tag. *Release, Milestone, Stage, Task, And
Checkpoint Terminology* defines the words. This section defines the Git refs a
release uses and how a release is run. Both had been left to each release to
improvise, and improvising them cost real work: fixes committed twice, a
candidate gate that had to prove two copies were the same patch, and a checkout
switching branches for every fix.

In the reference vocabulary, releasing is a **sub-process** of the development
process, and a release is one case of it. It has a trigger (the decision to
cut), a bounded duration, one resource that drives it from start to finish, and
a defined end. In `multiple-streams` mode that resource is a workstream, and
*Taking A Release Over* says how a workstream takes a release on and hands it
back.

### Release Refs

A project's release refs are the branch and the tags that identify one
release's source:

- **The release branch**, `release-<version>`, holds the source of every
  candidate and of the final release. The source describes itself as that
  version no later than the branch's first commit. The product owner may set
  the version earlier, at any point in the cycle and by any jump; the first
  commit then only confirms it.
- **Candidate tags**, `v<version>-rc<n>`, mark each candidate on the release
  branch, numbered from zero. They are never moved and never deleted.
- **The final tag**, `v<version>`, marks the accepted candidate's commit.

A project may spell these differently. If it does, it records the spelling
once, in its release policy, and uses it everywhere. What matters is that a
reader can tell a release ref from a workstream branch by its name alone.

**Release refs are not workstream branches.** They carry no `ws-<name>/`
prefix, belong to no workstream, and are the one exception to the rule that
every branch other than `main` belongs to exactly one workstream. A release
branch is associated with a workstream only for the duration of a release, and
only through the workstream-list row, as described under *Taking A Release Over*.
Nothing is inferred from a release ref's name except that it is one.

**Lifetime.** A release branch is created at the cut and retained for as long
as the project keeps its history. Once a candidate tag points into it, it is
never rebased, never force-pushed, and never deleted. Tags are immutable. A
release whose source must change gets a new candidate; a released version that
needs a fix gets a new version.

**The source version between releases.** Between releases the source names
itself by a development marker that the ecosystem's tooling orders before the
release it works toward; the release branch's first commit replaces it with
the release version, or confirms one the product owner already set; and after
the final tag `main` reopens with the next development version, the next patch
by default unless the owner names another. The marker's spelling and the
command that sets it are the project's, under *Version scheme* in
`WORKFLOW-LOCAL.md`.

**Direction of flow.** Work flows from the release branch to `main`, by merge,
and never the other way after the cut. *Staying Current With `main`* does not
apply to release refs: a release branch is not synchronized with `main`, and
tested release source is never rebased onto a `main` that has moved on. Other
workstreams keep integrating to `main` during a release; the release branch
does not take their work.

**Who may commit.** While a release is open, only the resource driving it
commits to the release branch, and only release fixes: changes needed to make
the candidate acceptable. Everything else waits for `main`. After the final tag
the branch is closed and nobody commits to it.

**A candidate is cut only from source `main` already has.** Every commit the
release branch carries since it left `main`, or since its previous candidate,
is merged to `main` before the candidate is tagged. Merged, not cherry-picked:
a merge lets the candidate gate pass by plain ancestry, while a cherry-pick
produces a second commit with the same content and forces the gate to prove
equivalence. A maintenance release that cannot merge uses the exception below.

**Maintenance releases.** A fix to an already released version, when `main`
cannot ship, starts a new release from that version's final tag rather than
from `main`. Its release branch is named for the new version and follows every
rule above. Its source may be unable to merge to `main` at all, because `main`
has moved past it. The project's candidate gate then accepts a documented
exception naming who authorized it, why, who owns the forward port of the fix
to `main`, and what follow-up closes it. The exception is a reviewed record
committed on the release branch, not a flag.

### Taking A Release Over

In `multiple-streams` mode, a workstream drives a release. It is the
workstream whose deliverable is the release's headline. A maintenance release
of an already released version is driven by the reserved `maintenance`
workstream. When the headline is unclear, `project-management` decides who
drives. The product owner decides the cut.

For the duration of the release, the rules below replace the ordinary branch
rules for that workstream, and only for that workstream. Unrelated workstreams
are unaffected.

1. **Cut from `main`, not from the workstream branch.** The workstream merges
   its working branch to `main` first. The release branch starts at that merge
   commit on `main`, and its first commit confirms the version, bumping it if
   the product owner has not already. The working branch is then closed for
   modification.
2. **The release branch is the workstream's selection.** The workstream-list row's
   branch association names the release branch, and its state reads
   `active; releasing <version>`. The status file is edited on the release branch
   and published from there, and reaches `main` with the merges of rule 3.
   The checkout sits on the release branch from the cut to the final tag.
3. **Integrate by merging the release branch into `main` before each
   candidate tag.** By pull request or the repository's delivery method, never
   by cherry-pick. The candidate gate then passes by ancestry, and the
   acceptance record uses the ancestry method.
4. **Closed means closed.** While the release is open, work on the
   workstream's subject lands only as release fixes on the release branch.
   Nothing is committed to the closed working branch, and no new working
   branch is opened under the name.
5. **Afterwards**, the workstream resumes on a fresh `ws-<name>/...` branch
   forked from `main`, or concludes. The workstream-list row's branch association
   returns to a workstream branch. The release branch stays behind as a release
   anchor, closed, and is never a workstream branch again.
6. **The status file records the release** as it records any task: the cut
   commit, each candidate and its outcome, the accepted candidate, the
   acceptance record, and the final tag. That is the release's durable record
   inside the workstream. The project's release policy says what else is
   recorded, and where.

Pausing or blocking during a release follows *Workstream States, Pausing, And
Resuming* unchanged, with one addition: the workstream-list row keeps naming the
release branch, so whoever resumes knows they are resuming a release and not
ordinary work.

In `single-stream` mode there is no workstream to take a release over. The
same ref rules apply, and `CURRENT-STATUS.md` records the open release, its
branch, and its candidates in place of a workstream-list row.

### Two Examples

The versions are illustrative. The rules are the same in a project that spells
its refs differently.

**An ordinary release, `1.4.0`, driven by the workstream whose work it ships.**

1. The workstream `search` has merged its branch `ws-search/v2` to `main`. The
   merge commit is the cut point. The owner decides to release.
2. `release-1.4.0` is created at the cut point. Its first commit bumps the
   source version to `1.4.0`. The workstream-list row for `search` now names
   `release-1.4.0` with state `active; releasing 1.4.0`, and `ws-search/v2` is
   closed.
3. `release-1.4.0` is merged to `main` by pull request. `v1.4.0-rc0` is tagged
   at its tip and pushed. The candidate is built, published, and validated.
4. Validation finds a defect. The fix is committed on `release-1.4.0`, the
   branch is merged to `main` again, and `v1.4.0-rc1` is tagged. Meanwhile an
   unrelated workstream merges its own work to `main`; `release-1.4.0` does not
   take it.
5. `v1.4.0-rc1` is accepted. The acceptance record is committed and reaches
   `main`. `v1.4.0` is tagged at the same commit as `v1.4.0-rc1`.
6. The `search` workstream resumes on `ws-search/v3`, forked from `main`, and its
   workstream-list row names that branch. `release-1.4.0`, `v1.4.0-rc0`,
   `v1.4.0-rc1`, and `v1.4.0` remain for good.

**A patch to a released version, `1.3.1`, when `main` is not shippable.**

1. `v1.3.0` is in use. A defect must be fixed in it, but `main` carries
   unfinished `1.4.0` work that cannot ship. The owner decides on a
   maintenance release, which the reserved `maintenance` workstream drives.
2. `release-1.3.1` is created at `v1.3.0`, not at `main`. Its first commit
   bumps the version to `1.3.1`. The `maintenance` workstream-list row names
   `release-1.3.1` for the duration.
3. The fix is committed on `release-1.3.1`. Merging it to `main` would carry
   the whole `1.3` line across `main`'s newer history, so it is not merged.
   Instead the release branch carries a documented integration exception
   naming who authorized it, why, which workstream owns forward-porting the fix
   to `main`, and the follow-up that closes it. `v1.3.1-rc0` is tagged and
   validated.
4. `v1.3.1-rc0` is accepted, and `v1.3.1` is tagged at the same commit. The
   forward-port owner delivers the fix to `main` through its own working branch
   as ordinary work.
5. The `maintenance` row returns to a `ws-maintenance/...` branch.
   `release-1.3.1` stays behind, closed.

### What This Section Leaves To The Project

The shape above is reusable; the mechanics are not. Each project records in
`WORKFLOW-LOCAL.md`, under *Release policy* and *Version scheme*: the exact
ref spelling if it differs from the default, how a candidate is built and
published, what the candidate gate checks and how an exception is recorded,
what acceptance evidence is required and where the acceptance record lives,
and the version-bump command. That policy is project state, not part of this
definition, and a project writes it before its first release.

## Turn-Level Choreography

Use each meaningful work cycle as a small contract between the human and the
agent.

1. Frame the slice.
   - The human states the goal, constraint, or uncertainty.
   - The agent restates the target outcome, relevant assumptions, and the next
     narrow slice it intends to execute.
2. Define closure before deep work.
   - State what "done for this slice" means.
   - State what evidence will count: test output, diff review, manual
     validation, or a documented decision.
3. Execute one narrow slice.
   - Prefer one coherent change over multiple partially finished ideas.
   - If the work uncovers a larger issue, record it and either finish the
     current slice or stop at a clear checkpoint.
4. Report with evidence.
   - Lead with the result.
   - Include only the evidence the human needs to evaluate the slice.
   - Separate "done", "not done", and "needs human input".
5. Decide the next branch explicitly.
   - Continue to the next slice.
   - Ask the human to validate or choose.
   - Stop and update the selected status file because the session reached a useful
     checkpoint.

The goal is steady throughput, not long uninterrupted agent runs with vague
status.

## Slice Sizing Rules

Prefer slices that fit one of these shapes:

- one code path plus its direct tests;
- one documentation or workflow improvement plus the matching status file update;
- one bug reproduction or diagnosis write-up;
- one manual-validation request with exact commands and expected observations;
- one decision that removes ambiguity for later implementation work.

Avoid slices that mix several of these unless the work is trivial. If a task is
too large to validate in one pass, split it before implementation.

## Human Input Contract

The human should provide, when relevant:

- the current priority or outcome to optimize for;
- risk tolerance, especially for host access, credentials, and security
  tradeoffs;
- manual validation results that only the human can observe;
- tie-break decisions when several defensible approaches remain.

The agent should ask for human input only when it materially changes the work
or when external validation is required. Otherwise, make the smallest reasonable
assumption, state it, and continue.

## Agent Reporting Contract

For each meaningful slice, the agent should report in this order:

1. Outcome.
2. Evidence.
3. Remaining gap or risk.
4. Recommended next slice.

Keep reports concise. The user should not need to reconstruct the state from a
long chronology.

A check reported as not runnable names the step of the local workflow
file's *Validation commands* that failed. An agent never reports a tool or
a dependency as absent without having followed that section; the project
wrote it so that the question has an answer.

## Decision And Escalation Rules

Escalate to the human when:

- a choice changes scope, architecture, or security posture materially;
- repository evidence is insufficient and several plausible interpretations
  remain;
- external state must change outside the agent's authority;
- the next slice would otherwise become speculative or broad.

Do not escalate merely because implementation is tedious or because several
small, compatible actions are possible.

## Checkpoint Triggers

Create or refresh durable state when any of these happen:

- a stage or subtask reaches a real closure point;
- manual validation changes project state;
- a new bug, decision, or requirement appears;
- the session ends with unfinished but resumable work;
- the active next step changes;
- the way the software is built, tested, started or smoke-tested was
  introduced or changed: the same commit updates the local workflow file's
  *Validation commands*.

If the user and agent are moving quickly, prefer more frequent small selected-
status file updates over one large retrospective rewrite.

## Markdown Roles

Use markdown files with distinct responsibilities:

- `README.md`: stable, developer-facing welcome page, project overview, setup,
  and documentation entry points.
- `CURRENT-STATUS.md`: the active status file in `single-stream` mode and the
  workstream list on `main` in `multiple-streams` mode. Refresh it
  according to the selected mode's checkpoint rules.
- `REQUIREMENTS.md`: implementation-agnostic requirement overview and index for
  project-level goals and concrete requirements.
- `docs/`: stable product guidance and reference material intended for users
  and adopters.
- `engineering-docs/`: contributor- and agent-facing engineering records,
  classified by authority and purpose.
- `engineering-docs/requirements/product/`: one markdown file per root
  requirement, with frontmatter metadata and canonical detailed requirement
  text.
- Subproject requirement overviews, such as `devcapsule-src/REQUIREMENTS.md`:
  implementation-specific requirement scope, status framing, and links to the
  canonical detailed requirement records for that subproject.
- `AGENTS.md`: instructions every future agent should read before touching the
  repository.
- `WORKFLOW-LOCAL.md`: the project's own half of the workflow, beside the
  installed `WORKFLOW.md`; see *The Project's Local Workflow*.
- `engineering-docs/design-notes/`: proposals, alternatives, research, and
  unsettled implementation-scoped architecture.
- `engineering-docs/implementation-notes/`: execution plans, validation
  details, debugging history, checklists, and other evidence that should not
  clutter the active task list.
- `engineering-docs/wip/YYYY-MM-DD-NAME/`: temporary documentation and the
  detailed status file for an open workstream in `multiple-streams` mode. Exactly
  two of these are always the reserved workstreams: `project-management`,
  which holds project-wide priorities, sequencing, and lifecycle reasoning
  rather than a second copy of the workstream list, and `maintenance`, which owns the
  defects no open workstream covers.
- `engineering-docs/archive/YYYY-MM-DD-NAME/`: final status and retained
  historical material for an ended workstream.
- `engineering-docs/bugs/`: one file per active or recently investigated
  bug, with symptoms, reproduction, evidence, hypotheses, verification target,
  and close criteria.
- `engineering-docs/completed-tasks/`: one file per completed, retired,
  manually validated, or no-longer-reproduced task. This is the retrospective
  archive.
- `engineering-docs/session-records/`: user-requested preservation of a
  consequential human/agent session. These records are historical context,
  not canonical decisions, requirements, status file state, or active backlog.
- Target-specific docs such as `docker4pycharm/README.md`: operational usage
  for one subproject or runtime target.
- Subproject implementation notes: strategy, decisions, retired issues,
  validation details, debugging history, and tradeoffs specific to one
  implementation path.

## User-Requested Session Records

Create a repository session record only when the user explicitly asks for the
conversation or session to be preserved. Do not infer this request merely from
session length, importance, a checkpoint, or session closure.

Store the record beneath the relevant scope in
`engineering-docs/session-records/`. For example, DevCapsule implementation
sessions use `engineering-docs/session-records/devcapsule/`. Repository-wide
sessions may live directly beneath `engineering-docs/session-records/` or in a
documented `product/` scope.

The default capture mode is `detailed`: an agent-authored chronological record
of important user instructions, decisions, rationale, examples, changes,
validation, rejected alternatives, and open work. Use `summary` when the user
asks for a concise record. Use `verbatim` only when the user or IDE supplies an
export and explicitly asks to store it; an agent reconstruction must never be
represented as an exact transcript.

Before writing, remove credentials, secret values, unrelated personal data,
hidden model reasoning, and raw output that does not improve durable project
memory. Record material omissions or redactions when they affect
interpretation.

Session records supplement the canonical project files. Propagate decisions,
requirements, bugs, validation, current state, and next work to their normal
artifacts, then link those artifacts from the session record. Never require a
future agent to read a session record to discover the current next task.

Use `YYYY-MM-DD-short-session-topic.md`, include capture metadata, and update
`index.md` for every record added, removed, or renamed. The detailed policy and
template guidance live in the `README.md` of each session-record directory.

## Subproject Roles

Top-level documentation must keep the repository split clear:

- `devcapsule-src/` is the active Python distribution project. New framework
  behavior, configuration protocol work, packaging, and tests should normally
  be implemented there.
- `docker4pycharm/` is the historical/reference PyCharm shell subproject. It
  remains useful as an operational baseline and comparison target, but current
  docs should not present it as the active development path unless the work is
  explicitly about preserving or validating the reference implementation.

When editing user-facing docs, avoid mixing these roles. Historical notes may
describe old commands, but current instructions should point users to
`devcapsule-src/` and the configuration-first CLI when describing active
development.

## Requirements Register

Use root `REQUIREMENTS.md` as the project-level overview and index for
requirements that should remain true across implementations. Use
`engineering-docs/requirements/product/` for the canonical detailed record of each root
requirement. Use subproject requirements files for implementation-specific
behavior, validation scope, and traceability.

The selected status file says what to do next; the relevant requirements register
says why the task exists, how important it is, and how implementation and
validation map back to project intent.

Each root requirement record under `engineering-docs/requirements/product/` should have:

- A stable ID such as `R-CONC-001`.
- A short title.
- A type split: high-level goal or concrete requirement.
- A clear statement.
- Priority: `gating`, `wanted`, `optional`, or `later`, relative to the next
  release; see *Glossary*.
- Status: `proposed`, `accepted`, `implemented`, `repo-validated`,
  `manually validated`, `deferred`, or `rejected`.
- Frontmatter metadata that stays easy to maintain in source control.
- Validation references or evaluation signals appropriate to the item type.
- Related tasks, bug records, decisions, or completed-task records.

Goals are evaluated by judgment and accumulated evidence. Concrete requirements
must be testable in principle, even if some verification is manual.

When a task, bug, or implementation note materially implements, validates,
changes, defers, rejects, or reinterprets a requirement, add a `Requirements:`
line with the relevant IDs. If no requirement exists yet, either add a proposed
requirement first or explicitly note that the work is exploratory.

Do not turn requirements files into a second active backlog. Requirements
should remain stable enough to help future sessions understand intent. The
active tasks in `README.md` remain the source of truth for immediate next work.

## User-Level Documentation Protocol

When changing behavior that an end user can observe or invoke, update the
user-level documentation in the same change as the code and requirement update.
Examples include command names, command order, options, defaults, generated
artifacts, setup steps, validation expectations, IDE configuration names, or
host-exposure behavior.

Use this documentation split:

- `REQUIREMENTS.md` records the requirement overview and links to the
  canonical detailed requirement files.
- Target user docs such as `devcapsule-src/README.md` describe how the user does
  it: installation path, command path, common examples, validation expectations,
  and current limitations.
- Root `CURRENT-STATUS.md` records the linear status file or open-workstream
  workstream list selected by the declared mode; a status file records track-local state
  in `multiple-streams` mode.
- Implementation notes record design rationale, rejected alternatives, and
  evidence that would distract from user instructions.

For every user-visible change, check:

1. Is there an accepted or proposed requirement for the behavior?
2. Does the relevant user-level README show the supported command path and
   defaults?
3. Are unsupported or intentionally removed paths absent from current user docs?
4. If host exposure, credentials, devices, Docker access, or persistent state
   changed, is the isolation impact documented beside the option/default?
5. Does the selected status file mention any manual validation still required?

Do not rely on historical notes as user documentation. Historical sections may
keep old command names when they describe what happened at that time, but
current user docs must show only the supported interface.

## Active Task Format

Each active task should include enough closure detail that the next agent knows
when to remove it from the list:

```markdown
1. Task title.
   Requirements: R-...
   Done means: ...
   Verification: ...
   Reopen if: ...
```

Use a lighter form only for very small tasks. The important rule is that the
done condition and verification path should be explicit before work starts.

## Active Tasks Versus Historical Context

The selected status file's active task list should contain only work that the next
session on that track should actually consider doing.

## Bug Intake

Before filing, apply *Bug Or Feature* in `INFORMATION-MODEL.md`: a record
here needs a requirement it threatens or a promised behavior observed wrong;
a wish, however large, is a backlog entry.

Use the relevant scope beneath `engineering-docs/bugs/` when a bug needs
durable evidence before it is fixed, retired, or converted into a completed
task. Name files like:

```text
engineering-docs/bugs/SCOPE/YYYY-MM-DD-short-title.md
```

**Every bug record opens with frontmatter carrying the controlled fields**, so
that questions about bugs can be answered from the records rather than by
reading all of them:

```text
---
status: reported
severity: untriaged
target: none
owner: maintenance
opened: 2026-09-18
requirements: [R-PRODUCT-001]
---
```

- `status`, exactly one of: `reported`, filed but not yet reproduced or
  evidenced; `confirmed`, reproduced or evidenced, no fix yet; `fixing`, an
  owner is working on it on a named branch; `fixed`, a fix is committed and
  validation is pending; `closed`, validated or no longer reproduced, and the
  record says which; `retired`, will not be fixed, with the reason recorded.
- `severity`, exactly one of: `blocking`, the named `target` cannot ship with
  it; `major`, wrong or unsafe behaviour that the product claims to prevent,
  with no acceptable workaround; `minor`, everything else; `untriaged`, not
  yet rated, which is the owner's first job.
- `target`: the release version the fix is meant for, or `none`.
- `owner`: the name of the workstream that owns the fix, or `none` in
  `single-stream` mode. In `multiple-streams` mode a bug always has one: the
  open workstream whose goal covers it, otherwise `maintenance`.
- `opened`, and once closed or retired `closed`: ISO dates.
- `requirements`: the identifiers of the requirements the bug threatens, or an
  empty list.

Prose after the frontmatter may say more and never contradicts the fields.
Whoever changes a field changes it in the record, in the same commit as the
work that justified the change. A bug whose `severity` is `blocking` and whose
`target` names a release blocks that release until its `status` is `closed`
or `retired`; nothing else needs to be consulted to know that.

Each bug file should also capture:

- Symptom.
- Environment: image, launcher command, project path or mount, host
  assumptions, and relevant versions.
- Reproduction: manual steps are acceptable when automation is not practical.
- Expected and actual behavior.
- Evidence: logs, stack traces, screenshots, commands, and timestamps.
- Current hypothesis, with uncertainty.
- Verification target: automated test, script/check, or manual validation.
- Fix notes and close criteria.

Do not include secrets. Keep detailed bug evidence in the bug file. The
selected status file should only contain the next action, such as investigating the
bug, validating a fix, or adding a regression check.

**Filing and routing.** A bug record is a durable product artifact and lives on
`main`. In `multiple-streams` mode, the filer commits it on its working branch
with `owner` set by the rule above, and it reaches `main` with the filer's
ordinary integration; until then the owner learns of it by mail if it must act
sooner. A bug
record is not an intake item and is not decided; the `owner` field is
its routing, and each owner reads its queue from the records on `main` at
session start. Handing a bug to another workstream is changing `owner`, with
the reason recorded in the record, on the working branch of whoever changes it.

When a bug is fixed and validated, no longer reproduced, or intentionally
retired:

1. Set `status` to `closed` or `retired` and fill in `closed`, with the reason
   in the record.
2. Add a dated status note near the current-state section of the owner's
   status file if future agents need to know why it disappeared from the queue.
3. Move detailed evidence into the corresponding scope beneath
   `engineering-docs/completed-tasks/` when the record has served its purpose
   as active evidence; the bug file may stay as the short durable pointer.
4. State when the bug should be reopened, for example "only if a later image or
   launcher change regresses this path."

This keeps the next-session question "what should we do next?" unambiguous.

## Completed Task Archive

Use one markdown file per closed task:

```text
engineering-docs/completed-tasks/SCOPE/YYYY-MM-DD-short-task-name.md
```

Recommended structure:

```markdown
# Completed Task: ...

Date: ...

Status: completed | retired | manually validated | no longer reproduced

## Original Task

...

## Requirements

R-...

## Done Means

...

## Verification

...

## Environment Provenance

- Image: ...
- Launcher mode: ...
- Project mount: ...
- Important host-side assumptions: ...

## Retrospective Notes

...

## Reopen If

...
```

This folder is not a second active backlog. It is the evidence trail for
retrospective, debugging, and future comparison.

## Human And Agent Responsibilities

The human owns product direction, risk tolerance, code-quality judgment,
overall project-quality acceptance, manual validation in the GUI, and external
operations the container cannot perform, such as pushing without Git
credentials.

The agent owns repository inspection, implementation, documentation updates,
status hygiene, tests or static checks that can run in the current environment,
and commits when requested.

When the human reports a manual validation result, treat it as authoritative
project state and update markdown accordingly.

In practical terms:

- the human chooses the hill to climb;
- the agent chooses the next safe foothold;
- both should expect each slice to end in evidence or an explicit blocker.

## Session Close Checklist

At the end of a meaningful session, update the selected status file with:

```text
Changed:
- ...

Requirements:
- ...

Validated:
- ...

Not validated:
- ...

External state:
- ...

Uncommitted changes:
- ...

Next task:
- ...
```

Keep this concise. The goal is to make the next session start cleanly.

## Design Decision Records

Some choices outlive the implementation that provoked them. "We chose
capabilities over named configurations" stays true across rewrites, new
subprojects, and model changes. Those get a ceremony.

Design decision records live at:

```text
engineering-docs/decisions/product/
```

They are root-level because they are implementation-agnostic and outlast any
subproject. Use `engineering-docs/decisions/product/_template.md` as the starting point.

### Two Tiers

- `engineering-docs/decisions/product/`: product and architecture decisions. Ceremonial,
  human-adopted, immutable once accepted. Use when a choice crosses
  subprojects, changes an accepted requirement, or moves a security boundary.
- `engineering-docs/design-notes/SCOPE/`: lightweight proposals and decision
  notes described in the next section. They are local, reversible,
  implementation-scoped, and writable by an agent without decision-record
  ceremony.

Promotion rule: a lightweight note that turns out to change a requirement,
cross subprojects, or set a boundary graduates into a root decision record.
Keeping the ceremony rare is what makes it mean something.

### The Ceremony

1. Propose.
   - A human or an agent writes the record with `status: proposed`.
   - It must carry at least two real options, each with an honest cost, plus a
     recommendation.
   - An agent may propose. An agent never adopts.
2. Review.
   - The human rejects, amends, or asks for more options.
3. Adopt.
   - The human states the decision. Status becomes `accepted`, and
     `date-decided` plus `decided-by` are filled in.
   - The agent records the act; it does not perform it.
4. Propagate.
   - An accepted decision produces or changes a requirement record, and a task
     if work follows. The decision is linked from both.
   - Decisions say why. Requirements say what must be true. Tasks say what to
     do next. Do not let a decision record become a second backlog.
5. Supersede, never edit.
   - Once accepted, the Decision and Rationale sections are frozen.
   - Changed your mind? Write a new record and mark the old one
     `superseded-by`. Editing an accepted decision retcons history and destroys
     the only property that makes it trustworthy as memory.

### Status Values

- `proposed`: written, not yet decided.
- `accepted`: adopted by the human owner.
- `rejected`: considered and intentionally not pursued.
- `deferred`: accepted direction, intentionally outside the current target.
- `superseded`: replaced by a later record.

A decision is never `implemented` or `repo-validated`. A decision is not built;
its consequences are. Those belong to requirements and tasks.

### Triggers

Write a design decision record when:

- a choice changes scope, architecture, or security posture materially;
- several defensible options remain and the choice will be re-litigated later;
- an accepted requirement is being reinterpreted or superseded;
- an isolation relaxation is being deliberately accepted.

These mirror the escalation rules above, because the same conditions that
warrant asking a human also warrant recording the answer.

## Decision Notes

These are the lightweight tier described above. For decisions that may be
revisited but stay local to one implementation, use a small note under the
relevant scope in `engineering-docs/design-notes/`:

```markdown
# Decision: ...

Date: ...

Context:
...

Options:
...

Decision:
...

Consequences:
...

Reopen if:
...
```

## External State Register

Some state cannot or should not live in Git: credentials, GUI logins, local
image tags, manually built images, host firewall behavior, or services running
outside the container. Record these facts without secrets in the current-state
section or an implementation note.

## Git Hygiene

Before editing or committing:

1. Check `git status --short --untracked-files=all`.
2. Keep unrelated user or IDE changes out of commits unless they are clearly
   part of the requested save point.
3. Use one commit message that describes the saved state, not every small
   conversational step.
4. If pushing is blocked by missing user credentials, commit locally and let the
   human push externally.

### Verifying Shared Branch State

Two questions about shared refs are easy to answer incorrectly by inspection.
Run the check rather than inferring the answer.

**Has this branch's work reached `main`?** Ancestry is the wrong test. A squash,
a rebase, or a merge queue rewrites commits, so

```text
git merge-base --is-ancestor <branch> origin/main
```

answers "no" for work that is already fully integrated. An agent that trusts it
concludes the merge failed and redoes integrated work. Compare by patch
identity instead:

```text
git cherry origin/main <branch>
```

Lines beginning `+` are genuinely absent from `main`. Lines beginning `-` are
already upstream under different commit identifiers. No `+` lines means the
work has landed, whatever the commit identifiers say.

**Have two refs diverged, and is the divergence real?** When a local ref and its
remote have both advanced, first establish whether the local-only commits carry
anything that is actually missing:

```text
git rev-list --left-right --count <local>...<remote>
git cherry <remote> <local>
```

If every local commit is reported as already upstream, the divergence is an
artifact of rewritten history and resetting the local ref to the remote one
discards nothing. An agent may do that without asking, and must then report the
evidence it relied on: the counts, the `git cherry` output, and the ref it
reset.

If any commit is genuinely missing, stop and ask the human. Do not choose a
side, discard history, or force-push to resolve it.

This applies to any ref, not only `main`. A stale workstream branch left by an
earlier session diverges the same way and is resolved the same way. Never
force-push `main` under either outcome.

## Applying This To Other Projects

When using a Dockerized IDE environment created by this project on another
repository, the same process should live inside that repository, not only
inside this DevCapsule repo.

An environment may include a reusable bootstrap template at a documented path,
for example:

```text
/usr/local/share/docker4ide/vibe-coding-process.md
```

In the mounted project, ask the agent:

```text
Bootstrap the vibe-coding process documentation from
/usr/local/share/docker4ide/vibe-coding-process.md into this project.
Create or update AGENTS.md, README.md, CURRENT-STATUS.md, REQUIREMENTS.md,
docs/, and engineering-docs/ as appropriate. Preserve existing project docs
and adapt the process to this repository. Declare the workflow in the
[workflow] table of .devcapsule/devcapsule.toml: definition, version, and
mode, single-stream or multiple-streams. If
multiple-streams, follow Initializing Multiple-Stream Mode, including the
reserved project-management workstream.
```

At minimum, add or update these files in the target project:

```text
.devcapsule/devcapsule.toml
AGENTS.md
WORKFLOW-LOCAL.md
README.md
CURRENT-STATUS.md
REQUIREMENTS.md
docs/
engineering-docs/requirements/
engineering-docs/specifications/
engineering-docs/decisions/
engineering-docs/design-notes/
engineering-docs/implementation-notes/
engineering-docs/wip/
engineering-docs/archive/
engineering-docs/bugs/
engineering-docs/completed-tasks/
engineering-docs/session-records/
```

The target project's `README.md` should point to its current status and workflow
entry points. The target project's `REQUIREMENTS.md` should give an overview
and index of accepted requirements with stable IDs, while the canonical
detailed records live under `engineering-docs/requirements/`. The target
project's `AGENTS.md` should instruct agents to read the brief, workflow type,
root status, and selected status file. Design proposals and lightweight decisions
belong in `engineering-docs/design-notes/`; execution and validation evidence
belongs in `engineering-docs/implementation-notes/`; active bug evidence
belongs in `engineering-docs/bugs/`; and closed task records belong in
`engineering-docs/completed-tasks/`.

The Docker image and launcher provide the working environment. The mounted
project provides the source of truth for the work.
