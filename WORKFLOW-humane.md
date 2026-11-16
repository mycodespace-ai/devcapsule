# Human / Agent Iteration Workflow: The Reasons

*For humans.* This file explains [`WORKFLOW.md`](WORKFLOW.md). It carries no
rule of its own. For each group of rules it repeats the rule in a sentence,
states the effect the rule is meant to have, and gives the motivation behind
it. An agent skips this file in ordinary work and returns to it when the rules
do not settle a decision. The numbering follows `WORKFLOW.md`'s topics. The
last section maps the section names of the previous edition onto the new ones.

## 0. Why This File Exists

**Rule.** `WORKFLOW.md` states rules in a controlled style, one rule per
sentence, grouped by topic, and keeps the reasons out.

**Intended effect.** An agent reads the rules in a third of the tokens the
previous edition took, finds every rule about one topic in one place, and does
not have to separate what is binding from what is explanation.

**Motivation.** The previous edition mixed rule and reason in the same
paragraphs. That served a human reader well on first contact and served every
later reader poorly: each session re-read the arguments to find the
instructions, and the length invited skimming, which is how rules get missed.
Splitting the two lets the rule book be short and lets this file be as long as
the reasons need. The rules are the same. Only their presentation changed.

## 1. How To Read, And The Intents Behind Every Rule

**Rule.** Read the glossary first, then whole topics; treat numbered lists and
imperatives as binding; skip *for humans* material in ordinary work; report
conflicts between rules as defects; where the rules are silent, use judgment
and record it; the definition binds where it speaks and the local file where
it is silent.

**Intended effect.** Every agent, whatever its vendor, follows the same
protocol from the same text, and every human can see which text is binding.

**Motivation.** This workflow structures how a human and a coding agent build
software together. Its purpose is to make that pair more productive than
either would be alone. It tries to achieve that by removing specific frictions
rather than by adding process. Every rule is meant to pay for itself. The rules
follow from a small number of intents. Read a rule against these when it seems
arbitrary, and reason from these when the rules are silent.

- **Resumability.** A competent pair should be able to open the repository
  cold, discover the current state, and continue, without the conversation
  that produced it. Sessions end abruptly, models change, context windows
  fill, and people forget. So state lives in committed files rather than in
  chat, exactly one document is authoritative for each effort, and the next
  step is written down rather than remembered. A workflow that only works
  while someone remembers the last conversation is not a workflow.
- **Low-ceremony coordination.** Coordination should cost as little as it can
  while still working. Where several efforts run concurrently, the structure
  exists to keep them from colliding, not to schedule them, gate them, or make
  them negotiate. Contention is treated as a design failure rather than
  something to arbitrate. Prefer conventions that make conflicts impossible
  over procedures that resolve them, and prefer a rule an agent can apply
  alone over one requiring a round trip.
- **No accidental loss of knowledge.** Anything of importance surfaced during
  development is recorded in the source tree and is predictably discoverable.
  A fact stored somewhere nobody thinks to look has been lost as surely as one
  never written. This is why documents have assigned roles and fixed
  locations, and why an index exists at all.
- **Judgment where the rules are silent.** The workflow is incomplete and says
  so. What it does not expressly deny is allowed, and a pair meeting an
  unforeseen situation decides for themselves rather than stalling. The
  obligations that keep this safe are in topic 3.
- **Retrospective value, subordinate to the work.** Record enough about how
  the project evolved to support later analysis and rediscovery of reasoning.
  But the source tree's first purpose is the software. Process records are
  placed so that someone reading the code can ignore them entirely.
- **Explicit decision rights.** The pair is not two interchangeable actors.
  Mechanical, reversible, and evidently intended work is the agent's to do
  without asking; product intent, ambiguity that changes the outcome, and
  irreversible or outward-facing acts are the human's. The rules say which is
  which at each point, because an agent that asks about everything is useless
  and one that asks about nothing is dangerous.
- **Portability across agents and projects.** The workflow must work for any
  capable agent and in an adopter's repository. It therefore lives in plain
  markdown, depends on no tool-specific storage, and keeps project-specific
  facts separate from the reusable protocol.

**When the intents conflict.** They will. Recording everything serves
knowledge and violates low ceremony. Full retrospective detail competes with a
source tree that stays about the software. Judgment sits in tension with
predictability. Three tiebreaks, in order: resumability wins, because it is the
purpose the others serve; write what changes future behavior and skip what
merely proves work happened, asking what a reader would do differently having
read it; prefer one durable record to several, because duplication is how
records drift apart and stop being trustworthy.

**The *for humans* marker.** A file or section that opens with *For humans*
carries explanation, not rules. `PREAMBLE.md` says why the workflow is what it
is; `INFORMATION-MODEL.md` draws what it stores; this file says why each rule
exists. Explanation and examples for end users live in the project's user
documentation, which explains these terms and defines none of them.

## 2. The Glossary And The Reference Vocabulary

**Rule.** Every term with a fixed meaning is defined once, in plain words, with
what it must not be confused with. Older names stay synonyms for one release.

**Intended effect.** Humans and agents mean the same thing by "status file",
"workstream list", "record", and the rest, and a renamed term does not break a
reader of last release's text.

**Motivation.** The information model's first failure mode was six things
called by two names each, and several names shared between unlike things: a
bug's `status` and a workstream's state, a status file and the status it
records, a registry of workstreams and a registry of images. Defining each term
once, with its anti-definition, is cheaper than disambiguating in every rule.

**Why the Workflow Patterns vocabulary.** Where the rules need a precise word
for a piece of process, they use the base terms of the Workflow Patterns
initiative (van der Aalst, ter Hofstede, Russell and others). Its base terms
are ordinary words humans and agents already know, and its catalogue gives a
shared, neutral name to a shape of process when one is needed. The three
limits in topic 2.6 keep this useful rather than ceremonial: rules stay in
plain English, pattern names appear only where they shorten a rule, and this
file's own definitions win inside this file. **Milestone** is the known
collision: here a planning unit, in the catalogue a control-flow pattern.

**Why validation has a vocabulary.** The kinds of check are named the same in
every ecosystem so that an agent arriving on any project knows what "the gate"
or "a smoke test" means before it reads the local file's commands. The local
file's *Validation Commands* says which kinds exist here and how each runs.

## 3. Judgment Where The Rules Are Silent

**Rule.** What the rules do not expressly deny is allowed; establish silence
before invoking it; express denials are never silence; contradictions are
defects; record every exercise of judgment; send recurring gaps to the
workflow's owner.

**Intended effect.** A pair is never stopped by a gap in the rules, and every
gap it meets becomes visible to the people who write the next edition.

