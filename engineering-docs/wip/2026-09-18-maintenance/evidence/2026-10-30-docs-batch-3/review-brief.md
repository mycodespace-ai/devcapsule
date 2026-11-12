# Review brief for the Codex + gpt-6-astra pair: PR323.1 on Batch 3 user-docs 0.3.0 CLI alignment

The Antigravity + Gemini 4 Argon (High) pair opened [PR #323](https://github.com/ccozianu/devcapsule/pull/323) ("docs: align README, getting-started, your-project, and containment with 0.3.0 CLI (Batch 3)") on branch `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment` against `release-0.3.0`. This is Batch 3 of 5 under [`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md). Your job is one file-by-file improvement pull request (`PR323.1`) against `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/docs-batch-1-review`, reset cleanly onto branch `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment-review`, branched from `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment`. Work only there. Do not touch `/home/devcapsule/worktrees/ai-learning-bootstrap` or any other worktree under `/home/devcapsule/worktrees` or `/workspace`.

Read first, in this order:
1. `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`
2. `git show origin/main:engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md`
3. `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md` (section `User documentation 0.3.0 CLI alignment and prose review (Batch 3) — 2026-10-30`)
4. `engineering-docs/wip/2026-09-18-maintenance/evidence/2026-10-30-docs-batch-3/README.md`
5. `website/CONTRACT.md`

## GitHub CLI

In every shell where you run `gh`, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is authenticated against `ccozianu/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` and `website/node_modules` are already installed. Use `/var/tmp/dc-docs-batch3-codex` for all scratch probes and pytest basetemp:

- When probing CLI behavior with `devcapsule-src/.venv/bin/devcapsule`, always set `DEVCAPSULE_CONFIG_HOME=/var/tmp/dc-docs-batch3-codex/home` (or another directory inside `/var/tmp/dc-docs-batch3-codex`) and redirect `</dev/null` on any command that can prompt interactively (`project init`, `home trust accept`, `project config`). Never mutate host or capsule checkouts.
- Before your final push, run and report the counts from all three checks:
  1. `(cd devcapsule-src && .venv/bin/python -m nox -s docs-contract)`
  2. `./scripts/website.sh build && ./scripts/website.sh check` (builds `.site-next` and runs the 23 website unit tests plus 196-page HTML/link/anchor verification)
  3. `(cd devcapsule-src && PYTEST_ADDOPTS="--basetemp=/var/tmp/dc-docs-batch3-codex/pytest" .venv/bin/python -m pytest -q -k release_docs)`
- Do not build Docker images or start containers; no container or GUI E2E run is part of this documentation slice.

This PR touches 10 end-user documentation files across `docs/README.md`, `docs/getting-started/`, `docs/your-project/`, and `docs/containment/`:
- `docs/README.md`
- `docs/getting-started/install.md`
- `docs/getting-started/first-session.md`
- `docs/getting-started/stop-and-come-back.md`
- `docs/your-project/existing-repository.md`
- `docs/your-project/new-project.md`
- `docs/your-project/declare-needs.md` (former `status: planned` stub, authored in full)
- `docs/your-project/services-and-ports.md` (former `status: planned` stub, authored in full)
- `docs/containment/the-boundary.md`
- `docs/containment/granting-and-withdrawing.md`

## The task

Review the diff of PR #323 against `release-0.3.0` (`gh pr diff 323`) **and read each of the 10 `docs/*.md` files in full** (not only the changed hunks, so untouched lines with stale `0.2.x` claims, wrong command details, or awkward prose are caught too).

Improve the 10 files on your branch, focused on three things in this order:

1. **CLI and runtime accuracy against `release-0.3.0` (`devcapsule-src/`):**
   - Check every command name, subcommand, positional argument, option flag, interactive prompt, exit status, error message, TOML table/key, container mount/port/flag, and XDG path in all 10 files against `devcapsule-src/.venv/bin/devcapsule --help` (and subcommand `--help` / scratch probes) and the Python modules (`commands/project.py`, `commands/home.py`, `commands/_launcher.py`, `launch/pycharm/_launcher.py`, `project_information.py`, `runtime_configuration.py`, `resolution_matrix.py`, `configuration/manifest_schemas.py`, `configuration/owner_commands.py`, `configuration/operations.py`, `configuration/capability_commands.py`, `configuration/authorization.py`, `configuration/docker_arguments.py`, `configuration/values.py`, `configuration/trust.py`, `materialization.py`, `components/*.py`).
   - Check subtle edge cases:
     - In `docs/your-project/declare-needs.md`, verify `.devcapsule/devcapsule.toml` schema `2` tables and keys (`[project]`, `[requirements]`, `[requirements.env]`, `[configuration]`, `[configuration.values]`, `[recommendations]`, `[workflow]`), lock file naming and validation (`config check --manifest --lock`), exact `owner_commands.py` / `project config` command syntax and flags (`require`, `offer`, `drop`, `require env`, `offer env`, `drop env`, `recommend`, `init --regenerate` vs. `--force`), all 17 catalog capabilities and their versions/types in `resolution_matrix.py`, and declared value types (`boolean`, `integer`, `string`, `choice`) and defaults.
     - In `docs/your-project/services-and-ports.md`, verify `LAUNCHER_OWNED_DOCKER_OPTIONS` and `docker_arguments.py` validation on `--publish` / `-p` / `--add-host` / `--network` via both `project run --` and `project config docker-args set/add/clear`, `authorize network host` vs. `bridge` (`default`), `authorize docker-daemon host-socket` (`none` / `default`), `postgresql-client` capability, `env set`, and container mount paths (`/workspace/<project>`, `/home/devcapsule`).
     - In `docs/getting-started/install.md`, `first-session.md`, and `stop-and-come-back.md`, verify `{{download_url}}`/`{{tag}}`/`{{release_url}}` placeholders, `.pex` Python version requirements (`pyproject.toml` `requires-python`), exact interactive `project init` prompt sequence and defaults (`antigravity-agent`, `[none]`, `[default]`), `project run` startup output (desktop URL, recipe-11+ web console loopback URL, password line), IDE exit vs. `Ctrl+C` shutdown behavior, and what persists vs. stops on container exit.
     - In `docs/your-project/existing-repository.md` and `new-project.md`, verify `--ide`, `--require`, `--offer`, `--with`, `--without`, `--name`, `--bind`, `--regenerate`, `--force`, `checkout register`, IDE alias acceptance (both abstract capabilities like `python-ide` and concrete component names like `vscode`/`codium`), and non-mutating `config show` / `config check` behavior in uninitialized or freshly cloned repositories.
     - In `docs/containment/the-boundary.md`, `docs/containment/granting-and-withdrawing.md`, and `docs/README.md`, verify every default container mount, port, Linux capability/security-opt flag (`--cap-drop ALL`, `no-new-privileges`), `config authorize` nodes and accepted values (`true`, `false`, `bridge`, `host`, `host-socket`, `none`, `default`), `config deny` 5-node scope vs. `authorize <vendor>-download false`, `run --no-host-browser` / `--no-host-clipboard`, and section cross-links.
2. **Clarity and human prose for the adopter reader:**
   - The reader of `docs/**/*.md` is a DevCapsule user/adopter. Tighten any remaining LLM-English filler, passive circumlocutions, internal repository/operator jargon, or ambiguous instructions so every sentence is direct and concrete. Never place reviewer notes inside `docs/**/*.md`.
3. **Website content contract (`website/CONTRACT.md`) and cross-link integrity:**
   - Verify preserved `role` keys (`overview`, `getting-started`, `your-project`, `containment`) and `aliases` (`/docs/guides/first-session/`, `/docs/guides/your-project/`), intact anchors (`#check-your-computer`, `#1-make-a-first-workspace`), single-sentence `description` (`<= 200` chars), `updated: 2026-10-30`, zero `status: planned` lines across all 10 files, zero literal `v?0\.\d+\.\d+` version strings, and valid `sh`/`bash` syntax in code blocks.

Stay strictly inside Batch 3's 10 `docs/*.md` files. Do not edit any file under `docs/` outside those 10 paths (`git diff --name-only origin/release-0.3.0 -- docs/` must list at most those 10 `.md` files and never `docs/versions.yaml`). Do not edit Python production code; if you discover a genuine `0.3.0` CLI bug while verifying docs, leave code untouched and report it under *Proposals not implemented* in your PR body.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, `index.md`, `engineering-docs/releases/**`, `engineering-docs/development/review-partner-loop.md`, or the `evidence/` directory, and do not run `devcapsule workflow publish`.
- Do not add, delete, move, or rename any file in `docs/`, and do not edit `docs/versions.yaml` or `website/CONTRACT.md`.
- Do not commit the `website` submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Do not push to `main`, `release-0.3.0`, or any branch other than `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment-review`.
- Do not rebase or force-push. Do not build Docker images or run containers.

## Deliverable

1. Keep the human's Git author and committer identity (`git var GIT_AUTHOR_IDENT`: `Costin Cozianu <ccozianu@gmail.com>`). Commit your improvements on `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment-review`, ending every commit message after a blank line with:
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`
   Verify with `git log -1 --format=fuller` before pushing.
2. Push your branch and open one pull request with:
   `gh pr create --base ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment --head ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment-review`
   Title: `"Correctness, clarity and coverage review of #323 (PR323.1)"`.
   In the PR body, include:
   - A 10-row file-by-file audit table covering every file in Batch 3 (commands/modules checked and verdict).
   - Each finding under *Changed* (what was inaccurate or unclear, where, what you changed, and which CLI invocation or source line proves it).
   - *Considered and left alone, because*.
   - *Proposals not implemented* (any CLI defects or out-of-batch `docs/` follow-ups spotted for Batches 4–5 or `0.3.1`).
   - Validation results with counts (`nox -s docs-contract`, `./scripts/website.sh build && ./scripts/website.sh check`, `pytest -q -k release_docs`, `git diff --check`).
   If you find nothing to change across all 10 files, say so in your final report with the 10-file audit evidence instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or `NO PR` if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about twenty words, active voice. Every behavioral claim must cite a command you ran or an exact source file and line.

If you hit a blocker such as network or credentials, stop and report the exact blocker rather than working around it.
