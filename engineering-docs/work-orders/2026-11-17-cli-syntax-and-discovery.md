# Work Order: Simplify CLI Syntax And Help Discovery

Date: 2026-11-17.
Owner: presentations, by explicit product-owner direction.
Status: reviewed; all review-questionnaire decisions resolved by the owner; implementation not started.
Release scope: RC4 gets the help bug fix and presentations cleanup; broader CLI cleanup follows 0.3.1.
The exact next release number remains undecided.

Author reread and Claude `claude-fable-5-2` review completed on 2026-11-17.
See the [review assessment](../wip/2026-11-16-presentations/evidence/2026-11-17-cli-work-order-review.md).
The review identified decisions; it did not adopt changes to the owner's vocabulary.

## Outcome

Make the current project the default CLI context. Reduce the ordinary command list.
Use options for variations of an operation. Keep advanced operations discoverable.
Preserve the implementation's behavior and storage model.

The owner assigned this cleanup to presentations during an iterative CLI review.
This work order records those decisions. The original six-question questionnaire's structure was rejected,
but the owner subsequently answered all six items at 2026-11-17T20:16:44Z.
Chat decisions take precedence where they conflict with those older options.
The review questions were subsequently answered in chat. Their outcomes are recorded below.

### Recorded questionnaire outcomes

- Remove the separate skill-install command, consistent with the later removal of the presentations group.
- Group help by purpose. The older option to keep command paths does not override the explicit chat renames.
- Explain and group configuration operations; do not add an unrequested hierarchy for project and personal settings.
- Standardize project selection on `--project`.
  The later no-legacy-alias ruling supersedes the older compatibility suggestion; exact placement remains proposed.
- Rewrite help across the command tree with short summaries, meaningful arguments, examples, and discoverable operations.
- RC4 gets the help bug fix and presentations cleanup. Broader changes belong to the first release after 0.3.1.
  Do not interpret this as permission to implement the entire proposed layout for RC4.

### Final review decisions from the owner

- Do not support old command aliases. Update callers to the new syntax.
- Remove legacy PyCharm implementation code made unreachable by removing the public command group.
  Preserve code still used by other operations; establish reachability before deleting it.
- Move host-side checkout registration to `devcapsule config --register NAME`.
- Install the complete recording helper directory and instructions alongside the skill during workflow setup.
  The owner explicitly accepts the bounded resource-installation change needed for this delivery.
  Retain automatic installation for wrapper setup as already directed.

These decisions supersede the reviewer's suggestions to retain hidden old commands.

## Evidence and existing contracts

- Reviewed working source: `c5549f720aec2e94cdee31fb39c87b9cc5388d30`.
- Fetched main: `upstream/main` at `0baf70bd6d02365b594cd73501c2ad338de9a50b`.
- Release baseline: `757392b21794ba2cb275db7976441f218da1fbe1`, before this branch's automatic skill installation.
- Main's workflow difference from the working branch is its `0.3.2.dev0` version stamp.
  Retain the release baseline for this document; no main synchronization is needed.
- A recursive inspection exercised 102 help invocations against the local PEX from the reviewed source.
  One invocation, `pycharm check-runtime --help`, ran diagnostics instead of printing help.
  This work removes that public command and any legacy implementation code left without callers.
- Both `project config show` and `project info` were run inside the current capsule.
  They overlap, but neither is a complete replacement for the other.
  The first shows effective choices, sources, and pending decisions.
  The second adds software, environment, and persistence information.
- Existing adapters are under `devcapsule-src/devcapsule/commands/`.
  The skill is `devcapsule-src/devcapsule/presentation_tools/SKILL.md`.
  It currently calls `presentations guide`, `export`, and `hand-off`.
- Relevant requirements: [configuration](../requirements/product/r-config-001-conservative-writers-tolerant-readers.md),
  [wrapped projects](../requirements/product/r-wrap-001-wrapped-projects.md),
  [web console](../requirements/product/r-console-001-capsule-web-console.md),
  [software versions](../requirements/product/r-upgrade-001-component-version-sets.md),
  and [current CLI documentation](../requirements/product/r-docs-002-current-user-docs-show-current-interfaces.md).
  Verify the final syntax against these contracts before implementation.
  This order does not reopen their behavioral decisions.

## Binding implementation boundary

This is a CLI syntax refactor. Keep underlying implementation unchanged except for the two explicit owner grants:
remove unused legacy PyCharm code, and install the complete recording kit with the skill.
Limit production changes to a well-delimited CLI adapter layer: parse arguments, construct values,
dispatch to existing operations, and compose their existing reports.
The adapter boundary includes `devcapsule/cli.py`, `commands/framework.py`, and the console's CLI caller adapter.
Migrate affected command invocations and user-facing command suggestions mechanically; do not change their domain behavior.
Update directly affected tests, instructions, examples, and documentation.
Do not move domain behavior into command adapters to evade this boundary.

