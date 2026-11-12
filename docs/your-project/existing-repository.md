---
description: Open an existing repository inside a capsule, whether it already commits .devcapsule/ or needs initialization, and see what crosses the boundary.
role: your-project
aliases:
  - /docs/guides/your-project/
weight: 1
updated: 2026-10-30
---
# An existing repository

Complete [Install DevCapsule](../getting-started/install.md) first, then run
the commands below from your repository's root directory on your host. Only
open repositories whose code you trust to run. The project folder is mounted
read-write inside the capsule. Commit or back up work before experimenting;
the capsule can also change the repository's `.git` directory.

## A repository that already has `.devcapsule/`

When the repository already commits `.devcapsule/devcapsule.toml` and a
platform lock (`.devcapsule/devcapsule.<platform>.lock`), start directly with:

```bash
devcapsule project run
```

`project run` reads the shared manifest and lock and combines them with your
checkout and home settings. At an interactive terminal, it prompts for any
missing required decisions—such as your IDE choice (when the project neither
requires nor recommends one), required environment variables, or base/vendor
channel trust. Project host-access recommendations are shown with their reason
for your decision; they never grant themselves automatically ([Granting and
withdrawing access](../containment/granting-and-withdrawing.md)).

Completing that first review registers this checkout path in your local
configuration home. If you clone or add a second worktree of the same
repository on the same computer, it receives its own checkout record and
isolated state directories without inheriting answers from the first checkout.
To assign a specific checkout record name before first launch (useful before
running pre-launch `project config` mutations on a second checkout), run:

```bash
devcapsule project checkout register my-feature-wt
```

`checkout register` creates a new record name only—it cannot rename an already
registered checkout.

To inspect what a checkout needs before answering anything, run `devcapsule
project config show` or `devcapsule project config check`; neither writes a
record on disk. `config check` exits with status `3` when decisions remain
pending. Without `.devcapsule/devcapsule.toml`, all three commands exit with
status `2` and point you to `devcapsule project init`.

## A repository without `.devcapsule/`

Pick the IDE and runtime capabilities your repository needs and initialize from
its root directory (`--ide` accepts either an IDE capability or a component
name):

| Stack and IDE | Initialize command |
|---|---|
| Python with PyCharm | `devcapsule project init --require python --ide python-ide` |
| JavaScript/TypeScript with VSCodium | `devcapsule project init --require node --ide frontend-ide` |
| Any stack with Visual Studio Code | `devcapsule project init --require node --ide vscode-ide` |
| Java with IntelliJ IDEA | `devcapsule project init --require java --ide java-ide` |
| Java with Eclipse IDE | `devcapsule project init --require java --ide eclipse-ide` |
| .NET with JetBrains Rider | `devcapsule project init --require dotnet --ide dotnet-ide` |

Complete any IDE sign-in or license setup inside the capsule. Add
`--offer browser-automation` when contributors run browser tests with Python Playwright and bundled Chromium (exposed via
`DEVCAPSULE_PLAYWRIGHT_PYTHON` and `PLAYWRIGHT_BROWSERS_PATH`).

Answer the initialization prompts described in [Your first
session](../getting-started/first-session.md#1-make-a-first-workspace), then
launch with `devcapsule project run`.

DevCapsule supplies the base OS, toolchains, IDE, and optional coding agents or
Playwright. Project-specific package installs (`npm ci`, `pip install`, `mvn
test`) and database migrations still follow your repository's README—run them
inside the IDE's terminal in the capsule. To declare version minimums,
environment inputs, and team recommendations, see [What a project
declares](declare-needs.md).

## What goes in Git versus what stays local

Commit `.devcapsule/devcapsule.toml` and `.devcapsule/devcapsule.<platform>.lock`
together to share the project's pinned base and required or offered tools.
Each checkout separately pins its personal IDE and added capabilities. Your host
authorizations, channel trust, private environment variables, agent sign-ins,
and IDE state stay in your local DevCapsule home outside the repository; see
[Project versus personal](../configuration/project-versus-personal.md).

A repository that is not yours to configure is wrapped instead; see
[Someone else's repository](someone-elses-repository.md).

**Next: [choose a coding agent](../working-with-ai/choose-an-agent.md) or
[declare project needs](declare-needs.md).**
