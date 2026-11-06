# DevCapsule Python CLI

This directory contains DevCapsule's Python CLI implementation, packaging and
contributor reference. Current project commands use `devcapsule project …`;
image operations use `devcapsule images …`.

`devcapsule project info` (or `info --json`) provides a read-only overview of
software, environment and persistent storage. It works from the host project's
directory or descendants and anywhere inside its running capsule. See
[extra tools and environment inspection](../docs/guides/your-project.md#install-extra-tools-0215)
for the persistent `/opt/xtras` contract.

## User Setup

To use DevCapsule, start with [your first session](../docs/guides/first-session.md):
download the released executable, open an IDE and return to your saved work.
You do not need to clone this repository, install Python or build an artifact.
For an existing repository or a coding agent, continue with
[use your own project](../docs/guides/your-project.md).

To develop DevCapsule itself, read [For developers](../DEVELOPING.md) and the
[subproject requirements](REQUIREMENTS.md), then use the setup below.

## Development Setup

Nox is the preferred developer cycle. By default this repository reuses Nox's
managed virtual environments between runs, so repeated commands avoid starting
from a completely fresh venv unless explicitly requested.

Create the checkout-local developer environment once, then call its interpreter
explicitly. Shell activation is optional.

```bash
cd devcapsule-src
python3.12 -m venv .venv
.venv/bin/python -m pip install -r dev-requirements.txt
.venv/bin/python -m pip install -e . --no-deps

.venv/bin/python -m nox -s tests   # Python compile checks plus pytest
.venv/bin/python -m nox -s syntax  # Python compile checks plus shell syntax checks
.venv/bin/python -m nox -s typecheck  # mypy for package, tests, and noxfile.py
.venv/bin/python -m nox -s smoke   # source CLI and shell-wrapper help smoke tests
.venv/bin/python -m nox -s pex     # build the PEX artifact and smoke-test it
.venv/bin/python -m nox -s build   # full local gate
```

The explicit interpreter path prevents a broken activation from silently
selecting `/usr/bin/python`. If preferred, activation works too:

```bash
. .venv/bin/activate
python -m nox -s build
```

A Python virtualenv is not relocatable: its activation scripts and installed
console-script shebangs contain the absolute path where it was created. If the
checkout or `devcapsule-src/` directory moves, rebuild this disposable
environment at its final path:

```bash
deactivate 2>/dev/null || true
python3.12 -m venv --clear .venv
.venv/bin/python -m pip install -r dev-requirements.txt
.venv/bin/python -m pip install -e . --no-deps
```

The `tests` session is the Nox way to run pytest for this project. It installs
the locked contributor dependencies into the managed Nox venv, installs
`devcapsule` editable with `--no-deps`, runs Python compile checks, then runs
`python -m pytest tests`.

The `typecheck` session runs `mypy` across the `devcapsule` Python package,
tests, and `noxfile.py`.

The `build` session is the default Nox session, so these are equivalent:

```bash
cd devcapsule-src
.venv/bin/python -m nox
.venv/bin/python -m nox -s build
```

Run a clean-slate build when dependency or environment reuse could hide a
problem:

```bash
cd devcapsule-src
.venv/bin/python -m nox --no-reuse-existing-virtualenvs -s build
```

If you want to discard all cached Nox environments before a clean build:

```bash
cd devcapsule-src
rm -rf .nox
.venv/bin/python -m nox -s build
```

The manual virtualenv workflow is still supported when directly inspecting a
developer environment:

```bash
python3.12 -m venv .venv-dev
. .venv-dev/bin/activate
python -m pip install --upgrade pip
python -m pip install -r dev-requirements.txt
python -m pip install -e . --no-deps

python -m pytest devcapsule
```

The Nox build session installs the locked contributor dependencies, installs
`devcapsule` editable with `--no-deps`, compiles Python files, checks shell
script syntax, runs `mypy`, runs tests, smoke-tests the Python CLI and shell
wrapper help, builds the PEX artifact, and smoke-tests the PEX CLI.

`pyproject.toml` is the source of truth for Python runtime and development
dependencies. The pinned `requirements.txt` and `dev-requirements.txt` files
are reproducibility artifacts. Contributors should use the locked setup above;
the direct `python -m pip install -e "./devcapsule-src[dev]"` path remains useful
for quick local checks when exact dependency reproducibility is not needed.

Regenerate lock files after editing dependencies in `pyproject.toml`:

```bash
cd devcapsule-src
python -m piptools compile --strip-extras pyproject.toml --output-file requirements.txt
python -m piptools compile --strip-extras --extra dev pyproject.toml --output-file dev-requirements.txt
```

## Component Version Sets

The v0.2.14 development CLI supports checkout-local component upgrades:
`devcapsule project versions show`, `check`, `preview COMPONENT VERSION`,
`select PREVIEW_ID`, `history`, `rollback`, `follow-project`, and `propose PATH`.
See [the practical upgrade and recovery guide](../docs/guides/component-upgrades.md).
Local choices preserve a complete version set without changing the committed
project lock. Only successful ordinary launches become known-good; rollback
preserves current host permissions and personal state.

Contributors adding a component must supply a distribution channel or document
why one is omitted. The [channel contract and implementation](../engineering-docs/implementation-notes/devcapsule/2026-09-21-component-distribution-channels.md)
describes the typed interface, exact acquisition, validation evidence and tests.
All six curated components have read-only discovery; Codex is the first complete
selection channel. No generic upgrade logic names it specially. Failed checks
consult the maintained [component status service](../component-status/README.md)
for applicable CLI fixes or known issues while preserving offline launch.

## Distribution Version

The Python distribution version is advanced only by an explicit developer
command. From `devcapsule-src/`, select a semantic increment or provide the
exact next numeric version:

```bash
python -m nox -s bump -- patch
python -m nox -s bump -- minor
python -m nox -s bump -- major
python -m nox -s bump -- 0.2.0
```

The version is authored in exactly one place, the `[project]` table of
`pyproject.toml`; the command rewrites that single line and refuses malformed,
equal, or decreasing versions. Everything else derives the version: runtime
code reads the installed distribution's metadata through `importlib.metadata`,
and `scripts/build-pex.sh` stamps it — with the release mnemonic and source
revision — into the build information embedded in every built artifact. A
source checkout carries no build information at all; `devcapsule version`
recognizes that absence as a source-form run and reports the derived
`v<version>-local` identity. Review and commit the version change before
building a public revision-bearing artifact.

## End-User Artifact

The published `devcapsule.pex` is a native Linux executable with an eagerly
embedded, stripped CPython runtime. An end user runs it directly: no Conda,
Python, pip, virtualenv, or first-run runtime download is required.

Build the single-file PEX scie from a contributor environment:

```bash
cd devcapsule-src
scripts/build-pex.sh
```

The script embeds source identity without modifying the checkout. By default
it requires clean PEX inputs and a full `HEAD` revision advertised by the
public GitHub repository, then records the repository, revision, and canonical
commit URL. Build a publication candidate only after its commit is pushed:

```bash
scripts/build-pex.sh
dist/devcapsule.pex version --json
```

For an explicit dirty development build, use
`scripts/build-pex.sh --allow-local-source`. That PEX discloses an `unknown`
revision instead of presenting local bytes as public source. The Nox build
gate uses this escape hatch because it validates changes before commit.
Every non-release binary also embeds a recognizable derived mnemonic such as
`v0.2.7-local-linux-x86_64`: the package version from `pyproject.toml`, a
`-local` marker, and the binary's target platform. An editable source install
reports plain `v0.2.7-local` because it is not a binary artifact. The mnemonic
describes the release identity for humans; source revision and the artifact
SHA-256 remain the exact identities.

For a clean commit that has not been pushed yet, use
`scripts/build-pex.sh --allow-unpublished-revision`. It embeds the exact local
`HEAD` and canonical commit URL while deliberately omitting only the GitHub
revision-existence check. The resulting artifact is suitable for local tests;
rerun the default strict command after pushing before publication.

For a deliberately local-only development artifact, use:

```bash
python -m nox -s pex
```

This session writes its intentionally local-only artifact to
`dist/devcapsule-local.pex`. The full `nox -s build` gate always builds and
tests that local artifact too. If the repository is clean, the full gate also
builds and smoke-tests `dist/devcapsule.pex` with the exact local `HEAD`, even
when that commit is not on GitHub yet. If the repository is dirty, it clearly
reports that the revision-bearing artifact was not built. The standalone
default `scripts/build-pex.sh` command retains the remote publication check.
An intentionally origin-free clean clone can provide canonical public metadata
only to the final Nox packaging step:

```bash
DEVCAPSULE_PUBLIC_PEX_SOURCE_REPOSITORY=https://github.com/OWNER/REPOSITORY \
  python -m nox -s build
```

Nox does not translate that value into the packaging script's general
`DEVCAPSULE_SOURCE_REPOSITORY` variable until after tests complete, so nested
packaging tests retain their own isolated repository metadata.

If the contributor environment is not activated, point the script at it:

```bash
PYTHON=/path/to/venv/bin/python devcapsule-src/scripts/build-pex.sh
```

Run the artifact directly:

```bash
devcapsule-src/dist/devcapsule.pex --help
devcapsule-src/dist/devcapsule.pex project run --help
devcapsule-src/dist/devcapsule.pex pycharm build --help
```

Published executable downloads and checksum verification are documented in
[your first session](../docs/guides/first-session.md#1-get-devcapsule). The
remaining examples in this section are contributor build/release validation,
not prerequisites for using DevCapsule.

To build a full candidate base and run the Docker E2E smoke suite using a
published executable:

```bash
cd devcapsule-src # from the repository root
release_tag=v0.2.11-rc3
release_dir="$PWD/dist/releases/$release_tag"
mkdir -p "$release_dir"
for asset in devcapsule.pex devcapsule.pex.sha256 release-manifest.json; do
  curl --fail --location --output "$release_dir/$asset" \
    "https://github.com/mycodespace-ai/devcapsule/releases/download/$release_tag/$asset" || exit 1
done
(cd "$release_dir" && sha256sum --check devcapsule.pex.sha256) || exit 1
chmod 0755 "$release_dir/devcapsule.pex"
DEVCAPSULE_PEX_UNDER_TEST="$release_dir/devcapsule.pex" \
DEVCAPSULE_EXPECTED_BUILD_MNEMONIC="$release_tag" \
  .venv/bin/python -m nox -s e2e -- --build-base
```

Pull `ubuntu:24.04` before running. `--build-base` invokes the selected PEX's
`images build --type base --recipe ubuntu-24.04` with its public source revision.
This builds the full OS/toolchain recipe, including the independent Node, Temurin
and Maven contributions, and retains a local `devcapsule-base-e2e:<candidate>-<id>`
image for inspection. `dist/e2e-base-build.json` records its tag, immutable image
ID, builder identity and builder checksum. Runtime tests consume that exact image
ID (Dockerfile builds use the unique local tag and verify its identity first);
the extra base test checks installed tools, symlinks, provenance, agent absence
and the absence of an embedded runtime. This mode runs seven tests.

The build needs dependency-download access. Where Docker bridge DNS is unavailable,
explicitly select `--build-base --build-network host`; the default remains Docker's
normal build network. This option affects construction, not the smoke containers'
network settings.

Omitting `--build-base` runs the six executable-compatibility tests on already
installed bases; that faster mode does not validate a new full base recipe. Pull
`ubuntu:24.04` and the base reference in the checkout's platform lock before
running; the smoke suite requires those images to be available locally. The
runtime test accepts `DEVCAPSULE_E2E_BASE_IMAGE`, and the removed-container test
accepts `DEVCAPSULE_EARLY_EXIT_E2E_IMAGE` for explicit base overrides.

With `DEVCAPSULE_PEX_UNDER_TEST` set, Nox uses that executable without rebuilding
it, reports its source identity and SHA-256, and derives release-version assertions
from it. Explicit expected version/mnemonic values still fail on a mismatch.
The six smoke cases cover component cache reuse, PEX delivery to both fixture IDE
surfaces, supervisor sessions, unexpected container removal, and execution without
host Python or networking. The removal test also copies and verifies the selected
PEX, independent of any runtime inherited from the base. Source contributor
bootstrap and recursive dogfood retain their separate validation paths; they are
excluded from the selected-executable smoke run. Without the selection variable,
`nox -s e2e` retains its local build and contributor-bootstrap behavior.

The GitHub backend owns release construction. Pushing `v0.2.11-rc0` on
`release-0.2.11` runs the source and packaging gates, then publishes
download-verified assets as a prerelease. The workflow runs no Docker: the
clean-machine, component-cache and runtime-session proofs are local acceptance
steps against the downloaded assets.
The assets include `devcapsule.pex`, its SHA-256 checksum, and a release manifest.
Candidates do not require main integration and never become GitHub's Latest.

Final tags such as `v0.2.11` must identify the accepted candidate's source commit
on the matching release branch. The backend checks a reviewed engineering
promotion record on main, including acceptance of the candidate checksum and
main integration or a scoped exception. It rebuilds with the final package
version, checks dependency and Python fingerprints against the candidate, and
reruns the release gates. See [Releasing a new DevCapsule version](../engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md)
for the complete operator checklist and the successful v0.2.11 example.

The tag supplies the package version in a disposable packaging tree; no version
bump is needed in the tagged source. `v0.2.11-rc0` reports package version
`0.2.11rc0`, while `v0.2.11` reports `0.2.11`. Development builds retain the
checked-in baseline and a `-local-linux-x86_64` mnemonic. Existing release assets
are verified and reused on retries; published candidate bytes are never replaced.
Historical v026-era identities remain readable.

The executable contains CPython 3.12.14 from the pinned 20260814 Python Build
Standalone release, the Python CLI, runtime dependencies, and the legacy
PyCharm build/runtime helper assets still needed by the current delegated
`pycharm build` and `pycharm check-runtime` commands. The Python-native
workflow bootstrap assets are packaged separately.
It targets `linux-x86_64`, matching the supported v026 host and Docker base.

Before publishing, prove the artifact on a network-disabled Ubuntu image that
contains no Python interpreter:

```bash
python -m nox -s pex_clean_machine
```

To prove an already-built or downloaded artifact rather than having Nox build
the local candidate first, select it explicitly:

```bash
DEVCAPSULE_PEX_UNDER_TEST="$PWD/dist/devcapsule.pex" \
  python -m nox -s pex_clean_machine
```

Developers who deliberately manage Python tools can instead install the source
checkout in one command with `uv tool install ./devcapsule-src`; this is an
alternative development workflow, not an end-user prerequisite.

The PEX build embeds `/tmp/devcapsule-pex-root` as its default runtime
extraction/cache root so it does not depend on IDE project-state cache
directories being writable. If the launch environment explicitly sets
`PEX_ROOT`, that value still controls PEX before DevCapsule starts; point it
at a writable directory or unset it if PEX warns about an unwritable cache.

## Commands

### Managed local images

List only V1 DevCapsule-managed images from the local Docker image store:

```bash
devcapsule images list
devcapsule images list --include-legacy
```

The default view requires the managed-image metadata labels and does not infer
ownership from a repository or tag prefix. `--include-legacy` also shows older
images carrying the transitional `devcapsule.configuration` label. Listing is
read-only and performs no registry access.

Build the JetBrains-free DevCapsule base:

```bash
# From a source/editable installation, identify the builder PEX for provenance.
devcapsule images build \
  --type base \
  --tag devcapsule-base:debug-v023 \
  --pex dist/devcapsule.pex \
  --source-revision "$(git rev-parse HEAD)" \
  --network host

# When invoked from a PEX, its source identity is used by default.
dist/devcapsule.pex images build \
  --type base \
  --tag devcapsule-base:debug-v023 \
  --source-revision "$(git rev-parse HEAD)"

# WIP: build the NVIDIA CUDA development variant for specialized validation.
dist/devcapsule.pex images build \
  --type base \
  --recipe nvidia-cuda-devel \
  --tag devcapsule-base:cuda-v023 \
  --source-revision "$(git rev-parse HEAD)"
```

`--recipe` accepts `ubuntu-24.04` or `nvidia-cuda-devel`. The default
`ubuntu-24.04` recipe uses `ubuntu:24.04` and installs the established
DevCapsule developer utilities. The WIP `nvidia-cuda-devel` recipe uses
`nvidia/cuda:12.8.1-devel-ubuntu24.04` and installs the same utilities on top
of the CUDA compiler/runtime development baseline. It emits a WIP warning and
remains blocked for V1 release until the specialized NVIDIA host E2E task is
complete.

#### What is in the base, and where to audit it

TL;DR: the default base starts from Ubuntu 24.04 and adds a broad Python and
native-development workstation baseline. It contains Python 3.12 and headers,
Git and OpenSSH, GCC/G++ plus Make/CMake/pkg-config, GDB/LLDB/strace, common
shell/process/filesystem/network diagnostics, Docker CLI/buildx/Compose and
daemon binaries, X11/GTK/audio/font/Mesa runtime libraries, `tini`, `gosu`, and
the `sudo` binary. It also installs the pinned language-tooling baseline:
Node.js `v22.23.1` with bundled npm, Eclipse Temurin JDK `25.0.4+7`, and Apache
Maven `3.9.16`. `JAVA_HOME` is `/opt/java/current`, `MAVEN_HOME` is
`/opt/maven/current`, and the Maven, Java, and Node `bin` directories are on
executable `PATH`. Recipe 7 added no DevCapsule runtime: the launcher supplies
its PEX at `/opt/devcapsule/bin/devcapsule.pex` in each derived environment.
Recipe 8 adds the contained display stack — TigerVNC's `Xvnc`, the core X
fonts, noVNC with `websockify`, and the Openbox window manager — and recipe
9 the tint2 panel; the base is labelled
the base `devcapsule.base.display=contained`, which is how the launcher knows
a capsule can bring its own desktop instead of borrowing the host's X session
(see *Display* below).

The repository-owned Python build plan is the inspectable source of truth:

- [`devcapsule/images/base.py`](devcapsule/images/base.py) defines the curated
  `ubuntu-24.04` and WIP `nvidia-cuda-devel` recipes, root images, managed-image
  labels, and independent tool-installation contributions.
- [`devcapsule/launch/pycharm/_image_build.py`](devcapsule/launch/pycharm/_image_build.py)
  currently owns `BASE_APT_PACKAGES`, the exact Ubuntu package list shared by
  the Python-owned base planner. Despite that transitional module location,
  the base remains JetBrains-free.
- [`devcapsule/images/tooling.py`](devcapsule/images/tooling.py) pins and verifies
  Node.js/npm, Eclipse Temurin, and Apache Maven for each supported architecture.
- [`devcapsule/images/build.py`](devcapsule/images/build.py) shows how those
  components become the generated Dockerfile/build context and are executed
  through Docker buildx.
- [`devcapsule/container_runtime/`](devcapsule/container_runtime/) is the
  generic runtime embedded in the PEX and invoked when a completed environment
  is launched.

The base does **not** contain an IDE or vendor archive, project source,
developer state, credentials, host mounts, host authorization, license/EULA
acceptance, or an ambient AI-agent CLI. Installing Docker and `sudo` binaries
grants no Docker-daemon or sudo access. Materialization adds the
checksum-verified IDE/component; the
developer-owned runtime resolution separately controls project/state mounts,
networking, devices, Docker access, privilege, and secrets.

Claude Code is deliberately not redistributed in the base. A project may lock
an exact upstream Claude Code artifact as a `claude-code` component. After the
developer reviews Anthropic's terms, this checkout-owned command records the
otherwise absent acquisition authorization:

```bash
devcapsule project config authorize claude-code-download true
devcapsule project config resolve
devcapsule images build --type environment --project .
```

Materialization then downloads the locked binary directly from Anthropic,
verifies its SHA-256, installs it at `/opt/claude/bin/claude` only in the local
environment image, adds `/opt/claude/bin` to executable `PATH`, disables
self-updates, and persists sensitive `~/.claude` state separately. The public
base and public DevCapsule PEX contain no Claude Code binary, authentication,
or terms acceptance. Use remains subject to
[Anthropic's Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms).

`--from IMAGE` overrides the selected recipe's root image. The builder reuses
that root image when it is already local and otherwise allows Docker to obtain
the reference.
`--network` accepts `default`, `host`, or `none` and is forwarded to Docker
buildx. Host mode is an explicit build-time isolation relaxation and adds the
BuildKit `network.host` entitlement; it does not configure the network of later
runtime containers.
The resulting image carries the V1 managed marker, metadata version, base kind,
canonical name, recipe name/status/version, builder source identity, and
OCI-standard source/revision labels. Recipe 7 omits the runtime PEX; each
environment receives the launching PEX at materialization, and its checksum
is part of the formation identity. `--source-revision` is an
assertion against the PEX rather than an independent label value, so the image
cannot silently claim a different commit. `images build --type base` is the
sole supported base-build command; there is no compatibility `build-base`
alias.

Public source is the base-build default. A local PEX with dirty or unpublished
source is accepted only with `--allow-local-source`; use that flag at both PEX
packaging and image build, and omit `--source-revision`, for an explicitly
non-public development checkpoint.

Before starting Docker buildx, the default base build performs a live `HEAD`
request against the exact canonical GitHub commit URL embedded in the PEX. A
missing commit or network failure stops the build before an image is created.
This deliberately complements `nox -s build`, which may embed a clean local
commit before it is pushed so that the PEX itself can be tested. Use
`--allow-local-source` to bypass the live check only for an explicitly local
image that will not be published.

Do not use `dist/devcapsule-local.pex` for a public base. If a revision
mismatch reports that the selected PEX embeds `unknown`, rebuild
`dist/devcapsule.pex` with the default `scripts/build-pex.sh`, inspect it with
`dist/devcapsule.pex version --json`, and retry.

### Checkout notifications

What one checkout's DevCapsule environment tells its human, local to that
checkout and never a record. An agent or a tool inside the capsule posts; the
human reads under the web console's bell or with the same commands from the
host. Unanswered decision pages of the console appear in the listing as the
kind `decision`, linking to their page; they are never copied.

```bash
devcapsule project checkout notifications list [--unread] [--json]
devcapsule project checkout notifications post --kind gate --title "Gate failed on main" \
    --summary "Two unit cases; see the log." --link /records/engineering-docs/README.md
devcapsule project checkout notifications read ID
devcapsule project checkout notifications dismiss ID
```

The store is `$XDG_STATE_HOME/devcapsule/notifications/<id>.json` inside the
capsule, which is the checkout's persistent home on the host; from the host
the commands find that home as `project info` reports it, honoring
`DEVCAPSULE_HOME_DIR`. `DEVCAPSULE_NOTIFICATIONS` names another directory
outright. The document format is in `devcapsule/notifications.py`.
Project-wide notifications, a coordinator reaching every collaborator, are a
later source merged into the same listing (owner's note, 2026-10-09).

### Checkout decisions

The web console's decision tools from the runtime CLI, inside a capsule:

```bash
devcapsule project checkout decisions from-table TABLE.md --id ID --title TITLE [--asked-by WHO] [--context MD]
devcapsule project checkout decisions check DECISIONS-DIR/ID.json
devcapsule project checkout decisions hand-off DECISIONS-DIR/ID.json
```

Each runs `python -m devcapsule_webconsole.decisions` with the console the
base installs under `/opt/devcapsule-webconsole`, or the checkout's mounted
console source when the runtime plan names one. `hand-off` prints the
decision as numbered chat text ending with the link into the console, with
the run's token; the link belongs in the chat, never in a record. Outside a
capsule the command says where the module is. The contract is
`DECISIONS.md` in the console's source; the rule for agents is topic 8.8 of
`WORKFLOW.md`.

`decisions --help` shows the wrapper's help without a console.
`decisions SUBCOMMAND --help` shows that tool's help inside a capsule.
With no arguments, the console module reports a missing subcommand and
returns status 2. The wrapper preserves the tool's output and exit status.
`from-table` prints JSON to standard output; redirect it to
`DECISIONS-DIR/ID.json` to save the document.

### Shared component installations

Node, Temurin, and Maven install in separate BuildKit stages when building a
base. IDEs and locally acquired agents likewise contribute separate stages to
environment builds. Each stage exports only its installation paths; final
images use `COPY --link --from` to assemble those paths. Updating a surface,
sibling component, or launcher does not rerun an unchanged component installer.
Maven's installation stage explicitly depends on the JDK it uses for validation.

Reuse is per Docker builder and lasts while its BuildKit cache is retained.
Changed parent images, installation recipes, or component inputs invalidate the
corresponding stage. A fresh host or a pruned cache rebuilds it. Component cache
images are not published; acquisition authorizations and checksum checks still
apply before installation, and credentials/state never enter these stages.

The packaged launcher supplies its own PEX automatically. For source-form
launches, build with `nox -s pex` and either run `dist/devcapsule-local.pex` or
set `DEVCAPSULE_RUNTIME_PEX` to the built artifact's absolute path. Existing
project locks remain valid; the chosen runtime digest changes the local
formation identity without rewriting those locks.

### Declared checkout configuration values

Projects declare ordinary configurable values and their validation metadata in
`.devcapsule/devcapsule.toml`. For example, this repository declares:

```toml
[configuration.values."runtime.memory-limit"]
type = "memory-size"
runtime-effect = "docker.memory-limit"
description = "Hard memory limit applied to the checkout's project container."
```

A declaration may also supply a typed `recommended` value. Resolution uses it
when the checkout has neither an explicit value nor an explicit omission;
`config show` labels it `project-recommended`. `config set NAME default` records
the current recommendation, while `config unset NAME` follows it again. These
ordinary-value defaults never grant host access or authorize downloads.

For DevCapsule development, this repository declares:

```toml
[configuration.values."runtime.devcapsule-command"]
type = "string"
recommended = "devcapsule0"
```

The name `runtime.devcapsule-command` is reserved: DevCapsule applies the
`devcapsule.command-name` runtime effect to it whether or not the declaration
spells `runtime-effect`, and rejects any other effect on that name. This
repository omits the attribute so that released clients before 0.2.14, which
reject every effect they do not know, still read the manifest as an ordinary
string value. An unknown effect is reported with the running version, since
it usually means the project needs a newer DevCapsule.

This names the shipped CLI `devcapsule0` so the development build can own
`devcapsule`. Both names are real commands, not interactive shell aliases.
The two supported values are `devcapsule` and `devcapsule0`; projects without
this declaration use `devcapsule`. Explicit omission also uses the normal name.
The change applies when materializing and launching the next environment;
internal runtime integrations still use the identical PEX at its absolute path.
This value is persistent checkout configuration, not a run-once `--set` effect.

The developer selects a value for one checkout with the generic command:

```bash
devcapsule project config show
devcapsule project config set runtime.memory-limit 8GiB
devcapsule project config resolve
```

`project config show` initializes the selected checkout's workstation-owned
directory, minimal checkout input, and unresolved generated-plan placeholder
when they do not exist, then prints every declared value, component binding,
recommended authorization, and the generated resolution's state. It is a
listing and nothing else: no advice, no commands to run. `project config show`
prints the same listing followed by the configuration review: the pending
decisions with their remedies, the recorded base beside the recommendation,
and whether resolving is needed. A ready review over a fresh resolution says
so and gives no resolve instruction. Every row carries a `SOURCE` column
naming the document its status and value come from: `checkout` for the
checkout input, `manifest` for a project recommendation or declaration,
`lock` for the platform lock's recommendations and component declarations,
`resolution` for the generated plan, `managed` for DevCapsule-owned state
directories, and `environment` for a bound secret. `config show` expands
those tokens in a `Sources:` block with each file's path and whether the
generated resolution still reflects it. It shows
the materialized checkout name and exact files. Repeated calls do not rewrite
existing choices or a resolved plan. If the same portable project identity is
already registered for another checkout, assign a distinct name first with
`project checkout register NAME`; the list command never invents or inherits a
checkout name.

Value statuses distinguish configured, project-recommended, explicitly omitted,
invalid, required-but-missing, and optional-but-unset values. Bindings show an explicit host directory, legacy
adoption, conflict, or managed-default storage. Authorizations show authorized,
stale, required-but-missing, or recommended-but-missing decisions. Resolution
is unresolved, fresh, or stale. Missing choices are reported without making a
valid readiness listing fail.

To review and accept every current authorization recommendation interactively,
use:

```bash
devcapsule project config authorize --all-recommended
```

The command prints each exact value, justification, and recommendation digest
before reading one terminal key. Only a lowercase `y` authorizes the complete
set and writes the checkout once; every other key cancels without writing.
Non-interactive workflows must continue to authorize each exact name and value
separately.

`config set` accepts only keys declared by the project, validates the supplied
value from its metadata, and writes the resulting ordinary value to the
developer-owned checkout input reported by the command. It does not edit the
project declaration or generated resolution. The supported V1 scalar metadata
types are `string`, `integer`, `boolean`, and `memory-size`; runtime effects
are a separate curated catalog rather than arbitrary Docker arguments.

For `docker.memory-limit`, resolution converts the declared memory size to an
exact byte count. `project run` supplies that value to Docker as the
container's hard memory limit. Host access, credentials, networking, devices,
and privilege remain outside ordinary values and require their dedicated
binding or authorization contracts.

Component persistence metadata declares the logical resources that may be
bound to developer-owned storage. The initial provider accepts only an
existing host directory:

```bash
devcapsule project config bind home host-directory:/path/to/home
devcapsule project config bind pycharm/config host-directory:/path/to/config
devcapsule project config bind pycharm/plugins host-directory:/path/to/plugins
devcapsule project config bind pycharm/system host-directory:/path/to/system
devcapsule project config bind pycharm/log host-directory:/path/to/log
devcapsule project config bind pycharm/cache host-directory:/path/to/cache
devcapsule project config bind codex/home host-directory:/path/to/codex-home
devcapsule project config bind codex/openai-api-key \
  host-environment:OPENAI_API_KEY
devcapsule project config resolve
```

The command is generic: it looks up the selected component's persistence
metadata instead of hard-coding these names in its parser. It rejects an
undeclared resource or missing directory, identifies the checkout file it
wrote, and warns that the source becomes a read-write container mount. It also
reports the resource's sensitivity and whether its component contract permits
concurrent use. Resolution revalidates every directory before `project run`
uses the bindings. The initial secret provider records only the declared host
environment-variable name, never its value. Host-file, socket, and
alternative-storage providers are not part of this initial contract.

This repository's dogfood declaration explicitly requests the optional
`codex-agent` capability. Its lock pins Codex as npm publishes it: the
`@openai/codex` meta package, which carries the `codex` launcher, and the
per-platform package the meta package's optional dependencies name for the
lock's platform, both by URL and SHA-256. Local environment materialization
downloads and verifies both tarballs on the host, copies them into
`/opt/codex/<version>` beside a generated `package.json` that names each as a
`file:` dependency, and runs one offline `npm install --ignore-scripts` with
the base's node during the image build, so the image holds the vendor's tested
package tree — the binary beside the bundled helpers it resolves relative to
itself — and `/opt/codex/<version>/node_modules/.bin` joins `PATH`. No agent
is added to the shared base. The component declares a namespaced `codex/home`
state slot mounted at `/home/devcapsule/.codex`, and its Python component
interface derives `CODEX_HOME` from that slot for the IDE process. Projects
that do not select Codex receive none of these contributions.

The capsule is the sandbox. When a checkout's `codex/home` slot is created,
the component seeds `~/.codex/config.toml` with approvals off
(`approval_policy = "never"`), no inner sandbox
(`sandbox_mode = "danger-full-access"`), and `use_legacy_landlock = true` so a
sandboxed mode still works if you switch one on: codex's default bubblewrap
sandbox needs unprivileged user namespaces, which capsule hardening denies. The
seed is written once, as you, only when the file is absent; edit or delete it
freely. Keep any keys you add above the first `[table]` header, because codex
appends tables such as `[tui.model_availability_nux]` to the same file, and a
key placed after a header belongs to that table.

Authenticate naturally from a terminal inside the running capsule:

```bash
codex login
codex login status
```

Claude Code and Antigravity also start with tool approvals disabled in
checkout-managed state. Before either tool's first launch, DevCapsule creates
`$CLAUDE_CONFIG_DIR/settings.json` (normally `~/.claude/settings.json`) with
`permissions.defaultMode = "bypassPermissions"` and
`skipDangerousModePermissionPrompt = true`, and
`~/.gemini/antigravity-cli/settings.json` with
`toolPermission = "always-proceed"`. Authentication and workspace trust still
follow each tool's normal setup.

For existing managed JSON settings, launches add only missing keys and preserve
explicit choices and unrelated fields. Set a different permission mode to opt
out; deleting the key restores the capsule default next launch. Invalid JSON,
incompatible object structure and linked settings are left untouched with a
diagnostic. Externally adopted state is never seeded: add these properties
yourself there if you want the same behavior. Codex retains its absent-file-only
TOML seeding described above.

Codex falls back to file-backed authentication beneath `$CODEX_HOME` when no
container keyring is available, so its login and configuration survive later
launches. The component interface also declares `OPENAI_API_KEY` as an
optional secret input. `project config show` shows that input and warns that
environment delivery exposes it to every process in the capsule and through
Docker inspection while the container runs. DevCapsule never imports it
ambiently: the developer must explicitly bind the declared same-named host
variable as shown above, and launch fails if it is unavailable. Interactive
`codex login` remains the lower-exposure default because its file-backed result
persists in `codex/home`. A resulting `auth.json` is a plaintext credential
and must be protected like a password. OpenAI API-key use is billed under the
developer's OpenAI Platform account and does not grant ChatGPT workspace or
cloud-task entitlements.

Normal `project run` now realizes the lock-selected local environment
automatically after loading a fresh checkout resolution. To prebuild or inspect
that same environment explicitly without launching a container, use:

```bash
devcapsule project --path /path/to/checkout config resolve
devcapsule project --path /path/to/checkout config authorize base-image \
  docker.io/mycodespaceai/devcapsule-base@sha256:695f9eb6dd269dc694b3367f6a2570d500b938998d6f7aa3aa00e5d04cc7394a
devcapsule project --path /path/to/checkout config resolve
devcapsule images build \
  --type environment \
  --project /path/to/checkout \
  --alias devcapsule-local-pycharm:debug-v026
```

The platform lock must select a DevCapsule base plus a
`local-materialization` PyCharm component with an exact version, variant,
download URL, SHA-256, and supported materialization recipe. A locked base
must use an explicit global registry and digest-pinned reference. Local image
IDs, daemon-local aliases, and mutable tags are rejected in committed locks.

The committed recommendation is not authorization. V1 supports four exact,
developer-owned decisions:

```bash
devcapsule project config authorize base-image \
  docker.io/ORGANIZATION/devcapsule-base@sha256:DIGEST
devcapsule project config authorize docker-daemon host-socket
devcapsule project config authorize network host
devcapsule project config authorize development-sudo true
```

A formation lock may pair its immutable base reference with a presentation-only
`base.build-mnemonic`, such as `v026`. Configuration listings, authorization
previews, and missing-authorization errors show that mnemonic beside the full
digest so the developer can recognize the release being reviewed. The
authorization record still binds the exact digest and complete lock; the
mnemonic is never accepted as an artifact identity.

`config authorize NAME VALUE` accepts the lock-selected base, the host
capability nodes every project has (`network`, `docker-daemon`,
`development-sudo`, `host-browser`, `host-x11`) and the vendor acquisitions;
a project's recommendation attaches its justification to a node, it does not
create it. The command writes the exact value and a digest of the relevant
recommendation to this checkout's input file. A changed
base lock or host recommendation is stale and requires deliberate review and
reauthorization; a committed project change never grants access by itself.

`base-image` authorizes one immutable published digest after the developer
reviews its available checksum and scan evidence. It never trusts a mutable
tag, repository, organization, publisher, or future digest. The prompt and
`config show` name the base by its contract, `<family>@<recipe>` such as
`ubuntu-24.04@9`, which the lock records beside the digest; the release that
built the image follows as provenance with a permalink to the recipe at that
tag, and `config show` lists which locked components are validated for the
base and why. Consent binds to the image: a lock that changes around an
unchanged base, a component version bump for instance, keeps the consent,
and only a moved recommendation asks again. Within a family a newer recipe
only adds services, so a component validated on an older recipe runs on a
newer one; a new family is an incompatible change and inherits no validation. `docker-daemon
host-socket` exposes the host Docker control socket, effectively granting the
container control over the host daemon. `network host` shares the host network
namespace instead of the default Docker bridge. `development-sudo true`
authorizes the launcher to let the capsule's development user elevate inside
the container; it is not host-root authorization. The following `config
resolve` incorporates the recorded decisions into the inspectable generated
resolution, and `project run` applies the Docker and network effects.
Development-sudo authorization generates a temporary group-scoped `NOPASSWD`
policy, makes that one file root-owned through a network-disabled,
read-only, `CHOWN`-only helper invocation of the selected local image, and
mounts it read-only under `/etc/sudoers.d/`. The policy and its launcher-owned
temporary directory are removed after exit or launch failure. The enabled
banner is printed only after policy preparation and the complete Docker plan
succeed. Without authorization, normal project launch retains no Docker
socket, bridge networking, no policy or sudo group, a read-only root, dropped
capabilities, and `no-new-privileges`.

For developer-built base testing, `base-image` also accepts an already-local
DevCapsule metadata-v1 base name:

```bash
devcapsule project config authorize base-image devcapsule-local-base:v026
devcapsule project config resolve
devcapsule project run
```

This is a developer-owned override, not a new project recommendation. At
authorization time DevCapsule inspects the local image, validates its managed
base metadata and platform, and records both the supplied name and immutable
Docker image ID; the selection stays valid across lock changes, being bound
to the image. Resolve and run inspect it again;
removing or retagging the name fails instead of pulling or silently running a
different image. Reauthorize after deliberately rebuilding the tag.
`config show` reports this state as `authorized-local`, while
`authorize --all-recommended` deliberately switches back to the lock's
published recommendation. A different published registry digest remains
rejected unless the project lock recommends it.

`--base IMAGE` is an explicit run-once development override and needs no
persisted authorization. It never rewrites the lock or resolution, and the
selected local image must still pass DevCapsule metadata, platform, and
immutable image-ID inspection.

This repository's current Linux dogfood lock uses published digest
`docker.io/mycodespaceai/devcapsule-base@sha256:695f9eb6dd269dc694b3367f6a2570d500b938998d6f7aa3aa00e5d04cc7394a`.
The associated `ubuntu-24.04-v026` tag is only a dogfood discovery tag;
official V1 artifacts will use semantic release versions and committed locks
will continue to use immutable digests.

The immutable v026 image uses agent-neutral base recipe version 5, embeds the
self-contained DevCapsule PEX released from source revision `91d50b1...` at
the canonical `mycodespace-ai/devcapsule` repository, and contains the supported
Python, Node.js, Java, Maven, and PostgreSQL client toolchain. It contains no
ambient agent CLI.

The command obtains the selected base when it is not local, verifies that it
is a managed metadata-v1 base for the locked platform, and downloads the
locked JetBrains archive into `$XDG_CACHE_HOME/devcapsule` (normally
`~/.cache/devcapsule`). Artifact acquisition and formation are protected by
per-identity locks. The archive is checksum-verified and unpacked only into a
temporary build context.

The canonical output name is
`devcapsule-local-pycharm:<formation-identity-prefix>`. Existing canonical
images are reused only after their stored canonical descriptor, full digest,
base identity, recipe, and component metadata all match. A conflicting tag
fails with cleanup guidance instead of being overwritten. `--alias` adds an
extra local debugging tag without changing the formation identity.

Environment images contain the generic PyCharm component template, but no
project source, checkout state, credentials, host authorization, or
checkout-specific runtime plan. This command never launches a container.
The template declares that PyCharm uses the persistent home and home-relative
XDG roots, and owns its exceptional config, plugins, system, log, and cache
slots with their lifecycle and storage semantics. Components that keep state
entirely under standard `HOME`/XDG locations declare no custom slots; shared
runtime planning contains no agent- or IDE-named state field.
`images build --type environment` and `project run` share the same realization
service and strict reuse checks. Normal run obtains the locked base only when it
is missing locally, then reuses or materializes the canonical environment
without requiring a debug alias or a separate image-build command.

For V1 container compatibility, the PyCharm component intentionally sets
`ide.browser.jcef.sandbox.enable=false` before IDE startup. This keeps Markdown
and other JCEF previews working without `SYS_ADMIN`, unconfined seccomp or
AppArmor profiles, privileged mode, or host policy installation. The tradeoff
is explicit: embedded content runs with the IDE user's access to project
source, persistent state, networking, and any separately authorized Docker
socket. Treat the embedded browser as a project preview surface, not as a
general-purpose browser for untrusted sites. Docker's outer isolation policy
is unchanged.

External hyperlinks use a separate, opt-in host integration. Authorize
`host-browser` persistently with `devcapsule project config authorize
host-browser true`, or for one launch with `project run --authorize
host-browser true` to let `xdg-open` inside the capsule ask a
launcher-owned Unix-socket broker to open an absolute HTTP(S) URL in the
physical host's default browser. The protocol does not expose the host
desktop session bus, accept commands or filesystem paths, or invoke a shell.
The socket is mounted read-only and its physical host source is omitted from
ordinary evidence. Any process running as the capsule user can exercise the
enabled bridge, so it is disabled unless the developer makes this explicit
choice.

A recursive launch can propagate an existing authorized broker to its
successor; it cannot create host-browser access from inside a capsule. The
physical-host foreground launcher owns the broker lifetime and removes its
private runtime directory on exit. A nested detached successor therefore
retains working links only while that owning outer launch remains alive.

#### Display

When the materialized image carries the display stack (base recipe 8 and
later), `project run` gives the capsule its **own desktop**: the entrypoint
starts `Xvnc`, Openbox, and a noVNC bridge as supervised infrastructure
children ahead of the IDE, and nothing about the host's X session — no
socket, no credential, no `DISPLAY` — crosses into the container. The
display number is chosen at start (`:10` or the next free one) and the
server listens on its private filesystem socket only, so it neither
collides with nor is visible to the host's X servers even under host
networking. The launcher prints a URL of the form
`http://127.0.0.1:PORT/vnc.html?...token=...` and opens it in your default
browser once the capsule answers. The port is allocated per run on host
loopback only; the token is generated per run, mounted read-only at
`/run/devcapsule-display-token`, and required by the bridge before it will
speak RFB. Closing the browser tab leaves the IDE running; reopening the URL
resumes the session. The session still ends when the IDE exits or on
`docker stop`. A native VNC viewer is not required and not supported as a
separate path; the browser is the client.

**Keys, Escape, and fullscreen.** In a normal tab every key the browser does
not reserve reaches the capsule, Escape included. Do **not** use the
fullscreen button on noVNC's side bar: that is the page-requested kind of
fullscreen, which browsers leave on Escape, so Escape never reaches your
editor. Enter *browser* fullscreen instead, which only F11 leaves: give
keyboard focus to the address bar first (Ctrl+L), press F11, then click back
into the desktop; or use the browser menu's fullscreen entry. noVNC forwards
F11 to the capsule while the desktop has focus, which is why the focus step
is needed, both to enter and to leave. Shortcuts the browser itself owns,
such as Ctrl+W, Ctrl+T, Ctrl+N and Alt+Tab, never reach the capsule in any
mode; closing the tab by accident does not end the session, and the printed
URL reopens it.

**The desktop itself.** Openbox runs DevCapsule's own configuration, not
the distribution default, and a tint2 panel sits at the bottom of the
desktop with a button per window and a clock. A browser-reached desktop
must have nowhere for a window to disappear into and a visible way back
when it does: there is one virtual desktop and the mouse wheel over the
background does not switch desktops; title bars carry no minimize (or
shade) button; the IDE starts maximized and follows the browser window;
any window, including one an application minimized itself or a dialog
behind the IDE, is one click away on the panel, and a middle or right click
on the empty background shows the same list. Alt+Tab cycles windows when
the host lets it through; no other keyboard chord is promised, because
hosts and browsers reserve unpredictable keys.

**Clipboard.** The capsule cannot see your host clipboard, and that is by
design: nothing crosses without your gesture on the noVNC side. Text copied
inside the capsule appears in the clipboard box on noVNC's side bar, from
which you copy it; text going *into* the capsule is pasted into that box and
is then available to the IDE. This is deliberately more work than Ctrl+C and
Ctrl+V, and it is an area where we will pursue improvements: browsers can
hand a page the clipboard exactly during your own Ctrl+V and let it write
the clipboard only when you copy inside a focused tab, which would restore
the familiar keys without the capsule ever gaining standing access. noVNC
does not offer that yet; the planned route is an upstream contribution
rather than a local patch. Native VNC viewers are not a shortcut here: they
share the host clipboard continuously in both directions.

Two limitations are stated rather than worked around: Docker network mode
`none` cannot publish the bridge, so the contained display refuses it and
names the alternatives; and a second `project run` against an already running
capsule cannot recover the first run's URL yet.

Host X11 passthrough — the transport every earlier release used — remains
available only as the `host-x11` authorization: `devcapsule project config
authorize host-x11 true` persistently, or `project run --authorize host-x11
true` once. It is never a default and no project can recommend it. Granting it
binds the host X socket and your trusted cookie into the capsule, which can
then capture keystrokes and windows across your whole session, inject input,
and read the clipboard; the launch says so, and the session-credential
boundary test is recorded as waived for that run. Images built before recipe
8 have no display stack and keep using passthrough with the same statement.

For a formation-based run, DevCapsule generates a version-1 runtime plan from
the same component template used in the image's formation identity. The JSON
contains only in-container project/home/state destinations, the runtime
UID/GID/username, component adapter configuration, names of enabled host
integrations, and the display transport (`contained`, with the in-container
bridge address, port and token path, or `host-x11`) — never host source/state
paths, checkout files, credentials, or authorization secrets, and never the
display token itself. The launcher
writes it to a temporary mode-`0644` file, mounts it read-only at
`/etc/devcapsule/runtime-plan.json`, and removes it with the generated identity
files after exit or launch preparation failure. No command follows the image
name in `docker run`, so Docker retains the canonical image's generic PEX
entrypoint and runtime-plan CMD. Host-level launch validation and the remaining
explicit runtime effects continue in Stage 3 of the active dogfood plan.

### .NET SDK and Rider

For a new .NET project on Linux x86-64:

```bash
devcapsule project init --need dotnet-ide
devcapsule project run
```

`dotnet-ide` selects JetBrains Rider and automatically includes the pinned
.NET SDK. To add the SDK to another IDE, include `dotnet` alongside that
IDE's capability, for example `--need frontend-ide --need dotnet`.
The current catalog pins SDK 10.0.401 and Rider 2026.2.3.1; resolution is
offline and locks exact versions and SHA-256 checksums, never a moving
`latest` installer. Updates require a reviewed catalog pin.

The complete SDK, matching runtime, MSBuild and targeting packs install in
`/opt/dotnet`, on `PATH` with `DOTNET_ROOT` set. The IDE's terminal can run
`dotnet new`, `dotnet build` and `dotnet run`. SDK telemetry is disabled by
default. NuGet packages and user tools use the persistent capsule home;
no host SDK, NuGet configuration or credentials are imported. Additional
workloads and SDK versions are not supplied by this component.

Rider uses its bundled Java runtime and independent `rider/*` IDE state
slots. JetBrains licensing is handled inside Rider; installing the component
does not grant a license or activate a trial. The noVNC startup smoke and
optional licensed editor interaction are described in the
[E2E guide](../engineering-docs/development/e2e-tests.md).

### Capability-first dogfood path

`devcapsule project init` initializes a project completely: it authors (or
honors) the declaration, derives the current-platform lock offline from the
client's embedded resolution matrix, records the owner's checkout answers,
and ends with a fresh resolution, so `init` followed by `run` is the entire
owner first-run:

```bash
devcapsule project --path . init --creator https://github.com/example \
  --need python --need python-ide --need docker-cli
```

Interactively, `init` asks only what no flag, existing record, or derivable
default already answers; every question can be pre-answered with the same
spellings the `config` family uses (`--set NAME VALUE`,
`--bind NAME PROVIDER:VALUE`, `--authorize NAME VALUE [JUSTIFICATION]`).
Repairing a partially initialized project is `init`'s own job, and
`init --regenerate` rewrites the derived platform lock while keeping the
authored manifest. Dogfood image locks written by the retired
`project lock` stub remain fully readable.
Adopt the six existing dogfood state directories once, then generate the local
developer-owned resolution:

```bash
devcapsule project state adopt home --from ~/.config/docker-pycharm-codex/state/home
devcapsule project state adopt pycharm/config --from ~/.config/docker-pycharm-codex/state/config
devcapsule project state adopt pycharm/plugins --from ~/.config/docker-pycharm-codex/plugins
devcapsule project state adopt pycharm/system --from /path/to/project-state/system
devcapsule project state adopt pycharm/log --from /path/to/project-state/log
devcapsule project state adopt pycharm/cache --from /path/to/project-state/home/.cache
devcapsule project config resolve
```

Normal launch then uses the committed manifest and platform lock plus that
checkout-local resolution:

```bash
devcapsule project run \
  --docker-daemon host-socket \
  --development-sudo \
  --host-browser
```

For the DevCapsule repository's own recursive dogfood validation, this same
ordinary `project run` path marks the launched environment as recursive-ready
when host Docker has been accepted. It recognizes the repository by
`devcapsule-src/pyproject.toml` declaring `[project].name = "devcapsule"`. Use
`--no-recursive-e2e` for a one-launch opt-out; it forces host Docker off,
bridge networking, and development sudo off without rewriting configuration.
The flag cannot grant host access. Launch readiness does not execute the
expensive E2E. That test remains an explicit developer action inside the
running environment:

```bash
cd devcapsule-src
python -m nox -s recursive_dogfood_e2e
```

Those two host relaxations are run-once choices and are not granted by the
committed Docker recommendation. They can be recorded manually in the
developer-owned checkout file's `[host]` table for this initial slice. The
PyCharm runtime now uses Docker bridge networking unless an expert path adds a
different explicit Docker choice.

This is intentionally a dogfood bridge, not the complete V1 resolver: `lock`
currently pins a local image tag supplied with `--image`; immutable image
digest resolution and general curated capability selection remain follow-up
work.

Registered checkout records can be listed without scanning source trees:

```bash
devcapsule project list
```

Use `devcapsule project --path /path/to/checkout SUBCOMMAND` when operating
outside a checkout. Otherwise project commands discover the nearest
`.devcapsule/devcapsule.toml` upward from the current directory.

Run PyCharm and other selected IDE surfaces through the configured project:

```bash
python -m devcapsule --help
devcapsule project run
devcapsule project --path /path/to/project run
devcapsule project --path /path/to/project run --print-command > launch.sh
```

For a directory without DevCapsule configuration, start with
`devcapsule project --path /path/to/project init`. Select the required
capabilities and review the developer-owned authorizations before running.

`pycharm run` is retired in 0.2.14. It no longer launches a container or
accepts legacy image/profile options; use the project path above. This is an
intentional release compatibility exception: the sole current user already
uses `project run`, and the old entrypoint bypassed configured host-access
choices. There is no replacement direct-image launch command in this release.
Future capability decisions are tracked in the
[V1 work item](../engineering-docs/work-orders/2026-09-22-legacy-launch-capability-disposition.md).
The earlier `codium_with_claude` and `vscode_with_claude` command trees are
also retired; VSCodium is selected through the `frontend-ide` capability.

PyCharm image utilities remain available:

```bash
devcapsule pycharm build --pycharm /path/to/pycharm.tar.gz
devcapsule pycharm check-runtime
```

### Project Workflow Bootstrap

`bootstrap` (or the explicit `bootstrap project`) is Python-native and uses workflow assets embedded in the
installed distribution or self-contained PEX. It installs reusable
`AGENTS.md` and `WORKFLOW.md` definitions separately from project-owned
`CURRENT-STATUS.md`, `REQUIREMENTS.md`, `index.md`, and engineering-record
state. A missing `workflow-type` in `.devcapsule/devcapsule.toml` means
`single-stream`; `multiple-streams` additionally initializes the reserved
`project-management` registry and handoff.

Existing files are preserved. An older README-centered handoff is copied into
a newly created single-stream `CURRENT-STATUS.md`. To deliberately replace
only the reusable definition files while preserving all project state, run:

```bash
devcapsule bootstrap project --project /path/to/project \
  --refresh-workflow-definition
```

See the repository's
[`project workflow bootstrap specification`](../engineering-docs/specifications/product/project-workflow-bootstrap.md)
for the definition/instance boundary and idempotency contract.

`pycharm build` uses Ubuntu 24.04 and installs Python and pinned Node.js/npm
alongside the supplied PyCharm archive or directory. Customize it with
`--image`, `--base-image`, `--network`, and repeatable `--extra-apt-package`.
This retained image-building utility does not replace project initialization
or the configured environment materialization used by `project run`.

Project launch preserves home and IDE state through declared bindings, including
`home`, `pycharm/config`, `pycharm/plugins`, `pycharm/system`, `pycharm/log`, and
`pycharm/cache`. Use `project config show` to inspect them and
`project config bind NAME host-directory:/path/to/directory` to select an
explicit location, then `project config resolve`. Separate concurrent PyCharm
sessions must use separate IDE configuration directories. Legacy profile and
state-root flags are no longer a public launch interface.

### Persist extra Docker options

Use `project config set-extra-docker-args -- OPTIONS...` to replace the saved
argument list for this checkout. For example, `--gpus all` grants GPU access
when the host has the necessary GPU runtime. `list-extra-docker-args [--json]`
shows the saved tokens with inline environment values masked;
`remove-extra-docker-args` clears the list. The hidden-input `set-env KEY`
convenience edits that same list. See [saved Docker arguments](../docs/configuration/project-versus-personal.md#saved-docker-arguments)
for storage, precedence, mounts and credential handling.

### Inspect the Docker launch command

```bash
devcapsule project --path /path/to/project run --print-command > launch.sh
```

This prepares the currently selected environment through ordinary configuration
and authorization checks, then prints the shell-quoted Docker command, masking
inline environment values from saved or one-off extra options. A redacted
command is a preview; use `project run` to supply the actual saved values.
It may acquire/build the image and prepare state; it does not launch the project
container, open a desktop, check/select component updates or record successful use.
Preparation messages go to stderr, keeping stdout suitable for a file or editor.
Run-once configuration choices and accepted Docker passthrough options still apply.

The output is for inspection and manual editing, **not a standalone replay script**.
Comments identify temporary runtime files removed on return, helper sockets that
require a live service, and environment dependencies. Persistent mounts still point
at real project/IDE state. The developer must provide missing resources before
manual execution and owns any changes to the command. Secret environment bindings
remain variable names; their values are not copied into the output. Do not share
output without reviewing its host paths and any raw arguments you supplied.

The former `project run-image` arbitrary-image convenience command is removed.
For an arbitrary image, use Docker directly; use the print option to inspect what
DevCapsule would execute for a configured project.

Unsupported command shapes such as top-level `devcapsule run`,
`devcapsule run-image`, `devcapsule config`, `devcapsule state`, and
`devcapsule lock`, as well as `devcapsule build pycharm` and
`devcapsule bootstrap-project`, are intentionally not part of the Python CLI.
