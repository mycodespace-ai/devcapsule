---
id: D-0017
title: The Launcher Delivers Its Web Console Package On The Base Interpreter
status: accepted
date-proposed: 2026-11-08
date-decided: 2026-11-08
decided-by: Costin Cozianu
requirements:
  - R-CONSOLE-001
  - R-RUNTIME-001
supersedes:
superseded-by:
---

# D-0017: The Launcher Delivers Its Web Console Package On The Base Interpreter

Decided by the product owner on 2026-11-08 during `v0.3.1-rc1` release
candidate validation; see the
[bug record](../../bugs/devcapsule/2026-11-08-webconsole-changes-do-not-ship-without-a-base-rebuild.md).

## Context

[R-CONSOLE-001](../../requirements/product/r-console-001-capsule-web-console.md)
installs the capsule web console into the base image under
`/opt/devcapsule-webconsole`: a hash-pinned Python virtual environment
(`FastAPI`, `Uvicorn`, `Pydantic`, `psutil`) and the `devcapsule_webconsole`
package.
[D-0009](d-0009-launcher-delivers-identical-runtime.md) decoupled CLI releases
from base-image publication by having the launcher install its own
`devcapsule.pex` into the derived formation image during materialization.

`devcapsule_webconsole` remained outside `devcapsule.pex`. Consequently, a CLI
release that changed web console routes or static assets—without changing
third-party Python dependencies—did not reach adopter capsules unless both
`linux-amd64` and `linux-arm64` base images were rebuilt, published, and
re-pinned first. At the same time, the launcher's self-hosting exception
mounted `<project_mount>/devcapsule-webconsole` on `PYTHONPATH` whenever a
mounted workspace contained `devcapsule-webconsole/`, even when running a built
release candidate executable. During `v0.3.1-rc1` validation on a checkout on
an older branch, that unconditional override shadowed the console and hid what
the candidate itself delivered; on `release-0.3.1`, it would instead mask the
missing candidate delivery.

## Options Considered

### Console delivery

#### Option A: The launcher delivers `devcapsule_webconsole` on the base interpreter

Embed `devcapsule_webconsole` in `devcapsule.pex` as a tracked PEX build input.
During environment materialization, unpack and copy that package read-only to
`/opt/devcapsule/webconsole` alongside `/opt/devcapsule/bin/devcapsule.pex`.
Run `/opt/devcapsule-webconsole/venv/bin/python` with `/opt/devcapsule/webconsole`
on `PYTHONPATH` when the base interpreter satisfies the console's dependencies,
falling back to `/opt/devcapsule-webconsole` on older bases.

Cost: ~420 KB compressed in `devcapsule.pex`, and console code edits change
`pex-sha256` (triggering a fast local formation rebuild, just as CLI edits
already do under D-0009). Adding or upgrading a third-party Python dependency
of `devcapsule_webconsole` still requires a new base recipe.

#### Option B: Keep `devcapsule_webconsole` base-image-only and gate release pins

Keep the console package exclusively in `/opt/devcapsule-webconsole`, rebuild
and re-pin both `linux-amd64` and `linux-arm64` base images before every
release that touches `devcapsule-webconsole/`, and add a release gate check
that refuses older base pins.

Cost: every console HTML, CSS, JavaScript, or Python fix forces a multi-arch
base-image build, registry publication, and lock refresh across adopter
projects—reintroducing for console UI changes the release coupling D-0009
removed for the runtime.

### Self-hosting checkout override

#### Option 1: Built executable runs its own console; source runs or opt-in use the checkout

A built `devcapsule.pex` runs its own launcher-delivered console by default,
even when the mounted project is a DevCapsule checkout. Unbuilt source-form
launches (`.venv/bin/devcapsule`) use `<project_mount>/devcapsule-webconsole`
automatically, and built executables opt in only when
`DEVCAPSULE_DEV_WEBCONSOLE=1` is set on the host.

Cost: a contributor running a built `devcapsule` binary while editing
`devcapsule-webconsole/` sets `DEVCAPSULE_DEV_WEBCONSOLE=1` (or runs from
`.venv`) to preview live checkout edits.

#### Option 2: Keep the unconditional checkout `PYTHONPATH` override

Always mount `<project_mount>/devcapsule-webconsole` when that directory exists
in the workspace.

Cost: dogfooding a release candidate on the DevCapsule repository tests
whichever branch is checked out in the workspace rather than the candidate
artifact under test.

#### Option 3: Remove the checkout `PYTHONPATH` override completely

Always run `/opt/devcapsule/webconsole` and require building a local PEX to
test console edits inside a capsule.

Cost: slower inner loop during active web console development from a source
environment.

## Decision

Adopt **Option A** (`launcher-package`) and **Option 1** (`source-or-opt-in`):

1. `scripts/build-pex.sh` embeds `devcapsule_webconsole` (Python modules and
   static assets) inside `devcapsule.pex` and checks `devcapsule-webconsole/`
   alongside `devcapsule-src/` when verifying clean PEX inputs.
2. During environment materialization, `devcapsule/materialization.py` unpacks
   the embedded `devcapsule_webconsole` bundle from the delivered `runtime_pex`
   and installs it read-only at `/opt/devcapsule/webconsole`. Because the
   bundle lives inside `runtime_pex`, `runtime.pex-sha256` binds the console
   package into formation identity.
3. The base image continues to provide `/opt/devcapsule-webconsole/venv` and a
   baseline console copy. Inside the capsule, the runtime supervisor and
   `project checkout decisions` select the console package in precedence order:
   an explicit checkout `console.source_path` when compatible with the base
   interpreter, otherwise `/opt/devcapsule/webconsole` when present and
   compatible, otherwise the base image's `/opt/devcapsule-webconsole` copy.
4. A built DevCapsule executable sets `console.source_path` to empty by
   default, even on a DevCapsule checkout. `console_development_source`
   selects `<project_mount>/devcapsule-webconsole` only in unbuilt source-form
   launches or when `DEVCAPSULE_DEV_WEBCONSOLE` explicitly enables it (`1` /
   `true`); setting `DEVCAPSULE_DEV_WEBCONSOLE=0` disables it in source runs.

## Rationale

The web console renders and mediates the CLI's own `--json` contracts,
configuration verbs, workflow records, and decision documents. Shipping CLI and
console from the same revision by construction eliminates version skew between
`/opt/devcapsule/bin/devcapsule.pex` and `devcapsule_webconsole` while keeping
the heavy, hash-pinned third-party Python dependencies (`FastAPI`, `Uvicorn`,
`Pydantic`, `psutil`) cached in the shared base image. Scoping the checkout
override to unbuilt source launches and explicit opt-in ensures that release
candidate dogfooding exercises the exact console shipped inside the candidate
binary.

## Consequences

- Console routes, static pages, and `decisions` CLI tools ship with every
  `devcapsule.pex` release on existing recipe-11 `linux-amd64` and
  `linux-arm64` bases without rebuilding or re-pinning base images.
- Any edit under `devcapsule-webconsole/` marks PEX inputs dirty for
  public-revision builds and produces a new `pex-sha256` on materialization.
- Base images remain responsible for `/opt/devcapsule-webconsole/venv`; adding
  or changing third-party dependencies in `devcapsule-webconsole/requirements.in`
  still requires advancing the base recipe and compatibility probe.
- Dogfooding a built candidate on the DevCapsule repository tests that
  candidate's console regardless of which branch is checked out in the mounted
  workspace.

## Reopen If

`devcapsule_webconsole` gains native compiled extensions that vary by capsule
architecture, or third-party console dependencies change frequently enough to
warrant delivering wheels separately from the base image.
