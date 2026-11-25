# Check All Existing Components for Version Upgrades (`release-0.3.1`)

**From:** `project-management`
**To:** `component-catalog`
**Date:** 2026-11-25
**Target release:** `release-0.3.1` (owner direction, 2026-11-25)

## What Is Handed Over

Execute the all-component version upgrade check across every existing component in the `release-0.3.1` catalog and resolution matrix (IDEs, agent CLIs, SDKs, browsers, and tools including `graphviz` and `xfce4-terminal`) and deliver any verified pin upgrades and the per-component outcome summary for `release-0.3.1`.

## Why It Belongs to `component-catalog`

The owner assigned implementation of the full-catalog upgrade check to `component-catalog` on 2026-11-25, fulfilling the November 17 standing release-sweep rule (`coordination-backlog.md` item 1) for `release-0.3.1`.

## Scope and Finish Criteria

1. **Check every existing component:** Probe upstream channels (e.g., `devcapsule project versions check` and platform pin sources for both `linux-amd64` and `linux-arm64`) for every component currently in `devcapsule/components/` and `resolution_matrix.py`.
2. **Record exactly one outcome per component:**
   - **Upgraded:** updated checksum-pinned artifact(s), matrix edge(s), and validation evidence in a PR targeting `release-0.3.1`.
   - **No update needed:** recorded reason (already latest, or upstream unchanged).
   - **Deferred update:** open a bug record under `engineering-docs/bugs/` (or update an existing one) targeted at the next release after `0.3.1`, with the concrete reason/evidence; never treat an unsuccessful probe as "no update needed".
3. **Deliver sweep summary:** Provide the complete component outcome table so `maintenance` / `engineering-docs/releases/v0.3.1/README.md` can record closure of the `0.3.1` all-component freshness review.

## What Accepting This Means

Acknowledge this item on `component-catalog`, run the full-catalog upgrade check against `upstream/release-0.3.1`, submit pin-upgrade PR(s) targeting `release-0.3.1`, and publish/share the per-component sweep table.
