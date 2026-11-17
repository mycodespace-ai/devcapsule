# Pair Review: finish RC4 presentation CLI rewiring in PR52

Implementor: Codex, GPT-6. Reviewer: Antigravity, exact `gemini-4-hydrogen`.
The owner answered the open choices and directed continued implementation.
This second bounded slice extends the still-open PR52 against `release-0.3.1`.
PR53's initial help/kit fixes are already merged; review the new changes since
`8540d073` and their interaction with that initial slice. Do not reopen the
accepted staging fix without a concrete regression.

## Checkout and reading order

Work only in `/home/devcapsule/worktrees/maintenance-review`, branch
`ws-maintenance/cli-syntax-review`, with your own installed `devcapsule-src/.venv`.
Read README.md, DEVELOPING.md, AGENTS.md, WORKFLOW.md topic 9.11 and WORKFLOW-LOCAL.md
(test conventions, host inputs, validation, GitHub and Pair Review rules), then
`engineering-docs/work-orders/2026-11-17-cli-syntax-and-discovery.md`,
`engineering-docs/wip/2026-09-18-maintenance/2026-11-17-cli-syntax-implementation.md`,
and only current CLI sections at the TOP of maintenance status. The brief is your
only conversational context; no need to read thousands of historical status lines.

Inspect `git diff 8540d073..HEAD` and the actual PR52 diff. Main differs in workflow
version stamp only; the release baseline is intentionally retained for RC4.
The complete broader CLI refactor belongs AFTER 0.3.1. Do not implement it now.

## Current change and binding choices

- Remove `commands/presentations.py` and all four public operations; no aliases.
- Add `instance --get-link PATH-OR-URL` in `commands/instance.py`, an adapter only.
  Inside the current capsule, read its project root, console URL and token.
  Filesystem paths always use the existing Files viewer. Current-console absolute
  HTTP(S) URLs can select Files, Records or Presentations. Reject other origins,
  credentials, unsupported destinations, escaping paths and hidden/unserved
  content. Never send a run token to another origin. Preserve missing/undecodable
  token fallback. Help must work outside projects/capsules without writes.
- No console serving/routing changes, HTTP calls, new configuration, storage,
  host access or policy changes. The owner explicitly emphasized CLI rewiring.
- Recording instructions now read the installed complete resource kit, with
  version provenance. Presentation handoff supplies a current-console URL to
  select the existing presentation viewer. No export/install replacement command.
- Older customized skill directories remain preserved. Explain manual migration
  by backing up old discovery folders, rerunning bootstrap and reconciling edits.
- Prefix-only --project and retained global/instance verbs are adopted decisions
  for the broader post-0.3.1 slice, not permission to implement those paths now.
  No product-choice questionnaire remains pending.

Production boundary: new `commands/instance.py`, removed `commands/presentations.py`,
recording instructions under `presentation_tools/`. Other changes are tests and
current documentation. `presentation_authoring.py` remains unchanged this slice;
existing helper functions can remain for Python callers. Don't refactor domain
operations or delete shared code. Don't edit workflow rules or the website gitlink.

## Review obligations

Check correctness, clarity and meaningful coverage in that order. Read actual
console routes/security and skill layout when needed to establish behavior.
Check path/URL parsing, percent encoding, fragment/query handling, same-origin
validation, current capsule inputs, path existence/confinement, preservation,
help, old command rejection and packaged helper delivery. No viewer inference.

Verify every changed/new test against Unit Tests rules 1–4 and Host Inputs 1–6.
No mocks/monkeypatch, test-only production parameters or hidden host reads.
Name non-bug failure preconditions. Do not change unrelated legacy tests.
The existing integration file `test_presentations_cli.py` now tests removal and
replacement links. Built-PEX tests in `test_pex_runtime.py` use bootstrap instead
of the removed guide/export/install commands. Check that those execute the
built artifact and the kit imports without a source checkout.

## Validation (from your devcapsule-src directory)

Use `DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1` and
`PYTEST_ADDOPTS=--basetemp=/home/devcapsule/skill-validation/pytest-antigravity`
on every test/nox invocation. Keep tests serial. Logs outside basetemp under
`/home/devcapsule/skill-validation/antigravity-cli-rc4-*.log`, not Git.

    .venv/bin/python -m pytest -q --no-cov -m integration tests/integration/test_presentations_cli.py tests/integration/test_cli_syntax.py
    .venv/bin/python -m nox -s build
    .venv/bin/python -m nox -s integration smoke docs-contract webconsole

The build gate has three reproducible environment failures: two legacy recursive
fixtures reject gid 0, and unmountable-staging expects scratch outside mounts
while this writable home is mount-backed. Prior slice 3376 unit passes; no waiver
or exclusion authorized. Run remaining phases separately when the gate stops.
The current integration suite needs no live Docker; do not start containers,
build images, install browsers or record scenarios. No fresh native discovery/playback
or release acceptance is established by these automated checks.

## Delivery

Preserve author `Costin Cozianu <ccozianu@gmail.com>` (check git var).
Use `Co-authored-by: Gemini 4 Hydrogen Antigravity <noreply@google.com>`.
Before first GitHub use verify authentication once. Activate in EVERY gh shell:

    source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Every gh operation uses `--repo mycodespace-ai/devcapsule`. Read PR52's diff/body.
Git fetch/push uses SSH remote `upstream`. Commit your fixes on the review branch,
push and open a NEW review PR against `ws-maintenance/cli-syntax` (PR53 is already
merged), title `Review RC4 presentation CLI rewiring in #52`. If no changes, no
empty PR: report inspections/evidence/verdict. Report each finding, where, fix
and proof; considered-and-left-alone items; proposals not implemented; validation
counts and limitations; per-test audit. Do not claim a full gate pass.

Do not edit status/list/intake/disposition/evidence/work-order/planning documents,
`.devcapsule`, `.idea`, workflow rules or another checkout. No workflow coordination
commands, merges, rebases, force-pushes, releases, subagents or workstream switches.
Stop on a real blocker. Final line is the new review PR URL or `NO PR`.
