# Workstream Current Status: Component Catalog

Mnemonic: `component-catalog`

Start date: 2026-08-30

State: active 2026-11-25; checking all existing components for version upgrades on `ws-component-catalog/version-upgrades` targeting `release-0.3.1`; `gh` and `gcloud` queued next for `release-0.3.1`

Definition read: WORKFLOW.md@196d3760f99e, WORKFLOW-LOCAL.md@5b0f27c04de1

Branch association: `ws-component-catalog/version-upgrades`, forked from `origin/release-0.3.1` (`82a83b9a`)

Integration target: `release-0.3.1`

Delivery method: pull request, merge commit; owner operates the GitHub UI

Requirements: `R-PRODUCT-001`, `R-PRODUCT-002`, `R-SCOPE-001`, `R-DOCKER-001`, `R-DOCS-002`

## Goal And Scope

Maintain the optional IDE/tool component catalog and shared noVNC smoke harness.
The owner requested Eclipse IDE for Java Developers on 2026-10-04, following
IntelliJ/Rider, with a recorded Playwright smoke. The owner then requested an
update to today’s blog with the latest accomplishments and screenshots/movies.
The owner then reported `project run` rejecting Playwright and requested a
local workflow rule to prevent this. The 2026-10-05 correction establishes
command-only configuration writes, validation by the running `devcapsule0`,
a managed self-hosting exception and mandatory/optional capability handling
for all adopters. Implement the accepted configuration contract at the owner’s explicit request on
2026-10-06: shared required/optional capabilities, SDK-major constraints, local
IDE/agent selection, conservative CLI writers and tolerant readers. No task or
workstream-specific capability profiles. New/changed code coverage must exceed
90%, aiming for complete coverage; document the system ab initio in docs/.
No release or website publishing.

## Current State

