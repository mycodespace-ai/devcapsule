---
description: What a capsule and its coding agents can reach on your computer by default, what stays isolated, and which permissions you can grant or withdraw.
role: containment
weight: 1
updated: 2026-10-30
---
# The boundary

A capsule runs your IDE and coding agents inside a container. By default,
it mounts your project directory and managed state, but not your host home
directory or display session. It also has outbound network access.
You can inspect and withdraw saved authorizations.

## Shared by default

| What crosses | How it works | Why |
|---|---|---|
| Project working tree | Mounted read-write at `/workspace/<slug>` (or the manifest's `project.mount`) | Edits change your real files, including `.git`; keep an independent backup |
| Per-checkout persistent home and component slots | Managed host directories under your [configuration home](../configuration/home.md), mounted into the capsule | Preserves IDE preferences, plugins/extensions, agent sign-ins, and `/opt/xtras` across container replacements ([What persists](../sessions/what-persists.md)) |
| Outbound internet (`bridge` network) | Outbound connections work, including to reachable host and LAN services; host loopback is separate, and only session endpoints are published by default | Package managers, language servers, and hosted AI APIs need outbound HTTPS |
| Contained desktop and web console | Loopback-only (`127.0.0.1`) ports with fresh per-run tokens for the desktop tab and (on base recipe `11`+) the read-only/request [web console](../sessions/web-console.md) | Gives you the IDE desktop and session inspector in your browser without exposing your host display session |

Also mounted read-only on startup when present: your active configuration
home's `settings.toml` (channel trust names and resource defaults, containing
no credentials) so `devcapsule home show` works inside the capsule. The launcher
also mounts this checkout's configuration and launch context read-only, plus
writable session-log and console-request directories. It supplies generated
user/group files and session tokens. See [The
configuration home](../configuration/home.md#inside-a-capsule).

## Not shared by default

- **Your host home directory (`$HOME`)**, shell dotfiles, `~/.ssh` keys, cloud
  CLI profiles, browser cookies, and password stores—agents inside the capsule
  cannot read them because they are not mounted.
- **Your host clipboard**—text crosses only when you copy or paste through the
  contained desktop's clipboard panel ([Clipboard and
  browser](../everyday-development/clipboard-and-browser.md)).
- **Your host display server**—the capsule renders on its own virtual display
  and cannot capture your host windows or keystrokes.
- **Your host Docker daemon**—processes inside the capsule cannot start or
  inspect host containers.
- **Your host network namespace**—services listening on `127.0.0.1` on your
  computer are not reachable as `localhost` inside the capsule.
- **Host root privileges**—unprivileged capsules run with `--cap-drop ALL` and
  `--security-opt no-new-privileges`. Granting `development-sudo` removes
  these restrictions inside the container. Granting a rootful host Docker
  socket can give capsule processes root-level control of the host.

## What you can grant

Every permission below is an authorization node visible in `devcapsule project
config show`. A project manifest may recommend host access with a reason, and
only you can grant it; see [Granting and withdrawing
access](granting-and-withdrawing.md) for the commands.

| Authorization | What it opens | Grant it when |
|---|---|---|
| `network host` | Shares your host network namespace: host `localhost` services and capsule ports become one namespace | Your app needs direct access to host-bound services or dynamic local ports ([Services and ports](../your-project/services-and-ports.md)) |
| `docker-daemon host-socket` | Mounts `/var/run/docker.sock` into the capsule | Your build or tests start containers; this grants broad control of the daemon and its host bind mounts |
| `development-sudo true` | Grants passwordless `sudo` **inside the capsule container** | You need to install temporary OS packages inside a session |
| `host-browser true` | Forwards `http://` and `https://` URLs opened inside the capsule to your host browser through a URL-only broker | OAuth sign-ins and external documentation links are more convenient on your host browser |
| `host-x11 true` | Runs the IDE directly on your host X11 display instead of the contained desktop | Almost never—X11 lets clients read keystrokes, clipboard, and windows across your entire host display session; manifests cannot recommend it |
| `vscode-download`, `claude-code-download`, `antigravity-download` (`true`) | Permits DevCapsule to download that vendor's pinned artifact under its license terms (when not already covered by home channel trust) | You selected that IDE or agent and accept its vendor terms ([Vendor software and trust](../configuration/software-approvals.md)) |
| `base-image` (`default` or `<image>`) | Approves the lock's pinned base digest for this checkout or selects an inspected [local base image](../configuration/local-base.md) | Settled once via home `devcapsule-base` trust or per-checkout consent |

Authorizations take effect on the **next** launch; they do not change a running
container. The five host-access nodes can also be granted for one run with
`project run --authorize ...`. Base and vendor consents require saved approval
or home channel trust. A Git repository cannot grant itself an authorization.

## Working with coding agents

An agent can edit mounted files, run builds and tests, and change persistent
checkout state. Files under the project mount remain accessible, including
credentials accidentally stored there. Git cannot protect its own metadata
from a process with write access.

Use `devcapsule project config show` to inspect saved authorizations. Also
inspect `config docker-args list`: extra Docker options can add mounts and
capabilities outside those authorization nodes. Changes to either apply on
the next launch.
