# Workstream Current Status: GitHub Authentication

Mnemonic: `github-auth`

Start date: 2026-11-16

State: paused; implementation and local review prepared, gate and PR delivery pending.

Definition read: WORKFLOW.md@89de30622697, WORKFLOW-LOCAL.md@d92bdcbb0a01

Branch association: `ws-github-auth/ssh-proxy`, from canonical `upstream/main` at `1942f396`.

Integration target: `main`

Delivery method: pull request with Pair Review; the human merges.

Requirements: R-PRODUCT-002 (explicit host boundaries), R-PRODUCT-003 (durable memory).

## Goal and accepted scope

GitHub Git operations inside a capsule use the host's existing SSH authentication
through a proxy owned by the outside launcher. Private keys remain on the host.
The owner selected the new `github-auth` workstream and Git over SSH first on
2026-11-16 through the console decision. HTTPS and `gh` API authentication are
outside this slice. Review partner: Antigravity, `gemini-4-hydrogen-high`.

## Current state

A clean checkout at `/home/devcapsule/worktrees/github-auth` preserves the previous
checkout, its maintenance records commit, and its independent website gitlink.
The branch starts at fetched canonical main: no synchronization is required now.
No open bug is owned by this newly registered workstream. Mail and intake are empty.
The new feature belongs here, not in the maintenance release.

## Implementation and evidence

The initial Linux/WSL implementation includes the GitHub-only request validator,
launcher-owned Unix socket broker, capsule Git adapter, optional `github-ssh`
authorization, launch mount/environment wiring and user documentation. It does not
copy private keys or forward the host agent. The socket grants all GitHub Git
repositories available to the host identity. Docker Desktop transport is deferred
and explicitly refused. GitHub aliases, Git LFS authentication, SSH signing and
HTTPS/API credentials are not implemented in this slice.

Focused validation: 42 tests pass, including real Git clone/fetch/push through a
fixture SSH process, binary streaming, refusal, deadline, shutdown and authorized
Docker arguments. Initial mypy over the touched import graph passed (157 files).
The full build gate reached the unit suite: 20 failed, 2917 passed, 1 skipped,
14 xfailed and 7 xpassed. A selected rerun on an archive of unchanged
`upstream/main` reproduced 19 of those failures; the added authorization exposed
one exact-vocabulary legacy test. That file was refurbished into its proper
module mirror, preserving its contracts in 20 passing cases. The original gate
attempt failed in pytest setup because
`/opt` is read-only and `/opt/devcapsule-gate` does not exist. Scratch now uses
`/home/devcapsule/.cache/devcapsule-gate/github-auth` per the local rule allowing
another directory with space. No Docker containers or real credential files changed.

Additional checks: CLI smoke, PEX build and smoke, and documentation contract
pass. The console gate identified a mirrored authorization-table omission; after
alignment, all 458 console tests pass. A read-only live `git ls-remote` through
both the source adapter and the built PEX returned GitHub HEAD `1942f396`.
That used the current capsule's already-installed SSH credentials on the broker
side; it is not physical-host/capsule acceptance evidence.

The implementation and review branches are pushed to canonical upstream.
Gemini Hydrogen completed local round 1 at `388f62a3`. Its corrections remain
on the separate review branch for PR delivery. A temporary combined merge passed
75 focused cases, type checking and conventions (zero breaches), then was aborted.
Git connectivity integrity and authenticated fetch/push checks pass. The original
checkout remains untouched. Review evidence and prepared PR text are indexed below.

## Planned next step

Resolve the 19 reproduced baseline/environment failures in an appropriate gate
environment, then complete owner-operated implementation/review PR delivery and
physical-host acceptance. Do not claim a green full gate or mainline integration.
At resume, fetch upstream, check live workflow state and the review SHA, merge
through the prescribed PR process, and validate the actual combined tree.

## Open Threads

- Awaiting the human: suitable gate environment and owner-operated GitHub PR delivery.
  Workstream selection and Git-over-SSH scope are already accepted.
- Engineering choices: initial transport must account for Linux/rootless Docker
  permissions; Docker Desktop cannot bind ordinary host Unix sockets.
- Physical-host launch acceptance and Docker Desktop transport remain open.
- GitHub CLI is absent at the policy-prescribed path. PR creation/merging remains
  owner-operated under WORKFLOW-LOCAL.md; prepare reviewed commits and compare links.
- Reviewer worktree removed at pause; pushed `ws-github-auth/ssh-proxy-review`
  preserves its commit. Review corrections are not yet merged into implementation.
- Unimplemented review proposals and exact baseline failure IDs are in the assessment.
- Deliberately not preserved: scratch logs/venvs, credentials or console decision tokens in Git.

## Workstream document index

- [Review brief](evidence/review-brief.md)
- [Review follow-up 1](evidence/round-1.md)
- [Intake](intake/README.md)
- [Intake decisions](intake-dispositions.md)

- [Review assessment](evidence/review-assessment.md)
- [Prepared PR delivery](evidence/delivery.md)
