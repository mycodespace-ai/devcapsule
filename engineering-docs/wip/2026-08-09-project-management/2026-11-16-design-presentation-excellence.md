# Packaged E2E recording and presentation authoring

Status: owner-directed delivery scope; packaging design and implementation assignment remain open.
Owner clarification, 2026-11-16: the existing web-console presentation experience already meets the prospective-user quality goal.
Florin, the other developer in this repository, tested it and was wowed by it, as the owner reports.
This is accepted human validation. Do not reopen viewer design or commission another general quality exercise for this slice.

## The user request this must enable

In a different DevCapsule, on a different codebase, an engineer tells the local agent:

> Run an E2E test with Step 1, Step 2, Step 3, and make a presentation like the DevCapsule web console.

The agent discovers installed instructions and supporting Python, cooperates with Playwright to execute the real journey,
and leaves a presentation that the existing console discovers and plays.
The engineer should not need to point the agent at DevCapsule's public source code.
The agent should not need to reconstruct the recording apparatus or hand-assemble the presentation.

The owner previously selected both engineering and prospective-user/tutorial audiences with equal priority.
That outcome remains. The existing viewer satisfies the human-facing baseline; this slice delivers the missing authoring capability.
The earlier proposal to revisit narrative, layout, audience acceptance and viewer quality is superseded by this clarification.

## What we know

The consolidated November 16 handoff records successful six-step playback, captions, screenshots and byte-range media serving.
The owner also reports recorder reuse in another project after an ad-hoc source clone, with excessive presentation setup work.
The handoff's audit found the viewer shipped in the inspected artifact, but not the authoring guide, recorder or producer.
The browser-automation component supplies browser tools; that alone does not supply the authoring apparatus.
These observations identify a delivery and reuse gap.

The mainline recording guide says interactive `serve` generates no presentation.
The replay path requires a script and numbered action reasons to produce metadata.
Both facts matter: the requested natural-language agent journey must work without requiring a later replay merely to get a deck.

## Required delivered pieces

### 1. Discoverable Markdown instructions

Ship an agent-facing playbook, a scenario template and a complete worked example.
An agent must find them through a documented installed entry point in the adopter project.
A document copied into the package but never surfaced to the agent does not meet this requirement.

The playbook explains:

- How to turn the engineer's numbered steps into a script with expected observations.
- How to find and use the packaged Python helpers and the available Playwright/browser dependencies.
- How to use the project's own start, readiness and reset procedures from its documentation.
- How to record a step, capture its result and retain timings, screenshots and captions.
- How to finalize the recording, validate the presentation and return its console link.
- How to report an unsuccessful or interrupted run and preserve useful evidence.

The instructions and their executable examples must agree with the installed toolkit version.
Package the presentation contract or equivalent generated reference with them.

### 2. Reusable Python support

Provide supported Python operations for the work already solved here:
recording lifecycle, step/action boundaries, screenshots, captions, timing, encoding and presentation generation.
Use Playwright through a supported boundary with explicit browser/session inputs.
Take the adopter's script, output directory and target as inputs; do not derive them from DevCapsule's repository layout.
The agent may write project-specific test actions and assertions. It should not rewrite recording or presentation infrastructure.

Separate the reusable apparatus from DevCapsule's own IDE smoke-project orchestration.
Adopter use must not depend on `tests.e2e` imports, DevCapsule fixture projects, its nox sessions or a DevCapsule source checkout.
Do not force every adopter test to launch a disposable DevCapsule child merely because the current harness does so.
The packaging design must name the supported browser/desktop attachment and ownership contract before implementation.

### 3. A complete agent-driven recording path

An interactive agent must be able to finish a run and receive a valid presentation automatically.
Retain the timing and step data during recording; do not reconstruct chapter boundaries afterward.
Preserve the existing useful handling of agent thinking time and retain the raw recording where the apparatus already does so.
The same presentation producer should serve interactive runs and deterministic replay.
Keep actions, observed results and test success distinct; producing a video does not turn a failed test into a passed one.

