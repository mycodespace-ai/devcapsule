# Round 1: establish the directory-mode regression precondition

Continue the same Claude session for review PR58:
https://github.com/mycodespace-ai/devcapsule/pull/58

**Round 1 (gpt-6.1-sol Codex).** I read the complete eight-file diff at `a5541a7e`. The production fixes are appropriately scoped. One regression-test precondition blocks acceptance: `test_grouped_inputs_stage_directories_any_image_user_can_enter` passes the original renderer under umask 022. I reproduced original modes `0755` at 022 and `0700` at 077. The test must establish its own restrictive umask, as Unit Tests rule 2 requires for an environmental input. There is no rule forbidding a test from setting that input.

Please set process umask 077 for this test, restore the previous value in `finally` (or a fixture), and keep `render_build_context` as its one operation under test. Prove it fails against the original renderer and passes with the correction; then run the focused tests and full gate. Correct the PR body's claim that unit tests may not set umask. No other production change is requested. I own the native-image rerun after acceptance.

Work only in /home/devcapsule/worktrees/maintenance-graphviz-review on
ws-maintenance/graphviz-031-review. Keep all previous scope, forbidden actions,
GitHub activation and authorship rules. Read the assessment with:

    source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh && gh pr view 58 --repo mycodespace-ai/devcapsule --comments

Run the focused test with its own precondition, show red-before/green-after,
then from devcapsule-src run:

    .venv/bin/python -m nox -s build
    .venv/bin/python -m pytest -q -m integration tests/integration/test_graphviz_component.py tests/integration/test_resolution_matrix.py

Use PYTEST_ADDOPTS=--basetemp=/opt/devcapsule-gate/pytest-claude-graphviz.
Commit the correction with the actual-model Claude Code trailer, push only your
review branch, update the review PR's claims and final counts, and reply with
what changed and what passed. Do not merge, build images, start capsules or
change status/evidence files. No additional scope is requested.
Print your final comment URL as the last line. Stop on a blocker.
