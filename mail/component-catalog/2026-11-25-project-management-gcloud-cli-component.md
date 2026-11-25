# Implement `gcloud` (Google Cloud CLI) as an Available Component (`release-0.3.1`)

**From:** `project-management`
**To:** `component-catalog`
**Date:** 2026-11-25
**Target release:** `release-0.3.1` (owner direction, 2026-11-25)

## What Is Handed Over

Implement `gcloud` (Google Cloud CLI) as an available optional component in the DevCapsule component catalog for `release-0.3.1`.

## Why It Belongs to `component-catalog`

`component-catalog` owns optional CLI/tool components, checksum-pinned platform artifacts, channel freshness probes, and catalog smoke coverage (`R-PRODUCT-001`, `R-PRODUCT-002`, `R-SCOPE-001`, `R-DOCS-002`).

## Scope and Finish Criteria

1. **Capability & component declaration:** Expose `gcloud` as an optional catalog capability/component on `linux-amd64` and `linux-arm64` using official checksum-pinned Google Cloud CLI archives. Keep it strictly separate from Gemini CLI, which remains unselected per `CURRENT-STATUS.md` *Shared Constraints*.
2. **Freshness / channel probe:** Add upstream release probing for `gcloud` so `devcapsule project versions check` / `component-status` tracks new versions.
3. **Persistence & auth boundary:** Do not mount host `$HOME/.config/gcloud` or host ADC credentials by default; declare capsule-managed persistence and explicit auth/secret bindings per `R-PRODUCT-002` and `R-SCOPE-001`.
4. **Tests & docs:** Add unit tests (following `WORKFLOW-LOCAL.md` *Unit Tests* rules 1–4 and *Host Inputs* rules 1–6), a non-interactive smoke check (e.g., `gcloud version`), and user documentation under `docs/`.

## What Accepting This Means

Acknowledge this item on `component-catalog`'s working branch forked from `upstream/release-0.3.1`, implement the `gcloud` component in a PR targeting `release-0.3.1`, and record its validation evidence.
