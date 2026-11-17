# Run an E2E scenario with recording and presentation

These instructions are for the agent in the engineer's project. Accept the
scenario from the engineer's existing Markdown file or their inline English.
Read it yourself; do not require the engineer to translate it into a schema.
Execute the requested test, check its observations, and give the engineer the
result and a link to the recorded presentation in their DevCapsule web console.

## Install the optional agent skill

`devcapsule bootstrap` installs this skill with the workflow files.
`devcapsule project wrap` installs it in the wrapper repository, outside the
foreign source. Both supply `.agents/skills/devcapsule-recorded-e2e/SKILL.md`
for Codex/Antigravity and `.claude/skills/devcapsule-recorded-e2e/SKILL.md` for
Claude Code. No separate installation command is needed. Start a new agent
session after project setup, then ask it to run your scenario.

Re-running bootstrap or wrap adds missing skill folders and preserves existing
ones, including customized skills. A symlinked skill location is left under
its owner's control. Bootstrap does not require `--refresh-workflow-definition`
to add missing skills and does not replace existing workflow files by default.
Keep the installed skill files in the project or wrapper repository under its
normal commit policy so other contributors receive them.

For projects that do not use workflow bootstrap or wrapping, or to choose a
custom skill location, install directly from the executable:

```sh
devcapsule presentations install-skill .agents/skills/devcapsule-recorded-e2e
```

This creates the parent directories and writes `SKILL.md` into the new skill
folder. It refuses an existing destination, preserving any customized skill;
review and move an existing installation before installing its replacement.
There is no temporary export or manual copy step.

Choose the destination your agent discovers:

| Agent | Project skill directory |
| --- | --- |
| Codex | `.agents/skills/devcapsule-recorded-e2e` |
| Antigravity | `.agents/skills/devcapsule-recorded-e2e` |
| Claude Code | `.claude/skills/devcapsule-recorded-e2e` |

