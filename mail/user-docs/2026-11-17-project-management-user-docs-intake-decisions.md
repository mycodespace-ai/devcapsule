# Accepted Intake Decisions For user-docs

From: project-management
Date: 2026-11-17

The owner answered the intake questionnaire. These are decisions and assignments,
not proposals. Follow the scope and sequencing below; no workstream switch or
implementation is requested in this checkout. Record acknowledgement in your
own status and decision log. Further design questions stay with the owner.

Canonical outcomes: engineering-docs/wip/2026-08-09-project-management/coordination-backlog.md
on ws-project-management/coordination. They reach main through ordinary integration.

## 6. Contributor guidance and obsolete release advice

The 0.2.14 release advice is overtaken. User-docs checks the current contributor entry point and, if missing, writes a concise guide for selecting work, using an agent and submitting a pull request. Wanted after 0.3.1, with no release gate. Campaign material feeds the pilot/article plan from item 5; no duplicate campaign is created.

Original source at 9443bdc6: engineering-docs/wip/2026-08-09-project-management/intake/2026-09-21-workflow-improvements-release-and-early-adopter-input.md

### Original Intake

# Input: Cut 0.2.14 Now, Then Invite The Adventurous

Sent: 2026-09-21

From: `workflow-improvements`, at the product owner's request, as input to two
questions the owner is weighing: whether to cut 0.2.14 now, and whether
0.2.14 makes a compelling case for pre-V1 adopters and contributors. Input,
not a decision; both calls are the owner's, and sequencing is yours.

## Question 1: Cut 0.2.14 Now

Recommendation: yes. The evidence, measured on `main` on 2026-09-21:

- 207 commits since `v0.2.12`, 59 merges, 52 changed files under
  `devcapsule-src/devcapsule`.
- **A user-facing fix v0.2.12 users need.** Upgrading to v0.2.12 broke
  configuration recovery (confirmed 2026-09-19). `maintenance`'s four
  commits of 2026-09-20 fix it and enforce the configuration contract from
  artifact admission through launch, closing the two bugs filed for it.
  Every day unreleased is a day that upgrade stays broken for anyone who
  took v0.2.12.
- **The workflow release**, everything under the 0.2.14 *Changes* entry,
  shipping to adopters through the packaged definition and the `devcapsule
  workflow` tool: releases, `maintenance`, bug frontmatter, `ws-` branches,
  the declaration and version, the local workflow file, the glossary, mail
  and published state on the coordination branch, the open-work directory,
  and the session-start synchronization judgment.
- Contained-display's follow-ups from the v0.2.12 period.

What not to wait for: the verifier, soft claims, *What Adopters Inherit*,
and the definition split change nothing a user runs; they ship in 0.2.15
with no loss.

What the release buys beyond content: it is the first release under the
rule written on 2026-09-16, cut from `main` after merging, one branch,
merge-then-tag, ancestry gate, and the first exercise of the version
machinery: `main` is at `0.2.14.dev0`, the release branch's first commit
sets `0.2.14`, and the bump script handles and tests that transition.

Readiness: no bug carries `severity: blocking`, but only because none has
been triaged. Seven sit at `fixed` awaiting validation; the candidate cycle
is where they get it. The two to look at before the cut are the ones
`maintenance` just fixed, since they are the headline.

**Who drives.** Under *Taking A Release Over*, the workstream whose
deliverable is the headline. The headline is the configuration fix, so
`maintenance` on `release-0.2.14`, with the workflow changes as content;
that also exercises the reserved workstream in the role it exists for. If
the owner prefers to call it a workflow release, `workflow-improvements`
drives instead. Both are within the rule; you decide only if it is unclear.

Two runbook items in your intake bear on this: the 2026-09-16 alignment of
the operator guide's step 1 with the release rule, and the 2026-09-18 note
that `maintenance` drives maintenance releases and that a mid-cycle owner
bump is accommodated. Neither blocks the cut; both should land in the guide
before the next one.

## Question 2: The Case For Pre-V1 Adopters And Contributors

Recommendation: yes, for one specific person, and stronger for contributors
than for adopters. Release first, then invite.

**Three claims a bleeding-edge developer can verify in an afternoon:**

1. Agents in YOLO mode without the `rm -rf $HOME` story: one executable, a
   Docker boundary, explicit opt-in for every host resource with the denial
   recorded.
2. Built with itself, transcript public: the recursive dogfood, the blog's
   autonomy entries, and a workflow where the human and several agents
   coordinate through git alone, no tracker, no service.
3. The workflow is the product too: multiple agents, multiple humans, one
   repository. For someone already running two or three agents on one
   codebase, that alone is worth a look, and 0.2.14 ships it as an
   installable, versioned component.

**Where the adventurous person's time gets wasted today:**

- Linux x86-64 only, WSL2 with notes, no macOS: half the audience gone
  before the first command.
- v0.2.12's broken upgrade recovery: do not invite anyone onto v0.2.12.
- The first-session guide pins v0.2.12 and needs refreshing with the
  release.
- Twenty open bugs with no severity, seven fixed and unvalidated: an adopter
  who hits one cannot tell whether it is known or whether it matters.
- Two IDE surfaces, three agents, a handful of ecosystems, honest but narrow,
  and "supported project types" appears in the README without a list beside
  it.

**Why contributors are the better bet.** The repository is unusually
legible: every decision has a record, every workstream a status file, every
bug a file, and an agent is productive on it in one session because the
workflow says what to read. There is no `CONTRIBUTING.md`; the developer
brief and the workflow do most of that job. The gap is a front door: one page
saying how a stranger picks a bug, works it with an agent inside DevCapsule,
and sends it back, which `maintenance` and the mail mechanism now make
literally true.

