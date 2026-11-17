# Preserve Historical Links After Intake Disposition

From: project-management
To: maintenance
Date: 2026-11-17

The owner decided the init/config intake, now delivered to component-upgrades
with catalog support and further owner discussion required. Its intake file is
removed in the same commit as the decision log entry. Two maintenance-owned
records link to that former file. Please apply the narrow patch below to retain
the historical source at its immutable pre-disposition revision. No product
behavior or bug status changes. These files were not edited in this checkout.

Patch base: 9443bdc69d15df7514e13e8e3ded2f3a8720dd51

```diff
--- a/engineering-docs/wip/2026-09-18-maintenance/configuration-contract.md
+++ b/engineering-docs/wip/2026-09-18-maintenance/configuration-contract.md
@@ -458,7 +458,7 @@
   defaults are adopted architecture without a complete implemented interface.
 - The missing-platform-lock consumer experience and the exact project/local
   mutation boundary of regeneration retain the project-artifact ownership defined by the
-  [earlier owner-accepted interim behavior](../../wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-init-regenerate-versus-config-semantics.md).
+  [earlier owner-accepted interim behavior](https://github.com/mycodespace-ai/devcapsule/blob/9443bdc69d15df7514e13e8e3ded2f3a8720dd51/engineering-docs/wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-init-regenerate-versus-config-semantics.md).
   The owner's instruction to implement this contract supersedes the part that
   conflated reading an existing recommendation with local consent.
 - Identity relocation, fully specified retention/restore semantics and the
--- a/engineering-docs/bugs/devcapsule/2026-09-19-upgrade-config-recovery-rejects-its-own-remedy.md
+++ b/engineering-docs/bugs/devcapsule/2026-09-19-upgrade-config-recovery-rejects-its-own-remedy.md
@@ -228,7 +228,7 @@
 - [Recommended-base choice and override visibility](../../wip/2026-08-09-project-management/intake/2026-09-14-contained-display-config-offers-the-recommended-base.md).
 - [Listing by the project's configured schema](../../wip/2026-08-09-project-management/intake/2026-09-13-contained-display-config-list-renders-by-configured-schema.md).
 - [Upgrade experience as a V1 feature](../../wip/2026-08-09-project-management/intake/2026-09-03-component-catalog-upgrade-experience-as-a-v1-feature.md).
-- [Init/regenerate versus config semantics](../../wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-init-regenerate-versus-config-semantics.md).
+- [Init/regenerate versus config semantics](https://github.com/mycodespace-ai/devcapsule/blob/9443bdc69d15df7514e13e8e3ded2f3a8720dd51/engineering-docs/wip/2026-08-09-project-management/intake/2026-09-06-component-catalog-init-regenerate-versus-config-semantics.md).
 - [Earlier Hoare-standard remediation directive](../../archive/2026-08-06-recursive-e2e/CURRENT-STATUS.md) (directed item 3, deferred beyond v027).
 - [Client-upgrade compatibility requirement](../../requirements/devcapsule/r-compat-001-client-upgrades-require-no-user-action.md).
 - [Earlier closed resolution-refusal bug](2026-09-03-resolution-refusal-names-only-the-last-base-and-no-remedy.md): related pattern, different failure; its recorded closure is not reversed by this incident.
```
