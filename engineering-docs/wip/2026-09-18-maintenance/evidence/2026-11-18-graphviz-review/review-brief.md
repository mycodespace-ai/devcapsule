# Claude Pair Review brief: Graphviz PR56

Implementor: gpt-6.1-sol Codex. Reviewer: Claude Code; report the actual model
from your session, not an inferred default. The owner explicitly requested this
review after rejecting the unexplained release-specific automatic CI trigger.
Review the entire PR56 implementation, not just its YAML. No earlier Pair Review
has covered this Graphviz slice. Deliver an improvement PR against PR56 if needed.

## Goal and scope

Graphviz 16.1.1 must be selectable through project require/offer, install under
/opt/graphviz, work on both Linux architectures, and participate in freshness
reporting. It must compose with existing components without changing the base.
The original PR had automatic native Docker builds on PR and main/release-0.3.1
push. The implementor now makes that workflow manual-only, with explanatory
comments and contributor documentation, respecting the opt-in Docker policy.
Review that correction critically. Do not add new automatic CI, release-specific
triggers, or a generic component framework beyond what this slice needs.

## Your checkout and reading order

Work only in /home/devcapsule/worktrees/maintenance-graphviz-review on
ws-maintenance/graphviz-031-review, branched from ws-maintenance/graphviz-031.
Never edit /workspace/301e4208ef81-ChatGPT_Codex. Read:
1. README.md, DEVELOPING.md, AGENTS.md.
2. WORKFLOW.md topics 2, 9.11; WORKFLOW-LOCAL.md (validation, tests, host inputs,
   authorship, GitHub and Pair Review sections).
3. engineering-docs/requirements/product/r-tools-001-graphviz-component.md.
4. engineering-docs/wip/2026-09-18-maintenance/2026-11-18-graphviz-component.md;
   CURRENT-STATUS.md in that directory, Graphviz section only (read-only).
5. .github/workflows/graphviz-component.yml and scripts/graphviz-component-smoke.py
   under devcapsule-src; then graphviz*.py under components, interface.py,
   materialization.py, images/build.py, resolution_matrix.py and changed tests.

Inspect the complete diff against origin/release-0.3.1 and `gh pr diff 56`.
Generated pin data and migrated resolution tests are in scope. Priority:
1. Correctness: source/dependency pin validation, architecture selection, offline
   build isolation, runtime library/licenses, PATH composition, grouped-copy
   renderer and exports, discovery failure/downgrade behavior, require/offer.
   Does the smoke script prove the actual production composition rather than
   mask a missing contribution? Are report assertions meaningful?
2. Clarity: documented contracts, obvious purpose and scheduling of workflow,
   no unexplained permanent release coupling. Check user docs against behavior.
3. Coverage of changed branches. Add meaningful regression cases for findings.
   Check every new/changed test against local Unit Tests rules 1-4 and 8:
   own inputs, one public action, promised postcondition, mirror, docstring.
   Name what could fail each test for a reason other than a bug. Check Host Inputs
   rules 1-6: ambient reads, effectful defaults/constructors, test-only inputs,
   entry-layer decisions and patches. Do not dismiss test-contract findings.

Stay within Graphviz and necessary build integration. Do not modify unrelated
release, recursive-test fixtures, agent updates, CLI syntax or website source.
Flag larger proposals without implementing them. No new product choices.

## Environment and validation

Your own devcapsule-src/.venv will be prepared before launch. Work from
`devcapsule-src`, set PYTEST_ADDOPTS=--basetemp=/opt/devcapsule-gate/pytest-claude-graphviz.
Run these exact commands:

    .venv/bin/python -m nox -s build
    .venv/bin/python -m pytest -q -m integration tests/integration/test_graphviz_component.py tests/integration/test_resolution_matrix.py

Run a focused test first for each change. Gate before final push, unit session
on the exact branch to push. State all counts, skips and limitations. An absent
website submodule may cause docs-contract to skip; report it. Native amd64 and
arm64 source builds/render tests already passed in Actions run 44211166923.
Do NOT build images, start capsules or dispatch workflows. The implementor owns
any needed native rerun. The hosted automatic gate does not catch real compiler,
plugin/library or downloaded-release regressions; state those limits in your PR.

## GitHub, authorship and delivery

Before the first gh use check auth once. For every shell invoking gh:

    source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then use gh against mycodespace-ai/devcapsule. Stop if auth fails; do not retry
or substitute credentials. Git fetch/push uses the existing SSH origin remote.
Check `git var GIT_AUTHOR_IDENT`: human author Costin Cozianu <ccozianu@gmail.com>.
Each commit must end in `Co-authored-by: <actual model> Claude Code <noreply@anthropic.com>`.
Verify saved author and trailer. Record actual model in PR body and final report.

Commit fixes only on ws-maintenance/graphviz-031-review. Push, then open PR:

    gh pr create --repo mycodespace-ai/devcapsule --base ws-maintenance/graphviz-031 --head ws-maintenance/graphviz-031-review --title "Review Graphviz component correctness and CI policy (PR56.1)" --body-file <scratch-body-file>

Write actual multiline body to a scratch file. List findings: what was wrong,
where, what changed, and how the test proves it. Separately list considered and
left alone with reasons, proposals not implemented, validation counts/limits.
If no fixes or useful tests are needed, open no empty PR and report NO PR.

Do not edit status files, root workstream list, intake, evidence or publication
state. Do not merge, rebase, force-push, tag, release, touch main/release refs,
edit credentials or shell profiles. Do not commit website, .idea, .venv, .nox,
egg-info, dist, pycache or scratch. No images/capsules or extra agents.
If blocked by credentials, network or inability to proceed, stop and state it.
Print the review PR URL as the final line, or NO PR if no change was needed.
