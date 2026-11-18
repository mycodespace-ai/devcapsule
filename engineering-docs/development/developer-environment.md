# Developer Environment

[Development](README.md) · [Source layout](source-layout.md) · [Unit tests](unit-tests.md) · [Integration tests](integration-tests.md) · [End-to-end tests](e2e-tests.md)

## Setup

The Python project lives in `devcapsule-src/`. Nox is the validation entry
point; bootstrap a checkout-local virtual environment and invoke Nox through
its interpreter explicitly:

```text
cd devcapsule-src
python3.12 -m venv .venv
.venv/bin/python -m pip install -r dev-requirements.txt
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m nox -s tests
```

`dev-requirements.txt` is the locked contributor environment, compiled by
pip-tools from the `dev` extra in `pyproject.toml`; change dependencies
there and recompile, never by editing the lock by hand.

Calling the interpreter directly is intentional: it works without shell
activation and cannot fall through to `/usr/bin/python` when an activation
script carries a stale path. Activation still works:
`. .venv/bin/activate && python -m nox -s build`.

Activation scripts and console-script shebangs embed the directory the
environment was created in. After moving or renaming the checkout or
`devcapsule-src/`, recreate the environment rather than carrying it along:

```text
cd devcapsule-src
deactivate 2>/dev/null || true
python3.12 -m venv --clear .venv
.venv/bin/python -m pip install -r dev-requirements.txt
.venv/bin/python -m pip install -e . --no-deps
```

## The gate

Run the full local gate before a checkpoint and before integration:

```text
cd devcapsule-src
.venv/bin/python -m nox -s build
```

In order it checks that the three version copies agree, compiles the
package, parses every shell script, type-checks, runs the unit tests with
coverage, smokes the source CLI, builds the local executable and smokes it,
runs the integration tests against it, checks the documentation against the
website's content contract, and, on a clean repository only, builds and
smokes the revision-bearing `dist/devcapsule.pex`. On a dirty repository it
says that the revision-bearing artifact was skipped. Add
`--no-reuse-existing-virtualenvs` to discard Nox's cached environments.

Pytest writes its scratch under the system temporary directory by default;
on a host where that is small, point it elsewhere with
`PYTEST_ADDOPTS="--basetemp=/path/with/room"`.

## The executable

The product ships as one self-contained Linux x86-64 executable, a PEX
scie with an embedded CPython. `nox -s pex` writes the local-only
`dist/devcapsule-local.pex`; the gate builds it too. For a source-form
launch of an environment, build it first and either run that artifact or set
`DEVCAPSULE_RUNTIME_PEX` to its absolute path when invoking the source CLI;
rebuild after runtime changes, since the launcher supplies its own bytes to
the capsule. That identity of outside launcher and inside runtime is the
[adopted default](../decisions/product/d-0009-launcher-delivers-identical-runtime.md).
`scripts/build-pex.sh` and its publication rules are described in the
[CLI source README](../../devcapsule-src/README.md#end-user-artifact).

## Shipped CLI versus development CLI

This repository's `.devcapsule/devcapsule.toml` recommends
`runtime.devcapsule-command = "devcapsule0"`: in a newly materialized
capsule, `devcapsule0` is the exact shipped launcher and the name
`devcapsule` stays free for the development installation. Use the shipped
command deliberately when testing released behaviour, and the virtualenv's
`devcapsule` or the built PEX for current work; never fall back to the
shipped one silently when the development setup is missing. The
recommendation is an ordinary configuration value, not a permission; a
checkout overrides it from the outside launcher with
`devcapsule project config set runtime.devcapsule-command devcapsule`;
inspect it with `devcapsule project config show`. It takes effect at the next launch.

## Working inside a capsule

The project is developed inside DevCapsule. A capsule with host Docker and
host networking can run everything above, including the Docker-backed
suites: the launcher translates bind sources to host paths for a nested
launch, provided the project lives on a host-backed path such as the
persistent home. `/opt` and the container's own filesystem are disposable;
`/opt/xtras` and the home persist. Local operating rules, host networking
for launches among them, are in [`WORKFLOW-LOCAL.md`](../../WORKFLOW-LOCAL.md).
