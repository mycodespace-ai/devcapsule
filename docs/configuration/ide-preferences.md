---
description: Where each IDE stores settings, plugins, and extensions, how they persist per checkout, and how to bind or adopt an existing host directory.
weight: 4
updated: 2026-10-30
---
# IDE preferences and plugins

Inside a capsule, your IDE's settings, keymaps, installed plugins or
extensions, and workspace state live in persistent directories mounted from
your computer. Stopping, recreating, or upgrading the container leaves them
intact.

By default, every checkout gets its own isolated IDE directories, so two
checkouts (or two worktrees) can run side by side with different plugins,
window layouts, or IDE versions without corrupting each other's state. When you
work in one checkout at a time and want a shared profile, you can point a
checkout's IDE slots at your own host directories instead.

## Declared IDE slots

Each IDE declares named storage slots, visible in `devcapsule project info
--json` (and listed in [Configuration nodes](../reference/configuration-nodes.md)):

| IDE components | Slot name | Path in capsule | Storage class | What lives there |
|---|---|---|---|---|
| `pycharm`, `intellij`, `rider` | `<ide>/config` | `/ide-config` | `durable` (`personal`) | Keymaps, themes, code style, inspections, UI preferences |
| `pycharm`, `intellij`, `rider` | `<ide>/plugins` | `/ide-plugins` | `durable` (`personal`) | Plugins installed inside the IDE |
| `pycharm`, `intellij`, `rider` | `<ide>/system` | `/ide-project-state/system` | `cache` (`ordinary`) | Rebuildable indexes, caches, local history |
| `pycharm`, `intellij`, `rider` | `<ide>/log` | `/ide-project-state/log` | `state` (`personal`) | `idea.log` and thread dumps |
| `pycharm`, `intellij`, `rider` | `<ide>/cache` | `/home/devcapsule/.cache` | `cache` (`ordinary`) | User-tool cache overlay (`XDG_CACHE_HOME`) |
| `codium`, `vscode` | `<ide>/user-data` | `/ide-user-data` | `durable` (`personal`) | `User/settings.json`, `keybindings.json`, snippets, UI/workspace state, editor `logs/` |
| `codium`, `vscode` | `<ide>/extensions` | `/ide-extensions` | `durable` (`personal`) | Installed VSIX extensions |
| `codium`, `vscode` | `<ide>/cache` | `/home/devcapsule/.cache` | `cache` (`ordinary`) | User-tool cache overlay (`XDG_CACHE_HOME`) |
| `eclipse` | `eclipse/workspace` | `/ide-workspace` | `durable` (`personal`) | Workspace `.metadata/` preferences, imported project references, local history |

Every capsule also mounts `home` at `/home/devcapsule` (`durable`,
`credentials`). For Eclipse, per-user installation state and `p2` bundle pools
live under that persistent `home` directory alongside `eclipse/workspace`.

Every IDE component uses its own namespace (`pycharm/*`,
`intellij/*`, `rider/*`, `codium/*`, `vscode/*`, `eclipse/*`). Switching a
checkout from `codium` to `vscode` (or temporarily launching another IDE with
`project run --ide ...`) keeps both editors' settings and extensions intact in
separate directories.

## Where managed directories live on your computer

Unless you rebind a slot, DevCapsule creates per-checkout directories under
your active [configuration home](home.md):

- `durable` slots (`config`, `plugins`, `user-data`, `extensions`,
  `workspace`): `$XDG_DATA_HOME/devcapsule/projects/by-path/<checkout id>/components/<ide>/<slot>`
  (default `~/.local/share/devcapsule/...`, or
  `$DEVCAPSULE_CONFIG_HOME/data/projects/by-path/...`).
- `state` slots (`log`): `$XDG_STATE_HOME/devcapsule/projects/by-path/<checkout id>/components/<ide>/<slot>`
  (default `~/.local/state/devcapsule/...`, or
  `$DEVCAPSULE_CONFIG_HOME/state/projects/by-path/...`).
- `cache` slots (`system`, `cache`): `$XDG_CACHE_HOME/devcapsule/projects/by-path/<checkout id>/components/<ide>/<slot>`
  (default `~/.cache/devcapsule/...`, or
  `$DEVCAPSULE_CONFIG_HOME/cache/projects/by-path/...`).

Run `devcapsule project info` (or `devcapsule project info --json` to see the
exact slot names) from your checkout to print every slot's current host backing
path.

## Reuse or share a directory (`config bind` and `state adopt`)

To use an existing directory on your computer—either to bring preferences you
prepared outside the checkout or to share one profile across sequential
checkouts—create or pick the directory on the host first, then bind or adopt
the slot:

```bash
mkdir -p "$HOME/.devcapsule-profiles/codium/user-data" "$HOME/.devcapsule-profiles/codium/extensions"
devcapsule project config bind codium/user-data "host-directory:$HOME/.devcapsule-profiles/codium/user-data"
devcapsule project config bind codium/extensions "host-directory:$HOME/.devcapsule-profiles/codium/extensions"
```

With PyCharm selected for the checkout, adopt an existing PyCharm configuration
directory with `state adopt`:

```bash
devcapsule project state adopt --from "$HOME/.devcapsule-profiles/pycharm/config" pycharm/config
```

How `bind`, `state adopt`, and `unbind` behave:

- **Direct mount, no copy:** both `config bind <slot> host-directory:PATH` and
  `state adopt --from PATH <slot>` mount `PATH` directly read-write inside the
  capsule on the next `devcapsule project run`. Neither copies files into
  managed storage. `config bind`, `state adopt`, and `init --bind` each reject
  a missing directory before saving its binding. Resolution checks the path
  again, so keep the directory available for subsequent launches.
- **Only active components can be bound:** you can bind or adopt slots declared
  by the IDE and components in your checkout's effective lock (plus `home`). You
  can also pass `--bind <slot> host-directory:PATH` during `devcapsule project
  init` (there is no `--bind` flag on `project run`).
- **One source per slot:** a slot cannot be both configuration-bound and
  adopted at the same time. Run `config unbind <slot>` before changing between
  these two methods. `config bind` prints the slot's sensitivity and
  concurrency rule on standard error when recording the binding.
- **Return to managed storage:** run `devcapsule project config unbind <slot>`
  to clear either a `config bind` or a `state adopt` entry. Your external host
  directory stays untouched, and the next launch uses the checkout's private
  managed directory again. Unbinding does not copy external files back into
  managed storage. It fails if the slot has no binding or adoption to remove.

## Concurrency warning when sharing slots

Every IDE slot (and `home`) declares `concurrent = false`. Desktop IDEs place
process locks in their configuration and workspace directories and assume a
single running instance owns their caches and databases:

- **Never share `<ide>/system`, `<ide>/log`, or `eclipse/workspace` across two
  capsules running at the same time.** Concurrent writes can corrupt indexes
  or cause an IDE lock error.
- Even for `<ide>/config`, `<ide>/plugins`, `<ide>/user-data`, and
  `<ide>/extensions`, share a bound directory across checkouts only when you
  run one checkout at a time. When you run several checkouts
  simultaneously, keep the default per-checkout managed directories.

## Project-shared settings versus personal preferences

Persistent IDE slots belong to you and never enter Git. Settings that every
contributor on the repository should share—such as `.editorconfig`, formatting
rules, `.vscode/settings.json`, or committed run configurations—still live in
the project working tree as usual, where the IDE reads them from the mounted
repository alongside your personal preferences.
