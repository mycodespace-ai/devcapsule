# Owner-directed presentation-authoring use case

From: project-management
To: presentations
Date: 2026-11-16

The owner requested a presentations workstream if none already exists.
No standalone workstream exists; the earlier viewer slice belonged to capsule-webconsole and is merged.
This hands over the defined use case and the two authoring messages for the new workstream's goal.
Creation does not start design or implementation; the owner explicitly deferred that work while defining this use case.
No release target or packaging interface is assigned.

## Agreed use case



An engineer works with an LLM agent in a DevCapsule on their own codebase.
The engineer wants the agent to execute an E2E scenario and present the recorded result in that capsule's web console.

## Request

The engineer tells the agent:

> Run E2E with recording and presentation along the scenario described in `<scenario.md>`.

Or:

> Run E2E with recording and presentation along the scenario described here: `<plain-English scenario>`.

The Markdown file already belongs to the engineer, or the engineer describes the steps inline.
The engineer supplies the scenario in ordinary language, not a recording-tool-specific script or metadata format.

## What the agent does

1. Read the specified Markdown file or the inline scenario.
2. Run the described E2E test in the project's environment, recording the journey.
3. Produce the presentation from that run, using the capability already demonstrated in DevCapsule.
4. Make the presentation available in that project's existing DevCapsule web console.
5. Report the test result and show the engineer the presentation link when finished.

The agent uses the provided instructions and supporting code to handle the recording and presentation mechanics.
The engineer does not need to direct it to DevCapsule's public source or reconstruct the process with it.

## Successful outcome

The engineer opens the returned link in their web console and views the recorded scenario as a presentation.
The experience is the one already demonstrated by DevCapsule's web-console presentations.

## Evidence and scope

The owner reports that an agent already recorded an English-specified E2E scenario in another project after being pointed at this repository.
That establishes demonstrated reuse; this is not a request to invent a new process.
The owner confirms the existing viewer's human acceptance, including Florin's test and enthusiastic response.
Both engineering and prospective-user/tutorial audiences remain served by the existing presentation experience.

The delivery need is to make the existing Markdown instructions and supporting Python/Playwright apparatus available to adopter agents.
Package layout, interfaces, installation, and implementation ownership are later work.
Do not start that design work in this use-case definition or make selecting a new example project a prerequisite.


## Original correspondence and source revision

Both original messages remain available at project-management commit `cac3861e699641836dec5ba96de29fc453571784`:

- `engineering-docs/wip/2026-08-09-project-management/intake/2026-11-16-github-auth-presentation-authoring-handoff.md`
- `engineering-docs/wip/2026-08-09-project-management/intake/2026-11-16-presentation-authoring-portability.md`

The full use case at that revision is `engineering-docs/wip/2026-08-09-project-management/2026-11-16-design-presentation-excellence.md`.
Read the consolidated handoff for the installed-artifact audit, prior recording evidence, and existing source locations.
Current mainline `dac6b9d4` contains the recorder, producer, console contract and recording guide.
Accepting this item makes the defined use case this workstream's goal and retains the original evidence as input.
The viewer remains the accepted baseline; the deliverable is making the proven instructions and Python/Playwright support usable in other projects.
