# Pair Review Loop Brief & Outcome — PR #65 / PR #66 (`host-ide` VS Code Slice)

- **Workstream:** `host-ide` (`ws-host-ide/vscode-codium`, targeting `release-0.3.1`)
- **Implementor:** Codex `gpt-6-astra` (high effort, thread `01a1f549-1816-79d0-af14-84fda0521d75`) in `/home/devcapsule/worktrees/host-ide-impl` (`ws-host-ide/vscode-codium-impl`)
- **Reviewer:** Antigravity `Gemini 4 Hydrogen High` in `/home/devcapsule/worktrees/host-ide-review` (`ws-host-ide/vscode-codium-impl-review`)
- **PRs:** [PR #65](https://github.com/mycodespace-ai/devcapsule/pull/65) (`ws-host-ide/vscode-codium-impl` -> `release-0.3.1`), [PR #66](https://github.com/mycodespace-ai/devcapsule/pull/66) (`PR65.1`, review PR -> `ws-host-ide/vscode-codium-impl`)

## Findings Reviewed and Resolved (PR #66 at `8eee48c1`)

1. **Static `container_name` collision across concurrent or rapid launches (`devcapsule/commands/project.py`):** Added per-launch PID and random hex suffix when `--name` is omitted so containers do not collide while staying aligned with the `attached-container` URI.
2. **Boolean `--authorize host-ide` evaluation (`devcapsule/configuration/host_ide.py`, `devcapsule/commands/project.py`):** Added `split_surface_requested` using `normalize_authorization_value` so `--authorize host-ide false` / `none` no longer sets `split_surface=True` or suppresses container VS Code gating.
3. **`ArtifactUnavailable` fallback drops split surface (`devcapsule/configuration/host_ide.py`, `devcapsule/commands/project.py`):** Preserved `source_selected` (retaining `vscode` in components) across `omit_unavailable_optional` and re-applied `apply_host_ide_surface` so optional artifact degradation keeps `xfce4-terminal` instead of crashing on missing `vscode` provider or reverting to container VS Code.
4. **Lexicographic managed VS Code version sort (`devcapsule/host_ide.py`):** Replaced path string sorting with numeric `_installed_version_key` so e.g. `1.10.0` beats `1.9.0`.
5. **`unverified-combinations` overwrite (`devcapsule/configuration/host_ide.py`):** Merged and deduplicated semicolon-separated notes across base and terminal lock pins.

## Round 1 Pushback & Resolution (`5eb9f317`, merged at `717ce587`)

- **Implementor pushback ([comment](https://github.com/mycodespace-ai/devcapsule/pull/66#issuecomment-7021026022)):** Flagged `test_omitting_unavailable_optional_tool_preserves_host_ide_terminal` in `tests/unit/devcapsule/configuration/test_host_ide.py` for calling `omit_unavailable_optional` (which implicitly read `settings.toml` via `load_settings()`) without covering the CLI retry wiring in `commands/project.py`, and asked to parameterize `test_split_surface_flag_distinguishes_grant_from_denial` into single-call cases.
- **Resolution ([reply](https://github.com/mycodespace-ai/devcapsule/pull/66#issuecomment-7021135718)):** Replaced the unit test with pure value-based `test_apply_host_ide_surface_updates_resolved_component_without_mutating_source` (zero home I/O), parameterized `test_split_surface_flag_distinguishes_grant_from_denial`, and added subprocess integration test `test_optional_artifact_unavailable_retry_keeps_split_surface` exercising the real `ArtifactUnavailable` retry path in `devcapsule.cli.main` with private home and fake `docker`/`code`.
- **Acceptance & Merge ([comment](https://github.com/mycodespace-ai/devcapsule/pull/66#issuecomment-7021162428)):** Accepted at `5eb9f317` after 1 round and merged into `ws-host-ide/vscode-codium-impl` at `717ce587`.

## Merged-Branch Verification (`717ce587`)

- Focused units (`test_host_ide.py`, `configuration/test_host_ide.py`): `44 passed`
- Isolation probe (malformed/empty/missing `DEVCAPSULE_CONFIG_HOME`): `7` cases passed (`PROBE_OK`)
- Merged `nox -s build`: `3477 passed, 1 skipped, 288 deselected, 1 xfailed, 1 xpassed`, mypy (`377` files) `0` issues, `validate_unittests_follow_conventions.py` `0` breaches, local PEX smoke passed, docs contract (`249` pages) passed
- `nox -s webconsole`: mypy (`9` files) `0` issues, `474 passed`
- Host-IDE CLI integration (`tests/integration/test_host_ide_cli.py`): `21 passed`
- Not executed in capsule sandbox: real host VS Code GUI attach (`code` + `ms-vscode-remote.remote-containers`) against a live Docker container.
