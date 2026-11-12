# Review brief for Claude Code, Claude Fable 5.1: PR299.1 on the configuration home

Codex, GPT-6 Astra opened [PR #299](https://github.com/ccozianu/devcapsule/pull/299).
Its title is "One configuration home and the home commands: DEVCAPSULE_CONFIG_HOME, settings.toml, devcapsule home trust|default|show".
Its branch is `ws-maintenance/home-settings`; its base is `release-0.3.0`.
No review of this slice has run yet. Related release reviews include #293/#295 and #294/#296.
Your job is one improvement pull request against the implementation branch.
Costin Cozianu starts your session and merges the implementation PR.

## Your checkout

You are in `/home/devcapsule/worktrees/maintenance-review`, on `ws-maintenance/home-settings-review`, branched from `ws-maintenance/home-settings`.
Work only there. The human prepares and starts your session.
Do not touch `/home/devcapsule/worktrees/maintenance-impl-4`, `/workspace/301e4208ef81-ChatGPT_Codex`, or any other worktree.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`, then the work order:

```sh
git fetch origin ws-project-management/coordination
git show origin/ws-project-management/coordination:engineering-docs/work-orders/2026-10-27-configuration-home-and-the-home-commands.md
```

The order is on the project-management branch. PR #297 proposes it.
Next read PR #299's "Judgments for the human", then `engineering-docs/development/review-partner-loop.md`.
The PR body records this slice's judgments because the owner prohibits status-file edits.
Read the selected maintenance status for context, without changing it.
Then read these contracts and their implementations:

- `devcapsule-src/devcapsule/platforms.py`, especially `XdgHomes`.
- `devcapsule-src/devcapsule/configuration/storage.py`, `home.py`, `trust.py`, and `home_channels.py`.
- `devcapsule-src/devcapsule/commands/home.py`, the remaining config commands in `commands/project.py`, and `commands/_run_flow.py`.
- `devcapsule-src/devcapsule/resolution_matrix.py` and `components/interface.py` for pins, acquisition contracts, and artifacts.
- `devcapsule-src/devcapsule/runtime_configuration.py`, `notifications.py`, `persistence.py`, and `launch/pycharm/_launcher.py`.
- `devcapsule-src/devcapsule/launch/session_logs.py`, `configuration/bindings.py`, and their diagnostic and successor callers.
- `engineering-docs/decisions/product/d-0011-vendor-trust-once-per-configuration-home.md` and `docs/configuration/home.md`.

The owner's continuation adds one precise requirement. Use three release integers for the minimum-version comparison, without a runtime dependency.
Normalize launcher candidate and development suffixes. The file's minimum must be exactly `X.Y.Z`.
Commit `e1c42e1` fixes the missing runtime dependency found by the packaging test.
Commit `3d30602` fixes session-log and binding paths found by acceptance item 3.
Commit `f1c8f9ae` updates the web console contract test to check the launcher adapter after the command moves.
The mechanical rename remains separate in `7d14aa6`.
The settings commit includes the replacement storage APIs; the mechanical commit renames their callers and remaining code names.

## GitHub CLI

In every shell you run, first execute:

```sh
. /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh
```

Then `gh` is logged in to github.com as the owner's account against `ccozianu/devcapsule`.
Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists. From `devcapsule-src`, install the development dependencies once:

```sh
.venv/bin/pip install -r dev-requirements.txt -e .
```

Run unit tests and mypy from `devcapsule-src` with `PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-claude"`.
The gate type-checks `tests/` too. Run the full gate in the foreground before your final push:

```sh
PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-claude" .venv/bin/python -m nox -s build
```

Report the unit, packaging integration, web console, and documentation page counts.
Keep logs outside the pytest basetemp. The implementation PR records the implementor's gate and acceptance evidence.
The full gate passed on `f1c8f9ae`: 2,517 unit tests, 17 packaging tests, 357 web console tests, and 190 documentation pages.
The unit run also recorded 37 deselected tests, one xfailed, and one xpassed. Both mypy checks passed.

The touched files fall into these groups:

- Platform and storage: `platforms.py`, `notifications.py`, configuration storage and home models, and shared binding paths.
- Commands: new `commands/home.py`; project, terminal run, console adapters, and runtime configuration.
- Channels: new `configuration/home_channels.py`, shared trust extraction, and matrix pin access.
- Launch and diagnostics: persistence consumers, the settings mount, session logs, and successor path derivation.
- Console contract: `devcapsule-webconsole/tests/test_launcher_contract.py` checks request routing through the launcher adapter.
- Tests: new `tests/test_home.py` and `tests/test_settings.py`; existing configuration, platform, launch, trust, and packaging tests.
- Texts: new `docs/configuration/home.md`, the listed configuration/reference pages, amended D-0011, and filename references.

Do not build images or run capsules. Do not run a real console or recursive smoke session.
The build gate's unit-based web console session is required.
Acceptance item 5 uses the synthetic capsule-context tests in `tests/test_home.py`.
For optional command reproductions, use a fresh directory under `/home/devcapsule/home-evidence/`.
Set `HOME` and all XDG paths to throwaway directories there. Remove only directories you create.
The implementation used a copied compatibility fixture for `project run --print-command`; it did not build or run its declared image.

## The task

Review the diff against the release base:

```sh
gh pr diff 299
```

Start with the work order's decisions and stopping points, then `XdgHomes`, settings admission, shared channel extraction, and command dispatch.
Improve the implementation on your branch, focused on exactly three things, in this order:

1. Correctness of the new and modified lines.
   What does malformed `settings.toml` do to each home command and to `project run`?
   Can any write occur before the minimum-version refusal, including checkout recovery, prompts, and terminal acceptance?
   Are the four XDG defaults byte-identical when `DEVCAPSULE_CONFIG_HOME` is unset or empty?
   Do notification paths preserve the existing no-follow property?
   Does the matrix channel equal the channel from a lock written by the same matrix, field by field?
   What happens when two launchers write the same home concurrently?
   Can an update of either table overwrite a concurrent update, despite atomic replacement?
   Does unchanged content preserve the file, comments, and modification time?
   Do session logs, managed bindings, diagnostics, and nested launch paths select the same home?
   Do capsule reads use the mounted settings, and do mutation refusals name the outside home command?
   Does an explicitly selected writable nested home work?
   Is every deleted command spelling gone from applicable user-facing texts and parser registration?
   Are retained historical records and tests of deleted spellings the only intentional textual exceptions?
   Does the built executable perform the comparison without an undeclared dependency?
2. Clarity of the new and modified lines. The standard is "obviously no deficiencies".
3. Test coverage of the new and modified lines. Add tests where a branch is not exercised.
   Every test must fail if the line it covers is broken. Do not pad.

Stay inside this slice: one selected configuration home, its settings and commands, shared channel definitions, and their texts.
Do not redesign the configuration schemas, release process, acquisition policy, or console protocol.
Do not restore aliases or migrate the previous candidate files.
The order's decisions are settled. If a contract appears wrong, state why and keep your change minimal.
The owner retains choices about future concurrency guarantees; report any proposal separately from implemented fixes.

## What you must not do

- Do not edit any `CURRENT-STATUS.md`, `intake-dispositions.md`, changelog, or `evidence/` file. Do not run `devcapsule workflow publish`.
- Do not commit `website` or sample-project submodule pointers, `.idea/`, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Push only `ws-maintenance/home-settings-review`.
- Do not rebase, force-push, push tags, or dispatch workflows.
- Do not build images or run capsules.
- Keep the terminology constraints from the work order. Preserve compatibility fixture records.

## Deliverable

1. Make commits on `ws-maintenance/home-settings-review`. Name the component, behavior, and evidence in each message.
   Before every commit, check `git status` and `git var GIT_AUTHOR_IDENT`.
   The author must be the human, Costin Cozianu. End each message with:
   `Co-Authored-By: Claude Fable 5.1 Claude Code <noreply@anthropic.com>`.
2. Push the branch and open one pull request:

   ```sh
   git push -u origin ws-maintenance/home-settings-review
   gh pr create --base ws-maintenance/home-settings --head ws-maintenance/home-settings-review
   ```

   Title: "Correctness, clarity and coverage review of #299 (PR299.1)".
   For each finding, state what was wrong or unclear, where, what changed, and how its test proves the change.
   Separate changes from items considered and left alone, with reasons. List proposals not implemented.
   State the gate counts and exclusions. If only tests change, open the PR with those tests.
   If nothing changes, report that instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or "NO PR" with the reason.

Write the body and report at about 80% ASD-STE100. Use one fact per sentence, about twenty words, and active voice.
Back every behavior claim with a test or command you ran.
If an order stopping point, network failure, or credential blocker prevents progress, stop and name it. Do not work around it.