### 4. Installed delivery and the existing viewer

Deliver the guide and Python together through a supported, versioned installation route.
Document and detect required Playwright, browser and encoder dependencies with actionable setup guidance.
The precise distribution and installation entry point remain engineering design decisions to settle before the packaging slice.
The result must be usable from an ordinary supported adopter capsule, including its documented capability setup.

Emit the existing `presentation.json` contract and its media into a project-visible folder outside disposable build output.
Use the current console's discovery, captions and step playback. A new viewer is not a deliverable of this slice.
A necessary viewer-contract change must identify a concrete authoring limitation before expanding scope.
Support outside DevCapsule, website publishing and older-capsule compatibility are not implied by this delivery scope.
The broad reusable-assets idea remains pending for its other parts.

## Existing code to extract and preserve

Mainline inspected at `dac6b9d4`:

- `devcapsule-src/tests/e2e/scenario_presentation.py` already provides script parsing, presentation planning and writing using Python's standard library.
  Its `E2E_ROOT` derives from the source file's directory, so the reusable entry path must take the adopter's paths explicitly.
- `devcapsule-src/tests/e2e/scenario_recorder.py` imports `tests.e2e.ai_driver`, `browser_session`, `ide_session` and the producer.
  Its recorder and controller sit beside IDE provisioning, repo-relative scenario paths and DevCapsule-specific shortcuts.
  Extract the reusable boundary; copying that module wholesale into the product does not establish portability.
- `devcapsule-src/tests/e2e/todo_demo_controller.py` demonstrates further reuse, but combines it with project-specific PostgreSQL and seed-project setup.
  Keep that scenario orchestration as an example or adapter, rather than imposing it on every adopter.

This was a bounded read of the modules' declared operations, imports and setup.
It establishes the extraction issue, not a completed architecture or dependency audit.

## Acceptance: the engineer's request succeeds elsewhere

Use an unrelated codebase in a capsule containing the installed candidate and its documented dependencies.
Give a fresh agent that project's normal instructions and the engineer's numbered E2E steps.
Give it no DevCapsule source URL, repository-specific workaround or instructions from this conversation.

Done means:

1. The agent finds the installed playbook and Python support through the supported discovery route.
2. It starts or attaches to the project's target using the documented recording path.
3. It executes the steps with Playwright, checks the requested results and retains evidence.
4. Finalization produces the video, screenshots, captions and validated `presentation.json` without manual timing reconstruction.
5. The engineer receives a working link; the existing console lists the presentation and plays each step with the right screenshot and caption.
6. The agent can regenerate an explanation change from retained run data without repeating the test.
7. A failed or interrupted step is reported accurately, with useful evidence and the documented recovery/finalization behavior.

Retain the candidate/toolkit identity, the agent task, setup steps and interventions, resulting test evidence and console playback observations.
Run the acceptance without mounting or importing this repository's source tooling.
The existing human acceptance of the viewer stands; check the new producer's compatibility with it.
The particular external project is an acceptance fixture choice, not a prerequisite for specifying or preparing the package.

## Next planning slice

Prepare the implementation work order around these delivered pieces and this acceptance.
Resolve the installed discovery route, distribution boundary and Python/Playwright attachment contract with a small packaging design.
Then assign implementation and release placement. No workstream switch is authorized by this document.
The two presentation intake items remain pending until the agreed work is routed through the normal process.

## Sources

- [Consolidated authoring handoff](intake/2026-11-16-github-auth-presentation-authoring-handoff.md).
- [Portability audit handoff](intake/2026-11-16-presentation-authoring-portability.md).
- [Presentation contract](../../../devcapsule-webconsole/PRESENTATIONS.md).
- [Recording guide](../../development/running-e2e-scenario-recordings.md).
- [Reusable processes idea](../../pile-of-ideas/2026-11-13-advertise-the-processes-we-proved-as-reusable-assets.md).