Preserve storage layouts, defaults, consent rules, validation, side effects, and host-access boundaries.
Changing vocabulary does not grant new global settings or new in-capsule mutation capabilities.
Update machine-readable consumers with the new syntax while preserving existing report contracts.
If an agreed interface needs further implementation changes beyond the recorded grants, ask for a bounded exception.
Do not perform the implementation as part of preparing or reviewing this work order.

## Accepted public vocabulary

Ordinary `devcapsule --help` lists these eight entries:

```text
config      Show or change configuration; -g / --global selects per-user scope.
images      List and build images.
init        Initialize a project; --wrap wraps another repository.
instance    Operations associated with the running capsule.
list        List registered checkouts.
run         Launch the current project's capsule.
version     Show the DevCapsule version.
workflow    Install workflow files and coordinate workstreams.
```

Advanced top-level help additionally lists `diagnose`, `recursive-e2e`, and `runtime`.
These commands remain callable without `--advanced`.
The flag controls help visibility, not execution permission.

Every help page that hides advanced commands or options advertises them:

```text
Additional commands or options are available with --help --advanced.
```

The rule applies at every nesting level.
`devcapsule config software --help --advanced` reveals the software-management operations.
Ordinary software help still describes its purpose and points to advanced help.
Help must not execute an operation or require a running capsule merely to explain its syntax.

## Accepted old-to-new mapping

All examples below have the `devcapsule` prefix.

| Old syntax | New syntax or disposition |
| --- | --- |
| `project <command> ...` | `<command> ...`, subject to the more specific mappings below |
| `project --path DIR ...` | Use `--project DIR`; no old command alias; exact placement remains proposed |
| `home ...` | `config -g ...` or `config --global ...`; map individual operations before implementation |
| `bootstrap project` | `workflow bootstrap` |
| `project config ...` | `config ...` |
| `project config show` | `config show` |
| `project info` | `config show --detailed`, including the ordinary configuration view |
| `project wrap URL ...` | `init --wrap URL ...` |
| `project state adopt --from DIR SLOT` | `config --set-state SLOT DIR` |
| `project versions ...` | `config software ...`; operations appear only in advanced software help |
| `project checkout register NAME` | `config --register NAME`, preserving host-side registration behavior |
| Other `project checkout ...` operations | `instance ...`, preserving their existing access rules |
| `presentations hand-off ...` | `instance --get-link PATH-OR-URL`, generalized to project content |
| `presentations guide`, `export`, `install-skill` | Remove commands; install instructions and complete helper directory with the skill |
| `pycharm ...` | Remove the public group and legacy implementation code made unused by its removal |
| `project diagnose ...` | `diagnose ...`, shown only in advanced top-level help |
| `project recursive-e2e ...` | `recursive-e2e ...`, shown only in advanced top-level help |
| `runtime ...` | Remains callable; shown only in advanced top-level help |
| `images ...`, `version`, existing `workflow ...` | Retain, with the help and bootstrap changes above |
| Existing hidden `github-ssh` and `host-open` helpers | Retain hidden and unchanged; they are not ordinary user commands |

`project`, `home`, `bootstrap`, `info`, `wrap`, `state`, `versions`, `checkout`,
`presentations`, and `pycharm` do not appear as ordinary top-level entries.
Removed or renamed paths have no callable compatibility aliases.
Do not delete shared implementation code that still has callers.

## Meaning of the selected forms

### Project and global configuration

A project command uses the current project unless the user explicitly selects another.
`config` retains the existing distinction between project-owned declarations and checkout choices.
`config -g` and `config --global` mean settings shared across projects for this user.
They never mean system-wide configuration.
Do not create global variants of settings that the existing implementation only supports locally.
Specify which existing home operations map to global config and what unsupported combinations report.
Global configuration must remain usable without project discovery, as the existing home operations are.
It retains their existing host/capsule access rules.

### Detailed information

`config show --detailed` includes the ordinary configuration information and the existing information report.
Preserve labels distinguishing captured-at-launch, observed-in-process, and next-launch information.
Preserve secret omission and masking. Detailed output does not mean an unfiltered environment dump.
Compose the reports at the CLI boundary; do not rewrite their implementation.
The JSON form and existing web console consumers need an explicit compatibility disposition.
Proposed adapter design: keep plain `show --json` unchanged; detailed JSON contains the two original
documents as separate named members. This is not permission to change either existing schema.

### Initialization and state

`init --wrap URL ...` dispatches to the existing wrapper operation.
Preserve its handling of foreign sources, repeated wrapping, options, and skill installation.
Specify which options belong to ordinary initialization and which belong to wrapping.
Reject conflicting forms before dispatch rather than inventing a compound operation.

`config --set-state SLOT DIR` dispatches to the existing state-adoption operation.
`DIR` is a directory on the host. Preserve its checks and interpretation of paths.
Its syntax does not grant a capsule access to an arbitrary host directory.
`--set-state` selects one operation; it cannot be combined with a config subcommand or `--global`.
Existing `config bind` behavior remains unchanged.

`config --register NAME` dispatches to the existing host-side checkout registration operation.
It registers this checkout, not global user settings, and preserves existing duplicate-registration checks.

### Running-instance operations and links

