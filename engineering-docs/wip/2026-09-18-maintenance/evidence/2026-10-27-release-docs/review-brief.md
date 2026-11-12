# Review brief for Claude Code, Claude Fable 5.1: PR294.1 on release documentation automation

Codex, GPT-6 Astra opened PR #294, "Release documentation automation (C20): release-docs.py, the final-tag checks and the test-site dispatch".
Its branch is `ws-maintenance/c20-release-docs`, based on `release-0.3.0` at `5585e09`.
This is the first review of C20. Your job is one improvement pull request against that implementation branch.
Costin Cozianu merges the implementation PR. The human starts your review session.

## Your checkout

You are in `/home/devcapsule/worktrees/maintenance-review`, on
`ws-maintenance/c20-release-docs-review`, branched from `ws-maintenance/c20-release-docs`.
Work only there. Do not touch the implementor's checkout at
`/home/devcapsule/worktrees/maintenance-impl-4`, the main checkout at
`/workspace/301e4208ef81-ChatGPT_Codex`, or any other worktree.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`,
then the work order, which exists on `main`:

    git fetch origin main
    git show origin/main:engineering-docs/work-orders/2026-10-27-release-documentation-automation.md

Then read `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md`,
including *Open Threads*. Its earlier release steps are historical.
The implementor's judgments are in PR #294, under "Judgments for the human".
The implementation brief prohibited changes to that status file.
Read the contract docstring in `devcapsule-src/scripts/release-docs.py`,
then `engineering-docs/development/review-partner-loop.md`.
Read the release runbook, `engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md`.
Read `devcapsule-src/scripts/release-protocol.py`, `docs/versions.yaml`,
and sections 4.1, 4.2, 8 and 9 of
`engineering-docs/specifications/product/content-website-contract.md`.
The work order's decisions are settled. Do not reopen them.

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against
`ccozianu/devcapsule`. Check `gh auth status -h github.com` once before use.
Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists. Install this branch's requirements before testing:

    cd devcapsule-src
    .venv/bin/python -m pip install -r dev-requirements.txt
    PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-claude" .venv/bin/python -m pytest --no-cov -q tests/test_release_docs.py
    PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-claude" .venv/bin/python -m mypy scripts/release-docs.py tests/test_release_docs.py
    PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-claude" .venv/bin/python -m nox -s build

Run the gate in the foreground before your final push. Keep logs outside pytest's basetemp.
Report unit, packaging integration, web console, and documentation page counts.
The gate checks tests with mypy. The explicit mypy command also checks the new script.
Initialize the pinned `website` submodule in your own checkout if needed.
Do not commit its pointer. Do not omit the documentation check silently.

This PR touches these files:

- New: `devcapsule-src/scripts/release-docs.py` and `devcapsule-src/tests/test_release_docs.py`.
- Dependencies: `devcapsule-src/pyproject.toml` and `devcapsule-src/dev-requirements.txt`.
- Workflows: `.github/workflows/release-pex.yml` and `.github/workflows/website.yml`.
- Rules: `WORKFLOW-LOCAL.md`, its humane companion, the content–website contract,
  the release runbook, and `engineering-docs/releases/v0.3.0/README.md`.
- Handoff: this brief under the maintenance evidence directory.

Do not build images, start capsules, run IDE smoke, push tags, or dispatch workflows.
The release driver owns candidate acceptance with those environments.
The read-only `published` checks against real GitHub releases are permitted.
`actionlint` is unavailable. Load both workflows with `yaml.safe_load` and read them against GitHub Actions syntax.
The implementor also ran `bash -n` on all 23 workflow run blocks.
Do not run those workflow bodies against GitHub.

Implementor evidence on `24dc12b`: the full gate passed both sessions.
Unit tests: 2,416 passed, 36 deselected, one xfailed, one xpassed.
Packaging integration: 17 passed. Web console: 357 passed.
The documentation contract passed for 189 pages, including 17 aliases.
The focused tests passed all 78 cases. Explicit mypy passed for the helper and tests.
The PR body quotes scratch promotion, missing/present notes, and real-release checks.
`published` passed on main's manifest and refused the promoted copy for missing 0.3.0.
A trial promotion in the implementation checkout failed the full content check
because `docs-0.3.0` does not exist yet. The manifest was restored byte for byte.
The pinned consumer's parser accepted the promoted manifest separately.
Do not create that ref to remove the limitation. The release driver owns it.

## The task

Review the diff against the release base:

    gh pr diff 294
    gh pr view 294 --json body

Read the work order and module docstring before the tests.
Read the final-tag protocol before judging the runbook's candidate sequence.
Read the website consumer's manifest parser at the pinned submodule revision.

Improve exactly these three things, in this order:

1. Correctness of changed lines. Does promotion handle every admitted manifest shape,
   including reordered entries, no supported entry, several deprecated entries,
   and repeatable holds? Does it refuse duplicate versions, duplicate fields,
   a repeated promotion, a wrong package version, an unsupported contract,
   unknown holds, and two supported versions without writing?
   Do `notice`, `note`, `legacy`, and `source-version` survive the round trip?
   Does `check` report every failed obligation? Does `notes` remove only the
   initial front matter and reject empty bodies and placeholders?
   Does `published` skip development and name each absent download?
   What happens for a draft, a prerelease, a missing release, or a missing asset?
   What does malformed versions input do to each of the four commands?
   `notes` intentionally reads only the notes file; judge that scope explicitly.
   Are shell arguments quoted? Does the documentation comparison select root `docs/`?
   Are the new release steps final-only? Does each run before or after the correct predecessor?
   Do recovered releases still run documentation checks? Does a failed dispatch fail its step?
   Does the website guard run in both modes with the workflow token and pinned PyYAML?
   Are the original candidate commands unchanged? Do the final tag and accepted candidate still name identical source?
2. Clarity of changed lines. The standard is "obviously no deficiencies".
3. Test coverage of changed lines. Add tests for uncovered behavior.
   Each test must fail if the line it covers breaks. Do not pad.

Stay within release documentation automation as the work order defines it.
Do not change the changelog, maintenance state, candidate protocol, website implementation,
or release content. Do not broaden the contract. Explain any disagreement in the PR body.

## What you must not do

- Do not edit any `CURRENT-STATUS.md`, `intake-dispositions.md`, or the `evidence/` directory.
  Do not run `devcapsule workflow publish`.
- Do not commit submodule pointers, `.idea/`, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Push only `ws-maintenance/c20-release-docs-review`.
- Do not rebase, force-push, build images, start capsules, push tags, or dispatch workflows.

## Deliverable

1. Commit on `ws-maintenance/c20-release-docs-review` with messages that name the component and evidence.
   Before each commit, run `git status --short` and `git var GIT_AUTHOR_IDENT`.
   The author must remain Costin Cozianu. End every message with:
   `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
2. Push and open one PR:

       git push -u origin ws-maintenance/c20-release-docs-review
       gh pr create --base ws-maintenance/c20-release-docs --head ws-maintenance/c20-release-docs-review

   Title: "Correctness, clarity and coverage review of #294 (PR294.1)".
   For each finding, state what was wrong, where, what changed, and how a test proves it.
   Separate changes from "considered and left alone, because".
   List proposals not implemented. Report gate counts and limits.
   If nothing needs changing, report that result. Open no empty PR.
3. Print the PR URL as the last output line, or "NO PR" if you opened none.

Write the PR body and report at about 80% ASD-STE100.
Use one fact per sentence and about twenty words per sentence.
Back each behavior claim with a test or command you ran.
If network, credentials, or another blocker prevents progress, stop and name it.
Do not work around a blocker.
