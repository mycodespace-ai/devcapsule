---
description: "Every configuration node a checkout can record: host and software authorizations, declared values, and directory or secret bindings."
weight: 2
updated: 2026-10-30
---
# Configuration nodes

Each checkout choice that is not a capability or provider selection is stored
as a named configuration node in your checkout record, outside the Git
repository. Run `devcapsule project config show` to see the value the next
launch will use, where it came from, and the command that changes any pending
item.

Published base images and vendor downloads are normally trusted once for your
[configuration home](../configuration/home.md) (`devcapsule home trust accept
CHANNEL`), while host-access grants and optional per-checkout software consents
live on the checkout itself. Channel names are `devcapsule-base`, `vscode`,
`claude-code`, and `antigravity-cli`; they differ from the authorization node
names below. See
[Vendor software and trust](../configuration/software-approvals.md).

## Authorizations, `config authorize NAME VALUE [JUSTIFICATION]`

| Node | Values | Effect |
|---|---|---|
| `base-image` | `default`, the lock's exact digest, or a local image tag or ID | Consents to run that base image on this checkout when the base channel is not trusted in this home; bound to the image identity, so unrelated lock edits preserve it. |
| `network` | `host`, `bridge` (default `bridge`) | `host` shares the host network stack with the capsule; `bridge` keeps isolated container networking. Available on every project. |
| `docker-daemon` | `host-socket`, `none` (default `none`) | `host-socket` mounts the host Docker socket into the capsule; `none` keeps the daemon unreachable. |
| `development-sudo` | `true`, `false` (default `false`) | `true` lets the capsule user run `sudo` inside the container via a launcher-generated policy; `false` disables elevation. |
| `host-browser` | `true`, `false` (default `false`) | `true` lets `xdg-open` inside the capsule ask your host browser to open URLs. |
| `host-x11` | `true`, `false` (default `false`) | `true` binds your host X11 display instead of starting the contained web desktop. Never recommended by a project. |
| `vscode-download`, `claude-code-download`, `antigravity-download` | `true`, `false` | Per-checkout vendor download consent when the vendor's channel is not trusted in this home; setting `false` blocks that vendor on this checkout even if the home trusts the channel. |

`config authorize --all-recommended` previews every open recommendation from
the project manifest and records them together only when you confirm with `y`.
For a single session, pass `--authorize NAME VALUE` to `devcapsule project run`
(add `--save` to persist it).

Use `config deny NAME` to record an explicit denial, and `config forget NAME`
to delete your recorded answer so the secure default applies (or a project
recommendation prompts again). When you use per-checkout software consent
instead of home channel trust, `config approve [NAME...|--all]` approves newer
locked versions of that software.

## Values, `config set NAME VALUE`

`memory` and `cpus` are built in on every project. Additional value nodes come
from declarations in `.devcapsule/devcapsule.toml` and are validated against
their declared type (`string`, `integer`, `boolean`, or `memory-size`). Passing
`default` as the value clears your checkout override so the project
recommendation or home default (`devcapsule home default`) takes effect again.

| Node | Effect |
|---|---|
| `memory`, `cpus` | Sets the container's memory limit (`6GiB`, `6g`) and CPU limit (`4`). A legacy manifest node with `runtime-effect = "docker.memory-limit"` maps to `memory`. |
| `runtime.devcapsule-command` | Sets the command name (`devcapsule` or `devcapsule0`) installed inside the capsule when developing DevCapsule itself. |

## Bindings, `config bind RESOURCE PROVIDER:VALUE`

`config bind` redirects a declared persistent state slot or supplies a secret
input. `config unbind RESOURCE` returns a directory slot to managed storage;
for a secret input, it removes the host-variable binding. Directory slots and
secret inputs must belong to the selected components; `home` is always available.

Two providers exist:

- `host-directory:PATH` mounts an existing host directory read-write at the
  slot's container path.
- `host-environment:VAR` reads a host environment variable at launch for a
  declared component secret input, storing only the variable's name on disk.

| Resource | Component | Holds |
|---|---|---|
| `home` | Capsule | Persistent `/home/devcapsule` directory (including `~/xtras`, aliased at `/opt/xtras`). |
| `pycharm/config`, `pycharm/plugins`, `pycharm/system`, `pycharm/log`, `pycharm/cache` | PyCharm | Settings, installed plugins, rebuildable indexes, `idea.log`, and user caches. |
| `intellij/config`, `intellij/plugins`, `intellij/system`, `intellij/log`, `intellij/cache` | IntelliJ IDEA | Settings, installed plugins, rebuildable indexes, `idea.log`, and user caches. |
| `rider/config`, `rider/plugins`, `rider/system`, `rider/log`, `rider/cache` | Rider | Settings, installed plugins, rebuildable indexes, `idea.log`, and user caches. |
| `codium/user-data`, `codium/extensions`, `codium/cache` | VSCodium | Editor settings and workspace state, installed extensions, and user caches. |
| `vscode/user-data`, `vscode/extensions`, `vscode/cache` | Visual Studio Code | Editor settings and workspace state, installed extensions, and user caches. |
| `eclipse/workspace` | Eclipse | Workspace preferences, project metadata, and local history (`/ide-workspace`). |
| `codex/home` | Codex | `~/.codex` configuration, authentication, and local session state. |
| `claude-code/home` | Claude Code | `~/.claude` authentication, settings, and local session state. |
| `antigravity-cli/home` | Antigravity CLI | `~/.gemini` settings, project registry, and local session state. |
| `codex/openai-api-key` | Codex | Optional `host-environment:OPENAI_API_KEY`; exported into the container environment and visible to all capsule processes. |
| `antigravity-cli/gemini-api-key` | Antigravity CLI | Optional `host-environment:GEMINI_API_KEY`; exported into the container environment and visible to all capsule processes. |

For directory bindings, `config bind` prints the slot's sensitivity
(`ordinary`, `personal`, or `credentials`) and its sharing restriction. All
directory slots above declare `concurrent = false`. For secret bindings, it
warns that all capsule processes and Docker inspection can see the value.
Every binding is rechecked when `project run` derives the launch plan. For ordinary application environment
variables rather than component-declared secret inputs, use
`devcapsule project config env set`.
