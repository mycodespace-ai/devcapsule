# Implementation brief for the Codex + gpt-6-astra pair: one configuration home and the `home` commands (0.3.0)

You are the implementor pair of one maintenance slice on the 0.3.0 release
branch, under the review-partner loop, topic 9.11 of `WORKFLOW.md`. The
work order is
`engineering-docs/work-orders/2026-10-27-configuration-home-and-the-home-commands.md`;
the owner designed it in chat on 2026-10-27 and said on 2026-10-28 to run
with it. Claude Code, Claude Fable 5.1, is the review partner. The human's
session starts the review partner after you hand over your pull request;
you do not start it. The owner merges your pull request.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/maintenance-impl-4`,
on the branch `ws-maintenance/home-settings`, forked from
`origin/release-0.3.0` at `0514d50`. Work only there. Do not touch the
main checkout at `/workspace/301e4208ef81-ChatGPT_Codex` or any other
worktree under `/home/devcapsule/worktrees`.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`,
then the work order, which is on the project-management branch, not yet on
`main` (PR #297 is open):

    git fetch origin ws-project-management/coordination && git show origin/ws-project-management/coordination:engineering-docs/work-orders/2026-10-27-configuration-home-and-the-home-commands.md

Then `engineering-docs/development/review-partner-loop.md`, the bug
record `engineering-docs/bugs/devcapsule/2026-10-25-workstation-commands-live-under-project-config.md`,
D-0011 at `engineering-docs/decisions/product/d-0011-vendor-trust-once-per-workstation.md`,
`devcapsule/platforms.py`, `devcapsule/configuration/storage.py`,
`configuration/trust.py`, `configuration/workstation.py`,
`commands/project.py` (the `ConfigDefaultCommand`, `ConfigTrust*` classes
and `ConfigGroup`), `commands/_run_flow.py`, `runtime_configuration.py`,
`persistence.py`, `notifications.py`, `resolution_matrix.py`
(`_ComponentPin`, `component_closure`), `components/interface.py`
(`AcquisitionContract`, `locked_artifacts`), and the docs pages the order
lists under *The texts*.

The work order is the specification. Its *Decisions taken here* are
decided; do not reopen them. Its *Stopping points* are the only reasons to
stop. Where it is silent, choose the smallest thing that satisfies it and
list the choice under judgments in the PR body.

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against
`ccozianu/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists with the development
dependencies installed from the previous slice; run
`.venv/bin/pip install -r dev-requirements.txt -e .` once before you start,
to be sure. Run unit tests and mypy from `devcapsule-src` with
`PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-codex"`. The gate
type-checks `tests/` too. Run `nox -s build` from `devcapsule-src` before
your final push, in the foreground, and report its counts: unit tests,
packaging integration, the web console session, the documentation
contract's page count.

For the acceptance evidence, use a throwaway home under
`/opt/devcapsule-gate/home-evidence/` as `DEVCAPSULE_CONFIG_HOME`, and for
the unset case set `HOME` and `XDG_CONFIG_HOME` to throwaway directories
under the same tree rather than touching the real `~/.config/devcapsule`.
Item 5 of the acceptance evidence, inside a capsule, is replaced by the
unit test with the synthetic capsule context; you do not run capsules.

Do not build images, run capsules, push tags, or dispatch workflows.

## The task

Implement the work order on your branch, in these commits, each with a
message naming the component, the behaviour and the evidence:

1. `XdgHomes` and `DEVCAPSULE_CONFIG_HOME`, with the `notifications`
   derivation following; the tests of *Tests* item 1.
2. `settings.toml`: the one document, the two header fields, the
   refusal of a too-old launcher before any write, the no-rewrite of
   unchanged content; `workstation.toml` and `trust.toml` no longer
   read; the tests of item 2. This commit may carry the first half of
   the rename if the two cannot be separated cleanly; say so.
3. The `home` group with its five commands, the deletion of the three
   `project config` spellings, the channel source from the embedded
   matrix through the one shared function, `project config trust list`
   on the home, the terminal and `--trust` paths, the in-capsule hint;
   tests of items 3 to 6.
4. The mechanical rename of the code names the order lists, in one
   commit of its own, with the word test of item 7.
5. The texts: the docs pages, the new configuration section on the home,
   D-0011 amended and its file renamed with the two references
   following. Plain prose, the way the surrounding text reads. Do not
   edit the changelog or the maintenance status file; the release driver
   does.
6. The review brief for the review partner, as the template in
   `review-partner-loop.md` prescribes, every section filled, at
   `engineering-docs/wip/2026-09-18-maintenance/evidence/2026-10-28-configuration-home/review-brief.md`.
   The review partner's worktree is `/home/devcapsule/worktrees/maintenance-review`
   on the branch `ws-maintenance/home-settings-review`, its scratch
   `/opt/devcapsule-gate/pytest-claude`, its pull request `PRn.1` against
   your branch, where `n` is your pull request's number. Name the pair
   "Claude Code, Claude Fable 5.1". The correctness questions are the
   ones a careful engineer would ask of this slice: what a malformed
   `settings.toml` does to each command and to `project run`; whether
   any write can happen before the minimum-version refusal; whether the
   XDG defaults are byte-identical with the variable unset; whether the
   channel from the matrix equals the channel from a lock; what two
   launchers writing one home concurrently do; whether every deleted
   spelling is gone from every text.

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
  any branch other than `ws-maintenance/home-settings`.
- Do not rebase or force-push. Do not build images or run capsules. Do
  not push tags. Do not dispatch any workflow.
- Do not use the words gen1, gen2, substrate or edge in any text you
  write. Do not keep "workstation" anywhere the order says it goes.

## Deliverable

1. Commits on `ws-maintenance/home-settings`, as above.
2. Push the branch with `git push -u origin ws-maintenance/home-settings`
   and open one pull request with
   `gh pr create --base release-0.3.0 --head ws-maintenance/home-settings`.
   Title: "One configuration home and the home commands:
   DEVCAPSULE_CONFIG_HOME, settings.toml, devcapsule home trust|default|show".
   The body, in the house style of PR #294: who implements, who reviews,
   who merges; a numbered list of what changed; the judgments for the
   human, each with the choice you made and why; the validation with
   counts; the acceptance evidence the order asks for, quoted, items 1 to
   4; "Review is pending." as the last line before the trailer.
3. Print the PR URL as the last line of your output, or "NO PR" with the
   reason if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per
sentence, about twenty words, active voice. Every claim about behavior
must be backed by a test or a command you ran.

If you reach one of the order's stopping points, or a blocker like
network or credentials, stop and say exactly what stopped you. Do not
work around it.
