# Authoring toolkit validation, 2026-11-16

Target: `release-0.3.1`, starting at `10e7fda3`. The implementation branch is
`ws-presentations/0.3.1-authoring`. Main's next-development version was not
carried onto this branch. The original registration branch remains intact.

## Contract and implementation

The engineer supplies Markdown or inline English. The agent translates that
scenario into the ordinary Playwright actions and assertions for the project,
using shipped instructions and helpers. The toolkit does not interpret natural
language itself. It does not require a DevCapsule source clone or test imports.

The installed CLI exposes `presentations guide`, `export <new-directory>` and
`hand-off <evidence-folder>`. Export supplies a standard-library Python package
for the capsule's Playwright interpreter, plus the guide and an adaptable driver.
The existing producer moved into that package; the repository replay adapter
keeps its former script-root default. Its 39 existing tests moved with it.

The recorder captures bursts around small Playwright callbacks. It keeps native
video when the caller configures it, derives times from frame counts and writes
the presentation last. The project's assertions determine test success. Failed
and incomplete attempts stay labelled. The existing viewer and schema are unchanged.

## Checks

Commands run from `devcapsule-src` with its existing `.venv`:

```sh
.venv/bin/python -m pytest -q --no-cov tests/test_scenario_recorder.py tests/unit/devcapsule/presentation_tools tests/unit/devcapsule/test_presentation_authoring.py
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS='--basetemp=/var/tmp/presentations-gate/pytest --maxfail=1' .venv/bin/python -m nox -s build
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS='--basetemp=/var/tmp/presentations-gate/console' .venv/bin/python -m nox -s pex docs-contract webconsole
```

The scratch parent was created first. `/opt/devcapsule-gate` is read-only here.

| Check | Result |
| --- | --- |
| Focused unit tests | 59 passed; final run including the repository recorder: 121 passed |
| Version and syntax | passed; package remains 0.3.1 |
| Mypy | 352 source files, no errors |
| Conventions | 99 legacy files / 1315 legacy tests; 64 conforming files; 0 breaches; 3 files in command-line debt |
| Full gate's unit phase | 1438 passed, 1 skipped, 175 deselected, stopped at 1 failure |
| Remaining PEX build and smoke | passed |
| Documentation contract | 249 pages including 18 aliases, passed |
| Webconsole | 474 tests passed; type check passed |

The failure is the previously observed
`test_public_dry_run_is_unique_redacted_and_cleans_owned_staging`:
`host Docker group ID must be a positive integer`. No attempt was made to
change this unrelated fixture. The full gate is not green. An initial invocation
from the wrong directory, and a missing scratch parent, were corrected before
the results above; neither is counted as a product failure.

## Installed artifact and real browser

Built `dist/devcapsule-local.pex` with the repository's local-source policy;
SHA-256 `ca6ee98a3f7af039729fa42c34f05e3b9ad299acc1a83ab2b03b8adced1e2aea`.
This is not a published release candidate. From `/var/tmp`, the executable
printed its packaged guide and exported the kit into an unrelated scratch
directory. Its helpers imported without importing `devcapsule` or `tests`.

The scratch project was a small shopping-list application served on loopback.
Its English scenario was: open the application, add milk, reload and verify
milk remains. The agent wrote a driver using only the exported kit and ordinary
Playwright. The cached Chromium and Playwright ffmpeg ran locally; no image,
capsule or browser download was needed.

| Run | Assertions/result | Presentation |
| --- | --- | --- |
| Passing | add and reload observations passed | 3 steps; 2 seconds |
| Deliberately failing | wrong expected item raised AssertionError; result stayed failed | 2 reached steps; FAILED title; 0.917 seconds |
| Incomplete | stopped after opening; result stayed incomplete | 1 reached step; INCOMPLETE title; 0.667 seconds |

Each retained a native Playwright video and the generated movie/screenshots.
The viewer was extracted from the built executable and served with the existing
webconsole environment against the scratch project. Links came from the built
`presentations hand-off`, including its token-file handling. All six chapters
played, all step screenshots loaded, and the native media duration agreed with
each manifest to within 0.1 second. No viewer schema failure appeared.
The temporary services were stopped. Raw files and verification scripts remain
only under `/var/tmp/presentations-acceptance`; no tokened URL is committed.

The exported example driver also ran successfully against the scratch application's file URL, checking its heading before and after reload.

These checks prove packaging and compatibility with the accepted viewer. They
do not replace the owner's prior human acceptance or the requested independent
Pair Review. The model catalog lists `gemini-4-hydrogen-high` and CLI help
supports `--effort high`; no reviewer invocation has occurred. The prescribed
GitHub CLI is absent, so PR creation is an owner action under WORKFLOW-LOCAL.
