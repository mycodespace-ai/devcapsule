# Pair Review: current CLI documentation after PR52

Implementor: Codex, GPT-6. Reviewer: Antigravity, exact `gemini-4-hydrogen`.
The owner merged implementation PR52 and requested a thorough documentation audit.
This is a documentation-only follow-up, targeting `release-0.3.1` from `3a5aea22`.
The broader syntax migration in the work order remains AFTER 0.3.1. Do not document
proposed flattened commands as implemented. No product choice is pending.

## Checkout and reading order

Work only in `/home/devcapsule/worktrees/maintenance-review`, on
`ws-maintenance/cli-docs-review`, with its own `devcapsule-src/.venv`.
Read README.md, DEVELOPING.md, AGENTS.md, WORKFLOW.md topic 9.11 and WORKFLOW-LOCAL.md
(validation, test/host-input rules, GitHub, authorship, Pair Review), then this
brief and the top current section of maintenance status. Historical status text
need not be reread. Inspect `git diff upstream/release-0.3.1..HEAD -- '*.md'`.
Read the changed documents and the actual command adapters they describe.
The brief is your only conversational context. Main differs from release in its
workflow version stamp only; retain the release baseline.

## Scope and review

Review correctness, clarity, then coverage. Fix documentation findings directly.
The edits cover the CLI reference, console links, installed recording kits and
migration, bootstrap/wrapper guides, bootstrap specification, upcoming changelog,
and obsolete contributor README/configuration examples. Verify concrete commands,
argument placement, path/URL semantics, token fallback, kit preservation and refresh,
current-versus-future grammar, and RC3-versus-upcoming candidate availability.
Check code in `commands/instance.py`, `commands/project.py`, `commands/bootstrap.py`,
`workflow_bootstrap.py`, `presentation_authoring.py` and current installed skill docs.
Check changed Markdown links and examples. Source README historical configuration
claims were corrected, not merely renamed. Look for other current guides that
still teach the removed commands; preserve historical evidence and dated decisions.

No production code or tests change. Do not add mirror tests for prose. If a concrete
code defect appears, report it without widening this documentation slice.
For any new/changed tests (none expected), verify Unit Tests rules 1–4 and Host
Inputs rules 1–6, naming non-bug failure preconditions. Do not change legacy tests.

## Validation

From your own devcapsule-src directory, use your own environment and scratch:

    DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS=--basetemp=/home/devcapsule/skill-validation/pytest-antigravity-docs .venv/bin/python -m nox -s build
    .venv/bin/python -m nox -s docs-contract

Run tests serially. The inherited full gate has three local fixture failures:
mount-backed home scratch in unmountable-staging, and two gid-zero recursive
fixtures. No exclusion or waiver is authorized. Report exact results; do not
claim a full pass. The implementor independently checks packaging/console if
build stops. Reviewer need not repeat unaffected packaging or console phases.
Docs contract requires the website checkout; if absent, report it as skipped
and use the implementor's independently recorded website check as separate evidence.
Use harmless help commands outside project/capsule context and scratch fixtures
only. Do not execute real launches, configuration writes on this project, network
component acquisition, E2E recordings, or browser installation.

## Delivery

Preserve `Costin Cozianu <ccozianu@gmail.com>` as author (verify `git var`).
Add `Co-authored-by: Gemini 4 Hydrogen Antigravity <noreply@google.com>`.
Use canonical SSH remote `upstream` for fetch/push. Activate gh in EVERY shell:

    source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Verify `gh auth status -h github.com` once. Use `--repo mycodespace-ai/devcapsule`
on every PR command. Find the implementation PR by head `ws-maintenance/cli-docs`.
Commit fixes, push `ws-maintenance/cli-docs-review`, and open a review PR against
`ws-maintenance/cli-docs`. Give findings, locations, fixes, evidence, considered
and left-alone issues, proposals not implemented, and validation counts/limits.
If no change is needed, report inspections and verdict and open no empty PR.

Do not edit status/list/intake/disposition/evidence/work-order records, `.devcapsule`,
`.idea`, workflow rules, website gitlink, or another checkout. No coordination
commands, merges, rebases, force pushes, tags, releases, images, capsules,
subagents or workstream changes. Stop on a real blocker.
Final line: the review PR URL or `NO PR`.
