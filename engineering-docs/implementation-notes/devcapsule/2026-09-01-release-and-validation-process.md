# Releasing A New DevCapsule Version

This is the canonical operator guide for releasing DevCapsule. On 2026-09-11,
the product owner adopted the successful v0.2.11 process as the process for
new versions. Project management owns this release-process decision and its
documentation; completing it does not depend on delegation to another
workstream. The guide was originally recorded on 2026-09-01.

The normal sequence is **prepare and cut → account for fixes on main → publish
an RC → validate the downloaded RC → record acceptance → integrate the acceptance
record → tag the accepted source → verify the final release**. Repeat the fix
and candidate steps as needed. An ordinary CLI release reuses its pinned base.
The workflow builds and publishes artifacts; the operator supplies acceptance.
GitHub PRs and workflow operations are owner-operated through the UI, as stated
in `WORKFLOW-LOCAL.md`; agents prepare changes and push through ordinary Git.

Owner clarification, 2026-09-22: release-blocking bugs must be addressed on main
as well as on the release line, while main stays open to unrelated development.
Merge when suitable; otherwise use cherry-picking, an adapted fix, or evidence
that main is unaffected. *Release Fixes And Main* below defines that judgment.
This supersedes the generic workflow's blanket merge-only restriction through
the recorded local exception, pending the generic definition's correction.

Requirements: `R-PRODUCT-006`.

## Release Working Documents

Maintain `engineering-docs/releases/vX.Y.Z/README.md` as the release overview,
checklist and candidate history, with `bugs.md` for bug dispositions and next
actions. Update these files as work proceeds; chat should highlight changes
and decisions rather than repeatedly reproduce the inventory. Add further
evidence files only when needed. See the [0.2.14 working directory](../../releases/v0.2.14/README.md).

Linked bug records remain authoritative for status, severity, target, ownership
and technical evidence; keep their working-table summaries reconciled. The
driving workstream maintains these release documents, while its status file
links here for resumption. Retain them after release. The existing sibling
`vX.Y.Z.json` remains the machine-checked acceptance record, created only when
an exact candidate is accepted; the working directory does not replace it.

## Operator Checklist

The commands below use v0.2.11 as the worked example. For a new release,
substitute its version and candidate number; never recreate or move an existing
published tag. Run Git commands from the repository root. Python commands use
the checkout-local environment described in the [developer environment](../../development/developer-environment.md).

1. **Prepare and cut.** The owner selects version, scope and the cut. The
   workstream whose deliverable is the headline drives; maintenance drives a
   patch to an already released version; project-management settles an unclear
   driver. Integrate the driving workstream's prepared slice into main, then
   create `release-X.Y.Z` at that merge commit and record its full SHA as the
   preparation baseline. A maintenance patch may instead start at the prior
   final tag. The release branch becomes the driving workstream's selection;
   its former working branch closes for modification. Update its registry row
   to `active; releasing X.Y.Z` with the release branch association. Set or
   confirm the source version no later than the first release-branch commit,
   and run `.venv/bin/python -m nox -s build` from `devcapsule-src`. Then
   reopen `main` with the next development version by a pull request, so
   `main` is ahead of every candidate (`WORKFLOW-LOCAL.md`, *Version
   Scheme*; owner decision of 2026-10-18). Run the *Agent Freshness Review*
   below and record its table in the release overview.
2. **Account for main and publish the first candidate.** Follow *Release Fixes
   And Main* and the current candidate gate below. Push the release branch;
   merge it into `main` by a pull request from a throwaway copy,
   `4PR-NNN-release-X.Y.Z` created at the release branch's tip, since the
   repository deletes a pull request's branch on merge (`WORKFLOW-LOCAL.md`,
   *Release Policy* 8); verify the applicable main disposition before creating
   an immutable `vX.Y.Z-rc0` tag. Wait for **Publish DevCapsule PEX** to pass
   and publish a non-draft GitHub prerelease with all three assets: the PEX,
   its checksum file, and `release-manifest.json`.
