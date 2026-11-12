---
description: Where every component of a session writes its log, how to capture a diagnostic snapshot or sanitized export bundle, how to collect browser evidence, and what to include when asking for help.
weight: 2
updated: 2026-10-31
---
# Diagnostics and logs

Every launch gets its own log directory on your computer, and every critical
component of the session writes one file there named after itself. Nothing
depends on a flag you had to set before the problem happened: the files are
created by default, and they survive closing the browser tab, pressing Ctrl+C
in the launcher, exiting the IDE, and removing the container.

If the session directory cannot be created, or an external Docker daemon
cannot see its backing mount, the launcher reports that and continues with
terminal output only.

## Where the logs are

At every start, the launcher prints the directory on the `Session logs:` line
of the storage summary. Inside the capsule, the same directory is mounted at
`/var/log/devcapsule`, and `DEVCAPSULE_LOG_DIR` points to it so tools and
agents in the capsule can find it directly.

Components do not write their stream noise to your launcher terminal. The
terminal prints the launcher's own status lines, the desktop and web console
links, supervisor warnings when a component dies or shutdown runs out of time,
and at exit one summary line (`Session ended`, `Session failed`, or `Session
interrupted`) followed by the host path of every log file from that session.
Routine IDE and display-stack output—including harmless `ERROR` lines from GUI
toolkits—stays in the log files.

On your computer, session logs live in DevCapsule state storage, grouped by
checkout, with one directory per session:

```text
$XDG_STATE_HOME/devcapsule/projects/by-path/<checkout id>/logs/<session id>/
```

`$XDG_STATE_HOME` defaults to `~/.local/state`. When `DEVCAPSULE_CONFIG_HOME`
is set (see [The configuration home](../configuration/home.md)), state storage
lives under `$DEVCAPSULE_CONFIG_HOME/state/projects/by-path/<checkout id>/logs/<session id>/`
instead. Each `<session id>` combines the UTC start time and a short random
suffix (such as `20261011-041533-3f9a`), so directories sort chronologically.
`devcapsule project info` prints the exact `logs` directory for your checkout.

## What is in a session directory

| File | Written by | What it holds |
|---|---|---|
| `session.json` | the launcher | The session id, start time, launcher version and source revision, image, container name, network mode, published display and console ports, IDE log paths, project path and mount, the IDE |
| `snapshot-<utc>.json` | `devcapsule project diagnose` | Bounded health snapshot: container state, cgroup v2 counters, process states, protocol probe verdicts, and log inventory (mode `0600`) |
| `devcapsule-launcher.log` | the launcher, on your computer | The session's start and end, the `docker run` command, warnings |
| `devcapsule-supervisor.log` | the capsule's process supervisor | Every child's start, readiness, exit and signal, with the exit code or signal name; warnings |
| `devcapsule-xvnc.log` | Xvnc, the capsule's X server | Errors and connection events: a viewer accepted or closed |
| `devcapsule-window-manager.log`, `devcapsule-panel.log` | openbox, tint2 | Their standard output and error, as they print it |
| `devcapsule-novnc.log` | websockify, the browser bridge | Connections opened and closed, handshake failures |
| `devcapsule-console.log` | the web console | Warnings and errors of the console and its server |
| `devcapsule-<ide>.log`, for example `devcapsule-pycharm.log` | the IDE's standard output and error | What the IDE prints when it starts and fails; its own log stays in its log directory, see below |
| `devcapsule-job.log` | a headless job | The job's output |

Each child's file carries a UTC timestamp in front of every line. If a file
cannot be opened or a write fails, the supervisor reports that once and
copies the remaining output to the terminal so nothing is lost. The
launcher's and the supervisor's own records carry the level and the process
id as well.

The IDE keeps its own structured log in its persistent log directory:
`idea.log` for PyCharm, IntelliJ IDEA, and Rider (under the IDE `log` slot, such as
`pycharm/log`, listed by `devcapsule project info --json`), the `logs/` directory
inside VSCodium's or Visual Studio Code's `user-data` slot, and `.metadata/.log` inside the
Eclipse `workspace` slot. Those native IDE logs stay in place; the session
directory captures the IDE process's standard output and error streams.

## Levels and the verbosity override

By default, components log at `WARNING` plus session lifecycle events (starts,
readiness, signals, and exits), which are always recorded so you can
reconstruct an incident. `Xvnc` runs at its status level, recording errors as
well as connection and server state changes.