**Motivation.** This workflow is incomplete, and the project says so rather
than pretending otherwise. It was written from real use, and real use keeps
producing situations it does not describe. Being stopped by silence is itself a
failure: the protocol exists to make work possible and legible, not to
authorize each step of it. The guard rails matter as much as the permission. A
rule that is inconvenient, costly, or arrived at for reasons no longer visible
is still a rule; change it through the owning workstream rather than around it.
Express denials are decisions already made, usually because the failure they
prevent is expensive or irreversible. Unrecorded judgment means the gap stays
invisible, the next pair re-derives it differently, and two projects using "the
same" workflow quietly diverge. Recorded judgment is how the next version of
the rules gets written. This is a V1 position adopted 2026-08-17, for a
workflow young enough that its gaps outnumber the cost of specifying them.

## 4. Declaration, Local Workflow, And File Roles

### 4.1 The declaration and the declared version

**Rule.** The `[workflow]` table names the definition, its version, and the
mode; the declared version governs; tools never refresh the definition as a
side effect; a mismatch is a defect to report.

**Intended effect.** A project runs one known edition of the rules, whatever
newer text a contributor's tool or agent happens to know.

**Motivation.** A contributor's tool may be newer than the project's workflow,
and a contributor's agent may have been trained on a newer text. Neither
changes the rules the project runs; the file in the repository does. The
version is a DevCapsule release because the definition ships inside each
release and release tags are immutable, so every edition is readable for good
at its tag with no second numbering scheme. The mode selects a repository
protocol, not runtime behavior or live presence, which is why reading it is the
first act and guessing it is forbidden.

### 4.2 The local workflow file

**Rule.** `WORKFLOW-LOCAL.md` holds what only one project can decide, such as
an integration branch called `master` or `trunk`, or a version scheme where a
Python project says `0.2.14.dev0` then `0.2.14` and a Maven project says
`0.2.14-SNAPSHOT`; *Validation Commands* is required and runnable as written;
contradictions of the definition are recorded exceptions; bootstrap writes the
file once.

**Intended effect.** A contributor can rely on the generic half being identical
everywhere, and can find the project's own facts in one predictable place.

**Motivation.** The definition is the generic half: installed, versioned, the
same in every project. The other half depends on ecosystem, hosting, and
history. Filling the definition's silence is the ordinary job of the local
file, not an exception to it; only a contradiction is an exception, recorded so
that it is visible and reportable, and so that it signals where the definition
should have been silent. *Validation Commands* is the one required heading
because it is what lets any agent on any project build the software and run
its tests without guessing. "The tool is missing" is a finding only after
following that section, which the project wrote so that the question has an
answer.

### 4.3 to 4.5 File roles, subproject roles, bootstrapping

**Rule.** Each markdown file has one assigned role and location; the active
subproject and the historical one are kept distinct in user-facing docs; the
same process is bootstrapped into any repository the environment is used on.

**Intended effect.** A reader knows where to look for a kind of fact, and an
agent knows what not to load.

**Motivation.** Assigned roles and fixed locations are the mechanism behind
"no accidental loss of knowledge": a fact in the right place is discoverable,
one somewhere convenient is lost. The subproject split exists because the
historical PyCharm shell remains a useful baseline but presenting it as the
development path misleads newcomers. Bootstrapping exists because the Docker
image and launcher provide the working environment while the mounted project
is the source of truth; a process that lives only in this repository would not
travel with the environment.

## 5. Checkouts, Branches, And Git

### 5.1 and 5.2 Relationships and claimed refs

**Rule.** A checkout has one current branch and therefore at most one selected
workstream; the workflow claims only `main`, `ws-` branches and release refs;
everything else is the project's; one checkout works one workstream at a time,
from a clean tree.

**Intended effect.** Every "current" in the rules has one meaning, two pairs
can hold different current workstreams without either being wrong, and an
adopting project keeps its own branch namespace.

**Motivation.** The terms project, remote, checkout, branch, workstream, and
pair are used precisely and never interchangeably, because the protocol is
defined in terms of branches, not directories. Mixing two workstreams'
uncommitted changes in one directory is the failure the protocol exists to
prevent. Genuine concurrency comes from several pairs in several checkouts
integrating through the remote, not from any local arrangement of directories.
Nothing about a checkout is registered, which is why the workstream list is a
record rather than a presence or locking system: a workstream listed as active
means someone opened it and has not concluded it, not that anyone is working on
it right now. Two pairs may select the same workstream; they will contend on
one status file, and the usual result of an accident is a conflict in that
file rather than lost work. The `ws-` form lets a reader tell a workstream
branch without the list; the list row is what makes the association true,
which is why an older-named branch is still its workstream's.

### 5.3 Git hygiene and commit cadence

**Rule.** Check status before editing; keep unrelated changes out of commits;
one message per saved state; commit each coherent unit as it is finished.

**Intended effect.** An interruption loses at most one unit of work, and the
order in which decisions were made survives.

**Motivation.** An uncommitted session is one interruption away from losing
not just the changes but the order of decisions, which is the part no one can
reconstruct. Committing is cheap and local; it is not publication, and it does
not require the work to be complete. A checkpoint is a statement about project
state and belongs in the status file; a commit is a save point.

### 5.4 Verifying shared branch state

**Rule.** Use `git cherry`, not ancestry, to learn whether work has landed;
reset a diverged local ref only when every local commit is proven upstream, and
report the evidence; otherwise stop and ask; never force-push `main`.

**Intended effect.** An agent never redoes integrated work and never discards
history on a guess.

**Motivation.** Two questions about shared refs are easy to answer incorrectly
by inspection. A squash, a rebase, or a merge queue rewrites commits, so
`git merge-base --is-ancestor` answers "no" for work that is fully integrated;
an agent that trusts it concludes the merge failed and redoes the work.
Comparing by patch identity answers the real question. When a local ref and
its remote have both advanced, the divergence is usually an artifact of
rewritten history; resetting then discards nothing, and the agent may do it
alone provided it reports the counts and the `git cherry` output it relied on.
If anything is genuinely missing, choosing a side is the human's call.

### 5.5 Staying current with `main`

**Rule.** Synchronize at stage boundaries, before substantial slices, and
before integration; propose the judgment at session start; rebase only what
was never pushed; after your own delivery lands, fast-forward or reset rather
than rebase; resolve mechanical conflicts and hand semantic ones to the human.

**Intended effect.** A branch never drifts far enough that a conflict becomes
unaffordable, and a session never decides against stale rules.

