# Review brief for the Codex + gpt-6-astra pair: PR321.1 on Batch 2 user-docs 0.3.0 CLI alignment

The Antigravity + Gemini 4 Argon (High) pair opened [PR #321](https://github.com/ccozianu/devcapsule/pull/321) ("docs(0.3.0): user docs CLI alignment & prose review — Batch 2 (configuration)") on branch `ws-maintenance/0.3.0-docs-batch-2-configuration` against `release-0.3.0`. This is Batch 2 of 5 under [`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md). Your job is one file-by-file improvement pull request (`PR321.1`) against `ws-maintenance/0.3.0-docs-batch-2-configuration`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/docs-batch-1-review`, reset cleanly onto branch `ws-maintenance/0.3.0-docs-batch-2-configuration-review`, branched from `ws-maintenance/0.3.0-docs-batch-2-configuration`. Work only there. Do not touch `/home/devcapsule/worktrees/ai-learning-bootstrap` or any other worktree under `/home/devcapsule/worktrees` or `/workspace`.

Read first, in this order:
1. `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`
2. `engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md`
3. `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md` (section `User documentation 0.3.0 CLI alignment and prose review (Batch 2) — 2026-10-30`)
4. `engineering-docs/wip/2026-09-18-maintenance/evidence/2026-10-30-docs-batch-2/README.md`
5. `website/CONTRACT.md`

## GitHub CLI

In every shell where you run `gh`, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is authenticated against `ccozianu/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` and `website/node_modules` are already installed. Use `/var/tmp/dc-docs-batch2-codex` for all scratch probes and pytest basetemp:

- When probing CLI behavior with `devcapsule-src/.venv/bin/devcapsule`, always set `DEVCAPSULE_CONFIG_HOME=/var/tmp/dc-docs-batch2-codex/home` (or another directory inside `/var/tmp/dc-docs-batch2-codex`) and redirect `</dev/null` on any command that can prompt interactively (`project init`, `home trust accept`, `project config`). Never mutate host or capsule checkouts.
- Before your final push, run and report the counts from all three checks:
  1. `(cd devcapsule-src && .venv/bin/python -m nox -s docs-contract)`
  2. `./scripts/website.sh build && ./scripts/website.sh check` (builds `.site-next` and runs the 23 website unit tests plus 196-page HTML/link/anchor verification)
  3. `(cd devcapsule-src && PYTEST_ADDOPTS="--basetemp=/var/tmp/dc-docs-batch2-codex/pytest" .venv/bin/python -m pytest -q -k release_docs)`
- Do not build Docker images or start containers; no container or GUI E2E run is part of this documentation slice.

This PR touches all 10 end-user documentation files under `docs/configuration/`:
- `docs/configuration/index.md`
- `docs/configuration/project-versus-personal.md`
- `docs/configuration/home.md`
- `docs/configuration/inspect.md`
- `docs/configuration/extra-tools.md`
- `docs/configuration/ide-preferences.md` (former `status: planned` stub, authored in full)
- `docs/configuration/resource-limits.md`
- `docs/configuration/local-base.md`
- `docs/configuration/software-approvals.md`
- `docs/configuration/capabilities.md`

## The task

Review the diff of PR #321 against `release-0.3.0` (`gh pr diff 321`) **and read each of the 10 `docs/configuration/*.md` files in full** (not only the changed hunks, so untouched lines with stale `0.2.x` claims, wrong command details, or awkward prose are caught too).

Improve the 10 files on your branch, focused on three things in this order:

1. **CLI and runtime accuracy against `release-0.3.0` (`devcapsule-src/`):**
   - Check every command name, subcommand, positional argument, option flag, exit status, error message, TOML table/key, XDG path, and JSON schema key in all 10 files against `devcapsule-src/.venv/bin/devcapsule --help` (and subcommand `--help` / scratch probes) and the Python modules (`commands/project.py`, `commands/home.py`, `commands/images.py`, `commands/_launcher.py`, `project_information.py`, `runtime_configuration.py`, `platforms.py`, `configuration/storage.py`, `configuration/home.py`, `configuration/home_channels.py`, `configuration/trust.py`, `configuration/values.py`, `configuration/bindings.py`, `configuration/operations.py`, `configuration/capability_commands.py`, `configuration/manifest_schemas.py`, `configuration/console_channel.py`, `materialization.py`, `components/*.py`).
   - Check subtle edge cases:
     - In `docs/configuration/ide-preferences.md`, verify every IDE component's slot name, container mount path, storage class (`durable`/`state`/`cache`), sensitivity (`personal`/`ordinary`/`credentials`), XDG and `DEVCAPSULE_CONFIG_HOME` host backing path, and exact validation timing/behavior of `config bind`, `state adopt`, `init --bind`, and `config unbind` (for example, when directory existence is validated on `config bind` versus `state adopt` or resolution/launch!).
     - In `docs/configuration/project-versus-personal.md`, verify every console-allowed vs. host-confirmation-required request verb (`console_channel.py`), `docker-args` and `env` flag handling and masking, and `config forget` / `config use` / `config set` behavior.
     - In `docs/configuration/home.md` and `docs/configuration/software-approvals.md`, verify `settings.toml` keys, channel IDs, `project config trust list [--json]` vs. `home trust list`, `home trust accept` vs. `run --trust`, per-checkout `authorize` vs. `approve`, and in-capsule read-only mounted settings fallback vs. `DEVCAPSULE_CONFIG_HOME`.
     - In `docs/configuration/capabilities.md`, `docs/configuration/resource-limits.md`, `docs/configuration/local-base.md`, `docs/configuration/inspect.md`, and `docs/configuration/extra-tools.md`, verify `--unverified`, `--force`, `recommend`, `memory`/`cpus` normalization, declared value types and omission (`none` vs `default`), `images build --type base`, `authorize base-image`, `config show`/`config check`, and `/opt/xtras`.
2. **Clarity and human prose for the adopter reader:**
   - The reader of `docs/**/*.md` is a DevCapsule user/adopter. Tighten any remaining LLM-English filler, passive circumlocutions, internal repository/operator jargon, or ambiguous instructions so every sentence is direct and concrete. Never place reviewer notes inside `docs/**/*.md`.
3. **Website content contract (`website/CONTRACT.md`) and cross-link integrity:**
   - Verify single-sentence `description` (`<= 200` chars), `updated: 2026-10-30`, zero `status: planned` lines in `docs/configuration/`, zero literal `v?0\.\d+\.\d+` version strings, valid `sh`/`bash` syntax in code blocks, and intact anchors (`#when-the-project-changes`, `#saved-docker-arguments`, `#from-the-console`, `#a-required-ide`).

Stay strictly inside Batch 2's 10 `docs/configuration/*.md` files. Do not edit any file under `docs/` outside those 10 paths (`git diff --name-only origin/release-0.3.0 -- docs/` must list at most those 10 `.md` files and never `docs/versions.yaml`). Do not edit Python production code; if you discover a genuine `0.3.0` CLI bug while verifying docs, leave code untouched and report it under *Proposals not implemented* in your PR body.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, `index.md`, `engineering-docs/releases/**`, `engineering-docs/development/review-partner-loop.md`, or the `evidence/` directory, and do not run `devcapsule workflow publish`.
- Do not add, delete, move, or rename any file in `docs/`, and do not edit `docs/versions.yaml` or `website/CONTRACT.md`.
- Do not commit the `website` submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Do not push to `main`, `release-0.3.0`, or any branch other than `ws-maintenance/0.3.0-docs-batch-2-configuration-review`.
- Do not rebase or force-push. Do not build Docker images or run containers.

## Deliverable

1. Keep the human's Git author and committer identity (`git var GIT_AUTHOR_IDENT`: `Costin Cozianu <ccozianu@gmail.com>`). Commit your improvements on `ws-maintenance/0.3.0-docs-batch-2-configuration-review`, ending every commit message after a blank line with:
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`
   Verify with `git log -1 --format=fuller` before pushing.
2. Push your branch and open one pull request with:
   `gh pr create --base ws-maintenance/0.3.0-docs-batch-2-configuration --head ws-maintenance/0.3.0-docs-batch-2-configuration-review`
   Title: `"Correctness, clarity and coverage review of #321 (PR321.1)"`.
   In the PR body, include:
   - A 10-row file-by-file audit table covering every file in Batch 2 (commands/modules checked and verdict).
   - Each finding under *Changed* (what was inaccurate or unclear, where, what you changed, and which CLI invocation or source line proves it).
   - *Considered and left alone, because*.
   - *Proposals not implemented* (any CLI defects or out-of-batch `docs/` follow-ups spotted for Batches 3–5 or `0.3.1`).
   - Validation results with counts (`nox -s docs-contract`, `./scripts/website.sh build && ./scripts/website.sh check`, `pytest -q -k release_docs`, `git diff --check`).
   If you find nothing to change across all 10 files, say so in your final report with the 10-file audit evidence instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or `NO PR` if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about twenty words, active voice. Every behavioral claim must cite a command you ran or an exact source file and line.

If you hit a blocker such as network or credentials, stop and report the exact blocker rather than working around it.
