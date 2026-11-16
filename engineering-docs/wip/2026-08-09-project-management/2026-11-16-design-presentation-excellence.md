# Use case: run an E2E scenario with recording and presentation

Status: defined by the product owner, 2026-11-16.
This use case replaces the earlier broad quality and packaging-design proposals in this document.
No architecture or implementation design is selected here.

## Actor and context

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

## References

- [Consolidated handoff](https://github.com/mycodespace-ai/devcapsule/blob/cac3861e/engineering-docs/wip/2026-08-09-project-management/intake/2026-11-16-github-auth-presentation-authoring-handoff.md).
- [Portability handoff](https://github.com/mycodespace-ai/devcapsule/blob/cac3861e/engineering-docs/wip/2026-08-09-project-management/intake/2026-11-16-presentation-authoring-portability.md).
- [Existing presentation contract](../../../devcapsule-webconsole/PRESENTATIONS.md).
- [Existing recording instructions](../../development/running-e2e-scenario-recordings.md).
