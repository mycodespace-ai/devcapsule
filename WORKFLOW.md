---
definition: devcapsule
version: 0.3.1
---

# Human / Agent Iteration Workflow

This file is the rule book for a human and a coding agent who build software
together. Markdown files in the repository are the durable memory of that work.
Conversation is fast. Project state must survive without it.

This file is written in a controlled style. One sentence states one rule.
Rules are grouped by topic. The reasons for the rules are not here. They are in
[`WORKFLOW-humane.md`](WORKFLOW-humane.md), which repeats each rule with its
intended effect and its motivation. That file is *for humans*. Two more files
are *for humans*: [`PREAMBLE.md`](devcapsule-src/devcapsule/assets/project_workflow/definition/PREAMBLE.md)
and [`INFORMATION-MODEL.md`](devcapsule-src/devcapsule/assets/project_workflow/definition/INFORMATION-MODEL.md).

## 1. How To Read This File

1. Read the *Glossary* first. Every term with a fixed meaning is defined there
   once.
2. Read the topics that apply to the current mode and task. Read a whole topic
   before you act on it.
3. Treat every numbered list and every sentence in the imperative as binding.
4. Skip a file or section that opens with *For humans*. Return to
   `PREAMBLE.md` when the rules do not settle a decision. Return to
   `INFORMATION-MODEL.md` when the question is what kind a thing is.
5. If two rules conflict, choose the reading that serves the evident intent.
   Say which reading you chose. Report the conflict as a defect.
6. Where this file is silent, apply *Judgment Where This File Is Silent* in
   topic 3.

**Precedence.** This file binds wherever it speaks. `WORKFLOW-LOCAL.md` binds
wherever this file is silent. A local rule that contradicts this file is an
exception. It is recorded under *Exceptions* in the local file with its reason.

**Intents.** Seven intents stand behind every rule: resumability, low-ceremony
coordination, no accidental loss of knowledge, judgment where the file is
silent, retrospective value subordinate to the work, explicit decision rights,
and portability across agents and projects. When intents conflict, apply three
tiebreaks in order: resumability wins; write what changes future behavior and
skip what only proves work happened; prefer one durable record to several.
`WORKFLOW-humane.md` explains each intent.

## 2. Glossary

Each term below has one fixed meaning in this file. Each entry says what the
thing is, where it lives when it is a file, and what it is not. A term not
listed here has its ordinary English meaning. An older name listed under
*Changes* stays a synonym for one release and is then retired.

### 2.1 The project and its copies

- **Project**: the repository and its history.
- **Remote**: the shared hosted copy. Branches meet there. `main` is
  authoritative there. Not a checkout.
- **Checkout**: one local clone directory where a pair edits files. Not a
  branch. A checkout has a current branch and can change it.
- **Pair**: one human and one agent who work together in one checkout.
- **Product owner**: the human who makes product decisions. "The human" in
  this file means the product owner.
- **Mode**: `single-stream` or `multiple-streams`, declared in
  `.devcapsule/devcapsule.toml`. Not a runtime setting.
- **Declaration**: the `[workflow]` table in `.devcapsule/devcapsule.toml`. It
  names the definition, its version, and the mode.
- **Definition**: this file, installed and versioned. Not the local workflow
  file.
- **Local workflow file**: `WORKFLOW-LOCAL.md`, the project's own half of the
  workflow. It governs where this file is silent.

### 2.2 Branches

- **Integration branch**: `main`, or the branch the local workflow file names
  instead. Every `main` in this file means the integration branch.
- **Workstream branch**: `ws-<name>/<sub>`, a branch that belongs to one
  workstream. A ref the workflow does not name is the project's.
- **Coordination branch**: `coordination`, the shared branch on the remote
  that carries mail and published state. Never merged into `main`. Never
  reset. Not a workstream branch. Not a place for work.
- **Mail**: an intake item in flight, as a file under `mail/<recipient>/` on
  the coordination branch. It becomes an intake item when the recipient takes
  it.
- **Claim**: a workstream's `state/<name>/claim` on the coordination branch.
  It says who works on the workstream, on which branch, on what, until when.
  It informs. It never refuses. Not a lock.
- **Published state**: the live copy of a workstream's status file and
  decision log under `state/<name>/` on the coordination branch. The
  workstream pushes it from its working branch. It is the truth while the
  workstream is open. The copies on `main` are the record as of the last
  integration.
- **Release branch**: `release-<version>`, with candidate tags
  `v<version>-rc<n>` and the final tag `v<version>`. Not a workstream branch,
  also while a workstream drives the release.

### 2.3 Workstreams and their records

- **Workstream**: a named, registered effort with one goal and its own status
  file, in `multiple-streams` mode. A case of the workstream sub-process. Not
  a branch. A workstream can own several branches.
- **Workstream name**: the unique lowercase identifier of a workstream. It
  follows `ws-` in branch names and appears in the directory name.
- **Reserved workstreams**: `project-management` and `maintenance`. Every
  multiple-stream project has both. They end only when the project leaves the
  mode.
- **State**: what a workstream does now: `active`, `paused`, `blocked`, or
  `integrating`. Not a bug's `status`. Not the status file.
- **Workstream list**: the table of open workstreams in root
  `CURRENT-STATUS.md` on `main`, in `multiple-streams` mode. Not a container
  image registry. Not the checkout list of `project list`. The older name was
  "registry".
- **Status file**: a workstream's `CURRENT-STATUS.md` under its open-work
  directory. It is the one authoritative account of the workstream's state,
  last task, next task, and open threads. In `single-stream` mode, root
  `CURRENT-STATUS.md` is the project's status file. Not the workstream list.
  Not a bug's status. The older name was "handoff".
- **Open-work directory**: `engineering-docs/wip/<start-date>-<name>/`. It
  holds a workstream's status file, intake, decision log, and dated documents
  by kind. See topic 7.6. The directory keeps its short name `wip`.
- **Record** (dated document): a dated document under the open-work directory.
  It holds history shed from the status file, a checkpoint, or a custody
  account. Read it for retrospection. It is never required for work.
- **Archive**: `engineering-docs/archive/<start-date>-<name>/`. An ended
  workstream's directory moves there unchanged.
- **Intake**: a workstream's `intake/` directory on its working branch. It is
  the queue of items the workstream took from its mailbox and has not decided.
  Not where bugs go. A bug is routed by its record's `owner` field.
- **Item**: one file in an intake. One delivered piece of work or one
  question. Not a bug record. Not a task until the recipient decides it.
- **Decision** (of an item): what a recipient does with an item. Exactly two
  kinds exist: acknowledge it as its own work, or forward it to
  `project-management`. Not a decision record.
- **Decision log**: a workstream's `intake-dispositions.md`. It lists every
  item the workstream received and what it decided. The file keeps its older
  name.
- **Deliverable**: what a workstream exists to produce. It travels the
  working branch and is reviewed as a whole. Not a record.
- **Records** (of a workstream): the files that describe a workstream while
  it runs: status file, decision log, list row, and intake. They are edited on
  the working branch, published live to the coordination branch, and carried
  to `main` inside the deliverable's integration. They are never merged for
  their own sake.

### 2.4 Work and its units

- **Release**: an externally meaningful product version with artifacts,
  documentation, and acceptance evidence. A case of the release sub-process.
- **Candidate**: a versioned set of artifacts under release acceptance, tagged
  `v<version>-rc<n>`. Not a milestone.
- **Task**: a bounded unit of implementation, documentation, investigation,
  or validation.
- **Slice**: the narrow unit selected for one human/agent work cycle.
- **Checkpoint**: a durable snapshot of state, normally an update of the
  status file. It does not mean that anything is complete.
- **Milestone** and **stage**: optional planning words. A milestone is an
  outcome on the path to a release, with closure criteria and evidence. A
  stage is an ordered subdivision inside a milestone or a plan. No rule in
  this file depends on them. Not the milestone pattern of the reference
  catalogue.
- **Requirement**: a record of what must be true, under
  `engineering-docs/requirements/`, with a controlled status and priority.
- **Decision record**: a `D-####` record of a durable choice, under
  `engineering-docs/decisions/`. Not an intake decision.
- **Bug record**: a file under `engineering-docs/bugs/` with controlled
  `status`, `severity`, `target`, and `owner` fields. Routed by `owner`,
  never by intake.
- **Backlog entry**: a wanted capability or improvement that is not yet a
  requirement, with a priority. It lives in a living list under
  `project-management`'s open-work directory, named for what it is. The
  everyday word is "feature". Not a bug record. See *Bug Or Feature* in
  `INFORMATION-MODEL.md`.
- **Work order**: a scoped hand-over of requirements, decisions, and backlog
  entries to a workstream, with finish criteria, under
  `engineering-docs/work-orders/`. Optional. Delivered by mail like any item.
  Not a requirement. Not the workstream's status file.
- **Priority**: for requirements and backlog entries, one of `gating`, the
  next release does not ship without it; `wanted`, high value, the release
  ships without it; `optional`, taken if cheap; `later`, not for this release.
  Not a bug's severity.
- **Exception**: a recorded departure from a rule, with its reason and the
  condition that ends it. It lives in the local workflow file or in the record
  it concerns. Not silence. A rule that does not exist needs no exception.
- **Judgment where this file is silent**: the standing permission to resolve an
  uncovered situation and keep working, with the obligation to record what
  was done. The older name was "latitude".

### 2.5 Validation

The local workflow file's *Validation Commands* section says which of these
kinds the project has and how each runs.

- **Environment**: what must exist on the machine before any check runs, and
  how to obtain it. Declared first.
- **Unit test**: exercises code in one process, with no network, no
  subprocess, and no external service. Runs wherever the environment exists.
  Always in the gate.
- **Integration test**: crosses a packaging or process boundary: a built
  artifact, a subprocess, an external tool, or a local service the project
  can start. Runs on any developer machine. In the gate when it does.
- **End-to-end test**: exercises the delivered software the way a user would,
  with real infrastructure. Opt-in, or run on a candidate. Its evidence is
  kept.
- **Smoke test**: the smallest end-to-end check that the software starts and
  answers. Run on every candidate and after every deployment.
- **Gate**: the fixed set of checks a pair runs before a checkpoint and before
  integration. It passes or fails as a whole. Not the candidate gate.
- **Candidate gate**: the checks a release candidate must pass before
  acceptance, with the acceptance evidence the release record keeps.
- **Acceptance evidence**: the recorded proof, from a downloaded or deployed
  candidate, that it does what the release claims. Kept in the release
  record. Never inferred from the gate.

### 2.6 Reference vocabulary

