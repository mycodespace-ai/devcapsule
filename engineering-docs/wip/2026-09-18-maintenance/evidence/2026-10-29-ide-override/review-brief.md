# Review brief for Codex, gpt-6-astra (high): PR304.1 on the explicit IDE requirement override

Claude Code, Claude Fable 5.1 opened PR #304, "One launch may depart from a required IDE: project run --ide IDE --force".
Its branch is `ws-maintenance/0.3.0-ide-override`; its base is `release-0.3.0`, into which `main` was merged on 2026-10-29 on the owner's word; the branch is synchronized with that merge.
The owner ruled on 2026-10-29 that `--save` with `--force` stays refused; that judgment is settled, do not reopen it.
No review of this slice has run yet. Related release reviews of this cycle are #293/#295, #299/#300 and #301/#302.
Your job is one improvement pull request against the implementation branch.
Costin Cozianu starts your session and merges the implementation PR.

## Your checkout

You are in `/home/devcapsule/worktrees/ide-override-review`, on `ws-maintenance/0.3.0-ide-override-review`, branched from `ws-maintenance/0.3.0-ide-override`.
Work only there. The human prepares and starts your session.
Do not touch `/home/devcapsule/worktrees/ide-override`, `/workspace/301e4208ef81-ChatGPT_Codex`, or any other worktree.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`, then the work order and the decision:

- `engineering-docs/work-orders/2026-10-28-explicit-ide-requirement-override.md`: the outcome, the deliverables and the acceptance evidence the owner ordered.
- `engineering-docs/decisions/product/d-0016-explicit-launch-departure-from-a-required-ide.md`: the owner's choice of an explicit launch exception over forbidding IDE requirements.
- `engineering-docs/requirements/product/r-config-001-conservative-writers-tolerant-readers.md`, *One explicit launch exception: the required IDE*.

Next read PR #304's "Judgments for the human", then `engineering-docs/development/review-partner-loop.md`.
Read the selected maintenance status, `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md`, for context, without changing it.
Then read these contracts and their implementations:

- `devcapsule-src/devcapsule/configuration/capabilities.py`: `RequirementDeparture`, `IDE_REQUIREMENT`, `CapabilityPolicy.departing`.
- `devcapsule-src/devcapsule/configuration/derivation.py`: `CheckoutState.departures`, `policy`, `required_ide`, `depart`; `with_selection`, `composed_lock`, `listing`, `derive_plan`.
- `devcapsule-src/devcapsule/configuration/capability_selection.py`: `compose_lock` with its `policy` parameter and the conflict message; `effective_lock`; `usable_lock`, the kept second surface; `inspection_capabilities`.
- `devcapsule-src/devcapsule/commands/_run_flow.py`: `RunFlags.force`, the two refusals at the top of `prepare_launch`, `_requested_ide`, `launch_listing_document`.
- `devcapsule-src/devcapsule/commands/project.py`: the `--force` argument of `ProjectRunCommand`, the warning after `prepare_launch`, the known-good and version-set records a departed launch does not write, `_run_flags`.
- `devcapsule-src/devcapsule/configuration/resolution.py` and `fingerprints.py`: the `[departures.<policy>]` table and the baseline digest from the launch policy; `model.py`, `Configuration(departures=...)`.
- `devcapsule-src/devcapsule/configuration/listing.py`: the `departures` parameter, the IDE row's source, the note and `Listing.document`; `storage.py`, `ResolvedProject.departures`.
- `devcapsule-src/tests/test_ide_requirement_override.py`, `tests/integration/test_pex_runtime.py` (the last test), `tests/e2e/test_required_ide_override.py` and `tests/e2e/ide_session.py`, `launched_ide`.
- `docs/reference/cli.md` (`run`), `docs/configuration/capabilities.md` (*A required IDE*), `docs/everyday-development/ides-and-terminals.md`.

## GitHub CLI

In every shell you run, first execute:

```sh
. /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh
```

Then `gh` is logged in to github.com as the owner's account against `ccozianu/devcapsule`.
Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists with the development dependencies installed.
Run unit tests and mypy from `devcapsule-src` with `PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-codex"`.
The gate type-checks `tests/` too. Run the full gate in the foreground before your final push:

```sh
PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-codex" .venv/bin/python -m nox -s build
```

Report the unit, packaging integration, web console, and documentation page counts.
Keep logs outside the pytest basetemp.
On the implementation tip the gate passed; PR #304 records the counts.

The touched files fall into these groups:

- The departure and the policy: `configuration/capabilities.py`, `derivation.py`, `capability_selection.py`, `fingerprints.py`, `model.py`, `resolution.py`, `listing.py`, `storage.py`.
- The command: `commands/_run_flow.py`, `commands/project.py`.
- Tests: new `tests/test_ide_requirement_override.py`; `tests/test_run_flow.py`, `tests/test_capability_policy.py`, `tests/test_retired_spellings.py`, `tests/integration/test_pex_runtime.py`; new `tests/e2e/test_required_ide_override.py`, `tests/e2e/ide_session.py`, `noxfile.py`.
- Texts: `docs/reference/cli.md`, `docs/configuration/capabilities.md`, `docs/everyday-development/ides-and-terminals.md`, R-CONFIG-001, D-0016, `REQUIREMENTS.md`, `index.md`.

