---
description: How a DevCapsule session starts and ends, how the desktop and web console URLs work, and how to reconnect after closing the browser tab.
weight: 1
updated: 2026-10-30
---
# Start, stop, reconnect

A session starts with `devcapsule project run` in your project directory and
ends when the IDE exits. While it runs, a browser tab shows the capsule's
desktop.

## Start

Run `devcapsule project run` from the project directory (or
`~/.local/bin/devcapsule project run` if `~/.local/bin` is not yet on `PATH`):

```bash
devcapsule project run
```

The launcher materializes any missing image layers, starts the container, and
prints per-run URLs on `127.0.0.1`, each carrying a random token generated for
this launch:

- **Contained display**: `http://127.0.0.1:PORT/vnc.html?...` (when the
  session uses the contained desktop rather than host X11 passthrough).
- **Web console**: `http://127.0.0.1:PORT/?token=...` on base recipe 11 or
  newer; see [The web console](web-console.md).

One page opens automatically in your default browser once its listener is
ready—the desktop when the session has a contained desktop, or the web console
otherwise—and the other link stays printed in the terminal. If no browser tab
opens, copy and paste the full URL yourself. Every run selects available loopback
ports and generates new tokens; treat the printed URLs as private keys to the live
session.

## Reconnect

Closing the browser tab leaves the container, the IDE, and every terminal or
agent inside it running. Reopen the printed desktop or console URL in your
browser and you are back where you left off.

Running `devcapsule project run` a second time in the same checkout does not
print or recover a running session's URL, so keep the launcher terminal open or
keep its printed links handy while you work.

## Stop

- **Inside the IDE:** choose **File → Exit** (or **File → Quit**). The capsule
  shuts down cleanly and Docker removes the container.
- **In the launcher terminal:** press **Ctrl+C** once. The launcher forwards
  the interrupt to the capsule's supervisor, waits for the container to stop,
  and prints the session outcome together with the host paths of the session's
  log files. Pressing **Ctrl+C** a second time stops waiting and prints the
  `docker stop` command to run if the container has not exited yet.
- **From another host terminal:** find the container with `docker ps` (named
  `pycharm-isolated-<user>-<timestamp>` by default, or the name you gave
  `devcapsule project run --name NAME`) and run `docker stop CONTAINER_NAME`.
  Inside the capsule, `$DEVCAPSULE_CONTAINER_NAME` and `devcapsule project
  info` also show the running container's name.

For what survives container removal, see [What persists](what-persists.md). To
run two projects at once—or two checkouts of the same repository—see
[Several projects](several-projects.md).
