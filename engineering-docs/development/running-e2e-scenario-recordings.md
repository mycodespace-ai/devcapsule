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
file under `devcapsule-src/tests/e2e/scenarios/<scenario-id>.json`.