- 2026-11-25. Resumed `component-catalog` on `ws-component-catalog/version-upgrades` off `origin/release-0.3.1` (`82a83b9a`, after Xfce Terminal PR #62 and PR #72 merged). Acknowledged three `project-management` items targeting `release-0.3.1`:
  1. All-component version-upgrades sweep (active first slice).
  2. `gh` (GitHub CLI) optional component (queued next).
  3. `gcloud` (Google Cloud CLI) optional component (queued after `gh`).

- 2026-11-18. At the owner's request, the terminal addition from
  [PR #60](https://github.com/mycodespace-ai/devcapsule/pull/60) now targets
  0.3.1. The release branch at `5c222388` includes Graphviz and its own
  resolution test layout. Matrix `embedded-35` resolves the terminal with
  Graphviz and Codex on amd64. The release driver owns the merge.

- 2026-11-18. The owner selected Xfce Terminal as a tabbed desktop IDE with
  the exact configuration value `xfce4-terminal`. The fresh branch started
  at `deffc8fe`, the accepted mainline, so it needed no synchronization.
- Accepted project-management's GitHub CLI component for the backlog after
  the terminal. Its scope includes pinned acquisition, persistence and secret
  binding for authentication, and a read-only API smoke.
- Accepted the V1 assignments. Support component-upgrades with the bounded
  validation inventory and its init/config review. Maintain the plain-language
  catalogue terminology audit. The release driver owns the per-release component
  sweep. Continue manual evidence curation through the successor to 0.3.1.
  Component-upgrades owns the later evidence submission and automation work.

- 2026-10-08, after the pause: the owner merged
  [PR #171](https://github.com/ccozianu/devcapsule/pull/171) into
  `ws-component-catalog/intellij-idea` at `4575eae` (10:04 UTC) and then
  [PR #170](https://github.com/ccozianu/devcapsule/pull/170) into `main` at
  `6ae1a01` (10:42 UTC). The workstream branch is fast-forwarded to `main`
  (`3dfeece`); the review branch `ws-component-catalog/intellij-idea-correctness`
  is fully contained in `main`. The omission bug record is closed on its stated
  condition; the Playwright record stays `fixed` pending the owner's `project
  run` confirmation. The owner directed the pair to `project-management`; this
  entry records the integration only, no source changed.
- 2026-10-08, Codex re-review at `522f239`: all three original independent
  counterexamples now pass; the revised consent, artifact-pinning and preview
  freshness paths address the findings without discarding hidden pins. The
  retained-consent regression is also covered in the branch's tests. No further
  blocking finding. Accepted for integration through
  [PR #171](https://github.com/ccozianu/devcapsule/pull/171) into
  `ws-component-catalog/intellij-idea`, with a merge commit as authorized by
  the owner. PR #170 is not approved or merged by this acceptance.
- The full-composition fingerprint is an accepted conservative tradeoff for
  ephemeral previews: metadata-only changes can require a fresh preview, while
  execution/known-good identities remain unchanged. Old previews lacking the
  fingerprint safely require regeneration. The note now explicitly excludes
  rollback from the persistence claim. No source changes made in this re-review.
- Entry: zero commits behind main and unchanged workflow; no synchronization
  needed. No waiting mail or undecided intake. Both owned bug records remain
  fixed pending their documented closure conditions; the omission record calls
  for integration of both #171 and #170. The existing IDE edit stays uncommitted.

- 2026-10-08, response to the Codex review of PR #171 (Claude Fable 5.1). All
  three findings were valid and are fixed on the review branch: `babbb96` adds
  four reproducers (the two Codex counterexamples, the retained-consent variant
  and the stale-preview case) that fail at `236fa3c`; `e9be77a` makes `select`
  read consent declarations from the admitted projection, pin artifacts on the
  projection and write only active entries back, and refuse a preview whose
  composition fingerprint no longer matches. Hidden and opaque entries are
  carried unchanged. `set_id` and known-good identities are untouched. The
  follow-up note now states the converse invariant (consumers act on the
  projection) and qualifies the persistence claim to the two command writers,
  rollback excluded. Nothing was pushed back: each counterexample reproduced
  as described.

- 2026-10-08, owner-directed Codex review of PR #171 at `7c8e355`:
  original six defects independently reproduced on test-only commit `3bc9eb6`;
  all 252 capability-policy, version-set and upgrade-recovery cases pass on
  the proposed tree. Composition/projection separation is justified, but
  [changes requested on #171](https://github.com/ccozianu/devcapsule/pull/171#issuecomment-6056998885):
  version selection reads omitted acquisition declarations and crashes for
  absent Antigravity consent; artifact pinning attempts acquisition of an
  unsupported optional provider. Both new counterexamples pass before the
  fix and fail on the PR. A third counterexample shows preview freshness
  ignores changed hidden pins and silently persists their old versions.
- Next reviewer/author should fix those boundaries, add the counterexamples
  as regressions, and qualify the universal persistence claim that excludes
  rollback. Reproducer code and proposed corrections are in the PR comment;
  scratch evidence is under `/opt/devcapsule-gate/pr171-review/`. No source
  or test changes were made by this review. Existing rollback, corrupt-pin
  recovery and proposal-export product threads remain for later discussion.
- The owner explicitly authorized review/acceptance or comments on #171 via
  the newly available `gh`; #170 stays for the human after #171 is resolved.
  Activate with `source /opt/xtras/miniconda3/etc/profile.d/conda.sh` then
  `conda activate gh`, without shell-startup-file edits. Both agents use the
  PR author's GitHub account, so the review is a PR comment, not a formal
  self-review. No PR was merged. Entry synchronization: zero commits behind
  main, unchanged definition/local workflow; nothing to synchronize. No mail
  or undecided intake. Owned bugs remain omission/version-set (fixed pending
  acceptance) and Playwright launcher compatibility (fixed pending host acceptance).

- 2026-10-08, owner-directed correctness review of the configuration slice
  (Claude Fable 5.1), on review branch `ws-component-catalog/intellij-idea-correctness`
  branched from this workstream's branch, proposed as a pull request into
  `ws-component-catalog/intellij-idea` because the reviewing environment has
  no GitHub token to comment on PR #170 directly. The owner asked for failing
  unit tests before each fix; the branch has three commits: showcase tests,
  fix, records.
- Fixed the confirmed omission/version-set defect by separating the checkout's
  persistent selection (`compose_lock`) from its execution projection
  (`usable_lock`); only the projection applies omissions and every version-set
  writer persists the selection. The same review found and fixed three smaller
  defects: locally selecting a project-optional tool re-pinned it from the
  catalog instead of following the shared lock; a corrupt local pins document
  crashed `config capabilities --local` with a traceback; `init --local
  codex-agent` without an IDE was refused while `config capabilities --local`
  accepted it. One message now names an unavailable local selection as such.
  `configure` is split into project and local halves; the version-set
  workspace carries the composition beside the effective lock.
- Argument and limits are in the commit-pinned
  [follow-up note](../../implementation-notes/devcapsule/2026-10-08-configuration-composition-correctness.md);
  the 2026-10-06 argument keeps its snapshot and now points at it. The bug
  record is `fixed`, to be closed by the owner on merge. The user guide states
  that an omission hides a tool without changing the selection.
- Judgment call recorded: the review branch is not a registered workstream
  branch. The owner directed it explicitly as the delivery vehicle for review
  comments on PR #170; the workstream's branch association is unchanged, and
  the records below are edited on the review branch so they travel with the
  change they describe.

- Renamed the configuration format module to `file_formats.py`, with
  `ConfigurationFileKind`, `validate_file_format` and `render_toml` replacing
  vague names. Rewrote its docstrings to describe checks, TOML output and hashes
  directly; updated callers, tests and the source-layout guide. Behavior is
  unchanged. The historical correctness argument keeps its commit-pinned links.

- Owner requested readable contracts at the code definitions. Added docstrings
  for capability values, their fields/methods, selection and command functions,
  and the matrix's provider/SDK queries. Examples explain capability names and
  `sdk_major` pairs; contracts state validation, return values and write effects.
  This changes docstrings only; the omission/version-set defect remains open.

- Completed the owner-requested [commit-pinned correctness argument](../../implementation-notes/devcapsule/2026-10-06-configuration-correctness.md)
  for implementation and tests at `99ff26ac564368427f77773ac0a4c2beaa257eea`.
  Source and tests are unchanged by this documentation review.
- Review reproduced a [local version-set omission defect](../../bugs/devcapsule/2026-10-06-optional-omission-loses-local-version-pin.md):
  clearing an optional omission does not restore its discarded provider/pin.
  Owned here, confirmed, no fix yet; this qualifies the earlier completion claim.
  The passing tests cover the separate behaviors but miss their interaction.
- No new mainline synchronization: the argument concerns the exact entry commit,
  entry brief reported zero commits behind main and the definition was current.
  No waiting mail or intake on entry.

- Owner-assigned configuration implementation is complete in this branch:
  project required/optional capabilities, explicit Python/.NET SDK-major checks,
  developer-local IDE/agent/tool pins and optional omissions; no task/workstream
  profiles. New project creation uses `init --required`; changes use
  `config capabilities`, with preview and interrupted-edit recovery. `config check`
  validates candidate/shared documents and artifact metadata without writes.
- Readers preserve shared bytes while omitting unsupported optional capabilities.
  Optional-only contributions reconcile at launch when the mandatory baseline and
  local answers are unchanged. Optional download failures can reduce one run;
  mandatory dependencies and integrity failures cannot be waived. A reduced run
  does not certify the full stored environment as known-good.
- Local version pins for retained tools and all host decisions survive local
  reselection. Following shared versions retains personal capabilities. SDK
  constraints are checked again on local version-set selection and base overrides.
- The ab-initio [capability guide](../../../docs/configuration/capabilities.md)
  explains ownership, commands, validation, recovery and reader rollout. Legacy
  `need` inputs/commands remain available; shared IDE/agent declarations must be
  deliberately migrated. Fresh policy creation has no implicit IDE or agent.
- No reply arrived to the optional IDE-default question: used the proposed
  developer-choice behavior. Missing IDE selection gives an actionable command.
- Merged origin/main at `1eb8e76` via `710fd04` before implementation. The owner
  explicitly assigned this slice here, superseding the earlier maintenance
  handoff; maintenance/project-management were notified by coordination mail.
  No new intake items; the one previously fixed owned bug still awaits host acceptance.
- Existing self-hosting manifest/lock and running `devcapsule0` are unchanged.
  Current baseline identifies 0.2.16.dev0-local-linux-x86_64, source unknown.
  The new source CLI accepts the existing shared contract via read-only check;
  this is offline validation, not a new container launch. Adopting the new
  representation on this host still needs the baseline/candidate transition
  and independent restart path in R-CONFIG-001. No release/version bump.

### Earlier checkpoints

- Owner correction is canonical in accepted [R-CONFIG-001](../../requirements/product/r-config-001-conservative-writers-tolerant-readers.md)
  and the rewritten local rule. Conservative writers, tolerant readers,
  mandatory/optional needs and graceful local degradation are product direction;
  exact schema/commands remain implementation work. The previous blanket
  released-vocabulary rule is superseded; current guards are interim protection
  for today's required-only configuration.
- Sent `2026-10-05-component-catalog-conservative-writers-tolerant-readers.md`
  to project-management and maintenance, correcting the prior planning handoff
  and identifying missing command-based mutations/candidate validation. No
  configuration, launcher or runtime was changed in this follow-up.
- At the 2026-10-05 checkpoint main was `242e13e`, zero commits behind and no definition change on entry;
  no synchronization needed. One owned bug remains fixed pending host acceptance.

- Owner follow-up: recovered the host launch using an already-built executable
  in the shared `dist` folder, then directed the lessons toward a 0.3 release.
  Exact executable identity remains unknown. This recovery does not validate
  the separate released-launcher rollback path or constitute a blanket decision
  to require development builds for every checkout.
- Sent `2026-10-04-component-catalog-0-3-launcher-bootstrap-lessons.md` to
  `project-management` by coordination mail: owner’s 0.3 direction, evidence,
  and agent-proposed compatibility, safe-transition, independent recovery and
  cold-restart acceptance requirements. Detailed scope, owners, timing and the
  relationship to 0.2.16 are pending release planning. No version was bumped.
- The prior 0.3 direction follow-up changed records only; its content check passed.

- New owned bug: [unreleased Playwright breaks checkout launch](../../bugs/devcapsule/2026-10-04-unreleased-playwright-breaks-checkout-launch.md).
  The original component commit also changed the shared need and lock, making
  the checkout depend on a launcher that has not shipped in a final release.
- Restored `.devcapsule/devcapsule.toml` and the platform lock byte-for-byte
  from `ada153c^`; other pins and the Playwright component/tests are unchanged.
  No generated lock fields were hand-patched, and no host launcher was replaced.
- Added the local shared-checkout compatibility rule and two regression guards
  against final v0.2.15's frozen capability/component vocabulary. The owner
  has since clarified that self-hosting with a development build is an allowed,
  managed exception and optional capabilities need tolerant consumption.
- Entry synchronization fast-forwarded to accepted main `242e13e`; the blog
  update is integrated in PR #167. Definition unchanged; no waiting mail or
  intake and no previously open owned bugs. The new bug is owned here because
  it was introduced by this workstream’s catalog/bootstrap change.

- Today’s existing blog is now **An AI takes our IDEs for a test drive**, with
  the .NET CLI build, Rider’s activation limit, Eclipse’s WebKitGTK fix and
  accepted save. Four screenshots and three original movies are linked.
  Existing media is reused without duplication or alteration; movie/report
  links use verified mainline `ff6fde1`. Filename/URL and draft flag are retained.

- `eclipse-ide` selects Eclipse Java Developers 2026-09 R; `java-ide` remains
  IntelliJ. The whole package and native WebKitGTK dependencies are pinned and
  verified; native packages install offline with build networking disabled.
- Runtime uses the ordinary capsule user, a read-only install, persistent home
  configuration and the separate `eclipse/workspace` state slot. The component
  discovery adapter reads stable Java package availability, without auto-upgrades.
- Accepted smoke `20261004T090121Z-ea0a5b` saved a marker through noVNC/Playwright,
  independently checked it on disk and visually recognized the editor. Original
  movie and final screenshot are committed with the permanent record below.
- Implementation: `370abad`, native-library/harness correction `f926036`.
  The accepted executable identifies `f926036` and matches the child checksum.
- Eclipse is integrated through PR #166; remote main contains `d79b967`.
  The blog follow-up was based on `ff6fde1`; this repair starts at `242e13e`.
  No workflow declaration/version was changed.

## Planned Next Step

1. Check all existing catalog components for version upgrades on `ws-component-catalog/version-upgrades` targeting `release-0.3.1`, deliver verified pin upgrades, and record per-component outcomes.
2. Implement `gh` (GitHub CLI) and `gcloud` (Google Cloud CLI) as available optional components targeting `release-0.3.1`.
3. Existing rollback, pin recovery, and proposal-export questions remain in Open Threads.

## Validation And External State

- The rebased `v0.3.1-local-linux-x86_64` executable passed the amd64 browser
  smoke on the published base: two independent tab shells in the checkout,
  a saved Vim edit, and clean exit after closing the last shell. All 25
  release matrix integration cases passed, including the new terminal lock.

- Xfce Terminal, 2026-11-18. The packaged CLI initialized and ran a fresh
  amd64 checkout against the published recipe-11 base. Playwright opened a
  second tab, checked separate shell PIDs and the project path in both,
  saved a file with Vim and closed both shells. The launcher returned zero.
  The recording and screenshot are under
  `devcapsule-src/tests/e2e/evidence/xfce4-terminal-tabs/`. Switching an
  existing PyCharm checkout to the terminal retained its Codex capability.
  The build and web console suites, docs contract and resolution-loader
  integration check passed. The release owner has the PR for review.

- Codex acceptance recheck at `522f239`: the three independent PR-review
  counterexamples pass. Full `nox -s build` passed with 1,257 passing unit
  cases, one xfail, one pre-existing non-strict xpass, ten packaged integration
  cases, types, syntax/version checks, source/PEX smokes and content contract.
  Log: `/opt/devcapsule-gate/pr171-review/acceptance-build.log`. No containers,
  self-hosting configuration changes or host-launcher replacement were needed.

- Codex-review response: full `nox -s build` passed on the revised tree
  (1,257 unit cases, ten packaged integration cases, mypy, syntax/version
  checks, source/PEX smokes and content contract). Log:
  `.git/correctness-review-build.log`. The four new reproducers fail at
  `236fa3c` and pass at `e9be77a`; the earlier eight still pass.

- Codex review handoff: full `nox -s build` passed (1,253 passing unit cases,
  one xfail and one pre-existing non-strict xpass, ten packaged integration
  cases, types, syntax/version checks,
  source/PEX smokes and documentation contract). Log:
  `/opt/devcapsule-gate/pr171-review/build.log`. This validates the existing
  automated gate; it does not invalidate the three additional counterexamples
  posted on #171. Only workstream/root status records changed in this handoff;
  the pre-existing `.idea/project.iml` edit remains untouched and uncommitted.

- Correctness review fix: full `nox -s build` passed on the review branch
  (1,253 unit cases, ten packaged integration cases, mypy, syntax/version
  checks, source/PEX smokes and content contract). Log:
  `.git/correctness-review-build.log`. The six showcase tests fail at `17289b9`
  and pass at the fix; two deselection guards were added with the fix. Branch
  coverage of the changed modules under the focused suites: selection 99%,
  commands 97%; the uncovered arcs are named in the follow-up note. The
  reviewing environment pushes over SSH and has no GitHub API token; the
  review PR #171 was opened with `gh` once the owner installed it, and the
  findings were posted as a comment on #170.

- Configuration naming cleanup: full build gate passed (1,245 unit cases,
  ten packaged integration cases, types, syntax, source/PEX smokes and content
  contract). Log: `.git/config-file-formats-build.log`. The renamed module has
  92% combined line/branch coverage. AST comparison of all 40 affected Python
  files confirms only the declared renames and docstrings changed; test
  assertions and file formats retain their behavior.
- Sent maintenance `2026-10-06-component-catalog-configuration-format-names.md`
  with a patch for its report's source link and symbol names. The IDE's
  incidental edit to that report was reverted; maintenance owns its disposition.
  No waiting mail on exit. The existing `.idea/project.iml` edit is untouched.

- API documentation correction: full build gate passed, including 1,245 unit
  cases and ten packaged integration cases. Log: `.git/capability-api-docs-build.log`.
  AST comparison confirms all four Python changes are docstrings only; runtime
  behavior and tests are unchanged. Existing xfail/xpass outcomes remain.

- Correctness-review checkpoint: required full `nox -s build` passed again
  (1,245 unit cases, ten packaged integration cases, type/syntax/version checks,
  source/PEX smokes and content contract). Log: `.git/config-correctness-build.log`.
  All 44 commit-pinned source ranges and new relative links were checked against
  Git/the filesystem. Source, tests and `.devcapsule` configuration are unchanged.
  The isolated counterexample is documented; a passing gate does not close it.

- Final full `nox -s build` passed: **1,245 unit tests**, ten packaged-executable
  integration tests, mypy, syntax/version checks, source/PEX smokes and documentation
  contract. Log: `.git/config-policy-build.log`. One pre-existing xfail and one
  pre-existing non-strict xpass remain; no skipped gate or new container launch.
- New policy suite: **87 tests**, covering ownership, malformed/unknown inputs,
  SDK mismatches, mandatory dependency closure, optional-only launch reconciliation,
  download versus integrity failures, no-write preview/check, preservation of
  opaque optional pins, local version pins and consent, crash endpoints and
  conflicting edits. The packaged PEX also authors and validates an isolated
  project and rejects an incompatible SDK major without changing shared bytes.
- Changed production-code coverage against merge `710fd04`: **574/574 executable
  lines (100%)**, **199/204 branches (97.55%)**. Measured from the full unit suite,
  Coverage.py JSON and zero-context Git diff; `.git/measure-config-coverage.py`,
  `.git/config-policy-coverage.json`, `.git/config-policy-diff-coverage.json` retain
  the local calculation. Tests establish these finite cases and invariants;
  coverage is not a proof that every possible environment is defect-free.
- Pure configuration dependency checks were extended for the new modules and
  pass. The initial architecture violation and legacy base-override regression
  were fixed; no existing checks were weakened. The documentation frontmatter
  was corrected to conform to the existing content contract.
- Local artifact: `devcapsule-src/dist/devcapsule-local.pex`, built and exercised.
  The dirty-tree gate intentionally leaves public `dist/devcapsule.pex` alone.


- Revised-rule/requirement full gate passed: 1,152 tests, nine packaging checks,
  type checks, source/PEX smokes and content contract. Log:
  `.git/config-contract-build-20261005.log`. Only rules, requirements, indexes
  and records changed; the project manifest and platform lock are unchanged.

- `devcapsule0 project config list` exit 0: recorded launcher inspection only,
  not launch/candidate validation. CLI identity: `/usr/local/bin/devcapsule0`,
  0.2.16.dev0 local-linux-x86_64, source unknown. `need` adds capabilities;
  `resolve` writes and requires launcher context. Help exposes no removal,
  classification or read-only candidate-validation command. Local log:
  `.git/devcapsule0-config-preflight-20261005.log` (not published).

- Repair full `nox -s build` passed: 1,152 unit tests, nine packaging checks,
  mypy, CLI/PEX smokes and content contract. Log: `.git/launcher-compat-build.log`.
  This resumed environment lacked the documented scratch parent; `/var/tmp`
  also proved too small. Recreated `/opt/devcapsule-gate` on the large overlay,
  removed only this attempt’s alternate scratch, and passed without code fixes.

- New capability/lock guards failed before repair, then all 43 focused
  compatibility/resolution tests passed. Isolated v0.2.15 tagged source
  reproduced the exact error and accepted the restored pair through runtime
  planning. Log: `.git/launcher-compat-tagged-source.log`. This did not execute
  the published release binary or launch a container.

- Blog render check: draft preserved, four images resolved as site assets and
  three distinct movie links. All pinned evidence links exist at the cited
  mainline commit; original movie SHA-256 values match the acceptance records.
  Both added screenshots were visually reviewed. No new GUI run was needed.
- Previous blog follow-up full gate passed; `.git/ide-blog-build.log`.

- Previous Eclipse full gate passed: 1,150 tests and nine packaging checks.
  Logs and original acceptance details remain in the permanent validation record.
- The saved-edit smoke used the child's Playwright component with a deliberately
  unavailable parent browser path. Both model driver and recognizer used the
  existing Codex/GPT-6 Astra harness. Log: `.git/eclipse-accepted-smoke.log`.
- Owned test containers, workspaces and checkout records are removed. Acquired
  artifacts and materialized images remain reusable caches. Scratch and the
  exact accepted executable remain under `/opt/xtras/eclipse-work`.
- Raw evidence stays in `devcapsule-src/dist/e2e-evidence/ide-smoke/`; desktop
  access tokens are not published. The movie is retained as original WebM.
- Two packaging checks transiently read local editable metadata instead of the
  release executable's wheel; maintenance received reproduction, proposed fix
  and the successful final-gate follow-up by mail. No unrelated fix was committed.

## Open Threads

- The amd64 graphical smoke covers separate shell tabs, working directory
  and shutdown. ARM64 has pinned packages and awaits a native desktop smoke.

- #171 and #170 are merged, checked on 2026-10-08 after the pause; the GitHub
  merge records are the integration evidence. No request to Fable or Codex is
  outstanding on either PR.
- Full-composition preview fingerprinting is deliberately conservative and
  accepted; a narrower digest is not needed for this slice. Re-review found
  no additional blocking defect. Counterexamples remain in the PR discussion
  and regression suite; no raw session transcript is retained.

- Product decisions surfaced by the review, not taken: (1) `versions rollback`
  re-persists an execution snapshot, so a rollback to a run that omitted an
  optional tool bakes the omission in; fixing it needs the composition recorded
  beside the known-good lock. (2) A corrupt local pins document is refused and
  left intact; there is no command-only recovery. (3) `versions proposal`
  exports the effective lock, so personal IDE or omission state appears as a
  project change; pre-existing and outside the slice's diff.
- The `--local` selection of a tool the project already declares now follows
  the project's pin; the owner may prefer refusing such a selection outright.

- API documentation correction leaves the user's pre-existing `.idea/project.iml`
  edit untouched and uncommitted. No other source changes were present on entry.
  Entry brief again reported zero commits behind main and no definition changes;
  no synchronization was needed for this follow-up.

- The correctness review is complete; the implementation has a confirmed open
  omission/version-set defect. No fix or test modification is hidden in the
  documentation checkpoint. The exact isolated reproduction is in the bug record.
  The follow-up should separate persistent selected pins from runtime filtering;
  detailed implementation alternatives have not yet been investigated.

- Awaiting owner PR integration and release sequencing. The implemented contract
  requires a reader containing it; binaries already shipped cannot learn it
  from configuration. Host rollout and a real next-session launch are not claimed.
- SDK-major knowledge is explicit catalog data (currently Python and .NET).
  Extra providers are not installed by naming an arbitrary model/vendor.
- No additional product decision is needed to review this implementation. The
  IDE-default question was optional; no implicit default was selected.

- Awaiting the human: compatibility-repair PR merge, host launcher identity
  and confirmation of `project run`. Blog editorial release and existing website
  video-publication follow-up remain; Eclipse #166 and blog #167 are on main.
- No new assets or website implementation changes; screenshots render through
  the existing content contract and movie links open/download original WebMs.
- Earlier IDE validation limits: Java build/debug, Maven/Gradle builds,
  Marketplace installation and restart preference acceptance are not claimed.
- Rider licensed-editor acceptance remains unverified as recorded in its report.
- Raw transcripts stay local. No verbatim session record was requested. Existing
  `.git/recovery/` files and the website gitlink remain untouched.

## Workstream Document Index

- [Commit-pinned implementation and test correctness](../../implementation-notes/devcapsule/2026-10-06-configuration-correctness.md) — owner-requested review
- [Persistent selection versus execution projection](../../implementation-notes/devcapsule/2026-10-08-configuration-composition-correctness.md) — fix argument, commit-pinned
- [Optional omission loses local version pin](../../bugs/devcapsule/2026-10-06-optional-omission-loses-local-version-pin.md) — closed 2026-10-08 on the merge of #171 and #170

- [Capability system guide](../../../docs/configuration/capabilities.md) — ab-initio user documentation

- [Conservative writers and tolerant readers](../../requirements/product/r-config-001-conservative-writers-tolerant-readers.md) — accepted 0.3 direction

- [Shared-checkout Playwright regression and recovery](../../bugs/devcapsule/2026-10-04-unreleased-playwright-breaks-checkout-launch.md) — current slice

- [Eclipse package, native libraries, movie and validation](../../implementation-notes/devcapsule/2026-10-04-eclipse-validation.md) — current slice acceptance

- [SDK/Rider provenance, commands, evidence and limitations](../../implementation-notes/devcapsule/2026-10-04-dotnet-rider-validation.md) — acceptance and resumption
- [Repeatable E2E commands](../../development/e2e-tests.md#rider-and-net-sdk-smoke) — run the smoke
- [IntelliJ completion snapshot](2026-10-04-record-intellij-completion.md) — previous slice history and retained follow-ups
- [IntelliJ/Playwright validation](../../implementation-notes/devcapsule/2026-10-04-intellij-playwright-validation.md) — earlier accepted GUI runs
- [Accepted IntelliJ work order](../../work-orders/2026-10-03-playwright-intellij-agent-smoke.md) — original scope
- [Blog draft and movies](../../blog/2026-10-04-an-ai-takes-intellij-for-a-test-drive.md) — owner editorial review
- [Intake decisions](intake-dispositions.md) and [intake](intake/README.md) — coordination
- [Historical Antigravity status](2026-10-03-record-antigravity-status.md) — earlier delivery history
- [Antigravity license analysis](antigravity-cli-license-and-redistribution-analysis.md) — licensing reference
- [Historical release-candidates proposal](release-candidates-proposal.md) — retrospection