To capture full diagnostic detail for one launch, set `DEVCAPSULE_LOG_LEVEL`
in the shell that runs the launcher. It accepts `DEBUG`, `INFO`, `WARNING`,
and `ERROR`, and applies across the launcher, supervisor, web console, and
`Xvnc`:

```bash
DEVCAPSULE_LOG_LEVEL=DEBUG devcapsule project run
```

Unrecognized values print a single warning and fall back to `WARNING`.

## How much disk this takes

Every writer rotates its own file, in the process that writes it, the moment
a write would carry the file past its segment. The live file never exceeds
the segment; the one exception is a single write longer than the segment,
which goes into a fresh file on its own. Python logs write whole formatted
records, including tracebacks. Copied child output is read in bounded chunks,
so a line split across reads can span segments; a segment can start without
a timestamp when it continues a line from the preceding segment.

- Each file rotates at its segment, 8 MiB by default. The live file becomes
  `devcapsule-novnc.log.1.gz`, the older segments shift to `.2.gz` and on,
  and the fifth is removed: four compressed segments per file, at most.
- The launcher's log on your computer and the supervisor's in the capsule
  rotate the same way, each by its own process.
- There is no rotation daemon, no polling and no window in which output
  lands in a rotated file.
- Compression runs on the writer. While a child's copied log is compressed,
  its output pipe is not drained; if the pipe fills, the child waits until
  copying resumes. Slow storage can prolong that wait.
- Rotation is not atomic as a whole. A crash can leave a temporary `.gz.tmp`
  file, partly shifted archives, or the latest output in both the live file
  and `.1.gz`. The live path briefly disappears between removal and reopening;
  a reader following an open file must reopen the path to see new output.

One knob sets the checkout's retention target: `DEVCAPSULE_LOG_BUDGET` on the
launcher's shell, `256M` by default. It accepts a number with `K`, `M` or
`G`, with a minimum of `16M`. An invalid or smaller value prints a warning
and uses `256M`, so a logging option cannot prevent a launch.

```bash
DEVCAPSULE_LOG_BUDGET=1G devcapsule project run
```

- The segment size follows the budget: one thirty-second of it, between
  1 MiB and 10 MiB. Each component normally keeps one live segment and four
  compressed segments. Oversize writes, temporary compression space and gzip
  overhead mean this is not a hard bound on disk use.
- At each launch, the oldest ended sessions are removed until the checkout's
  logs directory fits the budget or no eligible session can be removed,
  and the launcher's log names what was removed. The session being launched
  is never removed. Other sessions without a recorded end are protected for
  seven days from their start, then count as abandoned even if still running.
  Missing or unreadable manifests use the same age rule. The directory may
  exceed the target between launches, while sessions are protected, or when
  cleanup fails.
- `session.json` records when the session ended and with which exit code.

## Diagnostic snapshots and export

Run `devcapsule project diagnose` from your project directory (or pass
`--path <dir>`) while a session is misbehaving or after it has ended:

```bash
devcapsule project diagnose
devcapsule project diagnose --session 20261011-041533-3f9a --json
```

On the host, omitting `--session` selects the newest running session, or the
latest session directory when none is running. Inside a capsule, only its
current session is mounted; inspect other sessions from the host. With a
writable session directory, each run writes a private (`0600`)
`snapshot-<utc>.json` file there and prints a short verdict.

For a running container, the command runs bounded checks (`docker inspect` up
to 3 seconds, in-capsule probe up to 5 seconds, and 2 seconds per protocol
probe) so a wedged display stack never stalls diagnosis or shutdown:

- **Process and cgroup state:** reads `/proc` (including stopped `T`
  processes, `Z` zombies, and `websockify` worker children) and cgroup v2
  counters (`memory.current`, `memory.max`, `memory.events` `oom` and
  `oom_kill`, CPU throttling, and `pids.current` / `pids.max`).
- **RFB Unix socket greeting:** connects to `rfb.sock` and waits for `Xvnc`'s
  12-byte `RFB 003.008` greeting. A socket that accepts the connection without
  sending a greeting is reported as unhealthy, separating a hung or stopped
  `Xvnc` from a healthy server.
