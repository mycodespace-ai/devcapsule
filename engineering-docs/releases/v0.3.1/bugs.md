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
| [Codex status and version checks fail: the npm registry document exceeds the channel's 16 MiB cap](../../bugs/devcapsule/2026-11-08-codex-npm-metadata-exceeds-16-mib.md) | confirmed | major | maintenance | found 2026-11-08 reading the feed: Codex `inconclusive` for 45 runs since 2026-10-01; the full registry document is 18.7 MB against the channel's 16 MiB cap; also breaks `project versions check` for Codex in the 0.3.0 and 0.3.1 launchers | fix slice on `release-0.3.1` before candidate 2: request the registry's abbreviated document, unit test with a constructed document, verify `project versions check` on the downloaded candidate and Codex `ok` in the next feed |
| [Web console changes in `v0.3.1-rc1` do not reach capsules: the PEX omits the console package and the self-hosting override shadows it](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md) | fixed | blocking | maintenance | found 2026-11-08 validating `v0.3.1-rc1` (`accdec5b`): `/files`, `/filetree`, and `/api/project/tree` returned `404`; resolved on `ws-maintenance/webconsole-delivery` under `D-0017`: `build-pex.sh` embeds `devcapsule_webconsole` in `devcapsule.pex`, `materialization.py` installs `/opt/devcapsule/webconsole` on the base's venv, and built launchers use their own console unless `DEVCAPSULE_DEV_WEBCONSOLE=1` opts in | merge `ws-maintenance/webconsole-delivery` into `release-0.3.1` before candidate 2; close on downloaded `v0.3.1-rc2` against a fresh non-DevCapsule project |
| [Release-dependent test fixtures cause avoidable release PR churn](../../bugs/devcapsule/2026-10-31-release-dependent-test-fixtures.md) | confirmed | minor | maintenance | test-only; queued for 0.3.1 on 2026-10-31; not a gate of a candidate | the owner keeps it in the cycle or retargets it at planning |

## Related work that is not a release gate

- The seventeen tests expected to fail inside a capsule (#341), diagnosed
  on 2026-11-06 in the maintenance status: test work on `main`, repaired
  slice by slice, reaching the release only with the merges before each
  candidate.
- Release Policy rules 9 and 10 (#7) name a test-run record and a notes
  section that no script reads or renders yet. The record is kept by hand
  for 0.3.1; the forcing functions are an implementation slice on `main`.