3. **Validate the published candidate.** Download and checksum-check its PEX;
   use that executable for smoke/E2E testing. The [published-executable smoke
   commands](../../../devcapsule-src/README.md#end-user-artifact) are documented
   in the CLI README. Use the full-base `--build-base` mode when validating
   the base recipe; ordinary CLI releases need not rebuild or publish a base.
   Record actual evidence for changed GUI, login, and provider behavior.
   Fixture tests cannot supply that acceptance. Before accepting a candidate,
   satisfy *Documentation Is Part Of The Release* below: the release branch's
   `docs/` describes this version and passes the website's build check.
   Before the last candidate, write `engineering-docs/releases/vX.Y.Z/notes.md`
   and run `devcapsule-src/.venv/bin/python devcapsule-src/scripts/release-docs.py promote X.Y.Z`
   on the release branch. Read the printed lifecycle moves. Use repeatable
   `--hold VERSION` only for an owner-authorized status exception.
   Commit the notes and promotion, then push the documentation branch with
   `git push origin HEAD:refs/heads/docs-X.Y.Z`. The helper changes no Git ref.
   Merge the release branch into `main` before tagging that candidate.
   This places the promoted manifest and notes in the exact source that
   can later be accepted and tagged as final.
   Make release-blocking fixes on
   the release branch, account for the bug on main using the appropriate method,
   and publish the next RC number without changing earlier tags. Repeat until
   an exact candidate is accepted; do not add unrelated development to the release.
4. **Record acceptance.** Run `prepare-promotion.py` as shown below with the
   accepted RC, preparation baseline, accepting operator, and evidence. Review
   the generated record. Recheck the freshness review's vendor pointers; a
   version that appeared meanwhile gets an adopt-or-hold decision, never a
   silent replacement of the accepted candidate. For v0.2.11 the accepted candidate was **RC3**, not
   RC0 or a later workstream tip. Commit the record after the accepted candidate
   on the release branch, leaving the accepted candidate's source unchanged.
5. **Integrate acceptance.** Deliver the acceptance record through the normal
   PR process and verify it on remote main. If a whole-branch merge is unsuitable,
   deliver the record separately along with the reviewed main dispositions;
   do not carry incompatible release code into main merely to deliver its record.
   Use `ancestry` only when it holds, and `reviewed` for an evidenced alternative.
   A genuinely outstanding main fix needs explicit scope and follow-up; a failed
   merge alone does not authorize leaving the bug in main. Do not rebase the
   tested candidate to make it match main.
6. **Publish the final tag at the accepted candidate commit.** Use the final
   tagging commands below. As the last check before creating the tag, run
   `devcapsule-src/.venv/bin/python devcapsule-src/scripts/release-docs.py check X.Y.Z`
   against the accepted candidate's checkout. The final-tag job repeats the
   check and compares the documentation branch's `docs/` tree with the tag.
   A failure stops publication. Wait for the final backend run to finish.
   It rebuilds version metadata, checks frozen inputs against the RC, and
   repeats the automated gates. It uses the release notes as the GitHub body
   and dispatches the test website after publication. A pushed tag alone
   does not mean a successful release.
7. **Verify delivery.** Confirm the GitHub release is non-draft and is a final
   release, with all three assets. Download them into a fresh directory, check
   `sha256sum --check devcapsule.pex.sha256`, make the PEX executable, and run
   `./devcapsule.pex version --json`. Check its version, build mnemonic, and
   source revision against the final tag and acceptance record. Record the
   release URL, successful Actions run, and verification result in the owning
   workstream's handoff. Retain the release branch and candidate tags. After
   final publication the release branch closes; resume ordinary work on a fresh
   `ws-<name>/...` branch from main or conclude the driving workstream; `main`
   has carried the next development version since the cut.
   Verify the dispatched test website. The owner reads it and promotes its
   candidate to production in the website repository. The manifest already
   reached `main` through the pre-final merge. Both website modes check
   published downloads, so a build before the final release fails harmlessly.

## Documentation Is Part Of The Release

Owner grant of 2026-09-28, exercised by `project-management`, after 0.2.15
shipped while the website still documented v0.2.12: a release is not complete
until the documentation describes it and the site serves it. Three
obligations of the driving workstream, in the order the checklist meets them:

1. **Before the final tag, the release's `docs/` is true for the version.**
   On the release branch, every guide describes this version's behaviour,
   names no version literally (the contract's tokens render it), and passes
   the website's build check at the pinned consumer revision. Corrections
   discovered after the tag go on the `docs-<version>` ref that
   `WORKFLOW-LOCAL.md` declares, never on the closed release branch.
2. **Before the final tag, the release notes exist** as
   `engineering-docs/releases/vX.Y.Z/notes.md` on the release branch: plain
   Markdown for adopters, what changed for them, compatibility exceptions
   with remedies, tested agent versions and holdbacks from the freshness
   review, deferred items. `release-docs.py check X.Y.Z` refuses missing or
   empty notes and `<...>` placeholders. The final job passes the output of
   `release-docs.py notes X.Y.Z`, without front matter, to `--notes-file`.
   Candidates retain GitHub's generated notes.
3. **Before the final tag, promote the manifest; after publication, build
   the site.** Run `release-docs.py promote X.Y.Z` on the release branch.
   It makes the version `current` and `supported`, demotes the previous
   supported version to `deprecated`, and demotes deprecated versions to
   `unsupported`. It sets `devel`'s `source-version` to the promoted release.
   Commit it with the notes before the last candidate. Push `docs-X.Y.Z`
   at that commit, then merge to `main` before the candidate tag.
   The final-tag job checks the manifest, notes, and documentation ref
   before publication. After publication, it dispatches this repository's
   Website workflow on `main`, in `production` mode, for the test domain
   `https://test-devcapsule.mycodespace.ai` and base path `/`.
   Both website modes run `release-docs.py published`. Every listed
   non-development version must have a non-draft final GitHub release
   with `devcapsule.pex`. The owner reads the test deployment and promotes
   its candidate in the website repository.

The contract these follow is [the content–website contract, version 1](../../specifications/product/content-website-contract.md);
the ideal structure of the documentation is in
[the 2026-09-28 visitor-content work order](../../work-orders/2026-09-28-visitor-content-and-producer-migration.md).

## Agent Freshness Review

Owner direction of 2026-09-27, first applied in 0.2.15: every release tries
to upgrade the supported AI agent CLIs to their then-current generally
available versions, since newer clients reach newer models.

For every release, review each supported agent CLI, today Codex, Claude Code
and Antigravity, against its vendor's current generally available release,
not beta or nightly channels. Record in the release overview a table of the
date, the vendor source consulted, the current pin, the candidate and the
disposition. Attempt the upgrades: acquire the exact artifacts through the
trusted component mechanisms, verify checksums and platform compatibility,
and validate configuration defaults, an ordinary tool action and state
persistence on the selected versions before accepting new pins. Record a
concrete reason and a follow-up for every holdback and for every feed that
could not be checked. Keep checkout-selected version sets and acquisition
consent intact; an upgrade grants nothing new.

Recheck the vendor pointers before final acceptance. A version that appears
during acceptance gets an adopt-or-hold decision recorded in the overview;
adopting it means a new candidate and the relevant validation again, never a
pin changed under an accepted candidate. The release notes carry the tested
versions and the holdbacks. A newer CLI alone does not establish that an
account can use a particular model; say what was verified.

## Release Fixes And Main

During stabilization, fix bugs that block the selected release. For each fix,
inspect current main and use judgment in this order:

1. **Merge when suitable.** Prefer merging the release branch into main when
   the result preserves main's current behavior and the correction. Resolve
   ordinary conflicts and validate the result; a textual conflict alone does
   not make a merge unsuitable. Never hold unrelated workstreams out of main
   merely to keep this merge easy.
2. **Cherry-pick when a selective transfer fits.** Transfer the relevant fix
   through an ordinary mainline PR when a whole-branch merge is inappropriate.
   Retain its origin, for example with `git cherry-pick -x`, and test it on main.
3. **Adapt the reasoning when the implementation differs.** If main's APIs,
   architecture or dependencies have changed, correct the same failure in the
   implementation main actually uses. Link the release fix and the main fix
   in the bug record, with the validation for each. Textual patch identity is
   neither necessary nor sufficient to establish this result.
4. **Establish that main is unaffected when that is the case.** Identify the
   failure's necessary conditions and explain why they cannot occur at the
   inspected main revision, supported by relevant code reasoning and, where
   useful, a focused regression check. An already-delivered fix may supply
   that evidence. A failed cherry-pick or passing unrelated tests do not.

Record the release revision, main revision and disposition with the bug. Keep
the evidence proportional: enough for another engineer to assess the conclusion,
without a separate approval round for the method. This is the owner's standing
direction. Ancestry records history, not whether conflict resolution or a later
revert preserved a fix. Review the behavior on each applicable line.

The same judgment applies when a release-relevant fix is first discovered on
main: selectively transfer or adapt it onto the release line, validating there,
without importing unrelated mainline work. Never rebase a published release or
move an existing candidate tag. Main's work and the release's stabilization can
proceed concurrently.

## The Successful v0.2.11 Reference

| Fact | Accepted value |
|---|---|
| Release branch | `release-0.2.11` |
| Candidate | `v0.2.11-rc3` |
| Candidate and final source commit | `94e798f1d1a7aaab93ae3e47d9636471448a8e66` |
| Preparation baseline | `3f028eeb97d7de6bce5b9f2ac2faf0a1b940cb61` |
| Integration evidence | `ancestry` |
| Final tag | `v0.2.11` |

The [committed acceptance record](../../releases/v0.2.11.json) identifies the
candidate checksum and the exact scope of acceptance. The [candidate backend
run](https://github.com/ccozianu/devcapsule/actions/runs/34333414510) and
[final release](https://github.com/ccozianu/devcapsule/releases/tag/v0.2.11)
are the corresponding published evidence. The record covers the release/build
change and does not claim fresh GUI/login or provider acceptance. Preserve that
distinction when using it as a template for a release with different changes.

## Release Identity And Trigger

Prepare a release on `release-MAJOR.MINOR.PATCH`, selected by the driving
workstream through its registry row. Start from the integrated cut commit, or
the prior final tag for a maintenance patch. These commands illustrate the cut;
use the version and full baseline SHA selected by the owner:

```text
git switch -c release-0.2.11 FULL_PREPARATION_BASE_SHA
```

Set or confirm the version, update the driving workstream's records, validate,
commit and push the release branch. Account for the mainline result using
*Release Fixes And Main* before tagging. Where merging is appropriate, the owner
merges the release PR in the GitHub UI and the agent fetches main to verify it.
Then tag the exact prepared commit on the release branch, not main's merge tip:

```text
git tag -a v0.2.11-rc0 -m 'DevCapsule 0.2.11 candidate 0'
git push --atomic origin release-0.2.11 v0.2.11-rc0
```

Use a new commit and RC number for fixes, advance the release branch, and keep
previous tags unchanged. `.github/workflows/release-pex.yml` requires the tag's
commit to belong to the matching release branch. Main stays open; do not rebase
tested release source onto it.

**Current candidate gate and its limits.** The 2026-09-22 decision changes the
allowed integration methods; this guide retains the existing timing of resolving
the main disposition before each candidate. `scripts/release-protocol.py` accepts
commits reachable from main or patch-equivalent cherry-picks. Its check ignores
merge commits and cannot establish semantic correctness, recognize an adapted
implementation, or prove that a bug does not affect main. Human/agent review
supplies those judgments; a green ancestry or patch check does not replace them.

For an evidenced main disposition that this check cannot recognize, use its
existing record at `engineering-docs/releases/<tag>-integration-exception.json`
on the release branch before tagging. The schema requires `schema-version: 1`,
the `tag`, `authorized-by`, `rationale`, `forward-port-owner` and `follow-up`.
For a routine adaptation or unaffected-main case, cite the owner's standing
2026-09-22 direction in `authorized-by`, the exact main revision and bug evidence
in `rationale`, and the responsible workstream in `forward-port-owner`. State
the completed main disposition in `follow-up`, including when no further fix is
needed. The field names are the existing gate's compatibility format, not a
requirement to invent unfinished work or ask the owner to approve the method
again. Account for release-only metadata as well as code changes.

A genuinely unresolved main bug is different: the normal propagation obligation
is not satisfied. Record the blocker and obtain an explicit owner decision before
deferring it; merge difficulty alone is not that authority. The gate embeds
`mainline` or the `exception` record and unmatched commits in the manifest.
The release manifest preserves the captured evidence for retries.

The tag supplies the package version of a *tagged* build. `scripts/build-pex.sh`
stamps package metadata and `_build_info.json` in a temporary directory:
`v0.2.11-rc1` becomes `0.2.11rc1`, and `v0.2.11` becomes `0.2.11`. The source
version in `pyproject.toml` is what everything else reports — local builds
(`v0.2.12-local-…`), source-form runs, `pip show devcapsule` after an editable
install — so it must not lag the release. **Set or confirm the release version
no later than the first release-branch commit**. The owner may have set it
earlier; otherwise use `.venv/bin/python -m nox -s bump -- 0.2.11` for this
worked example. Preserve main's intended development version when accounting
for release metadata there. This retains the purpose of the 2026-09-13 fix
for a baseline that lagged its releases, while accommodating an earlier owner bump.

## Automated Candidate Release

The tag workflow:

1. Verifies the tag/branch identity, runs syntax checks, unit tests and mypy.
2. Recovers exact existing assets, or builds the self-contained PEX.
3. Records source identity, base digests, checksum, build-input hashes, dependency
   distribution fingerprints and the embedded Python fingerprint in the manifest.
4. Runs the integration tests that need no Docker against the built PEX,
   and, since 2026-11-06, requires on `main`, read as the acceptance record
   is read, the record of a run of the integration tests marked `docker`
   on the candidate's source revision, under
   `engineering-docs/releases/vX.Y.Z/test-runs.json` (*Release
   Policy* rule 9 in `WORKFLOW-LOCAL.md`; the workflow's check of the
   record is the maintenance workstream's next slice). Nothing in
   the workflow runs Docker: a hosted runner is an environment nobody
   controls, and a proof that depends on it gates the candidate on the runner
   (owner ruling 2026-09-24, after rc2 of 0.2.14 failed on a Docker build
   that rc1 had passed hours earlier with identical test code).
5. Retains build artifacts, creates a draft release, downloads the assets and
   compares their bytes and checksum with the build.
6. Publishes candidates as GitHub prereleases with Latest disabled.

The Docker-backed proofs moved to local acceptance of the downloaded assets,
run by the driving workstream and recorded in the release overview: the
clean-machine proof (`nox -s pex_clean_machine` with `DEVCAPSULE_PEX_UNDER_TEST`
set to the download), component-cache reuse and launcher delivery
(`pytest -m e2e tests/e2e/test_component_cache.py`), and the runtime session
on each pinned base (`tests/e2e/test_runtime_image.py` with
`DEVCAPSULE_E2E_BASE_IMAGE`). A candidate is not accepted without them; they
are simply run where the environment is known.

An incomplete or inconsistent staged asset set fails explicitly. Recover partial
uploads from the retained Actions artifact. Reruns verify and test the existing
bytes; they never replace published candidate assets or move tags.

## Acceptance And Final Promotion

Since 2026-11-06, *Release Policy* rule 10 in `WORKFLOW-LOCAL.md`: at
least one end-to-end test runs against the downloaded candidate, the run
goes into `engineering-docs/releases/vX.Y.Z/test-runs.json` on `main` with
the candidate's checksum, the release notes carry the section *End-to-end
tests run* rendered from that record, with the argument for a subset when
fewer than all ran, and the final-tag job checks record against notes and
revision. The record's schema, the renderer and the check are the
maintenance workstream's next slice; until they land the reviewer holds
the rule.

Accept an exact candidate's checksum and source commit with smoke/E2E evidence.
Generate the reviewable record on the release branch after candidate acceptance:

```text
cd devcapsule-src
.venv/bin/python scripts/prepare-promotion.py v0.2.11-rc3 \
  --baseline FULL_PREPARATION_BASE_SHA --accepted-by OPERATOR \
  --evidence 'Exact candidate smoke result and Actions run URL'
```

The helper downloads and checksum-verifies the candidate and creates
`engineering-docs/releases/v0.2.11.json`. It does not perform or invent smoke
acceptance. Commit the record and deliver it to main through normal PR review,
using a separate record delivery when merging the whole release branch is
unsuitable. Keep the accepted tag at its tested source commit; the release branch
may advance to carry its acceptance record. Main can contain that record and
unrelated development without changing the candidate.

The record has schema version 1, `tag`, `candidate-tag`, `source-revision`,
`candidate-sha256`, `accepted-by`, a nonempty `evidence` list, and `integration`:

- `ancestry` (helper default): `baseline` identifies the preparation base; the
  accepted candidate must be an ancestor of main, including ordinary merge commits.
- `reviewed`: additionally supply `main-commits` (full SHAs), `reviewed-by`,
  `rationale`, and `covers-release-delta: true`. Every referenced commit must be
  reachable from main. Identify the integrated or examined main commits for
  cherry-picked, adapted, already-fixed or unaffected-main dispositions. The
  reviewed assertion accounts for the entire baseline-to-RC delta, including
  release-only metadata; it does not claim the two trees are identical. Patch
  IDs alone do not establish the behavioral result. Review the generated record
  and select this method instead of the default when ancestry is inappropriate.
- `exception`: additionally supply `authorized-by`, `rationale`,
  `forward-port-owner`, and `follow-up`. This is a scoped authorization in a
  reviewed engineering record, not a boolean bypass. Baseline still applies.

After the record and integration reach main:

```text
git tag -a v0.2.11 'v0.2.11-rc3^{commit}' -m 'DevCapsule 0.2.11'
git push origin v0.2.11
```

The backend checks release-branch membership, reads the record from a captured
main revision, validates the acceptance/integration record's structural conditions,
downloads the published candidate
and verifies its checksum, then builds final-version bytes from exactly the same
source SHA. It compares base, dependency and Python fingerprints with the candidate
and reruns all automated gates before final publication. The final manifest embeds
the record and its main revision. Later main commits do not invalidate retries if
the accepted record remains unchanged. Final publication uses GitHub's legacy
Latest selection, which considers semantic version; candidates explicitly disable
Latest. Tagging is the publication trigger and needs no second approval prompt.

This is source promotion with a final packaging build, not byte-for-byte PEX
promotion: version metadata changes intentionally. A new source fix requires a
new candidate. Neither a broken main nor unrelated main changes require bringing
that work into a maintenance release. The initial implementation automates each
tag's backend and promotion checks; acceptance, normal PR integration, and the
final tag remain operator/agent steps.

## Failed Candidates And Publication Retries

A failed candidate is not promoted. Source or build-input fixes receive a new
commit and RC tag. Published tags and assets remain immutable; do not delete or
replace them to make an old candidate appear successful. If a final release
needs a source fix, prepare a new patch release through the same RC process.

For an infrastructure failure with unchanged source and inputs, rerun the
failed Actions run or dispatch the workflow with its existing `release_tag`.
The backend verifies and reuses staged assets. If an upload stopped partway,
restore the missing original assets from that run's retained Actions artifact;
do not rebuild replacements or overwrite assets. Resume publication only once
the complete set passes verification. The workflow retains build artifacts for
30 days; if the originals cannot be recovered, use a new candidate (or a new
patch version if the final tag was already published).

## Runtime Delivery And Base Lifecycle

The continuing default is [D-0009: One Executable Outside And Inside The
Container](../../decisions/product/d-0009-launcher-delivers-identical-runtime.md),
adopted 2026-09-11: use the corresponding resolved base and install the invoking
CLI itself, unless explicitly overridden by user choice. The base and CLI do
not need matching release numbers. The procedure below describes that default.

Recipe 7 produces a base containing the existing OS libraries and developer
tools, with no DevCapsule PEX or entrypoint added by the recipe. The builder's
source identity remains recorded as provenance; `--pex`, when supplied, selects
provenance metadata, not bytes to embed. Running the packaged builder uses its
own source identity by default. The public-revision checks still apply.

The launcher copies its exact executable PEX into the materialized environment
at `/opt/devcapsule/bin/devcapsule.pex`. Its SHA-256 is part of the formation
descriptor, so a launcher update creates a new local formation and cannot reuse
an image carrying an older runtime. Component installation stages are shared
between those formations. Source-form launches explicitly select a built PEX
through `DEVCAPSULE_RUNTIME_PEX`, or invoke the built artifact directly.

Ordinary CLI releases reuse the catalog's pinned base. In particular, v0.2.11
can use the published v0.2.10 base and replace its inherited runtime in the
derived image. Existing base tags and project locks are unchanged. This avoids
a mandatory Docker Hub publication, digest repin, sample migration, and owner
smoke cycle every time the CLI version advances.

Base maintenance has an independent cadence: update dependencies, build and
validate the base, publish under a fresh immutable name, then review its digest
pin as an ordinary catalog change. A base is not named after every CLI release.
This change does not introduce automatic base publication or choose a new
permanent base-naming scheme. Explicit dependency updates remain necessary for
security fixes; retaining a cached base is not a dependency-update policy.

## Independent Component Contributions

`ContributionComponent` describes installation steps and the paths they export.
The renderer emits a shared baseline stage, an independent stage for each
contribution, and a final image assembled with `COPY --link --from`.

- Base builds isolate Node, Temurin and Maven. Maven explicitly consumes the
  JDK stage for its installation-time verification; it exports only Maven.
- Environment builds isolate the IDE and each ancillary component. All of a
  component's npm packages remain one offline install, preserving the vendor's
  multi-file layout. Environment variables are composed in the final image.
- Component contexts have stable names independent of sibling ordering. A
  different IDE, agent or launcher does not invalidate another installer.
- BuildKit supplies cache identities from the parent image, platform, commands
  and file inputs. A version/recipe/parent change rebuilds the affected stage.
  Reuse lasts while that builder retains its cache; another host or cache
  pruning requires rebuilding. No component images or credentials are published.
- Only declared installation paths are exported. System-package side effects
  cannot be handled by copying an arbitrary installation directory; apt's
  shared baseline remains a complete filesystem layer.

The Docker regression test makes an installer emit a random identifier, builds
two different images with reordered/changed siblings and a changed launcher,
and verifies identical identifiers. A changed recipe must emit a new one.
This tests reuse itself rather than only the generated Dockerfile text.

## Validation And Integration

`nox -s build` remains the local gate. The explicit Docker cache/runtime check
is `python -m pytest --no-cov -m e2e tests/e2e/test_component_cache.py` after
building the local PEX and making `ubuntu:24.04` available; run it, and the
clean-machine and runtime-image checks above, locally against the downloaded
release artifact, since the release workflow no longer runs Docker. Packaging
tests also build a tag whose version differs from the source baseline and
verify source remains clean.

Product-owner GUI/login acceptance for changed component behavior remains part
of development and integration. Fixture tests do not replace that evidence or
convert provisional matrix entries. Publishing an unchanged, accepted
component combination should not repeat the manual release walk.

Docker's behavior is documented in [multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
and [`COPY --link`](https://docs.docker.com/reference/dockerfile/#copy---link).
