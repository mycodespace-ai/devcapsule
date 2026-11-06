---
description: Run DevCapsule on Windows through WSL2 and Docker Desktop's Linux integration, and open the capsule desktop in your Windows browser.
role: windows
aliases:
  - /docs/guides/windows-wsl2/
weight: 2
updated: 2026-10-30
---
# Windows: read this before installing

DevCapsule {{tag}} ships a **Linux Intel/AMD 64-bit (`x86_64`) executable**. On
Windows, run it inside a Linux distribution under **WSL2** with Docker
Desktop's WSL2 Linux container integration enabled. PowerShell and Command
Prompt cannot run the executable directly, and Windows on ARM is not supported
in {{tag}}.

Pay attention to three WSL2 details up front: enabling Docker Desktop for your
specific WSL2 distribution, keeping project files inside the Linux filesystem,
and opening the capsule's loopback URL in your Windows browser.

## Get Docker working in your WSL2 terminal

Follow [Docker Desktop's WSL2 backend guide](https://docs.docker.com/desktop/features/wsl/)
and enable your Linux distribution under **Settings → Resources → WSL
Integration**. Open that distribution's Linux terminal and verify:

```bash
uname -sm
docker info
docker buildx version
```

Confirm you see `Linux x86_64`, a responding Docker daemon, and a Buildx
version before continuing. If `docker info` works in PowerShell but fails inside
WSL2, re-check the distribution toggle under **WSL Integration** in Docker
Desktop.

Keep your repositories inside your WSL2 Linux home directory (for example,
`~/projects/my-app`) rather than under `/mnt/c/...`. Linux bind mounts, file
permissions, and IDE file watchers are substantially faster and more reliable
on the native ext4 WSL2 filesystem; see Microsoft's
[WSL filesystem guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems).

Next, complete [Install](../getting-started/install.md) and
[Your first session](../getting-started/first-session.md), running every
host-terminal command inside this WSL2 Linux terminal.

## Open the desktop and web console in Windows

When `devcapsule project run` starts a session, it prints `127.0.0.1` links for
the contained desktop and the [web console](../sessions/web-console.md). Paste
the **entire URL** (including its token) into your Windows browser. Because the
capsule serves its own desktop over HTTP to your browser, you do not need WSLg
or a separate Windows X server.

If your WSL2 distribution has `wslview` installed (from the `wslu` package),
you can have the launcher open your Windows browser automatically:

```bash
BROWSER=wslview devcapsule project run
```

(Use `~/.local/bin/devcapsule` if `~/.local/bin` is not yet on `PATH`.)
Otherwise, copying and pasting the printed URL into your browser works the same
way. Keep the WSL2 terminal open while you work; closing the browser tab leaves
the capsule running so you can reconnect at the same URL.

## If the URL does not connect

1. Check that Docker Desktop is still running and that you pasted the full URL
   from the **current** `devcapsule project run` output (every launch uses a
   new token and selects an available port).
2. Test from inside WSL2 (`curl -I "http://127.0.0.1:PORT/"` using the printed
   port) to see whether the listener answers inside Linux before troubleshooting
   WSL2-to-Windows `localhost` forwarding.
3. Avoid applying unverified firewall or DNS workarounds. If loopback
   forwarding fails on your setup, [open an issue](https://github.com/mycodespace-ai/devcapsule/issues/new)
   with the exact error, Windows build, and `wsl --version` output—removing the
   private URL tokens before posting.
