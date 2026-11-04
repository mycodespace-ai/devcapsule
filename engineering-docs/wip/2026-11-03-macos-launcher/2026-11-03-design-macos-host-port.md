# Design: The Launcher On macOS

Workstream: `macos-launcher`. Written 2026-11-03 from a read of the launcher and probes on
an Apple Silicon Mac with Docker Desktop 29.3.1. Statements marked *to verify* are read from
code or recalled Docker Desktop behaviour, not yet observed on this host.

## 1. The two platforms

Today one value plays two roles. `Platform.current()` (`devcapsule/platforms.py`) derives a
key from the host's `system` and `machine`, and every caller uses it to name and select the
platform lock and the resolution matrix:

- `configuration/storage.py`: the lock path `devcapsule.<platform>.lock`, and the refusal of a
  version set recorded for another platform;
- `configuration/derivation.py`, `configuration/operations.py`,
  `configuration/owner_commands.py`, `version_sets.py`: `MATRICES[Platform.current()]`.

None of those callers asks about the host. They ask which platform the capsules run as. On
Linux the two coincide. On a Mac the host is `darwin-arm64` and the capsules are Linux.

Design:

1. `Platform` keeps its meaning, the wire format of a lock: a capsule platform. Its members
   stay append-only; no `darwin-*` member is added, because no lock is ever for macOS.
2. `Platform.current()` keeps its name and its callers, and its contract becomes *the
   platform this host runs capsules as*. On Linux it is the host's own platform, as now. On
   macOS it is `linux-amd64` on both architectures: Intel natively, Apple Silicon under
   Docker's emulation. When `linux-arm64` exists, Apple Silicon maps to it and emulation
   becomes the fallback, not the rule. The mapping lives in `platforms.py` alone.
3. A new `HostOs` (`linux`, `darwin`) names the host's operating system for the host-side
   mechanisms of section 2. Feature code asks `HostOs.current()`, never `sys.platform`.
4. `Platform.docker_platform` gives Docker's spelling (`linux/amd64`), and
   `Platform.emulated()` says whether this host's CPU differs from the capsule platform's.
   When it does, every `docker run` and every buildx build the launcher composes carries
   `--platform`, so that Docker does not pick the host's architecture for a multi-platform
   image or warn on a single-platform one.

Rejected: renaming `current()` to `for_capsules()`. The name is accurate once the contract is
written down, and the rename touches 27 call and test sites for no behaviour.

## 2. Host mechanisms that assume Linux

Found by reading the launch path from `run_pycharm` (`launch/pycharm/_launcher.py`) outward.

| Mechanism | Where | On macOS | Plan |
|---|---|---|---|
| Lock and matrix key | section 1 | refuses `darwin-arm64` | slice 1 |
| Docker `--platform` | `_launcher.py` `docker run`; `images/build.py` buildx | Docker picks arm64 or warns | slice 1 |
| Host-browser bridge | `host_open.py` | peer check used `SO_PEERCRED`, Linux only; the broker socket is a host Unix socket bind-mounted into the capsule, which Docker Desktop refuses (section 2.1) | slice 2: unavailable on macOS with a warning, per R-CONFIG-001; the peer check also reads macOS `LOCAL_PEERCRED`; a TCP transport is a later decision. The contained desktop's own opener is Python's `webbrowser`, which already uses `open` |
| Host Docker socket | `_launcher.py` `host_docker_socket`, `write_user_files` | both socket paths bind; `--group-add` took the host file's gid (`staff`), but the socket is `0:0 0660` inside (section 2.1) | slice 3: on macOS the capsule user joins group 0; the capsule already holds the daemon, root on the VM, so the root group adds no authority beyond it; confirmed in the live launch (section 2.2) |
| Container identity | `current_host_user`, `write_user_files` | 501:20; the generated `/etc/group` avoids the image's `dialout`; ownership round-trips (sections 2.1, 2.2) | none |
| Container detection | `host_daemon.py` | a marker file, not `/proc`; already correct (section 2.1) | none |
| Runtime artifact | `runtime_artifact.py` | the launcher delivers its own executable into the capsule; a macOS binary cannot run there | slice 1: deliver `DEVCAPSULE_RUNTIME_PEX` when the launcher's own binary is foreign, refuse with the remedy otherwise; how a release ships the Linux runtime beside the macOS launcher is slice 4 |
| Executable | `scripts/build-pex.sh` | `DEVCAPSULE_SCIE_PLATFORM=macos-aarch64` | slice 4 |
| Development sudo | `ensure_sudoers_policy_ownership`, `build_docker_args` | the policy must be root's; a bind-mounted Mac file stays the Mac user's, and the helper's `chown` is refused even to root (found by the human, 2026-11-04) | fixed: on macOS root writes the policy into a Docker volume named after the container, mounted read-only from it and removed with the session; `sudo -n id -u` prints 0 in a live launch |
| Ports | `--publish 127.0.0.1:<port>` | forwarded to the Mac's loopback (section 2.1) | none |
| Host networking | `_launcher.py` `build_run_config` | a listener on loopback under `--network host` is unreachable from the Mac; a bridge publish to `127.0.0.1` answers (section 2.1) | slice 3: on macOS an authorized `network host` launches on bridge with a warning; the Mac's services are `host.docker.internal`. This is the concrete reason and fallback *Local Launch Networking* asks to record, and a product default for the owner to confirm |

