# Batch 1 Verification Ledger: `docs/reference/`, `docs/updates/`, `docs/troubleshooting/`

Date: 2026-10-30
Workstream: `maintenance`
Slice branch: `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting` (from `release-0.3.0` at `9eb500da`)
Work order: [`2026-10-30-user-docs-0-3-0-cli-alignment.md`](../../../../work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
Implementor: Antigravity (`Gemini 4 Argon (High)`)
Review partner: Codex (`gpt-6-astra`)

## Batch 1 File-by-File Ledger (10 `docs/*.md` files)

| # | File | Prior state | Live `0.3.0` CLI / source checks performed | `0.3.0` alignment and prose changes |
|---|---|---|---|---|
| 1 | `docs/reference/cli.md` | Published (`updated: 2026-10-28`) | `devcapsule --help`, `project --help`, `project config --help`, `project state adopt --help`, `project versions --help`, `home --help`, `images --help`, `workflow --help` | Added missing `diagnose` subcommand to `devcapsule project` and *Other project commands*; documented `--unverified` on `config ide\|add\|restore\|use` and component-name IDE selection; matched exact `state adopt --from SOURCE SLOT` and `versions` signatures; kept `#home-and-development-commands` anchor; tightened prose. |
| 2 | `docs/reference/configuration-nodes.md` | Published (`updated: 2026-10-24`) | Probed `KNOWN_COMPONENTS` (`runtime_template`, `acquisition`, `secret_inputs`) and `project config --help` | Added `config unbind`; completed bindings table with `intellij/*`, `rider/*`, `codium/*`, `vscode/*`, `eclipse/workspace`, `claude-code/home`, `antigravity-cli/home`, and `antigravity-cli/gemini-api-key`; clarified checkout approvals vs. home channel trust. |
| 3 | `docs/reference/project-info.md` | `status: planned` stub | Read `devcapsule/project_information.py`; ran `devcapsule project info` and `project info --json` in both host-selection and running-capsule modes | Authored complete `0.3.0` reference page: command options, host vs. capsule context differences (`running-selection`, `next-launch-components`, `selection-changed`, `PATH`, backing mounts), `schema-version: 1` JSON fields, fixed variable allowlist / secret redaction, and `persistence` vs. `temporary` slots; removed `status: planned`. |
| 4 | `docs/updates/component-freshness.md` | Published (`updated: 2026-10-28`) | Verified `component_status.py` and component adapters (including `vscode`) | Preserved `aliases` and link to `component-upgrades.md#preview-then-choose`; rewrote leaked internal PR/operator prose into direct adopter prose. |
| 5 | `docs/updates/component-upgrades.md` | Published (`updated: 2026-10-28`) | Probed `project versions --help`, `home trust --help`, `XdgHomes.from_environment` (`DEVCAPSULE_CONFIG_HOME`) | Updated version-set state root (`~/.local/state/devcapsule/version-sets` or `$DEVCAPSULE_CONFIG_HOME/state/version-sets`), separated home channel trust (`home trust accept`) from per-checkout versioned consent (`config approve` / `--authorize`), preserved `#preview-then-choose` and `aliases`, and removed repetitive fixture prose. |
| 6 | `docs/updates/launcher-updates.md` | Published (`updated: 2026-10-24`) | Checked `commands/_upgrade_prompt.py` and `configuration/storage.py` (`minimum-devcapsule`) | Clarified single-executable replacement, preservation of locks, checkout records, and `settings.toml` (`[defaults]` and `[trust.channels]`), and `minimum-devcapsule` protection against older launchers. |
| 7 | `docs/updates/supported-versions.md` | Published (`updated: 2026-09-28`) | Checked `website/CONTRACT.md` and `docs/README.md` | Corrected misleading `[versions index](../README.md)` link text (`../README.md` is the release's documentation home; the top-bar version switcher opens *all versions*); linked configuration home and tightened prose. |
| 8 | `docs/troubleshooting/first-session.md` | Published (`updated: 2026-09-28`) | Probed `project init` error paths (`</dev/null`), retired flags, `--set` without `--ide`, re-init on existing manifest, and `validate_settings` `minimum-devcapsule` error | Replaced `0.2.15` strings (`unknown configuration name`, `already fully initialized`) with `0.3.0` messages (`The embedded resolution matrix does not know '...'`, `... is retired; use '...'`, `--set <name> needs the checkout's IDE first`, `Honored existing .../devcapsule.toml`, `DevCapsule home ... requires DevCapsule X.Y.Z`) and added `devcapsule project diagnose [--export]`. |
| 9 | `docs/troubleshooting/diagnostics-and-logs.md` | Published (`updated: 2026-10-27`) | Checked `diagnostics.py` and `launch/session_logs.py` (`XdgHomes`) | Added `$DEVCAPSULE_CONFIG_HOME/state/projects/by-path/...` path note, named PyCharm/IntelliJ IDEA/Rider and both VSCodium and Visual Studio Code `logs/` directories, preserved `#browser-evidence` and `#when-asking-for-help`, and tightened prose. |
| 10 | `docs/troubleshooting/cleanup-and-uninstall.md` | `status: planned` stub | Checked `commands/home.py`, `commands/images.py` (`images list --include-legacy`), `materialization.py` (`artifacts/`), `platforms.py` (`XdgHomes`), and `launch/pycharm/_launcher.py` (`--rm`) | Authored complete `0.3.0` page covering storage inspection (`home show`, `project list`, `project info`, `images list --include-legacy`), removing unused Docker images (`docker image rm` and offline `versions rollback` caveat), clearing reconstructable caches, log retention (`DEVCAPSULE_LOG_BUDGET`), resetting or removing one checkout, and full uninstall without inventing deferred `0.3.1` cleanup commands; removed `status: planned`. |

## Pre-Review Validation Summary

- `git diff --name-only origin/release-0.3.0 -- docs/` lists 10 `.md` files and does not touch `docs/versions.yaml`.
- `git grep -n '^status: planned' -- docs/reference docs/updates docs/troubleshooting` returns zero matches (`2` stubs retired: `docs/reference/project-info.md`, `docs/troubleshooting/cleanup-and-uninstall.md`).
- `(cd devcapsule-src && .venv/bin/python -m nox -s docs-contract)`: passed (`192 pages including 18 aliases; devel (0.3.0): 49 pages`).
- `./scripts/website.sh build` and `./scripts/website.sh check`: passed (`23/23` website tests, `196` HTML pages, `14,437` local links/assets/anchors).
- `(cd devcapsule-src && PYTEST_ADDOPTS="--basetemp=/var/tmp/dc-docs-batch1/pytest" .venv/bin/python -m pytest -q -k release_docs)`: `92 passed`.

## Pair Review Sign-Off (`Codex / gpt-6-astra`, PR #320 -> PR #319)

- Review brief: [`review-brief.md`](review-brief.md).
- Reviewer PR: [PR #320](https://github.com/ccozianu/devcapsule/pull/320) (`71243a0c`), accepted without a revision round and merged into `ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting` at `0c0006c4`.
- Scope audited: all `10` Batch 1 `docs/*.md` files in full plus `106` CLI `--help` and scratch `DEVCAPSULE_CONFIG_HOME` invocations (`supported-versions.md` confirmed accurate as written; `9` files tightened with `13` source-verified corrections).
- Unimplemented CLI proposals filed as [`2026-10-30-config-show-json-help-and-retired-home-command-hints.md`](../../../../bugs/devcapsule/2026-10-30-config-show-json-help-and-retired-home-command-hints.md) (`STABLE_JSON_HELP` schema-1 help string on schema-2 `config show --json`, and missing replacement hints on `project config default` and mutating `project config trust`).
- Post-merge validation: `nox -s docs-contract` (`192` pages), `./scripts/website.sh build` and `./scripts/website.sh check` (`23` website tests, `196` HTML pages, `14,441` local links/assets/anchors), and `nox -s smoke` + `release_docs` unit tests passed.
