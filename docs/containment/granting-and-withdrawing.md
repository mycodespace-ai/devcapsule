---
description: Inspect recommended host access, grant only what your checkout needs, allow access for a single launch, or deny and forget saved answers.
weight: 2
updated: 2026-10-30
---
# Granting and withdrawing access

Run these commands from your project directory on the host. Authorization
changes apply to the **next** launch—exit any running capsule, update your
choices, and start `devcapsule project run`.

## See what is recommended and pending

```bash
devcapsule project config show
```

`config show` lists every authorization row with its effective value, where
that value came from (`checkout`, `home trust`, `secure default`), and whether
a project recommendation is awaiting your answer. Each pending row prints the
exact command that settles it.

## Grant access for this checkout

```bash
devcapsule project config authorize network host
devcapsule project run
```

`config authorize` saves your answer in this checkout's record alongside a
digest of the recommendation you answered.

If you run `devcapsule project run` interactively before answering a project
host-access recommendation, the launcher displays the project's `--because`
reason and DevCapsule's boundary warning and lets you:

- **allow for this checkout** (saved),
- **allow once** (this launch only),
- **deny for this checkout** (saved), or
- **skip for now** (launches with the secure default and asks again next time).

Without an interactive terminal, unanswered host-access recommendations fall
back to their secure defaults during `project run`, while `devcapsule project
config check` exits with status `3` so scripts can detect unanswered rows. If
the project later changes a host recommendation's reason, your previously saved
allowance or denial stays in force and `config show` notes what changed—a
committed manifest edit never widens access behind your back.

To preview every host-access recommendation declared by the project and accept
all of them interactively:

```bash
devcapsule project config authorize --all-recommended
```

The command prints every recommended value and reason first and writes only
when you press `y`. (It never enables host capabilities that the project did
not recommend.)

## Allow for one run only

```bash
devcapsule project run --authorize host-browser true
```

Without `--save`, `--authorize` applies to that single launch and leaves your
checkout record unchanged; add `--save` to persist the answer once launch
checks succeed.

The five host-access nodes—`network`, `docker-daemon`, `development-sudo`,
`host-browser`, and `host-x11`—are available on every project whether or not
the manifest recommends them. Extra `docker run` flags can also follow `--` (or
be saved via `config docker-args set`), except options owned by the launcher
such as `--network`, `--memory`, `--cpus`, `--privileged`, and `--shm-size`,
which are refused with a reason or a supported alternative. `--shm-size` has
no user setting; the IDE component declares it. Extra flags such as mounts
and added Linux capabilities can widen access, so inspect saved flags with
`devcapsule project config docker-args list`.

## Deny and forget

```bash
devcapsule project config deny host-x11
devcapsule project config forget network
```

- `config deny NAME` records an explicit denial on any of the five host-access
  nodes (`network`, `docker-daemon`, `development-sudo`, `host-browser`,
  `host-x11`). To deny a vendor download on one checkout (overriding home
  channel trust), use `devcapsule project config authorize claude-code-download
  false` (or `none`).
- `config forget NAME` deletes your saved answer for a host access or software
  consent so the secure default (or home trust / project prompt) applies on the
  next launch.

## Authorization values at a glance

Every authorization below accepts `default` to select its recommended or pinned
value. **This is not the secure fallback:** `authorize network default` grants
`host`, and `authorize docker-daemon default` grants `host-socket`, even without
a project recommendation. Use the deny values below to withhold access.
`none` selects a node's deny value; `base-image` has no deny value.

| Authorization | Grant value | Deny value | Notes |
|---|---|---|---|
| `network` | `host` | `bridge` (`none` stores `bridge`) | `bridge` is the secure default when unanswered |
| `docker-daemon` | `host-socket` | `none` | Exposes `/var/run/docker.sock` when set to `host-socket` |
| `development-sudo` | `true` | `false` (`none` stores `false`) | Passwordless `sudo` inside the container only |
| `host-browser` | `true` | `false` (`none` stores `false`) | Opens `http(s)` links in your host browser |
| `host-x11` | `true` | `false` (`none` stores `false`) | Exposes your host X11 display session; never recommended by a manifest |
| `vscode-download`, `claude-code-download`, `antigravity-download` | `true` | `false` (`none` stores `false`) | Per-checkout vendor consent (or denial overriding home channel trust) |
| `base-image` | `default`, pinned `<reference>`, or local `<tag-or-id>` | *(mandatory; no deny state)* | Covered across projects by `home trust accept devcapsule-base`, or per checkout here ([Build and select a local base](../configuration/local-base.md)) |

See [Vendor software and trust](../configuration/software-approvals.md) for
home-wide channel trust, [The boundary](the-boundary.md) for what each grant
exposes, and [Configuration nodes](../reference/configuration-nodes.md) for the
full node reference.
