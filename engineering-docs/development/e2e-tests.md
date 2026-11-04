# End-To-End Tests

[Development](README.md) · [Developer environment](developer-environment.md) · [Source layout](source-layout.md) · [Unit tests](unit-tests.md) · [Integration tests](integration-tests.md) · [Running scenario recordings](running-e2e-scenario-recordings.md)

The end-to-end suites run real Docker: they build images, start containers,
launch capsules and look at what happens. They are opt-in, they run on a
developer's machine or inside a capsule with host Docker, and never on the
hosted runner. During a release they run against the downloaded candidate,
which is how the acceptance record gets its Docker proofs; see the
[release runbook](../implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md).

## Entry points

| Session | Runs | Needs |
|---|---|---|
| `nox -s e2e` | the `e2e` tests that are not `recursive_e2e`, `contributor_e2e` or `ide_smoke`; with `-- --build-base` also `base_build_e2e` | Docker; the executable |
| `nox -s pex_clean_machine` | the clean-machine proof: the executable on a networkless image with no host Python | Docker; the executable |
| `nox -s recursive_dogfood_e2e` | `project recursive-e2e run` on this checkout, then the `recursive_e2e` and `contributor_e2e` tests | a capsule with host Docker and host networking |
| `nox -s ide-smoke` | the `ide_smoke` tests, one per IDE surface; `-- --display` adds Playwright evidence, `-- --surface NAME` limits the run | Docker; the executable; the recommended base |

Every session selects the executable the same way: `DEVCAPSULE_PEX_UNDER_TEST`
when set, otherwise it builds `dist/devcapsule-local.pex`. When a candidate
is selected, `DEVCAPSULE_EXPECTED_RELEASE_VERSION` and
`DEVCAPSULE_EXPECTED_BUILD_MNEMONIC` assert its identity, and the session
logs the executable's checksum and source revision so the evidence names
exact bytes. `-- --build-network host` reaches the image builds that install
packages, for hosts whose bridge network has no DNS.

## The tests, and what each proves

| Test | Markers | Proves |
|---|---|---|
| `test_self_contained_pex.py` | `e2e` | The executable runs without a host Python and without network |
| `test_runtime_image.py` | `e2e` | Inside a disposable image: the runtime entrypoint, the supervisor's session end on `docker stop`, and the contained display's boundary: one token-gated bridge, no abstract X socket, no host credential, display processes as the capsule user, Openbox on DevCapsule's configuration |
| `test_component_cache.py` | `e2e` | A component installation is reused across images and invalidated by its recipe; a formation receives the exact launcher on a runtime-free base |
| `test_recursive_successor_lifecycle.py` | `e2e` | A successor capsule removed from outside is reported as failed, not lost |
| `test_built_base.py` | `e2e`, `base_build_e2e` | The full base built by the selected release's own CLI has the tools and no embedded runtime |
| `test_contributor_bootstrap.py` | `e2e`, `contributor_e2e` | A first-time contributor bootstraps in a disposable base, from a host or from inside a capsule |
| `test_recursive_local_clone.py` | `e2e`, `recursive_e2e` | The recursive E2E local-clone protocol, from a dogfood capsule |
| `test_recursive_successor_attached_launch.py` | `e2e`, `recursive_e2e` | From a fresh workspace (a clean clone, configured and resolved under its own roots; a dirty source is refused), `launch-successor` is the ordinary attached launch: it stays attached while the successor runs, the independent inspection passes meanwhile, stopping the container ends the command with Docker having removed it and the run directory holding the log and manifest, and the capsule's own records are untouched |
| `test_ide_comes_alive.py` | `e2e`, `ide_smoke` | Each IDE surface comes alive in a fresh project: the desktop URL answers, an X11 window of the IDE's class exists on the capsule's display; optionally a screenshot and a recording |

## Drivers and helpers

Four modules under `tests/e2e/` are not tests; they are what the tests run:

- `contributor_bootstrap_driver.py` runs the isolated contributor bootstrap
  inside a disposable base container.
- `ide_session.py` launches a real IDE session with the executable under
  test and asks the capsule whether the IDE came alive: the table of IDE
  surfaces, the session context manager with its cleanup, the minimal X11
  client that reads top-level windows through the display socket so the
  image needs no X tools, and the optional Playwright capture. A new IDE
  surface is one row in its table.
