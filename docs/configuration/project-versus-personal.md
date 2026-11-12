---
description: Which choices belong to the project in Git, which stay on your checkout, which belong to your configuration home, and how changes apply at launch.
weight: 2
updated: 2026-10-30
---
# Project versus personal

The project, your checkout, and your configuration home each hold a distinct
part of the launch configuration. [Configuration](index.md) introduces all
three records.

## The project, in Git

The **manifest**, `.devcapsule/devcapsule.toml`, declares required and offered
capabilities, environment inputs, and recommendations. Requirements can carry a
minimum version such as `java>=21`, and resolution recommendations name a
preferred component provider. The **platform lock**,
`.devcapsule/devcapsule.<platform>.lock`, pins the base image and resolved
component versions. Commit both files together; [Capabilities and
components](capabilities.md) covers `require`, `offer`, `drop`, and
`recommend`.

## Your checkout, on your computer

The **checkout record** holds your IDE choice, added and omitted capabilities,
provider choices, local component pins, host-access answers, values, and
directory or secret bindings. None of these travel in Git or affect another
checkout unless you explicitly share a directory.

- `config ide` chooses your IDE by capability (`python-ide`, `frontend-ide`,
  `vscode-ide`, `java-ide`, `eclipse-ide`, `dotnet-ide`) or component name
  (`pycharm`, `codium`, `vscode`, `intellij`, `eclipse`, `rider`). Its
  component opens the project, owns the container's lifetime, and uses the
  display.
- `config add` adds a personal capability (such as a coding agent), `config
  omit` leaves out a project offer or removes your addition, `config restore`
  restores an omitted offer, and `config use` picks a provider when alternatives
  exist.
- A separate private file holds your saved `docker run` options, including
  environment variables. Managed per-checkout directories hold the capsule's home,
  IDE preferences, and agent sign-ins. Use `config bind` or `state adopt` (and
  `config unbind`) to point a declared slot at your own host directory; see
  [IDE preferences and plugins](ide-preferences.md) and
  [What persists](../sessions/what-persists.md).

Project recommendations supply defaults whenever you have no checkout choice.
`config show` reports where each active value came from; `config use CAPABILITY
default` clears a provider override, and `config set NAME default` clears a
value override. Host-access recommendations ask for your decision instead of
taking effect silently: `project run` shows the project's reason and the access
requested so you can allow it once, save an allowance or denial, or defer.
`config forget NAME` clears a saved host-access answer or software consent.

## Your configuration home

The home's settings apply to every project launched from it.
`home default memory 8GiB` and `home default cpus 4` set resource defaults.
A project recommendation or checkout value overrides those defaults.
The file is `settings.toml` in the [configuration home](home.md).
Set `DEVCAPSULE_CONFIG_HOME` to select a different home.

The same file's **trust table** holds accepted vendor channels. A coding-agent capability
uses the same acquisition rules as other capabilities. Its component owns
its terms, consent, sign-in and persistent directories.
[Vendor software and trust](software-approvals.md) explains channel acceptance.

<a id="when-the-project-changes"></a>

## Changes at the next launch

`devcapsule project run` derives a launch from all three records each time.
The launcher asks for missing required decisions, including an IDE, an
application input or software consent. Without a terminal, these decisions
stop launch with status 3 before answers are saved. The message names each
blocking decision and its command. Unanswered host-access recommendations
use secure defaults.

Inspect the next launch without downloading software or contacting Docker:

```sh
devcapsule project config show
devcapsule project config check
```

`show` prints effective choices, providers, sources and pending decisions.
`check` returns status 3 for pending decisions, including unanswered host
recommendations. A saved host answer remains in force when its recommendation
changes. The listing reports the difference.

