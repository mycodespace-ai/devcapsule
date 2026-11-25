# Implement `gh` (GitHub CLI) as an Available Component (`release-0.3.1`)

**From:** `project-management`
**To:** `component-catalog`
**Date:** 2026-11-25
**Target release:** `release-0.3.1` (owner direction, 2026-11-25; supersedes the 2026-11-17 manual-only deferral in item 9 of the coordination backlog and activates the item queued after Xfce Terminal)

## What Is Handed Over

Implement `gh` (GitHub CLI) as an available optional component in the DevCapsule component catalog for `release-0.3.1`, delivering the scope already queued after Xfce Terminal (`PR #62`, merged in `release-0.3.1` at `8d71b26c`).

## Why It Belongs to `component-catalog`

`component-catalog` owns optional CLI/tool components, checksum-pinned platform artifacts, channel freshness probes, and catalog smoke coverage (`R-PRODUCT-001`, `R-PRODUCT-002`, `R-SCOPE-001`, `R-DOCS-002`).

## Scope and Finish Criteria

1. **Capability & component declaration:** Expose GitHub CLI (`gh`) as an optional catalog capability/component across supported capsule platforms (`linux-amd64` and `linux-arm64`), using official GitHub CLI release artifacts with checksum pins (do not depend on `/opt/xtras/miniconda3`).
2. **Freshness / channel probe:** Add upstream release probing for `gh` so `devcapsule project versions check` / `component-status` tracks new releases.
3. **Persistence & auth boundary:** Keep host `~/.config/gh` unmounted by default; bind capsule-managed auth/config state explicitly and keep credential/token handling explicit per `R-PRODUCT-002` and `R-SCOPE-001`.
4. **Tests & docs:** Add unit tests (following `WORKFLOW-LOCAL.md` *Unit Tests* rules 1–4 and *Host Inputs* rules 1–6), a read-only CLI/API smoke check, and user documentation under `docs/`.

## What Accepting This Means

Acknowledge this item on `component-catalog`'s working branch forked from `upstream/release-0.3.1`, implement the `gh` component in a PR targeting `release-0.3.1`, and record its evidence. Once shipped, `WORKFLOW-LOCAL.md`'s interim Miniconda `gh` hack can retire in a follow-up.
