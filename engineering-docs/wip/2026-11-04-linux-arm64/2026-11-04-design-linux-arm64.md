# Design: linux-arm64 Capsules

Workstream: `linux-arm64`. Written 2026-11-04 from two read-only surveys of the launcher and
the base recipe, on top of `macos-launcher`'s platform split. File references are to
`devcapsule-src/`.

## 1. What exists

- **Resolution is already per platform.** `MATRICES` (`resolution_matrix.py`) maps each
  `Platform` to one matrix of base pins, component pins, verified edges, capabilities and
  materialization recipes. Locks are `devcapsule.<platform>.lock`; a project may commit one
  per platform, and a checkout holds one version set.
- **The base recipe is arch-neutral.** `images/base.py` renders a Dockerfile from
  `ubuntu:24.04` and Ubuntu packages, which exist for arm64; Node and Temurin choose their
  archive by `dpkg --print-architecture`, and Temurin's arm64 digest is already pinned.
- **Discovery already speaks arm64.** `components/discovery.py` and `npm_channel.py` map
  `linux-arm64` for JetBrains, Eclipse, VSCodium, VS Code, Claude Code and npm packages.
- **What is amd64-only.** `Platform` has one member; every component pin is an amd64
  archive; Eclipse refuses other platforms (`components/eclipse.py`); Codex's npm alias map
  names only `linux-amd64` (`components/codex.py`); the JetBrains runtime check names
  `libskiko-linux-x64.so` (`assets/*/check-runtime-deps.sh`); `build-pex.sh` defaults to a
  `linux-x86_64` scie; the published base is a single-platform amd64 manifest.

## 2. Decisions taken by the human, 2026-11-04

1. Every component at once, not a first slice.
2. The arm64 base is built locally and approved per checkout; the owner publishes later.
3. On Apple Silicon, a project runs as `linux-arm64` when it has a `linux-arm64` lock, and
   otherwise as `linux-amd64` under emulation. Amended the same day, after the human's
   first init of a new project: on a host that runs several platforms, init asks which a
   new project is for, the native one by default ("depending on the current os just ask",
   "default arm64 on arm").
4. A new workstream on the macOS branch.

## 3. Design

1. **`Platform.LINUX_ARM64`.** Host detection stays in `platforms.py`: `runnable()`, every
   platform a host runs, native first (Apple Silicon: arm64, then amd64 under emulation),
   and `current()`, the host's native platform, a new project's default, per section 2's
   amended ruling; init asks on a host of several platforms. Which platform a
   project runs as is the configuration's question: `configuration.storage.project_platform`,
   read-only, answers the first runnable platform the project has a lock for, else
   `current()`. `project init --platform` adds a platform's lock, and the project then runs
   as it; `images build --platform` names the platform of a base build. A checkout so runs
   one platform until its project's locks change. An owner's edit of the shared contract
   regenerates every lock the project carries, so a committed lock never falls behind the
   manifest (R-COMPAT-001). Below the configuration, the platform is the lock's, a required
   parameter of the base pull, the image build, the runtime choice and the launch (D-0006's
   consequence). Emulation is judged against the Docker daemon's architecture, asked once
   per launch, not the launcher's CPU.
2. **The runtime.** An arm64 capsule needs a `linux-aarch64` executable. A launcher whose own
   binary runs on the capsule platform delivers itself (R-RUNTIME-001). Otherwise the user
   names the runtime: `DEVCAPSULE_RUNTIME_PEX` names one file, or a directory holding
   `devcapsule-linux-amd64` and `devcapsule-linux-arm64`. A runtime that is not the
   launcher's own bytes must be its build: the same version, and the same revision where
   both record one.
3. **The base.** Built natively on this Mac by `devcapsule images build --type base`, and
   approved per checkout by the documented local-base path. Whether the `linux-arm64` matrix
   can resolve without a published base pin is slice 2's first question.
4. **Pins.** The same versions as the amd64 matrix, each with its arm64 archive's URL and a
   sha256 computed from the downloaded bytes, never copied from a page alone. Eclipse's
   native closure comes from `ports.ubuntu.com`. Playwright's Chromium has no
   Chrome-for-Testing arm64 build; its arm64 source is slice 3's open question, and
   `browser-automation` is unavailable on arm64 with a warning (R-CONFIG-001) if none passes.

## 4. Slices

1. **Second platform.** `LINUX_ARM64`, the per-project selection, the runtime directory, the
   `linux-aarch64` scie, the Eclipse, Codex and skiko hard-codes, tests. Done when the unit
   suite passes here and on Linux, and `project init` on this Mac writes an arm64 lock
   against a stub matrix.
2. **Base.** Build the arm64 base here; settle how the arm64 matrix and a local base meet.
3. **Pins.** Every component, by script: download, hash, record.
4. **Live and documentation.** `nox -s ide-smoke` for every surface natively on this Mac;
   the Linux, macOS and install pages.

## 5. Reviews, 2026-11-04

A review of all changes since `main`, run by a separate agent, rejected the
branch with seven high findings: a Mac's new projects defaulting to the unpublished arm64
base; `images build` ignoring the project's locks; the platform read from a process-wide
selection below the configuration instead of from the lock; no version check on the
delivered runtime; personal pins re-derived on their own platform; a leaking sudo-policy
volume; a hash test that skipped three components. Fourteen medium and three low findings
followed. The human said "fix all"; each is fixed as described in section 3, except that a
lock naming an unpublished base is reported, not refused, since the human's ruling has the
checkout select a local base for it.

A second review of all changes since `main`, and a review of the branch against the
codebase's own conventions, followed the fixes. The first rejected the branch again with
three high findings: an owner's edit on a Mac rewrote only the lock of the platform the
project ran as, leaving the committed `linux-amd64` lock behind its manifest; a checkout's
one base-image answer applied to whichever lock `project --platform` named, so switching
platforms per command broke the launch; and each macOS launch's sweep of sudo-policy
volumes could remove a concurrent launch's fresh one. Nine medium and three low findings
followed. The second found seventeen departures, the first that `--platform` was kept in a
module global, process-wide state the codebase nowhere else has. The fixes are section 3's
design: `project --platform` is gone, owner edits regenerate every lock under one journal
that still reads the single-lock form an older launcher wrote, the sweep removes only
unused policy volumes older than a day, and the retained successor plan carries its
planned `--platform`. Comments, messages, tests and the generated pin module now follow the
surrounding code.

Left as it is: a checkout keeps one base-image answer. A developer who deletes the arm64
lock to return to emulation answers the base again (`docs/platforms/macos.md`).

## 6. What this does not decide

- Publishing an arm64 or multi-platform base, or arm64 release executables: the owner's.
- Whether ARM Linux becomes a supported release platform: the owner's.
- D-0006 says host detection is `current()` and parsing a lock is `parse()`, with
  deliberately no third way to obtain a `Platform`. `runnable()`, a host's list, and
  `of_elf_machine()`, an executable's platform, are two more; amending D-0006 to name them
  is the owner's.
