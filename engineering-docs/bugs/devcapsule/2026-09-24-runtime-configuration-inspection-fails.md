---
status: closed
severity: major
target: 0.3.0
owner: maintenance
opened: 2026-09-24
requirements: [R-UPGRADE-001, R-PRODUCT-001]
---

# In-capsule configuration inspection fails in the RC1 recursive session

The owner reports that RC1 mostly works, but configuration inspection fails
from both `/opt` and the mounted project. The original terminal transcript
was unavailable; both diagnostics were reproduced independently below.
This is separate from the repaired public-command/PATH defect: `devcapsule0`
is present and running the correct published executable.

## Expected behavior and ownership

Read-only configuration inspection from inside the capsule was part of the
component-upgrades deliverable for 0.2.14. See the
[implemented runtime inspection contract](../../implementation-notes/devcapsule/2026-09-21-component-distribution-channels.md#runtime-inspection).
The component-upgrades workstream therefore owns this bug, including the
recursive launcher parity gap; maintenance filed it during release validation.

`project config list` should report the launcher's recorded configuration
without attempting host-path validation, creating a shadow checkout, or
repairing host records. The owner additionally expects inspection with no
explicit project from a directory such as `/opt` to discover the enclosing
capsule's project. Preserve explicit project selection and nested-project
launcher use when defining that fallback.

Mutating commands such as `config set`, `authorize` and `resolve` remain
launcher operations under the current read-only contract. This report does
not authorize making host configuration writable inside a capsule.

## Exact environment and reproduction

- Published executable: `v0.2.14-rc1`, source `cec7a0c`, SHA-256
  `68c58ec09c1a73e07c3bb1b1f7514341ddddaf645c7fae1ff4ff0763ff6f7689`.
- Retained run: `0edc6f491291f0d5ffa4e31b0238863b`; successor
  `devcapsule-e2e-0edc6f491291f0d5ffa4e31b0238863b-successor`.
- Environment image:
  `sha256:bc387eb69b8457f61f016a0a21485302e3fc14bcbbae977e4a1623b8d5544863`.
- Base: `devcapsule-base:0.2.14-rc1-local`; host networking in the original run.
- Actual project mount: `/workspace/301e4208ef81-ChatGPT_Codex`.

The original successor had already exited with code 0. A disposable CLI-only
container used its exact image, the same project mounted read-only, and its
`PROJECT_PATH`/`DEVCAPSULE_CONTAINER_NAME` values. It ran as UID 1000, with
network disabled, no Docker socket or credentials, and temporary HOME. The
probe did not restart the IDE or alter the checkout/configuration.

| Working directory | Command | Result |
|---|---|---|
| `/opt` | `devcapsule0 project config list` | Exit 2: `No .devcapsule/devcapsule.toml found from /opt; run 'devcapsule project init'.` |
| Project mount | `devcapsule0 project config list` | Exit 2: `This capsule has no launcher configuration mount. Relaunch this project from outside the capsule with the updated DevCapsule launcher, then retry. Its running versions cannot be inferred from the project recommendation.` |

`project versions show` produces the same two failures. Bare `project config`
prints help and exits 0 in both directories; it is not the inspection command.
Exact probe output is retained in `configuration-diagnostics.json` under the
run's persistent-home `e2e-workspaces/` directory.

## Confirmed causes and coverage gap

1. Docker inspection of the original successor proves it lacks both
   `/etc/devcapsule/launch-context.json` and `/etc/devcapsule/checkout`.
   `ProjectRunCommand` passes `LaunchConfiguration.capture(...)` through
   `PycharmRunOptions`; `recursive_successor._resolved_run_options` does not.
   The missing-context diagnostic is intended for old capsules, but here the
   current recursive launch omitted the contract itself. Repeating that launch
   with the same RC1 executable will not repair it.
2. `runtime_configuration.for_project` discovers from the supplied starting
   directory. When no project exists there, it retains that directory and
   compares it to the runtime root; it never selects the capsule project as
   the default. This also affects an ordinary launch with valid context when
   inspection starts outside the project tree.

Existing runtime-inspection tests in `tests/test_version_sets.py` construct
the two mounts from ordinary launch options and invoke commands at the project
root. The recursive inspector validates its generated expected plan, but that
plan itself omits these mounts. Its earlier PASS did not test this user story.

## Verification needed before closure

- Actual ordinary and recursive launches supply the same read-only inspection
  contract; test the launch producer as well as the runtime reader.
- Published-candidate `config list` and `versions show` work from the project,
  its descendants, and `/opt` without an explicit project selection.
- Explicit `--path` and separate/nested projects retain their documented
  meaning; malformed or missing context is diagnosed without inventing state.
- Host-record atomic replacement remains visible through directory mounting;
  reads do not mutate records and unsupported mutations remain refused.
- Relaunch with the fix and validate the owner-facing terminal behavior.

No implementation changes made during intake. Severity and release disposition
await owner triage; no final-release acceptance is inferred from "mostly works."

## Owner observation on v0.2.14-rc3, 2026-09-24

In a capsule launched by an ordinary `project run` with the published rc3:
from `/opt`, `devcapsule0 project config list` fails as recorded above
(cause 2, no fallback to the enclosing capsule's project when the working
directory is outside the project tree); from the project mount under
`/workspace`, it succeeds and shows the project's configuration as
recorded on the host. This narrows the bug: cause 1, the missing
launch-context mounts, belongs to the recursive test launcher only and does
not affect ordinary launches. The user-facing defect is cause 2 alone, and
it is small: discovery should fall back to the capsule's project when no
project is found from the working directory and the runtime context names
one. The recursive launcher's parity gap remains a test-harness fix.

## Disposition, 2026-09-25

Owner ruling: discovery of the configuration inside the capsule from a
directory outside the project, such as `/opt`, is minor and is sent to the
V1 release to decide; it does not hold 0.2.14. The recursive test launcher's
missing mounts remain a test-harness fix on the same record.

## Owner ruling, 2026-10-01: fix it for 0.2.16, whole and not by halves

The owner, inside a 0.2.15 capsule, hit both failures again and ruled that
inside a capsule every `project` subcommand selects the capsule's own
project automatically, from any working directory, exactly as `project info`
does since 0.2.15; the read-only ones then answer, the mutating ones then
say to run the launcher. "Time to kill this bug once and for all." Fields
changed accordingly: `target` 0.2.16, `severity` major (the product claims
read-only inspection inside the capsule and from `/opt` there is no
workaround), `owner` `maintenance` under the owner's routing rule of the
same day: `component-upgrades` owns component wiring, defects in the project
CLI are maintenance's. Recorded by `project-management` at the owner's
direction.

### Reproduction on the published v0.2.15, 2026-10-01

Installed launcher `devcapsule0` reporting `DevCapsule v0.2.15 (package
0.2.15)`, inside the dogfood capsule for this repository, which has
`/etc/devcapsule/launch-context.json` and `/etc/devcapsule/checkout` mounted.

| Working directory | Command | Result |
|---|---|---|
| project mount | `project config show` | Exit 2: `This command needs launcher-owned configuration or state. Inside this capsule that configuration is read-only. Run outside the capsule: devcapsule project --path <host path> config show` |
| project mount | `project config list` | works: `Runtime context: read-only launcher configuration for the next launch.` |
| project mount | `project versions show` | works |
| project mount | `project info` | works |
| `/opt` | `project config show`, `config list`, `versions show` | Exit 2: `No .devcapsule/devcapsule.toml found from /opt; run 'devcapsule project init'.` |
| `/opt` | `project info` | works: `Context: running capsule (captured at launch)` |

### Confirmed causes, read from the source at `fd49bd1`

Three separate defects in two files produce the owner's transcript; the
fallback mechanism itself exists and `project info` already uses it.

1. **`config show` is refused as launcher-only although it is read-only.**
   `ProjectCommand.make_context` in `devcapsule/commands/project.py`
   admits only `("versions", "show")` and `("config", "list")` before
   calling `runtime_configuration.require_launcher`. `ConfigShowCommand`
   shares `_print_configuration_listing` with `config list`, which prints
   the runtime report and returns `None`, and `show` then returns 0. The
   allowlist is simply out of date.
2. **No fallback to the capsule's project for `config list`, `config show`
   and `versions show`.** `_print_configuration_listing` and
   `version_sets.inspect` call `runtime_configuration.for_project(start)`
   without `fallback=True`. From `/opt`, discovery fails, `for_project`
   returns `None` because the start directory is not the runtime root, and
   the caller falls through to `manifest_for(start)`, which raises the
   "No .devcapsule/devcapsule.toml" error. `ProjectInfoCommand` passes
   `runtime_fallback=selected.selected_path is None` and works; the other
   three need the same.
3. **The guard runs before argparse validates the subcommand**, the defect
   of the 2026-09-26 record, in the same function.

`require_launcher` also calls `for_project(start)` without the fallback, so
from `/opt` a mutating command reaches the "no devcapsule.toml" error
instead of the launcher message; the fix should give it the same fallback.

### Fix shape and close criteria

Replace the token allowlist with the rule the ruling states: the `project`
group resolves its project as `info` does (explicit `--path` wins,
otherwise discovery, otherwise the capsule's runtime context), every
implemented read-only command answers from the runtime context, and
`require_launcher` is reached only for a valid, mutating subcommand. Tests
in `tests/test_project_commands.py` and `tests/test_version_sets.py` cover
the four commands from the project root, a descendant and an unrelated
directory with a patched launch context, plus the unknown-subcommand case.
Close when the owner reruns the table above on a 0.2.16 candidate and every
row works. The recursive test launcher's missing mounts (cause 1 of the
original record) stay a test-harness task on this record.

## Fix, 2026-10-05, on `ws-maintenance/post-0.2.15`

Whole and not by halves, as ruled: the `project` group now applies one
declaration per subcommand instead of a token allowlist.

- `CapsuleAccess` in `runtime_configuration.py` names what each leaf of the
  `project` tree may do with the capsule's own project: `INSPECTS` (selects
  it, answers read-only), `MUTATES` (selects it, refused inside in favour of
  the launcher command), `CREATES_HERE` (`init`: acts in the working
  directory, refused when that is the capsule's project), `INDEPENDENT`
  (`list`, `recursive-e2e`). Every leaf declares its own; a test walks the
  tree. `config show` is `INSPECTS`, which closes cause 1.
- `capsule_project_root` selects the capsule's project when no project
  encloses the working directory and the runtime context names one; the
  group sets it on the command context before dispatch for every
  `INSPECTS` and `MUTATES` leaf, which closes cause 2 for `config list`,
  `config show`, `versions show` and every mutating command alike. An
  explicit `--path` still wins, a nested project is still a launcher, and
  an older capsule without the mounted context is still diagnosed.
- `Group.resolve` in the command framework names the subcommand without
  side effects; the group consults it before applying the access, so an
  unknown name reaches the ordinary dispatch error, which closes cause 3
  and the [guard record](2026-09-26-project-group-guard-hides-unknown-subcommand-in-capsule.md).

Cause 1 of the first section, the recursive successor launched without the
two read-only mounts, is not touched here: it belongs to the test launcher,
which the [recursive-successor record](2026-10-04-recursive-successor-cannot-refresh-its-capsule-local-resolution.md)'s
option D rewrites.

Evidence: `tests/test_version_sets.py` (inspection from anywhere, mutation
from anywhere, unknown subcommand, `init` acting where invoked),
`tests/test_project_commands.py` (every leaf declares its access),
`tests/test_command_framework.py` (resolution); and the source CLI run from
`/opt` inside this repository's own 0.2.15 capsule: `config list`, `config
show` and `versions show` answer from the runtime context, `config set`
names the launcher command with the host path, `project --path $PWD
bootstrap` reports an unknown command. Closes on the owner's confirmation
with a 0.3.0 candidate.

## Downloaded RC9 verification — 2026-10-31

The published RC9 executable returns valid JSON for config show, versions show and project info from the project root, a descendant and /opt (nine checks). The fresh-workspace attached-successor inspection also passes. The old config list spelling is retired; config show is the current contract.

[Final audit evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#final-promotion-audit--2026-10-31).
Verification is complete; the release acceptance/closure checkpoint remains
pending the explicit final scope and provider dispositions.

## Closed — 2026-10-31

Closed on the RC9 verification above and the owner's final acceptance of
that exact candidate on 2026-10-31. [Acceptance record](../../releases/v0.3.0.json).
The fix is in RC9 source 475427da and main 4b59b10d; the documented test
limits are retained. This supersedes the pending-closure sentence above.
