---
description: Open a desktop IDE inside a capsule, run a small JavaScript program, stop the session, and come back—in fifteen minutes with no AI account.
role: getting-started
aliases:
  - /docs/guides/first-session/
weight: 2
updated: 2026-10-30
---
# Your first session

Open a desktop IDE inside a capsule, run a small JavaScript file, exit the IDE,
and come right back. This walkthrough needs no AI account, no Git repository,
and no Node.js installed on your computer. Complete [Install
DevCapsule](install.md) first, or jump straight to [An existing
repository](../your-project/existing-repository.md) if you already have a
codebase.

## 1. Make a first workspace

In your host terminal:

```bash
mkdir -p ~/hello-devcapsule
cd ~/hello-devcapsule
~/.local/bin/devcapsule project init --require node --ide frontend-ide
```

This requires Node.js for the project and selects `frontend-ide` (default
provider VSCodium) for your checkout. The `--ide codium` alias selects the same IDE. Choosing `--ide vscode` instead
selects Visual Studio Code and adds its vendor download consent question.

Answer the interactive prompts as follows:

| Prompt | What to enter |
|---|---|
| `Project creator (URL or email address)` | Enter `mailto:you@example.org` (or a `https://...` URL you control). This names the project namespace—it is not an account sign-in. |
| `Select the default agent component (antigravity-agent) for your checkout? (yes/no) [yes]` | Type `no` for this walkthrough. You can add any agent later with a single command ([Choose an agent](../working-with-ai/choose-an-agent.md)). |
| `Recommend docker-daemon`, `network`, `development-sudo`, `host-browser` `[none]` | Press **Enter** at each prompt to keep `none`. See [The boundary](../containment/the-boundary.md) for what each host permission controls. |
| `Authorize this checkout to execute ... [default]` | Press **Enter** to approve the pinned base image for this checkout. |

The base prompt shows the recipe (such as `ubuntu-24.04@11`) and exact SHA-256
digest. Approving it during `init` records per-checkout base consent rather
than home-wide channel trust; [Vendor software and
trust](../configuration/software-approvals.md) explains both scopes.

Initialization finishes with `Project initialized; 'devcapsule project run'
starts it.` It writes the shared manifest and platform lock under
`.devcapsule/` in `~/hello-devcapsule` and stores your personal checkout record
under your local DevCapsule configuration home. You initialize a project only
once.

## 2. Open the IDE

```bash
~/.local/bin/devcapsule project run
```

Keep this terminal running. On the first launch, DevCapsule pulls the base
image, downloads VSCodium, and builds the environment image. During startup,
the launcher prints:

- a **desktop URL** (`http://127.0.0.1:<port>/vnc.html?...`) and tries to open it in
  your default browser (if no tab opens automatically, copy the full URL into a
  browser on this machine), and
- on recipe `11` or newer bases, a **web console URL**
  (`http://127.0.0.1:<port>/...`) where you can inspect the running session and
  checkout configuration as web pages.

You see VSCodium inside its own contained desktop with `hello-devcapsule` open
in the Explorer. Your host desktop is not shared with the capsule. Treat both
loopback URLs as session credentials—keep them private and leave the terminal
output visible in case you close the browser tab.

The `~/hello-devcapsule` folder is mounted read-write inside the container, so
edits apply directly to your files on disk while the rest of your home
directory stays outside the capsule.

## 3. Run something

Inside VSCodium:

1. If VSCodium shows a **Restricted Mode** banner, click **Manage** and trust
   the workspace folder.
2. In the Explorer, right-click `HELLO-DEVCAPSULE`, choose **New File**, and
   create `hello.js`.
3. Add this line and save (**File → Save**):

   ```javascript
   console.log("Hello, DevCapsule!");
   ```

4. Open **Terminal → New Terminal** inside VSCodium and run:

   ```bash
   node hello.js
   ```

You see `Hello, DevCapsule!` printed by the capsule's Node.js runtime with
nothing installed on your host. Edit the message, save, and run it again.

Your host clipboard is not shared automatically with the contained desktop. To
copy or paste across the boundary, open the noVNC control bar on the left edge
of the desktop tab and use its clipboard box; see [Clipboard and
browser](../everyday-development/clipboard-and-browser.md).

## 4. Stop, and come back

Save your file and choose **File → Exit** inside VSCodium. The container stops
and removes itself, and your host terminal returns to its prompt. Whenever you
want to resume:

```bash
cd ~/hello-devcapsule
~/.local/bin/devcapsule project run
```

Open the newly printed desktop URL: `hello.js` and your VSCodium layout and
settings persist. You do not need to initialize this checkout again. Processes
inside the previous container stopped when it exited—run `node hello.js` (or any dev server) again when you
need it. See [Stop and come back](stop-and-come-back.md) for tab closing and
`Ctrl+C` behavior.

**Next: [bring an existing repository](../your-project/existing-repository.md)
or [choose a coding agent](../working-with-ai/choose-an-agent.md).** Hit a
snag? Check [First-session troubleshooting](../troubleshooting/first-session.md).
