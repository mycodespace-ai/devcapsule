# Workflow Gap: Commitments To A Release That Has No Version Yet

To: workflow-improvements
From: project-management
Date: 2026-11-16

The owner requires upgrades in the first release after 0.3.1, whether numbered
0.3.2 or 0.4.0, and asks whether the workflow provides a forcing function before
that release exists. Topic 2.4 defines gating as the next release not shipping;
topics 11 and 12 permit scope decisions, but do not specify a release-relative
target, its binding when a version is chosen, or its mandatory propagation to
release acceptance. The current next release (0.3.1) is explicitly excluded.

Under topic 3, project-management has recorded the owner's ordinal target in
its accepted decision and coordination backlog, added cut/acceptance checkpoints
to the project-owned release operator guide, and delivered the obligation to
component-upgrades and maintenance. This is procedural, not machine enforcement.
The generic definition and declared version are unchanged.

Please address the reusable gap: preserving and surfacing future release
commitments until bound to a concrete release, carrying them into scope and
acceptance, and requiring explicit owner amendments instead of silently dropping
them at a version change. Decide the generic representation and enforcement
in the workflow-owning workstream. No new tooling design or delivery deadline
for that improvement is selected here. The upgrade commitment stands meanwhile.

Source decision on ws-project-management/coordination:
engineering-docs/wip/2026-08-09-project-management/2026-11-16-decision-upgrades-next-release.md
