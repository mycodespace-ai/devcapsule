---
name: devcapsule-recorded-e2e
description: Run a visual end-to-end scenario in a DevCapsule, record its execution, and return a verified web-console presentation. Use for a scenario supplied as Markdown or plain English, including requests to run an end-user scenario and record a presentation with videos of what happened.
---

# Recorded E2E with DevCapsule

Deliver the requested test's outcome and a clickable presentation of what
actually ran. Accept the engineer's existing Markdown or inline English;
translate it into the project's driver without requiring a new input format.
Recognize equivalent wording; the engineer need not say E2E or name this skill.

## Load the installed procedure

Run `devcapsule version --json` and `devcapsule presentations guide`. Follow
that installed guide for the recorder API, evidence layout, playback checks
and hand-off. It is the version-matched procedure; this skill is its entry point.
Use the project's installed command name if it differs from `devcapsule`.

If the command or guide is unavailable, report the installed version and the
missing authoring support. The portable guide and helpers first shipped in
0.3.1rc3. An upgrade requires the engineer's normal host-side installation
and a new capsule launch; changing the host executable does not upgrade an
already-running capsule. Do not substitute an invented command or a source
checkout requirement. Installing this skill requires no workflow-file upgrade.

## Apply it to this project

- Read the scenario and the project's application/test instructions. Use its
  actual application, test data and observable assertions. Ask about a missing
  prerequisite or consequential choice only when it blocks the requested run.
- Check the available browser automation, encoder and console environment as
  the guide describes. Use existing capabilities; do not silently download
  browsers, change project configuration or launch additional capsules.
- Export the installed helpers to a new scratch directory with
  `devcapsule presentations export <new-directory>`. Adapt the exported
  example to the project's existing E2E setup and teardown. This command
  supplies tools; it does not run the scenario itself.
- Keep each attempt in a new, visible directory beneath the console's project
  root, preferably the project's existing evidence location. Keep recordings
  outside disposable build output. Respect the project's retention policy;
  do not automatically commit captured media or secrets.
- Record real interactions and verify expected observations independently.
  Preserve the test's failing exit status and reached-step evidence when an
  assertion fails. A movie or a rendered presentation is not proof of success.

## Return the result

Check the driver's exit status and `scenario-result.json`, then verify the
presentation in the running console, including chapter playback. Use
`devcapsule presentations hand-off <evidence-directory> --project <console-project-root>`
to obtain the link. Follow the guide's path and console-environment rules.

Report passed, failed or incomplete; identify failed and unexecuted steps and
any recording/playback limitation. If a presentation could not be generated
or opened, say so and retain the available evidence instead of claiming it
was verified. Finish with the clickable presentation link when one exists.
Keep token-bearing links in chat only, never in Git or saved reports.
