# DevCapsule 0.3.1 — Release Work

Updated: 2026-11-07. Stage: **candidate 0 published; cycle slices await the owner's rulings**.
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
     on amd64. The bug record is in the table; the fix is a repin, proposed
     as a slice of the cycle so that candidate 1 carries it.
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
  the table, confirmed against the archive.

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
vendor pointers were read on 2026-11-07 at 12:27 UTC, with the sources the
0.3.0 review used.

| Agent | Current pin | Vendor current | Source consulted | Disposition |
|---|---|---|---|---|
| Codex | 0.166.0 | 0.167.0 | [OpenAI npm latest](https://registry.npmjs.org/@openai/codex/latest) | ahead; the upgrade attempt is a slice of the cycle, on the owner's word |
| Claude Code | 2.1.314 | 2.1.319 | [Vendor latest channel](https://downloads.claude.ai/claude-code-releases/latest) | ahead; 2.1.316 was held at 0.3.0 for this review; same slice |
| Antigravity CLI | 1.4.12 | 1.5.3 | [Vendor Linux amd64 manifest](https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json) | ahead by a minor version; same slice |

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
- [ ] The cycle's slices, each merged to `main` before the next candidate
  tag; the bug records closed on candidates.
- [ ] The gates before the final tag: the documentation describing the
  accepted candidate; `notes.md` with the *End-to-end tests run* section,
  Release Policy rule 10; `release-docs.py promote 0.3.1` and `docs-0.3.1`;
  the acceptance record; the final tag; delivery verified.

## Candidates

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
