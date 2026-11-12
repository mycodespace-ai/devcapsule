# Schedule a design session: lightweight test-session timing history

From: human, relayed by the maintenance side conversation
To: project-management
Date: 2026-10-31

## Request

The owner asks project management to schedule a design session for a lightweight
mechanism to retain and compare how long unit-test, E2E and acceptance-test
sessions run. This requests design and scheduling, not implementation now.
Project management owns sequencing and allocation; no priority or release
target is assigned by this handoff.

## Evidence

pytest currently prints execution duration and nox prints overall session
elapsed time. Captured local/CI logs retain these figures, but inspection of
the current runners found no unified timing history or routine per-test
reporting. Acceptance timing is recorded selectively.

The RC9 downloaded-artifact verification record at
engineering-docs/wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/published/verification.json
(local maintenance evidence commit a8e62b3c) preserves 129.38 seconds for
8 E2E tests and 22.90 seconds for the shared-browser regression. Other local
main-integration logs report 148.33 seconds for 2,645 unit tests, 42.32 seconds
for 18 packaging tests, and 4.10 seconds for 374 web-console tests. These are
pytest times, not total environment preparation/build times.

## Design questions to settle with the owner

- Which session totals matter, and how to distinguish test execution from
  setup/build/download time and any human-driven acceptance time.
- The minimum context needed for useful comparisons: revision/artifact,
  suite, result/count, environment and relevant cache conditions.
- A low-overhead capture/storage/retention approach that reuses existing
  runner output where practical, plus a simple way to inspect trends.
- Whether per-test timing or slowdown alerts are useful initial scope or
  should be deferred.

Acceptance means acknowledging this as a scheduled design-session task in
project management's ordered work, with a recorded outcome defining the
smallest useful mechanism and who would implement it. No test reruns,
new service, dashboard, or release gate are requested by this item.
