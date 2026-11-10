# 0.3.1 — Bug Table

[Release overview](README.md)

Initial review: 2026-11-07 at the cut, `31e8fec7`. Reconciled before
`v0.3.1-rc2` at `be0140ca`; candidate 2 closures recorded 2026-11-10. The
linked records own status, severity, target, ownership and technical evidence;
this table mirrors those fields for review and records the release's
disposition and next action. Update the record and its row together; reconcile
before each candidate and record the reconciliation revision here.

## Records targeted at 0.3.1

| Record | Status | Severity | Owner | Disposition | Next action |
|---|---|---|---|---|---|
| [Eclipse cannot be acquired from scratch on amd64: the libsoup package URLs return 404](../../bugs/devcapsule/2026-11-07-eclipse-amd64-libsoup-urls-return-404.md) | closed | major | maintenance | found by PR #338 on 2026-11-04, confirmed at the cut; both packages repinned at `3.4.4-5ubuntu0.10` (PR #10), matrix `embedded-32`; closed 2026-11-08 by a fresh amd64 Eclipse acquisition with an empty home on the downloaded `v0.3.1-rc1` | none; the 0.3.0 executable stays affected, 0.3.1 is the remedy |
| [Codex status and version checks fail: the npm registry document exceeds the channel's 16 MiB cap](../../bugs/devcapsule/2026-11-08-codex-npm-metadata-exceeds-16-mib.md) | closed | major | maintenance | found 2026-11-08 reading the feed: Codex `inconclusive` for 45 runs since 2026-10-01; the full registry document is 18.7 MB against the channel's 16 MiB cap; resolved via PR #20 (`eb8ff8cf`, `Accept: application/vnd.npm.install-v1+json` in `NpmChannel.check()`); closed 2026-11-10 on `origin/component-status` (`0bc31c64`, `result: "ok"`, `consecutive_failures: 0`) and `project versions check` on downloaded `v0.3.1-rc2` (`2c3ace0f…`) | none; the 0.3.0 executable stays affected, 0.3.1 is the remedy |
| [Web console changes in `v0.3.1-rc1` do not reach capsules: the PEX omits the console package and the self-hosting override shadows it](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md) | closed | blocking | maintenance | found 2026-11-08 validating `v0.3.1-rc1` (`accdec5b`): `/files`, `/filetree`, and `/api/project/tree` returned `404`; resolved under `D-0017` via stacked PRs #18 (`b84b06e9`) and #16 (`f2bae5cb`); closed 2026-11-10 on downloaded `v0.3.1-rc2` (`2c3ace0f…`) serving `/files` (`200`), `/filetree` (`307 -> /files`), and `/api/project/tree` (`200`) on pre-PR-#12 `/opt/devcapsule-webconsole/venv` without a DevCapsule checkout mount | none |
| [Release-dependent test fixtures cause avoidable release PR churn](../../bugs/devcapsule/2026-10-31-release-dependent-test-fixtures.md) | confirmed | minor | maintenance | test-only; queued for 0.3.1 on 2026-10-31; not a gate of a candidate | the owner keeps it in the cycle or retargets it at planning |
| [Unit tests read the developer's real launcher settings inside a capsule: the consent and trust tests fail or prove nothing there](../../bugs/devcapsule/2026-11-10-unit-tests-read-the-capsules-mounted-launcher-settings.md) | confirmed | blocking | maintenance | filed 2026-11-10 at the owner's direction, to be fixed before 0.3.1 ships: `nox -s tests` in the owner's capsule gives 17 failed on `v0.3.1-rc2`, all passing once the mounted settings are hidden; the hosted run passes; one expected-to-fail test downloads 1.5 GB of vendor artifacts there, most of the local gate's twelve minutes; test-only, the product behaves as designed | make the isolation fixture a private home, then clear the expected-to-fail marks this cause explains; no fix started |
| [Markdown-only changes run the whole Python unit suite: the hosted path filter lists too few non-inputs, and the local gate has no filter](../../bugs/devcapsule/2026-11-10-markdown-only-changes-run-the-python-unit-suite.md) | fixing | major | maintenance | reported by the owner 2026-11-10 and re-rated major; the Python route becomes a short list of inputs, `.github/ci-python-inputs.yml`, and the unit suite is held to it by a guard in `tests/conftest.py`, on `ws-maintenance/python-route-guard` | the owner's review of that branch; then the local gate, and `docs/**` off the list when the legacy scan of `docs/` is retired |

Added after the `v0.3.1-rc2` reconciliation; the table is not reconciled
again until the next candidate.

## Related work that is not a release gate

- The seventeen tests expected to fail inside a capsule (#341), diagnosed
  on 2026-11-06 in the maintenance status: test work on `main`, repaired
  slice by slice, reaching the release only with the merges before each
  candidate. Since 2026-11-10 the tests among them that fail for the
  mounted launcher settings are covered by the blocking record above; the
  rest stay here.
- Release Policy rules 9 and 10 (#7) name a test-run record and a notes
  section that no script reads or renders yet. The record is kept by hand
  for 0.3.1; the forcing functions are an implementation slice on `main`.