- **Display HTTP and WebSocket-to-RFB bridge:** checks `GET /vnc.html` and
  performs an authenticated WebSocket upgrade on `/websockify` (reading the
  capsule's display token in memory only) until WebSocket data
  delivers `Xvnc`'s RFB greeting. An HTTP `200` on `/vnc.html` alone does not
  count as a healthy desktop bridge.
- **Host loopback vs. capsule network:** probes the published `127.0.0.1`
  display and web console ports on the host alongside the in-capsule listeners
  to distinguish host port-forwarding problems from container failures.

Diagnostic requests send `User-Agent: devcapsule-diagnose/<version>` and
`X-DevCapsule-Diagnostic: 1` so probe connections in `devcapsule-novnc.log`
and `devcapsule-xvnc.log` are distinct from browser traffic. After a session
ends and `docker run --rm` removes the container, `project diagnose` degrades
cleanly: it reports that the container is no longer present and summarizes
`session.json`, the exit code, and the persisted session logs.

To package a single archive you can attach to a bug report, add `--export`:

```bash
devcapsule project diagnose --export
devcapsule project diagnose --export ./my-session.tar.gz --include-ide-logs
```

- `--export` writes `devcapsule-diagnostics-<session>-<utc>.tar.gz` (or the
  path you give) atomically with file permissions `0600`.
- Known credentials are redacted across `snapshot.json`, `session.json`, plain
  `.log` files, and compressed `.log.<n>.gz` segments: `?token=` query values,
  URL-encoded tokens, `devcapsule-console-token` and port-scoped
  `devcapsule-console-token-<port>` cookies, `Authorization`,
  `Cookie`, and `X-DevCapsule-Token` headers, secret command flags, and saved
  inline Docker environment values.
- IDE-native logs (`idea.log`, VSCodium and Visual Studio Code `logs/`,
  Eclipse `.metadata/.log`) are **excluded by default** because they often
  contain project paths and source excerpts. `snapshot.json` records their
  locations, file counts, and byte sizes; pass `--include-ide-logs` with
  `--export` when IDE startup or UI freezes are part of the problem. Discovery
  visits at most 4,096 entries per IDE log location and reports when it reaches
  that limit. Reads refuse symlinks in the file path, including parent
  directories.
- Redaction covers known token and credential formats only. Arbitrary child
  output and IDE logs can still contain secrets or proprietary code; inspect
  the archive before sharing it outside your machine.

## Browser evidence

Host and capsule exports do **not** collect browser logs automatically:
`snapshot.json` records `"browser_evidence": {"collected": false, "mode":
"manual-devtools"}`. The launcher cannot read browser tab memory, client-only
JavaScript exceptions, or WebSocket close codes when the browser cannot reach
`websockify`.

When a browser tab disconnects, shows a blank canvas, or fails to reconnect,
capture browser-side evidence manually (these steps remain usable even when the
capsule bridge is unreachable):

1. **Optional client debug logging:** if the problem is reproducible, append
   `&logging=debug` (or `?logging=debug` when there is no query string) to the
   desktop URL so noVNC writes detailed state transitions to the browser
   console.
2. **Console log:** open browser Developer Tools (`F12` or `Ctrl+Shift+I`),
   switch to the **Console** tab, right-click inside the message list, and
   choose **Save as...** to save the log text.
3. **WebSocket close code and status:** switch to the **Network** tab, filter
   by **WS**, click the `/websockify` request, and record the HTTP status code
   plus the WebSocket **Close** code and reason (for example `1006` abnormal
   closure or `1008` policy violation) shown under **Messages** or **Headers**.
4. **Sanitize before sharing:** remove any `?token=<hex>` query parameter and
   any `Cookie` or `Set-Cookie` headers from copied URLs, console text, or HAR
   exports. Browser HAR files include full request URLs and cookies by default.

## When asking for help

Run `devcapsule project diagnose --export` (add `--include-ide-logs` when the
IDE itself failed to start or froze) and attach:

1. The generated `devcapsule-diagnostics-<session>-<utc>.tar.gz` bundle, or
   from the session directory: `session.json`, the latest `snapshot-<utc>.json`,
   `devcapsule-launcher.log`, `devcapsule-supervisor.log`, and the log of the
   component that misbehaved.
2. When the desktop tab disconnected or failed in the browser, the saved
   browser DevTools Console output and `/websockify` WebSocket close code from
   [Browser evidence](#browser-evidence).
3. What you did, in order, and what you expected to see.

The web console's request access log is disabled, so raising verbosity does
not record run tokens from request URLs, and `--export` redacts known run
tokens and configured environment secrets. Child output, custom Docker
arguments and the IDE's own log can still contain credentials or project
content; review the files before sharing them.
