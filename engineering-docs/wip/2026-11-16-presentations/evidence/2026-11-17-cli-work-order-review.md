# CLI work-order review assessment

Date: 2026-11-17.
Work order: [CLI syntax and discovery](../../../work-orders/2026-11-17-cli-syntax-and-discovery.md).
Source examined: `c5549f720aec2e94cdee31fb39c87b9cc5388d30`.
Fetched main: `0baf70bd6d02365b594cd73501c2ad338de9a50b`.

## Review performed

The author wrote and reread the full work order, then inspected the relevant adapters and console caller.
The owner requested Claude Fable 5.2 as the independent reviewer.
The actual responding model was `claude-fable-5-2`, verified in assistant events and the final response.
Session: `99beb086-6a6b-4f8d-9ebd-930088960bd3`. The review exited 0.

The prescribed permission-bypass launch refused to run as root.
A read-only launch used `--tools Read,Glob,Grep --allowedTools Read Glob Grep`.
The short model spelling `fable-5.2` was rejected; the full model identifier worked.
No other model substituted for the requested reviewer.
The reviewer used a same-workstream checkout at `/home/devcapsule/worktrees/presentations-cli-review`.
It changed no files and executed no project tests or shell commands.
This document review required no reviewer Python environment or implementation review PR.

## Findings and author assessment

1. **Compatibility and code boundary.** The console calls `project --path ...` directly in
   `devcapsule-webconsole/devcapsule_webconsole/cli.py`.
   Runtime reports and configuration remedies also generate old commands outside `commands/`.
   The reviewer recommends hidden aliases for at least one release and a separate string-only exception.
   The author agrees the compatibility decision is necessary, and leaves both choices to the owner.
   An alias alone does not make generated help adopt the new vocabulary.

2. **Instance versus checkout.** `CheckoutRegisterCommand` is a host mutation in `commands/project.py`.
   Notifications intentionally work from the host and inside the capsule.
   Moving names must not silently change those access rules.
   Both reviewers ask the owner whether registration belongs under `config`,
   or whether `instance` explicitly includes pre-launch checkout operations.
   The owner must also preserve or explicitly retire host notification access.

3. **Recording resources.** The installed skill invokes `presentations guide`, `export`, and `hand-off`.
   Setup preserves existing skill directories, so older copies retain those calls.
   The reviewer recommends keeping those paths hidden and callable.
   The author also offers installing the complete versioned kit with the skill,
   which requires a bounded resource-installation exception and a migration plan for existing copies.
   Neither option is adopted. No replacement public command is invented.

4. **General links.** The existing presentation adapter validates a presentation before using
   `presentation_authoring.presentation_link`, which formats a presentation route only.
   The console already exposes file, record, and presentation routes.
   The reviewer recommends restricting the new command to presentations for this refactor.
   The author rejects that recommendation because the owner explicitly requested general links.
   Preserve that goal, constrain URLs to the current console, and assess the adapter boundary.
   New server routes or serving behavior require a separate decision.

5. **Detailed JSON.** The console currently consumes configuration and information as separate documents.
   Both reviewers favor preserving those contracts, with a separate envelope for the new detailed form.
   Hidden old paths would preserve existing consumers while they migrate.
   This remains a proposed adapter design, subject to the compatibility decision.

6. **Explicit selection.** Reusing `--path` would conflict with the wrapper's subdirectory option.
   Both reviewers recommend a root `--project DIR` selector.
   This exact spelling was not adopted during the owner's iterative decisions.

7. **Release scope.** Neither review assigns this cleanup to RC4.
   The owner must set delivery scope before implementation is scheduled.

## Corrections made after review

Subsequent owner-question verification corrected the compatibility premise:
`scripts/build-pex.sh` bundles the console application in the PEX, and materialization installs it
ahead of the base-image fallback under D-0017. The base supplies its interpreter and dependencies.
The CLI and console callers can migrate together without a base-image rebuild for this syntax change.
The reviewer's base-only delivery claim, repeated initially by the author, was incorrect.
Old generated strings still exist outside the CLI adapter boundary; their disposition remains relevant.

The owner later answered the original six-question questionnaire, at 2026-11-17T20:16:44Z.
The work order records all six outcomes with explicit chat decisions taking precedence.
This selects `--project` and narrow RC4 scope; it does not answer the separate review questionnaire.

The order now names the CLI framework boundary and retains existing hidden runtime helpers.
It states that global configuration bypasses project discovery and preserves existing access rules.
It rejects compound `--set-state` operations and records the detailed-JSON proposal explicitly.
The configuration requirement link was repaired during the author's reread.

Not every reviewer suggestion was adopted. The state-adoption argument order was not a defect:
both orders accepted by argparse are equivalent. The complete public PyCharm removal is already
an owner decision; it does not depend on proving another image builder is identical.
Suggested spellings for global settings remain proposals rather than editorial facts.

## Validation and retained state

Subsequent owner decisions resolve the review questionnaire:
no old command aliases; delete legacy PyCharm code rendered unused by removing its command group;
move registration to `config --register NAME`; install the full recording kit alongside the skill.
The owner expressly accepts the bounded resource-installation exception.
Update callers with the new syntax while preserving behavior and JSON contracts.
These chat decisions override the reviewer's hidden-alias recommendation.
All outcomes are recorded in the work order before retiring the console question document.

Only work-order, index, and selected workstream records changed. No implementation files changed.
Work-order relative links resolve. `nox -s docs-contract` passes for 249 pages.
The required local build reached 3373 passing unit tests and the same two inherited recursive Docker-group failures.
It reported 1 skip, 198 deselections, 1 xfail, and 1 xpass in 89.23 seconds.
Syntax, version, types, and conventions passed before that stop; the full build is not green.
No new tests, containers, or environments were provisioned for this documentation change.
Raw CLI review and gate logs remain disposable under `/home/devcapsule/skill-validation/cli-work-order-*`.
The review checkout contains only disposable copies of the work order and brief on its review branch.
No records-only PR was opened. The review decisions are resolved; implementation has not begun.
