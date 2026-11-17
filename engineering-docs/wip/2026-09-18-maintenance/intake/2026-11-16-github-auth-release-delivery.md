# SSH proxy release delivery and main propagation constraint

From: github-auth
To: maintenance
Date: 2026-11-16

The owner directed SSH proxy to release-0.3.1 and asked to finish Pair Review.
Review PR #44 is merged at 9638cb11 after acceptance of 455d3acc. Implementation
PR #47 now targets release-0.3.1. The human merges it; maintenance owns the
release and its subsequent propagation to main.

Evidence: ws-github-auth/ssh-proxy at 3ed31a87, especially
engineering-docs/wip/2026-11-16-github-auth/evidence/2026-11-16-final-review.md.
64 focused cases passed. Full gate: 3320 passes and two inherited failures in
tests/test_recursive_orchestrator.py, test_public_dry_run_is_unique_redacted_and_cleans_owned_staging
and test_contained_display_dry_run_forwards_no_host_x11. Both reject Docker gid 0.
These are a subset of the already delivered release-merge validation failures.
Types/conventions, CLI smoke, PEX build/smoke, docs contract and 474 console tests
passed. Rebuilt-PEX authenticated read with an empty HOME and missing-socket
control passed. No new Docker container or GitHub write was performed.

Main propagation needs deliberate preservation because this pushed branch retains
its original mainline ancestry. The release-target tree uses version 0.3.1 and
release docs/versions.yaml. Its cleanup excludes three documents that belong only
to current main. When propagating to main, retain main's development version,
docs manifest and these documents plus their blog/index entries:

- engineering-docs/blog/2026-11-13-thirteen-hours-thirty-five-tests.md
- engineering-docs/implementation-notes/devcapsule/2026-11-08-testing-the-macos-launcher-on-cloud-mac-hardware.md
- engineering-docs/work-orders/2026-11-08-test-improvements.md

Do not let an ordinary automatic merge propagate those release-side removals as
mainline deletions. This is a constraint of the existing branch history, not an
instruction to switch workstreams or perform a release merge now.
Acknowledgement means retaining the preservation constraint in release/main
integration work and the two remaining known test failures in acceptance review.
