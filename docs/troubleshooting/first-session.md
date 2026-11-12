---
description: What to do when the first session stops at Docker, initialization, downloads, pending decisions, the browser, or the keyboard.
weight: 1
updated: 2026-10-30
---
# First-session troubleshooting

| What you see | What to do |
|---|---|
| Docker connection, permission, or Buildx error | Recheck the three [prerequisite commands](../getting-started/install.md#check-your-computer) in the same terminal. On Windows, check [WSL integration](../platforms/windows-wsl2.md). |
| `The embedded resolution matrix does not know '...'` or `... is retired; use '...'` | `project init` rejected an unknown capability or a retired flag (`--need`, `--local`, `--agent`); nothing was written. Run `project init` again with a supported capability or the replacement option named in the message. |
| `--set <name> needs the checkout's IDE first` | Pass `--ide IDE` alongside `--set`, or run `project init` first and record the choice afterward with `devcapsule project config`. |
| `... is already fully initialized` (exit status `2`) | The manifest, lock, checkout record, and resolution already exist and are current. Start with `devcapsule project run`; use `config` to change choices. |
| `Honored existing .../devcapsule.toml` and `Kept .../devcapsule.<platform>.lock` | Initialization reused the shared files while completing this checkout. Read the remaining output for any pending choices. |
| The launch stops with status `3` and a list of pending decisions | Answer each item with the command or flag the list prints (such as `devcapsule home trust accept ...` or `devcapsule project config ...`), or run again in an interactive terminal and answer there; see [Project versus personal](../configuration/project-versus-personal.md#when-the-project-changes). |
| `DevCapsule home ... requires DevCapsule X.Y.Z` | That [configuration home](../configuration/home.md) was written by a newer launcher. Upgrade the executable (see [Launcher updates](../updates/launcher-updates.md)) or select a separate home with `DEVCAPSULE_CONFIG_HOME`. |
| Download or build failure | Check the reported URL, your network connection, and free disk space, then retry `devcapsule project run`. Keep the exact error if you ask for help. |
| No browser tab opens | Open the full printed desktop URL yourself in a browser on the computer running Docker. |
| Escape leaves fullscreen instead of reaching the editor | You clicked the desktop sidebar's fullscreen button. Use the browser's own fullscreen instead; see [Clipboard, keys and browser](../everyday-development/clipboard-and-browser.md). |
| `Session failed: a capsule component died` | Run `devcapsule project diagnose`, or open `devcapsule-supervisor.log` in the session log directory the launcher printed, to see which component exited and why; see [Diagnostics and logs](diagnostics-and-logs.md). |
| `the capsule may still be running` after a second Ctrl+C | Run the `docker stop` command the launcher printed. |
| A shortcut closed the tab | The browser owns certain window and tab shortcuts. Reopen the printed desktop URL and trigger that action from the IDE menus. |

If a session started, run `devcapsule project diagnose --export` (see
[Diagnostics and logs](diagnostics-and-logs.md#when-asking-for-help)) and
[open an issue](https://github.com/mycodespace-ai/devcapsule/issues/new) with your
OS, the output of `devcapsule version`, and the failing command and error.
If no session started, attach the terminal error instead; no session logs exist
yet. Review any text or archive before posting and remove private project details,
access tokens, and live desktop URLs.
