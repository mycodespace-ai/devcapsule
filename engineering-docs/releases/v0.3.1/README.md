# DevCapsule 0.3.1 — Release Work

Updated: 2026-11-10. Stage: **candidate 2 (`v0.3.1-rc2` on `be0140ca`) published and verified; all three 0.3.1 release bugs closed (Eclipse libsoup on rc1; launcher-delivered web console `D-0017` and Codex npm abbreviated metadata on rc2 + `component-status` feed); Codex `0.167.0` and Claude Code `2.1.321` shipped in `embedded-33`; two rulings open**.
Driver: **maintenance**. Product owner: Costin Cozianu.

[Changelog since 0.3.0](changelog.md) ·
[Bug table](bugs.md) ·
[Scope and cut decision](../../wip/2026-09-18-maintenance/2026-11-07-decision-release-0-3-1-scope-and-cut.md) ·
[Runbook](../../implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md) ·
[0.3.0 release work](../v0.3.0/README.md)

Update this file as decisions and evidence arrive. Chat highlights changes
and questions; the bug records remain authoritative for individual status,
ownership and technical evidence; the maintenance status file links here
for resumption.

## Headline

DevCapsule runs on an Apple Silicon Mac, built from source, with capsules
native on `linux-arm64` on a published arm64 base; and `project wrap`
brings someone else's repository into a project.

## Scope And Owner Decisions

- **Cut now**, decided 2026-11-07 by the owner in the maintenance session:
  a minor release of what `main` carries. The release branch starts at
  `31e8fec71f2901f5e2e9893d35a6481215471ba9`, the merge of PR #7; version
  0.3.1 at `bf833849`, the branch's first commit, by `nox -s bump -- 0.3.1`.
  `main` reopens at `0.3.2.dev0` by a pull request at the cut.
- **In scope:** everything under *What `main` Carried At The Cut*. The
  remaining wrapped-projects slices stay on `main`'s side unless the owner
  directs a slice into the release during the cycle, as in 0.3.0.
- **Rulings the owner is asked for before candidate 0:**
  1. *Executables for the Mac.* The candidate workflow builds and publishes
     the Linux x86-64 executable alone. The macOS guide says so and tells a
     Mac user to build three executables from a published commit. PR #338
     left to the owner whether a macOS executable, an arm64 executable or
     both are published. Publishing either is a change to
     `.github/workflows/release-pex.yml` and to the final-tag checks, a
     slice of the cycle if ruled in; otherwise 0.3.1 ships the Mac as the
     guide describes it, experimental and built from source.
  2. *The compatibility feed's home.* The launcher reads
     `https://devcapsule.mycodespace.ai/status/compatibility-v1.json` since
     PR #3, and the path does not exist. The maintenance status of
     2026-11-05 names two ways and asks for the ruling before the first
     0.3.1 candidate. Until one exists a 0.3.1 launcher falls back to its
     cache, then to its built-in snapshot, on every check, and starts
     regardless.
  3. *Eclipse on amd64.* Found by PR #338 and confirmed at the cut: the two
     libsoup package URLs in the amd64 Eclipse closure return 404 since
     Ubuntu replaced the build, so Eclipse cannot be acquired from scratch
     on amd64. The bug record is in the table; the owner ruled the repin
     the cycle's first slice on 2026-11-07, and it is done on the release
     branch, so candidate 1 carries it.
- **Out of 0.3.1 unless the owner pulls them in:** the 0.3.1 preparation
  queue of 2026-10-31 in the maintenance status: release-independent test
  fixtures; parts A and B of the October 25 documentation order; C17, the
  generic project-operation instructions, with `workflow-improvements`; the
  nine September 28 documentation proposals, item by item; image and cache
  cleanup. The seventeen tests expected to fail inside a capsule, their
  repair queued on 2026-11-04 and diagnosed on 2026-11-06, are test work on
  `main`, not release work.
