# Workstream Current Status: Presentations

Mnemonic: `presentations`
Start date: 2026-11-16
State: active 2026-11-17; owner-directed recorded-E2E skill for rc4; authoring PR #43 is merged into release and main.
Branch association: `ws-presentations/recorded-e2e-skill` from release `dbfba699`; `ws-presentations/0.3.1-authoring` merged through #43
Branch prefix: `ws-presentations/`
Integration target: `release-0.3.1`
Delivery method: pull request; records published on coordination

Definition read: WORKFLOW.md@196d3760f99e, WORKFLOW-LOCAL.md@94a29cb6eedb

## Goal and agreed use case

Make the proven E2E recording and presentation capability available to LLM agents in other DevCapsule projects.
Provide the existing Markdown instructions and supporting Python/Playwright apparatus without requiring a DevCapsule source clone.

The engineer asks their agent to run E2E with recording and presentation along a scenario:

- In an existing Markdown file supplied by the engineer; or
- Described inline in plain English.

The agent reads the scenario, executes the E2E test, records it and creates the presentation.
When finished, it reports the result and returns a link the engineer opens in that project's DevCapsule web console.
The engineer does not need to point it at this repository or reconstruct the recording process.

## Recorded-E2E skill — 2026-11-17

The owner requested a skill inside this project and a PR for rc4, then explicitly
switched this checkout from maintenance to presentations. Prior PR #43 is merged
at release `c8b56a07` and propagated to main by #49 (`0baf70bd`); rc3 shipped it.
This slice packages a portable skill with the existing authoring kit. It reads
`devcapsule presentations guide` rather than duplicating the recording procedure,
checks prerequisites and returns the real test outcome with a verified console
presentation. No workflow bootstrap/update, recorder redesign or viewer change.

Start from release `dbfba699`, with maintenance's completed rc3 records. Main's
workflow difference is only the development-version stamp; retain the release
baseline and do not merge main into this release-targeted slice. The definition
and local workflow were read. No open bug is owned by presentations.

Accepted project-management mail `2026-11-17-project-management-presentations-intake-decisions.md`:
provide recording/presentation support for the future sample-project release
check, after this skill slice. Sample-projects owns scenarios and project updates;
maintenance owns release enforcement. The first enforcing release, list and pass
criteria await design; this does not create a new 0.3.1 gate. Full work order is
preserved in the mail receipt commit and will reach main through its owner.

## Current state and authority (original authoring slice)

Created at the owner's request after checking the live list, canonical mainline, open/archive directories and remote refs.
No standalone presentations workstream existed. The earlier `ws-capsule-webconsole/presentations` slice is merged.
The owner confirms that the current viewer is already human-validated, including Florin's enthusiastic test.
An agent already recorded an English-specified scenario in another project after the owner pointed it at this source.
Both engineering and prospective-user/tutorial audiences remain in scope; the existing viewer is the accepted baseline.

The owner authorized implementation on 2026-11-16 and selected release 0.3.1.
Pair reviewer: Antigravity `gemini-4-hydrogen-high`, with `--effort high`, verified in `antigravity models`.
The existing viewer and its schema remain the contract.
The broader reusable-processes idea is not assigned wholesale to this workstream.
Project-management delivered the use case and references to both original authoring messages by coordination mail.
Acknowledged that handoff as the goal above; its full text is preserved in the handoff record.
The mailbox and intake are empty after receipt and acknowledgement.
Original correspondence is preserved on `ws-project-management/coordination` at `cac3861e` under its intake directory.
The self-contained handoff names the exact paths and evidence.

## Planned next step

Implement the portable skill, export it with the installed PEX, document
installation and invocation, validate the skill and packaged delivery, then open
a PR against `release-0.3.1`. The human merges; maintenance handles propagation
and rc4. Do not change the authored release version.

## Validation and checkout state

