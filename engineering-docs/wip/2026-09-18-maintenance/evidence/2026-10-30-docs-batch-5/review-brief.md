# Review-Partner Brief — PR327.1: 0.3.0 User Documentation Batch 5 (`sessions/`, `collaboration/`, `platforms/`)

## Slice Identity

- **Workstream:** `maintenance`
- **Target integration branch:** `release-0.3.0`
- **Slice pull request:** [PR #327](https://github.com/ccozianu/devcapsule/pull/327)
- **Slice branch:** `ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms`
- **Implementation commit:** `4cc5e10aaad75c8955eb3fa97b8b7fc9a9ff2eeb`
- **Implementor:** `Antigravity, Gemini 4 Argon (High)` pair
- **Review partner:** `Codex, gpt-6-astra` pair
- **Review checkout:** `/home/devcapsule/worktrees/docs-batch-1-review`
- **Review branch:** `ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms-review` (open your review PR against `ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms`, never against `release-0.3.0` or `main`)

## Contracts and Governing Records

1. **Work order (on `origin/main` at `ebab228a`):** examine via `git show ebab228a:engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md` (and `git show ebab228a:engineering-docs/work-orders/2026-10-24-maintenance-docs-language-review-before-0-3-0.md`).
   - Owner binding decisions:
     - `write-full-pages`: author complete `0.3.0` pages for `status: planned` stubs (`docs/sessions/several-projects.md` and `docs/sessions/another-machine.md` in this batch), removing `status: planned` and setting `updated: 2026-10-30`. Never invent unshipped CLI commands.
     - `combine-with-language`: fold direct human prose & entry clarity from the Oct 24 language review; keep Oct 25 new-page/recipes/glossary proposals deferred to `0.3.1` (do not add, delete, move, or rename `docs/` files; do not touch `website/CONTRACT.md` or `docs/versions.yaml`).
     - `direct-wo-pair-batches`: strictly `<= 10` `docs/*.md` files modified per PR against `release-0.3.0`.
2. **Website content contract:** `website/CONTRACT.md` (no literal `v?0\.\d+\.\d+` version strings in `docs/`, single-sentence `description` `<= 200` chars, preserve `role` and `aliases` frontmatter, valid relative links and anchors).
3. **Process:** `WORKFLOW.md` topic 9.11 and `engineering-docs/development/review-partner-loop.md`.

## Files Under File-by-File Review (9 `docs/*.md` files)

Review **every single one** of these 9 files line by line against the actual `0.3.0` implementation in `devcapsule-src/` and `devcapsule-webconsole/` (use `../ai-learning-bootstrap/devcapsule-src/.venv/bin/devcapsule ... --help` and inspect `devcapsule/project_information.py`, `devcapsule/launch/pycharm/_launcher.py`, `devcapsule/configuration/storage.py`, `devcapsule/configuration/bindings.py`, `devcapsule/configuration/console_channel.py`, `devcapsule/commands/_console_channel.py`, `devcapsule/commands/_run_flow.py`, `devcapsule/commands/project.py`, `devcapsule/commands/bootstrap.py`, `devcapsule/workflow_coordination.py`, `devcapsule/platforms.py`, `devcapsule/display_client.py`, `devcapsule_webconsole/app.py`, and `devcapsule_webconsole/configuration.py`):

1. `docs/sessions/start-stop-reconnect.md`
2. `docs/sessions/what-persists.md`
3. `docs/sessions/several-projects.md` (`status: planned` retired)
4. `docs/sessions/another-machine.md` (`status: planned` retired)
5. `docs/sessions/web-console.md`
6. `docs/collaboration/working-in-workstreams.md` (`aliases: [/docs/guides/working-in-workstreams/]` must stay intact)
7. `docs/platforms/linux.md`
8. `docs/platforms/macos.md`
9. `docs/platforms/windows-wsl2.md` (`role: windows` and `aliases: [/docs/guides/windows-wsl2/]` must stay intact)

## Review Instructions

1. Work **exclusively** inside `/home/devcapsule/worktrees/docs-batch-1-review` on branch `ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms-review`. Do **not** touch `/home/devcapsule/worktrees/ai-learning-bootstrap` or any other worktree.
2. Verify every CLI command, flag, argument order (for example `state adopt --from PATH <slot>` vs `config bind <slot> host-directory:PATH`), environment variable, file path, exit code, web console route/verb classification, and workflow rule across all 9 files against `devcapsule-src/` and `devcapsule-webconsole/`.
3. Check every fenced `bash`/`sh` block with `bash -n` (watch out for unquoted `<placeholder>` tokens!).
4. Do **not** edit `CURRENT-STATUS.md` or `review-partner-loop.md` on your review branch (the implementing session records the loop after merging your review PR, and keeps sibling PR diff lines non-overlapping). Keep the `docs/` diff strictly within these 9 files (`<= 10` `docs/*.md` files total, never touching `docs/versions.yaml` or `website/CONTRACT.md`).
5. Fix any concrete inaccuracy, contract mismatch, broken link, shell-syntax bug, or unclear phrasing directly on `ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms-review`, commit preserving `git var GIT_AUTHOR_IDENT` with your `Co-Authored-By:` trailer, and run the validation gate using `/var/tmp/dc-docs-batch5-codex` for any pytest `--basetemp` scratch:
   - `../ai-learning-bootstrap/devcapsule-src/.venv/bin/nox -f ../ai-learning-bootstrap/devcapsule-src/noxfile.py -s docs-contract` (or run `npm --prefix website run check:content` inside `/home/devcapsule/worktrees/docs-batch-1-review`, making sure `website/node_modules` is linked if needed — check `ls -la website/node_modules` first!)
   - `./scripts/website.sh build && ./scripts/website.sh check`
   - `PYTHONPATH=devcapsule-src ../ai-learning-bootstrap/devcapsule-src/.venv/bin/pytest devcapsule-src/tests -q -k "release_docs" --basetemp=/var/tmp/dc-docs-batch5-codex/basetemp -o cache_dir=/var/tmp/dc-docs-batch5-codex/cache`
6. Push `ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms-review` and open a pull request **with `--base ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms`** (using Graphviz `dot`, never Mermaid, if you include a diagram). If zero defects are found, still report your file-by-file verification evidence clearly in your final response (or PR).