- **Stopping points where the owner is consulted:** before each candidate
  tag; before the final tag.
- Routine release-fix propagation to `main` follows the runbook's *Release
  Fixes And Main* under the owner's standing direction of 2026-09-22.

## Found At The Cut

- **Three integration tests failed on `main` since PR #3.** `scripts/build-pex.sh`
  embeds the compatibility snapshot from `component-status/policy-v1.json`
  and refuses to build without it; the fixture repository of
  `test_clean_revision_build_and_tag_derived_version` copied everything
  but the policy. The integration tests left the build gate in PR #2 and
  the candidate workflow, which runs them on the hosted runner, had not
  run since, so nobody saw it: candidate 0 would have failed its gate. The
  first integration run of the cycle, rule 9's, found it; fixed on the
  release branch at `7570b14e`, and the test moved at `3aa21dc0` to a
  module of its own, `test_build_pex.py`, when the conventions gate refused
  the change to a legacy file; test-only changes that reach `main` with
  the pre-candidate merge (*Release Fixes And Main*, ancestry).
- **Eclipse cannot be acquired from scratch on amd64**, the bug record in
  the table, confirmed against the archive; repinned on the release branch
  the same day as the cycle's first slice.

## What `main` Carried At The Cut

Integrated between `v0.3.0` (final 2026-10-31, source `475427da`) and the
cut commit, by the merges on `main`'s first parent:

- The macOS launcher and `linux-arm64` capsules (#338, #340, from the
  `macos-launcher` and `linux-arm64` workstreams): the host's differences
  as properties of `HostOs`; one lock per capsule platform; `init`'s
  platform question and `--platform`; the arm64 base published as
  `mycodespaceai/devcapsule-base:linux-arm64-recipe-11-20261104` and
  pinned; the macOS guide.