Do not build images or run capsules. Do not run the IDE smoke.
The first pair ran the recorded IDE smoke, `nox -s ide-smoke -- --display --required-ide`, inside a capsule and records it in PR #304 and the status file.
For optional command reproductions, use a fresh directory under `/home/devcapsule/ide-override-review-evidence/`.
Set `DEVCAPSULE_CONFIG_HOME` to a throwaway directory there, so no real home is written. Remove only directories you create.

## The task

Review the diff against the release base:

```sh
gh pr diff 304
```

Start with the departure value and the policy, then derivation and the usable lock, then the command and its records.
Improve the implementation on your branch, focused on exactly three things, in this order:

1. Correctness of the new and modified lines.
   Does `--ide IDE` without `--force` refuse a conflicting required IDE before any materialization, through `run` and through `--print-command`, naming the exact override command, and does it write nothing?
   Does `_requested_ide` treat a component name and a capability name alike, compare canonical names, and refuse `--force` without `--ide`, with the required IDE itself, and on a project that requires no IDE?
   Does `CapabilityPolicy.departing` set aside exactly the named requirement and its minimum, and nothing else?
   Does the forced plan hold one interactive surface, the requested IDE, with the replaced IDE's closure omitted only as far as the remaining required and selected capabilities do not need it; is a remaining real dependency on the replaced IDE refused by name in `usable_lock` rather than failing in the catalog?
   Does the departure reach every derivation a real launch uses: `with_selection` and `pin_selection`, `compose_lock`, `effective_lock`, `derive_plan`, the second derivation after the upgrade offer in `ProjectRunCommand._run`, `realize_environment` and the runtime plan?
   Do the resolution's `[departures.ide-requirement]` table, the launch listing's IDE row and note, and the stderr warning agree with each other and with the documentation?
   Is nothing persisted: the manifest, the lock, the checkout record, the home; is `--force` with `--save` refused before any write; does a failed or interrupted forced launch leave the next plain launch ordinary; is a forced launch neither a known-good generation nor a proven version set?
   Do consent, channel trust, artifact integrity and the dependency checks still stop a forced launch; does `--force` grant no host access?
   Does an ordinary `--ide` override without a requirement conflict still work without `--force`, including the schema-1 `need` project whose IDE is a recommendation?
   Does `resolution_source_digests` with the launch policy keep the plain resolution's digests unchanged, so no fresh checkout is told to resolve again?
   Does a `config show` of the checkout after a forced launch report the checkout, never the departure?
2. Clarity of the new and modified lines. The standard is "obviously no deficiencies".
3. Test coverage of the new and modified lines. Add tests where a branch is not exercised.
   Every test must fail if the line it covers is broken. Do not pad.

Stay inside this slice: the one policy identity `ide-requirement`, its flag, its derivation, its records and its texts.
Do not broaden `--force` to other checks or other commands. Do not define `--save` semantics for a departure; the owner decides them.
Do not change how an IDE requirement is declared or migrated, D-0011, the matrix's shape, or the known-good history.
If a contract appears wrong, state why and keep your change minimal.
The owner retains the judgments listed in PR #304; report any proposal separately from implemented fixes.

## What you must not do

- Do not edit any `CURRENT-STATUS.md`, `intake-dispositions.md`, changelog, or `evidence/` file. Do not run `devcapsule workflow publish`.
- Do not commit `website` or sample-project submodule pointers, `.idea/`, `*.egg-info`, `.nox/`, `dist/`, or `__pycache__`.
- Do not merge anything. Push only `ws-maintenance/0.3.0-ide-override-review`.
- Do not rebase, force-push, push tags, or dispatch workflows.
- Do not build images, run capsules, or run the IDE smoke.

## Deliverable

1. Make commits on `ws-maintenance/0.3.0-ide-override-review`. Name the component, behavior, and evidence in each message.
   Before every commit, check `git status` and `git var GIT_AUTHOR_IDENT`.
   The author must be the human, Costin Cozianu. End each message with:
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`.
2. Push the branch and open one pull request:

   ```sh
   git push -u origin ws-maintenance/0.3.0-ide-override-review
   gh pr create --base ws-maintenance/0.3.0-ide-override --head ws-maintenance/0.3.0-ide-override-review
   ```

   Title: "Correctness, clarity and coverage review of #304 (PR304.1)".
   For each finding, state what was wrong or unclear, where, what changed, and how its test proves the change.
   Separate changes from items considered and left alone, with reasons. List proposals not implemented.
   State the gate counts and exclusions. If only tests change, open the PR with those tests.
   If nothing changes, report that instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or "NO PR" with the reason.

Write the body and report at about 80% ASD-STE100. Use one fact per sentence, about twenty words, and active voice.
Back every behavior claim with a test or command you ran.
If a network failure or credential blocker prevents progress, stop and name it. Do not work around it.