The implementation branch starts at `upstream/release-0.3.1` (`10e7fda3`), carrying only this workstream's registration commits from the former `ws-presentations/authoring`.
Do not synchronize with main: its development-version changes do not belong in this release-targeted slice.
The workflow text differs only in its source-version stamp; its rules were read.
The owner installed the prescribed GitHub CLI. Authentication passed as `ccozianu` on resumption.
Re-fetched upstream: release is unchanged and main differs in workflow only by the development-version stamp.
Keep the release baseline; do not merge next-cycle development-version changes.
The required pre-PR unit session again stopped at the known Docker-group failure after 1438 passes.
No open bug is owned by presentations at registration.
Product changes: `presentations guide`, `export` and `hand-off`; the existing producer is now shipped
and the repository replay harness imports it through an adapter. The portable recording helper accepts
ordinary Playwright callbacks and derives chapters/captions from captured frames. Failed and incomplete
runs keep their outcome and have labelled decks. The viewer is unchanged.

Final validation after merging review PR #46: 148 focused/compatibility tests and 11 integration tests passed;
syntax, mypy (353 files) and conventions (0 breaches) passed. The full gate stopped at the inherited Docker-group failure after 1438 passes and 1 skip (178 deselected).
Separate PEX build/smoke, docs contract (249 pages) and webconsole checks (474 tests) passed.
An unrelated scratch project used only the final exported kit and produced passing, failed and incomplete
recordings; all six chapters played in the viewer extracted from the rebuilt PEX. See the validation record.
The exported example driver also passed its two-step browser run.
Maintenance was notified by coordination mail of the owner-directed 0.3.1 dependency.
No Docker image or capsule was launched. Temporary loopback application and console services were stopped.
The local artifact is a development validation build, not a published release candidate.

## Pair Review

Antigravity `gemini-4-hydrogen-high` with `--effort high` reviewed in its own worktree.
Conversation `861df986-5407-4636-8a5d-3a2d26da53fc`; initial invocation and `-c` correction round both exited 0.
Review PR [#46](https://github.com/mycodespace-ai/devcapsule/pull/46) delivered input/output guards,
recorder lifecycle tests and installed-CLI/PEX coverage. Round 1 split multi-operation unit tests,
removed fixed-cadence assertions, isolated encoder interpreter startup and clarified cwd-relative paths.
Accepted final review commit `e331693f` after reading its actual diff; merged at `d4564313`.
The assessment and acceptance comments are on PR #46. Final implementor checks are recorded below and
in the validation record. Hosted checks passed on the pre-review implementation; PR #43 holds the final live results.

Reviewer proposals: the relative-path clarification is included. The optional nox smoke expansion was
not adopted because the new PEX integration test covers the installed delivery boundary. The requested
Chromium check and the docs contract both passed again on the merged implementation.

## Open Threads

- Implementation authorized; release target and reviewer settled.
- PR #43 and its main propagation are verified complete. The skill PR is the current delivery.
- Future sample-project release-check support is acknowledged above; design criteria remain pending.
- Preserve the recorded viewer acceptance and demonstrated external-project recording reuse.
- Local full gate still fails on the known recursive Docker-group test; no unrelated fixture fix is included.
- Automated checks establish the kit and existing viewer contract, not a second human acceptance of presentation quality.
- Final raw acceptance files and logs are in `/var/tmp/presentations-final-acceptance`,
  `/var/tmp/presentations-antigravity` and `/var/tmp/presentations-*.log`;
  they are disposable and not committed. Durable outcomes are in the validation record.
- No transcript or tokened link is preserved in Git.

## Workstream Document Index

- [Validation record](2026-11-16-record-authoring-validation.md): installed-artifact and browser checks, counts and limits.
- [Implementation PR draft](2026-11-16-record-pr-draft.md): description prepared for PR #43, targeting release 0.3.1.
- [Round 1 brief](evidence/2026-11-16-review-round-1.md): accepted test-contract corrections and hand-off path clarification.
- [Pair Review brief](evidence/2026-11-16-review-brief.md): PR #43; exact Antigravity model and high effort.
- [Full use-case handoff](2026-11-16-record-use-case-handoff.md): owner-defined flow, constraints and original correspondence references.

- [Intake](intake/README.md): handoff and correspondence awaiting acknowledgement.
- [Intake decisions](intake-dispositions.md): append-only record of acknowledged work.
