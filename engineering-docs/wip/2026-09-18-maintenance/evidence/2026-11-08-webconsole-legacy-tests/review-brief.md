# Review brief for the Claude Code + Claude Fable 5.1 pair: PR18.1 on whole-file legacy test retirement and 4-file refurbishment

The Antigravity + Gemini 4 Argon (High) pair opened PR #18 ("Retire and refurbish legacy build_info, console, and materialization unit tests") on branch `ws-maintenance/webconsole-legacy-tests` targeting `release-0.3.1`. No earlier review PRs exist on this slice (PR #18 is the prerequisite base slice of a two-PR stack; once PR #18 settles, PR #16's launcher-delivered web console implementation, previously reviewed by your pair in merged PR #17, will be rebased onto `ws-maintenance/webconsole-legacy-tests` without leaving legacy/mirror test twins in the tree). Your job is one improvement pull request (`PR18.1`) against `ws-maintenance/webconsole-legacy-tests`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/maintenance-review`, on the branch `ws-maintenance/webconsole-legacy-tests-review`, branched from `ws-maintenance/webconsole-legacy-tests`. Work only there. Do not touch the implementor's checkouts at `/home/devcapsule/worktrees/maintenance-legacy-tests` or `/workspace/301e4208ef81-ChatGPT_Codex`.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md` (especially *Unit Tests* rules 1 to 7 and *Pair Review Loop In This Checkout*), `WORKFLOW-LOCAL-humane.md` (*Unit Tests* Rule and Motivation), `engineering-docs/development/unit-tests.md`, `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md` (the section `## Whole-file legacy test retirement and 4-file refurbishment for 0.3.1, by Pair Review — 2026-11-08`), and `devcapsule-src/scripts/validate_unittests_follow_conventions.py`.

## GitHub CLI

