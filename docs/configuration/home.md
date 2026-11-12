---
description: Select one DevCapsule configuration home for settings, checkout records, persistent data, state, and cache.
weight: 3
updated: 2026-10-30
---
# The configuration home

A DevCapsule home holds the settings shared by launches from that home. You can
use separate homes with the same executable; the executable's file path does
not select the home.

By default, configuration lives in `$XDG_CONFIG_HOME/devcapsule` (or
`$HOME/.config/devcapsule` when `XDG_CONFIG_HOME` is unset or empty), and
persistent data, state, and cache use their own XDG directories:

| Purpose | XDG directory | Default |
|---|---|---|
| Configuration | `$XDG_CONFIG_HOME/devcapsule` | `$HOME/.config/devcapsule` |
| Persistent data | `$XDG_DATA_HOME/devcapsule` | `$HOME/.local/share/devcapsule` |
| State | `$XDG_STATE_HOME/devcapsule` | `$HOME/.local/state/devcapsule` |
| Cache | `$XDG_CACHE_HOME/devcapsule` | `$HOME/.cache/devcapsule` |

Set `DEVCAPSULE_CONFIG_HOME` to keep all four under one root:

```sh
export DEVCAPSULE_CONFIG_HOME="$HOME/devcapsule-homes/learning"
devcapsule home show
devcapsule home trust accept devcapsule-base --yes
devcapsule home trust accept vscode --yes
devcapsule home trust accept claude-code --yes
devcapsule home default memory 8GiB
devcapsule home default cpus 4
```

The named directory holds configuration, while its `data/`, `state/`, and
`cache/` subdirectories hold persistent data, operational state, and caches
(including managed per-checkout storage). Explicit host-directory bindings
still point to the paths you chose. An empty `DEVCAPSULE_CONFIG_HOME` keeps the
XDG defaults, a relative path resolves from the current working directory, and
a leading `~` expands to your user home.

`devcapsule home` commands need no project directory. `home show` prints the
selected path, how it was chosen, schema metadata, defaults, and accepted
channels; `home trust list` prints accepted channels and dates. Neither read
command creates directories on disk—the first write creates the home with mode
`0700` and `settings.toml` with mode `0600`.

## One settings document

`settings.toml` stores resource defaults under `[defaults]` and accepted
distribution channels under `[trust.channels]`. Each channel entry records its
vendor, product, origins, integrity method, acceptance date, and terms URL when
applicable. Checkout records live under `projects/` in the same configuration
directory, while saved Docker arguments (`docker-arguments/`) and pending
web-console requests (`console-requests/`) keep their own subdirectories.

Two header fields guard `settings.toml`:

- `devcapsule-settings-schema-version`: format version (`1` in {{tag}}).
- `minimum-devcapsule`: lowest launcher release allowed to load the home.

When a launcher creates `settings.toml`, it sets `minimum-devcapsule` to its
own release version (without any candidate or development suffix), and later
writes preserve an existing minimum. Launchers older than `minimum-devcapsule`
refuse to read or modify that home and print the required version and release
download URL. No-op writes leave the file and its modification time untouched.

## Inside a capsule

When a capsule starts, it mounts the host launcher's `settings.toml` read-only
if that file exists.
While the capsule has no `settings.toml` of its own and
`DEVCAPSULE_CONFIG_HOME` is unset or empty inside the capsule, `home show` and `home
trust list` read that mounted file (and `home show` notes the read-only source).
The capsule's own home, data, state, and cache still live in the capsule's XDG
directories. A settings change starts from the mounted settings and writes the
result to the capsule's own `settings.toml`. It leaves the host's file untouched.
Subsequent reads use the capsule's copy. A no-op command does not create that
copy. Setting `DEVCAPSULE_CONFIG_HOME` to a nonempty path inside the capsule
selects that directory immediately and disables fallback to the mounted settings.

See [Vendor software and trust](software-approvals.md) for channel acceptance
and [Resource limits](resource-limits.md) for how home defaults interact with
project recommendations and checkout overrides.
