---
status: closed
severity: untriaged
target: none
owner: maintenance
opened: 2026-09-19
closed: 2026-09-22
requirements: [R-PRODUCT-001, R-PRODUCT-002, R-COMPAT-001]
---

# Bug: Upgrade Configuration Recovery Rejects Its Own Remedy

## Closure — 2026-09-22

Closed at the owner's explicit direction after review of the implemented
recovery fix, regression evidence and recorded acceptance. PR #117 merge
`d2386bb` is verified as an ancestor of both main and `v0.2.14-rc0` (`d078b87`).
The 2026-09-21 owner report and
[graphical predecessor-configuration acceptance](../../wip/2026-09-18-maintenance/2026-09-21-record-maintenance-before-component-upgrades.md)
establish successful use and normal successor exit; the earlier notes awaiting
integration and host acceptance below are historical and superseded.

This closes the demonstrated recovery/upgrade failure. It does not certify
every historical configuration or complete RC0's end-user acceptance campaign;
exact original host configuration bytes remain unavailable. The release keeps
its predecessor-recovery checks, and the existing reopen conditions still apply.

## Symptom And Impact

After replacing the v0.2.11 launcher with v0.2.12, the owner tried the ordinary
`devcapsule project run` in this project's host checkout. It failed. Following
the prescribed commands exposed successive stale authorizations, then a
base-image recovery command that the same executable rejected. Recovery depended
on the owner remembering the undisclosed `default` shortcut. After resolving,
the owner reports that the previous host-X11 experience was lost and an
unexpected, non-instant Docker image build occurred; explicit `host-x11`
authorization and another resolution restored host-X11 launch.

Confirmed from owner-supplied terminal evidence on 2026-09-19; the incident's
exact execution date was not supplied. The implementation and deterministic
regression evidence are recorded below; host acceptance remains pending.
Severity and release target await owner triage.

This is an end-to-end upgrade/recovery defect, not just an isolated wording
issue. Individually plausible checks compose into a failed user journey. The
owner explicitly connected this incident to the earlier Hoare-standard
directive: configuration should be simple enough to reason about its correctness,
not merely pass checks that fail to expose deficiencies.

## Environment And Provenance

- Host shell reports `(base) costin@pop-os`; host checkout:
  `/home/costin/work.provisional/costin3/myProjects/devcapsule-2`.
- Owner reports exiting the existing capsule, downloading/installing v0.2.12
  `devcapsule.pex` over v0.2.11, then attempting `devcapsule project run`.
- The owner subsequently clarified that the immediately preceding session was
  working under host X11 while demonstrating the project to a friend. They
  exited that working environment, downloaded the latest release PEX, and
  expected to resume. This is a continuity failure from a demonstrated working
  session, not difficulty setting up an unfamiliar checkout. No deliberate
  configuration change was reported as part of that sequence.
- Executable reports package `0.2.12`, revision
  `2916c4c09aee13eeed85276c1a32889515ce7b19`.
- Both manifest and platform-lock differ from the saved local resolution,
  according to the first error. Their prior contents were not supplied; this
  is not evidence that replacing the executable alone changed those files.
  How and when those source files diverged from the saved resolution remains
  unknown; that uncertainty does not negate the owner's working-X11 baseline.
- Previous selected base digest:
  `76a07cb9e72158f810b32598eb05f9a375f8e4748b80b6eac04c403798d39a45`.
- Current recommended base digest:
  `8837edd36720763796ab9fe1dbeb66f1aa7ca2db0dabc8d73a58716440f42f7c`,
  displayed as `v0.2.12-rc5` by the final v0.2.12 executable.
- Host checkout configuration lives under
  `/home/costin/.config/devcapsule/projects/https%3A%2F%2Fgithub.com%2Fccozianu/devcapsule/checkouts/`.
  These are the host launcher's records, not assumed to be the same as records
  visible inside the capsule.
- Final successful launch reused
  `devcapsule-local-pycharm:4356c1fcfe2b762aad9c` with explicit host-X11 access.
  The preceding unexpected build's output, duration and image identity were
  not supplied.

## Owner-Supplied Command And Output Evidence