- `scenario_recorder.py` drives richer multi-step IDE workflows (such as
  importing a project, setting breakpoints, launching the debugger, and
  stepping through code) and encodes pause-free WebM videos (`scenario-video.webm`)
  from active transition frames. It supports both deterministic replay of JSON
  scenarios under `tests/e2e/scenarios/` and interactive HTTP takeover
  (`serve` / `ctl`) by any coding agent (`codex`, `claude`, `antigravity`).
- `tests/resources/supervisor_driver.py` runs the supervisor over a JSON
  child-set specification, shared with the unit tests.

The X11 probe in `test_runtime_image.py` and the one in `ide_session.py`
speak the core protocol over the Unix socket, enough for the setup
handshake, `InternAtom` and `GetProperty`; it is the deliberate alternative
to installing `xprop` in every image.

## Environment the tests read

| Variable | Set by | Meaning |
|---|---|---|
| `DEVCAPSULE_PEX_UNDER_TEST` | you, or the session | The executable under test |
| `DEVCAPSULE_EXPECTED_RELEASE_VERSION`, `DEVCAPSULE_EXPECTED_BUILD_MNEMONIC` | you, for a candidate | Its asserted identity |
| `DEVCAPSULE_E2E_BASE_IMAGE`, `DEVCAPSULE_E2E_BUILT_BASE`, `DEVCAPSULE_EXPECTED_BASE_SOURCE` | `-- --build-base` | The base the session built and its provenance |
| `DEVCAPSULE_EARLY_EXIT_E2E_IMAGE`, `DEVCAPSULE_CONTRIBUTOR_E2E_IMAGE`, `DEVCAPSULE_PEX_CLEAN_MACHINE_IMAGE` | the sessions | Disposable images the tests build or reuse |
| `DEVCAPSULE_E2E_BUILD_NETWORK` | `-- --build-network` | The network mode of image builds |
| `DEVCAPSULE_SMOKE_SCENARIO` | `-- --scenario` | Catalog ID or JSON path of a recorded IDE scenario to replay |
| `DEVCAPSULE_SMOKE_PLATFORM` | `-- --platform` | The capsule platform the IDE smoke creates each project for, such as `linux-arm64` |
| `DEVCAPSULE_RUNTIME_PEX` | you, for a macOS launcher | The Linux runtime it delivers, or a directory of `devcapsule-<platform>` runtimes |
| `PLAYWRIGHT_BROWSERS_PATH` | you, optionally | Where `ide-smoke -- --display` finds or installs Chromium |

## Evidence

- `dist/e2e-base-build.json`: the base a `--build-base` run built, its image
  id, and the builder's identity and checksum.
- `dist/e2e-evidence/ide-smoke/<UTC time>-<id>/`: one directory per IDE
  smoke run, never overwritten, with `run.json` naming the executable and,
  per surface, the launcher and init logs, the window found, the records
  removed, and with `--display` the screenshot and the WebM recording of
  the browser session.
- The release runbook says which of these the acceptance record cites.

## Scenario-driven IDE video recording (`--scenario` and `scenario_recorder`)

To record pause-free product and documentation videos of real IDE workflows
(debugger sessions, multi-step navigation, terminal-to-IDE handoffs), use
`tests/e2e/scenario_recorder.py` and the catalog under
`tests/e2e/scenarios/*.json`.

### 1. Deterministic scenario replay

Run a catalog scenario through `ide-smoke`; `--scenario` needs exactly one
`--surface`, the scenario's own, and cannot be combined with `--agent`:

```sh
.venv/bin/python -m nox -s ide-smoke -- --surface eclipse --scenario eclipse-hello-time-debug --component-browser
```

Or invoke the recorder module directly against an existing PEX executable:

```sh
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder replay \
  --scenario eclipse-hello-time-debug \
  --evidence dist/e2e-evidence/eclipse-debug \
  --pex dist/devcapsule-local.pex
```

The replay seeds `seed_files` into the disposable project workspace, executes
each `ActionStep` (`click`, `double_click`, `right_click`, `type`, `press`,
`wait`) with `${PROJECT_PATH}` and `${WORKSPACE}` substitution, and writes:

- `scenario-video.webm`: pause-free 12 fps VP8 WebM encoded by `BurstFrameRecorder`
  using `ffmpeg` (`image2pipe` `mjpeg` $\rightarrow$ `libvpx`) from either the host or
  the child capsule's `/opt/playwright/browsers/ffmpeg-*/ffmpeg-linux`.
