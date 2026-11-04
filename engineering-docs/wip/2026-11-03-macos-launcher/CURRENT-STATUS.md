# Workstream Current Status: macOS Launcher

Mnemonic: `macos-launcher`

Start date: 2026-11-03

State: active; on `main` since #338, 2026-11-04, with `linux-arm64`; waits on the owner's rulings

Branch association: `ws-macos-launcher/host-port`, forked from local `main` at b3f10b7d

Integration target: `main`

Delivery method: pull request, merge commit; the human opens and merges it

Requirements: R-PRODUCT-002 (host boundaries stay explicit on the new host); R-CONFIG-001

## Goal And Scope

Run the DevCapsule launcher natively on an Apple Silicon Mac (`darwin-arm64`) against
Docker Desktop, with capsules running as `linux-amd64` under Docker's x86 emulation.

In scope: the launcher on macOS, the existing `linux-amd64` lock, pins and base image used
unchanged, the host-side mechanisms that assume Linux, a `macos-aarch64` executable, and the
macOS platform page.

Out of scope, by the human's direction of 2026-11-03 ("do stage 2 no need for stage 1"):
`linux-arm64` capsules, their resolution matrix, pins and base image. Native-speed
capsules on Apple Silicon need that work later; this workstream leaves room for it.

## Current State

**2026-11-03, opened.** The human asked whether DevCapsule builds for ARM, then for native
macOS on Apple Silicon, and directed the macOS host port without ARM capsules. Evidence on
the human's Mac (macOS 27.0, arm64, Docker Desktop 29.3.1, `desktop-linux` context at
`~/.docker/run/docker.sock`, 14 CPUs, 47 GiB):

- `docker run --platform linux/amd64 ubuntu:24.04 uname -m` prints `x86_64`: emulation works.
- The locked base `devcapsule-base@sha256:8c97d308…` is a single-platform manifest.
- The development CLI runs (`version --json` answers), and every project command stops at
  `Unsupported platform 'darwin-arm64'; supported platforms: linux-amd64.`

The work plan, one slice each, is in the
[design note](2026-11-03-design-macos-host-port.md).

**2026-11-03, slices 1 and 2.** `Platform.current()` now means the platform this host runs
capsules as (`linux-amd64` on a Mac), with `HostOs` for host mechanisms. Every `docker run`,
buildx build and base pull carries `--platform linux/amd64` when the host emulates it, and a
native Linux launch composes the same command as before. A launcher whose own binary cannot
run in the capsule delivers `DEVCAPSULE_RUNTIME_PEX` instead, or refuses with that remedy.
The host-browser bridge is unavailable on macOS with a warning; its peer check reads
`LOCAL_PEERCRED`, and two macOS socket races in its protocol are fixed (an early rejection
closed with unread input; `shutdown` after the broker closed). The capsule user joins group 0
for Docker Desktop's socket. `project config show` answers on this Mac.

Validation on this Mac: the unit suite, 2,725 passed, 19 skipped (the container-side
supervisor and the X11-dependent recursive dogfood, by marker), from 411 failed and 461 errors
before; the host-open module 20 runs clean; `mypy --platform linux` clean over 269 files. `nox`
cannot run its sessions here, having no `python3.12` on `PATH`, so the commands were run from
`.venv` directly. The unit suite on Linux is still to run, inside an amd64 container.

**2026-11-03, slice 3 so far.** Host networking falls back to bridge on macOS with a warning:
under `--network host` the contained desktop and console would listen on the VM's loopback,
out of the Mac's reach. The unit suite pins the host OS to Linux by default, as it pins the
host-not-container default, and the macOS tests opt in; `real_host_os` opts a test out.

Both executables exist: `devcapsule-src/dist/devcapsule-macos-arm64`, built natively, and the
`linux-x86_64` runtime, built in an amd64 container from an export of 062782bf. In that
container the unit suite ran on Linux: 2,738 passed, 1 failed,
`test_recursive_host.py::test_staging_cleans_up_after_preparation_failure`, which expects a
`chmod 0500` directory to refuse a write and runs as root there; not caused by this change.
On this Mac after the fallback: 2,727 passed, 19 skipped; `mypy --platform linux` clean.

