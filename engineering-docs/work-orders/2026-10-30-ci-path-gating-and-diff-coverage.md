# Work Order: CI Path Gating And Advisory Diff Coverage

Origin: product-owner draft composed outside the capsule, reviewed against
the repository on 2026-10-30; owner decisions 1B and 2B the same day.
Status: implemented and Pair Reviewed in PR #312/#314; local and hosted
acceptance passed; merged into release-0.3.0 through #312. Required-check
configuration and propagation to main remain open.
Evidence: [maintenance acceptance record](../wip/2026-09-18-maintenance/evidence/2026-10-30-ci-gating/acceptance.md).
Coordination owner: `project-management`. Implementation owner: `maintenance`.
Target: **0.3.0**. This is repository engineering work, not an adopter feature.
No new workstream is opened and no 0.4.0 product commitment is made.

## Outcome

Avoid running the Python unit suite for changes that cannot affect it, without
letting a failed routing step or an unexpectedly skipped check produce a green
required check. When Python implementation changes, show uncovered changed
executable lines through native GitHub annotations, a job summary and downloadable
reports, without an external coverage service.

Coverage is **advisory** in 0.3.0. Low coverage does not block a pull request.
Failed tests and failures to compute or publish the required reports still fail
their checks. A valid diff with no measured executable lines is explicitly
reported as not applicable, not as proof of complete coverage.

## Binding decisions

- The owner selected **1B: report coverage without blocking initially**. Do not
  introduce `--fail-under=85`, a coverage failure status or an equivalent hidden
  threshold. A future blocking threshold requires a new owner decision.
- The owner selected **2B: defer parallel execution beyond 0.3.0**. Keep serial
  tests. Do not add `pytest-xdist`, global worker options, or a parallelism trial
  to this order. No later release is assigned to that deferred work.
- Preserve Python 3.12, branch coverage and the existing test selection,
  including the integration/E2E exclusions. Do not force `core = "sysmon"`:
  its branch measurement requires Python 3.14. Remove the draft's unmeasured
  less-than-5-percent overhead promise. No interpreter upgrade is authorized.
- Maintenance implements this during the 0.3.0 cycle under the repository's
  release workflow. Project-management records and delivers the assignment;
  it does not edit maintenance's records or switch workstreams to implement it.
- This order does not decide the pending project-wide testing-policy
  reconciliation, add Docker to hosted CI, or change the local build gate's tiers.

## Repository evidence used

Read against mainline `b026936b2d476b27d7d81c19670c5e3dc7915cdb`:

- [Tests workflow](../../.github/workflows/tests.yml): Python 3.12 on
  `ubuntu-24.04`, serial unit tests with coverage, PRs into `main` and
  `release-*`, pushes to main and manual checkout-ref runs. XML/HTML reports
  and a summary already exist; main pushes publish a badge separately.
- [Runtime configuration](../../devcapsule-src/pyproject.toml) and
  [compiled dependencies](../../devcapsule-src/dev-requirements.txt): package
  `devcapsule-src/devcapsule`, existing pytest/pytest-cov and branch coverage.
  There is no root `src/` package or root `pyproject.toml` to modify.
- [Web-console configuration](../../devcapsule-webconsole/pyproject.toml):
  a separate Python distribution and environment. Its existing validation is
  specified by [local workflow](../../WORKFLOW-LOCAL.md); the runtime coverage
  report does not measure that distribution.
- [Website workflow](../../.github/workflows/website.yml) and
  [website script](../../scripts/website.sh): website CI is currently manually
  dispatched. Builds need the pinned website submodule, Node, npm dependencies
  and the documentation refs. README landing content and engineering journal
  content are site inputs. Adding a conditional PR website build is new
  verification, not merely skipping an existing PR job.
- [Local workflow](../../WORKFLOW-LOCAL.md),
  [developer brief](../../DEVELOPING.md) and
  [testing-policy intake](../wip/2026-08-09-project-management/intake/2026-10-10-capsule-webconsole-reconcile-testing-approach-with-practice.md):
  the local build gate is broader than hosted unit testing. This order does
  not silently reconcile that policy difference.
- [Ast-grep proposal](2026-10-29-ast-grep-guardrails.md): a separate draft, not
  authorization to implement its rules here. Route its configuration inputs
  appropriately if present when this order is executed.

Reinspect the actual release branch before implementation; this evidence is
not a claim that its files are identical to mainline.

## Deliverables and completion conditions

### 1. Path routing with a reliable aggregate check

Use `dorny/paths-filter` v3, pinned according to the repository's action policy,
to classify PR changes. Derive the filter table from actual dependencies:
runtime source, tests, packaged assets, build/configuration files, pinned
dependencies, scripts, relevant submodule pointers and workflow definitions.
Account for `devcapsule-webconsole/` explicitly; never imply that runtime
coverage establishes coverage of the console. Preserve its separate existing
validation contract. Do not exempt all Markdown or all `engineering-docs/`.

Changes only to workstream status, planning records or other proven non-input
documents skip the heavy jobs. Website inputs run website verification;
runtime inputs run the existing serial unit suite. Unknown or ambiguous inputs
take the conservative route. Workflow changes exercise the affected jobs.
Keep full applicable verification on main pushes and manual runs, including
the existing explicit checkout-ref behavior. Preserve PR support for release
branches, cancellation behavior, coverage artifacts and main-only badge output.

