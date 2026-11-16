# Presentation excellence: outcome and proposed acceptance

Status: both audiences accepted by the owner; delivery scope remains a proposal. No implementation work order or release commitment.
Owner direction, 2026-11-16: focus project management on what presentations need to reach excellence.

## The outcome to design for

An agent in an unrelated project can turn a real feature journey into a presentation with little setup.
A person can understand the journey, inspect the result and revisit a relevant moment without the author explaining it live.
The presentation remains useful when the recording ends and when the software changes.

Owner decision, 2026-11-16: serve engineering reviewers and prospective users/tutorial readers equally from the first delivery.
The chat answer `both` resolves decision `2026-11-16-presentation-audience`.
Acceptance must cover each audience explicitly. Neither is a later enhancement.

## What equal priority requires

One recorded journey should support a clear explanation and close inspection of what happened.
The proposed design uses a shared recording, script and run identity, with the amount of visible detail suited to the reader.
This is a design direction to assess, not a requirement for two modes or two separate presentation products.

| Audience | What the presentation must help them do | Proposed acceptance observation |
|---|---|---|
| Prospective user | Understand the problem, the benefit and the visible result without repository or conversation context. | A first-time viewer can explain what the feature does and why they might use it. |
| Tutorial reader | Follow the prerequisites and meaningful actions, then recognize the expected result. | A reader can perform the demonstrated journey in the agreed setup and identify where their result differs. |
| Engineering reviewer | Locate a step, inspect the actual result, and understand the run's identity and limits. | A reviewer can trace a presented claim to its recorded moment and supporting evidence, including any failure or incomplete check. |

The same scenario is evaluated from all three perspectives before acceptance.
The overview and captions carry the explanation; run details and evidence remain readily accessible.
A demonstration's smooth pacing must preserve what was actually observed and disclose relevant time compression.
Public sharing needs a supported audience-appropriate route; the route and publication policy still require a scope decision.


## Evidence and its limits

Read the current presentation contract and recording guide, plus both November 16 intake items.
The consolidated handoff reports successful playback of a six-step SSH presentation, including captions, screenshots and byte ranges.
The owner reports successful recorder reuse in another project, with excessive setup and presentation assembly work.
The handoff's installed-artifact audit found the viewer shipped, while authoring instructions, recorder and producer were absent.
These are recorded findings for the named artifact and source revisions, not a new audit of every released version.

The current contract already provides discovery, slides, step links, step playback, captions, keyboard controls and larger video.
The guide says interactive recording produces no presentation and ties the replay authoring path to this repository's tests.
It also documents sparse frames and video without intrinsic duration. Half-speed playback cannot add missing frames.
The existing producer and viewer are useful foundations. Their existence does not establish an effortless authoring experience.
No fresh visual review or usability session was conducted for this proposal.

## Proposed quality bar

| Outcome | What needs to be true | Evidence for acceptance |
|---|---|---|
| Easy authoring | Installed, discoverable agent guidance, one worked template and supported recording/generation tools serve the project's own journey. | An agent with no conversation context produces a presentation in an unrelated project without cloning DevCapsule or importing its tests. |
| A clear story | The overview explains the purpose. Each step explains the action and what to notice. Captions describe meaningful moments. | A new viewer understands the benefit, a tutorial reader can follow the journey, and a reviewer can inspect the observed result. The owner judges these separately. |
| Readable viewing | Text and screenshots remain legible. Pacing leaves time to understand. Zoom, keyboard use and step navigation keep the viewer oriented. | Review an agreed display size and a long caption, dense terminal output and a GUI result. Check actual playback and legibility. |
| Trustworthy evidence | Text, screenshots and time ranges refer to the same run. Expected behavior is distinguished from observed results. Incomplete or failed runs remain explicit. | A changed video, missing screenshot or incomplete run cannot silently appear as a complete, passing presentation. |
| Reuse | Scripted and interactive runs produce the same presentation contract. Editorial changes regenerate metadata without recording again. | Record once, improve the explanation, regenerate, then record a changed journey and verify that no old assets are silently reused. |
| Durable delivery | A documented folder contains the presentation and its media, survives builds and can be moved through a supported sharing route. | Reopen retained evidence after a build and test the sharing route selected for both audiences. No absolute author-machine paths are required. |

