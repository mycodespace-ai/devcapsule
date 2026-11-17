# Round 1: test-contract corrections for PR #46

Continue the same Antigravity Gemini 4 Hydrogen High review of PR #43.
I read the actual diff of PR #46 at `e40d16a5`. The product fixes are accepted
in principle; make only the following corrections before integration. Do not
repeat the broad investigation or widen product behavior.

1. Make the new recorder unit tests follow WORKFLOW-LOCAL Unit Tests rule 2:
   one public action under test, with setup stated separately. In particular:
   - `test_recording_keeps_failed_outcome_and_reached_steps_when_callback_fails`
     tests the callback exception, rejection of a later action and finalization.
     Split those into distinct contracts/tests, constructing each precondition.
   - Split repeated finish from action-after-finish.
   - Split or parameterize empty evidence versus missing screenshot evidence.
   - Split or parameterize encoder nonzero exit versus successful exit without
     output. Each case should call `finish` once as its action under test.
   - The passing-run test may prepare its run through `action` calls, then test
     `finish`; make that separation explicit. Its numeric `[8,16,24]`, fixed
     duration and fixed repeated frame bytes encode the current burst cadence,
     which the public contract does not promise. Assert the contract instead:
     logs have increasing frame boundaries, chapters/captions align to those
     boundaries and the video duration, and encoder input equals captured data.
     Do not declare a new public cadence guarantee merely to keep the assertions.
   - Keep the controlled encoder subprocess (running the encoder is part of
     `finish`'s contract), but isolate its interpreter invocation from ambient
     Python startup customization with `-I -S`.
   Correct the PR body's blanket claim that every new test already has one
   public action. Report concrete non-bug failure conditions for the final tests.
2. Clarify the shipped guide's hand-off example: run it from the console project
   root; a relative evidence folder resolves from cwd, and `--project` supplies
   the root used to form the console-relative link. No resolution behavior change.

Do not add the proposed nox smoke expansion: the new PEX integration test already
covers this delivery boundary. The implementor will rerun the real Chromium
acceptance and docs contract on the merged branch. No browser/service/container
work in your worktree. Do not edit workstream records or published state.

Run from your worktree's `devcapsule-src`:

```sh
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 .venv/bin/python -m pytest -q --no-cov tests/test_scenario_recorder.py tests/unit/devcapsule/presentation_tools tests/unit/devcapsule/test_presentation_authoring.py
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 .venv/bin/python scripts/validate_unittests_follow_conventions.py
DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 PYTEST_ADDOPTS='--basetemp=/var/tmp/presentations-antigravity/round-1 --maxfail=1' .venv/bin/python -m nox -s build
```

The known Docker-group limitation remains disclosed. Do not repeat the other
unchanged suites merely to accumulate checks. Commit on your existing review
branch with the established authorship, push via upstream SSH and update PR #46
using the prescribed Conda gh environment. Preserve previous findings and limits,
update the unit counts, and mark this response to Round 1. No merge/rebase/force push.
Finish with `PAIR REVIEW COMPLETE: <PR URL>; <counts and limits>` or the established
blocked form if necessary.
