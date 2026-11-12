# User Documentation 0.3.0 CLI Alignment — Batch 3 Verification Ledger

Workstream: `maintenance`
Work order: [`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
Slice branch: `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment` (target `release-0.3.0`)
Implementor pair: `Antigravity (Gemini 4 Argon (High))`
Review partner: `Codex (gpt-6-astra)`

## Scope (10 `docs/*.md` files across `docs/README.md`, `getting-started/`, `your-project/`, and `containment/`; 2 `status: planned` stubs retired)

| # | File | Stub retired? | Key 0.3.0 CLI & prose changes | Verification status |
|---|---|---|---|---|
| 1 | `docs/README.md` | No | Preserved `role: overview`, retired the obsolete `"Pages marked coming soon..."` paragraph, updated section summaries to cover web console, component freshness, cleanup, and `reference/cli.md`, and tightened adopter prose. | Verified against `docs/` section tree and `website/CONTRACT.md` |
| 2 | `docs/getting-started/install.md` | No | Preserved `#check-your-computer`, clarified `.pex` system-Python (`3.10+`) usage without host virtualenvs, and explained adding `$HOME/.local/bin` to `PATH` alongside `~/.local/bin/devcapsule` examples. | Verified against `{{download_url}}`/`{{tag}}`/`{{release_url}}` placeholders and `website.sh check` |
| 3 | `docs/getting-started/first-session.md` | No | Preserved `role: getting-started`, `/docs/guides/first-session/` alias, and `#1-make-a-first-workspace`; aligned interactive `project init` prompt wording (`antigravity-agent` `[yes]` default, `[none]` host recommendations, `[default]` base consent), documented both desktop and recipe-11+ web console loopback URLs, and fixed misleading `"running processes restart"` claim. | Verified against interactive `pty` probe of `project init --require node --ide frontend-ide` and `_launcher.py` |
| 4 | `docs/getting-started/stop-and-come-back.md` | No | Clarified IDE exit vs. single/double `Ctrl+C` shutdown, desktop + web console tab behavior, and corrected misleading `"Processes you had running, servers or watchers, restart"` wording to state that container processes stop on exit and must be started again. | Verified against `_launcher.py` and `sessions/what-persists.md` |
| 5 | `docs/your-project/existing-repository.md` | No | Preserved `role: your-project` and `/docs/guides/your-project/` alias; added `eclipse-ide` and `dotnet-ide` (`rider`) rows to the stack/IDE table, clarified `project checkout register NAME` and `config show`/`config check` non-mutating behavior, and replaced `~/.local/bin/` prefixes with `devcapsule`. | Verified against `commands/project.py` and `resolution_matrix.py` |
| 6 | `docs/your-project/new-project.md` | No | Expanded stack/IDE options (`python-ide`, `java-ide`, `eclipse-ide`, `dotnet-ide`, component-name IDE aliases), documented `antigravity-agent` default prompt vs. `init --with` / `config add`, and replaced `~/.local/bin/` prefixes. | Verified against `commands/project.py` and `operations.py` |
| 7 | `docs/your-project/declare-needs.md` | **Yes** (`status: planned` removed) | Authored complete `0.3.0` page covering `.devcapsule/devcapsule.toml` (schema `2`) and `.devcapsule/devcapsule.<platform>.lock`, all 17 catalog capabilities by category, `require` (`NAME>=VERSION`) vs. `offer` vs. `drop`, `require/offer env`, `[configuration.values]`, recommendations vs. permissions, `init --regenerate`, and `config check --manifest --lock`. | Verified against `resolution_matrix.py`, `owner_commands.py`, `values.py`, and `commands/project.py` |
| 8 | `docs/your-project/services-and-ports.md` | **Yes** (`status: planned` removed) | Authored complete `0.3.0` page covering reaching capsule web servers (in-capsule browser/Playwright, `--publish=127.0.0.1:PORT:PORT` via `run --` or `docker-args set` with `0.0.0.0` bind, and `authorize network host`) and running databases/services (host services + `host.docker.internal:host-gateway` + `postgresql-client`/`env set`, `docker-daemon host-socket` sibling-container caveats, and persistent in-capsule SQLite/DuckDB paths). | Verified against `_launcher.py` (`LAUNCHER_OWNED_DOCKER_OPTIONS`), `docker_arguments.py`, and `authorization.py` |
| 9 | `docs/containment/the-boundary.md` | No | Preserved `role: containment`; added recipe-11+ web console loopback port and read-only `settings.toml` mount to default boundary, listed `vscode-download`, `claude-code-download`, and `antigravity-download` explicitly, noted `--cap-drop ALL` / `no-new-privileges`, and tightened prose. | Verified against `_launcher.py` and `authorization.py` |
| 10 | `docs/containment/granting-and-withdrawing.md` | No | Replaced `~/.local/bin/` prefixes, distinguished `config deny` (the 5 host-access nodes only) from `config authorize <vendor>-download false`, documented `default` and `none` keywords across every authorization node, and added vendor download rows to the reference table. | Verified against `commands/project.py` (`ConfigDenyCommand`) and `authorization.py` |

## Pair Review (`PR323.1` / PR #324)

- **Review brief:** [`review-brief.md`](review-brief.md)
- **Review PR:** [PR #324](https://github.com/ccozianu/devcapsule/pull/324) (`Codex + gpt-6-astra`, commit `f218a6d5`), accepted without a revision round (`#issuecomment-6520810424`) and merged at `18728ce8`.
- **Accepted improvements (all 10 files audited and refined):**
  1. `docs/getting-started/install.md`: removed host system-Python `3.10+` prerequisite because the release SCIE executable bundles its own standalone Python runtime (`devcapsule-src/scripts/build-pex.sh:279`).
  2. `docs/README.md` & `docs/containment/the-boundary.md`: replaced broad `"touches nothing else"` wording with exact default mounts and Docker bridge outbound scope (`_launcher.py:1283-1335`), and removed `"the version in this page's URL"` (`website/CONTRACT.md:239`).
  3. `docs/containment/the-boundary.md` & `docs/your-project/existing-repository.md`: clarified writable `.git` access, rootful `docker-daemon host-socket` host control (`_launcher.py:2201`), and `development-sudo` removing `--cap-drop ALL` / `--security-opt no-new-privileges` inside the container (`_launcher.py:1706-1715`).
  4. `docs/containment/the-boundary.md` & `docs/containment/granting-and-withdrawing.md`: restricted one-run `project run --authorize` to the 5 host-access nodes (`_run_flow.py:153-156`), documented read-only checkout/context and session-log/console-request mounts (`_launcher.py:1410, 1489`), and noted `config docker-args list` inspection (`_launcher.py:1628`).
  5. `docs/containment/granting-and-withdrawing.md`: clarified that `authorize network default` grants `host` and `authorize docker-daemon default` grants `host-socket` (`authorization.py:54-68, 333`), separated `default` from deny values, and noted component-declared `--shm-size` (`_launcher.py:1633`).
  6. `docs/getting-started/first-session.md`: distinguished `--ide codium` from `--ide vscode` (`vscode-download` consent) and clarified startup link printing/browser opening (`_launcher.py:334`).
  7. `docs/getting-started/stop-and-come-back.md`: clarified second-`Ctrl+C` stop-confirmation behavior (`_launcher.py:486`) and prompts caused by unanswered software consent or forgotten answers (`_run_flow.py:180`, `project.py:1165`).
  8. `docs/your-project/existing-repository.md` & `docs/your-project/new-project.md`: documented separate per-checkout IDE/added-capability pins (`operations.py:385`), `config show`/`config check`/`run` exit statuses (`2` vs. `3`), and `config add codex-agent`.
  9. `docs/your-project/declare-needs.md`: added the schema-2 manifest table reference (`manifest_schemas.py:57`), `drop env`, `--preview`, `recommend cpus`, `[configuration.values]` defaults (`values.py:84`), `postgresql-client` base supply, `init --regenerate` (no `--force`), and candidate-only `config check --manifest --lock` semantics.
  10. `docs/your-project/services-and-ports.md`: aligned published/example port `3000`, clarified `docker-args set`/`clear` shared storage with `config env` (`project.py:986`, `docker_arguments.py:110`), separated `network host` vs. `bridge` `POSTGRES_HOST` examples, and added `run --authorize network host` vs. `deny`/`forget`.
- **Proposals not implemented:**
  - Narrow `"Everything you would miss"` in `docs/sessions/what-persists.md:8` to explicitly mounted paths — queued for Batch 5 (`docs/sessions/`).
  - No production Python CLI defects raised in this batch.

## Post-Merge Validation Gate (`18728ce8`)

- `git diff --name-only origin/release-0.3.0 -- docs/`: 10 files (`<= 10` batch limit satisfied; `docs/versions.yaml` untouched).
- `git grep -n '^status: planned' -- docs/README.md docs/getting-started/ docs/your-project/ docs/containment/`: 0 matches (`declare-needs.md` and `services-and-ports.md` stubs retired).
- `(cd devcapsule-src && .venv/bin/python -m nox -s docs-contract)`: passed (`192` pages including `18` aliases).
- `./scripts/website.sh build && ./scripts/website.sh check`: passed (`23` website tests, `196` HTML pages, `14,449` local links/assets/anchors).
- `(cd devcapsule-src && .venv/bin/pytest -q -k "release_docs")`: `92 passed`.
- `(cd devcapsule-src && .venv/bin/python -m nox -s smoke)`: passed.
