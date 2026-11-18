---
description: "Where your editor, debugger and agent run when you use a built-in sandbox, Docker Sandboxes, JetBrains Air or DevCapsule."
---
# Choosing an agent environment, November 2026

There are good alternatives, and for some people one of them is the better
choice.

- **An agent's built-in sandbox** can be enough if you want to restrict shell commands while keeping your current editor and toolchain.
- **Docker Sandboxes** runs local agents in microVMs. Editors such as VS Code and Cursor can connect over SSH. [Docker editor integrations](https://docs.docker.com/ai/sandboxes/integrations/)
- **JetBrains Air** lets you delegate tasks from an IntelliJ-based IDE using a local session, a temporary worktree or the cloud. The standalone Air app also offers a Docker mode. [JetBrains' guide to Air environments](https://support.jetbrains.com/hc/en-us/articles/40066588393746-How-to-run-an-agent-in-Docker-on-Air-plugin)

Choose DevCapsule when you want the desktop IDE itself, its debugger and the
agent to run together inside Docker. DevCapsule is open source and needs no
DevCapsule account.
