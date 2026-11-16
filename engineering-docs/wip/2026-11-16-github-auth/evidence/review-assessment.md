# GitHub SSH proxy review assessment

Date: 2026-11-16. Implementor: GPT-6 Codex. Reviewer: Antigravity,
`gemini-4-hydrogen-high` (Gemini 4 Hydrogen High).

## Final disposition, 2026-11-16

Round 2 accepted at `455d3acc`; review PR #44 merged at `9638cb11`.
Both pairs posted their assessments on #44. PR #47 targets release-0.3.1.
The full combined gate and remaining checks are in the [final record](2026-11-16-final-review.md).
Two inherited recursive Docker gid-zero unit failures remain; they do not arise
from the review corrections. The reviewer's broad Host Inputs compliance claim
is qualified: pure parsing/decisions are separated, but the broker/relay/bridge
still perform runtime effects. Stricter separation remains a follow-up.

## Earlier local disposition (superseded by the final disposition)

Round 1 accepted locally at `388f62a34fe373882201f9118faaf34cec61680b`.
The reviewer branch is pushed as `ws-github-auth/ssh-proxy-review`.
No review PR or implementation PR exists yet. This is local review preparation,
not completion of the PR-mediated Pair Review Loop or mainline integration.

The implementor inspected the diff and accepted the unused helper removal,
separate capsule-SSH error attribution, public API declaration, launcher dry-run
warning and disclosure layout, deny-help update, and expanded hostile-input,
permission, cancellation, process-group and authorization coverage.
Round 1 replaced an ambient-current-directory PATH check, bounded the readiness
handshake, guaranteed client cleanup, and distinguished dead orphan zombies from
running descendants. The process tests depend on Linux /proc and scheduling
within their explicit timeouts; they do not prove prompt reaping by PID 1.

The reviewer ran 55 focused cases successfully. A temporary, uncommitted merge of
`388f62a3` with implementation `890fa91d` was conflict-free and passed **75 focused
tests**, mypy on the nine touched modules/test files, and the conventions checker
(103 legacy files, 1380 legacy tests, 50 conforming files, zero breaches).
`git diff --check` and `git fsck --connectivity-only --no-dangling` passed.
The temporary merge was aborted deliberately: reviewer corrections remain on
their separate pushed branch for the owner-operated review PR.

## Build evidence and limits

The implementor's full build reached pytest: 20 failed, 2917 passed, 1 skipped,
76 deselected, 14 xfailed, 7 xpassed. The reviewer's independent build found the
same failure set: 20 failed, 2926 passed, 1 skipped, 80 deselected, 14 xfailed,
7 xpassed. The new node-name expectation was repaired on the implementation
branch by refurbishing the complete legacy file into the unit mirror (20 passing
cases); the reviewer was told not to duplicate this change. The other 19 failures
reproduced by selecting all 20 failed IDs on an archive of unchanged canonical
main `1942f396`: 19 failed, 1 passed. They concern inherited capsule trust,
permissions/ownership and recursive-launch environment; they remain unresolved.
A full gate on the combined final tree has not passed.

CLI smoke, PEX build/smoke and documentation contract passed separately. After
aligning the console authorization mirror, all 458 webconsole tests and its types
passed. Both source and built PEX adapters completed authenticated GitHub
`ls-remote` through the broker, returning mainline HEAD `1942f396`. The broker in
that probe used the current capsule's existing SSH setup. This is **not** evidence
of physical-host Docker launch acceptance. No real GitHub write was tested; local
fixture repositories exercised real Git clone/fetch/push. No containers were
launched and no key files were read by the agent, copied or changed.

## Remaining proposals

- Docker Desktop needs a separate transport design; this slice explicitly refuses
  hosts unable to bind Unix sockets. Linux/WSL with native Docker is first.
- GitHub aliases, HTTPS/gh, Git LFS authentication, signing, and arbitrary SSH flags
  (including Git's -4/-6 switches) are outside this adapter's current contract.
- Additional reference cross-links and a tighter operation-deadline cap inside
  the bounded send loop were considered; the existing send timeout is 10 seconds
  and cancellation checks remain active. These are recorded follow-ups, not
  claims of implemented behavior.
- The inherited canonical socket positive path is not covered by a pure unit
  test; physical-host and recursive-launch acceptance remain required.

## Reviewer execution

Conversation `6280de13-6b45-4215-8e97-af6b466fbd61` used streaming JSON output.
The first redirected-stdin invocation failed to convey the brief; continuation
with an explicit brief path proceeded. The reviewer's CLI stalled after its full
gate had already returned. The implementor interrupted and continued that same
conversation with the committed round brief and a bounded print timeout. The
final response reported REVIEW_COMPLETE, the final shell marker was
ANTIGRAVITY_EXIT=0, and the commit and remote SHA were independently verified.
The aggregate JSON result retained an ERROR/idle-timeout from the earlier turn;
we therefore rely on observed commits/checks, not that aggregate status alone.
Scratch logs and virtual environments are not durable evidence. Briefs, the
assessment and validation counts are retained here. The reviewer worktree is
removed at pause; its pushed branch preserves all changes.

## Baseline failure IDs

- `tests/configuration/test_contract.py::test_second_checkout_cannot_inherit_the_first_checkouts_authority`
- `tests/configuration/test_contract.py::test_config_list_is_data_only_and_show_carries_the_review`
- `tests/test_capability_policy.py::test_cli_check_and_capability_mutation`
- `tests/test_host_daemon.py::test_unmountable_staging_fails_loudly`
- `tests/test_owner_commands.py::test_tool_edit_does_not_change_checkout_answers_when_not_ready[True]`
- `tests/test_recursive_orchestrator.py::test_public_dry_run_is_unique_redacted_and_cleans_owned_staging`
- `tests/test_recursive_orchestrator.py::test_contained_display_dry_run_forwards_no_host_x11`
- `tests/test_run_flow.py::test_a_second_checkout_is_registered_under_its_directory_name`
- `tests/test_run_flow.py::test_interactive_questions_record_answers_where_the_config_family_would`
- `tests/test_run_flow.py::test_save_with_pending_consent_writes_nothing[False-False]`
- `tests/test_run_flow.py::test_save_with_pending_consent_writes_nothing[False-True]`
- `tests/test_run_flow.py::test_save_with_pending_consent_writes_nothing[True-False]`
- `tests/test_run_flow.py::test_save_with_pending_consent_writes_nothing[True-True]`
- `tests/test_run_flow.py::test_partial_terminal_review_saves_no_answers[1\n]`
- `tests/test_run_flow.py::test_partial_terminal_review_saves_no_answers[1\nn\n]`
- `tests/test_runtime_entrypoint.py::test_entrypoint_rejects_unknown_adapters`
- `tests/test_trust.py::test_a_real_run_launches_on_the_homes_trust_alone`
- `tests/test_trust.py::test_trust_write_is_private_atomic_and_keeps_previous_record_on_failure`
- `tests/test_trust.py::test_terminal_acceptance_stays_staged_if_a_later_answer_is_missing`