### 2.1 Observed on this Mac, 2026-11-03

Docker Desktop 29.3.1, macOS 27.0, arm64, `desktop-linux` context.

- **Host Unix sockets.** A host socket as a bind source fails with `invalid mount config for
  type "bind": bind source path does not exist: /socket_mnt/<host path>`, for a socket in the
  session scratch, in `$TMPDIR` (`/var/folders/…/T/devcapsule-host-open.*/broker.sock`, where
  the broker would bind it, 90 bytes) and in `~/.cache`. Docker Desktop rewrites the source to
  `/socket_mnt/…` and does not find it. The host-browser bridge cannot reach a capsule.
- **The Docker socket** is the exception: `/var/run/docker.sock` on the Mac is a symlink to
  `~/.docker/run/docker.sock`, and binding either path gives the capsule a socket owned
  `0:0`, mode `0660`. The host file's group means nothing inside.
- **Ownership.** A capsule process running as `501:20` writes files that the Mac shows as
  owned by uid 501; the group is the parent directory's, as macOS assigns it.
- **Identity.** The launcher writes the capsule's `/etc/passwd` and `/etc/group` whole, so the
  host's `staff` (20) does not collide with the image's `dialout` (20).
- **`/proc`.** `host_daemon.in_container()` tests a marker file; nothing on the host path reads
  `/proc`. The row above is void.
- **Networking.** A `linux/amd64` HTTP server bound to `127.0.0.1` under `--network host` is
  unreachable from the Mac (`curl` HTTP 000); the same server on bridge, published to
  `127.0.0.1:18766`, answers HTTP 200. `host.docker.internal` resolves inside a capsule.
- **Executables.** `build-pex.sh` with `DEVCAPSULE_SCIE_PLATFORM=macos-aarch64` builds natively
  here: a 31 MB Mach-O arm64 scie, CPython 3.12.14, that answers `version --json` and
  `project config show`. The `linux-x86_64` runtime, 40 MB, builds inside a `linux/amd64`
  `python:3.12-slim` container from an export of the commit. With both, `runtime_artifact()`
  delivers the Linux one, and without `DEVCAPSULE_RUNTIME_PEX` it refuses with the remedy.
- **Disk.** Docker Desktop's VM disk was 32 GB with 5.9 GB free; the base is 0.89 GB
  compressed. The human raised it to 96 GB before the live launch.

### 2.2 The live launch, 2026-11-03

The macOS launcher and the `linux-x86_64` runtime, both built from 4e42d073, against Docker
Desktop on this Mac. Evidence under `devcapsule-src/dist/e2e-evidence/` (not committed).

- **`nox -s ide-smoke -- --surface pycharm` passes.** The first run took 10 minutes: it built
  the PyCharm formation under emulation, the build's last step alone 63 s. It failed only in
  the harness, which matched the ready line a capsule prints, not the one a host prints; see
  below. The second run, from the built image, passed in 13 s: desktop page 200, console 200
  with its token and 403 without, a `jetbrains-pycharm` window, the capsule's runtime equal to
  the Linux runtime delivered, container removed, project records removed.
