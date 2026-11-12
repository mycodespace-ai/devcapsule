---
description: What the DevCapsule documentation covers, the three places to start, and how to find the version you run.
role: overview
weight: 0
updated: 2026-10-30
---
# Use DevCapsule

DevCapsule runs a desktop IDE and coding agents inside a capsule: a container
that mounts your project folder, keeps its own per-checkout persistent state,
and leaves your host home directory and desktop unmounted by default.
The capsule has outbound network access; [The boundary](containment/the-boundary.md)
explains its limits and the access you can grant.
These pages describe {{tag}}; use the version switcher to inspect another release.

## Start in one of three places

| You want to | Read |
|---|---|
| See it work in fifteen minutes, with no AI account | [Your first session](getting-started/first-session.md) |
| Open a repository you already have | [An existing repository](your-project/existing-repository.md) |
| Run a coding agent at full speed inside a clear boundary | [Choose an agent](working-with-ai/choose-an-agent.md) |

## Everything else, by the question you have

| Question | Section |
|---|---|
| How quickly can I install and try it? | [Getting started](getting-started/install.md): install, first session, stop and come back |
| How do I bring or create a project? | [Your project](your-project/existing-repository.md): existing repositories, new projects, manifest declarations, services and ports |
| How do I work effectively with coding agents? | [Working with AI](working-with-ai/choose-an-agent.md): choosing agents, sign-in, instructions, models, reviewing agent work |
| Can I do my normal day-to-day coding? | [Everyday development](everyday-development/clipboard-and-browser.md): clipboard and browser, IDEs and terminals, Git, run/debug/test, previews and ports |
| How do I configure the project, checkout, and home? | [Configuration](configuration/index.md): project versus personal, configuration home, inspection, IDE preferences, resource limits, local base, vendor trust, capabilities |
| What can the capsule and its agents reach? | [Containment](containment/the-boundary.md): the default boundary, granting and withdrawing access |
| How do sessions, persistence, and parallel checkouts work? | [Sessions](sessions/start-stop-reconnect.md): start/stop/reconnect, web console, what persists, several projects, moving machines |
| How do people and agents share one repository? | [Collaboration](collaboration/working-in-workstreams.md): working in workstreams |
| How do launcher and component updates work? | [Updates](updates/supported-versions.md): supported versions, launcher updates, component upgrades, component freshness |
| What if something fails or I want to clean up? | [Troubleshooting](troubleshooting/first-session.md): first-session checks, diagnostics and logs, cleanup and uninstall |
| Does it run on my operating system? | [Platforms](platforms/linux.md): Linux, Windows via WSL2, macOS |
| What are the exact commands, nodes, and JSON fields? | [Reference](reference/cli.md): CLI reference, configuration nodes, `project info` |

## Developing DevCapsule

To contribute to DevCapsule itself, read [For developers](../DEVELOPING.md) and
the [repository documentation index](../index.md).
