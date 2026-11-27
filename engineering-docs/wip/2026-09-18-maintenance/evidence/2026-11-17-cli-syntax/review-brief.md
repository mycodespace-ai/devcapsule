# Pair Review brief: Antigravity + gemini-4-hydrogen, PR52.1

Codex (GPT-6) opened https://github.com/mycodespace-ai/devcapsule/pull/52,
`ws-maintenance/cli-syntax` into `release-0.3.1`. Review the independent first
slice: safe `pycharm check-runtime --help` and complete recording-kit installation
at workflow/wrapper setup. The full CLI work order is NOT implemented yet.
The owner selected you in place of Claude. Your exact launch model is
`gemini-4-hydrogen`; report the actual model in your report and attribution.

## Your checkout and reading order

Work only in `/home/devcapsule/worktrees/maintenance-review`, branch
`ws-maintenance/cli-syntax-review`, based on the implementation branch.
Do not touch `/workspace/301e4208ef81-ChatGPT_Codex`.
Your `.venv` is installed in your checkout's `devcapsule-src`.
The brief is your only conversation context.

Read first: `README.md`, `DEVELOPING.md`, `AGENTS.md`, the glossary and Pair Review
rules in `WORKFLOW.md`, `WORKFLOW-LOCAL.md`, the work order
`engineering-docs/work-orders/2026-11-17-cli-syntax-and-discovery.md`, and the
current CLI sections at the TOP of maintenance's status file (the thousands of
historical lines below them are not needed for this slice). Then read
`engineering-docs/wip/2026-09-18-maintenance/2026-11-17-cli-syntax-implementation.md`.

Inspect the real PR diff and implementation; do not rely on its description:

    git diff upstream/release-0.3.1...ws-maintenance/cli-syntax

Production changes are in `devcapsule-src/devcapsule/commands/_pycharm.py`,
`commands/project.py`, `presentation_authoring.py`, and `workflow_bootstrap.py`.
Tests changed in `tests/unit/devcapsule/test_presentation_authoring.py`; the new
subprocess tests are `tests/integration/test_cli_syntax.py`.

## Scope and decisions

- `--help` must not execute the dependency-check script, even outside a project.
- Fresh workflow and wrapper setup must install SKILL.md, the complete helper
  directory, and version provenance in both existing agent discovery locations.
- Existing directories, customized contents and symlinked skill locations remain
  untouched. No automatic upgrade/overwrite is authorized.
- This is the owner's explicit bounded recording-resource installation grant.
  Preserve all other storage, behavior, defaults, consent and host access rules.
- The existing standalone presentations commands still exist in THIS slice.
  Do not remove them or implement the new instance link command here.
- Grammar choices are still pending: --project placement, global/instance verb
  shape, and automatic viewer routing for file paths. Do not decide them.
- The complete work order's command migration, instruction migration, PyCharm
  reachability deletion and broad advanced-help changes remain later work.
  Correct directly misleading documentation about THIS slice if needed, keeping
  current commands usable; do not claim the whole work order is complete.

## Review obligations

In this order: correctness, clarity, and meaningful coverage of changed lines.
Check missing/unsafe resource names, fresh and customized installations,
symlink parents and destinations, incomplete writes, version provenance, wrapper
and bootstrap callers, help dispatch, and diagnostics remaining callable.
Preserve shared helpers with remaining callers.

Verify every new/changed test against WORKFLOW-LOCAL Unit Tests rules 1–4:
correct module mirror, self-contained precondition, one public operation and
promised postcondition, contract docstring. For each changed/new test, name what
could make it fail for a reason other than a bug. No new monkeypatch/mock use.
Legacy files cannot be edited without whole-file retirement under that rule.
Verify Host Inputs rules 1–6: host reads at entry layers, explicit values below,
no test-only parameters or host-reading defaults, dataclasses only store, no
hidden policy in entry layers. Existing unrelated debt is not this PR's scope.
State what hosted validation does not prove. Do not widen merely to improve debt.

