---
description: What survives when a capsule stops, where each persistent directory lives on your computer, and what is deliberately temporary.
weight: 2
updated: 2026-10-30
---
# What persists

The container itself is disposable and its root filesystem is normally
read-only. Your project tree and the persistent directories DevCapsule mounts
from your computer survive when the container stops; anything written outside
those mounts—such as files in `/tmp` or OS packages installed during a session
with development `sudo`—disappears when the container is removed.

Run `devcapsule project info` (or `devcapsule project info --json` for slot
names) to inspect the exact mounts and host backing paths for your checkout:

| In the capsule | Kind | What it holds |
|---|---|---|
| The project folder (`/workspace/<slug>` or `project.mount`) | `source` | Your working tree, shared directly with your computer |
| `/home/devcapsule` (`home`) | `durable` | The capsule user's home: shell history, dotfiles, `~/xtras` |
| `/opt/xtras` | `durable` | Alias of `/home/devcapsule/xtras`; see [Extra tools](../configuration/extra-tools.md) |
| `~/.claude`, `~/.codex`, `~/.gemini` | `durable` | Agent configuration and session state: Claude Code and Codex also store interactive sign-ins here, while Antigravity CLI keeps settings and local state under `~/.gemini` and stores credentials in its keyring or per-run variables; see [Sign in and defaults](../working-with-ai/sign-in-and-defaults.md) |
| IDE configuration and plugins (`<ide>/config`, `<ide>/plugins`, `<ide>/user-data`, `<ide>/extensions`) | `durable` | Keymaps, themes, editor settings, and installed plugins or extensions; see [IDE preferences and plugins](../configuration/ide-preferences.md) |
| Eclipse's `/ide-workspace` (`eclipse/workspace`) | `durable` | Workspace `.metadata/` preferences, imported project references, and local history; keep source files in the project folder |
| IDE log and system directories (`<ide>/log`, `<ide>/system`, `<ide>/cache`) | `state`, `cache` | IDE logs and reconstructable indexes and caches; caches may be cleared |
| `/var/log/devcapsule` | `state` | This session's component logs, rotated per component; older session directories are pruned within a per-checkout budget (`256 MiB` by default; see [Diagnostics and logs](../troubleshooting/diagnostics-and-logs.md)) |
| `~/.cache` | `cache` | Reconstructable user-tool caches |
| `/tmp`, `/var/tmp`, `/run`, `/dev/shm`, and the container filesystem | `temporary` | Lost as soon as the container is removed |

## Where backing directories live

By default, DevCapsule creates per-checkout `durable`, `state`, and `cache`
directories under your user's XDG data, state, and cache roots
(`~/.local/share/devcapsule`, `~/.local/state/devcapsule`, and
`~/.cache/devcapsule`, or under `$DEVCAPSULE_CONFIG_HOME` when you use an
isolated [configuration home](../configuration/home.md)).

A second checkout or `git worktree` of the same repository gets its own
`projects/by-path/<checkout-id>` directories automatically, so concurrent
sessions do not overwrite each other's locks or indexes. When you want to reuse
or share an existing host directory across checkouts that you run one at a
time, point the slot at that path with `devcapsule project config bind <slot>
host-directory:PATH` or `devcapsule project state adopt --from PATH <slot>`;
see [IDE preferences and plugins](../configuration/ide-preferences.md) and
[Configuration nodes](../reference/configuration-nodes.md).

Persistence is not backup. It keeps a checkout's local state across container
restarts on one computer; it does not sync files to [another machine](another-machine.md),
and it never replaces Git for your source code.