A required capability must remain present and meet its minimum. The explicit
exception is [replacing a required IDE for one launch](capabilities.md#a-required-ide)
with `run --ide IDE --force`. A launcher upgrade keeps the lock and your saved choices.

## Saved Docker arguments

Save the extra Docker options you need once, from your checkout on the
launcher host:

```bash
devcapsule project config docker-args set -- \
  --gpus all \
  --volume "$HOME/.ssh/my_special_key:/home/devcapsule/.ssh/my_special_key:ro"
devcapsule project config docker-args list
devcapsule project run
```

`docker-args set` **replaces the complete saved list**. Quote each value as
you would in `docker run`; DevCapsule preserves the argument tokens and does
not evaluate shell syntax. Use absolute host and container mount paths. GPU
access still needs a suitable runtime and drivers on the host.

`project run` puts saved arguments after its own options and before
arguments you supply after `run --`. Docker decides how repeated options
combine. DevCapsule refuses options that it controls, including `--network`,
`--memory`, `--cpus` and `--shm-size`. It names an alternative when one exists.
Shared-memory size comes from the IDE's runtime template and has no user setting.
`docker-args clear` removes the whole list, including environment variables.
`docker-args list --json` reports the file's path and tokens, with recognized
environment values masked.

## Environment variables

```bash
devcapsule project config env set POSTGRES_PASSWORD
devcapsule project config env set POSTGRES_HOST db.example.org
devcapsule project config env set AWS_PROFILE --from-host
devcapsule project config env list
devcapsule project config env unset POSTGRES_PASSWORD
```

Without a value, `env set` prompts for it hidden, out of shell history, and
keeps it in the private list on your computer; `--from-host` passes your
shell's variable through at each launch instead, without storing its value.
Without a terminal, supply a value or use `--from-host`.
`env list` shows names and whether each value is saved or comes from the host.
At a terminal, `run` asks for a missing required value with a hidden prompt.
A missing variable bound with `--from-host` also needs an answer, even if the
project does not declare it. Without a terminal, either missing input stops
launch with status `3`. Set the host variable, save a literal value, or remove
an unwanted binding with `config env unset NAME`.
For one launch, use `run --env NAME=VALUE` or `run --env NAME`.
Add `--save` to record the assignment or host-variable binding.

These commands edit the same list as `docker-args set`.
Replacing or clearing that list also removes its environment entries.
Environment helpers refuse ambiguous option tokens, such as `--label --env`.
Replace the list with unambiguous arguments, with environment options first.
Use separate `--env NAME=VALUE` tokens. Short-option clusters such as
`-te NAME=value` are not recognized or masked by these helpers.

The private store lives under `docker-arguments/` in your configuration home
(`$XDG_CONFIG_HOME/devcapsule/docker-arguments/`, normally
`~/.config/devcapsule/docker-arguments/`, or
`$DEVCAPSULE_CONFIG_HOME/docker-arguments/` when `DEVCAPSULE_CONFIG_HOME` is
set), keyed by project and checkout, with owner-only permissions, outside Git
and outside anything mounted into a capsule. DevCapsule masks inline
environment values in launch narration, session logs, and printed commands;
Docker receives the originals, so processes with Docker inspection access can
still read them. Other options, such as labels, appear as supplied—keep
credentials out of them.

## From the console

The configuration page needs a console-capable base, recipe 11 or later,
and an attached launcher that supports configuration requests.
It shows the listing captured at launch, with its timestamp.
It also shows later requests and their results; these do not update the snapshot.
Inside the capsule, `devcapsule project config show` reports the same view.

The launcher validates console requests with the corresponding CLI command.
It can record IDE choices, values, literal environment assignments, denials,
and removed bindings. Automatic environment assignments must use exactly
`env set NAME VALUE`, with neither `NAME` nor `VALUE` starting with `-`.
Other forms need host confirmation.
It can also withdraw home trust or clear saved Docker arguments.
The console accepts `add`, `omit`, `restore` and `use` for capability choices.
The launcher applies valid requests to the next launch. Adding a vendor
capability leaves its consent decision for that launch.

The console also applies these restrictive authorization requests without host
confirmation. Use exactly the three tokens shown, replacing `VALUE`:

| Request | Allowed values |
|---|---|
| `authorize network VALUE` | `bridge`, `none` |
| `authorize docker-daemon VALUE` | `none` |
| `authorize development-sudo VALUE` | `false`, `none` |
| `authorize host-browser VALUE` | `false`, `none` |
| `authorize host-x11 VALUE` | `false`, `none` |

Authorization grants, trust acceptance, bindings, replacement Docker
arguments, forgotten answers and host-variable bindings need confirmation
on the host: a forgotten denial can restore home trust, and a host
binding exposes a variable. Inspect them with:

```bash
devcapsule project config console list
devcapsule project config console apply ID
devcapsule project config console discard ID
```

Replace `ID` with a listed request ID. Apply or discard each request as appropriate.
An interactive `run` also offers these choices. A noninteractive run keeps
unconfirmed requests pending and continues without applying them.
The console cannot edit the shared manifest or set home resource defaults.
No request reconfigures the running capsule.