The owner chose `instance --get-link PATH-OR-URL` for a general web console link operation.
It runs inside the current capsule and uses that capsule's console and project context.
It must serve project content generally, not only recorded presentations.
Tokened links remain in chat or runtime output, never in Git records.
Notifications and decisions move under `instance`, retaining their existing host/capsule access rules.
The owner resolved the host-side registration conflict by placing it under `config --register NAME`.

Do not assume that an arbitrary project directory has the same console route as a presentation.
Decide the accepted input forms and supported destinations against existing console routes.
Do not add console routing or serving behavior under the guise of a CLI rename.
The reviewer proposed limiting this to presentations. That recommendation is not adopted:
it contradicts the owner's explicit requirement for general links.
Existing `/files`, `/records`, and `/presentations` routes are relevant implementation evidence.
Reject URLs outside the current console origin; never forward the run token to another origin.
Determine whether all required formatting can stay in the adapter before requesting a code-boundary exception.

### Recording skill

Install the skill with workflow files; retain the already requested automatic wrapper installation.
The user should not need a separate skill-install command.
Removing `presentations` must not strand instructions that invoke its deleted commands.
Install the full instructions and Python helper directory alongside the skill, not only `SKILL.md`.
Use the packaged kit from the workflow installer and record its version provenance.
Update the skill to use those installed resources and the general instance link operation.
Do not add a replacement export command or hidden legacy aliases.
Define migration guidance for previously installed skills that invoke deleted commands.
Preserve the existing protection of user-customized files; do not silently overwrite them during migration.

## Open decisions and stopping points

These are not adopted solutions. Present concrete alternatives with reasons after review.

1. `--project DIR` is selected by the questionnaire; should its canonical placement be before the command?
2. Which individual global and instance operations keep subcommands, and which become modifiers?
   Prefer modifiers for variations; do not convert every verb mechanically.
3. What input forms and existing console destinations does `instance --get-link` support?
   Is a bounded implementation exception required for general links?
4. Inventory JSON consumers, runtime invocations, and generated command suggestions for migration.
   Old CLI paths are removed without aliases; preserve schemas and operation behavior behind the new paths.
   The shipped console invokes old paths, but its application code travels in the PEX under D-0017.
   CLI and console callers can therefore change together without a base rebuild for syntax-only changes.
   The earlier claim of ordinary console/CLI version skew from base-only delivery was incorrect.
   Remedy strings and generated guidance also exist outside the CLI adapter layer.
   Update those strings without changing the operation they describe.
5. RC4 scope is narrow and broader cleanup follows 0.3.1. Set the exact next release number when scheduling.

Review may resolve editorial ambiguity within accepted decisions.
Review cannot adopt product choices or enlarge the implementation boundary.
Keep unaffected accepted decisions binding while disputed parts await the owner.

## Deliverables and completion criteria

1. A reviewed syntax specification and complete mapping for every existing operation.
   Enumerate all 102 inspected help paths and any forwarded or internal callers discovered during implementation.
   Mark each retained, moved, removed, or hidden. Leave no operation accidentally unreachable.
2. CLI adapters implementing the adopted grammar, global scope selector, and recursive help visibility.
   Ordinary and advanced help match the agreed command inventory.
3. Existing behavior preserved behind the adapters.
   Document the exact production-file boundary before editing; obtain approval for any exception.
4. Updated skill instructions and consumers, using the agreed replacement delivery and link paths.
   Automatic setup still results in a usable recording skill.
5. Updated current CLI documentation and generated examples.
   Historical records remain historical; do not rewrite previous release evidence.
6. Validation evidence and a reviewable implementation pull request when implementation is authorized.
   This work-order review itself creates no records-only pull request.

## Acceptance evidence

- Recursively run ordinary and advanced help through the built executable.
  Verify exit status, discoverability, and absence of execution side effects, including outside a project.
- Exercise representative old-to-new adapter equivalence at the CLI boundary.
  Verify parsed values, selected existing operations, errors, and exit codes.
  Do not write tests that merely restate a new parser's structure.
- Check project discovery, explicit project selection, and per-user global scope outside a project.
- Check ordinary and detailed reports on the host and inside a capsule, including provenance and redaction.
- Check wrapper dispatch and state adoption with existing relevant tests and safe temporary fixtures.
- Check the real shipped console consumer and internal launcher calls against the compatibility decision.
- Verify removed command paths are not accepted as aliases. Confirm no live caller depends on deleted legacy PyCharm code.
- Verify installed skill resources and generalized links using existing console routes.
  No fresh recording or container launch is required merely to review this document.
- Run the repository's required build and targeted integration checks for the implementation changes.
  Document inherited environment failures separately from regressions.
- Review the production diff for implementation-layer changes before declaring the syntax-only constraint met.

## Workstream and review

The owner explicitly keeps this work in presentations; do not switch workstreams.
The author must reread this order after writing it.
The requested independent reviewer is Claude `fable-5.2` through the installed CLI.
Verify and record the actual model reported by that session.
Ask it to identify contradictions, missing mappings, and unnecessary vocabulary.
Bring justified concerns back to the owner before making implementation changes.