Where this file needs a precise process word, it uses the base terms of the
Workflow Patterns initiative (<http://www.workflowpatterns.com/>): process,
case, sub-process, task, work item, resource, trigger. The development process
is the process. A project is one case of it. A workstream and a release are
cases of its sub-processes. The pair, and in `multiple-streams` mode the
workstream, are the resources. A selected task or slice is a work item. The
product owner's decisions and the events named in each procedure are the
triggers. Three limits apply:

1. The vocabulary is a reference, not a modelling obligation. Rules are written
   in plain English. No formal model of the process is kept.
2. Use a pattern name only where it makes a rule shorter or less ambiguous.
   The sentence must still read correctly to someone who does not know the
   pattern.
3. Where this file defines a word, this file's definition governs inside this
   file. **Milestone** is the known collision.

### Changes

One entry per DevCapsule release that changed a rule, newest first, each with
the step a project takes to adopt it where one exists. The `version` in this
file's frontmatter names the release this text ships in; see topic 4.1.

#### 0.3.0

Entered on the working branch; the release that ships it stamps this entry
with its version. Rules changed since 0.2.14:

- **Pair Review Loop.** Formerly the review-partner loop; **Pair Review**
  is the short name. Topic 9.11: a slice built by an implementor
  pair and a review partner of a different engine; PRn and PRn.1; a written
  brief as the partner's only context; at most three rounds; the human
  merges PRn. Since 2026-10-29 the loop runs only on the human's request,
  for a task or for a session, or as the local file's default procedure.
  No migration.
- **Hand decisions to the human through capsule state and chat.** Topic 8.8:
  present numbered options and the available console link; prefer chat
  answers for the same item; record outcomes under the existing intake and
  design-decision rules before deleting temporary files. Keep unanswered
  items pending and use chat when console tools are absent.
- **Human-facing documents are materialized views.** Topic 12.12: a
  document derived from records is a view that records its dependencies
  inside itself, section-level when authored by an agent, file-level when
  rendered; software detects staleness from content ids and regenerates
  mechanically or by producing an agent task from the dependency difference;
  humans review views and do not maintain them; the humane companions are
  the first authored views. Migration: the companions gain their dependency
  records when the console's view registry exists; until then the local
  file's same-commit rule keeps them fresh by hand.
- **Work orders start workstreams.** Topic 12.11 defines the work order: one
  markdown file under `engineering-docs/work-orders/`, human language first
  with optional embedded formal specification, complete enough for a human or
  an agent to run the workstream to completion; topic 7.5 lets a workstream
  begin from one and link it. No migration: existing work orders stay as they
  are.
- **Record visual end-to-end tests; no generated explainer videos.** Topic
  9.6 rule 7: a harness that records the session is preferred for end-to-end
  tests of visual software, and the recording is acceptance evidence;
  generated explainer videos are not an output of this workflow. No
  migration.
- **Diagrams first, in DOT.** Topic 9.6 rule 6: an explanation with
  structure is given as a diagram first, in the DOT language in a fenced
  `dot` block rendered by Graphviz, with prose second; no other diagram
  notation. No migration: existing prose is not redrawn.
- **Controlled language for reports and records.** Topic 9.6 rule 5: every
  report to the human and every human-facing record text is written at about
  80% ASD-STE100, in the glossary's terms. Code, commands, quotations, and
  tables are exempt. No migration: existing records are not rewritten.
- **Controlled language and topic grouping.** This file is rewritten at
  about 80% ASD-STE100: one rule per sentence, grouped by topic, with every
  rule kept and the reasons moved to `WORKFLOW-humane.md`, which repeats each
  rule with its intended effect and motivation. Section names changed; the
  humane file carries the map from old names to new. No rule changed meaning.
  No migration.
- **Two files for humans.** `PREAMBLE.md`, why the workflow is opinionated
  and for whom, and `INFORMATION-MODEL.md` are installed and refreshed beside
  this file and marked *for humans*: explanation, not rules, which an agent
  skips in ordinary work; topic 1 says when it returns. The model is
  published as work in progress and says so. No migration.
- **Information model.** `INFORMATION-MODEL.md`, installed beside this
  file, names every kind of thing the workflow stores, its home, its controlled fields, what it may point at,
  and how a thing moves between kinds; *Bug Or Feature* is the test by
  field, and the *Glossary* gains **backlog entry** and **work order**.
  Migration: a bug record that violates no requirement and no promised
  behavior is retired with that reason and reopened as a backlog entry at
  the next triage; nothing else changes shape.
- **Validation commands are required, and the brief prints them.** Topic 4.2
  makes the local file's *Validation Commands* section required: the
  environment and the commands, runnable as written; topic 9.6 forbids
  reporting a check as not runnable without having followed it; `workflow
  brief` prints the section at session start. Migration: a local file whose
  section only points elsewhere states the environment inline.
- **Validation vocabulary and the checkpoint that keeps it true.** The
  *Glossary* names the validation kinds, environment, unit, integration,
  end-to-end, smoke, gate, candidate gate, acceptance evidence, the same in
  every ecosystem; `INFORMATION-MODEL.md` says they are declared in the local
  file's *Validation Commands*, `none` allowed with a reason; topic 9.8 gains
  the change of how the software is built, tested, started or smoke-tested;
  the local file template carries the structure and the obligation.
  Migration: a project fills the kinds it has at its next checkpoint.
- **Integration is a merge commit.** Topic 5.6: one merge commit per
  reviewed deliverable, never fast-forward, never squash; `main` is read by
  first parent; pushed history is never rewritten. Topic 10 follows in both
  delivery paths, and topic 5.5 no longer assumes a configurable strategy. A
  project that prefers squash records the exception in its local file with
  the consequence for cited commits. Migration: set the hosting platform's
  merge method to merge commits; nothing already on `main` changes.

#### 0.2.14

Stamped 2026-09-18 by the product owner, ahead of the release that ships it.
There is no 0.2.13. Rules changed since 0.2.12:

- **Reference vocabulary.** The glossary adopts the Workflow Patterns base
  terms. No migration.
- **Releases.** Topic 11 defines release refs and how a workstream takes a
  release over. The product owner may set the version at any point in the
  cycle; the release branch's first commit confirms it rather than owning it.
  No migration for existing refs; the next release follows topic 11.3.
- **The reserved `maintenance` workstream, and bug frontmatter.** Topics 7.4
  and 12.5. Migration: create the reserved workstream under its adoption
  exception, and add the controlled frontmatter to every bug record; a
  definition refresh does the first and the bug template shows the second.
- **The integration branch may be renamed locally.** `main` in this file
  means the project's integration branch; a project whose branch has another
  name says so under *Integration Branch* in `WORKFLOW-LOCAL.md`. No
  migration.
- **The `ws-` branch form.** Topic 5 and restrictions 4, 5, and 13: new
  workstream branches are `ws-<name>/<sub>`, and the workflow claims no other
  ref. No migration is required: a workstream branch under an older name
  stays that workstream's through its workstream-list row. A project that
  chooses to rename does so one workstream at a time, each on its own working
  branch, and may record its schedule under *Exceptions* in
  `WORKFLOW-LOCAL.md`.
- **The workflow declaration.** Topic 4.1: the `[workflow]` table names the
  definition, its version, and the mode; the frontmatter of this file
  carries the same version. Migration: add the table; a definition refresh
  writes it.
- **The open-work directory has a fixed shape.** Topic 7.6: a bounded status
  file that sheds history into dated records, dated documents by kind, and an
  index that says when to open each. No migration: existing documents keep
  their names; new ones follow the form.
- **A misplaced change travels as a patch.** Topic 8.7: work found to belong
  to another workstream is sent to it as a diff in an ordinary intake item
  and reverted from the sender's checkout, never committed on the wrong
  branch; the recipient owns application and integration. No migration.
- **Claims and the brief.** Topic 8.5: `workflow claim` says who is on what,
  shown live and expiring, never refusing; `workflow brief` prints the
  session's context in one command; `status` shows when each workstream last
  published. Resuming ends with a claim and pausing with its release. No
  migration.
- **The session-start synchronization judgment.** Topics 9.2 and 5.5: the
  agent proposes whether to synchronize, from facts the tool reports, and a
  changed definition or local workflow file is a must. `publish` stamps what
  was read; `list` shows commits behind `main` and whether the definition
  changed; `mail send` accepts a comma-separated list of recipients or
  `all`. No migration; the stamp appears at each workstream's next publish.
- **Coordination leaves `main`'s pull-request queue.** Topic 8.3: intake
  items travel one shared `coordination` branch on the remote, sent and taken
  with `devcapsule workflow mail`, and are decided on the recipient's working
  branch. Each workstream's status file and decision log are published live
  to the same branch with `devcapsule workflow publish`, read with
  `devcapsule workflow status`, and reach `main` only inside the workstream's
  ordinary integration. The outbox is retired: its one-way flow was right,
  and it put the buffer under the wrong owner and the records behind a pull
  request nobody reviewed. A workstream edits only its own row in the
  workstream list. Migration: an outbox send in flight is folded into its
  sender's working branch or discarded once its content is there; every open
  workstream publishes once; outbox branches are deleted.
- **The information model.** Glossary: every term with a fixed meaning is
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
- **The project's local workflow.** Topic 4.2: `WORKFLOW-LOCAL.md` holds what
  only one project can decide, permissively, with recommended headings.
  Topic 11 now states the development-version rule generically and delegates
  its spelling there. Migration: create the file from the template; bootstrap
  does so where it is missing.

#### 0.2.12 and earlier

Unversioned. The definition shipped in each release is readable at that
release's tag.

## 3. Judgment Where This File Is Silent

1. What this file does not expressly deny is allowed. When you meet a
   situation this file does not cover, resolve it with judgment and keep
   working.
2. Before you invoke rule 1, establish that this file is silent. A rule that
   is inconvenient or costly is still a rule. Change it through the
   workstream that owns the workflow. Do not work around it.
3. Rule 1 never overrides an instruction to stop, ask, refrain, or seek
   authority. Such instructions include: never force-push `main`; stop before
   editing when branch and workstream list disagree; do not infer permission
   to update `main` from the ability to do so; the carve-outs in restriction
   11 of topic 7.1; and every instruction to ask the human. Follow the
   instruction and raise the difficulty.
4. A conflict between two rules, or one rule with several readings that lead
   to different work, is a defect. Choose the reading that serves the evident
   intent. Say which reading you chose. Report the defect. A contradiction is
   not permission to pick the convenient side.
5. Record every exercise of judgment in the selected status file: what was
   missing, what you did, and why.
6. If the gap would recur in any project, send it by mail to the workstream
   that owns the workflow.

This topic is a V1 position adopted 2026-08-17. Revisit it when gaps become
rare.

## 4. Declaration, Local Workflow, And File Roles

### 4.1 The workflow declaration

Read the `[workflow]` table in `.devcapsule/devcapsule.toml` before you
interpret project status:

```toml
[workflow]
definition = "devcapsule"
version = "0.2.14"
mode = "multiple-streams"
```

1. `definition` names the workflow the project runs: `devcapsule`, the name
   or URL of another, or `none`. The product works in every case.
2. `version` is the DevCapsule release whose packaged definition this file was
   installed or refreshed from. It equals the `version` in this file's
   frontmatter. Tooling keeps the two equal. Report a mismatch as a defect.
   Do not resolve it by guessing. The value `unversioned` means the definition
   predates versions. Refresh to adopt one.
3. `mode` is `single-stream` or `multiple-streams`. A missing table or a
   missing `mode` falls back to the older top-level `workflow-type` field. A
   missing value means `single-stream`. Any other value is invalid. Report it.
   Do not guess which status protocol applies. The mode selects repository
   workflow, not runtime behavior.
4. The declared version governs. Follow the `WORKFLOW.md` in the repository at
   the declared version, whatever newer text a tool or an agent knows.
5. Change the definition only by a deliberate refresh, with the migration
   steps in *Changes*. A tool never refreshes the definition or changes the
   declared version as a side effect of another action.
6. A mechanical action a tool performs on workflow state follows the declared
   version's rules, or says plainly that it does not know that version.

The version is a DevCapsule release because the definition ships inside each
release and release tags are immutable. A release that changes no rule still
advances the version. *Changes* says whether anything changed.

### 4.2 The local workflow file

`WORKFLOW-LOCAL.md` beside this file holds the rules that only one project can
decide: its ecosystem, its hosting, its history.

1. Read this file first and the local file second. Both bind in their own
   territory.
2. Where this file is silent, the local file may say what the project needs.
   This is the ordinary way to fill silence, not an exception.
3. Record a local rule that contradicts this file under *Exceptions* in the
   local file, with its reason.
4. The local file is project state. Bootstrap renders it once from the
   template and never touches it again. A definition refresh replaces this
   file only.
5. The *Validation Commands* section is required. It states how to obtain the
   environment and the commands a pair runs before a checkpoint and before
   integration. Each command is runnable as written from a named directory.
   `workflow brief` prints the section at session start.
6. The other recommended headings are optional: *Integration Branch*, only
   when it is not `main`; *Version Scheme*, how the source names itself
   between releases and at a release, and the command that sets it; *Release
   Policy*, ref spelling if it differs, how a candidate is built and
   published, what the candidate gate checks, the acceptance evidence, and
   where the acceptance record lives; *Host Capabilities*, what the project
   needs from the machine and the hosting service, with justifications;
   *Exceptions*, every recorded departure from this file with its reason and
   the condition that ends it.
7. Delete or leave empty a section the project does not need. Add a section
   the template did not foresee.

### 4.3 File roles

Each markdown file has one role:

- `README.md`: stable developer-facing welcome page: overview, setup, and
  documentation entry points.
- `CURRENT-STATUS.md`: the status file in `single-stream` mode; the
  workstream list on `main` in `multiple-streams` mode.
- `REQUIREMENTS.md`: implementation-agnostic requirement overview and index.
- `AGENTS.md`: instructions every agent reads before touching the repository.
- `WORKFLOW-LOCAL.md`: the project's own half of the workflow.
- `docs/`: stable product guidance for users and adopters.
- `engineering-docs/`: contributor- and agent-facing engineering records.
- `engineering-docs/requirements/product/`: one file per root requirement,
  with frontmatter and the canonical requirement text.
- Subproject requirement overviews, such as `devcapsule-src/REQUIREMENTS.md`:
  implementation-specific scope, status framing, and links to the canonical
  records.
- `engineering-docs/design-notes/`: proposals, alternatives, research, and
  unsettled implementation-scoped architecture.
- `engineering-docs/implementation-notes/`: execution plans, validation
  details, debugging history, checklists, and other evidence.
- `engineering-docs/decisions/product/`: design decision records; see topic
  12.7.
- `engineering-docs/wip/YYYY-MM-DD-NAME/`: the open-work directory of an open
  workstream. Two of these are always the reserved workstreams.
- `engineering-docs/archive/YYYY-MM-DD-NAME/`: final status and retained
  material of an ended workstream.
- `engineering-docs/bugs/`: one file per active or recently investigated bug.
- `engineering-docs/completed-tasks/`: one file per completed, retired,
  manually validated, or no-longer-reproduced task. The retrospective archive.
- `engineering-docs/session-records/`: user-requested records of
  consequential sessions. Historical context, never canonical state.
- `engineering-docs/work-orders/`: work orders; see the glossary.
- Target-specific docs, such as `docker4pycharm/README.md`: operational usage
  for one subproject or runtime target.
- Subproject implementation notes: strategy, decisions, retired issues,
  validation details, and tradeoffs of one implementation path.

### 4.4 Subproject roles

1. `devcapsule-src/` is the active Python distribution project. Implement new
   framework behavior, configuration protocol work, packaging, and tests
   there.
2. `docker4pycharm/` is the historical PyCharm shell subproject. It is an
   operational baseline and comparison target. Do not present it as the
   active development path, except in work about preserving or validating the
   reference implementation.
3. Do not mix these roles in user-facing docs. Historical notes may describe
   old commands. Current instructions point users to `devcapsule-src/` and
   the configuration-first CLI.

### 4.5 Applying this workflow to another project

When a DevCapsule environment is used on another repository, the same process
lives inside that repository.

1. An environment may carry a reusable bootstrap template at a documented
   path, for example `/usr/local/share/docker4ide/vibe-coding-process.md`.
2. In the mounted project, ask the agent:

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

3. Add or update at minimum: `.devcapsule/devcapsule.toml`, `AGENTS.md`,
   `WORKFLOW-LOCAL.md`, `README.md`, `CURRENT-STATUS.md`, `REQUIREMENTS.md`,
   `docs/`, and under `engineering-docs/`: `requirements/`,
   `specifications/`, `decisions/`, `design-notes/`, `implementation-notes/`,
   `wip/`, `archive/`, `bugs/`, `completed-tasks/`, `session-records/`.
4. The target `README.md` points to its current status and workflow entry
   points. The target `REQUIREMENTS.md` indexes accepted requirements with
   stable IDs. The canonical records live under
   `engineering-docs/requirements/`. The target `AGENTS.md` instructs agents
   to read the brief, the workflow type, the root status, and the selected
   status file.
5. The Docker image and launcher provide the working environment. The mounted
   project is the source of truth for the work.

## 5. Checkouts, Branches, And Git

### 5.1 Relationships

1. Work means editing files in a checkout. Everything in this file happens in a
   checkout or in the remote.
2. A project has one authoritative remote and any number of checkouts.
3. A checkout has exactly one current branch.
4. Every `ws-` branch belongs to exactly one workstream. Release refs belong to
   none. Any other ref is outside the workflow.
5. A workstream can own several branches.
6. A checkout has at most one selected workstream at any moment. The current
   branch determines the current workstream, not the reverse.
7. Nothing about a checkout is registered or coordinated. A checkout carries
   only local facts: which one it is, its branch, and what is uncommitted.
8. The remote carries everything the project agrees on: branches, `main`, the
   workstream list, status files, and intake.
9. One checkout works on one workstream at a time. It changes workstream only
   on the human's specific direction and only from a clean tree. Concurrency
   comes from several pairs in several checkouts, through the remote.
10. Two pairs may select the same workstream. No lock exists. They contend on
    one status file. Coordinate outside the protocol before doing it
    deliberately.
11. How many checkouts exist on a machine, and whether one is a clone, a Git
    worktree, or a container, is the developer's choice. It is not workflow
    state. Each checkout obeys the selection rules on its own.
12. A checkout made for another purpose, such as running the product against
    itself or reproducing a bug, is not a workstream checkout. This file does
    not govern it.

### 5.2 Refs the workflow claims

The workflow claims three kinds of ref, recognizable by name alone:

1. `main`, the integration branch. A project whose integration branch has
   another name says so under *Integration Branch* in `WORKFLOW-LOCAL.md`.
2. `ws-<name>/<sub>`, a workstream branch. `<sub>` is the workstream's choice.
3. `release-<version>`, a release branch, with its `v<version>` tags. A
   project may spell these differently in `WORKFLOW-LOCAL.md`.

Every other ref belongs to the project. Do not create, rename, delete, rebase,
or select such a ref, except when the local workflow file or the human directs
it. A workstream branch under an older name is still that workstream's branch
through its workstream-list row.

### 5.3 Git hygiene

Before you edit or commit:

1. Check `git status --short --untracked-files=all`.
2. Keep unrelated user or IDE changes out of commits, except when they are
   clearly part of the requested save point.
3. Write one commit message that describes the saved state, not every
   conversational step.
4. If missing credentials block a push, commit locally. Let the human push.
5. Commit each coherent unit of work when it is finished. A commit is a save
   point. It is not publication. It does not require complete work.
6. A checkpoint is a statement about project state in the status file. Every
   checkpoint is committed. Most commits are not checkpoints.

### 5.4 Verifying shared branch state

Run the check. Do not infer the answer by inspection.

1. To learn whether a branch's work reached `main`, do not use ancestry. Run
   `git cherry origin/main <branch>`. A line that begins with `+` is absent
   from `main`. A line that begins with `-` is already upstream under another
   commit identifier. No `+` lines means the work has landed.
2. To learn whether two refs have diverged for real, run
   `git rev-list --left-right --count <local>...<remote>` and
   `git cherry <remote> <local>`.
3. If every local commit is already upstream, reset the local ref to the
   remote one. You may do this without asking. Report the counts, the
   `git cherry` output, and the ref you reset.
4. If any commit is genuinely missing, stop and ask the human. Do not choose a
   side. Do not discard history. Do not force-push.
5. Apply rules 1 to 4 to any ref, not only `main`.
6. Never force-push `main`.

### 5.5 Staying current with `main`

1. Synchronize the working branch with `main` at least at every stage
   boundary, before a substantial slice, and before integration.
2. At every session start, propose whether to synchronize now. See topic 9.2
   for the judgment.
3. `devcapsule workflow status` shows two facts beside each row: commits
   behind `main`, and whether the definition or the local workflow file on
   `main` differs from what the status file says was last read.
4. `devcapsule workflow publish` writes that stamp as a `Definition read:`
   line that names the files' content ids. A workstream that has never
   published shows no stamp.
5. Rebase a branch only when it has never been pushed. Merge `main` into a
   branch that was pushed.
6. After your own delivery lands under a merge commit, the branch is an
   ancestor of `main`. Synchronize by fast-forward.
7. After your own delivery lands under a squash or rebase exception, compare
   trees, not commit identities. Confirm the branch has nothing unique. Then
   hard reset it to `main`. Do not rebase a branch with nothing left to carry.
8. Resolve mechanical conflicts yourself and say so: reformatting, moved
   sections, adjacent edits.
9. Give semantic conflicts to the human: two workstreams assert incompatible
   things.
10. Do not stop synchronizing because a conflict is unresolved.
11. Synchronize before you plan a session's work. A stale branch decides
    against stale rules.

### 5.6 Integration is a merge commit

1. A workstream reaches `main` through one merge commit per reviewed
   deliverable. Never fast-forward. Never squash.
2. Read `main` by first parent: `git log --first-parent`,
   `git bisect --first-parent`.
3. Never rewrite pushed history.
4. A project that prefers squash records it under *Exceptions* in its local
   file, with the consequence stated: its records cite pull requests and tags,
   never branch commits.

## 6. Single-Stream Mode

1. Root `CURRENT-STATUS.md` is the status file.
2. It records current state, evidence, and one next resumable slice.
3. Routine checkpoints update that file.
4. Branches are the unit of work. How many checkouts exist locally is an
   implementation detail.
5. Topics 9, 10.5, 11, and 12 apply to both modes. In `single-stream` mode,
   "the selected status file" means root `CURRENT-STATUS.md`.

## 7. Workstreams

### 7.1 Definition and restrictions

A workstream is a bounded set of changes developed toward one goal. It
begins, develops, and ends successfully or unsuccessfully. The reserved
`project-management` and `maintenance` workstreams are the exceptions: they
stay open for as long as the project uses `multiple-streams` mode.

1. Workstreams are flat. Do not create parent, child, or nested workstreams.
2. Every workstream has one unique lowercase name made of letters, numbers,
   and hyphens. Never reuse an archived name.
3. Every workstream has one immutable ISO start date: the calendar date on
   which its registration is first committed to `main`. A migration exception
   records a historically established start date.
4. Every `ws-` branch belongs to exactly one workstream. Release refs belong to
   none. A ref the workflow does not name is the project's. Leave it alone.
5. Each workstream branch name begins with `ws-<name>/`. A release branch does
   not.
6. A workstream may have several branches. Every branch starts from `main` and
   is intended to return to `main` if the workstream succeeds. A release
   branch is not a workstream branch; see topic 11.
7. `main` belongs to no workstream. It is the shared registration, visibility,
   finishing, and integration branch.
8. Do not implement workstream work directly on `main`.
9. Each open workstream has exactly one status file at
   `engineering-docs/wip/<start-date>-<name>/CURRENT-STATUS.md`.
10. Root `CURRENT-STATUS.md` on `main` lists open workstreams only. An open
    workstream stays listed while active, paused, blocked, or integrating.
11. No workstream holds exclusive editing rights over a file. A workstream may
    edit any file its task requires. Do not infer exclusivity from a file's
    subject, directory, or creator. Three carve-outs stand: another
    workstream's open-work directory except its `intake/`; another
    workstream's row in the workstream list; uncommitted recovery state in
    another checkout. Report what you observe about another workstream. Do
    not edit its record. Deliver work to it through its `intake/`; see topic
    8. Wider exclusivity applies only where a documented locking protocol
    exists and is used. None exists today.
12. `project-management` and `maintenance` are reserved names. Exactly one
    workstream carries each. No ordinary workstream takes either. Neither is
    archived and recreated while the project stays in `multiple-streams` mode.
13. A workstream's records travel its working branch and are published live to
    the coordination branch. No branch carries records alone. Nothing is
    merged to `main` for a record's sake.
14. Once a pair has selected a workstream and begun a task, the agent changes
    workstream only on a specific instruction from the human. Do not infer
    that authority from task subject, file location, apparent ownership,
    urgency, dependency routing, a next step in another status file, or the
    availability of another checkout. If a change seems needed, stop before
    switching or editing, explain why, and ask. Returning is another change
    and needs its own instruction.

### 7.2 Initializing multiple-stream mode

Do this in one commit on `main`, both for a new project and for a
single-stream project that adopts the mode:

1. Set `mode = "multiple-streams"` in the `[workflow]` table.
2. Convert root `CURRENT-STATUS.md` into the compact workstream list. Move
   detailed state into a workstream status file.
3. Create the reserved `project-management` and `maintenance` workstreams by
   the procedure in topic 7.5, with the initialization date as their start
   date. Register both.
4. Create `engineering-docs/wip/` and `engineering-docs/archive/`.

Initialization creates exactly these two workstreams. Ordinary workstreams
begin later, when there is real work. A multiple-stream project that lacks
either reserved workstream is incompletely initialized. Report that. Do not
work around it.

### 7.3 The reserved `project-management` workstream

1. It owns project-wide priorities, sequencing, cross-workstream dependencies,
   portfolio-level checkpoints, lifecycle decisions about other workstreams,
   and routing of work that has no owner yet.
2. It is not a second workstream list. Root `CURRENT-STATUS.md` on `main`
   stays the single list of open workstreams.
3. It is not an implementation catch-all. Work that fits an open workstream's
   goal belongs to that workstream. Work that fits none is a reason to begin a
   workstream, which `project-management` decides and hands over.
4. It does not own other workstreams' state. Restriction 11 binds it.
5. Its authority is advisory and recorded. It does not gate other workstreams'
   commits, integrations, or checkpoints.
6. It is permanent for the lifetime of `multiple-streams` mode. Its list state
   reads `active; permanent coordination`. Paused and blocked are legitimate.
7. Its branches are `ws-project-management/<topic>`, forked from `main`.
   `ws-project-management/coordination` is the conventional first branch.
   Selection, intake, checkpoints, commits, and integration are ordinary.
8. It ends only when the project leaves `multiple-streams` mode. Migrate to
   `single-stream` in one commit on `main`:
   1. Confirm no ordinary workstream is open. Confirm its own intake and
      `maintenance`'s are empty. Empty its own intake last.
   2. Fold useful coordination state into root `CURRENT-STATUS.md`, which
      becomes the single-stream status file again.
   3. Move both reserved open-work directories to `engineering-docs/archive/`
      unchanged. Record the migration, its date, and the resulting mode in
      each final status.
   4. Set `mode = "single-stream"`.
9. A project that adopts the mode with an existing branch, directory, or
   effort named `project-management` records a migration exception in the
   reserved workstream's status file. Do not rename history.

### 7.4 The reserved `maintenance` workstream

1. It owns the bug records under `engineering-docs/bugs/` whose `owner` field
   names it: triage, fixes on `main`, and fixes on maintained release lines.
   It drives maintenance releases under topic 11.
2. It keeps the bug queue honest. Every open bug carries a controlled status
   and severity. Triaging an untriaged bug is its work.
3. It is not a catch-all for defects. A bug inside an open workstream's subject
   is owned and fixed by that workstream. `maintenance` owns a bug when no open
   workstream's goal covers it, or when the owner hands it over with a recorded
   reason.
4. It is not a feature workstream. Work that changes what the product does is
   a reason to begin an ordinary workstream. Hand over a fix that grows into a
   feature.
5. It is not a second bug tracker. The bug records are the queue and the
   evidence. Its status file holds only what is being fixed now and what is
   next.
6. Read its queue from `main`: the bug records whose `owner` is `maintenance`
   and whose `status` is neither `closed` nor `retired`. List them at session
   start.
7. Balance load by branches and pairs, not by more workstreams. Its branches
   are `ws-maintenance/<bug-or-release-line>`. Several pairs may work it at
   once. A defect cluster with its own goal and end is an ordinary workstream.
8. It is permanent for the lifetime of `multiple-streams` mode. Its list state
   reads `active; permanent maintenance`. Paused is legitimate when its queue
   is empty. Blocked is legitimate when every open bug waits on something
   external.
9. Selection, intake, checkpoints, commits, and integration are ordinary.
10. It retires with `project-management` on migration to `single-stream`. Its
    intake must be empty. Its open bug records stay. Their `owner` becomes
    `none`.
11. A project that adopted the mode before this workstream existed creates it
    when it adopts this rule, with that date as the start date, and records in
    the new status file that the start date is later than the mode's
    initialization.

### 7.5 Beginning a workstream

Begin from a clean, current `main` checkout:

1. Choose the goal, an unused name, and the ISO start date. When a work
   order exists for the goal, the work order is the goal; see topic 12.11.
2. Create `engineering-docs/wip/<start-date>-<name>/CURRENT-STATUS.md`.
3. Record the start date, goal, state, branch prefix, target branch, delivery
   method or repository default, current task, and next resumable task. Link
   the work order when there is one.
4. Create `intake/README.md` and an empty `intake-dispositions.md` beside the
   status file.
5. Add the workstream to root `CURRENT-STATUS.md`.
6. Commit the registration on the workstream's first `ws-<name>/...` branch,
   forked from `main`. Run `devcapsule workflow publish`. The registration
   reaches `main` inside the first integration. At initialization, the
   initializing commit on `main` carries it.
7. Make workstream changes only on the workstream's branches.

A branch created before the registration commit is not a valid workstream
branch. A branch that predates adoption needs an explicit migration exception
in the workstream's status file. An inactive legacy branch is not an open
workstream. Register and associate its continuation before committing new work
to it.

### 7.6 The open-work directory

`engineering-docs/wip/<start-date>-<name>/` holds everything a workstream keeps
while it runs. Its contents are fixed in kind:

1. `CURRENT-STATUS.md`, the status file. It holds what the workstream is, its
   state and branch, what it does now, what is next, its open threads, and an
   index of the directory's other documents. Keep it short: what a person
   reads in ten minutes. Move anything that has stopped changing out of it.
2. `intake/` and `intake-dispositions.md`, the queue and the decision log.
3. Dated documents, `YYYY-MM-DD-<kind>-<slug>.md`, one per topic. The kinds
   are `design`, a design discussion or spike; `note`, evidence or analysis;
   `record`, history shed from the status file, a checkpoint, or a custody
   record. A project may add kinds in its local workflow file. A living
   document with no date, such as a backlog or a ledger, is allowed and is
   named for what it is.
4. Nothing else. Deliverable content never lives here.
5. Draft user documentation lives under `docs/` inside this directory; see
   topic 12.3.

At each pause, and when a task's narrative is finished, move its account
verbatim into a dated record. Keep one line in the status file that points at
it. List every document once in the status file's document index, with when
to open it. At conclusion the directory moves to `engineering-docs/archive/`
unchanged.

### 7.7 Workstream states

Every open workstream is in exactly one state, recorded in its list row and
its status file:

- `active`: being worked on, or expected to be shortly.
- `paused`: deliberately set down. Nothing external prevents work. Resuming is
  a decision.
- `blocked`: cannot proceed. Something external is required. Resuming is an
  event. A blocked workstream names the blocker and what would clear it.
- `integrating`: in the completion sequence. Not taking new work.

### 7.8 Selecting a workstream at session start

1. Identify the current checkout, its branch, and its dirty state.
2. Read the live workstream list from the coordination branch with
   `devcapsule workflow status`. When offline, fall back to the table in root
   `CURRENT-STATUS.md` on the locally accepted mainline ref. Never consult a
   long-lived workstream branch's copy of that table. If mainline candidates
   have diverged, resolve that under topic 5.4 before choosing.
3. If the human names an open workstream, select it. Explicit intent chooses
   the target. It does not move the current branch. It does not authorize
   mixing dirty state.
4. Otherwise, when the current branch starts with `ws-<name>/`, select the
   open list entry with that name. A documented adoption exception may give
   the same unique association to a historical branch.
5. If a name-prefixed or excepted branch has no open list entry, or its
   association disagrees with the list, the routing is invalid. Stop before
   editing. Report the inconsistency.
6. `main` has no default editing workstream. Workstream-list coordination and
   repository-wide inspection may happen there. A workstream change needs an
   explicit selection, then a switch to that workstream's branch in a clean
   checkout.
7. Never check out the coordination branch for work. Read and write it through
   the tool or through plumbing from any branch. A checkout found on it is on
   no workstream. Switch to a working branch first. Treat uncommitted changes
   found there as recovery material.
8. Detached HEAD, an unregistered branch, or several plausible mappings have
   no default. Ask the human only when neither explicit intent nor a unique
   registered association settles the workstream.
9. Follow the selected row's status-file link. Do not guess the start date
   from branch or commit timestamps. On the workstream branch, the committed
   status file is authoritative for the latest local state.
10. Read the selected workstream's `intake/` before planning the session.
11. If the selected workstream differs from the current branch, switch to its
    branch in a clean checkout only when the human's instruction identifies
    that workstream. Otherwise stop and ask.
12. Do not combine dirty state from two workstreams. Do not use a stash as
    their boundary.

### 7.9 Changing workstream during a task

1. After the pair has begun work, the selection is sticky for the task.
2. A change needs a specific human instruction that names the target
   workstream or branch, or unmistakably directs the work there. A request
   that merely exposes work belonging elsewhere is not such an instruction.
   An agent's view that another workstream fits better is not such an
   instruction.
3. If you think a change is necessary, pause before you change any checkout or
   make any edit attributed to the proposed target. Tell the human: the
   current workstream; the proposed target; why the task appears to need the
   change; what happens to unfinished work. Wait for the human's direction.
4. If the human approves, pause or hand off the current workstream
   deliberately. Enter the target through a clean, correctly associated
   branch.
5. Completion of the target does not authorize a return. Changing back waits
   for specific human direction.
6. Read-only inspection of another workstream's published state is not a
   change. Sending mail, taking mail, and publishing are not changes.
7. Creating, entering, or reusing another checkout to edit for a different
   workstream is a change, whether or not the current checkout's branch moves.

## 8. Mail, Intake, Decisions, And The Coordination Branch

### 8.1 Writing and delivering an item

1. Any workstream, or the human, may send an item to a workstream.
2. One item is one file, named `YYYY-MM-DD-<sender-name>-<slug>.md`. The date
   is the delivery date.
3. The file states: what is handed over; why it belongs to the recipient; the
   evidence or documents behind it; what accepting it would mean.
4. The sender does not assign priority, sequence, or a release target.
5. Deliver by mail on the coordination branch, with
   `devcapsule workflow mail send <recipient> <file>`. Do not wait for anyone's
   integration. `<recipient>` is one name, a comma-separated list, or `all`.
6. Sent mail is append-only. A sender never edits, renames, or removes a file
   in a mailbox or intake, including its own. Send a correction as a new item
   that names what it supersedes.
7. Only the recipient removes or reclassifies items in its own intake.

### 8.2 Taking and deciding

1. Take your mail at every session start and again before you pause:
   `devcapsule workflow mail take`. The tool copies each item into `intake/` on
   the working branch, stages it, then removes it from the branch in one
   commit.
2. Commit taken items on the working branch promptly.
3. Every item ends in exactly one of two decisions: acknowledge or forward.
   Scheduling is not a third outcome. An item accepted for later is
   acknowledged, with its position recorded.
4. **Acknowledge** means the workstream takes the item as its own work. On the
   working branch, record it in the status file as a requirement, backlog
   entry, task, or next step, with the reasoning, and place it in the order of
   work. In one commit, add an entry to the decision log and delete the intake
   file. Recording an opinion about an item is not acknowledging it.
5. **Forward** means the workstream is not the right owner. Reasons include:
   the item is not a well-formed requirement; it will not be fixed; it belongs
   to another workstream or a later release; it is outside the registered
   scope. Send a new item to `project-management` by mail that carries the
   original's full text, or its path and revision, and the reason. In one
   commit, add a decision-log entry that names where the item went and delete
   the original. Record in the status file what was forwarded and why. Do not
   choose the new owner. Routing is `project-management`'s decision.
6. Items from `project-management` are not forwardable. Acknowledge them. If
   such an item is impossible, misrouted, or conflicts with the registered
   scope, raise that with the human. Until the routing changes, the item
   stands.
7. `project-management`'s own decisions are terminal. An item that reaches it
   ends in one of three ways: delivered onward to a workstream; made the
   reason to begin a workstream; dropped with recorded reasoning.
8. Intake gates completion. A workstream is not complete while any item
   remains in its intake or mailbox. A workstream that ends unsuccessfully
   still forwards every item it will not do.
9. The `intake/` directory carries a `README.md`, so that an empty intake is
   unambiguous. Do not list intake items in `index.md` or in the workstream's
   document index.

### 8.3 The decision log

1. Each workstream keeps one append-only log at
   `engineering-docs/wip/<start-date>-<name>/intake-dispositions.md`.
2. Only the receiving workstream writes it, in the same commit that removes
   the item from the queue. Anyone may read it.
3. One entry per item, appended, newest last, never edited or removed:

   | Item | Dispositioned | Outcome | Note |
   |---|---|---|---|
   | `2026-08-16-sender-some-slug.md` | 2026-08-16 | acknowledged | One line. Full reasoning in the status file. |
   | `2026-08-16-sender-other-slug.md` | 2026-08-17 | forwarded | Where it went. |

4. The note is one line. The reasoning is in the status file.
5. The log is never pruned. It travels with the workstream into the archive.
   List it in the workstream's document index, not in `index.md`.
6. Write no reply into a sender's intake. The sender looks in three places:
   the mailbox, the recipient's intake, and the recipient's published decision
   log.

**Invariant.** Across the coordination branch and the recipient's working
branch, every item ever sent is in exactly one of three places: the mailbox,
in flight; the recipient's `intake/`, taken and undecided; the decision log,
decided. Never two. Never none. Taking moves an item from the first place to
the second in one operation. Deciding moves it from the second to the third in
one commit.

### 8.4 The coordination branch

1. One branch, `coordination`, on the remote, carries mail under
   `mail/<recipient>/<item>.md`, published state under `state/<name>/`, and a
   README.
2. Never merge it into `main`. Never reset it. Never force-push it. Every
   change is an ordinary commit on top. Ask the host to forbid force-pushes to
   it.
3. Senders add. Only the recipient removes, and only after taking.
4. A push that loses a race is retried from a fresh fetch. Racing commits
   touch different files.
5. `devcapsule workflow mail send`, `check`, and `take` do this through git
   plumbing. They do not switch branches. They touch the working tree only to
   write taken items into `intake/`. `check` and `take` infer the workstream
   from a `ws-<name>/...` branch.
6. Without the tool: `git fetch origin coordination`,
   `git show origin/coordination:mail/<name>/` to see, and a commit on that
   branch to send or take. The rules are the same.
7. Mail is read from the remote. A checkout that cannot reach it reads what it
   last fetched.
8. `main` sees an item only when the recipient's working branch integrates.

### 8.5 Published state, claims, and the brief

1. `devcapsule workflow publish` pushes the working tree's current status file
   and decision log to `state/<name>/`, without a branch switch, and replaces
   what was there. It publishes what the pair is looking at, committed or not.
2. Publish at each checkpoint, before pausing, and at finish.
   `publish --retire` removes the directory when the workstream concludes.
3. `devcapsule workflow status` renders every open workstream's state,
   branch, and next step from the published copies, with when each last
   published.
4. While a workstream is open, its published state is the truth for routing,
   selection, and resumption. Read it first. The copies on `main` are the
   record as of the last integration. If the two disagree, the published copy
   is newer, and the working branch is where to fix it.
5. `devcapsule workflow claim "<slice>"` writes who, which branch, which slice,
   and an expiry of twelve hours by default to `state/<name>/claim`.
   `claim --release` removes it. Pausing and finishing release it. `status`
   and `brief` show live claims and mark expired ones.
6. A claim informs. It never refuses. A pair about to start on a claimed
   workstream tells its human and chooses: wait, take another slice, take
   another workstream, or proceed knowingly.
7. `devcapsule workflow brief` prints, for the selected workstream: its row
   and next task; who works on what; its waiting mail; the titles of the
   *Changes* entries it has not read since its stamp; the synchronization
   facts with a suggested verdict; the local file's *Validation Commands*.
   Read it first, before the status file. The verdict it suggests is the
   agent's to propose and the human's to accept.

### 8.6 Records reach `main` with the deliverable

1. Two kinds of file travel differently. The deliverable travels the
   workstream's branch and reaches `main` by repository policy, reviewed as a
   whole. Records are edited on the working branch, published live, and
   carried to `main` inside the deliverable's integration.
2. No pull request ever exists for a record alone. Nothing is merged for a
   record's sake.
3. Publish whenever anyone outside the branch might read the workstream: when
   a document refers to a per-workstream path; when the workstream pauses or
   blocks; when another workstream needs it to act.
4. Publishing pushes the branch's current copy verbatim. Never write a
   different version for others.
5. Do not use publishing or mail to integrate deliverable content early. If
   anyone would review it as part of the workstream's work, it is
   deliverable, and it travels the owning workstream's branch under review.
6. A finished slice of the deliverable may land through an ordinary pull
   request before the workstream is done. The status file records what has
   landed.

### 8.7 A misplaced change travels to its owner as a patch

1. When a pair finds that a bounded change it is making belongs to another
   workstream, it stops expanding that work.
2. If the change is separable and uncommitted, send the owning workstream an
   ordinary intake item that carries: the diff; its base revision; the paths
   affected; new files in full; the reason for the handoff; what validation
   was done or is still missing.
3. The human may authorize finishing the bounded change first. Nothing permits
   starting another workstream's implementation on purpose.
4. Verify delivery before you remove anything. Then revert from the sender's
   checkout only what the delivered patch represents. Record the handoff in
   the sender's status file.
5. Do not switch workstream for it. Do not commit the source change on the
   sender's branch. Do not rewrite shared history to manufacture a clean
   handoff.
6. If the change is already committed or cannot be separated safely, ask the
   human to choose the recovery. Finishing on the current branch is one
   option.
7. The recipient decides the item through ordinary intake. It reviews the
   patch, checks that it applies, and owns application, validation, the source
   commit, and integration. A patch is a proposal. A later patch supersedes an
   earlier one by a new item that says so.

### 8.8 Handing a decision to the human

1. Hand a choice with several options, or several items each with options,
   to the human as a decision document and numbered chat text.
   Inside a capsule with console tools, build the document with
   `devcapsule project checkout decisions from-table`.
   Save its output in the capsule's decisions directory using the format in
   [DECISIONS.md](devcapsule-webconsole/DECISIONS.md).
   Without console tools, present the numbered chat text directly.
2. Present each item's options by key with
   `devcapsule project checkout decisions hand-off <file>` when available.
   End with the console link when the command supplies one.
   Accept answers in chat or on the page.
   Prefer a chat answer over a page answer for the same item.
3. Keep the document and answer in capsule state, outside Git.
   Keep links that carry the run token in chat only.
4. Read page answers from the decisions directory.
   Record each outcome under the applicable rules: topics 8.2 and 8.3 for
   intake, and topic 12.7 for design decisions.
   Use intake options consistent with topic 8.2 instead of the table
   builder's defaults.
   Keep unanswered items pending.
   Delete the document and its answer only after all outcomes are recorded
   in the normal repository files.
5. Send other environment notices through
   `devcapsule project checkout notifications post` when available.
   Otherwise give the notice in chat.
   Do not use notification files as repository records.
   Preserve durable facts under the applicable record rules.

## 9. Sessions

### 9.1 Session start

1. Run `devcapsule workflow brief`.
2. Take your mail. See topic 8.2.
3. Read the live workstream list, then the selected status file in full, then
   its intake.
4. Read `REQUIREMENTS.md` when the task changes behavior, validation scope, or
   priorities. Open detailed requirement files only as the task needs them.
5. Work from the selected status file's active task or next slice, not from
   conversation memory.
6. In `multiple-streams` mode, list the open bugs whose `owner` is the
   selected workstream.

### 9.2 Resuming a paused or blocked workstream

1. Take your mail. Read the live list, the status file, and the intake.
2. Propose the synchronization judgment before planning, from four facts in
   this order. `devcapsule workflow status` reports the first two.
   - The definition or the local workflow file changed on `main` since this
     workstream last read them: **must** synchronize, and read the *Changes*
     entries since.
   - Files the planned task will touch changed on `main`: **should**
     synchronize.
   - Coordination facts changed that affect the plan: **should** synchronize.
   - None of the above, and the branch is mid-slice: **may** defer, with the
     reason recorded in the status file, never past the next stage boundary
     or integration.
   The judgment is proposed, not executed. The human may say wait.
3. Read *Open Threads* before planning.
4. Re-verify what the status file asserts about external state. Treat it as
   claims to check.
5. Put unanswered questions from *Open Threads* to the human early.
6. Set the workstream-list row to `active`.
7. Claim the slice before editing: `devcapsule workflow claim "<slice>"`.

### 9.3 Pausing

Before you leave a workstream:

1. Commit everything. If something must stay uncommitted, say what and why in
   the status file.
2. Update the status file: current state, the last task and its status, the
   next resumable task.
3. Write *Open Threads*; see topic 9.4.
4. Take your mail. Send anything owed. Publish.
5. Record external state that outlives the session: running containers, held
   ports, manual setup, anything that decays.
6. Set the list row to `paused` or `blocked`, with a short reason. If blocked,
   name the blocker and what clears it. Tell whoever can clear it, through
   their intake if it is a workstream.
7. Release your claim. Publish once more.

### 9.4 Open threads

*Open Threads* is a bounded section of the status file, written at pause, of
about ten lines. It has three parts:

1. **Awaiting the human**: questions that need a decision before work
   continues. Each states what turns on the answer.
2. **Weighed and unresolved**: options considered and not settled, with enough
   reasoning to reopen the question. Include what was rejected and why.
3. **Deliberately not preserved**: what was let go on purpose.

Do not write a transcript. Anything larger belongs in a design note or, on
explicit request, a session record. This file does not try to restore a
dialogue. Capture is repository-level. Do not depend on an agent's
session-resumption feature.

### 9.5 The work cycle

1. Frame the slice. The human states the goal, constraint, or uncertainty. The
   agent restates the target outcome, the assumptions, and the next narrow
   slice.
2. Define closure before deep work. State what "done for this slice" means and
   what evidence counts: test output, diff review, manual validation, or a
   documented decision.
3. Execute one narrow slice. Prefer one coherent change. If the work uncovers
   a larger issue, record it, then finish the slice or stop at a checkpoint.
4. Report with evidence. See topic 9.6.
5. Decide the next step explicitly: continue, ask the human to validate or
   choose, or stop and update the status file.
6. Size slices to one of these shapes: one code path plus its direct tests;
   one documentation or workflow change plus the status-file update; one bug
   reproduction or diagnosis; one manual-validation request with exact
   commands and expected observations; one decision that removes ambiguity.
   Split a task that is too large to validate in one pass before you start.
7. The human provides, when relevant: the priority or outcome to optimize for;
   risk tolerance, especially for host access, credentials, and security;
   manual validation results; tie-break decisions.
8. Ask for human input only when it materially changes the work or when
   external validation is required. Otherwise make the smallest reasonable
   assumption, state it, and continue.
9. Escalate to the human when: a choice changes scope, architecture, or
   security posture materially; repository evidence is insufficient and
   several plausible interpretations remain; external state must change
   outside the agent's authority; the next slice would otherwise become
   speculative or broad. Do not escalate because work is tedious or because
   several small compatible actions are possible.

### 9.6 Reporting

1. For each meaningful slice, report in this order: outcome; evidence;
   remaining gap or risk; recommended next slice.
2. Keep reports concise. Separate "done", "not done", and "needs human input".
3. Before you report a check as not runnable, follow the local file's
   *Validation Commands* section. Then name the step that failed. Never report
   a tool or a dependency as absent without having followed that section.
4. When the human reports a manual validation result, treat it as
   authoritative project state. Update the markdown accordingly.
5. Write every report to the human, and every human-facing record text, at
   about 80% ASD-STE100: one fact per sentence, about twenty words or fewer,
   active voice, the glossary's terms and no synonyms for them. This covers
   session reports, status-file narrative, open threads, decision notes, bug
   prose, pull-request descriptions, and intake items. It does not cover
   code, commands, quoted material, or tables.
6. When an explanation to the human has structure, give a diagram first and
   prose second. Structure means a sequence, a hierarchy, a set of states and
   transitions, a dependency graph, or a layout. Write the diagram in the DOT
   language, in a fenced `dot` block in the markdown, so that Graphviz and
   related software render it. Use no other diagram notation. Commit an
   image only where a renderer is unavailable to the reader, and keep the
   `dot` source beside it. This covers reports, status files, decision notes,
   design notes, pull-request descriptions, and the humane companions. The
   rule file stays text.
7. When an end-to-end test exercises visual software, such as an IDE or a
   browser, prefer a harness that records the session as a movie and
   screenshots. Playwright is the reference: open the browser context with
   `record_video_dir` and `record_video_size`, save the context's video as
   a `.webm` beside the test's report, and take `page.screenshot` at the
   moments the report cites. Keep the recording as acceptance evidence.
   Do not generate explainer videos as a way to explain work to the human;
   the recording of what ran is the video the project keeps.

### 9.7 Responsibilities

1. The human owns product direction, risk tolerance, code-quality judgment,
   project-quality acceptance, manual validation in the GUI, and external
   operations the container cannot perform.
2. The agent owns repository inspection, implementation, documentation
   updates, status hygiene, tests and static checks that run in the current
   environment, and commits when requested.
3. Each slice ends in evidence or an explicit blocker.

### 9.8 Checkpoints

Create or refresh durable state when any of these happen:

1. A stage or subtask reaches a real closure point.
2. Manual validation changes project state.
3. A new bug, decision, or requirement appears.
4. The session ends with unfinished but resumable work.
5. The active next step changes.
6. The way the software is built, tested, started, or smoke-tested changed.
   The same commit updates the local file's *Validation Commands*.

Prefer frequent small status-file updates over one large rewrite.

### 9.9 Session close

At the end of a meaningful session, update the selected status file with:
changed; requirements; validated; not validated; external state; uncommitted
changes; next task. Keep it concise.

### 9.10 Session records

1. Create a session record only when the human explicitly asks to preserve the
   conversation or session. Do not infer the request from length, importance,
   a checkpoint, or closure.
2. Store it under the relevant scope in `engineering-docs/session-records/`,
   named `YYYY-MM-DD-short-session-topic.md`, with capture metadata.
3. The default mode is `detailed`: an agent-authored chronological record of
   instructions, decisions, rationale, examples, changes, validation, rejected
   alternatives, and open work. Use `summary` when the human asks for a
   concise record. Use `verbatim` only when the human or the IDE supplies an
   export and asks to store it. Never present a reconstruction as a
   transcript.
4. Before writing, remove credentials, secrets, unrelated personal data,
   hidden model reasoning, and raw output that adds nothing durable. Record
   material omissions.
5. Propagate decisions, requirements, bugs, validation, current state, and
   next work to their normal files. Link them from the record. Never require a
   future agent to read a session record to find the next task.
6. Update `index.md` for every record added, removed, or renamed. The
   directory README holds the detailed template.

<a id="911-the-review-partner-loop"></a>

### 9.11 Pair Review Loop

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

## 10. Completing A Workstream

### 10.1 Preconditions

1. The intake and the mailbox are empty. Check this first.
2. The status file records: the target branch, normally `main`; the designated
   integration branch; the delivery method, `pull-request` or `direct-main`;
   the repository's synchronization and merge policy; any human-only
   publication, approval, or merge step.
3. A pull request is the default delivery method. Direct integration needs
   explicit permission from the repository or the status file. Do not infer
   permission to update `main` from the ability to do so.
4. The agent owns routine preparation, synchronization, file movement,
   mechanical conflict resolution, and validation. Ask the human when a
   conflict needs a product or documentation decision, when policy is unclear,
   when credentials or approval are unavailable, or when the intended result
   is ambiguous.
5. Before the sequence, inspect changes since the branch point and reconcile
   overlaps with other open workstreams.

### 10.2 Prepare the integration candidate

1. Verify the integration branch and every checkout that holds it are clean,
   with all accepted changes committed. Freeze the branch against unrelated
   work.
2. Inspect local and remote `main`. Fetch when possible. If they diverged,
   apply topic 5.4.
3. Synchronize the integration branch with current `main` by repository
   policy. Pull-request delivery does not imply rebasing.
4. Resolve mechanical conflicts. Where reconciliation needs intent, preserve
   the evidence and ask the human.
5. Run the validation the status file requires.

### 10.3 Finish at the delivery boundary

Put the following changes in one finishing commit. For pull-request delivery,
add it only when the pull request is otherwise merge-ready. For direct-main
delivery, add it after synchronizing and validating, before merging.

1. Apply proposals for existing user documentation. Move new user documents
   into root `docs/`.
2. Move enduring records from the open-work directory into their permanent
   categories: requirements, specifications, decisions, design notes,
   implementation notes, bugs, or others.
3. Update links and the root documentation index.
4. Remove the workstream from root `CURRENT-STATUS.md`.
5. Create `engineering-docs/archive/<start-date>-<name>/CURRENT-STATUS.md`
   with: a brief outcome; evidence; delivery method and durable integration
   reference; residual risks; links to permanent records. Keep the directory
   name. For a pull request, record its number or URL.
6. Keep only brief archive notes of lasting value. Remove the open-work
   directory.
7. Run the required checks on the complete final tree.

The finishing tree is provisional while it exists only on the branch or in an
open pull request. Root `CURRENT-STATUS.md` on remote `main` stays the
authoritative list until delivery completes. Never merge the workstream status
text into the workstream list.

### 10.4 Deliver

**Through a pull request:**

1. Push the integration branch. Open or update its pull request against the
   required base branch.
2. Address review and CI. Resynchronize only by methods repository policy
   allows. Rerun required checks after any synchronization or finishing
   change.
3. Add the finishing commit when the pull request is otherwise ready. Let
   invalidated checks and approvals run again.
4. Merge through the hosting platform as a merge commit. Use squash or rebase
   only when the local file records that exception. Perform the merge when
   authorized. Otherwise ask the human or the designated reviewer.
5. Verify from the updated remote ref that `main` contains the final tree and
   that the list entry and open-work directory are absent.

**Directly to `main`**, only when repository policy or the status file permits:

1. Fast-forward clean local `main` to remote `main`. If they diverged, apply
   topic 5.4. Reset local `main` only when every local-only commit is proven
   upstream. Otherwise stop and ask.
2. Bring the frozen integration branch up to local `main`: merge `main` into
   it if it was ever pushed; rebase it only if it was not. Rerun validation.
3. Merge the branch into local `main` with `git merge --no-ff
   <integration-branch>`, titled as the delivery. If `main` moved meanwhile,
   repeat from step 1.
4. Push `main` normally. Never force-push `main`. If credentials, approval, or
   policy prevent the push, ask the human. If remote `main` moved, fetch and
   repeat without force.
5. Verify that remote `main` contains the integration commit.

The workstream is done only when remote `main` contains the final tree. An
open pull request, or a local `main` ahead of its remote, is pending
integration. Remove associated branches only after their changes are reachable
from remote `main`.

### 10.5 Unsuccessful completion

1. Decide every remaining intake item first. Forward to `project-management`
   everything this workstream will not do, with the reason.
2. Do not promote unfinished source or user documentation.
3. Publish the branch's final open-work documentation checkpoint to `main`
   without the unfinished source changes.
4. Remove the workstream from root `CURRENT-STATUS.md`.
5. Move the complete open-work directory to `engineering-docs/archive/`
   without changing its name.
6. Update its `CURRENT-STATUS.md` with the unsuccessful conclusion, the last
   task, and that task's final status.
7. Record the reason for ending, the branches and revisions, and any
   reconsideration condition.
8. Update links and the root documentation index.
9. Draft user documentation stays inside the archive. It never enters root
   `docs/`.

### 10.6 Recovery after interruption

1. Enumerate checkouts and branches.
2. Inspect each dirty state separately.
3. Compare local `main` with remote `main`.
4. Match branch prefixes to workstreams.
5. Resume from the selected workstream's last committed status.
6. An open integration pull request, or a local finishing already merged to
   local `main` but not pushed, is pending integration, not a new workstream.
7. Treat newer uncommitted files as recovery material, not canonical status.

## 11. Releases

### 11.1 Terminology

1. A release is an externally meaningful product version with a defined
   contract, artifacts, documentation, and acceptance evidence. V1 and V2 name
   releases, not milestones.
2. A release candidate is an actual set of versioned artifacts under release
   acceptance. Do not use the word for a milestone.
3. Requirements say what must be true. Decisions explain durable choices. Bugs
   preserve defect evidence. A release selects requirements. Milestones, where
   used, organize outcomes toward it. Tasks and slices execute the work.
4. When planning a release: record a dated, revision-scoped gap review when the
   remaining scope needs a baseline; group accepted gaps into a small sequence
   of outcomes; define closure and evidence before starting an outcome; keep
   the selected status file focused on the active release and next task; when
   an outcome closes, update the status file and the plan without claiming the
   release is complete; reserve release completion for the product owner,
   after the artifacts, documentation, and acceptance evidence exist.

### 11.2 Release refs

1. The release branch is `release-<version>`. It holds the source of every
   candidate and of the final release. The source describes itself as that
   version no later than the branch's first commit. The product owner may set
   the version earlier, by any jump. The first commit then confirms it.
2. Candidate tags are `v<version>-rc<n>`, numbered from zero. Never move or
   delete them.
3. The final tag `v<version>` marks the accepted candidate's commit.
4. A project may spell these refs differently. It records the spelling once in
   its release policy and uses it everywhere. A reader must tell a release ref
   from a workstream branch by name alone.
5. Release refs are not workstream branches. They carry no `ws-` prefix. A
   release branch is associated with a workstream only for the duration of a
   release, only through the workstream-list row.
6. Once a candidate tag points into a release branch, never rebase it, never
   force-push it, never delete it. Tags are immutable. Changed source gets a
   new candidate. A released version that needs a fix gets a new version.
7. Between releases the source names itself by a development marker that
   orders before the release it works toward. The release branch's first
   commit replaces it with the release version. After the final tag, `main`
   reopens with the next development version, the next patch unless the owner
   names another. The spelling and the command are in the local file under
   *Version Scheme*.
8. Work flows from the release branch to `main` by merge, never the other way
   after the cut. Do not synchronize a release branch with `main`. Never
   rebase tested release source onto a moved `main`. Other workstreams keep
   integrating to `main` during a release.
9. While a release is open, only the resource that drives it commits to the
   release branch, and only release fixes. After the final tag the branch is
   closed.
10. Cut a candidate only from source `main` already has. Merge every commit
    the release branch carries to `main` before tagging the candidate. Merge,
    do not cherry-pick.
11. A maintenance release of an already released version starts from that
    version's final tag, not from `main`. Its branch is named for the new
    version and follows every rule above. If its source cannot merge to
    `main`, the candidate gate accepts a documented exception that names who
    authorized it, why, who owns the forward port to `main`, and what
    follow-up closes it. The exception is a reviewed record committed on the
    release branch.

### 11.3 Taking a release over

In `multiple-streams` mode a workstream drives a release: the workstream whose
deliverable is the release's headline. The reserved `maintenance` workstream
drives a maintenance release. `project-management` decides when the headline
is unclear. The product owner decides the cut. For the duration, these rules
replace the ordinary branch rules for that workstream only:

1. Cut from `main`. The workstream merges its working branch to `main` first.
   The release branch starts at that merge commit. Its first commit confirms
   the version. The working branch is then closed.
2. The release branch is the workstream's selection. The list row names the
   release branch, with state `active; releasing <version>`. Edit and publish
   the status file from the release branch. The checkout sits on the release
   branch from the cut to the final tag.
3. Merge the release branch into `main` before each candidate tag, by pull
   request or the repository's delivery method, never by cherry-pick.
4. Closed means closed. Work on the workstream's subject lands only as release
   fixes on the release branch. Commit nothing to the closed working branch.
   Open no new working branch under the name.
5. Afterwards, the workstream resumes on a fresh `ws-<name>/...` branch forked
   from `main`, or concludes. The row's branch association returns to a
   workstream branch. The release branch stays behind, closed.
6. The status file records the release: the cut commit, each candidate and
   its outcome, the accepted candidate, the acceptance record, and the final
   tag. The release policy says what else is recorded.
7. Pausing or blocking during a release follows topic 9, with one addition:
   the row keeps naming the release branch.
8. In `single-stream` mode, the same ref rules apply. `CURRENT-STATUS.md`
   records the open release, its branch, and its candidates.

### 11.4 What the project records

Each project records in `WORKFLOW-LOCAL.md`, under *Release Policy* and
*Version Scheme*: the exact ref spelling if it differs; how a candidate is
built and published; what the candidate gate checks and how an exception is
recorded; the acceptance evidence required and where the acceptance record
lives; the version-bump command. Write that policy before the first release.
In this repository the policy is the
[operator guide for releasing a new version](engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md),
owned by `project-management`. `WORKFLOW-humane.md` carries two worked
examples.

## 12. Records

### 12.1 Requirements

1. Root `REQUIREMENTS.md` is the project-level overview and index of
   requirements that stay true across implementations.
2. `engineering-docs/requirements/product/` holds the canonical record of each
   root requirement. Subproject requirement files hold implementation-specific
   behavior, validation scope, and traceability.
3. Each root requirement record has: a stable ID such as `R-CONC-001`; a short
   title; a type, high-level goal or concrete requirement; a clear statement;
   a priority, `gating`, `wanted`, `optional`, or `later`; a status,
   `proposed`, `accepted`, `implemented`, `repo-validated`, `manually
   validated`, `deferred`, or `rejected`; frontmatter that is easy to
   maintain; validation references or evaluation signals; related tasks, bug
   records, decisions, or completed-task records.
4. A goal is evaluated by judgment and accumulated evidence. A concrete
   requirement must be testable in principle.
5. When a task, bug, or note materially implements, validates, changes, defers,
   rejects, or reinterprets a requirement, add a `Requirements:` line with the
   IDs. If no requirement exists, add a proposed one first, or state that the
   work is exploratory.
6. Do not turn requirement files into a second backlog. The selected status
   file says what to do next. The requirement says why the task exists and how
   important it is.

### 12.2 User-level documentation

1. When you change behavior a user can observe or invoke, update the
   user-level documentation in the same change as the code and the
   requirement. This includes command names and order, options, defaults,
   generated artifacts, setup steps, validation expectations, IDE
   configuration names, and host-exposure behavior.
2. `REQUIREMENTS.md` records the requirement overview. Target user docs, such
   as `devcapsule-src/README.md`, describe how the user does it. Root
   `CURRENT-STATUS.md` records status. Implementation notes record rationale,
   rejected alternatives, and evidence.
3. For every user-visible change, check: a requirement exists, accepted or
   proposed; the user-level README shows the supported command path and
   defaults; unsupported or removed paths are absent from current docs; a
   change to host exposure, credentials, devices, Docker access, or
   persistent state documents the isolation impact beside the option; the
   status file names any manual validation still required.
4. Current user docs show only the supported interface. Historical sections
   may keep old command names.

### 12.3 Draft user documentation

1. Root `docs/` contains only current user-facing documentation.
2. Workstream drafts live at `engineering-docs/wip/<start-date>-<name>/docs/`.
   `docs/` is otherwise a reserved name under `engineering-docs/`, allowed only
   inside `wip/<start-date>-<name>/` and `archive/<start-date>-<name>/`.
3. Store a new user document at its intended relative destination, for
   example `engineering-docs/wip/2026-04-12-api/docs/guides/new-guide.md` for
   `docs/guides/new-guide.md`.
4. For a change to an existing root `docs/` file, do not create a divergent
   copy. Write a change proposal that identifies: the target file; why it must
   change; the intended semantic and wording changes; implementation
   dependencies; final verification.
5. Apply the proposal to the existing document only when finishing a
   successful workstream.

### 12.4 Active tasks

1. The selected status file's active task list contains only work the next
   session on that track should consider doing.
2. Each active task states enough closure detail that the next agent knows
   when to remove it:

   ```markdown
   1. Task title.
      Requirements: R-...
      Done means: ...
      Verification: ...
      Reopen if: ...
   ```

3. Use a lighter form only for very small tasks. State the done condition and
   the verification path before work starts.
4. When the human validates something manually, update the status file so the
   task is not picked up again.
5. When an issue disappears or is deferred, remove it from the active list.
   Preserve its symptoms, logs, and reasoning in the completed-task archive.

### 12.5 Bug records

1. Before filing, apply *Bug Or Feature* in `INFORMATION-MODEL.md`. A bug
   record needs a requirement it threatens or a promised behavior observed
   wrong. A wish is a backlog entry.
2. File under `engineering-docs/bugs/SCOPE/YYYY-MM-DD-short-title.md`.
3. Every bug record opens with frontmatter that carries the controlled fields:

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

4. `status` is exactly one of: `reported`, filed, not yet reproduced;
   `confirmed`, reproduced or evidenced, no fix yet; `fixing`, an owner works
   on it on a named branch; `fixed`, a fix is committed, validation pending;
   `closed`, validated or no longer reproduced, and the record says which;
   `retired`, will not be fixed, with the reason.
5. `severity` is exactly one of: `blocking`, the named `target` cannot ship
   with it; `major`, wrong or unsafe behavior the product claims to prevent,
   with no acceptable workaround; `minor`, everything else; `untriaged`, not
   yet rated. Rating it is the owner's first job.
6. `target` is the release version the fix is meant for, or `none`.
7. `owner` is the workstream that owns the fix, or `none` in `single-stream`
   mode. In `multiple-streams` mode a bug always has one: the open workstream
   whose goal covers it, otherwise `maintenance`.
8. `opened`, and once closed or retired `closed`, are ISO dates.
   `requirements` lists the threatened requirement IDs, or is empty.
9. Prose after the frontmatter never contradicts the fields. Change a field in
   the record, in the same commit as the work that justified the change.
10. A bug with `severity: blocking` and a release `target` blocks that release
    until its `status` is `closed` or `retired`.
11. The record also captures: symptom; environment; reproduction; expected and
    actual behavior; evidence; current hypothesis with its uncertainty;
    verification target; fix notes and close criteria. Include no secrets.
12. A bug record lives on `main`. In `multiple-streams` mode the filer commits
    it on its working branch with `owner` set by rule 7. It reaches `main`
    with the filer's integration. Tell the owner by mail if it must act
    sooner.
13. A bug record is not an intake item. It is not decided. Its `owner` field
    is its routing. Each owner reads its queue from the records on `main` at
    session start. To hand a bug over, change `owner` with the reason recorded
    in the record.
14. The selected status file holds only the next action on a bug.
15. When a bug is fixed and validated, no longer reproduced, or retired: set
    `status` to `closed` or `retired` and fill in `closed`, with the reason;
    add a dated note near the owner's current-state section if future agents
    need to know why it left the queue; move detailed evidence to
    `engineering-docs/completed-tasks/` when the record has served as active
    evidence; state when the bug should be reopened.

### 12.6 Completed tasks

1. Use one file per closed task:
   `engineering-docs/completed-tasks/SCOPE/YYYY-MM-DD-short-task-name.md`.
2. Recommended sections: title; date; status, one of `completed`, `retired`,
   `manually validated`, `no longer reproduced`; original task; requirements;
   done means; verification; environment provenance, with image, launcher
   mode, project mount, and host assumptions; retrospective notes; reopen if.
3. This folder is not a second backlog. It is the evidence trail.

### 12.7 Design decision records

1. Design decision records live in `engineering-docs/decisions/product/`.
   Start from `_template.md` there.
2. Use a decision record when a choice crosses subprojects, changes an
   accepted requirement, or moves a security boundary. Use a decision note,
   topic 12.8, for a local, reversible, implementation-scoped choice.
3. Promote a note that turns out to change a requirement, cross subprojects,
   or set a boundary into a decision record.
4. The ceremony: a human or an agent proposes the record with
   `status: proposed`, at least two real options with honest costs, and a
   recommendation; the human rejects, amends, or asks for more options; the
   human adopts by stating the decision, and `status` becomes `accepted` with
   `date-decided` and `decided-by` filled in; the decision produces or changes
   a requirement, and a task if work follows, each linked from the decision.
5. An agent may propose. An agent never adopts. The agent records the act.
6. Once accepted, the Decision and Rationale sections are frozen. To change
   your mind, write a new record and mark the old one `superseded-by`.
7. Status values: `proposed`; `accepted`; `rejected`; `deferred`, accepted
   direction outside the current target; `superseded`. A decision is never
   `implemented` or `repo-validated`.
8. Write a decision record when: a choice changes scope, architecture, or
   security posture materially; several defensible options remain and the
   choice would be re-litigated; an accepted requirement is reinterpreted or
   superseded; an isolation relaxation is deliberately accepted.
9. Decisions say why. Requirements say what must be true. Tasks say what to do
   next. Do not let a decision record become a backlog.

### 12.8 Decision notes

For a decision that stays local to one implementation and may be revisited,
write a small note under the relevant scope in `engineering-docs/design-notes/`
with: title; date; context; options; decision; consequences; reopen if.

### 12.9 External state

Record state that cannot or should not live in Git, without secrets, in the
current-state section or an implementation note: credentials, GUI logins,
local image tags, manually built images, host firewall behavior, services
outside the container.

### 12.10 The documentation index

1. `index.md` lists permanent documentation with relative links grouped by
   category.
2. When you add, delete, rename, or move a permanent markdown file, update
   `index.md` in the same change.
3. In `multiple-streams` mode, `index.md` lists each open or archived
   workstream's `CURRENT-STATUS.md`, not every internal workstream document.
   The status file's own index lists those.
4. Add promoted documents to `index.md` when they reach their permanent
   location.

### 12.11 Work orders

1. A work order is one markdown file under `engineering-docs/work-orders/`,
   named `YYYY-MM-DD-<slug>.md`. It defines what a workstream is to achieve,
   in enough detail that an intelligent agent, a human or a human and agent
   pair, can take it and run the workstream to completion without the author.
2. A work order states: the outcome; the deliverables, each with what done
   means; the acceptance evidence; the decisions already taken that bind the
   work; the decisions left to the executing workstream and to the owner;
   the stopping points where the owner must be consulted; the mainline
   evidence read before it was written.
3. A work order is written in human language. It may embed formal
   specification in fenced code blocks, for example a `lean` block, a schema,
   or a test. The human language governs. The executing agent derives any
   formal specification it needs from the human language and the embedded
   blocks, when it needs it.
4. A workstream may begin from a work order. The work order is then the
   workstream's goal, and the status file links it.
5. A work order is delivered by mail like any item, by `project-management`
   or by the owner. The recipient acknowledges it as its goal or its tasks,
   or raises disagreement with the human.
6. The author commits the work order under `engineering-docs/work-orders/`
   and lists it in `index.md`. Changes to a work order after delivery are new
   items that say what they supersede. The recipient's status file records
   what it accepted.
7. A work order is not a requirement, not a status file, and not a release
   plan. Requirements it depends on are cited by ID. Decisions it depends on
   are cited by record.

### 12.12 Materialized views

1. A human-facing document whose content derives from records is a
   materialized view. The records are the source. The view is never the
   source of anything.
2. Every view records its dependencies inside itself: the records it was
   built from, with their content ids at build time. An authored view, one
   an agent writes, records them per section against the source section it
   explains. A rendered view, one software produces, records them per file.
3. Software detects a stale view by comparing the recorded content ids with
   the current records. A stale view is shown as stale, never silently
   served as current.
4. Regenerate a view on demand. Where the derivation is mechanical, software
   regenerates it. Where the derivation needs judgment, software produces an
   agent task from the dependency difference, naming the section, its
   recorded text and its current text, and an agent regenerates the view
   from that task.
5. A human reviews a view and asks for changes of wording or style. A human
   does not maintain a view. Do not write a new hand-maintained human copy of
   anything derivable from records.
6. The humane companions of this file and of the local file are authored
   views: each paragraph depends on the rule it explains. The web console is
   the home of views and of their staleness.
