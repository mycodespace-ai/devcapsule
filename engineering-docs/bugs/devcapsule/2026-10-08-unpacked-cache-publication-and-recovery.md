---
status: closed
severity: minor
target: 0.3.0
owner: maintenance
opened: 2026-10-08
requirements: [R-IMAGE-BUILD-001]
---

# Unpacked archive cache can lose concurrent work and trust incomplete entries

Found during review of [PR #172](https://github.com/ccozianu/devcapsule/pull/172)
at `4be56a7`. Different formations can unpack the same archive concurrently,
but their formation locks do not serialize the shared digest cache. A delayed
cache miss can delete another caller's completed entry; callers in the same
process also collide on the staging path. The marker reader accepts missing or
escaping roots and ignores the digest/schema. Extraction failure retains a
PID-named partial tree that a later process never cleans up.

Expected: a complete tree remains usable by its callers, only a structurally
valid completion record is reused, and interrupted preparation can be retried
without accumulating another abandoned staging tree each time.

Fixed on `ws-maintenance/pr172-correctness`: per-digest locking, bounded marker
validation, and one recoverable staging path with cleanup on failure. The
test-only commit `ac20182` demonstrates seven failures before the correction.
See the [review and evidence](../../wip/2026-09-18-maintenance/2026-10-08-pr172-review.md)
for the exact cases and limits. Close after the stacked fix and #172 reach main;
no released-candidate acceptance is claimed.

## Downloaded RC9 verification — 2026-10-31

All 17 unpacked-cache regression cases pass against the devcapsule-0.3.0rc9 wheel inside the downloaded PEX. The PEX interpreter pre-imported the packaged module before pytest loaded the existing test file; the recorded package path confirms this was not a source-only retest.

[Final audit evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#final-promotion-audit--2026-10-31).
Verification is complete; the release acceptance/closure checkpoint remains
pending the explicit final scope and provider dispositions.

## Closed — 2026-10-31

Closed on the RC9 verification above and the owner's final acceptance of
that exact candidate on 2026-10-31. [Acceptance record](../../releases/v0.3.0.json).
The fix is in RC9 source 475427da and main 4b59b10d; the documented test
limits are retained. This supersedes the pending-closure sentence above.
