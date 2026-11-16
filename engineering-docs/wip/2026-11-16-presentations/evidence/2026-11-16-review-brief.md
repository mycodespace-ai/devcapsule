# Pair Review brief: Antigravity, Gemini 4 Hydrogen (High)

Status: prepared, not launched. The implementation PR must exist first. The
implementor supplies its number when this brief is used. The prescribed GitHub
CLI is absent in the implementor checkout; the owner operates GitHub until it
is installed. Do not silently substitute another credential or delivery route.

## Goal and checkout

Review `ws-presentations/0.3.1-authoring` against `upstream/release-0.3.1`.
The implementor pair is GPT-6 Codex. This is the first review of the slice.
Deliver any improvements on `ws-presentations/0.3.1-authoring-review`, forked
from the implementation branch at review start, in
`~/worktrees/presentations-review`. Work only in that worktree. Do not touch
the implementor checkout `/workspace/301e4208ef81-ChatGPT_Codex`.

Read first, in order:

1. `AGENTS.md`, `README.md`, `DEVELOPING.md`, `.devcapsule/devcapsule.toml`,
   `WORKFLOW.md` and `WORKFLOW-LOCAL.md`.
2. `engineering-docs/wip/2026-11-16-presentations/CURRENT-STATUS.md` and
   `2026-11-16-record-use-case-handoff.md` in the same directory.
3. `2026-11-16-record-authoring-validation.md` in that directory.
4. `devcapsule-src/devcapsule/presentation_tools/README.md` and
   `devcapsule-webconsole/PRESENTATIONS.md`.

The engineer supplies an existing Markdown scenario or inline English. The
agent translates that into project-specific Playwright actions and assertions,
records them and returns the existing viewer's link. The viewer is already
human-accepted. Do not redesign it, invent an English parser or require a new
user-facing scenario format. The scope is packaging the proven producer and
recording support so an adopter agent does not need this source checkout.

## Changes and review priorities

Read the branch diff. Review correctness, then clarity, then coverage of the
changed lines. New modules: `commands/presentations.py`,
`presentation_authoring.py`, and `presentation_tools/`. The latter contains
the existing producer moved from `tests/e2e/scenario_presentation.py`, a new
portable recorder, shipped guide and example. The old path is a compatibility
adapter; its producer tests moved to the corresponding production mirror.
Package-data, README, recording documentation and the index expose the kit.

Check especially that an installed PEX can export complete, importable tools
without `tests` or `devcapsule` in the adopter's Playwright interpreter; that
timing, step ownership, screenshots and captions satisfy the viewer contract;
that failure/incompletion never becomes a passing result; and that existing
evidence is not overwritten. Check callback failure, capture failure, encoder
failure, repeated steps and missing steps. Check console path/token handling
without persisting tokened links. The helper intentionally uses sparse bursts
around small actions, with native video kept by the driver.

Do not expand into a generic process framework, application provisioning,
viewer redesign, natural-language parsing, unrelated legacy test repairs or
changes to the workflow definition. Propose substantive product choices to
the implementor rather than choosing them in this review.

For every new or changed test, verify Unit Tests rules 1–4 and 7: a module
mirror; its own explicit precondition, one public action and a promised
postcondition; a plain-English contract docstring; and a declared public
surface. Name what could make each fail for a reason that is not a bug.
Verify Host Inputs rules 1–6 on code and tests: host reads only at entry;
required explicit values thereafter; shared host values in frozen data;
decisions separate from effects; no monkeypatch, unittest.mock, environment
mutation or module/class attribute replacement; short entry sequencing tested
through a real program in an integration test. Respect legacy-test retirement
and command-line test restrictions. Do not weaken tests to obtain a green gate.

## Environment and validation

The implementor prepares a separate `devcapsule-src/.venv` in your worktree
using the local workflow's validation instructions. Run from `devcapsule-src`:

```sh
mkdir -p /var/tmp/presentations-antigravity
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 .venv/bin/python -m pytest -q --no-cov tests/unit/devcapsule/presentation_tools tests/unit/devcapsule/test_presentation_authoring.py
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS='--basetemp=/var/tmp/presentations-antigravity/pytest --maxfail=1' .venv/bin/python -m nox -s build
```

Use that separate scratch because `/opt/devcapsule-gate` is read-only on this
host; Validation Commands permits another directory with room. The known
inherited Docker-group failure may stop the full gate; report it and do not
repair that unrelated fixture. The implementor's separate PEX, docs and
webconsole checks passed. Its real Chromium checks covered passing, failing
and incomplete recordings and playback of every generated chapter. If code
changes invalidate this evidence, request a focused rerun from the implementor.
Do not build images, launch capsules, install browsers or provision services.
Report what the hosted gate does not catch.

## Authorship and delivery

Check `git var GIT_AUTHOR_IDENT`. Preserve the human author
`Costin Cozianu <ccozianu@gmail.com>`. Credit the actual reviewer engine/model
using the project's Antigravity co-author convention in WORKFLOW-LOCAL.

Detect GitHub CLI only at `/opt/xtras/miniconda3/envs/gh/bin/gh`. In each shell
using it, activate it first:

```sh
source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh
```

Check `gh auth status -h github.com` once before first use. On auth failure,
stop and report; no retries or alternate credentials. If absent, stop at the
owner-operated PR handoff prescribed in WORKFLOW-LOCAL. Use ordinary Git SSH
to push the review branch to `upstream`.

After required checks, create the review PR against
`ws-presentations/0.3.1-authoring`, never against the release or main. Its body
lists findings (problem, location, change, evidence), what was considered and
left alone with reasons, unimplemented proposals, and validation counts/limits.
If nothing changes, report that and create no empty PR. Do not merge, rebase,
force-push, change workstreams, edit status/intake/published state, or send mail.
At most three review rounds; the implementor assesses the actual diff.

Finish with exactly one of these forms, filling the result:

`PAIR REVIEW COMPLETE: <review PR URL or no changes>; <counts and limits>`

`PAIR REVIEW BLOCKED: <specific blocker and next human action>`

## Invocation for the implementor

The model catalog was checked on 2026-11-16. Use the exact listed ID and the
explicit effort setting; do not substitute a model:

```sh
antigravity --model gemini-4-hydrogen-high --effort high --dangerously-skip-permissions --output-format stream-json -p 'Follow the Pair Review brief on standard input.' < <brief-path>
```

Run detached in the review worktree, capture its streaming output in session
scratch and append its exit status. Relay start, commits, gate results and end
to the human. Keep this brief as the reviewer's only task context. Record the
actual invocation and outcome in the Pair Review development document after
the loop runs; this prepared brief is not evidence of a completed review.