- `scenario-video.webm.ffmpeg.log`: `ffmpeg`'s output, and the failure reason
  when `scenario-video.webm` is missing.
- `agent-desktop-raw.webm`: continuous raw Playwright context recording.
- `step-NNN.png` and `poster.png`: full-resolution `1600×1000` step screenshots.
- `action-log.json` and `scenario-result.json`.

### 2. Interactive agent takeover (`serve` / `ctl`)

When authoring a new scenario from a plain-English script, an agent (`codex`,
`claude`, or `antigravity`) can launch the interactive controller and drive the
inner capsule's desktop turn by turn without recording LLM thinking pauses:

```sh
# Start the child IDE capsule and local HTTP controller:
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder serve \
  --scenario eclipse-hello-time-debug \
  --evidence /tmp/scenario-run \
  --pex dist/devcapsule-local.pex

# Inspect the current screen and X11 window list:
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder ctl \
  --evidence /tmp/scenario-run '{"cmd":"screenshot"}'

# Execute a batch of keyboard/mouse steps (frames are recorded only during active steps):
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder ctl \
  --evidence /tmp/scenario-run \
  '{"cmd":"act","actions":[{"action":"press","text":"F11"},{"action":"wait","ms":3000}]}'

# Finalize and encode scenario-video.webm:
PYTHONPATH=src:. .nox/ide-smoke/bin/python -m tests.e2e.scenario_recorder ctl \
  --evidence /tmp/scenario-run '{"cmd":"stop"}'
```

 When the interactive session finishes, `action-log.json` holds the exact
verified action sequence ready to save into `tests/e2e/scenarios/<name>.json`.

## Eclipse Java smoke

```sh
.venv/bin/python -m nox -s ide-smoke -- --agent --surface eclipse --component-browser
```

The shared scenario launches Eclipse IDE for Java Developers in a fresh
`eclipse-ide` project, uses the child's Playwright component to control noVNC,
opens `smoke.txt` in the editor, saves a unique marker and visually recognizes
the result. The test independently reads the saved file. Evidence includes the
original `eclipse/agent-desktop.webm` movie and chronological PNG frames.
Use `--display` instead of `--agent` for startup/window/pixel evidence only.
The JetBrains-specific `--relaunch` preference check does not apply to Eclipse.

## Rider and .NET SDK smoke

```sh
.venv/bin/python -m nox -s ide-smoke -- --display --surface rider --component-browser
```

A fresh `dotnet-ide` project resolves Rider plus the .NET SDK. The test
requires the noVNC endpoint, a Rider window, browser pixels, SDK identity,
and a successful build/run of a package-free `net10.0` console project as
the capsule user. It retains SDK output, screenshots and the recording.
An activation screen is startup evidence only, not editor acceptance.

Add `--agent --component-browser` for the same saved-edit and visual
recognition scenario as IntelliJ. This mode never signs in or activates a
trial and fails if licensing prevents an edit. `--relaunch` is available
for Rider and IntelliJ when editor access is available; it checks a UI-set
font preference and repeats the edit after restart.

## AI-driven graphical acceptance

From `devcapsule-src`, with host Docker, the recommended base image, and an
authenticated Codex CLI on `PATH`:

```sh
.venv/bin/python -m nox -s ide-smoke -- --agent --surface intellij
```

For the component and persistence acceptance repeat, add
`--component-browser --relaunch`. The browser then runs from `/opt/playwright`
inside the fresh child, accessed over a loopback Playwright connection with a
random endpoint path. Agent CLIs and their authentication remain in the parent.
The agent changes IntelliJ's editor font size to 17 through Settings; the test
checks that preference and the saved marker across one bounded relaunch of the
same project. The test closes its browser server and both owned sessions.

The default action driver and visual recognizer are Codex with `gpt-6-astra`.
The shared scenario opens `smoke.txt`, types a unique marker through the
noVNC canvas using Playwright, saves it in the IDE and asks the recognizer to
review chronological frames including the final editor. The test independently
checks the saved file. A model verdict alone cannot pass. Each invocation
creates one disposable project/capsule and keeps its evidence after cleanup.

Use `--driver claude` for Claude CLI with `claude-fable-5-1`, and `--model`
to override the driver's model. `--recognizer codex|claude` and
`--recognizer-model` independently select the final visual reviewer. For example:

```sh
.venv/bin/python -m nox -s ide-smoke -- --agent --surface pycharm --driver claude
.venv/bin/python -m nox -s ide-smoke -- --agent --surface codium --driver claude --recognizer codex
```

Both providers implement `tests/e2e/ai_driver.py`'s image/decision contract;
`visual_smoke.py` owns the sole scenario and applies mouse/keyboard actions.
CLIs run in an evidence directory with their tools disabled. They use the
parent developer's existing authentication; no agent credentials are copied
to the child IDE capsule. Codex's JSONL currently omits a reported model id,
so the record distinguishes its explicit CLI selection from server-reported
identity. Claude's structured result must report the selected model.

Agent mode requires Playwright, Chromium and working model access; absence is
a failure. Defaults bound the agent to 30 actions, 900 seconds overall and
120 seconds per model invocation, without automatic retries. Set
`--max-actions` or `--agent-timeout` for a deliberate different budget.
The launch and IDE-window checks have their own finite deadlines.

Select `browser-automation` in a development project's capabilities to install
the Playwright component. It supplies Python Playwright and pinned Chromium
under `/opt/playwright`, with `PLAYWRIGHT_BROWSERS_PATH`,
`DEVCAPSULE_PLAYWRIGHT_PYTHON` and `DEVCAPSULE_PLAYWRIGHT_WHEELS` in its runtime
environment. Nox installs its binding from those verified local wheels and
uses the component browser without downloading another copy. The wheels
currently target Linux x86-64 and CPython 3.12. They and the browser belong to
the image; they need no persistent state slot. A host without the component
uses Nox's explicitly pinned package/browser installation. The authorized
one-off `/opt/xtras` bootstrap is separate from this managed installation.

Evidence adds executable checksum/version, image/container identity,
`ai-selection.json`, `agent-result.json`, per-action prompts, CLI events,
usage where reported, screenshots and `agent-desktop.webm`. The recognizer
consumes sampled PNG frames, not a claimed direct video input. Raw launcher
logs contain the ephemeral desktop access URL; sanitize it before sharing.

## Running inside a capsule

All of this runs from a capsule that has host Docker and host networking:
the launcher translates bind sources to host paths for nested launches, and
the IDE smoke puts its projects under the persistent home's E2E workspace for
that reason. `project recursive-e2e preflight --json` reports whether the
capsule is ready. This harness records host networking in its disposable
project at initialization: the current CLI rejects the local workflow guide's
run-once `--authorize network host` spelling. The hosted runner runs none of it; that is a rule, not a
limitation to fix.

## Fresh workspaces, by rule

Owner ruling of 2026-10-05: every end-to-end test runs on a fresh
workspace. It refuses a source checkout with uncommitted changes, clones
the current branch from the local tree into its own run directory, resolves
that clone under configuration roots isolated beneath the run directory,
and runs against the clone. It never runs against the live checkout and
never reads the capsule's own checkout records or resolution. This is what
removes the circular dependency between the repository under test and the
capsule that tests it: the capsule's configuration can go stale or be
read-only without the test caring. Inside a capsule the run directory goes
under the persistent home's E2E workspace, a host-backed path the daemon
can bind; `/tmp` is a container-local tmpfs the host daemon cannot see.
At the end the test makes a best-effort attempt to remove the workspace and
free the space; a failure to clean up is reported, not fatal.

`tests/e2e/fresh_workspace.py` is the rule as code: `FreshWorkspace.create`
refuses a dirty source and clones HEAD into an owned run directory,
`configure_like_this_capsule` answers and resolves the clone under
isolated roots through the ordinary commands, `environment` and `cli` run
the launcher under test against the clone, `cleanup` removes the run
directory. `test_recursive_successor_attached_launch.py` uses it;
`test_recursive_local_clone.py` keeps its own protocol proof of the clone
itself; the other suites follow as they are touched.

## Where the next end-to-end test goes

A new proof that needs Docker goes in `tests/e2e/` with the `e2e` marker,
plus a second marker when it needs a capsule (`recursive_e2e`), a
contributor base (`contributor_e2e`), a freshly built base
(`base_build_e2e`) or a real IDE (`ide_smoke`), so the right session picks it
up and no other does. Register a new marker in `pyproject.toml`, since
pytest warns about an unknown one at collection, and wire its session in
the noxfile; `test_noxfile.py` covers how each session selects the
executable under test, so a new session that selects one gets a case there.
