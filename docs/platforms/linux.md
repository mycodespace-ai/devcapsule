---
description: What DevCapsule needs from a Linux computer, and which distributions and Docker setups are supported.
weight: 1
updated: 2026-11-24
---
# Linux

DevCapsule {{tag}} ships as a single executable for **64-bit Intel/AMD Linux
(`x86_64` / `linux-amd64`)**. You need:

- **Docker Engine with Buildx**, usable directly by your ordinary user account
  (never run `devcapsule` under `sudo`).
- **A modern web browser** to open the capsule's contained desktop and
  [web console](../sessions/web-console.md) on `127.0.0.1`.
- **`curl` and `sha256sum`** to download and verify the release executable,
  plus several gigabytes of free disk space for base and IDE image layers.

[Install](../getting-started/install.md) starts with three commands to check
the architecture, Docker daemon, and Buildx.
ARM Linux (`aarch64` / `linux-arm64`) is not supported in {{tag}}.

DevCapsule is developed and tested on Ubuntu-family desktops using Docker
Engine from [Docker's official repository](https://docs.docker.com/engine/install/).
Other current `x86_64` Linux distributions with a standard Docker Engine and
Buildx setup are expected to work without special flags; if yours hits a
platform-specific failure, please [open an issue](https://github.com/mycodespace-ai/devcapsule/issues/new)
with your distribution, Docker version, and error output (omitting private
session URLs and tokens).

## Docker installed as a snap

DevCapsule {{tag}} does not run on Docker installed with
`sudo snap install docker`, on Ubuntu or on any other distribution. To check
yours:

```bash
command -v docker
```

`/snap/bin/docker` means the snap. It confines Docker in two ways that
DevCapsule cannot work around:

- Docker cannot see the computer's `/tmp` or the hidden directories in your
  home, where DevCapsule keeps its build files, cache, and data. Image builds
  fail with `path ... not found` or `failed to read dockerfile`.
- Docker cannot start a container with the `no-new-privileges` hardening that
  every capsule uses. The launch ends with `exec ...: operation not permitted`.

We recommend one of two routes:

1. **Replace the snap** with Docker Engine from
   [Docker's official repository](https://docs.docker.com/engine/install/).
   Before it removes anything, `sudo snap remove docker` saves a copy of all
   of Docker's data, which can take a long time and look stuck.
   `sudo snap remove --purge docker` skips that copy and permanently deletes
   every image, container, and volume the snap holds. DevCapsule needs none of
   that data, but only you know what else is in it: using `--purge` is your
   decision and at your own risk.
2. **Keep the snap and install a second Docker Engine beside it** for
   DevCapsule to use. Instructions for this setup are still to come.
