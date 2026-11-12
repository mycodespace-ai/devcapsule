---
description: Check prerequisites, download the DevCapsule executable for this release, verify its SHA-256 checksum, and install it under ~/.local/bin.
weight: 1
updated: 2026-11-03
---
# Install DevCapsule

DevCapsule ships as a single executable for **Linux (`x86_64` / Intel-AMD
64-bit)**. It requires a web browser and a working Docker daemon on the same
machine. It does not run natively on macOS, Windows, or ARM. **On Windows, read
[Windows via WSL2](../platforms/windows-wsl2.md) first** and run every command
below inside your WSL2 Linux terminal. On an Apple Silicon Mac, read
[macOS](../platforms/macos.md) for the experimental launcher you build from
source; the steps below do not apply.

## Check your computer

In a Linux terminal:

```bash
uname -sm
docker info
docker buildx version
```

Expect `Linux x86_64`, Docker server details, and a Buildx version. If Docker
is missing or prints a connection or permission error, complete [Docker Engine
installation](https://docs.docker.com/engine/install/) first. Docker must work
for your ordinary user account—never run `devcapsule` with `sudo`.

You also need `curl` and `sha256sum`. Allow several gigabytes of free disk
space for the base image and IDE on your first launch; subsequent launches
reuse those cached layers.

## Download, verify, install

Paste this block into your terminal to download the release executable, check
its SHA-256 digest, and install it to `~/.local/bin/devcapsule`:

```bash
(
  set -eu
  download_dir="$(mktemp -d)"
  cd "$download_dir"
  release_url="{{download_url}}"
  curl --fail --location --output devcapsule.pex "$release_url/devcapsule.pex"
  curl --fail --location --output devcapsule.pex.sha256 "$release_url/devcapsule.pex.sha256"
  sha256sum --check devcapsule.pex.sha256
  mkdir -p "$HOME/.local/bin"
  install -m 0755 devcapsule.pex "$HOME/.local/bin/devcapsule"
)
```

Expect `devcapsule.pex: OK`. If checksum verification fails, delete the
temporary file and retry—never install an unverified binary.

Check the installed version:

```bash
~/.local/bin/devcapsule version
```

Expect `{{tag}}` (release notes: [{{tag}}]({{release_url}})). The release
executable includes its own Python runtime. You do not need host Python, a
virtual environment, `pip`, or a source checkout.

The onboarding walkthroughs spell out `~/.local/bin/devcapsule` so they work
immediately even before `~/.local/bin` is on your shell's `PATH`. Add
`$HOME/.local/bin` to `PATH` in your shell profile (`export
PATH="$HOME/.local/bin:$PATH"`) to run `devcapsule` directly as shown in the
rest of the documentation.

**Next: [your first session](first-session.md).**
