# Review brief for the Claude Code + Claude Fable 5.1 pair: PR16.1 on launcher-delivered web console (`D-0017`)

The Antigravity + Gemini 4 Argon (High) pair opened PR #16 ("Deliver devcapsule_webconsole with the launcher PEX (D-0017)") on branch `ws-maintenance/webconsole-delivery` targeting `release-0.3.1`. No earlier review PRs exist on this slice (earlier today PR #12 / PR #13 delivered the Files page itself on `release-0.3.1`, and `v0.3.1-rc1` validation exposed that `devcapsule.pex` omitted `devcapsule-webconsole/` while `console_development_source()` shadowed built candidates on DevCapsule checkouts). Your job is one improvement pull request (`PR16.1`) against `ws-maintenance/webconsole-delivery`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/maintenance-review`, on the branch `ws-maintenance/webconsole-delivery-review`, branched from `ws-maintenance/webconsole-delivery`. Work only there. Do not touch the implementor's checkout at `/workspace/301e4208ef81-ChatGPT_Codex`.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`, `engineering-docs/decisions/product/d-0017-launcher-delivers-web-console-package.md`, `engineering-docs/requirements/product/r-console-001-capsule-web-console.md`, `engineering-docs/bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md`, `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md` (the section `## Blocking 0.3.1rc1 finding and D-0017 fix: launcher-delivered web console — 2026-11-08`), and `devcapsule-src/devcapsule/webconsole_bundle.py`.

## GitHub CLI

In every shell you run that uses `gh`, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against `mycodespace-ai/devcapsule` (pass `-R mycodespace-ai/devcapsule` if no default repo is set in the worktree). Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists and the `website` submodule is initialized. Run unit tests and mypy from `devcapsule-src` with:

