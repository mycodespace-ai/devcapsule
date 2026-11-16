# Presentation authoring toolkit targets release 0.3.1

From: presentations
To: maintenance
Date: 2026-11-16

The owner authorized the reusable E2E recording/presentation kit and explicitly
selected release-0.3.1 as its PR base. The implementation branch is
ws-presentations/0.3.1-authoring, forked from upstream/release-0.3.1 at 10e7fda3.
It adds installed guide/export/hand-off commands, the shared producer and portable
Playwright support. The accepted viewer remains unchanged.

Implementation and local packaging/browser checks are complete. Requested Pair
Review with Antigravity gemini-4-hydrogen-high at effort high is pending the
implementation PR; the prescribed GitHub CLI is absent. No claim of release
readiness or integration is made. See presentations' published status and its
validation record. Its full local gate encounters the already-known recursive
Docker-group failure after 1438 passes; the focused, PEX, docs and console checks
passed.

Acknowledge this as an owner-directed 0.3.1 dependency awaiting review/integration.
Include the new authoring capability in release documentation when it lands.
Do not start a viewer redesign or duplicate the implementation in maintenance.
