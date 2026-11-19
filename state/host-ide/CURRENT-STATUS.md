# Workstream Current Status: Host IDE

Mnemonic: `host-ide`

Start date: 2026-11-19

State: active 2026-11-19; workstream opened and registered, aligning on remote transport, CLI/configuration UX, and platform scope for host VS Code / VSCodium with container `xfce4-terminal`.

Definition read: WORKFLOW.md@196d3760f99e, WORKFLOW-LOCAL.md@5b0f27c04de1

Integration target: `release-0.3.1` (owner direction, 2026-11-19)

Delivery method: pull request to `release-0.3.1`; owner merges; records published live on `coordination`.

Branch prefix: `ws-host-ide/`

Branch association: `ws-host-ide/vscode-codium`, forked from `upstream/release-0.3.1` (`8d71b26c`).

Requirements: `R-PRODUCT-001`, `R-PRODUCT-002`, `R-SCOPE-001`

## Goal and Problem Statement

Reduce daily IDE UX friction (multi-step copy/paste across the browser noVNC tab on macOS/Windows and cramped integrated terminals for CLI agents) while keeping builds, toolchains, and coding agents inside the isolated capsule:

- **Container side:** Run the capsule with `xfce4-terminal` as its supervised GUI surface over noVNC so terminal-centric coding agents (`claude`, `codex`, `antigravity`) get a full-screen tabbed terminal inside the container.
- **Host side:** Launch the user's host-installed IDE (`vscode` / `codium` first) via host execution and connect it to `/workspace/<slug>` inside the running container using its remote development extension/mechanism for native editing, project navigation, clipboard, and debugging.

## Workflow Exceptions

- **Forked from `release-0.3.1` rather than `main`:** `WORKFLOW.md` topic 7.5 specifies forking a new workstream's first branch from `main`. By owner direction on 2026-11-19, `host-ide` targets `release-0.3.1` and depends directly on `xfce4-terminal` (`PR #62`, merged into `release-0.3.1` at `8d71b26c` and not yet on `main`), so `ws-host-ide/vscode-codium` forks from `upstream/release-0.3.1` (`8d71b26c`). Ends when `release-0.3.1` propagates to `main`.

## Current State

- 2026-11-19: Closed out prior maintenance checkout effort (`ws-maintenance/website-candidate-checkout`, merged as PR #61 into `main`), removed its temporary worktree, and switched this checkout to `ws-host-ide/vscode-codium` while preserving the user's two uncommitted `.devcapsule/` files.
- Registered `host-ide` in root `CURRENT-STATUS.md`, `index.md`, and `engineering-docs/wip/2026-11-19-host-ide/`. No production source code changed yet.

## Planned Next Step

Align with the product owner on the three open design questions for the `vscode` / `codium` split-surface UX before drafting the implementation plan:

1. Remote connection transport for VS Code (`attached-container` vs. SSH) and VSCodium (`open-remote-ssh` over `docker exec` / loopback vs. alternatives).
2. CLI and checkout configuration representation for selecting the split-surface UX mode.
3. Host platforms in scope for the first slice (Linux, WSL2, macOS) and host IDE/extension readiness checks.

## Open Threads

- Preserve the user's two uncommitted `.devcapsule/devcapsule.toml` and `.devcapsule/devcapsule.linux-amd64.lock` edits in this checkout (exclude from commits).
- Confirm whether `docs/` updates and Playwright/integration validation belong in the first slice targeting `release-0.3.1`.

## Document Index

- [Workstream status](CURRENT-STATUS.md) — active state, recorded `release-0.3.1` base exception, and next design alignment questions.
- [Intake](intake/README.md) — workstream intake queue (empty).
- [Intake dispositions](intake-dispositions.md) — intake decision log (no items received).
