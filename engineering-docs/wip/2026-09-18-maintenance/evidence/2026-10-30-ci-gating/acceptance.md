# CI gating acceptance — 2026-10-30

Implementation: [PR #312](https://github.com/ccozianu/devcapsule/pull/312),
`ws-maintenance/ci-gating-030` into `release-0.3.0`.
Order: [CI path gating and advisory diff coverage](../../../../work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md).
Pair: GPT-6 Codex implements; Claude Code / Claude Fable 5.1 reviews.
Status: implementation and Pair Review validated; owner merge and required-check
settings remain outstanding.

## Local evidence before review

Source `3115b19e` (the code tree was tested before the commit; records and the
workflow-SHA checkout adjustment were added while the gate ran):

- `pytest --no-cov -q tests/test_ci_reporting.py`: 56 passed, including a
  temporary real Git repository, actual coverage.py XML and diff-cover 10.6.0
  JSON. The changed line at `devcapsule-src/devcapsule/sample.py:3` is uncovered;
  the report is below 85% and the tool exits successfully. The bridge produces
  the correct repository-relative path and line.
- Focused mypy on both helpers and their test module: three files, clean.
- `nox -s build`: 2,630 unit tests passed, 40 deselected, one xfail and one
  XPASS; mypy clean; 18 packaging tests passed; source and PEX smokes passed;
  docs contract passed for 192 pages including 18 aliases. The notified
  console session passed 357 tests and mypy on nine files.
- Twenty routing cases passed with the actual picomatch installed by the
  pinned website dependencies, using `dot: true` and the every predicate.
  Cases include planning-only, README, journal, release notes, packaged
  Markdown, web-console code, workflow definitions and unknown files.

Scratch was `/var/tmp/maintenance-ci`, outside the mounted project, because
`/opt/devcapsule-gate` is unavailable. No Docker, capsule or service ran during this local gate.

## Hosted findings and fixes

The first hosted run
[40987146695](https://github.com/ccozianu/devcapsule/actions/runs/40987146695)
selected both jobs. Website verification found three pre-existing links to
`project-versus-personal/#when-the-project-changes`, whose section was renamed
by the earlier CLI documentation slice. Commit `8bbb0064` restores that stable
HTML anchor without changing prose. The local docs contract did not catch
this rendered-anchor failure; the newly added full website build did.
This first run was later cancelled by the next push, so it is not a passing
acceptance run. The failure is retained as evidence, not hidden by a weaker gate.

## Native annotation and advisory-policy evidence

Temporary draft [PR #313](https://github.com/ccozianu/devcapsule/pull/313),
commit `421a06ba`, adds only a two-line unexecuted runtime fixture beyond
PR #312. Its [hosted run](https://github.com/ccozianu/devcapsule/actions/runs/40987920651)
passed routing, website verification, Python tests and ci-gate with **0%**
changed-line coverage (two measured lines, both uncovered). It is acceptance
evidence only and was closed without merge; the fixture is absent from PR #312.

The [downloaded report](annotation-probe-report.json) records those numbers.
The [GitHub check annotation](annotation-probe-check.json) names the exact
fixture path and lines 1–2. A fresh, unauthenticated headless Chromium page
on GitHub's Files changed tab displayed the warning attached to that diff;
[the screenshot](native-pr-annotation.png) shows the native banner. This is
observed GUI behavior, not an inference from stdout or the API. No credential
or token is embedded in the evidence.

The ordinary implementation run at `8bbb0064`,
[40987508641](https://github.com/ccozianu/devcapsule/actions/runs/40987508641),
also passed all applicable jobs. The local full website build after the
anchor restoration checked 196 HTML pages and 14,403 local links/assets/
anchors successfully. The main-only badge job correctly skipped both PRs.

## Pair Review and final combined gate

[Review PR #314](https://github.com/ccozianu/devcapsule/pull/314), Claude Code /
Claude Fable 5.1, was accepted at `2dd3f14e` without a revision round and merged
at `0ea320e9`. The implementor read the complete diff and independently ran
all 70 focused tests before merging. Corrections cover the peeled action
commit pin, real release-doc test inputs, the 3000-file API limit, and more
faithful routing and nested-path tests. The review crosschecked 1,295 matcher
pairs against the action's actual picomatch 2.3.1 with no mismatch.

Both reviewer and implementor passed the full gate independently. The final
combined `nox -s build` gate at `0ea320e9` passed 2,644 unit tests (40 deselected,
one xfail and one XPASS), 18 packaging tests, source/PEX smokes, type checks,
the 192-page documentation contract including 18 aliases, and the notified
web-console gate's 357 tests and type checks. Scratch log:
`/var/tmp/maintenance-ci/final-gate.log` (not a permanent artifact).

The reviewed source's [hosted run 40989994671](https://github.com/ccozianu/devcapsule/actions/runs/40989994671)
passed Python, website verification and ci-gate. The badge job skipped correctly.

## Hosted routing acceptance

Closed, unmerged [probe PR #315](https://github.com/ccozianu/devcapsule/pull/315)
used an isolated base with reviewed source `0ea320e9` plus a temporary PR-trigger
allowlist entry for that base branch. This lets GitHub exercise the reviewed
filters and gate before release integration; the temporary trigger and fixtures
are absent from PR #312. Neither acceptance branch is to be merged.

- Planning-only head `1be2e932`, [run 40990213893](https://github.com/ccozianu/devcapsule/actions/runs/40990213893):
  changes and ci-gate passed; Python and website both skipped.
- README/site-input head `a44c25d9`, [run 40990609919](https://github.com/ccozianu/devcapsule/actions/runs/40990609919):
  changes, website verification and ci-gate passed; Python skipped.

## Required-check settings

Read-only GitHub API inspection on 2026-10-30 found one active ruleset,
25144717, `main: no force push, no deletion`, matching the default branch and
containing only deletion and non-fast-forward restrictions. Classic branch
protection reports `Branch not protected` (404) for main and release-0.3.0.
No required status check exists to replace. No settings were changed.

After successful representative hosted runs, the owner must add `ci-gate`
as a required check on the intended integration branches, retaining other
protections. YAML and a green job alone do not establish this acceptance step.

## Remaining acceptance

- Required-check settings action by the owner.
- Human merge into the release branch and normal 0.3.0 release propagation.