Add a conditional website verification job with the setup already required by
the website workflow, including its tests and build/check command. It must not
deploy, publish a site or change the pinned website implementation.

Add an always-evaluated `ci-gate`. It succeeds only when routing succeeded with
valid outputs and each applicable verification job succeeded. Accept a skipped
job only when the validated route says it was unnecessary. Failure, cancellation,
missing outputs and unexpectedly skipped applicable jobs cannot yield success.

Inspect actual required-check settings before changing job names. Establish the
new check on real PRs, then coordinate the owner's required-check migration;
do not remove unrelated required checks or assume editing YAML changes branch
protection. Preserve any configured merge-queue requirements. Record the final
settings and evidence, or the exact outstanding owner action.

### 2. Serial diff coverage and native GitHub reporting

Add `diff-cover` to the runtime's development dependencies and regenerate the
existing pinned dependency file by the project's normal procedure. Preserve
pytest-cov and coverage configuration; add or adjust dependencies only where
needed by the selected compatible versions. Do not replace existing pytest
options with the external draft's example.

For PRs whose runtime tests ran, compute changed-line coverage from their XML
report against the actual PR base, including a release-branch base. Define the
tested revision and diff range explicitly, fetch enough history to resolve the
merge base, and map report paths and line coordinates to the PR correctly.
Use the pinned diff-cover version's supported report flags and JSON schema.
Run without a failing coverage threshold. This measures changed executable
line coverage, not changed-branch coverage or all possible Python code.

Produce a Markdown summary and JSON report, upload the reports with the existing
coverage artifacts, and use a small standard-library Python bridge to emit
native warning annotations for contiguous uncovered changed-line ranges.
Use repository-relative paths, escape workflow-command properties and messages,
validate the report schema, and bound inline output to GitHub's supported
annotation limits. Preserve the complete report when annotations are truncated.
Missing or malformed expected reports and tool errors must fail visibly; do not
mask them with `|| true` or treat them as zero uncovered lines. Retain useful
diagnostics on failed runs without hiding the original test failure.

Verify the desired Files changed presentation on a real PR. The annotation
command alone is not evidence that GitHub attached it to the intended diff.
If that presentation cannot be achieved with the native mechanism, bring the
observed limitation to the owner before changing the acceptance criterion.

### 3. Local instructions and generated-file hygiene

Document the implemented serial commands, working directory, environment and
base-ref selection in project-owned validation documentation and
`WORKFLOW-LOCAL.md` as appropriate. Do not alter the generic `WORKFLOW.md`
protocol or duplicate the full commands in `AGENTS.md`.

The intended local shape, from `devcapsule-src`, is:

```sh
.venv/bin/python -m pytest tests/ --cov-report=xml:coverage.xml
.venv/bin/diff-cover coverage.xml --compare-branch=origin/main
```

Use the real target branch when it differs from main. Preserve the project's
existing pytest options. Final instructions must match the selected tools and
validated invocation. Extend the appropriate ignore file for coverage data and
diff reports; preserve existing coverage.xml/htmlcov ignores and do not hide
authored coverage configuration with an overbroad pattern. Update `index.md`
if permanent documentation is added or moved.

## Acceptance evidence

Maintenance records the implementation commits, commands, results and hosted
run/PR links. Demonstrate these cases with focused checks and representative
hosted runs rather than introducing a new broad test program:

| Case | Required result |
| --- | --- |
| Planning/status-only PR | Heavy jobs legitimately skipped; aggregate green. |
| Website-input PR | Website verification runs, including README/journal inputs; irrelevant Python tests skip. |
| Runtime or relevant build/configuration PR | Existing serial Python suite runs; other applicable checks run. |
| Routing failure or applicable job failure/cancellation/unexpected skip | Aggregate cannot succeed. |
| Valid report with uncovered changed lines, including below 85% | Warnings and complete reports; coverage alone does not fail the check. |
| No measured executable lines | Explicit not-applicable result, without fabricated coverage claims. |
| Missing/malformed report or diff/base-resolution failure | Reporting fails visibly. |
| Changed lines in a nested package path | Native annotations attach to the correct PR file and lines. |
| Release-base PR, main push and manual checkout-ref run | Intended revisions and existing behavior are preserved. |

Run the required local checks under `WORKFLOW-LOCAL.md` for the implementation.
Validate both paths through the aggregate and the report bridge with focused
tests; do not rely only on a happy-path green PR. Show the required-check
migration is complete before claiming branch-protection acceptance. Maintenance
records 0.3.0 integration and release inclusion through the release procedure.
Creating this work order is not implementation completion.

## Execution choices and stopping points

Maintenance chooses exact filter globs, compatible pinned dependency versions,
job structure and the bridge's location. Preserve existing validation scope;
raise any necessary expansion of hosted suites, Python-version change, coverage
policy change, external service or broader website work with the owner. Normal
implementation choices within this contract need no repeated permission.

Parallel execution and a blocking coverage threshold remain outside this order.
The pending testing-policy reconciliation stays pending. A technical inability
to meet a required outcome must be reported with evidence and options rather
than silently weakening the outcome.

Technical references checked during review:
[coverage core support](https://coverage.readthedocs.io/en/latest/config.html#run-core),
[diff-cover reporting and diff behavior](https://github.com/Bachmann1234/diff_cover),
[GitHub warning annotations](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#setting-a-warning-message).
