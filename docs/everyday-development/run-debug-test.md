---
description: Running, debugging and testing a realistic application from the IDE inside the capsule.
weight: 3
updated: 2026-10-30
---
# Run, debug, test

Inside a capsule, your editor, build tool, test runner, and interactive
debugger all execute inside the same Linux container against `/workspace/<slug>`.
You do not configure remote SSH interpreters or Docker run targets inside the
IDE: to the IDE, the capsule **is** the local machine.

## Running and debugging by stack

Start with the IDE's normal Run or Debug configuration. The capsule drops
Linux capabilities and enables `no-new-privileges` by default. Debugger
requirements depend on the language, extension, and whether you start a
program or attach to an existing process.

- **Python in PyCharm (`python-ide`):** Create or reuse a project virtual
  environment in the IDE terminal (`python3 -m venv .venv`). Install the
  dependencies specified by your project, then select `.venv/bin/python` in
  PyCharm (**Settings → Project → Python Interpreter**), and click **Run** or
  **Debug** in the editor gutter on any module or `pytest` test.
- **Node.js and TypeScript in VSCodium or VS Code (`frontend-ide`,
  `vscode-ide`):** Run `npm install` in the integrated terminal, open **Run and
  Debug** (`Ctrl+Shift+D`), and choose **JavaScript Debug Terminal** or launch
  an `npm` script directly with breakpoints set in your `.ts`/`.js` files. For
  Python, Java, or C# in VSCodium/VS Code, install the language extension once;
  it persists in your checkout's `extensions` slot.
- **Java and Maven in IntelliJ IDEA (`java-ide`) or Eclipse (`eclipse-ide`):**
  Temurin Java (`JAVA_HOME`) and Maven (`MAVEN_HOME`) are on `PATH` from the
  base image. Open `pom.xml` as a project in IntelliJ—or import `/workspace/<slug>`
  in Eclipse via **File → Import → Maven → Existing Maven Projects**—set
  breakpoints, and debug JUnit tests or `main` classes directly. Dependency
  downloads under `/home/devcapsule/.m2` persist across sessions.
- **`.NET` in JetBrains Rider (`dotnet-ide`):** Open your `.sln` or `.csproj`,
  build with `dotnet build`, and use Rider's application or test Debug
  configuration. Use `dotnet test` or `dotnet run` for terminal runs.
  NuGet packages under `/home/devcapsule/.nuget` persist per
  checkout.

The IDE terminal and coding agents use the same installed tools. The base
also includes PostgreSQL client commands such as `psql`; select
`postgresql-client` when declaring that project requirement.

## Browser and end-to-end tests

When your test suite drives a browser, run one of these commands on the host:

```bash
# Shared in the project manifest:
devcapsule project config offer browser-automation --because "Playwright E2E tests"
# Or added only on your checkout:
devcapsule project config add browser-automation
```

An offered capability is included unless you omitted it. Use `config restore
browser-automation` to restore an omitted offer; `config add` is for a
capability the project does not declare.

On the next launch, DevCapsule installs Python Playwright and pinned Chromium.
Inside the capsule, `$DEVCAPSULE_PLAYWRIGHT_PYTHON` names its Python interpreter.
`$PLAYWRIGHT_BROWSERS_PATH` names the browser directory, and
`$DEVCAPSULE_PLAYWRIGHT_WHEELS` names the bundled Python wheels.
Your project's separate virtual environment still needs its test dependencies.
For a browser window on the capsule desktop, launch Playwright with
`headless=False`. It can reach capsule servers on `127.0.0.1` without a
published port ([Previews and ports](previews-and-ports.md)).

If your integration tests start companion containers through `docker compose`,
declare `docker-cli` and authorize `docker-daemon
host-socket` on your checkout; see [Services and
ports](../your-project/services-and-ports.md) for host-bridge networking
caveats.

## Native debuggers (`gdb`, `lldb`) and resource limits

- **Native C/C++/Rust binaries:** `gcc`, `g++`, `cmake`, `gdb`, `lldb`, and
  `strace` are preinstalled in the base image. Starting a program as a child of
  the debugger (`gdb ./build/my-app`) avoids some attach restrictions.
  Attaching to another process can require `SYS_PTRACE`; the launcher accepts
  `devcapsule project run -- --cap-add=SYS_PTRACE` from your host terminal.
  Host kernel policy and Docker security settings still determine whether
  debugging is permitted.
- **Memory or CPU limits:** Exit status 137 can indicate a `SIGKILL`; it does not
  prove an out-of-memory kill. Check logs and resource use before changing limits.
  Increase memory for memory pressure and CPUs for CPU-bound work. For one
  launch, use `devcapsule project run --memory 8G --cpus 4`. Save limits with
  `devcapsule project config set memory 8G` and `devcapsule project config set
  cpus 4` on the host; see [Resource
  limits](../configuration/resource-limits.md).
