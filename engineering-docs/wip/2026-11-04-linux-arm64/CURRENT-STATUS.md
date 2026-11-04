# Workstream Current Status: linux-arm64 Capsules

Mnemonic: `linux-arm64`

Start date: 2026-11-04

State: active; on `main` since #338, 2026-11-04, its arm64 base published; the follow-up pull request turns
`main`'s CI green again

Branch association: `ws-linux-arm64/capsules`, forked from local `main` at b3f10b7d, with
`ws-macos-launcher/host-port` merged in as its foundation; merged to `main` as #338 from dcc2a7db.
Follow-up: `ws-linux-arm64/mirror-and-published-base`, from `main` at bf7e5d66

Integration target: `main`

Delivery method: pull request, merge commit; the human opens and merges it

Requirements: R-RUNTIME-001 (the runtime delivered matches the capsule); R-COMPAT-001
(projects locked for `linux-amd64` keep working); R-CONFIG-001

## Goal And Scope

Run capsules as `linux-arm64` as well as `linux-amd64`: natively on Apple Silicon Macs
through the `macos-launcher` work, and on ARM Linux hosts.

In scope, by the human's answers of 2026-11-04:

- every component the `linux-amd64` matrix offers, pinned for `linux-arm64` in one
  workstream: PyCharm, IntelliJ IDEA, Rider and the .NET SDK, Eclipse and its native
  package closure, VSCodium, VS Code, the Codex, Claude Code and Antigravity CLIs, and
  Playwright;
- an arm64 base image built locally from the existing recipe and approved per checkout as a
  local base; publishing it, and pinning its digest, is the owner's;
- on an Apple Silicon Mac, a project runs as `linux-arm64` when it has a `linux-arm64` lock,
  and otherwise as `linux-amd64` under emulation, as today;
- a `linux-aarch64` runtime executable for arm64 capsules.

Out of scope: publishing images or executables; release automation.

## Current State

**2026-11-04, opened.** The human, running capsules on the Mac under emulation, directed
native ARM capsules: "ok we need linux arm64", then answered four questions: everything at
once; build the base locally now; arm64 when locked, else amd64; a new workstream built on
the macOS branch. Two read-only surveys mapped the work; the plan is in the
[design note](2026-11-04-design-linux-arm64.md).

**2026-11-04, slices 1 to 3.** `Platform.LINUX_ARM64`; a project runs as the first platform
the host runs that it has a lock for, and `project --platform` names one (f1bba6c9,
7a32f1c6). `DEVCAPSULE_RUNTIME_PEX` may name a directory of runtimes. The arm64 base was
built natively here from a launcher at public `main` b3f10b7d and pinned at its local index
digest, unpublished (7a32f1c6). Every component is pinned for arm64 at the amd64 versions,
102 artifacts, 15.6 GB hashed from their bytes (87e71b19), and the Eclipse closure gained
`libunwind8`, which arm64's GStreamer needs (b12e2516). The human's own switch of
`~/hello-devcapsule` to arm64 found that a checkout's personal pins kept the amd64 VSCodium;
personal pins are now re-pinned per platform (52fb1a1a).

Native arm64 smokes on this Mac with the local base: VSCodium passed in 58 s with its main
window; VS Code passed. Eclipse failed at `libunwind8`, since fixed; PyCharm, Rider and
IntelliJ failed on Docker I/O errors when the Mac's disk filled. The disk filled because
these runs built five formations at once on top of a 20 GB artifact cache, and Docker
Desktop's VM failed with it; a restart recovered it. With the human's consent the test
images and build cache were removed, and the reruns go one surface at a time, checking free
space first and removing each image after. The macOS test session now removes its temporary
root; each run had left one in `/tmp`.

Found for `maintenance`, not fixed here: the amd64 Eclipse closure's `libsoup-3.0-0` and
`libsoup-3.0-common` 3.4.4-5ubuntu0.8 URLs return 404, since Ubuntu removed that version from
every noble pocket on 2026-10-08, so Eclipse cannot be acquired afresh on amd64.

**2026-11-04, review and fixes.** The human had all changes since `main` reviewed by a
separate agent: rejected, seven high, fourteen medium, three low findings. The human said "fix all"; the design note's section 5 records them, and
section 3 the design they produced. In short: a Mac creates `linux-amd64` projects again and
runs a project as the first platform it has a lock for; the configuration answers which
(`storage.project_platform`), and below it the lock's platform is passed down explicitly; a
delivered runtime must be the launcher's build; the unpublished arm64 base is reported at
init and refused at launch without a local base; Docker Desktop's conventions are `HostOs`
properties; emulation is the daemon's. Unit suite on this Mac: 2,749 passed, 25 skipped.
The human's `~/hello-devcapsule` checkout holds amd64 VSCodium pins labelled arm64, written
by the bug since fixed; re-choosing its IDE through DevCapsule commands repairs it.

