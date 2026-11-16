# Workstream Current Status: GitHub Authentication

Mnemonic: `github-auth`

Start date: 2026-11-16

State: active; first implementation slice.

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

The branch is pushed to `upstream/ws-github-auth/ssh-proxy`. Gemini Hydrogen High
is reviewing in `/home/devcapsule/worktrees/github-auth-review`. The first invocation
received no brief through redirected stdin. The same conversation resumed with an
explicit path to this committed brief; flags/model stayed unchanged. No credentials
were examined to repair this CLI input issue.

## Planned next step

Assess Gemini's review diff, incorporate accepted corrections, repeat affected
checks, and prepare owner-operated PR delivery. Full gate remains blocked by the
19 demonstrated mainline/environment failures; no test was disabled or reclassified
to hide them.

## Open Threads

- Awaiting the human: none for workstream or first delivery scope; both accepted.
- Engineering choices: initial transport must account for Linux/rootless Docker
  permissions; Docker Desktop cannot bind ordinary host Unix sockets.
- Physical-host launch acceptance and Docker Desktop transport remain open.
- GitHub CLI is absent at the policy-prescribed path. PR creation/merging remains
  owner-operated under WORKFLOW-LOCAL.md; prepare reviewed commits and compare links.
- Deliberately not preserved: no credentials or console decision tokens in Git.

## Workstream document index

- [Review brief](evidence/review-brief.md)
- [Intake](intake/README.md)
- [Intake decisions](intake-dispositions.md)
