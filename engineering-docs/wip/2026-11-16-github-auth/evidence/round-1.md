# Review follow-up 1: finish the bounded local review

Continue the same Gemini Hydrogen review in /home/devcapsule/worktrees/github-auth-review.
Your full build has FINISHED: step 130 returned 20 failed, 2926 passed, 1 skipped,
14 xfailed and 7 xpassed. No pytest or nox process remains. Your CLI stayed idle
after that completion, so the implementor interrupted it and resumed this turn.
Do not wait for the completed job. Do not repeat the full gate: its failures are known.

The implementor read your diff and accepts its production-code changes and added
coverage in principle. Fix these test issues before committing:
1. test_host_bridge_requires_openssh_on_path passes PATH="". shutil.which searches
   the current directory in that case; the test depends on no file named ssh being
   present there. Use tmp_path as an explicitly empty PATH directory instead.
2. test_broker_shutdown_cancels_active_ssh_process_group calls stdout.readline with
   no timeout. Bound the ready handshake and ensure client cleanup in finally even
   if readiness fails. Avoid a test that hangs forever when the product is broken.
3. An orphaned grandchild may be a zombie until the host's reaper runs. The broker
   cannot waitpid a grandchild. Verify that no descendant is running, without
   asserting timely reaping by an unrelated PID 1. State the test's actual claim.

Run focused tests INCLUDING your new unit test_github_proxy.py and integration
file and mypy. If new focused tests fail, fix those failures within this scope.
Commit your corrections. Do not merge, reset, rebase or touch the parent checkout.

Parent updates already committed separately (do not duplicate or cherry-pick):
- f1dbb338 refurbishes tests/configuration/test_nodes.py into its correct mirror,
  20 passing cases; this resolves the new github-ssh name expectation.
- 4ba1725f aligns webconsole/configuration.py SECURE_AUTHORIZATIONS and its contract;
  all 458 console tests now pass.
- The remaining 19 failures are reproduced on unchanged upstream/main, by selecting
  all 20 failing test IDs in an archive of the base (19 fail, the registry test passes).
- Parent CLI smoke, PEX build/smoke and docs contract pass. Both source and PEX Git
  adapters passed read-only authenticated GitHub ls-remote using the capsule's existing
  credential on the broker side; not a physical-host launch test.

Your branch can be pushed to upstream as review preparation, with limitations in
its report. No PR exists because local policy makes creation owner-operated without
its prescribed gh installation. Do not use another GitHub interface or credential.

Return the findings, corrections, focused results, known full-gate failures and
unimplemented proposals. End with REVIEW_COMPLETE or REVIEW_BLOCKED. Do not begin
another broad investigation; the remaining task is these test corrections and delivery.
