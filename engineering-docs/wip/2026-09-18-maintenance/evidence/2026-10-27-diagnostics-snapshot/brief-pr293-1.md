# Review brief for the Codex + gpt-6-astra pair: PR293.1 on diagnostics snapshot and export

The first pair, Antigravity with Gemini 4 Argon (High) and the owner, Costin Cozianu, has opened pull request 293 ("Session diagnostics snapshot and sanitized export (0.3.0)"), branch `ws-maintenance/0.3.0-diagnostics-snapshot`, against `release-0.3.0`. It implements Deliverable 4 (Diagnostics snapshot and sanitized export) and the manual browser-evidence contract of Deliverable 5 in `engineering-docs/work-orders/2026-10-08-persistent-session-diagnostics.md` for release `0.3.0`. Earlier reviews in this diagnostics series (`#207/#208` and `#209/#210, #211, #212`) covered Deliverables 1 through 3 (persistent session logs, signal preservation, and web-console crash logging). Your job is one improvement pull request against PR 293's branch under topic 9.11 of `WORKFLOW.md`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/maintenance-review`, on the branch `ws-maintenance/0.3.0-diagnostics-snapshot-review`, branched from `ws-maintenance/0.3.0-diagnostics-snapshot`. Work only there. Do not touch the implementor's worktree at `/home/devcapsule/worktrees/diagnostics-snapshot`, the primary mount at `/workspace/301e4208ef81-ChatGPT_Codex`, or any other `/home/devcapsule/worktrees/*` worktree.

