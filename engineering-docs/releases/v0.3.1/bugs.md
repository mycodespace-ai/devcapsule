# 0.3.1 — Bug Table

[Release overview](README.md)

Initial review: 2026-11-07 at the cut, `31e8fec7`. The linked records own
status, severity, target, ownership and technical evidence; this table
mirrors those fields for review and records the release's disposition and
next action. Update the record and its row together; reconcile before each
candidate and record the reconciliation revision here.

## Records targeted at 0.3.1

| Record | Status | Severity | Owner | Disposition | Next action |
|---|---|---|---|---|---|
| [Eclipse cannot be acquired from scratch on amd64: the libsoup package URLs return 404](../../bugs/devcapsule/2026-11-07-eclipse-amd64-libsoup-urls-return-404.md) | closed | major | maintenance | found by PR #338 on 2026-11-04, confirmed at the cut; both packages repinned at `3.4.4-5ubuntu0.10` (PR #10), matrix `embedded-32`; closed 2026-11-08 by a fresh amd64 Eclipse acquisition with an empty home on the downloaded `v0.3.1-rc1` | none; the 0.3.0 executable stays affected, 0.3.1 is the remedy |
| [Release-dependent test fixtures cause avoidable release PR churn](../../bugs/devcapsule/2026-10-31-release-dependent-test-fixtures.md) | confirmed | minor | maintenance | test-only; queued for 0.3.1 on 2026-10-31; not a gate of a candidate | the owner keeps it in the cycle or retargets it at planning |

## Related work that is not a release gate

- The seventeen tests expected to fail inside a capsule (#341), diagnosed
  on 2026-11-06 in the maintenance status: test work on `main`, repaired
  slice by slice, reaching the release only with the merges before each
  candidate.
- Release Policy rules 9 and 10 (#7) name a test-run record and a notes
  section that no script reads or renders yet. The record is kept by hand
  for 0.3.1; the forcing functions are an implementation slice on `main`.
