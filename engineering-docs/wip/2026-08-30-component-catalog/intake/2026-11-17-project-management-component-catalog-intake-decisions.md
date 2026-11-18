# Accepted Intake Decisions For component-catalog

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


## 2. Init and configuration commands

Retain the current model: init creates/completes the project, regeneration refreshes derived state and performs explicit format migration, and config commands make explicit shared/local edits. Reconcile old symptoms with current code, then reject ineffective flags or explain their real effect. This is wanted V1 work, not an additional release gate.

The owner specifically requests further discussion when the component update workstream takes this up. Route the work to component-upgrades, with component-catalog support; bring the remaining command behavior choices to the owner before implementing them. The intake routing is decided; the detailed behavior is not.

Original source at 9443bdc6: engineering-docs/wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-init-regenerate-versus-config-semantics.md

### Original Intake

# Intake: Clarify The Semantics Of `init --regenerate` Versus The `config` Family

Delivered 2026-09-06 by `component-catalog`, at the product owner's
direction, after a systematic walk through what `project init
--regenerate` tells the user and what it does. The owner ruled that the
current behaviour is acceptable for now, in the interest of speed, and
that the semantics be settled here rather than patched case by case.

## The Principle The Owner Stated

`init` exists to help a contributor operate on the `.devcapsule` in the
source tree — the project-owned manifest and platform lock. That it also
updates the local configuration that serves `project run` (the
developer-owned checkout record and its resolution) is a convenience,
not its purpose. The `config` family owns the local configuration.
Today the two overlap in ways the messages do not admit.

## What Is Being Handed Over

A design ruling on the boundary, and the message and flag changes that
follow from it. The discrepancies found on 2026-09-06, all verified
against the code:

1. `--regenerate --need …` derives the lock from the flagged need but
   never rewrites the manifest's authored `need` line, and nothing checks
   the lock's `capabilities-digest` against the manifest. The two diverge
   silently. `config need` is the only path that keeps them together.
2. Identity flags (`--name`, `--slug`, `--creator`, `--project-mount`) on
   a re-init are accepted, printed in the report as if applied, and never
   written to the standing manifest.
3. The design note says `--regenerate` "does not touch the
   developer-owned checkout records". It rewrites the owner's own record:
   every project recommendation is re-authorized for the owner's checkout
   without a question, and the base-image acceptance is re-asked because
   the lock digest changed. The behaviour may be right; the sentence is
   not.
4. The init report prints "Recommended docker-daemon = <justification>"
   where the value belongs.
5. Two messages still name `init --regenerate` as the sole remedy — for a
   hand-edited manifest and for a legacy lock met at run time — which is
   only right once item 1 is settled.

Candidate directions the owner did not choose between: `--regenerate`
refuses `--need` and identity flags on a standing manifest and names
`config need` (and a future manifest-editing verb) instead; or
`--regenerate` becomes the manifest-editing verb and rewrites the
authored lines it is given, with `config` confined to the local half.
Either way the help text, the fully-initialized refusal, the design
note's `--regenerate` section, and the README should say the same thing.

## Why It Belongs To `project-management`

The boundary between project-owned and developer-owned configuration is
the V1 user-experience design's spine ("Four Things With Different
Owners"); changing which command writes which artifact is a product
ruling that every workstream's users meet, not a `component-catalog`
matter. It also intersects the open checkout-local-needs ruling (whether
`config need` defaults to a local experiment) already with the owner.

## Evidence

- `initialize_project` in `project_operations.py`: the flag only disables
  the "already fully initialized" refusal and the "keep the existing
  lock" branch; identity and need are re-elicited into the derivation but
  `_write_manifest` appends only new recommendations to an existing
  manifest.
- The 2026-09-05 scratch reproduction: `init --regenerate --unverified
  --need <six capabilities>` on a copy of this repository's `.devcapsule`
  produced a six-capability lock beside a five-capability manifest with
  no warning.
- The `--regenerate` section of the V1 user-experience design note versus
  the owner-record writes at the end of `initialize_project`.

## What Accepting Would Mean

Owning the ruling and its sequencing; the implementation is small once
the direction is chosen (message text, flag refusals or manifest
rewrites, one design-note paragraph, one report line). Nothing blocks on
it: the owner has accepted current `init` for now.


## 3. Readable component terminology

Component-catalog owns a broader wanted V1 audit of current code and permanent guidance, including internal edge terminology. Preserve technical distinctions and frozen historical decisions; propose any schema changes separately. Base-family naming already exists, so establish the remaining gap rather than repeat an old rename. No release gate is added.

Original source at 9443bdc6: engineering-docs/wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-internal-naming-drops-generation-vocabulary.md

### Original Intake

# Intake: Internal Naming Drops The Generation Vocabulary

Delivered 2026-09-06 by `component-catalog`, at the product owner's
direction, prompted by the commit subject `feat: PyCharm gains a
provisional gen2 edge (matrix embedded-15)`: "we need to drop gen2 as we
are inside a pre-release 0.x and I am not aware of any gen1 still active
in the codebase."

## What Is Being Handed Over

