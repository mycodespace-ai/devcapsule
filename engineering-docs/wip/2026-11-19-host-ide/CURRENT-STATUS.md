# Workstream Current Status: Host IDE

Mnemonic: `host-ide`

Start date: 2026-11-19

State: active 2026-11-19; VS Code `host-ide` slice implemented and Pair Review complete ([PR #65](https://github.com/mycodespace-ai/devcapsule/pull/65) open against `release-0.3.1`; review [PR #66](https://github.com/mycodespace-ai/devcapsule/pull/66) merged after 1 round at `717ce587`).

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

- 2026-11-19: Implemented the VS Code `host-ide` first slice on `ws-host-ide/vscode-codium-impl` (`4c4ef9c5`) and opened [PR #65](https://github.com/mycodespace-ai/devcapsule/pull/65) targeting `release-0.3.1`.
- Completed Pair Review Loop with Antigravity (`Gemini 4 Hydrogen High`) reviewer / Codex (`gpt-6-astra`, high effort) implementor: review [PR #66](https://github.com/mycodespace-ai/devcapsule/pull/66) fixed 5 findings (`8eee48c1`), resolved a Round 1 unit-test isolation / CLI-retry coverage pushback (`5eb9f317`), and merged into `ws-host-ide/vscode-codium-impl` at `717ce587`.
- Merged-branch validation passed: `44` focused unit tests, `7` isolation-probe home cases, `3477` build unit passes (`1` skipped, `288` deselected, `1` xfailed, `1` xpassed), `474` webconsole tests, `21` host-IDE CLI integration tests, mypy (`377` + `9` files), `0` unittest convention breaches, local PEX smoke, and `249` docs contract pages.

## Planned Next Step

Owner review and merge of [PR #65](https://github.com/mycodespace-ai/devcapsule/pull/65) into `release-0.3.1`; follow with real-host VS Code smoke verification and the VSCodium (`codium`) slice via `open-remote-ssh` / `docker exec`.

## Open Threads

- Owner merge of [PR #65](https://github.com/mycodespace-ai/devcapsule/pull/65) into `release-0.3.1` and real-host VS Code attach verification outside the capsule sandbox.
- Remove `/home/devcapsule/worktrees/host-ide-impl` and `/home/devcapsule/worktrees/host-ide-review` once `PR #65` merges.
- Preserve the user's two uncommitted `.devcapsule/devcapsule.toml` and `.devcapsule/devcapsule.linux-amd64.lock` edits in `/workspace/301e4208ef81-ChatGPT_Codex` (exclude from commits).
- VSCodium (`codium`) support via `open-remote-ssh` / `docker exec` follows in the next slice after the VS Code slice lands.

## Document Index

- [Workstream status](CURRENT-STATUS.md) — active state, recorded `release-0.3.1` base exception, and next Pair Review step.
- [Work order](../../work-orders/2026-11-19-host-ide-vscode.md) — approved scope and engineering constraints for the VS Code `host-ide` slice.
- [Implementor brief](evidence/2026-11-19-vscode-impl-brief.md) — implementation brief for Codex (`gpt-6-astra`, high effort) on `ws-host-ide/vscode-codium-impl`.
- [Pair Review brief and outcome](evidence/2026-11-19-pr65-review-brief.md) — PR #65 / PR #66 review findings, Round 1 pushback/resolution, and merged verification counts.
- [Intake](intake/README.md) — workstream intake queue (empty).
- [Intake dispositions](intake-dispositions.md) — intake decision log (no items received).
