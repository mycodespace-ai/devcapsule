---
description: The command tree of the devcapsule launcher, with one line of intent per command and usage for init, run and config.
weight: 1
updated: 2026-11-04
---
# Command reference

Run `devcapsule COMMAND --help` on any command below to see its full argument
and option list. One exception: `devcapsule pycharm check-runtime` runs its
checks even when given `--help`.

`devcapsule project` commands discover the project from the current directory.
To target another directory, pass `--path` before the subcommand:
`devcapsule project --path PROJECT config show`. Inside a capsule, inspection
commands distinguish captured launch data from next-launch choices where available. Commands that need launcher-owned state
print the exact `devcapsule` command to run outside.

## `devcapsule home`

`home` commands act on your [configuration home](../configuration/home.md) and
run from any directory without a project or `--path`. Set
`DEVCAPSULE_CONFIG_HOME` to select a separate self-contained home.

| Command | Intent |
|---|---|
| `show` | Show the home's path and source, format and minimum reader, defaults, and accepted channels. |
| `trust list` | List channels accepted in this home, with vendors, products, origins, and acceptance dates. |
| `trust accept CHANNEL [--yes]` | Show the channel and vendor terms, then ask for acceptance; `--yes` skips the prompt. |
| `trust withdraw CHANNEL` | Remove a channel's acceptance from this home; succeeds cleanly if it was not accepted. |
| `default memory\|cpus VALUE\|none` | Set a memory or CPU default for this home, or clear it with `none`. |

Inside a capsule, `show` and `trust list` read the launcher's settings mounted
read-only until the capsule has its own settings. The first write copies those
settings into the capsule's home. Setting `DEVCAPSULE_CONFIG_HOME` selects that
home instead and disables this fallback to launcher settings.

## `devcapsule project`

| Command | Intent |
|---|---|
| `init` | Create the project manifest and platform lock, record your checkout's IDE and capabilities, and resolve when an IDE is chosen. |
| `wrap` | Add a foreign repository as a submodule, require what you name, create or extend the manifest and lock, declare it as a wrapped source, and write the wrapper's `AGENTS.md` and `README.md`. |
| `run` | Derive the launch plan from the project, this home, and this checkout, ask any open questions, and start the capsule. |
| `config` | Inspect what the next launch uses, change checkout choices or the shared project contract, and validate without launching. |
| `info` | Show selected software, container environment, and persistent storage paths without changing state. |
| `diagnose` | Capture a bounded health snapshot of a running or ended session, and optionally export a sanitized archive. |
| `list` | List checkouts registered in this home. |
| `checkout` | Manage this local checkout's name, notifications, and web-console decision documents. |
| `state` | Adopt an existing host directory into a checkout state slot. |
| `versions` | Check upstream freshness, preview and select checkout-local component versions, or roll back. |
| `recursive-e2e` | Run DevCapsule's own recursive validation harness (contributor tool). |

### `init`

```text
devcapsule project init [--require NAME[>=VERSION]]... [--offer CAPABILITY]... [--ide IDE] [--with CAPABILITY]...
                        [--name NAME] [--slug SLUG] [--creator CREATOR] [--project-mount PATH]
                        [--platform PLATFORM] [--regenerate] [--unverified]
                        [--set NAME VALUE]... [--authorize NAME VALUE]... [--bind NAME VALUE]...
```

`--require` and `--offer` write shared project capabilities into
`.devcapsule/devcapsule.toml` (schema 2) and generate the platform lock. Quote
`NAME>=VERSION` in your shell so `>` does not redirect output. `--ide` chooses
your IDE for this checkout (capability name such as `python-ide` or component
name such as `pycharm` or `vscode`), and repeatable `--with` adds personal
capabilities.

`--regenerate` rewrites the platform lock from the current embedded matrix and
migrates a schema-1 manifest to schema 2 while preserving its leading comments.
Schema-2 manifests cannot be read by candidate 3 or older launchers. When an
IDE is selected, `init` can ask for base or vendor consent; non-interactive
scripts can pass `--authorize NAME VALUE`. `--set`, `--bind`, and `--authorize`
also accept one optional justification argument after the value.