**Motivation.** Mail and live state travel the coordination branch, but
everything the project has agreed on travels `main`: the definition, the
requirements, the decisions, and every workstream's records as of its last
integration. A workstream that does not watch `main` works against a project
that has moved on. The `Definition read:` stamp exists so nobody types a hash
and a rewritten history cannot confuse the comparison. Rebasing a published
branch rewrites shared history and needs a force-push; merging `main` in is
safe. After a delivery lands under a squash or rebase, the branch's commits
have different identities from the ones `main` carries; rebasing then replays
them onto a `main` that already contains their effect and conflicts on
intermediate states even though the end states agree. Rebase is for carrying
unlanded work forward.

### 5.6 Integration is a merge commit

**Rule.** One merge commit per reviewed deliverable; never fast-forward, never
squash; read `main` by first parent; never rewrite pushed history; a project
that prefers squash records the exception and its consequence.

**Intended effect.** `main`'s first-parent history is the story, one entry per
delivery, and every commit a record cites remains a real commit in every clone.

**Motivation.** The branch's own commits stay reachable unchanged below the
merge line, so the order of decisions the small commits preserved survives the
moment the work is shared. Under squash those commits stop existing when the
branch does, which is why a project that prefers squash must cite pull requests
and tags rather than branch commits. The engineering source for the choice is
the merge-strategy note under `engineering-docs/implementation-notes/workflow/`.

## 6. Single-Stream Mode

**Rule.** Root `CURRENT-STATUS.md` is the status file; branches are the unit of
work; the general topics apply as they did before multiple-stream support.

**Intended effect.** A small project pays no coordination cost it does not
need.

**Motivation.** The single-stream mode preserves the linear process the
workflow began with. Multiple-stream mode is an addition for projects with
several concurrent efforts, not a replacement.

## 7. Workstreams

### 7.1 Definition and restrictions

**Rule.** Fourteen restrictions: flat workstreams; unique names; immutable
start dates; `ws-` branches belong to one workstream; `main` belongs to none;
one status file each; the list holds open workstreams only; no file
exclusivity except three carve-outs; reserved names; records travel the working
branch; no autonomous workstream change.

**Intended effect.** Concurrent work stays understandable: a reader can tell
from a branch name and the list who owns what, and no workstream can rewrite
another's account of itself.

**Motivation.** Flatness and unique names keep routing trivial. The start date
is immutable because it is part of the directory name, which is part of every
link. Restriction 11 is deliberately permissive about files, because inferring
exclusivity from subject or directory would make every cross-cutting change a
negotiation; the three carve-outs are each a workstream's account of its own
state, which another workstream cannot restate accurately. Restriction 14 is
the explicit-decision-rights intent applied to the one act that most often
goes wrong: an agent that infers authority to switch workstreams from task
subject, urgency, or a convenient second checkout mixes two efforts' state and
leaves neither resumable.

### 7.2 Initialization

**Rule.** Set the mode, convert the root status file into the list, create both
reserved workstreams, create the directories, all in one commit on `main`.

**Intended effect.** Every multiple-stream project has the same starting shape,
whether it adopted the mode at creation or later.

**Motivation.** A project missing a reserved workstream has nowhere to route
unowned work or unowned bugs; reporting that is safer than inventing a home.
Ordinary workstreams begin only when there is real work, because an empty
workstream is a row that misleads.

### 7.3 The reserved `project-management` workstream

**Rule.** It owns priorities, sequencing, dependencies, lifecycle decisions,
routing of unowned work, and triage of the pile of ideas; it is not a second
list, not a catch-all, and
not the owner of others' state; its authority is advisory and recorded; it is
permanent; it retires only on migration to single-stream.

**Intended effect.** Portfolio work has a durable owner without that owner
becoming a bottleneck or a second source of truth.

**Motivation.** Coordinating a portfolio is itself continuing work that belongs
to no bounded effort. Without a reserved home it either lands in whichever
workstream is selected, distorting its scope and record, or survives only in
conversation. The three exclusions keep it from absorbing the project. It does
not gate other workstreams' commits, integrations, or checkpoints, because
gating is the ceremony the low-ceremony intent forbids. Its own intake is the
last queue that can be emptied on migration because once it is gone there is
nowhere left to forward anything.

### 7.4 The reserved `maintenance` workstream

**Rule.** It owns bugs whose `owner` names it, keeps the queue triaged, drives
maintenance releases, reads its queue from `main`, balances load by branches
and pairs, and is permanent.

**Intended effect.** Every defect has an owner from the moment it is recorded,
and the list can show commitment to a bug nobody else covers.

**Motivation.** Without a reserved owner, a bug either waits for a feature
workstream that happens to be open on its subject, and there may be none, or
is filed and nobody is committed to it. The exclusions matter: a bug inside an
open workstream's subject is fixed at the source; work that changes what the
product does is a feature and a reason to begin a workstream; the bug records,
not the status file, are the queue and the evidence. A defect cluster large
enough to have its own goal and end is an ordinary workstream, not a second
permanent one.

### 7.5 and 7.6 Beginning a workstream and the open-work directory

**Rule.** Register on `main` in a fixed sequence, publish, then work only on
the workstream's branches; the open-work directory has fixed kinds of
content; the status file stays short and sheds history into dated records;
every document is indexed once with when to open it.

**Intended effect.** A workstream exists for everyone the moment it is
published, and a session loads only what it needs.

**Motivation.** A branch created before the registration commit cannot be
told from an experiment. The directory's contents are fixed in kind so a reader
knows what to open and an agent knows what not to load. The status file is read
in full at every session start, so its length is a tax on every session; a
bounded file that sheds history is the only sustainable shape. What the status
file says about the past is where to look, not what happened. The index is how
a reader decides what to load; the dated documents are how a workstream's size
stays out of every session's context.

### 7.7 Workstream states

**Rule.** Exactly one of active, paused, blocked, integrating; a blocked
workstream names its blocker.

**Intended effect.** Whoever considers resuming knows whether a decision or an
event is needed.

**Motivation.** Paused and blocked look alike from outside and behave
differently. A paused workstream needs someone to choose it. A blocked one
needs its blocker cleared, so it must name the blocker and what would clear
it, or nobody can tell when it became resumable.

### 7.8 and 7.9 Selecting and changing workstream

**Rule.** The current branch determines the workstream; explicit intent
chooses a target but does not move the branch or mix dirty state; invalid
routing stops editing; `main`, detached HEAD, and unregistered branches have
no default; the coordination branch is never checked out for work; after work
begins the selection is sticky and changes only on specific human direction.

**Intended effect.** No session edits under the wrong workstream, and the
human, not the agent, decides every change of workstream.

**Motivation.** Discovery and selection are related but distinct: the live
list says what exists, the checkout's branch says what this pair is on. The
protocol deliberately defines no second untracked "current workstream" file,
because a file that can disagree with the branch is a second source of truth.
A request that exposes work belonging elsewhere is not an instruction to go
there; neither is an agent's view that another workstream fits better.
Completion of the target does not authorize an automatic return, for the same
reason. Read-only inspection and the coordination commands are not changes
because they touch no workstream's files.

