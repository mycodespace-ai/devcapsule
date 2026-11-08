---
description: "The web console: inspect your running capsule, answer agent decisions, read records, browse project files, and queue configuration changes for the next launch."
weight: 5
updated: 2026-11-08
---
# The web console

Base recipe 11 and newer include a local web console inside the capsule. On an
older base image, `devcapsule project run` prints a short notice in place of
the console link—with the `devcapsule images build` command to build a newer
base and a pointer to
[building and selecting a local base](../configuration/local-base.md)—and runs
the capsule normally without the console.

On a base that carries the console, `devcapsule project run` prints its
per-run link alongside the desktop link:

```text
Web console: http://127.0.0.1:41273/?token=…
  (the capsule as a page; the link works for this run only)
```

When the session uses the contained desktop, the desktop opens automatically in
your browser and the console link stays printed in the terminal for you to open
whenever you want it. When the session has no contained desktop (for example,
under host X11 passthrough), the console opens automatically instead.

## What is on each page

Opening the link shows the capsule's identity at **Home**, with navigation to
eight pages:

- **Configuration**: the launch-time listing from `devcapsule project config
  show`, forms to send `config` changes to the launcher for the **next**
  launch, and a live table of requests sent during this run and what the
  launcher did with each.
- **Versions**: what `devcapsule project versions show` reports—the version set
  running in this capsule and the one selected for the next launch.
- **Project**: what `devcapsule project info` reports inside the
  capsule—selected components, runtime environment variables (including
  `DEVCAPSULE_CONTAINER_NAME`), persistent mounts, and temporary paths.
- **Processes**: live processes inside the capsule with their CPU and memory
  usage alongside the container's cgroup limits, refreshed every few seconds
  with a pause toggle for reading long lists. Nothing here stops or signals a
  process; use a terminal for that.
- **Records**: the project's Markdown files rendered in the browser, starting
  at `index.md`. Relative links between records stay inside the console, fenced
  `dot` blocks render as Graphviz diagrams, and linked images or text files are
  served alongside them. Each file is read from the mounted working tree on
  every open, so edits appear on reload.
- **Files**: every file of the mounted project listed directory by directory
  and served read-only with its media type. Videos, audio, PDFs, images, and
  plain-text source or configuration files open in the browser, Markdown files
  open in **Records**, and each file row offers a download link alongside its
  view link. `/files/<path>` links can be shared with anyone who has this run's
  console link.
- **Decisions**: structured multiple-choice questions an agent inside the
  capsule handed to you, with options and cited project records. Pick your
  answers, add an optional note, and submit. Your answer is written only to
  capsule state—never committed into the repository—where the agent reads it,
  records the outcome in project documentation, and removes the prompt.
- **Notifications**: messages posted for this checkout with `devcapsule project
  checkout notifications post`, merged with any unanswered decisions. The bell
  in the top bar shows the unread count and most recent items; the page lets
  you mark notifications read or dismiss them. Nothing pushes desktop pop-ups:
  check the console when convenient, or run `devcapsule project checkout
  notifications list` on the host.

When an agent hands off a decision in chat using `devcapsule project checkout
decisions hand-off`, its message ends with a tokened console link straight to
that decision page so you can answer either in the browser or in chat.

## Changing configuration for the next launch

The **Configuration** page shows the snapshot the launcher captured when this
session started, pre-fills pending `config` commands, and lets you submit
`devcapsule project config` requests to the launcher over a mounted per-run
channel. Requests never mutate the running container; they prepare the **next**
launch, and the launcher classifies each one before acting. Console
`trust accept` and `trust withdraw` requests change the host home’s channel
trust, so they affect other projects using that home too:

- **Recorded immediately for the next launch:** checkout choices and changes
  that keep or narrow host access—`ide`, `add`, `omit`, `restore`, `use`,
  `set`, `deny`, `unbind`, literal `env set NAME VALUE` (neither argument
  starting with `-`), `env unset`,
  `trust withdraw`, `docker-args clear`, and narrowing `authorize` settings
  (`network bridge` or `none`, `docker-daemon none`, and `false` or `none` for
  `development-sudo`, `host-browser`, and `host-x11`). The launcher runs the
  command with full CLI validation and reports `recorded` (or `refused` with
  the CLI's error).
- **Deferred until you confirm on the host:** requests that widen what the next
  launch can reach or trust—widening `authorize` grants, `trust accept`,
  `bind`, `forget`, `env set` from the host (`--from-host`), other `env set`
  forms, and `docker-args set`. Because any process inside the capsule can write to the mounted channel
  directory, widenings are never applied unconfirmed. The launcher saves them
  beside the checkout record so you can confirm or discard them interactively
  at the next `devcapsule project run`, or from a host terminal with:

  ```bash
  devcapsule project config console list
  devcapsule project config console apply REQUEST_ID
  devcapsule project config console discard REQUEST_ID
  ```

- **Refused on the console:** commands that edit shared repository files
  (`require`, `offer`, `drop`, `recommend`, `promote`) or home defaults. Run
  those directly in the repository or with `devcapsule home` on the host.

## The link and the token

Every request to the console—pages, JSON endpoints, and static assets—requires
this run's random token. The launcher writes the token to a private temporary
file, bind-mounts it read-only into the container, and deletes it when the
session ends. Opening the printed `?token=…` link stores the token in a
port-scoped `HttpOnly; SameSite=Strict` session cookie
(`devcapsule-console-token-<port>`) so internal navigation works and several
running capsules can keep their consoles open side by side in the same browser
profile without overwriting one another's cookie. State-changing `POST`
requests also verify the console's own `Origin` header. Stopping the capsule
invalidates the token, and the next run uses a new token and selects an
available port.

The console binds only to `127.0.0.1` on the host, so other machines on your
network cannot reach it directly.

## Without a local desktop (SSH)

On a remote Linux host over SSH, forward the console's loopback port to your
local machine and open the printed URL in your local browser:

```sh
ssh -L 41273:127.0.0.1:41273 user@dev-box
```

Substitute the port printed by `devcapsule project run`. The contained desktop
port forwards the exact same way.

## What you cannot do from it

The console never alters the running container in place, never kills or signals
processes, never edits files in your Git checkout, and never widens host access
or vendor trust without confirmation on the host. Its writes stay strictly
inside capsule state (decision answers and notification read/dismiss actions)
and launcher-mediated configuration requests for future runs.