These are proposed acceptance criteria, not claims about defects in each existing viewer behavior.
Exact screen sizes, supported browsers and packaging interfaces belong in the eventual work order.

## Work implied by that bar

### Authoring and recording

Separate the reusable authoring tools from DevCapsule's own disposable IDE smoke-project setup.
Keep a supported way to record the adopter's application or workflow.
Ship agent-facing instructions, a scenario template and a worked example with the tooling that consumes them.
Choose a supported command interface; retain Python integration only where a project benefits from it.
The package and command names remain open.

Capture step boundaries, screenshots, captions and video timing during both replay and interactive authoring.
Finishing either path should generate and validate the presentation without reconstructing timings by hand.
Explain how an interrupted run is recovered or presented as incomplete.
Preserve the raw recording when a condensed presentation removes agent thinking time.
Keep actual application waits understandable; do not accidentally imply that a compressed journey proves performance.

### Story and viewer

Use the Markdown scenario as the authored story, with run data supplying what happened.
Do not require people to read raw automation reasons to understand a step.
Separate semantic steps from keystrokes; let captions span a meaningful action group.
Offer enough image detail to inspect the result, especially code and terminal output.
Review the present layout and controls with the owner before commissioning a redesign.
Retain useful existing behavior: linked steps, keyboard navigation, continuous playback and larger video.

### Validation and maintenance

Validate media identity, referenced assets, ranges and agreement between the script and the completed run.
The contract should distinguish successful execution from an expected observation written before the run.
A recording alone is not independent proof that a feature meets its requirement.
Keep observed results or acceptance evidence linked where that claim matters.
Make text-only corrections cheap and retain a reproducible producer input.
Use schema and producer versions to explain compatibility and actionable refusals.
Decide the supported sharing destination before adding website publication or a standalone export.

## Recommended first deliverable

One complete author-to-viewer journey in an unrelated DevCapsule project, using an installed candidate.
Use the owner's real adopter experience to select the project and scenario.
Provide the agent only the project and the desired feature journey.
The agent discovers the installed guidance, records, generates and opens a valid presentation.
Review the same artifact with explicit tasks for each audience:

- A first-time viewer explains the feature's purpose, benefit and visible result.
- A tutorial reader follows its prerequisites and actions in the agreed setup.
- An engineering reviewer locates a claimed result, inspects its recorded moment and finds the run's identity and limitations.

Record separate findings for each task. Passing only one does not meet the agreed audience scope.
The author then edits one caption and regenerates without repeating the recording.
A second run demonstrates that the metadata and media still agree.

Record setup steps, manual interventions and readability findings; set numeric budgets after seeing that baseline.
Do not turn guessed effort numbers into acceptance requirements.
The first work order must name its supported recording surface and the acceptance tasks for both agreed audiences.
Keep the toolkit boundary portable; decide support outside a capsule explicitly rather than assuming it is cheap.

## Decisions before implementation

1. Settled: engineering reviewers and prospective users/tutorial readers have equal priority from the first delivery.
2. First supported recording journey and delivery boundary: the selected adopter project, its surface, and whether standalone use is required immediately.
3. Toolkit distribution and supported interface, after the journey is agreed.
4. Implementation owner and review arrangement, followed by release placement.

Next choose a real adopter project and feature journey. That choice makes the recording surface and delivery needs concrete.
The project-management pair remains on this workstream.
The two presentation intake items remain pending until the agreed scope is routed through the normal work order or intake process.
The broader reusable-assets idea remains in the pile; this proposal does not decide its other parts.

## Sources

- [Consolidated authoring handoff](intake/2026-11-16-github-auth-presentation-authoring-handoff.md).
- [Portability audit handoff](intake/2026-11-16-presentation-authoring-portability.md).
- [Presentation contract](../../../devcapsule-webconsole/PRESENTATIONS.md).
- [Recording guide](../../development/running-e2e-scenario-recordings.md).
- [Reusable processes idea](../../pile-of-ideas/2026-11-13-advertise-the-processes-we-proved-as-reusable-assets.md).
