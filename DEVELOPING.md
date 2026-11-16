# For developers

[Back to DevCapsule](README.md)

DevCapsule creates reproducible, resumable development environments for
humans and AI coding agents: a real IDE, agent-ready tooling, versioned
project memory, and explicit boundaries around access to the host. The
product is one Python distribution project in `devcapsule-src/`, shipped as
a single Linux executable, plus the capsule web console in
`devcapsule-webconsole/`, shipped inside the base image. This page is the brief; each subject has its own
document under [`engineering-docs/development/`](engineering-docs/development/README.md).

## Contents

1. [Developer Setup](#developer-setup)
2. [Source layout](#source-layout)
3. [Testing](#testing)
4. [Releasing](#releasing)
5. [Website](#website)
6. [Principles](#development-principles)
7. [Where to read next](#where-to-read-next)

## Developer Setup

```text
cd devcapsule-src
python3.12 -m venv .venv
.venv/bin/python -m pip install -r dev-requirements.txt
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m nox -s build      # the full local gate, before any checkpoint
```

Setup, the gate's steps, building the executable, the shipped `devcapsule0`
versus the development `devcapsule`, and working from inside a capsule:
[Developer environment](engineering-docs/development/developer-environment.md).

### IDE project files

The repository tracks the JetBrains project files that PyCharm itself does
not ignore. `.idea/.gitignore`, written by PyCharm, is JetBrains' own list
of per-machine files and is the contract; everything else under `.idea/`
is committed: the module files PyCharm generates from each `pyproject.toml`
it finds, the modules list, and the shared run configurations under
`.idea/runConfigurations/` (the unit tests and the `devcapsule` CLI), so
that another checkout runs and debugs without setup. Both configurations
use the module's interpreter and project-relative paths; nothing in them
names a machine.

The one per-machine step is the interpreter. Register
`devcapsule-src/.venv` as the project interpreter once; PyCharm names it by
its path, which is the name the module file carries as a `$MODULE_DIR$`
macro, so the committed module and run configurations resolve to it.
`.idea/misc.xml` stays ignored: it records the workstation's project SDK by
name, and once tracked it makes PyCharm add every new `.idea` file to VCS
on its own.

DevCapsule writes nothing into `.idea` and takes no responsibility for IDE
settings across ecosystems; it relies on the IDE cooperating with Git.
Other projects choose their own rule. Owner's rule of 2026-10-23, replacing
the ruling of 2026-10-01 to ignore the directory.

## Source layout

### Python package boundaries

The repository's directories and the `devcapsule` package's responsibilities,
including the enforced configuration boundary:
[Source layout](engineering-docs/development/source-layout.md).

`devcapsule-webconsole/` is a second, smaller distribution: the capsule web
console, a FastAPI application and a static tree that the runtime starts as
its own process. It reads the runtime CLI's `--json` output and imports none
of the `devcapsule` package. See its [README](devcapsule-webconsole/README.md).

## Testing

| Suite | Command | Document |
|---|---|---|
| Unit tests, with coverage; what the hosted runner runs | `nox -s tests` | [Unit tests](engineering-docs/development/unit-tests.md) |
| Integration: a subsystem with the real executable, subprocess, git or Docker daemon it uses, the rest faked | `nox -s integration`, on demand, and before a candidate; the CLI smoke, types and docs contract are gate checks inside `build` | [Integration tests](engineering-docs/development/integration-tests.md) |
| End-to-end, with Docker: images, capsules, the IDE smoke | `nox -s e2e`, `nox -s ide-smoke`, … | [End-to-end tests](engineering-docs/development/e2e-tests.md) |
| The capsule web console, `devcapsule-webconsole/`: types and tests in its own environment | `nox -s webconsole`, queued by `build` | [Web console README](devcapsule-webconsole/README.md) |
| A change to the web console, seen in a browser before anything is built | `nox -s webconsole-preview`, which serves this checkout's console on loopback and prints its links | [Trying a change](devcapsule-webconsole/PRESENTATIONS.md#trying-a-change) |

The hosted runner runs no Docker; the end-to-end suites run locally and
against downloaded candidates during release acceptance.

## Releasing

Follow [Releasing a new DevCapsule version](engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md):
an immutable candidate from a retained release branch, validated as
downloaded, integrated with its acceptance record, tagged for final
publication; documentation and the website are part of the release.

## Website

Initialize the submodule with `git submodule update --init website`, then
`./scripts/website.sh install` and `./scripts/website.sh preview`. The site
has its own checks and publishing rules in
[`website/README.md`](website/README.md) and
[`website/PUBLISHING.md`](website/PUBLISHING.md); the documentation it
publishes follows the
[content–website contract](engineering-docs/specifications/product/content-website-contract.md).

## Development Principles

- Keep host filesystem, credentials, Docker, devices and networking exposure
  explicit and documented.
- Keep current behaviour in user documentation; preserve obsolete behaviour
  only as clearly labelled history.
- Store requirements, decisions, bugs, validation evidence and status in
  versioned files, never only in chat.
- Add automated, Nox-covered checks when practical; validate host Docker,
  image and GUI behaviour manually where automation cannot reach.

## Where to read next

- [`AGENTS.md`](AGENTS.md), mandatory instructions for coding agents, and
  [`WORKFLOW.md`](WORKFLOW.md) with [`WORKFLOW-LOCAL.md`](WORKFLOW-LOCAL.md),
  the human-agent protocol and this project's half of it.
- [`CURRENT-STATUS.md`](CURRENT-STATUS.md), the open-workstream list;
  this repository runs the workflow in `multiple-streams` mode.
- [`REQUIREMENTS.md`](REQUIREMENTS.md), the requirement overview, and
  [`engineering-docs/README.md`](engineering-docs/README.md), the placement
  rules for everything under `engineering-docs/`.
- [`docs/README.md`](docs/README.md), the product documentation, and
  [`index.md`](index.md), the complete documentation map.
- [`devcapsule-src/README.md`](devcapsule-src/README.md), the CLI source and
  contributor reference.

DevCapsule is licensed under the [Apache License 2.0](LICENSE); third-party
components keep their own terms, see [NOTICE](NOTICE).