**2026-11-03, slice 3, the live launch.** The human raised Docker Desktop's disk to 96 GB.
Both executables rebuilt from 4e42d073. `nox -s ide-smoke -- --surface pycharm` passes on
this Mac with the macOS launcher delivering the Linux runtime: the first run built the
PyCharm formation under emulation in 10 minutes and failed only in the harness, the second
passed in 13 s. Two probe launches added what the smoke does not check: the capsule's desktop
open in Chrome on this Mac, PyCharm at its User Agreement 16 s after launch; `x86_64` in the
capsule; files written as uid 501 on both sides; with `docker-daemon` authorized, the IDE
user reaches Docker Desktop's daemon through group 0. The record is section 2.2 of the
design note. The User Agreement was left unaccepted; accepting it is the human's.

The harness had matched only the ready line a capsule prints; a launcher outside a container
prints another, so the smoke could not pass on any host but a capsule. It now takes either.
Its runtime digest check compares with the runtime the launcher delivers.

**2026-11-03, slice 4.** `docs/platforms/macos.md` now describes the experimental launcher
built from source on Apple Silicon: no macOS executable in the release, the two executables,
emulation, the bridge fallback, no host-browser bridge, Docker access reaching an `arm64`
daemon, file sharing, and a build of both executables. The page's commands were run on this
Mac, the Linux build from `git archive` of the commit into a `linux/amd64` container. The
install page sends Mac readers there. `nox -s docs-contract` skipped itself: the website
submodule is not initialized here, and fetching it needs the SSH key.

Reading for slice 4 found that a supported macOS release reopens
[D-0009](../../decisions/product/d-0009-launcher-delivers-identical-runtime.md): the
launcher cannot deliver its own bytes there. Today's path is the explicit user override
D-0009 admits. The design note's section 4 states the question for the owner.

**2026-11-04, development sudo.** The human's first own launch on this Mac, a project with
development sudo, stopped at "Permission denied": the sudo policy must be root's, and Docker
Desktop shares a Mac file as the Mac user, which even root in the helper container cannot
change. Neither smoke nor probe had enabled sudo. On macOS root now writes the policy into a
Docker volume named after the container, mounted read-only and removed when the session
ends (e5bd8acd); the Linux helper gained `--platform` when emulating. A live VSCodium launch
with development sudo: the policy `0 0 0440` in the capsule, `sudo -n id -u` as the IDE user
prints 0, the volume gone afterwards. Unit suite on this Mac: 2,729 passed, 19 skipped. The
fixed pair is installed in the human's `~/.local`.

**2026-11-04, merged.** This branch reached `main` inside `linux-arm64`'s pull request,
which the owner merged as #338.

## Next Resumable Task

None in the plan; the slices are done and on `main`. The owner's rulings below remain.

## Open Threads

- No `python3.12` exists on this Mac. `.venv` was created with `uv venv --python 3.12`
  (CPython 3.12.12) instead of `python3.12 -m venv`; the executable still embeds 3.12.14.
- Adding a supported host platform is a product commitment. The repository owner has not
  yet ruled on it; the human started the work. It includes reopening D-0009 (design note,
  section 4) and how a release would ship the Linux runtime beside the macOS launcher.
- The macOS default for an authorized `network host`, bridge with a warning, was put to the
  human on 2026-11-03 with refusal as the alternative; no answer yet, so the warning stands.
- The PyCharm User Agreement in the probe sessions was left unaccepted, so the project
  window was not reached on this Mac.

## Document Index

- [2026-11-03-design-macos-host-port.md](2026-11-03-design-macos-host-port.md): the host
  assumptions found, the design of the platform split, and the slice plan. Open before
  each slice.
