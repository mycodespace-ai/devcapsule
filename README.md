# DevCapsule

[![Tests](https://github.com/mycodespace-ai/devcapsule/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/mycodespace-ai/devcapsule/actions/workflows/tests.yml)
[![Coverage](https://raw.githubusercontent.com/mycodespace-ai/devcapsule/badges/coverage.svg)](https://github.com/mycodespace-ai/devcapsule/actions/workflows/tests.yml)

<!-- website:social title="DevCapsule: your coding agent, IDE and tools in one container" description="Run your coding agent and desktop IDE in the same Docker workspace. Set a breakpoint in the code your agent just tested, with the same files and tools." -->

<!-- website:hero -->
## Your coding agent, your IDE and your tools in one container

Your project brings its development environment with it. When a test fails,
set a breakpoint in the code your agent just ran. PyCharm,
IntelliJ IDEA, Rider, Eclipse, VS Code or VSCodium opens on the same project
files, with the same compilers and test runners.

The capsule runs on your own computer. It shares the project checkout.
Your host home directory, SSH keys and desktop session stay outside by default.

For a project configured with DevCapsule, clone the repository and run
`devcapsule project run`. On your first launch, review the project's requests
and choose any local settings it needs.

**[Try the fifteen-minute walkthrough](docs/getting-started/first-session.md)**
on Linux x86-64. You can try it without an AI account. On Windows, [read the WSL2 notes first](docs/platforms/windows-wsl2.md).

**The environment your agent tests in is the one you debug in.**

- PyCharm
- IntelliJ IDEA
- Rider
- Eclipse
- VS Code
- VSCodium

<!-- website:demo -->
### Watch a recorded IDE session

[![Eclipse IDE in the Debug perspective inside a DevCapsule container, paused at a breakpoint in HelloTime.java with live Variables and Console output](engineering-docs/blog/assets/2026-10-21-eclipse-debug/eclipse-hello-time-debug-poster.png)](engineering-docs/blog/assets/2026-10-21-eclipse-debug/eclipse-hello-time-debug.webm)

Eclipse inside a capsule, stopped at a breakpoint, recorded as it ran.

Ask your agent to run a scenario from a Markdown file or describe the steps in
plain English. It can record the session so you can replay it step by step in
the capsule's web console. See the [agent recording guide](devcapsule-src/devcapsule/presentation_tools/README.md).

<!-- website:benefits -->
## What you get

- **Let the agent run routine commands.** In a fresh managed setup, Claude Code, Codex and the Antigravity CLI can edit, build and test without asking you to approve each command. [What the capsule can touch](docs/containment/the-boundary.md)
- **Debug what the agent ran.** Set a breakpoint in the failing test, in a full IDE, on the build the agent just made. [Run, debug and test](docs/everyday-development/run-debug-test.md)
- **Choose what the project can reach.** Review requests for host access when you open the checkout. For GitHub pushes, an optional proxy can use your host credentials while your SSH key stays on your computer. [Granting and withdrawing access](docs/containment/granting-and-withdrawing.md)
- **Keep your setup between sessions.** Your project files, IDE settings and plugins, and tools installed under `~/xtras` survive a container rebuild. [What persists](docs/sessions/what-persists.md)

<!-- website:continuity -->
## Pick up where the last session stopped

When a developer or coding agent pauses work in DevCapsule, the handoff lives in a versioned status file in the repository rather than inside a chat window. Here is a real handoff excerpt from building DevCapsule (`0.3.0` release verification on `maintenance`):

- **What changed:** Repaired the automated GUI smoke harness and verified persistent workspace state across `devcapsule stop` and `devcapsule start` for IntelliJ IDEA, PyCharm, Eclipse, Rider, and VSCodium.
- **What was checked:** Full test suite (`557 passed`), documentation contract check (`docs-contract`), and recorded two-session persistence runs with saved screenshots and WebM videos.
- **What remains uncertain:** Cold first-import Maven indexing time on larger multi-module Java projects under constrained container CPU quotas.
- **Next action:** Publish the landing-page demonstration update and verify the rendered site across desktop and mobile viewports.

At the start of the next session, the incoming agent or developer reads [`CURRENT-STATUS.md`](CURRENT-STATUS.md) and the active workstream record before touching code—resuming with the same verified state, open questions, and next step ([read the workflow](WORKFLOW.md) · [browse the engineering journal](engineering-docs/blog/2026-09-30-what-i-have-been-up-to-lately.md)).

<!-- website:fit -->
## Is it for you?

### Good fit today

- You work on Linux x86-64, or on Windows through WSL2, with Docker and Git
  installed.
- You use a JetBrains IDE, Eclipse or VS Code, and want to use the debugger
  on code your agent has changed.
- You run agents on real projects and want to leave them alone without
  handing them your home directory.
- You like knowing exactly what a tool can touch, and you would rather read
  a bug record than guess.

### Not a fit, or not yet

- You only need a shell for your agent. Its built-in sandbox may already
  cover your needs.
- Your isolation requirements call for a separate virtual machine. DevCapsule
  uses Docker containers.
- On Apple Silicon, the [macOS launcher](docs/platforms/macos.md) is an
  experimental source build for Docker Desktop.
- A polished experience: this is pre-V1. Expect edges, and expect every edge
  to have a file.

<!-- website:dogfood -->
DevCapsule is built inside DevCapsule, by one person and several agents, and
the journal is the record of it. **We DO eat our own dog food.**

<!-- website:why -->
## Why DevCapsule?

Before leaving an agent to work, you want to know what it can reach. When
you come back, you want to inspect what it did. DevCapsule lets you do both
in one workspace.

### 1. You choose what the agent can reach

The agent can write to your project checkout and the capsule's own persistent
directories. Your host home, SSH keys and browser profiles stay outside by
default. You can use Git to review changes to tracked files.

A project can request additional access such as host networking, the Docker
socket or development `sudo`. You review those requests for your own checkout
and can withdraw a grant later.

### 2. You check the work with real tools

Open the failing test in the capsule IDE, rerun it with the debugger and
inspect the variables at the breakpoint. The IDE uses the same files,
compilers and runtimes as the agent.

The IDE, its plugins and its language servers run inside the capsule too.
They use the same mounts and access grants as the agent.

### 3. The work is still there next time

The capsule keeps IDE settings and plugins in persistent directories.
Tools you install under `~/xtras` survive too. Packages added to the container filesystem disappear when it is removed.
The project keeps a different kind of history. Its status, decisions and next
step are written to files in the repository, where you or another agent can
pick up the work.

### 4. The setup page becomes a file

Many projects, open-source ones especially, carry a long document on how to
set up a development environment: which JDK, which Python, which IDE
plugins, which order. It goes stale, and every newcomer pays for it again.

A DevCapsule project commits its requirements in `.devcapsule/devcapsule.toml`
and pins the environment in a platform lock. A new contributor can clone the
project and run `devcapsule project run`, then review the checkout's settings
and choose an IDE when the project leaves that choice open. For an upstream
project without a manifest, `devcapsule project wrap` keeps the configuration
in a repository of your own.

<!-- website:comparison -->
### But is it really needed?

There are good alternatives, and for some people one of them is the better
choice.

- **An agent's built-in sandbox** can be enough if you want to restrict shell commands while keeping your current editor and toolchain.
- **Docker Sandboxes** runs local agents in microVMs. Editors such as VS Code and Cursor can connect over SSH. [Docker editor integrations](https://docs.docker.com/ai/sandboxes/integrations/)
- **JetBrains Air** lets you delegate tasks from an IntelliJ-based IDE using a local session, a temporary worktree or the cloud. The standalone Air app also offers a Docker mode. [JetBrains' guide to Air environments](https://support.jetbrains.com/hc/en-us/articles/40066588393746-How-to-run-an-agent-in-Docker-on-Air-plugin)

Choose DevCapsule when you want the desktop IDE itself, its debugger and the
agent to run together inside Docker. DevCapsule is open source and needs no
DevCapsule account. [See the detailed comparison](engineering-docs/design-notes/devcapsule/competitive-comparison.md).

<!-- website:contribute -->
## Contribute

Every open bug is a file under [engineering-docs/bugs](engineering-docs/bugs/)
with its evidence, and every workstream a status file that says what is next.
Pick a bug, work it with an agent inside DevCapsule, and send it back as a
pull request; the [developer brief](DEVELOPING.md) and the
[workflow](WORKFLOW.md) tell you what to read first. A one-page front door for
first contributions is coming; until then, an issue saying what you tried is
the right first message.

<!-- website:end -->

---

[Documentation](docs/README.md) · [For developers](DEVELOPING.md) · [Apache-2.0 license](LICENSE)
