---
status: fixed
severity: blocking
target: 0.3.1
owner: component-catalog
opened: 2026-11-27
requirements: [R-UPGRADE-001]
---

# The pinned linux-amd64 .NET SDK prevents capsule creation

The RC4 preflight used the embedded-36 linux-amd64 catalog from PR #74 at release source `17f316697a3c9ae2dfb2954a8c41795b9a8a43fa`. The all-components test expects a running Xfce Terminal capsule with the catalog's .NET SDK and other components installed.

The first live test failed in project initialization because it supplied the VS Code download consent to Xfce Terminal. Maintenance verified a fixture correction that takes IDE-specific consents from the selected surface. With that correction the ordinary launcher reached formation and exited 2 before starting the desktop. The SDK archive contains a symbolic link at `./sdk/11.0.100/Extensions/ja/ja/Microsoft.TestPlatform.Extensions.BlameDataCollector.resources.dll`. The archive's SHA-256 equals the catalog pin `6fdb8822f47ccdba28f507dcd5d92e632d5b99cd27908d6838f0cc575be33baf`. The extractor at that revision permitted regular files and directories. It rejected this member.

The full build passed. The integration suite returned 459 passed, 13 skipped and one failure. The targeted Docker case with the fixture correction failed during formation. The [test-run record](../../releases/v0.3.1/test-runs.json) identifies the revision. Maintenance sent the fixture patch and both results to component-catalog in coordination mail `2026-11-27-maintenance-rc4-catalog-integration.md` at `cc15c87befd5`.

To close, deliver a compatible SDK installation and corrected surface consents. Preserve safe archive handling, run the all-components Docker case with the release executable, and verify the live component probes. Maintenance then reruns the full integration suite on the candidate revision and verifies main integration.

## Component-catalog correction

The pinned SDK contains 1,830 relative symlinks. All 1,830 name regular files in the same archive. The extractor checks each target against the archive’s regular files, extracts data into a fresh directory, and creates relative links last. Direct extraction of the pinned archive on linux-amd64 verified that all 1,830 links resolve to files within the installed SDK. A regression test failed before this correction and passed afterwards. The live fixture takes the IDE download consent from the selected surface. On fix revision `b1275f87`, the full integration suite passed (460 passed, 13 skipped), including launching the live Xfce Terminal capsule and probing .NET, the other components and the browser. The [test-run record](../../releases/v0.3.1/test-runs.json) records the environment and exact revision. The owner merges the fix into the release branch. Maintenance verifies the release revision, propagates it to main and closes the bug after that verification.

Maintenance repeated the full build and integration suite on release merge `b32ab2fa`. The live component probes passed. Main propagation and final verification are tracked in [PR #77](https://github.com/mycodespace-ai/devcapsule/pull/77).