- **The launch**, as the launcher printed it: the host-networking warning, then bridge, the
  desktop on container port 6080 published to `127.0.0.1:<port>`, the console on 6081 the
  same way. `docker inspect` shows network mode `bridge`, platform `linux`, both ports bound
  to `127.0.0.1`.
- **In a Mac browser.** The desktop URL opened in Chrome on this Mac shows the capsule's
  desktop with PyCharm's User Agreement, the first window of a fresh configuration, 16 s
  after launch: splash at 10 s, the agreement at 16 s. Nobody accepted it, so the project
  window was not reached.
- **Identity and ownership.** `uname -m` in the capsule is `x86_64`. PyCharm's JVM runs as
  uid 501, gid 20. A file the IDE user writes in the project is uid 501 on the Mac, group
  the parent directory's; a host file reads as `501 20` inside. The workspace was under
  `/private/tmp`, which Docker Desktop shares by default.
- **Docker socket.** With `--authorize docker-daemon host-socket`, the container gets
  `--group-add 0`, PyCharm's process carries groups `0 20`, and the IDE user's
  `docker version` reaches Docker Desktop's daemon (server 29.3.1, `arm64`) and `docker ps`
  lists the host's containers. The daemon is the VM's: an image the IDE user runs without
  `--platform` is `arm64`, unlike the capsule itself.
- **Host-browser bridge.** Not exercised: unavailable on macOS with its warning (section 2.1).
- **The harness.** The smoke's readiness pattern required the ready line that names the URL,
  which a launcher inside a capsule prints. A launcher outside a container opens the URL
  instead, a no-op under the smoke's `BROWSER=true`, and prints the ready line without it;
  on any host but a capsule the smoke waited out its 600 s. The harness now takes either
  ready line and the URL from the launcher's earlier announcement. The child-runtime
  digest check compares with the runtime the launcher delivers.
- **Test suite.** Before slice 1: 411 failed and 461 errors of 2,743. After the platform
  split: 30 failed and 24 errors, in four groups: the supervisor (container-side,
  `signal.sigwaitinfo` is Linux only); Unix socket paths beyond macOS's 104 bytes under the
  per-user temporary directory; the recursive dogfood, which validates a host X11 socket
  directory; the host-browser bridge.

## 3. Slices

1. **Capsule platform.** Section 1, `--platform` on run and build, `/proc` absence. Done when
   `project config show` and `project run --print-command` answer on this Mac, and the unit
   tests pass here and keep passing on Linux.
2. **Browser bridge.** Unavailable-with-warning on macOS; `open` as the opener for when a
   transport exists.
3. **Live launch.** A real `project run` of this repository on this Mac: Docker socket,
   identity, ownership of written files, ports, the contained desktop in a Mac browser.
   Findings decide the code; this slice is mostly evidence.
4. **Executable and documentation.** A `macos-aarch64` scie, smoke-tested here; the macOS
   platform page and the install page rewritten for what works; release automation is the
   owner's call. Done 2026-11-03: the page describes the experimental from-source launcher,
   its differences from Linux, and a build of both executables whose commands were run on
   this Mac; the install page sends Mac readers there.

## 4. What this does not decide

- Whether macOS becomes a *supported* platform in a release. That is the owner's ruling;
  this workstream produces the evidence for it.
- [D-0009](../../decisions/product/d-0009-launcher-delivers-identical-runtime.md), one
  executable outside and inside. A macOS launcher cannot deliver its own bytes, so on macOS
  the delivered runtime is the user's explicit choice in `DEVCAPSULE_RUNTIME_PEX`, which
  D-0009's third point admits. As a product default it would not hold: D-0009's *Reopen If*
  names this case, a supported execution environment that cannot run the launcher inside its
  container. A macOS release needs the owner to reopen it and say how identity holds, for
  example a macOS launcher that carries the exact Linux runtime bytes and delivers them, or
  one that fetches the release's Linux executable against a digest it pins.
- Signing and notarization of a macOS executable.
- `linux-arm64` capsules.
