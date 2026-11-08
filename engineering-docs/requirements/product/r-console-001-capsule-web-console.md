---
id: R-CONSOLE-001
title: Every Capsule Serves A Web Console
type: requirement
kind: concrete-requirement
status: accepted
priority: wanted
source_of_truth: repo
verification: [tests, manual]
external_refs: []
---

# R-CONSOLE-001: Every Capsule Serves A Web Console

## Statement

Owner direction, 2026-10-09. Every capsule serves a read-only web console on a
loopback port of the host, gated by the run's token, whenever the runtime
runs, with or without a display. The console shows, as HTML, what the
`devcapsule` commands report about the capsule and its project: the
configuration, the versions, the project information, and live process and
resource data from inside the capsule. A user without a graphical host
reaches it through an SSH port forward.

### Placement

The console is part of the base image for every adopter. It is not a
component and not a selectable capability. It is a separate process from the
runtime, started and supervised by the runtime, built from a static web
structure and a FastAPI application for dynamic data. Under
[D-0017](../../decisions/product/d-0017-launcher-delivers-web-console-package.md),
the base image supplies the hash-pinned virtual environment and baseline
installation at `/opt/devcapsule-webconsole`, while a built launcher delivers
its matching `devcapsule_webconsole` package read-only at
`/opt/devcapsule/webconsole` during environment materialization so CLI and
console updates ship together without a base rebuild unless third-party
dependencies change. It reads the mounted
project and the runtime's read-only records, and calls the runtime CLI's
`--json` outputs as its API. It does not import the runtime's internals.

### Boundaries

The console binds inside the capsule only and is published to one host
loopback port, like the contained display. Every request carries the run
token or is refused. Paths resolve inside the project mount and the mounted
records only. The console changes nothing: it has no write operation on
configuration, records or the host.

### Later scope

Rendering of the repository's markdown records, the workflow state, diagrams,
and the decision pages the workflow's human-input rule allows are later
slices of the same requirement. An optional monitoring component, such as
Glances, may be linked from the console; it is not the console.

## Verification

- Unit tests: routing, token refusal, path-traversal refusal.
- Smoke: the console answers on its port in a fresh capsule, with and without
  a display; the home page and the configuration page render.
- Manual: the owner opens the console from `project run` and from an SSH
  port forward.

## Acceptance

Accepted by the `capsule-webconsole` workstream on 2026-10-09 in its first
integration, the JSON contract slice, as the work order asked. The statement
was read against the mainline evidence the work order names and found
consistent with it; the two amendments of the same day, DOT diagrams and
materialized views, extend the later scope without changing the statement.

## Related

- Workstream: `capsule-webconsole`, started 2026-10-09.
- Decision: [D-0017](../../decisions/product/d-0017-launcher-delivers-web-console-package.md),
  launcher delivery of `devcapsule_webconsole` on the base interpreter and
  scoping of the self-hosting checkout override.
- Contained display transport: the token and port model the console mirrors.
- `WORKFLOW.md` topic 9.5, decisions presented as structured artifacts.