In every shell you run that uses `gh`, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against `mycodespace-ai/devcapsule` (pass `-R mycodespace-ai/devcapsule` when no default repository is set in the worktree). Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv`, `.nox/` environments, and `website` submodule are initialized. Run unit tests, integration tests, and mypy from `devcapsule-src` with:

- `DEVCAPSULE_DIFF_BASE=origin/release-0.3.1` (so `scripts/validate_unittests_follow_conventions.py` compares legacy test files against `release-0.3.1`, PR #18's base)
- Default `/tmp` scratch (`tmpfs`, ~1.6 GB free; the unit suite uses ~215 MB). Do **not** use `/opt/devcapsule-gate` (it does not exist in this capsule), do **not** place `--basetemp` under `/home/devcapsule` (it is a Docker mount inside this capsule and breaks `test_unmountable_staging_fails_loudly`), and do **not** pass `--cov` flags in `PYTEST_ADDOPTS` when running `nox` (`nox -s webconsole` does not install `pytest-cov`).

**Important `claude -p` execution note:** Run every Bash command synchronously in the foreground (never pass `run_in_background: true`, because single-turn `-p` mode terminates background child processes when a tool wait ends; pass a sufficient foreground timeout for `nox -s build` and `nox -s integration`).

This PR touches:

- Workflow rules, developer guide, and unit-test convention gate:
  - `WORKFLOW-LOCAL.md`
  - `WORKFLOW-LOCAL-humane.md`
  - `engineering-docs/development/unit-tests.md`
  - `devcapsule-src/scripts/validate_unittests_follow_conventions.py`
  - `devcapsule-src/tests/unit/scripts/test_validate_unittests_follow_conventions.py`
- Production public-surface declarations (`__all__`) and collaborator seams:
  - `devcapsule-src/devcapsule/build_info.py`
  - `devcapsule-src/devcapsule/commands/version.py`
  - `devcapsule-src/devcapsule/container_runtime/contract.py`
  - `devcapsule-src/devcapsule/container_runtime/console.py` (also drops dead `_monitor_dependency_available()` per owner decision `psutil-probe-in-pr1 = drop-in-pr1`)
  - `devcapsule-src/devcapsule/container_runtime/entrypoint.py`
  - `devcapsule-src/devcapsule/console_tools.py`
  - `devcapsule-src/devcapsule/commands/project.py` (`CheckoutDecisionsCommand`)
  - `devcapsule-src/devcapsule/materialization.py`
- Retired legacy test files (deleted whole):
  - `devcapsule-src/tests/test_build_info.py` (deleted)
  - `devcapsule-src/tests/test_console_runtime.py` (deleted)
  - `devcapsule-src/tests/test_console_tools.py` (deleted)
  - `devcapsule-src/tests/test_materialization.py` (deleted)
- Refurbished unit mirror files and CLI integration file:
  - `devcapsule-src/tests/unit/devcapsule/test_build_info.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/commands/test_version.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/container_runtime/__init__.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/container_runtime/test_contract.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/container_runtime/test_console.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/container_runtime/test_entrypoint.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/test_console_tools.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/test_materialization.py` (new)
  - `devcapsule-src/tests/integration/test_console_decisions_cli.py` (new, `pytest.mark.integration`)
- Status record:
  - `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md`

The gate type-checks `tests/` too. Run `DEVCAPSULE_DIFF_BASE=origin/release-0.3.1 .venv/bin/python -m nox -s build integration` before your final push and report its result with exact counts.

Do not build Docker images (`images build`) or launch capsules (`project run`). The implementor reruns the full gate on the merged branch and records the evidence in `CURRENT-STATUS.md`.

## The task

Review the diff of PR #18 against its base:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh && gh pr diff 18 -R mycodespace-ai/devcapsule

Inside the diff, read first: `WORKFLOW-LOCAL.md`, `WORKFLOW-LOCAL-humane.md`, `engineering-docs/development/unit-tests.md`, and `devcapsule-src/scripts/validate_unittests_follow_conventions.py` (+ its unit tests), then the production modules (`build_info.py`, `commands/version.py`, `container_runtime/{contract,console,entrypoint}.py`, `console_tools.py`, `commands/project.py`, `materialization.py`), and finally compare each deleted legacy test file against the refactored unit mirror files and `tests/integration/test_console_decisions_cli.py`.

Improve it on your branch, focused on these four things, in this order:

1. **Correctness of the new and modified lines:**
   - **Whole-file legacy retirement rule and gate (`validate_unittests_follow_conventions.py`):**
     - Does the checker reject *any* addition, deletion, or modification of a `test_*` function (including class-nested `test_*` methods or decorator changes) inside a `legacy` file unless the whole legacy file is deleted?
     - Does the mirror-twin check reject adding or modifying a `test_*` function in `tests/unit/<path>/test_<name>.py` whenever a flat legacy unit file `tests/test_<name>.py` still exists in `tests/`, while avoiding false positives against nested heavier/boundary suites such as `tests/configuration/test_contract.py` or `tests/e2e/*`? What if two different packages had `tests/unit/devcapsule/foo/test_bar.py` and `tests/test_bar.py` — is basename matching intentional and accurately stated in rule 5 and the checker diagnostics, or are there edge cases (e.g., deleting a `test_*` function from a mirror file while `tests/test_<name>.py` still exists, or moving a legacy file without removing `pytest.mark.legacy`)?
     - Does `WORKFLOW-LOCAL.md` rule 5, `WORKFLOW-LOCAL-humane.md`, and `engineering-docs/development/unit-tests.md` agree word-for-fact with what `validate_unittests_follow_conventions.py` enforces?
   - **Production seams, `__all__`, and behavior preservation:**
     - Check every `__all__` list added in `build_info.py`, `commands/version.py`, `container_runtime/contract.py`, `container_runtime/console.py`, `container_runtime/entrypoint.py`, `console_tools.py`, and `materialization.py`: is every public symbol imported across `devcapsule/` and `tests/` included, and are private helpers kept out?
     - Check every new keyword-only collaborator/input parameter (`current_build_info`, `VersionCommand.invoke`, `console_child`, `entrypoint.run`, `run_console_decisions`, `CheckoutDecisionsCommand.invoke`): do default values preserve production runtime behavior identically when omitted? Are there mutable defaults, resource leaks (e.g., socket cleanup in `console_child` when `connect` or `popen` raises), or altered error messages/exit codes?
     - Check the removal of `_monitor_dependency_available()` in `container_runtime/console.py` (authorized by owner decision `psutil-probe-in-pr1 = drop-in-pr1`): are any stale references, unused imports, or misleading comments left behind?
2. **Clarity of the new and modified lines.** The standard is "obviously no deficiencies". Check helper naming, fixture clarity in the refactored test modules, and checker error messages.
3. **Test coverage and behavioral parity with the 4 retired legacy files:**
   - Audit every test deleted from `tests/test_build_info.py`, `tests/test_console_runtime.py`, `tests/test_console_tools.py`, and `tests/test_materialization.py` against the new mirror files (`test_build_info.py`, `commands/test_version.py`, `container_runtime/test_contract.py`, `container_runtime/test_console.py`, `container_runtime/test_entrypoint.py`, `test_console_tools.py`, `test_materialization.py`) and `tests/integration/test_console_decisions_cli.py`. Was any distinct contract, edge case, or refusal silently dropped during refurbishment?
   - Add tests where a branch in `validate_unittests_follow_conventions.py`, the touched production seams, or the refactored modules is not exercised. Every test must fail if the line it covers is broken. Do not pad.
4. **Every new or changed test against *Unit Tests* in `WORKFLOW-LOCAL.md` (rules 1 to 5, and rule 7 duty):**
   - Lives in `tests/unit/<path>/test_<name>.py` mirroring its unit and names its unit (`tests/integration/test_console_decisions_cli.py` is marked `pytest.mark.integration` because its purpose is real subprocess execution of `devcapsule_webconsole.decisions_cli`).
   - Establishes its own precondition from constructed inputs (`tmp_path`, parameters, in-memory fakes), calls one public operation, and asserts a promised postcondition.
   - Carries a docstring stating the contract.
   - Uses **zero** `monkeypatch.setattr` / `unittest.mock.patch` on `devcapsule.*` attributes, imports **zero** private `_` symbols from `devcapsule.*`, and spawns **zero** external subprocesses in unit tests unless spawning that program is the unit's contract with test-controlled inputs.
   - Per *Unit Tests* rule 7, for every new or changed unit test in the slice (group concisely where tests in a module share the identical isolation pattern, while calling out any distinct failure modes individually), name in your PR body what would make it fail for a reason that is not a bug. A finding here is a finding; "confined to tests" does not dismiss it.

Stay inside the PR's scope: tightening *Unit Tests* rule 5 + `validate_unittests_follow_conventions.py` for whole-file legacy retirement and refurbishing the 4 legacy test files (`test_build_info.py`, `test_console_runtime.py`, `test_console_tools.py`, `test_materialization.py`). Do **not** retire other legacy test files outside these four, and do **not** implement `D-0017` web-console bundle delivery here (that lands in the stacked PR #16 immediately on top of PR #18). If you spot a broader follow-up outside scope, record it under "Proposals not implemented".

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, the `evidence/` directory, or run `devcapsule workflow publish` / `devcapsule0 workflow publish`.
- Do not commit the `website` submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/` or `__pycache__`.
- Do not merge anything. Do not push to `main`, `release-0.3.1`, or any branch other than `ws-maintenance/webconsole-legacy-tests-review`.
- Do not rebase or force-push. Do not build Docker images or run capsules.

## Deliverable

1. Commits on `ws-maintenance/webconsole-legacy-tests-review`, preserving the human's Git author identity (`Costin Cozianu <ccozianu@gmail.com>`) and naming the component and the evidence in each commit message, ending after a blank line with:
   `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
2. Push the branch (`git push -u origin ws-maintenance/webconsole-legacy-tests-review`) and open one pull request with:
   `gh pr create -R mycodespace-ai/devcapsule --base ws-maintenance/webconsole-legacy-tests --head ws-maintenance/webconsole-legacy-tests-review`
   Title: `Correctness, clarity and coverage review of #18 (PR18.1)`
   The body lists:
   - Each finding as: what was wrong or unclear, where, what you changed, and how the test proves it.
   - Per *Unit Tests* rule 7, for the new/changed unit tests in the slice, what would make each fail for a reason that is not a bug.
   - "Considered and left alone, because".
   - "Proposals not implemented".
   - The gate result (`nox -s build integration`) with exact counts and what was skipped.
   If you find nothing to change, say so in the PR body and open the PR with the added tests only, or, if there are none, say that in your final report instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or `NO PR` if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about twenty words, active voice. Every claim about behavior must be backed by a test or a command you ran.

If you cannot proceed because of a blocker like network or credentials, stop and say exactly what blocked you. Do not work around a blocker.
