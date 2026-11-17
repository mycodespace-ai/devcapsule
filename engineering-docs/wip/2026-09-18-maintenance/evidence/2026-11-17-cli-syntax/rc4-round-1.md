# RC4 review round 1: exact origin comparison

Read the Round 1 assessment on PR54. Report your docs-contract check as skipped
(the website was uninitialized), not passed.

Continue the same Antigravity gemini-4-hydrogen review conversation and checkout.
The original RC4 brief's scope, authorship and delivery rules remain binding.

The implementor read the two-file review diff. Accept the direct formatter tests
and project-root normalization as defensive helper handling (the CLI already
resolves its root, so do not claim a demonstrated CLI failure for that change).

Fix one concrete issue in the implementation being reviewed: both origin keys
use `parsed.port or default_port`, which equates explicit port 0 with omitted
port 80/443. The work order requires current-console origin equality. Use the
scheme default only when `.port is None`; retain any explicit numeric port as
part of the key. Add regressions rejecting mismatched explicit-zero/default-port
origins in BOTH directions and retaining the existing omitted-versus-explicit
80/443 equivalence. Demonstrate the new regression fails before the correction.
No broader URL redesign, route additions or domain changes.

Run the focused formatter unit tests and CLI integration tests, then the full
build with the original explicit diff base and scratch. The three known local
unit failures are still not waived. Packaging/console already ran for your prior
revision; do not repeat those unrelated sessions for this origin-key correction.
Commit and push to your existing review PR, update its report and reply to the
assessment with the before/after regression evidence, test audit and final
counts. Do not merge or touch implementor records. Final line is your review PR
comment URL. Stop on a real blocker.
