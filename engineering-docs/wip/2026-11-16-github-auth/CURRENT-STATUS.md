# Workstream Current Status: GitHub Authentication

Mnemonic: `github-auth`

Start date: 2026-11-16

State: active; first implementation slice.

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

## Planned next step

Implement a constrained GitHub Git transport broker, capsule adapter, explicit
host authorization, and lifecycle integration. Validate the transport and refusal
paths, then run Pair Review with Gemini 4 Hydrogen High.

## Open Threads

- Awaiting the human: none for workstream or first delivery scope; both accepted.
- Engineering choices: initial transport must account for Linux/rootless Docker
  permissions; Docker Desktop cannot bind ordinary host Unix sockets.
- GitHub CLI is absent at the policy-prescribed path. PR creation/merging remains
  owner-operated under WORKFLOW-LOCAL.md; prepare reviewed commits and compare links.
- Deliberately not preserved: no credentials or console decision tokens in Git.

## Workstream document index

- [Intake](intake/README.md)
- [Intake decisions](intake-dispositions.md)
