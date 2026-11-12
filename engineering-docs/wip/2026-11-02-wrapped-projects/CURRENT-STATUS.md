# Workstream Current Status: Wrapped Projects

Mnemonic: `wrapped-projects`

Start date: 2026-11-02

State: active; PR1 (#333) complete and accepted by the owner 2026-11-03, awaiting merge; the project-capabilities design is handed to workflow-improvements by mail

Definition read: WORKFLOW.md@d2ccbbe43dfa, WORKFLOW-LOCAL.md@65501b3407db

Branch association: `ws-wrapped-projects/wrap`, forked from `origin/main` at 31d44fa473a8

Integration target: `main`

Delivery method: pull request, merge commit, under the Pair Review Loop with Codex as the review partner; PR1.1 (#334) merged 2026-11-02

Requirements: R-CONFIG-001, R-SCOPE-001; a new requirement for the wrapped-project shape is a deliverable

Work order: [wrapped projects](../../work-orders/2026-11-02-wrapped-projects.md), issued 2026-11-02 by the owner and accepted as this workstream's goal

## Goal And Scope

Let a developer wrap a foreign repository, one that is not theirs and carries no DevCapsule
configuration, in a small wrapper repository of their own, as a submodule, and work on it in a
capsule with three commands. The showcase is an FRC learning project around Mechanical-Advantage's
public robot code. The work order holds the owner's rulings; this file holds the state.

## Current State

**2026-11-02, opened.** The owner described the feature and ruled on its shape in conversation.
The work order records the rulings. Preparation evidence from inside the 0.3.0 capsule:

- A shallow clone of RobotCode2025Public, Gradle 8.11 through its wrapper, under the capsule's
  Temurin 25.0.4+7: `BUILD FAILED`, `Unsupported class file major version 69` during the
  build script's semantic analysis, before any Java compiled. Exit 1 after 2m 5s, most of it
  the Gradle download.
- The same build under Temurin 17.0.21+9, downloaded into the session scratch and selected
  with `JAVA_HOME` and `PATH` only: `BUILD SUCCESSFUL in 10m 55s`, 25 tasks executed,
  `compileJava`, `test` and `check` among them, exit 0. The foreign tree was clean afterwards
  even though the project's own build runs `spotlessApply` before compiling. The Gradle cache
  under the capsule home grew to 1.4 GB; the design's section 7 is why that is paid once.
  Both runs were made in this capsule's shell, not in a child capsule: no base with a second
  JDK exists yet, and the question needed one build each. Conclusion: the JDK line is the
  whole difference, and `JAVA_HOME` plus `PATH` is a sufficient selection mechanism.

**2026-11-02, the sample repository.** The owner created
`git@github.com:ccozianu/devcapsule-sample-frc-learning.git` for the showcase wrapper. The
wrapper the three commands produce is pushed there; the work order records it.

**2026-11-02, the owner's ruling and slice 1.** The owner read the design and said to run
with it in this capsule; the recommendations of the design note are taken as decided, and
the release target is the next minor after 0.3.0 until the owner names it. Slice 1 is
PR1, [#333](https://github.com/ccozianu/devcapsule/pull/333), against `main`: the
`[sources]` declaration, `declare_source`, `project wrap` with its detection and guidance
files, the `config show` rows, the user page, the CLI reference, R-WRAP-001 and the
R-CONFIG-001 section. The Codex + gpt-6-astra pair reviews it as PR1.1 from
`ws-wrapped-projects/wrap-review` in `~/worktrees/wrapped-projects-review`; the brief is
[evidence/2026-11-02-pr1-brief-codex.md](evidence/2026-11-02-pr1-brief-codex.md).

### Slice 1, judgments

1. The manifest holds only what DevCapsule adds to a source: `upstream` and `java`. The
   origin URL stays in `.gitmodules`.
2. `upstream` present means a fork to change; absent means the upstream to learn from.
3. The toolchain key is per source and named after the capability (`java = "17"`).
4. `wrap` writes nothing inside the submodule and does not install the workflow.
5. Guidance files with the wrap marker are regenerated on every wrap; the owner's own are
   kept and named in the report.
6. The IDE recommendation is added only when the manifest recommends none.
7. Detection covers the showcase only: Gradle, with or without GradleRIO.
8. The submodule's Git directory is embedded by moving `.git/modules/<path>` and editing
   `core.worktree` out of the file, not through repository discovery, which fails on the
   moved directory.

Validation of PR1 in this capsule: `nox -s typecheck` passes over 271 files; the new
tests, 100 in `test_sources.py`, `test_wrap_detection.py`, `test_wrap.py` and
`test_owner_commands.py`, pass; the full `nox -s tests` run is recorded on the PR when it
completes. Three pre-existing failures in `test_capability_commands_v2.py`
(`test_resolution_grants_no_consent_and_no_partial_save`) fail in this capsule with the
slice stashed as well as applied; disclosed on the PR, not fixed here.

**2026-11-02 late, PR1.1 and the owner's two rulings.** The Codex + gpt-6-astra pair's review,
[#334](https://github.com/ccozianu/devcapsule/pull/334), was accepted without a round and merged
at 5a18a5c9: inputs validated before Git writes, submodules found by path (a section name is not
a path), missing registered directories initialized, the embedding asking the submodule for its
own Git directory, recovery messages, the exact first-line marker. Its entity escaping of the
guidance was replaced afterwards by code spans, since agents read the file raw. Then the owner,
in chat, ruled twice: the launcher infers nothing from a foreign tree, so the Gradle detection
is deleted and `wrap` takes `--require` and `--java` (work order amendment 6); and the next
design is higher-level project capabilities, browse, build, test, debug and manage, each settled
or unsettled, with the unsettled ones surfaced by the status as the standing task of the agent
with the user (amendment 7). The four questions put to the owner for that note: one word or two
for the two kinds of capability; whether `browse` is the project's or the IDE's; whether `manage`
is these records or the workflow definition; whether the proving run's evidence is kept.

## Next Resumable Task

1. Done: the final gate on PR1 (#333) at 0a131d69, 2711 passed and the same 18 capsule-specific
   failures as before, is on the PR; PR1 is the owner's to merge. The showcase wrapper is
   regenerated with the final `wrap` and pushed (58d9219).
2. Done: the owner accepted PR1 as it stands on 2026-11-03 and ruled that the project-capabilities
   design is an AI-workflow issue; it went to `workflow-improvements` by mail the same day
   (`2026-11-03-wrapped-projects-project-capabilities.md`). No operations slice here until the
   definition speaks and a work order comes back.
3. Slice 2, at the owner's go at the second stopping point: Temurin 17 in the base under the
   stable names, the session environment from the settled facts, the acceptance run.

## Open Threads

- The release target is the owner's to fix at the first stopping point.
- `project-management` has four items waiting in its mailbox from 2026-10-31; this session
  left them untaken because the owner directed it to open this workstream instead.
- The owner's checkout carries an uncommitted 0.3.0 migration of the dogfood manifest and lock
  (schema 2) and an IDE module file change; they are not this workstream's and travel
  uncommitted.

## Document Index

- [the work order](../../work-orders/2026-11-02-wrapped-projects.md): read first.
- [the wrapped-source design](2026-11-02-design-wrapped-source.md): the manifest shape, the JDK mechanism, the IDE rule, the detection rules; ruled 2026-11-02.
- [evidence/2026-11-02-pr1-brief-codex.md](evidence/2026-11-02-pr1-brief-codex.md): the review brief of PR1; open when reading PR1.1.
- [the project-capabilities design](2026-11-03-design-project-capabilities.md): operations, settled and unsettled, the record, the commands, the discovery dialogue; handed to `workflow-improvements` 2026-11-03, kept here for reference.
- `intake/` and `intake-dispositions.md`: the queue and its log; empty at opening.
