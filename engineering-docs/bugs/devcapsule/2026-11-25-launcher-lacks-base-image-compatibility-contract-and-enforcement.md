---
status: confirmed
severity: untriaged
target: 0.3.1
owner: maintenance
opened: 2026-11-25
requirements: [R-COMPAT-001, R-RUNTIME-001, R-CONSOLE-001]
---

# `devcapsule` lacks a documented and enforced base-image compatibility contract when running projects with older bases

## Symptom and expected behavior

A newer `devcapsule` executable can carry features developed and tested against
a newer base image recipe than the base image available in a project it tries
to launch (via an older project lock, pinned base, explicit/local base
selection, or cached materialized image). Today, launching against an older or
otherwise mismatched base image has no universal compatibility enforcement and
no single documented runtime contract between `devcapsule` and the base image.

Expected:

1. **Documented contract (owner direction, 2026-11-25):** Document the explicit
   contract between the `devcapsule` utility and the base image for running
   `devcapsule` (under `engineering-docs/specifications/devcapsule/`, linked in
   `index.md`), covering required base interfaces (`family@recipe`, base
   services, supervisor/runtime/console interfaces), what may degrade gracefully
   vs what must refuse, and how new launcher features advance and test the
   contract.
2. **Enforced compatibility check:** State and enforce the mandatory
   launcher-to-base contract before launching an incompatible capsule across
   pinned bases, old project locks, explicit/local base selections, and cached
   materialized environments, failing with an actionable message naming
   required vs found `family@recipe`/capabilities and remediation.
3. **Explicit degradation boundary:** Distinguish mandatory launcher-to-base
   requirements from intentional optional degradation (such as `D-0017` console
   fallback on pre-recipe-11 bases, or resolve against `D-0017` and
   `R-CONSOLE-001` if console presence becomes mandatory). Verify that changed
   console or runtime third-party dependencies advance and enforce the base
   contract rather than failing only at runtime import.

## Environment and evidence

Inspected on `presentations` at revision `c5549f720aec2e94cdee31fb39c87b9cc5388d30`
(matching local PEX `version --json`) and re-verified on `ws-project-management/coordination`:

- `devcapsule-src/devcapsule/environment_realization.py` (`realize_environment`):
  calls `validate_base_image` before materialization.
- `devcapsule-src/devcapsule/materialization.py` (`validate_base_image`):
  checks OS/architecture against the lock's `platform`, checks metadata-v1
  base labels (`MANAGED_LABEL`, `METADATA_VERSION_LABEL`, `IMAGE_KIND_LABEL`),
  and checks `expected_identity` when supplied. It does not compare minimum
  base recipes or declared launcher requirements.
- `devcapsule-src/devcapsule/images/contract.py`: `BaseContract.accepts`
  defines family and minimum-recipe comparison, but definition alone is not
  wired into launch refusal. `web_console_availability` checks
  `devcapsule.base.webconsole` and `recipe >= 11` (`WEBCONSOLE_RECIPE`) and
  returns `available=False` rather than rejecting the base.
- `devcapsule-src/devcapsule/commands/project.py` (`prepare_display`): computes
  `web_console_availability(base.labels)` and continues launching; only a base
  without contained display and without `host-x11` consent raises
  `DecisionPending`.
- `devcapsule-src/devcapsule/launch/pycharm/_launcher.py` (`web_console_notice`):
  prints a notice that the capsule runs without the console on bases older than
  recipe 11.
- `devcapsule-src/devcapsule/container_runtime/console.py`: checks interpreter
  presence (`/opt/devcapsule-webconsole/venv/bin/python`) under `D-0017` and
  relies on `WEBCONSOLE_RECIPE` by construction; it does not verify third-party
  dependency versions at runtime.

Five existing unit tests confirm this current behavior without a real
incompatible-base launch:

- `tests/unit/devcapsule/test_materialization.py::test_validate_base_image_accepts_matching_managed_base`
- `tests/unit/devcapsule/test_materialization.py::test_validate_base_image_rejects_identity_mismatch`
- `tests/test_base_contract.py::test_web_console_availability_needs_the_label_and_recipe_11`
- `tests/test_pycharm.py::test_web_console_notice_names_the_base_the_command_and_the_guide`
- `tests/test_pycharm.py::test_no_web_console_is_planned_on_a_base_without_one`

## Origin and intake link

Filed by `project-management` on 2026-11-25 acknowledging
`2026-11-17-presentations-launcher-base-requirements.md`, assigned to
`maintenance` with target `0.3.1` and the owner's 2026-11-25 requirement to
document the utility-to-base-image running contract.

## Verification target and close criteria

1. A permanent specification documents the `devcapsule` utility-to-base-image
   running contract (mandatory invariants, optional degradation rules, and
   recipe-bump obligations) and is listed in `index.md`.
2. Incompatible base images (older recipes, unmet mandatory capabilities,
   explicit/local base overrides, or cached environments) are rejected with
   clear diagnostics naming required vs found base contract and remedy, while
   compatible bases and explicitly allowed degradations continue to launch.
3. Targeted unit and integration/real-boundary tests prove both rejection of
   incompatible bases and acceptance of compatible bases.
