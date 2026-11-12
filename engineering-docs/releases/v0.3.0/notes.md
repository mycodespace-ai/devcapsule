---
description: DevCapsule 0.3.0 adds a session web console, persistent diagnostics, more IDE choices, and separate project requirements and personal setup.
updated: 2026-10-31
---
# DevCapsule 0.3.0

DevCapsule 0.3.0 adds a web console and persistent session diagnostics,
expands the choice of IDEs, and separates a project's requirements from a
developer's personal setup. The launcher and the 49 user-guide pages now
use the same capability and configuration model.

## What changed

- **A web console for each session.** The launcher prints a session-specific
  console link beside the desktop link. Inspect configuration, component
  versions, processes and resource use; read project records; answer decisions
  prepared by an agent; and read checkout notifications. The console requires
  a compatible base. Older bases remain usable and receive a clear notice
  instead of a console link that cannot work. Several consoles can stay
  authenticated side by side in the same browser profile.
- **Logs that survive a session.** Each launch writes per-component logs to a
  directory on the launcher host. Files rotate and share a per-checkout budget.
  The terminal stays focused on startup, readiness, warnings and the final
  session result. Ctrl+C reports an interrupted session instead of a traceback.
- **A diagnostic snapshot and export.** `devcapsule project diagnose` combines
  launcher information with bounded probes of the running capsule. Its export
  redacts recognized secrets and bounds the captured data. Inspect an export
  before sharing it: application output can contain sensitive text that a
  general redactor cannot recognize.
- **More IDE choices.** Alongside PyCharm and VSCodium, the catalog includes
  IntelliJ IDEA, Eclipse IDE for Java Developers, JetBrains Rider with .NET,
  and Microsoft Visual Studio Code. VSCodium remains the default provider of
  `frontend-ide`. VS Code is downloaded from Microsoft on the developer's
  request under its acquisition terms; DevCapsule does not redistribute it.
  The browser-automation capability supplies Playwright and Chromium.
- **Capabilities for projects and checkouts.** Projects use `project config
  require`, `offer`, `drop` and `recommend` to declare capabilities, minimum
  versions and recommendations. Developers use `add`, `omit`, `restore` and
  `use` for their checkout. Agents use the same capability model as other
  tools. `project run` derives the plan directly; there is no separate
  configuration-resolution step.
- **One named configuration home.** `DEVCAPSULE_CONFIG_HOME` selects the home
  for launcher settings and checkout state. `devcapsule home show`,
  `home default` and `home trust` work without a project. Defaults and vendor
  trust live in one schema-versioned `settings.toml`. Inside a capsule, these
  commands operate on the capsule's own home.
- **Explicit choices at launch.** Software acquisition approvals are grouped
  into one prompt. Saved per-checkout Docker arguments and environment inputs
  support development scenarios without putting secret values in Git. A
  one-time `project run --ide IDE --force` may set aside a required IDE; it
  warns and records the departure without saving it or bypassing other checks.
- **Faster rebuilds and clearer compatibility checks.** Directory build inputs
  use named contexts and archives are cached by digest. Cache publication is
  serialized and incomplete entries are rejected. The launcher diagnoses an
  incompatible base or lock before attempting work it cannot support.
- **Complete versioned guides.** All 49 user-documentation files were checked
  against the CLI and reviewed for prose; all 12 planned-page stubs have full
  content. Packaged workflow instructions call the iterative review process
  **Pair Review Loop**, or **Pair Review** for short.

## Upgrading from 0.2.15

Install the new launcher, inspect your checkout with `devcapsule project
config show`, and use `devcapsule project config check` to see unresolved
choices. Installing the launcher grants no new host access and does not
silently replace a project's lock or a developer's selected versions.

To migrate a schema-1 manifest to schema 2 and refresh its lock, run
`devcapsule project init --regenerate`, review the `.devcapsule/` diff, and
commit the manifest and platform lock together. Do not hand-edit a lock.
The concurrent-console fix requires the rebuilt recipe-11 base; updating
only the launcher leaves an older locked base unchanged.

Scripts using retired configuration commands must move to the current CLI:
`config show` replaces `config list`; project requirements use `require`,
`offer` and `drop`; developer choices use `add`, `omit`, `restore` and `use`;
home defaults and mutating trust commands live under `devcapsule home`.
`config resolve` and `run --force-config` are retired. The new `run --force`
has the narrower required-IDE meaning described above and cannot be combined
with `--save`.

Old home files are not silently merged into the new `settings.toml`. Inspect
`devcapsule home show` and re-establish defaults or vendor trust with the home
commands where needed. Agent credentials still belong to your provider
accounts and are not granted by a launcher upgrade.

## Component versions and validation limits

The IDE catalog supplies PyCharm, IntelliJ IDEA and Rider **2026.2.4**,
VSCodium **1.143.17232**, VS Code **1.144.0**, and Eclipse Java **2026-09-R**.

The candidate's catalog pins Codex **0.166.0**, Claude Code **2.1.314**, and
Antigravity CLI **1.4.12**. Their artifacts were checked against vendor
integrity values and startup-tested on the pinned base with DevCapsule's
seeded settings. Existing locks retain their selected versions. These pins
are not a claim to be each vendor's latest release; authentication, model
access and provider tool actions still depend on the user's account.

## Known limits and deferred work

- A very old lock without provider evidence can keep its original IDE beside
  an ordinary IDE override. A plain launch still works; refresh the project's
  manifest and lock before relying on that override.
- `config show --json` uses schema 2 for the current listing, although its help
  still says schema 1. The retired `project config default` and mutating
  `project config trust` spellings do not yet print their `home` replacements.
- Automated image/cache cleanup and installed-IDE reuse with an empty download
  cache are deferred. The cleanup guide describes the available manual steps.
- The new orientation, glossary and recipe proposals are scheduled for 0.3.1.
  Console materialized views, additional diagnostics browser evidence, and
  ecosystem-aware project bootstrap remain outside this release.
