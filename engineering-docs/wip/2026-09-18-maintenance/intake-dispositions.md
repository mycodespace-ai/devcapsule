# Intake Dispositions: `maintenance`

What became of every item delivered to this workstream. Append-only, newest
last. Never pruned; travels with the workstream into the archive.

On `main`, every item ever delivered here is either still in `intake/`, meaning
undispositioned, or listed below, meaning resolved. Never both, never neither.

| Item | Dispositioned | Outcome | Note |
|---|---|---|---|
| `2026-09-21-workflow-improvements-definition-changed-please-publish.md` | 2026-09-21 | acknowledged | Fast-forwarded to main, read changed definition, took mail; publish at this checkpoint. Retired-outbox verification/deletion accepted after the owner-requested positioning handoff. |
| `2026-09-22-project-management-retire-run-image-print-command.md` | 2026-09-22 | acknowledged | Owner-selected bounded replacement accepted; later tested-patch mail supersedes the implementation request. Applied and validated on maintenance; see current status. |
| `2026-09-22-project-management-run-image-tested-patch.md` | 2026-09-22 | acknowledged | Exact checksum-verified patch applied after main synchronization; full gate passed. Maintenance owns source commit and PR delivery. Receipt commit `6c6f08f` and coordination `93d794a41882` preserve the diff; network defect remains open for legacy PyCharm. |
| `2026-09-22-project-management-drive-0-2-14-release.md` | 2026-09-22 | acknowledged | Accepted release driver; owner subsequently approved cut and progressive bug fixes/deferrals. See release overview. |
| `2026-09-22-project-management-release-working-documents.md` | 2026-09-22 | acknowledged | Accepted maintained release overview and bug table; integrated in PR #131 and now maintained on release-0.2.14. |
| `2026-09-26-project-management-init-discards-answers-bug.md` | 2026-09-26 | acknowledged | Blocking init bug taken as the 0.2.15 headline; fixed on this branch with tests, record carried here with status fixed. |
| `2026-09-26-project-management-release-0215.md` | 2026-09-26 | acknowledged | Maintenance drives 0.2.15 from `main` as `release-0.2.15`; superseded on scope by the fix-only item below. |
| `2026-09-26-project-management-release-0215-fix-only.md` | 2026-09-26 | acknowledged | 0.2.15 carries the init fix alone; cleanup candidates, surfaces and release notes move to 0.2.16. |
| `2026-09-27-project-management-0215-xtras-info-scope.md` | 2026-09-27 | acknowledged | Accepted xtras and host/runtime project info into 0.2.15; general guard repair remains non-gating. Supersedes fix-only scope. |
| `2026-09-27-project-management-0215-antigravity-default.md` | 2026-09-27 | acknowledged | Accepted always-proceed default with preservation of explicit choices and selected-version acceptance. |
| `2026-09-27-project-management-0215-claude-default.md` | 2026-09-27 | acknowledged | Accepted minimal pre-first-launch bypassPermissions settings and interactive first-use acceptance, extending the agent-defaults slice. |
| `2026-10-04-component-catalog-network-run-once-mismatch.md` | 2026-10-05 | acknowledged | Owner ruling: the documented command is supported on every project; its refusal on a project without a network recommendation is a bug, filed as `bugs/devcapsule/2026-10-05-run-once-network-authorization-needs-a-recommendation.md`, target 0.3.0. The local workflow text stands; the sender's `project init --authorize network host` workaround keeps working. |
| `2026-10-04-component-catalog-packaging-metadata-shadow.md` | 2026-10-05 | acknowledged | Owner accepted the bounded test patch: the packaging version check runs from the temp directory, so the editable egg-info in the source tree cannot shadow the embedded wheel. Applied on `ws-maintenance/post-0.2.15`; the three cases pass with the egg-info present. |
| `2026-10-04-component-catalog-packaging-shadow-followup.md` | 2026-10-05 | acknowledged | Confirms the shadow is a test-isolation problem, not a product bug; closed with the patch above. |
| `2026-10-05-component-catalog-conservative-writers-tolerant-readers.md` | 2026-10-05 | acknowledged | The maintenance part is a 0.3.0 requirement, folded into the in-capsule project-command work: read-only validation of the working-tree configuration, commands for every configuration change, and the owner's addition of the same day, `project config resolve --force` and `project run --force-config` with bash as the IDE of last resort. Principle and sequencing stay with project-management, mailed. |
| `2026-10-06-component-catalog-config-implementation.md` | 2026-10-08 | acknowledged | Owner-assigned implementation belongs to component-catalog; integrated through #170. Maintenance preserves that ownership and its configuration follow-ups; no duplicate implementation in the #172 review. |
| `2026-10-06-component-catalog-config-ready.md` | 2026-10-08 | acknowledged | Verified #170 merged at `6ae1a01`; incorporate the delivered contract on main synchronization after this stacked review. |
| `2026-10-06-component-catalog-configuration-format-names.md` | 2026-10-08 | acknowledged | Keep the existing argument as the historical `85bec27` snapshot. Update its links/names after this review stack integrates, recorded in the selected status file; the renames are already on main. |
| `2026-10-09-capsule-webconsole-project-info-checkout-name.md` | 2026-10-11 | acknowledged | Superseded by the item below. The owner directed the fix into capsule-webconsole on 2026-10-09, and `checkout_name_for` is on `main`. No maintenance work. |
| `2026-10-09-capsule-webconsole-project-info-checkout-name-taken-back.md` | 2026-10-11 | acknowledged | Both items closed together as superseded, as the sender asked. |
| `2026-10-11-project-management-maintenance-persistent-diagnostics.md` | 2026-10-11 | acknowledged | Owner assignment, not forwardable: persistent session diagnostics is maintenance work, target ready for 0.3.0, urgent. Accepted onto the plate as item 4; the first step is the bounded slice scope and acceptance with the owner. The work order text is at coordination `a535ccf`; project-management owes the committed file. |
| `2026-10-11-project-management-bootstrap-target-09.md` | 2026-10-18 | acknowledged | Owner decision, not forwardable: the ecosystem-bootstrap record is retargeted from 0.3.0 to 0.9 with the dated ruling, classification unchanged, and leaves the 0.3.0 plate; project-type templating stays a dependency sequenced by project-management. |
| `2026-10-11-project-management-pre-rc-sequence.md` | 2026-10-18 | acknowledged | Superseded by the owner's cut decision of 2026-10-18: consent is out of 0.3.0 and forced configuration is a slice of the candidate cycle; the scope clarifications it carries stand and are reflected in the plate. |
| `2026-10-18-project-management-release-0-3-0.md` | 2026-10-18 | acknowledged | Maintenance drives 0.3.0: `release-0.3.0` cut from `main` at `3c91183`, version 0.3.0 at `6965c5e`, the overview under releases/v0.3.0; the six dogfooding slices, the gates and the records are the plate. |

