# DevCapsule 0.3.1 changelog, since 0.3.0

Maintained by the agent driving the release and updated at every candidate,
from the merged pull requests and the bug records, for adopters: what is
new and what is fixed since 0.3.0. Records, workflow rules and the
project's own housekeeping are left out on purpose. The adopter notes for
the final release, `notes.md`, are written from this file.

RC3 was published on 2026-11-17 at `918f9fc7`; downloaded assets are verified.
It includes the merged SSH proxy and initial presentations support.
The recording-kit, link-command and runtime-help changes below merged after RC3, through
PRs #50–#52, for the next candidate; they are not in the RC3 executable.
Graphviz is also added after RC3 through PR #56 for the next candidate.

The RC4 source also adds Xfce Terminal as a selectable desktop, updates the linux-amd64 component pins to embedded-36, and lets the `ssh-proxy` authorization select a host key. Existing `github-ssh` authorizations remain readable.

## New

- **Graphviz diagrams.** Require or offer the `graphviz` capability to supply
  Graphviz 16.1.1 under `/opt/graphviz`, independently of the selected IDE.
  Its pinned source and platform dependencies build offline; `dot`, `neato`,
  `sfdp` and the other packaged tools are on PATH. SVG, PNG and PDF output are
  included. See [Graphviz setup](../../../docs/configuration/capabilities.md#graphviz-diagrams).

- **Recorded scenarios with an agent.** `devcapsule bootstrap project` and
  `devcapsule project wrap` install the complete versioned recording kit in
  project skill directories. Existing kits and customizations are preserved.
  Ask the agent to run a scenario and record a presentation; it reads the
  installed instructions and Python helpers. The initial `presentations`
  commands from RC3 are removed without aliases. For older installed skills,
  follow the [migration procedure](../../../docs/working-with-ai/instructions-for-agents.md#keep-or-update-an-existing-kit).
- **Console content links.** Inside a capsule, `devcapsule instance --get-link
  PATH-OR-URL` prints a current-run link. Filesystem paths always select Files;
  absolute URLs on the current console can select Records or Presentations.
  The command does not create or verify the content.

- **GitHub SSH through the host agent.** An authorized capsule can use GitHub
  SSH through a narrow host-side proxy without copying the host's private keys
  into the capsule. Merged through PR #47; the Git guide describes setup and
  the containment boundary.

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

- **A Files page in the web console.** Every file of the mounted project,
  listed directory by directory at `/files` and served read-only with its
  media type: a recording or an image opens in the browser, a Markdown
  file opens in Records, and each row has a download link. The raw route
  seeks by byte range, so long videos play from any point. `/filetree`
  leads to the same page. Built by Pair Review as PR #12, merged
  2026-11-08.

## Changed

- **The project's home is `github.com/mycodespace-ai/devcapsule`.**
  Releases from 0.3.1 on are published there; the website's links and the
  install guide name it. The old repository under the personal account
  stays as it was at the move and is not a redirect.
- **The launcher delivers its matching web console.** Materialization installs
  the launcher's own `devcapsule_webconsole` package at
  `/opt/devcapsule/webconsole` on the base image's pinned interpreter, so
  web-console updates ship with each launcher release without a base-image
  rebuild. A built executable runs its own console even on a DevCapsule
  checkout unless `DEVCAPSULE_DEV_WEBCONSOLE=1` opts into the checkout copy.
- **Refreshed Codex and Claude Code pins (`embedded-33`).** New locks and
  upgrades select Codex `0.167.0` (up from `0.166.0`) and Claude Code
  `2.1.321` (up from `2.1.314`) on both `linux-amd64` and `linux-arm64`,
  retaining all prior pins so existing locks remain valid.

## Fixed

- **Runtime-check help.** `devcapsule pycharm check-runtime --help` and `-h`
  now print usage without running diagnostics, including outside a project.

- **Rootless Docker launch identity.** The launcher uses the container's root
  identity when Docker reports rootless mode, avoiding inaccessible mounted
  launcher settings and cache paths. Non-rootless behavior stays unchanged;
  the owner verified the rootless fix before candidate packaging.
- **Video playback from Files.** Recordings open in the console's media player
  instead of navigating to a raw response whose policy prevents playback.
  Candidate-level browser verification remains before bug closure.

- **Codex version and compatibility checks answer again.** `NpmChannel.check()`
  requests the npm registry's abbreviated install metadata
  (`Accept: application/vnd.npm.install-v1+json`, ~5.2 MiB for `@openai/codex`
  against the channel's 16 MiB cap) rather than the full 18.7 MB package
  history, restoring `project versions check` for Codex and the published
  compatibility feed's Codex probe.
- Eclipse can be acquired from scratch on Linux x86-64 again. The closure's
  two libsoup packages are repinned at `3.4.4-5ubuntu0.10`, the build the
  Ubuntu archive serves since it replaced `0.8` on 2026-10-08; the arm64
  closure already pinned it. A lock generated by an earlier launcher still
  names the removed files; regenerate it with the 0.3.1 launcher. Embedded
  matrix `embedded-32`.

## Not in candidate 0

- A macOS or arm64 executable; the owner's ruling is open.
- The compatibility feed's path on the website; the owner's ruling is open.
- The remaining wrapped-projects slices.
- Antigravity CLI 1.5.3 (held at 1.4.12 pending test-fixture decoupling on
  `main`).
