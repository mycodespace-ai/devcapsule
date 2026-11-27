# Pair Review: recursive dry-run Docker group zero

Implementor: Codex, GPT-6. Reviewer: Antigravity, exact `gemini-4-hydrogen`.
The owner authorized accepting Docker group 0 and moving two failing legacy
checks into integration after a disposable experiment proved both pass without
that rejection. Deliver one bounded fix from `ws-maintenance/recursive-test-fixture`
to `release-0.3.1`. Find the implementation PR by that head branch.

## Checkout and reading order

Work only in `/home/devcapsule/worktrees/maintenance-review`, branch
`ws-maintenance/recursive-test-fixture-review`, with its own devcapsule-src/.venv.
Read README.md, DEVELOPING.md, AGENTS.md, WORKFLOW.md topic 9.11, WORKFLOW-LOCAL.md
(validation, Unit Tests, Host Inputs, GitHub, authorship, Pair Review), this brief,
the current recursive-test section of maintenance status, recursive_host.py and
the changed integration tests. The brief is your only conversation context.
Main's workflow differs only in the version stamp; retain the release baseline.

## Scope and review

Inspect correctness, clarity, then coverage. Docker gid 0 is valid here: namespace
0 maps to host 1000 and the actual Docker socket has gid 0. The real successor
launch path already supports rootless Docker. The old dry-run staging function
requires positive Docker group IDs; this fix accepts non-negative integers and
reuses the root group entry. Keep rejection of boolean/fractional/negative IDs.
Do not broaden to the separate runtime UID/GID or sudo-group policy. In particular,
the older dry-run's positive runtime identity guard remains; do not claim this
fix makes the whole dry-run CLI support rootless 0:0 identity.

The legacy rule requires retirement of the entire six-test file. Its metadata,
readiness, staging, cleanup, failure preservation and X11 isolation behaviors are
retained in integration, against real filesystem layouts and Unix sockets. The
failure tests now require the actual oversized-Xauthority error. Parameter cases
cover zero/distinct/primary Docker groups and malformed groups. Verify actual
postconditions and no duplicate root group entry. No skipping is authorized.

For every new or changed test verify Unit Tests rules 1–4 (including correct
heavier-suite placement) and Host Inputs rules 1–6 where applicable. Name each
non-bug failure prerequisite. This is filesystem integration, not a Docker E2E
or a pure-unit claim. Do not introduce patches/mocks or silently broaden scope.

## Validation

From your own devcapsule-src, run serially:

    PYTEST_ADDOPTS=--basetemp=/tmp/dc-recursive-review .venv/bin/python -m pytest -q --no-cov -m integration tests/integration/test_recursive_orchestrator.py
    DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 TMPDIR=/home/devcapsule/skill-validation/recursive-review-tmp PYTEST_ADDOPTS=--basetemp=/tmp/dc-recursive-review .venv/bin/python -m nox -s build

Create the named TMPDIR first. /opt is read-only in this capsule. Temporary
pytest files use /tmp (monitor its 2 GB limit); subprocess/packaging scratch uses
home. Home-based pytest scratch triggers an unrelated legacy host-daemon test
whose synthetic mount covers home. Do not modify that test. Docs contract may
skip for your uninitialized website; report this, and use the implementor's
independent docs check as separate evidence. No images, containers, configuration
writes to the working project, network acquisitions, recording or browser installs.

## Delivery

Verify author `Costin Cozianu <ccozianu@gmail.com>`; add trailer
`Co-authored-by: Gemini 4 Hydrogen Antigravity <noreply@google.com>`.
Use canonical SSH remote upstream. Activate gh in EVERY shell:

    source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Check `gh auth status -h github.com` once. Every PR command uses
`--repo mycodespace-ai/devcapsule`. Commit fixes and push your review branch,
then open its PR against `ws-maintenance/recursive-test-fixture`. Report findings,
changes, tests, considered-but-left-alone items and unimplemented proposals.
If no edits are needed, report the verdict and open no empty PR.
Do not edit status/list/intake/evidence/review-loop records, .devcapsule, .idea,
workflow rules, the website gitlink or another checkout. No coordination commands,
merges, rebases, force pushes, tags, releases, subagents or workstream changes.
Stop on a real blocker. Final line: review PR URL or `NO PR`.
