---
id: D-0016
title: A Required IDE Stays Required; One Launch May Depart From It Explicitly
status: accepted
date-proposed: 2026-10-28
date-decided: 2026-10-28
decided-by: product owner
requirements: [R-CONFIG-001]
supersedes:
superseded-by:
---

# D-0016: A Required IDE Stays Required; One Launch May Depart From It Explicitly

Decided by the product owner on 2026-10-28, during the 0.3.0rc8 IDE
investigation, and ordered as the
[work order of the same day](../../work-orders/2026-10-28-explicit-ide-requirement-override.md).
This record keeps the choice and its reasoning; it was written by the
implementing pair on 2026-10-29, after the decision, and records the act.

## Context

R-CONFIG-001 distinguishes mandatory needs from optional enhancements: an
unmet mandatory need refuses the launch. A project may list an IDE among its
required capabilities, and the schema-2 manifest keeps such a requirement
mandatory, while a schema-1 `need` that named an IDE is read as a
recommendation. A developer who wanted another IDE on a project requiring
PyCharm met, in rc8, a refusal that did not say how to proceed, or an internal
error about two interactive surfaces, depending on the manifest's form.

IDE and agent selections belong to each developer under R-CONFIG-001's
ownership rule, yet an IDE can be a legitimate project requirement: a project
that develops a plugin for that IDE is one example. The two pull against each
other only when a developer wants, for a while, an IDE the project does not
require.

## Options Considered

### Option A: Forbid IDE requirements

Read every IDE in a project's requirements as a recommendation, as the
schema-1 upgrade already does, and migrate existing requirements.

Cost: the plugin project loses the ability to say what it needs; a
collaborator's checkout can launch an IDE on which the project's own work
cannot be done, and nothing says so. A migration rewrites shared declarations
to avoid a conflict the declaration meant to express.

### Option B: An explicit per-launch override

Keep the requirement. Let the developer name a departure for one launch,
`project run --ide IDE --force`, warned and recorded, never saved.

Cost: a second path through plan derivation, which must stay coherent: one
surface, unrelated capabilities preserved, real dependencies honoured. A
flag whose name invites misuse, which the implementation limits to this one
policy check.

### Option C: A saved per-checkout waiver

Let `config ide` record another IDE on a required-IDE project, with the
waiver saved in the checkout record.

Cost: a persistent exception that every later launch applies silently; a
record that claims the project is satisfied while it is not; the interaction
with `--save` and the shared lock undefined.

## Decision

Option B. An IDE can be required, and existing requirements are not migrated
into recommendations. `--force` is the public escape hatch for the IDE policy
conflict, and the first implementation covers this case only; the mechanism
names each bypass by a policy identity so it can extend to other policy checks
deliberately, never as a general bypass of command failures.

Force means the developer accepts a named departure from the project
contract for this launch. It does not mean the requirement was satisfied. The
launcher warns which required IDE is bypassed and which IDE runs, and the
launch's recorded configuration and diagnostics show the departure wherever
they describe contract satisfaction. The override is transient: the manifest,
the lock and the checkout's saved IDE are unchanged, no exception is saved,
and the next plain launch returns to ordinary selection. Force grants no host
access, accepts no vendor terms, approves no software, skips no artifact
integrity check and invents no component. The combination with `--save` is
not defined and is refused until the owner decides it.

## Rationale

The requirement is information the project owner has and the collaborator
needs; removing it to avoid a conflict destroys that information. The
developer's ownership of the IDE choice is real too, and the cost of honouring
it for one launch is small once the departure is explicit, named and
recorded. A saved waiver would make the departure invisible to the next
launch and to the project's records, which is the state the requirement
exists to prevent. Keeping force narrow, one policy identity, one command,
keeps it from becoming the way around every refusal.

## Consequences

- `project run` gains `--force`, meaningful only beside `--ide` on a
  project that requires another IDE; the refusal without it names the flag.
- Plan derivation takes the launch's departures as a named value and
  derives from the policy with the departed requirement set aside; the
  usable lock refuses a remaining dependency on the replaced IDE by name.
- The resolution and the launch listing carry a `departures` record; a
  forced launch is not recorded as known-good and proves no version set.
- `--save` with `--force` is refused. The question was raised by the
  order's author, not by the owner; on 2026-10-29 the owner ruled the
  refusal final: the developer decides between saving an allowed IDE and
  departing for one launch, and the launcher does not help her save a
  checkout that can no longer launch plainly.
- The `config show` listing of the checkout is unchanged: departures are
  the launch's, not the checkout's.

## Reopen If

Another policy check needs the same explicit escape, or a project with a
required IDE turns out to need a persistent per-checkout exception that a
transient override cannot express.
