---
description: Require or offer capabilities, set version minimums, recommend providers, and choose what your checkout runs.
weight: 25
updated: 2026-10-30
---
# Capabilities and components

A **capability** names what an environment supplies; a **component** is the
software that provides it. For example, `browser-automation` is a capability
and `playwright` is its component, while `frontend-ide` can be provided by
either `codium` or `vscode`. Every selected capability resolves to one
component provider.

A project requires or offers capabilities and can recommend an IDE and
component providers:

- A **requirement** applies to every checkout and cannot be omitted.
- An **offer** is included by default unless a developer omits it on their
  checkout.
- A **resolution recommendation** names the provider the project prefers when
  several exist; a checkout can still pick another eligible provider.

The **IDE** has a special launch role: its component opens the project, uses
the capsule display, and owns the container's lifetime (the container exits
when the IDE exits). Coding agents (`codex-agent`, `claude-code-agent`,
`antigravity-agent`) are ordinary capabilities whose components arrive through
vendor channels.

## Create the shared configuration

From your project directory:

```sh
devcapsule project init --creator mailto:you@example.org \
  --require 'java>=21' --offer browser-automation --ide java-ide \
  --with codex-agent
```

`--require` writes a capability name (and optional minimum) to
`.devcapsule/devcapsule.toml`, `--offer` writes an optional project capability,
`--ide` records your checkout's IDE (accepting either an IDE capability such as
`java-ide` or a component name such as `intellij` or `vscode`), and `--with`
adds a personal capability for this checkout (repeatable). The manifest section
looks like:

```toml
[capabilities]
required = ["java>=21"]
optional = ["browser-automation"]
```

Initialization also writes `.devcapsule/devcapsule.<platform>.lock`, pinning the
resolved components for this platform. Commit the manifest and lock together.
If you omit `--ide`, an interactive `init` can ask for one, or you can choose
it later at the first `project run`. Pass `--unverified` when your chosen
combination is valid in the catalog but outside the embedded verification
matrix; the generated lock records any unverified combination explicitly.

## Require and offer capabilities

```sh
devcapsule project config require 'java>=21' --because "the build targets Java 21"
devcapsule project config require 'playwright>=1.21'
devcapsule project config offer codex-agent --because "the project uses Codex instructions"
devcapsule project config drop browser-automation
```

Minimums use one operator: `NAME>=VERSION` (that version or newer). Quote the
token in your shell so `>` does not redirect output. Version comparison checks
dotted integers from left to right, stripping a leading `v` and numeric `+` build
metadata (so `v22.23.1` and `25.0.4+7` compare as `22.23.1` and `25.0.4`).
Prerelease minimums, upper bounds, ranges, and exact pins in `require` are
rejected—the platform lock owns exact version pins.

Running `require 'java>=25'` replaces an earlier Java minimum, and `drop java`
removes the requirement regardless of its minimum. Unsatisfiable minimums fail
before writing any file (for example, `python>=3.14` fails when the catalog's
bases supply Python 3.12).

`require`, `offer`, and `drop` update the manifest and platform lock together
and accept `--preview` (validate without writing) and `--unverified`. If an
older launcher does not know an offered capability, it warns and omits the
offer while keeping required capabilities enforced.

Environment variable declarations use the `env` keyword and update only
`.devcapsule/devcapsule.toml`:

```sh
devcapsule project config require env POSTGRES_HOST POSTGRES_PASSWORD --because "the application connects to the database"
devcapsule project config offer env SMTP_HOST --because "email is optional in development"
```

These commands declare variable names, never values. At an interactive
terminal, `project run` prompts with hidden input for missing required values
and saves them privately; without a terminal, a missing required value stops
launch with status `3`. Optional `env` declarations appear in `config show`
without prompting.

## Recommend an IDE or resolution

```sh
devcapsule project config recommend ide frontend-ide
devcapsule project config recommend frontend-ide codium
```

The first command recommends the IDE capability; the second recommends which
component provides `frontend-ide`:

```toml
[recommendations]
ide = "frontend-ide"

[capabilities.resolution]
frontend-ide = "codium"
```

Provider resolution recommendations take no `--because` flag (the capability's
`require` or `offer` entry carries the reason), update both the manifest and
platform lock, and do not accept `--unverified`. Use `recommend frontend-ide
none` to clear a provider recommendation.
Recommending a provider does not add that capability to the project.

Resource and host-access recommendations update `.devcapsule/devcapsule.toml`:

```sh
devcapsule project config recommend memory 6G --because "the test suite builds a large index"
devcapsule project config recommend network host --because "the dev server uses host ports"
```

Neither grants host access or bypasses vendor trust—each checkout still decides
on its own machine.

## Choose for this checkout

```sh
devcapsule project config ide eclipse-ide
devcapsule project config add claude-code-agent
devcapsule project config omit codex-agent
devcapsule project config restore codex-agent
```

`ide` accepts an IDE capability or component name (`pycharm`, `intellij`,
`rider`, `eclipse`, `codium`, `vscode`). `add` adds a personal capability,
`omit` excludes a project offer or removes your personal addition, and
`restore` re-enables an omitted offer. Required project capabilities cannot be
omitted. `ide`, `add`, `omit`, `restore`, and `use` all accept `--unverified`
when your checkout combination steps outside verified matrix pairs.
Omitting an offer keeps its local version pin. A component needed by another
required capability remains installed.

`config use CAPABILITY COMPONENT` picks a provider when alternatives exist (for
example, `config use frontend-ide vscode` or `codium`), and `config use
CAPABILITY default` returns to the project's recommendation or catalog default.
Any chosen provider must still satisfy the project's minimum version.

All checkout choices and local component pins stay in your checkout record; see
[Component upgrades](../updates/component-upgrades.md) for testing newer
component versions. To override choices for a single launch:

```sh
devcapsule project run --ide frontend-ide --with codex-agent
```

`--with` and `--use CAPABILITY=COMPONENT` are repeatable; add `--save` to
persist launch flags to your checkout record once all required checks pass.
Channel trust accepted via `run --trust CHANNEL` belongs to your configuration
home and is saved even without `--save` once launch review completes.

### A required IDE

A project may require an IDE, for example a project that develops a plugin
for it: `init --require python-ide` or `config require python-ide`. Every
checkout of that project then launches it, and `--ide` with another IDE is
refused. The refusal names the one way past it, for one launch:

```sh
devcapsule project run --ide codium --force
```

`--force` accepts a named departure from the project's contract for this
launch. It does not satisfy the requirement. The launcher warns which required
IDE it sets aside and which IDE runs; the launch's plan and its listing inside
the capsule record the departure. The requirement, the shared lock and your
saved IDE stay as they are. The next plain `run` applies the ordinary
requirements to your saved selection. If that selection already conflicted
with the requirement, the plain launch still refuses it. The downloaded IDE
and its own settings remain available for later;
each IDE keeps its separate settings namespace. `--force` cannot be combined
with `--save`, and it is refused when nothing is set aside: without `--ide`,
with the required IDE itself, or on a project that requires no IDE. It grants
no consent and skips no check: a channel to accept, an artifact that fails
verification, or a required tool that needs the replaced IDE still stops the
launch. A forced launch records no known-good configuration.

## Inspect and recover

```sh
devcapsule project config show
devcapsule project config check
```

`show` lists effective choices, their sources, providers and pending decisions.
A requirement row includes its minimum and resolved version. `check` validates
the contract and reports pending host decisions with status 3. Neither command
downloads components or contacts Docker. Inside a capsule, `show` uses the
captured launch view. `check` validates the contract on disk; current host
decisions need the host launcher.

`check --manifest FILE --lock FILE` validates a candidate contract only.
`config capabilities --recover` repairs an interrupted manifest/lock edit.
Recovery refuses to overwrite files changed independently.

A saved version set must still meet new project requirements. An incompatible
set stops `run` with status 3. `devcapsule project versions follow-project
--apply` returns to the shared lock. The launcher waives no requirement on its
own; the one explicit, per-launch exception is `run --ide IDE --force` for a
required IDE, [above](#a-required-ide).

## Existing files and older launchers

{{tag}} reads schema-1 manifests as well as schema-2 manifests, preserving
existing checkout selections, offered capabilities, IDE recommendations,
provider locks, and per-checkout consents. Deprecated SDK-major tables in older
manifests are ignored with a note; the next shared owner edit or `devcapsule
project init --regenerate` upgrades `.devcapsule/devcapsule.toml` to schema `2`
(keeping its leading comment block) and removes the retired table, while an
untouched schema-1 manifest keeps its existing lock valid until the project
owner edits shared capabilities.

Launchers from releases older than {{tag}} cannot read schema-2 manifests
(`devcapsule-schema-version = 2`), capability minimums, provider resolution
tables, or component-name IDE aliases. When contributors share a repository,
ask everyone to upgrade to {{tag}} before committing a schema-2 manifest.