A project has one lock per capsule platform it runs as, such as
`devcapsule.linux-amd64.lock`. A project runs as the first platform this host
runs that it has a lock for; an Apple Silicon Mac runs `linux-arm64` before
`linux-amd64`. On a host that runs more than one, init asks which platform a
new project is for, the native one by default. `--platform PLATFORM` answers
without the question, and adds that platform's lock to a project locked for
another, so on the Mac `devcapsule project init --platform linux-arm64` lets an
emulated project run natively.

### `wrap`

```text
devcapsule project wrap URL [--path NAME] [--upstream URL] [--require CAPABILITY]... [--java LINE]
                        [--ide IDE] [--with CAPABILITY]...
                        [--name NAME] [--slug SLUG] [--creator CREATOR] [--project-mount PATH]
                        [--unverified] [--set NAME VALUE]... [--authorize NAME VALUE]... [--bind NAME VALUE]...
```

Run it at the top level of a Git repository, the wrapper. `wrap` adds `URL`
as a submodule at `--path` (default: the repository's name) with its Git
directory embedded in the tree, requires the capabilities you name, and
declares the source under `[sources."NAME"]` in `.devcapsule/devcapsule.toml`
with the Java line you give, `java = "17"`. Without a manifest it initializes
one as `init` would; with one it adds what is missing. It infers nothing from
the source. It then writes `AGENTS.md` and `README.md` from the manifest,
regenerated on every wrap and left alone when they are yours; a source
without a Java line is described as unsettled, to be found out with the user.

`--upstream` says `URL` is your fork of that upstream: changes and pull
requests go to the fork, never to the upstream. Without it the origin is the
upstream itself and the intent is to learn; nothing is pushed. A rerun keeps
a submodule already added from the same URL, and initializes a registered
submodule whose directory is missing. A different registered URL is refused.
After a partial Git failure, the error names the state to inspect; no files
are removed. An initialization interruption leaves the submodule for a rerun.
Guidance files are replaced only when their entire first line is the generated
marker. The owner options are `init`'s.
See [Someone else's repository](../your-project/someone-elses-repository.md).

### `run`

```text
devcapsule project run [--ide IDE] [--with CAPABILITY]... [--use CAPABILITY=COMPONENT]... [--memory SIZE] [--cpus N] [--env NAME[=VALUE]]...
                       [--trust CHANNEL]... [--authorize NAME VALUE]... [--set NAME VALUE]... [--save]
                       [--name NAME] [--no-update-check] [--no-recursive-e2e] [--print-command] [--force] [-- DOCKER-RUN-OPTIONS...]
```

Flags for IDE, capabilities, providers, memory, CPUs, environment variables,
and host access apply to one launch unless you add `--save`. `--save` persists
those choices to the checkout record once review and plan validation succeed.
`--trust CHANNEL` records channel trust in this home without `--save`, provided
no required launch answer remains missing. `--set` on `run` accepts `memory`
(including a declared memory alias) and `cpus`; use `config set` for other
project-declared values.

`--ide IDE --force` launches an alternate IDE for one session when the project
requires a specific IDE. The launcher warns which required IDE is set aside,
records the departure in the launch plan, and leaves the manifest, shared lock,
and saved checkout IDE untouched. Plain `run` enforces the project requirement
again on the next launch. Consent, artifact verification, and dependency checks
still apply. `--force` is refused without `--ide`, with `--save`, when the
project requires no IDE, or when `--ide` already matches the required IDE, and
a forced session does not record a known-good configuration. See
[Capabilities and components](../configuration/capabilities.md#a-required-ide).

`--name` overrides the container name for one launch. `--no-update-check` skips
the daily channel check while keeping cached critical notices active.
`--no-recursive-e2e` disables recursive-validation readiness when running
DevCapsule on itself. Arguments after `--` pass straight to `docker run`,
except flags the launcher owns (`--network`, `--memory`, `--cpus`,
`--shm-size`, and managed mounts); conflicts fail with the DevCapsule flag or
command to use instead.

Without an interactive terminal, any unanswered required question stops launch
with exit status `3` and prints the flag or command that settles each item.
Unanswered host-access recommendations fall back to secure defaults for a plain
launch, whereas `config check` exits `3` until they are answered.

`--print-command` stops before starting a container and never saves checkout
answers, though it can still download components, build images, and populate
caches. Printed secret and environment values are redacted. Use `config show`
or `config check` when you want pure offline inspection.

## `devcapsule project config`

Read-only inspection (`--json` supported on all six):

| Command | Intent |
|---|---|
| `show` | Show every effective choice for the next launch, where it came from, and the command for any pending item. |
| `check [--manifest FILE --lock FILE]` | Validate configuration without writing or launching; exits `3` on the host when decisions are pending. With `--manifest` and `--lock`, checks only that candidate pair. |
| `env list` | List configured checkout environment variable names and sources without revealing values. |
| `docker-args list` | List saved `docker run` arguments with inline environment values masked. |
| `trust list` | List channels referenced by this checkout's lock alongside channels accepted in this home. |
| `console list` | List pending web-console configuration requests awaiting host confirmation. |

Checkout choices (stored outside the repository):

| Command | Intent |
|---|---|
| `ide [--unverified] IDE` | Set this checkout's IDE (`python-ide`, `frontend-ide`, `vscode-ide`, `java-ide`, `eclipse-ide`, `dotnet-ide`, or a component name such as `codium` or `vscode`). |
| `add [--unverified] CAPABILITY` | Add a personal capability not declared by the project. |
| `omit [--unverified] CAPABILITY` | Leave out an offered project capability or remove a personal addition. |
| `restore [--unverified] CAPABILITY` | Restore a previously omitted offered capability. |
| `use [--unverified] CAPABILITY COMPONENT\|default` | Pick a provider when several exist (such as `codium` or `vscode` for `frontend-ide`), or return to the project/catalog default. |
| `set NAME VALUE\|default` | Set `memory` (`6GiB`, `6g`), `cpus` (`4`), or a project-declared value; `default` clears your override. |
| `authorize NAME VALUE [JUSTIFICATION]` | Grant host access or per-checkout software consent; `--all-recommended` walks through project recommendations interactively. |
| `deny NAME` | Record an explicit host-access denial for this checkout. |
| `forget NAME` | Clear your recorded answer so the default applies or a recommendation asks again. |
| `approve [NAME...\|--all]` | List pending per-checkout software updates, or approve named updates (or `--all`). |
| `env set NAME [VALUE] [--from-host]` | Save a private variable value, prompt with hidden input when `VALUE` is omitted, or pass a host variable through at launch. |
| `env unset NAME` | Delete a saved or pass-through checkout environment entry. |
| `docker-args set -- OPTIONS...` | Replace this checkout's saved `docker run` options, including entries saved with `config env set`. |
| `docker-args clear` | Clear all saved `docker run` options, including entries saved with `config env set`. |
| `bind NAME PROVIDER:VALUE`, `unbind NAME` | Bind a declared state slot to a host directory or a secret input to a host variable; `unbind` removes that binding. |
| `console apply\|discard ID` | Apply a queued web-console request on the host, or discard it. |

Shared project contract (for repository owners; writes schema 2):

| Command | Intent |
|---|---|
| `require 'CAPABILITY[>=VERSION]'... [--because REASON]` | Require capabilities on every checkout, with an optional minimum version. |
| `require env NAME... [--because REASON]` | Declare required application environment variables; prompted hidden on first launch and stored per checkout. |
| `offer CAPABILITY... [--because REASON]`, `offer env NAME... [--because REASON]` | Offer optional capabilities or environment inputs that a checkout may omit or leave unset. |
| `drop [env] NAME...` | Remove a capability or environment requirement or offer. |
| `recommend CAPABILITY COMPONENT\|none` | Recommend a component provider (such as `vscode` or `codium` for `frontend-ide`), or clear it with `none`. |
| `recommend ide\|memory\|cpus VALUE [--because REASON]` | Set an ordinary project default that applies unless a checkout overrides it, or clear with `none`. |
| `recommend network\|docker-daemon\|development-sudo\|host-browser VALUE --because REASON` | Recommend wider host access with a reason so each developer is asked; `none` removes it. |

Every shared-contract command accepts `--preview` to validate and print the
resulting change without writing files. Capability changes and provider
recommendations update the manifest and every platform lock together. Capability
commands accept `--unverified`; `recommend` does not. Environment declarations
and non-provider recommendations update only `.devcapsule/devcapsule.toml`.

See [Vendor software and trust](../configuration/software-approvals.md) for
home trust vs. per-checkout consent, and
[Project versus personal](../configuration/project-versus-personal.md#from-the-console)
for confirming web-console requests.

## Other project commands

Each command below follows `devcapsule project`:

| Command | Intent |
|---|---|
| `info [--json]` | Inspect software versions, container environment, and persistent storage paths; see [project info fields](project-info.md). |
| `diagnose [--session ID] [--export [PATH]] [--include-ide-logs] [--json]` | Capture a bounded session health snapshot or mode-`0600` sanitized `.tar.gz` bundle; see [Diagnostics and logs](../troubleshooting/diagnostics-and-logs.md). |
| `list` | List checkout records registered in this home. |
| `checkout register NAME` | Name an unregistered checkout (refuses to rename an already registered checkout). |
| `checkout notifications list\|post\|read\|dismiss` | Read, post, mark read, or dismiss checkout notifications used by the capsule web console. |
| `checkout decisions from-table\|check\|hand-off` | Build a web-console decision file from a Markdown table, validate it, or print chat handoff text and the console link. |
| `state adopt --from SOURCE SLOT` | Use an existing host directory directly for a declared checkout state slot; no files are copied. |
| `versions show [--json]` | Show the effective version set, its origin, validation evidence, and local launch history. |
| `versions history` | List exact version sets that have completed an ordinary launch on this checkout. |
| `versions check` | Query upstream distribution channels for newer releases or notices without changing selections. |
| `versions preview COMPONENT VERSION` | Resolve a candidate version and checksums without downloading executables or activating it. |
| `versions select PREVIEW [--unvalidated] [--authorize NAME VALUE]` | Materialize a previewed version set and select it for the next launch. |
| `versions follow-project [--apply] [--authorize NAME VALUE]` | Diff against the shared project lock, or return this checkout to the project lock with `--apply`. |
| `versions rollback [IDENTITY] [--reacquire] [--authorize NAME VALUE]` | Restore the previous known-good version set (or a named `history` identity). |
| `versions propose OUTPUT` | Write a reviewable Git patch updating the shared lock from a proven local version set. |
| `versions defer`, `versions dismiss` | Quiet checked update candidates for seven days, or until upstream candidates change. |
| `recursive-e2e preflight\|run\|launch-successor\|inspect-successor` | Preflight and run DevCapsule's recursive self-hosting validation suite. |

See [Component upgrades](../updates/component-upgrades.md) for version-set workflows.

## Retired spellings

Retired commands such as `config list`, `config resolve`, `config need`,
`config agent add`, and `config tool omit` exit with status `2`, write nothing,
and print their replacements. Retired `init`/`run` flags do the same.
`project config default` and mutating `project config trust` subcommands are
absent; use `devcapsule home default` and `devcapsule home trust` instead.
`project config capabilities --recover` remains available solely to repair an
interrupted manifest/lock write.

<a id="home-and-development-commands"></a>

## Launcher, image and workflow commands

Each command below follows `devcapsule`:

| Command | Intent |
|---|---|
| `version [--json]` | Print the launcher version, package version, and source revision provenance. |
| `images build --type {base,environment} ...` | Build a curated base image, for the capsule platform `--platform` names, or materialize a project environment image. |
| `images list [--include-legacy]` | List DevCapsule base and environment images in the local Docker store. |
| `bootstrap [--refresh-workflow-definition] project` | Install or refresh DevCapsule workflow files and initialize project status records. |
| `workflow brief` | Print the active workstream summary, live claims, waiting mail, sync distance, and validation commands. |
| `workflow status` | Show published state across all open workstreams on the coordination branch. |
| `workflow claim [--hours N \| --release] [SLICE]` | Publish or release an advisory work claim on the coordination branch. |
| `workflow publish` | Push the current workstream's status and disposition records to the coordination branch. |
| `workflow mail check\|send\|take` | Check waiting mail, deliver an intake item, or take waiting mail into the current workstream's `intake/`. |
| `runtime PLAN.json [-- COMMAND ...]` | Execute a capsule runtime plan inside the container (internal entry point). |
| `pycharm build`, `pycharm check-runtime` | Legacy standalone PyCharm image builder and runtime check. |
