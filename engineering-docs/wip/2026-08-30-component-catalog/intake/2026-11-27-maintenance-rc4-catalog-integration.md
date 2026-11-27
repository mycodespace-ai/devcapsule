# RC4 blocked by live catalog instantiation

From maintenance to component-catalog, 2026-11-27. The owner requested the next 0.3.1 candidate. The test and the new linux-amd64 SDK pin arrived in PR #74. Please deliver a validated correction to the release branch and notify maintenance for a fresh run.

The unmodified release preflight at `17f316697a3c9ae2dfb2954a8c41795b9a8a43fa` passed the full build. Integration returned 459 passed, 13 skipped, 1 failed. The live test selects Xfce Terminal, then project init rejects its undeclared vscode-download consent. VS Code already supplies its own consent in SURFACES. The proposed patch below removes that consent for other surfaces.

With the patch, initialization passes. A targeted rerun fails during materialization of the pinned linux-amd64 .NET SDK 11.0.100. The cached artifact matches its catalog SHA-256. Its ja/ja/Microsoft.TestPlatform.Extensions.BlameDataCollector.resources.dll entry is a symbolic link, whereas the existing directory extractor accepts regular files and directories. Resolve the catalog incompatibility preserving safe extraction. The checked-in component and its live probes must pass on the selected release revision. A skip or removal of the .NET probe would not establish compatibility.

Base: `17f316697a3c9ae2dfb2954a8c41795b9a8a43fa`. Only affected patch path: `devcapsule-src/tests/integration/test_all_components_instantiation.py`. No new files in the patch. The release driver retains the bug and run evidence.

```diff
diff --git a/devcapsule-src/tests/integration/test_all_components_instantiation.py b/devcapsule-src/tests/integration/test_all_components_instantiation.py
index 16905903..7c213c02 100644
--- a/devcapsule-src/tests/integration/test_all_components_instantiation.py
+++ b/devcapsule-src/tests/integration/test_all_components_instantiation.py
@@ -74,10 +74,9 @@ EXPECTED_NON_IDE_COMPONENTS: tuple[str, ...] = (
     "postgresql-client",
 )
 
-ALL_VENDOR_CONSENTS: tuple[tuple[str, str], ...] = (
+AGENT_DOWNLOAD_CONSENTS: tuple[tuple[str, str], ...] = (
     ("antigravity-download", "true"),
     ("claude-code-download", "true"),
-    ("vscode-download", "true"),
 )
 
 
@@ -204,7 +203,7 @@ def test_all_supported_components_instantiate_live_capsule(built_pex: Path, tmp_
         needs=(base_surface.needs[0], *non_ide),
         window_class=base_surface.window_class,
         ready_timeout=base_surface.ready_timeout,
-        consents=tuple(dict((*base_surface.consents, *ALL_VENDOR_CONSENTS)).items()),
+        consents=(*base_surface.consents, *AGENT_DOWNLOAD_CONSENTS),
     )
 
     run_id = uuid.uuid4().hex[:8]
```
