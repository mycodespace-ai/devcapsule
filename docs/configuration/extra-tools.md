---
description: Install personal tools that the project does not declare under /opt/xtras so they persist across container replacements.
weight: 3
updated: 2026-10-30
---
# Extra tools

Shared project requirements belong in `.devcapsule/devcapsule.toml`. Personal
tools that only you need—such as a cloud CLI, a database client, or a language
toolchain you are evaluating—belong under `/opt/xtras` inside the capsule:

- `/opt/xtras` is writable by the capsule user without `sudo`.
- `/opt/xtras` is a symlink to `/home/devcapsule/xtras` inside the checkout's
  persistent `home` directory, so everything installed there survives stopping,
  removing, recreating, or upgrading the container.
- `/opt/xtras/bin` is prepended to `PATH` for the IDE, login shells, and coding
  agents.

Install a tool into its own subdirectory under `/opt/xtras` following the
vendor's user-space instructions, then link its executable into
`/opt/xtras/bin`:

```bash
# Replace my-tool with the directory and executable you installed.
ln -s /opt/xtras/my-tool/bin/my-tool /opt/xtras/bin/my-tool
```

Because `/opt/xtras` lives inside the checkout's `home` slot, each checkout
gets its own `/opt/xtras` under your active [configuration home](home.md)
unless you rebind `home` with `devcapsule project config bind home
host-directory:PATH` or `devcapsule project state adopt --from PATH home`. You
manage installation and updates yourself: files in `/opt/xtras` are not
recorded in the project lock, are not copied to other machines, and are not
verified against future base images. `devcapsule project info` lists the
`xtras` entry alongside its host backing directory (`<home backing>/xtras`).