## 8. Mail, Intake, Decisions, And The Coordination Branch

### 8.1 and 8.2 Items, taking, and the two decisions

**Rule.** One item per dated file stating what, why the recipient, the
evidence, and what accepting means; the sender assigns no priority; delivery
is by mail without waiting for integration; sent mail is append-only; every
item ends acknowledged or forwarded; items from `project-management` are not
forwardable; `project-management`'s own decisions are terminal; intake gates
completion.

**Intended effect.** Work handed between workstreams is never lost, never
silently ignored, and never circulates forever.

**Motivation.** The intake directory is the only place another workstream may
write inside a workstream's open-work directory, because a protocol that
forbids all such writing has no way to hand work over. Announcing a handoff in
the sender's own status file does not deliver it: the recipient reads its own
status file at session start, so an item recorded anywhere else is invisible to
the workstream expected to do it. An item that waits for the sender's
integration is invisible for as long as that takes, which reproduces the
failure the mechanism exists to fix. Ownership is asymmetric so that a
workstream's account of itself remains its own. Scheduling is not a third
outcome because "later" is a property of work a workstream owns, not a way to
avoid owning it; recording an opinion about an item is not acknowledging it.
Routing on forward is `project-management`'s decision because that workstream
is authoritative for what is worked on, by whom, and in what order, which is
also why its items cannot be forwarded back: that would be a loop. Its own
decisions are terminal because it has nowhere to forward to, which is what
stops a refused item from circulating indefinitely. Intake gates completion
because leaving items behind would silently destroy work other workstreams
handed over in good faith. Intake is a queue, not an archive; Git retains
every item and every reason.

### 8.3 The decision log

**Rule.** One append-only log per workstream, written only by the recipient in
the commit that removes the item, one line per item, never pruned, carried into
the archive.

**Intended effect.** A sender learns what became of what it sent by looking in
three predictable places, and a later reader reopening a decision finds its
trail.

**Motivation.** The invariant is the whole value: every item ever sent is in
exactly one of mailbox, intake, or log, never two, never none. Taking and
deciding are each one operation so that the invariant holds at every commit.
This is also why no reply is written back into the sender's intake: a reply is
not work, and a queue whose whole meaning is "own this or forward it" should
not carry messages that are neither. The reasoning belongs in the status file,
where a decision is argued; the log records that it happened and points at it.

### 8.4 The coordination branch

**Rule.** One shared branch on the remote carries mail and published state;
never merged into `main`, never reset, never force-pushed; senders add, only
recipients remove; the tool works through plumbing and the plain-git
equivalent follows the same rules.

**Intended effect.** A message between workstreams never needs `main`, and no
human opens a pull request whose only content is somebody's records.

**Motivation.** Intake defines where an item lands; the coordination branch is
how it travels. The earlier outbox design had the right one-way flow but put
the buffer under the wrong owner and the records behind a pull request nobody
reviewed. Append-only history and compare-and-swap pushes make races harmless:
racing commits touch different files, so a retry from a fresh fetch never
conflicts. The party that empties the mailbox is the party that has provably
received its contents.

### 8.5 Published state, claims, and the brief

**Rule.** Publish pushes the working tree's status file and decision log
verbatim; publish at checkpoints, pauses, and finish; the published copy is the
truth while the workstream is open; claims inform and never refuse; the brief
is read first.

**Intended effect.** Every checkout sees every workstream's live state and who
is on what, without any workstream waiting for integration.

**Motivation.** What is published is what the pair is looking at, committed or
not, so the live view is never behind the checkout and the two copies can lag
but never disagree. Claims are information, not locks, because locking source
control is the failure Git exists to end; a crashed session's claim simply
expires. The brief exists so that the session's context arrives in one command
rather than in a dozen reads; the judgment it suggests stays the agent's to
propose and the human's to accept.

### 8.6 and 8.7 Records travel with the deliverable; misplaced changes travel as patches

**Rule.** Records are published live and carried to `main` inside the
deliverable's integration; nothing is merged for a record's sake; a bounded
change found to belong elsewhere is sent as a patch in an item and reverted
from the sender's checkout, never committed on the wrong branch.

**Intended effect.** Humans review deliverables, never records, and no agent
starts another workstream's implementation by accident.

**Motivation.** Two kinds of file travel differently because one is reviewed
and the other is the project's view of a workstream in flight. Two versions of
one record is the failure the mechanism exists to avoid, hence verbatim
publication. The patch rule exists because the alternatives are worse:
committing on the wrong branch mixes two workstreams' deliverables, and
switching workstreams to finish it violates restriction 14. A patch is a
proposal; the recipient owns application, validation, and integration. Landing
a finished slice early is permitted because a correction other workstreams are
waiting on should not sit behind work that has months to run.

### 8.8 Handing a decision to the human

Present a choice with several options as a temporary decision document and
numbered chat text. Inside a capsule with console tools, build it with
`devcapsule project checkout decisions from-table`, save its output in the
console's decisions directory, and present it with `hand-off`. End with the
link when the command supplies one. Without the tools, give the numbered
text directly. Both chat and page answers count; a chat answer wins for the
same item. This keeps the choice accessible without requiring a browser.

Read page answers from capsule state and record outcomes under the existing
rules before deleting the document and answer. Keep unanswered items pending.
Intake choices must follow topics 8.2 and 8.3, including project-management's
terminal outcomes; the builder's generic accept, decline and defer defaults
cannot replace those rules. Design decisions still need the records that
topic 12.7 requires. Capsule-state deletion is not a Git operation. Neither
the document nor its answer belongs in Git, and tokened links belong only
in chat. This separates the temporary question from its durable outcome.

Send other environment notices through `notifications post` when available,
or in chat otherwise. Notification files are capsule state. Durable facts
still go into the normal records. The notification channel tells the human
what happened without replacing the project's memory.

## 9. Sessions

### 9.1 to 9.4 Start, resume, pause, open threads

**Rule.** Start with the brief, mail, the live list, the status file, and the
intake; propose the synchronization judgment before planning; read *Open
Threads* before planning; verify external-state claims; pause with a small
ceremony that commits, updates, writes open threads, takes and sends mail,
publishes, records external state, sets the row, and releases the claim.

**Intended effect.** A resumed workstream is resumed at the level of
reasoning, not of tasks, and a paused one tells whoever considers it why it
stopped.

