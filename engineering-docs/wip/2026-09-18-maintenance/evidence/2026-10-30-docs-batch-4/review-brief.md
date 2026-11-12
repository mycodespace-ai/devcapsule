# Review brief for the Codex + gpt-6-astra pair: PR325.1 on Batch 4 user-docs 0.3.0 CLI alignment

The Antigravity + Gemini 4 Argon (High) pair opened [PR #325](https://github.com/ccozianu/devcapsule/pull/325) ("docs: align everyday-development and working-with-ai with 0.3.0 CLI (Batch 4)") on branch `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai` against `release-0.3.0`. This is Batch 4 of 5 under [`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md). Your job is one file-by-file improvement pull request (`PR325.1`) against `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/docs-batch-1-review`, reset cleanly onto branch `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai-review`, branched from `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai`. Work only there. Do not touch `/home/devcapsule/worktrees/ai-learning-bootstrap` or any other worktree under `/home/devcapsule/worktrees` or `/workspace`.

Read first, in this order:
1. `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`
2. `git show origin/main:engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md`
3. `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md` (section `User documentation 0.3.0 CLI alignment and prose review (Batch 4) — 2026-10-30`)
4. `engineering-docs/wip/2026-09-18-maintenance/evidence/2026-10-30-docs-batch-4/README.md`
5. `website/CONTRACT.md`

## GitHub CLI

In every shell where you run `gh`, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is authenticated against `ccozianu/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` and `website/node_modules` are already installed. Use `/var/tmp/dc-docs-batch4-codex` for all scratch probes and pytest basetemp:

- When probing CLI behavior with `devcapsule-src/.venv/bin/devcapsule`, always set `DEVCAPSULE_CONFIG_HOME=/var/tmp/dc-docs-batch4-codex/home` (or another directory inside `/var/tmp/dc-docs-batch4-codex`) and redirect `</dev/null` on any command that can prompt interactively (`project init`, `home trust accept`, `project config`). Never mutate host or capsule checkouts.
- Before your final push, run and report the counts from all three checks:
  1. `(cd devcapsule-src && .venv/bin/python -m nox -s docs-contract)`
  2. `./scripts/website.sh build && ./scripts/website.sh check` (builds `.site-next` and runs the 23 website unit tests plus 196-page HTML/link/anchor verification)
  3. `(cd devcapsule-src && PYTEST_ADDOPTS="--basetemp=/var/tmp/dc-docs-batch4-codex/pytest" .venv/bin/python -m pytest -q -k release_docs)`
- Do not build Docker images or start containers; no container or GUI E2E run is part of this documentation slice.

This PR touches all 10 end-user documentation files under `docs/everyday-development/` (5) and `docs/working-with-ai/` (5):
- `docs/everyday-development/ides-and-terminals.md`
- `docs/everyday-development/git.md` (former `status: planned` stub, authored in full)
- `docs/everyday-development/run-debug-test.md` (former `status: planned` stub, authored in full)
- `docs/everyday-development/previews-and-ports.md` (former `status: planned` stub, authored in full)
- `docs/everyday-development/clipboard-and-browser.md`
- `docs/working-with-ai/choose-an-agent.md`
- `docs/working-with-ai/sign-in-and-defaults.md`
- `docs/working-with-ai/instructions-for-agents.md`
- `docs/working-with-ai/hosted-and-local-models.md` (former `status: planned` stub, authored in full)
- `docs/working-with-ai/review-and-change-agents.md` (former `status: planned` stub, authored in full)

## The task

Review the diff of PR #325 against `release-0.3.0` (`gh pr diff 325`) **and read each of the 10 `docs/*.md` files in full** (not only the changed hunks, so untouched lines with stale `0.2.x` claims, wrong command details, or awkward prose are caught too).

Improve the 10 files on your branch, focused on three things in this order:

1. **CLI and runtime accuracy against `release-0.3.0` (`devcapsule-src/`):**
   - Check every command name, subcommand, positional argument, option flag, interactive prompt, exit status, error message, container path, environment variable, state slot, secret binding, and seeded setting across all 10 files against `devcapsule-src/.venv/bin/devcapsule --help` (and subcommand `--help` / scratch probes) and the Python modules (`commands/project.py`, `commands/home.py`, `commands/_run_flow.py`, `launch/pycharm/_launcher.py`, `launch/pycharm/_image_build.py`, `images/base.py`, `images/tooling.py`, `container_runtime/entrypoint.py`, `container_runtime/filesystem.py`, `container_runtime/display.py`, `container_runtime/components/*.py`, `resolution_matrix.py`, `configuration/home_channels.py`, `configuration/trust.py`, `configuration/authorization.py`, `configuration/bindings.py`, `configuration/capability_commands.py`, `configuration/console_channel.py`, `configuration/docker_arguments.py`, `components/claude_code.py`, `components/codex.py`, `components/antigravity_cli.py`, `components/playwright.py`, `components/vscode.py`, `components/codium.py`, `components/pycharm.py`, `components/intellij.py`, `components/eclipse.py`, `components/rider.py`, `components/dotnet_sdk.py`).
   - Check subtle edge cases:
     - In `docs/everyday-development/git.md`, verify what `project run` (`inherit_legacy_configuration=False`) and `container_runtime/entrypoint.py` + `filesystem.py` actually mount, create (`/home/devcapsule/.ssh` `0700`), or pass on `docker run` (including whether `SSH_AUTH_SOCK` passthrough via `project run --` passes `reject_launcher_owned_docker_options`, and whether any host Git or SSH state crosses by default).
     - In `docs/everyday-development/ides-and-terminals.md` and `run-debug-test.md`, verify every IDE capability/provider name, `config ide` vs. `config use`, `run --ide ... --force` departure semantics (`project.py:2385`), `dotnet-sdk` environment variables (`dotnet_sdk.py`), `playwright.py` environment variables (`PLAYWRIGHT_BROWSERS_PATH`, `DEVCAPSULE_PLAYWRIGHT_PYTHON`, `DEVCAPSULE_PLAYWRIGHT_WHEELS`), `filesystem.py` directories (`~/xtras/bin` vs. `/opt/xtras` — verify whether `/opt/xtras` is mounted on `project run`!), and `--cap-add=SYS_PTRACE` passthrough acceptance.
     - In `docs/everyday-development/previews-and-ports.md` and `clipboard-and-browser.md`, verify `--publish` / `-p` passthrough and `docker-args set` / `list` / `clear`, `authorize network host` / `deny network` / `run --authorize network host`, `authorize host-browser true` / `deny host-browser` / `run --authorize host-browser true` (`HOST_OPEN_BROWSER` and `container_runtime/display.py`), and `openbox` / `tint2` / `noVNC` behavior.
     - In `docs/working-with-ai/choose-an-agent.md`, `sign-in-and-defaults.md`, `instructions-for-agents.md`, `hosted-and-local-models.md`, and `review-and-change-agents.md`, verify `known_channels()` (`claude-code`, `antigravity-cli`, `vscode`, `devcapsule-base`), `claude-code-download` and `antigravity-download`, `config add` / `omit` / `restore` / `run --with` (and which capability/component aliases `canonical_tool_name` accepts!), console-channel immediate vs. deferred verbs (`console_channel.py`), `config bind` / `unbind` for `codex/openai-api-key` and `antigravity-cli/gemini-api-key` (and whether `bind` is immediate or deferred on console, or requires existing env var at bind time vs. launch time!), exact seeded JSON/TOML files and keys (`claude_code.py`, `codex.py`, `antigravity_cli.py`, plus `state_seeding` implementation), and `codex` / `claude` / `antigravity` CLI invocations.
2. **Clarity and human prose for the adopter reader:**
   - The reader of `docs/**/*.md` is a DevCapsule user/adopter. Tighten any remaining LLM-English filler, passive circumlocutions, internal repository/operator jargon, or ambiguous instructions so every sentence is direct and concrete. Never place reviewer notes inside `docs/**/*.md`.
3. **Website content contract (`website/CONTRACT.md`) and cross-link integrity:**
   - Verify preserved `role: agents` on `docs/working-with-ai/choose-an-agent.md`, single-sentence `description` (`<= 200` chars), `updated: 2026-10-30`, zero `status: planned` lines across all 10 files, zero literal `v?0\.\d+\.\d+` version strings, and valid `sh`/`bash` syntax in code blocks.

Stay strictly inside Batch 4's 10 `docs/*.md` files. Do not edit any file under `docs/` outside those 10 paths (`git diff --name-only origin/release-0.3.0 -- docs/` must list at most those 10 `.md` files and never `docs/versions.yaml`). Do not edit Python production code; if you discover a genuine `0.3.0` CLI bug while verifying docs, leave code untouched and report it under *Proposals not implemented* in your PR body.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, `index.md`, `engineering-docs/releases/**`, `engineering-docs/development/review-partner-loop.md`, or the `evidence/` directory, and do not run `devcapsule workflow publish`.
- Do not add, delete, move, or rename any file in `docs/`, and do not edit `docs/versions.yaml` or `website/CONTRACT.md`.
- Do not commit the `website` submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Do not push to `main`, `release-0.3.0`, or any branch other than `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai-review`.
- Do not rebase or force-push. Do not build Docker images or run containers.

## Deliverable

1. Keep the human's Git author and committer identity (`git var GIT_AUTHOR_IDENT`: `Costin Cozianu <ccozianu@gmail.com>`). Commit your improvements on `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai-review`, ending every commit message after a blank line with:
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`
   Verify with `git log -1 --format=fuller` before pushing.
2. Push your branch and open one pull request with:
   `gh pr create --base ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai --head ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai-review`
   Title: `"Correctness, clarity and coverage review of #325 (PR325.1)"`.
   In the PR body, include:
   - A 10-row file-by-file audit table covering every file in Batch 4 (commands/modules checked and verdict).
   - Each finding under *Changed* (what was inaccurate or unclear, where, what you changed, and which CLI invocation or source line proves it).
   - *Considered and left alone, because*.
   - *Proposals not implemented* (any CLI defects or out-of-batch `docs/` follow-ups spotted for Batch 5 or `0.3.1`).
   - Validation results with counts (`nox -s docs-contract`, `./scripts/website.sh build && ./scripts/website.sh check`, `pytest -q -k release_docs`, `git diff --check`).
   If you find nothing to change across all 10 files, say so in your final report with the 10-file audit evidence instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or `NO PR` if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about twenty words, active voice. Every behavioral claim must cite a command you ran or an exact source file and line.

If you hit a blocker such as network or credentials, stop and report the exact blocker rather than working around it.
