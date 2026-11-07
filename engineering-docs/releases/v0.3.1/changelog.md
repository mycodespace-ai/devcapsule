# DevCapsule 0.3.1 changelog, since 0.3.0

Maintained by the agent driving the release and updated at every candidate,
from the merged pull requests and the bug records, for adopters: what is
new and what is fixed since 0.3.0. Records, workflow rules and the
project's own housekeeping are left out on purpose. The adopter notes for
the final release, `notes.md`, are written from this file.

No candidate is tagged yet; the cut is 2026-11-07 at `31e8fec7` on `main`.

## New

- **Apple Silicon Macs, experimental.** The launcher runs natively on an
  M-series Mac against Docker Desktop, built from source as the macOS guide
  describes; no macOS executable is published. A project's capsules run
  natively as `linux-arm64`, the default on a Mac, or as `linux-amd64`
  under Docker Desktop's emulation. VSCodium, VS Code, Eclipse, PyCharm,
  Rider and IntelliJ IDEA start natively as ARM. Docker Desktop's
  differences are handled for you: the capsule user joins the socket's
  group, a project authorized for `network host` launches on bridge
  networking with a warning and reaches your Mac as `host.docker.internal`,
  the host-browser bridge is unavailable with a warning, and the launcher
  delivers the Linux runtime you built from `DEVCAPSULE_RUNTIME_PEX`,
  refusing one of another version. Intel Macs are untested.
- **One lock per capsule platform.** A project has `devcapsule.linux-amd64.lock`,
  `devcapsule.linux-arm64.lock` or both, and runs as the first platform the
  host runs that it has a lock for. On a host that runs more than one,
  `project init` asks which platform a new project is for; `--platform`
  answers without the question and adds a platform's lock to a project
  locked for another. A Linux host runs one platform and is never asked.
- **An arm64 base.** `mycodespaceai/devcapsule-base:linux-arm64-recipe-11-20261104`
  is published and pinned for `linux-arm64` capsules, the image the native
  IDE smokes ran on. Nothing changes for `linux-amd64`, which keeps the
  0.3.0 base.
- **`project wrap`.** Run at the top of a Git repository, the wrapper, it
  adds someone else's repository as a submodule with its Git directory
  embedded in the tree, requires the capabilities you name, creates the
  manifest and lock as `init` would or extends yours, declares the source
  under `[sources."<path>"]` with its Java line and, when the origin is your
  fork, its upstream, and writes `AGENTS.md` and `README.md` from the
  manifest for an agent to read. It infers nothing from the foreign tree.
  `config show` lists each source. The guide: *Someone else's repository*.
- **The compatibility feed from the website.** `project versions check`
  reads `https://devcapsule.mycodespace.ai/status/compatibility-v1.json`;
  `DEVCAPSULE_STATUS_URL` overrides the address for every check and
  `--status-url` for one. The last successful fetch is cached in
  `~/.cache/devcapsule/`, a snapshot is built into the launcher, and the
  report names which of the three it used. A launcher never fails to start
  because the feed cannot be fetched. The website path is not served yet;
  until it is, every check uses the cache or the snapshot.

## Changed

- **The project's home is `github.com/mycodespace-ai/devcapsule`.**
  Releases from 0.3.1 on are published there; the website's links and the
  install guide name it. The old repository under the personal account
  stays as it was at the move and is not a redirect.

## Fixed

Nothing yet. The bug table lists what the cycle is asked to fix, Eclipse's
acquisition on amd64 first.

## Not in candidate 0

- A macOS or arm64 executable; the owner's ruling is open.
- The compatibility feed's path on the website; the owner's ruling is open.
- The remaining wrapped-projects slices.
- The agent upgrades: Codex 0.167.0, Claude Code 2.1.319 and Antigravity
  CLI 1.5.3 are ahead of the tested pins 0.166.0, 2.1.314 and 1.4.12.
