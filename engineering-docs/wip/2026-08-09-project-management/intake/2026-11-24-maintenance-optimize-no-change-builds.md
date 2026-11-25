# Optimize Local No-Change and Non-Input Builds (`nox -s build` / `WORKFLOW-LOCAL.md`)

**Sender:** `maintenance` (`ws-maintenance/investigating-git-links`)
**Date:** 2026-11-24

## What Is Handed Over

Prioritize and assign optimization of local builds (`nox -s build` / `nox -s tests`) and the local PR gate rule in `WORKFLOW-LOCAL.md` (*GitHub Integration* rule 4 and *Validation Commands*) so changes that touch no Python/console/test inputs (such as blog entries, records, or `.devcapsule/`-only updates) do not run the full multi-minute unit suite and PEX build locally.

## Why It Belongs to `project-management`

- `project-management` owns project-wide priorities, sequencing, and coordination across `maintenance` (local gate / `noxfile.py`) and `workflow-improvements` (`WORKFLOW-LOCAL.md` / `WORKFLOW.md` rule changes).
- `WORKFLOW-LOCAL.md` (*GitHub Integration* rule 4, owner direction 2026-11-06) currently requires running the unit session before opening or updating any pull request, explicitly stating *"A change to records alone is not an exception."*

## Evidence and Documents

- [2026-11-10-markdown-only-changes-run-the-python-unit-suite.md](engineering-docs/bugs/devcapsule/2026-11-10-markdown-only-changes-run-the-python-unit-suite.md): hosted CI routing via `.github/ci-python-inputs.yml` is already implemented, while close criterion 2 remains open (*"The local gate still runs everything; close criterion 2 is open"* / *"The local workflow says what to run for such a change, and an agent following it does not run the unit suite for it"*).
- In today's session (2026-11-24), both a two-file `.devcapsule/` PR (`#70`) and a three-file blog draft PR (`#71`) hit the full local `nox -s build` requirement (~2+ minutes each, creating and populating `.nox/build` and `.nox/webconsole` virtualenvs and building `dist/devcapsule-local.pex` even when no Python or webconsole file changed).
- Even when Python files do not change, running `nox -s docs-contract` (for docs/blog PRs) or skipping unchanged `nox` sessions / test suites based on `.github/ci-python-inputs.yml` would eliminate wasted build time and agent wait time.

## What Accepting It Would Mean

`project-management` schedules and routes the follow-up slice (to `maintenance` and/or `workflow-improvements`) to:
1. Define path-aware / no-change fast paths in the local gate (`noxfile.py`) aligned with `.github/ci-python-inputs.yml` and `docs-contract`.
2. Update `WORKFLOW-LOCAL.md` (*GitHub Integration* rule 4 and *Validation Commands*) so agents skip unaffected suites on non-input changes (such as blog-only or records-only PRs) and close criterion 2 of the 2026-11-10 bug record.
