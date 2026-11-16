# Workstream Current Status: Presentations

Mnemonic: `presentations`
Start date: 2026-11-16
State: active; registered at owner direction; design and implementation not started
Branch association: `ws-presentations/authoring`
Branch prefix: `ws-presentations/`
Integration target: `main`
Delivery method: pull request; records published on coordination

Definition read: WORKFLOW.md@781c9e39df58, WORKFLOW-LOCAL.md@94a29cb6eedb

## Goal and agreed use case

Make the proven E2E recording and presentation capability available to LLM agents in other DevCapsule projects.
Provide the existing Markdown instructions and supporting Python/Playwright apparatus without requiring a DevCapsule source clone.

The engineer asks their agent to run E2E with recording and presentation along a scenario:

- In an existing Markdown file supplied by the engineer; or
- Described inline in plain English.

The agent reads the scenario, executes the E2E test, records it and creates the presentation.
When finished, it reports the result and returns a link the engineer opens in that project's DevCapsule web console.
The engineer does not need to point it at this repository or reconstruct the recording process.

## Current state and authority

Created at the owner's request after checking the live list, canonical mainline, open/archive directories and remote refs.
No standalone presentations workstream existed. The earlier `ws-capsule-webconsole/presentations` slice is merged.
The owner confirms that the current viewer is already human-validated, including Florin's enthusiastic test.
An agent already recorded an English-specified scenario in another project after the owner pointed it at this source.
Both engineering and prospective-user/tutorial audiences remain in scope; the existing viewer is the accepted baseline.

Registration starts no design or implementation. The owner explicitly deferred design during use-case definition.
No package layout, interface, installation route, release target or outside-capsule support promise is selected.
The broader reusable-processes idea is not assigned wholesale to this workstream.
Project-management delivered the use case and references to both original authoring messages by coordination mail.
Acknowledged that handoff as the goal above; its full text is preserved in the handoff record.
The mailbox and intake are empty after receipt and acknowledgement.
Original correspondence is preserved on `ws-project-management/coordination` at `cac3861e` under its intake directory.
The self-contained handoff names the exact paths and evidence.

## Planned next step

Registration and handoff acknowledgement are complete.
Wait for the owner's next direction before beginning design or implementation.
Do not restart a viewer redesign, audience study or general process invention.

## Validation and checkout state

Forked from fetched canonical `upstream/main` at `dac6b9d4`; no synchronization is needed at registration.
No open bug is owned by presentations at registration.
This is an administrative registration with no product changes. Check the new records and links, not the product gate.
The owner's direction permits this project-management coordination despite local test failures.
The existing full-gate result on this source passed type/convention checks, then stopped on a recursive Docker-group test.
Do not claim that result as a successful product gate for later implementation.
No service, container or environment was created. Existing raw evidence remains ignored.

## Open Threads

- Awaiting owner direction after registration; design and implementation remain unstarted.
- Workstream goal and input/output use case are settled; implementation choices and release placement are open.
- Preserve the recorded viewer acceptance and demonstrated external-project recording reuse.
- Deliberately not preserved: no transcript, tokened link, new experiment or speculative architecture.

## Workstream Document Index

- [Full use-case handoff](2026-11-16-record-use-case-handoff.md): owner-defined flow, constraints and original correspondence references.

- [Intake](intake/README.md): handoff and correspondence awaiting acknowledgement.
- [Intake decisions](intake-dispositions.md): append-only record of acknowledged work.