Shell prompts are omitted below; commands, output, digests and paths are retained.
The final command's `cevcapsule` spelling is retained from the supplied excerpt;
the owner reports a successful DevCapsule launch and supplies its output. This
record does not infer that an executable named `cevcapsule` exists.

### Initial Run And Serial Recovery

```text
devcapsule project run
devcapsule: Local resolution is stale (manifest, platform-lock); run 'devcapsule project config resolve'.

devcapsule project config resolve
devcapsule: Checkout authorization 'host-browser' is stale; review the current recommendation and run 'devcapsule project config authorize host-browser true'.

devcapsule project config authorize host-browser true
Authorized host-browser for this checkout: true
Recommendation: Open HTTP(S) links from the capsule in the physical host's default browser through the URL-only broker.
Recommendation digest: aedbe4b8b32c5901a487f804569ea9c4c0c01e71bfc64353ae3a47aceb04d0a2
Checkout input: /home/costin/.config/devcapsule/projects/https%3A%2F%2Fgithub.com%2Fccozianu/devcapsule/checkouts/dev-capsule-2.checkout.toml
This authorization applies only to the exact recorded value, image identity when local, and current lock.
Run 'devcapsule project config resolve' before materialization or launch.

devcapsule project config resolve
devcapsule: The checkout's base-image authorization is stale for the current lock; review the lock and run 'devcapsule project config authorize base-image docker.io/mycodespaceai/devcapsule-base@sha256:76a07cb9e72158f810b32598eb05f9a375f8e4748b80b6eac04c403798d39a45'.

devcapsule version
DevCapsule v0.2.12 (package 0.2.12)
Source repository: https://github.com/ccozianu/devcapsule
Source revision: 2916c4c09aee13eeed85276c1a32889515ce7b19
Source URL: https://github.com/ccozianu/devcapsule/commit/2916c4c09aee13eeed85276c1a32889515ce7b19

devcapsule project config resolve
devcapsule: The checkout's base-image authorization is stale for the current lock; review the lock and run 'devcapsule project config authorize base-image docker.io/mycodespaceai/devcapsule-base@sha256:76a07cb9e72158f810b32598eb05f9a375f8e4748b80b6eac04c403798d39a45'.

devcapsule project config authorize base-image docker.io/mycodespaceai/devcapsule-base@sha256:76a07cb9e72158f810b32598eb05f9a375f8e4748b80b6eac04c403798d39a45
devcapsule: Authorization 'base-image' accepts its recommended value 'docker.io/mycodespaceai/devcapsule-base@sha256:8837edd36720763796ab9fe1dbeb66f1aa7ca2db0dabc8d73a58716440f42f7c', or the keywords 'default'/'none'; got 'docker.io/mycodespaceai/devcapsule-base@sha256:76a07cb9e72158f810b32598eb05f9a375f8e4748b80b6eac04c403798d39a45'. Any other value requires distinct reviewed metadata.
```

### Remembered Workaround

The owner remembered that the `default` keyword accepts the lock's recommendation:

```text
devcapsule project config authorize base-image default
Authorized base-image for this checkout: v0.2.12-rc5 — docker.io/mycodespaceai/devcapsule-base@sha256:8837edd36720763796ab9fe1dbeb66f1aa7ca2db0dabc8d73a58716440f42f7c
Recommendation: Execute DevCapsule v0.2.12-rc5 at the exact registry digest selected by the platform lock.
Recommendation digest: 871d4913f3fb1b43a9da15501241af304b8d45b1c9784f368557f883f842430e
Checkout input: /home/costin/.config/devcapsule/projects/https%3A%2F%2Fgithub.com%2Fccozianu/devcapsule/checkouts/dev-capsule-2.checkout.toml
This authorization applies only to the exact recorded value, image identity when local, and current lock.

devcapsule project config resolve
Resolved /home/costin/.config/devcapsule/projects/https%3A%2F%2Fgithub.com%2Fccozianu/devcapsule/checkouts/dev-capsule-2.resolved.toml from devcapsule.linux-amd64.lock
```

### Display Change And Recovery

The owner reports that launch was then possible, but the prior host-X11 setup
was no longer effective and a Docker image build added delay. The intervening
launch/build output is absent from the excerpt. The supplied recovery is:

