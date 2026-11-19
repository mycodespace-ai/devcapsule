---
description: The IDEs DevCapsule offers, the terminal inside them, and how the capsule's shell differs from your computer's.
updated: 2026-11-19
weight: 1
---
# IDEs and terminals

In a host terminal, choose one desktop IDE with `devcapsule project config ide
NAME` (or pass `--ide NAME` during `devcapsule project init`). Your IDE choice
is stored in your local checkout record rather than committed to the shared
manifest, so teammates on the same repository can each use their preferred
editor.

| Capability | IDE component | Included toolchains |
|---|---|---|
| `xfce4-terminal` | Xfce Terminal | Tabbed shells for the project’s selected tools and agents |
| `python-ide` | PyCharm (`pycharm`) | Python 3 from the base image |
| `frontend-ide` | VSCodium (`codium`, default) or Visual Studio Code (`vscode`) | Node.js and npm from the base image |
| `vscode-ide` | Visual Studio Code (`vscode`) | Polyglot editor; combine with base or component toolchains |
| `java-ide` | IntelliJ IDEA (`intellij`) | Temurin Java and Maven (`JAVA_HOME`, `MAVEN_HOME`) from the base image |
| `eclipse-ide` | Eclipse IDE for Java Developers (`eclipse`) | Bundled Eclipse runtime plus Java and Maven from the base image |
| `dotnet-ide` | JetBrains Rider (`rider`) | `.NET` SDK (`dotnet-sdk`) selected automatically |

## Choosing a tabbed terminal

Run `devcapsule project config ide xfce4-terminal` and then
`devcapsule project run`. Xfce Terminal opens maximized in the project directory
on the capsule desktop. Press **Ctrl+Shift+T** or choose **File → Open Tab**
to start another shell. For example, run `vi README.md` in one tab and a
configured CLI agent or a test command in another. Closing the
last terminal window ends the session. Preferences and shell history use the
checkout’s persistent home. The terminal has been verified on Linux amd64.
The Linux arm64 selection currently requires an unverified combination.

## Choosing Visual Studio Code

To select Microsoft Visual Studio Code when the project permits that IDE, run:

```bash
devcapsule project config ide vscode
```

(On a `frontend-ide` checkout, `devcapsule project config use frontend-ide
vscode` also switches the provider from VSCodium to VS Code.)

DevCapsule does not redistribute VS Code in published images. On the first
launch that needs a pinned version, DevCapsule downloads the archive directly
from Microsoft on your machine and verifies its SHA-256 digest. Trust the
channel once for your configuration home with `devcapsule home trust accept
vscode`, or approve it per checkout with `devcapsule project config authorize
vscode-download true` after reviewing [Microsoft's Visual Studio Code license
terms](https://code.visualstudio.com/license); see [Vendor software and
trust](../configuration/software-approvals.md).

## Host VS Code with a capsule terminal

With VS Code selected, enable `host-ide` for one session:

```bash
devcapsule project run --authorize host-ide true
```

Add `--save` to remember the grant, or run `devcapsule project config authorize
host-ide true`. It defaults to `false`. To return to the container editor, run
`devcapsule project config deny host-ide`. This first slice supports only
`vscode`; VSCodium and all other selected surfaces are refused.

Your saved IDE selection and project lock stay unchanged. For this launch,
DevCapsule materializes and supervises `xfce4-terminal` inside the capsule
and attaches host VS Code to the container's project directory with Microsoft's
Dev Containers extension. Tools, builds and agents still run in the capsule.
The terminal uses the browser desktop unless you separately authorize
`host-x11`. The host IDE does not grant Docker access inside the capsule or
change its Docker mode, network access or sudo authorization. The launcher
uses host Docker to attach. Recursive E2E readiness is disabled for DevCapsule
checkouts using `host-ide`.