**2026-11-04, after the fixes.** A personal pin is remapped when its table is exactly
another platform's embedded pin, whatever its label, so the human's checkout healed without
a command (4d2aeb28): their `~/hello-devcapsule` capsule runs natively, `aarch64`, an arm64
VSCodium. The unit suite in Linux containers: amd64, emulated, 2,770 passed, 4 failed; arm64,
native, 2,757 passed, 17 failed. Both fail three recursive-orchestrator tests that need a host
X11 directory, as `main` does in a headless container now that the skip is Linux-only. The
amd64 run fails a console test whose 0.3 s timeout emulated Python misses; it passes natively.
The arm64 run fails 14 console-channel tests whose real `devcapsule` subprocess sees the
arm64 host while the suite's fixtures are amd64: a limit of the suite on ARM Linux, not CI.
The IDE smoke takes `DEVCAPSULE_SMOKE_PLATFORM` to create its project for a platform.

**2026-11-04, native smokes and a second review.** One at a time, each after a check of free
space and followed by removing its images, every IDE passed natively as `linux-arm64` with
the local base: VSCodium, VS Code, Eclipse, PyCharm, Rider and IntelliJ IDEA, runs
20261104T120158Z-e8f78f to 20261104T121007Z-289109. The JetBrains IDEs were seen at their
splash window. The six are the `linux-arm64` matrix's first verified edges; the .NET SDK and
Playwright rode along unexercised and stay unverified. A second review of all changes since
`main`, and a review against the codebase's own conventions, followed; the design note's
section 5 records both, and 9d285a5a their fixes: `project --platform` and its module-global
selection are gone and `project init --platform` adds a lock; an owner's edit regenerates
every lock; the lock's platform is required below the configuration; the sudo-policy sweep
spares a concurrent launch's volume; comments, messages and tests follow the surrounding
code. Unit suite on this Mac: 2,760 passed, 25 skipped; in a `linux/amd64` container, 2,779
passed and 5 failed, the same five recursive tests that fail on `main` there, for want of a
host X11 directory, a non-root user and a Docker group. From 9d285a5a, VSCodium passed
natively (20261104T130201Z-392364, created with `init --platform linux-arm64` and verified
without `--unverified`) and under emulation (20261104T130042Z-36f56a).

**2026-11-04, init asks for the platform.** The human's first init of a new project on the
Mac chose `linux-amd64` without a question; they ruled that init ask on a host of several
platforms, the native one by default ("depending on the current os just ask", "default
arm64 on arm"). `Platform.current()` is now the native platform, and init asks through its
elicitor before the identity questions: Enter, or a run without a terminal, takes it. A
project with a lock the host runs is not asked, and a Linux host never is.

**2026-11-04, on today's `main`.** Rebased onto `main` at 7ab3adcd, which brought the
unit-test conventions of WORKFLOW-LOCAL.md: a legacy test file only loses tests. Every test
this branch added or changed now lives in the `tests/unit` mirror with a contract docstring;
the two end-to-end files it changed are marked `e2e` at module level; the Linux-only skips
it had added to three legacy files are gone, so on a Mac those tests fail as they do on
`main`. The gate: 108 legacy files holding 1,461 tests, 22 conforming files, no breach.
In a `linux/amd64` container, 2,821 passed and 5 failed, the five that fail on `main` there.

**2026-11-04, merged, and the base published.** The owner merged the pull request as #338
from dcc2a7db, before the three commits above it were pushed, so `main`'s CI fails at the
conventions gate: 115 breaches in legacy files. `ws-linux-arm64/mirror-and-published-base`
carries those three commits, applied unchanged onto `main` at bf7e5d66. `main` now has the
Linux-only skips the move had taken out of three legacy files, so they stay: taking them out
again would change legacy tests. The gate against bf7e5d66: 108 legacy files holding 1,461
tests, 22 conforming files, no breach. The human pushed
this Mac's arm64 base as `mycodespaceai/devcapsule-base:linux-arm64-recipe-11-20261104`
at 15:29 UTC; the registry returns the pinned index digest, `sha256:7d32268065b6…`, for
`linux/arm64`, so the pin and its six verified edges stand. The pin's `published` flag,
init's note and report line, and the launch's refusal served only the unpublished base and
are removed; the macOS page no longer builds or selects a local base.

## Next Resumable Task

The human pushes `ws-linux-arm64/mirror-and-published-base` and opens its pull request;
once it is merged and `main`'s CI is green, the owner's rulings remain.

## Open Threads

- `main` at bf7e5d66 fails CI at the conventions gate until the follow-up branch is merged.
- A rebuilt arm64 base gets another digest: it must be pushed, pinned and smoked again.
- The libsoup 404 on amd64 goes to `maintenance` by intake mail once the coordination branch
  can be pushed.
- Docker access from an arm64 capsule reaches an arm64 daemon either way; on amd64 capsules
  under emulation it also defaults to arm64 images (`docs/platforms/macos.md`).
- A checkout that selected a locally built arm64 base before the push keeps it until its
  base is answered `default` again, as the macOS page says.

## Document Index

- [2026-11-04-design-linux-arm64.md](2026-11-04-design-linux-arm64.md): what the second
  platform needs, the decisions, and the slices. Open before each slice.
