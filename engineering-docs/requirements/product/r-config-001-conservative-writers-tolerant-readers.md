---
id: R-CONFIG-001
title: Conservative Configuration Writers And Tolerant Readers
type: requirement
kind: concrete-requirement
status: accepted
priority: wanted
source_of_truth: repo
verification: [tests, manual]
external_refs: []
---

# R-CONFIG-001: Conservative Configuration Writers And Tolerant Readers

## Statement

Owner direction, 2026-10-05, for 0.3 planning: be liberal in what DevCapsule
accepts and conservative in what it produces. A contribution to a shared
repository must not prevent a collaborator with a less capable local launcher
from working merely because an optional enhancement is unavailable to them.
This requirement applies to adopter projects as well as DevCapsule itself.

### Configuration is written through commands

DevCapsule commands provide the supported operations for writing project
configuration and its derived documents. They maintain consistency across the
manifest, locks, checkout configuration and resolution. Missing operations
must be implemented as commands, not worked around by agent-authored file edits.
Commands validate the starting configuration and proposed change before promoting
it, and expose a validation path that does not require applying the change first.

Writers preserve unrelated choices and use compatible representations rather
than introducing a newer requirement incidentally. Unknown optional declarations
must survive a supported round trip; when a writer cannot safely preserve them,
it explains the limitation and refuses that mutation without destroying the
existing documents or unnecessarily preventing their usable runtime subset.
Compatibility validation must include the consumer that will use the output,
not just the producer's newer implementation.

### Mandatory needs and optional enhancements are distinct

The project explicitly distinguishes capabilities essential to its usable
baseline from optional enhancements. The consumer resolves the usable subset
against its own implementation and the checkout's environment.

An unsupported or unavailable optional capability produces a clear warning
naming the omission, why it occurred and the functionality that will be missing.
If all mandatory needs can still be met, ordinary launch continues with that
reduced environment. A missing mandatory capability receives an actionable
explanation and prevents a launch falsely claiming to satisfy the project.
An optional dependency of a mandatory capability cannot be silently omitted
when doing so would break that mandatory capability.

Graceful degradation is local runtime behavior. It does not delete declarations
from the shared manifest, rewrite its lock to the local launcher's subset, or
silently reduce the project's mandatory needs. A more capable collaborator can
still use the enhancement from the same shared project. Tolerant reading does
not authorize ignoring constraints needed for integrity or host-access boundaries.

### Wrapped sources are an optional table

