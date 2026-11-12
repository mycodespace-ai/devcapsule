---
description: The project, checkout, and home records that define a DevCapsule launch, and where each configuration guide lives.
weight: 1
updated: 2026-10-30
---
# Configuration

A DevCapsule configuration describes what a project needs and how you want to
work on it. That configuration lives in three places:

1. **The project, in Git:** `.devcapsule/devcapsule.toml` (the manifest)
   declares required and offered capabilities, environment inputs, and
   recommendations. A capability names something the environment supplies, such
   as a Java runtime or browser automation, and a component supplies it. The
   platform lock, `.devcapsule/devcapsule.<platform>.lock`, pins the base image
   and resolved component versions. Both files travel in Git.
2. **Your checkout, on your computer:** your checkout record stores your IDE
   choice, added and omitted capabilities, provider choices, values, directory
   and secret bindings, host-access answers, and local component pins. A second
   checkout of the same repository keeps its own record.
3. **Your configuration home:** `settings.toml` holds default resource limits
   and the vendor channels you trust across every project launched from that
   home. Channel trust permits verified downloads; it grants no host access.

`devcapsule project run` derives the launch plan from all three records every
time. Checkout choices override recommendations, while required capabilities
must stay present and satisfy their minimum versions. The explicit exception is
[replacing a required IDE for one launch](capabilities.md#a-required-ide).
If a required choice or consent is missing, the launcher asks before starting a
container. Without a terminal, it exits with status `3` instead.
The selected IDE opens the project, owns the container's lifetime, and uses the
capsule's display.

## Guides in this section

- [Project versus personal](project-versus-personal.md): what lives in Git, on your checkout, and in your home, plus saved Docker options, environment variables, and web-console requests.
- [The configuration home](home.md): XDG defaults, `DEVCAPSULE_CONFIG_HOME`, `settings.toml`, and inside-capsule behavior.
- [Inspect a checkout](inspect.md): `project info`, `config show`, `config check`, and `versions show`.
- [Extra tools](extra-tools.md): installing personal tools under `/opt/xtras` that survive container replacement.
- [IDE preferences and plugins](ide-preferences.md): per-checkout IDE config, plugin, extension, and workspace slots, plus `config bind` and `state adopt`.
- [Resource limits](resource-limits.md): memory, CPU count, precedence, and project-declared values.
- [Build and select a local base](local-base.md): building a base image locally and selecting it for one checkout.
- [Vendor software and trust](software-approvals.md): home channel trust versus per-checkout approvals.
- [Capabilities and components](capabilities.md): `require`, `offer`, `drop`, `recommend`, checkout overrides, and `--force`.
- [Configuration nodes](../reference/configuration-nodes.md): reference tables for authorizations, values, and bindings.