- Wrapped projects, slice 1 (#333, reviewed by #334): `project wrap`, the
  `[sources."<path>"]` table of schema 2, the guidance files, the guide
  *Someone else's repository*.
- The compatibility feed read from the website's domain, with the
  command-line override, the cache in the cache home and the snapshot
  built into the launcher (#3).
- The repository's move to `mycodespace-ai/devcapsule` (#1), the website
  and samples decisions (#4, #5, #6): releases are published under the
  organization from this version on.
- Testing: the unit-test conventions and the gate (#335), coverage numbers
  in pull requests (#336), the base-consent test from constructed locks
  (#337), seventeen capsule-reading tests expected to fail (#341), the
  integration tests out of the build gate (#2), the isolation criterion,
  the integration and end-to-end definitions and Release Policy rules 9
  and 10 (#7). None of these changes the product.

## Agent Freshness Review

Owner direction of 2026-09-27, applied to every release: try to upgrade the
supported agent CLIs to their current generally available versions. The
vendor pointers were read at the cut on 2026-11-07 (`0.167.0`, `2.1.319`,
`1.5.3`) and rechecked on 2026-11-09 (`0.167.0`, `2.1.321`, `1.5.3`).

| Agent | Prior pin | Vendor current (2026-11-09) | Source consulted | Disposition |
|---|---|---|---|---|
| Codex | 0.166.0 | 0.167.0 | [OpenAI npm latest](https://registry.npmjs.org/@openai/codex/latest) | **adopted (`embedded-33`)**: `linux-amd64` and `linux-arm64` tarballs verified against npm SHA-512 SRI; offline npm materialization, `--version` (`codex-cli 0.167.0`), `--help`, and seeded `config.toml` smoke passed on `mycodespaceai/devcapsule-base:v0.3.0-base-20261031` |
| Claude Code | 2.1.314 | 2.1.321 | [Vendor latest channel](https://downloads.claude.ai/claude-code-releases/latest) | **adopted (`embedded-33`)**: `linux-x64` and `linux-arm64` binaries verified against `2.1.321/manifest.json` SHA-256 checksums; offline `--version` (`2.1.321 (Claude Code)`), `--help`, and seeded `settings.json` smoke passed on `mycodespaceai/devcapsule-base:v0.3.0-base-20261031` |
| Antigravity CLI | 1.4.12 | 1.5.3 | [Vendor Linux amd64 manifest](https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json) | **held at `1.4.12` (pending owner ruling)**: `1.5.3` alters four literal `"1.4.12"` expectations in `1,396`-line legacy `tests/test_project_init.py` (tracked under [`2026-10-31-release-dependent-test-fixtures.md`](../../bugs/devcapsule/2026-10-31-release-dependent-test-fixtures.md)), which *Unit Tests* rule 5 requires refurbishing whole |

Every vendor is ahead of the pin. The attempt follows the 0.3.0 method on
a slice branch for a pull request into the release branch: artifacts
checked against the vendors' integrity values, laid out and started on the
pinned base, the matrix advanced with the old pins kept, the golden locks
regenerated, this repository's lock regenerated by the owner's command on
the host. Since 0.3.1 has two capsule platforms, the attempt covers the
`linux-arm64` pins as well. The pointers are rechecked before final
acceptance; a version that appears meanwhile gets an adopt-or-hold
decision here, never a silent replacement.

## Preparation And Publication

- Release branch `release-0.3.1` starts at the preparation baseline
  `31e8fec71f2901f5e2e9893d35a6481215471ba9`, `main` at the merge of PR
  #7, selected by the driver: nothing of maintenance was unmerged, and the
  owner's decision of the day is recorded beside the branch. Version 0.3.1
  at `bf833849`, the branch's first commit.
- [x] Cut, version, the content contract satisfied on the branch, the
  decision record, this overview, the bug table and the changelog, the
  registry row and the status file.
- [x] Full gate on the release branch at the cut, `nox -s build` on
  `c449342f` from the scratchpad worktree: distribution version 0.3.1,
  syntax, mypy clean over 323 files, 2825 unit tests passed, 41
  deselected, 14 xfailed, 7 xpassed, the conventions gate without a
  breach, the CLI smoke of every command's help, the local PEX built and
  smoked, the web console session mypy clean over 9 files with its tests
  passed, the content contract at 249 pages with devel reading 0.3.1:
  passed in four minutes.
- [x] Integration tests run before candidate 0 and recorded in
  [`test-runs.json`](test-runs.json) beside this file, Release Policy
  rule 9: `nox -s integration`, 26 passed and 1 skipped by design on
  `3aa21dc0`. The rule is new
  with PR #7 and the gate does not read the record yet; the record is kept
  by hand until the check exists. The first run found three of the
  eighteen failing on `main` since PR #3, see *Found at the cut*.
- [x] `main` reopened at `0.3.2.dev0` by PR #8, merged by the owner at `41289b9e`.
- [x] The release branch merged into `main` through the throwaway copy
  `4PR-1-release-0.3.1`, PR #9, merged by the owner at `f30903c3`;
  `v0.3.1-rc0` tagged on the release tip on the owner's word of
  2026-11-07; the three assets downloaded, checksum and version verified.
  See *Candidates*.
- [x] The cycle's slices through candidate 2, each merged to `main` before the
  next candidate tag; all three candidate-gating bug records closed on
  candidates. Slices 1 and 2 reached `main` through PR #14 (`8c5a4723`) and
  shipped in candidate 1 (`v0.3.1-rc1`, closing the Eclipse libsoup bug, PR #10,
  and adding the web console's Files page, PR #12 / PR #13). Slices 3 to 6 —
  whole-file legacy test retirement and 4-file refurbishment (PR #18 / PR #19,
  `b84b06e9`), launcher-delivered `devcapsule_webconsole` and source-or-opt-in
  self-hosting override (`D-0017`, PR #16 / PR #17, `f2bae5cb`), Codex npm
  abbreviated metadata (PR #20, `eb8ff8cf`), and Codex `0.167.0` + Claude Code
  `2.1.321` freshness (`embedded-33`, PR #21, `3ea05e68`) — reached `main`
  through PR #22 (`aabace3c`) and shipped in candidate 2 (`v0.3.1-rc2`, closing
  both the web-console delivery bug and the Codex npm cap bug).
- [ ] The gates before the final tag: the blocking record of 2026-11-10,
  [unit tests read the capsule's mounted launcher settings](../../bugs/devcapsule/2026-11-10-unit-tests-read-the-capsules-mounted-launcher-settings.md),
  closed; any slice from the remaining owner
  rulings; the documentation describing the accepted candidate; `notes.md` with
  the *End-to-end tests run* section, Release Policy rule 10;
  `release-docs.py promote 0.3.1` and `docs-0.3.1`; the acceptance record; the
  final tag; delivery verified.

## Candidates

### RC2 — tagged 2026-11-10

- Tag `v0.3.1-rc2` on `be0140ca19b426cc9eea4dafa1a8958826d20c56`, the release
  branch's tip at the pre-candidate merge (PR #22 from the throwaway copy
  `4PR-3-release-0.3.1`, merged by the owner at
  `aabace3cce7e3560e302e1cc04ee2b0987e08847`). Carries whole-file legacy test
  retirement and 4-file refurbishment (PR #18, reviewed by PR #19),
  launcher-delivered `devcapsule_webconsole` and source-only/opt-in self-hosting
  override (`D-0017`, PR #16, reviewed by PR #17), Codex npm abbreviated
  metadata (`Accept: application/vnd.npm.install-v1+json` on `NpmChannel.check()`,
  PR #20), and Codex `0.167.0` + Claude Code `2.1.321` freshness across
  `linux-amd64` and `linux-arm64` (`embedded-33`, PR #21).
- Pre-candidate integration run on `3ea05e68` (`40` passed, `3` skipped in
  `39.65s`, recorded in [`test-runs.json`](test-runs.json)); candidate gate
  before the push: method `mainline`, no unintegrated commits, version
  `0.3.1rc2`.
- Backend run [42734994462](https://github.com/mycodespace-ai/devcapsule/actions/runs/42734994462)
  passed in `5m57s`: `2929` unit tests passed, `66` deselected, `1` xfailed,
  `1` xpassed on the hosted runner; packaging integration `40` passed, `3`
  skipped in `54.14s` against the built PEX (recorded in
  [`test-runs.json`](test-runs.json)). The
  [prerelease](https://github.com/mycodespace-ai/devcapsule/releases/tag/v0.3.1-rc2)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.1-rc2`:
  the checksum file verifies `devcapsule.pex`, SHA-256
  `2c3ace0f2f5b94ef4dfce9f568a09cf00ce045964fbbf6bf90ff06b1fe54a5d4`; the
  manifest records tag `v0.3.1-rc2`, branch `release-0.3.1`, source revision
  `be0140ca19b426cc9eea4dafa1a8958826d20c56`, `mainline` disposition, CPython
  `3.12.14` and recipe-11 `linux-amd64` base `d7047ced…`; `devcapsule.pex
  version --json` from an empty directory reports `0.3.1rc2`, build
  `v0.3.1-rc2`, at `be0140ca…`.
- **Codex npm metadata bug and `embedded-33` agent pins verified**, closing
  [`2026-11-08-codex-npm-metadata-exceeds-16-mib.md`](../../bugs/devcapsule/2026-11-08-codex-npm-metadata-exceeds-16-mib.md):
  `origin/component-status` (`0bc31c64`, generated `2026-11-10T00:58:45Z` from
  `aabace3c`) reports `codex / codex-v1` with `"result": "ok"`,
  `"consecutive_failures": 0`, and `"candidates": ["0.167.0"]` (resetting 45
  consecutive `inconclusive` runs since `2026-10-01`). With the downloaded
  `v0.3.1-rc2` executable and an empty `DEVCAPSULE_CONFIG_HOME`, `project init
  --ide python-ide --require python --require codex-agent --require
  claude-code-agent` on a fresh repository locked `codex 0.167.0` and
  `claude-code 2.1.321` (`embedded-33`), and `project versions check` succeeded
  live (`codex 0.167.0: available`, `claude-code 2.1.321: available`).
- **Launcher-delivered web console and self-hosting override verified**, closing
  [`2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md`](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md):
  extracting `_webconsole_bundle.zip` from the downloaded `v0.3.1-rc2`
  `devcapsule.pex` and serving it on the pre-PR-#12 base interpreter
  (`/opt/devcapsule-webconsole/venv/bin/python -m devcapsule_webconsole`)
  against that non-DevCapsule project answered `200 OK` on `GET /files`,
  `GET /api/project/tree`, and `GET /api/project/raw?path=hello.txt`, and `307`
  (`Location: /files`) on `GET /filetree`; `is_built_distribution()` inside the
  downloaded PEX returned `True`, leaving `console_development_source()` empty
  by default on a DevCapsule checkout and honoring
  `DEVCAPSULE_DEV_WEBCONSOLE=1`.
- Not in rc2: a macOS or arm64 published executable and the compatibility
  feed's website path, both waiting for the owner's ruling; Antigravity CLI
  held at `1.4.12` (vendor `1.5.3` blocked on whole-file refurbishment of
  legacy `tests/test_project_init.py`, surfaced to the owner).
- Next: the owner's rulings; end-to-end test run on the accepted candidate
  (*Release Policy* rule 10); the documentation round, `notes.md`,
  `release-docs.py promote 0.3.1`, and the final `v0.3.1` tag.

### RC1 — tagged 2026-11-08

- Tag `v0.3.1-rc1` on `accdec5bb36626875b0564afbcbf20f67f9d961b`, the release
  branch's tip at the pre-candidate merge (PR #14 from the throwaway copy
  `4PR-2-release-0.3.1`, merged by the owner at `8c5a4723`). Carries slice 1,
  the Eclipse amd64 libsoup repin (PR #10), and slice 2, the web console's
  Files page (PR #12 with its review PR #13).
- Candidate gate from the release worktree before the push: method
  `mainline`, no unintegrated commits, version `0.3.1rc1`.
- Backend run [42436425955](https://github.com/mycodespace-ai/devcapsule/actions/runs/42436425955)
  passed: 2844 unit tests passed, 50 deselected, 1 xfailed, 1 xpassed on
  the hosted runner; packaging integration 26 passed, 1 skipped against the
  built PEX. The [prerelease](https://github.com/mycodespace-ai/devcapsule/releases/tag/v0.3.1-rc1)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.1-rc1`:
  the checksum file verifies the executable, SHA-256 `711d239c0809f892…`;
  the manifest records the tag, the branch, the source revision, the
  `mainline` disposition, CPython 3.12.14 and the recipe-11 linux x86-64
  base `d7047ced…`; `devcapsule version --json` from an empty directory
  reports `0.3.1rc1`, build `v0.3.1-rc1`, at `accdec5b…`.
- **Eclipse acquired from scratch on amd64**, closing the libsoup bug: with
  the downloaded executable and an empty configuration home
  (`DEVCAPSULE_CONFIG_HOME` on a fresh directory), `project init --ide
  eclipse-ide --require java --platform linux-amd64` on a scratch
  repository, then `images build --type environment --network host`: the
  closure downloaded in full, the two libsoup files landed in the home's
  artifact cache under their hashes (`c2acdf20…`, 292,272 bytes;
  `89f066fe…`, 12,882 bytes), the image build set up
  `libsoup-3.0-0:amd64 (3.4.4-5ubuntu0.10)` and WebKitGTK, and the
  environment image `devcapsule-local-eclipse:39671f01…` was built in
  13 minutes 41 seconds on the maintenance capsule's host daemon with
  the base already present. No container was launched. Log kept at
  `/home/devcapsule/.cache/devcapsule-releases/acceptance-rc1/acceptance.log`.
- **Blocking finding on `v0.3.1-rc1` (2026-11-08):** `/files`, `/filetree`,
  and `/api/project/tree` return `404` in capsules launched by `v0.3.1-rc1`.
  `devcapsule.pex` does not carry `devcapsule-webconsole/`, both pinned
  recipe-11 bases (`d7047ced…` and `7d322680…`) predate PR #12, and
  `console_development_source()` unconditionally overrides the console on
  DevCapsule checkouts. Filed as
  [blocking for 0.3.1](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md);
  fixed via PRs #18/#16 and closed on candidate 2.
- Not in rc1: a macOS or arm64 executable and the compatibility feed's
  home, both waiting for the owner's ruling; the agent and IDE freshness
  upgrade; the Files-page proposals left by the review.
- Next: the rulings; the freshness slice; the documentation round, the
  notes and the promotion before the last candidate.

### RC0 — tagged 2026-11-07

- Tag `v0.3.1-rc0` on `8bcee1d04ce80e29853692e745476de4d8862386`, the release
  branch's tip at the pre-candidate merge (PR #9 from the throwaway copy
  `4PR-1-release-0.3.1`, merged by the owner at `f30903c3`, after PR #8
  reopened `main` at `0.3.2.dev0`). The copy carried one commit keeping
  `main`'s version files, as the 0.3.0 copies did; both merge orders gave
  the same tree.
- Candidate gate from the release worktree before the push: method
  `mainline`, no unintegrated commits, version `0.3.1rc0`.
- Backend run [42424847709](https://github.com/mycodespace-ai/devcapsule/actions/runs/42424847709)
  passed: 2844 unit tests passed, 50 deselected, 1 xfailed, 1 xpassed on
  the hosted runner; packaging integration 26 passed, 1 skipped against the
  built PEX. The [prerelease](https://github.com/mycodespace-ai/devcapsule/releases/tag/v0.3.1-rc0)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.1-rc0`:
  the checksum file verifies the executable, SHA-256
  `8c29a15e2fa4ecf61bd67c59ba9c0421a2f662a8f50a9d89e7625eab1d269925`; the
  manifest records the tag, the branch, the source revision, the
  `mainline` disposition, the embedded CPython 3.12.14 and, as its base
  reference, the recipe-11 linux x86-64 base `d7047ced…`; `devcapsule
  version --json` from an empty directory reports `0.3.1rc0`, build
  `v0.3.1-rc0`, at `8bcee1d0…` under the organization's repository URL.
- The hosted runner reports 1 xfailed where the maintenance capsule
  reports 14: the tests expected to fail depend on the environment. Noted
  for the repair slices queued on `main`; not a candidate defect.
- Not in rc0: the Eclipse amd64 libsoup repin (bug record of 2026-11-07),
  the agent and IDE freshness upgrade, a macOS or arm64 executable, the
  compatibility feed's home on the website. Each waits for the owner's
  ruling listed under *Scope And Owner Decisions*; each that is ruled in
  is a slice merged to `main` before the next candidate tag.
- Next: the local acceptance proofs on the downloaded executable where
  the candidate changed behavior (none yet beyond the cut's content), the
  rulings, the slices, candidate 1.

## Release Notes Preparation

Write `notes.md` beside this file before the final tag: plain Markdown for
adopters, what changed for them, compatibility exceptions with remedies,
the tested agent versions and holdbacks from the freshness review, the
deferred items, and the end-to-end tests run on the accepted candidate with
the argument for the subset, rendered from the test-run record once the
renderer exists and written by hand until then. The changelog is its
source.
