# Evidence: 0.3.0 User Documentation CLI Alignment — Batch 5 (`sessions/`, `collaboration/`, `platforms/`)

## Scope

This slice implements Batch 5 (the final batch) of [2026-10-30-user-docs-0-3-0-cli-alignment.md](../../../../work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md) on `release-0.3.0` under the `maintenance` workstream. It updates 9 `docs/*.md` files (`<= 10` per pull request) and retires the final 2 `status: planned` stubs:

1. `docs/sessions/start-stop-reconnect.md`: replaces the `~/.local/bin/devcapsule` prefix with `devcapsule`, documents both per-run loopback links (contained desktop and recipe-11+ web console), clarifies `Ctrl+C` first-interrupt wait vs second-interrupt exit, and fixes the stale host `project info` container-name statement (`docker ps` / `--name NAME` on the host, `$DEVCAPSULE_CONTAINER_NAME` / `project info` inside the capsule).
2. `docs/sessions/what-persists.md`: narrows container persistence claims to explicitly mounted paths (`project` + declared slots), aligns `~/.gemini` credential storage with `antigravity_cli.py`, and links `config bind` / `state adopt` in `ide-preferences.md`.
3. `docs/sessions/several-projects.md` (`status: planned` retired): authors complete 0.3.0 guidance for running distinct projects concurrently, registering additional checkouts or `git worktree` directories with `devcapsule project checkout register NAME`, avoiding concurrent launches on one checkout or shared `concurrent = false` IDE slot, naming containers with `--name`, and sizing memory/CPU limits.
4. `docs/sessions/another-machine.md` (`status: planned` retired): authors complete 0.3.0 guidance distinguishing Git-committed state from host-local settings/state, clean setup on a second machine, and safe adoption of portable preferences via `devcapsule project state adopt --from PATH <slot>` without copying raw `*.checkout.toml` records.
5. `docs/sessions/web-console.md`: updates the page for the 0.3.0 configuration channel (`devcapsule/configuration/console_channel.py` and `devcapsule_webconsole/configuration.py`), distinguishing immediately recorded next-launch choices from deferred widenings confirmed via `project run` or `devcapsule project config console list|apply|discard`, and clarifying launch-time `listing.json` behavior.
6. `docs/collaboration/working-in-workstreams.md` (`aliases` preserved): aligns all `devcapsule workflow` (`brief`, `status`, `claim`, `publish [--retire]`, `mail check|send|take`) and `devcapsule bootstrap project [--refresh-workflow-definition]` commands and `WORKFLOW.md` topic 5.5 synchronization rules.
7. `docs/platforms/linux.md`: aligns `linux-amd64` host prerequisites and `{{tag}}` support statement with `platforms.py` and `install.md`.
8. `docs/platforms/macos.md`: states `{{tag}}` `linux-amd64` scope and native macOS port requirements directly.
9. `docs/platforms/windows-wsl2.md` (`role: windows` and `aliases` preserved): removes internal operator testing notes, aligns WSL2 Docker Desktop and ext4 filesystem guidance, updates `BROWSER=wslview devcapsule project run`, and covers both desktop and web console loopback URLs.

## Validation

- Changed `docs/*.md` files against `origin/release-0.3.0`: `9` (`<= 10` limit respected; `docs/versions.yaml` and `website/CONTRACT.md` untouched).
- Cross-batch union check across Batches 1–5 (`#319`, `#321`, `#323`, `#325`, `#327`): `49 / 49` `docs/**/*.md` files covered with zero overlaps, zero missing pages, and zero `status: planned` stubs remaining.
- Shell syntax check (`bash -n`) across all 17 fenced `bash`/`sh` blocks in Batch 5: passed.
- `devcapsule-src/.venv/bin/nox -s docs-contract`: passed (`192 pages including 18 aliases; versions devel (0.3.0): development, 49 pages`).
- `./scripts/website.sh build && ./scripts/website.sh check`: passed (`23` promotion/check tests, `196` HTML pages, `14,462` links/assets/anchors).
- `devcapsule-src/.venv/bin/pytest -q -k "release_docs"`: `92 passed`.
- `devcapsule-src/.venv/bin/nox -s smoke`: passed.

## Pair Review

- **Slice PR:** [PR #327](https://github.com/ccozianu/devcapsule/pull/327) (`4cc5e10a`, brief at [review-brief.md](review-brief.md) `77726397`).
- **Review PR:** [PR #328](https://github.com/ccozianu/devcapsule/pull/328) (`PR327.1` by `Codex / gpt-6-astra`, commit `59bc1bae`).
- **Outcome:** Accepted without a revision round after independent verification against `devcapsule-src/` (`logs.py`, `values.py`, `storage.py`, `platforms.py`, `commands/project.py`, `commands/_console_channel.py`, `configuration/console_channel.py`, `display_client.py`, `workflow_coordination.py`) and `devcapsule-webconsole/` (`security.py`), and merged at `edcab618`. Unimplemented runtime proposal (port/instance-isolated console auth cookies on `127.0.0.1`) recorded in `CURRENT-STATUS.md`.
