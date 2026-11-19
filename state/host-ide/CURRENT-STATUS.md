# Workstream Current Status: Host IDE

Mnemonic: `host-ide`

Start date: 2026-11-19

State: active 2026-11-19; work order authored and approved; coordinating Pair Review implementation (Codex `gpt-6-astra` high-effort implementer, Antigravity `Gemini 4 Hydrogen` reviewer) targeting `release-0.3.1`.

Definition read: WORKFLOW.md@196d3760f99e, WORKFLOW-LOCAL.md@5b0f27c04de1

Integration target: `release-0.3.1` (owner direction, 2026-11-19)

Delivery method: pull request to `release-0.3.1`; owner merges; records published live on `coordination`.

Branch prefix: `ws-host-ide/`

Branch association: `ws-host-ide/vscode-codium`, forked from `upstream/release-0.3.1` (`8d71b26c`); implementation branch `ws-host-ide/vscode-codium-impl`.

Work order: [Split-surface host IDE (`host-ide`) — VS Code first slice](../../work-orders/2026-11-19-host-ide-vscode.md)

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

Dispatch Codex (`gpt-6-astra`, high effort) in `/home/devcapsule/worktrees/host-ide-impl` (`ws-host-ide/vscode-codium-impl`) to implement the VS Code `host-ide` work order and open the implementation PR against `release-0.3.1`, then review it in the Pair Review Loop.

## Open Threads

- Preserve the user's two uncommitted `.devcapsule/devcapsule.toml` and `.devcapsule/devcapsule.linux-amd64.lock` edits in `/workspace/301e4208ef81-ChatGPT_Codex` (exclude from commits).
- VSCodium (`codium`) support via `open-remote-ssh` / `docker exec` will follow in the next slice after the VS Code slice lands.

## Document Index

- [Workstream status](CURRENT-STATUS.md) — active state, recorded `release-0.3.1` base exception, and next Pair Review step.
- [Work order](../../work-orders/2026-11-19-host-ide-vscode.md) — approved scope and engineering constraints for the VS Code `host-ide` slice.
- [Implementor brief](evidence/2026-11-19-vscode-impl-brief.md) — implementation brief for Codex (`gpt-6-astra`, high effort) on `ws-host-ide/vscode-codium-impl`.
- [Intake](intake/README.md) — workstream intake queue (empty).
- [Intake dispositions](intake-dispositions.md) — intake decision log (no items received).
