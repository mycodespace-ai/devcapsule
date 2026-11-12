# DevCapsule 0.3.0 — Release Work

Updated: 2026-10-31. Stage: **0.3.0 complete: final downloads and production website verified**.
Driver: **maintenance**. Product owner: Costin Cozianu.

[Release notes](notes.md) ·
[Changelog since 0.2.15](changelog.md) ·
[Bug table](bugs.md) ·
[Work order](../../work-orders/2026-10-18-release-0-3-0.md) ·
[Scope and cut decision](../../wip/2026-08-09-project-management/2026-10-18-decision-release-0-3-0-scope-and-cut.md) ·
[Runbook](../../implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md)

Update this file as decisions and evidence arrive. Chat highlights changes
and questions; the bug records remain authoritative for individual status,
ownership and technical evidence; the maintenance status file links here
for resumption.

## Production handoff complete — 2026-10-31

The owner confirmed "All done". Independently checked
[production build-info](https://devcapsule.mycodespace.ai/build-info.json):
current 0.3.0, content 31d44fa4, and the exact reviewed candidate
website-candidate-41188626026-1 with archive digest feb14cb499782540f4d7b051122201650d787bb89cb76c217547702b60ab90ca.
[Verification record](website-verification.json). CLI and production website
delivery are complete. Earlier pending-promotion statements are historical.

## Final delivery — 2026-10-31

[DevCapsule v0.3.0](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0)
was published at 09:25:15 UTC after owner merge of acceptance PR #332 at
main `31d44fa473a86f608110caa53ee38c6aef40a717`.
[Publication run 41188312058](https://github.com/ccozianu/devcapsule/actions/runs/41188312058)
passed all gates, packaged tests, staging and download verification.
The final tag points to accepted RC9 source
`475427da033633ff5ee0e44e09face700630bf36`, not the acceptance PR commit.

The three public assets were downloaded independently into a fresh directory.
Checksum, `0.3.0` version, `v0.3.0` mnemonic, source SHA and embedded acceptance
record all match. Base references and frozen dependencies/Python match RC9.
Final PEX SHA-256:
`f59e05cdbb5ab157641aae5a27f269f963400a650c1ae3db1650e1881a6df714`.
[Verification facts](final-verification.json) and [final manifest](final-manifest.json).

The workflow dispatched [test website run 41188626026](https://github.com/ccozianu/devcapsule/actions/runs/41188626026).
Build, deploy and candidate publication all passed. Live build-info names
main 31d44fa4, docs-0.3.0 at 7a813b80 and current version 0.3.0; the home,
current guides, versioned guides and release-note pages return HTTP 200.
[Website verification](website-verification.json). The public candidate is
[website-candidate-41188626026-1](https://github.com/ccozianu/devcapsule/releases/tag/website-candidate-41188626026-1),
with bundle SHA-256 feb14cb499782540f4d7b051122201650d787bb89cb76c217547702b60ab90ca.
The owner reviews [the test site](https://test-devcapsule.mycodespace.ai/)
and selects that candidate in **Publish production website** in
ccozianu/devcapsule-website. Production promotion was not performed here.
The release branch is closed and retained; corrections to released guides
belong on docs-0.3.0. Maintenance resumes on
`ws-maintenance/0.3.1-preparation` from the acceptance merge on main.

## Final acceptance — 2026-10-31

Costin Cozianu answered "Yes to both questions, let's move ahead" after
requesting final publication. Exact RC9 is accepted with the documented
provider/editor verification limits. This does not claim unobserved
provider actions or editor flows. C17 and the nine undecided September 28
documentation proposals move to **0.3.1 planning**, retaining their owners
and item-level decisions; they no longer gate 0.3.0. This supersedes the
older explicit gates and pending questions below. October 25's separate
work order remains scheduled for 0.3.1 as already decided.

[The promotion record](../v0.3.0.json) binds source
`475427da033633ff5ee0e44e09face700630bf36` and candidate SHA-256
`413b1d45bac9c39b6fa5fab68090e43550c9e255108de48b387c50a715c4fcf2`.
The six fixed maintenance records close on their RC9 verification and owner
acceptance; the cookie fix was already verified on the rebuilt published base.
All required downloaded-executable checks pass. The notes, documentation
manifest and docs branch match the candidate. Claude 2.1.316 is held for a
0.3.1 review; the accepted source retains tested 2.1.314.

Next: owner merges [acceptance PR #332](https://github.com/ccozianu/devcapsule/pull/332) to main, then publish v0.3.0 from
RC9's source, verify final assets and the test-site deployment. No new
publication approval is needed. The owner promotes the site to production.
Main remains 0.3.1.dev0; preparation for 0.3.1 follows final delivery.

## RC9 verification — 2026-10-31

[#331](https://github.com/ccozianu/devcapsule/pull/331) merged at main
`4b59b10d`. [RC9](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc9)
is published from release `475427da`; its three assets, checksum and embedded
identity agree. Downloaded PEX verification passes eight ordinary E2E tests
and the shared-browser authentication regression. The blocking cookie bug
is closed, including delivery through the rebuilt default base.
[Evidence and limits](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#downloaded-rc9-verification).

Next: owner acceptance of this candidate and completion of the remaining
release obligations, then the formal acceptance record and promotion under
the runbook. These smoke results do not authorize the final tag.

## Final promotion audit — 2026-10-31

The owner requests 0.3.0 publication and then 0.3.1 preparation. The restarted
capsule now uses the verified fixed base after removing its saved local-base
override. Runtime inspection, attached recursive lifecycle, 18 packaged
cache/network cases and a real fresh-project run-once network launch pass.
[Audit evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#final-promotion-audit--2026-10-31).
Final vendor recheck found Claude 2.1.316; retain tested RC9's 2.1.314 for
this promotion and review the new version in 0.3.1. Other agent feeds match.

The October 27 scope record still explicitly gates C17 and the nine
September 28 proposal decisions. The owner has been asked to move these to
0.3.1 planning or keep them before 0.3.0, and to confirm provider acceptance
or accept its documented limits. No disposition is inferred. On resolution,
commit the formal acceptance record and obtain its mainline PR merge before
tagging the exact RC9 source. The published executable remains unchanged.

## Headline

The capsule web console, persistent session diagnostics, and a launcher
that is honest about what it skips.

## Scope And Owner Decisions

- **0.3.0 user documentation CLI alignment, full stub authoring, and prose review, 2026-10-30.**
  The owner merged [PR #316](https://github.com/ccozianu/devcapsule/pull/316) on
  `main` (`ebab228a`) and assigned
  [the work order](../../work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
  to `maintenance` on `release-0.3.0` (`write-full-pages`,
  `combine-with-language`, `direct-wo-pair-batches`), closing final-tag gate
  **C16** and the October 24 language-review booking in one pass. All `49`
  `docs/*.md` files on `release-0.3.0` (including authoring all `12`
  `status: planned` stubs in full, without inventing `0.3.1`-deferred commands)
  are audited and rewritten in five coherent pull-request batches of `<= 10`
  `docs/*.md` files each using Pair Review: Antigravity (`Gemini 4 Argon
  (High)`) implements and Codex (`gpt-6-astra`) reviews.
- **CI path gating and advisory diff coverage, 2026-10-30.** The owner
  assigned the [reviewed work order](../../work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md)
  to maintenance for 0.3.0. Decisions 1B and 2B mean advisory coverage with
  no percentage gate and serial execution; parallelism is deferred beyond
  0.3.0 without a later release target. PR #312 implements the slice with
  GPT-6 Codex and Claude Code / Claude Fable 5.1 Pair Review. Review #314 is accepted and the final local/hosted gates passed.
  Integration is complete through #312 and #317. The `ci-gate` required-check
  setting remains open: the live main rules on 2026-10-31 prevent deletion
  and non-fast-forward pushes, but require no status check.
- **October 25 documentation proposals, retargeted 2026-10-29.** Parts A
  and B of that work order belong to 0.3.1, still owned by maintenance.
  They no longer gate 0.3.0. The separate language review, accurate candidate
  documentation (C16) and C20 remain 0.3.0 obligations.
- **Pair Review Loop name, 2026-10-30.** The owner requires the terminology
  and packaged-definition change in 0.3.0. Main PR #309 is merged; maintenance
  has accepted the release-adapted patch for a separate slice after CI review.

- **The explicit IDE requirement override, 2026-10-29.** The owner brought
  the [work order of 2026-10-28](../../work-orders/2026-10-28-explicit-ide-requirement-override.md)
  from `main` into 0.3.0 and assigned it to `maintenance`: a project may
  require an IDE, and `project run --ide IDE --force` launches another one
  for one session, warned, recorded in the plan and never saved
  ([D-0016](../../decisions/product/d-0016-explicit-launch-departure-from-a-required-ide.md),
  R-CONFIG-001's one explicit launch exception). Claude Code, Claude
  Fable 5.1, implements on `ws-maintenance/0.3.0-ide-override` with the
  recorded acceptance session; the review partner is the owner's choice.
  The `--save` combination is refused until the owner defines it.
- **C20, release documentation automation, 2026-10-27.** The owner approved
  the release documentation work order on `main`. Codex, GPT-6 Astra,
  implements it; Claude Code, Claude Fable 5.1, reviews it.
  Before the last candidate, write `notes.md`, run `release-docs.py promote 0.3.0`,
  commit both, push `docs-0.3.0` at that commit, and merge to `main`.
  Validate and accept that candidate. Integrate its acceptance record.
  Run `release-docs.py check 0.3.0`, then tag the accepted source.
  The final job verifies the documentation, publishes the PEX with the
  notes as its body, and dispatches the test website. The owner reads the
  test site and promotes it to production. Both website modes refuse a
  listed release without its published download.

- **Cut now**, decided 2026-10-18 after the inventory of what the plan still
  had unimplemented: a candidate of what exists is worth validating, and
  the candidate cycle is the better place for the remaining launcher work,
  with 0.2.14 as the precedent. `main` stays at `0.2.16.dev0` until the
  final tag, then reopens at `0.3.1.dev0` unless the owner names another.
- **Dogfooding during the cycle.** Six items are implemented during the
  candidate cycle, each a maintenance slice with the implementor-and-reviewer
  loop, landing on the release branch by the owner's direction and reaching
  `main` by the merge before each candidate tag: the universal `network`
  authorization node; C10, the first-session terminal summary and Ctrl+C
  ending with a result; forced configuration, `project config resolve
  --force` and `project run --force-config`, mandatory needs split from
  optional ones; the diagnostics snapshot and export command; cleanup of
  obsolete images and cached files, design reviewed with the owner first;
  C20, release notes and documentation automation, last. Features landing
  on a release branch during a candidate cycle are the owner's direction
  for this release, as the decision asks this overview to record; a
  standing local rule is `workflow-improvements`' to propose if it recurs.
- **Out of 0.3.0:** consent and vendor trust (D-0010 to D-0013,
  `component-upgrades`); installed-IDE reuse with an empty launcher cache;
  browser evidence for the diagnostics; the web console's deliverable 6,
  materialized views; ecosystem-aware project bootstrap, retargeted to 0.9
  on 2026-10-11 and applied with the cut. Their next home is 0.3.1 or the
  next cycle, decided at that planning.
- **Gates before the final tag:** the owner's eleven user-docs proposal
  decisions, the gate of 2026-09-28; the documentation describing the
  accepted candidate, C16; a published base for the candidate, since the
  console needs recipe 11; the fixed bug records verified against a
  downloaded candidate; the release notes as `notes.md` beside this file.
  Project-operation instructions, C17, stay assigned to
  `workflow-improvements` for 0.3.0 and gate the final tag. Added by the
  owner's direction of 2026-10-24, on reading the candidate-4 stack: a
  language review of the user documentation, which reads as machine prose
  and whose sections lack a conceptual entry page, the configuration
  section first; booked with `project-management` by mail at
  `9fcfdb8db440`, which assigns the reviewer and the method.
  Added by the owner's direction of 2026-10-26: `init --regenerate`
  migrates the manifest to schema 2, and schema 1 and schema 2 are
  represented as classes; the work order of 2026-10-26 in `work-orders/`.
- **Rulings of 2026-10-21.** The base publication happens later, in the
  promotion of the accepted candidate, not before the next one. The
  candidates are grouped: rc2 carries the network node and C10; rc3 forced
  configuration and the diagnostics snapshot; rc4 image cleanup and C20.
  C17 stays a gate in both halves, the generic rule in `WORKFLOW.md` with
  `workflow-improvements` and this project's own operating instructions in
  `WORKFLOW-LOCAL.md`, the concrete case against which the abstract rule is
  debugged.
- **Direction of 2026-10-24.** Candidate 3 is tagged now with what the
  release branch carries, software approvals at launch (PR #250) and the
  saved Docker arguments (PR #253), because the owner needs the extra
  Docker arguments to test development scenarios, environment variables
  and GPUs among them. Forced configuration and the diagnostics snapshot,
  grouped into rc3 on 2026-10-21, move to rc4 with image cleanup and C20;
  the manifest's schema-version slice goes with them. The regenerated
  shared lock rides rc3, so provider acceptance of the new agent pins on
  a downloaded candidate becomes possible there.
- **Direction of 2026-10-24, evening.** Candidate 4 is tagged with the
  CLI UX redesign, the stack of PRs #260 to #269 the owner merged the same
  day: the manifest's schema 2 with the owner's `require`, `offer`, `drop`
  and `recommend` commands; the checkout commands; `run` deriving the plan
  with no resolve step; workstation trust (D-0011); the console writing
  through the launcher; the documentation and the candidate-4 changelog.
  Forced configuration is superseded by the redesign: there is no resolve
  step to force and `run --force-config` is retired. The diagnostics
  snapshot, image cleanup and C20 move to the next candidate. The
  documentation language review is a gate before the final tag (above).
- **Direction of 2026-10-25.** Candidate 5 is tagged with the capabilities
  and components work order, the three slices the owner merged the same
  day (#276, #277, #279): one model of capabilities provided by
  components, the IDE the only special role; agents as ordinary
  capabilities; the SDK major removed, old files still read; a minimum
  on a requirement; the resolution recommendation; the developer's
  `add`, `omit`, `restore`, `use`; every retired spelling deleted; the
  configuration documentation rewritten on the model, with its entry
  page. The diagnostics snapshot, image cleanup and C20 move to the next
  candidate.
- **Direction of 2026-10-25, after the rc5 test.** The owner's test of
  the rc5 download found the console's configuration page failing: the
  console ran `config list`, retired by candidate 5, and showed its
  status-2 refusal. The repair, PR #281 on the release branch, points the
  console and the launcher's in-capsule hints at `config show`, and the
  console's own test session now runs the launcher it ships with, so a
  retired command fails the build instead of the page. Candidate 6 is cut
  on that repair alone; the diagnostics snapshot, image cleanup and C20
  stay with the next candidate.
- **Direction of 2026-10-25, after the rc6 test.** The owner rebuilt the
  base from the rc6 executable, confirmed the console's configuration
  page on it, and published it as `mycodespaceai/devcapsule-base:v0.3.0.rc6`,
  digest `8c97d308…`, `ubuntu-24.04@11`. The matrix pins it (PR #284,
  `embedded-28`), the recipe-9 pin stays for existing locks, and candidate
  7 is cut on that pin alone, so every regenerated lock reaches the
  console on the published base. The published-base gate before the
  final tag is met by this candidate. A project's own constraint on its
  base is D-0015, proposed for V1, not for 0.3.0.
- **Direction of 2026-10-26.** On finding that `init --regenerate` left the
  AI Learning manifest at schema 1, the owner ruled that regeneration
  migrates the manifest to schema 2 and that schema 1 and schema 2 are
  represented explicitly, as classes, and made both a gate of the final
  tag: the work order of 2026-10-26, implemented as PR #289 with Codex,
  gpt-6-astra, as the review partner, merged at `9e4a2a8`. Candidate 8 is
  cut on it. The owner's own regeneration of this repository's, the
  website's and the samples' manifests follows the shipped candidate.
- **Stopping points where the owner is consulted:** before each candidate
  tag; before the image-cleanup implementation; when a slice proves larger
  than the cycle tolerates; before the final tag. Scope changes go by the
  decision record's reopen rule.
- Routine release-fix propagation to `main` follows the runbook's *Release
  Fixes And Main* under the owner's standing direction of 2026-09-22.

## What `main` Carried At The Cut

Integrated between `v0.2.15` (final 2026-09-27) and the cut commit, by the
merges on `main`'s first parent:

- The capsule web console, first iteration (#184, #190) and the second
  (#192 to #206, delivered through #201 on `main`), with the notifications
  and decisions groups under `project checkout`.
- Persistent session logs: one file per component, a WARNING baseline, a
  host-backed directory per session (#207); in-process rotation and one
  budget per checkout (#209, #216).
- Maintenance after 0.2.15 (#164, #168, #169, #172): the fresh-workspace
  recursive test, the in-capsule project-command fix, named build contexts,
  the unpacked-cache corrections.
- IntelliJ IDEA and the configuration contract commands from
  `component-catalog` (#163 to #173).
- The user documentation of 43 pages, the website producer migration and
  the versioned documentation live on the site (#151 to #158), the landing
  page identity and the comparison (#219, #221, #222).
- Workflow and coordination records from `project-management` and
  `workflow-improvements` (#159, #162, #176 to #183, #214, #215, #220).

## Agent Freshness Review

Owner direction of 2026-09-27, applied to every release: try to upgrade the
supported agent CLIs to their current generally available versions. The
vendor pointers were read on 2026-10-18 at 12:59 UTC, with the sources the
0.2.15 review used.

| Agent | Current pin | Vendor current | Source consulted | Disposition |
|---|---|---|---|---|
| Codex | 0.157.1 | 0.163.0 | [OpenAI npm latest](https://registry.npmjs.org/@openai/codex/latest) | adopted provisionally, matrix embedded-27 on the slice branch; provider acceptance on the downloaded candidate |
| Claude Code | 2.1.283 | 2.1.302 | [Vendor latest channel](https://downloads.claude.ai/claude-code-releases/latest) | adopted provisionally, matrix embedded-27 on the slice branch; provider acceptance on the downloaded candidate |
| Antigravity CLI | 1.2.12 | 1.4.2 | [Vendor Linux amd64 manifest](https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json) | adopted provisionally, matrix embedded-27 on the slice branch; provider acceptance on the downloaded candidate |

Every vendor was ahead of the pin. The attempt, the same day, on the
slice branch `ws-maintenance/0.3.0-agent-freshness` for a pull request
into the release branch:

- **Artifacts.** The four downloads were checked against the vendors' own
  integrity values before their SHA-256 was recorded in the matrix: npm's
  SHA-512 for `codex-0.163.0.tgz` and `codex-0.163.0-linux-x64.tgz`, the
  Claude manifest's SHA-256 for the 2.1.302 binary, the Antigravity
  manifest's SHA-512 for the 1.4.2 archive, whose member is still
  `antigravity`. Codex still requires Node 16 or newer; the base carries
  22. No layout change was found in any of the three.
- **Startup on the base.** A disposable container on the local recipe-11
  base `devcapsule-base-e2e:v0.2.16.dev0-local-linux-x86_64-36bef9f1e151`
  (Ubuntu 24.04.5, Node 22.23.1, npm 10.9.8), host networking, fetched
  the artifacts again and verified them, laid Codex out with the same
  offline `npm install` the image build emits, and started each CLI as a
  fresh uid-1000 user with DevCapsule's seeds in place: `codex --version`
  reported `codex-cli 0.163.0`, `codex features list` printed its 175
  flags over the seeded `config.toml` and `codex exec --help` answered;
  `claude --version` reported `2.1.302 (Claude Code)`, and a headless
  prompt answered with a JSON result record and stopped at the missing
  account while its debug log recorded `mode=bypassPermissions
  flag=false(fallback)`, the seeded default taken without a command-line
  override; `antigravity --version` reported `1.4.2`, its help and
  `changelog` printed. The three seed files were byte-identical after the
  starts. Not shown without an account: an actual tool action, model
  entitlement, the first-use notices; those are the owner's acceptance
  on the downloaded candidate, as in 0.2.15.
- **Matrix.** `embedded-27`: the three pins, provisional verified edges on
  the Ubuntu 24.04 family, the golden locks regenerated, the init tests
  naming Antigravity 1.4.2. The earlier pins stay, so locks that select
  them keep resolving.
- **The repository's own lock is the owner's step.** The gate test that
  resolves this checkout's need against the matrix fails until
  `.devcapsule/devcapsule.linux-amd64.lock` carries the new pins, and the
  local rule lets only a DevCapsule command write it, outside the capsule.
  One command on the host, with a build of the slice branch's source
  (`devcapsule-src/dist/devcapsule-local.pex` in the shared checkout):

  ```text
  cd /home/costin/work.provisional/costin3/myProjects/devcapsule
  devcapsule-src/dist/devcapsule-local.pex project config capabilities \
    --required antigravity-agent claude-code-agent codex-agent docker-cli python python-ide
  devcapsule0 project config check
  ```

  The first regenerates the lock from the matrix; the second validates the
  written result with the known baseline. Until it runs, the slice is not
  gated and rc0 cannot carry the new pins; the alternative is rc0 on the
  current pins and the upgrade in rc1, the owner's word either way.

The pointers are rechecked before final acceptance, and a version that
appears meanwhile gets an adopt-or-hold decision here, never a silent
replacement.

## Preparation And Publication

- Release branch `release-0.3.0` starts at the preparation baseline
  `3c91183ffd2130f6c7b40d2f9e3fd41588f977eb`, `main` at the merge of PR
  #223, selected by the driver: nothing of maintenance was unmerged, and
  the commit carries the decision and the work order. Version 0.3.0 at
  `6965c5e`, the branch's first commit, by `nox -s bump -- 0.3.0`.
- [x] Cut, version, the work order acknowledged, the bootstrap record
  retargeted, the registry row and the status file on the release branch.
- [x] Full gate on the release branch at the version commit: distribution
  version, syntax, mypy clean over 214 files, 1584 unit tests passed, CLI
  smoke, test PEX built and smoked, packaging integration 17 passed; the
  documentation contract passed after the manifest's release-branch line
  (`source-version: "0.3.0"` on the `devel` entry, a judgment recorded in
  the status file and mailed to project-management as a contract gap); the
  web console session mypy clean over 8 files, 293 tests.
- [x] Agent freshness upgrade attempt; dispositions in the table above.
- [x] PR #224 merged into the release branch at `6b97657`; the release branch merged into `main` by PR #228 at `7c20292`, ancestry holds; `main` carries 0.3.0 during the cycle by the owner's merge. The branch, deleted by `delete_branch_on_merge`, restored at the same tip.
- [x] The shared lock regenerated on 2026-10-22 by `project config capabilities` on a fresh clone inside the capsule, where the command runs for any project but the capsule's own; committed on the release branch at `0c1a555`, gated (1672 unit tests), proven by the recursive attached launch from a fresh clone; merges to `main` with the next pre-candidate merge.
- [x] `v0.3.0-rc0` tagged on the release branch at `53ebc17`; backend run
  passed; the three assets downloaded, checksum and version verified.
- [x] Local proofs against downloaded RC9: clean machine, component cache,
  runtime session on the pinned base; see the acceptance record.
- [ ] The dogfooding slices, each merged to `main` before the next
  candidate tag; the bug records closed on candidates.
- [ ] The gates before the final tag; `notes.md`; the acceptance record;
  the final tag; delivery verified; `docs/versions.yaml` promoted on `main`.

## RC9 preparation — 2026-10-31

**Cookie fix merged:** PR #330 is on `release-0.3.0` at `36b5e660`,
carrying fix `3af21584`. PR #329 incorporates it; the only merge conflict
was the maintenance status State line, resolved while retaining both sessions'
records. Console cookies now use the browser-facing port in their name.
noVNC authenticates through its WebSocket token URL, not this console cookie.

The owner selected **base-first** in `2026-10-31-rc9-base-refresh` at
02:14:16 UTC. It is complete: the strict public-source builder at `12a30fa6`
produced `mycodespaceai/devcapsule-base:v0.3.0-base-20261031`, published and
pinned at `sha256:d7047ced8556cd35964fcc058a1101cf2b5b202f7a5daa2fdd434dcda5ed82c9`.
The installed console matches the fix, and only its layer changed from rc6.
Catalog embedded-31 retains old pins and selects the fixed base for new
resolutions. Existing locks require an explicit base refresh.

Two ordinary fresh-project capsules on the new default pin passed one shared
browser context: tokenless console navigation/reload, noVNC reload/reconnect,
and refusal of each other's console and desktop credentials. Both test
containers were removed. Full local gate passes (2,645 unit, 18 packaging,
374 console tests, type/syntax/CLI/PEX/docs), as do 112 focused tests and the
website check. The base/concurrency hold is resolved. Owner release/main
merges, the candidate gate and downloaded-RC9 acceptance remain.

The owner requested the intended final release candidate after all open PRs
merged. PR #317 is on main at `ce08ebad`; documentation batches #319, #321,
#323, #325 and #327 are on release tip `338f94ab` but not yet on main.
All 49 guides were reviewed; all 12 planned stubs were authored. The next
unused tag is `v0.3.0-rc9`; it has not been created.

Preparation: write the adopter notes, promote docs/versions.yaml with the
C20 helper, establish docs-0.3.0, run the full local gate and website build,
and integrate the resulting release source into main before tagging.
`docs-0.3.0` was published at promotion commit `68b21a18`; docs-only commit
`7a813b80` now includes #330's three guide corrections for hosted PR checks.
The owner merges the integration PR. No final release or candidate acceptance
is claimed by this preparation.

Freshness recheck, 2026-10-31: vendor latest pointers offer Codex 0.166.0,
Claude Code 2.1.314 and Antigravity CLI 1.4.12, compared with the existing
pins 0.163.0, 2.1.302 and 1.4.2. Sources are the same vendor endpoints in
the freshness table. The owner selected **upgrade** in decision `2026-10-31-rc9-agent-pins`
(answered 2026-10-31 at 00:50:18 UTC) and additionally requested IDE updates
because of security fixes. Stable vendor feeds select PyCharm, IntelliJ IDEA
and Rider 2026.2.4, VSCodium 1.143.17232 and VS Code 1.144.0; Eclipse Java
2026-09-R is unchanged. All nine full artifacts passed vendor integrity checks. All three agents
and five updated IDEs passed startup checks on the pinned recipe-11 base;
JetBrains editor/account acceptance remains beyond the first-use dialogs.
The full build gate and website checks pass. See the maintenance
[evidence ledger](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md).
Existing pins remain available for old locks.
Do not claim a particular security fix from version age alone; the vendor
security table did not return usable advisory rows during this check.

Final acceptance still needs downloaded-artifact verification, the remaining
fixed-bug/provider checks, and an explicit disposition of the C17 generic
half and nine documentation proposal decisions left open in the October 27
scope record. Candidate preparation does not silently close those items.
Automated cleanup and empty-cache IDE reuse are out by that record, despite
older historical candidate plans below.

## Candidates

### RC0 — tagged 2026-10-18

- Tag `v0.3.0-rc0` on `53ebc17705bf99461bbbbf3c4a128228a14c0d51`, the
  release branch's tip at the pre-candidate merge (PR #231 from the
  throwaway copy); the two record commits after it on the branch carry no
  source. The source is byte-identical to the tree the full gate passed on
  2026-10-18 (PR #230's branch: 1584 unit tests, packaging, documentation
  contract, web console), and the hosted unit run passed on PR #231.
- Candidate gate, run locally from a detached checkout of the tag before
  the push: method `mainline`, no unintegrated commits, version
  `0.3.0rc0`.
- Pushed atomically with the branch; backend run
  [39175482525](https://github.com/ccozianu/devcapsule/actions/runs/39175482525).
  The run passed (`Build, publish, and prove`), and the
  [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc0)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into a fresh directory,
  `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc0`: the checksum
  file verifies the executable, SHA-256
  `5d0f0e6c60e72eb291ce5de18036b10c5496b71cfce4e5c7076fe60cd195a6b1`, and
  the manifest records the same value, the tag, the release branch, the
  source revision `53ebc17…` and the gate's `mainline` disposition. The
  executable reports version `0.3.0rc0`, mnemonic `v0.3.0-rc0` and that
  source revision; its help answers.
- What it carries, beyond 0.2.15: everything `main` had at the cut (see
  above), the agent pins Codex 0.163.0, Claude Code 2.1.302 and
  Antigravity CLI 1.4.2, and the launchable-lock test.
- Owner-reported, 2026-10-18: the downloaded candidate, installed as
  `devcapsule-local` on the host and reporting `v0.3.0-rc0`, package
  `0.3.0rc0`, source `53ebc17…`, ran `project run` on the second
  DevCapsule checkout and the capsule launched the first time. This is
  the owner's evidence, distinct from the agent's machine proofs; the
  interactive agent and console checks continue there. The local Docker
  proofs against the download, clean machine, component cache, runtime
  session on the pinned base, follow once the owner's session on that
  daemon is done.
- Owner-reported, 2026-10-19: with the candidate's own builder, the owner
  built a recipe-11 base on the host (`images build --type base
  --recipe ubuntu-24.04 --network host --source-revision 53ebc17…`),
  selected it for the second checkout with `config authorize base-image`,
  resolved and launched: the web console answered on the printed link.
  The first finding of the day, the console link on the recipe-9 base,
  is the bug record below; the console itself works on the base the
  release will publish.

### RC1 — tagged 2026-10-19

- Tag `v0.3.0-rc1` on `7016cdd7cbd373204c4ae0b9fcb01cede3433d94`, the
  release branch's tip after the merge of PR #232 and the pre-candidate
  merge into `main` by PR #233 from the throwaway copy `4PR-2-release-0.3.0`.
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc1`.
- What it adds to rc0: the console-link fix, the launcher announcing the
  web console only on a base that has one, and the local-base guide. The
  candidate verifies the fix against the published recipe-9 base and a
  recipe-11 base and closes the bug record.
- Backend run [39265210147](https://github.com/ccozianu/devcapsule/actions/runs/39265210147)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc1)
  is public, non-draft, with the three assets, and the changelog is its
  body.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc1`:
  the checksum file verifies the executable, SHA-256
  `4022a1828575eb24ac029d8915e5fb3a29f191aed4e9aab2ca9b2d1f6452cfc0`, the
  manifest records the same value, the tag, the branch, the source
  revision and the `mainline` disposition; the executable reports
  `0.3.0rc1`, `v0.3.0-rc1` and `7016cdd…`, and its help answers.
- Verified by the owner, 2026-10-21: on the published recipe-9 base the
  launcher prints the substitute line and no link; on the local recipe-11
  base the link works and the console answers. The bug record is closed.
  The owner's judgment of the console: it works nicely, to the extent
  required for 0.3.0.

### RC2 — tagged 2026-10-22

- Tag `v0.3.0-rc2` on `e5b5a8b73309959f9407e115dcb3acd8707d6050`, the release
  branch's tip at the pre-candidate merge (PR #249 from the throwaway copy
  `4PR-3-release-0.3.0`, which carried one commit keeping `main`'s version
  files); the record commits after it on the branch carry no source.
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc2`.
- Backend run [39803285881](https://github.com/ccozianu/devcapsule/actions/runs/39803285881)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc2)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc2`:
  the checksum file verifies the executable, SHA-256
  `abb9a8e18f6688326b7a94aae5b504ccdfa1e1782f1215465857eb9a03d9ba7e`; the
  manifest records the tag, the branch, the source revision and the
  `mainline` disposition; the executable reports `0.3.0rc2` at `e5b5a8b…`.
- The shared lock is not in rc2: it was regenerated after the tag and
  rides the next candidate. Provider acceptance of the new agent pins on a
  downloaded candidate stays the owner's.

- Carries, beyond rc1: the universal `network` authorization node (PR #240,
  review #242 by the Codex pair); the first-session summary and Ctrl+C
  ending with a result (PR #244, review #246 by the Antigravity pair), the
  session's log paths printed at its end; the listing's source label for
  workstation defaults. Each slice gated in full on its merged branch; the
  interrupted-launch end-to-end test passed on a real fresh VSCodium
  launch.
- The release branch synchronized with `main` twice on 2026-10-22, on the
  owner's word, so the cycle's workflow rules and both checkouts' records
  bind it; the version files kept the release side.
- Next: the owner's dogfooding of the terminal and of Ctrl+C, and the three
  records' verification: the IDE smoke on a fresh project, the interrupted
  launch, the quiet terminal.

### RC3 — tagged 2026-10-24

- Tag `v0.3.0-rc3` on `a22a21585f353c269c566686fe348e99959a91cd`, the release
  branch's tip at the pre-candidate merge (PR #257 from the throwaway copy
  `4PR-4-release-0.3.0`, merged by the owner at `cf760b8`); the record
  commits after it on the branch carry no source.
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc3`.
- Backend run [40052369307](https://github.com/ccozianu/devcapsule/actions/runs/40052369307)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc3)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc3`:
  the checksum file verifies the executable, SHA-256
  `be739875ac75da0188f1330ebc6ca25805f2fb0257650ed986f2e9f7212c39bb`; the
  manifest records the tag, the branch, the source revision and the
  `mainline` disposition; `devcapsule version` reports `0.3.0rc3` at `a22a215…`.

- Carries, beyond rc2: software approvals at launch, the one y/n for new
  versions of software approved before and `project config approve`
  (PR #250, review #251 by the Codex and gpt-6-astra pair); the saved
  Docker arguments for each checkout, `set-extra-docker-args`,
  `list-extra-docker-args`, `remove-extra-docker-args` and the `set-env`,
  `list-env`, `unset-env` conveniences on the same list, with inline
  environment values masked in every report (PR #253, review #255 by
  Claude Code); the shared lock regenerated on matrix embedded-27, Codex
  0.163.0, Claude Code 2.1.302, Antigravity CLI 1.4.2 (`0c1a555`). Each
  slice was gated in full on its merged branch.
- Full gate on the release tip before the pre-candidate merge: mypy clean
  over 224 files, 1769 unit tests passed, 36 deselected, 2 xfailed,
  packaging integration 17 passed, the documentation contract 188 pages,
  the web console clean with its tests passed; posted on PR #257.
- Next: the owner's test of the saved Docker arguments and of the
  approvals prompt on the download; provider acceptance of the new agent
  pins, which this candidate's lock makes possible; the network node's
  check on a fresh project, still open from rc2.
- Not in rc3: forced configuration, the diagnostics snapshot, the
  schema-version slice; see the direction of 2026-10-24 above.

### RC4 — tagged 2026-10-24

- Tag `v0.3.0-rc4` on `78a9c6617226599f457504929d747faa9387830b`, the release
  branch's tip at the pre-candidate merge (PR #274 from the throwaway copy
  `4PR-5-release-0.3.0`, merged by the owner at `c04cb4e`).
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc4`; record at
  `/opt/devcapsule-gate/rc4-release-protocol.json`.
- Backend run [40123896286](https://github.com/ccozianu/devcapsule/actions/runs/40123896286)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc4)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc4`:
  the checksum file verifies the executable, SHA-256
  `474fea1e04a5c87f99cac61ec50d980a88244f1ed9a74a267eb0e7ef51494995`; the
  manifest records the tag, the branch, the source revision and the
  `mainline` disposition; `devcapsule version` from an empty directory
  reports `0.3.0rc4`, build `v0.3.0-rc4`, at `78a9c66…`.
- Next: the owner's test of the redesigned commands on the download,
  `init`, `config require|offer|recommend`, `config show|check`, `run`
  asking at the terminal, `config trust`, the console's configuration
  requests; then the diagnostics snapshot, image cleanup and C20 for the
  next candidate; provider acceptance of the agent pins and the network
  node's check on a fresh project, still open.

How the candidate was prepared:

- The release branch's tip after the owner's merge of the stack is
  `3cc8a50`, PR #269. The full gate on it: mypy clean over 242 files,
  2091 unit tests passed, 36 deselected, 1 xfailed, 1 xpassed; the
  packaging integration failed one test of seventeen,
  `test_built_pex_authors_shared_policy_and_keeps_personal_selection_local`,
  which authored a project with the old spellings and expected `config
  check` to pass with the base channel neither trusted nor consented to,
  and expected the retired `--sdk-major` flag to resolve. Both
  expectations predate the redesign: `check` reports the pending channel
  with status 3, and the old flag refuses with a migration note. The test
  now asserts the pending check, accepts the channel under its isolated
  configuration home, and refuses the SDK major through `config require
  tool`; `fe886ad` on the release branch, a test-only change. The unit
  gate never ran this test, so the slices' gates could not see it; the
  packaging integration runs only in `nox -s build` against the built
  executable.
- Full gate on `fe886ad`: mypy clean over 242 files, 2091 unit tests
  passed, packaging integration 17 passed, the web console session clean
  with its tests passed; the documentation contract passed on the same
  `docs/` content, 188 pages, at the slice-6 tip.
- The throwaway copy `4PR-5-release-0.3.0`, the release tip plus the
  cherry-pick of `62fa063` keeping `main`'s version files, test-merged
  into `main` cleanly and was PR #274, merged by the owner; the tag
  followed on the release tip, `78a9c66`, the record commit.
- Carries, beyond rc3: the CLI UX redesign of the direction above, every
  slice reviewed by the Codex and gpt-6-astra pair (#262, #264, #267,
  #270, #271, #272) with the reviews merged. The resolution matrix is
  still embedded-27 with the recipe-9 base, so an existing lock
  regenerated by this candidate is byte-identical.
- Not in rc4: the diagnostics snapshot, image cleanup, C20; the gaps the
  docs reviewer found and the candidate-4 changelog lists under *Not in
  candidate 4*.

### RC5 — tagged 2026-10-25

- Tag `v0.3.0-rc5` on `03ed3483608de97ebf7770149fd25544e8387b49`, the release
  branch's tip at the pre-candidate merge (PR #280 from the throwaway copy
  `4PR-6-release-0.3.0`, merged by the owner at `35d74d9`).
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc5`; record at
  `/opt/devcapsule-gate/rc5-release-protocol.json`.
- Backend run [40147675417](https://github.com/ccozianu/devcapsule/actions/runs/40147675417)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc5)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc5`:
  the checksum file verifies the executable, SHA-256
  `429aefee8af6434615b92f97c6c3b1f2f6ef55f177a3d58f9127e8b1cad8bfbb`; the
  manifest records the tag, the branch, the source revision and the
  `mainline` disposition; `devcapsule version` from an empty directory
  reports `0.3.0rc5`, build `v0.3.0-rc5`, at `03ed348…`.
- Next: the owner's test of the model's commands on the download, `init
  --require 'java>=21' --with`, `config require|offer|drop|recommend`,
  `config add|omit|restore|use`, `run --with|--use`, the refusals of the
  old spellings, the console's configuration page; then the diagnostics
  snapshot, image cleanup and C20 for the next candidate; the
  documentation language review before the final tag.

How the candidate was prepared:

- The release branch's tip after the owner's merges is `d01fb8c`, PR
  #279. Full gate on it from a separate worktree: mypy clean over 246
  files, 2281 unit tests passed, 36 deselected, 2 xfailed, packaging
  integration 17 passed, the web console session mypy clean over 9 files
  with 326 tests passed; the documentation contract 189 pages, passed.
- Carries, beyond rc4: the capabilities and components work order of the
  direction above, implemented by the Codex and gpt-6-astra pair and
  reviewed by Claude Fable 5.1, one round per slice (PRs #276, #277,
  #279). The resolution matrix is still embedded-27 with the recipe-9
  base; an rc4 lock regenerated by this candidate is byte-identical, and
  an rc4 manifest with the SDK-major table reads with one note.
- The throwaway copy `4PR-6-release-0.3.0`, the release tip plus the
  cherry-pick of `62fa063` keeping `main`'s version files, test-merged
  into `main` cleanly and was PR #280, merged by the owner; the tag
  followed on the release tip, `03ed348`, the record commit.
- Not in rc5: the diagnostics snapshot, image cleanup, C20; the gaps the
  candidate-5 changelog lists under *Not in candidate 5*.

### RC6 — tagged 2026-10-25

- Tag `v0.3.0-rc6` on `2ed8ecf536b0d653056ac35792cae413a6d6732a`, the release
  branch's tip at the pre-candidate merge (PR #282 from the throwaway copy
  `4PR-7-release-0.3.0`, merged by the owner at `b64187f`).
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc6`; record at
  `/opt/devcapsule-gate/rc6-release-protocol.json`.
- Backend run [40162886659](https://github.com/ccozianu/devcapsule/actions/runs/40162886659)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc6)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc6`:
  the checksum file verifies the executable, SHA-256
  `6cef940ec86c4b45fc89bb265aeb2c3750155dcb7c0fec50ad8a1fe8e658de75`; the
  manifest records the tag, the branch, the source revision and the
  `mainline` disposition; `devcapsule version` from an empty directory
  reports `0.3.0rc6`, build `v0.3.0-rc6`, at `2ed8ecf…`.
- Next: the owner's test of the download, the console's configuration
  page first, then the model's commands; then the diagnostics snapshot,
  image cleanup and C20 for the next candidate; the documentation
  language review before the final tag.

How the candidate was prepared:

- Carries, beyond rc5: the console's configuration page and the
  in-capsule hints calling `config show` (PR #281, `cd128bb`), and the
  console's test session installing the launcher with contract tests
  against its command tree (`ed01b4d`): every configuration-channel verb
  is a `config` command that takes `--json`; the channel's applied,
  deferred and secure sets agree with the launcher's; the channel
  document lists the verbs.
- The release branch's tip after the owner's merge of PR #281 is
  `5daf5a2`, whose tree is the reviewed `ed01b4d`; `2ed8ecf`, the
  preparation record, is the tagged tip. Full gate on `5daf5a2` from a
  separate worktree: mypy clean over 246 files, 2281 unit tests passed,
  36 deselected, 1 xfailed, 1 xpassed, packaging integration 17 passed,
  the web console session mypy clean with 357 tests passed, 31 of them
  the new contract; the documentation contract 189 pages, passed.
- Not in rc6: the diagnostics snapshot, image cleanup, C20; the gaps the
  candidate-5 changelog lists under *Not in candidate 5*.

### RC7 — tagged 2026-10-25

- Tag `v0.3.0-rc7` on `73bbe5361bad1ff190d2c27586aad578796f191f`, the release
  branch's tip at the pre-candidate merge (PR #286 from the throwaway copy
  `4PR-8-release-0.3.0`, merged by the owner at `77ac058`).
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc7`; record at
  `/opt/devcapsule-gate/rc7-release-protocol.json`.
- Backend run [40198740279](https://github.com/ccozianu/devcapsule/actions/runs/40198740279)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc7)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc7`:
  the checksum file verifies the executable, SHA-256
  `1fe418a2c453c9640996bf8fbc86005c6b7e7de1518a5977b050a180a7ca7a91`; the
  manifest records the tag, the branch, the source revision, the
  `mainline` disposition and, as its base reference, the published
  recipe-11 digest `8c97d308…`; `devcapsule version` from an empty
  directory reports `0.3.0rc7`, build `v0.3.0-rc7`, at `73bbe53…`.
- Next: the owner's test of the download on a regenerated lock, the
  console on the published base first; then the diagnostics snapshot,
  image cleanup and C20 for the next candidate; the documentation
  language review before the final tag.

How the candidate was prepared:

- Carries, beyond rc6: the published recipe-11 base pinned in the matrix
  (PR #284, `dedb485`): `v0.3.0-rc6`, `ubuntu-24.04@11`, digest
  `8c97d308…`, newest pin of the family; matrix `embedded-28`; the golden
  locks and this repository's lock regenerated onto it; the lock's base
  table records the recipe's source path so consent links it; the
  recipe-9 pin kept, with a test that its locks still resolve.
- The release branch's tip after the owner's merge of PR #284 is
  `349b3ad`, whose tree is the reviewed `dedb485` plus the status entry.
  Full gate on it from a separate worktree: mypy clean over 246 files,
  2282 unit tests passed, 36 deselected, 2 xfailed, packaging integration
  17 passed, the web console session mypy clean over 9 files with 357
  tests passed; the documentation contract 189 pages, passed.
- Not in rc7: the diagnostics snapshot, image cleanup, C20; the gaps the
  candidate-5 changelog lists under *Not in candidate 5*.

### RC8 — tagged 2026-10-26

- Tag `v0.3.0-rc8` on `8d41fabe9f7ecc439e6854a0e89e9a9586fd4edf`, the release
  branch's tip at the pre-candidate merge (PR #291 from the throwaway copy
  `4PR-9-release-0.3.0`, merged by the owner at `8afa5f6`).
- Candidate gate from a detached checkout of the tag before the push:
  method `mainline`, no unintegrated commits, version `0.3.0rc8`; record at
  `/opt/devcapsule-gate/rc8-release-protocol.json`.
- Backend run [40271738816](https://github.com/ccozianu/devcapsule/actions/runs/40271738816)
  passed; the [prerelease](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc8)
  is public, non-draft, with the three assets.
- Downloaded over HTTPS into `/home/devcapsule/.cache/devcapsule-releases/v0.3.0-rc8`:
  the checksum file verifies the executable, SHA-256
  `5f1f8429351f0acf4a86bcaf92eb1cccaf6e26b0bb281a28c66c93d546ac8e6a`; the
  manifest records the tag, the branch, the source revision, the
  `mainline` disposition and, as its base reference, the published
  recipe-11 digest `8c97d308…`; `devcapsule version` from an empty
  directory reports `0.3.0rc8`, build `v0.3.0-rc8`, at `8d41fab…`. With
  the downloaded executable, `project init --regenerate` on a copy of the
  trading sample reported *Migrated ... to schema 2* and wrote the
  `required` form with the IDE as the recommendation; the same command
  with rc7 had left the file at schema 1.
- Next: the owner's regeneration of this repository's, the website's and
  the samples' manifests; then the diagnostics snapshot, image cleanup
  and C20 for the next candidate; the documentation round before the
  final tag.

How the candidate was prepared:

- Carries, beyond rc7: the manifest's two schemas as classes (PR #289,
  reviewed by PR #290, accepted without a round): `ManifestV1`,
  `ManifestV2`, `read_manifest` and `upgrade` in one module, every
  consumer reading schema 2; `project init --regenerate` writes a
  schema-1 manifest as schema 2 with its leading comment block kept and
  says so, a schema-2 manifest stays byte for byte, a plain `init` writes
  neither; the IDE a schema-1 file required becomes the project's IDE
  recommendation and each developer may choose another; the retired
  SDK-major table and the root `workflow-type` are never written again;
  legacy locks are recognized by their own evidence and matrix generation.
- The release branch's tip after the owner's merge of PR #289 is
  `9e4a2a8`, whose tree is the reviewed `f4d0566` plus the status entry.
  Full gate on it from a separate worktree: mypy clean over 248 files, 2338 unit tests passed, 36 deselected, 1 xfailed, 1 xpassed, packaging integration
  17 passed, the web console session mypy clean over 9 files with 357
  tests passed; the documentation contract 189 pages, passed.
- Not in rc8: the diagnostics snapshot, image cleanup, C20; the gaps the
  candidate-5 changelog lists under *Not in candidate 5*.

## Release Notes Preparation

Write `notes.md` beside this file before the final tag: plain Markdown for
adopters, what changed for them, compatibility exceptions with remedies,
the tested agent versions and holdbacks from the freshness review, the
deferred items. C20, the last slice of the cycle, makes the notes block and
the manifest promotion need no operator step.
