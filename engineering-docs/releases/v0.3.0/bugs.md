# 0.3.0 — Bug Table

[Release overview](README.md)

Initial review: 2026-10-18 at the cut, `3c91183`; the console-link row added after the owner's rc0 launch the same day; reconciled 2026-10-21 after the owner's verification of rc1; the two C10 rows closed 2026-10-23 on the owner's verification of rc2; reconciled 2026-10-24 before candidate 4, no row changed. The linked records own
status, severity, target, ownership and technical evidence; this table
mirrors those fields for review and records the release's disposition and
next action. Update the record and its row together; reconcile before each
candidate and record the reconciliation revision here.

## Records targeted at 0.3.0

| Record | Status | Severity | Owner | Disposition | Next action |
|---|---|---|---|---|---|
| [Concurrent consoles overwrite cookies across ports](../../bugs/devcapsule/2026-10-31-webconsole-cookie-collides-across-ports.md) | closed | blocking | maintenance | fixed in release and main; rebuilt published base selected by RC9 | closed 2026-10-31 on downloaded RC9 shared-browser verification; evidence in the bug record |
| [Runtime configuration inspection fails in the recursive session](../../bugs/devcapsule/2026-09-24-runtime-configuration-inspection-fails.md) | closed | major | maintenance | fixed on `main` before the cut | closed 2026-10-31 on recorded RC9 verification and owner final acceptance |
| [Detached containers exit and are never cleaned up](../../bugs/devcapsule/2026-08-15-detached-successors-not-cleaned-up.md) | closed | minor | maintenance | fixed on `main` before the cut | closed 2026-10-31 on recorded RC9 verification and owner final acceptance |
| [`project <unknown>` refused as launcher-only inside a capsule](../../bugs/devcapsule/2026-09-26-project-group-guard-hides-unknown-subcommand-in-capsule.md) | closed | minor | maintenance | fixed on `main` before the cut | closed 2026-10-31 on recorded RC9 verification and owner final acceptance |
| [The recursive successor cannot refresh its capsule-local resolution](../../bugs/devcapsule/2026-10-04-recursive-successor-cannot-refresh-its-capsule-local-resolution.md) | closed | minor | maintenance | fixed on `main` before the cut; the fresh-workspace test proves it | closed 2026-10-31 on recorded RC9 verification and owner final acceptance |
| [Unpacked archive cache can lose concurrent work](../../bugs/devcapsule/2026-10-08-unpacked-cache-publication-and-recovery.md) | closed | minor | maintenance | fixed on `main` through PR #172 | closed 2026-10-31 on recorded RC9 verification and owner final acceptance |
| [`project run --authorize network host` refused without a recommendation](../../bugs/devcapsule/2026-10-05-run-once-network-authorization-needs-a-recommendation.md) | closed | minor | maintenance | the universal `network` node, fixed 2026-10-22 on the slice branch for rc2 | closed 2026-10-31 on recorded RC9 verification and owner final acceptance |
| [The launcher prints a web console link on a base without the console](../../bugs/devcapsule/2026-10-18-console-link-printed-on-a-base-without-the-console.md) | closed | minor | maintenance | found by the owner on rc0; fixed by PR #232, carried by rc1 | closed 2026-10-21 on the owner's verification of rc1 against the recipe-9 and a recipe-11 base |
| [A healthy launch looks unhealthy in the terminal](../../bugs/devcapsule/2026-10-22-healthy-launch-looks-unhealthy-in-the-terminal.md) | closed | minor | maintenance | C10, filed and fixed 2026-10-22 on the slice branch, carried by rc2 | closed 2026-10-23 on the owner's verification of rc2: the terminal summary as expected |
| [Ctrl+C ends the launcher with a traceback instead of a result](../../bugs/devcapsule/2026-10-22-ctrl-c-ends-the-launcher-with-a-traceback.md) | closed | minor | maintenance | C10, filed and fixed 2026-10-22 on the slice branch, carried by rc2 | closed 2026-10-23 on the owner's verification of rc2: Ctrl+C ends with a result |
| [Workstation-scoped commands live under `project config` and need a project](../../bugs/devcapsule/2026-10-25-workstation-commands-live-under-project-config.md) | confirmed | minor | maintenance | filed 2026-10-25 at the owner's direction from the rc7 setup script; the commands' home is the owner's design choice | the owner names the home; a slice of the cycle deletes the `project config` spellings |
| [Installed IDE cannot be reused before archive acquisition](../../bugs/devcapsule/2026-09-24-installed-ide-docker-reuse.md) | confirmed | minor | maintenance | split: cleanup of obsolete images and caches is a cycle slice after the owner's design review; reuse with an empty launcher cache is out of 0.3.0 | design review with the owner; retarget the reuse half at the next planning |

## Records of other workstreams the decision names

Two fixed records still say 0.2.16 on `main` and are their owners' to
retarget to 0.3.0: [agents cannot discover how to build and test](../../bugs/devcapsule/2026-10-03-agents-cannot-discover-how-to-build-and-test.md)
(`workflow-improvements`) and [an unreleased Playwright breaks the checkout launch](../../bugs/devcapsule/2026-10-04-unreleased-playwright-breaks-checkout-launch.md)
(`component-catalog`). They are verified against a downloaded candidate
once retargeted.

## Moved out with the cut

| Record | Status | Severity | Owner | Disposition |
|---|---|---|---|---|
| [Fresh clones require manual ecosystem bootstrap](../../bugs/devcapsule/2026-08-03-ecosystem-aware-project-bootstrap.md) | confirmed | minor | maintenance | retargeted to 0.9 on 2026-10-18 by the owner's decision of 2026-10-11; project-type templating is the dependency |

## Filed by the C10 slice

The two C10 records of 2026-10-22, the first-session terminal summary and
Ctrl+C ending with a result, have their rows above.