The launcher first uses `code` on your host `PATH`, then an already unpacked
managed copy. If neither exists on Linux or macOS (amd64 or arm64), it requires
`devcapsule home trust accept vscode` (or `run --trust vscode`), downloads the
stable release from Microsoft and verifies its SHA-256 before installing it
under the DevCapsule data home's `host-ide/vscode/<version>/`. Download scratch
uses the cache home's `host-ide/vscode/`. On WSL2, install VS Code on Windows
with **Add to PATH**, reopen the WSL terminal, and check `code --version`;
DevCapsule does not download a Linux editor for WSL2. Host acquisition uses
home channel trust; a per-checkout `vscode-download` grant does not authorize
it. Container `vscode-download` consent is unnecessary for this launch.

The host editor has an isolated profile under your [DevCapsule configuration
home](../configuration/home.md): `host-ide/vscode/user-data/` and
`host-ide/vscode/extensions/`. The launcher installs
`ms-vscode-remote.remote-containers` there before starting the container and
preserves unrelated settings. On WSL2 with a Docker daemon inside the distro,
it sets `dev.containers.executeInWSL` to `true`; with Docker Desktop, to `false`.
Your normal VS Code profile is not imported. This profile separates preferences
and extensions; it is not a sandbox. Host VS Code and its host extensions run
with your host user's permissions, outside the capsule boundary.

After the container is running and its project directory exists, VS Code opens
in a new window. Closing that window leaves the terminal and agents running;
closing the terminal ends the capsule. On headless Linux, the launcher prints
the attach command for use on your desktop. `project run --print-command`
prints both commands without installing or starting VS Code; the ordinary
requirement that the container environment already exists still applies.

## Overriding a project-required IDE for one launch

When a project requires a specific IDE in `.devcapsule/devcapsule.toml` (for
example, while developing an IDE plugin), every checkout uses that IDE and
plain `run --ide` with another editor is refused. To launch a different IDE for
one session without modifying the manifest or your saved checkout record, add
`--force`:

```bash
devcapsule project run --ide codium --force
```

The launcher warns which required IDE it set aside, runs your requested editor
for this session only, and skips recording that departed run as a known-good
project configuration. You cannot combine `--force` with `--save`. Trust,
download consent, and dependency checks still apply. Your next plain
`devcapsule project run` checks the project's requirements against your saved
selection again; see [A required
IDE](../configuration/capabilities.md#a-required-ide).

## Eclipse and JetBrains specifics

- **Eclipse (`eclipse-ide`):** After opening the desktop URL, choose **File →
  Open Projects from File System** to import `/workspace/<slug>` (or **File →
  Import → Maven → Existing Maven Projects**). Keep your source files inside
  `/workspace/<slug>`; Eclipse stores workspace metadata, preferences, and local
  history separately at `/ide-workspace`, which persists per checkout alongside
  `/home/devcapsule`.
- **PyCharm, IntelliJ IDEA, and Rider:** Complete any JetBrains sign-in or
  license setup inside the capsule; DevCapsule does not supply a license or
  activate trials automatically. Settings and installed plugins persist per
  checkout under separate slots for each IDE ([IDE preferences and
  extensions](../configuration/ide-preferences.md)).
- **`.NET` with another editor:** Add or require the `dotnet` capability (for
  example, `devcapsule project config add dotnet` alongside `vscode-ide`) to
  include the pinned `.NET` SDK, runtime, and MSBuild (`DOTNET_CLI_TELEMETRY_OPTOUT=1`
  by default) without switching to Rider.

## The terminal inside the capsule

The IDE's integrated terminal runs inside the Linux container at
`/workspace/<slug>`, not on your host:

- Compilers, runtimes, and agents come from the pinned base image and selected
  components; your host's `PATH`, shell dotfiles, SSH keys, and cloud
  credentials are not imported.
- Your shell home is `/home/devcapsule`, which persists per checkout across
  container restarts—along with `~/.bashrc`, language caches (`~/.cache`,
  `~/.npm`, `~/.nuget`, `~/.m2`). `/opt/xtras` is an alias for `~/xtras`,
  so tools installed there also persist. `/opt/xtras/bin` is on `PATH` ([Extra tools
  in `/opt/xtras`](../configuration/extra-tools.md) and [What
  persists](../sessions/what-persists.md)).
