---
description: Where to find a newer DevCapsule launcher, how to install it, and what stays untouched when you upgrade.
weight: 2
updated: 2026-10-30
---
# Launcher updates

Check the [DevCapsule releases page](https://github.com/mycodespace-ai/devcapsule/releases)
for launcher updates. Install a newer release with the steps in
[Install DevCapsule](../getting-started/install.md), using that release's
download URL. This replaces the single-file executable.

The daily interactive check in `devcapsule project run` checks component
channels, not the launcher's release list. `--no-update-check` skips that live
check. Cached component notices can still ask for a decision in an interactive
terminal; non-interactive launches report them and continue. See
[Component freshness](component-freshness.md).

Upgrading the launcher preserves every project's lock, every checkout's
recorded choices, and your [configuration home](../configuration/home.md)
(`settings.toml` defaults and accepted channels). It grants no new host
access. Existing per-checkout approvals and home channel acceptances stay
valid while they still match the selected software.

If a project updated its manifest or lock in the meantime, or a newly selected
component requires a channel acceptance or checkout approval, the next launch
stops and asks, as
[Project versus personal](../configuration/project-versus-personal.md#when-the-project-changes)
describes. When the launcher creates `settings.toml`, it records its release in
`minimum-devcapsule`. Later writes preserve an existing minimum. A launcher
older than that minimum refuses commands that load the home, including reads.