A wrapper project declares the foreign repositories it holds as submodules
under `[sources."<path>"]`, one entry per submodule path, with `upstream`
(the upstream URL when the origin is the developer's fork) and a toolchain
key named after the capability it refines (`java = "17"`, the Java line the
source builds with). The declaration adds no capability by itself; the
capability stays in `[capabilities]`. A launcher without this field reads the
table as an unknown root table, carries it through its own writes, and runs
the capsule without the toolchain selection; a launcher with it validates the
entries and reports them. See R-WRAP-001.

### One explicit launch exception: the required IDE

Owner decision, 2026-10-28, [D-0016](../../decisions/product/d-0016-explicit-launch-departure-from-a-required-ide.md):
a project may require an IDE, and a developer may launch another IDE for one
session with `devcapsule project run --ide IDE --force`. This is the only
exception to the mandatory-constraint rule above, and it is distinct from
ordinary enforcement:

- It is explicit. The launcher refuses the conflicting IDE without `--force`
  and names the override in its diagnostic. `--force` never selects a
  replacement itself: without `--ide`, with the required IDE, or on a project
  that requires no IDE it is refused.
- It is a named departure, not satisfaction. The launcher warns which required
  IDE it sets aside and which IDE runs. The launch's plan and its listing
  record the departure, and no record of that launch claims the project was
  satisfied: it is not recorded as a known-good configuration or a proven
  version set.
- It is one coherent plan. The plan has one interactive surface, the requested
  IDE; the replaced IDE's closure is omitted only as far as the remaining
  capabilities do not need it. A remaining real dependency on the replaced
  IDE is explained and refuses the launch.
- It is transient. The shared manifest, the lock and the checkout's saved IDE
  are unchanged; `--force` cannot be combined with `--save`, and the next plain
  launch returns to ordinary selection, also after a failed or interrupted
  forced launch.
- It waives nothing else. The requested IDE's consent, channel trust, artifact
  integrity and dependency checks still apply; host access is not granted.

Every other unmet mandatory constraint keeps its ordinary refusal.

### Project scope and developer ownership

Owner refinement, 2026-10-06: the project describes the ideal developer
experience. Do not introduce capability profiles per task or workstream.
Required/optional describes necessity; project/developer describes ownership.
The required Python SDK and its major version are a shared contract. Playwright
is an optional project enhancement. IDE and coding-agent/provider selections
belong to each developer, with local exact-version pins; they must not impose
the original author's preferred agents on collaborators. Local choices cannot
waive mandatory project constraints; the explicit per-launch IDE departure
above is a named exception, not a waiver. Installing a tool grants no host access.

### Self-hosting requires a deliberate transition

DevCapsule developed inside DevCapsule creates a circular dependency. This is
an allowed, managed exception. Before this project's configuration changes,
validate it using at least the running instance's identifiable `devcapsule0`;
validate the candidate and resulting configuration as well. Testing only with
the new code is insufficient. Preserve a known working tool and an independent
host-side restart/recovery path when intentionally adopting a development build.
An inspection listing does not count as complete configuration validation.

## Acceptance scenarios

- A newer contributor adds an optional capability through a DevCapsule command.
  A less capable supported launcher reads the updated project, warns about the
  omitted capability and launches the mandatory environment. Shared documents
  are unchanged by that degraded launch; a capable launcher provides the extra.
- The equivalent addition marked mandatory cannot be satisfied silently. The
  diagnostic names what is missing and an actionable path forward.
- Dependency handling never reports mandatory functionality satisfied after
  removing something it requires.
- A command preserves unknown optional declarations when modifying an unrelated
  supported value, or safely refuses that mutation while retaining the prior
  documents and usable launch path.
- Invalid or incompatible proposed changes are caught before replacing working
  configuration. Failed/interrupted changes retain a recoverable consistent state.
- The self-hosting path validates with the recorded `devcapsule0` baseline as
  well as the candidate. Evidence identifies both executables and distinguishes
  parsing, resolution/runtime planning and an actual next-session launch.
- A project requires PyCharm and a checkout saved it. `run --ide codium`
  is refused before materialization, naming `--ide codium --force`. With
  `--force`, by component or by capability name, the plan's one surface is
  Codium, the unrelated mandatory tools remain, the plan records the
  departure and the launcher warns. The manifest, the lock and the saved IDE
  are unchanged, and the next plain launch selects PyCharm, also after a
  failed or interrupted forced launch. Consent, artifact validation and a real
  dependency on PyCharm still refuse the forced launch.

## Implementation and rollout

The implementation uses project `required`, `optional` and `sdk-major`
declarations, with developer selections in the local checkout record. The
[configuration guide](../../../docs/configuration/capabilities.md) describes
`init --required`, `config capabilities`, read-only `config check`, preview,
omission and recovery. Legacy `need` inputs remain readable. Capability policy
is project-scoped; no task/workstream profile is introduced.

Existing shipped binaries cannot retroactively learn this contract. Adoption
requires a reader containing the implementation; release sequencing remains
project-management's responsibility. Inspection on 2026-10-05 established that
the running `devcapsule0` lacked read-only candidate checking and classification
commands. The implementation does not replace that executable or migrate this
self-hosting checkout's manifest/lock. Such migration still requires the
baseline/candidate validation and independent restart path above.

## Related

- [R-COMPAT-001](../devcapsule/r-compat-001-client-upgrades-require-no-user-action.md)
  protects old project inputs when the client upgrades. This requirement also
  covers newer shared-project contributions reaching a less capable client.
- [R-UPGRADE-001](r-upgrade-001-component-version-sets.md) governs local selections,
  consent and recovery; the new contract must compose with those decisions.
- [Playwright regression](../../bugs/devcapsule/2026-10-04-unreleased-playwright-breaks-checkout-launch.md)
  supplied the concrete failure; removing the component was only a containment fix.
- [Local workflow](../../../WORKFLOW-LOCAL.md#keep-the-development-checkout-launchable)
  applies the owner's command-only and baseline-validation rules immediately.
- [D-0016](../../decisions/product/d-0016-explicit-launch-departure-from-a-required-ide.md)
  records the owner's choice of an explicit launch exception over forbidding
  IDE requirements; the
  [work order of 2026-10-28](../../work-orders/2026-10-28-explicit-ide-requirement-override.md)
  defines the delivery; `maintenance` implemented it for 0.3.0.