## Validation commands

Run from your worktree's `devcapsule-src`:

    DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS="--basetemp=/home/devcapsule/skill-validation/pytest-antigravity" .venv/bin/python -m pytest -q --no-cov tests/unit/devcapsule/test_presentation_authoring.py
    DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS="--basetemp=/home/devcapsule/skill-validation/pytest-antigravity" .venv/bin/python -m pytest -q --no-cov -m integration tests/integration/test_cli_syntax.py
    DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS="--basetemp=/home/devcapsule/skill-validation/pytest-antigravity" .venv/bin/python -m nox -s build

Use your own environment and scratch. `/opt` is read-only; the alternative scratch
above follows Validation Commands' allowance for another directory with room.
Do not share the implementor's coverage files, environment or pytest scratch.
Run tests serially. Logs belong under `/home/devcapsule/skill-validation/` with
an `antigravity-cli-` prefix, never in Git. The initial focused counts are 29
unit and 3 integration passes. The implementor's full build passed version,
syntax, types (361 files) and conventions, then stopped with 3374 passing unit
tests and three known environment-dependent failures: two gid-0 fixtures in
`tests/test_recursive_orchestrator.py` and the unmountable-staging fixture in
`tests/test_host_daemon.py` (home scratch is mount-backed). No waiver or new test
exclusion is authorized; report these distinctly from regressions. Hosted tests
on the release baseline have passed; these local failures do not imply hosted
failure. If the full gate stops there, report unexecuted later stages honestly.
No image builds, capsule launches, release tags, full recordings or browser
installations are authorized. Do not provision new services.

## GitHub, authorship and delivery

Activate GitHub CLI in EVERY shell call using it:

    source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Check `gh auth status -h github.com` once before your first GitHub use. If it
fails, stop; do not retry or use another credential. Repository is
`mycodespace-ai/devcapsule`; Git fetch/push use SSH remote `upstream`.
Use explicit `--repo mycodespace-ai/devcapsule` on gh operations.
Read PR52 with `gh pr diff 52 --repo mycodespace-ai/devcapsule`.

Before committing, verify `git var GIT_AUTHOR_IDENT`: preserve Costin Cozianu
<ccozianu@gmail.com>. Credit your actual model, e.g.
`Co-authored-by: Gemini 4 Hydrogen Antigravity <noreply@google.com>`.
Commit only your changes on `ws-maintenance/cli-syntax-review`, run the required
checks, and push with `git push upstream HEAD`. Create PR52.1 against the
IMPLEMENTATION branch, never the release:

    gh pr create --repo mycodespace-ai/devcapsule --base ws-maintenance/cli-syntax --head ws-maintenance/cli-syntax-review --title "Correctness, clarity and coverage review of #52 (PR52.1)" --body-file <temporary-body-file>

For each finding, state what was wrong/unclear, where, what changed and which test
proves it. Separate considered-and-left-alone items with reasons and proposals
not implemented. Report validation counts and limits. If there are no changes,
open no empty PR: report your inspection, evidence and verdict.

## Forbidden actions and final report

Do not edit status files, workstream lists, intake/disposition logs, evidence
briefs, the work order, or the implementation planning document. Do not run
workflow claim/mail/publish. The implementor owns those records.
Do not merge, rebase, force-push, switch workstreams or touch another checkout.
Do not change `.devcapsule/`, `.idea/`, the website gitlink or release refs.
Do not commit generated environments, caches, dist files or logs.
Do not spawn subagents. Stop and report real blockers; do not work around them.

Print a concise final assessment with findings, what you changed, what remains,
tests and actual model. The FINAL LINE must be your review PR URL, or `NO PR`
when there are no changes. The implementor will assess your diff, handle up to
three rounds, merge the review PR when accepted, and rerun the full gate.
Only the human merges PR52 into the release.
