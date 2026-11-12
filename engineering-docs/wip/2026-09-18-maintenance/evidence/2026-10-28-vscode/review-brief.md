# Review brief for Antigravity, Gemini 4 Argon (High): PR301.1 on VS Code as an IDE surface

Claude Code, Claude Fable 5.1 opened [PR #301](https://github.com/ccozianu/devcapsule/pull/301),
taking over an implementation Antigravity, Gemini 4 Argon (High) wrote in a session cut short by a power outage.
Its title is "VS Code as an IDE surface: a second provider of frontend-ide and its own vscode-ide, acquired from Microsoft under the vscode-download channel".
Its branch is `ws-maintenance/0.3.0-vscode`; its base is `release-0.3.0`.
No review of this slice has run yet. Related release reviews of this cycle are #293/#295, #294/#296 and #299/#300.
Your job is one improvement pull request against the implementation branch.
Costin Cozianu starts your session and merges the implementation PR.

## Your checkout

You are in `/home/devcapsule/worktrees/maintenance-review`, on `ws-maintenance/0.3.0-vscode-review`, branched from `ws-maintenance/0.3.0-vscode`.
Work only there. The human prepares and starts your session.
Do not touch `/home/devcapsule/worktrees/vscode-ide`, `/home/devcapsule/worktrees/vscode-e2e-tmp`, `/workspace/301e4208ef81-ChatGPT_Codex`, or any other worktree.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`, then the scope decision:

```sh
git fetch origin main
git show origin/main:engineering-docs/wip/2026-08-09-project-management/2026-10-27-decision-release-0-3-0-scope-at-rc8.md
```

Item 3 of that decision orders VS Code into 0.3.0 as a second provider of `frontend-ide`, VSCodium the default, under an acquisition contract and a trust channel of D-0011.
Next read PR #301's "Judgments for the human", then `engineering-docs/development/review-partner-loop.md`.
Read the selected maintenance status, `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md`, for context, without changing it.
Then read these contracts and their implementations:

- `devcapsule-src/devcapsule/components/interface.py`, then `components/codium.py` beside the new `components/vscode.py`, and `components/catalog.py`.
- `devcapsule-src/devcapsule/resolution_matrix.py`: `canonical_name`, the `vscode` pin, the capability table and the verified edges.
- `devcapsule-src/devcapsule/configuration/capability_selection.py`, `usable_lock`; `configuration/trust.py`, `component_channel`; `configuration/home_channels.py`; `configuration/authorization.py` where the acquisition contract becomes a decision.
- `devcapsule-src/devcapsule/materialization.py`, `SURFACE_MATERIALIZATIONS` and `normalize_archive_directory`; `container_runtime/components/vscode.py`; `components/discovery.py`.
- `devcapsule-src/devcapsule/commands/project.py`, `ConfigIdeCommand` and `ConfigUseCommand`; `commands/_run_flow.py` for the non-interactive refusal.
- `devcapsule-src/tests/e2e/ide_session.py`, the surface table and `initialize_project`.
- `engineering-docs/decisions/product/d-0011-vendor-trust-once-per-configuration-home.md`, `docs/everyday-development/ides-and-terminals.md`, `docs/configuration/home.md`.

## GitHub CLI

In every shell you run, first execute:

```sh
. /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh
```

Then `gh` is logged in to github.com as the owner's account against `ccozianu/devcapsule`.
Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists with the development dependencies installed.
Run unit tests and mypy from `devcapsule-src` with `PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-antigravity"`.
The gate type-checks `tests/` too. Run the full gate in the foreground before your final push:

```sh
PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-antigravity" .venv/bin/python -m nox -s build
```

Report the unit, packaging integration, web console, and documentation page counts.
Keep logs outside the pytest basetemp.
On the implementation tip, 108 focused tests in `test_vscode_component.py`, `test_resolution_matrix.py` and `test_console_channel.py` pass and mypy is clean over 260 files; the full gate has not run yet.

The touched files fall into these groups:

- Catalog and matrix: new `components/vscode.py`; `components/catalog.py`, `components/discovery.py`, `resolution_matrix.py`, `materialization.py`.
- Configuration: `configuration/capability_selection.py`, `trust.py`, `operations.py`, `storage.py`; `commands/project.py`.
- Status: `component-status/policy-v1.json`.
- Tests: new `tests/test_vscode_component.py`; `tests/test_resolution_matrix.py`, `tests/test_console_channel.py`; the golden locks, `vscode-node.lock` new; `tests/e2e/ide_session.py`.
- Texts: `docs/everyday-development/ides-and-terminals.md`, `docs/configuration/{capabilities,home,software-approvals}.md`, `docs/reference/{cli,configuration-nodes}.md`, `docs/updates/{component-freshness,component-upgrades}.md`, `docs/your-project/existing-repository.md`.

Do not build images or run capsules. Do not download Visual Studio Code. Do not run the IDE smoke.
The first pair runs the recorded IDE smoke of the `vscode` surface from a temporary clone inside a capsule and records it in PR #301 and the status file.
For optional command reproductions, use a fresh directory under `/home/devcapsule/vscode-review-evidence/`.
Set `DEVCAPSULE_CONFIG_HOME` to a throwaway directory there, so no real home is written. Remove only directories you create.

## The task

Review the diff against the release base:

```sh
gh pr diff 301
```

Start with the component definition and the matrix, then the trust channel, then selection and the commands.
Improve the implementation on your branch, focused on exactly three things, in this order:

1. Correctness of the new and modified lines.
   Does `canonical_name` stay unambiguous: `vscode` names `vscode-ide`, `codium` names `frontend-ide`, and a name in two capabilities' providers without a sole listing is refused with the supported list?
   Does `usable_lock` keep exactly the pinned surface and its required closure, refuse a provider missing from the catalog or from the lock by name, and leave a lock without a pinned surface as before?
   Does `component_channel` establish a channel only for a component with an acquisition contract, and only from HTTPS, credential-free origins with a 64-hex SHA-256; does a tampered or incomplete lock establish none, for the vscode table and for the per-file tables of the agents?
   Does the channel from the matrix equal the channel from a lock the same matrix wrote, field by field, so a home acceptance covers the launch?
   Does a checkout's `vscode-download = false` override home trust, and does a non-interactive launch stop before any write?
   Does `locked_artifacts` refuse every tampered acquisition field, and does `parse_locked_environment` carry the url and sha256 the materialization downloads and verifies?
   Does the archive, whose top-level directory is `VSCode-linux-x64/`, normalize to a root holding `code`, `bin/code` and `chrome-sandbox`, with setuid stripped, and does the runtime plan put the Electron binary in the foreground with `--no-sandbox`?
   Does `VscodeDiscovery` refuse a non-stable `productVersion`, a non-tarball or non-HTTPS url, a malformed `sha256hash`, and map `linux-arm64` and unknown platforms without a surprise?
   Does `config ide` print the provider a checkout choice or a project recommendation selects, and does `config use frontend-ide default` remove the choice?
   Does `config use` on a single-provider capability still refuse as before, in the command and through the console channel?
   Are the IDE lists in every user-facing text in one order, and does the documentation say when the download happens and what it consents to?
   Does the e2e surface's consent reach `project init` as one `--authorize vscode-download true` and nothing else?
2. Clarity of the new and modified lines. The standard is "obviously no deficiencies".
3. Test coverage of the new and modified lines. Add tests where a branch is not exercised.
   Every test must fail if the line it covers is broken. Do not pad.

Stay inside this slice: the `vscode` component, its pin, channel, selection, commands, smoke surface and texts.
Do not redesign the acquisition policy, D-0011, the matrix's shape, the materialization recipe or the console protocol.
Do not change VSCodium's defaults. Do not add or change pins of other components.
If a contract appears wrong, state why and keep your change minimal.
The owner retains the judgments listed in PR #301; report any proposal separately from implemented fixes.

## What you must not do

- Do not edit any `CURRENT-STATUS.md`, `intake-dispositions.md`, changelog, or `evidence/` file. Do not run `devcapsule workflow publish`.
- Do not commit `website` or sample-project submodule pointers, `.idea/`, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Push only `ws-maintenance/0.3.0-vscode-review`.
- Do not rebase, force-push, push tags, or dispatch workflows.
- Do not build images, run capsules, or download Visual Studio Code.

## Deliverable

1. Make commits on `ws-maintenance/0.3.0-vscode-review`. Name the component, behavior, and evidence in each message.
   Before every commit, check `git status` and `git var GIT_AUTHOR_IDENT`.
   The author must be the human, Costin Cozianu. End each message with:
   `Co-Authored-By: Gemini 4 Argon (High) Antigravity <noreply@google.com>`.
2. Push the branch and open one pull request:

   ```sh
   git push -u origin ws-maintenance/0.3.0-vscode-review
   gh pr create --base ws-maintenance/0.3.0-vscode --head ws-maintenance/0.3.0-vscode-review
   ```

   Title: "Correctness, clarity and coverage review of #301 (PR301.1)".
   For each finding, state what was wrong or unclear, where, what changed, and how its test proves the change.
   Separate changes from items considered and left alone, with reasons. List proposals not implemented.
   State the gate counts and exclusions. If only tests change, open the PR with those tests.
   If nothing changes, report that instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or "NO PR" with the reason.

Write the body and report at about 80% ASD-STE100. Use one fact per sentence, about twenty words, and active voice.
Back every behavior claim with a test or command you ran.
If a network failure or credential blocker prevents progress, stop and name it. Do not work around it.