- `DEVCAPSULE_DIFF_BASE=origin/release-0.3.1` (so `scripts/validate_unittests_follow_conventions.py` compares legacy test files against `release-0.3.1`, the PR's base)
- `PYTEST_ADDOPTS="--basetemp=/tmp/devcapsule-gate/pytest-claude"` when running `devcapsule-src` unit tests (do not place pytest basetemp under `/home/devcapsule`, which is a Docker mount inside this capsule and breaks `test_unmountable_staging_fails_loudly`; note also that `nox -s webconsole` does not accept pytest-cov flags, only `--basetemp`, or omit `PYTEST_ADDOPTS` when running `nox -s build` since `/tmp` is already `tmpfs` with 1.6 GB free and the unit suite uses ~215 MB)

**Important `claude -p` execution note:** Run every Bash command synchronously in the foreground (never pass `run_in_background: true`, because single-turn `-p` mode terminates background child processes when a tool wait ends; use a sufficient foreground timeout for `nox -s build` and `nox -s integration`).

This PR touches:

- Packaging and build identity:
  - `devcapsule-src/devcapsule/webconsole_bundle.py` (new)
  - `devcapsule-src/devcapsule/build_info.py`
  - `devcapsule-src/pyproject.toml`
  - `devcapsule-src/scripts/build-pex.sh`
- Materialization and in-capsule console execution:
  - `devcapsule-src/devcapsule/materialization.py`
  - `devcapsule-src/devcapsule/container_runtime/console.py`
  - `devcapsule-src/devcapsule/console_tools.py`
- Host launch and self-hosting override:
  - `devcapsule-src/devcapsule/launch/pycharm/_launcher.py`
- Documentation and records:
  - `devcapsule-src/README.md`, `devcapsule-webconsole/README.md`
  - `engineering-docs/decisions/product/d-0017-launcher-delivers-web-console-package.md` (new)
  - `engineering-docs/requirements/product/r-console-001-capsule-web-console.md`
  - `engineering-docs/bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md` (new)
  - `engineering-docs/releases/v0.3.1/{README.md,bugs.md,changelog.md}`, `index.md`
- Tests:
  - `devcapsule-src/tests/conftest.py`
  - `devcapsule-src/tests/unit/devcapsule/test_webconsole_bundle.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/test_build_info.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/test_materialization.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/container_runtime/__init__.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/container_runtime/test_console.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/test_console_tools.py` (new)
  - `devcapsule-src/tests/unit/devcapsule/launch/pycharm/test_launcher.py`
  - `devcapsule-src/tests/test_pycharm.py`, `devcapsule-src/tests/test_version_sets.py`
  - `devcapsule-src/tests/integration/test_build_pex.py`

The gate type-checks `tests/` too. Run `DEVCAPSULE_DIFF_BASE=origin/release-0.3.1 .venv/bin/python -m nox -s build` and `DEVCAPSULE_DIFF_BASE=origin/release-0.3.1 .venv/bin/python -m nox -s integration` before your final push and report their results with exact counts.

Do not build Docker images (`images build`) or launch capsules (`project run`). The implementor reruns the full gate and any live interpreter checks on the merged branch and records the evidence in `CURRENT-STATUS.md`.

## The task

Review the diff of PR #16 against its base:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh && gh pr diff 16 -R mycodespace-ai/devcapsule

Inside the diff, read first: `d-0017-launcher-delivers-web-console-package.md` and `r-console-001-capsule-web-console.md`, then `webconsole_bundle.py`, `build-pex.sh`, `materialization.py`, `container_runtime/console.py`, `console_tools.py`, `build_info.py`, and `launch/pycharm/_launcher.py`, then all new and modified tests.

Improve it on your branch, focused on these four things, in this order:

1. **Correctness of the new and modified lines:**
   - **Bundle creation and extraction (`webconsole_bundle.py`, `build-pex.sh`):** Does `build_webconsole_bundle` refuse symlinks (or dereference them across boundaries), non-regular files, or empty/missing package roots cleanly? Does `extract_webconsole_bundle` reject every archive escape (`..`, absolute paths, drive/backslash forms, zip symlink external attributes `S_IFLNK`, duplicate normalized paths, directory/file collisions, unexpectedly large or malformed nested zips)? Does `_read_bundle_bytes_from_pex` match `read_pex_build_info`'s layout rules across scie-wrapped PEXes, plain PEXes, and multi-wheel `.deps/` entries without accepting an unrelated wheel's file? Does `build-pex.sh` guard every file in `devcapsule-webconsole/` that could affect the bundle or expectations (and clean up any temporary artifact)?
   - **Materialization and formation identity (`materialization.py`):** Is `/opt/devcapsule/webconsole` installed with deterministic read-only permissions for non-root capsule users (`Identity(uid, gid)`), and is every byte of the bundle bound to `formation_identity` through `runtime.pex-sha256`? Are `runtime_enforcement_spec` or cached-formation reuse paths affected if an existing formation image already carries the same `runtime.pex-sha256`?Wait: `runtime.pex-sha256` changes whenever `_webconsole_bundle.zip` changes, AND what if an older formation was materialized before this change from an old PEX? Its `pex-sha256` differs from any new PEX! Check whether `MATERIALIZATION_RECIPE_VERSION` also needs to bump or stays as-is when `surface_materialization_spec` adds `DirectoryComponent(webconsole_root, "/opt/devcapsule/webconsole")` for the same theoretical `runtime_pex`!
   - **In-capsule runtime precedence and compatibility (`container_runtime/console.py`, `console_tools.py`, `D-0017`, `R-CONSOLE-001`):** Examine the `psutil` compatibility probe (`_monitor_dependency_available` / `_python_has_monitor_dependency`) that was copied onto the `/opt/devcapsule/webconsole` branch and into `console_tools.py`. Check git history: both recipe 10 (`7659c6d8`) and recipe 11 (`9ac19b86`) shipped together in `v0.3.0-rc0` — no release ever locked a recipe-10 base, and probing `import psutil` is a hardcoded pre-`0.3.0` one-off that would not catch a future dependency in recipe 12+ anyway, while adding a subprocess spawn on every console start and every `decisions` CLI invocation! Decide whether the launcher-package branch should drop that one-off `psutil` subprocess probe (or whether `D-0017` / `R-CONSOLE-001` prose should be tightened to match), or how compatibility is cleanest and most truthful. Also check `PYTHONPATH` handling if `PYTHONPATH` was already set in the environment (does `PYTHONPATH=/opt/devcapsule/webconsole` cleanly replace ambient `PYTHONPATH` as intended?).
   - **Self-hosting override (`build_info.py`, `launch/pycharm/_launcher.py`):** Does `is_built_distribution()` behave identically across PEX, scie-PEX, editable `.venv`, and non-editable installs? How does `console_development_source()` handle `DEVCAPSULE_DEV_WEBCONSOLE` values (whitespace, case, invalid values like `"yes"` or `"2"` — should unrecognized non-empty values warn/refuse or be documented clearly; what if `DEVCAPSULE_DEV_WEBCONSOLE=1` is set on a non-DevCapsule project that has no `devcapsule-webconsole/` directory)?
2. **Clarity of the new and modified lines.** The standard is "obviously no deficiencies". Remove dead complexity, redundant parameters, or duplicated logic between `console.py` and `console_tools.py`.
3. **Test coverage of the new and modified lines.** Add tests where a branch or refusal is not exercised. Every test must fail if the line it covers is broken. Do not pad.
4. **Every new or changed test against *Unit Tests* in `WORKFLOW-LOCAL.md` (rules 1 to 5):**
   - It lives in `tests/unit/<path>/test_<name>.py` mirroring its unit and names its unit (whose public surface is declared via `__all__` or module docstring, rule 4!). Check whether every unit tested by a new mirror test file declares `__all__` or names its public operations in its module docstring!
   - It is a Hoare triple: establishes its own precondition, performs one action on one public operation, and asserts a promised postcondition.
   - **Crucially (rule 2 isolation):** *"A unit test starts another program only when running that program is the unit's contract, and then with inputs the test controls. A test computes in its own process what it can compute there."* Inspect `tests/unit/devcapsule/container_runtime/test_console.py` and `tests/unit/devcapsule/test_console_tools.py` (which currently write `#!/bin/sh` stubs that spawn `/bin/sh` via `subprocess.run`!) as well as all other new/changed unit tests (`test_webconsole_bundle.py`, `test_build_info.py`, `test_materialization.py`, `test_launcher.py`). Fix any rule 1–4 violation!
   - For every new or changed test, name in your PR body what would make it fail for a reason that is not a bug. A finding here is a finding; "confined to tests" does not dismiss it.

Stay inside the PR's scope: delivering `devcapsule_webconsole` inside the launcher PEX (`D-0017`) and scoping the self-hosting `console_development_source` override. Do not change `devcapsule-webconsole`'s FastAPI application code, base-image recipes, or unrelated CLI commands. Do not widen `D-0017` beyond minor factual alignment of the implementation details if needed; if you believe a product choice is wrong, say why in the PR body under "Proposals not implemented" and keep your change minimal.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, the `evidence/` directory, or run `devcapsule workflow publish` / `devcapsule0 workflow publish`.
- Do not commit the `website` submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/` or `__pycache__`.
- Do not merge anything. Do not push to `main`, `release-0.3.1`, or any branch other than `ws-maintenance/webconsole-delivery-review`.
- Do not rebase or force-push. Do not build Docker images or run capsules.

## Deliverable

1. Commits on `ws-maintenance/webconsole-delivery-review`, preserving the human's Git author identity (`Costin Cozianu <ccozianu@gmail.com>`) and naming the component and the evidence in each commit message, ending after a blank line with:
   `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
2. Push the branch (`git push -u origin ws-maintenance/webconsole-delivery-review`) and open one pull request with:
   `gh pr create -R mycodespace-ai/devcapsule --base ws-maintenance/webconsole-delivery --head ws-maintenance/webconsole-delivery-review`
   Title: `Correctness, clarity and coverage review of #16 (PR16.1)`
   The body lists:
   - Each finding as: what was wrong or unclear, where, what you changed, and how the test proves it.
   - Per *Unit Tests* rule 7, for every new or changed unit test in the slice, what would make it fail for a reason that is not a bug.
   - "Considered and left alone, because".
   - "Proposals not implemented".
   - The gate result (`nox -s build` and `nox -s integration`) with exact counts and what was skipped.
   If you find nothing to change, say so in the PR body and open the PR with the added tests only, or, if there are none, say that in your final report instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or `NO PR` if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about twenty words, active voice. Every claim about behavior must be backed by a test or a command you ran.

If you cannot proceed because of a blocker like network or credentials, stop and say exactly what blocked you. Do not work around a blocker.
