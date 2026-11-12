---
description: Start a new project from an empty directory with your chosen IDE, runtime, and coding agent, and commit .devcapsule/ with the first commit.
weight: 2
updated: 2026-10-30
---
# A new project

Create the directory, initialize Git and DevCapsule with the runtime and IDE
you want, and launch the capsule:

```bash
mkdir -p ~/projects/my-app
cd ~/projects/my-app
git init
devcapsule project init --require node --ide frontend-ide
devcapsule project run
```

Change the values of `--require` and `--ide` to match your stack. Examples
include `--require python --ide python-ide`, `--require java --ide java-ide` (or `eclipse-ide`), or
`--require dotnet --ide dotnet-ide` (and `--ide vscode` or `--ide pycharm`
component names also work).

To include a coding agent on your checkout from the first launch, either accept
the default agent (`antigravity-agent`) during interactive `project init`, pass
`--with codex-agent` or `--with claude-code-agent` on `project init`, or add
one later with `devcapsule project config add codex-agent`; see [Choose an
agent](../working-with-ai/choose-an-agent.md).

Commit `.devcapsule/devcapsule.toml` and `.devcapsule/devcapsule.<platform>.lock`
in your initial Git commit. Anyone who clones the repository later starts with
`devcapsule project run`: the shared lock supplies the exact base and component
versions for the shared capabilities. Personal IDE and added-agent pins live
in each checkout's record. The launcher prompts each developer for their
choices and registers their checkout locally.

To add version minimums, environment variable declarations, recommendations, or
companion services as the project grows, read [What a project
declares](declare-needs.md) and [Services and ports](services-and-ports.md).
