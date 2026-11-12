---
status: confirmed
severity: minor
target: 0.3.1
owner: maintenance
opened: 2026-10-31
requirements: []
---

# Release-dependent test fixtures cause avoidable release PR churn

## Symptom and expected behavior

The owner reported this maintenance defect while reviewing RC9 preparation
PR #329: future release preparation should touch fewer files by reducing
hard-coded current-release and component values in unrelated behavioral tests.
Tests documented as checking CLI refusal/remedy behavior or base contracts
currently fail after a valid catalog refresh unless their literal expected
versions are also edited. The behavior being tested has not changed.

Behavior tests should remain valid when production pins advance without a
change to the tested contract. Historical compatibility tests must retain
intentional old values. Exact artifact digests, independently checked release
metadata and deliberate lock snapshots remain necessary evidence; removing
all hard-coded values is not the objective.

## Environment and evidence

Observed in the 0.3.0 RC9 preparation branch at `eb6a9c6d`, against main
`ce08ebad` (whose authored launcher version is 0.3.1.dev0).

- `devcapsule-src/tests/test_project_init.py`: unverified-selection and
  acquisition tests name Antigravity 1.4.12 and the exact current base
  mnemonic inside expected messages and lock assertions. The sparse matrix
  fixture derives from the production catalog, so a pin refresh changes
  these behavior tests' inputs implicitly.
- `devcapsule-src/tests/test_resolution_matrix.py`: generic resolution and
  provenance assertions repeat current base and IDE versions separately
  from production pins and the captured golden locks.
- `devcapsule-src/tests/test_base_contract.py`: several generic contract and
  consent tests read this repository's live manifest/lock, then assume its
  rc6 base. Updating the development checkout's lock can therefore invalidate
  tests unrelated to that checkout. The newly added public-source provenance
  regression also names two real digests, a build mnemonic and a commit SHA
  where fixed synthetic provenance could test the same contract.
- The base pin refresh changed 11 golden locks plus test expectations in
  multiple modules. Snapshot changes are intentional, but their repeated
  catalog fragments should be evaluated for avoidable duplication without
  losing byte-level lock-format coverage.

## Reproduction

1. Compare `ce08ebad..eb6a9c6d` for the three test modules above and the
   production resolution matrix.
2. Observe that version literals in refusal/remedy tests change alongside
   pins, although refusal/remedy behavior does not change.
3. In an isolated test fixture, advance a valid component/base pin while
   leaving those literal assertions unchanged. The generic behavior test
   expects the old version and fails on otherwise correct output.

The source diff establishes coupling. The isolated refresh experiment is a
verification target for the fix, not a run claimed by this record.

## Mainline integration and current hypothesis

A launcher version, a base builder's version and an agent version are separate
identities. Main at 0.3.1.dev0 may legitimately use a base built during 0.3.0.
The release's catalog and matching expectations should propagate together;
do not mechanically replace every 0.3.0 string with 0.3.1. An October 31
merge-tree preview against ce08ebad merges both named test files cleanly;
conflicts are in the two status records and docs/versions.yaml. This is a
mechanical preview, not validation of the final main integration.

The evidenced causes are behavioral fixtures coupled to the live catalog,
repeated current-pin expectations, and tests coupled to the contributor
checkout's live lock. If main later has newer pins, integration must retain
its intended catalog and validate tests against that catalog rather than
blindly taking release-side expectations.

## Verification target and close criteria

- Use explicit, stable synthetic catalogs/locks for generic CLI and contract
  tests, independent of the installed project lock and current production pins.
- Keep historical compatibility examples explicit and independently asserted.
- Keep a focused check of real catalog defaults/artifact provenance with an
  independent expected source. Do not replace assertions with values read
  from the same result or computation under test.
- Reduce repeated snapshot/catalog data where practical while retaining
  meaningful serialization and integration coverage.
- Demonstrate a representative next pin refresh without edits to unrelated
  behavior-test modules, and a checkout-lock refresh without unrelated
  contract-test failures. Record the before/after changed-file inventory.
- Demonstrate that a broken refusal message, provenance URL or compatibility
  rule still fails the relevant test; run the normal gate on the integrated tree.

## Fix notes

No refactor is included in 0.3.0. Owner-directed target is 0.3.1. Next action:
maintenance isolates the fixtures and verifies a representative pin refresh.