| `2026-10-29-project-management-october25-docs-to-031.md` | 2026-10-30 | acknowledged | Parts A/B retained for 0.3.1; canonical scheduling update follows the CI slice; language review, C16 and C20 unchanged. |

| `2026-10-30-project-management-ci-path-gating-and-diff-coverage-030.md` | 2026-10-30 | acknowledged | Accepted for immediate 0.3.0 implementation with owner decisions 1B/2B and Claude Fable 5.1 Pair Review. |

| `2026-10-30-workflow-improvements-pair-review-loop-030.md` | 2026-10-30 | acknowledged | Accepted for 0.3.0; apply supplied release patch in a separate slice after CI review settles; PR #309 verified on main. |

| `2026-10-30-project-management-user-docs-0-3-0-cli-alignment.md` | 2026-10-30 | acknowledged | Accepted for immediate 0.3.0 execution across five `<= 10`-file Pair Review batches (`Antigravity` + `Codex / gpt-6-astra`) on `release-0.3.0`: file-by-file 0.3.0 CLI alignment, full 0.3.0 authoring of all 12 `status: planned` stubs, and human-English prose cleanup; PR #316 verified on `main` at `ebab228a`. |
| `2026-11-10-project-management-console-video-does-not-play-from-files.md` | 2026-11-16 | acknowledged | Acknowledged; the bug record is on `release-0.3.1` with `status: fixed` and `target: 0.3.1` after PR #35 (`6ff6bf18`), awaiting browser verification before closure. |

| `2026-11-16-github-auth-release-delivery.md` | 2026-11-17 | acknowledged | PR #47 merged; preserve main development version, manifest and three main-only documents during propagation; two inherited unit failures remain disclosed. |
| `2026-11-16-github-auth-rootless-propagation.md` | 2026-11-17 | acknowledged | Superseded by completed rootless propagation through PR #42 to main; preserve owner-verified release closure. |
| `2026-11-16-presentations-authoring-for-0-3-1.md` | 2026-11-17 | acknowledged | Accepted 0.3.1 dependency; PR #43 awaits human merge; no duplicate implementation. |
| `2026-11-16-presentations-reviewed-authoring-pr-43.md` | 2026-11-17 | acknowledged | Reviewed deliverable accepted for the release; verified PR #43 open with successful checks on 2026-11-17. |
| `2026-11-16-project-management-upgrades-next-release.md` | 2026-11-17 | acknowledged | Mandatory first release after 0.3.1 (0.3.2 or 0.4.0); retain next-cut obligation; not a 0.3.1 gate. |
| `2026-11-16-release-merge-validation.md` | 2026-11-17 | acknowledged | Accepted known failures into release validation follow-up; fresh rc3 preflight recorded in release overview and test-run record. |
| `2026-11-17-project-management-disposed-intake-links.md` | 2026-11-17 | acknowledged | Applied the two immutable historical-link repairs without changing bug status. |
| `2026-11-17-project-management-maintenance-intake-decisions.md` | 2026-11-17 | acknowledged | Every-release all-component sweep accepted, including 0.3.1 acceptance; deferred upgrades require next-release bugs. Sample-project release gate accepted for later design; first enforcing release remains undecided. Full work order retained at receipt commit 579d0e6a. |

| `2026-11-17-presentations-rc4-skill.md` | 2026-11-17 | acknowledged | PR #50 merged into release; retain release propagation, candidate validation and rc4 tagging in maintenance. Receipt 52154b3f; automatic setup supersedes initial manual instructions. |
| `2026-11-17-presentations-direct-skill-install.md` | 2026-11-17 | acknowledged | Historical PR #50 delivery accepted; installation guidance superseded by automatic setup in #51 and the reviewed CLI work order. Receipt 52154b3f. |
| `2026-11-17-presentations-automatic-skill-setup.md` | 2026-11-17 | acknowledged | PR #51 merged at release 7ad956d4; automatic setup accepted for rc4 validation. Native discovery remains unverified; full-kit installation and command removal remain pending under the CLI work order. Receipt 52154b3f. |
| `2026-11-25-project-management-launcher-base-contract-bug.md` | 2026-11-27 | acknowledged | Maintenance accepts the 0.3.1 launcher/base compatibility triage, specification and verification task. Original notice received at 2b7bc5b6. |
| `2026-11-27-component-catalog-rc4-sdk-fix.md` | 2026-11-27 | acknowledged | Verified the merged SDK correction at `b32ab2fa` in the release suite. PR #77 carries this revision and its passing test record into main. |
