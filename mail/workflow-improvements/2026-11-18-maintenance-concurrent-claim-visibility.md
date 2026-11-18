# Concurrent claims within one workstream

Maintenance hands over a workflow/tooling gap observed while delivering Graphviz
for 0.3.1 (PR56). The owner explicitly selected maintenance for this independent
slice while another pair delivered CLI, documentation and recursive-test fixture
slices in separate checkouts.

The tool stores one `state/maintenance/claim`. Claims replaced one another:
Graphviz's claim named the concurrent CLI pair, then the documentation and fixture
claims superseded it. Thus the brief's claim list alone did not show both active
slices. No source or recovery state in another checkout was touched. This pair
preserved the other pair's current claim and carries both handoffs in the live
status rather than clearing another checkout's claim at pause.

Evidence: maintenance's Graphviz section on ws-maintenance/graphviz-031, the
coordination history on 2026-11-17/18, and WORKFLOW.md topics 5.1 and 8.5.

Accepting this means clarifying how deliberately concurrent pairs in one
workstream publish presence and pause independently, and aligning claim/brief
behavior if needed. This does not select an implementation, priority or release.