Read first, in this order: `AGENTS.md`; `WORKFLOW.md` (topic 9.11); `WORKFLOW-LOCAL.md` (*Review Partners In This Checkout*, *GitHub Integration*, *Validation Commands*); `engineering-docs/work-orders/2026-10-08-persistent-session-diagnostics.md` (especially Deliverables 4 and 5 and *Security And Redaction*); `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md` (section `## Diagnostics snapshot and export — 2026-10-27`, which records the slice's judgments); then the modules whose docstrings carry the contract: `devcapsule-src/devcapsule/diagnostics.py`, `devcapsule-src/devcapsule/container_runtime/diagnose.py`, and `devcapsule-src/devcapsule/_redaction.py`; then the PR body (`gh pr view 293`).

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against `ccozianu/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists, with the source installed editable from this worktree. Run unit tests, `mypy`, and `nox` synchronously in the foreground from `devcapsule-src` with `PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-codex"`. Keep any log files you write outside pytest's basetemp (for example under `/opt/devcapsule-gate/logs/`), never inside `/opt/devcapsule-gate/pytest-codex`.

This PR touches:
- `devcapsule-src/devcapsule/`: `_redaction.py` (new), `diagnostics.py` (new), `container_runtime/diagnose.py` (new), `container_runtime/entrypoint.py`, `commands/project.py`, `launch/session_logs.py`, `launch/pycharm/_launcher.py`
- `devcapsule-src/noxfile.py`
- `devcapsule-src/tests/`: `test_runtime_diagnose.py` (new), `test_diagnostics.py` (new), `e2e/test_session_diagnostics.py` (new), `test_project_commands.py`, `test_checkout_commands.py`, `test_version_sets.py`
- `docs/troubleshooting/diagnostics-and-logs.md`

The gate type-checks `tests/` too. Run `.venv/bin/python -m nox -s build` synchronously before your final push and report its result and counts. Run the website content contract check from `/workspace/301e4208ef81-ChatGPT_Codex/website` (read-only; do not edit it) with `CONTENT_DIR=/home/devcapsule/worktrees/maintenance-review npm run check:content`.

Do not build Docker images, do not start capsules or containers, and do not run `-m e2e` container tests (`tests/e2e/test_session_diagnostics.py`). The implementor runs the real-container E2E fault-injection check before and after merging your review PR, and records the evidence on PR 293 and in `maintenance` status.

## The task

Review the diff of PR 293 against its base:

    gh pr diff 293

Read first inside the diff: `devcapsule-src/devcapsule/_redaction.py`, `devcapsule-src/devcapsule/container_runtime/diagnose.py`, `devcapsule-src/devcapsule/diagnostics.py`, then `commands/project.py`, `launch/session_logs.py`, `launch/pycharm/_launcher.py`, and `docs/troubleshooting/diagnostics-and-logs.md`.

Improve it on your branch, focused on exactly three things, in this order:

1. Correctness of the new and modified lines. Questions a careful engineer would ask:
   - Session selection and filesystem safety (`diagnostics.py`): What happens if a session directory vanishes mid-scan, has a malformed or non-object `session.json`, has a non-regular file or symlink inside `sessions/<id>/`, or `--session <id>` contains path traversal (`..`, `/`) or points at a symlink? Does atomic snapshot writing (`snapshot.json`) or `--export` archive creation follow symlinks, leak temporary files on failure, or leave archive permissions wider than `0600`?
   - Redaction completeness and false-positive safety (`_redaction.py`, `diagnostics.py`, `container_runtime/diagnose.py`): Can live tokens (`/run/devcapsule-display-token`, `/run/devcapsule-console/token`, `Authorization`, `Cookie`, `X-DevCapsule-Token`, raw `?token=`, URL-encoded `path=websockify%3Ftoken%3D...`, `DEVCAPSULE_*TOKEN*`, `*_API_KEY`, `*_SECRET*`, `*_PASSWORD*`) leak through `snapshot.json`, `argv` in `/proc/<pid>/cmdline`, `docker inspect` `Config.Env`, compressed `.log.<n>.gz` files, or IDE logs when `--include-ide-logs` is passed? What if a `.log.<n>.gz` file is corrupt, truncated mid-stream, or unexpectedly huge (gzip bomb)?
   - Bounded protocol probes (`container_runtime/diagnose.py` and host loopback probes in `diagnostics.py`): Does every socket connect, send, and receive loop enforce the monotonic 2-second deadline when a peer stalls mid-header or dribbles 1 byte at a time? In `probe_websocket_rfb`, how are RFC 6455 frames handled if `websockify` sends a control frame (ping/close), a 16-bit (`126`) or 64-bit (`127`) extended payload length, an empty frame, or split TCP reads across the HTTP `101` header and first WebSocket frame? Does `probe_rfb_unix` distinguish socket-missing, connection-refused, accept-then-EOF, and accept-then-timeout (such as `SIGSTOP` on `Xvnc`)?
   - Linux `/proc` and cgroup v2 readers (`container_runtime/diagnose.py`): What happens when processes exit between `os.listdir("/proc")` and reading `stat`/`cmdline`/`fd`, when `comm` contains spaces or parentheses (for example `(Web Content)`), when socket inodes appear in `/proc/net/tcp6` or `/proc/net/unix` with varying column counts, or when cgroup v2 files (`memory.current`, `memory.max`, `memory.events`, `cpu.stat`, `pids.current`, `pids.max`) are missing or unreadable?
   - CLI and capsule routing (`commands/project.py`, `diagnostics.py`): Is `CapsuleAccess.INSPECTS` the right classification, and what happens if a user runs `devcapsule project diagnose` inside a capsule vs. on the host, passes `--include-ide-logs` without `--export`, passes `--export` pointing to an existing directory or unwritable parent, or inspects a project with zero sessions?
   - IDE log discovery and opt-in export (`diagnostics.py`, `launch/pycharm/_launcher.py`): Are IDE log trees (`idea.log*`, VSCodium `logs/`, Eclipse `.metadata/.log`) excluded from `--export` unless `--include-ide-logs` is given, bounded in size/file count, symlink-safe (refusing or skipping symlinks inside the workspace/state directory so a hostile workspace symlink cannot exfiltrate arbitrary host files into the tarball), and scrubbed before archiving?
2. Clarity of the new and modified lines. The standard is "obviously no deficiencies": clear helper boundaries, accurate docstrings and CLI help text, and diagnostic status reasons that tell an operator what succeeded or failed without ambiguity.
3. Test coverage of the new and modified lines. Add focused unit tests in `tests/test_runtime_diagnose.py` and `tests/test_diagnostics.py` where branches or edge cases above are not exercised. Every test must fail if the line it covers is broken. Do not pad.

Stay inside the PR's scope: `devcapsule project diagnose`, `devcapsule runtime diagnose-probe`, redaction, launcher session-manifest endpoint/IDE-log metadata, and the troubleshooting guide. Do not change unrelated `project` or `checkout` subcommands, web-console application routes, or container image recipes. Do not widen the CLI contract; if you believe any part of the contract is wrong, explain why in the PR body under proposals not implemented and keep your change minimal.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, the `evidence/` directory, or run `devcapsule workflow publish`.
- Do not commit the `website` submodule pointer, `.idea/` files, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Do not push to `main`, `release-0.3.0`, or any branch other than `ws-maintenance/0.3.0-diagnostics-snapshot-review`.
- Do not rebase or force-push. Do not build images or run capsules.

## Deliverable

1. Commits on `ws-maintenance/0.3.0-diagnostics-snapshot-review`, each message naming the component and the evidence, ending with your `Co-Authored-By:` line in the form `Co-Authored-By: <model name> Codex <noreply@openai.com>`, the model name being the one you actually run as. Never the words substrate, edge, gen1, or gen2.
2. Push the branch and open one pull request with:
   `gh pr create --base ws-maintenance/0.3.0-diagnostics-snapshot --head ws-maintenance/0.3.0-diagnostics-snapshot-review`
   Title: `"Correctness, clarity and coverage review of #293 (PR293.1)"`.
   The body lists each finding as: what was wrong or unclear, where, what you changed, how the test proves it. Separate "changed" from "considered and left alone, because". List the proposals you did not implement. State the gate result with counts and what was skipped. If you find nothing to change, say so in the PR body and open the PR with the added tests only, or, if there are none, say that in your final report instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or `NO PR` if you opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per sentence, about twenty words, active voice. Every claim about behavior must be backed by a test or a command you ran.

If you cannot proceed, because of a blocker like network or credentials, stop and say exactly what blocked you. Do not work around a blocker.
