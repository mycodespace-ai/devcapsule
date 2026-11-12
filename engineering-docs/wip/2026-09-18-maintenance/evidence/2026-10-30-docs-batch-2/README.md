# User Documentation 0.3.0 CLI Alignment — Batch 2 Verification Ledger

Workstream: `maintenance`
Work order: [`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
Slice branch: `ws-maintenance/0.3.0-docs-batch-2-configuration` (target `release-0.3.0`, [PR #321](https://github.com/ccozianu/devcapsule/pull/321))
Implementor pair: `Antigravity (Gemini 4 Argon (High))`
Review partner: `Codex (gpt-6-astra)` ([PR #322](https://github.com/ccozianu/devcapsule/pull/322), accepted at `a082a710` without a revision round and merged at `b7849132`)

## Scope (10 `docs/configuration/*.md` files; 1 `status: planned` stub retired)

| # | File | Stub retired? | Key 0.3.0 CLI & prose changes | Verification status |
|---|---|---|---|---|
| 1 | `docs/configuration/index.md` | No | Added `.devcapsule/devcapsule.<platform>.lock`, tightened three-record overview prose, and expanded `## Guides in this section` to link all 9 sibling `docs/configuration/` guides (`ide-preferences.md`, `resource-limits.md`, `local-base.md`, `extra-tools.md` were missing). | Verified against `docs/configuration/` file list and contract checks |
| 2 | `docs/configuration/project-versus-personal.md` | No | Documented component-name IDE support (`pycharm`, `codium`, `vscode`, `intellij`, `eclipse`, `rider`), `config bind` / `state adopt` / `config unbind` links to `ide-preferences.md`, and `$DEVCAPSULE_CONFIG_HOME/docker-arguments/` while preserving `#when-the-project-changes` and `#from-the-console` anchors. | Verified against `commands/project.py` and website anchor check |
| 3 | `docs/configuration/home.md` | No | Removed leaked internal `0.3.0-rc` notes, clarified `minimum-devcapsule` read/write refusal and release-suffix stripping, documented `DEVCAPSULE_CONFIG_HOME` disabling in-capsule mounted-settings fallback, and tightened prose. | Verified against `commands/home.py` and `configuration/storage.py` |
| 4 | `docs/configuration/inspect.md` | No | Clarified `project info --json` (`schema-version: 1`, linked to `../reference/project-info.md`), `config check` (`--manifest`/`--lock` candidate mode vs. host exit `3` vs. in-capsule note), `config show --json` (`schema-version: 2` vs. legacy channel-less `1`), and `versions show --json` (`schema-version: 1`). | Verified against `commands/project.py`, `listing.py`, and `runtime_configuration.py` |
| 5 | `docs/configuration/extra-tools.md` | No | Clarified `/opt/xtras -> /home/devcapsule/xtras` symlink, `PATH` prepending, `config bind home` and `state adopt --from PATH home` sharing semantics, and `project info` `xtras` entry (`<home backing>/xtras`). | Verified against `materialization.py` and `project_information.py` |
| 6 | `docs/configuration/ide-preferences.md` | **Yes** (`status: planned` removed) | Authored complete `0.3.0` page covering all declared IDE slots (`pycharm`, `intellij`, `rider`, `codium`, `vscode`, `eclipse`), per-checkout XDG / `DEVCAPSULE_CONFIG_HOME` backing paths, `config bind` vs. `state adopt` vs. `init --bind` vs. `config unbind` (direct mount, no file copy), `concurrent = false` lock hazards, and Git-shared vs. personal settings. | Verified against `components/jetbrains.py`, `codium.py`, `vscode.py`, `eclipse.py`, `bindings.py`, and `commands/project.py` |
| 7 | `docs/configuration/resource-limits.md` | No | Replaced `~/.local/bin/devcapsule` command prefixes with `devcapsule`, formatted 4-level precedence list, documented accepted memory units and canonical binary normalization, listed all 4 declared value types (`string`, `integer`, `boolean`, `memory-size`) plus `init --set`, and tightened legacy `runtime.memory-limit` migration prose. | Verified against `configuration/values.py` and `commands/project.py` |
| 8 | `docs/configuration/local-base.md` | No | Replaced `~/.local/bin/devcapsule` prefixes with `devcapsule`, explicitly noted that `images build --type base` requires `--tag <local-name>` when copying the launcher's printed build hint, fixed `an capability minimum` typo, and tightened prose. | Verified against `commands/_launcher.py` and `commands/images.py` |
| 9 | `docs/configuration/software-approvals.md` | No | Corrected `antigravity-cli` origin description from `"a bare Cloud Run host"` to shared Google Cloud Storage (`https://storage.googleapis.com`) with the exact deployment/credentials trust note from `trust.py`, distinguished `project config trust list [--json]` from `home trust list`, removed `~/.local/bin/` prefixes, and tightened prose. | Verified against `configuration/trust.py`, `home_channels.py`, and `commands/home.py` |
| 10 | `docs/configuration/capabilities.md` | No | Documented `--unverified` (`init`, `require`, `offer`, `drop`, `ide`, `add`, `omit`, `restore`, `use`; absent on `recommend`), component-name IDE support, and replaced leaked internal `"Candidate 4"` notes with adopter-facing `{{tag}}` schema-1/schema-2 compatibility guidance while preserving `#a-required-ide`. | Verified against `commands/project.py` and `configuration/manifest_schemas.py` |

## Validation Gate (Post-Merge of PR #322 at `b7849132`)

- `git diff --name-only origin/release-0.3.0 -- docs/`: 10 files (`<= 10` batch limit satisfied; `docs/versions.yaml` untouched).
- `git grep -n '^status: planned' -- docs/configuration/`: 0 matches (`ide-preferences.md` stub retired).
- `(cd devcapsule-src && .venv/bin/python -m nox -s docs-contract)`: passed (`192` pages including `18` aliases).
- `./scripts/website.sh build && ./scripts/website.sh check`: passed (`23` website tests, `196` HTML pages, `14,425` local links/assets/anchors).
- `(cd devcapsule-src && .venv/bin/pytest -q -k "release_docs")`: passed (`92` tests).
- `(cd devcapsule-src && .venv/bin/python -m nox -s smoke)`: passed.
