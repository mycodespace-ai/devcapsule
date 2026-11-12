# Review brief for the Codex + gpt-6-astra pair: PR1.1 on the sources declaration and project wrap

The Claude Code + Fable 5.1 pair opened PR1, #333, "Wrapped projects, slice 1: the sources
declaration and project wrap (PR1)", branch `ws-wrapped-projects/wrap`, base `main`. It is
the first slice of the wrapped-projects workstream; no earlier review of this series exists.
Your job is one improvement pull request against that branch.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/wrapped-projects-review`, on the
branch `ws-wrapped-projects/wrap-review`, branched from `ws-wrapped-projects/wrap`. Work only
there. Do not touch the main checkout at `/workspace/301e4208ef81-ChatGPT_Codex`.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`,
`engineering-docs/work-orders/2026-11-02-wrapped-projects.md`,
`engineering-docs/wip/2026-11-02-wrapped-projects/CURRENT-STATUS.md` (the section
*Slice 1, judgments*), `engineering-docs/wip/2026-11-02-wrapped-projects/2026-11-02-design-wrapped-source.md`,
then the module docstrings of `devcapsule-src/devcapsule/configuration/sources.py` and
`devcapsule-src/devcapsule/wrap.py`, which are the contract.

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against `ccozianu/devcapsule`.
Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists. Run unit tests and mypy from `devcapsule-src`
with `PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-codex -p no:cacheprovider"`.
This PR touches, under `devcapsule-src/devcapsule/`: `configuration/sources.py` (new),
`configuration/manifest_schemas.py`, `configuration/manifest_document.py`,
`configuration/owner_commands.py`, `configuration/listing.py`, `wrap.py` (new),
`wrap_detection.py` (new), `commands/project.py`; under `devcapsule-src/tests/`:
`test_sources.py` (new), `test_wrap.py` (new), `test_wrap_detection.py` (new),
`test_owner_commands.py`; and documentation under `docs/`, `engineering-docs/requirements/`,
`REQUIREMENTS.md`, `index.md`. The gate type-checks `tests/` too. Run `nox -s build` before
your final push and report its result.

Three tests in `tests/test_capability_commands_v2.py`,
`test_resolution_grants_no_consent_and_no_partial_save[project|checkout|run]`, fail in this
capsule with the PR's changes stashed as well as with them applied; they are not this PR's.
Report them as pre-existing if you see them; do not fix them here.

Do not build images, start capsules, or run the console smoke; the implementor runs the
acceptance inside a capsule in slice 2, and the evidence lands in the workstream's
status file.

## The task

Review the diff of PR 333 against its base:

    gh pr diff 333

Read first inside the diff: the docstring of `sources.py` (what the table means), the
docstring of `wrap.py` (the five steps and the rerun rule), then `wrap_detection.py` (facts as
data), then the command in `commands/project.py`.

Improve it on your branch, focused on exactly three things, in this order:

1. Correctness of the new and modified lines. Ask:
   - Does `source_path` refuse every path that escapes the wrapper or is not in normal POSIX
     form, and admit nested paths? Can a key reach the writer unquoted when it must be quoted?
   - Does `ManifestV2.document()` round-trip an explicitly empty `[sources]` and a table with
     unknown keys inside an entry? Does a schema-1 file with `[sources]` get refused by name?
   - Does `declare_source` leave the lock bytes untouched, keep unknown keys of an existing
     entry, and refuse before writing on every malformed input?
   - In `wrap.py`: is the repository-root check right for a worktree or a symlinked path? Is
     the existing-path rule right when `.gitmodules` names the path with a different URL, or
     when the path is a registered submodule whose directory is missing? After
     `_embed_git_directory`, is the submodule usable (`git status` inside it, `git submodule
     status` from the wrapper)? What happens when `git submodule add` fails halfway? Is the
     report honest when `initialize_project` is interactive and the user aborts?
   - In `wrap_detection.py`: can a `build.gradle` that mentions GradleRIO in a comment or a
     string mislead the rule? Is the Gradle version parsed from `distributionUrl` only?
   - In `listing.py`: do the new rows break the JSON document or the pending logic?
   - Guidance files: can a wrapped source's origin or path inject Markdown that misleads an
     agent? Is the marker check exact?
2. Clarity of the new and modified lines. The standard is "obviously no deficiencies".
3. Test coverage of the new and modified lines. Add tests where a branch is not exercised.
   Every test must fail if the line it covers is broken. Do not pad.

Stay inside the PR's scope: the `[sources]` declaration, `declare_source`, `project wrap`,
its detection and guidance, the `config show` rows and the documentation of these. Do not
change `initialize_project`, the lock generation, the capsule runtime or the base image. Do
not widen the manifest contract; if you believe the table's shape is wrong, say why in the PR
body and keep your change minimal.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, the `evidence/` directory,
  or run `devcapsule workflow publish`.
- Do not commit the `website` submodule pointer, the `devcapsule-sample-trading-research`
  submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/` or `__pycache__`.
- Do not merge anything. Do not push to `main` or to any branch other than your review branch.
- Do not rebase or force-push. Do not build images or run capsules.

## Deliverable

1. Commits on `ws-wrapped-projects/wrap-review`, each message naming the component and the
   evidence, ending with your `Co-Authored-By:` line:
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`.
2. Push the branch and open one pull request with
   `gh pr create --base ws-wrapped-projects/wrap --head ws-wrapped-projects/wrap-review`.
   Title: "Correctness, clarity and coverage review of #333 (PR1.1)". The body lists each
   finding as: what was wrong or unclear, where, what you changed, how the test proves it.
   Separate "changed" from "considered and left alone, because". List the proposals you did
   not implement. State the gate result with counts and what was skipped. If you find nothing
   to change, say so in the PR body and open the PR with the added tests only, or, if there
   are none, say that in your final report instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or "NO PR" if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about
twenty words, active voice. Every claim about behavior must be backed by a test or a command
you ran.

If you cannot proceed, because of a blocker like network or credentials, stop and say exactly
what blocked you. Do not work around a blocker.
