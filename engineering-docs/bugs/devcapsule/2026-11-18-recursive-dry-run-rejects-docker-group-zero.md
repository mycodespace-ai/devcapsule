---
status: fixed
severity: minor
target: 0.3.1
owner: maintenance
opened: 2026-11-18
requirements: [R-PRODUCT-002]
---

# Recursive dry-run staging rejects a valid Docker socket group

The older recursive dry-run preparation rejects Docker socket group 0 before
staging. This is valid for rootless namespace mappings and Docker Desktop.
In the owner's capsule, both the real socket and the fixture socket have gid 0;
namespace gid 0 maps to host gid 1000. The independent successor launcher already
supports rootless identity 0:0, so successful recursive E2E does not exercise
this old staging restriction.

Accept non-negative integer Docker groups and reuse the existing root group
when the socket group is 0. Keep invalid-value rejection and the separate runtime
identity/sudo-group checks. Retire the six-test legacy orchestration file into
integration. Preserve cleanup, redaction, metadata/readiness and display checks;
require the actual oversized-Xauthority error in failure scenarios.

Verification: the unchanged source produced two failures; a temporary copy
without the positive Docker-group guard passed both. The corrected integration
module passes 12 cases, including explicit gid 0/998/1000 and rejection of
negative, boolean and fractional IDs. No socket chown, skip or xfail is needed.

Delivery is on `ws-maintenance/recursive-test-fixture` for `release-0.3.1`.
Main has the same affected implementation. Main propagation remains pending
release integration; a release-only merge does not close that disposition.
The old dry-run command's separate positive runtime UID/GID restriction is
unchanged; this fix does not claim that command supports rootless identity 0:0.
