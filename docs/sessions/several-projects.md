---
description: Run multiple projects at once, or register additional checkouts and worktrees of one repository so each runs in its own capsule.
weight: 3
updated: 2026-10-31
---
# Several projects

You can keep several capsules running on the same computer at the same time—either
for unrelated repositories or for parallel branches of one repository. Each
checkout gets its own configuration record, its own persistent directories, and
its own desktop and [web console](web-console.md) URLs.

## Two different projects

Projects with different `creator` and `slug` fields in
`.devcapsule/devcapsule.toml` are already separate everywhere on your machine:

- Checkout configuration lives under
  `~/.config/devcapsule/projects/<creator>/<slug>/devcapsule.checkout.toml`
  (the creator and slug are URL-encoded in these paths).
- Managed `home`, IDE, agent, log, and cache directories live under
  `projects/by-path/<checkout-id>` inside your XDG data, state, and cache
  roots.
- Each `devcapsule project run` selects available loopback ports on `127.0.0.1`
  and fresh per-run tokens for its desktop and web console.

Open a terminal in each project directory, run `devcapsule project run`, and
keep each capsule's desktop and web console in their own browser tabs. Docker layers for shared
base images, IDEs, and capabilities are stored once in your local Docker cache
and reused across projects.

## Two checkouts or worktrees of the same project

When you clone a repository a second time or create a `git worktree`, both
directories share the same `creator` and `slug` in
`.devcapsule/devcapsule.toml`. The first checkout you configure claims that
project's `default` record (`devcapsule.checkout.toml`), tied to its canonical
directory path on disk.

If you run a configuration or launch command in the second directory,
DevCapsule refuses to overwrite or mix the first checkout's choices and asks
you to register the new directory under its own name:

```bash
git worktree add ../my-app-auth -b feature/auth
cd ../my-app-auth
devcapsule project checkout register auth
devcapsule project run
```

You can also register from outside the directory with `--path`:

```bash
devcapsule project --path ~/worktrees/my-app-auth checkout register auth
```

Checkout names start with an ASCII letter or digit and may contain letters,
digits, `.`, `_`, or `-`. Registering creates
`~/.config/devcapsule/projects/<creator>/<slug>/checkouts/auth.checkout.toml`.
From then on:

- Every `devcapsule project ...` command run inside `~/worktrees/my-app-auth`
  automatically selects the `auth` checkout record by matching its path.
- You can pick a different IDE, optional capabilities, resource limits, or host
  authorizations in `auth` without touching `default`.
- Its managed persistent storage (`home`, IDE settings and indexes, agent
  state, session logs) lives under its own `by-path` namespace, so both
  checkouts can run side by side without IDE lock conflicts.

From a host terminal, run `devcapsule project list` to see registered checkout
names, paths, and record status. Inside a capsule, it reports only that
capsule’s checkout. It does not list running containers; use `docker ps` for
that.

Run `devcapsule project info` in any checkout to confirm its `Checkout name`,
host checkout path, and storage paths.

## Do not launch twice in the same directory

Avoid running `devcapsule project run` twice at the same time in a single
checkout directory. Desktop IDEs place process locks in their configuration and
workspace directories (`concurrent = false`), and two containers sharing one
working tree and one IDE index directory at once will either fail the lock
check or step on each other's files. Whenever you want a second live session on
the same repository, create a `git worktree` (or second clone) and register it.

For the same reason, only share a slot with `devcapsule project config bind
<slot> host-directory:PATH` across checkouts that you run **one at a time**;
leave concurrent checkouts on their default per-checkout storage (see
[IDE preferences and plugins](../configuration/ide-preferences.md)).

## Practical tips for concurrent capsules

- **Name containers when inspecting Docker directly:** pass `--name` on launch
  (`devcapsule project run --name my-app-auth`) when you want predictable names
  in `docker ps` and `docker stats` instead of the generated
  `pycharm-isolated-<user>-<timestamp>` name.
- **Budget memory and CPUs:** each capsule's `--memory` / `config set memory`
  and `--cpus` / `config set cpus` limits apply per container, not across all
  running capsules combined. Size per-checkout or [home defaults](../configuration/home.md)
  so two or three concurrent IDEs and language servers fit comfortably in your
  machine's RAM; see [Resource limits](../configuration/resource-limits.md).
- **Watch loopback ports under host networking:** the desktop and web console
  always pick free loopback ports automatically, regardless of network mode. If
  two capsules both authorize `--authorize network host` and start an
  application server on the same port (such as `localhost:3000`), the second
  server fails with `EADDRINUSE`—either run one server on another port or keep
  capsules on default `bridge` networking; see
  [Previews and ports](../everyday-development/previews-and-ports.md).

## Separate configuration homes

Named checkouts normally provide the separation you need. To keep home defaults,
channel trust, checkout records, and managed storage separate too, select an
isolated home on the host:

```bash
DEVCAPSULE_CONFIG_HOME="$HOME/.devcapsule-homes/testing" devcapsule project run
```

Use the same `DEVCAPSULE_CONFIG_HOME` value for later configuration, listing,
and launch commands in that home. Its managed data, state, and cache live under
that directory. Your working tree and the Docker daemon’s image cache remain
shared; see [Home defaults](../configuration/home.md).
