# Implementation brief for the Codex + gpt-6-astra pair: the release documentation automation slice (C20 for 0.3.0)

You are the implementor pair of one maintenance slice on the 0.3.0 release
branch, under the review-partner loop, topic 9.11 of `WORKFLOW.md`. The
work order is `engineering-docs/work-orders/2026-10-27-release-documentation-automation.md`
on `main`; the owner read it and said to run with it on 2026-10-27. Claude
Code, Claude Fable 5.1, is the review partner. The human's session starts
the review partner after you hand over your pull request; you do not start
it. The owner merges your pull request.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/maintenance-impl-4`,
on the branch `ws-maintenance/c20-release-docs`, forked from
`origin/release-0.3.0` at `5585e09`. Work only there. Do not touch the
main checkout at `/workspace/301e4208ef81-ChatGPT_Codex` or any other
worktree under `/home/devcapsule/worktrees`.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`,
then the work order, which is not on your branch:

    git fetch origin main && git show origin/main:engineering-docs/work-orders/2026-10-27-release-documentation-automation.md

Then `engineering-docs/development/review-partner-loop.md`, the release
runbook `engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md`,
`.github/workflows/release-pex.yml`, `.github/workflows/website.yml`,
`devcapsule-src/scripts/release-protocol.py` and
`devcapsule-src/tests/test_release_protocol.py`, `docs/versions.yaml`,
the content–website contract `engineering-docs/specifications/product/content-website-contract.md`
sections 4.1, 4.2, 8 and 9, and the `docs-<version>` section of
`WORKFLOW-LOCAL.md`.

The work order is the specification. Its *Decisions taken here* are
decided; do not reopen them. Where it is silent, choose the smallest thing
that satisfies it and list the choice under judgments in the PR body.

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against
`ccozianu/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists with the development
dependencies installed. Run unit tests and mypy from `devcapsule-src` with
`PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-codex"`. The gate
type-checks `tests/` too. Run `nox -s build` from `devcapsule-src` before
your final push, in the foreground, and report its counts: unit tests,
packaging integration, the web console session, the documentation
contract's page count.

After you add PyYAML and its stubs to the `dev` extra in
`devcapsule-src/pyproject.toml`, regenerate `dev-requirements.txt` with
the exact command its header names, from the `.venv`, then reinstall the
requirements into the `.venv` before running anything else.

`actionlint` is not on this capsule. Validate the two workflow files by
reading them against the GitHub Actions syntax and by loading each with
`yaml.safe_load`; say in the PR body that this is how they were checked.

Do not build images, run capsules, push tags, or dispatch workflows. The
`published` subcommand may be run against the real releases through `gh`,
read-only, as the order's acceptance evidence asks.

## The task

Implement the work order on your branch, in these commits, each with a
message naming the component and the evidence:

1. `devcapsule-src/scripts/release-docs.py` with its four subcommands,
   `promote`, `check`, `notes` and `published`, and
   `devcapsule-src/tests/test_release_docs.py`, loading the script as
   `test_release_protocol.py` does. The release state for `published`
   enters through a callable the tests replace. The script mutates no Git
   ref.
2. The `dev` extra and the regenerated `dev-requirements.txt`.
3. `.github/workflows/release-pex.yml`: the final-only step *Verify the
   documentation obligations*, the `--notes-file` body for a final
   release, the final-only *Build the test website* dispatch, and
   `actions: write` in the permissions. The candidate path stays
   unchanged, line for line.
4. `.github/workflows/website.yml`: the `published` guard step after the
   checkout, in both modes, with `GH_TOKEN` set to the workflow token.
5. The rules: `WORKFLOW-LOCAL.md`, the `docs-<version>` section, item 2;
   the contract's section 4.2 sentence on `source-version`; the runbook's
   *Documentation Is Part Of The Release* and its steps 3, 6 and 7; the
   0.3.0 release overview's *Scope And Owner Decisions* gains one entry
   recording the slice and the order of the final steps. Plain prose, the
   way the surrounding text reads. Do not edit the changelog or the
   maintenance status file; the release driver does.
6. The review brief for the review partner, as the template in
   `review-partner-loop.md` prescribes, every section filled, at
   `engineering-docs/wip/2026-09-18-maintenance/evidence/2026-10-27-release-docs/review-brief.md`.
   The review partner's worktree is `/home/devcapsule/worktrees/maintenance-review`
   on the branch `ws-maintenance/c20-release-docs-review`, its scratch
   `/opt/devcapsule-gate/pytest-claude`, its pull request `PRn.1` against
   your branch, where `n` is your pull request's number. Name the pair
   "Claude Code, Claude Fable 5.1". The correctness questions are the
   ones a careful engineer would ask of this slice: the lifecycle moves
   on every shape the file can have, the refusals, the front-matter
   stripping, a release that is a draft or a prerelease or lacks the
   asset, the workflow steps' quoting and the exact conditions under
   which each runs, what a malformed versions file does to each
   subcommand.

Before you commit, check `git var GIT_AUTHOR_IDENT`: the author is the
human's identity, Costin Cozianu, as the checkout has it. End every commit
message with your trailer:
`Co-Authored-By: GPT-6 Astra Codex <noreply@openai.com>`.

## What you must not do

- Do not edit any `CURRENT-STATUS.md`, `intake-dispositions.md`, the
  changelog, or run `devcapsule workflow publish`.
- Do not commit the `website` submodule pointer, the sample-project
  submodule pointers, `.idea/` files, `*.egg-info`, `.nox/`, `dist/` or
  `__pycache__`. Check `git status` before every commit.
- Do not merge anything. Do not push to `main`, to `release-0.3.0`, or to
  any branch other than `ws-maintenance/c20-release-docs`.
- Do not rebase or force-push. Do not build images or run capsules. Do
  not push tags. Do not dispatch any workflow.
- Do not use the words gen1, gen2, substrate or edge in any text you
  write.

## Deliverable

1. Commits on `ws-maintenance/c20-release-docs`, as above.
2. Push the branch with `git push -u origin ws-maintenance/c20-release-docs`
   and open one pull request with
   `gh pr create --base release-0.3.0 --head ws-maintenance/c20-release-docs`.
   Title: "Release documentation automation (C20): release-docs.py, the
   final-tag checks and the test-site dispatch". The body, in the house
   style of PR #276: who implements, who reviews, who merges; a numbered
   list of what changed; the judgments for the human, each with the
   choice you made and why; the validation with counts; the acceptance
   evidence the order asks for, quoted: the `promote 0.3.0` diff on a
   scratch copy of the branch's `docs/versions.yaml`, `check 0.3.0` on
   that copy before and after a `notes.md` stub, `published` against the
   real releases on `main`'s file and on the promoted copy; how the
   workflow files were checked.
3. Print the PR URL as the last line of your output, or "NO PR" with the
   reason if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per
sentence, about twenty words, active voice. Every claim about behavior
must be backed by a test or a command you ran.

If you cannot proceed, because of a blocker like network or credentials,
stop and say exactly what blocked you. Do not work around a blocker.
