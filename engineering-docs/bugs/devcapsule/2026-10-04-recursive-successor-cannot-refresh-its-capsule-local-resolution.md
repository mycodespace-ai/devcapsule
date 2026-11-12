---
status: closed
severity: minor
target: 0.3.0
owner: maintenance
opened: 2026-10-04
requirements: [R-PRODUCT-001, R-COMPAT-001]
---

# The recursive successor cannot be launched: its capsule-local resolution is stale and nothing inside the capsule may refresh it

## Symptom

Inside this repository's own capsule (released 0.2.15, checkout
`devcapsule-2nd-home`, host Docker granted), the recursive dogfood's
`launch-successor` exits with status 2 before any launch:

```text
devcapsule: Local resolution is stale (manifest, platform-lock); run 'devcapsule project config resolve'.
```

The remedy it names is refused in the same capsule:

```text
$ devcapsule project --path /workspace/301e4208ef81-ChatGPT_Codex config resolve
devcapsule: This command needs launcher-owned configuration or state. Inside this capsule that
configuration is read-only. Run outside the capsule: devcapsule project --path /home/costin/... config resolve
```

Running it outside the capsule, as advised, does not help: it refreshes
the host's record, which is not the one the recursive launch reads.

Found on 2026-10-04 by the new end-to-end test
`tests/e2e/test_recursive_successor_attached_launch.py`, which failed fast
with the first message. The recursive preflight reports `ready: true` for
the same capsule, so the preflight does not cover this condition either.

## Expected behavior

`launch-successor` launches, or the preflight says why it cannot and names
a remedy that works where the operator is.

## Cause

Two rules that are each right on their own meet badly:

1. **Stage 5 isolates HOME for checkout-local configuration.** The recursive
   launch resolves the checkout through `fresh_resolved_project(checkout)`,
   which reads the checkout record and resolution under the capsule's own
   XDG configuration root, `/home/devcapsule/.config/devcapsule/projects/.../devcapsule/`.
   That copy was written on 2026-09-14 and is stale against the platform
   lock of 2026-09-27; `ExecutionConfiguration.load` refuses stale inputs
   and points at `config resolve`.
2. **Inside a capsule, mutating `project` commands are launcher-only.** The
   guard in `ProjectCommand.make_context` refuses `config resolve` whenever
   the project is the capsule's own, and the remedy it prints targets the
   host record, which the recursive flow never reads.

So the capsule-local copy can go stale and nothing is allowed to refresh
it. Before the guard existed (0.2.14), the operator refreshed it by hand;
since then the recursive dogfood has been unrunnable from a capsule whose
lock moved, and nobody ran it to notice.

## Fix options, for the owner's design review

- **A. The recursive launch resolves its own copy.** `launch_successor` calls
  `resolve_checkout(checkout)` under the isolated HOME before loading the
  resolution. The record it writes is the dogfood's own, in the capsule's
  home, not the launcher-owned host state the read-only rule protects; the
  guard stays as it is for users. One call, plus the preflight reporting
  staleness as a named check. This is the fix the agent proposed on
  2026-10-04; the owner asked for the record first.
- **B. The guard admits `config resolve` for the capsule-local copy** when
  the recursive environment variable is set. Wider than needed, and it
  reopens the question the 2026-09-24 inspection record settled.
- **C. The recursive launch reads the mounted read-only runtime context**
  instead of a capsule-local copy. The cleanest in principle, but it changes
  Stage 5's isolation and the plan the inspector compares against.

Option A is the recommendation. Whichever is chosen, the preflight gains a
check for a stale capsule-local resolution with the remedy that works.

## Decision, 2026-10-05: option D, the test stops sharing the capsule's record

Owner ruling during the 0.2.16 triage, after a reading of the code with the
agent. Options A, B and C are set aside. They all keep what causes the bug:
a checkout record shared between the capsule's ordinary configuration
directory and the recursive launch, which nothing may refresh.

The attached-launch test today runs against the live working tree, never
checks for uncommitted changes, fakes the clean-clone stage by writing a
`stage-5-materialized` manifest, and lets `launch_successor` read the
capsule-local record through the ambient `XDG_CONFIG_HOME`. "Stage 5
isolates HOME" exists only as a comment; the milestone plan of 2026-08-06
(stage 5 confines checkout, resolution, cache and state to the run root;
stage 6 rejects a dirty source and a stale resolution) was never built for
this test. The sibling `test_recursive_local_clone.py` already has the
pieces: a `git clone --local` into the run workspace, a hard failure on a
dirty source, and isolated XDG roots under the run root.

