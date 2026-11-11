# Workstream Current Status: Maintenance

Mnemonic: `maintenance`

Start date: 2026-09-18

State: active 2026-11-10; releasing 0.3.1 from `release-0.3.1`, cut from `main` at `31e8fec7`; candidate 2 (`v0.3.1-rc2` on `be0140ca`, merged to `main` via PR #22 `aabace3c`) published and verified; all three 0.3.1 release bugs closed (Eclipse libsoup on rc1; launcher-delivered `devcapsule_webconsole` `D-0017` and Codex npm abbreviated metadata on rc2 + `component-status` feed `0bc31c64`); Codex `0.167.0` and Claude Code `2.1.321` shipped in `embedded-33`; two rulings open (Mac/arm64 executables, compatibility feed's website path) plus end-to-end run, `notes.md`, and docs promotion before final `v0.3.1`; one blocking bug open since 2026-11-10, unit tests reading the capsule's mounted launcher settings, no fix started; one major bug in fixing, the Python route and its guard, merged through #25 with the local gate's routing open; a follow-up to PR #18 on `ws-maintenance/host-inputs-at-source`, by Pair Review, for the owner's review

Definition read: WORKFLOW.md@e83f22a20701, WORKFLOW-LOCAL.md@d92bdcbb0a01

Integration target: `main`

Delivery method: ordinary maintenance PRs to `main`; owner merges. No records-only PR. The 0.3.0 release is published; website production promotion remains owner-operated.

Branch association: `release-0.3.1` from main 31e8fec7, the workstream's selection from the cut to the final tag; `ws-maintenance/host-inputs-at-source` from release-0.3.1 2f1109db, PR #26 open, the owner merges; `ws-maintenance/python-route-guard` merged through #25 and closed; `ws-maintenance/pile-of-ideas` merged through #23 and closed; `ws-maintenance/0.3.1-agent-freshness` merged through #21 and closed; `ws-maintenance/codex-npm-metadata` merged through #20 and closed; `ws-maintenance/webconsole-legacy-tests` merged through #18 and closed; `ws-maintenance/webconsole-delivery` merged through #16 and closed; `ws-maintenance/move-to-organization` merged through #1 and closed; `ws-maintenance/base-consent-test` from main 445469f1; `ws-maintenance/coverage-in-pr` merged through #336 and closed; `ws-maintenance/test-conventions` merged through #335 and closed; `ws-maintenance/0.3.1-preparation` from main 31d44fa4; `release-0.3.0` closed after final publication and retained with its tags; `ws-maintenance/0.3.0-acceptance` merged through #332 and closed; earlier slice branches are historical

Requirements: `R-PRODUCT-006`, `R-COMPAT-001`, `R-PRODUCT-002`, `R-CONSOLE-001`

## PR #18's test-only parameters removed; the tests set the host at its source — 2026-11-11

On 2026-11-10 the owner asked for an independent assessment of
[PR #18](https://github.com/mycodespace-ai/devcapsule/pull/18), then asked
for its shortcomings to be fixed, by Pair Review with Codex and GPT-6 Astra
as the review partner. The assessment's findings, each measured on the tree
at the merge `b84b06e9`:

- PR #18 gave eight production signatures twenty keyword parameters that no
  production caller passes, so that no new test would patch a `devcapsule.*`
  attribute. Each test passed the parameter, so the branch that ships, the
  default, was run by no new test. Of six production faults planted in those
  defaults, the four retired legacy files had caught five; the whole unit
  suite after PR #18 caught none of the six.
- `entrypoint.run` forwarded `caller_uid` and `runtime_root` only when given,
  so that two legacy tests' `lambda *args: None` stand-in for
  `prepare_filesystem` kept working.
- `VersionCommand` and `CheckoutDecisionsCommand` carried test inputs through
  the command framework's group-context argument and told them apart by type.
- The hosted run was red on five consecutive pushes while the slice was
  reviewed, accepted and recorded as validated; both pairs had validated
  inside a capsule, where `/ide-config` exists.

Delivered on `ws-maintenance/host-inputs-at-source`, from `release-0.3.1` at
`2f1109db`, as [PR #26](https://github.com/mycodespace-ai/devcapsule/pull/26):

- `entrypoint.run`, `console_child`, `plan_filesystem`, `prepare_filesystem`,
  `foreground_command`, `VersionCommand`, `CheckoutDecisionsCommand` and
  `run_console_decisions` have their signatures of before PR #18 again:
  seventeen of the twenty parameters, the type aliases that served them and
  the private `_DecisionsInvocation` are gone, and `console_child` loses the
  `launcher_source` parameter PR #16 added in the same style. `run`'s body is
  the one 0.3.0 shipped. The one addition is a name for a fact,
  `filesystem.RUNTIME_ROOT`, `/tmp`.
- The mirror tests set each host input where the code reads it:
  the caller's uid, ownership changes and the readiness connection through
  `os.geteuid`, `os.chown` and `socket.create_connection`; the image's fixed
  locations through the public constants `CONSOLE_PYTHON`,
  `LAUNCHER_CONSOLE_SOURCE`, `RUNTIME_ROOT` and `RUNTIME_PLAN_PATH`; the
  environment with `monkeypatch`; and, for `run` alone, the supervisor, the
  display and the log setup by stand-ins. The code a test runs is the code
  that ships.
- `identity.py` has its mirror file. `images/contract.py` no longer calls the
  runtime's check at start a backstop for the recipe. The integration test of
  the wrapper's help builds a base without a console interpreter again.

Judgments taken, for the owner's review:

1. A production signature has a parameter only when production passes it.
   This reverses the choice recorded on 2026-11-08, that no refurbished test
   patches a `devcapsule.*` attribute. The tests patch public names only,
   and never a private one; the conforming tests merged on 2026-11-04 and
   2026-11-05 do the same (`status.read_metadata`,
   `runtime_artifact.current_build_info`).
2. `current_build_info` keeps its three parameters: the stamped record lies
   inside the installed package, where a test cannot build it.
   `console_decisions_command` keeps the four it had before PR #18; its
   defaults are now run by the tests of `run_console_decisions`.
3. `commands/project.py` gets no mirror test: a mirror would oblige its
   public surface to be declared and `tests/test_project.py` to be retired
   in the same change. The one line by which `project checkout decisions`
   delegates is run by the integration file only.
4. The target is `release-0.3.1`, as it was for PR #18.

Evidence: 26 faults planted one at a time in a scratch copy of the tree and
run against the touched unit files. 24 are caught there, among them the five
that PR #18 had lost. One, the command dropping its arguments, is caught by
the integration file only. One survives both, as it did before PR #18: a
built executable that never finds its stamped record; the gate's smoke runs
`version --json` and reads only its exit status.

Validation at `8274a546`, in the owner's capsule: `nox -s tests` gives 17
failed and 2913 passed, the 17 of the
[blocking record](../../bugs/devcapsule/2026-11-10-unit-tests-read-the-capsules-mounted-launcher-settings.md)
and no other; the convention check counts 103 legacy files with 1372 legacy
tests and 49 conforming files, 0 breaches; mypy is clean over 330 files; the
integration file gives 10 passed. The gate as a whole cannot pass in this
capsule while those 17 stand, so the hosted run is the authority for the
suite.

Proposals not implemented, for the owner:

- *Unit Tests*, rule 2 or its companion: a parameter is added to production
  code for a test only when production passes it, and the default a release
  ships stays under a test of the gate.
- *Pair Review Loop*: a review is accepted, and a slice recorded as
  validated, only on a green hosted run of the head; the brief asks for it.
- The gate's smoke compares `version --json` of the built executable with
  the stamp the build wrote.
- `WORKFLOW-LOCAL.md`, *Pair Review Loop In This Checkout*, rule 3 still
  names `/opt/devcapsule-gate` as the review partner's scratch, which the
  owner retired on 2026-11-04.

## The Python route becomes a list of inputs the suite is held to — 2026-11-10

The owner re-rated
[Markdown-only changes run the whole Python unit suite](../../bugs/devcapsule/2026-11-10-markdown-only-changes-run-the-python-unit-suite.md)
major and chose the wider fix: the hosted Python job runs only when a
changed file is in `.github/ci-python-inputs.yml`, and a guard in
`tests/conftest.py` fails any counted unit test that opens or lists a
repository path outside that list, so no test can come to depend on a file
the route skips. Branch `ws-maintenance/python-route-guard` from
`release-0.3.1` at `137c4591`. The legacy `tests/test_ci_reporting.py`, whose
filter test the change breaks, is refurbished whole under rule 5.

Judgments taken, for the owner's review: `docs/**` is listed as an input,
because one legacy scan reads all of `docs/` and counts on the hosted
runner, so docs-only pull requests run the suite until that scan is
retired; the routing tests are integration tests now and leave the hosted
job; the bug's target is set to 0.3.1 without the owner having named it.

Found on the way and added to the blocking record: inside the owner's
capsule one expected-to-fail unit test downloads 1.5 GB of vendor artifacts
on every run, which is most of the local gate's twelve minutes and what
fills `/tmp`.

PR #25. Hosted runs: the guard alone at `772c3e77`, 2976 passed with no
breach; the flip at `3bd6cc27`, 2947 passed, the new filter matching the 11
changed files under `devcapsule-src/` and `.github/` and none of the 5 under
`engineering-docs/`.

PR #25 is merged into `release-0.3.1` at `2f1109db`. Next action, on the
owner's word: the local gate's routing and the retirement of the `docs/`
scan.

## The pile of ideas, a workflow rule for 0.3.1 — 2026-11-10

Owner direction of 2026-11-10: a directory, `engineering-docs/pile-of-ideas/`,
holds one file per idea nobody has triaged, and `project-management` triages
it. The rule is topic 12.13 of `WORKFLOW.md` with its glossary entry, file
role, one sentence in topic 7.3, the 0.3.1 changes entry and the humane
paragraph; the packaged definition carries the same rules under *Pile Of
Ideas*, so adopters get it with 0.3.1. The owner chose to ship it in the
definition before it has been used here. Two ideas open the pile: the
recursive test machinery out of the adopter's executable, and a tiling
desktop with the IDE on the side. Branch `ws-maintenance/pile-of-ideas` from
`release-0.3.1` at `c4bd458b`; PR #23 to `release-0.3.1` is open for the
owner, and the merge to `main` follows it.

Finding, not caused by this slice and not diagnosed: `nox -s tests` in the
owner's capsule on this branch gives 17 failed, 2893 passed, and the same 17
fail on the untouched `v0.3.1-rc2` tree in the same environment. They are in
`tests/test_run_flow.py` (8), `tests/test_trust.py` (3),
`tests/configuration/test_contract.py` (2),
`tests/test_ide_requirement_override.py` (2),
`tests/test_capability_policy.py` (1) and `tests/test_owner_commands.py`
(1). None is among the tests marked expected to fail on 2026-11-04.

Diagnosed the same day: the capsule's read-only mount of the host's launcher
settings, where `devcapsule-base` and `vscode` were accepted on 2026-11-08;
all 17 pass with the mount hidden. Filed at the owner's direction as
[blocking for 0.3.1](../../bugs/devcapsule/2026-11-10-unit-tests-read-the-capsules-mounted-launcher-settings.md).
Next action: make the isolation fixture a private home; no fix started.

Also filed the same day, reported by the owner:
[Markdown-only changes run the whole Python unit suite](../../bugs/devcapsule/2026-11-10-markdown-only-changes-run-the-python-unit-suite.md),
minor, no target. Next action: the owner chooses among the fix notes.

## Candidate 2 (`v0.3.1-rc2`) published and verified — 2026-11-10

After the owner merged PR #20 (`eb8ff8cf`) and PR #21 (`3ea05e68`) into
`release-0.3.1`, `nox -s integration` passed on `3ea05e68` (`40` passed, `3`
skipped in `39.65s`, recorded at `be0140ca` in `test-runs.json`). Pre-candidate
PR #22 (`4PR-3-release-0.3.1` -> `main`, keeping `main` at `0.3.2.dev0` while
preserving `_webconsole_bundle.zip` in `pyproject.toml`) merged at `aabace3c`.

- Tagged `v0.3.1-rc2` on `be0140ca19b426cc9eea4dafa1a8958826d20c56` (`mainline`,
  zero unintegrated commits, `0.3.1rc2`). Hosted workflow run
  [`42734994462`](https://github.com/mycodespace-ai/devcapsule/actions/runs/42734994462)
  passed (`2,929` unit passed, `66` deselected, `1` xfailed, `1` xpassed;
  packaging integration `40` passed, `3` skipped in `54.14s`) and published the
  non-draft [prerelease](https://github.com/mycodespace-ai/devcapsule/releases/tag/v0.3.1-rc2).
- Downloaded into `/home/devcapsule/.cache/devcapsule-releases/v0.3.1-rc2`
  (`devcapsule.pex` SHA-256 `2c3ace0f2f5b94ef4dfce9f568a09cf00ce045964fbbf6bf90ff06b1fe54a5d4`,
  `version --json` `0.3.1rc2` at `be0140ca…`) and closed both remaining
  candidate-gating bugs:
  - [`2026-11-08-codex-npm-metadata-exceeds-16-mib.md`](../../bugs/devcapsule/2026-11-08-codex-npm-metadata-exceeds-16-mib.md):
    `origin/component-status` (`0bc31c64`, `2026-11-10T00:58:45Z` from
    `aabace3c`) reports Codex `ok` with `consecutive_failures: 0` and candidate
    `0.167.0`; `devcapsule.pex project init` + `project versions check` on a
    fresh adopter project with empty `DEVCAPSULE_CONFIG_HOME` locked `codex
    0.167.0` and `claude-code 2.1.321` (`embedded-33`) and reported both
    `available` live.
  - [`2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md`](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md):
    `_webconsole_bundle.zip` extracted from the downloaded `v0.3.1-rc2`
    `devcapsule.pex` and served on the pre-PR-#12 base interpreter
    (`/opt/devcapsule-webconsole/venv/bin/python`) against that non-DevCapsule
    project answered `200 OK` on `/files`, `/api/project/tree`, and
    `/api/project/raw`, and `307` (`Location: /files`) on `/filetree`;
    `is_built_distribution()` returned `True`, leaving `console_development_source()`
    empty by default on DevCapsule checkouts.
- Also updated this capsule's persistent `/home/devcapsule/.gemini/config/AGENTS.md`
  co-author address from `<noreply@google.com>` (unclaimed on GitHub, no commit
  avatar) to Google's official Gemini GitHub App noreply address
  `<176961590+gemini-code-assist[bot]@users.noreply.github.com>` at the owner's
  request.
- Planned next step: await the owner's rulings on Mac/arm64 published
  executables, the compatibility feed's website path, and whether Antigravity
  CLI stays held at `1.4.12` for `0.3.1`; then run the end-to-end test selection
  on the accepted candidate (*Release Policy* rule 10), write `notes.md`, run
  `release-docs.py promote 0.3.1`, and prepare final `v0.3.1`.

## Agent CLI freshness refresh for 0.3.1 candidate 2 (`embedded-33`) — 2026-11-09

Stacked on PR #20 (`ws-maintenance/codex-npm-metadata` at `8f458a12`) as
`ws-maintenance/0.3.1-agent-freshness`:

- Rechecked live vendor pointers on 2026-11-09: Codex `0.167.0`, Claude Code
  `2.1.321` (up from `2.1.319` at the 2026-11-07 cut after Anthropic's model
  launch), and Antigravity CLI `1.5.3`.
- Downloaded and cryptographically verified both `linux-amd64` and
  `linux-arm64` artifacts for Codex `0.167.0` (against npm SHA-512 SRI:
  meta `e858522a…`, `linux-x64` `2dc9aa87…`, `linux-arm64` `e24d7b6f…`) and
  Claude Code `2.1.321` (against `2.1.321/manifest.json` SHA-256: `linux-x64`
  `426c3381…`, `linux-arm64` `6bea0633…`).
- Verified offline layout, seeded configuration (`config.toml` /
  `settings.json`), `--version` (`codex-cli 0.167.0`, `2.1.321 (Claude Code)`),
  and `--help` inside `mycodespaceai/devcapsule-base:v0.3.0-base-20261031`
  (`--network none`) using `materialization.npm_install_step`.
- Advanced `resolution_matrix.py` to `embedded-33` (appending `_CODEX_0_167_0`,
  `_CLAUDE_CODE_2_1_321`, and their `_VerifiedEdge` entries while keeping all
  prior pins), added matching `linux-arm64` entries in
  `components/linux_arm64_pins.py`, and regenerated all 11 golden locks.
- Held Antigravity CLI at `1.4.12` (surfaced to the owner): advancing
  `antigravity-cli` alters four literal `"1.4.12"` assertions in `1,396`-line
  legacy `tests/test_project_init.py` (documented in
  `2026-10-31-release-dependent-test-fixtures.md`), which *Unit Tests* rule 5
  requires refurbishing whole.
- Planned next step: once PR #20 and this stacked freshness PR merge into
  `release-0.3.1`, run `nox -s integration` on `release-0.3.1` (recording
  `test-runs.json`), merge `release-0.3.1` into `main` through a throwaway
  `4PR-3-release-0.3.1` PR keeping `main`'s `0.3.2.dev0` version files, and tag
  `v0.3.1-rc2` on the owner's word.

## Codex npm registry metadata > 16 MiB fix for 0.3.1 candidate 2 — 2026-11-09

After the owner merged stacked PRs #18 (`b84b06e9`) and #16 (`f2bae5cb`) into
`release-0.3.1`, the owner directed fixing
[the Codex npm metadata cap bug](../../bugs/devcapsule/2026-11-08-codex-npm-metadata-exceeds-16-mib.md)
first, followed by the agent CLI freshness upgrade (noting Anthropic's new model
launch; live vendor pointers read 2026-11-09: Codex `0.167.0`, Claude Code
`2.1.321`, Antigravity CLI `1.5.3`) and cutting `v0.3.1-rc2`.

On `ws-maintenance/codex-npm-metadata` (from `release-0.3.1` at `f2bae5cb`):

- `NpmChannel._metadata` in `devcapsule/components/npm_channel.py` sends
  `Accept: application/vnd.npm.install-v1+json` when `version == ""` (`check()`),
  keeping full single-version fetches in `select()` and the 16 MiB cap intact,
  and exposes `__all__` plus an optional `opener` parameter for pure unit tests
  while preserving `urlopen` module-level compatibility for legacy
  `test_distribution_channels.py` and `test_version_sets.py`.
- Added 6 single-action Hoare-triple unit tests in
  `tests/unit/devcapsule/components/test_npm_channel.py` (`45` conforming files,
  `104` legacy files, `0` breaches).
- Verified live against `https://registry.npmjs.org/@openai%2Fcodex` (`5,456,187`
  bytes / `5.20 MiB`, `5,786` versions): `CodexComponent().distribution_channel().check("0.166.0", ...)`
  returns `0.166.0` `available` and candidate `0.167.0` `available` on both
  `linux-amd64` and `linux-arm64`.
- Planned next step: open PR to `release-0.3.1`, prepare the agent CLI freshness
  upgrade slice (`0.167.0` / `2.1.321` / `1.5.3` across `linux-amd64` and
  `linux-arm64`), merge `release-0.3.1` to `main`, and cut `v0.3.1-rc2`.

## Blocking 0.3.1rc1 finding and D-0017 fix: launcher-delivered web console (stacked on PR #18) — 2026-11-08 / 2026-11-09

Validating `v0.3.1-rc1` (`accdec5b`) inside a running capsule found that
`GET /files`, `GET /filetree`, and `GET /api/project/tree` all returned `404`.
Two couplings caused the failure: `devcapsule.pex` did not carry
`devcapsule-webconsole/` (so adopter capsules ran the pre-PR-#12 package baked
into the pinned `linux-amd64` and `linux-arm64` recipe-11 bases), and
`console_development_source()` unconditionally put a mounted DevCapsule
checkout's `devcapsule-webconsole/` first on `PYTHONPATH` (shadowing built
candidates on older branches and masking missing delivery on `release-0.3.1`).
Filed as [the blocking bug record](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md)
on `ws-maintenance/webconsole-delivery` (local `main` fast-forwarded 122
commits to `origin/main` `46ded16d`, `git cherry` clean).

The owner answered both design decisions through the capsule console, recorded
in [D-0017](../../decisions/product/d-0017-launcher-delivers-web-console-package.md)
and [R-CONSOLE-001](../../requirements/product/r-console-001-capsule-web-console.md):

1. `console-delivery = launcher-package`: `scripts/build-pex.sh` treats
   `devcapsule-webconsole/` as a tracked clean build input and embeds
   `devcapsule/_webconsole_bundle.zip` inside `devcapsule.pex` via
   `devcapsule/webconsole_bundle.py`; `materialization.py` extracts and installs
   `/opt/devcapsule/webconsole` read-only alongside
   `/opt/devcapsule/bin/devcapsule.pex` (bound to `runtime.pex-sha256` in
   formation identity); `container_runtime/console.py` and `console_tools.py`
   share `console_package_path` (`console.source_path` ->
   `/opt/devcapsule/webconsole` -> `/opt/devcapsule-webconsole`), while the host
   launcher settles interpreter compatibility via `WEBCONSOLE_RECIPE` (`11`).
2. `self-hosting-override = source-or-opt-in`: `is_built_distribution()` in
   `build_info.py` distinguishes built executables from source runs;
   `console_development_source()` leaves `console.source_path == ""` by default
   for built executables even on a DevCapsule checkout, keeps automatic checkout
   mounting for unbuilt source runs, and honors `DEVCAPSULE_DEV_WEBCONSOLE`
   (`1`/`true` or `0`/`false`).

Reviewed under Pair Review by `Claude Code + Claude Fable 5.1` in
[PR #17](https://github.com/mycodespace-ai/devcapsule/pull/17) (`PR16.1`,
[brief](evidence/2026-11-08-webconsole-delivery/review-brief.md)), accepted at
`e23e22c7` without a round and merged at `9919f4ce`. PR #17 unified
`console_package_path` and dropped the dead `psutil` probe, masked
`external_attr >> 16` with `stat.S_IFMT` in `extract_webconsole_bundle` while
pinning `match=` on every refusal test (`99%` bundle coverage), tightened
`DEVCAPSULE_DEV_WEBCONSOLE` to `1`/`true`/`0`/`false`, and aligned `D-0017` and
the bug record. Per subsequent owner decision (`2026-11-08-stacked-legacy-tests`:
`legacy-marker-scope = retire-four-plus-gate`,
`stacked-delivery-branch = force-push-pr-16`,
`psutil-probe-in-pr1 = drop-in-pr1`), `ws-maintenance/webconsole-delivery` was
then rebased onto [PR #18](https://github.com/mycodespace-ai/devcapsule/pull/18)
(`ws-maintenance/webconsole-legacy-tests`) so all new `D-0017` unit tests extend
the refurbished mirror modules with zero legacy/mirror test twins and zero
`devcapsule.*` attribute patches (`test_pycharm.py` untouched).

Stacked gates on `ws-maintenance/webconsole-delivery` passed: `nox -s build`
(mypy clean across `332` files, `0` unit-convention breaches across `104` legacy
files holding `1,387` legacy tests and `44` conforming files, `2,904` unit tests
passed at `89%` total coverage, `smoke_pex`, `249`-page content contract),
`nox -s integration` (`40` passed, `3` skipped), `nox -s webconsole` (`458`
passed), and a live HTTP check on this capsule's pre-PR-#12
`/opt/devcapsule-webconsole/venv/bin/python` serving `/files` (`200`),
`/filetree` (`307` -> `/files`), `/api/project/tree` (`200`), and
`/api/project/raw?path=hello.txt` (`200`) from `dist/devcapsule-local.pex`
against a non-DevCapsule project. Three remaining proposals from PR #17 stay
queued for `main` follow-up (PR #17's fourth proposal, migrating private
`materialization` test imports, was completed in PR #18): (1) declare `__all__`
on `launch/pycharm/_launcher.py` for its pre-existing mirror test file; (2)
share a single "one member by suffix" PEX zip helper between
`read_pex_build_info` and `extract_webconsole_bundle`; and (3) add a test tying
`WEBCONSOLE_RECIPE` to `BASE_RECIPE_VERSION` and
`devcapsule-webconsole/requirements.in`. Planned next step: await the owner's
merge of PR #18 into `release-0.3.1` followed by PR #16 into `release-0.3.1`,
then implement the Codex 16 MiB npm cap slice before `v0.3.1-rc2`.

## Whole-file legacy test retirement and 4-file refurbishment for 0.3.1, by Pair Review — 2026-11-08

Reviewing the initial `0.3.1` web-console delivery PR (#16), the owner noted
that per-function shrinkage under *Unit Tests* rule 5 had left two
`test_materialization.py` files side by side (and 38 mirror files with only
two retired legacy files across the tree). By owner decision
(`2026-11-08-stacked-legacy-tests`: `legacy-marker-scope = retire-four-plus-gate`,
`stacked-delivery-branch = force-push-pr-16`, `psutil-probe-in-pr1 = drop-in-pr1`),
this prerequisite slice (`ws-maintenance/webconsole-legacy-tests` ->
`release-0.3.1`) tightens rule 5 and its gate checker so legacy unit-test
files are retired whole when touched or mirrored, and refurbishes all four
legacy files touched by the web-console delivery slice (`test_build_info.py`,
`test_console_runtime.py`, `test_console_tools.py`, and
`test_materialization.py`), dropping legacy files from `108` to `104`
(`1,445 -> 1,387` legacy tests, `-58`) and raising conforming files from
`34` to `43`. Each touched module declares `__all__` and exposes explicit
input/collaborator parameters (`current_build_info`, `VersionCommand.invoke`,
`console_child`, `plan_filesystem`, `entrypoint.run`, `run_console_decisions`,
`CheckoutDecisionsCommand.invoke`) so no refactored test patches
`devcapsule.*` attributes; the dead per-start `import psutil` subprocess
probe in `console.py` is removed (`WEBCONSOLE_RECIPE` 11 on the host already
gates console planning).

Pair Review (`Claude Code + Claude Fable 5.1`, [brief](evidence/2026-11-08-webconsole-legacy-tests/review-brief.md))
opened [PR #19](https://github.com/mycodespace-ai/devcapsule/pull/19)
(`PR18.1`), accepted at `4aac5dfc` without a round and merged at `a1aad17f`:
completed `__all__` in `container_runtime/console.py`,
`container_runtime/entrypoint.py`, and `materialization.py`; removed a dead
`subprocess` import in `commands/project.py`; aligned rule 5, its companion,
`engineering-docs/development/unit-tests.md`, and the checker diagnostic on
basename pairing and mirror test deletions (4 new checker tests); added an
`environ` isolation test in `test_entrypoint.py`; and restored interpreter-path
matching in `test_console_tools.py`. Hosted CI on `e301367d` caught a
capsule-masked host-filesystem leak in `test_entrypoint.py` (`make_plan`
inherited `pycharm_runtime_template()`'s `/ide-config` state slots and
`/tmp/devcapsule-jetbrains.properties`, which existed inside the PyCharm
capsule but raised `PermissionError: '/ide-config'` on GitHub Actions); fixed
by rooting `make_plan`'s `state_slots` and `properties_path` under `tmp_path`
and implementing PR #19's third proposal (`runtime_root`, `caller_uid`, and
`configure_logs` seams across `filesystem.py`, `identity.py`, and
`entrypoint.run`, with `__all__` on `filesystem.py` and `identity.py` plus
mirror unit tests in `test_filesystem.py` so the unit tests touch no host
paths, `os.geteuid()`, `os.environ`, or the root logger). Two unimplemented proposals from PR #19 remain
recorded for later owner review: pairing legacy files with mirrors by imported
`devcapsule.*` modules rather than file name alone, and descending into nested
`Test*`-in-`Test*` classes in `_test_functions`. Gate passed (`330` mypy files,
`0` breaches across `104` legacy / `1,387` legacy tests and `43` conforming
files, `2,842` unit passed, `458` webconsole passed, `249` contract pages;
`nox -s integration`: `36` passed, `1` skipped).
[PR #18](https://github.com/mycodespace-ai/devcapsule/pull/18) is ready for
owner merge into `release-0.3.1`, with PR #16
(`ws-maintenance/webconsole-delivery`) stacked directly on top.

## Slice 2 of 0.3.1: the web console's Files page, by Pair Review — 2026-11-08

The owner asked how hard a file browser in the web console would be,
heard the answer, and ordered it as a slice of 0.3.1 with the pairs
reversed from the usual: the Antigravity + Gemini 4 Argon (High) pair
implementing, the Claude Code + Claude Fable 5.1 pair reviewing. The
implementor brief, written by the reviewer's pair for the owner, decided
the shape: a listing route `/api/project/tree`, a page at `/files` with
`/filetree` redirecting to it, byte ranges and a `download=1` disposition
on the raw route, media types for well-known extensions, nothing hidden,
no library, no editing. The implementor delivered PR #12 against
`release-0.3.1` in five commits with 84 new console tests and a Node page
test, all four gates green. The review, PR #13, found one defect: the raw
route carried a branch that detected whether a test had replaced
`read_project_bytes` and read the whole file through it, written to keep
one existing test green under the brief's rule against touching existing
test files; the reviewer removed the branch and repointed that test at the
streaming open. A live smoke against a standalone console confirmed the
206 bytes, the 416, the disposition and the redirect. The implementor
accepted at `49bb2e8e` without a round, merged PR #13 at `83949a30`, reran
the gate on the merged branch (458 console tests, 2825 unit tests, 0
breaches, 249 contract pages) and handed PR #12 to the owner at
`61446044`. Both briefs are under
`evidence/2026-11-08-console-files-page/`. Two proposals were left for a
later change: a structured answer when the tree route is asked about a
file, and `Last-Modified` with `If-Range` on the raw route.

## Release 0.3.1 cut — 2026-11-07

The owner's decision, once the website's links named the organization:
"let's cut the release 0.3.1 as we have plenty for a minor release: we have
the mac platform ability and we have some the wrap functionality". Recorded
in [the scope and cut decision](2026-11-07-decision-release-0-3-1-scope-and-cut.md);
the release work lives in [the 0.3.1 overview](../../releases/v0.3.1/README.md)
with [the bug table](../../releases/v0.3.1/bugs.md) and
[the changelog since 0.3.0](../../releases/v0.3.1/changelog.md).

Done on `release-0.3.1`, cut from `main` at `31e8fec7`, the merge of PR #7:
the version set to 0.3.1 by `nox -s bump` as the branch's first commit; the
`devel` entry of `docs/versions.yaml` declaring `source-version: "0.3.1"`
on the branch alone, as 0.3.0 did; the decision record, the overview, the
bug table, the changelog and the index entries; the registry row and this
file. The agent freshness review read the vendors on 2026-11-07: Codex
0.167.0, Claude Code 2.1.319 and Antigravity CLI 1.5.3 are ahead of the
pins 0.166.0, 2.1.314 and 1.4.12; the attempt is a slice of the cycle.

Found at the cut, from PR #338's note and confirmed against the archive:
the amd64 Eclipse closure pins `libsoup-3.0` build `3.4.4-5ubuntu0.8`,
which Ubuntu replaced with `0.10` on 2026-10-08; the two URLs return 404
and the archive serves `0.10` for amd64, the build the arm64 closure
already pins. [The bug record](../../bugs/devcapsule/2026-11-07-eclipse-amd64-libsoup-urls-return-404.md)
is filed as major for 0.3.1: an adopter who requires Eclipse on a Linux
host with an empty cache cannot acquire it. Fixed on the release branch on
2026-11-07 by the owner's ruling, the cycle's first slice: both packages
at `0.10`, hashes from the signed index, matrix `embedded-32`, golden
locks regenerated; closed when a fresh acquisition succeeds on candidate 1.
The owner also asked for a first cut of how the pin promise is reconciled
with an archive that recycles its files; that proposal is a design matter
for the owner, outside the release.

The full gate passed on the branch, `nox -s build`: 2825 unit tests, mypy
over 323 files, the conventions gate, the smoke, the local PEX, the web
console, the content contract at 249 pages. The integration session, run
before the candidate as rule 9 asks, failed three of eighteen on its first
run: the fixture repository of the clean-revision build test lacked the
compatibility policy that `build-pex.sh` embeds since PR #3, a break on
`main` the candidate workflow would have found at the tag. Fixed at
`7570b14e`; the conventions gate then refused the change to the legacy
file, and the test moved at `3aa21dc0` to `test_build_pex.py`, four
tests of one contract each; 26 passed, recorded in the release's
`test-runs.json`.

Three rulings are asked of the owner before candidate 0, in the overview:
whether 0.3.1 publishes a macOS or an arm64 executable, where the
compatibility feed lives on the website's domain, and whether the Eclipse
repin is the cycle's first slice. The full gate, the integration tests and
their record are done; `main` reopened at `0.3.2.dev0` through PR #8 and the
release branch reached `main` through PR #9 from the throwaway copy, both
merged by the owner on 2026-11-07. On the owner's word of the same day,
`v0.3.1-rc0` was tagged on `8bcee1d0`; the backend run passed, the
prerelease is public with its three assets, and the download verified its
checksum and version. The candidate record is under *Candidates* in the
overview; the hosted run's integration result is the second entry of
`test-runs.json`. The cycle's slices wait for the three rulings.

## Rule 2 names the isolation criterion — 2026-11-06

Before the repair of the seventeen tests expected to fail, the owner asked
for a shared understanding of unit, integration and end-to-end tests, in
general and as the repository defines them, and then reaffirmed the
general criterion that *Unit Tests* rule 2 had left implicit: a unit is
tested in isolation, from no service even a local one, from no clock,
from no other process whose work the test does not fully control; a
digest of a file the test wrote is fine, a Docker build never is. The
agent's refinement, taken: the criterion is that the outcome is a
function of inputs the test constructs; a unit that needs the time takes
it as a parameter; another program runs in a unit test only when running
it is the unit's contract and the test controls its inputs; what can be
computed in process, a digest among them, is computed there; a test that
needs a program for what the program does is an integration test. Rule 2
gained those sentences, the humane companion its paragraph, and the
unit-tests guide its summary, on the branch
`ws-maintenance/unit-test-isolation-rule`.

The same conversation settled the integration tests. The owner preferred
the ordinary meaning to the local one: a subsystem tested together with
the real external things it uses, the services it does not test faked;
Docker commands are allowed, and the guide's "without Docker" was the
hosted runner's limit written into a definition. The type check and the
documentation contract are gate checks, not tests. A `docker` marker names
the need, and the candidate workflow's selection became `integration and
not docker`. The owner then ruled that the integration tests run before a
candidate is produced: in the workflow where they can, and otherwise with
a run record the workflow can find and check,
*Release Policy* rule 9. The agent proposed the record's place and
fields, `engineering-docs/releases/vX.Y.Z/integration-runs.json` with the
source revision, the selection, the environment, the operator, the date
and the result; the workflow's check of it is the next slice, after the
owner confirms the shape.

For the end-to-end tests the owner asked for a synthesis of the general
practice with the local rules, so that nothing general is left out, and
ruled: on demand, at least one for every release, the release notes
naming the tests run and arguing a subset, with an executable forcing
function. The guide gained the nine rules, two of them new in words, the
deadline as the only wait and the rerun as a finding; *Release Policy*
rule 10 states the release obligation; the record of rule 9 became the
test-run record of both kinds, `test-runs.json`, with the candidate's
checksum on end-to-end entries, a notes section rendered from it, and a
check at the final tag. Schema, renderer and check are one implementation
slice with the rule 9 check. The owner then asked whether the last
candidate and the final are identical; checked on 0.3.0: `v0.3.0-rc9` and
`v0.3.0` point at the same commit, `475427da`, the workflow rebuilds the
final under its own version and proves the same source, frozen inputs
and base references against the accepted candidate's manifest, so the
bytes differ, `413b1d45` against `f59e05cd`, while everything that went
into them is the same. Hence the record lives on `main`, read as the
acceptance record is, keyed by source revision for integration runs and
by the candidate's checksum for end-to-end runs; a record in the tagged
revision would force a commit after the one the candidate was built from.

The seventeen stand as follows on 2026-11-06, after the sample
submodules left the tree: sixteen of the moved tests fail inside a capsule
as expected, thirteen for the mounted settings and three for the live
repository configuration; the three scope-word tests pass now that no
virtualenv sits under the resources; the workflow-parity test of
`tests/test_workflow_bootstrap.py`, marked non-blocking since 2026-08-22,
fails because the root and the packaged `WORKFLOW.md` differ; the
coordination claim test of 2026-09-22 passes when its two calls fall in
the same second. The repair is planned against the criterion above and
waits for the owner's rulings on its slices.

## The compatibility feed: website address, override, cache, built-in snapshot — 2026-11-05

Owner ruling: from 0.3.1 and its candidates the feed is read from the
website's domain, not from a repository; the address is overridable from
the command line for a check against the test site; the last successful
fetch is cached; a snapshot is built into the launcher; and under no
circumstances does a launcher fail to start because the feed cannot be
fetched. Checked first: the last point already held, the fetch being
bounded, caught and off the ordinary start path, and the cache existed per
project. The override and the snapshot did not exist.

Delivered on `ws-maintenance/status-feed-fallbacks`:

- `component_status.FEED_URL` is
  `https://devcapsule.mycodespace.ai/status/compatibility-v1.json`;
  `DEVCAPSULE_STATUS_URL` overrides it for every check and
  `project versions check --status-url` for one.
- The cache moved from each project's state to the cache home,
  `~/.cache/devcapsule/compatibility-v1.json`, so a new project starts from
  the newest feed the machine has seen. Lookup order: fetched, cached,
  built in; the report names the source.
- `scripts/build-pex.sh` generates the snapshot from
  `component-status/policy-v1.json` with the publisher's new
  `--without-probes`, asking no vendor, and packages it as
  `devcapsule/_compatibility-v1.json`. A snapshot is not a publication: its
  advisories apply within their own review windows, while a fetched or
  cached feed stays bound to its three-day validity.
- Unit tests in the `component_status`, `component_status_publisher` and
  `commands/versions` mirrors, against constructed feeds, no network.

Blocked, and the owner's ruling is needed before the first 0.3.1 candidate:
the website path does not exist yet. The production site is a promoted
candidate deployed whole by `deploy-pages`, so a file refreshed daily
cannot ride on it without changing how the site is published. Two ways
keep the ruling that the feed lives on the website's domain: the
component-status workflow pushes the feed into the website repository and
that repository's publish workflow redeploys production on such a push,
daily; or a subdomain, `status.devcapsule.mycodespace.ai`, served by a small
Pages repository the workflow pushes to. Until one exists, a 0.3.1 launcher
falls back to its cache, then its snapshot, on every check.
## Integration tests leave the gate — 2026-11-05

Owner ruling: the integration tests run on demand, as the end-to-end
suites do, never inside `nox -s build`, `nox -s tests` or a plain
`pytest`. The unit selection already deselected them through the
`integration` marker; `build` ran them through its packaging step. That
step is removed; `nox -s integration` stays as the on-demand session and
the release workflow keeps running them against the release executable.
`WORKFLOW-LOCAL.md`, the developer brief and the integration-test document
say so.

## The website and sample repositories move too — 2026-11-05

The production site went dark with a 404 from GitHub: the custom domain
had disappeared from the website repository's Pages settings while its
DNS and its last deployment were sound, and putting it back on a
repository under the personal account was refused, which is what the
organization's verification of `mycodespace.ai` does to any repository
outside it. At the owner's direction, the website repository was
transferred to the organization on 2026-11-05, keeping its settings, with
GitHub redirecting the old name. The five sample repositories were
transferred with it and transferred back the same day: the owner ruled
that no sample project moves, so they stay under the personal account
and the organization holds `devcapsule` and `devcapsule-website` only. The
production domain was set on `mycodespace-ai/devcapsule-website`, the last
promoted candidate was redeployed there, and the site answers again. The
owner then changed both DNS records to the organization's Pages host.

The owner ruled the same day that the sample projects are no longer
submodules of this repository: which samples users get to try DevCapsule
with, and in what form, is decided later, and probably not as submodules.
The branch `ws-maintenance/submodules-in-organization` therefore removes
the four sample gitlinks and their `.gitmodules` entries, with the pytest,
mypy and unit-test-gate exclusions that existed only for them, and points
the one remaining submodule, the website, and the two workflows that fetch
it at the organization.

One link in the publishing chain is broken by the move and is not yet
fixed: the promotion script of the website repository,
`scripts/candidate.mjs`, downloads candidates from
`ccozianu/devcapsule`. That is not a redirect: the personal repository
still exists, since this one was migrated branch by branch rather than
transferred, and a candidate built by the organization's repository
never appears there. The next promotion needs the script pointed at
`mycodespace-ai/devcapsule` first, a change in the website repository
together with its records that name the old owner. For the same reason
a checkout whose `origin` still names the personal repository pushes
there, silently; remotes are repointed by hand.

## The repository moves to the `mycodespace-ai` organization — 2026-11-05

The owner created the free organization `mycodespace-ai` and the empty
repository `mycodespace-ai/devcapsule`, and ruled the move branch by
branch: what git holds is preserved, nothing else. The reason is the
merge queue, which GitHub grants only to repositories an organization
owns; a personal repository can require a check on the pull request's
head but cannot run that check on the merged result before landing it.
`PR #338` merged with a red check and the seventeen tests of the section
above reached `main` the same way.

What moved on 2026-11-05: 26 branches, every one the old repository had
except the two stray `upstream/*` refs, and 44 tags, every one except the
`website-candidate-*` build tags. `main` is the default branch; merge
commits are the only merge method, deleted branches on merge and
auto-merge are on. Ruleset 26585527 guards `main`: no deletion, no force
push, changes through a pull request only, the `ci-gate` check required,
and the merge queue required, so a pull request enters the queue when
`ci-gate` is green on its head and lands only when `ci-gate` is green on
the merge commit the queue builds. `tests.yml` already runs on
`merge_group` and confines coverage publication to the pull request run,
so the workflow needed no change for the gate. The old repository had no
Actions secrets or variables to carry.

What did not move: the issues, the closed pull requests and the stars stay
at `ccozianu/devcapsule`, and the records keep linking to them. There is
no redirect. The website and the sample-project submodules are separate
repositories still under `ccozianu`, so `.gitmodules` is unchanged.

This branch renames the repository everywhere the live code and
documentation name it: the coverage and component-status workflow
conditions, the launcher's release page in `images/contract.py` and in
the settings-admission message, the component-status feed and page, the
trust note, the promotion script's default, the READMEs, the platform and
update docs, the compare link in `WORKFLOW-LOCAL.md` and the canonical
URL in the root status. The one legacy test asserting the release URL,
`test_minimum_refusal_precedes_content_and_command_diagnoses`, moved into
the `storage` mirror with the new URL and a docstring; the legacy test
data naming the old repository in `test_pycharm.py` and `test_wrap.py`
is left as data.

Open for the owner's ruling:

1. Launchers already shipped, 0.3.0 included, check for updates against
   `ccozianu/devcapsule` releases and read the compatibility feed from its
   `component-status` branch. Without a redirect they keep doing so. Either
   0.3.1 is also published there, with the feed branch kept current on both
   repositories for a while, or 0.3.0 users update once by hand. The old
   repository cannot be archived before this is ruled.
2. The Pages site `test-devcapsule.mycodespace.ai` is served by the old
   repository. The new one has no Pages site yet; the domain's DNS record
   must point at `mycodespace-ai.github.io`, then the domain is removed
   from the old repository and set on the new.
3. Whether `devcapsule-website` and the sample-project repositories move
   too. If they do, `.gitmodules`, the submodule URLs in the workflows and
   the website's own records follow in a second slice.
4. Every checkout renames its remotes; the owner's wrap checkout had the
   organization as `upstream` already.

## Seventeen tests expected to fail for reading the capsule — 2026-11-04

The owner ran the unit suite in the capsule after syncing
`ws-wrapped-projects/wrap` with `main` at `cc8f1288`: 17 failed, 2809
passed. A clean checkout of `main` fails the same tests, so no workstream
broke them; each reads a precondition from outside the test, which *Unit
Tests* rule 2 forbids. The owner's disposition: mark every one of them
expected to fail with the reason `TODO: fix the wrong approach to testing`
and assign the fix to this workstream. Three causes:

1. **The capsule's mounted launcher settings.** Inside a capsule
   `mounted_settings_path` in `devcapsule/runtime_configuration.py`
   answers `/etc/devcapsule/home/settings.toml` whenever the launch context
   file exists, and the owner's capsule has accepted the Claude Code
   download there. `private_user_directories` in `tests/conftest.py`
   redirects `HOME` and the XDG variables but has no hold on that path, so
   every test that assumes no accepted vendor channel sees one. Pointing
   `HOME_PATH` at an empty directory makes them pass. Thirteen tests:
   six in `tests/test_trust.py`, three in
   `tests/test_capability_commands_v2.py`, one each in
   `tests/test_capability_minimums.py`, `tests/test_console_channel.py`,
   `tests/test_environment_realization.py` and `tests/test_project_init.py`.
   This is the private-home fixture already noted in
   `engineering-docs/development/unit-tests.md` for the 0.3.1 fixture slice.
2. **The live repository configuration.** The three tests in
   `tests/test_repository_manifest_compatibility.py` load this checkout's
   `.devcapsule/devcapsule.toml`; the owner's uncommitted schema-2 rewrite
   renames `need` to `required` and they raise `KeyError`.
3. **An ignored directory under the resources.** `test_replaced_scope_word_is_absent`
   in `tests/test_home.py` walks `tests/resources` and finds a `.venv`
   inside the `fastapi-webapp` sample project, vendored pip sources included.

The marker is on the 14 functions (three are parametrized). As written in
the eight legacy files the convention gate refused it, 14 breaches of the
form `changed in a legacy file`, since rule 5 never marks a legacy test
expected to fail and the gate compares each function's source, decorators
included, with the base. The owner's second disposition: move the marked
tests out of the legacy files into the mirror, against a dummy target
where the unit has none. So each test left its legacy file verbatim, with
a one-line docstring naming its cause, and sits in
`tests/unit/devcapsule/legacy_refactoring/test_<legacy file>.py`, one
file per legacy file because their `project` fixtures and `config` and
`snapshot` helpers collide by name; each imports its fixtures and helpers
from the legacy module as the existing mirror files do. The targets are
the temporary package `devcapsule/legacy_refactoring/`, eight modules
holding no code but a docstring saying why they exist; each is deleted
when its last test is rewritten against its real unit, and the package
with the last module. The owner's worry at the merge, that the move undermines the safety
the bad tests still gave, is answered by the marker's condition: it is
`pytest.mark.xfail(IN_CAPSULE, ...)`, with `IN_CAPSULE` the presence of
the launch context file, so the tests are expected to fail only inside a
capsule, where they inherit its state, and run as the tests they were on
the hosted workflow and on any host. The one change to a body is in
`test_replaced_scope_word_is_absent`, whose path to `devcapsule-src` is
taken from the mirror file's deeper place. Verified in the capsule: `nox -s tests` green, the
checker at 108 legacy files holding 1447 legacy tests, 30 files following
the convention, 0 breaches; `nox -s typecheck` green. Nothing committed;
the move is in the owner's checkout.

Two environment findings from the same run, both for the owner:

- Under `devcapsule-src/.venv`, `tests/test_console_channel.py` fails 16
  tests that pass under the nox session's own environment. The venv's
  site-packages still carries `devcapsule-0.2.15.dist-info`, so a
  subprocess started outside `devcapsule-src`, as the console channel's
  `config` command is, reports itself as 0.2.15 and is refused by the
  0.3.0 home. The documented one-module command
  `.venv/bin/python -m pytest tests/<module>.py` is therefore unreliable in
  this checkout until the editable install is redone:
  `.venv/bin/python -m pip install -e . --no-deps` from `devcapsule-src`.
- The suite used about 215 MB of the capsule's 2 GB `/tmp`; no scratch
  relocation is needed.

## The first legacy test moves — 2026-11-04

The owner had marked `test_consent_names_the_contract_and_the_recipe_source`
expected-to-fail with a note to rewrite or eliminate it, the rc6 string pin
dissected on 2026-11-03. Under *Unit Tests* rule 5 the fix is the move: the
test leaves `tests/test_base_contract.py`, and its unit,
`devcapsule.configuration.authorization`, gains the mirror file
`tests/unit/devcapsule/configuration/test_authorization.py` with four
triples over constructed locks: the full declaration with contract, builder
and recipe permalink; a lock without a builder; a lock predating recorded
contracts with the legacy recipe path; a lock without a base. Every expected
value is derived from the lock the test built. Rule 4 applies to the unit:
the module now declares `__all__`. Checker: 110 legacy files, 1523 tests,
4 files follow the convention, 0 breaches. Delivered as
[PR #337](https://github.com/ccozianu/devcapsule/pull/337). The xfail stays uncommitted in
the owner's checkout until this merges and is dropped at the next sync.

## Coverage numbers in the pull request — 2026-11-04

The owner merged #335 at 650e2be3 and asked for the next slice from the
2026-11-03 question: the diff coverage and the overall coverage in the pull
request's summary, and later in the merge commit's detail. CI already
computed both, the overall figure into the job summary and diff-cover's
report into an artifact and annotations; nothing reached the pull request.

Delivered on `ws-maintenance/coverage-in-pr` as
[PR #336](https://github.com/ccozianu/devcapsule/pull/336) to `main`:
`scripts/publish_coverage_numbers_to_pr.py` reads `coverage.json` and
`diff-cover.json`, renders one block between `<!-- coverage-numbers:begin -->`
and `<!-- coverage-numbers:end -->`, and replaces that block in the pull
request's description through the REST API, appending it when absent; the
author's text is never touched. The pytest job gains `pull-requests: write`
and runs the step on pull requests after diff coverage. Its tests are the
third mirror file, 9 cases in triple form. The merge commit part needs no
code: the owner sets the repository's default merge commit message to the
pull request's title and description, and the block travels into `main`'s
history as it stands at merge time. The owner set it from the command line
the same day; verified through the API: `merge_commit_title` PR_TITLE,
`merge_commit_message` PR_BODY. Recorded under *Integration Method* in
WORKFLOW-LOCAL.md. The first run on #336 spliced the block into prose that
quoted the markers and reported 100% of zero measured lines; both fixed at
87bba34e, the second run appended the block correctly.

## Unit-test conventions — 2026-11-03

The owner resumed from travel and ran `nox -s build` in the dogfood capsule:
18 failures, 2711 passed, none a product regression. Thirteen tests read the
owner's accepted claude-code channel through the launcher's mounted settings
at `/etc/devcapsule/home/settings.toml`, which `settings_source` consults
whenever a home has no settings of its own and no named home; the autouse
isolation fixture moves HOME and XDG but deletes `DEVCAPSULE_CONFIG_HOME`,
so inside a capsule every test's private home falls back to the mount.
Four tests read the repository's own manifest and lock, which the owner's
checkout carries migrated to schema 2 against a local base build. One
scanned `tests/` for a forbidden word and hit a sample project's `.venv`.
Verified: the thirteen pass with the launch context hidden, the four pass
on a clean worktree of HEAD.

The owner's diagnosis, accepted: these tests state no contract. A hard-coded
value tests only that the file still says what it said; the precondition the
assertion hinges on was inherited from the machine. Measured over the
project's own suite: 1525 test functions, 61 with a docstring, 237 with more
than twelve lines before the first assertion, 29 asserting a version or
digest literal, 46 of 110 files named after a module; over the 0.3.0 cycle
the tests changed 13.3k lines against 12.7k in the product, with 9 of 402
commits touching tests alone. Pair review had endorsed the dissected test by
name and dismissed its private monkeypatch as "confined to tests".

Delivered on `ws-maintenance/test-conventions`, by owner order, as
[PR #335](https://github.com/ccozianu/devcapsule/pull/335) to `main`;
the owner merges:

- *Unit Tests* in `WORKFLOW-LOCAL.md`: mirror placement, the Hoare triple
  with the precondition established by the test, a docstring stating the
  contract, a declared public surface as the precondition of testability,
  the `legacy` marker on existing files that only shrink, fix-and-move on
  touch, the reviewer's duty in the Pair Review Loop. The humane companion
  carries the motivation.
- `scripts/validate_unittests_follow_conventions.py`, run in the `tests` and `build` sessions
  and as a `tests.yml` step against the PR's base SHA: placement, docstrings,
  and legacy files compared with the merge base. Its own tests are the first
  mirror file, `tests/unit/scripts/test_validate_unittests_follow_conventions.py`, 15 cases in
  triple form. Against the suite: 110 legacy files, 1525 legacy tests, 0
  breaches.
- All 110 existing test files marked `legacy`; the marker registered in
  `pyproject.toml`; the review brief template and the unit-tests guide
  updated, the guide's stale fixture list corrected.

Out of this slice, queued: the isolation fixture should set
`DEVCAPSULE_CONFIG_HOME` so a capsule's mount is never consulted (joins the
release-independent fixtures item); the shared `project`, `config` and
`record` helpers imported across test modules move to the unit tree's
conftest before legacy tests start moving; a workstream for the measured
refactor of the legacy debt, module by module, with the owner choosing the
module; frameworks for contracts and property-based testing to be decided
inside its first slice.

## Paused for travel — 2026-10-31

The owner requested a travel break. Maintenance is deliberately paused on
ws-maintenance/0.3.1-preparation. Final 0.3.0 artifacts and production website
are independently verified, the production handoff is complete, and no
release operation remains. The 0.3.1 queue below is preserved; implementation
has not started. No waiting mail was present at pause. Records are committed,
pushed and published; the active claim is released.

Resume only on the owner's return. Read Open Threads and the 0.3.1 preparation
queue, recheck remote/main and live coordination state, then settle the first
slice. Release-independent test fixtures remain the proposed starting point.

## 0.3.0 delivery complete — 2026-10-31

The owner confirmed production promotion complete ("All done"). Independent
HTTPS inspection of production build-info confirms current 0.3.0, content
31d44fa4 and the exact reviewed website-candidate-41188626026-1 with matching
bundle digest. [Evidence](../../releases/v0.3.0/website-verification.json).
No release handoff remains. Earlier pending-production statements below are
superseded. Maintenance remains on ws-maintenance/0.3.1-preparation; no new
implementation task was started by this release-closing checkpoint.

## 0.3.0 published; 0.3.1 preparation — 2026-10-31

Verified owner merge of #332 at main 31d44fa473a86f608110caa53ee38c6aef40a717.
Validated acceptance identity/ancestry, exact candidate documentation and
matching docs-0.3.0 tree before creating v0.3.0 at accepted RC9 source
475427da033633ff5ee0e44e09face700630bf36. No release synchronization or source
change was needed. Final publication succeeded in
[run 41188312058](https://github.com/ccozianu/devcapsule/actions/runs/41188312058).
[The release](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0) is
public, non-draft and final, with all three assets.

Independently downloaded/checksummed the final PEX and verified version,
mnemonic, source, embedded mainline acceptance, base and frozen build inputs.
Final PEX SHA-256 f59e05cdbb5ab157641aae5a27f269f963400a650c1ae3db1650e1881a6df714.
[Final verification](../../releases/v0.3.0/final-verification.json).
The release branch and tags are retained and closed for development. Local
release-side records remain at 4aedfb74; all their delivery reached main
through #332. Do not tag their tip or merge it over main's metadata.

At the owner's direction to prepare 0.3.1, selected a fresh branch
ws-maintenance/0.3.1-preparation from fetched main 31d44fa4. This is still
maintenance. Main already carries 0.3.1.dev0, so no version bump or release
branch cut is needed. Its current workflow and local rules are unchanged
apart from the intentional main development-version frontmatter. New status
and release-verification records travel with the next deliverable, and live
state is published on coordination; no administrative PR is opened.

Test-site run 41188626026 succeeded (build, deploy and candidate). Live
build-info and HTTP checks verify current 0.3.0, content main 31d44fa4 and
docs-0.3.0 at 7a813b80. [Website verification](../../releases/v0.3.0/website-verification.json).
The published candidate is website-candidate-41188626026-1, bundle SHA-256
feb14cb499782540f4d7b051122201650d787bb89cb76c217547702b60ab90ca.
The owner reviews test-devcapsule.mycodespace.ai and promotes this candidate
through devcapsule-website's Publish production website workflow. This is the
remaining release handoff; production deployment was not performed here.
Delivery/routing notice sent to project-management and website through
coordination mail at 35e5c6a599cd. GitHub Latest now resolves to v0.3.0.

### 0.3.1 preparation queue

| Item | Owner | Disposition / next action |
|---|---|---|
| Seventeen tests reading the capsule, the repository config or an ignored directory | maintenance | Marked expected to fail on 2026-11-04 at the owner's direction, reason `TODO: fix the wrong approach to testing`, and moved to `tests/unit/devcapsule/legacy_refactoring/` against the temporary targets in `devcapsule/legacy_refactoring/`. Next: rewrite each against its real unit, the private-home fixture first, and delete the targets as they empty. See *Seventeen tests expected to fail for reading the capsule* above. |
| [Release-independent test fixtures](../../bugs/devcapsule/2026-10-31-release-dependent-test-fixtures.md) | maintenance | Confirmed minor, target 0.3.1; proposed first implementation slice. Use stable fixtures for behavior tests and retain independent real-pin/historical-contract checks. |
| [October 25 documentation order](../../work-orders/2026-10-25-documentation-orientation-and-concepts.md) | maintenance | Parts A and B assigned to 0.3.1; plan their delivery against the now-complete 0.3.0 guides. |
| C17 generic project-operation instructions | workflow-improvements | Moved to 0.3.1 planning by the owner's final disposition; scheduling mail delivered at 6fe8ac4cfbb9. Do not implement from maintenance. |
| Nine September 28 documentation proposals | project-management / user-docs | Moved to 0.3.1 planning; item-level choices still pending, not blanket implementation approval. |
| Claude Code freshness | maintenance | Final check found 2.1.316 versus accepted 2.1.314; recheck the vendor before a 0.3.1 pin update. No new pin selected yet. |
| Image/cache cleanup and empty-cache IDE reuse | maintenance | Excluded from 0.3.0; revisit scope in 0.3.1 planning. The older bug target still needs reconciliation with the recorded deferral. |
| Remaining open bug triage | maintenance | Legacy-lock IDE replacement, JSON-help/retired-command hints, old-project compatibility proof, unchanged-manifest writes; targets remain unassigned. The old workstation-command record is stale after the delivered home API and needs evidence-based reconciliation. |

No 0.3.1 implementation, new release branch or candidate has been started.
The retained 0.9/1.0 bugs stay at their own targets; preparation does not
silently pull them into 0.3.1. The workstream intake contains only its README;
no mail waited at resumption. Earlier release sequences below are historical.

## Acceptance delivery PR #332 — 2026-10-31

[PR #332](https://github.com/ccozianu/devcapsule/pull/332),
ws-maintenance/0.3.0-acceptance -> main, delivers the canonical acceptance
record and accumulated post-tag audit. Initial head a5d88954. The promotion
helper redownloaded and verified RC9; protocol identity/ancestry validation
passes. Main's product code, build inputs, workflow files and docs are
unchanged; main remains 0.3.1.dev0. No repeat product suite is warranted
for this acceptance/evidence-only delivery; prior exact-artifact evidence
is retained. The release-side acceptance commit is 4aedfb74 (local only).
The main-derived branch avoids propagating release-only version metadata.

The owner merges #332. Then fetch and validate the record on remote main,
tag v0.3.0 at 475427da (not this PR's commit), and verify final publication.
No renewed acceptance or tag approval is needed. The temporary decision
state was removed after the durable outcome commit. Scheduling mail was
already sent; no other workstream files were edited.

## Final acceptance decision — 2026-10-31

The owner answered "Yes to both questions, let's move ahead" to decision
`2026-10-31-final-030-dispositions`. Recorded outcomes:

1. Move C17's remaining generic project-operation instructions and the nine
   undecided September 28 documentation proposals to 0.3.1 planning. They
   no longer gate 0.3.0. The proposals still require item-level decisions;
   this is not approval to implement all nine. Existing owners remain.
2. Accept exact RC9 with the documented provider/editor verification limits.
   Do not invent additional Claude/Antigravity authenticated tool actions or
   full IDE editor acceptance from this answer. Codex/PyCharm live use and
   the recorded automated, browser and lifecycle proofs remain the evidence.

Scheduling notice delivered to project-management, workflow-improvements and
user-docs through coordination mail at 6fe8ac4cfbb9. Their records remain
their own to reconcile.

This supersedes the older pending scope/acceptance statements below.
The six fixed maintenance bugs now close on their RC9 verification and this
acceptance; the cookie bug was already closed. Generated the machine-checked
[acceptance record](../../releases/v0.3.0.json) with prepare-promotion.py,
which independently downloads and checksum-verifies RC9. Its source remains
475427da033633ff5ee0e44e09face700630bf36. Mainline ancestry holds at 4b59b10d.

Delivery uses the release guide's separate acceptance-record path: commit
on the release branch, then carry only acceptance/audit records on
ws-maintenance/0.3.0-acceptance from origin/main. This avoids merging the
release's 0.3.0 metadata over main's 0.3.1.dev0. No release code or tag moves.
The machine-consumed acceptance record is a required promotion deliverable,
not an administrative records-only PR. The human merges this PR into main.
After verification of that merge, final tagging/publication is already
authorized. The owner then promotes the verified test website to production.

The 0.3.1 planning plate includes release-independent test fixtures, the
October 25 documentation order, C17/nine proposal decisions with their owners,
and a Claude 2.1.316 freshness review. Start ordinary 0.3.1 maintenance on a
fresh main-derived branch after final delivery; do not develop on the closed
release branch. This stays within the user-selected maintenance workstream.

## Final promotion requested — 2026-10-31

The owner requests final 0.3.0 publication and then preparation for 0.3.1.
After the host cleared the saved RC0 local-base override, the live capsule
matches RC9 and the new published base, including the exact fixed console
security code. Nine runtime inspection probes, unknown-subcommand diagnosis,
18 packaged cache/network regression cases, the published-PEX attached
recursive successor and a fresh Codium run-once host-network proof all pass.
See [final audit](evidence/2026-10-31-rc9/README.md#final-promotion-audit--2026-10-31).
The active checkout is still maintenance on release-0.3.0. Main remains
4b59b10d; its workflow difference is only the intentional development-version
frontmatter, so no synchronization is needed or allowed for this promotion.

A reviewable promotion draft with RC9 identity/checksum and ancestry baseline
3c91183ffd2130f6c7b40d2f9e3fd41588f977eb passes the protocol validator. It
remains outside Git until the explicit final-tag obligations are resolved.
Decision `2026-10-31-final-030-dispositions` is pending in capsule state:
(1) move C17 and nine undecided September 28 documentation proposals to 0.3.1
planning, or retain their 0.3.0 gate; (2) owner-confirm provider actions,
accept the documented coverage limits, or request further verification.
The October 27 scope record explicitly retains these obligations; the
October 25 deferral does not decide them. Do not infer an answer from the
request to release or from elapsed time. No final tag has been created.

Final freshness recheck: Codex 0.166.0 and Antigravity 1.4.12 still current;
Claude offers 2.1.316. Preserve tested RC9's 2.1.314 for this requested
promotion and record the newer version for 0.3.1. The existing 0.3.1 plate
includes release-independent test fixtures and October 25 documentation.
No 0.3.1 implementation or workstream switch has occurred yet.

Once dispositions arrive: persist them, generate the canonical acceptance
record with prepare-promotion.py, deliver it and these audit records on a
main-derived maintenance acceptance branch (separate record delivery allowed
by the release guide, preserving main's 0.3.1.dev0 metadata), and create the
PR. The owner merges into main under WORKFLOW-LOCAL.md; verify it, tag exact
RC9 source, await publication, download/check final assets, and verify the
test-site dispatch. The current user instruction authorizes final tagging
once those conditions hold; do not ask for publication approval again.

## RC9 published and downloaded verification — 2026-10-31

Owner merge of [#331](https://github.com/ccozianu/devcapsule/pull/331) verified
at main `4b59b10daede8b77ff7c7aee753b9df483d62458`; release remains
`475427da033633ff5ee0e44e09face700630bf36`. Returned this clean checkout to
`release-0.3.0`. No main-to-release synchronization: the approved integration
preserves main's development metadata, and the release source is already an
ancestor of main. The candidate gate passes with no unintegrated commits.

Tagged and published [v0.3.0-rc9](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc9)
at that release source. [Hosted publication](https://github.com/ccozianu/devcapsule/actions/runs/41181720227)
passed. Downloaded all three public assets and verified checksum, manifest,
version `0.3.0rc9`, mnemonic and source SHA. PEX SHA-256:
`413b1d45bac9c39b6fa5fab68090e43550c9e255108de48b387c50a715c4fcf2`.

Downloaded-artifact validation: ordinary E2E suite **8 passed** (129.38 s),
including component cache, exact executable delivery, runtime lifecycle and
clean-machine execution; shared-browser regression **1 passed** (22.90 s).
Two fresh projects use the fixed default base with one browser context;
tokenless console navigation/reload and noVNC reconnection pass, sibling
credentials are refused, and containers/project records are removed.
The blocking cookie bug is closed on this evidence. Existing locks still
require explicit refresh; noVNC uses a WebSocket token URL, not the console
cookie. See [downloaded verification evidence](evidence/2026-10-31-rc9/README.md#downloaded-rc9-verification).

These post-tag records are committed locally and published on coordination;
they travel with the acceptance integration, without a records-only PR.
The immutable RC9 tag stays at 475427da. This is candidate verification,
not final-release acceptance. Historical preparation statements below are
superseded by this checkpoint.

## Web-console port-scoped authentication cookie fix for 0.3.0 — 2026-10-31

SSH fetch verified owner merges of all five `0.3.0` user-documentation batches
into `release-0.3.0` at `338f94ab` (`#319` at `add23bb0`, `#321` at `031de0a5`,
`#323` at `b28af13d`, `#327` at `6a5d9803`, `#325` at `338f94ab`) and of
`4PR-10-release-0.3.0` (`#317`) into `main` at `ce08ebad`.

At the owner's direction on `2026-10-31`, filed and fixed blocking `0.3.0` bug
[`2026-10-31-webconsole-cookie-collides-across-ports.md`](../../bugs/devcapsule/2026-10-31-webconsole-cookie-collides-across-ports.md)
(`status: fixed`, `severity: blocking`, `target: 0.3.0`, `owner: maintenance`,
`requirements: [R-CONSOLE-001]`) on `ws-maintenance/0.3.0-webconsole-port-cookie`
targeting `release-0.3.0`:

- `devcapsule-webconsole/devcapsule_webconsole/security.py`: scopes session
  cookie names to the browser-facing port in the HTTP `Host` header
  (`devcapsule-console-token-<port>`, falling back to `devcapsule-console-token`
  when portless) so concurrent capsules on `127.0.0.1` no longer overwrite one
  another's cookie under RFC 6265 §8.5, and reads `;` cookie pairs directly
  across all `Cookie` headers so non-RFC2109 cookies set on `127.0.0.1` by
  sibling local applications cannot abort credential parsing.
- `devcapsule-src/devcapsule/_redaction.py`: widens `_CONSOLE_COOKIE_RE` to
  scrub suffixed `devcapsule-console-token-<port>=` cookies while keeping the
  cookie name and port readable in diagnostic exports.
- `docs/sessions/web-console.md`, `docs/sessions/several-projects.md`,
  `docs/troubleshooting/diagnostics-and-logs.md`, and
  `devcapsule-webconsole/README.md`: replace the multi-profile workaround note
  with the port-scoped `0.3.0` cookie behavior.
- Local validation passed: `374` web-console tests (up from `357`, including
  dual-port cookie jar isolation, live two-`uvicorn` + `http.cookiejar`
  loopback proof, IPv6/portless/malformed `Host` handling, HTTP/2 split
  `Cookie` headers, and sibling localhost cookies) and strict `mypy` (`9`
  files); runtime `mypy` (`264` files), syntax checks, CLI and PEX smokes, `18`
  packaging/install integration tests, `2,644` unit tests (`40` deselected, `1`
  `xfail`, `1` `XPASS`), `192`-page `docs-contract` (`18` aliases), and website
  build/check (`196` HTML pages, `14,636` links/assets/anchors, `23` tests).
- Next step: owner review and merge into `release-0.3.0`, propagation to `main`,
  and before the final `v0.3.0` tag, rebuilding and re-pinning the published
  `ubuntu-24.04@11` base image in `resolution_matrix.py` from a `0.3.0`
  candidate carrying this commit so non-self-hosting adopters receive the
  updated `/opt/devcapsule-webconsole` without building a local base.

## 0.3.1 test maintenance follow-up — 2026-10-31

Owner requested [release-independent behavioral fixtures](../../bugs/devcapsule/2026-10-31-release-dependent-test-fixtures.md)
for 0.3.1. Next action after 0.3.0: isolate generic CLI/contract tests from
current production pins and the repository lock; demonstrate reduced changed-file
count on a representative pin refresh while preserving independent assertions
and historical compatibility coverage. This does not expand the RC9 code slice.

## RC9 main integration — 2026-10-31

SSH fetch verified #329 merged into release at
`475427da033633ff5ee0e44e09face700630bf36`. Its tree matches tested preparation
head b6dd2335. Main remains ce08ebad. Created [PR #331](https://github.com/ccozianu/devcapsule/pull/331)
from `4PR-11-release-0.3.0`, an untouched copy at the release tip.

Prepared main integration on this maintenance working branch. Resolved three
conflicted metadata files: retain current RC9 status and main's nonconflicting
history; remove one identical duplicated Batch 1 section; keep promoted
0.3.0 documentation and omit devel's release-only source-version. The three
version declarations retain main's 0.3.1.dev0 without manual changes.
Main's existing explicit launcher-version fixtures in test_home.py and
test_settings.py are also preserved.
Product code and tests merge without conflicts. Release remains at 475427da.

The resolved main integration tree passed the full local gate under
0.3.1.dev0: 2,645 unit tests, 18 packaging tests, 374 console tests,
type/syntax checks, CLI/PEX smoke and documentation contract. Website
build/check passed (252 pages, 21,031 links/assets/anchors). Manual
resolution touches only the three metadata files. The main version
frontmatters, pyproject version and existing fixture fixes match origin/main.
The prepared correction is merge commit `cf34b85e95cea697428cc616e0a3a48704173ef2`.
The owner approved applying it in chat on 2026-10-31: "Approved go ahead".
This answers decision `2026-10-31-rc9-main-integration` and grants the narrow
exception to WORKFLOW-LOCAL.md Release Policy 8 for #331. Publish that tested
merge and this approval record to `4PR-11-release-0.3.0`; keep release at
475427da and main at 0.3.1.dev0. The copy is now an integration branch under
the explicit exception; never reset it back to the release tip.

Local gate evidence remains applicable: after cf34b85e only the root and
maintenance status records change. Hosted checks and the owner's main merge
remain before the candidate tag. Candidate acceptance uses the downloaded
published executable.

## Intended final candidate RC9 — 2026-10-31

**Cookie fix integration, 2026-10-31:** SSH fetch confirms
[PR #330](https://github.com/ccozianu/devcapsule/pull/330) merged to release at
`36b5e660`, carrying fix `3af21584`. Merged the release into this preparation
branch; the only conflict was this file's State line. Both the RC9
preparation and the parallel session's fix/verification records are retained. Workflow
files are identical to the preparation branch, so no definition update is
needed. The release branch itself is not synchronized or rewritten.

The owner selected **base-first** in decision
`2026-10-31-rc9-base-refresh`, answered 2026-10-31 at 02:14:16 UTC.
That sequence is complete: recipe 11 was rebuilt with the supported strict
public-source builder from commit `12a30fa60322de585810048881ee166fcdb26854`,
published as `mycodespaceai/devcapsule-base:v0.3.0-base-20261031`, and pinned
at `sha256:d7047ced8556cd35964fcc058a1101cf2b5b202f7a5daa2fdd434dcda5ed82c9`
in catalog embedded-31. Registry pull matches the built image. Only the
console layer differs from rc6, and its security module matches the merged
fix byte-for-byte. Old pins remain valid; existing locks are not rewritten.

Two real fresh-project capsules on that default pin passed one shared-browser
check: tokenless console navigation/reload, noVNC reload/reconnect, and refusal
of sibling credentials. Console cookies use browser-facing port suffixes;
noVNC uses its WebSocket token URL. Both test containers and their project
records were cleaned up. Evidence retains image lineage, sanitized facts
and screenshots. The base/concurrency hold on #329 is resolved.

Final local validation: full build gate passed (2,645 unit tests, 18 packaging
tests, 374 console tests, type/syntax/CLI/PEX/documentation checks), 112 focused
catalog/init/contract tests, concurrent browser regression (1 passed), and
website build/check (252 pages, 21,031 links/assets/anchors). The first gate
exposed a test assumption that every retained base pin increases the recipe
number; corrected to require identical contracts for same-recipe rebuilds.
The new pin's exact builder SHA supplies its recipe-source permalink.
Main remains ce08ebad and release 36b5e660; no new synchronization is needed.

Owner requests the intended final candidate after all PRs merge. Verified
main `ce08ebad` includes #317; release `338f94ab` includes all five user-docs
batches. Those documentation batches still need pre-candidate main integration.
The next unused tag is v0.3.0-rc9; no tag has been created. The owner selected
**upgrade** in `2026-10-31-rc9-agent-pins`, answered 00:50:18 UTC, and asked
also to check IDE updates because of security fixes. The choice and note
are preserved here before the console decision state is removed.

Current slice: `ws-maintenance/0.3.0-rc9-preparation`, based on release
`338f94ab`, for the required component pin updates, release notes and docs
promotion. The release remains the integration selection. Main has no newer
workflow definition to import; do not merge main into the release without
a new owner direction. The approved main-metadata adjustment is already
merged through #317 and must be preserved in subsequent main delivery.

Selected vendor stable versions: Codex 0.166.0, Claude Code 2.1.314,
Antigravity 1.4.12; PyCharm/IntelliJ/Rider 2026.2.4, VSCodium 1.143.17232,
VS Code 1.144.0. Eclipse Java stays 2026-09-R. All nine full downloads passed
vendor integrity checks. Catalog embedded-31 keeps prior pins for old locks.
The base refresh above supersedes the initial embedded-30 preparation.
No repository configuration migration was made. The running rc8
baseline validates the repository's existing schema-1 manifest and lock.

Initial component-refresh validation: full build gate passed (2,644 unit tests, 18 packaging tests,
type/syntax/CLI/PEX/docs checks, 357 console tests); 101 focused catalog/init
tests; 92 release-document tests; website check (252 pages and 21,031 links).
All three agents passed recipe-11 startup/seed checks. All five updated IDEs
passed desktop/console/window/pixel startup checks. Rider's SDK built and ran
the C# fixture; Rider/IntelliJ component browsers rendered HTML. JetBrains
screenshots stop at first-use agreements, VS Code at welcome/sign-in;
provider authentication and editor use are not claimed. See the
[evidence ledger](evidence/2026-10-31-rc9/README.md).

Notes and documentation promotion are ready: 0.3.0 current, 0.2.15 deprecated,
0.2.14/0.2.12 unsupported. `docs-0.3.0` was published at promotion commit `68b21a18`; docs-only commit
`7a813b80` adds #330's guide corrections, and its docs tree matches this
preparation branch. The
promotion itself remains on the release review slice until the owner merges. Deliver `ws-maintenance/0.3.0-rc9-preparation` into
`release-0.3.0`, then use the prescribed untouched release copy for the main
PR. The human merges both. Tag only after main disposition passes, then
verify the downloaded published PEX. Final acceptance still needs the
fixed-bug/provider checks and the C17/nine-doc-proposal dispositions from
the October 27 scope record. No candidate or final release is tagged yet.

Read-only merge-tree preview against main ce08ebad finds three record conflicts:
root CURRENT-STATUS.md, docs/versions.yaml, and this status file. Keep current
RC9 progress plus nonconflicting main history; use the promoted documentation
list but omit devel's release-only source-version on main. Main's authored
0.3.1.dev0 versions merge unchanged. Resolve the delivery method after release
integration: the prescribed untouched copy cannot receive correction commits
without owner direction (the #317 exception was specific to that PR).

Live main rules checked 2026-10-31: deletion and non-fast-forward prevention,
no required status check. `ci-gate` enforcement still requires the owner's
repository setting; workflow propagation did not configure it.

## User documentation 0.3.0 CLI alignment and prose review (Batch 1) — 2026-10-30

Implementation [PR #319](https://github.com/ccozianu/devcapsule/pull/319)
(`ws-maintenance/0.3.0-docs-batch-1-reference-updates-troubleshooting` ->
`release-0.3.0`) received Pair Review [PR #320](https://github.com/ccozianu/devcapsule/pull/320)
from `Codex (gpt-6-astra)`, accepted at `71243a0c` without a revision round and
merged at `0c0006c4`.

Batch 1 covers all 10 files in `docs/reference/` (3), `docs/updates/` (4), and
`docs/troubleshooting/` (3) under
[`2026-10-30-user-docs-0-3-0-cli-alignment.md`](../../work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
(merged to `main` in PR #316 at `ebab228a` and acknowledged from coordination
mail at `2d4aa223`), retiring two `status: planned` stubs
(`docs/reference/project-info.md` and
`docs/troubleshooting/cleanup-and-uninstall.md`) and folding in the human-prose
pass from `2026-10-24-maintenance-docs-language-review-before-0-3-0.md`.
Codex ran 106 CLI `--help` and isolated `DEVCAPSULE_CONFIG_HOME` probes across
all 10 files, confirming `supported-versions.md` and applying 13 source-verified
fixes across the other 9 files; two unimplemented CLI help/migration-hint gaps
(`STABLE_JSON_HELP` schema-1 string on schema-2 `config show --json`, and
missing replacement hints on `project config default` and mutating `project
config trust`) are filed as
[`2026-10-30-config-show-json-help-and-retired-home-command-hints.md`](../../bugs/devcapsule/2026-10-30-config-show-json-help-and-retired-home-command-hints.md);
see the [Batch 1 verification ledger](evidence/2026-10-30-docs-batch-1/README.md).
Next step: owner merge of PR #319 into `release-0.3.0`; Batch 2
(`docs/configuration/`, 10 files) proceeds on its own slice branch.

## Release-to-main integration — 2026-10-30

Owner requested a PR carrying everything currently on release-0.3.0 to main.
Opened [PR #317](https://github.com/ccozianu/devcapsule/pull/317), head
`4PR-10-release-0.3.0`, an untouched copy of the release tip under local
Release Policy 8. Read-only merge-tree preview against main `ebab228a`
found two conflicts: WORKFLOW.md (retain the Pair Review short name) and
the CI work order (retain the implementation evidence). Main's development
version remains 0.3.1.dev0; its final tree must omit the release-only
source-version override in docs/versions.yaml.

Owner authorized main-to-release synchronization on 2026-10-30 and
requested a PR to inspect the resolution. [PR #318](https://github.com/ccozianu/devcapsule/pull/318),
`ws-maintenance/0.3.0-main-sync` into `release-0.3.0`, contains merge
`fb8d8f10` with parents release `c2742621` and main `ebab228a`. This
owner-requested review branch is a temporary maintenance slice; the release
remains the workstream's integration selection. No merge is pushed directly
to the release branch. `git show --remerge-diff fb8d8f10` isolates the
resolution edits for the owner:
- retain the Pair Review short-name sentence and the explicit-trigger rule;
- retain CI implementation/acceptance evidence, acknowledge #312's merge,
  and use the local ast-grep proposal link now that its file is present.

The automatic merge carries main's accepted Pair Review naming and packaged
definition; a separate application of that accepted patch is no longer
needed after #318 lands. Other incoming work orders retain their own scope
and owners. All three source-version fields remain 0.3.0; docs/versions.yaml
keeps its release-only source-version override. No new tests are warranted
for these textual conflict resolutions. The full combined gate at `fb8d8f10`
passed: 2,644 unit tests (40 deselected, one xfail and one XPASS), 18 packaging
tests, 357 web-console tests, type checks, source/PEX smokes and the 192-page
documentation contract including 18 aliases. Log: local scratch
`/var/tmp/maintenance-ci/main-sync-gate.log`; counts are preserved here and
in PR #318. Only status records changed after this gate.

Owner merge of #318 verified at `9a412058` by GitHub and SSH fetch.
Its tree equals tested head `a2485dd4`. PR #317's untouched release copy
was fast-forwarded to that release tip; main `ebab228a` is an ancestor,
so the textual conflicts are resolved.

The owner explicitly authorized the four-file main-metadata correction on
#317's branch on 2026-10-30, a one-time exception to Release Policy 8.
Commit `2e8709ad` on `4PR-10-release-0.3.0` applies it: standard
`nox -s bump -- 0.3.1.dev0` updates pyproject.toml and both workflow
frontmatters; docs/versions.yaml loses its release-only source-version
override. The exact prepared patch was verified by reverse apply-check.
The release branch remains at `def205a4` with version 0.3.0. This copy is
now a main integration branch by the owner's exception; do not overwrite
its correction by resetting it to the release tip. This project-local rule
conflict needs clarification before the next release propagation.

The first main-version gate exposed three existing tests with hard-coded
0.3.0 launcher expectations (home display, settings round-trip, refusal
message). Runtime behavior correctly normalizes 0.3.1.dev0 to 0.3.1 and is
already covered by the release-comparison matrix. Commit `580b4ce0` gives
those three tests explicit 0.3.0 launcher inputs; both affected modules pass
39 tests. No runtime behavior changes. The final full gate at `580b4ce0`
passed: 2,644 unit tests (40 deselected, one xfail and one XPASS), 18 packaging
tests, 357 web-console tests, type checks, source/PEX smokes and the 192-page
documentation contract including 18 aliases, with devel correctly identified
as 0.3.1.dev0. Log: `/var/tmp/maintenance-ci/main-metadata-final.log`.
The earlier three-failure run is retained in `main-metadata-gate.log`.
Only status records changed after the successful gate. Hosted CI is linked
from #317; website verification passed and Python was still running at this
checkpoint. PR #317 is ready for owner review and merge after its checks pass. Existing documentation batch
status and dispositions from coordination have been preserved; these pending
PRs are not silently folded into this integration. No final
tag or publication was requested. Required ci-gate enforcement remains a
separate GitHub setting.

## CI path gating and advisory diff coverage — 2026-10-30

Owner merge verified by GitHub and SSH fetch: PR #312 merged into
`release-0.3.0` at `9eb500da4177e85aa4c4aa353e936327c2bded10` on
2026-10-30. Its tree equals the validated PR head `3aba7d04`; final hosted
run 40990774517 passed Python, website and ci-gate. No repeat gate is
needed for the unchanged tree. The clean maintenance checkout now selects
`release-0.3.0`, fast-forwarded to that remote merge; no main synchronization.
The mainline Pair Review naming change was read but remains the accepted
separate release patch. Required-check configuration and release propagation
to main remain open; the PR merge alone does not establish either.
This post-merge record is committed locally and published on coordination;
it travels with the next deliverable, with no records-only PR.

Implementation [PR #312](https://github.com/ccozianu/devcapsule/pull/312)
has received [review PR #314](https://github.com/ccozianu/devcapsule/pull/314),
accepted at `2dd3f14e` without a revision round and merged into the slice.
The implementor read the full diff and independently passed all 70 focused
tests. The reviewer fixed the annotated-tag pin, protected actual release-doc
inputs, guarded GitHub's 3000-file API limit and strengthened routing and
nested-path tests. The reviewer full gate passed: 2,644 unit, 18 packaging,
357 web-console tests and 192 documentation pages. The implementor’s final
combined gate at `0ea320e9` independently passed the same counts, type checks,
source/PEX smokes and documentation contract. Hosted run 40989994671 also
passed Python, website verification and ci-gate on that reviewed source.

Native Files changed placement is observed in a Chromium screenshot from
closed probe PR #313: a warning on lines 1–2 with 0% diff coverage and green
CI. Its fixture is absent from the implementation. Evidence is retained in
[the acceptance record](evidence/2026-10-30-ci-gating/acceptance.md).
The owner still must add required ci-gate; the release-targeted PR is merged.
No main/release branch was merged by the agent.


Owner-selected slice: implement the
[work order](../../work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md)
for 0.3.0 with GPT-6 Codex implementing and Claude Code / Claude Fable 5.1
reviewing through Pair Review. Owner decisions 1B and 2B bind: advisory
coverage without a percentage gate; serial tests, no parallelism work.
The owner merged the order's mainline PR #311 at `27f24fc6`. The exact order
is copied here for release delivery; no mainline source is merged.

Clean checkout `/home/devcapsule/worktrees/maintenance-ci`, from released
branch tip `000c8656` (PR #310). Main synchronization is forbidden for the
open release and is not performed. Read the changed mainline naming rule;
its delivered release patch is a separate accepted task below. The
owner-requested Pair Review uses a temporary slice branch
`ws-maintenance/ci-gating-030` targeting `release-0.3.0`, as prior release
slices did; the release remains maintenance's integration selection. This
resolves the overlap between topic 11.3's selection and topic 9.11's
required PR/review branches without reopening a closed maintenance branch.
The human merges the implementation PR into the release branch.

Acknowledged all three delivered items:
- CI gating and advisory diff coverage: implement now, then review and
  validate; reporting errors fail, low coverage does not.
- October 25 documentation proposals: retain Parts A and B for 0.3.1;
  canonical work-order and release-overview scheduling records now reflect
  the deferral. The separate
  language review, C16 and C20 remain 0.3.0 obligations.
- Pair Review Loop naming and packaged definition: accepted for 0.3.0,
  apply the supplied release patch as the next separate workflow slice
  after the CI review settles. Main PR #309 is already merged.

Implementation judgments: retain the existing hosted runtime suite and its
separate local console-gate contract; classify unknown paths conservatively;
use PR head for both measured coverage and annotation coordinates against
the event base SHA; keep the badge publisher separate. No Docker or new
hosted console suite is added. Native warnings are capped at ten per step;
complete reports remain in the artifact. Fifty-six focused tests passed,
including actual coverage/diff-cover execution below 85% without failure;
review expanded this to 70 focused tests, all passing.

GitHub settings inspected 2026-10-30 through the read-only API: the only
active ruleset is `main: no force push, no deletion` (25144717), with
`deletion` and `non_fast_forward` rules. Both main and release-0.3.0's
classic protection endpoints return `Branch not protected`. No existing
required CI check needs replacement. The owner must add `ci-gate` as required
after the representative hosted runs succeed; no settings are changed here.

Existing IDE and sample-project changes stay in the original PM checkout.
Claude availability check returned `claude-fable-5-1`; no API key is used.
Validation scratch uses `/var/tmp/maintenance-ci` because the configured
`/opt/devcapsule-gate` is unavailable; no container or service is needed.

## User documentation 0.3.0 CLI alignment and prose review (Batch 2) — 2026-10-30

Implementation [PR #321](https://github.com/ccozianu/devcapsule/pull/321)
(`ws-maintenance/0.3.0-docs-batch-2-configuration` -> `release-0.3.0`) received
Pair Review [PR #322](https://github.com/ccozianu/devcapsule/pull/322) from
`Codex (gpt-6-astra)`, accepted at `a082a710` without a revision round and
merged at `b7849132`.

Batch 2 updates all 10 `docs/configuration/*.md` files under
[`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
(merged to `main` in PR #316 at `ebab228a`) and folds in the human-prose pass
from `2026-10-24-maintenance-docs-language-review-before-0-3-0.md`, retiring
`status: planned` on `docs/configuration/ide-preferences.md` (complete 22-slot
IDE storage reference across `pycharm`, `intellij`, `rider`, `codium`, `vscode`,
and `eclipse`) and correcting `antigravity-cli` channel origin, `images build
--type base --tag`, missing `docs/configuration/index.md` guide links, and
leaked internal RC notes. Codex ran 46 `--help` calls and 68 isolated scratch
CLI probes across all 10 files and applied 11 source-verified refinements
(required-IDE `--force` links, console auto-applied restrictive authorizations,
`project info` runtime allowlist vs. `config show` declared inputs, `default`
vs. `none` value omission, `images list` columns vs. `devcapsule.source.revision`
label, and immediate directory checks on `bind`/`adopt`/`init --bind`); see the
[Batch 2 verification ledger](evidence/2026-10-30-docs-batch-2/README.md).
Two unimplemented CLI hint proposals surfaced during review are recorded for a
separate code slice: `_launcher.py:160-163` omits required `--tag` in the
printed `images build --type base` hint, and `project.py:1138` still prints
retired `config resolve` when non-software decisions accompany `config approve`.
Next step: owner merge of PR #321 into `release-0.3.0`; Batch 3 (`docs/README.md`,
`docs/getting-started/`, `docs/your-project/`, `docs/containment/` — 10 files)
proceeds on its own slice branch.

## Goal

Own defects no open workstream covers and drive maintenance releases. This
reserved workstream remains open for the lifetime of multiple-stream mode.
Its 2026-09-18 start is the recorded adoption exception.

## Explicit IDE requirement override — 2026-10-29

Owner direction of 2026-10-29: pick the
[work order of 2026-10-28](../../work-orders/2026-10-28-explicit-ide-requirement-override.md)
up from `main`, bring it into the 0.3.0 scope and implement it. The order
was delivered on `main` by PR #303 (`39dbb6ec`) with no implementation
owner and no release target; this workstream acknowledges it as its task,
release target 0.3.0, and the release overview's *Scope And Owner Decisions*
records the ruling. Work on `ws-maintenance/0.3.0-ide-override`, forked from
`origin/release-0.3.0` (`7545a536`, PR #301's merge), targeting
`release-0.3.0`, in `/home/devcapsule/worktrees/ide-override`, by Claude
Code, Claude Fable 5.1. The order's document and its `index.md` line came
onto the branch as one commit from `main`; nothing else of `main` was
merged, under the exception that the release branch synchronizes with
`main` on the owner's word each time.

Judgments taken, for the owner's review in the pull request:
1. The departure is a value, `RequirementDeparture(policy, capability,
   replacement)` with the one policy identity `ide-requirement`, carried
   in memory by the launch's `CheckoutState`; the manifest, the lock and
   the record are never written with it. Every derivation a launch uses
   takes the policy with that requirement set aside
   (`CapabilityPolicy.departing`): pin selection, composition, the usable
   lock, the listing, the resolution's baseline digest.
2. The records of the departure: the resolution's
   `[departures.ide-requirement]` table, the launch listing's IDE row
   (`this launch (--force); the project requires python-ide`) and note, and
   the stderr warning. A forced launch that exits 0 records no known-good
   generation and no proven version set, since it satisfied the developer,
   not the project. After a forced launch, commands that admit the
   on-disk resolution (`images build`, the recursive successor) ask for a
   plain `run`, which is honest and cheap.
3. `--force` is refused where it would select a replacement itself:
   without `--ide`, with the required IDE, on a project requiring no IDE;
   and with `--save`. The `--save` question was the order author's, Codex,
   not the owner's; on 2026-10-29 the owner ruled the refusal final: the
   developer must make up her mind, since saving the IDE beside a
   transient departure leaves a checkout that no longer launches plainly.
4. A second surface that a remaining capability's closure needs is
   refused by name in `usable_lock` (`Capability 'x' needs pycharm, an IDE
   that cannot accompany the selected IDE codium`) instead of the catalog's
   internal error; no catalog component has such a dependency today, the
   test monkeypatches one.
5. The saved-IDE conflict message of `compose_lock` now names the
   override too; its head is unchanged for the existing test.
6. `--force` replaces the retired spelling of the same name
   (`_retired_option`), `--force-config` stays retired.

Tests: `tests/test_ide_requirement_override.py`, 18 tests at the policy,
plan and CLI boundaries, the eight acceptance items of the order among
them; the built-executable flag propagation in
`tests/integration/test_pex_runtime.py`; the help and retired-spelling
expectations updated. Recorded acceptance session, 2026-10-29, inside this
capsule with the executable built from `fcf5c4e6`:
`nox -s ide-smoke -- --display --required-ide` passed in 50.5 s; the
refusal without force, VSCodium owning the display on the forced launch
(class `codium codium`, the fixture folder open), the unchanged project
files and checkout record, the forced plan's `departures` table, then
PyCharm owning the display on the plain launch (class `jetbrains-pycharm`)
with a plan without departures; see
[evidence/2026-10-29-ide-override](evidence/2026-10-29-ide-override/README.md).
Opened as [PR #304](https://github.com/ccozianu/devcapsule/pull/304) into
`release-0.3.0`. D-0016 records the owner's choice; R-CONFIG-001 gains the explicit launch
exception; the CLI reference, the capabilities guide and the IDE page
describe the flag; the 0.3.0 changelog carries it.

Pre-review gate passed: `nox -s build` and `webconsole` on `fcf5c4e6` with the records uncommitted: mypy clean on 263 source files; 2,559 unit tests passed, 40 deselected, 1 xfailed, 1 xpassed; the local executable built and smoked; 18 packaging tests passed; `docs-contract` 190 pages including 17 aliases passed; 357 web console tests passed, mypy clean on 9 files.

Post-merge gate passed on `3bfb3a16`, the slice with the review's PR #306 merged: mypy clean on 263 source files; 2,574 unit tests passed, 40 deselected, 1 xfailed, 1 xpassed; the executable built and smoked; 18 packaging tests passed; `docs-contract` 192 pages including 18 aliases passed; 357 web console tests passed, mypy clean on 9 files. The owner merged PR #304 into `release-0.3.0` at `cfa45937` on 2026-10-30.

## User documentation 0.3.0 CLI alignment and prose review (Batch 3) — 2026-10-30

Slice branch `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment`
(from `origin/release-0.3.0` at `c2742621`) updates 10 `docs/*.md` files across
`docs/README.md` (1), `docs/getting-started/` (3), `docs/your-project/` (4), and
`docs/containment/` (2) under
[`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
and folds in the human-prose pass from
`2026-10-24-maintenance-docs-language-review-before-0-3-0.md`.

Key changes:
- Authored `docs/your-project/declare-needs.md` and
  `docs/your-project/services-and-ports.md` in full (`status: planned` retired
  on both), covering schema-2 manifests and platform locks, all 17 catalog
  capabilities, `require`/`offer`/`drop`/`recommend`, `init --regenerate`,
  `config check --manifest --lock`, loopback `--publish=127.0.0.1:PORT:PORT` vs.
  `network host`, and host/Testcontainers/embedded service patterns.
- Updated `docs/README.md` (retired `"coming soon"` notice, refreshed section
  links), `docs/getting-started/install.md`, `first-session.md` (exact `0.3.0`
  `project init` prompts including `antigravity-agent` default and recipe-11+
  web console URL), `stop-and-come-back.md` (corrected container process
  restart wording), `existing-repository.md` and `new-project.md` (added
  `eclipse-ide`, `dotnet-ide`, component-name IDE aliases, and `checkout
  register`), and `the-boundary.md` / `granting-and-withdrawing.md` (`config
  deny` 5-node scope vs. `authorize <vendor>-download false`, `default`/`none`
  keywords, `vscode-download`); see the
  [Batch 3 verification ledger](evidence/2026-10-30-docs-batch-3/README.md).
- Opened [PR #323](https://github.com/ccozianu/devcapsule/pull/323) against
  `release-0.3.0`, dispatched `Codex (gpt-6-astra)` under
  [`review-brief.md`](evidence/2026-10-30-docs-batch-3/review-brief.md),
  accepted [PR #324](https://github.com/ccozianu/devcapsule/pull/324)
  (`f218a6d5`, 10 source-verified fixes across all 10 files) without a revision
  round, and merged it at `18728ce8`.
- Recorded unimplemented Batch 5 follow-up (`docs/sessions/what-persists.md:8`
  mount-scope wording); post-merge gate passed (`docs-contract`: `192` pages;
  `website.sh build && check`: `23` tests, `196` HTML pages, `14,449`
  links/anchors; `pytest -q -k release_docs`: `92` passed; `nox -s smoke`:
  passed). Ready for owner merge into `release-0.3.0`; next step: execute Batch
  4 (`docs/everyday-development/` + `docs/working-with-ai/`, 10 files, 5 stubs).

## Diagnostics snapshot and export — 2026-10-27

Owner-directed work on `ws-maintenance/0.3.0-diagnostics-snapshot`, forked
from `origin/release-0.3.0` (`5585e09d`), targeting `release-0.3.0`, with
Codex (`gpt-6-astra`) as the review partner under topic 9.11. Recorded
outcomes of console decision `2026-10-27-session-direction` before removing
its state file: `next-slice = diagnose-slice` (Deliverable 4 and the manual
browser-evidence contract of Deliverable 5 in
[2026-10-08-persistent-session-diagnostics.md](../../work-orders/2026-10-08-persistent-session-diagnostics.md)),
`checkout-alignment = clean-worktree` (keep `/workspace/301e4208ef81-ChatGPT_Codex`
untouched on `ws-maintenance/e2e_videos-2` with its pre-existing `.devcapsule/`
and `.idea/` edits; work in `/home/devcapsule/worktrees/diagnostics-snapshot`),
and conditional item `workstation-cli-home` skipped as not applicable (#287
already merged). Under topic 5.4.3, local `main` fast-forwarded cleanly to
`origin/main` (`0\t219` commits, empty `git cherry main origin/main`, now
`8afa5f6dfa0cef54e8649f008b5f3f26181bcf59`).

Judgments and scope settled with the owner before implementation:
1. CLI surface: `devcapsule project diagnose` (`CapsuleAccess.INSPECTS`),
   supporting `--path <dir>`, `--session <id>` (defaults to the active running
   session, or the latest ended session when none is running), `--json`
   (`schema-version: 1`), `--export [PATH]` (atomic mode-`0600` `.tar.gz`),
   and `--include-ide-logs` (requires `--export`; IDE-native logs `idea.log`,
   VSCodium `logs/`, and Eclipse `.metadata/.log` are excluded by default
   because they can contain source excerpts, while `snapshot.json` records
   their paths, file counts, and byte sizes).
2. Bounded stdlib-only probing: `devcapsule runtime diagnose-probe` scans
   `/proc` (supervisor, `Xvnc`, `openbox`, `tint2`, parent `websockify`,
   `novnc-worker` children, stopped `T` processes, `Z` zombies, and redacted
   `argv`), reads cgroup v2 (`memory.current`, `memory.max`, `memory.peak`,
   `memory.events` `oom`/`oom_kill`, `cpu.stat` throttling, `cpu.max`, `pids`),
   inspects sockets/listeners, and runs 2-second monotonic probes labeled with
   `User-Agent: devcapsule-diagnose/<version>` and `X-DevCapsule-Diagnostic: 1`
   on `rfb.sock` (verifying the 12-byte `RFB 003.008\n` greeting), `/vnc.html`,
   authenticated `/websockify` (WebSocket `101` upgrade plus the first RFB
   greeting frame, reading `/run/devcapsule-display-token` in memory only),
   and web console `/` (`X-DevCapsule-Token` in memory). Host collection runs
   bounded `docker inspect` (3 s, extracting `Config.Env` variable names only,
   never values, and degrading cleanly when `--rm` removed the container),
   `docker exec` (5 s), and host-loopback HTTP probes (2 s).
3. Redaction and honesty boundaries: scrubs `?token=`, URL-encoded `token%3D`,
   `devcapsule-console-token` cookies, `Authorization`/`Cookie`/`Set-Cookie`/
   `X-DevCapsule-Token` headers, secret CLI flags, inline secret assignments,
   and saved checkout Docker environment values across `snapshot.json`,
   `session.json`, `.log`, and `.log.<n>.gz` files; states explicitly that
   arbitrary child output and IDE logs are not universally scrubbable; sets
   `browser_evidence.collected = false` (`mode: "manual-devtools"`) and
   documents manual DevTools capture in `docs/troubleshooting/diagnostics-and-logs.md`.
4. Dogfood test-isolation fix included: isolated `runtime_configuration.CHANNEL_PATH`
   in the synthetic in-capsule fixtures of `tests/test_checkout_commands.py`
   and `tests/test_version_sets.py` so they do not read the outer rc8 capsule's
   mounted `/run/devcapsule-configuration/listing.json`.

Pre-review gate passed on `c0bec50d`: `nox -s build` + `webconsole` (`mypy`
clean on 254 source files and 9 webconsole files; 2,347 unit tests passed, 37
deselected, 2 xfailed; 17 packaging tests passed; `docs-contract` 189 pages
passed; 357 webconsole tests passed) plus real-container E2E fault-injection
test `tests/e2e/test_session_diagnostics.py` (1 passed in 16.73 s: live healthy
probes, `SIGSTOP` `Xvnc` hang proving `/vnc.html` 200 and socket accept are
not mistaken for health, `SIGCONT` recovery, Ctrl+C exit 130 + `--rm`, and
post-mortem mode-`0600` `.tar.gz` with zero token leakage). Opened
[PR #293](https://github.com/ccozianu/devcapsule/pull/293) against
`release-0.3.0` and committed the review brief at
[brief-pr293-1.md](evidence/2026-10-27-diagnostics-snapshot/brief-pr293-1.md).

Codex (`gpt-6-astra`) delivered
[PR #295](https://github.com/ccozianu/devcapsule/pull/295) (`c190d1cf`),
accepted without a round and merged into `ws-maintenance/0.3.0-diagnostics-snapshot`
at `5cc52392`. The review added nine substantive hardenings and 33 new focused
regression checks (42 total in `test_diagnostics.py` and
`test_runtime_diagnose.py`):
1. Extended `_redaction.py` and `_sanitize_plain_bytes` to cover bare `TOKEN`
   keys, quoted inline values, `%`-bearing encoded tokens, and structured JSON
   credential fields while keeping non-secret path keys and `token_gate_active`.
2. Verified live container state across unfinished sessions from newest to
   oldest so a newer crashed session cannot shadow an older live container.
3. Replaced manifest text reads with a bounded 1 MiB `O_NOFOLLOW | O_NONBLOCK`
   regular-file reader refusing FIFOs, symlinks, and oversized manifests.
4. Added descriptor-pinned `_open_directory` traversal and `.absolute()` path
   preservation so ancestor symlinks and post-discovery directory-to-symlink
   swaps are refused on read.
5. Unified snapshot and archive writes under `_private_output` (`dir_fd`-pinned
   mode `0600` creation, atomic replacement, guaranteed scratch cleanup).
6. Bounded IDE log discovery at `MAX_IDE_LOG_ENTRIES = 4096` via lazy
   `os.scandir` and documented the limit in `docs/troubleshooting/diagnostics-and-logs.md`.
7. Preserved buffered WebSocket bytes across split or coalesced TCP reads,
   replied to Ping (`0x9`) with masked Pong (`0x8A`), and rejected malformed or
   masked server frames.
8. Anchored archive session identity to validated `session_dir.name` and
   stripped `.` in `_safe_slot_dir`, closing tar-slip injection from a mutated
   in-capsule `session.json`.
9. Converted `OSError` failures in `ProjectDiagnoseCommand.run` into redacted
   `DiagnosticsError` CLI errors (exit code 2).

Reviewer proposals not implemented (for owner consideration on a future slice):
1. Add an overall runtime-probe deadline budget that preserves partial probe
   results when multiple sequential 2 s probes time out inside the 5 s outer
   `docker exec` timeout.
2. Distinguish unlimited cgroup v2 `"max"` values from unreadable cgroup limit
   files in the snapshot schema (both currently serialize as `null`).
3. Automatic browser-side console/network capture (outside this slice per
   Deliverable 5's manual DevTools contract).

Post-merge gate passed on `5cc52392`: `nox -s build` + `webconsole` (`mypy`
clean on 254 source files and 9 webconsole files; 2,380 unit tests passed, 37
deselected, 1 xfailed, 1 xpassed; 17 packaging tests passed; `docs-contract`
189 pages including 17 aliases passed; 357 webconsole tests passed) and
real-container E2E `tests/e2e/test_session_diagnostics.py` against the newly
built `dist/devcapsule-local.pex` (1 passed in 21.15 s). Slice state:
integrating; [PR #293](https://github.com/ccozianu/devcapsule/pull/293) is
ready for the owner's merge into `release-0.3.0`.

## User documentation 0.3.0 CLI alignment and prose review (Batch 4) — 2026-10-30

Slice branch `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai` (from
`origin/release-0.3.0` at `c2742621`) updates 10 `docs/*.md` files across
`docs/everyday-development/` (5) and `docs/working-with-ai/` (5) under
[`2026-10-30-user-docs-0-3-0-cli-alignment.md`](https://github.com/ccozianu/devcapsule/blob/main/engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
and folds in the human-prose pass from
`2026-10-24-maintenance-docs-language-review-before-0-3-0.md`.

Key changes:
- Authored all 5 `status: planned` stubs in full (`status: planned` retired):
  `docs/everyday-development/git.md`, `docs/everyday-development/run-debug-test.md`,
  `docs/everyday-development/previews-and-ports.md`,
  `docs/working-with-ai/hosted-and-local-models.md`, and
  `docs/working-with-ai/review-and-change-agents.md`.
- Updated `ides-and-terminals.md` (`config ide`, `use frontend-ide vscode`,
  `run --ide codium --force` departure behavior, Eclipse `/ide-workspace`,
  Rider/`dotnet`), `clipboard-and-browser.md` (`host-browser` broker and `F11`
  fullscreen), `choose-an-agent.md` (`role: agents` preserved, retired stale
  pre-`0.3.0` personal-agent trust limit, added web-console `add` and writable
  `.git` guidance), `sign-in-and-defaults.md` (`codex/openai-api-key` and
  `antigravity-cli/gemini-api-key` secret bindings, `host-browser`, seeded
  settings), and `instructions-for-agents.md`; see the
  [Batch 4 verification ledger](evidence/2026-10-30-docs-batch-4/README.md).
- Opened [PR #325](https://github.com/ccozianu/devcapsule/pull/325) against
  `release-0.3.0`, dispatched `Codex (gpt-6-astra)` under
  [`review-brief.md`](evidence/2026-10-30-docs-batch-4/review-brief.md),
  accepted [PR #326](https://github.com/ccozianu/devcapsule/pull/326)
  (`5f734995`, 15 source-verified fixes across all 10 files) without a revision
  round, and merged it at `65fa4958`.
- Recorded unimplemented proposals (residual `_launcher.py` `GIT_USER_NAME` /
  `GIT_USER_EMAIL` forwarding under `inherit_legacy_configuration=False`, Batch
  5 follow-up on `docs/sessions/what-persists.md:18` Antigravity credential
  scope, and `bash -n` docs-contract check); post-merge gate passed
  (`docs-contract`: `192` pages; `website.sh build && check`: `23` tests, `196`
  HTML pages, `14,471` links/anchors; `pytest -q -k release_docs`: `92` passed;
  `nox -s smoke`: passed). Ready for owner merge into `release-0.3.0`; next
  step: execute final Batch 5 (`docs/sessions/`, `docs/collaboration/`,
  `docs/platforms/`, 9 files, 2 stubs).

## General saved Docker arguments — 2026-10-23

The owner broadened PR #253 before merge, then requested the same reviewer
for the implementation. Accepted the superseding
[work order](../../work-orders/2026-10-23-saved-docker-arguments.md).
One private JSON argument list replaces the experimental env-file store;
set-env remains a hidden-input convenience over that list. GPU options,
mounts and other raw options persist with token order intact. One-off options
follow saved options; Docker owns duplicate semantics. Inline env values are
masked in listings and printed previews; actual Docker arguments are unchanged.
The generalization gate passed: 1756 unit tests, 36 deselected, one xfail and
one xpass; 17 packaging tests; 293 webconsole tests; docs contract passed.
Focused tests passed (31 storage/argument checks and 15 renderer/argument checks).
A fake-value Docker probe proved literal tokens, empty values and one-off env
precedence on the existing recipe-11 base. No GPU execution was tested.
Claude Code / Claude Fable 5.1 delivered
[PR #255](https://github.com/ccozianu/devcapsule/pull/255), accepted at
`af39c59` after two revision rounds and merged into this branch. The review
masked the persistent launch session log, refused ambiguous environment
convenience operations before writes, handled overlapping split-token
candidates in redaction, and closed attached launcher-owned short spellings.
The implementor independently ran the six affected test modules: 319 passed.
The reviewer's final gate passed: 1769 unit tests, 36 deselected, two xfails;
17 packaging tests; docs contract 188 pages; 293 webconsole tests. The second
xfail is the known non-strict clock-dependent workflow claim test, which
xpassed in earlier runs.

Review evidence: [initial brief](evidence/2026-10-23-checkout-env/general-review-brief.md),
[round 1](evidence/2026-10-23-checkout-env/general-round-1.md),
[round 2](evidence/2026-10-23-checkout-env/general-round-2.md).
The final combined `nox -s build` gate passed: 1769 unit tests, 36 deselected,
one xfail and one xpass; 17 packaging tests; docs contract 188 pages;
293 webconsole tests. Log: `/tmp/checkout-args-final-gate.log` (temporary).
Slice state: integrating, ready for the human merge. The review checkout
was clean and has been removed with its merged local branch. No maintenance
mail was pending at handoff; publish and claim release follow this record.

Retained limits: the existing raw-option warning stays; ambiguous saved
lists still launch literally, but environment convenience commands refuse
rather than guess Docker's option schema. The helpers recognize the five
documented separate environment spellings, not environment letters inside
short-option clusters; such clusters pass through without masking. The user
page now states this boundary. No actual GPU execution, full IDE launch or
real credentials were used. No unanswered product choice blocks delivery.
Next: the human merges PR #253 into release-0.3.0, then host dogfooding with
application settings. Release tip and workflow are unchanged; no main merge
is needed. The previous env-file validation record below is historical,
superseded by this slice's work order and final evidence.

## Checkout environment slice — 2026-10-23

Owner-directed work on `ws-maintenance/0.3.0-checkout-env`, from release tip
`fb1970e`, targeting `release-0.3.0`. The owner explicitly authorized leaving
the completed e2e_videos branch. The original checkout's IDE changes remain
untouched. Accepted [work order](../../work-orders/2026-10-23-checkout-environment.md).
Implementation ready for the Claude Fable 5.1 PR review loop. The full gate
passed: 1732 unit tests, 36 deselected, one xfail and one xpass; 17 packaging
tests; docs contract 188 pages; 293 webconsole tests. Follow-up focused checks
passed (14 environment tests; 20 combined checks before the added CR case).
A Docker probe against the existing recipe-11 base passed literal values,
empty values and explicit --env precedence, using fake credentials only.
No full IDE launch or real service credentials were used.
Review brief: [implementation review](evidence/2026-10-23-checkout-env/review-brief.md).
[PR #253](https://github.com/ccozianu/devcapsule/pull/253) is the implementation.
Claude Code / Claude Fable 5.1 delivered
[PR #254](https://github.com/ccozianu/devcapsule/pull/254), accepted at `65bed97`
without a round and merged into the implementation branch. The review fixed
record lookup triggering unrelated recovery, validation after the optional
upgrade offer, corruption/OS error messages and absent-key rewrites. It added
lock-contention, registration, runtime-routing and broader no-disclosure tests.
Its full gate passed: 1745 unit tests, 36 deselected, one xfail and one xpass;
17 packaging; 188 docs pages; 293 webconsole. The implementor independently
ran 98 focused tests, all passed. The final full gate on the combined tree
passed too: 1745 unit tests, 36 deselected, one xfail and one xpass; 17 packaging
tests; docs contract 188 pages; 293 webconsole tests. The clean review checkout
and its merged local branch were removed. Slice state: integrating, ready for
the human to merge PR #253. Next: merge into release-0.3.0, then exercise the
commands on the host with real application settings during candidate dogfood.
No tag, candidate publication or mainline integration is implied by this PR.

Review limitations retained: env-file validation follows the earlier software
approval offer; list-env uses the existing host-only MUTATES guard, whose
message calls configuration read-only; use the hidden prompt for values that
begin with a dash because the shared CLI handles `--` as passthrough. The
managed format intentionally rejects comments and bare names rather than
silently importing host environment values. No wider parsing/guard change is
part of this slice. A cosmetic index spacing suggestion needs no follow-up.

Review environment finding: placing pytest scratch under the mounted home
makes `test_unmountable_staging_fails_loudly` see a mountable path. The reviewer
passed the gate with `/tmp/checkout-env-review-scratch`. Its first gate log
was inside the pytest scratch and was removed by pytest; gate logs must be
outside basetemp. Final validation uses tmpfs scratch and an external log. No merge from main is planned: this is a release slice based on
the current release tip, whose workflow and approval changes are already
present. The release branch is not synchronized or rewritten.

## User Documentation 0.3.0 CLI Alignment — Batch 5 (`sessions/`, `collaboration/`, `platforms/`) — 2026-10-30

Slice branch: `ws-maintenance/0.3.0-docs-batch-5-sessions-collab-platforms` ([PR #327](https://github.com/ccozianu/devcapsule/pull/327) targeting `release-0.3.0`, final batch of [2026-10-30-user-docs-0-3-0-cli-alignment.md](../../work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)).

- Updated 9 `docs/*.md` files across `docs/sessions/` (5), `docs/collaboration/` (1), and `docs/platforms/` (3), retiring the final 2 `status: planned` stubs (`docs/sessions/several-projects.md` and `docs/sessions/another-machine.md`) so all 49 `docs/**/*.md` files and all 12 stubs across Batches 1–5 (`#319`, `#321`, `#323`, `#325`, `#327`) are complete with zero overlaps.
- Pair Review [PR #328](https://github.com/ccozianu/devcapsule/pull/328) (`PR327.1` by `Codex / gpt-6-astra`, `59bc1bae`) reviewed all 9 pages against `devcapsule-src/` and `devcapsule-webconsole/`, verified `macos.md` clean, and fixed 8 pages (`256 MiB` default log budget in `what-persists.md`, `HomeDefaults` keys `memory`/`cpus` and URL-encoded `<creator>/<slug>` paths in `another-machine.md`, `project list` host vs runtime scope and `DEVCAPSULE_CONFIG_HOME` isolated homes in `several-projects.md`, home-wide console `trust` scope, `env set` leading-dash rule, and `HttpOnly; SameSite=Strict` RFC 6265 host-shared cookie behavior in `web-console.md`, `--workstream` subcommand scope and `project-management` non-forwardability in `working-in-workstreams.md`, and ephemeral port wording / 3-command check scope in `start-stop-reconnect.md`, `linux.md`, and `windows-wsl2.md`). Verified independently, accepted without a round, and merged (`edcab618`).
- Unimplemented runtime proposal from PR #328 (out of scope for docs slice): isolate web-console authentication cookies per console instance/port so multiple consoles opened on `127.0.0.1` in one browser profile do not overwrite `devcapsule_console_token`.
- Post-merge validation passed: `docs-contract` (`192` pages), `./scripts/website.sh build && ./scripts/website.sh check` (`23` tests, `196` HTML pages, `14,462` links/assets/anchors), `92` `release_docs` unit tests, `nox -s smoke`, and `bash -n` on all 17 shell blocks. Ready for owner review and merge alongside PRs `#319`, `#321`, `#323`, and `#325`.

## The CLI UX redesign in rc4 — 2026-10-24

The owner answered the
[CLI UX redesign work order](../../work-orders/2026-10-24-cli-ux-redesign.md)
on 2026-10-24: items 1 to 9 in their words, items 10 to 24 as the agent's
proposals accepted for implementation, the release 0.3.0 rc4 (item 8), and
directed the implementation through the review-partner loop with the Codex,
gpt-6-astra pair, as a stack of pull requests to `release-0.3.0`. The stack,
one slice per pull request, each stacked on the previous, each with its
own review loop and brief under `evidence/2026-10-24-cli-ux/`:

0. **The work order itself**, `ws-maintenance/cli-ux-0-work-order`: the
   document and its records, reviewed in #258/#259 on `main`, carried here
   because the implementation lands on the release branch.
1. **The manifest, schema 2, and the owner's commands**: one writer with
   bare keys and the leading comment block kept; `[environment.required]`
   and `[environment.optional]` with reasons; `[recommendations]` for the
   IDE, memory and CPUs; `config require|offer|drop tool|env`, `config
   recommend`; `init --require/--offer/--ide/--agent` writing the new form
   with a project-only lock; `need` read, never written.
2. **The checkout's choices and the truthful listing**: `config ide`,
   `agent add|remove`, `tool omit|restore`, `set NAME VALUE|default`,
   `authorize|deny|forget`, `env`, `docker-args`; launcher-owned `memory`
   and `cpus` with workstation defaults; `config show` with EFFECTIVE,
   SOURCE and PENDING, computed, writing nothing; exit code 3 for a pending
   decision.
3. **`run` derives, reports and asks**: the resolve step retired, the
   resolution regenerated by `run`; the first launch asks what is pending,
   or exits 3 without a terminal; `--ide --agent --memory --cpus --env
   --authorize --save`; the second checkout registered by itself; a new
   mandatory need against a saved version set; `init` ends ready to run.
4. **Workstation trust and host access**: the D-0011 trust record, one
   acceptance per channel and vendor per workstation, replacing per-checkout
   base-image and vendor-download consents; D-0012's silent secure defaults,
   host X11 only by explicit consent, a recorded answer never re-asked.
5. **The console writes through the launcher**: a mounted request
   directory with write-then-rename files, the launcher applying each for
   the next launch, its computed listing mounted for the capsule's own
   `config show`.
6. **Removals, documentation, changelog**: Part 4 of the work order, the
   user pages, the command reference, rc4's changelog section.

Slice 0 is #260. Slice 1 is #261, `ws-maintenance/cli-ux-1-manifest`,
delivered 2026-10-24: 1813 unit tests, 36 deselected, one xfail and one
xpass; mypy clean; 37 new tests; its brief is
[brief-pr261-1.md](evidence/2026-10-24-cli-ux/brief-pr261-1.md). The
Codex gpt-6-astra pair's PR261.1 is #262, accepted at `468b1a2` without a
round and merged at `45bbf61`: the writer dropped root scalars and typed
extension values and left DEL unescaped; a manifest-only promotion rewrote
the lock; owner edits dropped unknown fields; init wrote shared files before
the consent batch failure; the rc3 flag mapping mishandled component aliases;
64 regression cases; the reviewer's gate 1877 unit tests, mypy clean.
Slice 2 is #263, `ws-maintenance/cli-ux-2-checkout`, delivered 2026-10-24:
1899 unit tests, mypy clean, 33 new tests; its brief is
[brief-pr263-1.md](evidence/2026-10-24-cli-ux/brief-pr263-1.md). Its
PR263.1 is #264, accepted at `49ebac4` without a round and merged at
`1451c94`: inspection no longer recovers an activation; a cpus edit keeps
legacy memory answers; missing pass-through variables and corrupt saved
arguments reported; legacy host answers and the base's display support
shown; the workstation digest normalized; 60 regression cases; the
reviewer's gate 1964 unit tests, mypy clean.
Slice 3 is #265, `ws-maintenance/cli-ux-3-run`, delivered 2026-10-24: 1967
unit tests, mypy clean, 10 new tests; its brief is
[brief-pr265-1.md](evidence/2026-10-24-cli-ux/brief-pr265-1.md). Its
PR265.1 is #267, one round: the review staged every answer so nothing is
written before the last blocking decision, fixed the registration names,
the run-once selections, the print-only path, the carriers and the saved
set's refusal (36 cases); round 1 asked for the second derivation to carry
a saved required consent (`run --save --authorize base-image default`
exited 2 on both branches), fixed at `189e54f` with the flag matrix;
accepted there, merged at `1a22a17`; the reviewer's gate 2006 unit tests,
mypy clean. Merged forward into slice 4, where the trust acceptance moved
onto the staged model (written with the answers, never before) and the
base selection takes the workstation trust at every reader: the
realization, the version-set history, the legacy resolve. The merged
slice's gate: 2010 unit tests, 36 deselected, one xfail, one xpass, mypy
clean (the merge commit's message overstates the count; this line is the
record).
Slice 4 is #266, `ws-maintenance/cli-ux-4-trust`, delivered 2026-10-24:
1972 unit tests, mypy clean, 6 new tests in `tests/test_trust.py`; the
trust record `trust.toml` under the launcher's config root, schema 1; the
review's `trusted` status and `superseded` host answers; the `trust`
decision, `--trust CHANNEL`, `config trust list|accept|withdraw`; its
brief is [brief-pr266-1.md](evidence/2026-10-24-cli-ux/brief-pr266-1.md).
Its PR266.1 is #270, accepted at `8975126` without a round and merged at
`694dfe8`: the integrity method bound into the acceptance, HTTPS
checksum-pinned origins only, re-acceptance keeping earlier origins; the
composed lock as the channel's source; the trusted base reaching
derivation, display inspection and realization over an older per-checkout
consent; denials normalized before trust; the staged trust reaching the
preview; the kept host answer disclosed with its new reason; the account
scope in the statement; 23 regression cases; the reviewer's gate 2045 unit
tests, mypy clean. One policy question for the owner from the reviewer:
D-0011 kept Antigravity's bare Cloud Run origin on per-version consent;
the slice lets the user trust that deployment explicitly, with the note
that the URL alone does not prove Google's ownership; confirm or restore
the exception.
Slice 5 is #268, `ws-maintenance/cli-ux-5-console`, delivered 2026-10-24:
1993 unit tests, mypy clean, the console session 299 tests, mypy clean;
21 new launcher tests and 6 console tests; the channel contract
`devcapsule-webconsole/CONFIGURATION-CHANNEL.md`, the launcher's watcher
and deferred requests, `config console list|apply|discard`, the in-capsule
listing "At launch, <time>". One design choice the work order did not
state, for the owner: a request from the capsule that widens the next
launch (a grant, a trust, a mount, a Docker option) is deferred to the
user's confirmation on the host, because anything inside the capsule can
write the mounted directory. Its brief is
[brief-pr268-1.md](evidence/2026-10-24-cli-ux/brief-pr268-1.md).
Its PR268.1 is #272, accepted at `8807a53` without a round and merged at
`fd1fdb5`: `forget` and any `env set` that is not a literal value wait
for the host (a forgotten denial restores workstation trust; a host
binding exposes a variable), explicit secure authorizations apply; the
watcher's child gets record locations only, its own session and process
group, EOF on stdin, the group killed on timeout; only the worker drains
at stop and saves what it did not run; requests carry a UUID and the
deferred store is keyed by project identity and canonical checkout path;
malformed files contained on both sides, a full queue refused, result
text bounded; a confirmed command's disk changes overlaid on the staged
answers; the page shows exposures, bounds its polling and says sending
confirms nothing; 46 launcher cases and the page script run under Node;
the reviewer's gates 2091 unit tests and 320 console tests, mypy clean.
For the owner, from the reviewer: a durable inbox for requests written
after the launcher stops, and direct console approval of wider access,
which a writable capsule directory cannot establish as the human's.
Slice 6 is #269, `ws-maintenance/cli-ux-6-docs`, delivered 2026-10-24:
five user pages rewritten, the command reference written, nine pages
patched, the changelog's candidate-4 section; the website's content
contract check against the checkout passed (188 pages); no code changed.
The retired spellings stay hidden in the code, each answering with its
replacement, because deleting them would rewrite the tests that use
`config resolve` as a fixture step; the owner decides whether to delete
them. Its brief is [brief-pr269-1.md](evidence/2026-10-24-cli-ux/brief-pr269-1.md).
Its PR269.1 is #271, accepted at `b6f5124` without a round and merged at
`4ab687a`, run from a second review worktree so it ran beside PR266.1:
thirteen findings, every page measured against the executable (94 help
paths, 62 focused cases); the pages now say what the launcher does. One
limitation it documented was already gone with PR #270 (the trust lookup
reads the checkout's selected lock) and was re-verified and removed in the
merge. The reviewer's seven code gaps, for the owner, each documented as
current behavior: `--print-command` can still materialize images and
write caches (Part 3.4 promised a read-only preview); `init --ide` still
asks for a per-checkout base consent instead of the channel trust, and
refuses without a terminal; `init --less-pedantic` is still accepted
silently and `run --force-config` fails as an unknown argument without
the migration note (Part 4); a raw `--shm-size` is refused with no user
setting (answer 6 named only memory and CPUs); `checkout register` cannot
rename a registered checkout; `pycharm check-runtime --help` runs its
checks. None of these is in the stack; each is a one-line direction.
The stack to `release-0.3.0`, in order: #260, #261, #263, #265, #266,
#268, #269, every slice with its review merged and merged forward; the
tip of #269 carries everything. The owner merges it in that order, or
merges #269 alone once the lower ones are reviewed as part of it.

The owner read the stack on 2026-10-24 and accepted the code. On the
documentation the owner found machine prose throughout, not only in the
fifteen pages this stack changed, and a missing conceptual entry page per
section, `docs/configuration/index.md` the named first case: what a
configuration is before capabilities, IDEs, approvals and limits. A final
review round of the documentation's language before 0.3.0 is the owner's
direction; it went to `project-management` by mail at `9fcfdb8db440` as
the booking, with the owner's words and the evidence, and is recorded in
the release overview as a condition of the final tag. Maintenance does not
begin the rewrite until project-management assigns it.

## Current State

**2026-10-28: VS Code as an IDE surface implemented, smoked and reviewed; PR #301 ready.**
Item 3 of [the scope decision of 2026-10-27](../2026-08-09-project-management/2026-10-27-decision-release-0-3-0-scope-at-rc8.md),
on `main`: Visual Studio Code joins 0.3.0 as a second provider of
`frontend-ide`, VSCodium the default, acquired on the developer's machine
from Microsoft under the `vscode-download` authorization and a D-0011 trust
channel, never redistributed. Implemented by Antigravity, Gemini 4 Argon
(High), in a session a power outage cut before its smoke finished, with the
slice uncommitted; taken over by Claude Code, Claude Fable 5.1, on the
owner's word, committed in two commits, pushed as `ws-maintenance/0.3.0-vscode`
from the release tip `9e78dce1`, and opened as
[PR #301](https://github.com/ccozianu/devcapsule/pull/301) into
`release-0.3.0`. The slice: the `vscode` component with Microsoft's
acquisition contract and the vscode-family runtime template at `/opt/vscode`;
pin 1.143.1 from the stable feed with url and sha256, matrix `embedded-29`,
`frontend-ide: (codium, vscode)` and `vscode-ide: (vscode)`; `canonical_name`
accepts a component named by one capability among several providers; the
usable lock keeps the pinned surface's closure and refuses a missing provider
by name; a surface without per-file artifacts establishes its channel from
the lock's own url and sha256; discovery from Microsoft's stable update
feed; the IDE lists and the docs. The second pair added the per-checkout
consent a surface's launch needs to the IDE smoke, since the smoke runs
non-interactively against an empty home and the launcher stops at
`vscode-download` otherwise. Recorded IDE smoke, run inside this capsule
from a temporary clone of the branch at `d74666ff`
(`~/worktrees/vscode-e2e-tmp`) with the executable built from it, on the
recommended v0.3.0-rc6 base: `nox -s ide-smoke -- --display --surface
vscode` passed in 87.5 s, Visual Studio Code downloaded from Microsoft and
verified, the formation built, the desktop and the console answered, an X11
window of class `code code` titled `… - Visual Studio Code` owned the
display, 645 distinct colours; the same for `codium` passed in 18.2 s. The
recording, the screenshot, the facts and the redacted launcher log are under
[evidence/2026-10-28-vscode](evidence/2026-10-28-vscode/README.md); the
matrix's verified edge says what that run proved and that no relaunch or
persistence check has run. The review (PR #302, PR301.1, Antigravity, Gemini
4 Argon (High), accepted without a round, merged at `241e7b10`) found the
lock's version, url and sha256 unchecked by `locked_artifacts`; an
empty-credential or whitespace URL establishing a trust channel, since
`urlparse` reports an empty username as `""`; the discovery accepting a
hostless or credentialed URL by prefix; `config ide` reporting the
recommendation table rather than the composed lock it had written; a
docstring contradicting the wrapped VS Code tarball; and the IDE lists in
two orders, with no statement of when the download happens, both fixed.
Gate on the merged tip `241e7b10`: mypy clean over 261 files and 9 console
files, 2544 unit tests passed, 38 deselected, one xfail and one xpass,
packaging 17, the documentation contract 190 pages including 17 aliases
(the website submodule initialized in the worktree for it), the console
357; log `/opt/devcapsule-gate/2026-10-28-vscode-merged-build.log`. The
review partner's print mode was silent for 36 minutes, with progress visible
only in the engine's own log and the worktree; the owner directed the
streaming forms and the relay rule, recorded in `WORKFLOW-LOCAL.md` items 4
and 8 and in the loop document, and a work order in three layers sent to
project-management as
`2026-10-28-maintenance-agent-run-supervision.md` (coordination `b04131ea`).
Judgments for the owner in PR #301: the `vscode-ide` capability beside the
provider form the order named; the closure generalization in `usable_lock`;
the channel fallback for surfaces without artifacts. Awaiting the owner's
merge of PR #301 into `release-0.3.0`; the next candidate carries it, and
the changelog's next-candidate entry follows at the cut.
**2026-10-28: the configuration home and the home commands implemented; PR #299 ready.**
The slice of the [work order of 2026-10-27](../../work-orders/2026-10-27-configuration-home-and-the-home-commands.md),
designed by the owner in the project-management session and ordered
there (in PR #297 to `main`), implemented by Codex, gpt-6-astra, with
Claude Code, Claude Fable 5.1, as the review partner, dispatched from the
project-management session on the owner's word. `DEVCAPSULE_CONFIG_HOME`
names the one configuration home; set, data, state and cache are
subdirectories of it; unset, the four XDG directories as before.
`settings.toml` holds the defaults and the accepted channels under a
schema integer and `minimum-devcapsule`, the first file to declare its
minimum reader; `workstation.toml` and `trust.toml` are not read. The
`devcapsule home` group holds `show`, `trust list|accept|withdraw` and
`default`, from any directory; the three mutating spellings under
`project config` are deleted; a project-less `trust accept` takes the
channel from the embedded matrix's pin through the one function the lock
path uses. The word "workstation" is gone from code, docs and D-0011,
which is amended and renamed. The implementor stopped twice: on the
order's evidence location, capsule-local and so invisible to the host
daemon, moved to the host-backed home; and on `packaging`, a dependency
the PEX does not carry, caught by the packaging gate and replaced by a
three-integer comparison. The review (PR #300, PR299.1, accepted without
a round, merged at `e83c0881`) found the launcher exporting the variable
into the capsule as `/etc/devcapsule/home`, so every launcher-owned write
inside a capsule, the recursive dogfood's among them, failed under a
root-owned mount parent, reproduced with `checkout notifications post`;
now the capsule reads the launcher's settings from the mount until it has
settings of its own, writes only its own, and names no home, which
retires the order's in-capsule refusal, a rule change recorded for the
owner under the pull request's judgments. The review also deleted the
renderers the one document made dead and an environment reach in
`atomic_write`; the implementor had already routed session logs and the
managed bindings through the home before the review was cut. Gates on
the merged tip: mypy clean over 259 files and 9 console files, 2515
unit tests, 37 deselected, one xfail and one xpass, packaging 17, the
documentation contract 190 pages, the console 357. No image, capsule,
tag or dispatch was used. Awaiting the owner's merge of PR #299 into
`release-0.3.0`; the next candidate carries it.
**2026-10-27: diagnostics snapshot and sanitized export ready for merge (#293).**
Implemented `devcapsule project diagnose` and `devcapsule runtime diagnose-probe`
on `ws-maintenance/0.3.0-diagnostics-snapshot` targeting `release-0.3.0`
([PR #293](https://github.com/ccozianu/devcapsule/pull/293)), completing
Deliverable 4 and the manual browser-evidence contract of Deliverable 5 in
[2026-10-08-persistent-session-diagnostics.md](../../work-orders/2026-10-08-persistent-session-diagnostics.md).
Codex (`gpt-6-astra`) review [PR #295](https://github.com/ccozianu/devcapsule/pull/295)
(`c190d1cf`) was accepted without a round and merged at `5cc52392` (nine
hardenings, 42 focused checks). Post-merge `nox -s build` + `webconsole` passed
(`mypy` 254 + 9 files; 2,380 unit, 17 packaging, 189 docs pages, 357 webconsole)
and real-container E2E `tests/e2e/test_session_diagnostics.py` passed (`21.15 s`).
Awaiting the owner's merge of PR #293 into `release-0.3.0`.
**2026-10-27: C20, release documentation automation, implemented; PR #294 ready.**
The slice of the [work order of 2026-10-27](../../work-orders/2026-10-27-release-documentation-automation.md),
ordered by project-management on the owner's direction and merged into
`main` by PR #292, implemented by Codex, gpt-6-astra, with Claude Code,
Claude Fable 5.1, as the review partner, dispatched from the
project-management session on the owner's word. One helper,
`devcapsule-src/scripts/release-docs.py`: `promote` applies the lifecycle
on the release branch, `check` names every unmet obligation at the tag,
`notes` prints the release body without its front matter, `published`
refuses a listed version without a final download; PyYAML joins the
development dependencies. The release workflow's final-tag path checks
before it publishes, passes the notes as the body, and dispatches the
test-site build after; the website workflow runs `published` in both
modes. The `docs-<version>` rule, the contract's `source-version`
wording, the runbook and the overview changed with it. The implementor
found the order's ordering loose: the final tag's commit must equal the
accepted candidate's, so the promotion, the notes and the `docs-X.Y.Z`
push go before the last candidate, not merely before the final tag; the
runbook says so. The review (PR #296, PR294.1, accepted after one round,
merged at `7bb8883`) fixed two correctness defects: the placeholder rule
refused the 0.2.14 notes as published, which carry `--path <checkout>` in
code spans, so a placeholder is now angle-bracketed prose outside code
and autolinks, wrapped across lines or not but never across a paragraph
break, the round's correction; and the manifest reader refused a candidate
listed as `development`, a shape R-DOCS-003 admits, which would have
failed the website guard on a valid file. The reviewer's gate on the
merged tip: mypy clean over 249 files, 2430 unit tests passed, 36
deselected, one xfail and one xpass; packaging integration 17; the
documentation contract 189 pages; the console mypy clean over 9 files,
357 tests; the implementor's gate on the merged branch the same. No
`actionlint` on the capsule: the two workflows were checked by reading,
by `yaml.safe_load` and by `bash -n` on every run block; the final-only
steps run for the first time at the final tag, before anything is public.
Not proven: the content check on a promoted manifest, since `docs-0.3.0`
does not exist yet; the pinned consumer's parser accepted the promoted
file on its own. The 0.3.0 sequence the runbook now has: notes and
`promote 0.3.0` on the release branch, the `docs-0.3.0` push at that
commit, the merge to `main`, the last candidate, its acceptance, `check
0.3.0`, the final tag; the owner reads the test site and promotes it.
Next: the owner merges PR #294 into `release-0.3.0`; the slice rides the
next candidate; the status line above and the changelog's next-candidate
entry follow with it.

**2026-10-26: rc8 tagged, published and verified.** The owner merged
PR #291 at `8afa5f6`; `8d41fab` is an ancestor of `main`; `v0.3.0-rc8` on
`8d41fab`, the candidate gate `mainline` with no unintegrated commits from
a detached checkout, the atomic push, run 40271738816 passed, the
prerelease public with its three assets; downloaded, the checksum
verified (SHA-256 `5f1f8429…`), the manifest's base reference the
published recipe-11 digest, `version --json` from an empty directory
`0.3.0rc8` at `8d41fab`. The downloaded executable migrated a copy of the
trading sample to schema 2. The overview's rc8 entry and the changelog's
candidate-8 line record it. Note for the next cut: run the downloaded
executable directly after `chmod +x`; `python3 -I devcapsule.pex` picked
up another installation in this capsule and reported a different version.
The owner's gate of 2026-10-26 is met. Next: the owner regenerates this
repository's, the website's and the samples' manifests; the diagnostics
snapshot, image cleanup and C20; the documentation round before the
final tag.

**2026-10-26: rc8 in preparation.** The owner merged PR #289; the
release tip is `9e4a2a8`. Full `nox -s build` on it from a separate
worktree: mypy clean over 248 files, 2338 unit tests passed, 36 deselected, 1 xfailed, 1 xpassed, packaging integration 17, console 357; the
documentation contract 189 pages. The throwaway copy
`4PR-9-release-0.3.0`, the release tip (this record's commit) plus the
cherry-pick of `62fa063`, is the pull request for the owner's merge. On
that merge, the rc7 steps with `rc8` in place of `rc7`: the ancestry
check, the annotated tag on the tip, the release protocol from a detached
checkout expecting `mainline`, the atomic push of branch and tag, the
backend run, the download into `~/.cache/devcapsule-releases/v0.3.0-rc8`
with checksum and version verified, the overview's rc8 entry and the
changelog's candidate-8 line. The owner's gate of 2026-10-26 is met by
this candidate; the diagnostics snapshot, image cleanup and C20 stay with
the next; the documentation round before the final tag.

**2026-10-26: the manifest's two schemas as classes, implemented; PR #289 ready.**
The slice of the order of 2026-10-26, implemented by Claude Code, Claude
Fable 5.1, with Codex, gpt-6-astra, as the review partner (PR #290,
PR289.1, accepted at `94d2108` without a round, merged at `f4d0566`). One
pure module, `configuration/manifest_schemas.py`: `ManifestV1`,
`ManifestV2`, `read_manifest`, `upgrade` by the order's laws; the
boundary `manifest.current_manifest`, the IDE question answered by the
component catalog since the configuration core may not import the matrix;
every consumer reads schema 2; `CapabilityPolicy.layered` deleted, the
compatibility branches it gated keyed on the lock (`legacy_lock`: no
provider evidence, or a generation before embedded-27, which no release
carried between 22 and 27); `init --regenerate` writes a schema-1 file as
schema 2 with the leading comment block kept and says so, a schema-2 file
stays byte for byte, plain `init` honors either schema and refuses to
append a recommendation to a schema-1 file. Departures from the order's
letter, each for the owner in the PR body: `ManifestV2.read` folds a
carried-over `workflow-type` instead of refusing it, since rc4 to rc7
wrote such files; the environment and recommendation tables are kept as
written beside their values; the IDE a schema-1 file required is the
owner's checkout default at `init`, and the recommended IDE is the
`run` default only when the lock pins none; the two-IDE refusal cannot
name `config drop`, which the same admission refuses first. The review
made admission lossless (`document()` reproduces the file, explicit
empties included), validated the schema-1 policy before migration, and
added the launch test for a migrated project's old checkout. Gate on
`f4d0566`: mypy 248 files, 2338 unit tests (36 deselected, 1 xfailed,
1 xpassed), 17 packaging, 357 console, docs 189 pages. Acceptance on
scratch copies of the trading sample and the rc3 AI Learning manifest in
the PR body. Awaiting the owner's merge; then the repository's own,
the website's and the samples' manifests are the owner's regeneration.

**2026-10-26: the manifest's two schemas as classes; regenerate migrates.**
The owner, on learning that `init --regenerate` left the AI Learning
manifest at schema 1, ruled that regeneration migrates the manifest to
schema 2 and that the codebase keeps schema 1 and schema 2 explicitly
represented as classes; a gate of the final 0.3.0 tag. Written as
[2026-10-26-manifest-schemas-as-classes.md](../../work-orders/2026-10-26-manifest-schemas-as-classes.md),
listed in `index.md`, on `ws-maintenance/manifest-schema-classes` from the
release tip `e415e5b`, for the owner's edits in the IDE and merge. The
design: one pure module with `ManifestV1`, `ManifestV2`, `read_manifest`
and `upgrade`, each class strict about the other's words, tolerant of
unknown tables; the upgrade laws (need to required, a required IDE to the
IDE recommendation, the SDK-major table dropped, `workflow-type` folded
into `[workflow].mode`); every consumer reads a `ManifestV2`;
`init --regenerate` writes the migrated manifest with the leading comment
block kept and says so, a schema-2 file stays byte for byte; the owner
commands migrate through the same path. The gate is recorded in the
overview. Merged the same day: PR #283 (the documentation order), #285
(D-0015) and #287 (the workstation-commands bug).

**2026-10-25: rc7 tagged, published and verified.** The owner merged
PR #286 at `77ac058`; `73bbe53` is an ancestor of `main`; `v0.3.0-rc7` on
`73bbe53`, the candidate gate `mainline` with no unintegrated commits from
a detached checkout, record at `/opt/devcapsule-gate/rc7-release-protocol.json`;
pushed; backend run 40198740279 passed; the prerelease is public with its
three assets; the download under `~/.cache/devcapsule-releases/v0.3.0-rc7`
verifies, SHA-256 `1fe418a2…`, the manifest's base reference the published
recipe-11 digest, `devcapsule version` reporting `0.3.0rc7` at `73bbe53`.
The overview's rc7 entry and the changelog's candidate-7 line are
written. Next, the owner's: regenerate a project lock with rc7 and test
the console on the published base; then the diagnostics snapshot, image
cleanup and C20 for the next candidate; the documentation language review
before the final tag.

**2026-10-25: rc7 in preparation.** The owner merged PR #284; the
release tip is `349b3ad`. Full `nox -s build` on it from a separate
worktree: mypy 246 files, 2282 unit tests, packaging integration 17,
console 357; the documentation contract 189 pages. The throwaway copy
`4PR-8-release-0.3.0`, the release tip (this record's commit) plus the
cherry-pick of `62fa063`, is the pull request for the owner's merge. On
that merge, the rc6 steps with `rc7` in place of `rc6`: the ancestry
check, the annotated tag on the tip, the release protocol from a detached
checkout expecting `mainline`, the atomic push of branch and tag, the
backend run, the download into `~/.cache/devcapsule-releases/v0.3.0-rc7`
with checksum and version verified, the overview's rc7 entry and the
changelog's candidate-7 line. The published-base gate is met by this
candidate. The diagnostics snapshot, image cleanup and C20 stay with the
next candidate; the documentation language review before the final tag;
D-0015, a project's own constraint on its base, is proposed for V1.

**2026-10-25: the published recipe-11 base pinned; rc7 next.** The
owner built the base from the published rc6 executable and pushed it as
`mycodespaceai/devcapsule-base:v0.3.0.rc6`, digest `8c97d308…`; the registry
copy re-inspected by digest: linux/amd64, `ubuntu-24.04@11`, contained
display, launcher-supplied runtime, the six services, the console at
`/opt/devcapsule-webconsole`, source revision `2ed8ecf`. The pin is
[PR #284](https://github.com/ccozianu/devcapsule/pull/284) on
`ws-maintenance/base-recipe-11-pin` from `b19d654`, implemented by the
Codex and gpt-6-astra pair from the brief under
`evidence/2026-10-25-base-recipe-11/`, session
`01a172d9-a9a3-7f43-b7ec-1e6f8c7547b2`, reviewed by Claude Fable 5.1:
`_V0_3_0_RC6_BASE` appended newest-last, the recipe-9 pin kept (retirement
is the owner's act under D-0007) with a test that its locks still resolve
as a known base of the family; matrix `embedded-28`; the ten golden locks
and this repository's lock regenerated by the executable, each diff the
matrix line and the base table only; the lock's base table gains
`recipe-source` so consent links the recipe at its current path without a
matrix lookup, older locks falling back to the legacy path; the rc6 and
rc2 executables read the new lock. Full gate at `dedb485`: 2282 unit,
packaging 17, console 357; the review re-ran the base-contract and matrix
modules (49) and checked every lock diff. Accepted, no round. On the
owner's merge: the rc7 record, the pre-candidate copy, the tag; a
regenerated lock in any project then moves to recipe 11, the AI Learning
bootstrap among them. `config show` prints the base's digest and not its
contract; left as is.

**2026-10-25: documentation work order from the owner's outside list.**
The owner brought an analysis, made outside this project, of a
complementary product's documentation and eight improvements it suggests for
ours, and asked for it as a work order attached to an existing workstream.
Written as
[2026-10-25-documentation-orientation-and-concepts.md](../../work-orders/2026-10-25-documentation-orientation-and-concepts.md),
listed in `index.md`, on `ws-maintenance/docs-orientation-order` from the
release tip `7c86141`, the rc7 publication record, for the owner's edits in the IDE and merge. Grounded
against `docs/` at that tip, the rc6 executable and the content contract:
the sidebar's first group is the six role pages in the contract's order,
not a misordered section; *What persists* is already the storage table;
the configuration entry page already defines the words; glossary and
recipes are items 5 and 6 of the eleven open user-docs proposals, taken as
decided by the owner's handing-over. Kept, corrected: *what it is not* on
the overview and `/why/`; a *What a capsule is* page leading Getting
started; two columns and a *when the manifest changes* section on *What
persists*; a `docs/recipes/` area, four recipes on catalog capabilities; a
background-agents section in the workstreams guide; and, as Part B after
the final tag's documentation round, the Windows role moved up in the
contract, a five-step landing strip as a new contract section, one
dogfooding journal entry. Dropped: a separate concepts area, a Scala recipe,
product names in `docs/`. Attached to `maintenance`, joining the booked
language review (`9fcfdb8db440`) so the pages are rewritten once.

**2026-10-25: rc6 tagged, published and verified.** The owner merged
PR #282 at `b64187f`; `2ed8ecf` is an ancestor of `main`; `v0.3.0-rc6` on
`2ed8ecf`, the candidate gate `mainline` with no unintegrated commits from
a detached checkout, record at `/opt/devcapsule-gate/rc6-release-protocol.json`;
pushed; backend run 40162886659 passed; the prerelease is public with its
three assets; the download under `~/.cache/devcapsule-releases/v0.3.0-rc6`
verifies, SHA-256 `6cef940e…`, `devcapsule version` reporting `0.3.0rc6`
at `2ed8ecf`. The overview's rc6 entry and the changelog's candidate-6
line are written. Next, the owner's: test the download, the console's
configuration page first; then the diagnostics snapshot, image cleanup
and C20 for the next candidate; the documentation language review before
the final tag.

**2026-10-25: rc5 regression repaired; rc6 in preparation.** The owner's
test of the rc5 download found the console's configuration page failing:
`/api/configuration` ran `config list`, retired by candidate 5, status 2.
[PR #281](https://github.com/ccozianu/devcapsule/pull/281) on
`ws-maintenance/console-config-show` from the release tip `1f1a5cc`:
`cd128bb` points the console's `cli.py`, the runtime configuration's
launcher command, the PyCharm launcher's lock hint and the channel's
read-only verbs at `config show`; `ed01b4d` adds the forcing functions,
the console's nox session installing the launcher from this checkout, a
`READ_COMMANDS` table in the console, and `test_launcher_contract.py`
against the launcher's own command tree (commands exist and take
`--json`; the channel's verbs equal the launcher's applied, deferred and
subverb sets; widening equals deferred; the secure authorizations agree;
the channel document lists the verbs; the listing row's fields). Full
gate on `ed01b4d` after clearing a stale `__pycache__`: mypy 246 files,
2281 unit tests, packaging integration 17, console 357 (31 new). The
owner merged it; the release tip is `5daf5a2`, the same tree. The owner's
direction: cut rc6 now. The throwaway copy `4PR-7-release-0.3.0`, the
release tip (this record's commit) plus the cherry-pick of `62fa063`, is
the pull request for the owner's merge; on that merge, the rc5 steps
with `rc6` in place of `rc5`: the ancestry check, the annotated tag on
the tip, `scripts/release-protocol.py v0.3.0-rc6 --output
/opt/devcapsule-gate/rc6-release-protocol.json` from a detached checkout,
expecting `mainline`; the atomic push of the branch and the tag; the
backend run; the download into `~/.cache/devcapsule-releases/v0.3.0-rc6`
with checksum and version verified; the overview's rc6 entry and the
changelog's candidate-6 line. The diagnostics snapshot, image cleanup
and C20 stay with the next candidate; the documentation language review
before the final tag.

**2026-10-25: rc5 tagged, published and verified.** The owner merged
PR #280 at `35d74d9`; `03ed348` is an ancestor of `main`; `v0.3.0-rc5` on
`03ed348`, the candidate gate `mainline` with no unintegrated commits from
a detached checkout, record at `/opt/devcapsule-gate/rc5-release-protocol.json`;
pushed; backend run 40147675417 passed; the prerelease is public with its
three assets; the download under `~/.cache/devcapsule-releases/v0.3.0-rc5`
verifies, SHA-256 `429aefee…`, `devcapsule version` reporting `0.3.0rc5`
at `03ed348`. The overview's rc5 entry and the changelog's candidate-5
line are written. Next, the owner's: test the model's commands on the
download; then the diagnostics snapshot, image cleanup and C20 for the
next candidate; the documentation language review before the final tag.

**2026-10-25: rc5 in preparation.** The owner merged the three slices;
the release tip is `d01fb8c`. Full `nox -s build` on it from a separate
worktree: mypy 246 files, 2281 unit tests, packaging integration 17,
console 326; the documentation contract 189 pages. The throwaway copy
`4PR-6-release-0.3.0`, the release tip (this record's commit) plus the
cherry-pick of `62fa063`, is the pull request for the owner's merge. On
that merge: confirm the release tip is an ancestor of `main`; `git tag -a
v0.3.0-rc5 <tip> -m 'DevCapsule 0.3.0 candidate 5'`; from a detached
checkout of the tag, `scripts/release-protocol.py v0.3.0-rc5 --output
/opt/devcapsule-gate/rc5-release-protocol.json`, expecting `mainline`;
push the tag; the backend run; download into
`~/.cache/devcapsule-releases/v0.3.0-rc5`, verify the checksum and the
version; record rc5 in the overview and the changelog's candidate-5 line.

**2026-10-25: capabilities and components, slice 3 accepted; the stack is
complete.** Slice 3, the retired spellings deleted, the documentation on
the model, the configuration entry page and the candidate-5 changelog, is
[PR #279](https://github.com/ccozianu/devcapsule/pull/279) on
`ws-maintenance/capabilities-3-docs` into slice 2's branch, Codex session
`01a1702e-7625-7230-adc1-7a9fb6d98e4b`. One review round: the console's
configuration channel still named the deleted `agent` and `tool` verbs on
both sides (the brief's "do not touch the web console" caused it; the
round lifted it), the listing labelled rows "agent" by a credentials-slot
rule, `init` kept its own grammar and lacked `--with`, the pages carried
the previous day's date; fixed at `1ae09df`. Accepted there: full gate
from a separate worktree, mypy 246 files, 2281 unit tests, packaging
integration 17, console 326; the documentation check 189 pages; the
commands and the channel classifier verified by hand. The three slices
(#276, #277, #279) are the owner's to merge in order into
`release-0.3.0`; each later PR targets the previous slice's branch, so
GitHub retargets it as the earlier one merges. The next candidate, rc5,
follows the merges, with the diagnostics snapshot, image cleanup and C20
still to come, and the documentation language review before the final tag.
**2026-10-25: capabilities and components, slice 2 accepted; slice 3
running.** Slice 2, the owner's and the developer's commands, the
resolution recommendation and the provider choice, is
[PR #277](https://github.com/ccozianu/devcapsule/pull/277) on
`ws-maintenance/capabilities-2-commands` into slice 1's branch, Codex
session `01a17009-1972-75e1-a5e1-29bc111a6de4`. Codex stopped first on a
real blocker: the rc4 reader refuses an unknown key under
`[recommendations]`, so the order's `[recommendations.resolution]` was
unreadable by rc4; the reviewer verified with the rc4 executable that an
unknown table under `[capabilities]` is tolerated silently, moved the
table to `[capabilities.resolution]` and corrected the order (`168181d`);
the reviewer also struck the reason on a resolution recommendation, by
the owner's rule of removal, nothing reading it (`34fa5f1`). One review
round: `compose_lock` had become a writer, the resolver's steps were not
legible and the lock's shape depended on inputs, the resolution's reason
was encoded in a key, two messages named retired words, base rows showed
a provider; fixed at `be3821c`. Accepted there: full gate from a separate
worktree, mypy 244 files, 2191 unit tests, packaging integration 17,
console 320; the commands verified by hand on a scratch project. Slice 3,
the retired spellings deleted, the documentation on the model, the
configuration entry page and the candidate-5 changelog, is running on
`ws-maintenance/capabilities-3-docs`, worktree `maintenance-impl-3`,
session `01a1702e-7625-7230-adc1-7a9fb6d98e4b`. The owner merges #276 then
#277; #277's PR targets #276's branch.
**2026-10-24, night: capabilities and components, slice 1 accepted.** The
owner merged the work order (PR #275) and swapped the roles: Codex with
gpt-6-astra implements, Claude Fable 5.1 reviews, the owner merges.
Slice 1, the catalog and derivation on one capability table with the rc4
commands still working, is [PR #276](https://github.com/ccozianu/devcapsule/pull/276)
on `ws-maintenance/capabilities-1-model` into `release-0.3.0`, Codex
session `01a16fe7-2eeb-7b70-8013-0d585196e04b`, brief under
`evidence/2026-10-24-capabilities/`. One review round: the listing had
rewritten the capability's name with its minimum, the base refusal
special-cased "Python", a versionless locked provider failed without a
minimum, and the retired-table note had two spellings; fixed at `5530843`.
Accepted there: full gate from a separate worktree, mypy 243 files, 2130
unit tests, packaging integration 17, console 320; the acceptance greps
hold; the owner's three-requirement use case and the AI Learning rc2
files verified by hand (refusal naming 3.12; byte-identical regenerated
lock; the old table dropped on the next owner write). Slice 2, the
commands, run flags, resolution recommendation and provider choice, is
running on `ws-maintenance/capabilities-2-commands`, stacked on slice 1,
worktree `maintenance-impl-2`, session `01a17009-1972-75e1-a5e1-29bc111a6de4`.
The owner merges #276 when ready; slice 2's PR targets slice 1's branch.

**2026-10-24, late: the next work order drafted.** Reviewing rc4's
vocabulary, the owner found the split of components into IDEs, agents
and tools unjustified and settled the model with the agent in
conversation: capabilities (the project's word) provided by components
(the catalog's), the surface the one special role, cardinality a property
of the capability, and the project able to require, offer or recommend a
capability and, optionally, recommend its resolution. The draft
[work order](../../work-orders/2026-10-24-capabilities-and-components.md)
refactors the redesign's output: it deletes the `-agent` kind, the
matrix's refusal of agents in the shared contract and the three command
families, and adds `[recommendations.resolution]` and a minimum version on any
requirement; the SDK major is removed entirely by the owner's ruling. Its
Part 5 asks the owner nothing: the implementation choices are taken by the
agent within the rulings and the owner reverses any by a word; the two
that change scope, deleting the rc4 aliases and targeting the final 0.3.0
tag, are marked. The owner struck cardinality from the model and tabled
the renaming of the IDE role to the capsule's entry point as D-0014,
proposed and in scope for V1; the order and the records say the IDE owns
the container's lifetime and can make use of the display, never that it
owns the display. The owner's complaint that every work order makes work
for them is taken: an order is written as decisions taken, not as
questions. Nothing is implemented.

**2026-10-24, evening: rc4 tagged, published and verified.** The owner
merged PR #274 at `c04cb4e`; `78a9c66` is an ancestor of `main`;
`v0.3.0-rc4` on `78a9c66`, the candidate gate `mainline` with no
unintegrated commits from a detached checkout, record at
`/opt/devcapsule-gate/rc4-release-protocol.json`; pushed with the branch;
backend run 40123896286 passed; the prerelease is public with its three
assets; the download under `~/.cache/devcapsule-releases/v0.3.0-rc4`
verifies, SHA-256 `474fea1e…`, `devcapsule version` reporting `0.3.0rc4`
at `78a9c66`. The overview's rc4 entry and the changelog's candidate-4
line are written. The AI Learning setup the owner asked for is delivered
in chat from the dry run described below. Next, the owner's: test the
redesigned commands on the download; then the diagnostics snapshot, image
cleanup and C20 for the next candidate; the documentation language review
before the final tag, booked with project-management.

**2026-10-24, evening: rc4 in preparation.** The owner merged the CLI UX
stack, #260 to #269, the release tip at `3cc8a50`. The full `nox -s build`
on it failed in the packaging integration: one test of seventeen expected
`config check` to pass without the base channel trusted and the retired
`--sdk-major` flag to resolve; the unit gates the slices ran never execute
that suite. Fixed as a test-only change at `fe886ad`, pushed to the release
branch directly as a release-blocking gate fix; the full gate on it passed
(mypy 242 files, 2091 unit tests, packaging integration 17, the console
session). The throwaway copy `4PR-5-release-0.3.0`, the release tip (this
record's commit) plus the cherry-pick of `62fa063`, test-merged cleanly into `main` and is the pull
request for the owner's merge. On that merge: confirm the release tip is
an ancestor of `main`; `git tag -a v0.3.0-rc4 <tip> -m 'DevCapsule 0.3.0
candidate 4'`; from a detached checkout of the tag,
`scripts/release-protocol.py v0.3.0-rc4 --output
/opt/devcapsule-gate/rc4-release-protocol.json`, expecting `mainline`;
`git push --atomic origin release-0.3.0 v0.3.0-rc4`; the backend run;
download into `~/.cache/devcapsule-releases/v0.3.0-rc4`, verify the
checksum and the version; record rc4 in the overview and the changelog's
candidate-4 line. The owner also asked for the AI Learning bootstrap
project's optimal setup with the rc4 launcher; the dry run against a scratch
clone found `init --regenerate` leaves the lock byte-identical on the
unchanged matrix, the owner commands rewrite the manifest to schema 2, and
non-interactive `init` still needs `--authorize base-image default` and the
agent download consents despite workstation trust, the gap already recorded.

**2026-10-24: rc3 tagged, published and verified.** The owner merged
PR #257 at `cf760b8`; `a22a215` is an ancestor of `main`; `v0.3.0-rc3` on
`a22a215`, the candidate gate `mainline` with no unintegrated commits from
a detached checkout, record at `/opt/devcapsule-gate/rc3-release-protocol.json`;
pushed atomically with the branch; backend run 40052369307 passed; the
prerelease is public with its three assets; the download under
`~/.cache/devcapsule-releases/v0.3.0-rc3` verifies, SHA-256 `be739875…`,
`devcapsule version` reporting `0.3.0rc3` at `a22a215`. The overview's rc3
entry, the table and the changelog's candidate-3 date are written. Next,
the owner's: test the saved Docker arguments and the approvals prompt on
the download; provider acceptance of the new agent pins; the network
node's check on a fresh project. Then rc4's slices: forced configuration,
the diagnostics snapshot, the schema-version slice on the owner's go,
image cleanup after the design review, C20.

**2026-10-24: rc3 in preparation, by the owner's direction.** The owner
needs the saved Docker arguments on a downloaded candidate to test
development scenarios, environment variables and GPUs among them, so
candidate 3 is tagged now with what the release branch carries: software
approvals at launch (PR #250, review #251), the saved Docker arguments
(PR #253, review #255) and the regenerated shared lock (`0c1a555`).
Forced configuration, the diagnostics snapshot and the schema-version
slice move to rc4 with image cleanup and C20; the overview records the
direction and the changelog has its candidate-3 section. `main` is ahead
of the release branch by PR #252, the AI Learning sample, and PR #256, the
`.idea` rule; a test merge of the copy into `main` was clean, and `main`
is not merged into the release branch this time, since nothing on it is
release content and the owner gave no such direction. The full gate on
the release tip `a22a215`: mypy clean over 224 files, 1769 unit tests
passed, 36 deselected, 2 xfailed, packaging integration 17 passed, the
documentation contract 188 pages, the web console clean and its tests
passed. The throwaway copy `4PR-4-release-0.3.0`, the release tip plus the
cherry-pick of `8b7fbc3` keeping `main`'s version files, is
[PR #257](https://github.com/ccozianu/devcapsule/pull/257) into `main`, the
gate posted on it. The session is interrupted here by the owner; the claim
is released; nothing is uncommitted. On resumption, after the owner's
merge: fetch and confirm the release tip `a22a215` is an ancestor of
`main`; `git tag -a v0.3.0-rc3 a22a215 -m 'DevCapsule 0.3.0 candidate 3'`;
from a detached checkout of the tag, `scripts/release-protocol.py
v0.3.0-rc3 --output /opt/devcapsule-gate/rc3-release-protocol.json`,
expecting `mainline`; `git push --atomic origin release-0.3.0 v0.3.0-rc3`;
the backend run; download the three assets into
`~/.cache/devcapsule-releases/v0.3.0-rc3`, verify the checksum and the
version; record rc3 in the overview, the table and the changelog's
candidate-3 date. Then the owner's test of the saved Docker arguments and
of the approvals prompt on the download, provider acceptance of the new
agent pins, and the network node's check on a fresh project.

**2026-10-23: the repository's `.idea` rule reversed and executed,
[PR #256](https://github.com/ccozianu/devcapsule/pull/256) into `main`.**
The owner sorted the directory with this session: the hand-written,
portable part is three small files; the churn is the module files PyCharm
generates from every `pyproject.toml` it finds, the website test fixtures
and the sample projects included. The owner's rule, replacing the
unexecuted ruling of 2026-10-01: track what PyCharm itself does not ignore,
JetBrains' own `.idea/.gitignore` being the contract; `misc.xml` stays out;
DevCapsule writes nothing into `.idea` and relies on the IDE cooperating
with Git, taking no responsibility for IDE settings across ecosystems.
Research before the go, from PyCharm 2026.2's *Share project settings*
and this capsule's IDE state: a run configuration stored as a project file
is portable in the module-SDK form, empty `SDK_HOME`, `$PROJECT_DIR$`
paths, the interpreter by the module's name; the one per-machine step is
registering the venv, which PyCharm names by its path and the module file
carries as a `$MODULE_DIR$` macro, the same on the host and in this
capsule; `SDK_HOME` is machine-bound and the uv-managed name is the
documented exception. On `ws-maintenance/idea-tracking` off `main`, in a
worktree: the ignore rule, the generated modules as the IDE wrote them, two
shared run configurations (the unit tests, the `devcapsule` CLI), the rule
in `DEVELOPING.md` under *IDE project files*, the backlog's reversal. The
run configurations are hand-written from the form the IDE produced here;
the owner's next IDE open verifies them. Next: the owner reviews and
merges PR #256; the generated module for the AI Learning sample arrives
with the next IDE open on `main`.

**2026-10-23: the two C10 records are closed on rc2.** The owner verified
the downloaded `v0.3.0-rc2` on the host: Ctrl+C ends the launcher with a
result, and the terminal summary, the links, the ready line and the result
with the log paths without the IDE's output, worked as expected. Both
records, [the terminal](../../bugs/devcapsule/2026-10-22-healthy-launch-looks-unhealthy-in-the-terminal.md)
and [Ctrl+C](../../bugs/devcapsule/2026-10-22-ctrl-c-ends-the-launcher-with-a-traceback.md),
are closed and the bug table's rows with them. Since the pause, PR #250,
software approvals at launch, and PR #253, general saved Docker arguments
with its review PR #255, are merged into the release branch by the owner;
neither is in a candidate yet, and `main` has taken PR #252, the AI
Learning sample, so the next pre-candidate merge reconciles both sides.
Still open on rc2: the network node's check on a fresh project. Next: the
go for the schema-version slice; the rc3 slices.

**2026-10-22, night: PR #250's review loop is settled; the slice awaits the
owner.** PR250.1, [PR #251](https://github.com/ccozianu/devcapsule/pull/251)
by the Codex and gpt-6-astra pair, is merged after one round: inspecting
the approvals could recover an interrupted activation, a write, so the
launch defers to its loader and the command refuses with the resolve
command; EOF on the keypress is a refusal; saved approvals are named when
the resolution fails after them; the history lookup is best effort on
every error; the page and the help say what a by-name approval leaves
alone; the index lists the page; regression cases for the strict
qualification, the in-capsule refusal through a real runtime context and
the replacement order. The round: the activation journal's suffix spelled
once in `storage.py` with a predicate both sites call. Full gate on the
merged branch, 1719 unit tests, the documentation contract with 47 pages.
Both briefs are under `evidence/2026-10-22-software-approvals/`. Open
thread from the review, for the consent slice of D-0011: a stored consent
holds only its value and digest, so it cannot prove yesterday's terms,
only that the lock matches today's contract. Next: the owner merges
PR #250; the schema-version slice on the owner's go; then rc3 with the
regenerated lock.

**2026-10-22, evening: software approvals at launch, PR #250, the first
slice of rc3.** The owner's finding on the host after merging the
regenerated lock: `config resolve` asked for the Antigravity and Claude Code
consents again, one per component, nothing new to decide. The diagnosis:
the acquisition consent's digest covers the component's whole lock entry,
version included, so a pin bump re-asks; D-0011 of 2026-10-01 rules that
out, once per vendor product per user, and its slice is out of 0.3.0 with
the consent work. The owner's direction instead: when the only pending
decisions are new versions of vendor software approved before, from the
same vendors under the same terms, `project run` offers the whole list
with one y/n; on no, it names `project config approve` and a page,
*software approvals*. Three design points settled with the owner: this
replaces the digest change, the strict definition of "only component
upgrades", the command and the page. On
`ws-maintenance/0.3.0-software-approvals` off the release branch:
`devcapsule/configuration/approvals.py`, the qualification and the list;
`devcapsule/commands/_software_approvals.py`, the launch-time offer, the
last launched version from the newest known-good record, approve and
resolve, the quoted command, the page's address, the keypress helper
moved beside it; the `config approve` command, mutating, refused inside a
capsule for its own project; the hook before the launch's loading, never
in `--print-command`; the page under `docs/configuration/`. Fifteen tests
through the real command line; the documentation contract passed with the
page; the full gate, 1686 unit tests.
[PR #250](https://github.com/ccozianu/devcapsule/pull/250) into
`release-0.3.0`; the review partner is the Codex and gpt-6-astra pair, by
the owner's word, running detached. Also this evening: the owner's
requirement that configuration files declare their format and the minimum
DevCapsule that reads them went to `project-management` by mail at
`ced0ed1aab9a`; the manifest rewrite by `config capabilities` is filed as a
bug; the owner's ruling that a writer emitting the `required`/`optional`
vocabulary bumps the manifest's schema version to 2 is the next slice,
beside this one, for rc3.

**2026-10-22, afternoon: rc2 tagged and verified; the shared lock
regenerated and proven.** PR #249 merged at `e998dc0`; `v0.3.0-rc2` on
`e5b5a8b`, the candidate gate `mainline` from a detached checkout, pushed
atomically; backend run 39803285881 passed; the prerelease is public with
its three assets; the download under `~/.cache/devcapsule-releases/v0.3.0-rc2`
verifies, SHA-256 `abb9a8e1…`, version `0.3.0rc2` at `e5b5a8b`. Then the
lock, on the owner's word, the way the owner suggested: `project config
capabilities --required …` ran on a fresh clone of the release branch
inside this capsule, which the capsule rule allows for any project but its
own; it wrote the lock on matrix embedded-27, Codex 0.163.0, Claude Code
2.1.302, Antigravity CLI 1.4.2, the capabilities digest unchanged;
`config check` on the clone, the running rc1 launcher's `config check` on
this checkout and the full gate, 1672 unit tests, all passed; committed at
`0c1a555`. The recursive attached launch from a fresh clone of that commit
built the formation on the new pins and ran a successor through its eleven
inspection checks, 170 s, nothing left behind. The rc1 launcher's `versions
show` lists the running capsule on the old pins and the shared lock on the
new. Findings: the command also rewrote the manifest in canonical TOML,
dropping its comments and turning `need` into `required` and `optional`;
only the lock was taken, since the vocabulary would shut the released
0.2.15 client out of the shared checkout and the comments carry the
devcapsule0 rationale; the rewrite of an unchanged manifest is a defect
against the conservative-writers ruling, for the owner's word. The gate
scratch under `/opt/devcapsule-gate` vanished again mid-session and `/opt`
is root-owned; recreated with sudo; the filed gap stands.

**2026-10-22, evening: rc2 is go; the second synchronization.** The owner
answered yes to candidate 2 and to merging `main` into the release branch
again: PR #244 merged at `a809970`, PR #247 on `main`; `main` at `e03b060`
is merged into `release-0.3.0` at `245f067`, the status file keeping both
checkouts' entries, the version files the release side, the exception now
worded for the cycle. The changelog has its candidate-2 section and the
overview its rc2 entry. Next: the pre-candidate merge from
`4PR-3-release-0.3.0`, the tag on the tip after it, the backend, the
download, the records. The design-review record of the session logs'
Python data path is filed for V1 at the owner's direction.

**2026-10-22, later: PR #244's review loop is settled; the slice awaits the
owner.** PR244.1, [PR #246](https://github.com/ccozianu/devcapsule/pull/246)
by the Antigravity and Gemini 4 Argon (High) pair, the first review by that
engine in this workstream, is merged after one round: it hardened the
attached run, the bounded daemon stop, the kill race, the notice inside
the guarded block, an unreadable log directory, and proved the mid-chunk
tee fallback; the round took three of its own proposals as defects, the
readiness watcher stopped on the first Ctrl+C, a session the launcher gave
up on left open in its manifest so the pruner's abandonment rule governs
it, and the manifest docstring. Full gate on the merged branch, 1610 unit
tests; the interrupted-launch end-to-end test passed again against that
build. Both briefs and the transcripts are under `evidence/2026-10-22-c10/`.
Open threads from the review: the supervisor blocks SIGINT during a
child's readiness wait, so an interrupt before the desktop is ready waits
for the readiness check; a second Ctrl+C within 250 ms of the first is
absorbed by Python's own wait. Neither changes this slice. Next: the owner
merges PR #244, then rc2 on the owner's word, carrying the network node
and C10; the C17 local half and forced configuration follow.

**2026-10-22, morning: C10 is PR #244; its review partner is the
Antigravity and Gemini 4 Argon (High) pair, by the owner's word.** The two
records are filed, [the terminal](../../bugs/devcapsule/2026-10-22-healthy-launch-looks-unhealthy-in-the-terminal.md)
and [Ctrl+C](../../bugs/devcapsule/2026-10-22-ctrl-c-ends-the-launcher-with-a-traceback.md),
with their rows in the release bug table. On
`ws-maintenance/0.3.0-first-session-summary` off the release branch: the
tee writes a child's output to its file only, the console the fallback
when the file fails; the launcher runs `docker run` under `Popen` and
waits through Ctrl+C, asks the daemon after sixty seconds, stops waiting
on a second Ctrl+C naming the container, records 130 and returns it; every
session ends with one result line and the path of every log file of the
session, the owner's addition; the infrastructure exit code moved into the
runtime contract; four user pages say the result in place of the
traceback. No knob keeps the old streaming, as ruled. The full gate
passed. The end-to-end proof, `tests/e2e/test_interrupted_launch.py`,
launched a fresh VSCodium project in its own process group, sent SIGINT to
the group and read the result: the lines, exit 130, the files, the
container gone, the IDE's output in its file; the transcript is under
`evidence/2026-10-22-c10/`. [PR #244](https://github.com/ccozianu/devcapsule/pull/244)
into `release-0.3.0`. The review partner runs detached in the review
worktree with the brief on standard input; Antigravity's print mode takes
the model flag before the prompt, `antigravity --model <model>
--dangerously-skip-permissions -p '<instruction>' < <brief>`, proven on
2026-10-22 and to be recorded in the developer document. The scratch
directory under `/opt/devcapsule-gate` was recreated after the restart;
the gap is with `project-management`.

**2026-10-22, night: the network-node slice is PR #240, reviewed by
PR240.1; the first loop under topic 9.11.** On
`ws-maintenance/0.3.0-network-node` off the release branch: `network`
joins the host capabilities every project has, with `bridge` as the deny
value already recorded; a unit test on a manifest without the
recommendation proves the run-once command, the bridge default, the
persistent form, the refusal and the listing; the node-registry test's
pinned set gains the node, found by the full gate's first run; two
documentation rows and the README say the node is on every project. The
full gate passed on the branch. [PR #240](https://github.com/ccozianu/devcapsule/pull/240)
into `release-0.3.0`. The review partner, the Codex and gpt-6-astra pair,
answered with [PR #242](https://github.com/ccozianu/devcapsule/pull/242),
PR240.1: the listing attributed an unanswered workstation default to the
manifest, a real defect that predates the slice; a sharper description;
lifecycle tests for the stale transitions when a recommendation appears
and disappears, the unset path, the bulk exclusion and the init
postconditions; the run-once test now proves nothing is written. One
round: the fix was keyed on the node's name where the declaration already
carries `project_recommended`; the general condition went in, correcting
one assertion for `development-sudo`. Accepted at `494e7b0` and merged
into the slice branch; the gate on the merged branch is under
*Validation*. The briefs are committed under
`evidence/2026-10-22-network-node/`, the first under the new rule. The
scratch-mount gap went to `project-management` by mail at `cf12c9eb0393`.
Learned: this Codex version resumes a session with the prompt on standard
input and the sandbox as a config override; the developer document's
recipe says otherwise and is corrected by a small pull request to `main`.
The bug record says fixed; the IDE smoke on a fresh project closes it on
rc2. Next: C10, its two records filed first; then rc2.

**2026-10-22 (`ws-maintenance/e2e_videos-2`): updated landing-page hero eyebrow
and demo video caption in `README.md`, and fixed leftover IntelliJ WebVTT
captions ([ccozianu/devcapsule-website#10](https://github.com/ccozianu/devcapsule-website/pull/10),
[PR #245](https://github.com/ccozianu/devcapsule/pull/245)).**
- Handed the two `README.md` landing-page wording choices to the owner via the
  capsule web console (`2026-10-22-hero-eyebrow-and-caption`) and recorded the
  owner's selections (`answered-at: 2026-10-22T09:35:04+00:00`):
  - `hero-eyebrow`: `ide-list-only` (`PyCharm · IntelliJ IDEA · Eclipse · Rider · VSCodium`),
    replacing `Linux x86-64 · Windows via WSL2 · Apache-2.0 · Pre-V1`.
  - `video-caption`: `polished-close` (`"See a sample of a full graphical IDE running inside DevCapsule's isolated Docker container. More scenario illustrations coming soon."`).
- After PR #236 merged (`423819f`), the owner spotted that the `<track
  kind="captions" src="/assets/session-demo.vtt">` on the landing-page video
  still showed the 4 cues from the earlier IntelliJ IDEA persistence session
  (`"Contained Linux desktop opens after container stop and relaunch; IntelliJ IDEA 2026.2.3 starts in the workspace."`).
- Updated `website/src/assets/session-demo.vtt` ([ccozianu/devcapsule-website#10](https://github.com/ccozianu/devcapsule-website/pull/10),
  merged to `website` `main` at `2bcfe6e` and integrated via [PR #245](https://github.com/ccozianu/devcapsule/pull/245)
  at `e91b965`) and saved a matching copy at
  `engineering-docs/blog/assets/2026-10-21-eclipse-debug/eclipse-hello-time-debug.vtt`
  with 5 timed cues (`00:00.000` to `00:27.420`) mapped from the 329 recorded
  frames of `eclipse-hello-time-debug.webm`.
- Verified with `npm test` (`23 passed`), `npm run check:content` (`187 pages`),
  `npm run build`, and `npm run check` (`191 HTML pages, 13876 local links/assets/anchors`).

**2026-10-22 (`ws-maintenance/e2e_videos-2` / `ws-maintenance/4PR-e2e_videos-2`):
review-partner loop on [PR #236](https://github.com/ccozianu/devcapsule/pull/236)
completed with Claude Fable 5.1; [PR #241](https://github.com/ccozianu/devcapsule/pull/241)
(PR236.1) accepted and merged without a round; PR #236 merged at `423819f`.**
- Synchronized `ws-maintenance/e2e_videos-2` with `origin/release-0.3.0` (`106f8b3`)
  to bring in the review-partner loop rules (`WORKFLOW.md` topic 9.11,
  `WORKFLOW-LOCAL.md` *Review Partners In This Checkout*, and
  `engineering-docs/development/review-partner-loop.md`), preserving `main`'s
  `0.3.1.dev0` version on the four version-bearing files.
- Committed the review brief at
  [evidence/2026-10-22-pr236-review-brief.md](evidence/2026-10-22-pr236-review-brief.md)
  (`e2f41cd`) and ran the review partner (`claude -p --model claude-fable-5-1 --dangerously-skip-permissions`)
  in an isolated worktree (`/home/devcapsule/worktrees/maintenance-review` on
  `ws-maintenance/4PR-e2e_videos-2-review`).
- Operational finding recorded in `engineering-docs/development/review-partner-loop.md`:
  in `claude -p` (single-turn print mode), a Bash tool call started with
  `run_in_background: true` is killed when the turn exits; running `nox -s build`
  synchronously in the foreground (and resuming with `claude -c -p` when needed)
  completed the full gate in 2 minutes.
- Claude Fable 5.1 opened [PR #241](https://github.com/ccozianu/devcapsule/pull/241)
  (`a33338a`, `a9eb87b`) with ten concrete improvements and 50 new unit tests
  (96 total across the 4 touched test modules, verified with a 17-point mutation
  check):
  1. `ActionStep.parse` validates `seconds` with `_require_int` (rejecting booleans),
     refuses steps setting both `ms` and `seconds`, and requires non-empty `text`
     for `press` and `type`.
  2. `ScenarioSpec.from_dict` and `seed_scenario_workspace` reject empty,
     whitespace-padded, directory-only, absolute, and `..` paths in `seed_files`,
     and verify `target.resolve()` stays inside `workspace.resolve()` before writing.
  3. `BurstFrameRecorder.encode_webm` writes `ffmpeg` stderr to
     `scenario-video.webm.ffmpeg.log` instead of an unread pipe, reaps `proc`,
     joins `reader`, and closes pipes on every exit path; `_resolve_ffmpeg_cmd`
     catches `(OSError, subprocess.SubprocessError)` and returns `None`.
  4. `start_controller_server` and `ControllerQueue` extract the loopback HTTP
     controller so it is unit-testable without a container, returning `400` on
     malformed JSON/UTF-8 or non-dict payloads without queueing and `504` on
     command timeout; `write_json_atomically` writes `controller.json` via temp
     file + `os.replace` after unlinking stale copies; `ctl` exits `2` on
     non-object JSON and `1` when `ok` is false.
  5. `noxfile.py` (`ide_smoke`) requires a single `--surface` and refuses
     `--agent` when `--scenario` is passed.
- Accepted PR #241 without a round, merged it into `ws-maintenance/4PR-e2e_videos-2`
  and `ws-maintenance/e2e_videos-2` (`e17065e`), removed the review worktree,
  and reran `nox -s build` (`1649 passed`, `mypy` clean over 216 files,
  `17 passed` packaging, `187 pages` docs-contract, `293 passed` webconsole).

**2026-10-22, later: PR #237 and PR #239 merged; `main` merged into the
release branch.** PR #238, stacked on #237's branch, merged into that
branch instead of `main` because the branch survived #237's merge while
#238 was open against it; PR #239 carried its content and the rule-8
rewrite to `main`. Then, by the owner's direction, `main` at `c779dc2` is
merged into `release-0.3.0`, a one-time synchronization recorded under
*Exceptions* in `WORKFLOW-LOCAL.md`: nothing was developed on `main`
outside the candidate process, and the cycle's workflow rules must bind
this checkout. The version-bearing files keep the release side. The
website submodule's working tree was brought to the committed pointer so
the documentation contract could run; it passed, as did the version and
workflow suites.

**2026-10-22: two workflow pull requests to `main`, at the owner's
direction, before the network-node slice.**
[PR #237](https://github.com/ccozianu/devcapsule/pull/237), from
`ws-maintenance/gh-cli-rule` off `main`: the local file's *GitHub
Integration* section replaced by the conditional rule of 2026-10-21, the
GitHub CLI used when the human provides it under `/opt/xtras`, detected by
its file, activated per shell call, its login checked once per session,
the compare link handed over when it is absent; and Release Policy rule 8,
the throwaway copy, rewritten in the controlled style with the companion
paragraph it lacked. [PR #238](https://github.com/ccozianu/devcapsule/pull/238),
stacked on it: the review-partner loop, the mechanism of the webconsole
and diagnostics slices extracted from the transcripts of 2026-10-09 to
2026-10-12 as topic 9.11 of `WORKFLOW.md` with its Changes bullet and
companion, the local section *Review Partners In This Checkout*, and the
developer document with the brief template, the assessment forms, the
recipes per engine and the record of the loops run. The definition change
is noticed to `workflow-improvements` by mail at `574b6bc68268`. Both go
to `main` directly because a workflow rule binds every workstream now;
the release branch's copies lag as they already do for the main-reopens
rule. A finding on the way: the gate's scratch under `/opt/devcapsule-gate`
is on the container's overlay and died with the restart; the owner sees a
product gap, a host-backed scratch mount in the capsule contract, to be
filed with `project-management` on the owner's word. The network-node
branch created for the rule was deleted unused; the slice starts clean.

**2026-10-21 (`ws-maintenance/e2e_videos-2`): reusable scenario-driven E2E IDE
controller and pause-free WebM recorder packaged; Proof of Concept #1 Eclipse
Java debugger video (`eclipse-hello-time-debug.webm`) recorded, saved, and
wired into `README.md` (`website:demo`).**
- Merged PR #234 (`ccozianu/devcapsule`), PR #9 (`ccozianu/devcapsule-website`),
  and PR #235 (submodule bump to `f4d35d2`), then opened continuation branch
  `ws-maintenance/e2e_videos-2`.
- Packaged `devcapsule-src/tests/e2e/scenario_recorder.py` (`ActionStep`,
  `ScenarioSpec`, `BurstFrameRecorder`, `run_scenario_replay`,
  `serve_interactive_controller`, `send_controller_command`) and wired
  `--scenario` (`DEVCAPSULE_SMOKE_SCENARIO`) into `devcapsule-src/noxfile.py`
  (`ide-smoke`) and `devcapsule-src/tests/e2e/test_ide_comes_alive.py`, with
  unit tests in `devcapsule-src/tests/test_scenario_recorder.py`.
- Packaged the Proof of Concept #1 scenario definition at
  `devcapsule-src/tests/e2e/scenarios/eclipse-hello-time-debug.json` and saved
  the recorded 27.4 s (`1600×1000`, `1.35 MB`, 12 fps pause-free) WebM video
  and key screenshots under
  `engineering-docs/blog/assets/2026-10-21-eclipse-debug/`.
- Updated `engineering-docs/development/e2e-tests.md`, added
  `engineering-docs/development/running-e2e-scenario-recordings.md` and
  `engineering-docs/implementation-notes/devcapsule/2026-10-21-e2e-scenario-video-recorder.md`
  (indexed in `index.md`), and updated `README.md` (`website:demo`) to display
  `eclipse-hello-time-debug.webm` + `eclipse-hello-time-debug-poster.png` with
  a concise visitor-facing caption and no QA/audit boilerplate.

**2026-10-21: resumed under rc1; the owner's rulings.** This capsule runs
under the downloaded rc1 (`devcapsule0 version`: `v0.3.0-rc1`, source
`7016cdd`), on the local recipe-11 base; the console answers. The shared
lock is unchanged since 2026-10-04, so the agents in this capsule are the
old pins, Codex 0.157.1, Claude Code 2.1.283, Antigravity 1.2.12; the rc1
pins have run nowhere yet, and the freshness table's provider acceptance
stays open until the owner's lock command. `main` moved past the release
branch with PR #234 and PR #235 from the second checkout, the landing-page
work and the hero-video work order on `ws-maintenance/e2e_videos`; a test
merge of the release branch into `main` is clean. That session published
this file with the rc0 state line; this publish restores the live copy.
The owner's rulings of 2026-10-21: the console-link fix is verified on
rc1 against both bases and
[the record](../../bugs/devcapsule/2026-10-18-console-link-printed-on-a-base-without-the-console.md)
is closed, the console working as 0.3.0 requires it; the base is published
later, in the promotion of the accepted candidate; the candidates are
grouped, rc2 the network node and C10, rc3 forced configuration and the
diagnostics snapshot, rc4 image cleanup and C20; C17 stays a gate in both
halves, the generic rule in `WORKFLOW.md` with `workflow-improvements` and
this project's own operating instructions in `WORKFLOW-LOCAL.md`, since a
concrete, complex case is how the abstract rule gets debugged. The local
half, build, the three test tiers separately, selective tests, the main
program and the debugger with its attachment, is a maintenance slice of
this cycle; the generic half waits in `workflow-improvements`' mailbox
since 2026-10-11, which the owner knows.

**2026-10-19 (`ws-maintenance/e2e_videos`): landing-page work order
(`2026-10-18-landing-page-why-devcapsule.md`) baseline verified; bounded
stretch-goal inspection completed.**
- **Baseline (Deliverables 1–4):** Recorded the work order at
  `engineering-docs/work-orders/2026-10-18-landing-page-why-devcapsule.md` and
  indexed it in `index.md`. Extended Contract v1 (`website/CONTRACT.md` and
  `engineering-docs/specifications/product/content-website-contract.md`) with
  `website:demo`, `website:continuity`, multi-paragraph `website:hero`, and
  self-hosted `.webm`/`.mp4` assets. Replaced the invented right-hand hero
  schematic with a framed `1152×720` (`16:10`) 26-second (`2.6×`) WebM excerpt
  (`after-restart-hero-excerpt.webm`) and poster (`after-restart-hero-poster.png`)
  from the verified 2026-10-04 IntelliJ persistence session, with WebVTT captions,
  step summary, modal `<dialog>` expansion, and direct links to both full
  recordings (`after-restart.webm`, `first-session.webm`) and the validation
  note (`2026-10-04-intellij-playwright-validation.md`). Reorganized
  `website:benefits` into three outcome-led cards, added the four-fact
  `website:continuity` handoff excerpt, and aligned `/why/`. Verified with
  `npm test` (`23 passed`), `npm run check:content`, `npm run build`,
  `npm run check`, `nox -s docs-contract`, 50 documentation unit tests,
  `scripts/browser-check.mjs` (59 viewport/palette/WCAG A/AA audits), and
  Playwright layout/playback checks at `1366×768` and `390×844`.
- **Stretch-goal inspection (15-minute budget):** Inspected the cached
  `devcapsule-local-eclipse:59ccaf413ce00f743fbc` image. It includes Eclipse
  2026-09 R (`/opt/eclipse`), OpenJDK `25.0.4+7` (`/opt/java/jdk-25.0.4+7`),
  Apache Maven `3.9.16`, JUnit 5/6, EclEmma `3.1.12` (`org.eclipse.eclemma.ui`
  + JaCoCo `0.8.15` for source coverage highlighting), and CLI `jfr`. Two
  prerequisites for the 6-step 1BRC stretch scenario are absent without
  component/harness changes: (1) no coding agent (`claude`, `codex`, `agy`) is
  installed in the cached Eclipse image and the E2E harness does not copy parent
  agent credentials into child IDE capsules, and (2) no graphical profiler UI
  (`JDK Mission Control` / `org.openjdk.jmc.*` / `VisualVM`) is bundled in
  `eclipse-ide` (`--network none` prevents runtime Marketplace installs). Per
  the work order's stop condition, stopped the stretch pass, retained the
  verified baseline recording, and recorded the follow-up stretch-goal work
  order at
  `engineering-docs/work-orders/2026-10-19-eclipse-java-1brc-hero-video.md`
  (indexed in `index.md`) with a preamble of reusable work and unblocking
  options.

**2026-10-19: the console-link fix is PR #232, along the owner's lines.**
The launcher reads the base's promise from its labels before the launch,
`web_console_availability` in the images contract: the
`devcapsule.base.webconsole` label and recipe 11 or later, the recipe
that gives the console its process monitor. `project run` reads it beside
the display transport and hands it to the launcher, which on a base
without the console plans nothing, no port, no token, no console section,
no published port, no origin, no readiness watcher, and prints one
statement in place of the link: the base, the recipe the console needs,
the one `images build` command with the launcher's own source revision,
and the guide. The guide is new, `docs/configuration/local-base.md`, the
page the C16 gate was missing: build a base, list it, select it with
`config authorize base-image`, what the selection is and is not, the way
back. [PR #232](https://github.com/ccozianu/devcapsule/pull/232) into the
release branch; the full gate passed end to end and the hosted run passed;
the bug record says fixed, verification on a downloaded candidate against
the recipe-9 and a recipe-11 base closes it. The implementor-and-reviewer
loop's review round is the owner's to run.

**2026-10-19: the console works on a recipe-11 base built from rc0.** The
owner built the base on the host with the candidate's own `images build`,
provenance `53ebc17`, selected it for the second checkout with `config
authorize base-image`, the developer-owned selection the product
provides, resolved and launched: the console answered on the printed
link. Two things follow for the cycle. The published recipe-11 base, a
gate before the final tag, is what makes this the default for everyone;
and the user documentation has no page that walks through building and
selecting a base, which belongs to the C16 documentation gate.

**2026-10-18, the owner's first finding on rc0: a console link on a base
without the console.** The launcher prints the web console link for every
run, and the runtime then says the base has no console, which is true of
the published `ubuntu-24.04@9`. Filed as a bug by the owner's word, target
0.3.0, a release fix in this cycle:
[the record](../../bugs/devcapsule/2026-10-18-console-link-printed-on-a-base-without-the-console.md).
Then, the owner reports, the launcher waits 180 s for that console and
advises opening the link; the readiness watcher shared with the display
cannot hear the runtime's notice. The launcher can read the base's
recipe label before it prints; the fix is one statement that is true,
link or substitute line, and no port, token or wait for a console that
cannot answer. It sits beside C10, the
first-session summary, and goes in the same slice or just before it. The
changelog's *Known in candidate 0* and the bug table carry it.

**2026-10-18, rc0 tagged.** PR #231 merged; the owner said go. The tag
`v0.3.0-rc0` is on `53ebc17`, the release branch's tip at the merge, whose
source is byte-identical to the fully gated PR #230 tree; the two record
commits after it carry no source. The candidate gate script, run from a
detached checkout of the tag before the push, reported `mainline` and no
unintegrated commits. Pushed atomically with the branch; backend run
39175482525 passed, the prerelease is public with its three assets, and
the download under `~/.cache/devcapsule-releases/v0.3.0-rc0` verifies:
checksum file and manifest agree on the executable, which reports
`0.3.0rc0` at `53ebc17`. Deliverable 1 of the work order is done to its
letter. Next the owner's test on the other checkout; the local Docker
proofs against this download follow that. The owner keeps this capsule, the old workhorse,
running meanwhile.

**2026-10-18, night, second: the pre-candidate merge goes through a
throwaway copy, PR #231.** PR #229 and PR #230 are merged. The owner
keeps delete-on-merge on and rules the workaround for the one ref that
must survive its merges: each merge of the release branch into `main` is
a pull request from `4PR-NNN-release-X.Y.Z`, the owner's spelling of the
same night so that no copy starts with the `release-` prefix, a copy
created at the release branch's tip for that pull request alone, deleted
on merge;
*Release Policy* 8 in `WORKFLOW-LOCAL.md` and the runbook's step 2 say
so, with the copy named a throwaway integration ref, never a release ref,
since the definition wants release refs told by name alone.
[PR #231](https://github.com/ccozianu/devcapsule/pull/231) from
`release-0.3.0-4PR-1` is the first: the pre-candidate merge, carrying
PR #230, the policy rule and this file's record; `main` keeps 0.3.1.dev0.
After it merges, every commit of the release branch is reachable from
`main`, the main disposition for rc0 is ancestry, and the tag waits for
the owner's word.

**2026-10-18, last: the red test was wrong, not the lock; PR #230.** The
owner read `test_resolution_reconstitutes_the_dogfood_environment` and
ruled it unacceptable: it asserted that the repository's committed lock
equals the matrix's newest selection, repository housekeeping rather than
a behaviour of the code, unsatisfiable from inside a capsule since only a
host launcher command writes the lock, and silent about whether an older
project still launches. The analysis went through three candidate
triples; the owner kept one. [PR #230](https://github.com/ccozianu/devcapsule/pull/230)
into the release branch deletes the test and adds
`test_repository_lock_is_launchable_by_this_launcher`: precondition the
committed lock as written by an earlier matrix; action
`parse_locked_environment`, the reader `project run` uses; postcondition
a launchable environment, the surface, the base, one validated artifact
set per materialized component. Its TODO names the wider contract as a
new work item, [the bug record](../../bugs/devcapsule/2026-10-18-no-test-proves-old-projects-launch-with-new-releases.md):
every project initialized by an earlier release keeps launching with a
new one, to be enforced over configurations captured from each released
client; no target, next planning. The hosted unit run on the pull request
passed; the full local gate passed end to end, so the lock command on the
host is no longer a gate for rc0, only the dogfooding it always was. After
the merge, the pre-candidate merge of the release branch into `main`
carries the fix there; PR #229 stays separate.

**2026-10-18, late: `main` reopens at the cut, PR #229.** After PR #228
carried 0.3.0 onto `main`, the owner weighed cherry-pick stacking and
chose, on the agent's analysis, a protocol change instead: a development
version orders before the release it names under PEP 440, so `main` on
the old development version sits behind the release branch for the whole
cycle. From now on `main` reopens with the next development version at
the cut, by pull request, and the merges of the release branch into `main`
before each candidate tag carry no version conflict after the first.
[PR #229](https://github.com/ccozianu/devcapsule/pull/229) is the rule
and its first application: `main` to 0.3.1.dev0, the manifest's
release-branch line removed from `main`, *Version Scheme* rule 4 and an
*Exceptions* entry in `WORKFLOW-LOCAL.md` against topic 11.2.7, the
runbook's steps 1 and 7 following; the definition change is mailed to
`workflow-improvements`. Its gate fails only the lock test, as `main` does
since PR #228; the documentation contract passes with `devel` at
0.3.1.dev0. The release branch keeps its own `source-version` line, since
its source declares 0.3.0. Cherry-pick stacking was set aside: it would
need every non-merge release commit cherry-picked or excepted at each
candidate, and the version commit never can be.

**2026-10-18, night: everything merged, the release branch merged into
`main`, the branch restored, the lock still the owner's.** The owner
merged PR #224 into the release branch at `6b97657` and then the release
branch into `main` by [PR #228](https://github.com/ccozianu/devcapsule/pull/228)
at `7c20292`. `main` therefore carries the release version 0.3.0, the
matrix at embedded-27 and the manifest's release-branch line; the
decision's "`main` stays at 0.2.16.dev0" gave way to the owner's merge,
as in 0.2.14, and the prepared-merge-branch thread below is closed by it.
`main` reopens with the next development version after the final tag, as
the version scheme says. GitHub deleted `release-0.3.0` on that merge: the
repository has `delete_branch_on_merge` on, which deletes every branch a
merged pull request came from, release branches included. The ref is
restored at `6b97657`, the exact tip it had, nothing lost; the setting is
the owner's to turn off, or every pre-candidate merge will delete the
release branch again. The shared lock is still at embedded-23 on both
branches, so the dogfood-reconstitution test fails on `main` and on the
release branch until the owner's host command runs; the candidate
workflow runs the unit suite, so rc0 cannot be tagged before it.

**2026-10-18, evening: the unit gate with coverage runs on pull requests
against `main` and `release-*`; PRs #225 to #227 merged.** The owner's request of the day, as part of this
release: `tests.yml` now triggers on pull requests against `main` and
against `release-*` branches, the owner's addition of the same evening,
as well as on pushes to `main`: the same job, the summary and the report
before the merge, rapid pushes to one pull request cancelling the older
run; the badge still comes from `main` alone. [PR #225](https://github.com/ccozianu/devcapsule/pull/225)
into `release-0.3.0`, with the unit-tests document updated. Left to the
owner: making the `Python 3.12` check required in the repository rules,
and a coverage threshold if one is wanted. The owner merged PR #225 with
the `main` trigger while the `release-*` addition was still in flight;
that commit follows as PR #226 from the same branch, and since GitHub
reads a pull request's workflow from its merge commit, PR #226 is the
first real run of the `release-*` trigger.

**2026-10-18, later: the agent freshness slice is PR #224, gated on one
owner step.** The upgrade attempt the runbook asks of every release is on
`ws-maintenance/0.3.0-agent-freshness`, forked from the release branch's
tip, as [PR #224](https://github.com/ccozianu/devcapsule/pull/224) into
`release-0.3.0`: the matrix at `embedded-27` with Codex 0.163.0, Claude
Code 2.1.302 and Antigravity CLI 1.4.2, every artifact checked against its
vendor's own integrity value, the golden locks regenerated, provisional
verified edges, and a two-pass startup smoke in a disposable container on
the local recipe-11 base, where the three CLIs reported their versions as
a fresh uid-1000 user, Codex listed its 175 feature flags over the seeded
`config.toml`, Claude's debug log took `mode=bypassPermissions` from the
seeded settings without a flag, and the seed files stayed byte-identical.
The evidence is in the [overview](../../releases/v0.3.0/README.md). The
branch is not gated: the test that resolves this checkout's own need
against the matrix fails until `.devcapsule/devcapsule.linux-amd64.lock`
carries the new pins, and the local rule lets only a DevCapsule command
write it, outside the capsule, where `config capabilities` and `config
check` both refuse as launcher-only. The command for the owner, with the
PEX built from the slice in the shared checkout, is in the PR and the
overview. Judgment recorded: the slice went on its own branch for the
implementor-and-reviewer loop the owner directed for the cycle, which
reads against topic 11.3's "open no new working branch under the name";
the decision record already hands the standing rule to
`workflow-improvements`.

**2026-10-18: release 0.3.0 is cut; maintenance drives it.** The owner
decided the scope, the driver and the cut in the project-management session
of the same day: [the decision](../2026-08-09-project-management/2026-10-18-decision-release-0-3-0-scope-and-cut.md)
and [the work order](../../work-orders/2026-10-18-release-0-3-0.md). The
order was taken from the mail and acknowledged, together with the two items
of 2026-10-11 that were waiting in the intake: the bootstrap retargeting is
applied, the [record](../../bugs/devcapsule/2026-08-03-ecosystem-aware-project-bootstrap.md)
now says 0.9 with the dated ruling; the pre-candidate sequence is superseded
by the cut decision, which moves consent out of 0.3.0 and forced
configuration into the candidate cycle. The cut commit is
`3c91183ffd2130f6c7b40d2f9e3fd41588f977eb`, `main` at the merge of PR #223,
chosen because nothing of maintenance was unmerged, PR #207 and PR #209
having reached `main` on 2026-10-11 and through #216 on 2026-10-15, and
because that commit carries the decision and the order themselves.
`release-0.3.0` starts there; its first commit, `6965c5e`, sets the version
to 0.3.0 in the three authored copies, by `nox -s bump`. `main` stays at
0.2.16.dev0 until the final tag. The release overview, the bug table and
the checklist are under [releases/v0.3.0](../../releases/v0.3.0/README.md).
The agent freshness review of this date found every vendor ahead of the
pins: Codex 0.163.0 against 0.157.1, Claude Code 2.1.302 against 2.1.283,
Antigravity 1.4.2 against 1.2.12; the table is in the overview, and the
upgrade attempt is the next step, before rc0 as 0.2.15 did it, unless the
owner says rc0 ships the current pins. The gate on the branch is under
*Validation*.

Judgment where the contract is silent, recorded as topic 3 asks: the
website's content check, which the gate runs, reads the checkout as `main`
and requires the `devel` entry's source to declare a development version;
on the release branch the source declares 0.3.0, so the check failed. The
manifest on the release branch now carries `source-version: "0.3.0"` on
the `devel` entry, the form the check itself names, with a comment that the
line is release-branch metadata, not carried to `main`, where the source
declares a development version. The durable rule, a check that knows a
release branch, or a manifest form for it, is project-management's, as the
contract's owner; mailed on 2026-10-18.

**2026-10-12: the process record was mailed to the trading-research sample
project.** At the owner's request, an intake item describing the
implementor, reviewer and owner loop with pull requests, what it produced,
what we learned, and how it may inform that project's LLM debates, was
delivered to `project-management` of
`ccozianu/devcapsule-sample-trading-research` with `devcapsule workflow
mail send`, run in the submodule checkout. That repository had no
coordination branch; the tool created it, commit `9d26eed`. A sender from
another repository is outside the definition; the item says so and the
owner directed it. The submodule pointer is untouched.

**2026-10-11, after the owner's report: the stack's conflict resolved.**
PR1's branch was rebased on GitHub onto the newer `main`; its commits kept
their content and changed their hashes, so PR2, which carried the old
merge, showed a conflict in every file. One merge of the rewritten PR1
tip into PR2's branch resolved it: every conflict took PR2's version, the
tree changed only by the coverage badge, and both PRs read mergeable
again. Note for the next time: a rebase of a stacked branch's base rewrites
history the branches above it carry; the local rule, merge rather than
rebase for published branches, exists for this.

**2026-10-11, last: round three merged; the rounds on PR2 are used; the
owner's turn.** [PR #212](https://github.com/ccozianu/devcapsule/pull/212),
the Codex pair's review of the in-process rotation, was merged: compression
completes before any history is expired, a gap in the archives ages its
slot out, short raw writes are completed and accounted, a second failure
while closing cannot stop the tee from draining the pipe, and the docs
state the limits: synchronous compression on the writer, a non-atomic
sequence with a crash table, a write rather than a line as the unit. Two
proposals stay as threads below. The gate on the merged branch is recorded
under *Validation*. The owner also asked that this change go through the
same review scheme; it did.

**2026-10-11, later again: the owner clarified the rotation; every writer rotates its
own file.** The owner's mental model was the piped rotator, the writer
that rotates on write when the size is reached, and asked for "the solid
approach with no overshooting". PR2 changes accordingly: `SegmentedFile`
in `devcapsule.logs` rotates the live file the moment a write would carry
it past its segment, compresses it to `.1.gz`, shifts the older segments
and drops the one beyond the count; the tee and the Python handler both
write through it. The logrotate child, its stanza, the reopen-on-rename
logic and base recipe 12 are gone; the base stays at recipe 11 and the
behavior is the same on every base. Exact bound: the live file never
exceeds its segment, except a single write longer than the segment, which
goes into a fresh file alone. The budget knob, the segment derivation, the
manifest and the pruning are unchanged. The earlier logrotate acceptance
evidence stands as history; the rotation it proved is replaced, and the
unit suite now proves rotation with a real child writing 4000 lines
through the tee. A third Codex round reviews this change.

**2026-10-11, late: acceptance passed on a real capsule; PR #207 and PR
#209 await the owner.** From a clean clone of PR2's branch at `174480f`, a
public PEX built the recipe-12 base through `nox -s e2e -- --build-base`:
nine end-to-end tests passed, the built base carries recipe-version 12 and
answers `logrotate --version`. A fresh codium project then ran through the
real launcher on that base with a 16 MiB budget. The session directory
held every component's file, user-owned, plus `logrotate.conf` and
`session.json`; the supervisor's record shows logrotate as the first child
and the session's end; a log padded to 1.5 MiB was rotated to `.1` by the
next tick with no complaint in `devcapsule-logrotate.log`; the launcher
recorded the `docker run` and the end, and `session.json` carries
`ended-at` and the exit code. Evidence under
[evidence/2026-10-11-session-logs](evidence/2026-10-11-session-logs/).
Not shown by this run: compression, which needs a second rotation of the
same file, and a writer's reopen, since the padded panel printed nothing
afterwards; both are pinned by unit tests.

**2026-10-11, night: PR2.1 accepted; logrotate became a supervised child.**
The Codex pair's review of PR2, [PR #210](https://github.com/ccozianu/devcapsule/pull/210),
was merged: UTC arithmetic for abandonment, the budget falls back to the
default with a warning instead of refusing the launch, `nocreate` so the
writers own the replacement file, and both rotation keys required
together. Its three proposals were right and were taken as defects: the
rotation thread was created before the supervisor blocks its signals, so a
SIGTERM could end PID 1 without the orderly stop, and the supervisor's reap
loop could take logrotate's exit first. Commit `adfbff7` runs logrotate as
a supervised child, a `sh` loop that sleeps the interval and runs
logrotate, started first and stopped last, teed into
`devcapsule-logrotate.log`. The gate passed again. The second round,
[PR #211](https://github.com/ccozianu/devcapsule/pull/211), found no
runtime defect and was merged: it pins SIGTERM and SIGKILL of the loop
under the real supervisor, hostile paths through `shlex.join`, and the
`gosu` wrap, and corrects the wording on shutdown. Rounds used on PR2: two
of three. Acceptance on a real capsule follows; see *Validation*.

**2026-10-11, evening: PR1.1 accepted; slice 2 is
[PR #209](https://github.com/ccozianu/devcapsule/pull/209), stacked on PR1.**
The Codex pair's review of PR1, [PR #208](https://github.com/ccozianu/devcapsule/pull/208),
was merged into PR1's branch without a round. It found five real gaps:
the tee waited for a newline, the per-child drain could delay signal
forwarding, `DEVCAPSULE_LOG_LEVEL` never entered the container, a log
directory an external daemon cannot see produced an empty bind, and the
console's access log could persist tokens under INFO. Its two proposals are
open threads below.

Slice 2, by the owner's brief of the same day: logrotate owns the rotation
and one knob, `DEVCAPSULE_LOG_BUDGET`, bounds the checkout's logs directory
(256 MiB by default, 16 MiB floor). The entrypoint writes `logrotate.conf`
and runs logrotate as the capsule user every 30 seconds; the writers reopen
after a rotation; the segment per file is one thirty-second of the budget
within 1 to 10 MiB, four rotations, delayed compression; the launcher
records the session's end in `session.json` and prunes only ended sessions;
base recipe 12 ships logrotate and an older base keeps the 50 MiB cut. The
reviewed PR1 is merged into the slice. Gate green; see *Validation*.

Judgments for the owner's review in PR #209: the knob is an environment
variable, not a configuration node, because a node changes the manifest
vocabulary released launchers guard; the directory may exceed the budget by
the running sessions and a file its segment by thirty seconds of output,
both stated in the docs.

**2026-10-11, later: persistent session diagnostics, slice 1, is
[PR #207](https://github.com/ccozianu/devcapsule/pull/207).** The owner
merged PR #172 and said "go for it" on item 1 of the plate, with the brief:
every critical component writes a log recognizable by its file name, at the
WARNING equivalent of slf4j, with the launcher, the supervisor, the desktop
manager, the IDE and the web console as the components; where a component
has no level, redirect its stderr and stdout through a tee so the console
keeps them. Slice 1 is the Python logging framework and that wiring:

- `devcapsule.logs`: `devcapsule-<component>.log`, WARNING baseline,
  `DEVCAPSULE_LOG_LEVEL` override, lifecycle events at INFO always, a
  UTC-stamped rotating file (10 MiB, five segments), the tee with a 50 MiB
  cut, the newest 20 sessions kept per checkout.
- The runtime plan carries a `logs` section; the supervisor tees every
  child and records starts, readiness, exits and signals; Xvnc logs at
  status (`-Log *:stderr:10`); the console honours the override; the
  launcher creates `<state namespace>/logs/<session id>`, binds it at
  `/var/log/devcapsule`, writes `session.json` and its own log, and prints
  the directory; `project info` lists the row; the diagnostics page is
  written.
- Delivery follows the owner's review scheme from the web console work:
  stacked PRs, each reviewed by the Codex and gpt-6-astra pair as PRn.1
  from a `-review` branch, at most three rounds, the owner merges.

Judgments recorded for this slice, for the owner's review in the PR:

- Xvnc's baseline is its status level, not errors only, because connection
  accepted and closed are the events the original incident needs.
- The web console writes no file of its own; its stderr is teed like every
  other child, so one mechanism covers every component.
- The IDE's native log stays in its slot; the session directory holds the
  IDE's standard streams.
- The size numbers are the work order's proposal; compression and the
  aggregate budget are the next slice, with the snapshot command after.

**2026-10-11: resumed; `main` merged in; the diagnostics work order is
accepted.**

- The owner merged PR #174 into this branch on 2026-10-08. PR #172 stays
  open against `main`.
- `origin/main` was merged in at `86f78eb`: 118 commits, no conflicts.
  The definition changed since the last read: the controlled-language
  edition, decisions handed to the human through capsule state and chat,
  work orders, materialized views, diagrams first in DOT, recorded visual
  end-to-end tests. The local file adds the web console session to the
  gate and the rules for definition changes. All are read and apply from
  now.
- Three mail items were taken and decided; see the decision log. The two
  capsule-webconsole items on the `project info` checkout name are
  superseded: the owner directed that fix into capsule-webconsole, and
  `checkout_name_for` is on `main`. The project-management item assigns
  persistent session diagnostics to maintenance, target ready for 0.3.0,
  urgent. It is accepted onto the plate below. Its work order text is the
  intake item at coordination `a535ccf`; project-management owes the
  committed file at
  `engineering-docs/work-orders/2026-10-08-persistent-session-diagnostics.md`.
- The C10 first-session bug records (a ready/stopped/error summary, Ctrl+C
  ends with a result) are not filed on `main` yet. The diagnostics slice
  coordinates with that work, as the assignment asks.
- This capsule's base has no web console tools, so decisions reach the
  owner as numbered chat text under topic 8.8.
- The gate on the merged tree passed; see *Validation And External State*.

**2026-10-08: PR #172 reviewed at `4be56a7`; fixes are in
[PR #174](https://github.com/ccozianu/devcapsule/pull/174), from
`ws-maintenance/pr172-correctness` into `ws-maintenance/post-0.2.15`.** The owner requested no edits to
#172 and a stacked fix PR. Seven regressions failed before the correction;
the focused suite now passes 69 tests. The unpack cache now locks each digest
through inspection and publication, validates completion records and root
containment, and cleans/reuses one staging path after failure. The full build
gate passed: 1,177 unit cases, nine packaged integrations, mypy, source/PEX
smokes and the documentation contract. See [review and evidence](2026-10-08-pr172-review.md).

Synchronization exception: this owner-directed review branches from #172,
leaving its source branch unchanged; main synchronization belongs to the parent
integration. Main's newer configuration-writer rules were read; this review
changes no project configuration. The explicit `gh` authorization supersedes
the local UI-only delivery rule for consulting, creating and updating PRs.
The isolated review worktree preserves the original checkout's dirty website.

The three component-catalog messages were received and acknowledged. Their
configuration implementation and format rename reached main through #170.
The maintenance configuration argument is retained as a historical snapshot
at `85bec27`; updating its old links/names is queued after this review stack
integrates, together with the existing configuration follow-ups, not mixed
into these cache corrections.

**2026-10-06: named build contexts are built and measured.** Directory
inputs are named contexts read in place, one context root per launcher
cache, archives unpacked once by digest. On the real 3.69 GB PyCharm tree
a rebuild after a launcher change transfers 1.29 MB in 1.1 s instead of
3.69 GB plus a 9 s copy; first build of a tree still sends it once. Gate
green; record updated with the table and what is left for the reuse and
reaping design review. The design as built is written up for the owner in
[image layers, the local cache, and composition](../../implementation-notes/devcapsule/2026-10-06-image-layers-local-cache-and-composition.md). Next on the plate: the universal `network` node,
then that design review.

**2026-10-05, latest: option D is built and proven; the recursive attached
launch runs from a fresh workspace.** `tests/e2e/fresh_workspace.py` is the
fresh-workspace rule as code; the attached-launch test uses it and passed
in this capsule (run `8a543a0613a9c1f22d839102d592c995`, eleven inspection
checks, container removed, workspace removed). The 2026-10-04 record and
the 2026-08-15 record are status fixed, closing on a 0.3.0 candidate.
Next on the plate: named build contexts. Seven older run directories
under the persistent home's E2E workspace predate the cleanup rule; they
are the owner's to remove.

**2026-10-05, later: the in-capsule project-command fix is on the branch,
status fixed, gate green; see the two records.**
The `project` group applies a per-subcommand `CapsuleAccess` after
resolving the subcommand without side effects: the capsule's project is
selected from any directory, read-only commands answer, mutating ones
name the launcher, unknown names are unknown. Proven by unit tests and
by the source CLI from `/opt` in this capsule. Next on the plate: the
fresh-workspace recursive test (option D).

**2026-10-05: the 0.3.0 triage is complete; the plate is set.** The decisions are listed under *Resumed 2026-10-03* and
the records they changed. Two bounded things happened on the branch beyond
records: the packaging version test now runs its check from a temp
directory (component-catalog's patch, three cases green with the editable
egg-info present), and the three component-catalog items are
dispositioned. The branch is ahead of `main` by records and that one test
change; the owner pushes and opens the PR.

### The 0.3.0 maintenance plate

The [work order of 2026-10-18](../../work-orders/2026-10-18-release-0-3-0.md)
fixes the deliverables; the order of the slices within the cycle is the
driver's, the network node and C10 first being the recommendation. Done
before the cut and on `main`: the fresh-workspace recursive test
(2026-10-05), the in-capsule project-command fix (2026-10-05), named build
contexts (2026-10-06), the session logs with in-process rotation and a
budget (#207, #209, #216). Each slice below is a maintenance slice with the
implementor-and-reviewer loop as practiced on the diagnostics slices, lands
on the release branch by the owner's direction, and merges to `main` before
the next candidate tag.

1. The cut and candidate 0: cut, version and records done 2026-10-18; the
   pull request to `main`, the tag and the downloaded-asset proofs follow
   on the owner's word.
2. The agent freshness review's upgrade attempt: done as PR #224 into the
   release branch; merges once the owner regenerates the shared lock on
   the host and the gate passes, or waits for rc1 if rc0 ships the
   current pins.
3. The universal `network` authorization node: run-once and saved
   `network host` on a project without a recommendation, bridge the
   default; closes the [bug of 2026-10-05](../../bugs/devcapsule/2026-10-05-run-once-network-authorization-needs-a-recommendation.md)
   on a candidate.
4. C10: a ready, stopped or error summary instead of streamed desktop
   diagnostics, and Ctrl+C ending with a result, not a traceback; the two
   bug records filed first; closes both on a candidate. Beside it, the
   owner's rc0 finding of 2026-10-18: the console link printed on a base
   without the console, fixed as PR #232, verified on the next candidate.
5. Forced configuration: `project config resolve --force` and `project run
   --force-config`, mandatory needs split from optional ones; the
   requirement below; the capabilities page documents both and a
   fresh-workspace launch proves them.
6. The diagnostics snapshot and export command, requirement 4 of the
   [diagnostics work order](../../work-orders/2026-10-08-persistent-session-diagnostics.md);
   runs from another terminal against a broken session, export reviewed.
7. Cleanup of obsolete images and cached files, the second half of the
   installed-IDE record; design agreed with the owner first.
8. C20, release notes and documentation automation, last: the notes block
   and the manifest promotion need no operator step.
9. Added by the owner on 2026-10-18: the unit gate with coverage on pull
   requests against `main` and `release-*`; done, PRs #225, #226 and #227
   merged into the release branch, the trigger proven on #226 and #227.

Gates before the final tag: the owner's eleven user-docs decisions; the
documentation describing the accepted candidate, the page on building and
selecting a local base now written with PR #232; a published base for the
candidate; the fixed bug records verified against a downloaded candidate;
the release notes under `releases/v0.3.0/notes.md`. Out of 0.3.0, named in
the overview: consent and vendor trust, installed-IDE reuse with an empty
launcher cache, browser evidence for diagnostics, the console's deliverable
6, and ecosystem bootstrap, at 0.9. The owner is consulted before each
candidate tag, before the image-cleanup implementation, when a slice proves
larger than the cycle tolerates, and before the final tag.

### Requirement: configuration validated and changed by commands only

From the owner's correction of 2026-10-04 (component-catalog's item of
2026-10-05, R-CONFIG-001 on its branch) and the owner's addition of
2026-10-05. Schema names and command spellings are chosen in the design
step with the owner; the behaviour is fixed:

- **Read-only validation before launch.** A command that checks the
  working-tree manifest and lock, plus a proposed change, for launch,
  without writing anything. `config list` shows recorded launcher state
  and is not that check.
- **Commands for every configuration change.** This project's
  configuration is written only by DevCapsule commands; `need` adds a
  capability, and removal and mandatory/optional classification need
  commands too, so no hand edits remain.
- **`project config resolve --force`.** Shows the configuration that would
  be produced if errors were skipped: a component the local launcher does
  not know is skipped; a missing IDE surface falls back to the IDE of last
  resort, bash (vim and the SDK are inside). It highlights what is skipped
  and shows the totality that would be in place. It writes no local lock.
- **`project run --force-config`.** Launches with that error-skipping
  configuration and warns the user about every skip. Distinct from
  today's `run --force`, which only accepts a stale resolution once.
- Behind both: mandatory needs are split from optional enhancements;
  optional ones warn and degrade, only a mandatory one refuses. This holds
  for adopter projects whose contributors run a launcher that does not
  know a newer declaration.

### Earlier state

Close-out PR #149 is merged at main `6980b60`. SSH fetch verified its tree
matches the delivered 0f6578d exactly and all three version copies read
0.2.16.dev0. This checkout fast-forwarded to main before this records-only
pause. No build rerun is needed: the integrated tree is the validated tree.
The owner now wants to dogfood the actual released 0.2.15 before judging
its everyday quality. Release verification and prior acceptance stand;
ongoing dogfooding feedback is pending, with no further work requested.


**0.2.15 is published and verified.** The owner merged the promotion; SSH
fetch found PR #148 and PR #146 at main 82a1b5d, with exactly the tested
preparation tree. The final tag is at accepted RC1 source
`a15ff8b58f4af93845c17eaca22f9c9d29c8e000`. Release-0.2.15 remains at 95c7bad;
retain the branch and both candidate tags. No candidate source was changed.

[Final release](https://github.com/ccozianu/devcapsule/releases/tag/v0.2.15)
is public, final and marked Latest. The
[backend](https://github.com/ccozianu/devcapsule/actions/runs/36353476393)
succeeded in 3m 13s. All three downloaded assets agree; final executable
SHA-256 is `0e66b9d9947aa447b53d0466d57de3290bb85ca07309df2d739baf82e4c5e113`.
Version 0.2.15, mnemonic v0.2.15, accepted source and help invocation passed.
Frozen inputs match RC1 and the inspected final executable. Embedded acceptance
matches main's record, captured at 82a1b5d. This is final delivery verification;
RC1's seven Docker proofs and owner-interactive acceptance remain the behavioral
acceptance. No extra GUI/provider or Docker campaign was performed.

A fresh maintenance branch `ws-maintenance/post-0.2.15` starts at fetched main
8243aef (only the coverage badge followed the promotion merge). The supported
bump command sets package and both definition headers to 0.2.16.dev0; the
installed workflow declaration is unchanged. This branch brings the latest
maintenance status/decision log back from the release's records-only exception,
updates only maintenance's registry row, and records final publication.
Reopening full build passed on clean commit 52bb2cf: 1089 source tests,
20 deselected, one existing xfail and one XPASS, mypy 174 files, nine packaged
checks and exact/local PEX builds/smokes. Log: `/tmp/0215-closeout-build.log`.
The subsequent checkpoint changes records only; source inputs are unchanged.
Project-management was notified by `2026-09-27-maintenance-0215-published.md`
at coordination a498133ed199. Mail take before pause returned no items.

No release branch was rebased or synchronized. The post-release branch is
based on current main; workflow prose is unchanged. The original checkout's
unrelated dirty source/website state is untouched. Both temporary RC test
containers are absent; private fixture storage remains. Mail take was empty.
The init bug remains fixed: machine init acceptance does not establish a
separate owner-performed init walk. Broader project-command guard repair and
other deferred work remain outside this completed release.

## Release 0.3.0

Cut 2026-10-18 from `main` at `3c91183ffd2130f6c7b40d2f9e3fd41588f977eb`,
the merge of PR #223, by the owner's decision of the same day; the commit
selected by the driver because every maintenance branch was merged and the
commit carries the decision and the work order. `release-0.3.0`: version
0.3.0 at `6965c5e`, the cut's records after it. The checkout sits on the
release branch from the cut to the final tag; the status file and the
registry row are edited and published from it. Running detail, the
checklist and the evidence: [releases/v0.3.0](../../releases/v0.3.0/README.md).

| Candidate | Source | Outcome |
|---|---|---|
| rc3 | `a22a215` | tagged 2026-10-24 after PR #257; gate `mainline`; backend run 40052369307 passed; published, downloaded and verified; carries software approvals at launch (#250, #251), the saved Docker arguments (#253, #255) and the regenerated lock; the owner tests the saved arguments and the approvals prompt on it |
| rc2 | `e5b5a8b` | tagged 2026-10-22 after PR #249; gate `mainline`; backend run 39803285881 passed; published, downloaded and verified; carries the network node (#240, #242) and C10 (#244, #246); the two C10 records closed 2026-10-23 on the owner's verification; the network node's record verifies on it |
| rc1 | `7016cdd` | tagged 2026-10-19 after PR #233; gate `mainline`; backend run 39265210147 passed; published, downloaded and verified; carries the console-link fix and the local-base guide; the owner verifies the fix on both bases |
| rc0 | `53ebc17` | tagged 2026-10-18; gate `mainline`; backend run 39175482525 passed; published, downloaded and verified; the owner's downloaded copy launched the second checkout the first time; the local Docker proofs follow the owner's session |

## Release 0.2.15

Cut 2026-09-26 from the `v0.2.14` tag (`abb785d`), not from `main`, by the
owner's ruling that 0.2.15 carries the init fix and nothing else and by lines
touched: the fix is 97/15 in two source files; `main` since the tag is 496/60
across seventeen, the rest being the base-contract naming and the images
package move, assigned to 0.2.16. `release-0.2.15`: fix cherry-picked with
origin as `9a0567c` (main `74bc4aa`, PR #143 at `3acc460`), version 0.2.15 at
`c601fb8`, release overview and the candidate gate's exception record at
`4f28a12`, gate recorded at the branch tip. Full gate passed on the branch.
Overview: [releases/v0.2.15](../../releases/v0.2.15/README.md).

Judgment where the definition is silent: *Taking A Release Over* assumes a
cut from `main`, where the working branch's records are already on `main`.
Cut from a tag, the release branch carries 0.2.14-era copies of this file and
the registry, so editing or publishing them from there would regress the live
state. This release therefore keeps the workstream records on
`ws-maintenance/post-0.2.14` and publishes from it; the release branch carries
only source, version and release documents. The row names the release branch
as the rule requires. Handed to workflow-improvements as a gap to close in
the definition.

Owner subsequently agreed to RC0 after the agent slice, with xtras and
project info in the next candidate. See the current evidence and next step
above; the original fix-only gate is historical.

## Resumed 2026-10-03: 0.2.16 Bug Triage

Resumed at owner direction for candidate C9 of project-management's 0.2.16
proposal: triage the untargeted maintenance bugs with the owner so severity
and target mean something before the cut. Synchronized with `main` at
`3038c48` by merge (`b2fc861`); one registry-row conflict resolved by
keeping `main`'s project-management row and this workstream's own row.
Three `.idea/` files that `main` tracks were set aside in the session
scratchpad, not committed; the owner ruled on 2026-10-01 that `.idea/` is
ignored in this repository and 0.2.16 documents the rule.

Decided so far:

- 2026-09-26 init discards answers: closed 2026-10-04 on the owner's
  heuristic confirmation against released 0.2.15, with the RC0 and RC1
  downloaded-candidate proofs; 0.2.15's one blocking record is done.
- 2026-08-03 JetBrains Runtime alpha compositing: retired 2026-10-04, an
  observation with no defect in two months, on a display connection the
  contained desktop has since replaced.
- 2026-08-03 PyCharm native launcher: confirmed, target 0.9, with the
  triage findings in the record (no recorded reason for the script; one
  environment variable couples the runtime to it; the binary honours the
  same); a minimal change plus the IDE smoke test as the end-to-end proof.
- 2026-08-15 detached successors: fixed 2026-10-04, target 0.2.16. The
  detached lifecycle had no reason to exist; `launch-successor` is now the
  ordinary attached launch with a cidfile, and the lifecycle enum is gone.
  Unit suite (1093 passed), typecheck and the gate's test session are green.
  The new recursive end-to-end test is blocked in this capsule by a stale
  capsule-local resolution that the in-capsule guard will not let anyone
  refresh; that is the next item's territory.
- 2026-10-04 recursive successor cannot refresh its capsule-local
  resolution: decided 2026-10-05, option D, by the owner's design. The test
  stops sharing the capsule's record: clean clone of the current branch
  into a fresh host-backed workspace, dirty source refused, resolution under
  isolated XDG roots, launch from the clone, best-effort cleanup. Options A,
  B and C set aside. Same ruling, as a general rule now in the e2e test
  doc: every end-to-end test runs on a fresh workspace, never the live
  checkout. Implementation is on the 0.3.0 plate, not started.
- 2026-09-24 installed IDE not reused by Docker: decided 2026-10-05, in
  the next release, 0.3.0, both halves (reuse across formations and
  reaping), design review with the owner before code, named build contexts
  first.
- Component-catalog's intake item on the host-network run-once launch:
  acknowledged 2026-10-05 as a bug by the owner's ruling, filed as
  `2026-10-05-run-once-network-authorization-needs-a-recommendation.md`,
  minor, target 0.3.0: `network` becomes a universal authorization node
  like docker-daemon, development-sudo and host-browser. The local
  workflow text stands.
- 2026-07-16 multi-line exec rendering: minor, target 0.9, the series the
  owner expects to host V1's betas and candidates; no attention unless it
  recurs in a release campaign.
- 2026-08-03 ecosystem-aware project bootstrap: stays a bug, minor, target
  0.3, by the owner's ruling of 2026-10-05. The feature reclassification
  was rejected: onboarding a developer in minutes is an implicit promise,
  and the 2026-10-03 incident (an agent pair unable to bring `nox` into
  scope) shows how it fails. Sequenced after the larger 0.2.16 items.

The triage is complete as of 2026-10-05. The project group guard
(2026-09-26) and in-capsule configuration inspection (2026-09-24) are owner
maintenance, target 0.3.0, by the owner's decisions of 2026-10-01, restated
on 2026-10-05 without objection; they are the in-capsule project-command
fix on the plate.

Owner's version decision of 2026-10-05, recorded here until project-management
registers it and the version scheme in `WORKFLOW-LOCAL.md` is amended: the
next release, planned as 0.2.16, is **0.3.0**, a marketing decision marking
the jump forward from 0.2.15. `main` stays at 0.2.16.dev0 until the release
branch's first commit sets the version, as the local scheme says. The
maintenance-owned records that targeted 0.2.16 now target 0.3.0; the two
other-owned ones (workflow-improvements' discoverability record,
component-catalog's IntelliJ lock record) are their owners' to retarget and
are named in the mail to project-management. Beyond 0.3.x the project
jumps to 0.9, which hosts V1's betas and release candidates; bug targets
may name 0.9 on that basis.

### Resumed 2026-10-04

Synchronized with `main` at `17532fd` by merge; the five definition changes
since the last read (two files for humans, information model, validation
commands required and printed by the brief, validation vocabulary and its
checkpoint trigger, integration is a merge commit) are read and apply from
now: this branch merges `main` in, never rebases, and its deliverables
land as merge commits. The other checkout has claimed `component-catalog`
for IntelliJ; this one takes the maintenance plate.

### Paused 2026-10-04, second session, mid-triage

Main merged in at `5e9cd94` (`581ffe2`); PR #164 had already integrated
this branch's tip, so the merge brought only component-catalog's IntelliJ
and Playwright work. Component-catalog's mail on the host-network run-once
launch was taken into intake and committed. No source was changed.

### Paused 2026-10-03, mid-triage (historical)

- Last task: the 0.2.16 bug triage with the owner; one record decided
  (multi-line exec rendering, minor, 0.9). Nothing uncommitted.
- Next resumable task: continue the triage from the ecosystem-bootstrap
  record (2026-08-03). The owner's test for the remaining records: a
  record that violates no requirement and breaks no promised behavior is
  a feature, not a bug; it leaves the bug queue for the V1 scope ledger by
  mail to project-management. Ecosystem bootstrap fails that test and is
  the first to move; the information model being written in
  workflow-improvements is what makes the test a rule.
- Owner intent for the release name, recorded for project-management's
  registration: if 0.2.16 delivers its full planned scope, new IDE
  surfaces included, it is released as **0.3.0**, marking how far the
  product is beyond the first 0.2. The release branch's first commit sets
  the version under the local scheme; the owner names it then.

## Planned Next Step

Current: 0.3.0 delivery is complete. Maintenance is ready for 0.3.1
planning from the queue above; the
release-independent fixture bug is the proposed first implementation slice.
No repeat 0.3.0 product testing is needed without new evidence of a problem.
Historical candidate sequencing below must not override this direction.

1. The network-node slice, on `ws-maintenance/0.3.0-network-node` from
   the release branch, a pull request into it with the reviewer loop;
   then C10 with its two records filed first; rc2 carries both. Then rc3:
   forced configuration and the diagnostics snapshot; rc4: image cleanup
   after the owner's design review, and C20. C17's local half, this
   project's operating instructions in `WORKFLOW-LOCAL.md`, is a slice
   of the cycle too, placed by the owner. The base is published in the
   promotion of the accepted candidate and pinned there. Before the
   final tag: the five fixed records verified on a downloaded candidate,
   two of them from inside a capsule, three with Docker; the eleven
   user-docs decisions; C17's generic half; `notes.md`.
   The lock command on the host is dogfooding at the owner's convenience;
   until it runs, no capsule has exercised the rc1 agent pins.
2. Done: the release branch is merged into `main` by PR #228; ancestry
   holds. The owner may turn `delete_branch_on_merge` off.
3. On the owner's word, tag `v0.3.0-rc0` on the release branch's tip, wait
   for the backend, download and verify the three assets, run the local
   proofs against the download, and record rc0 in the overview.
4. Then the slices in the recommended order: the network node, C10 with its
   two records filed first, forced configuration, the diagnostics snapshot,
   image cleanup after the owner's design review, C20 last.

Superseded 2026-10-18 by the cut (PR #207 and PR #209 are merged; the
recipe-12 base is history since rotation moved into the writers):

1. The owner reviews and merges PR #207, then PR #209. The three review
   rounds on PR2 are used; a further change needs the owner's word.
3. Acceptance: build a recipe-12 base and run a fresh-workspace launch,
   proving the files, the rotation and the budget on a real capsule.
4. Slice 3: the live snapshot and export command; then browser evidence.
5. Then the universal network node and the installed-IDE reuse and reaping
   design review. Configuration snapshot links stay an acknowledged
   follow-up.

Done 2026-10-11: PR1.1 (#208) merged into PR1's branch.

Done 2026-10-11: PR #172 merged by the owner; the plate position was decided
by the owner's "start working on #1".

Superseded on 2026-10-11: await owner review of PR #174; after approval the
owner merges the fix into #172, then the branch synchronizes and #172
integrates. PR #174 is merged and the branch is synchronized.

Historical planned steps (superseded by the current review):

Wait for the owner's real-use feedback on released 0.2.15. Triage any reported
problem against the published executable and route it by ownership; do not
start new implementation or infer 0.2.16 scope. Release publication and main's
0.2.16.dev0 reopening are complete. No further PR or release action is required
for this slice. This records-only pause is published through coordination and
will reach main with the next substantive maintenance integration.

Previous next step, superseded: the base-contract slice is on this branch for the owner's PR. Next after the
merge: the named-build-context fix for the 4.8 GB rebuild transfer if the
owner approves it, and the 0.2.15 sequencing from project-management.

Post-release, on `ws-maintenance/post-0.2.14`: deliver the registry rows,
the version reopening and the close-out records to `main` by PR; then the
cleanup slices the owner approves from the 0.2.15 plan: the named
build-context fix for the 4.8 GB rebuild transfer, the `v0.2.12` mnemonic
(option A recommended), and repository hygiene. 0.2.15 registration and
scope are with project-management.

0.2.14 is published and verified. Remaining for this release: the owner
pastes the notes block from the release overview into the GitHub release
body; the release overview and this status are delivered to `main` through
the ordinary PR; then the branch-name migration deferred through
publication is coordinated by project-management before substantive
next-release work, and `main` reopens with the next development version
per WORKFLOW-LOCAL.md.

The owner said "release 0.2.14" on 2026-09-25. The acceptance record
`engineering-docs/releases/v0.2.14.json` is generated from the verified rc4
download (integration by ancestry, baseline `2137108`); the final gate reads
the record from `main`, so it passes only after the merge. Next: the
owner merges the release branch to `main`; then tag `v0.2.14` on
`abb785d` (`v0.2.14-rc4^{commit}`), push, verify the published final assets
and run the local proofs against them; the owner pastes the notes text
from the release overview into the GitHub release. Then the branch-name
migration deferred through publication becomes due before next-release
work.

All 0.2.14 release-table rows are decided and rc4 is accepted on both host
checkouts. Next: on the owner's word, verify ancestry of the release branch
head on `main`, tag the final `v0.2.14` on the accepted candidate's commit
`abb785d` as the operator guide prescribes, verify the published final
assets and run the local proofs against them; carry the R-COMPAT-001
exception into the release notes.

RC4 accepted 2026-09-24: the owner tested it on `devcapsule-2` and
`devcapsule` and closed the manifest rejection, the runner-gated release,
the listing trailer and the acquisition-decision records. Open and owned
here: the `/opt` discovery fallback (minor, set aside), the installed-IDE
reuse design review, and the thirteen undecided rows in the release bug
table. Next: the owner decides the remaining rows and any further
candidate; then the final `v0.2.14` tag from the accepted candidate's
commit with the release notes carrying the R-COMPAT-001 exception.

RC2's backend run (36023910604) failed at "Verify pinned base availability
and runtime sessions": `docker build` of the disposable runtime image exited
1 after 42 seconds on the hosted runner, where the rc1 run had passed the
same step in 74 seconds with identical test code; the e2e helper discarded
the build's stderr, and the step log needs administrator rights. The local
reproduction against the same digest and PEX source passed. The owner ruled
that no test on hosted infrastructure runs Docker. Filed as a blocking bug
([record](../../bugs/devcapsule/2026-09-24-release-workflow-gated-on-docker-on-hosted-runner.md))
and fixed on this branch: the release workflow runs no Docker (both
clean-machine proofs, component-cache and runtime-session steps removed);
those proofs are local acceptance steps against the downloaded assets; the
e2e helpers now fail with the command's output; the operator guide,
DEVELOPING.md and the source README describe the new split.

Done since: PR #138 merged, `v0.2.14-rc3` tagged and published, assets and
all local proofs verified (see validation below). Next: the owner tests `config list`/`resolve` on this
repository with 0.2.12 and RC3 and the `devcapsule0` exception in a real
capsule. RC2's tag stays, without assets. The RC1 configuration-inspection
bug remains open for the owner's fix-or-defer call.

Owner-directed release steering resumed 2026-09-24 from this checkout. The
owner reported `project config list` and `config resolve` failing on a fresh
DevCapsule checkout with `runtime-effect must be one of: docker.memory-limit`.
Root cause, reproduced with the published executables: commit `658749f`
declared `runtime-effect = "devcapsule.command-name"` in this repository's
own manifest while adding it to the vocabulary; v0.2.12 and rc0 reject any
effect they do not know, so every released client failed on `main` and
`release-0.2.14`; rc1 accepts it. Filed as a blocking bug
([record](../../bugs/devcapsule/2026-09-24-released-launchers-reject-repository-manifest.md)),
then fixed on this branch: the value name `runtime.devcapsule-command` is
reserved and carries the effect without the attribute, unknown effects are
reported with the running version, the manifest drops the attribute, and a
guard test pins the repository manifest to the released vocabulary. Published
0.2.12 now lists and resolves the manifest. Full gate passed.

Next: the owner opens the PR from `release-0.2.14` to `main`. After the
merge, verify the candidate gate by ancestry, tag `v0.2.14-rc2` atomically
with the branch, download and verify the assets, and validate that RC2 applies
`devcapsule0` from the reserved name inside a real capsule. Then decide the
RC1 configuration-inspection bug with the owner: fix both causes on this
branch under maintenance, or defer. The receiving workstream is paused.

RC1 owner feedback: mostly works, except configuration inspection. Both
reported failures are confirmed; the [bug](../../bugs/devcapsule/2026-09-24-runtime-configuration-inspection-fails.md)
belongs to component-upgrades' runtime inspection contract, target 0.2.14.
Evidence delivered to component-upgrades by coordination mail
`2026-09-24-maintenance-rc1-runtime-configuration.md` at `dc91dbc8e484`.
Next: agree the release repair with the owner and receiving workstream.
No source fix or workstream switch was performed. Initial coordination claims
hit SSH authentication errors and a Git push hit a remote internal-server
error; mail delivery subsequently succeeded.


The runtime CLI blocker has a source fix and Docker regression evidence on
`release-0.2.14`. Normal capsules expose the shipped `devcapsule`; the owner
requested a saved configuration exception and this repository recommends
`runtime.devcapsule-command = "devcapsule0"`. That real command leaves the normal
name for development tooling; internal absolute-path calls retain the shipped
PEX. Explicit checkout values/omissions override ordinary recommendations.
Owner accepted the real recursive PyCharm/devcapsule0 session at `9cc0868`.
PR #136 integrated the release fixes; RC1 is tagged at `cec7a0c`.
Published RC1 assets are downloaded and checksum/version/source-verified.
The owner-requested local base is built and smoke-checked. Next: carry the
local PyCharm acceptance into exact-RC1 validation before closing the blocker.

The owner requested the installed-IDE reuse bug be filed first and its design
reviewed together before implementation. No release target or implementation
approach is approved. Review the linked bug when the owner resumes that topic;
do not start cache implementation or the broader composition redesign.
No live capsule or website source was patched. URL opening and non-blocking
workflow onboarding remain with their previously notified owners.

A single entry point now supports existing-project sessions:
`smoke/runner.py launch --project PATH`, followed by `resume`, `report` and
explicit actor `note` records. It verifies exact RC0 and captures process and
container facts without promoting them into a graphical PASS. The original website observation lacked candidate details; the subsequent
runner sessions establish exact RC0 startup and file/IDE resume evidence.
Owner confirmed the website VSCodium session works. Runner attempts 2 and 3
finished with exit 0, container absent and no monitor errors; owner confirmed
the S10 file/IDE resume checklist. `launch` and `resume` now accept a per-session
`--network host|bridge` override using the product authorization grammar. Next:
continue remaining campaign checks using `--network host` per local policy;
agent continuation is still untested. Owner verified host-network attempt 4.

The owner requested an engineering test specification before further campaign
work: enumerate stories, distinguish validation prerequisites from reused data,
state feature promises/preconditions/postconditions, and assign each action to
an agent or program. The [21-story specification](../../releases/v0.2.14/smoke/stories.md)
now does that. Fixed prompt answers are automated both through an actual terminal
and through unattended flags. S02/S03 and S17 (exact preservation of unrelated
coordination blobs) pass against downloaded RC0, with durable JSON evidence.
Fresh and all three public sample configurations complete unattended. Whole
GUI/upgrade/service stories are not yet implemented or passed; continue the
runner implementation from the story table, and establish desktop-control
tooling for the assigned graphical steps. Do not transfer unfinished automation
to the human. Personal provider login/MFA and release judgment remain owner acts.
The retirement is integrated;
publish RC1 when the owner is ready to test that change. RC0 still contains
the old command; do not move its tag. No base rebuild is needed: the existing
local Ubuntu recipe-9 image and published RC0 executable were rechecked on
2026-09-23, and base build inputs are unchanged. Release refs are not rebased;
main has no workflow-definition or devcapsule-src difference from this branch.

The owner requested and received a permanent
[V1-blocking legacy capability work item](../../work-orders/2026-09-22-legacy-launch-capability-disposition.md).
It preserves the full inventory, existing project-run equivalents and the
undecided image-oriented/non-DevCapsule-directory alternative. Project-management
is to register the owner's V1 gate and sequence future-release decisions and
implementation; this is not a new 0.2.14 implementation commitment.
Delivered the complete work item by coordination mail
`2026-09-22-maintenance-v1-legacy-launch-capabilities.md` at `5df12452fba6`;
project-management's acknowledgement/ledger update remains pending. Links,
all 13 inventory rows and the permanent documentation index were checked.

The two owner-approved configuration closures are applied. The networking bug
was marked retired before removal as requested, and its command is now removed.
Thirteen rows remain undecided in the [release bug table](../../releases/v0.2.14/bugs.md),
including eight targeted verifications and five deferrals. Other records still
have independent scope: shared image rendering, modern PyCharm behavior,
project display policy, and resource lifecycle do not disappear with the CLI.

Owner deferred the confirmed multiline execution-rendering bug for 0.2.14
unless it recurs during the release E2E campaign. Watch for that recurrence
during acceptance and reconsider the deferral if observed. After this release,
the accepted follow-up is a clean redesign of component image composition
around documented, unit-testable contracts; the bug and release table record
the scope. The release branch remains unsynchronized as required for release refs;
the command removal, unlike the earlier records-only decisions, needs a new candidate.

Use downloaded RC0 for the release overview's end-user acceptance journeys:
fresh project, predecessor upgrade/recovery, IDE/agent work and resume,
graphical/login behavior, diagnostic command and isolated coordination scenario.
Pick further bugs from the table, fix, verify obsolete, or explicitly defer.
Capture the actual platform/surface/agent and user-visible outcome. Neither
unit coverage nor executable portability alone completes release acceptance.
New source fixes require the next immutable candidate and a main disposition.
Only after owner acceptance of an exact candidate prepare the final JSON/tag.

## Validation And External State

Gate on `ws-maintenance/0.3.0-vscode` after merging review PR #302
(`241e7b10`, 2026-10-28, PR #301): `nox -s build` passed end to end: version
copies agree at `0.3.0`; syntax; mypy clean over 261 files; `2544 passed,
38 deselected, 1 xfailed, 1 xpassed`; CLI smoke; local and clean PEX built
and smoked; packaging integration 17; the documentation contract 190 pages
including 17 aliases; web console mypy clean over 9 files and 357 passed.
Logs `/opt/devcapsule-gate/2026-10-28-vscode-merged-build.log` and
`-docs-contract.log`. The recorded IDE smoke of `vscode` and `codium` from
the temporary clone is under `evidence/2026-10-28-vscode/`.

Gate on `ws-maintenance/e2e_videos-2` after merging review PR #241 (`e17065e`,
2026-10-22, PR #236): `nox -s build` passed end to end: version copies agree at
`0.3.1.dev0`; syntax; `mypy` clean over 216 source files; `1649 passed, 35
deselected, 1 xfailed, 1 xpassed` in the unit suite (`96 passed` across the four
touched test modules, `50` added in PR #241 with a 17-point mutation check); CLI
smoke; local PEX built and smoked (`dist/devcapsule-local.pex`); packaging
integration `17 passed`; documentation contract `187 pages including 17 aliases`
(`devel (0.3.1.dev0)` rendered); web console `mypy` clean over 8 source files
and `293 passed`. Log `/opt/devcapsule-gate/2026-10-22-pr236-merged-build.log`.
The review worktree `/home/devcapsule/worktrees/maintenance-review` and its
branch `ws-maintenance/4PR-e2e_videos-2-review` were removed after merging PR
#241.

Gate on `ws-maintenance/0.3.0-launchable-lock-test` (2026-10-18, PR #230):
`nox -s build` passed end to end: version copies agree; syntax; mypy clean
over 214 files; 1584 unit tests passed, 35 deselected, 1 xfailed, 1
xpassed; CLI smoke; test PEX built and smoked; packaging integration 17
passed; documentation contract 186 pages; web console mypy clean, 293
tests. Hosted run on the pull request: `Python 3.12` passed. Log
`/opt/devcapsule-gate/2026-10-18-locktest-build-2.log`.

Slice gate (2026-10-18, `ws-maintenance/0.3.0-agent-freshness` at
`de9537a`): `nox -s build` passes the distribution version, the syntax
checks and mypy over 214 files and stops at the unit tests: 1583 passed,
1 failed, the dogfood-reconstitution test that needs the owner's lock
step. The suite with that test deselected: 1582 passed; one host-open
broker test failed in that run only and passed alone and in the gate's
run. The local PEX of the slice, `devcapsule-src/dist/devcapsule-local.pex`,
reports 0.3.0 and is the owner's writer for the lock. Logs
`/opt/devcapsule-gate/2026-10-18-agent-freshness-*`. Smoke output under
the session scratchpad, summarized in the overview; the two containers
were removed on exit.

Gate at the cut (2026-10-18, `release-0.3.0` at the version commit
`6965c5e` with the records in the working tree): `nox -s build` passed
every step to the documentation contract: the distribution version agrees
in its three copies; mypy clean over 214 files; 1584 unit tests passed, 35
deselected, 1 xfailed, 1 xpassed; the CLI smoke; the test PEX built and
smoked; packaging integration 17 passed. The documentation contract failed
once on the `devel` entry and passed after the manifest line described
under *Current State*: 186 pages, 17 aliases, devel rendered at 0.3.0,
the three released versions reused. The web console session, which the
gate queues after the contract, ran on its own afterwards and passed:
mypy clean over 8 files, 293 tests. Logs `/opt/devcapsule-gate/2026-10-18-release-0.3.0-build-1.log`
and `-webconsole-1.log`.

Gate after round three (2026-10-11, PR #209 at `c3dd82a`): full `nox -s
build` passed, exit 0: mypy clean over 214 files; 1584 unit tests passed,
35 deselected, 1 xfailed, 1 xpassed; packaging integration 17 passed; PEX
built and smoked; documentation contract 184 pages; web console session
mypy clean, 293 tests. Log
`/opt/devcapsule-gate/2026-10-11-log-rotation-build-4.log`.

Second session (2026-10-11, PEX of `b86b899`, the recommended recipe-9
base, budget 16 MiB): the directory held every component's file present
on that base, the launcher's and the supervisor's, user-owned, and
`session.json` with the 1 MiB segment and the end record; exit 133 as
before. Evidence under `evidence/2026-10-11-session-logs/second-session/`.
The fixture project `e2e-logs-2b5c80eb` was removed after the run.

In-process rotation gate (2026-10-11, PR #209 after the owner's
clarification): full `nox -s build` passed, exit 0: mypy clean over 214
files; 1571 unit tests passed, 35 deselected, 1 xfailed, 1 xpassed;
packaging integration 17 passed; PEX built and smoked; documentation
contract 184 pages; web console session mypy clean, 293 tests. Log
`/opt/devcapsule-gate/2026-10-11-log-rotation-build-3.log`. Rotation is
proven in the unit suite with a real child writing 4000 lines through the
tee at a 100 KB segment, and the handler at a 160-byte segment.

Acceptance (2026-10-11): base `devcapsule-base-e2e:v0.2.16.dev0-local-linux-x86_64-36bef9f1e151`,
id `sha256:5034721d…`, built over host networking from the public PEX of
`174480f` (sha256 `6047ecf0…`) in the fresh workspace
`~/.local/share/devcapsule/e2e-workspaces/logs-accept`; e2e session 9
passed: built base, component cache (5), successor lifecycle, runtime
image, self-contained PEX. Proof session `20261011-085622-321e` on the
materialized codium image, exit 133 (codium's SIGTRAP on stop, as before).
The clone, its venv, the base and the codium image remain on this machine;
the fixture project `e2e-logs-1974aad7` was removed after the run.

Slice 2 gate after the review (2026-10-11, PR #209 at `adfbff7`): full
`nox -s build` passed, exit 0: mypy clean over 214 files; 1571 unit tests
passed, 35 deselected, 1 xfailed, 1 xpassed; packaging integration 17
passed; PEX built and smoked; documentation contract 184 pages; web
console session mypy clean, 293 tests. Log
`/opt/devcapsule-gate/2026-10-11-log-rotation-build-2.log`. The rotation
loop is proven under a real `sh` with a fake logrotate.

Slice 2 gate (2026-10-11, PR #209 at `4820289`): full `nox -s build`
passed, exit 0: mypy clean over 214 files; 1548 unit tests passed, 35
deselected, 1 xfailed, 1 xpassed; packaging integration 17 passed; PEX
built and smoked; documentation contract 184 pages; web console session
mypy clean, 293 tests. Log
`/opt/devcapsule-gate/2026-10-11-log-rotation-build.log`. logrotate is
absent on this capsule's recipe-11 base, so the real binary did not run;
the rotation thread, the stanza, the reopen after a rename and the reaping
race are proven with stand-ins. PR1's merged branch passed the focused
suites and mypy in the review worktree. The second review worktree is
`/home/devcapsule/worktrees/maintenance-review-pr2`.

Slice 1 gate (2026-10-11, PR #207 at `0af89a2`): full `nox -s build`
passed, exit 0, scratch on the overlay: mypy clean over 214 files; 1523
unit tests passed, 35 deselected, 2 xfailed; packaging integration 17
passed; PEX built and smoked; documentation contract 184 pages; web
console session mypy clean, 292 tests. Log
`/opt/devcapsule-gate/2026-10-11-session-logs-build.log`. The supervisor
tee is proven with real child processes in the unit suite; no capsule was
launched. The Codex pair's review worktree is
`/home/devcapsule/worktrees/maintenance-review` with its own venv.

Gate on the merged tree (2026-10-11, commit `e7e441f` plus records): full
`nox -s build` passed with exit 0, scratch on the overlay. Type check clean
over 211 source files; 1498 unit tests passed, 35 deselected, one xfail,
one xpass; packaging integration 17 passed; PEX built and smoked; the
documentation contract rendered 184 pages; the web console session passed
with mypy clean over 8 files and 290 tests. Log
`/opt/devcapsule-gate/2026-10-11-merged-main-build.log`. No Docker or IDE
acceptance was run; nothing in the merge needs one.

2026-09-27 resumption: SSH refs, waiting mail and the current main disposition
were rechecked; no candidate tag exists. Record-only acknowledgement changes
and the release-scope overview pass whitespace checks. The vendor metadata
reads are availability evidence only, not installation or model-access tests. The clean checkout has no developer virtualenv, as
already established during the project-management handoff; no new build pass
is claimed. Set up its developer environment before implementation validation.
No containers or vendor sessions were launched for workstream selection.


Base contract slice (2026-09-26, owner-directed, from the design note): new
`base_contract` module (`BaseContract`, `Provenance`, `BaseImage`), the
recipe declares and labels its contract, matrix pins carry recipe versions
5, 6, 9 and write `contract` into locks, matrix advanced to `embedded-21`,
consent bound to the image, the prompt and `config show` name the base by
contract with provenance and a recipe permalink, and `show` adds a
compatibility report from the matrix's verified edges. The configuration
core reads the contract from the lock and keeps its no-adapter rule. This
repository's lock regenerated to exactly the three expected lines. Golden
locks updated. Tests: 8 new contract tests; 3 tests rewritten from the
lock-digest rule to the image rule; full `nox -s build` passed with 1073
tests, mypy over 166 files, PEX smokes and nine packaged integrations (exit
read directly; log `/opt/devcapsule-gate/base-contract-build.log`). Prompt
and Base block rendered on a scratch copy and read by eye.

Layout (2026-09-26, owner request): the root package was crowded, so the
recipe, the contract, the build plans, the image metadata and the toolchain
pins moved into `devcapsule/images/` as `base`, `contract`, `build`,
`metadata` and `tooling`; 18 files had their imports rewritten, including
the monkeypatch targets in tests. The recipe's path is now provenance: new
images carry `devcapsule.base.recipe-source`, and permalinks for images
built before the move keep the old file. Full `nox -s build` passed again:
1073 tests, mypy over 167 files, PEX smokes and nine packaged integrations
(exit read directly; log `/opt/devcapsule-gate/images-layout-build.log`).

Host Docker cleanup (2026-09-25, owner: "run freely"): 98 DevCapsule-related
images at 288.9 GB total store. Removed the exited recursive-run containers,
then 88 tagged images, keeping the two running capsules' images, the newest
two formations per surface, the published pinned base under both tags, the
two other matrix-pinned bases and the rc2 local twin; ten remain. Store now
80.4 GB. The BuildKit cache held 645.9 GB in 2561 entries; entries unused
for more than seven days were pruned (377.2 GB reclaimed), keeping the
stages behind this week's builds so component stages stay `CACHED`. 268.7 GB
of cache from the last week remains; 21 unused local volumes (15 GB) were
not touched, their owners being unknown.

Post-release close-out (2026-09-25, owner-directed): branch names migrated
to `ws-<name>/<sub>` by creating the new refs at the old tips and pushing
them: `ws-project-management/coordination` (was `project-management/coordination`,
c5a011d), `ws-sample-projects/fastapi-webapp` (was `sample-projects/fastapi-webapp`,
6a9776c), `ws-contained-display/display-transport` (was
`contained-display/display-transport`, fa89c53),
`ws-component-catalog/antigravity-cli` (was `component-catalog/antigravity-cli`,
85a94d6); `ws-website/initial-cut` already existed and contains
`website/initial-cut` (0658207). Maintenance left the release ref for
`ws-maintenance/post-0.2.14`, cut from the release head so the two post-tag
record commits travel with it. `nox -s bump -- 0.2.15.dev0` reopened `main`'s
development version in `pyproject.toml`, `WORKFLOW.md` and the packaged
definition; `.devcapsule/devcapsule.toml`'s `[workflow] version` still reads
`0.2.14.dev0`, as it did before the release, and the bump does not touch it.
The registry rows are updated here under the owner's instruction; each
workstream's own status names its old branch until it next publishes. For a
checkout on an old name: `git branch -m OLD NEW && git branch -u origin/NEW`.
Old-name refs were deleted once their `ws-` successors contained them.
With the owner's confirmation the retired outbox delivery branches and the
superseded triage branch were deleted too, each with one never-merged record
commit, noted here for recovery: `component-catalog/outbox` 986136f,
`component-catalog/outbox-recovered-2026-09-06` 802adaf,
`sample-projects/outbox` e62d910, `ws-project-management/outbox` 09ac366,
`ws-website/outbox` 9383efe, `ws-maintenance/triage` f565689; also the
merged `contained-display/outbox`, `project-management/outbox`,
`project-management/outbox-pending-2026-08-19`, `ws-maintenance/outbox` and
`ws-workflow-improvements/nested-cwd-fix`. Remaining non-`ws-` refs are the
project's own and were not touched. The 0.2.15 plan went to project-management as
`2026-09-25-maintenance-0215-plan.md` at `354d4c7c2aff`.

Final tag (2026-09-25): PR #141 merged the release branch, fetched main
`bb3b0aa` carries `engineering-docs/releases/v0.2.14.json`. In a scratch
worktree at `abb785d`, `scripts/release-protocol.py v0.2.14` passed:
version `0.2.14`, prerelease false, candidate `v0.2.14-rc4`, integration
by ancestry, main revision `bb3b0aa`; record at
`/opt/devcapsule-gate/final-release-protocol.json`. Annotated `v0.2.14`
tagged on `abb785d`, the accepted candidate's commit, and pushed. A
detached chain waits for the final assets, verifies them, and runs the
local proofs with the release version exported. Results: `v0.2.14` public
at 01:55 UTC as a final release and GitHub Latest; checksum verified, the
executable reports `0.2.14` at `abb785d`, SHA-256
`98ff656499208bf2d4bb43adfeeafb34676b91d48adcb8ac6e8ee4e5e5d2c7bf`; the
manifest names main revision `bb3b0aa` for the acceptance record. Local
proofs: packaging integration 9 passed, clean-machine passed, component
cache 5 passed, runtime image on the pinned base passed
(`/opt/devcapsule-gate/final-proofs.log`).

Release table settled (2026-09-25): the owner deferred five rows as minor,
closed the base-image consent, CODEX_HOME, tooling PATH, embedded-browser
preview, X11 credential, formation-lifecycle and Codex installation rows,
and sent the `/opt` discovery fallback to V1 and component-layer reuse
outside the cycle. The last row, nested-directory coordination loss, closed
after the regression test was strengthened to assert blob identity per
command: coordination module 18 passed, mypy clean, full `nox -s build`
passed with 1065 tests, mypy, PEX smokes and nine packaged integrations
(exit code read directly; log `/opt/devcapsule-gate/coord-test-build.log`).

RC4 tag (2026-09-24): the owner merged PR #140; fetched main `d11848f`
contains `abb785d`, zero unintegrated commits. `scripts/release-protocol.py
v0.2.14-rc4` passed, record at `/opt/devcapsule-gate/rc4-release-protocol.json`;
annotated tag pushed atomically with the branch, peeled commit
`abb785d7ad4069606fd3ab84009ca8efeabc22b9`. A detached chain waits for the
assets, verifies them, and runs the local proofs with the release version
exported. Results, 2026-09-24: assets published under the Docker-free
workflow; checksum verified, executable reports `0.2.14rc4` at `abb785d`,
manifest records mainline integration with no unintegrated commits; PEX
SHA-256 `d5387d8a05a278bb0b8b109e9da0ea39c29d5a753e50013d9f09dc9e2a48d16a`,
files in `/opt/devcapsule-gate/0.2.14-rc4-published/`. Local proofs against
the download with `DEVCAPSULE_EXPECTED_RELEASE_VERSION=0.2.14rc4`: packaging
integration 9 passed; clean-machine passed; component-cache 5 passed;
runtime image on the pinned v0.2.12-rc5 digest 1 passed. Log
`/opt/devcapsule-gate/rc4-proofs.log`.

Provenance in the listing (2026-09-24, owner request before tagging RC4):
every configuration row carries a SOURCE column naming the document its
status and value come from (checkout, manifest, lock, resolution, managed,
environment, with a qualifier where it helps), placed before the value
column so it survives narrow terminals; `config show` adds a `Sources:`
block expanding those tokens to the manifest, lock, checkout input and
generated resolution paths, each marked as resolved or changed since the
resolution from the same freshness facts the resolution row uses, plus the
absent workstation configuration. Contract tests cover the column and the
block; the recovery, project-command and contract modules pass (167).
Rendered on a scratch copy of this repository for readability. Correction:
commit `e534d7b` was pushed with this entry claiming a passing gate, but
that gate run had failed one test, `test_config_list_shows_the_recorded_answer_and_names_a_denial`,
which parsed listing columns by position and met the new SOURCE column;
the agent read the background wrapper's exit code instead of the log. The
test now reads the status by position and the value as the last token and
checks the source. Full `nox -s build` then passed with its own exit code
read directly: 1065 tests, 20 deselected, one xfail, one quarantined XPASS,
mypy, PEX smokes and nine packaged integrations; log
`/opt/devcapsule-gate/sources-build-2.log`.

`config list`/`config show` split (2026-09-24): implemented on the release
branch at the owner's direction after the rc3 findings. `list` prints the
checkout identity and the table only; `show` adds the review, rendered from
the generated resolution's real state; newly required acquisition decisions
say they are new in 0.2.14. Contract tests 55 passed, including the new
list/show test across fresh, stale and decisions-required states; the
upgrade-recovery, project-command, release-compatibility, version-set and
configuration modules passed (423) with the recovery test reading remedies
from `show`; mypy clean on the touched modules. Full `nox -s build` passed:
1065 tests, 20 deselected, one xfail, one quarantined XPASS, mypy, PEX smokes
and nine packaged integrations; log `/opt/devcapsule-gate/list-show-build.log`.

RC3 local proofs (2026-09-24), against the verified download
`/opt/devcapsule-gate/rc3-published/devcapsule.pex` (SHA-256
`9a82ae7f91662f448ad180854e2cd43b14b6deca54c598d30440dd4a87ae4d43`), with
`DEVCAPSULE_PEX_UNDER_TEST`, `DEVCAPSULE_EXPECTED_BUILD_MNEMONIC=v0.2.14-rc3`
and `DEVCAPSULE_EXPECTED_RELEASE_VERSION=0.2.14rc3` exported, pytest scratch
on the overlay: packaging integration tests 9 passed; clean-machine proof
(`nox -s pex_clean_machine`, `docker run` without Python or network) passed;
component-cache reuse and launcher delivery 5 passed in 91 s; runtime image
on the manifest's single pinned base, the v0.2.12-rc5 digest, 1 passed in
28 s on a warm builder cache. Log `/opt/devcapsule-gate/rc3-local-proofs.log`;
its first packaging and clean-machine attempts failed only because the
release-version variable was not exported, and passed on rerun with it.
RC2 assets verified the same way: SHA-256
`eddf2cde00e07c8d7874c229283ff1a20f409400b5b7bbdcc9b5cc54dca8d3b1`,
version `0.2.14rc2`, source `a779295`, mainline integration.

RC3 tag (2026-09-24): the owner merged PR #138 (fetched main `7c0b5a2`
contains `997cd67`, zero unintegrated commits) and reported that a rerun of
rc2's failed run succeeded, which confirms the runner failure as flakiness.
`scripts/release-protocol.py v0.2.14-rc3` passed, record at
`/opt/devcapsule-gate/rc3-release-protocol.json`; annotated tag pushed
atomically with the branch, peeled commit `997cd67445b00c78da38f1a77c7f0622eaf5a0b3`.
A watcher downloads and verifies the rc2 and rc3 assets; the three local
Docker proofs against the rc3 download follow.

Docker-free release workflow (2026-09-24): workflow YAML parses; the two
edited e2e modules collect (six e2e tests, deselected as before) and pass
mypy; full `nox -s build` passed: 1064 tests, 20 deselected, one xfail, one
quarantined XPASS, mypy, PEX smokes and nine packaged integrations; log
`/opt/devcapsule-gate/no-docker-workflow-build.log`. Local
reproduction of rc2's failed step, `tests/e2e/test_runtime_image.py` with
`DEVCAPSULE_E2E_BASE_IMAGE` set to the v0.2.12-rc5 digest and the PEX built
from `8d005b3`: one passed in 608 seconds; log
`/opt/devcapsule-gate/rc2-runtime-image-repro.log`. Step timings from the
public jobs API: rc1 runtime-session step 74 s success; rc2 42 s failure;
rc2's component-cache Docker step 71 s success, so Docker itself worked on
that runner.

RC2 tag (2026-09-24): the owner merged the release PR; fetched main
`9e2396d` contains `8d005b3` and `a779295`, zero unintegrated commits.
`scripts/release-protocol.py v0.2.14-rc2` passed; record at
`/opt/devcapsule-gate/rc2-release-protocol.json`. Annotated tag pushed
atomically with the branch; remote tag object `4a02aa31d817`, peeled commit
`a779295d7343158d846df89d2d5da184548bfd1d`. Asset publication is the
workflow's; a watcher downloads and verifies the public assets when they
appear. No matrix or lock change: the default base remains the v0.2.12-rc5
digest pin, which carries no runtime (D-0009) and whose recipe is unchanged.

Local rc2 base (2026-09-24): built `devcapsule-base:0.2.14-rc2-local`, image
`sha256:64c8db54eac0bfbefa019c20777bc486abcad4bc5b0ff420d229f79a5f50718a`,
recipe `ubuntu-24.04@9`, host-network build, root `ubuntu:24.04`, by a
revision-bearing PEX built from the pushed branch head
`8d005b38af9777b7e3314bf3e2910314effef4d2` with `--source-revision` asserted.
The recipe is unchanged since rc1, so the content matches the rc1-local base;
only builder provenance differs. Not pushed to any registry, no lock repin,
no matrix change: the owner's reading of "reference the rc2 base by tag"
(digest pin of a new base named for rc2, or a literal tag reference) and the
merge of the release PR are pending. Log `/opt/devcapsule-gate/rc2-local-base.log`.
A first attempt with the `nox -s pex` local artifact was refused by the
builder for lacking a public source revision, as designed.

Manifest compatibility fix (2026-09-24): focused tests 15 passed; full
`nox -s build` passed with 1064 tests, 20 deselected, one xfail, one
quarantined XPASS, mypy, PEX smokes and nine packaged integrations; log
`/opt/devcapsule-gate/manifest-compat-build.log`. Published v0.2.12 and rc1
executables, checksums verified, exercised against the fixed manifest with
isolated XDG state: 0.2.12 `config list` and `config resolve` exit 0; rc1
`config list` exit 0. Pytest scratch had to move to the overlay: this
capsule's 2 GB `/tmp` overflowed on the first run, and a second run under
the home directory failed only `test_unmountable_staging_fails_loudly`,
which expects an unmounted scratch path; the single test passes in `/tmp`
and on the overlay. No capsule was launched; the effect application from
the reserved name is covered by unit tests until RC2 exists.

RC1 configuration failure intake (2026-09-24): owner could not retain the log.
Original successor inspection showed exit 0 and no launch-context/configuration
mounts. One disposable read-only CLI probe of the exact image reproduced
`config list` and `versions show` failures from /opt and the actual project
mount. Bare `project config` prints help successfully. Evidence lives in the
retained run's `configuration-diagnostics.json`; the bug records exact errors
and producer/reader causes. No IDE restart, host-record edit or source fix.
Earlier recursive inspection PASS did not cover this story. No full source
suite was needed for this documentation-only intake.


Published-RC1 recursive PyCharm launch (2026-09-24): retained run
`0edc6f491291f0d5ffa4e31b0238863b` beneath the persistent-home
`e2e-workspaces/` directory. Clean clone at exact RC1 source `cec7a0c`; launched
with downloaded RC1 bytes, SHA-256
`68c58ec09c1a73e07c3bb1b1f7514341ddddaf645c7fae1ff4ff0763ff6f7689`.
The isolated checkout explicitly selects `devcapsule-base:0.2.14-rc1-local`,
pinned locally to image `sha256:0d9a185ec5a2ac04380e9b5540bae2b212356b8b5d4c0f91c7db320d486a414a`;
the project lock is unchanged. Successor image:
`sha256:bc387eb69b8457f61f016a0a21485302e3fc14bcbbae977e4a1623b8d5544863`.
Container `devcapsule-e2e-0edc6f491291f0d5ffa4e31b0238863b-successor` is running
with host networking; the actual PyCharm JVM is PID 42. Independent
`inspect-successor` passed. As UID 1000, public `devcapsule0` reports published
RC1 and exact runtime bytes, ordinary `devcapsule` is absent, and workflow
installation succeeds in a disposable directory. Evidence in the retained run:
`inspection.json`, `runtime-check.json`, `cli-check.log`, `launch.log`.
Owner received the desktop URL; its token is not committed. Human GUI acceptance
of this exact session is pending; no full recursive Nox suite or final-release
acceptance is inferred. Both this session and the earlier local-source session
remain available. No source changes or new downloads of PyCharm were needed.


Published RC1 and local base (2026-09-24): downloaded the public PEX, checksum
and manifest into `devcapsule-src/dist/rc1-published/`. Verified version
`0.2.14rc1`, mnemonic `v0.2.14-rc1`, source
`cec7a0c2f3467b8cc9d84eca820f35ee869087ec`, and SHA-256
`68c58ec09c1a73e07c3bb1b1f7514341ddddaf645c7fae1ff4ff0763ff6f7689`.
Used those exact bytes to build `devcapsule-base:0.2.14-rc1-local` with
`--network host`, recipe `ubuntu-24.04@9`. Image ID:
`sha256:0d9a185ec5a2ac04380e9b5540bae2b212356b8b5d4c0f91c7db320d486a414a`.
Build reused cached installation layers. Metadata and a disposable offline
container smoke passed: Python/Git/Docker, Node/JDK/Maven, display executables;
no bundled runtime PEX or agent CLI. Base is local only, with no registry push
or project-lock change. Evidence: `dist/rc1-published/local-base-build.json`;
log `/tmp/maintenance-rc1-base-build.log`. No GUI acceptance of this new base
or final-release acceptance is claimed. Source unchanged; no need to rerun
the source gate for this image build. Initial coordination claim hit a transient
SSH rejection; a subsequent claim succeeded. The release branch was not rebased.

RC1 publication trigger (2026-09-24): fetched main is
`c6bea96cfbbb15a428c86bde6924df8ff3db1c15` (PR #136); it contains release
commit `cec7a0c2f3467b8cc9d84eca820f35ee869087ec`, with matching runtime/test
sources. Candidate gate passed: mainline, zero unintegrated commits. Pushed
annotated `v0.2.14-rc1` atomically with the release branch and verified both
remote tag object and peeled commit. Expected package version is `0.2.14rc1`.
The public manifest returned HTTP 404 immediately afterward; publication is
pending, not failed or verified. No GitHub API/UI inspection was attempted.
Existing source/type/packaging and real PyCharm evidence applies; no runtime
code changed since acceptance. The release branch was not rebased.

Owner follow-up (2026-09-24): "Everything works" for the retained recursive
PyCharm session below. The installed-IDE cache gap was confirmed by reading
the acquisition/materialization path; filed with proposed acceptance scenarios,
severity minor, target none. No implementation or new Docker experiment was
performed for that report. Documentation links and whitespace were checked.

Owner-requested recursive PyCharm launch (2026-09-24): clean local clone of
`9cc08686c5f6c9b44a1a132bf81e4befd0ecf641`, retained run
`29fb2abc530735da1ebd625acd991622` beneath
`/home/devcapsule/.local/share/devcapsule/e2e-workspaces/`.
The original checkout's preflight fails on its existing website Git pointer;
the exact-commit clone passes without changing the original or its user edits.
Built a revision-bearing PEX, initialized isolated checkout configuration/state,
and ran `recursive-e2e launch-successor` with the pinned real PyCharm distribution.
Successor `devcapsule-e2e-29fb2abc530735da1ebd625acd991622-successor` remains
running with host networking. Independent `inspect-successor` passed; PyCharm's
JVM is running and the desktop has a `PyCharm User Agreement` window.
As UID 1000, `devcapsule0` reports the exact source revision and identical PEX
SHA-256 `a0e29d237e978d8c6575ccf12541571a1c0f1d9e016e8f3174ae1b1e23efb34b`;
`devcapsule` is absent. Workflow bootstrap by public command created the expected
files in a disposable in-container directory. Owner received the desktop URL;
its session token is deliberately excluded from committed records. Fresh IDE
first-run interaction and owner terminal acceptance remain pending. This was
the actual successor launch/inspection, not a claim that the full recursive
Nox suite or release-candidate campaign passed. No new release tag was published.

Owner-requested enum cleanup (2026-09-24): `RuntimeCommand` now owns the
supported public names. Configuration boundaries construct enum members;
materialization accepts the enum without repeating string-domain checks.
Existing tests pass enum members and assert typed forwarding from the launcher.
Required `nox -s build`: type checks, 1,060 source tests and nine packaged
integrations passed (20 deselected, one xfail and one quarantined XPASS).
The final Git-status step still fails on the existing website Git pointer;
the overall gate remains failed. Log:
`/tmp/maintenance-runtime-command-enum-build.log`. No new Docker/GUI campaign
was needed for this refactor; the prior command-mode evidence remains separate.
The release branch was not synchronized or rebased; its local workflow
difference from main is the already-read dogfooding rule from this repair.

CLI repair and development exception (2026-09-24): 311 focused checks passed;
four real-Docker variants passed for PyCharm/VSCodium and devcapsule/devcapsule0.
Tests invoke the command by name as UID 1000, verify exact runtime identity,
and install workflow files in a disposable project. Development mode permits
an independent development command without a shipped fallback. Three additional
filesystem cases ensure only our inherited shipped link is removed, preserving
a development script or symlink (eight runtime-artifact checks passed).
Full gate log: `/tmp/maintenance-runtime-cli-build-final.log`; final source
checks passed (1,060 tests, 20 deselected, one xfail and one quarantined XPASS),
as did type checks and nine packaged integrations. Final Git status then
failed on the existing `/home/devcapsule/.git-website` pointer; overall gate
remains failed.
No actual IDE-terminal acceptance of the new code or RC1 publication is claimed.
Earlier lowercase-help assertion failure was a harness defect, corrected before
the four Docker passes. The pre-fix Docker test reproduced exit 127 as expected.

Blocker intake (2026-09-24): live read-only Docker inspection and runtime
version/hash checks confirm the missing public CLI; IDE process environment
inspection confirms the URL-opener conditions. Evidence is in the two new bug
records. No runtime or website source was changed. New record links/index and
Git diff whitespace checks passed. Full build source/type/PEX checks and nine
packaged integrations passed, then final Git status failed on the pre-existing
website pointer to `/home/devcapsule/.git-website`; overall gate not passed.
Log: `/tmp/maintenance-rc0-blocker-intake-build.log`.
Mail delivered: `2026-09-24-maintenance-url-opening-triage.md` to
contained-display at `ba6768619aac`; workflow-onboarding item delivered to
workflow-improvements. Both await disposition, not implementation in this checkout.

Host-network validation (2026-09-24): owner confirmed the runner's host-network
session works. Attempt 4 in `dist/rc0-runs/session-7a4dbc068f58/run.json` records
requested `host`, observed Docker network `host`, exit 0, container absent and
PROCESS_CHECKS_PASSED. The owner made host networking the standing local launch
preference; see WORKFLOW-LOCAL.md, Local Launch Networking. Deliberate network
isolation tests retain their declared mode. Release branch was not rebased.

Runner network option: `--network host` or `--network bridge` on launch/resume
maps to `project run --authorize network VALUE` for that invocation only.
Omitting the option uses saved configuration, not the previous override.
Requested override is saved with each attempt; Docker inspection already
records actual network mode. Existing run records remain readable. No new
container was started solely to test argument forwarding. The eight focused
runner tests pass, including both override values and omission behavior.
Full `nox -s build` passed (source tests, type checks, PEX smokes and nine
packaged integrations); log `/tmp/maintenance-rc0-network-runner-build.log`.
The release branch was not rebased; workflow definition is unchanged.

Website run (2026-09-23): published RC0 passed its checksum gate and
launched VSCodium from this capsule through the host Docker daemon. Run directory:
`devcapsule-src/dist/rc0-runs/session-7a4dbc068f58`; container
`rc0-runner-7a4dbc068f58`; tool PTY session `73149` (now finished).
Attempt 1 failed with exit 2 before creating a container: local resolution was
missing. `config resolve` exposed unanswered local choices. Applied the existing
campaign policy to this capsule's website checkout record: pinned base plus
Claude/Antigravity downloads accepted; host network/Docker/sudo/browser/X11
denied. Explicit resolve succeeded; website source/lock were not regenerated.
Attempt 2 reused the canonical Codium image, translated bind sources to host
paths, and reached contained-desktop readiness on host loopback port 52123.
The runner captured a running container, bridge network, read-only root and
non-privileged execution with no monitor errors. Terminal reports VSCodium
startup. Owner subsequently confirmed "This is working"; recorded as an S05
startup observation in run.json, without claiming specific editing/debugging
assertions. Attempt 2 ended at 23:17:56 UTC with launcher exit 0, container
absent and no monitor errors: PROCESS_CHECKS_PASSED. Owner subsequently
confirmed the file/IDE resume checklist; attempt 3 passed
exit/cleanup checks and its S10 human observation is saved. Agent-session
continuation remains untested. Token URL stays in the terminal/chat, not this record.
The launcher warned that this capsule lacks a global Git author identity;
no identity settings were changed. Existing full gate remains applicable:
this slice changed only launch configuration and records, not implementation.

Session runner (2026-09-23): seven focused stdlib tests passed, including
Docker errors versus absence, nonzero launch, no inferred graphical PASS,
configuration preservation, wrong candidate, changed daemon and concurrent
writers. `runner.py cli --run /tmp/rc0-stories-cli-only-20260923` passed S02,
S03 and S17 against downloaded RC0; attempt `evidence/cli-y6r9a2ve`.
No real GUI/container session was launched through the new wrapper.
The full required gate passed (1,046 tests, 18 deselected, one xfail, one
quarantined XPASS, type checks and nine packaged integrations), log
`/tmp/maintenance-rc0-session-runner-build.log`. No runtime code changed.
Fetched main and live coordination were inspected; mail was empty. Workflow
files are unchanged; the release branch was not synchronized or rebased.

Story automation (2026-09-23): `verify-cli.py` passed real terminal base
accept/decline, fixed creator/default-agent/host answers, missing-base refusal
and CLI remedy, prompted/batch semantic equivalence, and nine local-remote
coordination operations checking every path/blob plus exact staged mail bytes.
Saved evidence: [CLI validation](../../releases/v0.2.14/smoke/cli-validation.json).
Every attempt gets its own directory; S17 runs independently of failed init,
while S03 requires S02's choices.json. The first harness expectation incorrectly
rejected explicit denials; its correction and retained failure are documented.
The fixed configuration wrapper passed on fresh/TypeScript/trading/FastAPI
fixtures without stdin or human answers. CLI-only preparation also passed.
The required gate passed: 1,046 tests, 18 deselected, one existing xfail and
one quarantined XPASS, type checks and nine packaged integrations; log
`/tmp/maintenance-rc0-story-contracts-build.log`. No graphical/provider/service
acceptance was inferred. Shell syntax and documentation links were checked. The retained preview/launch
helpers now fail on Docker query errors instead of misreporting absence;
fault checks distinguish daemon error, missing container and present container.

RC0 smoke harness (2026-09-23): shell syntax, complete preparation with the
verified published PEX, exact public sample clones, fresh initialization,
resolution and configuration-wrapper roundtrip passed in isolated XDG state.
Refusal checks covered an existing run directory, invalid case/arguments and
a mismatched candidate checksum before CLI execution. Validation directory:
`/tmp/rc0-smoke-script-validation-20260923` (preparation/configuration only;
not a host-backed launch location). No IDE, service or provider campaign was
run while authoring these scripts; the generated result sheet remains NOT RUN.
The required `nox -s build` passed: 1,046 tests, 18 deselected, one existing
xfail and one quarantined XPASS, mypy and nine packaged checks. Log:
`/tmp/maintenance-rc0-smoke-scripts-build.log`. These are harness/repository
checks, not acceptance of the unrun graphical campaign.

Legacy-command removal: 115 focused checks passed, followed by successful
`nox -s build`: 1,046 tests, 18 deselected, one existing xfail and one
quarantined claim XPASS, mypy over 167 source files, source/PEX smokes and
nine packaged integrations. Log: `/tmp/maintenance-retire-pycharm-run-build.log`.
Direct built-PEX checks reject bare/help/legacy-option invocations, show only
retained utilities in PyCharm help, and create no checkout state. Source tests
also prove no launcher/subprocess call. Validated artifact:
`devcapsule-src/dist/devcapsule-local.pex`. The gate skipped revision-bearing
packaging due to checkout edits; no fresh Docker/GUI run was necessary for
this command removal, and no such acceptance is claimed. Main integration
is verified through PR #133; the next candidate remains pending. The pre-existing local bug-file edit
remains unstaged and is excluded from delivery.

Bug-combing review at `8e7cc21`: fetched main remains `e50b9f1`; PR #117 merge
`d2386bb` is in main and RC0. At that review runtime/test sources matched RC0. A CLI probe with
only the launcher substituted confirms legacy `pycharm run` still passes host
networking without an explicit choice. 243 focused existing checks passed;
the earlier image review passed 45. No Docker or provider acceptance was run
for this review. The release table distinguishes prior evidence from proposed
candidate checks, including the incomplete byte-preservation assertion in the
nested-directory regression. No branch synchronization or runtime change.

RC0's integration gate passed by mainline ancestry with zero missing commits.
Local RC0 PEX and Docker base were built from a disposable exact-tag worktree,
which was removed after the build; this checkout remains on release-0.2.14.
Nine packaged assertions/checks passed: eight in the first run, then the
identity check after using the harness's canonical artifact filename. No code
was changed to satisfy that filename check. Local and downloaded PEX each
passed the networkless/no-Python clean-machine check. The locally built base
retains tag devcapsule-base:0.2.14-rc0-local and is not published to a registry.

Prior full source gate: 1,044 passed, 18 deselected, one existing xfail and one
quarantined XPASS, mypy and packaged checks. RC0 has identical runtime/test
inputs. That gate describes RC0, not the subsequent removal. The old claim-test
xfail remains; the retirement has its own validation below.

GitHub PR/workflow UI operations stay with the owner; neither gh nor SSO is
available here. No credential probes or API operations were attempted. Public
asset downloads verify publication; no credentialed Actions-run inspection is
claimed. No final release or graphical/end-user acceptance is claimed yet.

## Open Threads

- Paused for owner travel on 2026-10-31. No work continues during the break.
- On return, confirm the first 0.3.1 slice; release-independent test fixtures
  are proposed. The nine documentation proposals still need item-level
  decisions with project-management; C17 belongs to workflow-improvements.
- No unresolved 0.3.0 release operation remains. Final artifacts, accepted
  source and production website provenance are preserved in release records.
- Scratch caches and raw logs are reproducible and not required to resume.
  Credentials, tokened links and deleted console decision state are deliberately
  not preserved in Git. All consequential decisions are in normal records.


- Final 0.3.0 and its production website are published and independently
  verified. The owner promotion handoff is complete; no release action remains.
- Maintenance now selects ws-maintenance/0.3.1-preparation from main 31d44fa4.
  Scope candidates and outstanding item-level decisions are listed above.
  No implementation slice is underway; the fixture bug is proposed first.
- Final verification/status changes remain on this new branch for the next
  deliverable; coordination carries live routing. No records-only PR.
- Preserve the accepted source, final/candidate tags, final manifest and
  verification facts. Scratch downloads/logs can be reproduced. Credentials,
  tokened links and obsolete console decision state are not durable records.

Earlier threads below are historical and superseded by the current state:

- RC9 is published from release 475427da and integrated through #331 at
  main 4b59b10d. Eight downloaded E2E checks and the shared-browser regression
  pass; the cookie bug is closed. Owner final acceptance remains pending.
- Post-tag evidence/closure records are committed locally on release-0.3.0,
  with live status published on coordination; carry them in the acceptance
  integration. The tag and remote release source remain at 475427da.
- docs-0.3.0 at 7a813b80 matches the release docs tree. Main retains its
  development metadata; do not undo the approved #331 resolution.
- Raw launcher logs, credentials and tokened URLs are deliberately excluded
  from durable evidence. Sanitized facts, screenshots and cleanup survive.
- Downloaded-candidate provider/tool actions, JetBrains editor acceptance and
  the remaining release obligations are not replaced by startup checks.
- The owner must configure ci-gate as required if enforcement is desired;
  main's live rules currently require no status check.
- The approved #317 correction is merged on main at ce08ebad; preserve main's
  0.3.1.dev0 metadata and absence of the release-only docs source override.
- Scratch download/setup attempts are not durable project records. The
  artifact digests, successful probe, screenshots/facts and validation limits
  are retained in the RC9 evidence ledger; caches and built PEX remain local.

- CI Pair Review #314 settled without a revision round. Reviewer proposals
  not implemented: migrate paths-filter v3 to v4 (Node 20 produces a hosted
  deprecation warning), and replace repository-file fixtures in release-doc
  tests so more docs changes can skip Python. These are future maintenance
  choices, not new 0.3.0 requirements or blockers to this approved scope.

- CI slice 2026-10-30: implementation and Pair Review are complete. Next:
  PR #312 is merged at `9eb500da`; the owner adds required `ci-gate` once
  the workflow is available on each intended integration branch; then
  follow normal release propagation to main. No coverage threshold or
  parallelism decision remains open for 0.3.0. Temporary probe PRs must
  remain closed without merge. Scratch logs are not canonical records;
  durable outcomes and GUI evidence are retained in the acceptance record.

- Explicit IDE requirement override, 2026-10-29:
  [PR #304](https://github.com/ccozianu/devcapsule/pull/304)
  (`ws-maintenance/0.3.0-ide-override` -> `release-0.3.0`) is open with
  its judgments and validation. On the owner's word the same day, `main`
  was merged into `release-0.3.0` at `15d8f9df` (34 files, the version
  files kept at 0.3.0, gate passed: mypy 261 files, 2,544 unit tests, 17
  packaging tests, 357 console tests) and the slice branch synchronized
  with it at `db11e8f1`, then again at `2391705c` after the merge had
  dropped the release-only `source-version` line of `docs/versions.yaml`,
  restored on the release branch at `da253875`. The owner then asked for
  the review-partner loop with Codex, `gpt-6-astra` at high effort, run
  detached in `/home/devcapsule/worktrees/ide-override-review` with
  [the brief](evidence/2026-10-29-ide-override/review-brief.md), the first
  loop on Codex's `exec --json` event stream. Its
  [PR #306](https://github.com/ccozianu/devcapsule/pull/306) (PR304.1,
  `6dd56fee`) was accepted without a round and merged at `3bfb3a16`: the
  software-approval offer now follows the IDE request check, a forced
  launch reviews its requested environment instead of the saved one (so
  the advertised override works for a saved IDE that already conflicts
  with a later requirement), the optional-download recovery and the
  local-base minimum guards use the launch policy; 15 tests. One proposal
  not implemented: an old v0.2.11 lock keeps PyCharm beside Codium on an
  ordinary override, the unfiltered legacy-lock path of `usable_lock`,
  which predates this slice; filed as
  [a bug](../../bugs/devcapsule/2026-10-29-legacy-lock-keeps-the-replaced-ide.md).
  The post-merge gate passed on `3bfb3a16` and the owner merged PR #304
  at `cfa45937` on 2026-10-30; the records of the loop, the bug and the
  restored D-0016 sentence follow in a records pull request.
- The review branch rule: [PR #305](https://github.com/ccozianu/devcapsule/pull/305)
  adds to topic 9.11 that the loop runs only on the human's request or as
  the local file's default; merged by the owner at `a1e3b0b2`.
- Settled 2026-10-29: `--save` with `--force` stays refused, by the
  owner's ruling. Awaiting the owner: whether any other policy check gets
  the same explicit escape; the review-partner loop runs only on request
  (PR #305), so no review is pending for PR #304 unless the owner asks.
- Weighed and unresolved: a forced launch's resolution on disk makes
  `images build` and the recursive successor ask for a plain `run` until
  the next launch; accepted as honest. The `config show` listing of the
  checkout never shows a departure, by design.
- Not run: the known-good record path of a successful forced launch on a
  real capsule, since the smoke stops its sessions with `docker stop`; the
  unit test covers it.
- External state preserved: the implementation worktree
  `/home/devcapsule/worktrees/ide-override`; the raw smoke evidence under
  its `devcapsule-src/dist/e2e-evidence/ide-smoke/`, removable; the gate
  scratch `/opt/devcapsule-gate/pytest-ide-override`.

- VS Code slice, 2026-10-28:
  [PR #301](https://github.com/ccozianu/devcapsule/pull/301)
  (`ws-maintenance/0.3.0-vscode` -> `release-0.3.0`) awaits the owner's
  merge; the review [PR #302](https://github.com/ccozianu/devcapsule/pull/302)
  is accepted without a round and merged at `241e7b10`.
- Awaiting the owner: the `vscode-ide` capability beside the provider form
  (judgment 1 of PR #301); whether the generic half of the relay rule goes
  to the definition, topic 9.11, through project-management.
- Weighed and unresolved, from PR #302 (PR301.1): the denial remediation
  text in `configuration/authorization.py` names a raw TOML key instead of
  `project config authorize vscode-download true`; `config recommend
  frontend-ide none` leaves a hand-written `codium = "vscode"` alias in
  place. Both predate the slice.
- Not run: a relaunch or persistence check of VS Code's user data and
  extensions; the recursive dogfood lifecycle session, which exercises the
  PyCharm dogfood lock and not VS Code.
- External state preserved: the implementation worktree
  `/home/devcapsule/worktrees/vscode-ide` on `ws-maintenance/0.3.0-vscode`;
  the temporary clone `/home/devcapsule/worktrees/vscode-e2e-tmp` with the
  raw smoke evidence under `devcapsule-src/dist/e2e-evidence/ide-smoke/`,
  removable; the recording also at `~/e2e-videos/`; the review worktree
  `/home/devcapsule/worktrees/maintenance-review` on
  `ws-maintenance/0.3.0-vscode-review`, reusable by a reset; the primary
  mount `/workspace/301e4208ef81-ChatGPT_Codex` untouched on
  `ws-maintenance/e2e_videos-2`.
- Deliberately not preserved: the session scratchpad with the Antigravity
  log and the gate scratch under `/opt/devcapsule-gate`, on the overlay.

- Diagnostics snapshot and export slice, 2026-10-27:
  [PR #293](https://github.com/ccozianu/devcapsule/pull/293)
  (`ws-maintenance/0.3.0-diagnostics-snapshot` -> `release-0.3.0`) awaits the
  owner's merge. Codex (`gpt-6-astra`) review
  [PR #295](https://github.com/ccozianu/devcapsule/pull/295) (`c190d1cf`) is
  accepted without a round and merged at `5cc52392`.
- Weighed and unresolved, from PR #295 (PR293.1):
  1. Overall runtime-probe deadline budget preserving partial results if
     several 2 s probes time out sequentially inside the 5 s `docker exec` cap.
  2. Separate cgroup v2 schema representation for `"max"` (unlimited) vs.
     unreadable limit files (both currently `null`).
  3. Automatic browser-side DevTools capture (outside this slice per
     Deliverable 5).
- External state preserved: implementation worktree
  `/home/devcapsule/worktrees/diagnostics-snapshot` on
  `ws-maintenance/0.3.0-diagnostics-snapshot`; primary mount
  `/workspace/301e4208ef81-ChatGPT_Codex` left untouched on
  `ws-maintenance/e2e_videos-2` with its pre-existing `.devcapsule/` and
  `.idea/` edits; local `main` fast-forwarded to `origin/main` (`8afa5f6d`).
- Deliberately not preserved: review worktree
  `/home/devcapsule/worktrees/maintenance-review` and local branch
  `ws-maintenance/0.3.0-diagnostics-snapshot-review` (removed after merging
  PR #295); temporary gate/pytest directories under `/opt/devcapsule-gate/`.

- Saved Docker arguments slice, 2026-10-23: PR #253 targets `release-0.3.0`;
  only the human merges it. Reviews #254 and #255 are accepted and merged
  into the slice; #255 took two revision rounds. No real credentials, full
  IDE launch or GPU execution were used. General options persist literally;
  env conveniences and masking have the documented supported-spelling and
  ambiguity boundaries. No unanswered product choice blocks this PR.
  Original e2e_videos checkout IDE changes were deliberately left alone.
  The implementation checkout remains at /home/devcapsule/worktrees/checkout-env;
  the clean review checkout and merged local review branch were removed.
  Resume by verifying PR #253 and the release tip before further work.

- Paused 2026-10-22 evening by the owner. Nothing is uncommitted; the
  checkout sits on `release-0.3.0` at the published tip; the claim is
  released. The other checkout's sessions write their entries on `main`;
  this one's on the release branch; both met in the second synchronization.
- Done 2026-10-22: PR #249 merged; rc2 tagged, published, verified; the
  lock regenerated and proven by the recursive launch.
- Done 2026-10-23: the owner verified the terminal summary and Ctrl+C on
  rc2; both C10 records closed. PR #250 and PR #253 merged by the owner.
- Awaiting the human: the go for the schema-version slice; the network
  node's check on rc2 on a fresh project; the wording of Release Policy 8
  for the one version commit on the throwaway copy; the eleven user-docs
  decisions; the word on the manifest-rewrite finding; provider acceptance
  of the new agent pins on a downloaded candidate, which needs the lock in
  a candidate, rc3.
- On resumption, after the merge: fetch and confirm the release tip
  `e5b5a8b` is an ancestor of `main`; `git tag -a v0.3.0-rc2 e5b5a8b -m
  'DevCapsule 0.3.0 candidate 2'`; from a detached checkout of the tag,
  `scripts/release-protocol.py v0.3.0-rc2 --output
  /opt/devcapsule-gate/rc2-release-protocol.json`, expecting `mainline`;
  `git push --atomic origin release-0.3.0 v0.3.0-rc2`; the backend run;
  download the three assets into `~/.cache/devcapsule-releases/v0.3.0-rc2`,
  verify the checksum and the version; record rc2 in the overview and the
  table above, and the changelog's candidate-2 date. Then the owner's
  dogfooding of the terminal and Ctrl+C on the download, and the three
  records' verification on it.
- Then the slices: C17's local half, this project's operating instructions
  in `WORKFLOW-LOCAL.md`; forced configuration and the diagnostics snapshot
  for rc3; image cleanup after the owner's design review, and C20, for rc4.
- Weighed and unresolved, from PR244.1: the supervisor's blocked SIGINT
  during a readiness wait; the 250 ms absorption of a second Ctrl+C.
- Weighed and unresolved, from PR250.1: a stored consent cannot prove the
  terms it was given for; for the consent slice of D-0011.
- Filed for V1 at the owner's direction: the session logs' Python data
  path, [the record](../../bugs/devcapsule/2026-10-22-child-output-is-processed-in-python-on-the-data-path.md).
- External state that outlives the session: the review worktree
  `~/worktrees/maintenance-review` on
  `ws-maintenance/0.3.0-first-session-summary-review`, reusable for the
  next loop by a reset; the gate scratch under `/opt/devcapsule-gate`, on
  the overlay, gone at the next restart; the e2e evidence under
  `devcapsule-src/dist/e2e-evidence/ide-smoke/`; the local branch
  `4PR-3-release-0.3.0`, deleted by the merge on the remote and to be
  deleted locally.
- Deliberately not preserved: the session scratchpad with the Codex and
  Antigravity logs; the briefs are committed under `evidence/`.
- Paused 2026-10-22 on `ws-maintenance/e2e_videos-2` after completing the
  Claude Fable 5.1 review-partner loop ([PR #241](https://github.com/ccozianu/devcapsule/pull/241))
  for [PR #236](https://github.com/ccozianu/devcapsule/pull/236).
- Awaiting the human: review and merge [PR #236](https://github.com/ccozianu/devcapsule/pull/236)
  (`ws-maintenance/4PR-e2e_videos-2` into `main`).
- Weighed and unresolved, from PR #241 (PR236.1):
  1. Transcoding PNG frames to JPEG with Pillow in the parent process instead of
     an in-page `<canvas>`, reducing browser round-trips and decoupling WebM
     encoding from a live Playwright page.
  2. Passing `-framerate` instead of `-r` before `-i pipe:0` for `ffmpeg`'s
     `image2pipe` input.
  3. Adding a dedicated `nox` session wrapper for `tests.e2e.scenario_recorder`
     (`serve`, `ctl`, `replay`) so operators do not need `PYTHONPATH=src:.`.
- Deliberately not preserved: the review worktree
  `/home/devcapsule/worktrees/maintenance-review` and its branch
  `ws-maintenance/4PR-e2e_videos-2-review` (removed after merging PR #241);
  gate and review logs under `/opt/devcapsule-gate/` and the session scratchpad.
- Resumed 2026-10-21 under rc1; the re-verification of the 2026-10-19
  threads is in Current State. Two checkouts work this workstream; the
  second one's session published this file from `main`'s copy with the
  rc0 state line. Open with the owner: which checkout publishes the
  status file while both are on maintenance; this one, the release
  checkout, is the recommendation.
- Closed 2026-10-21: the console-link record, on the owner's verification.
- Done 2026-10-22: PR #240 merged into `release-0.3.0` at `6ebadf2`, PR #243
  into `main`; the network node is on the release branch for rc2. Next:
  C10, its details to the owner first.
- Awaiting the human: PR #244 into `release-0.3.0`, C10, with its review
  merged after one round; then the word for rc2.
- Weighed and unresolved, from PR244.1: the supervisor's blocked SIGINT
  during a readiness wait; the 250 ms absorption of a second Ctrl+C.
- To record on `main`: the Antigravity invocation form proven on
  2026-10-22, the model flag before `-p` and the brief on standard input
  behind a one-line instruction, in the developer document.
- Done 2026-10-22: PR #237, #238 and #239 merged to `main`; the
  scratch-mount item mailed to `project-management`.
- Weighed: Version Scheme rule 4, `main` reopening at the cut, has no
  companion paragraph in the humane file; left out of PR #237 unless the
  owner adds it.
- On resumption, re-verify before trusting: which launcher started the
  capsule (`devcapsule0 version`), whether the shared lock changed on disk
  (the owner may run the lock command on the host before relaunching; if
  so, commit the written lock on the release branch and rerun the gate),
  and whether this checkout was given the local recipe-11 base.
- Next slices in the recommended order: the universal `network` node,
  then C10 with its two records filed first, forced configuration, the
  diagnostics snapshot, image cleanup after the design review, C20 last.
  The local Docker proofs against the rc1 download when the host daemon
  is free.
- Deliberately not preserved: the rc0 and rc1 downloads under
  `~/.cache/devcapsule-releases/`, regenerable from the public releases;
  the gate logs under `/opt/devcapsule-gate/`; the smoke scratch of the
  agent freshness attempt in the session scratchpad.
- Closed 2026-10-18, twice: PR #228 carried the release version onto
  `main`; the owner then changed the protocol, and PR #229 reopens `main`
  at 0.3.1.dev0 at the cut, ahead of every candidate.
- Closed 2026-10-18 by the owner: delete-on-merge stays; the release
  branch merges into `main` through a throwaway copy, *Release Policy* 8.
- Awaiting the human, with the version question: whether the manifest's
  release-branch line (`source-version` on `devel`) is acceptable until the
  contract or its check gains a release-branch rule, mailed to
  project-management on 2026-10-18.
- At the owner's convenience: the one host command in PR #224 that
  regenerates the shared lock, so this checkout runs the new agents; it no
  longer gates anything.
- The local branch `ws-maintenance/release-0.3.0`, the previous session's
  parking spot at the merge of PR #222, has no commits of its own and is
  not on the remote; left for the owner to delete.
- Weighed: the C10 bug records are not filed; the C10 slice files them
  first, as the work order says.
- External state that outlives the session, all removable now that the
  PRs are merged: review worktrees `~/worktrees/maintenance-review` and
  `~/worktrees/maintenance-review-pr2`; the acceptance clone and venv under
  `~/.local/share/devcapsule/e2e-workspaces/logs-accept`; local images
  `devcapsule-base-e2e:v0.2.16.dev0-local-linux-x86_64-36bef9f1e151` and
  `devcapsule-local-codium:60ed46caf1a3e8897e5d`.

Threads of the 2026-10-12 pause, decided or overtaken on 2026-10-18 where
marked:

- Decided 2026-10-18: two items from project-management taken on
  2026-10-12, `2026-10-11-project-management-bootstrap-target-09.md` and
  `2026-10-11-project-management-pre-rc-sequence.md`, in the intake; decide
  them first on resumption, they are not forwardable.
- Done: PR #207 and PR #209 are merged (2026-10-11, and #216 on 2026-10-15).
- External state that outlives the session: review worktrees
  `~/worktrees/maintenance-review` and `~/worktrees/maintenance-review-pr2`;
  the acceptance clone and venv under
  `~/.local/share/devcapsule/e2e-workspaces/logs-accept`; local images
  `devcapsule-base-e2e:v0.2.16.dev0-local-linux-x86_64-36bef9f1e151` and
  `devcapsule-local-codium:60ed46caf1a3e8897e5d`. All removable once the
  PRs are merged.
- Weighed and unresolved, from PR1.1: the supervisor's `preexec_fn` runs
  with tee threads alive, which Python documents as unsafe; a helper that
  sets the mask and execs would remove it. Not changed, no failure seen.
- Weighed and unresolved, from PR2.3: an atomic replacement of the live
  path for readers that follow it across a rotation; a drain policy for a
  compression that outlasts the supervisor's 0.5 s allowance at shutdown.
  Neither changes the contract; both are candidates for the next slice.
- Weighed and unresolved: the budget knob is an environment variable; a
  configuration node would be durable but touches the guarded vocabulary.
  Xvnc at status level rather than errors only.
- Weighed and unresolved: the C10 first-session bug records are not on
  `main`. The diagnostics slice takes the Ctrl+C result into its scope
  unless project-management files them first.
- Deliberately not preserved: the review worktree of
  `pr172-correctness`; the web console caches under
  `devcapsule-webconsole/`, which `.gitignore` covers.
- The original checkout's website pointer stays untouched. SSH through
  `ssh.github.com:443` worked when port 22 timed out on 2026-10-08.

Earlier threads follow; read against the state above.

- Resumed 2026-10-05; main merged in at `242e13e` (fast-forward). Decisions
  (1) to (3) are taken: ecosystem bootstrap stays a bug, target 0.3.0,
  last on the plate; the recursive successor record goes by option D, the
  fresh-workspace test, with the general rule in the e2e doc; the
  installed-IDE reuse and reaping design is in the next release, which
  the owner named 0.3.0 (mail to project-management sent); (5) the
  host-network run-once item is a bug by the owner's ruling, `network`
  becomes a universal node, filed and dispositioned. (4), the in-capsule
  project-command fix, stands as decided on 2026-10-01; restated on
  2026-10-05 without objection. The triage is complete. The three
  component-catalog items are dispositioned (packaging patch applied and
  green; the conservative-writers correction is the requirement under
  *Current State*, with the owner's `resolve --force` and `run
  --force-config` addition, mailed to project-management). Next: the
  owner confirms the plate's order; no implementation has started.
- Intake item, host-network run-once launch rejected (superseded 2026-10-05
  by the bug record; kept as the trail): component-catalog's
  diagnosis is incomplete. `_RUN_ONCE_AUTHORIZATIONS` includes `network` on
  `main` and here; the node exists only on projects whose manifest
  recommends `host.network.mode` (`authorization_declarations` builds it
  from `CURATED_HOST_RECOMMENDATIONS`, and `WORKSTATION_CAPABILITY_DEFAULTS`
  deliberately omits it because raw `--network` was the run-once form,
  which run help now refuses). This repository recommends it, so the
  WORKFLOW-LOCAL command works here; the smoke's fresh project does not.
  Product choice for the owner: make network a universal authorization node,
  or amend WORKFLOW-LOCAL to say the command presupposes the recommendation
  (recommended). Owner ruled 2026-10-05: universal node; it is a bug.
- The claim on the triage slice was released at this pause.

- Final 0.2.15 publication and download verification are complete.
- PR #149 is merged and verified; main is reopened at 0.2.16.dev0.
  Await owner dogfooding feedback on released 0.2.15; no new scope is inferred.
  User-facing release notes are prepared in the release overview; GitHub's
  final release body currently contains its generated changelog link.
- Project-management receives final identity/acceptance and reopening state;
  0.2.16 scope decisions remain with that workstream and the owner.
- New source and records branch: `ws-maintenance/post-0.2.15`. The release
  records exception has ended; publish from this branch going forward.
- Final downloads: `/home/devcapsule/.cache/devcapsule-releases/v0.2.15`;
  gate `/tmp/0215-final-gate.json`; verifier `/tmp/0215-verify-final.py`.
  RC1 downloaded proofs and private fixtures remain alongside. Scratch
  evidence is regenerable; no credentials/tokens or session transcript in Git.
- Use `TMPDIR=/opt/d215` for gates. Do not infer release identity from local
  mainline dist builds. Retain published release/candidate tags unchanged.

Earlier open-thread history (read against the current scope above):

- Pause of 2026-09-26. Merged to `main` today: the base-contract slice
  (consent bound to the image, bases named by `family@recipe`, compatibility
  report), the `devcapsule.images` package, and the design-experiment work
  order. Awaiting the owner: yes or no on the named-build-context fix for
  the 4.8 GB rebuild transfer; the GitHub release body for `v0.2.14`.
  Awaiting project-management: 0.2.15 registration and scope, the
  release-notes artifact, the mycodespace note and checkout naming. Still
  open from the design note: the base as a version-set member, registry tags
  by contract and date. The `ws-user-docs/first-session` branch carries the
  mycodespace design note and needs its own PR to reach `main`.

- Pause of 2026-09-25, after 0.2.14 shipped and the close-out cleanup.
  Awaiting the owner: the PR from `ws-maintenance/post-0.2.14` (registry
  rows, 0.2.15.dev0, close-out records); the GitHub release body for
  `v0.2.14`, notes text in the release overview; option A or B for the
  `v0.2.12` mnemonic; yes or no on the named-build-context fix. Awaiting
  project-management: registration and scope of 0.2.15 (mail of
  2026-09-25), adoption of the mycodespace note and the checkout-naming
  default (mail of 2026-09-25). Awaiting workflow-improvements: the four
  workflow gaps (mail of 2026-09-25). Deliberately not preserved: the
  scratch builds and downloaded candidates under `/opt/devcapsule-gate`,
  which are regenerable from the public releases.

- Owner's rc3 test, 2026-09-24, produced three findings, all recorded and
  now dispositioned: the trailer is fixed by the list/show split (RC4); the
  acquisition decision stays required with a named release-notes exception;
  the checkout naming is not a bug. Earlier text of this thread follows:
  the launcher change rebuilt the formation with a 4.28 GB context transfer
  and 39 retained images at 266 GB (added to the installed-IDE reuse bug);
  `config list` advises resolve on a fresh resolution (new minor bug, fix
  proposed); and an untouched 0.2.12 checkout now owes a required
  antigravity-download decision (new bug under R-COMPAT-001, disposition
  needed: restore 0.2.12 behavior or name the exception in the notes).
  The rc3 launch worked and the owner confirmed `devcapsule0` on the PATH in
  the capsule: the runtime-CLI blocker is closed as verified on rc3. From
  `/opt` the configuration inspection still fails; from the project mount it
  works, so only the discovery fallback (cause 2) affects ordinary launches.

- RC2 is required: rc1 accepts the fixed manifest but applies the
  `devcapsule0` exception only from the attribute, so dogfood sessions
  launched with rc1 on the fixed manifest get the normal `devcapsule` name
  until RC2. Existing running capsules are unaffected.
- The owner's host executable was not identified; the reported message can
  only come from 0.2.12 or rc0. Ask for `devcapsule version` when closing.
- The guard test pins `docker.memory-limit` as the released vocabulary; move
  it to include `devcapsule.command-name` when 0.2.14 final ships.
- The website checkout in this capsule has an embedded `.git` directory
  since 2026-09-23; the other checkout's pointer repair did not hold, as the
  owner's `git status` failure shows. Not repaired from here.

- RC1 runtime-configuration inspection bug needs component-upgrades triage;
  owner expects read-only inspection from /opt as well as the project root.
  Mail delivered at `dc91dbc8e484`; acknowledgement and repair remain pending.
- Run `0edc6f491291f0d5ffa4e31b0238863b` subsequently exited normally (code 0);
  earlier retained-running notes below are historical. No restart was attempted.

- Published RC1 plus the newly built local base is running in retained recursive
  run `0edc6f491291f0d5ffa4e31b0238863b`; agent checks passed, owner GUI acceptance
  pending. Keep it running for the owner; do not stop the earlier session either.

- Recursive PyCharm successor run `29fb2abc530735da1ebd625acd991622` is deliberately
  retained for the owner; see validation above. Do not stop or remove it merely
  because this agent turn finishes. Owner subsequently confirmed everything works.
- The runtime CLI blocker is fixed in source, awaiting main integration and
  exact-RC1 validation; public assets now verified and PR #136 is merged. Owner accepted
  the local PyCharm/devcapsule0 session; exact-candidate validation remains.
  Existing running capsules retain their original commands until relaunched.
- URL-opening triage and workflow-onboarding work item are handed to their
  owners through coordination mail. Their acknowledgement remains pending.
- The local workflow change reported by brief is our owner-directed host-network
  rule, already read; the release branch was not synchronized or rebased.
- Website Git pointer repaired locally on 2026-09-24 after the owner reported
  plain `git status` failing. Replaced missing `/home/devcapsule/.git-website`
  with relative `../.git/modules/website`; the existing metadata HEAD matches
  the parent's pinned commit `78b7b7f`. Original pointer saved at
  `.git/codex-website-git-pointer.before`. Plain parent/submodule status now
  works; website status and staged/unstaged binary diffs are unchanged.
  No source, index or ref was reset. The earlier policy-only full build passed
  source/type/PEX checks and nine packaged integrations before failing at this
  status operation; log `/tmp/maintenance-host-network-policy-build.log`.
  That historical full gate was not rerun for this local metadata repair.
- Exact RC0 website startup and file/IDE resume now have owner confirmation.
  Do not extend that evidence to unperformed edit/debug or agent tasks.
- Website runner attempts 2/3 are complete: owner confirmed startup and
  file/IDE resume; automatic exit/cleanup checks passed. Agent continuation
  and detailed edit/debug assertions still need execution. Website submodule
  changes belong to the owner and were untouched.
- Owner rejected the earlier manual-heavy campaign. Stories now govern the
  work; do not describe all 21 as automated. Implement remaining machine steps;
  desktop-control tooling is absent here. No provider/GUI acceptance is claimed.
- A pre-existing single `c` insertion in the smoke README remains in the working
  tree and is excluded from the rewritten document's commit, like the earlier
  unrelated bug-file edit. Its intent was not inferred.

- Legacy launch capabilities now have an owner-directed V1 gate: decide what
  is already covered, migrate selected capabilities, design an image-oriented
  mode only if justified, or explicitly drop them. The work order preserves
  the findings; project-management owns scheduling and ledger registration.
- Owner review of the 13 remaining bug dispositions remains; the full rationale
  and grouped acceptance observations are in the release bug table. Review
  project-launch old-base/X11 scope before closure of the display exposure record;
  distinguish repaired formation boot behavior from remaining image cleanup.
- A pre-existing local edit in the legacy-network bug removes one word and
  leaves trailing whitespace. It was preserved verbatim and excluded from
  all agent commits. Agent-authored retirement notes in that same file are
  staged separately from the pre-existing edit.
- Image composition redesign is deferred beyond 0.2.14 unless the confirmed
  multiline-rendering defect recurs during the release E2E campaign; preserve
  its documented-contract and unit-testing scope when scheduling the work.
- RC0 is published; end-user acceptance and selected further bug dispositions remain.
- Project-management coordinates renames after 0.2.14 publication, before
  substantive next-release work. This no longer holds 0.2.14 candidates.
- Workflow-improvements owns the claim-test design repair and generic release
  propagation rule revision; the local owner exception already governs here.
- Preserve retired-outbox follow-up, configuration contracts/coverage limits,
  and historical host/blog acceptance gaps; no unrelated cleanup was done.
- The pre-existing Codium delimiter edit remains saved at
  `.git/codex-preserved-codium-sudo-edit.patch`; its intent was never inferred.
  The canonical bug record now records retirement, so review before applying it.
- No transcript/session record was requested; canonical decisions live in the
  release documents and bug records.

## Workstream Document Index

- [PR #16 Pair Review brief (PR16.1)](evidence/2026-11-08-webconsole-delivery/review-brief.md), [D-0017](../../decisions/product/d-0017-launcher-delivers-web-console-package.md), and [0.3.1rc1 web console delivery bug](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md): launcher-delivered web console slice (`ws-maintenance/webconsole-delivery`, stacked on PR #18).

- [PR #26 Pair Review brief (PR26.1)](evidence/2026-11-11-host-inputs-at-source/review-brief.md): brief for `Codex + GPT-6 Astra` on the removal of PR #18's test-only parameters and the tests that set the host at its source.
- [PR #18 Pair Review brief (PR18.1)](evidence/2026-11-08-webconsole-legacy-tests/review-brief.md): brief for `Claude Code + Claude Fable 5.1` on whole-file legacy test retirement and 4-file refurbishment (`ws-maintenance/webconsole-legacy-tests`).

- [RC9 preparation and component verification](evidence/2026-10-31-rc9/README.md).

- [User-docs 0.3.0 CLI alignment work order](../../work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md),
  [Batch 1 verification ledger](evidence/2026-10-30-docs-batch-1/README.md),
  [PR319.1 Pair Review brief](evidence/2026-10-30-docs-batch-1/review-brief.md), and
  [CLI schema-help / migration-hint bug](../../bugs/devcapsule/2026-10-30-config-show-json-help-and-retired-home-command-hints.md): PR #319 / #320, reviewed 0.3.0 documentation alignment slice (`docs/reference/`, `docs/updates/`, `docs/troubleshooting/`).

- [CI Pair Review brief](evidence/2026-10-30-ci-gating/review-brief.md) and
  [acceptance evidence](evidence/2026-10-30-ci-gating/acceptance.md): PR #312,
  active review and hosted validation; owner required-check step outstanding.

- [CI path gating and advisory diff coverage](../../work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md): active 0.3.0 slice.

- [Explicit IDE requirement override evidence](evidence/2026-10-29-ide-override/README.md): the recorded acceptance session of 2026-10-29, forced Codium then plain PyCharm, and the review brief.
- [Batch 2 verification ledger (`docs/configuration/`)](evidence/2026-10-30-docs-batch-2/README.md) and
  [PR321.1 Pair Review brief](evidence/2026-10-30-docs-batch-2/review-brief.md): PR #321, 10-file 0.3.0 documentation alignment and prose slice on `ws-maintenance/0.3.0-docs-batch-2-configuration`.
- [VS Code smoke evidence](evidence/2026-10-28-vscode/README.md): the recorded IDE smoke of the `vscode` surface, 2026-10-28, and the PR301.1 brief for Antigravity, Gemini 4 Argon (High).
- [PR #293 review-partner brief (PR293.1)](evidence/2026-10-27-diagnostics-snapshot/brief-pr293-1.md): brief for Codex (`gpt-6-astra`) on the session diagnostics snapshot and sanitized export slice.
- [PR #236 review-partner brief (PR236.1)](evidence/2026-10-22-pr236-review-brief.md): brief for Claude Fable 5.1 on the E2E scenario video recorder and Eclipse Java debugger demo slice.
- [Landing-page work order (`Why DevCapsule?`)](../../work-orders/2026-10-18-landing-page-why-devcapsule.md): Deliverables 1–4 completed and verified on `ws-maintenance/e2e_videos`.
- [Stretch-goal hero video follow-up work order](../../work-orders/2026-10-19-eclipse-java-1brc-hero-video.md): Eclipse/Java 1BRC hero video stretch goal with reusable pipeline preamble and unblocking options.
- [Batch 3 verification ledger (`README`, `getting-started`, `your-project`, `containment`)](evidence/2026-10-30-docs-batch-3/README.md) and [PR323.1 review brief](evidence/2026-10-30-docs-batch-3/review-brief.md): 10-file 0.3.0 documentation alignment and prose slice ([PR #323](https://github.com/ccozianu/devcapsule/pull/323)) on `ws-maintenance/0.3.0-docs-batch-3-onboarding-project-containment`.
- [0.3.0 release overview](../../releases/v0.3.0/README.md): the cut, the checklist, the freshness review, the candidates; open for any release question.
- [0.3.0 bug table](../../releases/v0.3.0/bugs.md): the records the release carries and their dispositions.
- [0.3.0 changelog](../../releases/v0.3.0/changelog.md): what is new and fixed since 0.2.15, maintained at every candidate; the prerelease body.
- [Diagnostics and logs](../../../docs/troubleshooting/diagnostics-and-logs.md): the user-facing statement of slice 1; open when changing what a session logs.
- [Session logs acceptance](evidence/2026-10-11-session-logs/README.md): the recipe-12 base, the real session, the rotation; open when a reviewer asks what was proven on a capsule.
- [PR #172 review](2026-10-08-pr172-review.md): findings, fixes, regression evidence and remaining limits.
- [Batch 4 verification ledger (`everyday-development`, `working-with-ai`)](evidence/2026-10-30-docs-batch-4/README.md) and [PR325.1 review brief](evidence/2026-10-30-docs-batch-4/review-brief.md): 10-file 0.3.0 documentation alignment and prose slice ([PR #325](https://github.com/ccozianu/devcapsule/pull/325)) on `ws-maintenance/0.3.0-docs-batch-4-everyday-dev-and-ai`.
- [Unpacked cache publication/recovery bug](../../bugs/devcapsule/2026-10-08-unpacked-cache-publication-and-recovery.md): fixed on review branch; close after main integration.

- [Released launchers reject the repository manifest](../../bugs/devcapsule/2026-09-24-released-launchers-reject-repository-manifest.md): blocking, fixed on branch, needs RC2.

- [RC1 runtime configuration inspection](../../bugs/devcapsule/2026-09-24-runtime-configuration-inspection-fails.md): component-upgrades; confirmed, target 0.2.14.

- [Installed IDE Docker reuse](../../bugs/devcapsule/2026-09-24-installed-ide-docker-reuse.md): review design with owner before implementation; no release target.

- [Runtime CLI blocker](../../bugs/devcapsule/2026-09-24-runtime-cli-not-on-path.md): next implementation task; blocks 0.2.14.
- [URL-opening defect](../../bugs/devcapsule/2026-09-24-url-opening-without-browser-handler.md): contained-display triage.
- [Workflow onboarding](../../work-orders/2026-09-24-workflow-installation-onboarding.md): non-blocking follow-up.
- [Web-console port-scoped cookie bug (`0.3.0`)](../../bugs/devcapsule/2026-10-31-webconsole-cookie-collides-across-ports.md): fixed on `ws-maintenance/0.3.0-webconsole-port-cookie`; close after `release-0.3.0` merge, `main` propagation, and published recipe-11 base pin refresh.
- [0.3.0 user docs Batch 5 evidence](evidence/2026-10-30-docs-batch-5/README.md): Batch 5 (`sessions/`, `collaboration/`, `platforms/`) scope, validation, and Pair Review record.
- [PR #327 review-partner brief (PR327.1)](evidence/2026-10-30-docs-batch-5/review-brief.md): brief for `Codex (gpt-6-astra)` on Batch 5 (`#327`/`#328`).

- [Legacy launch capability work item](../../work-orders/2026-09-22-legacy-launch-capability-disposition.md): future-release decisions and delivery, blocking V1.
- [Release overview](../../releases/v0.2.14/README.md): cut, candidates and acceptance checklist.
- [Release bug triage](../../releases/v0.2.14/bugs.md): maintained dispositions and evidence.
- [RC0 validation runner](../../releases/v0.2.14/smoke/README.md): executable coverage and exact candidate inputs.
- [RC0 validation stories](../../releases/v0.2.14/smoke/stories.md): dependency types, actors, contracts and remaining automation.

- [Attribution checkpoint](2026-09-22-record-commit-attribution.md): integrated authorship convention, owner acceptance and build evidence.

- [Run-image replacement checkpoint](2026-09-22-record-run-image-replacement.md): merged implementation, validation and coordination recovery evidence; open only for those details.
- [Prior checkpoint record](2026-09-21-record-maintenance-before-component-upgrades.md): historical implementation, tests and graphical evidence; open only for those details.
- [Proposed bug triage](2026-09-21-note-proposed-bug-triage.md): open on resuming triage; not applied.
- [Pre-V1 assessment](2026-09-21-note-pre-v1-adopter-and-contributor-case.md): positioning input and owner Windows correction.
- [Early-adopter blog](../../blog/2026-09-21-why-try-devcapsule-before-v1.md): merged article and editorial follow-up.
- [Upgrade recovery contract](upgrade-recovery-contract.md): scope of the merged recovery fix.
- [Configuration contract](configuration-contract.md): lifecycle requirements relevant to future changes.
- [Correctness/test map](configuration-correctness.md): implementation evidence and coverage limits.
- [Intake decisions](intake-dispositions.md): outcomes of received mail.
- Persistent session diagnostics work order: expected at `engineering-docs/work-orders/2026-10-08-persistent-session-diagnostics.md` once project-management commits it; until then the text is the intake item at coordination `a535ccf`.
- `intake/`: empty; the three items of 2026-10-09 and 2026-10-11 are decided in the decision log.