For Claude Code, use the same command with the `.claude/skills/` destination.
These paths follow the [official OpenAI documentation](https://developers.openai.com/api/reference/cli#use-the-cli-from-a-coding-agent),
[Antigravity documentation](https://antigravity.google/docs/skills), and
[Claude Code documentation](https://code.claude.com/docs/en/skills).
Start a new agent session after installation. The file can be committed as a
project instruction under that project's rules.

The skill needs only `SKILL.md`. When running a scenario, the agent exports the
Python helpers from the installed executable, so they match that executable's
version. The install command does not run a test or configure browser automation.

Then ask, for example:

> Run the end-user scenario in tests/e2e/login.md and record a presentation
> with videos of what happened.

You can also explicitly ask to use `devcapsule-recorded-e2e`. Equivalent wording
should select the same procedure; an exact phrase or the skill name is not required.

For agents that do not discover the chosen directory, put this instruction in
`AGENTS.md` (adjust the path if you chose another location):

```markdown
When the user asks to execute an end-user scenario and capture video or produce
a recorded presentation, read and follow
`.agents/skills/devcapsule-recorded-e2e/SKILL.md` relative to the project root.
Apply this instruction to equivalent wording; the user need not name the skill.
```

Ensure the agent reads that instruction file. For Claude Code installations
that do not load it, import it with `@AGENTS.md` in the project's `CLAUDE.md`, as
[Claude's documentation describes](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools).
An instruction to read a file does not register a native slash command.

No workflow bootstrap, workflow-version change or `WORKFLOW.md` replacement is
needed. Agents without skill support can still read `devcapsule presentations
guide`. The guide and helpers first shipped in 0.3.1rc3; skill export, direct installation and
automatic installation with bootstrap/wrap are rc4 additions. Upgrade an older executable through the normal
host procedure and launch a new capsule before using them. A host executable
replacement does not update a running capsule.

## Get the tools

`devcapsule presentations guide` prints this guide from the installed executable.
No DevCapsule source checkout is needed. Export the supporting Python package:

```sh
devcapsule presentations export /var/tmp/e2e-authoring
```

The destination must be new. It contains `presentation_tools/` with this guide,
the producer, recorder, a runnable example and `SKILL.md`. Add the export directory to
`PYTHONPATH` when running the project's driver. The helpers use only the Python
standard library and the Playwright page you supply. They import no test harness.

Use the capsule's `browser-automation` capability, supplied by the `playwright`
component. Its interpreter is `$DEVCAPSULE_PLAYWRIGHT_PYTHON`, normally
`/opt/playwright/venv/bin/python`, and `$PLAYWRIGHT_BROWSERS_PATH` names its
browser directory. The directory's `ffmpeg-*/ffmpeg-linux` is the video encoder
on Linux. Locate the installed executable and pass its absolute path to the
driver. A full system `ffmpeg` also works. Do not download browsers or change
the capsule configuration silently. If the capability is missing, report it
and use the project's normal configuration/relaunch procedure with the engineer.

## Execute the engineer's scenario

1. Read the supplied scenario and the project's run/test instructions. Identify
   the real application URL, required data, actions and observable assertions.
   Ask only about a missing decision that prevents executing the test.
2. Export the tools. Adapt `presentation_tools/example.py` into a driver in the
   project's normal E2E location. Translate the English into `Script` and
   `ScriptStep` values in that driver. The engineer's Markdown stays unchanged.
3. Use ordinary synchronous Playwright operations for this project's UI. A
   browser page can be the application itself or the capsule's noVNC desktop
   when testing an IDE. The helper does not provision applications, databases
   or capsules; use the project's established setup and teardown.
4. Create `Recording` with a **new visible evidence subdirectory beneath the
   console's project root**: for example `evidence/login-success/run-001`.
   Hidden directories, `node_modules`, paths outside the project, and the project
   root itself do not appear in the presentation list. Do not overwrite attempts.
5. Call `recording.action(page, step_number, caption, callback)` around each small
   real interaction and its assertions. Step numbers start at 1 and proceed in
   order; several actions may belong to one step. Captions describe the action.
   The callback can use locators, keyboard/mouse operations and project checks.
   Assert expected observations independently of the screenshots; a recording
   is evidence of a run, not proof the test passed.
6. Keep `record_video_dir=str(recording.evidence / "raw")` on the Playwright
   context. The helper captures bursts before and after each action, following
   the existing recorder's sparse-frame approach. Its presentation movie excludes
   the agent's thinking pauses; the native video preserves motion during the
   action. Split long callbacks into smaller recorded actions when viewers need
   to follow intermediate UI states. Neither file is a generated explainer video.
7. Call `recording.finish()` while cleaning up, including after a test assertion
   fails. Close the browser context to flush its native video. Keep the failure
   exit code. Failed/incomplete runs receive labelled presentations containing
   only steps reached. If capture or encoding prevents a deck, report that failure
   and preserve the logs; do not claim a presentation exists.

The helper writes `action-log.json`, `scenario-result.json`, JPEG frame data,
the encoded `scenario-video.webm`, `poster.png`, step screenshots and finally
`presentation.json`. Chapters and captions come from the recorded frame counts.
Do not estimate timestamps or hand-edit the manifest to hide a failed step.
The existing webconsole schema and viewer are used unchanged.

## Verify and hand off

Read `scenario-result.json` and the driver's exit status. Open the presentation
in the webconsole with Playwright; check its title, overview, screenshots and
chapter playback, including the last chapter. A failing assertion is a failed
test even when its presentation renders correctly. Report failed and unexecuted
steps explicitly. Keep evidence only under the project's normal retention rules;
avoid committing recordings or captured secrets automatically.

Print the engineer's link with the installed CLI:

```sh
devcapsule presentations hand-off evidence/login-success/run-001 --project "$PROJECT_PATH"
```

Run this from the console project root: a relative evidence folder resolves
from the current working directory, and `--project` supplies the console root
used to form the relative link. It uses `$DEVCAPSULE_CONSOLE_URL` and the
mounted console token; `--console-url` and `--token-file` supply explicit values. Keep tokened links in chat only, never
in a source file, log or committed record. If no token can be read, the link
requires a browser session that already opened the console. If there is no
console URL, report that missing environment input rather than inventing a URL.

Finish the response with the test outcome, any limitation, and the clickable
presentation link. The engineer should not need to reconstruct a path themselves.

## Existing replay scripts

The exported `producer` also supports the existing structured replay format:
`parse_script`, `plan_presentation`, `PresentationPlan.timed` and
`write_presentation`. `plan_for_scenario(scenario, root)` reads the scenario's
script relative to the supplied project directory. This adapter is for agents
with existing structured scripts; it is not an input requirement for engineers.