**Option D.** The test:

1. refuses to run when the source checkout has uncommitted changes;
2. clones the current branch from the local tree into a fresh run
   workspace under the persistent home's E2E workspace, a host-backed path
   the daemon can bind (not `/tmp`, which inside a capsule is a 2 GB
   container-local tmpfs the host daemon cannot see);
3. resolves the clone under XDG roots isolated beneath the run root. The
   in-capsule guard does not fire: it keys on the project root equalling the
   launch context's `runtime-root`, and the clone's root differs;
4. launches the successor from that clone and that resolution;
5. on a best-effort basis removes the workspace and frees the space at the
   end.

No product code changes. The preflight may still gain a named check for a
stale resolution; that is a nicety, not the fix.

**General rule, same ruling.** Every end-to-end test runs on a fresh
workspace: a clean clone, its own resolution, isolated configuration roots,
never the live checkout or the capsule's own records. This removes the
circular dependency between the repository under test and the capsule that
tests it. Cleanup at the end is best effort. The rule is recorded in
[end-to-end tests](../../development/e2e-tests.md); suites that do not yet
follow it are brought into line as they are touched.

## Verification target

`tests/e2e/test_recursive_successor_attached_launch.py` passes inside a
capsule whose lock moved after launch, from a clean clone in a fresh
workspace, with the capsule's own stale record left untouched; `recursive-e2e preflight` names the
stale resolution before the fix and reports clean after it. Unit coverage
for the preflight check.

## Close criteria

The end-to-end test passes in this repository's capsule on a 0.2.16
candidate, and the 2026-08-15 detached-successor record closes on the same
run.

## Fix, 2026-10-05, on `ws-maintenance/post-0.2.15`: option D built and proven

`tests/e2e/fresh_workspace.py` is the fresh workspace every end-to-end
test is to use: `require_clean_source` refuses a dirty source (submodule
worktrees ignored, since the clone never recurses into them);
`FreshWorkspace.create` clones HEAD with `git clone --local --no-hardlinks
--no-checkout --no-recurse-submodules` under an allowlisted Git
environment into an owned run directory under the persistent home's E2E
workspace, checks out the exact revision detached, removes the local
origin; `configure_like_this_capsule` answers the clone's authorizations
and values as the mounted launch record answered them, through `config
authorize`, `config set` and `config resolve` with `XDG_CONFIG_HOME`,
`XDG_DATA_HOME`, `XDG_STATE_HOME` and `XDG_CACHE_HOME` under the run
directory; `cleanup` removes the run directory, best effort.

`test_recursive_successor_attached_launch.py` now builds that workspace
first and drives `launch-successor` on the clone under the isolated
roots. It also proves the capsule's own records under the capsule's
configuration root are byte-for-byte untouched by the run. No product
code changed; the guard, the stale capsule-local copy and Stage 5's HOME
comment are all left exactly as they were, because the test no longer
depends on them.

Evidence, this repository's 0.2.15 capsule, 2026-10-05: the first run
refused the dirty source (the uncommitted test files themselves); after
the commit, run `8a543a0613a9c1f22d839102d592c995` cloned, configured and
resolved under the run root, launched successor container `d625278fe691`
from formation `devcapsule-local-pycharm:e8f9b0c12623d7d366ca`, passed all
eleven inspection checks, was stopped, exited with Docker removing the
container, and the run directory was removed: `1 passed in 9.35s`, the
formation being cached. Docker's event log confirms create, start,
exec and removal under the run's label.

The preflight check for a stale resolution named above as a nicety is not
added. Closes when the owner confirms on a 0.3.0 candidate; the
2026-08-15 detached-successor record closes on the same run.

## Downloaded RC9 verification — 2026-10-31

The attached-successor regression passes with the published RC9 PEX for every CLI operation and supported init --regenerate for the isolated fresh clone. The original lifecycle, independent inspection, cleanup and own-record-unchanged assertions pass. No live checkout configuration was changed.

[Final audit evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#final-promotion-audit--2026-10-31).
Verification is complete; the release acceptance/closure checkpoint remains
pending the explicit final scope and provider dispositions.

## Closed — 2026-10-31

Closed on the RC9 verification above and the owner's final acceptance of
that exact candidate on 2026-10-31. [Acceptance record](../../releases/v0.3.0.json).
The fix is in RC9 source 475427da and main 4b59b10d; the documented test
limits are retained. This supersedes the pending-closure sentence above.
