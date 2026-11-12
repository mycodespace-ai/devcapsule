# Pair Review brief: Claude Code / Claude Fable 5.1, PR312.1

GPT-6 Codex opened draft PR #312, "Gate CI by affected paths and publish
advisory diff coverage", from `ws-maintenance/ci-gating-030` at `3115b19e`
into `release-0.3.0`. The owner explicitly requests Pair Review with you,
Claude Code / Claude Fable 5.1 (`claude-fable-5-1`). Review and improve this
one slice, then deliver a review PR against the implementor branch. No prior
review round exists. This brief is your task context.

## Checkout and reading order

Work only in `/home/devcapsule/worktrees/maintenance-ci-review`, branch
`ws-maintenance/ci-gating-030-review`, initially at `3115b19e`. Do not touch
`/home/devcapsule/worktrees/maintenance-ci` or the original checkout at
`/workspace/301e4208ef81-ChatGPT_Codex`.

Read first: AGENTS.md, README.md, DEVELOPING.md, the workflow declaration,
WORKFLOW.md (especially 9.11), WORKFLOW-LOCAL.md, then
`engineering-docs/work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md`.
Read the CI section at the top of maintenance's CURRENT-STATUS.md. Read
`.github/workflows/tests.yml`, `.github/ci-paths.yml`, the two new helpers
`devcapsule-src/scripts/ci_gate.py` and `diff_coverage_annotations.py`, and
`devcapsule-src/tests/test_ci_reporting.py`. Read their actual implementations,
not only search output. Follow only dependencies relevant to this slice.
Your reviewer role overrides ordinary intake/claim/status editing instructions:
the implementor handles those records. Do not run mail take or publish.

## Scope and decisions

The owner's decisions are final: coverage is advisory, and parallel execution
is deferred beyond 0.3.0. Retain Python 3.12 branch coverage and serial tests.
Do not introduce a threshold, xdist, sysmon, Docker, a new hosted console
suite, product behavior changes or website implementation changes. The
separate console gate and broader testing-policy reconciliation stay separate.
No generic workflow naming edits; that accepted release task is a later slice.

The work adds conservative path routing, website tests/build, a fail-closed
aggregate, diff-cover with native annotations and complete artifacts, developer
instructions and ignores. Main pushes, release-base PRs, manual refs, badge
publication and test marker exclusions must remain valid. PR coverage and tests
use the PR head SHA, with the event base SHA as diff comparison. The aggregate
uses the workflow SHA so manual tests of old targets still have its helper.

## Review priorities

1. Correctness: verify failure/cancellation/skipped propagation and output
   validation; actual v3 picomatch/every semantics; unknown inputs, renames,
   deletions and website dependencies; GitHub changed-file API bounds (large
   PRs must not silently escape the route); exact refs/history and annotation
   coordinates; actual pinned diff-cover JSON and path handling; malformed or
   missing reports versus legitimate not-applicable diffs; workflow-command
   escaping, annotation/summary limits; fork/merge-group/manual behavior.
2. Clarity: make the changed code and instructions easy to follow, without
   speculative frameworks or unrelated refactors.
3. Coverage: independent failure cases, useful boundary tests, real tool
   behavior. Fifty-six focused tests already pass, including a temporary Git
   repository with actual coverage and diff-cover below 85%, returning success.
   Add tests only for a specific gap. Check the tests do not merely mirror code.

The hosted run of PR #312 and local full gate are initially in progress. The
implementor will inspect hosted logs and handle any observed hosting failure.
Please flag conflicts before broadening your work. Native Files changed
placement needs actual hosted evidence; a local command does not establish it.
No required CI checks currently exist: read-only API inspection found only
ruleset 25144717's default-branch deletion/force-push prohibitions, and classic
branch protection returns 404 for main and release-0.3.0. Adding required
ci-gate is an owner settings step after successful hosted acceptance. Do not
change settings or claim the acceptance step done.

## Environment and validation

Your own devcapsule-src/.venv is installed from this branch's locked file.
Use `/var/tmp/maintenance-ci-review` for scratch because /opt/devcapsule-gate
is unavailable. Initialize only the pinned website submodule for docs checks;
never change its gitlink. No images, capsules, GUI launches or services.

From your worktree:

    git submodule update --init website
    cd devcapsule-src
    .venv/bin/python -m pytest --no-cov -q tests/test_ci_reporting.py --basetemp=/var/tmp/maintenance-ci-review/focused
    .venv/bin/python -m mypy scripts/ci_gate.py scripts/diff_coverage_annotations.py tests/test_ci_reporting.py
    PYTEST_ADDOPTS="--basetemp=/var/tmp/maintenance-ci-review/gate" .venv/bin/python -m nox -s build

Run the gate synchronously in the foreground, not a background Bash tool task:
Claude print mode kills unfinished background tools when the turn exits.
Report counts and limitations. Do not rerun broad tests after success unless
a change or unresolved concern warrants it. Do not fix unrelated failures.

## GitHub and authorship

In every shell using gh:

    source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Use the installed gh login; no API key. Check auth once in your session and
stop on an auth/network blocker. Read the PR with `gh pr diff 312` in
`ccozianu/devcapsule`. Keep human author Costin Cozianu <ccozianu@gmail.com>.
Credit only your contribution with:

    Co-authored-by: Claude Fable 5.1 Claude Code <noreply@anthropic.com>

## Forbidden actions

Do not edit status files, intake, intake-dispositions, evidence or published
state. Do not edit another checkout. Do not merge, rebase or force-push, push
main/release or the implementor branch, change settings, dispatch deployment,
build images or launch capsules. Do not commit .idea, venvs, generated artifacts
or website gitlink changes. Do not start other agents. Stop on a real blocker
and report it; do not substitute an engine or credential.

## Delivery

Commit focused fixes on your review branch, push it via ordinary SSH Git,
and open one PR with a body file:

    gh pr create --repo ccozianu/devcapsule --base ws-maintenance/ci-gating-030 --head ws-maintenance/ci-gating-030-review --title "Correctness, clarity and coverage review of #312 (PR312.1)" --body-file <file>

List each changed finding with problem, location, fix and evidence. Then list
what you considered and left alone, unimplemented proposals, and validation
counts/limits. If you change nothing, report that and open no empty PR.
The implementor reads your diff, assesses it, and may merge your review PR;
the human alone merges PR #312. At most three rounds.

Print the review PR URL as your final line, or NO PR if none, or BLOCKED with
the exact cause if you cannot proceed. The detached launcher records your exit.

## Pre-launch evidence update

The implementor's full gate passed: 2,630 unit tests (40 deselected, one
xfail and one XPASS), 18 packaging tests, 357 web-console tests and 192 docs
pages including aliases. The new hosted website job found a real inherited
broken anchor: three pages link to `#when-the-project-changes`, renamed by
the earlier CLI documentation slice to "Changes at the next launch". The
implementor restored the stable HTML anchor on that existing section in
`docs/configuration/project-versus-personal.md`, preserving external links
without changing prose. Review this narrow fix too. The updated branch is
fast-forwarded into your checkout before launch. Its hosted rerun will verify
the full site; the local gate checks the content contract, not rendered anchors.

The failing hosted job is 123840779587, run 40987146695. No other new hosted
failure is known yet. The implementor will monitor it while you review.
