# Intake Dispositions: `component-catalog`

What became of every item delivered to this workstream. Append-only, newest
last. Never pruned; travels with the workstream into the archive.

On `main`, every item ever delivered here is either still in `intake/`, meaning
undispositioned, or listed below, meaning resolved. Never both, never neither.

The note is one line. The reasoning is in this workstream's
[handoff](CURRENT-STATUS.md). See *The Disposition Log* in `WORKFLOW.md`.

| Item | Dispositioned | Outcome | Note |
|---|---|---|---|
| `2026-09-08-project-management-sync-item-never-arrived.md` | 2026-09-09 | acknowledged; completed | Corrected the historical delivery claim in the final archive and preserved original commit 802adafa; reconstructed alternatives are identified separately. |
| `2026-10-01-project-management-ide-surfaces-are-yours.md` | 2026-10-03 | acknowledged | IntelliJ IDEA is the next task, targeted at 0.2.16; new surfaces belong here, orchestration stays with component-upgrades, Eclipse remains unscheduled; historical Antigravity freeze lifted. |
| `2026-09-21-workflow-improvements-definition-changed-please-publish.md` | 2026-10-03 | acknowledged | Continuation starts at current main; current definition and local rules read, mail taken and live state published. Legacy outbox reconciliation is retained in Open Threads before any legacy-ref removal. |
| `2026-10-09-project-management-github-cli-component.md` | 2026-11-18 | acknowledged | Queued the GitHub CLI component and its auth design after the terminal. |
| `2026-11-17-project-management-component-catalog-intake-decisions.md` | 2026-11-18 | acknowledged | Recorded the release sweep, V1 validation and configuration support, terminology audit and evidence responsibilities in the handoff. |
| `2026-11-25-project-management-component-version-upgrades-sweep.md` | 2026-11-25 | acknowledged | Active first slice on `ws-component-catalog/version-upgrades` targeting `release-0.3.1`: check all existing catalog components and deliver updated pins and sweep outcomes. |
| `2026-11-25-project-management-gh-cli-component.md` | 2026-11-25 | acknowledged | Activated for `release-0.3.1` after version-upgrades sweep: add `gh` optional component with checksum-pinned artifacts, channel probe, isolated auth persistence, smoke, and docs. |
| `2026-11-25-project-management-gcloud-cli-component.md` | 2026-11-25 | acknowledged | Queued for `release-0.3.1` after `gh`: add `gcloud` optional component (separate from unselected Gemini CLI) with checksum-pinned artifacts, probe, auth persistence, smoke, and docs. |
