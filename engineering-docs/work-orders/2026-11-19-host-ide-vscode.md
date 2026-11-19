# Work Order: Split-Surface Host IDE (`host-ide`) — VS Code First Slice

Date: 2026-11-19.
Workstream: `host-ide` (`ws-host-ide/vscode-codium`).
Target release: `release-0.3.1`.
Status: approved for implementation via Pair Review (`codex` / `gpt-6-astra` high-effort implementer, `antigravity` / `gemini-4-hydrogen` reviewer and coordinator).

## Problem Statement

1. On macOS, Windows (WSL2), and contained-display Linux, running the full IDE inside a browser noVNC tab preserves isolation at the cost of everyday UX friction (for example, double-step clipboard copy/paste across the browser/VNC boundary).
2. Even on Linux with native X11 passthrough, terminal-centric coding agents (`claude`, `codex`, `antigravity`) end up constrained inside an IDE's bottom or side integrated terminal pane instead of having a full-screen dedicated terminal.

## Outcome

When the checkout's selected IDE is `vscode` (`vscode-ide`, or `frontend-ide` resolved to `vscode`) and the developer enables the new `host-ide` authorization (`true`, defaulting to `false`):

1. **Container side:** DevCapsule keeps the selected IDE name (`vscode`) in the checkout configuration and manifest untouched, but substitutes `xfce4-terminal` as the container's materialized and supervised `interactive-surface`. Everything else on the container side stays orthogonal and unchanged:
   - `host-x11` remains orthogonal (`false` runs `xfce4-terminal` in the browser noVNC tab; `true` on Linux runs `xfce4-terminal` directly in a native X11 window).
   - Docker mode (`none`, `host`, `dind`) remains orthogonal.
   - Recursive E2E readiness is disabled automatically (`DEVCAPSULE_RECURSIVE_E2E_ENABLED=0`) for DevCapsule checkouts launched with `host-ide = true`, with a clear launch notice.
   - Because `xfce4-terminal` replaces `vscode` in the container, `/opt/vscode` is neither downloaded nor installed in the container image, and container `vscode-download` acquisition consent is not required when host `code` is already on `PATH`.
2. **Host side:** DevCapsule prepares and attaches the host's VS Code (`code`) to `/workspace/<slug>` (the container's `project_mount`) inside the running capsule using Microsoft's Dev Containers extension (`ms-vscode-remote.remote-containers`) over `docker exec`:
   - Check first whether `code` is on the host `PATH`.
   - If `code` is not on `PATH`, reuse an already-unpacked DevCapsule host VS Code installation if present; otherwise, gate on the existing `vscode` channel trust (`devcapsule home trust accept vscode` / `--trust vscode`, `https://code.visualstudio.com/license`), download the SHA-256-verified VS Code archive for the host OS/architecture from `https://update.code.visualstudio.com/api/update/<target>/stable/latest`, and unpack it under DevCapsule's host data tree (`XdgHomes.data / "host-ide" / "vscode"`).
     - On WSL2, if `code` is missing from `PATH`, fail with actionable Windows VS Code installation guidance rather than downloading a Linux tarball.
   - Create and maintain an isolated VS Code configuration home under DevCapsule's host config tree (`XdgHomes.config / "host-ide" / "vscode"`):
     - `user-data/` (`--user-data-dir`)
     - `extensions/` (`--extensions-dir`)
   - Merge required settings into `user-data/User/settings.json` atomically while preserving user edits inside that isolated profile (including `"dev.containers.executeInWSL": true` on WSL2 when Docker runs inside the WSL2 distro rather than Docker Desktop).
   - Ensure `ms-vscode-remote.remote-containers` is installed in that isolated `--extensions-dir` (via `--list-extensions` and `--install-extension ms-vscode-remote.remote-containers` when absent) before starting the container, so missing tools/trust fail fast.
   - Once the container is running and `project_mount` exists (polled via a transport-independent Docker readiness check that works under both `contained` and `host-x11`), launch host VS Code detached (`--new-window --folder-uri vscode-remote://attached-container+<hex_json><project_mount>`, where `<hex_json>` is UTF-8 hex of `{"containerName":"/<container_name>"}`). On headless Linux (neither `DISPLAY` nor `WAYLAND_DISPLAY` set), print the exact attach command and a notice instead of failing the `xfce4-terminal` session.
   - Closing host VS Code leaves the container and agents in `xfce4-terminal` alive; closing `xfce4-terminal` ends the container cleanly.

## Scope & Guardrails

- **Included in this slice:** `host-ide` authorization (`false` default), `vscode` split-surface support (`xfce4-terminal` in container + host VS Code attach), `project run --print-command` output covering both the `docker run` command and the host `code` command, host `code` acquisition/isolated config home/extension provisioning, documentation updates under `docs/`, unit tests, and CLI/fake-`code` integration tests.
- **Explicitly deferred to the next slice:** VSCodium (`codium`) support (`open-remote-ssh` / host Codium profile). For this slice, enabling `host-ide = true` when the checkout's resolved `interactive-surface` is anything other than `vscode` must fail loudly with a clear message stating `host-ide` currently supports `vscode` only.
- **Engineering standards (`WORKFLOW-LOCAL.md`):**
  - Strictly obey *Host Inputs* rules 1–6 (pure decision/planning functions operating on values; entry layer performs host I/O, network, and subprocesses; frozen dataclasses; no `monkeypatch` or `unittest.mock` in new or changed unit tests).
  - Strictly obey *Unit Tests* rules 1–9 (mirror paths under `tests/unit/devcapsule/`, plain-English docstrings on every test, do not edit individual tests in `legacy` files without full-file refurbishment).
  - Preserve documentation contract (`nox -s docs-contract`), `mypy` (`nox -s typecheck`), unit test conventions (`validate_unittests_follow_conventions.py`), and `nox -s build` (gate).
