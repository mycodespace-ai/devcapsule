---
status: closed
severity: minor
target: 0.3.0
owner: maintenance
opened: 2026-10-05
requirements: [R-PRODUCT-001]
---

# `project run --authorize network host` is refused on a project that does not recommend host networking

## Symptom

On a project whose manifest carries no `[host.network.mode.recommended]`
table, the documented run-once launch

```text
devcapsule project run --authorize network host
```

exits with

```text
Authorization 'network' cannot be answered run-once; run-once authorizations: docker-daemon, development-sudo, host-browser, host-x11.
```

The same command works on this repository, whose manifest recommends host
networking. The run help also refuses a raw `--network` option.

## Environment

Reported by component-catalog on 2026-10-04 from the IDE graphical smoke,
run `20261004T002133Z-8f8069`, before any container launch, on source
`ada153c` (main baseline `17532fd`); the rejection is retained in that
run's `dist/e2e-evidence/ide-smoke/.../codium/launcher.log`. The smoke
initializes a fresh disposable project, which is what makes the
recommendation absent. Reproduced by reading the source on `main` at
`242e13e`, 2026-10-05.

## Cause

`_RUN_ONCE_AUTHORIZATIONS` in `commands/project.py` does include
`network`. The refusal comes one step earlier: `_run_once_answers` looks
the name up in `authorization_declarations(manifest, lock)`, and the
`network` node is built only from `CURATED_HOST_RECOMMENDATIONS`, that is,
only when the manifest recommends a host network mode.
`WORKSTATION_CAPABILITY_DEFAULTS`, the nodes that exist on every project,
deliberately omits it; the comment there says the run-once form of host
networking was the raw Docker passthrough and the persistent relaxation
"remains a project-recommended decision". That rule predates the run-once
`--authorize` family, which replaced the raw passthrough, and it was never
revisited. The error message then lists the nodes that happen to exist,
which is how a correct command gets reported as an unsupported one.

## Owner ruling, 2026-10-05

Component-catalog's handoff asked maintenance to reconcile the documented
command with the CLI. The owner ruled: `project run --authorize network
host` is supported on every project, and a project where it does not have
the intended effect is a bug, fixed for 0.3.0. The alternative, amending
`WORKFLOW-LOCAL.md` to say the command presupposes this repository's
recommendation, is rejected: the local workflow text stands as written.

## Expected

`network` is a host-capability node on every project, like `docker-daemon`,
`development-sudo` and `host-browser`: denial (`bridge`) is the default, a
developer may allow it once with `project run --authorize network host`,
or for the checkout with `project authorize`, whether or not the project
recommends it. A recommendation attaches the project's justification and
rebinds the answer to it, exactly as for the other three. The error for a
genuinely unknown or non-run-once name keeps listing the run-once nodes,
which now always include `network`.

## Verification target

A unit test on a manifest with no network recommendation: `project run
--authorize network host` is accepted, echoed as a run-once authorization,
and reaches the launch with host networking; `project authorize network
host` persists it; the deny value stays `bridge`. The IDE smoke's
`project init --authorize network host ...` keeps working. The existing
tests that pin the authorization catalog are updated for the new universal
node.

## Close criteria

The unit test passes on a 0.3.0 candidate, and component-catalog's IDE
smoke launches a fresh project with the documented run-once command.
Reopen if a fresh project refuses the command again, or if the run help
again advertises a raw `--network` option.

## Fix, 2026-10-22

On `ws-maintenance/0.3.0-network-node`, a slice of the 0.3.0 cycle into
`release-0.3.0`. `network` joins `WORKSTATION_CAPABILITY_DEFAULTS` in
`devcapsule/configuration/authorization.py`, the table of host
capabilities that exist as nodes on every project, with `host` as its
supported value and `bridge` as its deny value, which
`AUTHORIZATION_DENY_VALUES` already held. The table's comment, which had
kept networking out while its run-once form was the raw `--network`
passthrough, now says why it is in. A recommendation still takes precedence
and attaches the project's justification, as for the other three; the
run-once list, the review overlay and the launch already handled the node.
A unit test on a manifest with no network recommendation proves the
run-once command accepted and echoed and the launch planned with host
networking, the unanswered launch on bridge, the persistent form written,
a value outside the grammar refused with the deny value named, and the
listing; the run-once refusal test now expects `network` among the names
on a fresh project. The documentation rows that said the node is declared
only by projects that need it say instead that it is on every project.
Verification on a candidate: the unit test and component-catalog's IDE
smoke launching a fresh project with the documented command.

## Downloaded RC9 verification — 2026-10-31

The universal-network-node unit regression passes against the packaged RC9 wheel. A fresh Codium project with no network recommendation and saved network access denied launches with --authorize network host; independent inspection sees host networking and an IDE window. The owned container and project records are removed afterward.

[Final audit evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#final-promotion-audit--2026-10-31).
Verification is complete; the release acceptance/closure checkpoint remains
pending the explicit final scope and provider dispositions.

## Closed — 2026-10-31

Closed on the RC9 verification above and the owner's final acceptance of
that exact candidate on 2026-10-31. [Acceptance record](../../releases/v0.3.0.json).
The fix is in RC9 source 475427da and main 4b59b10d; the documented test
limits are retained. This supersedes the pending-closure sentence above.
