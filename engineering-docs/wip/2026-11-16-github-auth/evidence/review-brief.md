# Review brief: GitHub SSH proxy, Gemini 4 Hydrogen High

Implementor: Codex, GPT-6. Review partner: Antigravity, gemini-4-hydrogen-high.
The owner requested this feature with Pair Review and selected the github-auth
workstream and Git over SSH first. Review correctness, clarity and meaningful
coverage of the implementation against upstream/main.

## Checkout and first reads

Work only in /home/devcapsule/worktrees/github-auth-review on
ws-github-auth/ssh-proxy-review. Do not edit the implementor checkout.
Read AGENTS.md, WORKFLOW.md topic 9.11, WORKFLOW-LOCAL.md, this brief,
engineering-docs/wip/2026-11-16-github-auth/CURRENT-STATUS.md, then
`git diff upstream/main...HEAD`. Read the contracts in github_transport.py and
github_proxy.py before judging implementations. This brief is your only context.

## Scope and questions

Ordinary GitHub clone/fetch/push from a Linux/WSL capsule uses host-side OpenSSH
through a private launcher-owned Unix socket. No private keys or host agent socket
enter the capsule. Only fixed GitHub upload-pack/receive-pack requests are allowed.
The authorization is optional and denied by default; grant through host config or
run-once. All repositories accessible by the host identity are within the grant.
Host key checking remains strict; keys must authenticate noninteractively on the
host. Other Git hosts fall back to the capsule SSH. Mac Docker Desktop, HTTPS, gh,
Git LFS auth, SSH signing, arbitrary aliases are outside the first slice.

Review in order:
1. Correctness: injection/destination escape, request validation independent of
   the client, socket permission boundary, lifecycle cleanup, cancellation,
   bounded memory/concurrency, deadlocks/half-close/exit status, Docker environment
   integration and denial. Never weaken host-key checking to make a test pass.
2. Clarity: remove misleading guarantees or unnecessary machinery.
3. Coverage: new tests must establish independent contracts, especially auth
   gating, real binary streaming, failure/exit handling and process cleanup.
4. Follow Unit Tests rules 1-4 in WORKFLOW-LOCAL.md. New unit tests live in the
   module mirror, state their contract in a docstring, and construct inputs.
   For each, identify possible failures not caused by a product bug. Do not edit
   tests in legacy files. Add integration tests for subprocess/network effects.
5. Prefer explicit host inputs and pure decisions. No monkeypatch/unittest.mock
   in new tests. Code runs no invented cryptography; authentication is OpenSSH.

Keep corrections within this feature. Do not repair unrelated legacy tests or
expand to macOS, HTTPS, repository allowlists or generic SSH forwarding.

## Validation

Create your own environment exactly as the local workflow says, from devcapsule-src:
python3.12 -m venv .venv
.venv/bin/python -m pip install -r dev-requirements.txt
.venv/bin/python -m pip install -e . --no-deps

Use scratch under /home/devcapsule/.cache/devcapsule-gate/github-auth-review;
/opt is read-only. The parent cache directory exists.
Initialize website with `git submodule update --init website` for the docs gate.
Run focused tests:
.venv/bin/python -m pytest -q --no-cov -o addopts='' tests/unit/devcapsule/test_github_transport.py tests/unit/devcapsule/configuration/test_authorization.py tests/unit/devcapsule/configuration/test_review.py tests/integration/test_github_proxy.py

Run full gate synchronously, not a background tool job:
PYTEST_ADDOPTS='--basetemp=/home/devcapsule/.cache/devcapsule-gate/github-auth-review' DEVCAPSULE_DIFF_BASE=upstream/main .venv/bin/python -m nox -s build

The implementor's focused run passed 42 tests. Its full gate may expose existing
mainline legacy test failures in this capsule. Report exact failures; do not fix
unrelated code or disable tests. Do not build images or launch Docker capsules.

## Delivery and forbidden actions

The GitHub CLI is ABSENT at /opt/xtras/miniconda3/envs/gh/bin/gh. Local policy
requires the human to create PRs in this case. Do not use another credential or
GitHub interface. There is not yet a PRn; PR-mediated Pair Review completion is
pending owner delivery. Perform the local code review now, preserve your findings
and corrections, and report this delivery blocker accurately. Do not claim a
completed PR review loop. Push your review branch over ordinary upstream SSH
only after checks; no push to main. Provide a compare URL if changes exist.

Do not edit status files, intake/dispositions, evidence, root CURRENT-STATUS.md,
index.md, or run workflow publish. Do not change website gitlinks or configuration
manifests. Do not merge, rebase, force-push, create releases, inspect private keys,
read credential contents, use real GitHub repositories in tests, or run containers.
Do not modify the implementor's files or state. Do not add broad test-only seams.

Commit corrections with the existing human author and this trailer:
Co-authored-by: Gemini 4 Hydrogen High Antigravity <noreply@google.com>

Report findings (what/where/fix/evidence), things considered and left alone,
unimplemented proposals, exact validation counts and limits. If no changes, say
so. Print REVIEW_COMPLETE as your last line, or REVIEW_BLOCKED with the reason.
