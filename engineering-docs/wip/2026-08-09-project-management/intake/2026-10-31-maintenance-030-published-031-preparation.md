# 0.3.0 published; 0.3.1 maintenance preparation

Date: 2026-10-31
From: maintenance
To: project-management, website

Acceptance PR #332 merged at main 31d44fa473a86f608110caa53ee38c6aef40a717.
Final v0.3.0 is published from accepted RC9 source 475427da033633ff5ee0e44e09face700630bf36.
Release: https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0
Publication: https://github.com/ccozianu/devcapsule/actions/runs/41188312058
Independent download verification passed: final version/source/checksum,
embedded mainline acceptance, and base/dependency/Python equality with RC9.

The test website workflow passed and the deployed site identifies 0.3.0 as
current, main 31d44fa4 as content, docs-0.3.0 at 7a813b80 as current guides.
Public candidate: website-candidate-41188626026-1
https://github.com/ccozianu/devcapsule/releases/tag/website-candidate-41188626026-1
The owner reviews the test site and promotes that exact candidate in the
website repository. Production promotion has not been performed by this pair.
No new website implementation is requested.

The release branch is closed and retained. At the owner's direction,
maintenance now selects ws-maintenance/0.3.1-preparation from main 31d44fa4,
which already carries 0.3.1.dev0. The queue is in its current status: release-
independent fixtures, October 25 documentation, cross-workstream C17/nine
proposal planning, Claude freshness and pending bug triage. No 0.3.1 release
branch or implementation slice has started. Prior scheduling mail remains
applicable; do not infer blanket acceptance of the nine proposals.

Durable evidence: engineering-docs/releases/v0.3.0/{README.md,final-verification.json,
final-manifest.json,website-verification.json}; live routing on coordination.
