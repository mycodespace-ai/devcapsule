# Review brief for the Codex + gpt-6-astra pair: PR319.1 on Batch 1 user-docs 0.3.0 CLI alignment

The Antigravity + Gemini 4 Argon (High) pair opened [PR #319](https://github.com/ccozianu/devcapsule/pull/319) ("Align Batch 1 user docs (reference, updates, troubleshooting) with 0.3.0 CLI (10 files)") on branch `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting` against `release-0.3.0`. This is Batch 1 of 5 under [`2026-10-30-user-docs-0-3-0-cli-alignment.md`](../../../../work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md). Your job is one file-by-file improvement pull request (`PR319.1`) against `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/docs-batch-1-review`, on branch `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting-review`, branched from `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting`. Work only there. Do not touch `/home/devcapsule/worktrees/ai-learning-bootstrap` or any other worktree under `/home/devcapsule/worktrees` or `/workspace`.

Read first, in this order:
1. `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`
2. `engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md`
3. `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md` (section `User documentation 0.3.0 CLI alignment and prose review (Batch 1) — 2026-10-30`)
4. `engineering-docs/wip/2026-09-18-maintenance/evidence/2026-10-30-docs-batch-1/README.md`
5. `website/CONTRACT.md`

## GitHub CLI

In every shell where you run `gh`, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is authenticated against `ccozianu/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` and `website/node_modules` are already installed. Use `/var/tmp/dc-docs-batch1-codex` for all scratch probes and pytest basetemp:

- When probing CLI behavior with `devcapsule-src/.venv/bin/devcapsule`, always set `DEVCAPSULE_CONFIG_HOME=/var/tmp/dc-docs-batch1-codex/home` (or another directory inside `/var/tmp/dc-docs-batch1-codex`) and redirect `</dev/null` on any command that can prompt interactively (`project init`, `home trust accept`, `project config`). Never mutate host or capsule checkouts.
- Before your final push, run and report the counts from all three checks:
  1. `(cd devcapsule-src && .venv/bin/python -m nox -s docs-contract)`
  2. `./scripts/website.sh check` (runs the 23 website unit tests plus full site build and 196-page HTML/link/anchor verification)
  3. `(cd devcapsule-src && PYTEST_ADDOPTS="--basetemp=/var/tmp/dc-docs-batch1-codex/pytest" .venv/bin/python -m pytest -q -k release_docs)`
- Do not build Docker images or start containers; no container or GUI E2E run is part of this documentation slice.

This PR touches 10 end-user documentation files under `docs/`:
- `docs/reference/cli.md`
- `docs/reference/configuration-nodes.md`
- `docs/reference/project-info.md` (former `status: planned` stub, authored in full)
- `docs/updates/component-freshness.md`
- `docs/updates/component-upgrades.md`
- `docs/updates/launcher-updates.md`
- `docs/updates/supported-versions.md`
- `docs/troubleshooting/first-session.md`
- `docs/troubleshooting/diagnostics-and-logs.md`
- `docs/troubleshooting/cleanup-and-uninstall.md` (former `status: planned` stub, authored in full)

## The task

Review the diff of PR #319 against `release-0.3.0` (`gh pr diff 319`) **and read each of the 10 Batch 1 `docs/*.md` files in full** (not only the changed hunks, so untouched lines with stale `0.2.x` claims or awkward prose are caught too).

Improve the 10 files on your branch, focused on three things in this order:

1. **CLI and runtime accuracy against `release-0.3.0` (`devcapsule-src/`):**
   - Check every command name, subcommand, positional argument, option flag, exit status, error message, and JSON schema key in all 10 files against `devcapsule-src/.venv/bin/devcapsule --help` (and subcommand `--help` / scratch probes) and the Python modules (`commands/project.py`, `commands/home.py`, `commands/images.py`, `commands/workflow.py`, `project_information.py`, `diagnostics.py`, `platforms.py`, `configuration/storage.py`, `configuration/operations.py`, `materialization.py`, `components/*.py`).
   - Check subtle edge cases: Does `project info --json` actually emit every key and value string documented in `docs/reference/project-info.md` in both host and capsule modes? Are every component's persistent state slots, secret inputs, and download consent / channel names in `docs/reference/configuration-nodes.md` and `docs/updates/component-upgrades.md` exact? Are all storage paths in `docs/troubleshooting/cleanup-and-uninstall.md` and `docs/troubleshooting/diagnostics-and-logs.md` exact for both default XDG directories and `DEVCAPSULE_CONFIG_HOME`? Did any `0.3.1`-deferred feature (automated image/cache cleanup, new doc routes) or retired `0.2.x` flag slip through?
2. **Clarity and human prose for the adopter reader:**
   - The reader of `docs/**/*.md` is a DevCapsule user/adopter. Tighten any remaining LLM-English filler, passive circumlocutions, internal repository/operator jargon, or ambiguous instructions so every sentence is direct and concrete. Never place reviewer notes inside `docs/**/*.md`.
3. **Website content contract (`website/CONTRACT.md`) and cross-link integrity:**
   - Verify single-sentence `description` (`<= 200` chars), `updated: 2026-10-30`, zero `status: planned` lines in `docs/reference/`, `docs/updates/`, and `docs/troubleshooting/`, zero literal `v?0\.\d+\.\d+` version strings, valid `sh`/`bash` syntax in code blocks, and intact anchors (`#home-and-development-commands`, `#preview-then-choose`, `#browser-evidence`, `#when-asking-for-help`, `#how-much-disk-this-takes`).

Stay strictly inside Batch 1's 10 `docs/` files. Do not edit any file under `docs/` outside those 10 paths (`git diff --name-only origin/release-0.3.0 -- docs/` must list at most those 10 `.md` files and never `docs/versions.yaml`). Do not edit Python production code; if you discover a genuine `0.3.0` CLI bug while verifying docs, leave code untouched and report it under *Proposals not implemented* in your PR body.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, `index.md`, `engineering-docs/releases/**`, or the `evidence/` directory, and do not run `devcapsule workflow publish`.
- Do not add, delete, move, or rename any file in `docs/`, and do not edit `docs/versions.yaml` or `website/CONTRACT.md`.
- Do not commit the `website` submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Do not push to `main`, `release-0.3.0`, or any branch other than `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting-review`.
- Do not rebase or force-push. Do not build Docker images or run containers.

## Deliverable

1. Keep the human's Git author and committer identity (`git var GIT_AUTHOR_IDENT`: `Costin Cozianu <ccozianu@gmail.com>`). Commit your improvements on `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting-review`, ending every commit message after a blank line with:
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`
   Verify with `git log -1 --format=fuller` before pushing.
2. Push your branch and open one pull request with:
   `gh pr create --base ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting --head ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting-review`
   Title: `"Correctness, clarity and coverage review of #319 (PR319.1)"`.
   In the PR body, include:
   - A 10-row file-by-file audit table covering every file in Batch 1 (commands/modules checked and verdict).
   - Each finding under *Changed* (what was inaccurate or unclear, where, what you changed, and which CLI invocation or source line proves it).
   - *Considered and left alone, because*.
   - *Proposals not implemented* (any CLI defects or out-of-batch `docs/` follow-ups spotted for Batches 2–5 or `0.3.1`).
   - Validation results with counts (`nox -s docs-contract`, `./scripts/website.sh check`, `pytest -q -k release_docs`, `git diff --check`).
   If you find nothing to change across all 10 files, say so in your final report with the 10-file audit evidence instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or `NO PR` if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about twenty words, active voice. Every behavioral claim must cite a command you ran or an exact source file and line.

If you hit a blocker such as network or credentials, stop and report the exact blocker rather than working around it.
