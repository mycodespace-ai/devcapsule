# Round 2: complete review PR #44 for release 0.3.1

Continue the GitHub SSH proxy review with Antigravity gemini-4-hydrogen-high,
high effort. Implementor: GPT-6 Codex. Your previous review commit is 388f62a3.
Implementation PR #47 now targets release-0.3.1 by explicit owner direction;
its hosted base will be changed after validation. Review PR #44 targets
ws-github-auth/ssh-proxy. The implementor has merged the current implementation
into your review branch to prepare it, with no conflict and no reset/rebase.

Work only in /home/devcapsule/worktrees/github-auth-review on
ws-github-auth/ssh-proxy-review. Your independent devcapsule-src/.venv is prepared.
Read this brief, current WORKFLOW-LOCAL.md Unit Tests and Host Inputs, the earlier
review-assessment.md and round-1.md, then the actual diff against
ws-github-auth/ssh-proxy and the proxy contracts. Inspect the release merge's
interaction with your launcher and authorization changes. Do not widen the feature.

Two requested test corrections:
1. _read_ready_line selects readable and then calls blocking readline: a partial
   line still hangs. Make the entire expected handshake bounded, with cleanup.
2. Parameterize test_containerized_bridge_requires_an_inherited_canonical_socket
   so each case calls one public operation, per current Unit Tests rule 2.
Also assess whether the 0.2-second deadline test assumes Python startup timing;
make its preconditions explicit or report the limitation. Keep changes small.

Verify correctness, clarity, then meaningful changed-line coverage. Verify Unit
Tests rules 1-4 for every changed/new test, and name non-bug failure conditions
in your report. Verify Host Inputs rules 1-6 on the changed code/tests. Do not
invent test-only seams or fix unrelated inherited failures. Propose broader
changes separately if they cannot fit this bounded correction round.

From devcapsule-src, run:
PYTEST_ADDOPTS='--basetemp=/var/tmp/gpr' .venv/bin/python -m pytest -q --no-cov -o addopts='' tests/unit/devcapsule/test_github_transport.py tests/unit/devcapsule/test_github_proxy.py tests/unit/devcapsule/configuration/test_authorization.py tests/unit/devcapsule/configuration/test_review.py tests/integration/test_github_proxy.py
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 .venv/bin/python scripts/validate_unittests_follow_conventions.py
.venv/bin/python -m mypy devcapsule
PYTEST_ADDOPTS='--basetemp=/var/tmp/gpr' DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 .venv/bin/python -m nox -s tests > /var/tmp/github-auth-review-unit.log 2>&1
Run synchronously and report the log's exact result. The implementor runs the
full post-merge build gate. Prior combined gate had three inherited unit failures
(unmountable staging and two recursive Docker gid-zero cases); report current
results, do not disable tests or modify those unrelated contracts.

GitHub CLI is NOW installed. In every gh shell:
source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh
First verify gh auth status -h github.com; stop on failure, use no other credential.
You may read PR #44/#47. Commit and push your corrections over SSH to upstream.
If tests pass and a gate failure is not expected, update #44 with --body-file.
Otherwise report validation in a gh pr review --comment on #44; do not conceal
failures or claim a passing gate. Include findings, unimplemented proposals and
non-bug test failure conditions. Do not open another PR.

Preserve human git author; trailer:
Co-authored-by: Gemini 4 Hydrogen High Antigravity <noreply@google.com>
Do not merge, rebase, reset, force-push, edit other branches/checkouts, status,
intake, evidence, workflow files, index.md or configuration manifests. Do not
build images/start containers, inspect keys, use real GitHub repositories in tests,
or alter the installed launcher. No new broad investigation or repeated full gate.
Print REVIEW_COMPLETE or REVIEW_BLOCKED with the reason as the final line.
