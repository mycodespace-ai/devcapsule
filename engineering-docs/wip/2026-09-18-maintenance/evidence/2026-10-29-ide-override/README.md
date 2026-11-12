# Explicit IDE requirement override: the recorded acceptance session, 2026-10-29

The acceptance evidence of the
[work order of 2026-10-28](../../../../work-orders/2026-10-28-explicit-ide-requirement-override.md),
run inside this capsule from `/home/devcapsule/worktrees/ide-override` on
`ws-maintenance/0.3.0-ide-override` at `fcf5c4e6`, against the executable
the session built from that tree (`run.json`: `v0.3.0-local-linux-x86_64`,
sha256 `520f8163…cfc5`), on the recommended v0.3.0-rc6 base, with
`nox -s ide-smoke -- --display --required-ide`
(`tests/e2e/test_required_ide_override.py`). The whole session took 50.5
seconds, both environments materialized from cached layers. Plan evidence
and observed launches are kept apart below.

The isolated fixture (`init.log`): a fresh project under the e2e workspace
root, `--require python --require python-ide --ide python-ide`, the base and
host networking consented; `devcapsule.checkout.toml` is its checkout record
as it was before, during and after the two launches: `selected = ["python-ide"]`,
PyCharm 2026.2.0.1 pinned. The project's `.devcapsule/` files were compared
byte for byte after each launch and never changed.

1. **Refusal without force** (`refused.log`): `run --ide codium --print-command`
   exited 2 before any materialization, naming the exact override command
   and saying the requirement and the saved IDE stay as they are.
2. **Forced launch, observed** (`forced-launcher.log`, `forced-desktop.png`,
   `forced-desktop.webm`): `run --ide codium --force` printed the warning on
   its first line, materialized `devcapsule-local-codium:3c0799340a12c19c47db`,
   published the desktop and the console, and an X11 top-level window of
   class `codium codium` named `VSCodium` owned the display, 389 distinct
   colours on the coarse grid; the screenshot shows VSCodium with the
   fixture folder and `smoke.txt` open. The runtime plan inside the
   container named `codium`.
3. **Forced plan** (`forced-devcapsule.resolved.toml`): `runtime.component = "codium"`
   and `[departures.ide-requirement]` with `required = "python-ide"`,
   `launched = "frontend-ide"`; no `pycharm` component in the launched lock.
4. **Plain launch, observed** (`plain-launcher.log`, `plain-desktop.png`,
   `plain-desktop.webm`): the next `run` without flags printed no warning,
   materialized `devcapsule-local-pycharm:23af9ec77ca0fb4f2785`, and a window
   of class `jetbrains-pycharm jetbrains-pycharm` owned the display, 1432
   distinct colours; the screenshot shows PyCharm's first-run user
   agreement. The runtime plan named `pycharm`.
5. **Plain plan** (`plain-devcapsule.resolved.toml`): `runtime.component = "pycharm"`
   and no `departures` table.

`facts.json` is the test's own record of both launches. Both sessions were
stopped by the harness with `docker stop`, so each launcher log ends with a
non-zero session exit; the known-good record of a successful plain launch
was therefore not exercised here, the unit tests cover it. The launcher logs
have the run tokens redacted. The raw evidence directory was
`devcapsule-src/dist/e2e-evidence/ide-smoke/20261029T013240Z-49b3af-required-ide`.

`review-brief.md` is the brief Codex, gpt-6-astra at high effort, received
for PR304.1 (PR #306) on standard input, run as `codex exec --json`; the
review was accepted without a round and merged at `3bfb3a16`.