```text
devcapsule project config authorize host-x11 true
Authorized host-x11 for this checkout: true
Recommendation: Run the IDE on the host's X session instead of the capsule's contained display, handing the capsule your full X session credential: keystroke capture across the session, window capture, input injection, and clipboard access. The session-credential boundary test is waived for such runs.
Recommendation digest: 0f0674b914118a34d2098e6aec24f9838bb71e7a04c4599bf0a4020fbfd850eb
Checkout input: /home/costin/.config/devcapsule/projects/https%3A%2F%2Fgithub.com%2Fccozianu/devcapsule/checkouts/dev-capsule-2.checkout.toml
This authorization applies only to the exact recorded value, image identity when local, and current lock.
Run 'devcapsule project config resolve' before materialization or launch.

devcapsule project config resolve
Resolved /home/costin/.config/devcapsule/projects/https%3A%2F%2Fgithub.com%2Fccozianu/devcapsule/checkouts/dev-capsule-2.resolved.toml from devcapsule.linux-amd64.lock

cevcapsule project run
Reused canonical environment: devcapsule-local-pycharm:4356c1fcfe2b762aad9c
Display: host X11 passthrough, authorized by 'host-x11'; the capsule receives your full X session credential and the boundary test is waived for this run.
Recursive E2E readiness: enabled for this DevCapsule launch.
```

This is a recorded workaround for this incident, not an instruction to authorize
host-browser or host-X11 for other users. Those choices remain explicit.

## Expected Behavior And Verification Target

The upgrade path must be understandable as a complete transition from a working
checkout to a working checkout. Its checks must not prescribe mutually
incompatible commands or require remembered implementation vocabulary.

Before closing this bug, verify an upgrade with an existing checkout and saved
authorizations, including a changed lock and previously selected published base:

1. Every suggested recovery command is accepted in the very state that produced
   it and advances recovery toward a runnable checkout. In particular, a stale
   base selection must not elicit a command rejected as a non-recommended digest.
2. The user can discover the current selection, new recommendation, and required
   decisions together, rather than learning one stale authorization per failed
   attempt. The exact interaction belongs to the existing upgrade design work.
3. Existing display intent is preserved where its authorization remains valid;
   where a changed host boundary needs renewed consent, explain the transition
   and available choices before launch. Do not silently grant host-X11 access
   to make migration appear successful.
4. Any required image build and display change are explained as consequences of
   the selected transition. An image build can be legitimate; this evidence
   does not establish that the observed build was unnecessary.
5. Validate the full command sequence and eventual launch, not only isolated
   message assertions. Include unchanged-project/tool-only upgrade coverage
   separately from changed-lock recovery, under `R-COMPAT-001`.

Use historical project/configuration fixtures for the deterministic recovery
sequence, followed by owner validation of the actual upgrade/display experience.
Passing newly authored tests alone does not establish that the interaction is
satisfactory. Closing requires evidence for both the invalid remedy and the
remaining upgrade/display experience, or explicit owner-approved splitting into
linked, still-open records.

## Implementation Evidence And Remaining Uncertainty

The preceding code inspection used the v0.2.12 release source:

- `ProjectRunCommand.run` in `commands/project.py` checks source digests and
  refuses a stale resolution with `config resolve` as its remedy.
- `stale_resolution_inputs` in `project_configuration.py` compares manifest,
  platform-lock and checkout-input digests; it does not include tool version.
- `authorized_base_selection` checks the saved authorization against the entire
  current lock digest. On mismatch its suggested refresh uses the **previously
  authorized reference**, even when the current lock recommends another digest.
- The authorize command rejects a different published digest without distinct
  reviewed metadata. `default` resolves to the current recommendation. These
  two policies explain the contradictory base-image guidance in the logs.

The host-browser stale refusal is observed; the old and new recommendation
contents are unavailable, so whether renewed consent was warranted is not yet
established. Likewise, the record does not establish that base-image authorization
deleted or invalidated an explicit `host-x11` record. Earlier display defaults,
authorization representation, and the v0.2.12 contained-display transition must
be examined before attributing that causal mechanism. No build timings are known.

## Routing And Related Work