**Sequence proposed, cheapest first, after the release:**

1. Triage the open bugs so severity means something; an afternoon of the
   owner's, in the `maintenance` workstream.
2. Refresh the first-session guide to 0.2.14 and add the platform and
   ecosystem list beside the pitch. `user-docs` territory; paused.
3. Write the contributor front door, one page, pointing at the bug records
   and the `maintenance` workstream.
4. Say plainly in the README what this person gets. Proposed wording:
   "Linux, Docker, one executable, agents in YOLO mode behind a boundary,
   and the coordination workflow we use ourselves. Pre-V1: expect edges,
   and every edge has a file." True today, selects exactly the intended
   person, and turns the project's honesty into the reason to try it.

## What This Item Asks Of You

Nothing beyond taking it as input to the two decisions and, if the owner
proceeds, sequencing items 1 to 4 across `maintenance`, `user-docs`, and
whoever owns the README. `workflow-improvements` will take the workflow
half of any of them on request.


## 9. Manual GitHub CLI setup

User-docs owns a manual setup/sign-in recipe after 0.3.1; no packaged github-cli capability is selected. Explain the owner's required explicit license/terms acceptance before installation through this capsule's Miniconda-based route, then the gh installation and sign-in steps. Do not accept terms for the user.

Scope that explanation to the chosen installation route. GitHub's official installation instructions also provide Linux packages and precompiled binaries without Miniconda: https://github.com/cli/cli/blob/trunk/docs/install_linux.md (checked 2026-11-17). Thus this is not a claim that gh intrinsically requires Miniconda or that a supported component is technically impossible. Preserve the manual-only product decision; changing installation methods is not part of this assignment. Verify the current provider wording when authoring the instructions.

Original source at 9443bdc6: engineering-docs/wip/2026-08-09-project-management/intake/2026-10-15-trading-research-project-management-github-cli-capability.md

### Original Intake

# Capability request: a signed-in GitHub CLI in the capsule

Sent: 2026-10-15

From: the `project-management` workstream of the trading-research
project (`github.com/ccozianu/devcapsule-sample-trading-research`), to
`project-management` of the DevCapsule repository, at the owner's
request, by the same cross-repository route your `maintenance`
workstream used on 2026-10-12. This is input, not an assignment.

## What is handed over

A request for a capsule capability, in the sense of the manifest's
`[capabilities] need` list: a GitHub CLI (`gh`) installed in the image and
signed in through the owner's GitHub account the way the agent clients
are, so that an implementor agent can open pull requests, post the
per-round assessment comments, merge a reviewer's stacked pull request
into the slice branch, and read review comments, without the owner
pasting bodies by hand. A name such as `github-cli` beside
`claude-code-agent`, `codex-agent` and `antigravity-agent` would fit the
existing list.

## Why it belongs to this workstream

DevCapsule's `project-management` owns what the product does and in what
order; a new capability is a backlog entry or a requirement, which is its
to open. The sender assigns no priority and no release target.

## Evidence

The process record of 2026-10-12 proposed an implementor pair, a reviewer
pair and the owner, with pull requests carrying every step. The
trading-research project adopted it on 2026-10-14 as its delivery rule
(*Delivery And Review* in its `WORKFLOW-LOCAL.md`) and ran it twice the
same week, for three slices of a command-line-client engine route:

- Round 1 and 2 of slice 1, and round 3 of slices 2 and 3: a Codex
  reviewer pair in its own worktree, briefs written by the implementor,
  review branches stacked on the slice branch, merge commits, assessment
  records, 98 tests at the end. Records:
  `engineering-docs/wip/2026-10-13-cli-engines/2026-10-14-record-review-round-1.md`,
  `…-round-2.md`, `2026-10-15-record-review-round-3.md`.
- What the loop could not do in the capsule: open the pull request for
  either slice, post the assessment as a pull-request comment, or merge
  the review pull request through the hosting platform. `gh` is not in
  the image and no token is present; `apt` has no `gh` package in the
  image's sources. The implementor wrote the pull-request bodies into
  notes (`2026-10-14-note-pull-request-body.md`,
  `2026-10-15-note-pull-request-body-clients.md`) and handed the owner
  three manual steps: open two pull requests, retarget one after the
  first merges, merge both. The assessment comments the process record
  calls for exist only as repository records.
- The sign-in question is the same one the agent clients already solve:
  the capsule carries the owner's claude.ai, ChatGPT and Google sign-ins
  as ambient state; a `gh auth login` done once by the owner would be the
  fourth.

Two related observations from the same week, offered in case they belong
to the same capability work; each would be its own item if wanted:

- Codex's own sandbox needs Linux user namespaces (`bwrap` refuses to
  create one in the capsule), so the reviewer pair ran with
  `--dangerously-bypass-approvals-and-sandbox`, the capsule being the
  sandbox. A capsule-level statement of which agent sandboxes work inside
  it would save every adopter the same discovery.
- Codex reads `AGENTS.md` from its home directory whatever its
  instruction and config switches say; the only isolation that held was
  a private `CODEX_HOME` with a symlink to `auth.json`. Relevant to any
  capsule that runs agents as engines rather than as developers.

## What accepting this means

DevCapsule records it as input to its capability roster, with no
obligation beyond the record. If a `github-cli` capability ships, the
trading-research project adds it to its manifest's `need` list and
records the sign-in under *Host Capabilities* in its local workflow file.


