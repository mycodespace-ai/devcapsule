---
description: Inspect software, storage, and the next launch's choices without changing configuration.
weight: 3
updated: 2026-10-30
---
# Inspect a checkout

`project info` reports software, environment, and storage, while `project
config show` reports configuration choices and pending decisions. Neither
command writes files, downloads components, or contacts Docker.

## Software and storage

```sh
devcapsule project info
devcapsule project info --json
```

On the host, `info` describes the next launch. Inside a capsule, it describes
the running software and shows a separate next-launch selection when the lock on
disk differs. Both text and JSON (`schema-version: 1`) list component versions,
allowlisted runtime variables such as `HOME` and `PATH`, persistent paths, and
temporary storage. They omit application secrets. Use `config show` for
project-declared environment inputs and pending values; see
[Project info](../reference/project-info.md) for the full field reference.

Project commands discover the project from its root directory or any
descendant, and inside a capsule inspection commands also fall back to the
capsule's mounted project from `/opt`. To target a directory explicitly:

```sh
devcapsule project --path /path/to/project info
```

## Choices and pending decisions

```sh
devcapsule project config show
devcapsule project config show --json
devcapsule project config check
```

`show` lists effective choices, providers, sources, and pending decisions,
naming the exact command that settles each pending row. An unregistered
checkout is inspected without creating a checkout record on disk.

On the host, `check` validates the project contract and exits with status `3`
when checkout decisions remain pending (printing the JSON document first when
`--json` is passed). Passing `--manifest` or `--lock` validates only that
candidate contract (`context: "candidate contract"` in `--json`) without
checking checkout decisions. Inside a capsule, `check` validates the contract
on disk and notes that current host decisions require the host launcher.

Inside a capsule with a console channel, `show` renders the configuration
listing captured at launch alongside any web-console requests submitted since
launch (which apply to the next launch rather than the running container) and
prints the host command for changes.

`show --json` emits `schema-version: 2` (checkout identity and `rows`, plus
`console-requests` inside console-capable capsules), or `schema-version: 1`
inside capsules launched without a captured listing channel. Always check
`schema-version` before reading fields; see [Project versus
personal](project-versus-personal.md#from-the-console) for console request
rules.

`devcapsule project versions show` (and `--json`, `schema-version: 1`) reports
the effective component version set and its source; see [Component
upgrades](../updates/component-upgrades.md).
