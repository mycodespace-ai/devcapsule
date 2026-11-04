# Unit Tests

[Development](README.md) · [Developer environment](developer-environment.md) · [Source layout](source-layout.md) · [Integration tests](integration-tests.md) · [End-to-end tests](e2e-tests.md)

## Conventions

*Unit Tests* in [`WORKFLOW-LOCAL.md`](../../WORKFLOW-LOCAL.md) binds: a
unit test file mirrors its module under `tests/unit/`, a test is a
precondition, one call and a postcondition, and its docstring states the
contract. The companion explains why. `scripts/validate_unittests_follow_conventions.py` is the
gate's check; its summary line counts the files still marked `legacy`. The
flat files under `tests/` are those legacy files: they only lose tests, and
a test you change moves to the mirror with you.

## Running them

```text
cd devcapsule-src
.venv/bin/python -m nox -s tests          # the suite, with coverage
.venv/bin/python -m pytest tests/test_project_init.py -k regenerate   # one module, one pattern
```

Pytest's configuration is in `pyproject.toml`: `testpaths = ["tests"]`, the
project root on `pythonpath`, branch coverage of the `devcapsule` package
with a terminal report of missing lines, and the default selection
`-m "not integration and not e2e"`. So a bare `pytest` under `tests/` is the
unit suite; the heavier suites are chosen by marker, never by accident. The
`flaky` marker runs a test for visibility with a temporarily non-blocking
result; `own_host_patches` marks a unit test that patches the host itself
(see Fixtures); the other markers belong to the heavier suites.

On a pull request the hosted workflow also writes both coverage figures,
changed lines covered and the whole package, into the pull request's
description between two marker comments, through
`scripts/publish_coverage_numbers_to_pr.py`; a merge that takes the
description as its message carries them into `main`'s history. The block is
replaced on every run and the author's text around it is never touched.

The hosted `tests.yml` workflow selects the existing serial unit suite when
runtime, test, build or unclassified inputs change. It runs no Docker.
Planning/status-only PRs skip heavy jobs; website inputs run the website's
own tests and build. The filters live in `.github/ci-paths.yml`: each route
lists the paths proven not to be its inputs, and any other changed path runs
the job. Root README, journal entries and release notes are website inputs,
while packaged Markdown under `devcapsule-src/` remains a runtime input, and
so do `docs/versions.yaml` and the published release notes, which the unit
suite reads as fixtures. A pull request with more than 3000 changed files
runs everything, because GitHub's changed-file listing stops there. Console
changes conservatively run the hosted Python suite, but its runtime coverage
does not measure the separate console distribution; the local
`nox -s webconsole` gate still applies.

Main pushes, merge-queue checks and manual runs use full applicable verification.
PRs into `main` and `release-*` test the PR head SHA. The advisory diff report
compares that same revision against the merge base with the event's base SHA,
so warning coordinates refer to the code the author changed. Coverage
artifacts and the main-only badge remain available.

### Advisory changed-line coverage

From `devcapsule-src`, using the locked development environment:

```sh
.venv/bin/python -m pytest tests/ --cov-report=xml:coverage.xml
.venv/bin/diff-cover coverage.xml --compare-branch=origin/main \
  --format markdown:diff-cover.md,json:diff-cover.json
```

Fetch the actual target branch first and substitute it for `origin/main`
when appropriate, for example `origin/release-0.3.0`. The reports measure
changed executable lines in the runtime package, not changed-branch coverage.
No percentage blocks a PR. Tests, invalid routing and failed reporting still
fail CI. No measured executable lines means not applicable, not 100% coverage.

The annotation bridge publishes at most ten warning ranges per step, escapes
GitHub command fields, and directs the reader to the complete uploaded report
when inline output is truncated. The summary has a size budget too; an oversized
table remains available in the artifact. Native annotation placement must be
checked on a real PR, not inferred from the command's exit status.

### Required-check rollout

Establish `ci-gate` on a representative PR before making it required. The
owner changes repository settings: replace an existing required `Python 3.12`
check with `ci-gate`, preserving other required checks, or add `ci-gate` when
no CI check is currently required. YAML changes do not change branch protection.
The aggregate requires successful routing and every selected verification job;
unselected jobs may be skipped. A reporting failure is not a coverage warning.
Keep the implementation PR's acceptance record explicit about the settings
migration and the hosted cases verified.

## What is in the suite