**Motivation.** The synchronization judgment is ordered because the first fact
dominates: if the definition changed, the rules the session is about to follow
are the ones that changed. Tooling supplies the facts, the agent weighs them,
the human decides only when the weighing says it matters. Pausing is placed
where the knowledge is: only the pair stopping work knows whether a thread
finished or was suspended, and they know it at the moment they stop; asking on
return is guesswork after the information is gone. A paused workstream holding
unsent mail blocks its recipients without telling them. A blocked workstream
nobody was told about is indistinguishable from an abandoned one. *Open
Threads* is deliberately about ten lines so that it cannot become a dumping
ground: a rejected option with no recorded reason gets re-proposed, and a
question not written down gets re-derived. Conversational replay is not a goal:
context is cleared, models change, and a replayed transcript is expensive to
read and mostly noise; what is worth carrying is the reasoning. Depending on
any agent's session-resumption feature would break portability, so capture is
repository-level by construction. Status files record facts that were true at
pause; containers exit, ports are taken, branches move.

### 9.5 to 9.7 The work cycle, reporting, responsibilities

**Rule.** Frame the slice, define closure, execute one narrow slice, report
with evidence, decide the next step; size slices to one of five shapes; ask
for input only when it changes the work; escalate on material scope, security,
insufficient evidence, external state, or speculation; report outcome,
evidence, gap, next slice; never report a check as not runnable without
following the validation section.

**Intended effect.** Steady throughput that the human can validate at each
step, instead of long agent runs with vague status.

**Motivation.** Each cycle is a small contract between the human and the
agent. Defining closure before deep work is what lets the human validate the
result. One coherent change beats several partially finished ideas because a
half-finished idea has no evidence. The slice shapes are the sizes a human can
review in one pass; a task too large to validate in one pass is split before
implementation, not after. The input rule is the explicit-decision-rights
intent at turn level: the smallest reasonable assumption, stated, keeps the
work moving; a material change in scope or security stops it. Reports lead
with the result because the human should not reconstruct state from a
chronology. The not-runnable rule exists because "the tool is missing" was the
most common false report; the project wrote the section so the question has an
answer. The human chooses the hill to climb; the agent chooses the next safe
foothold; both expect each slice to end in evidence or an explicit blocker.

### 9.6 rule 5 Controlled language for reports and records

**Rule.** Reports to the human and human-facing record text are written at
about 80% ASD-STE100: one fact per sentence, short sentences, active voice,
the glossary's terms. Code, commands, quotations, and tables are exempt.

**Intended effect.** A human reads an agent's report or a status file in the
time it deserves, with no sentence to re-read, and two agents writing about
the same thing use the same words for it.

**Motivation.** Owner decision of 2026-10-09, after the controlled-language
edition of this definition measured a quarter fewer tokens and a third as many
long sentences with no loss of rules. Karpathy's observation of 2026-10-02 was
the prompt: as agents do more of the work, the human's job moves to
understanding their output, and a controlled language is the cheapest way to
make that output readable. ASD-STE100 was built for maintenance documentation
read under time pressure by people whose first language was often not English,
which is the position of a human reading an agent's report at the end of a
long session. Eighty percent, not a hundred, because the full specification
forbids words the project needs and permits only an approved dictionary; the
glossary is this project's dictionary. The exemptions exist because code and
commands are exact, quotations are someone else's words, and tables already
hold one fact per cell. Existing records are not rewritten, for the same
reason old section names are not: records are history.

### 9.6 rule 6 Diagrams first, in DOT

**Rule.** An explanation with structure is given as a diagram first and prose
second, in the DOT language, in a fenced `dot` block, rendered by Graphviz and
related software; no other notation; an image only where no renderer is
available, with the source beside it.

**Intended effect.** A human parses the shape of a thing from a picture in
seconds instead of reconstructing it from paragraphs, and every diagram in the
repository is in one notation that both humans and agents write fluently.

**Motivation.** Owner decision of 2026-10-09, from Karpathy's post of
2026-10-02: "Instead of writing, ask your LLM to create a diagram. These can
be a lot easier to process, parse, and understand." The point is general, not
about workflows: whenever an agent would explain structure in prose, the
diagram is the better output. DOT was chosen over Mermaid and PlantUML because
it is the notation of graphs as mathematics knows them, nodes and edges, with
decades of examples that make every model fluent in it, with layout engines
that handle large graphs and clusters, and with renderers that run anywhere
from the command line to a vendored JavaScript file in the capsule's web
console. One notation rather than two keeps the choice out of every diagram.
GitHub does not render DOT inline; the console does, and an image with the
source beside it covers the rest. State machines are one case of structure,
not the rule's subject; the first applications in front of the project are
the configuration composition boundary, the three places an intake item can
be, the console's process topology, and a release's branch and tag history.

### 9.6 rule 7 Recorded visual tests, and the no on explainer videos

**Rule.** Prefer a recording harness for end-to-end tests of visual software,
keep the recording as acceptance evidence under
`<e2e-root>/evidence/<scenario-id>/scenario-video.webm` inside the project
mount, ignored by Git and outside build directories that a clean build removes,
and do not generate explainer videos for the human.

**Intended effect.** When a test says an IDE came alive and a file was saved,
a human can watch it happen through the capsule web console without a clean
build deleting the movie, every agent writes scenario evidence to the same
project-relative path, and nobody spends tokens producing a narrated video
about work when the recording of the work itself exists.

**Motivation.** Owner decisions of 2026-10-09, closing the last item of the
Karpathy list, and 2026-11-14, standardizing the scenario evidence path after
two agents placed `.webm` recordings in different trees (`dist/` vs `e2e/`).
His fourth step, bespoke generated explainer videos, was judged not worth
adopting: one owner, a text-native project, no evidence of need, and a recorded
no so that nobody reopens it without new evidence. The recording preference is
the exception that the discussion surfaced: the IDE smokes of 2026-10-04 kept
Playwright movies and screenshots of IntelliJ, Rider and Eclipse coming alive
and saving a file, and those recordings were what the owner could accept at a
glance when a textual report could not have carried the same conviction. Placing
scenario recordings under `<e2e-root>/evidence/<scenario-id>/scenario-video.webm`
keeps them inside the project mount (where the web console can serve them),
colocated with `scenarios/` under the project's single end-to-end test root,
and safe from `dist/` wipes. The rule is a bias, not a mandate, because some
visual software cannot be driven by a recording harness; where it can, the
recording is the cheapest acceptance evidence there is.

**The example, as this project does it.** Recorded scenarios in
`devcapsule-src/tests/e2e/scenario_recorder.py` load `<scenario-id>` from
`devcapsule-src/tests/e2e/scenarios/<scenario-id>.json` and write
`scenario-video.webm`, `poster.png`, `step-NNN.png`, and `scenario-result.json`
under `devcapsule-src/tests/e2e/evidence/<scenario-id>/`. Surface-level IDE
smokes in `devcapsule-src/tests/e2e/ide_session.py` and `visual_smoke.py` open a
Playwright browser context with `record_video_dir=<evidence directory>` and
`record_video_size=<viewport>`, drive noVNC to the IDE, capture screenshots at
asserted moments, and save the context's `.webm` movie alongside the report
under `devcapsule-src/dist/e2e-evidence/ide-smoke/`. Any other harness
qualifies if it can produce the same three things: a movie of the whole
session, screenshots at cited moments, and a report that names both.

