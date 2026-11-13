---
status: confirmed
severity: minor
target: none
owner: maintenance
opened: 2026-10-18
requirements: [R-COMPAT-001, R-CONFIG-001]
---

# No test proves that projects initialized by an earlier release keep launching with a new one

## Symptom

The unit suite had one test that read this repository's own lock,
`test_resolution_reconstitutes_the_dogfood_environment`, and it asserted the
wrong thing: that the committed lock equals the matrix's newest selection.
That is repository housekeeping, not a behaviour of the code, and since the
2026-10-05 rule only a launcher command on the host may do that housekeeping.
The test went red on `main` and on `release-0.3.0` on 2026-10-18 when the
agent pins advanced (PR #224, PR #228), blocked the candidate workflow, and
told nobody anything about whether an older project still launches. Deleted
on 2026-10-18 and replaced by
`test_repository_lock_is_launchable_by_this_launcher`, which reads the
committed lock the way `project run` does and asserts it parses into a
launchable environment.

That replacement proves one lock, ours, written one matrix generation ago.
The contract the owner wants enforced is wider: every project that an
earlier release initialized, its manifest, its platform lock and its
checkout record, must keep launching with a new release. *Keep The
Development Checkout Launchable* in `WORKFLOW-LOCAL.md` and R-CONFIG-001
state the rule, be liberal in what we accept; nothing exercises it across
releases. The 2026-09-24 incident, released launchers rejecting the
repository manifest, and the 2026-10-04 incident, an unreleased Playwright
entry breaking the checkout launch, were both of this class and were both
found by people.

## Expected behaviour

A test, in the unit suite or the integration gate, that holds a
configuration captured from each released client still in support, today
v0.2.14 and v0.2.15: the manifest, the platform lock and the checkout record
a `project init` of that release wrote for a representative need. For each
captured configuration, the development code must: read the manifest and
validate it; parse the lock into a launchable environment, every artifact
declaration validated and every runtime template found; read the checkout
record and the authorizations; and resolve the manifest's need against the
development matrix without `--unverified`. A capture is added when a final
release ships and retired when the version leaves support.

## Close criteria

- The captured configurations live under `tests/resources/` with the
  release and the commit they came from in a README.
- The test fails when a reader, a vocabulary or a validator stops accepting
  one of them, naming the release and the file.
- The release runbook names the capture as a step after the final tag.

## Disposition

Opened 2026-10-18 by `maintenance` at the owner's direction, during the
0.3.0 cycle. No target: it is validation work for the next planning, not a
0.3.0 gate.

## Progress, 2026-11-12

On `ws-maintenance/launch-phases`, pull request #29, not merged.

`test_repository_lock_is_launchable_by_this_launcher` is deleted. It read
the lock in the working tree, and since 0.3 a project whose IDE is
recommended has a shared lock without one, which the launch's reader
rightly refuses alone; the test failed wherever a 0.3 launcher had
rewritten this repository's configuration. Its claim is now held on frozen
inputs by `tests/unit/devcapsule/configuration/test_capability_commands.py`:
the offline check of `project config check`, `check_documents`, accepts the
manifest and lock of three captured projects, `v026.2`, `v0.2.11` and
`repository-2026-10-25`, the last being this repository's own project as
committed, written from matrix `embedded-28`.

Still open, against the expected behaviour above:

- No capture was written by a released 0.3.0 client. For 0.2.14 and 0.2.15
  see the ruling below.
- No checkout record or authorization of a capture is read by the new
  test; `tests/test_upgrade_recovery.py` does that for `v0.2.11` only.
- The release runbook names no capture step.
- `v026-formation`, the hand-authored adopter shape, does not pass the
  check: `components.codex.npm-package must be '@openai/codex'`. Not
  judged here; the standing test of that capture covers inspection only.

## Owner ruling, 2026-11-12

Compatibility with 0.2.14, 0.2.15 and earlier releases may be dropped. No
capture from them is required, and the expected behaviour above no longer
names them.

What DevCapsule promises its users about compatibility is not yet defined.
It needs a story, which releases a project and a checkout stay usable
across and what a user does when they do not, and a packaging, how the
promise is stated, shipped and tested. The owner targets that for after
0.3.1. Until it exists:

- R-COMPAT-001 and R-CONFIG-001 stand as written; the story revises them.
- The captures `v026.2`, `v0.2.11` and `v026-formation` and the tests that
  read them stand. They are not a promise. A change that has to break one
  retires the capture and says so; it is not blocked by it.
- This record stays open as the test half of that work. Its close criteria
  are rewritten when the story is.