`maintenance` owns the fix because no open implementation workstream owns the
overall configuration-upgrade path. Project-management retains the cross-cutting
design and sequencing decisions. Filing here does not switch the current
checkout to maintenance or reopen component-catalog's frozen implementation scope.

- [Recommended-base choice and override visibility](../../wip/2026-08-09-project-management/intake/2026-09-14-contained-display-config-offers-the-recommended-base.md).
- [Listing by the project's configured schema](../../wip/2026-08-09-project-management/intake/2026-09-13-contained-display-config-list-renders-by-configured-schema.md).
- [Upgrade experience as a V1 feature](../../wip/2026-08-09-project-management/intake/2026-09-03-component-catalog-upgrade-experience-as-a-v1-feature.md).
- [Init/regenerate versus config semantics](https://github.com/mycodespace-ai/devcapsule/blob/9443bdc69d15df7514e13e8e3ded2f3a8720dd51/engineering-docs/wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-init-regenerate-versus-config-semantics.md).
- [Earlier Hoare-standard remediation directive](../../archive/2026-08-06-recursive-e2e/CURRENT-STATUS.md) (directed item 3, deferred beyond v027).
- [Client-upgrade compatibility requirement](../../requirements/devcapsule/r-compat-001-client-upgrades-require-no-user-action.md).
- [Earlier closed resolution-refusal bug](2026-09-03-resolution-refusal-names-only-the-last-base-and-no-remedy.md): related pattern, different failure; its recorded closure is not reversed by this incident.

## Fix Status

2026-09-20: implemented on `ws-maintenance/triage`, selected by the owner.
The [implementation contract and test map](../../wip/2026-09-18-maintenance/upgrade-recovery-contract.md)
record the entrypoint-to-launch invariants, historical fixture provenance and
acceptance boundary.

- Inspection and resolution share one read-only assessment. All pending
  authorizations appear together, with saved answers and current recommendations.
- Stale published-base recovery offers the accepted `default` choice. Local
  overrides remain visible and can be renewed by immutable identity, subject to
  inspection. Commands select and shell-quote the checkout path.
- Explicit grants and denials survive recovery. Regeneration cannot silently
  replace a denial with a recommendation; all selected vendor acquisitions use
  the same authorization gate.
- Run validates configuration and run-once options before materialization.
  Display selection and alternatives are explained before building. Legacy
  images refuse an explicit X11 denial instead of exposing the host session.
  A stale resolution cannot revive a removed host permission with `--force`.
- The full local gate passed: mypy, 704 tests, source smoke, PEX build and nine
  packaged-executable tests. The 71 new unit cases include complete CLI recovery
  journeys from v0.2.11 fixtures and separate unchanged-project coverage.
  The new assessment and authorization-review helpers have 100% statement and
  branch coverage.

`fixed` records implementation evidence, not closure or release. Owner validation
of the actual upgrade/display experience and PR integration remain outstanding.
No actual host upgrade or GUI acceptance run was performed here. Reopen after
eventual closure if a supported upgrade again rejects its prescribed remedy or
changes effective display behavior without the migration explanation.

The owner's subsequent full-configuration audit found broader composition
failures, including a lower launcher path that can override a sudo denial.
They are recorded in the linked
[configuration lifecycle defect](2026-09-20-configuration-contract-not-enforced-across-boundaries.md).
The recovery module's complete local coverage must not be read as proof of
the entire configuration-to-execution contract.

2026-09-20 continuation: the broader contract refactor is implemented. All ten
composition counterexamples now pass, with 128 additional invariant cases and
a full gate of 877 tests plus nine packaged tests. The linked correctness
argument covers document admission, edit preservation, initialization provenance,
scoped/legacy fingerprints, current permissions/bindings under force and the
actual lower launcher. The owner's serialized-access precondition is explicit.
Host acceptance and PR integration remain outstanding.

2026-09-21 acceptance update: the owner reports running successfully with these
fixes and requests branch delivery for GitHub merge. The isolated graphical
0.2.12-configuration successor also passed and exited normally. Earlier pending
live-use acceptance notes are superseded by that report; exact host configuration
bytes remain unavailable. Status remains `fixed` pending PR integration.
