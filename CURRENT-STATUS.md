# Current Status

DevCapsule uses `workflow-type = "multiple-streams"`. On `main`, this file is
the record of workstreams that have begun but not ended, as of each one's last
integration. The live list is `devcapsule workflow list`, read from the
coordination branch. Detailed state belongs in each linked status file.

## Open Workstreams

| Name | Started | Goal | State | Branch association | Status file |
|---|---|---|---|---|---|
| `workflow-improvements` | 2026-08-09 | Improve the multiple-stream workflow from concrete dogfood findings during the recursive E2E cycle | active 2026-10-30; Pair Review Loop naming implemented and packaging verified for 0.3.0; mainline and release integration pending | `ws-workflow-improvements/v1` | [workstream status](engineering-docs/wip/2026-08-09-workflow-improvements/CURRENT-STATUS.md) |
| `project-management` | 2026-08-09 | Maintain project-wide priorities, sequencing, dependencies, and lifecycle coordination | paused 2026-10-11 at owner direction; consent and forced configuration before RC work; remaining diagnostics/image scope and release cut decisions retained | `ws-project-management/coordination` | [workstream status](engineering-docs/wip/2026-08-09-project-management/CURRENT-STATUS.md) |
| `maintenance` | 2026-09-18 | Own the defects no open workstream covers, on `main` and on maintained release lines, and drive maintenance releases | active; releasing 0.3.1; cut 2026-11-07 from `main` at `31e8fec7` by the owner's decision of the same day, version 0.3.1 on the branch, the overview, bug table and changelog written; `main` reopened at `0.3.2.dev0` (#8) and the branch merged (#9); candidate 0 published as `v0.3.1-rc0` on `8bcee1d0` and verified from the download; slices 1 (Eclipse amd64 libsoup repin, #10) and 2 (web console Files page, #12) merged 2026-11-08; candidate 1 on the owner's word; rulings open: executables for the Mac, the compatibility feed's home | `release-0.3.1`, the workstream's selection from the cut to the final tag; `release-0.3.0` closed and retained; earlier slice branches merged and closed | [workstream status](engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md) |
| `component-upgrades` | 2026-09-21 | Deliver component distribution channels, developer-owned version sets and proven upgrade rollback; Codex first | paused 2026-10-02; consent design ruled (D-0011 to D-0013), 0.2.16 consent slice next; R-UPGRADE-002 follow-up retained | `ws-component-upgrades/v1` | [workstream status](engineering-docs/wip/2026-09-21-component-upgrades/CURRENT-STATUS.md) |
| `sample-projects` | 2026-08-14 | Provide realistic sample projects as submodules that demonstrate ordinary adopter development inside DevCapsule | samples left the repository as submodules 2026-11-05; their future form is the owner's later decision | `ws-sample-projects/ai-learning` | [workstream status](engineering-docs/wip/2026-08-14-sample-projects/CURRENT-STATUS.md) |
| `contained-display` | 2026-08-19 | Own the capsule supervisor core (container entry process, supervised children, explicit session end, headless mode) and the capsule's own display environment, closing the host-session credential exposure — supervisor first, display as its first consumer | active; **the contained display shipped in v0.2.12 on 2026-09-14** (recipe-9 base, contained desktop by default, X11 passthrough behind `host-x11`); the X11 credential bug is resolved; remaining threads are records and follow-ups (reconnect, WSL2 opener, sample locks) | `ws-contained-display/display-transport` | [workstream status](engineering-docs/wip/2026-08-19-contained-display/CURRENT-STATUS.md) |
| `component-catalog` | 2026-08-30 | Maintain the optional IDE/tool catalog and shared noVNC/Playwright smoke harness | paused 2026-10-08; PRs #171 and #170 merged, the IntelliJ slice is on `main`; the pair moves to project-management | `ws-component-catalog/intellij-idea` | [workstream status](engineering-docs/wip/2026-08-30-component-catalog/CURRENT-STATUS.md) |
| `user-docs` | 2026-09-12 | Deliver V1 adopter documentation from first useful session through resuming work | paused 2026-09-28; 0.2.15 documentation merged in PR #151 and on docs-0.2.15; improvement list awaits the owner's decision | `ws-user-docs/first-session` | [workstream status](engineering-docs/wip/2026-09-12-user-docs/CURRENT-STATUS.md) |
| `website` | 2026-09-16 | Deliver the website autonomy experiment: repository-owned landing/docs/blog content, independently developable website submodule, local preview and publishing mechanism | paused 2026-09-30; producer migration merged in PR #152 and the versioned documentation live; W04-C, W09-C, W11-C retained | `ws-website/contract-v1` | [workstream status](engineering-docs/wip/2026-09-16-website/CURRENT-STATUS.md) |
| `capsule-webconsole` | 2026-10-09 | Serve a token-gated web console from every capsule: configuration, versions, info, live resources, later records and workflow state | active; work order accepted 2026-10-09; the first iteration, deliverables 1 and 2, is three stacked pull requests, #184, #186 and the runtime-and-base slice, each reviewed by the Codex pair; the owner merges | `ws-capsule-webconsole/first-slice` | [workstream status](engineering-docs/wip/2026-10-09-capsule-webconsole/CURRENT-STATUS.md) |
| `wrapped-projects` | 2026-11-02 | Wrap a foreign repository as a submodule of a small wrapper project and work on it in a capsule with three commands; FRC learning project first | active; PR1 (#333) accepted by the owner 2026-11-03, awaiting merge; the project-capabilities design handed to workflow-improvements | `ws-wrapped-projects/wrap` | [workstream status](engineering-docs/wip/2026-11-02-wrapped-projects/CURRENT-STATUS.md) |
| `macos-launcher` | 2026-11-03 | Run the DevCapsule launcher natively on Apple Silicon Macs against Docker Desktop, with capsules as `linux-amd64` under emulation | active 2026-11-03; slices 1 to 4 done, on `main` since #338; waits on the owner's rulings | `ws-macos-launcher/host-port` | [workstream status](engineering-docs/wip/2026-11-03-macos-launcher/CURRENT-STATUS.md) |
| `linux-arm64` | 2026-11-04 | Run capsules as `linux-arm64` as well as `linux-amd64`: natively on Apple Silicon Macs and on ARM Linux hosts | active 2026-11-04; on `main` since #338, arm64 base published; the follow-up turns `main`'s CI green; waits on the owner's rulings | `ws-linux-arm64/mirror-and-published-base` | [workstream status](engineering-docs/wip/2026-11-04-linux-arm64/CURRENT-STATUS.md) |
| `website` | 2026-09-16 | Deliver the website autonomy experiment: repository-owned landing/docs/blog content, independently developable website submodule, local preview and publishing mechanism | paused 2026-09-20 at owner request to switch to maintenance; experiment accepted, A−; blog integrated and published; content/parent-integration follow-ups remain | `ws-website/initial-cut`; renamed from `website/initial-cut`; preparation and backlog-handoff exceptions in status | [workstream status](engineering-docs/wip/2026-09-16-website/CURRENT-STATUS.md) |

Paused and blocked workstreams remain open until they conclude successfully or
unsuccessfully. The two exceptions are `project-management` and `maintenance`,
which every multiple-stream project reserves and keeps open for as long as the
mode lasts; see *The Reserved `project-management` Workstream* and *The
Reserved `maintenance` Workstream* in `WORKFLOW.md`.

## Coordination Baseline

The canonical public repository is
`https://github.com/mycodespace-ai/devcapsule`. This repository adopted the
multiple-stream workflow while the recursive E2E branch already existed and
while local `main` had diverged. The existing branch is therefore the one
documented naming and registration exception.

The workflow transition reached `main` through
[`PR #8`](https://github.com/ccozianu/devcapsule/pull/8) at merge revision
`b648623`; its date-prefixed layout and checkout-selection refinements reached
`main` through [`PR #9`](https://github.com/ccozianu/devcapsule/pull/9) at merge
revision `ed30a58`. Later workstreams register on their first `ws-<name>/` branch and publish to
the coordination branch, use `ws-<name>/` as the branch prefix, and use an
immutable ISO-start-date and name directory name for open-work and archive
records; the row here follows with the workstream's first integration.
Branches named under the older `<mnemonic>/` prefix are renamed by their own
workstreams before the next release candidate is tagged, per *Changes* in
`WORKFLOW.md`; after that they are outside the workflow.

`project-management` was opened on 2026-08-09 as a one-off permanent workstream
before the workflow defined one. On 2026-08-16 `workflow-improvements` made it
the general rule: every multiple-stream project reserves exactly one
`project-management` workstream, created when the mode is initialized or
adopted. This repository's instance is therefore no longer an exception in
substance. It keeps one narrow adoption exception: this repository adopted
`multiple-streams` on 2026-08-08 and created the reserved workstream on
2026-08-09, so its immutable start date is one day later than initialization.
`maintenance` was reserved by `workflow-improvements` on 2026-09-18 and
created the same day, under the adoption exception `WORKFLOW.md` defines for
projects that adopted the mode before it existed.

Other local or remote branch refs that predate this transition are inactive
legacy refs, not implicitly open workstreams. Do not resume work on one until
`main` first registers a workstream and its branch association under the new
protocol.

## Shared Constraints

- Keep host filesystem, credentials, Docker, devices, and networking exposure
  explicit and preserve `R-SCOPE-001`, `R-DOCKER-001`, and `R-PRODUCT-002`.
- Release sequencing: the v026 series and v0.2.7 (the new CLI, under the
  unified release identity decided 2026-08-26) are released; `recursive-e2e`
  concluded 2026-08-27 with its remaining items dissolved into the
  project-management coordination backlog. The contained-display release
  target is open under the unified versioning. See the
  [portfolio checkpoint](engineering-docs/wip/2026-08-09-project-management/2026-08-16-portfolio-checkpoint.md)
  and the [V1 scope ledger](engineering-docs/wip/2026-08-09-project-management/v1-scope-ledger.md).
- Bases stay agent-neutral per `D-0005`: no ambient agent CLI is installed and
  no agent credential or state directory is mounted by default. Agent CLIs are
  optional components that materialize per developer after explicit
  authorization. Base agent-absence checks remain correct and apply to every
  agent, including selected ones.
- V1 curates three agent components and lets the developer choose: Claude Code,
  OpenAI Codex, and Google Antigravity CLI. Selected 2026-08-16; see the
  [V1 scope ledger](engineering-docs/wip/2026-08-09-project-management/v1-scope-ledger.md).
  This is the deliberate selection `D-0005` anticipated, not a change to it.
- Gemini CLI is not a selected component. Do not install, configure, mount state
  for, or advertise it. This is a product-boundary choice; `D-0005` verified on
  2026-08-02 that Google had not deprecated it.
- Root `docs/` contains current user-facing documentation only. Workstream
  drafts stay beneath the selected engineering WIP directory.
- No workstream holds exclusive editing rights over any file. A workstream may
  edit any file its task genuinely requires. Exclusivity applies only where a
  documented locking protocol exists and is actually used for that file; no
  such protocol exists yet, so none may be inferred from a file's subject,
  directory, or the workstream that created it. Established 2026-08-15; see the
  [portfolio checkpoint](engineering-docs/wip/2026-08-09-project-management/2026-08-15-portfolio-checkpoint.md)
  and the [coordination backlog](engineering-docs/wip/2026-08-09-project-management/coordination-backlog.md).
