# The compatibility promise to users: a defined story and its packaging

Date: 2026-11-12
From: maintenance, driving release 0.3.1
To: project-management

## What is handed over

A need the product owner stated on 2026-11-12, to be planned. Their words:

> we can drop compatibility with 0.2.14, 0.2.15 etc, but we need a defined
> story and a packaging for our compatibility promise to our user, let's
> target that for after 0.3.1

and, on sending this item: "Our compatibility story is important."

Two things are in it:

1. **A ruling, already in force.** Compatibility with 0.2.14, 0.2.15 and
   earlier releases may be dropped.
2. **Work not started.** DevCapsule has no defined statement of what it
   promises users about compatibility. It needs one, the story, and a way
   to state, ship and test it, the packaging. The timing, after 0.3.1, is
   the owner's; maintenance assigns none.

## Why it belongs to project-management

It is not a maintenance fix. It decides product behaviour across releases,
revises two accepted requirements, and touches the user documentation, the
release procedure and the test suite. No registered workstream owns that
whole. Routing it is project-management's decision.

## What exists today

The promise is stated in several places that do not agree, and nothing
ties them together.

- **R-COMPAT-001**, accepted 2026-08-23: a newer client requires no user
  action for a project, checkout or lock "created by an earlier client".
  It names no limit on how early. The ruling above contradicts it as
  written.
- **R-CONFIG-001**, 2026-10-05: liberal in what is accepted, conservative
  in what is produced; a collaborator with a less capable launcher must not
  be stopped by an optional enhancement.
- **`WORKFLOW-LOCAL.md`, *Keep The Development Checkout Launchable***: the
  same direction as rules for this repository's own configuration.
- **The user documentation** makes its own statements:
  `docs/updates/launcher-updates.md` says an upgrade preserves every
  project's lock and every checkout's choices;
  `docs/configuration/capabilities.md`, *Existing files and older
  launchers*, says older launchers cannot read a schema-2 manifest and
  asks every contributor to upgrade first. Neither says which releases
  are covered.
- **The mechanisms**: schema versions in the manifest and the lock, the
  schema-1 to schema-2 migration of 0.3.0, `minimum-devcapsule` in the
  home's settings, the refusal that says "The project may require a newer
  DevCapsule".
- **The tests**: captured projects under
  `devcapsule-src/tests/resources/compat`, written by `v026.2` and
  `v0.2.11`, plus one hand-authored project of that era; the legacy files
  `tests/test_release_compatibility.py` and `tests/test_upgrade_recovery.py`
  read them. No capture was written by a released 0.2.14, 0.2.15 or 0.3.0
  client. The release procedure has no capture step.

Three incidents show the cost of the gap: released launchers rejecting this
repository's manifest (2026-09-24); an unreleased Playwright entry breaking
the checkout's launch (2026-10-04); a test that froze the repository's
configuration to v0.2.15 vocabulary, written under a rule the owner
superseded the next day and found still standing on 2026-11-12, two
releases later.

The compatibility feed under `component-status/`, which reports tested
agent versions, is a different subject and is not part of this item.

## What accepting it would mean

A workstream, or a slice of one, that delivers:

- **The story.** Which releases a project and a checkout stay usable
  across, in both directions: a newer launcher on an older project, and an
  older launcher on a project a newer one has written. What the user is
  told and does when the limit is passed. What "dropped" means for a
  release outside it: refused with a named remedy, or untested.
- **The requirements brought into line.** R-COMPAT-001 and R-CONFIG-001
  revised to state the story, with its limit.
- **The packaging.** Where a user reads the promise, in the documentation
  and the release notes; how each release states what it covers and its
  exceptions; how the suite holds it, by captures written by the releases
  in scope and a step in the release procedure that adds one and retires
  one.

## What maintenance has done and will not do

On `ws-maintenance/launch-phases`, pull request #29, not merged:

- The frozen-vocabulary tests are deleted.
  `tests/unit/devcapsule/configuration/test_capability_commands.py` tests
  the offline check of `project config check` on the existing captures and
  on a byte copy of this repository's own manifest and lock.
- The ruling is recorded in the bug record
  `engineering-docs/bugs/devcapsule/2026-10-18-no-test-proves-old-projects-launch-with-new-releases.md`,
  which stays open as the test half of this work.
- Until the story exists, the pre-0.3 captures and their tests stand. They
  are not a promise: a change that has to break one retires the capture
  and says so.

One observation for whoever takes this: the hand-authored capture
`v026-formation` no longer passes `check_documents`
(`components.codex.npm-package must be '@openai/codex'`). Under the ruling
that may be acceptable; nobody has judged it.

Maintenance does not design the story, edit the two requirements, or
remove the old captures.

## Evidence

- The bug record of 2026-10-18 named above, with its sections *Progress,
  2026-11-12* and *Owner ruling, 2026-11-12*.
- `engineering-docs/requirements/devcapsule/r-compat-001-client-upgrades-require-no-user-action.md`
  and
  `engineering-docs/requirements/product/r-config-001-conservative-writers-tolerant-readers.md`.
- `engineering-docs/bugs/devcapsule/2026-09-24-released-launchers-reject-repository-manifest.md`
  and
  `engineering-docs/bugs/devcapsule/2026-10-04-unreleased-playwright-breaks-checkout-launch.md`.
- `devcapsule-src/tests/resources/compat/README.md`.
- The maintenance status file,
  `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md`,
  published at coordination `565b6d8962c9`.
