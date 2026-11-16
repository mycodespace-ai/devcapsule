# Running E2E Scenario Recordings From A Shell With Nox

[Development](README.md) · [End-to-end tests](e2e-tests.md) · [Implementation note](../implementation-notes/devcapsule/2026-10-21-e2e-scenario-video-recorder.md)

This note shows how to run a recorded IDE scenario—or author a new one with an
agent—from any shell where `nox` and Docker are available (either on a Linux /
WSL2 host or inside a dogfood DevCapsule with host Docker).

## 1. Prerequisites

From the repository root, change into `devcapsule-src`:

```sh
cd devcapsule-src
```

Make sure:

1. `docker info` succeeds in your shell.
2. `nox` is available (for example via `.venv/bin/python -m nox` or `nox` on `PATH`).
3. If running inside a dogfood DevCapsule without a host display, pass
   `--component-browser` so Playwright connects to the Chromium and FFmpeg
   bundled inside the child capsule's `browser-automation` component
   (`/opt/playwright`).

## 2. Replay a packaged scenario and record video with `nox`

Run the `ide-smoke` session with `--surface` and `--scenario`. A scenario targets
one IDE surface, so `--scenario` needs exactly one `--surface` and cannot be
combined with `--agent`:

```sh
nox -s ide-smoke -- \
  --surface eclipse \
  --scenario eclipse-hello-time-debug \
  --component-browser
```

If `nox` is installed in the project virtualenv rather than globally:

```sh
.venv/bin/python -m nox -s ide-smoke -- \
  --surface eclipse \
  --scenario eclipse-hello-time-debug \
  --component-browser
```

### Reusing an existing PEX executable (faster repeat runs)

By default, `nox -s ide-smoke` builds `dist/devcapsule-local.pex` first. To
skip the PEX build and test against an already-built executable, set
`DEVCAPSULE_PEX_UNDER_TEST`:

```sh
DEVCAPSULE_PEX_UNDER_TEST="$PWD/dist/devcapsule-local.pex" \
  nox -s ide-smoke -- \
  --surface eclipse \
  --scenario eclipse-hello-time-debug \
  --component-browser
```

### Listing available scenarios

```sh
PYTHONPATH=src:. python3 -m tests.e2e.scenario_recorder list
```

You can pass either a catalog ID (such as `eclipse-hello-time-debug`, resolved
from `devcapsule-src/tests/e2e/scenarios/<id>.json`) or a path to any `.json`
scenario file:

```sh
nox -s ide-smoke -- \
  --surface eclipse \
  --scenario /path/to/my-scenario.json \
  --component-browser
```

## 3. Where to find the recorded video and screenshots

Recorded scenario runs (`--scenario` or `scenario_recorder`) write their
artifacts into the build-safe, git-ignored `evidence/<scenario-id>/` directory
beside `scenarios/` (so clean `dist/` builds never remove recordings, and the
DevCapsule web console can stream them directly from the project mount):

```text
devcapsule-src/tests/e2e/evidence/<scenario-id>/
```

(Surface-level `nox -s ide-smoke` logs remain under
`devcapsule-src/dist/e2e-evidence/ide-smoke/<UTC-timestamp>-<id>/<surface>/`.)

For example, replaying `eclipse-hello-time-debug` writes into
`devcapsule-src/tests/e2e/evidence/eclipse-hello-time-debug/`:

| File | Contents |
|---|---|
| `scenario-video.webm` | Pause-free `1600×1000` 12 fps VP8 WebM video encoded from active UI transition frames |
| `scenario-video.webm.ffmpeg.log` | `ffmpeg`'s own output, and the reason when no `scenario-video.webm` was produced |
| `poster.png` | Final `1600×1000` frame suitable for a `<video poster="...">` thumbnail |
| `step-001.png` … `step-NNN.png` | Full-resolution screenshot captured after each action step |
| `agent-desktop-raw.webm` | Uncut Playwright browser-context video of the entire session |
| `action-log.json` | Concrete action trace with `${PROJECT_PATH}` and `${WORKSPACE}` expanded |
| `presentation.json` | For a scenario that names its script: the text, the step times and the captions the web console shows as slides beside the recording; see section 5 |
| `scenario-result.json` | Summary JSON (`status`, `steps_executed`, `frames_recorded`, output filenames) |

## 4. Interactive agent takeover (`serve` / `ctl`)

When an agent (`codex`, `claude`, or `antigravity`) is given a plain-English
scenario to act out live against an IDE capsule, run the interactive HTTP
controller so LLM thinking time between turns is never recorded into the video:

```sh
# 1. Start the child IDE capsule and local HTTP controller in the background
#    (--evidence defaults to tests/e2e/evidence/<scenario-id>):
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder serve \
  --scenario eclipse-hello-time-debug \
  --evidence tests/e2e/evidence/eclipse-hello-time-debug \
  --pex dist/devcapsule-local.pex
```

Once `controller.json` appears in `--evidence`, the agent drives the IDE with
`ctl` commands. `ctl` prints the controller's JSON answer and exits `0` when
`ok` is true, else `1`:

```sh
# 2. Capture the current screen and X11 window list:
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder ctl \
  --evidence tests/e2e/evidence/eclipse-hello-time-debug '{"cmd":"screenshot"}'

# 3. Send mouse/keyboard actions (frames are recorded only while actions execute):
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder ctl \
  --evidence tests/e2e/evidence/eclipse-hello-time-debug \
  '{"cmd":"act","actions":[
    {"action":"press","text":"F11","reason":"Launch Eclipse debugger"},
    {"action":"wait","ms":5000,"reason":"Wait for breakpoint hit"}
  ]}'

# 4. Stop the session and encode scenario-video.webm:
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder ctl \
  --evidence tests/e2e/evidence/eclipse-hello-time-debug '{"cmd":"stop"}'
```

To package an interactive run as a permanent repeatable scenario, copy the
generated `tests/e2e/evidence/<scenario-id>/action-log.json` array into a new
file under `devcapsule-src/tests/e2e/scenarios/<scenario-id>.json`. Then give
the scenario its script and number its actions as section 5 says, so its
replays are presented.

## 5. The presentation of a recording

A recording runs faster than a person reads, and nothing in the video says
what each moment is for. The web console therefore shows a recorded scenario
as slides beside its recording: an overview, then one slide per step of the
script with the step's text, its screenshot, and a button that plays only
that step's part of the video, with captions. The page reads
`presentation.json` from the evidence folder; its contract is
[`devcapsule-webconsole/PRESENTATIONS.md`](../../devcapsule-webconsole/PRESENTATIONS.md).

A replay writes `presentation.json` by itself when the scenario gives it the
three things below. `tests/e2e/scenario_presentation.py` does the work, and
both `scenario_recorder` and `todo_demo_controller` call it. The inputs are
checked before the capsule records anything, so a fault in them stops the
run in seconds and names what to correct. A scenario that names no script is
recorded as before, without a presentation; the interactive `serve` mode
writes none.

### 5.1 The scenario names its script

The scenario's JSON carries `"script": "scripts/<scenario-id>.md"`, a path
below `devcapsule-src/tests/e2e/`. Its `title` becomes the presentation's
title and its `description` the summary on the first slide, so write the
`description` as what the viewer is about to see.

### 5.2 The script follows the form

```markdown
# E2E Scenario Script: <name>

Anything before the first `##` heading is for the reader of this file only.

## Goal

One paragraph: why the scenario exists. It becomes "Why this scenario".

## Stack And Capabilities

- **Editor:** VSCodium, the project's `frontend-ide`
- **Database:** PostgreSQL 17 on `127.0.0.1:15432`

## What It Illustrates

- One thing about DevCapsule the recording shows.
- Another.

## Steps

1. **Open the workspace in the editor.**
   - *User action:* What the user does in this step.
   - *Expected observation:* What the viewer should see when it is done.

2. **The next step.**
   - *User action:* …
   - *Expected observation:* …
```

`Goal` and `Steps` are required; `Stack And Capabilities` and `What It
Illustrates` are optional. The four headings are spelled as above, and no
other `##` heading is allowed. Steps are numbered from 1 without a gap, and
each has both sub-bullets. A bullet may continue on indented lines. The
texts may mark `` `code` ``, `**strong**` and `*emphasis*`; the page
interprets nothing else. Write a backtick inside code with double backticks,
as in ``` `` Ctrl+` `` ```.

### 5.3 The actions name their steps, and may carry captions

Every action's `reason` starts with the number of the step it belongs to and
a period: `"reason": "3. Save frontend/src/App.jsx"`. The numbers never go
down, and every step of the script has at least one action. The step's part
of the video runs from the end of the step before it to the end of its last
action, and its screenshot is the one taken after its last action.

Captions come from the actions too:

- A step whose actions have no `caption` shows each action's reason, without
  the number, while that action plays. Nothing more is needed, and the
  captions change as fast as the actions do.
- For captions a person can read, give `"caption": "…"` to the first action
  of each group of actions that makes one moment. The caption is shown from
  that action until the next action that has one. A step that has any
  caption needs one on its first action.

```json
{"action": "press", "text": "Control+p", "reason": "2. Open Quick Open dialog",
 "caption": "Quick Open (`Ctrl+P`) finds `backend/main.py`."},
{"action": "type", "text": "backend/main.py", "reason": "2. Filter to backend/main.py"},
{"action": "press", "text": "Enter", "reason": "2. Open backend/main.py"}
```

Aim for a caption that stays up for a second or more of video: at the
page's default half speed that is two seconds of reading.

### 5.4 Looking at it

Inside a capsule whose console includes the page, open **Presentations** in
the console's top band; the recording is listed as soon as the replay has
written `presentation.json`. From this checkout, without a capsule:

```sh
.venv/bin/python -m nox -s webconsole-preview
```

serves the checkout's console on `http://127.0.0.1:8787` and logs its links.
`tests/e2e/scenarios/todo-fastapi-postgres-react.json` with
`tests/e2e/scripts/todo-fastapi-postgres-react.md` is the worked example,
and its presentation is the sample under
`devcapsule-webconsole/resources/presentations/`.

Two limits to know. The page slows the video down; it cannot add frames, so
a recording of sparse frames looks stepped at half speed. And
`scenario-video.webm` does not state its own length, because `ffmpeg` writes
it to a pipe; the page takes the length from `presentation.json`.
