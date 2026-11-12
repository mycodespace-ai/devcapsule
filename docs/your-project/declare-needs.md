---
description: How .devcapsule/devcapsule.toml and the platform lock define capabilities, minimums, environment inputs, and recommendations without granting permissions silently.
weight: 3
updated: 2026-10-30
---
# What a project declares

Every DevCapsule project commits two files under `.devcapsule/`:

1. **The manifest (`.devcapsule/devcapsule.toml`, schema `2` in {{tag}}):**
   declares project identity, required and offered capabilities, environment
   variable names, typed configuration values, and project recommendations.
2. **The platform lock (`.devcapsule/devcapsule.<platform>.lock`, such as
   `devcapsule.linux-amd64.lock`):** pins the exact base image digest and
   component versions resolved from the manifest.

Together they pin the project's shared base and capabilities. Each checkout
separately pins its personal IDE and added capabilities. Credentials and
host-access grants stay outside Git.

## Manifest fields

The root key `devcapsule-schema-version = 2` selects the current schema.
The manifest uses these tables:

| Table | Contents |
|---|---|
| `[project]` | `name`, `slug`, `creator`, and the container `mount` path |
| `[capabilities]` | `required` entries, optionally `NAME>=VERSION`, and `optional` capability names |
| `[capabilities.reasons]` | Reasons supplied with `--because` |
| `[capabilities.resolution]` | Recommended providers, such as `frontend-ide = "codium"` |
| `[environment.required.NAME]`, `[environment.optional.NAME]` | Environment variable declarations, with an optional `reason` |
| `[configuration.values."NAME"]` | A value's `type`, optional `required`, `recommended`, and `description` fields |
| `[recommendations]` | Default `ide`, `memory`, and `cpus` values |
| `[host.*.recommended]` | Host-access requests with `value` and `justification` |
| `[workflow]` | Workflow `definition`, `version`, and `mode`, when the project uses a workflow |

Use the commands below to keep the manifest and lock consistent.

## Capabilities in the catalog

You declare **capabilities** (what the project needs), and DevCapsule resolves
them to **components** (or base-image toolchains) in the lock:

| Category | Capabilities | Supplied by |
|---|---|---|
| Languages, build tools, and clients | `python`, `node`, `java`, `maven`, `docker-cli` | Pinned base image |
| SDK | `dotnet` | `dotnet-sdk` |
| Database client | `postgresql-client` | `postgresql-client` component, supplied by the pinned base |
| Browser automation | `browser-automation` | `playwright` (Python Playwright + Chromium) |
| Desktop IDEs | `python-ide`, `frontend-ide`, `vscode-ide`, `java-ide`, `eclipse-ide`, `dotnet-ide` | `pycharm`, `codium` or `vscode`, `vscode`, `intellij`, `eclipse`, `rider` |
| Coding agents | `codex-agent`, `claude-code-agent`, `antigravity-agent` | `codex`, `claude-code`, `antigravity-cli` |

Update capabilities with CLI commands so the manifest and platform lock stay
synchronized:

```bash
devcapsule project config require 'java>=21' --because "the build targets Java 21"
devcapsule project config offer browser-automation --because "needed for UI integration tests"
devcapsule project config offer codex-agent --because "optional Codex instructions in AGENTS.md"
devcapsule project config drop browser-automation
```

- **Required capabilities (`require`)** apply to every checkout and accept an
  optional `NAME>=VERSION` minimum. Contributors cannot omit them (the one
  per-launch departure is `project run --ide IDE --force` when a project
  requires an IDE; see [Capabilities and
  components](../configuration/capabilities.md#a-required-ide)).
- **Offered capabilities (`offer`)** are included by default, and any developer
  can omit them on their checkout with `devcapsule project config omit CAPABILITY`.

Add `--preview` to `require`, `offer`, `drop`, or `recommend` to validate the
change without writing it. IDE choices are personal: use `config recommend ide
IDE` for a team default.

## Environment inputs and declared values

Declare the environment variables your application or test suite expects—names
and reasons only, never secret values:

```bash
devcapsule project config require env DATABASE_URL --because "API integration tests connect to PostgreSQL"
devcapsule project config offer env LOG_LEVEL --because "overrides default info logging"
```

Remove a declaration with `devcapsule project config drop env LOG_LEVEL`.
Contributors supply values with `devcapsule project config env set NAME`;
that command prompts for a hidden value.

At an interactive terminal, `project run` prompts with hidden input for any
missing required variable and saves the answer in the developer's private
per-checkout store (never in Git). Without a terminal, a missing required
variable stops launch with exit status `3`.

Projects can also declare typed non-secret configuration values (`string`,
`integer`, `boolean`, `memory-size`) under `[configuration.values."..."]`.
`required` defaults to `false`. A `recommended` value supplies the default
unless the checkout overrides or omits it. `config set NAME default` accepts
that recommendation; it fails if no recommendation exists. See
[Resource limits](../configuration/resource-limits.md#values-a-project-declares).

## Recommendations versus permissions

A project owner can record defaults and advice in `.devcapsule/devcapsule.toml`:

```bash
devcapsule project config recommend ide frontend-ide
devcapsule project config recommend frontend-ide codium
devcapsule project config recommend memory 6G --because "integration tests need more memory"
devcapsule project config recommend cpus 2
devcapsule project config recommend network host --because "local OAuth callbacks target localhost:8080"
```

How DevCapsule treats recommendations:

- **IDE, provider, and resource recommendations** supply the default when a
  checkout has not chosen its own IDE, provider (`config use`), or resource
  limit (`config set`).
- **Host-access recommendations** (`network`, `docker-daemon`,
  `development-sudo`, `host-browser`) **never grant access automatically**.
  They require a `--because` reason and present a prompt (or pending row in
  `config show`) on each developer's machine so the developer can allow, allow
  once, or deny ([Granting and withdrawing
  access](../containment/granting-and-withdrawing.md)). `host-x11` can never be
  recommended by a manifest.

## Refreshing and validating the lock

When you upgrade your `devcapsule` launcher and want to refresh the repository's
platform lock against the launcher's current embedded component matrix (or
migrate an older schema-1 manifest to schema `2` while keeping its leading
comments):

```bash
devcapsule project init --regenerate
```

Use `--regenerate` for this operation; `project init` has no `--force` option.
Review the `.devcapsule/` diff with `git diff` and commit both files together.
To validate `.devcapsule/devcapsule.toml` and the platform lock in CI without
starting Docker or mutating checkout files, run:

```bash
devcapsule project config check --manifest .devcapsule/devcapsule.toml \
  --lock .devcapsule/devcapsule.linux-amd64.lock
```

This checks the candidate files without assessing a developer's pending
checkout decisions. Plain `config check` also assesses those decisions and
returns status `3` when any remain.

See [Capabilities and components](../configuration/capabilities.md) for the
complete command reference and [Component
upgrades](../updates/component-upgrades.md) for testing newer component pins
before promoting them to the shared lock.
