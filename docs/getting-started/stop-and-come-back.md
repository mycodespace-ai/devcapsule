---
description: How a capsule session ends, why closing the browser tab leaves it running, and what survives when you start the next session.
weight: 3
updated: 2026-10-30
---
# Stop and come back

A running session involves three pieces: the IDE inside the container, the host
terminal running `devcapsule project run`, and the browser tab displaying the
capsule's desktop. Exit the IDE or interrupt the launcher to end the session.

## Ending a session

Choose **File → Exit** inside the IDE for a clean shutdown. The IDE exits,
Docker removes the disposable container, and your host terminal returns to its
shell prompt. Your saved project files and persistent checkout directories
remain on your computer.

Pressing `Ctrl+C` in the launcher terminal also stops the capsule after a brief
shutdown grace period, printing `Session interrupted from the terminal
(Ctrl+C); the capsule stopped.` along with the host paths to that session's log
files. Pressing `Ctrl+C` a second time stops waiting. If the launcher cannot
confirm that the container stopped, it prints a `docker stop` command.
Prefer exiting from the IDE during normal work so the editor flushes unsaved workspace state
cleanly.

## Closing the browser tab

Closing the desktop tab (or the [web console](../sessions/web-console.md) tab)
leaves the capsule running. Reopen the URL printed in your launcher terminal to
reconnect to the exact same desktop with every window and terminal still live.

Every `project run` generates fresh loopback ports and tokens. Running a second
`devcapsule project run` cannot recover the URL of an already-running session,
so keep your launcher terminal open while the session runs.

## Coming back later

From the project directory in any host terminal:

```bash
~/.local/bin/devcapsule project run
```

The IDE reopens with your source tree, personal IDE preferences, installed
plugins or extensions, window layout, and coding-agent sign-ins intact.
Processes that were running inside the previous container—such as dev servers
or file watchers—stopped when that container exited, so start them again in the
IDE terminal when needed.

You do not run `project init` again. Unanswered or newly required decisions
can produce prompts, including software consent after an update or a forgotten
checkout answer. See [Changes at the next
launch](../configuration/project-versus-personal.md#when-the-project-changes)
and [What persists](../sessions/what-persists.md).