A naming ruling for internal records — commit messages, handoffs, bug
records, decision amendments, code comments and identifiers — that
complements the adopter-facing ruling of the same day (D-0007 amendment
2026-09-06: adopters read *validated / not yet validated*, components,
versions, bases; never *edge* or *substrate*). The internal vocabulary
has spread: 2 of the last 40 commit subjects on `main` and 9 permanent
documents carry `gen1`/`gen2`/`substrate`, and the words carry almost no
information at this stage of the project.

The facts to rule on:

1. **`gen1` is still active, in one place.** The `postgresql-client`
   component (delivery policy `base-image`; the base's apt list ships
   it) has exactly one matrix entry, on the older generation. Every need
   containing `postgresql-client` therefore still resolves to the v026
   base — the `pycharm-full` golden lock does. The newer bases ship the
   same package, so the missing entry is evidence, not capability.
   Adding it, then retiring the v026 pin and its entries (D-0007 makes
   retirement an explicit act), leaves a single generation.
2. **With one generation, the concept says nothing.** The substrate was
   introduced on 2026-09-02 so that a base rebuild would not orphan every
   validation; that purpose stands, but the *name* of the single current
   generation need not appear anywhere. Options: keep the field with a
   neutral value derived from the OS release (`ubuntu-24.04`), rename it
   to something an engineer reads without a glossary (*base family*,
   *base line*), or fold it into the base pin until a second generation
   exists.
3. **Commit subjects and records name what changed for whom.** The
   subject above becomes, for instance, `feat: PyCharm is validated on
   the v0.2.9 base (provisional)`; the matrix version stays in the body.
   A short house style for matrix commits (component, version, base,
   evidence status) would make the log readable to someone outside the
   workstream.
4. **Where the rename reaches.** Code identifiers (`_VerifiedEdge`,
   `substrate`, `_SUBSTRATE_GEN2`) and tests are the resolution-matrix
   cleanup already on the backlog; D-0007's text is a decision record and
   is amended, not rewritten; handoffs and bug records are history and
   stay as written.

## Why It Belongs To `project-management`

Naming that crosses every workstream's commits and records is a house
style, not a `component-catalog` matter, and the ruling on retiring the
older generation is a matrix-wide product decision that touches the
release process (which bases stay on Docker Hub) and the withdrawal of
0.2.9 decided today.

## What Accepting Would Mean

Ruling on points 1 and 2 and recording the house style of point 3 where
commit conventions live; `component-catalog` can add the
`postgresql-client` entry and retire the older base in the same matrix
advance as the 0.2.10 repin once ruled.


## 4. Evidence from successful experiments

Keep current manual evidence curation for the successor to 0.3.1. Component-upgrades retains the learning/submission channel and subsequent mandatory checks on matrix additions as wanted V1 tasks, revisited after that successor ships. Local successful experiments must not be silently promoted to general compatibility claims.

Original source at 9443bdc6: engineering-docs/wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-matrix-learns-from-experiments.md

### Original Intake

# Intake: The Matrix Learns From Adopters' Experiments, Then Gates On Claims

Delivered 2026-09-06 by `component-catalog`, at the product owner's
direction, given while ruling on the refusal UX (D-0007 amendment of the
same date).

## What Is Being Handed Over

Two design problems, in sequence:

1. **Learning from experience.** An owner or adopter who runs a
   combination the matrix has not validated does so as an *experiment*
   (`--unverified`), and the generated lock records exactly which
   component versions ran on which base. When such an experiment works,
   that fact should be able to reach the matrix — today the only path is
   the owner hand-editing `resolution_matrix.py` with an evidence string.
   Design the channel: what an adopter submits (the lock's
   `unverified-combinations`, the known-good generation D-0008 already
   records on a successful run, a formation identity?), what counts as
   "ran successfully", how a submission becomes a matrix entry, and how
   provisional entries are told apart from evidenced ones.
2. **Gating, later.** Once claims exist, a change to the matrix on
   mainline should be gated on the existence of a claim, for every
   combination the change adds, that it has run successfully. Design
   where that gate lives (pull-request check, release process, both) and
   what a claim must carry to count.

## Why It Belongs To `project-management`

It spans the resolution matrix (`component-catalog` hosts the data), the
release and validation process (recorded 2026-09-01), D-0008's known-good
history, the CLI's message surface, and the upgrade-experience feature
already in this intake (2026-09-03) — of which this is the "who verifies,
what evidence gates the advance" strand made concrete. The owner framed
the sequencing: warn owners and collaborators the same way for now, learn
from experience next, gate afterwards.

## Evidence

- The 2026-09-05 case: PyCharm was validated only on the older base
  generation, Antigravity only on the newer; the owner had in fact run
  PyCharm on the newer base all day, and the matrix learned it only by
  hand, as a provisional entry citing that session.
- Every agent CLI pin advanced this week carries a provisional entry
  whose evidence is "pending the owner's smoke"; there is no way for the
  smoke, when it happens, to convert the entry except by another hand
  edit.
- The lock already carries the fact an experiment would report
  (`unverified-combinations`), and D-0008 already records successful
  runs; the pieces of a claim exist, the channel does not.

## What Accepting Would Mean

Owning the two designs above and their sequencing against the rest of
V1. Nothing here blocks current work: the refusal-UX ruling is
implemented without it.


