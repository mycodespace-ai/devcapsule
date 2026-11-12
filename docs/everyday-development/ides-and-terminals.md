---
description: The IDEs DevCapsule offers, the terminal inside them, and how the capsule's shell differs from your computer's.
updated: 2026-10-30
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
| `python-ide` | PyCharm (`pycharm`) | Python 3 from the base image |
| `frontend-ide` | VSCodium (`codium`, default) or Visual Studio Code (`vscode`) | Node.js and npm from the base image |
| `vscode-ide` | Visual Studio Code (`vscode`) | Polyglot editor; combine with base or component toolchains |
| `java-ide` | IntelliJ IDEA (`intellij`) | Temurin Java and Maven (`JAVA_HOME`, `MAVEN_HOME`) from the base image |
| `eclipse-ide` | Eclipse IDE for Java Developers (`eclipse`) | Bundled Eclipse runtime plus Java and Maven from the base image |
| `dotnet-ide` | JetBrains Rider (`rider`) | `.NET` SDK (`dotnet-sdk`) selected automatically |

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