Sixty modules at the time of writing, about one per module or contract of
the package, in two places:

- `tests/test_*.py`, fifty-three modules, one per subsystem of the package:
  the command framework and CLI grammar, `project init` and the project
  commands, the resolution matrix and the base contract, materialization and
  image build, the components (Codium, PyCharm, Codex, Claude Code,
  Antigravity, PostgreSQL client), the contained display and its host-side
  client, the supervisor and the runtime entrypoint, the recursive-launch
  modules, release manifest, protocol and compatibility, version sets and
  upgrade recovery, workflow bootstrap and coordination, and the noxfile
  itself (`test_noxfile.py` checks the gate's own session wiring).
- `tests/configuration/`, seven modules that are the configuration
  boundary's proof: `test_architecture.py` asserts the domain/adapter
  dependency rule by inspecting imports; `test_adt.py` and `test_contract.py`
  state the laws of admission and resolution and the lifecycle's proof
  obligations independently of branch coverage; `test_invariants.py` holds
  the cross-boundary invariants partitioned by contract condition;
  `test_nodes.py` and `test_history.py` cover the node registry and the
  known-good history.

Tests are written from the contract: the module docstring names the
behaviour's ownership and invariants, and a test asserts a postcondition an
adopter can observe, not an implementation detail. Where the real path is
cheap it is exercised; where it needs Docker or a GUI it is controlled, and
the controlled parts are named in the docstring. The owner's standing
caution applies when adding tests beside new end-user functionality: a
fresh test can encode the same unvalidated assumption as the code it checks,
so prefer the existing laws and an acceptance step for what the user sees.

## Fixtures

`tests/conftest.py` holds the suite's shared fixtures and hooks:

- `host_launch_by_default`, autouse: makes launcher tests behave as if they
  run on the host, since the launcher translates bind sources when it finds
  itself inside a capsule and the suite is often run from one.
- `amd64_linux_host_by_default`, autouse: makes the host an amd64 Linux
  machine with an amd64 Docker daemon, as on the CI, since the launcher takes
  other paths on macOS and Apple Silicon runs linux-arm64 capsules. A test of
  another host patches the host itself and carries `own_host_patches`;
  Docker-marked tests keep the real host.
- `private_user_directories`, autouse: moves `HOME` and every XDG directory
  under the test's `tmp_path` for non-Docker tests. Inside a capsule this is
  not yet a private home: a home with no settings of its own reads the
  launcher's mounted settings, so tests that assume no accepted vendor
  channel fail there. Recorded on 2026-11-03 for the 0.3.1 fixture slice.
- `built_pex`: the executable under test, `DEVCAPSULE_PEX_UNDER_TEST` when
  set, otherwise `dist/devcapsule-local.pex`; it fails with the Nox session
  to run when the file is missing. The integration and end-to-end suites use
  it; the unit suite does not need an artifact.
- `pytest_configure` and `pytest_sessionfinish`: on macOS, a short temporary
  root under `/tmp`, because a Unix socket path there is limited to 104
  bytes. A session whose tests all passed removes it; a failed one keeps it
  and prints its path.

Everything else is local to its module: fakes for Docker and vendor
services, temporary XDG roots, and the `tmp_path` pytest provides.

## Resources

`tests/resources/` holds versioned inputs:

- `golden_locks/`: platform locks the matrix must keep producing for the
  named need sets, one per combination (`pycharm-minimal`, `pycharm-full`,
  `codium-node`, `codium-agents`, `codium-antigravity`, `dogfood`). A matrix
  change that alters one is a deliberate, reviewed change.
- `compat/`: artifacts produced by earlier released clients, never
  regenerated, proving R-COMPAT-001: a newer client needs no user action
  for a project, checkout or lock an older one created. [Its README](../../devcapsule-src/tests/resources/compat/README.md)
  names each client and what was templated.
- `sample_projects/`: three sample projects as submodules, fixtures for the
  project model; they have their own suites and are excluded from this one
  by `norecursedirs`.
- `supervisor_driver.py`: a driver that runs the supervisor over a JSON
  child-set specification, used by the supervisor and runtime tests.

## Type checking

`nox -s typecheck`, also inside the gate, runs mypy over the package, the
tests, the noxfile and the release scripts with the settings in
`pyproject.toml`. Tests are typed like source; an optional dependency a
test imports, Playwright for instance, carries an explicit ignore with its
reason rather than a loosened configuration.
