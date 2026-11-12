---
status: closed
severity: minor
target: 0.3.0
owner: maintenance
opened: 2026-08-15
requirements: [R-SCOPE-001, R-DOCKER-001, R-PRODUCT-002]
---

# Bug: Detached DevCapsule Containers Exit And Are Never Cleaned Up

Date opened: 2026-08-15

Status note (pre-vocabulary, kept as evidence): open

Requirements: R-SCOPE-001, R-DOCKER-001, root R-PRODUCT-002

## Symptom

DevCapsule tells developers that closing the IDE ends the environment and
leaves nothing behind. The ordinary foreground launch honours that: it runs
`docker run --rm`, so the container is removed when the IDE exits.

The detached launch path does not. Its containers exit normally and then stay
on the host indefinitely as `Exited (0)` objects. Nothing reaps them, and no
command surfaces them to the developer. A developer who has used the detached
path accumulates stopped containers that they did not ask for and are not told
about, which is not the lifecycle the product promises.

## Evidence

Observed on the development host on 2026-08-15:

```
devcapsule-e2e-482c34f24fc5c438da7b24ff172a619b-successor  Exited (0) 15 hours ago
devcapsule-e2e-b2093d85912fa34ac1324e1da26a9dcd-successor  Exited (0) 2 days ago
```

Both were launched detached through
`devcapsule project recursive-e2e launch-successor`. Both exited on their own
when their IDE closed. Neither was removed, and both still hold their image
reference, name, and writable layer.

The foreground contrast is in `build_docker_args`: `ContainerLifecycle.foreground`
emits `--rm`, and `ContainerLifecycle.detached` emits `--detach` with no
removal policy and no later reaping.

That contrast was confirmed directly on 2026-08-15. A foreground
`devcapsule project run` against the sample project started container
`pycharm-isolated-costin-1786756024`; when its client exited, the container was
removed with no trace, exactly as the product promises. The two detached
containers above were launched the same way apart from lifecycle, and both
survive. The promise is kept on one path and silently broken on the other.

## Why This Is Not Simply The Retention Policy

Recursive-dogfood Stage 6 deliberately retains a successful successor so
Stage 7 can prove persistence, and deliberately retains failed runs as
diagnostic evidence. That retention is correct and must not be removed
blindly.

The defect is that retention is **indefinite, invisible, and unowned**:

- nothing distinguishes a container retained on purpose from one merely left
  behind after a normal exit;
- no command lists what DevCapsule is currently keeping, so a developer cannot
  discover the objects without knowing Docker;
- there is no expiry, no reaping, and no prompt; and
- the same silence applies to the run-owned staging directories and workspaces
  those containers reference.

The two containers above are labelled `devcapsule.e2e.*`, so exact,
ownership-checked cleanup is already possible. The information needed to do
this safely exists; nothing acts on it.

## Expected Behaviour

- A detached container that has exited is either removed, or retained under an
  explicit, recorded reason with an owner.
- A public command lists every container, staging directory, and workspace
  DevCapsule is currently retaining, together with why.
- A public command removes exactly those objects, selecting them by recorded
  identity and ownership labels rather than by name prefix.
- Cleanup never selects a container DevCapsule does not own, and never removes
  a run still recorded as retained evidence.
- The promise made to developers about environment lifecycle matches what the
  detached path actually does, or the documentation states the difference.

## Notes

The V1 backlog item *Owned Workspace And Manifest* already requires proving
that cleanup and repair affect only the exact ownership-marked run. This bug is
the user-visible consequence of that work being outstanding, and should be
closed by the same slice rather than separately.

Stage 7 of the recursive dogfood milestone is the natural home for the
implementation, since it already owns persistence and deterministic cleanup.
Until then, do not remove the two containers above: they are the retained
Stage 6 and Stage 7 evidence.

## Disposition, 2026-09-25

Owner ruling during 0.2.14 acceptance: deferred beyond 0.2.14 and marked
minor; no functional failure was reported on any 0.2.14 candidate.

## Triage and fix, 2026-10-04

Owner ruling during the 0.2.16 triage, after the question "why does the
recursive E2E have to launch detached?" found no answer: the only caller of
the detached lifecycle was `launch-successor`, a stage command that printed
a report and exited; nothing downstream needed a parentless container.
Inspection runs from outside while the container is alive, the operator
holds a terminal open exactly as for `project run`, a failed run's evidence
is the attached output, and Stage 7's persistence proof relaunches from
files, never from an exited container.

**Fix, on `ws-maintenance/post-0.2.15`:** `launch-successor` is the ordinary
attached `docker run --rm`. It learns the container ID from a `--cidfile`
while the container runs, inspects it, records `stage-6-running` in the run
manifest and prints the report, then stays attached until the container
exits and records `stage-6-exited` with the exit code; Docker has removed
the container and the run directory keeps `successor.log` and the manifest.
`inspect-successor` reports an exited successor instead of inspecting it.
`ContainerLifecycle` and its detached branch are deleted from the launcher:
one lifecycle for every launch. The listing-and-cleanup commands this
record's *Expected Behaviour* asked for are no longer needed for
containers; what remains of them, formations and cache, belongs to the
IDE-reuse design review (record of 2026-09-24, addendum on reaping).

**Verification:** unit tests cover the cidfile wait, the early-exit and
timeout failures and the exited report (`tests/test_recursive_successor.py`);
the opt-in `tests/e2e/test_recursive_successor_attached_launch.py` drives
the command like the IDE smoke test drives `project run`: start, wait for
running, inspect independently, `docker stop`, wait for the command to
return, assert the container is gone and the evidence kept. The end-to-end
run in this repository's capsule on 2026-10-04 failed fast before the
launch, for a reason outside this fix: the recursive launch reads the
capsule-local copy of the checkout resolution (Stage 5's isolated HOME),
which was stale against the lock, and `config resolve` inside the capsule
is refused by the in-capsule guard that the 2026-09-24 inspection record
targets at 0.2.16. Close when that run passes.

## Proof on source, 2026-10-05

The attached-launch end-to-end test passes from a fresh workspace in this
repository's 0.2.15 capsule (see the
[recursive-successor record](2026-10-04-recursive-successor-cannot-refresh-its-capsule-local-resolution.md),
run `8a543a0613a9c1f22d839102d592c995`): the launch stays attached, the
successor is inspected while it runs, stopping it ends the command, Docker
removes the container, the run directory keeps the log and manifest.
Closes with the 2026-10-04 record on a 0.3.0 candidate.

## Downloaded RC9 verification — 2026-10-31

The attached-successor regression was rerun with every CLI operation selecting the published RC9 PEX. It launches and inspects the successor, stops it, observes the launcher exit, verifies Docker removed it and retained its evidence, then cleans the owned fresh workspace. The result passes in 8.66 seconds.

[Final audit evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#final-promotion-audit--2026-10-31).
Verification is complete; the release acceptance/closure checkpoint remains
pending the explicit final scope and provider dispositions.

## Closed — 2026-10-31

Closed on the RC9 verification above and the owner's final acceptance of
that exact candidate on 2026-10-31. [Acceptance record](../../releases/v0.3.0.json).
The fix is in RC9 source 475427da and main 4b59b10d; the documented test
limits are retained. This supersedes the pending-closure sentence above.
