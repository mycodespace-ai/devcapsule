# Implementor brief for the codex + gpt-6-astra (high) pair: `host-ide` VS Code first slice

You are the implementor pair (`gpt-6-astra`, high reasoning effort) for the `host-ide` workstream's first slice: split-surface VS Code support targeting `release-0.3.1`. The Antigravity (`Gemini 4 Hydrogen`) pair is coordinating and will review your pull request under the reversed Pair Review Loop.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/host-ide-impl`, on the branch `ws-host-ide/vscode-codium-impl`, branched from `ws-host-ide/vscode-codium`. Work only there. Do not touch the main checkout at `/workspace/301e4208ef81-ChatGPT_Codex`.

Read first, in this order:
1. `AGENTS.md`
2. `WORKFLOW.md`
3. `WORKFLOW-LOCAL.md`
4. `engineering-docs/work-orders/2026-11-19-host-ide-vscode.md`
5. `engineering-docs/wip/2026-11-19-host-ide/CURRENT-STATUS.md`

## GitHub CLI

In every shell that uses `gh`, first run:

```bash
. /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh
```

Then `gh` is logged in to `github.com` against `mycodespace-ai/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` and `website/` checkout exist. Run checks from `devcapsule-src` with:

```bash
export PYTEST_ADDOPTS="--basetemp=/home/devcapsule/pytest-host-ide-impl"
export DEVCAPSULE_DIFF_BASE="upstream/release-0.3.1"
```

(Do not put `"worktree"` in `--basetemp`, because `tests/test_wrap.py` asserts `"worktree"` does not appear in generated git config paths.)

Run the full gate `.venv/bin/python -m nox -s build` (and focused integration tests `.venv/bin/python -m pytest --no-cov -m integration tests/integration/test_host_ide_cli.py`) before your final push and report exact counts and any skipped checks. Do not build Docker images or launch live containers inside this capsule.

## The task

Implement `engineering-docs/work-orders/2026-11-19-host-ide-vscode.md`:

1. **Configuration & authorization (`host-ide` node):**
   - Add `"host-ide"` to `HOME_CAPABILITY_DEFAULTS` in `devcapsule/configuration/authorization.py` (user-owned like `host-x11` and `github-ssh`, NOT in `CURATED_HOST_RECOMMENDATIONS`; defaults to `False` when unanswered/denied).
   - Wire `"host-ide"` through `devcapsule/configuration/listing.py` (`HOST_ACCESS_NODES`), `devcapsule/configuration/review.py` (`HostAccess.host_ide`, `overlay`, `effective_host`), `devcapsule/configuration/console_channel.py` and `devcapsule-webconsole/devcapsule_webconsole/configuration.py` (`SECURE_AUTHORIZATIONS`), and `devcapsule/commands/project.py` (`_RUN_ONCE_AUTHORIZATIONS`, `ConfigDenyCommand`).
   - When `host-ide = true`, verify the checkout's resolved `interactive-surface` is `"vscode"` (fail loudly for any other IDE, including `codium` for now, since `codium` is the next slice).
   - Keep `host-x11` and Docker modes (`none`, `host`, `dind`) completely orthogonal.
   - Substitute `xfce4-terminal` into the launch runtime lock (`components.interactive-surface = "xfce4-terminal"`, replacing `vscode` in `components` and `materialization` with the resolution matrix's `xfce4-terminal` pin for the lock's platform and base family) without altering `devcapsule.toml`, `devcapsule.<platform>.lock`, or saved `capabilities.selected`. Ensure container `vscode-download` consent is not demanded when `host-ide = true` substitutes `xfce4-terminal`.
   - Disable recursive E2E readiness (`disabled=arguments.no_recursive_e2e or host_ide` in `recursive_e2e_launch_environment`) when `host-ide = true`, and print a clear notice on eligible DevCapsule checkouts.

