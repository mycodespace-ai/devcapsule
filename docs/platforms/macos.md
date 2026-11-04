---
description: An experimental launcher you build from source runs on Apple Silicon Macs against Docker Desktop, with capsules emulated or native.
weight: 3
updated: 2026-11-04
---
# macOS

DevCapsule {{tag}} ships no macOS executable. The release executable is for
64-bit Intel/AMD Linux and does not run on macOS.

The launcher in the source tree runs natively on **Apple Silicon Macs**
(`darwin-arm64`) against **Docker Desktop**, built by you. This is
experimental and not a supported platform in {{tag}}. Intel Macs are untested.

A project runs as one of two capsule platforms:

- **`linux-arm64`, natively, the default.** Faster, with a base image of its
  own for ARM.
- **`linux-amd64`, under emulation.** The same environments Linux users get,
  with the same base, run by Docker Desktop under x86-64 emulation.

`devcapsule project init` asks which one a new project is for; Enter takes
`linux-arm64`, and `--platform PLATFORM` answers without the question. A
project runs as `linux-arm64` when it has a `linux-arm64` lock, and otherwise
as `linux-amd64`.

## What differs from Linux

- **Two executables, or three.** On Linux the launcher copies itself into the
  capsule. A macOS executable cannot run there, so you build the Linux runtime
  for each capsule platform you use and put them in one directory that
  `DEVCAPSULE_RUNTIME_PEX` names. Each launch delivers the one for its
  project's platform and refuses one of another DevCapsule version. Rebuild
  them whenever you rebuild the launcher: runtimes of the same version from
  another commit are not told apart.
- **Emulation.** Under `linux-amd64`, the first launch of an IDE builds its
  image under emulation: about ten minutes for PyCharm on a 14-core Mac. Later
  launches reuse the image. The IDE runs slower than on a native host.
- **Networking.** Docker Desktop's host network belongs to its virtual machine,
  out of your Mac's reach. A project authorized for `network host` launches on
  bridge networking instead, with a warning. The contained desktop and the
  [web console](../sessions/web-console.md) are published to `127.0.0.1` as on
  Linux, and the capsule reaches services on your Mac as `host.docker.internal`.
- **No host-browser bridge.** Docker Desktop cannot share a Mac socket with a
  container, so links the IDE opens cannot reach your Mac's browser. The launch
  warns and continues. The contained desktop still opens in your browser.
- **Docker inside the capsule.** With `docker-daemon` authorized, the capsule's
  Docker client reaches Docker Desktop's daemon, whose engine is `arm64` on
  either capsule platform: an image you run from inside the capsule is the ARM
  variant unless you pass `--platform linux/amd64`.
- **File sharing.** Keep projects under a directory Docker Desktop shares, by
  default `/Users`, `/Volumes`, `/private`, `/tmp` and `/var/folders`. Files the
  capsule writes there belong to your user.

## Build and install

You need Docker Desktop with several gigabytes free under **Settings →
Resources → Disk usage limit**, and about as much free on the Mac itself, plus
Git and Python 3.12. From a clean checkout of a published commit:

```bash
git clone https://github.com/ccozianu/devcapsule.git
cd devcapsule/devcapsule-src
python3.12 -m venv .venv
.venv/bin/pip install -r dev-requirements.txt
.venv/bin/pip install -e . --no-deps
revision="$(git rev-parse HEAD)"
DEVCAPSULE_SCIE_PLATFORM=macos-aarch64 PYTHON=.venv/bin/python \
  scripts/build-pex.sh --source-revision "$revision" --allow-unpublished-revision \
  --output dist/devcapsule-macos-arm64
for target in amd64:linux-x86_64 arm64:linux-aarch64; do
  git -C .. archive HEAD | docker run --rm -i --platform "linux/${target%%:*}" \
    -v "$PWD/dist:/out" python:3.12-slim sh -c "
      mkdir /build && tar -x -C /build && cd /build/devcapsule-src &&
      python -m venv /venv && /venv/bin/pip install -q -r dev-requirements.txt &&
      /venv/bin/pip install -q -e . --no-deps &&
      DEVCAPSULE_SCIE_PLATFORM=${target#*:} PYTHON=/venv/bin/python scripts/build-pex.sh \
        --allow-local-source --output /out/devcapsule-linux-${target%%:*}"
done
```

This writes the macOS launcher and a Linux runtime for each capsule platform,
all from the same commit. `--allow-unpublished-revision` skips only the check
that the commit is a branch tip; the commit itself must be public, since a base
build installs the web console from it. Install them:

```bash
mkdir -p ~/.local/bin ~/.local/lib/devcapsule
install -m 0755 dist/devcapsule-macos-arm64 ~/.local/bin/devcapsule
install -m 0755 dist/devcapsule-linux-amd64 dist/devcapsule-linux-arm64 ~/.local/lib/devcapsule/
export DEVCAPSULE_RUNTIME_PEX="$HOME/.local/lib/devcapsule"
~/.local/bin/devcapsule version
```

Add the `export` line, and `$HOME/.local/bin` on your `PATH`, to your shell
profile. Then continue with
[your first session](../getting-started/first-session.md); init asks for the
platform, and Enter takes `linux-arm64`.

## Run a project natively as `linux-arm64`

A new project is `linux-arm64` unless you answer otherwise. To run a project
locked for `linux-amd64` natively, add the arm64 lock beside the other:

```bash
devcapsule project init --platform linux-arm64
devcapsule project run
```

The first launch pulls the arm64 base. VSCodium, VS Code, Eclipse, PyCharm,
IntelliJ IDEA and Rider have each started natively on it. A component no arm64
run has validated yet, such as the .NET SDK or Playwright, needs `--unverified`
on `init` or on the `config` command that adds it; the command says so. A
change to the project's requirements made on your Mac updates both locks.

A checkout that selected a locally built arm64 base before this one was
published keeps it until you select the project's base again with
`devcapsule project config authorize base-image default`.

To run the project under emulation again, delete
`.devcapsule/devcapsule.linux-arm64.lock`.

If something fails on your Mac, please [open an issue](https://github.com/ccozianu/devcapsule/issues/new)
with your macOS and Docker Desktop versions and the error output, omitting
private session URLs and tokens.