### 9.8 and 9.9 Checkpoints and session close

**Rule.** Refresh durable state at closure points, after manual validation, on
new bugs, decisions, or requirements, at session end, when the next step
changes, and when the way the software is built or tested changes.

**Intended effect.** The next session starts cleanly from a file, not from
memory.

**Motivation.** Frequent small updates beat one large retrospective rewrite
because the rewrite is where facts get lost. The build-and-test trigger exists
so that *Validation Commands* never drifts from how the software is really
built; the same commit that changes the build changes the instructions.

### 9.10 Session records

**Rule.** Only on explicit request; detailed by default, summary on request,
verbatim only from a supplied export; redacted; supplementary to the canonical
files; indexed.

**Intended effect.** A consequential conversation can be preserved when a human
wants it, without session records becoming a second source of truth.

**Motivation.** Inferring the request from length or importance would fill the
repository with transcripts nobody asked for. A reconstruction presented as a
transcript would be a false record. Decisions, requirements, bugs, and next
work propagate to their normal files so that no future agent must read a
session record to find the next task.

<a id="911-the-review-partner-loop"></a>

### 9.11 Pair Review Loop

**Rule.** Call the process **Pair Review Loop**, or **Pair Review** for short.
One slice, two agent pairs of different engines: the implementor
opens PRn, writes a brief that is the review partner's only context, and the
partner answers with PRn.1 from its own checkout, a pull request against
PRn's branch with findings, evidence and unimplemented proposals; the
implementor reads the diff, posts a labelled assessment, merges or pushes
back, at most three rounds; the full gate runs on the merged branch; the
human merges PRn.

**Intended effect.** Every slice is read closely by a second mind before the
human sees it, the second mind's work is a diff rather than an opinion, and
the whole exchange is on the pull requests where anyone can audit it. A
different engine is chosen on purpose: two models of the same family share
blind spots.

**Motivation.** The owner chose the name on 2026-10-30: the analogy to pair
programming is easier to remember, and "Loop" emphasizes iteration. It
replaces "review-partner loop" without changing the review rules.

