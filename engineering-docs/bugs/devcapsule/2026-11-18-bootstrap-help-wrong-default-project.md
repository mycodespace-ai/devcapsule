---
status: confirmed
severity: minor
target: none
owner: maintenance
opened: 2026-11-18
requirements: [R-DOCS-002]
---

# Bootstrap help names an unused project-directory default

`devcapsule bootstrap --help` and `devcapsule bootstrap project --help`
describe `--project` as defaulting to `PROJECT_PATH` or the current directory.
The adapter actually uses the explicit path or `Path(".")`.
An ambient `PROJECT_PATH` does not redirect bootstrap.

Antigravity `gemini-4-hydrogen` found the inconsistency while reviewing
[PR #55](https://github.com/mycodespace-ai/devcapsule/pull/55), at `bab6ec85`.
The evidence is `_add_bootstrap_options` and `_bootstrap` in
`devcapsule-src/devcapsule/commands/bootstrap.py`, plus their printed help.
The existing bootstrap specification correctly states the current-directory behavior.

Correct the help text when the CLI help slice resumes. Preserve the directory
selection behavior. This documentation-only follow-up does not change the adapter.
Verification should compare both help forms with bootstrap in a scratch current
directory while `PROJECT_PATH` names another directory.