2. **Host VS Code acquisition, isolated config home, and attach (`devcapsule/host_ide.py`):**
   - Strictly follow *Host Inputs* rules 1–6 in `WORKFLOW-LOCAL.md` (pure planning/decision functions of values, frozen dataclasses, entry layer executes I/O/network/subprocesses, no module-level host reads or host-reading defaults).
   - Resolve `code`:
     1) Check `code` on `PATH` first.
     2) If absent, reuse an already-unpacked DevCapsule host VS Code under `homes.data / "host-ide" / "vscode"` if present.
     3) Otherwise (Linux `amd64`/`arm64`, macOS `amd64`/`arm64`), require `vscode` channel trust (`HomeTrust`, `https://code.visualstudio.com/license`), fetch stable release JSON from `https://update.code.visualstudio.com/api/update/<target>/stable/latest`, verify HTTPS URL and `sha256hash`, download to `homes.cache / "host-ide" / "vscode"`, verify digest, and unpack atomically into `homes.data / "host-ide" / "vscode" / <version>`. On WSL2 without `code` on `PATH`, fail with actionable Windows VS Code installation guidance.
   - Maintain an isolated VS Code configuration home under `homes.config / "host-ide" / "vscode"`:
     - `user-data/` (`--user-data-dir`)
     - `extensions/` (`--extensions-dir`)
     - Atomically merge required settings into `user-data/User/settings.json` while preserving user edits (set `"dev.containers.executeInWSL": true` on WSL2 when Docker runs inside the WSL2 distro rather than Docker Desktop).
     - Ensure `ms-vscode-remote.remote-containers` is installed in `extensions/` (`--list-extensions`, then `--install-extension ms-vscode-remote.remote-containers` if missing) before starting the container.
   - Build `--folder-uri vscode-remote://attached-container+<hex_json><project_mount>` (UTF-8 hex of `{"containerName":"/<container_name>"}`) and `[code_bin, f"--user-data-dir={user_data_dir}", f"--extensions-dir={extensions_dir}", "--new-window", "--folder-uri", folder_uri]`.

3. **Launcher & CLI wiring (`commands/project.py`, `launch/pycharm/_launcher.py`):**
   - Support `--print-command` (printing both `docker run` and the host `code` attach command without downloading/installing/launching).
   - Ensure `container_name` is deterministic before launch, pass `host_ide_command` and test seam `open_host_ide` to `PycharmRunOptions` / `PycharmRunConfig`.
   - In `run_pycharm`, start a transport-independent readiness watcher thread (polling `docker inspect -f '{{.State.Running}}' <name>` + `docker exec <name> test -d <project_mount>` until `stop_watching` is set) so it works identically for both `contained` and `host-x11`, then invoke `open_host_ide` or detached host `subprocess.Popen` (on headless Linux without `DISPLAY`/`WAYLAND_DISPLAY`, print the attach command and a notice instead of failing).

4. **Tests & docs:**
   - Strictly obey *Unit Tests* rules 1–9 in `WORKFLOW-LOCAL.md` (mirror paths under `tests/unit/devcapsule/`, plain-English docstrings on every test, value-based tests with no `monkeypatch` or `unittest.mock` in new or changed unit tests, and never edit individual tests in `legacy` files).
   - Add mirror unit tests (`tests/unit/devcapsule/test_host_ide.py` and `tests/unit/devcapsule/configuration/...`) plus CLI/fake-`code` integration tests (`tests/integration/test_host_ide_cli.py`).
   - Update user docs under `docs/` (`docs/everyday-development/ides-and-terminals.md` and any affected reference/configuration docs) and ensure `nox -s docs-contract` passes.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, `index.md`, or `engineering-docs/wip/2026-11-19-host-ide/evidence/`, or run `devcapsule workflow publish` (the coordinator handles records after review).
- Do not commit `website/`, `.idea/`, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything, push to `main` or `release-0.3.1`, rebase, or force-push.
- Do not build Docker images or run live capsules.

## Deliverable

1. Commit cleanly on `ws-host-ide/vscode-codium-impl` with `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>` (keeping Costin Cozianu `<ccozianu@gmail.com>` as author).
2. Run the full gate (`nox -s build`) and focused integration tests (`tests/integration/test_host_ide_cli.py`).
3. Push `ws-host-ide/vscode-codium-impl` to `upstream` and open one pull request targeting `release-0.3.1`:
   `gh pr create -R mycodespace-ai/devcapsule --base release-0.3.1 --head ws-host-ide/vscode-codium-impl`
   Include a concise summary, what changed, design/review notes, and exact validation counts (plus what the hosted gate does not catch).
4. Print the PR URL as the last line of your output.
