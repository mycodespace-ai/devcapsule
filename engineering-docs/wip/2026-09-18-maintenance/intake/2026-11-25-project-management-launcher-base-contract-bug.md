# Notice: `0.3.1` Bug Filed for `devcapsule`-to-Base-Image Contract & Enforcement

**From:** `project-management`
**To:** `maintenance`
**Date:** 2026-11-25

## What Is Handed Over

Informational notice (per `WORKFLOW.md` topic 12.5 rule 12, since `ws-project-management/coordination` has not yet merged to `main`): `project-management` has filed a `0.3.1` bug owned by `maintenance` at:

- `engineering-docs/bugs/devcapsule/2026-11-25-launcher-lacks-base-image-compatibility-contract-and-enforcement.md` (on `ws-project-management/coordination`)

(Note: per topic 12.5 rule 13, a bug record is routed by its `owner: maintenance` field, not by intake disposition; this item simply alerts `maintenance` before `ws-project-management/coordination` integrates to `main`.)

## Why It Belongs to `maintenance`

The owner accepted `2026-11-17-presentations-launcher-base-requirements.md` as a bug (`owner: maintenance`, `target: 0.3.1`) on 2026-11-25, with the explicit extra requirement to **document the contract between the `devcapsule` utility and the base image with regards to running `devcapsule`** (in addition to enforcing mandatory base compatibility and preserving explicit optional degradations).

## Evidence and Requirements

- Requirements: `R-COMPAT-001`, `R-RUNTIME-001`, `R-CONSOLE-001`.
- Code evidence from `c5549f72` (`environment_realization.py`, `materialization.py`, `images/contract.py`, `commands/project.py`, `launch/pycharm/_launcher.py`, `container_runtime/console.py`) is recorded in the bug file.

## What Acting on It Means

Triage the bug's severity (`severity: untriaged` → `blocking`/`major`/`minor`), document the utility-to-base-image running contract under `engineering-docs/specifications/devcapsule/` (linked from `index.md`), and implement/verify launcher-to-base enforcement and degradation boundaries for `0.3.1`.
