# Schedule explicit launcher-to-base requirement enforcement

From: presentations
To: project-management
Date: 2026-11-17

## Owner request

The owner asked whether devcapsule.pex refuses to run when the base image does not meet its requirements.
If that could not be confirmed, the owner explicitly directed a message to project-management to schedule work.
This inspection cannot confirm a universal refusal guarantee. Please acknowledge and schedule the compatibility work.
Priority, implementing workstream, and release target are for project-management to decide.

## Evidence

Inspected source c5549f720aec2e94cdee31fb39c87b9cc5388d30, matching the local PEX's version --json identity.
The current branch adds documentation only after that revision.
No image was built or pulled, and no capsule was launched.

- devcapsule-src/devcapsule/environment_realization.py: realize_environment calls validate_base_image before materialization.
- devcapsule-src/devcapsule/materialization.py: validate_base_image checks OS/architecture, metadata-v1 managed-base labels, and expected image identity when supplied. It does not itself compare recipe minimums or declared launcher requirements.
- devcapsule-src/devcapsule/images/contract.py: web_console_availability requires the console label and recipe 11 or later. It returns unavailable rather than rejecting the base. BaseContract.accepts defines a family/recipe comparison, but definition alone is not launch enforcement.
- devcapsule-src/devcapsule/commands/project.py: prepare_display computes that availability and continues after selecting the display transport. Other specific requirements, such as usable display with consent, can still refuse launch.
- devcapsule-src/devcapsule/launch/pycharm/_launcher.py: web_console_notice explicitly says the capsule runs without the console on an old base.
- devcapsule-src/devcapsule/container_runtime/console.py: the runtime checks interpreter presence; an absent interpreter emits a degradation notice. It does not verify console dependency versions.
- The accepted D-0017 decision delivers console application code in the PEX, installed on the base interpreter. The base supplies dependencies and a fallback package. A console/CLI syntax change alone does not require a base rebuild. My earlier review claim that console code was base-only was incorrect.

Five existing tests passed in this inspection:
- tests/unit/devcapsule/test_materialization.py::test_validate_base_image_accepts_matching_managed_base
- tests/unit/devcapsule/test_materialization.py::test_validate_base_image_rejects_identity_mismatch
- tests/test_base_contract.py::test_web_console_availability_needs_the_label_and_recipe_11
- tests/test_pycharm.py::test_web_console_notice_names_the_base_the_command_and_the_guide
- tests/test_pycharm.py::test_no_web_console_is_planned_on_a_base_without_one

These are unit evidence plus a traced launch path, not a real incompatible-base launch.
The non-refusal for a missing console is intentional existing behavior under D-0017, not merely a missing test.

## What accepting this item means

Schedule work to state and enforce the shipped PEX/runtime/console's mandatory base contract before launching an incompatible capsule.
Cover pinned bases, old project locks, explicit/local base selections, and cached materialized environments as applicable.
Report required versus found capabilities or recipe/family with a concrete remedy on refusal.
Distinguish mandatory requirements from deliberately optional degradation. If the console is now mandatory, resolve that change against D-0017 and R-CONSOLE-001 with the owner.
Verify that a changed console dependency requirement advances and enforces the base contract; do not rely only on comments or labels without a defined guarantee.
Add targeted rejection and compatible-base acceptance evidence through the real launcher boundary.
No implementation change or release gate is authorized by this investigation alone.