The owner ran the pattern by hand on pull requests #170 and
#171 in October 2026 and on 2026-10-09 directed the agent to orchestrate it
for the capsule web console. Eleven slices (#184 to #205) each received a
review pull request from a Codex pair, ten merged without a round and one
after a round. On 2026-10-11 the persistent session diagnostics ran the same
loop (#207 to #212); the reviewer's "proposals not implemented" twice named a
defect in the design, a thread outside the supervisor's signal mask and an
exit the supervisor reaped first. The process record of 2026-10-12, sent to
the trading-research sample project, drew the lessons the rules encode: the
brief is the only context, so it lists files in reading order and asks
concrete questions; a reviewer that runs its own gate and reports counts and
limits is trustworthy, one that only summarizes is not; the implementor must
read the diff, because twice the summary was right and the diff needed a
decision the summary did not state; accepting without a round and pushing
back are both decisions with reasons and both go into the record; a round
took twenty to forty minutes of wall time, most of it the reviewer's gate,
and three rounds were always enough. The loop sits in topic 9 because it is
a way of running the work cycle, not a new record or a new ref; the local
file names the engines, the checkouts and the commands.

**Rule, added 2026-10-29.** Run the loop only when the human asks for it,
for a task or for a session, or when the local workflow file makes it the
default procedure.

**Intended effect.** An agent that receives a slice without that request
delivers its pull request and offers the loop in one line; it writes no
brief, prepares no review worktree and asks the human for no engine.

**Motivation.** The loop spends a second pair's tokens and wall time, and
the rule above said how it runs but not when. On 2026-10-29 the owner found
agents of several engines sliding into the loop by precedent, because every
0.3.0 slice before had run one, and asked for the trigger to be in the rule.

## 10. Completing A Workstream

**Rule.** Empty the intake and mailbox first; record the delivery facts in the
status file; a pull request is the default; prepare on a frozen, synchronized,
validated branch; finish in one commit at the delivery boundary; deliver by
merge commit; the workstream is done only when remote `main` holds the final
tree; an unsuccessful end still decides every item and promotes nothing
unfinished; recover from interruption by enumerating and comparing before
resuming.

**Intended effect.** Integration is mechanical for the agent, policy
decisions stay with the human, and `main` never carries a half-finished
workstream or an orphaned record.

**Motivation.** Integration is normally mechanical agent work, but delivery to
`main` follows repository policy, and permission to update `main` is never
inferred from the ability to do so. A full queue discovered late stalls the
integration rather than adding a step, hence the intake check comes first. The
finishing commit is added only when the pull request is otherwise merge-ready,
because it removes the workstream from the list and a review that then fails
would leave `main` lying about what is open. The finishing tree is provisional
until delivery completes; the list on remote `main` stays authoritative until
then. The pull request and the resulting history are the durable integration
record, so no commit is needed to predict the platform's merge revision. An
unsuccessful workstream still owes its queue a decision because work handed
over in good faith must not disappear with the workstream that failed to do
it. Draft user documentation stays inside the archive so that root `docs/`
never shows an unsupported path.

## 11. Releases

### 11.1 to 11.3 Terminology, refs, taking a release over

**Rule.** Releases, candidates, milestones, stages, tasks, slices, and
checkpoints are distinct words; release refs are `release-<version>`,
`v<version>-rc<n>`, `v<version>`, immutable once a candidate points at them;
work flows from the release branch to `main` by merge, never back; a candidate
is cut only from source `main` already has; one workstream drives a release
and its row names the release branch for the duration; maintenance releases
start from the final tag and may carry a documented integration exception.

**Intended effect.** A saved checkpoint is never mistaken for a release, a
release ref is recognizable by name alone, and a release never costs a fix
committed twice.

**Motivation.** Both the refs and the procedure had been left to each release
to improvise, and improvising them cost real work: fixes committed twice, a
candidate gate that had to prove two copies were the same patch, and a
checkout switching branches for every fix. Merging rather than cherry-picking
lets the candidate gate pass by plain ancestry. Release refs are not workstream
branches because a release outlives the workstream that drove it and must
never be rebased or deleted. The release branch does not take other
workstreams' work because tested release source must not move under the
tester. The product owner may set the version at any point, by any jump,
because versioning is a product decision; the branch's first commit only
confirms it.

### Two worked examples

The versions are illustrative. The rules are the same in a project that spells
its refs differently.

**An ordinary release, `1.4.0`, driven by the workstream whose work it ships.**

1. The workstream `search` has merged its branch `ws-search/v2` to `main`. The
   merge commit is the cut point. The owner decides to release.
2. `release-1.4.0` is created at the cut point. Its first commit bumps the
   source version to `1.4.0`. The list row for `search` now names
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
6. The `search` workstream resumes on `ws-search/v3`, forked from `main`, and
   its row names that branch. `release-1.4.0`, `v1.4.0-rc0`, `v1.4.0-rc1`, and
   `v1.4.0` remain for good.

**A patch to a released version, `1.3.1`, when `main` is not shippable.**

1. `v1.3.0` is in use. A defect must be fixed in it, but `main` carries
   unfinished `1.4.0` work that cannot ship. The owner decides on a
   maintenance release, which the reserved `maintenance` workstream drives.
2. `release-1.3.1` is created at `v1.3.0`, not at `main`. Its first commit
   bumps the version to `1.3.1`. The `maintenance` row names `release-1.3.1`
   for the duration.
3. The fix is committed on `release-1.3.1`. Merging it to `main` would carry
   the whole `1.3` line across `main`'s newer history, so it is not merged.
   Instead the release branch carries a documented integration exception
   naming who authorized it, why, which workstream owns forward-porting the fix
   to `main`, and the follow-up that closes it. `v1.3.1-rc0` is tagged and
   validated.
4. `v1.3.1-rc0` is accepted, and `v1.3.1` is tagged at the same commit. The
   forward-port owner delivers the fix to `main` through its own working
   branch as ordinary work.
5. The `maintenance` row returns to a `ws-maintenance/...` branch.
   `release-1.3.1` stays behind, closed.

### 11.4 What the project records

**Rule.** Ref spelling, candidate build and publication, the candidate gate and
its exception form, acceptance evidence and record location, and the bump
command live in the local file.

**Intended effect.** The shape of a release is reusable across ecosystems; the
mechanics stay with the project that knows them.

**Motivation.** A Python project and a Maven project version themselves
differently, build differently, and publish differently. The definition only
requires that the development marker exists and orders before the release.

## 12. Records

### 12.1 and 12.2 Requirements and user-level documentation

**Rule.** Requirements have stable IDs, a type, a priority, a status, and
validation references; work that touches a requirement cites it; requirement
files are not a backlog; user-visible behavior changes update user docs in the
same change, and current docs show only the supported interface.

**Intended effect.** A future session can tell why a task exists and how
important it is, and a user never follows a path the product no longer has.

**Motivation.** The status file says what to do next; the requirements say why
the task exists and how implementation and validation map back to intent.
Goals are evaluated by judgment and accumulated evidence; concrete
requirements must be testable in principle, even when verification is manual.
Requirements stay stable enough to help future sessions understand intent,
which they cannot do if they double as a backlog. User docs change with the
code because a doc that lags the code is the most common way users are misled;
historical notes may keep old command names because they describe what
happened then.

### 12.3 and 12.4 Draft documentation and active tasks

**Rule.** Drafts live under the workstream's `docs/` at their intended
destination; changes to existing docs are proposals, applied at finishing;
active tasks carry done, verification, and reopen conditions.

**Intended effect.** Root `docs/` is always current, and the next agent knows
when to remove a task from the list.

**Motivation.** A divergent copy of an existing document is two versions of
one record. Storing a new draft at its intended relative path makes the move at
finishing mechanical. A task without a done condition is never finished and
never removed.

### 12.5 Bug records

**Rule.** Frontmatter with controlled `status`, `severity`, `target`, `owner`,
dates, and requirements; prose never contradicts the fields; fields change in
the commit that justifies the change; a blocking bug with a target blocks that
release; routing is by `owner`, never by intake; closing follows a fixed
sequence.

**Intended effect.** Questions about bugs are answered from the records rather
than by reading all of them, and every bug has an owner from the moment it is
filed.

**Motivation.** The controlled fields exist so that "does anything block this
release" has a mechanical answer. Routing by `owner` rather than by intake
keeps bugs out of the queue mechanism, which was designed for handovers that
need a decision; a bug needs an owner, not a decision. The *Bug Or Feature*
test keeps the queue honest: a wish, however large, is a backlog entry. Moving
evidence to completed tasks on closure keeps the next-session question "what
should we do next" unambiguous.

### 12.6 to 12.9 Completed tasks, decision records, decision notes, external state

**Rule.** One file per closed task as the evidence trail; ceremonial,
human-adopted, immutable decision records for choices that cross subprojects,
change requirements, or move boundaries; lightweight notes for local reversible
choices; external state recorded without secrets.

**Intended effect.** The reasons behind durable choices survive rewrites and
model changes, and the ceremony stays rare enough to mean something.

**Motivation.** Some choices outlive the implementation that provoked them;
"we chose capabilities over named configurations" stays true across rewrites.
An agent may propose but never adopts, because adoption is a product decision.
Accepted decisions are frozen because editing one retcons history and destroys
the only property that makes it trustworthy as memory; a changed mind writes a
new record. A decision is never "implemented": a decision is not built, its
consequences are, and those belong to requirements and tasks. The triggers
mirror the escalation rules because the same conditions that warrant asking a
human warrant recording the answer. External state is recorded because
credentials, local images, and running services decay and cannot be
reconstructed from Git.

### 12.10 The documentation index

**Rule.** `index.md` lists permanent documentation by category and is updated
in the same change that adds, moves, or removes a document; it lists workstream
status files, not their internal documents.

**Intended effect.** Everything permanent is discoverable from one page, and
`index.md` is not a routine conflict point.

**Motivation.** An index exists because predictable discoverability is the
difference between recorded and lost. Workstream internals are indexed in the
workstream's own status file so that open work does not churn the root index.

### 12.11 Work orders

**Rule.** A work order is one markdown file that defines what a workstream is
to achieve, complete enough for a human or an agent to run it to completion;
human language governs, formal blocks may be embedded; a workstream may begin
from one; it is delivered by mail and acknowledged as the goal.

**Intended effect.** A workstream can be handed to whoever is available, human
or agent, with the author absent, and the result can be judged against what
was asked.

**Motivation.** Owner direction of 2026-10-09. The glossary had the kind and
several work orders existed, but nothing said a workstream could be born from
one or what one had to contain; each author improvised, and the executing
agent had to guess which parts were binding. The content list in rule 2 is the
set of questions an executor was observed to come back with: what is done,
what counts as evidence, what was already decided, what it may decide, and
when it must stop and ask. Human language governs because the owner writes in
it and because the executor's first job is to understand intent; embedded
formal specification is allowed because an agent can derive a precise check
from a loose description just in time, and a `lean` block or a test beside the
prose removes the ambiguity where it matters. Delivery by mail keeps the work
order inside the one handover mechanism the workflow has, so the
mailbox-intake-log invariant covers it too.

### 12.12 Materialized views

**Rule.** A human-facing document derived from records is a materialized
view with its dependencies recorded inside it, section-level when an agent
authors it and file-level when software renders it; staleness is detected
from content ids and shown; regeneration is on demand, mechanical or by an
agent task built from the dependency difference; humans review views and do
not maintain them; this file is the first authored view.

**Intended effect.** No human-facing document drifts from the records it
explains without the drift being visible, and nobody spends a human's time
maintaining prose that software or an agent can regenerate.

**Motivation.** Owner decision of 2026-10-09, closing the Karpathy list.
Karpathy's summary: as agents do the legwork, "a lot more of our work will
rise up the abstractions into oversight and understanding", and because
software is cheap, "you can ask for large, custom, discardable software
artifacts" that would never have made sense before. Discardable is the word
that matters: a view is built from records when a human needs it and has no
life of its own. The owner's refinement is the dependency record. A view that
knows what it was built from can be found stale mechanically, which is the
same mechanism the `Definition read` stamp already uses for the definition.
Section-level dependencies were chosen for authored views because a
file-level stamp would mark this whole file stale at every rule change and
make regeneration a rewrite rather than a paragraph; file-level is enough for
rendered views, which regenerate for free. The record lives inside the view,
not in a side registry, so that view and dependencies travel together and
survive any change of tooling; the console indexes them. This file is the
first case: it is not a human-maintained exception to the principle but a
view whose generator is an agent, reviewed by the owner for wording and style,
and the local file's same-commit rule is the hand-operated version of the
dependency until the console tracks it.

### 12.13 The pile of ideas

**Rule.** An idea nobody has triaged is one file under
`engineering-docs/pile-of-ideas/`, added by anyone on their working branch,
with no status, priority, or owner; `project-management` reads the pile at
its session starts and before each release branch is cut; triage ends an idea
as a backlog entry, a bug record, a sent item, a work order, or a drop,
removes the file, and logs one line.

**Intended effect.** Keeping a thought costs one small file, so it is not
lost in a conversation, and the pile holds only what nobody has decided yet.

**Motivation.** Owner direction of 2026-11-10, during the 0.3.1 cycle. A
model new to the codebase reported a list of observations, and the workflow
had nowhere cheap to put them: an item must say why it belongs to its
recipient and what accepting it means, and a backlog entry carries a priority
that somebody has already decided. An idea usually arrives in the middle of
other work, to whoever happens to be looking, and it survives only if writing
it down costs almost nothing. The rule therefore separates capture from
decision. One file per idea, rather than one living list, lets several
branches add ideas without conflicting. There is no status field because
presence in the directory is the status, and the file is removed at triage
because a pile that keeps decided ideas is the second backlog the other
record rules forbid. Slow transport is accepted: no pull request exists for a
record alone, so an idea reaches `main` with its branch, and an idea that
cannot wait for that is by that fact an item for mail. The two triage
occasions exist because a pile nobody is scheduled to read only grows;
`project-management` was paused when the rule was written. An idea may stay
through a triage, since forcing a decision would only move undecided ideas
into the backlog under `later`. The rule is new: the 0.3.1 cycle is its first
use, and it ships to adopters before it has been proven here.

## Section Map: Previous Edition To This One

| Previous section | Now |
|---|---|
| Purpose And Principles; When These Conflict; How To Read This Document | Topic 1, with the intents and tiebreaks in this file, section 1 |
| Vocabulary | Topic 2.6 |
| Glossary | Topic 2 |
| Changes | Changes, unchanged in place under topic 2 |
| Information Model | Topic 1, paragraph on *for humans* files; `INFORMATION-MODEL.md` |
| Checkouts, Branches, And Workstreams | Topics 5.1 and 5.2 |
| Where This Document Is Silent | Topic 3 |
| Workflow Declaration | Topic 4.1 |
| The Project's Local Workflow | Topic 4.2 |
| Single-Stream Workflow | Topic 6 |
| Definition And Restrictions | Topic 7.1 |
| Initializing Multiple-Stream Mode | Topic 7.2 |
| The Reserved `project-management` Workstream | Topic 7.3 |
| The Reserved `maintenance` Workstream | Topic 7.4 |
| Beginning A Workstream | Topic 7.5 |
| The Open-Work Directory | Topic 7.6 |
| Selecting Work At Session Start | Topic 7.8 |
| Changing Workstreams During A Task | Topic 7.9 |
| Workstream Intake | Topics 8.1 and 8.2 |
| The Decision Log | Topic 8.3 |
| The Coordination Branch | Topics 8.4 and 8.5 |
| Publishing Before Integration | Topics 8.6 and 8.7 |
| Staying Current With `main` | Topic 5.5 |
| Development And Checkpoints | Topics 5.3, 5.6, and 12.10 |
| Workstream States, Pausing, And Resuming; Open Threads | Topics 7.7, 9.2, 9.3, 9.4 |
| Draft User Documentation | Topic 12.3 |
| Successful Completion And Integration | Topics 10.1 to 10.4 |
| Unsuccessful Completion | Topic 10.5 |
| Integration And Recovery | Topics 10.1 and 10.6 |
| Core Loop | Topic 9.1 and 12.4 |
| Release, Milestone, Stage, Task, And Checkpoint Terminology | Topics 2.4 and 11.1 |
| Releases; Release Refs; Taking A Release Over; Two Examples; What This Section Leaves To The Project | Topics 11.2, 11.3, 11.4; examples in this file, section 11 |
| Turn-Level Choreography; Slice Sizing Rules; Human Input Contract; Decision And Escalation Rules | Topic 9.5 |
| Agent Reporting Contract | Topic 9.6 |
| Human And Agent Responsibilities | Topic 9.7 |
| Checkpoint Triggers | Topic 9.8 |
| Session Close Checklist | Topic 9.9 |
| User-Requested Session Records | Topic 9.10 |
| Markdown Roles | Topic 4.3 |
| Subproject Roles | Topic 4.4 |
| Requirements Register | Topic 12.1 |
| User-Level Documentation Protocol | Topic 12.2 |
| Active Task Format; Active Tasks Versus Historical Context | Topic 12.4 |
| Bug Intake | Topic 12.5 |
| Completed Task Archive | Topic 12.6 |
| Design Decision Records | Topic 12.7 |
| Decision Notes | Topic 12.8 |
| External State Register | Topic 12.9 |
| Git Hygiene; Verifying Shared Branch State | Topics 5.3 and 5.4 |
| Applying This To Other Projects | Topic 4.5 |
