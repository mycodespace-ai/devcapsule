# Documentation Index

Status: maintained index of repository markdown documentation.

When adding, deleting, or renaming permanent `.md` files, update this index in
the same change. In multiple-stream mode, this index lists each workstream
status file; internal WIP/archive documents use the local index in that status.

## Start Here

- [DevCapsule — why try it?](README.md)
- [For developers](DEVELOPING.md)
- [Releasing a new DevCapsule version](engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md)
- [Current status and handoff](CURRENT-STATUS.md)
- [Documentation index](index.md)
- [Agent instructions](AGENTS.md)
- [Claude compatibility pointer](CLAUDE.md)
- [Requirements overview and index](REQUIREMENTS.md)
- [Human / agent workflow](WORKFLOW.md)
- [Human / agent workflow: the reasons, for humans](WORKFLOW-humane.md)
- [This project's local workflow](WORKFLOW-LOCAL.md)
- [This project's local workflow: the reasons, for humans](WORKFLOW-LOCAL-humane.md)
- [Product documentation](docs/README.md), versioned per release under the content–website contract; pages marked *coming soon* are planned stubs
  - Getting started: [Install](docs/getting-started/install.md), [Your first session](docs/getting-started/first-session.md), [Stop and come back](docs/getting-started/stop-and-come-back.md)
  - Your project: [An existing repository](docs/your-project/existing-repository.md), [A new project](docs/your-project/new-project.md), [Someone else's repository](docs/your-project/someone-elses-repository.md), [What a project declares](docs/your-project/declare-needs.md) (coming soon), [Services and ports](docs/your-project/services-and-ports.md) (coming soon)
  - Working with AI: [Choose an agent](docs/working-with-ai/choose-an-agent.md), [Sign in and defaults](docs/working-with-ai/sign-in-and-defaults.md), [Instructions for agents](docs/working-with-ai/instructions-for-agents.md), [Hosted and local models](docs/working-with-ai/hosted-and-local-models.md) (coming soon), [Review and change agents](docs/working-with-ai/review-and-change-agents.md) (coming soon)
  - Everyday development: [Clipboard, keys and browser](docs/everyday-development/clipboard-and-browser.md); coming soon: [IDEs and terminals](docs/everyday-development/ides-and-terminals.md), [Git](docs/everyday-development/git.md), [Run, debug, test](docs/everyday-development/run-debug-test.md), [Previews and ports](docs/everyday-development/previews-and-ports.md)
- [Configuration](docs/configuration/index.md)
  - Configuration: [The configuration home](docs/configuration/home.md), [Inspect a checkout](docs/configuration/inspect.md), [Project versus personal](docs/configuration/project-versus-personal.md), [Capabilities and personal choices](docs/configuration/capabilities.md), [Extra tools](docs/configuration/extra-tools.md), [Resource limits](docs/configuration/resource-limits.md), [Software approvals](docs/configuration/software-approvals.md), [IDE preferences](docs/configuration/ide-preferences.md) (coming soon)
  - Containment: [The boundary](docs/containment/the-boundary.md), [Granting and withdrawing access](docs/containment/granting-and-withdrawing.md)
  - Sessions: [Start, stop, reconnect](docs/sessions/start-stop-reconnect.md), [What persists](docs/sessions/what-persists.md), [The web console](docs/sessions/web-console.md); coming soon: [Several projects](docs/sessions/several-projects.md), [Another machine](docs/sessions/another-machine.md)
  - Collaboration: [Work in workstreams with humans and agents](docs/collaboration/working-in-workstreams.md)
  - Updates: [Supported versions](docs/updates/supported-versions.md), [Launcher updates](docs/updates/launcher-updates.md), [Component freshness](docs/updates/component-freshness.md), [Component upgrades](docs/updates/component-upgrades.md)
  - Troubleshooting: [First session](docs/troubleshooting/first-session.md), [Diagnostics and logs](docs/troubleshooting/diagnostics-and-logs.md); coming soon: [Cleanup and uninstall](docs/troubleshooting/cleanup-and-uninstall.md)
  - Platforms: [Linux](docs/platforms/linux.md), [Windows via WSL2](docs/platforms/windows-wsl2.md), [macOS](docs/platforms/macos.md)
  - Reference: [Configuration nodes](docs/reference/configuration-nodes.md); coming soon: [Command reference](docs/reference/cli.md), [project info fields](docs/reference/project-info.md)
- [Engineering documentation](engineering-docs/README.md)

## Development

- [Development: how DevCapsule is built and tested](engineering-docs/development/README.md)
- [Developer environment](engineering-docs/development/developer-environment.md)
- [Source layout](engineering-docs/development/source-layout.md)
- [Unit tests](engineering-docs/development/unit-tests.md)
- [Integration tests](engineering-docs/development/integration-tests.md)
- [End-to-end tests](engineering-docs/development/e2e-tests.md)
- [Running E2E scenario recordings from a shell with nox](engineering-docs/development/running-e2e-scenario-recordings.md)
- [Pair Review Loop](engineering-docs/development/review-partner-loop.md)

## Releases

- [0.3.0 release notes](engineering-docs/releases/v0.3.0/notes.md)
- [0.2.15 release notes](engineering-docs/releases/v0.2.15/notes.md)
- [0.2.14 release notes](engineering-docs/releases/v0.2.14/notes.md)

- [0.3.0 release work, scope and candidates](engineering-docs/releases/v0.3.0/README.md)
- [0.3.0 changelog since 0.2.15](engineering-docs/releases/v0.3.0/changelog.md)
- [0.3.0 bug table](engineering-docs/releases/v0.3.0/bugs.md)
- [0.2.15 release work, scope and agent validation](engineering-docs/releases/v0.2.15/README.md)
- [0.3.0 accepted-candidate promotion record](engineering-docs/releases/v0.3.0.json)
- [0.2.15 accepted-candidate promotion record](engineering-docs/releases/v0.2.15.json)
- [0.2.14 release work and checklist](engineering-docs/releases/v0.2.14/README.md)
- [0.2.14 bug triage](engineering-docs/releases/v0.2.14/bugs.md)
- [0.2.14 RC0 smoke scripts and walkthrough](engineering-docs/releases/v0.2.14/smoke/README.md)
- [0.2.14 RC0 validation stories and contracts](engineering-docs/releases/v0.2.14/smoke/stories.md)
- [0.2.14 RC0 smoke results template](engineering-docs/releases/v0.2.14/smoke/results-template.md)

## Website

- [Website development and preview](website/README.md)
- [Website publication](website/PUBLISHING.md)
- [Website-owned backlog and producer dependencies](website/BACKLOG.md)
- [How the website is published, and what it still lacks](engineering-docs/implementation-notes/website/2026-09-22-website-publishing-contract.md)

## Root Requirement Records

- [Conservative configuration writers and tolerant readers](engineering-docs/requirements/product/r-config-001-conservative-writers-tolerant-readers.md) — R-CONFIG-001, accepted 0.3 direction.
- [R-WRAP-001 Wrapped projects](engineering-docs/requirements/product/r-wrap-001-wrapped-projects.md)
- [R-CONSOLE-001 Every capsule serves a web console](engineering-docs/requirements/product/r-console-001-capsule-web-console.md)
- [R-UPGRADE-001 Local Component Upgrades And Recoverable Version Sets](engineering-docs/requirements/product/r-upgrade-001-component-version-sets.md)
- [R-UPGRADE-002 Component Status Operational Reliability](engineering-docs/requirements/product/r-upgrade-002-status-operational-reliability.md)

- [R-PRODUCT-001 Batteries-Included IDE Environments](engineering-docs/requirements/product/r-product-001-batteries-included-ide-environments.md)
- [R-PRODUCT-002 Explicit Host Boundaries](engineering-docs/requirements/product/r-product-002-explicit-host-boundaries.md)
- [R-PRODUCT-003 Durable Human/Agent Project Memory](engineering-docs/requirements/product/r-product-003-durable-human-agent-project-memory.md)
- [R-PRODUCT-004 Reusable Human/Agent Workflow](engineering-docs/requirements/product/r-product-004-reusable-human-agent-workflow.md)
- [R-PRODUCT-005 Incremental Human/Agent Execution Loop](engineering-docs/requirements/product/r-product-005-incremental-human-agent-execution-loop.md)
- [R-PRODUCT-006 Multiple Human/Agent Workstream Coordination](engineering-docs/requirements/product/r-product-006-multiple-workstream-coordination.md)
- [R-DOCS-001 Root Documentation Stays Implementation-Agnostic](engineering-docs/requirements/product/r-docs-001-root-documentation-stays-implementation-agnostic.md)
- [R-DOCS-002 Current User Docs Show Current Interfaces](engineering-docs/requirements/product/r-docs-002-current-user-docs-show-current-interfaces.md)
- [R-DOCS-003 Website Content Carries Explicit Front Matter And A Versions Manifest](engineering-docs/requirements/product/r-docs-003-website-content-carries-front-matter.md)
- [R-SETTINGS-001 Per-IDE Profile Prototype](engineering-docs/requirements/product/r-settings-001-per-ide-profile-prototype.md)
- [R-GTM-001 Compelling V1 Announcement For Adopters](engineering-docs/requirements/product/r-gtm-001-compelling-v1-announcement-for-adopters.md)

## Component Upgrades

- [Component status service contract and operations](component-status/README.md)

- [Component upgrade and recovery validation](engineering-docs/implementation-notes/devcapsule/2026-09-21-component-upgrades-validation.md)
- [Capability configuration: implementation and test correctness](engineering-docs/implementation-notes/devcapsule/2026-10-06-configuration-correctness.md)
- [Capability configuration: persistent selection versus execution projection](engineering-docs/implementation-notes/devcapsule/2026-10-08-configuration-composition-correctness.md)
- [Scenario-driven E2E IDE controller and pause-free WebM video recorder](engineering-docs/implementation-notes/devcapsule/2026-10-21-e2e-scenario-video-recorder.md)
- [Eclipse Java component and recorded smoke validation](engineering-docs/implementation-notes/devcapsule/2026-10-04-eclipse-validation.md)
- [Linux .NET SDK and Rider validation](engineering-docs/implementation-notes/devcapsule/2026-10-04-dotnet-rider-validation.md)
- [IntelliJ, Playwright and graphical smoke validation](engineering-docs/implementation-notes/devcapsule/2026-10-04-intellij-playwright-validation.md)
- [Image layers, the local cache, and how the final image is composed](engineering-docs/implementation-notes/devcapsule/2026-10-06-image-layers-local-cache-and-composition.md)

- [Distribution channel contract and implementation](engineering-docs/implementation-notes/devcapsule/2026-09-21-component-distribution-channels.md)

## Design Decisions

- [D-0010 Developer-Owned Component Version Sets And Recovery](engineering-docs/decisions/product/d-0010-developer-owned-version-sets.md)
- [D-0011 Vendor Terms And Trust Are Given Once Per Configuration Home, Bound To A Verified Channel](engineering-docs/decisions/product/d-0011-vendor-trust-once-per-configuration-home.md)
- [D-0012 Host Access Is Asked Only When The Project Recommends The Less Secure Value](engineering-docs/decisions/product/d-0012-host-access-asked-only-when-recommended.md)
- [D-0013 A Provenance Sidecar Beside Each Checkout Records Which Client Wrote It](engineering-docs/decisions/product/d-0013-provenance-sidecar-for-local-records.md)
- [D-0014 The IDE Role Stays As It Is, Or Generalizes To An Entry Point That Owns The Container's Lifetime](engineering-docs/decisions/product/d-0014-entry-point-generalizes-the-ide-role.md) (proposed, in scope for V1)
- [D-0015 A Project Constrains Its Base Directly, Not Through Capabilities Or Components](engineering-docs/decisions/product/d-0015-a-project-constrains-its-base-directly.md) (proposed, in scope for V1)
- [D-0016 A Required IDE Stays Required; One Launch May Depart From It Explicitly](engineering-docs/decisions/product/d-0016-explicit-launch-departure-from-a-required-ide.md) (accepted 2026-10-28)

- [Decision record template](engineering-docs/decisions/product/_template.md)
- [D-0001 Capability-First CLI Model](engineering-docs/decisions/product/d-0001-capability-first-cli-model.md)
- [D-0004 Configuration Resolution And Guided Run Experience](engineering-docs/decisions/product/d-0004-configuration-resolution-and-guided-run.md)
- [D-0005 Agent-Neutral Base And Optional Agent Components](engineering-docs/decisions/product/d-0005-agent-neutral-base-and-optional-agent-components.md)
- [D-0006 One Module For Host And Platform Friction](engineering-docs/decisions/product/d-0006-host-platform-friction-module.md)
- [D-0007 Resolution Matrix As Accumulated Verified Combinations](engineering-docs/decisions/product/d-0007-resolution-matrix-model-and-interface.md)
- [D-0008 Known-Good Checkout Configuration History](engineering-docs/decisions/product/d-0008-known-good-configuration-history.md)
- [D-0009 One Executable Outside And Inside The Container](engineering-docs/decisions/product/d-0009-launcher-delivers-identical-runtime.md)

## Specifications

- [The content–website contract, version 1](engineering-docs/specifications/product/content-website-contract.md)
- [IDE profile prototypes](engineering-docs/specifications/product/ide-profile-prototypes.md)
- [DevCapsule V1 state and persistence](engineering-docs/specifications/product/state-and-persistence.md)
- [Project workflow bootstrap](engineering-docs/specifications/product/project-workflow-bootstrap.md)

## Work Orders

- [Wrapped projects: a foreign repository as a submodule, three commands](engineering-docs/work-orders/2026-11-02-wrapped-projects.md)
- [0.3.0 user documentation CLI alignment, full stub authoring, and prose review — maintenance, 0.3.0](engineering-docs/work-orders/2026-10-30-user-docs-0-3-0-cli-alignment.md)
- [CI path gating and advisory diff coverage — maintenance, 0.3.0](engineering-docs/work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md)
- [Structural guardrails for the repository with ast-grep](engineering-docs/work-orders/2026-10-29-ast-grep-guardrails.md)
- [Explicit IDE requirement override](engineering-docs/work-orders/2026-10-28-explicit-ide-requirement-override.md)
- [The manifest's two schemas as classes; `init --regenerate` migrates](engineering-docs/work-orders/2026-10-26-manifest-schemas-as-classes.md)
- [Orientation, concepts, persistence and recipes in the documentation](engineering-docs/work-orders/2026-10-25-documentation-orientation-and-concepts.md)
- [Redesign the project config and project run experience (draft)](engineering-docs/work-orders/2026-10-24-cli-ux-redesign.md)

- [Saved Docker arguments for each checkout](engineering-docs/work-orders/2026-10-23-saved-docker-arguments.md)

- [Persistent checkout environment for 0.3.0](engineering-docs/work-orders/2026-10-23-checkout-environment.md)

- [Capture the Eclipse/Java “WOW factor” 1BRC hero demonstration video](engineering-docs/work-orders/2026-10-19-eclipse-java-1brc-hero-video.md)
- [Make “Why DevCapsule?” clear on arrival](engineering-docs/work-orders/2026-10-18-landing-page-why-devcapsule.md)
- [The capsule web console](engineering-docs/work-orders/2026-10-09-capsule-webconsole.md)
- [Persistent session diagnostics — maintenance work order for 0.3.0](engineering-docs/work-orders/2026-10-08-persistent-session-diagnostics.md)
- [Playwright, IntelliJ IDEA and reusable agent-driven IDE smoke](engineering-docs/work-orders/2026-10-03-playwright-intellij-agent-smoke.md)
- [The website, seen from the visitor's chair](engineering-docs/work-orders/2026-09-28-website-visitor-experience.md)
- [The visitor content and the producer migration](engineering-docs/work-orders/2026-09-28-visitor-content-and-producer-migration.md)
- [0.2.15 extra tools, project information and agent defaults](engineering-docs/work-orders/2026-09-27-project-environment-discovery.md)

- [Workflow installation during onboarding](engineering-docs/work-orders/2026-09-24-workflow-installation-onboarding.md)

- [Legacy launch capability decisions — blocks V1](engineering-docs/work-orders/2026-09-22-legacy-launch-capability-disposition.md)

- [Component upgrades and recoverable version sets](engineering-docs/work-orders/2026-09-21-component-upgrades.md)

- [Release 0.3.0](engineering-docs/work-orders/2026-10-18-release-0-3-0.md) — the cut, the dogfooding slices of the candidate cycle, and the gates before the final tag.
- [DevCapsule website autonomy experiment](engineering-docs/work-orders/2026-09-16-website-autonomy.md)
- [Base images as a contract, design experiment](engineering-docs/work-orders/design-experiment-work-order.md)

## Workstream Status

- [Multiple-stream workflow successful archive](engineering-docs/archive/2026-08-08-multi-workflow/CURRENT-STATUS.md)
- [Recursive dogfood E2E successful archive](engineering-docs/archive/2026-08-06-recursive-e2e/CURRENT-STATUS.md)
- [Eclipse interactive surface, concluded 2026-10-01 and folded into component-catalog](engineering-docs/archive/2026-09-09-eclipse-surface/CURRENT-STATUS.md)
- [Project management current status](engineering-docs/wip/2026-08-09-project-management/CURRENT-STATUS.md)
- [Workflow improvements current status](engineering-docs/wip/2026-08-09-workflow-improvements/CURRENT-STATUS.md)
- [Component upgrades current status](engineering-docs/wip/2026-09-21-component-upgrades/CURRENT-STATUS.md)
- [Maintenance current status](engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md)
- [Capsule web console current status](engineering-docs/wip/2026-10-09-capsule-webconsole/CURRENT-STATUS.md)
- [Wrapped projects current status](engineering-docs/wip/2026-11-02-wrapped-projects/CURRENT-STATUS.md)
- [macOS launcher current status](engineering-docs/wip/2026-11-03-macos-launcher/CURRENT-STATUS.md)
- [linux-arm64 capsules current status](engineering-docs/wip/2026-11-04-linux-arm64/CURRENT-STATUS.md)
- [Sample demo projects current status](engineering-docs/wip/2026-08-14-sample-projects/CURRENT-STATUS.md)
- [Contained display current status](engineering-docs/wip/2026-08-19-contained-display/CURRENT-STATUS.md)

- [User documentation current status](engineering-docs/wip/2026-09-12-user-docs/CURRENT-STATUS.md)
- [Website autonomy experiment current status](engineering-docs/wip/2026-09-16-website/CURRENT-STATUS.md)

## Engineering Design Notes

- [Spike: driving the getting-started scenario through pixels](engineering-docs/design-notes/devcapsule/2026-09-30-pixel-driven-getting-started-acceptance.md)
- [Base images: how one is chosen, what its name is, and how a user could move to a newer one](engineering-docs/design-notes/devcapsule/2026-09-26-base-image-naming-and-selection.md)
- [mycodespace: a lifetime namespace and archive for one programmer's projects](engineering-docs/design-notes/devcapsule/2026-09-24-mycodespace-lifetime-namespace-and-archive.md)
- [DevCapsule: competitive landscape and critical viability analysis](engineering-docs/design-notes/devcapsule/competitive-comparison.md)
- [Multiple-stream workflow design](engineering-docs/design-notes/multiple-stream-workflow.md)
- [FastAPI web application configuration research](engineering-docs/design-notes/fastapi-webapp-configuration-research.md)
- [DevCapsule V1 user experience design draft](engineering-docs/design-notes/devcapsule/v1-user-experience.md)
- [DevCapsule V1 gap review at 0a0ff09](engineering-docs/design-notes/devcapsule/2026-08-06-v1-gap-review.md)
- [Click-based CLI parsing brief](engineering-docs/design-notes/devcapsule/click-based-cli-parsing-brief.md)
- [The VS Code-family setuid sandbox helper](engineering-docs/design-notes/devcapsule/vscode-sandbox-setuid.md)

## Active DevCapsule Development

- [DevCapsule Python CLI](devcapsule-src/README.md)
- [DevCapsule test suites](devcapsule-src/tests/README.md)
- [DevCapsule implementation requirements overview](devcapsule-src/REQUIREMENTS.md)
- [R-ENV-001 Dockerized PyCharm Runtime](engineering-docs/requirements/devcapsule/r-env-001-dockerized-pycharm-runtime.md)
- [R-RUNTIME-001 Identical Launcher And Container Runtime By Default](engineering-docs/requirements/devcapsule/r-runtime-001-launcher-runtime-identity.md)
- [R-STATE-001 Persistent IDE State And Plugins](engineering-docs/requirements/devcapsule/r-state-001-persistent-ide-state-and-plugins.md)
- [R-SCOPE-001 Explicit Host Filesystem Exposure](engineering-docs/requirements/devcapsule/r-scope-001-explicit-host-filesystem-exposure.md)
- [R-DEV-001 Useful Development Tooling Baseline](engineering-docs/requirements/devcapsule/r-dev-001-useful-development-tooling-baseline.md)
- [R-GIT-001 Git Identity And Credentials Without Host Credential Mounts](engineering-docs/requirements/devcapsule/r-git-001-git-identity-and-credentials-without-host-credential-mounts.md)
- [R-DOCKER-001 Explicit Docker Capability Profiles](engineering-docs/requirements/devcapsule/r-docker-001-explicit-docker-capability-profiles.md)
- [R-PROJECT-001 Per-Project IDE Runtime State](engineering-docs/requirements/devcapsule/r-project-001-per-project-ide-runtime-state.md)
- [R-CONC-001 Concurrent Project Sessions](engineering-docs/requirements/devcapsule/r-conc-001-concurrent-project-sessions.md)
- [R-PROC-001 Durable Human/Agent Project Memory](engineering-docs/requirements/devcapsule/r-proc-001-durable-human-agent-project-memory.md)
- [R-DOCS-001 Generated Documentation Index](engineering-docs/requirements/devcapsule/r-docs-001-generated-documentation-index.md)
- [R-DOCS-002 User-Level Documentation Coevolves With User-Visible Behavior](engineering-docs/requirements/devcapsule/r-docs-002-user-level-documentation-coevolves-with-user-visible-behavior.md)
- [R-IDE-CONFIG-001 Configuration-First End-User CLI Model](engineering-docs/requirements/devcapsule/r-ide-config-001-configuration-first-end-user-cli-model.md)
- [R-PYTHON-MVP-001 Source Checkout Install And Run](engineering-docs/requirements/devcapsule/r-python-mvp-001-source-checkout-install-and-run.md)
- [R-PYTHON-MVP-002 Single-File Python CLI Artifact](engineering-docs/requirements/devcapsule/r-python-mvp-002-single-file-python-cli-artifact.md)
- [R-PYTHON-MVP-003 Python MVP Feature Scope](engineering-docs/requirements/devcapsule/r-python-mvp-003-python-mvp-feature-scope.md)
- [R-IMAGE-BUILD-001 Python-Native Composable Image Building](engineering-docs/requirements/devcapsule/r-image-build-001-python-native-composable-image-building.md)
- [R-FRAMEWORK-001 Shared Python DevCapsule Orchestration](engineering-docs/requirements/devcapsule/r-framework-001-shared-python-docker4ide-orchestration.md)
- [R-COMPAT-001 Client Upgrades Require No User Action For Existing Projects](engineering-docs/requirements/devcapsule/r-compat-001-client-upgrades-require-no-user-action.md)
- [Packaged project workflow asset boundary](devcapsule-src/devcapsule/assets/project_workflow/README.md)
- [Packaged generic agent instructions](devcapsule-src/devcapsule/assets/project_workflow/definition/AGENTS.md)
- [Packaged generic workflow definition (the root `WORKFLOW.md` is its source)](devcapsule-src/devcapsule/assets/project_workflow/definition/WORKFLOW.md)
- [Information model, for humans: the kinds of thing the workflow stores and how they relate](devcapsule-src/devcapsule/assets/project_workflow/definition/INFORMATION-MODEL.md)
- [Preamble, for humans: why the workflow is opinionated, and for whom](devcapsule-src/devcapsule/assets/project_workflow/definition/PREAMBLE.md)
- [PyCharm image vibe-coding bootstrap template](devcapsule-src/devcapsule/assets/pycharm/image-assets/vibe-coding-process.md)
- [Legacy-compatible PyCharm bootstrap template copy](devcapsule-src/devcapsule/assets/docker4pycharm/image-assets/vibe-coding-process.md)
- [TypeScript five-in-a-row sample project](devcapsule-src/tests/resources/sample_projects/typescript_tictactoe_5inrow/README.md)

## Development Blog

- [Diagnosing a capsule from both sides](engineering-docs/blog/2026-10-28-diagnosing-a-capsule-from-both-sides.md) — probing a live browser desktop from outside and inside a nested PyCharm capsule, with embedded recording; draft for owner review.
- [An AI takes our IDEs for a test drive](engineering-docs/blog/2026-10-04-an-ai-takes-intellij-for-a-test-drive.md) — shared AI graphical tests across IntelliJ, Rider and Eclipse, the .NET build, and three original recordings; draft for owner review.
- [The workflow explains itself](engineering-docs/blog/2026-10-03-the-workflow-explains-itself.md) — preamble, information model, merge rule, and a bug filed against ourselves; draft for owner review.
- [What I have been up to lately](engineering-docs/blog/2026-09-30-what-i-have-been-up-to-lately.md)
- [Why give DevCapsule a spin before V1?](engineering-docs/blog/2026-09-21-why-try-devcapsule-before-v1.md) — early-adopter and contributor invitation; draft for owner review.
- [Lessons learned in AI autonomy — Part 2: the AI perspective](engineering-docs/blog/2026-09-19-lessons-learned-in-ai-autonomy-part-2.md) — agent-authored retrospective; draft for owner review.
- [Lessons learned in AI autonomy over a simple, straightforward task](engineering-docs/blog/2026-09-19-lessons-learned-in-ai-autonomy.md) — website autonomy experiment retrospective; draft for owner review.
- [The DevCapsule development blog](engineering-docs/blog/README.md)
- [Where DevCapsule sits: a competitive comparison, October 2026](engineering-docs/blog/2026-10-18-where-devcapsule-sits.md) — the published competitive comparison, with roadmap links.
- [When should a tool refuse? Taking stock of DevCapsule's refusal UX](engineering-docs/blog/2026-09-06-when-should-a-tool-refuse.md)
- [I asked for user docs](engineering-docs/blog/2026-09-16-i-asked-for-user-docs.md) — second development-blog entry.
- [Does the subscription include Navier–Stokes?](engineering-docs/blog/2026-09-16-does-the-subscription-include-navier-stokes.md) — alternative second entry in dialogue form.

## Product And Positioning

- [Product documentation map](docs/README.md)
- [Draft pitch: batteries included, boundaries explicit](engineering-docs/product/draft-pitch.md)
- [Issue-tracker positioning](engineering-docs/product/issue-tracker-positioning.md)
- [LinkedIn announcement draft](engineering-docs/product/linkedin-announcement.md)
- [V1 announcement draft](engineering-docs/product/v1-announcement.md)
- [Working backwards press release](engineering-docs/product/working-backwards-press-release.md)

## Docker4PyCharm Historical Reference

The `docker4pycharm/` directory is the original shell-based PyCharm MVP this
project was bootstrapped from, frozen at that point in time. Read these for
history; record current decisions in the active documents above.

- [Docker PyCharm isolation README](docker4pycharm/README.md)
- [Historical root project brief](engineering-docs/implementation-notes/docker4pycharm/historical-root-readme.md)
- [Post-MVP refactoring strategy](engineering-docs/design-notes/docker4pycharm/future-agent-refactoring-brief.md)
- [PyCharm AI plugin and ChatGPT subscription setup](engineering-docs/archive/docker4pycharm-ai-plugin-and-chatgpt-setup.md)
- [Debugging notes](engineering-docs/implementation-notes/docker4pycharm/debugging.md)
- [Vibe-coding process bootstrap template, frozen copy](docker4pycharm/image-assets/vibe-coding-process.md)

## Implementation Notes And Decisions

- [User-requested session-record policy](engineering-docs/session-records/devcapsule/README.md)
- [Project-management decisions and workflow review session record](engineering-docs/session-records/devcapsule/2026-09-11-project-management-decisions-and-workflow-review.md)
- [Project-management resume and individual-projects framing session record](engineering-docs/session-records/devcapsule/2026-08-19-resume-verification-and-individual-projects.md)
- [Inspector hardening, samples, and workflow bootstrap session record](engineering-docs/session-records/devcapsule/2026-08-16-inspector-hardening-samples-and-workflow-bootstrap.md)
- [v021 external dogfood and V1 backlog session record](engineering-docs/session-records/devcapsule/2026-08-03-v021-external-dogfood-and-v1-backlog.md)
- [D-0004 configuration and images CLI session record](engineering-docs/session-records/devcapsule/2026-08-01-d-0004-configuration-and-images-cli.md)
- [Per-project IDE state split](engineering-docs/design-notes/docker4pycharm/2026-06-21-per-project-ide-state-split.md)
- [Git identity and remote credential transport](engineering-docs/design-notes/docker4pycharm/2026-06-22-git-identity-and-credentials.md)
- [Default JetBrains GL to Mesa software rendering](engineering-docs/design-notes/docker4pycharm/2026-06-22-mesa-software-gl-default.md)
- [Development sudo profile](engineering-docs/design-notes/docker4pycharm/2026-06-24-development-sudo-profile.md)
- [Python project UX defaults](engineering-docs/design-notes/docker4pycharm/2026-06-24-python-project-ux-defaults.md)
- [Docker-in-Docker implementation choice](engineering-docs/design-notes/docker4pycharm/docker-in-docker-implementation-choice.md)
- [Docker in containerized development environments TLDR](engineering-docs/design-notes/docker4pycharm/docker-in-containerized-development-environments.md)
- [Using PyCharm v0 for real Python projects](engineering-docs/implementation-notes/docker4pycharm/using-v0-for-real-python-projects.md)
- [Docker Hub namespace and publication plan](engineering-docs/implementation-notes/devcapsule/2026-07-15-docker-hub-namespace-and-publication-plan.md)
- [Capability-first PyCharm dogfood manual test](engineering-docs/implementation-notes/devcapsule/2026-07-24-capability-first-dogfood-manual-test.md)
- [Local PyCharm materialization and Python entrypoint](engineering-docs/implementation-notes/devcapsule/2026-07-29-local-pycharm-materialization-and-python-entrypoint.md)
- [NVIDIA CUDA base recipe specialized validation](engineering-docs/implementation-notes/devcapsule/2026-08-01-nvidia-cuda-base-recipe-validation.md)
- [Next functional dogfood stage from b5d42e8](engineering-docs/implementation-notes/devcapsule/2026-08-03-next-functional-dogfood-stage-plan.md)
- [Recursive dogfood E2E milestone plan](engineering-docs/implementation-notes/devcapsule/2026-08-06-recursive-dogfood-e2e-milestone-plan.md)
- [Recursive dogfood Stage 2 execution checklist](engineering-docs/implementation-notes/devcapsule/2026-08-06-recursive-dogfood-stage-2-execution-checklist.md)
- [DevCapsule V1 test backlog](engineering-docs/implementation-notes/devcapsule/2026-08-07-v1-test-backlog.md)
- [Host browser URL bridge TLDR](engineering-docs/implementation-notes/devcapsule/2026-08-17-host-browser-url-bridge-tldr.md)
- [V2 launcher-loss resource reconciliation](engineering-docs/implementation-notes/devcapsule/2026-08-18-v2-launch-resource-reconciliation.md)
- [Releasing a new DevCapsule version — operator checklist and validation](engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md)
- [Merge strategy and commit identity](engineering-docs/implementation-notes/workflow/2026-08-17-merge-strategy-and-commit-identity.md)

## Bugs

- [Release-dependent test fixtures cause avoidable release PR churn](engineering-docs/bugs/devcapsule/2026-10-31-release-dependent-test-fixtures.md)

- [Concurrent web consoles on `127.0.0.1` overwrite one another's authentication cookie across ports](engineering-docs/bugs/devcapsule/2026-10-31-webconsole-cookie-collides-across-ports.md)
- [`project config show --help` advertises JSON schema 1 while emitting schema 2, and retired `project config default|trust` spellings print no replacement hint](engineering-docs/bugs/devcapsule/2026-10-30-config-show-json-help-and-retired-home-command-hints.md)
- [An old lock keeps the replaced IDE beside an ordinary IDE override](engineering-docs/bugs/devcapsule/2026-10-29-legacy-lock-keeps-the-replaced-ide.md)
- [Workstation-scoped commands live under `project config` and need a project](engineering-docs/bugs/devcapsule/2026-10-25-workstation-commands-live-under-project-config.md)
- [Console link printed on a base without the console](engineering-docs/bugs/devcapsule/2026-10-18-console-link-printed-on-a-base-without-the-console.md)
- [No test proves old projects launch with new releases](engineering-docs/bugs/devcapsule/2026-10-18-no-test-proves-old-projects-launch-with-new-releases.md)
- [Unpacked archive cache publication and recovery](engineering-docs/bugs/devcapsule/2026-10-08-unpacked-cache-publication-and-recovery.md)
- [Optional omission loses a local version-set pin](engineering-docs/bugs/devcapsule/2026-10-06-optional-omission-loses-local-version-pin.md)

- [`project init` discards every interactive answer when a `--authorize` name is unknown — blocking 0.2.15](engineering-docs/bugs/devcapsule/2026-09-26-init-discards-answers-on-late-authorize-validation.md)
- [Inside a capsule, `project <unknown>` is refused as launcher-only instead of as unknown](engineering-docs/bugs/devcapsule/2026-09-26-project-group-guard-hides-unknown-subcommand-in-capsule.md)
- [Usability: `bootstrap` never asks which workflow mode the user wants; a mode without an installed workflow is void](engineering-docs/bugs/devcapsule/2026-09-26-bootstrap-cannot-choose-the-workflow-mode.md)
- [RC1 in-capsule configuration inspection fails](engineering-docs/bugs/devcapsule/2026-09-24-runtime-configuration-inspection-fails.md)

- [Installed IDE reuse before archive acquisition — design review pending](engineering-docs/bugs/devcapsule/2026-09-24-installed-ide-docker-reuse.md)
- [`project run --authorize network host` is refused on a project that does not recommend host networking](engineering-docs/bugs/devcapsule/2026-10-05-run-once-network-authorization-needs-a-recommendation.md)

- [A client upgrade turns an unanswered acquisition into a required decision — R-COMPAT-001](engineering-docs/bugs/devcapsule/2026-09-24-client-upgrade-requires-acquisition-decision.md)
- [`config list` advises resolve on a fresh resolution](engineering-docs/bugs/devcapsule/2026-09-24-config-list-advises-resolve-on-fresh-resolution.md)
- [Release workflow gated candidates on Docker builds on a hosted runner — blocked rc2](engineering-docs/bugs/devcapsule/2026-09-24-release-workflow-gated-on-docker-on-hosted-runner.md)
- [Released launchers reject the repository manifest since RC1 — blocks 0.2.14](engineering-docs/bugs/devcapsule/2026-09-24-released-launchers-reject-repository-manifest.md)
- [Runtime DevCapsule command unavailable — blocks 0.2.14](engineering-docs/bugs/devcapsule/2026-09-24-runtime-cli-not-on-path.md)
- [Website URL opening has no browser handler](engineering-docs/bugs/devcapsule/2026-09-24-url-opening-without-browser-handler.md)

- [Claim lifecycle test depends on wall-clock timing](engineering-docs/bugs/devcapsule/2026-09-22-workflow-claim-test-flakiness.md)
- [Nested-directory workflow commands lose coordination files](engineering-docs/bugs/devcapsule/2026-09-22-workflow-nested-directory-loses-coordination.md)
- [Codex commit authorship and model attribution](engineering-docs/bugs/devcapsule/2026-09-22-codex-commit-attribution.md)

- [Configuration Contract Is Not Enforced Across Boundaries](engineering-docs/bugs/devcapsule/2026-09-20-configuration-contract-not-enforced-across-boundaries.md)
- [Website test publication accepts inconsistent settings — transferred](engineering-docs/bugs/website/2026-09-19-test-publishing-accepts-inconsistent-settings.md)
- [Upgrade Configuration Recovery Rejects Its Own Remedy](engineering-docs/bugs/devcapsule/2026-09-19-upgrade-config-recovery-rejects-its-own-remedy.md)
- [The Resolution Refusal Names Only The Last Base Tried And Offers No Remedy](engineering-docs/bugs/devcapsule/2026-09-03-resolution-refusal-names-only-the-last-base-and-no-remedy.md)
- [The Formation Identity Claims An Entrypoint The Recipe Never Sets](engineering-docs/bugs/devcapsule/2026-09-02-formation-identity-claims-an-entrypoint-the-recipe-never-sets.md)
- [The Codium Setuid Sandbox Crashes Under The Development-Sudo Posture](engineering-docs/bugs/devcapsule/2026-09-02-codium-setuid-sandbox-crashes-under-development-sudo.md)
- [Codium Relaunch Intermittently Crashes Its First Renderer After A Clean Exit](engineering-docs/bugs/devcapsule/2026-09-02-codium-relaunch-renderer-crash-after-clean-exit.md)
- [`--authorize base-image` Conflates Consent With Selection And Explains Neither](engineering-docs/bugs/devcapsule/2026-09-02-authorize-base-image-conflates-consent-with-selection.md)
- [The Authorization Grammar Cannot Express Denial](engineering-docs/bugs/devcapsule/2026-09-02-authorization-grammar-cannot-express-denial.md)
- [Antigravity's State Is Wider Than The Analyzed Path, And The Nested Slot Walls It Off](engineering-docs/bugs/devcapsule/2026-09-02-antigravity-state-wider-than-the-analyzed-path.md)
- [Codex was installed as a single plucked binary, so every sandboxed command failed](engineering-docs/bugs/devcapsule/2026-09-05-codex-installed-as-a-single-plucked-binary.md)
- [Init and run answers are not persisted as the authorizations they express](engineering-docs/bugs/devcapsule/2026-09-02-init-and-run-answers-not-persisted-as-authorizations.md)
- [init --authorize base-image left the checkout unauthorized](engineering-docs/bugs/devcapsule/2026-09-01-init-authorize-base-image-not-recorded.md)
- [X11 passthrough grants the container a full host session credential](engineering-docs/bugs/devcapsule/2026-08-16-x11-passthrough-grants-full-session-credential.md)
- [Detached DevCapsule containers exit and are never cleaned up](engineering-docs/bugs/devcapsule/2026-08-15-detached-successors-not-cleaned-up.md)
- [Codex ACP fails because explicit CODEX_HOME does not exist](engineering-docs/bugs/devcapsule/2026-08-03-codex-acp-missing-home.md)
- [Authorized development sudo is reported as enabled but is unusable](engineering-docs/bugs/devcapsule/2026-08-03-authorized-development-sudo-misreported.md)
- [PyCharm recommends its native launcher](engineering-docs/bugs/devcapsule/2026-08-03-jetbrains-native-launcher.md)
- [JetBrains Runtime disables alpha compositing on slow X11](engineering-docs/bugs/devcapsule/2026-08-03-jbr-slow-x11-alpha-compositing.md)
- [JetBrains embedded browser is suspended in the container](engineering-docs/bugs/devcapsule/2026-08-03-jcef-sandbox-container-preview.md)
- [Fresh clones require manual ecosystem bootstrap](engineering-docs/bugs/devcapsule/2026-08-03-ecosystem-aware-project-bootstrap.md)
- [Component tooling is not added to the runtime path](engineering-docs/bugs/devcapsule/2026-08-03-component-tooling-runtime-path.md)
- [Unreleased Playwright breaks shared-checkout launch](engineering-docs/bugs/devcapsule/2026-10-04-unreleased-playwright-breaks-checkout-launch.md)
- [IntelliJ relaunch stale directory lock](engineering-docs/bugs/devcapsule/2026-10-04-intellij-relaunch-stale-directory-lock.md)
- [PyCharm run-image network and Docker-option parity](engineering-docs/bugs/devcapsule/2026-07-23-pycharm-ambient-host-network.md)
- [Codium grants ambient passwordless sudo by default](engineering-docs/bugs/devcapsule/2026-07-16-codium-ambient-sudo-default.md)
- [PyCharm build emits fragile multiline RUN shell quoting](engineering-docs/bugs/devcapsule/2026-07-16-pycharm-build-multiline-exec-rendering.md)
- [Codium run lacks shared developer runtime options](engineering-docs/bugs/devcapsule/2026-07-13-codium-run-option-parity.md)
- [Bug template](engineering-docs/bugs/docker4pycharm/_template.md)
- [Concurrent projects sharing global settings lock](engineering-docs/bugs/docker4pycharm/2026-06-24-concurrent-projects-shared-global-settings-lock.md)

## Completed, Retired, And Deferred Tasks

- [VSCodium sandbox and foreground launch](engineering-docs/completed-tasks/devcapsule/2026-07-13-vscodium-sandbox-and-foreground-launch.md)
- [Completed task archive README](engineering-docs/completed-tasks/docker4pycharm/README.md)
- [Bootstrap process template V004 validation](engineering-docs/completed-tasks/docker4pycharm/2026-06-20-bootstrap-process-template-v004-validation.md)
- [Default host Docker passthrough validation retired](engineering-docs/completed-tasks/docker4pycharm/2026-06-20-default-host-docker-passthrough-validation-retired.md)
- [Explicit Docker-in-Docker validation](engineering-docs/completed-tasks/docker4pycharm/2026-06-20-explicit-docker-in-docker-validation.md)
- [Markdown preview Skiko/OpenGL hang retired](engineering-docs/completed-tasks/docker4pycharm/2026-06-20-markdown-preview-skiko-opengl-hang-retired.md)
- [Mesa/Skiko Markdown preview validation](engineering-docs/completed-tasks/docker4pycharm/2026-06-22-mesa-skiko-markdown-validation.md)
- [Development sudo account validation failure](engineering-docs/completed-tasks/docker4pycharm/2026-06-28-dev-sudo-account-validation.md)
- [Git remote credential manual validation deferred](engineering-docs/completed-tasks/docker4pycharm/2026-06-28-git-remote-validation-deferred.md)
- [Local Git identity edge-case validation](engineering-docs/completed-tasks/docker4pycharm/2026-06-30-local-git-identity-edge-validation.md)
- [PyCharm v0 MVP checkpoint](engineering-docs/completed-tasks/docker4pycharm/2026-06-30-pycharm-v0-mvp-checkpoint.md)

- [CI path gating and advisory diff coverage — maintenance, 0.3.0](engineering-docs/work-orders/2026-10-30-ci-path-gating-and-diff-coverage.md)
