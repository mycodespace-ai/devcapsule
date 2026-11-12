---
description: "Move a project to another computer: what travels in Git automatically, what personal choices you recreate, and how to carry preferences safely."
weight: 4
updated: 2026-10-30
---
# Another machine

Moving a DevCapsule project to a second computer separates cleanly into two
halves: the shared environment committed to Git, which arrives on `git clone`,
and your personal choices, credentials, and local state, which stay on the
machine where you created them.

## What arrives with `git clone`

Everything the repository commits is ready immediately on the new computer:

- **Environment contract and pinned versions:** `.devcapsule/devcapsule.toml`
  and `.devcapsule/devcapsule.<platform>.lock` carry the project's required and
  offered capabilities, exact component versions and SHA-256 digests, base
  image reference, project mount path, declared environment variables, and
  optional workflow declaration.
- **Repository rules and agent instructions:** committed editor rules
  (`.editorconfig`, `.vscode/settings.json`, shared run configurations),
  `AGENTS.md`, `CLAUDE.md`, and `WORKFLOW.md` / `WORKFLOW-LOCAL.md`.
- **In-progress workstream coordination:** if the repository uses DevCapsule's
  [multiple-stream workflow](../collaboration/working-in-workstreams.md), live
  status files, claims, and mail live on the remote's `coordination` branch and
  are visible from the new clone as soon as you run `devcapsule workflow
  brief`.

## What stays on the old computer

Nothing outside the repository working tree is pushed to Git or copied
automatically:

- **Home settings and channel trust** (`~/.config/devcapsule/settings.toml`):
  your [home defaults](../configuration/home.md) (`memory`, `cpus`) and
  accepted vendor or DevCapsule download channels.
- **Per-checkout configuration**
  (`~/.config/devcapsule/projects/<creator>/<slug>/`, with URL-encoded creator
  and slug): your chosen IDE (when
  the project leaves the choice open), added or omitted optional capabilities,
  host-access authorizations, saved `config env` variables, secret bindings,
  and extra `docker run` arguments.
- **Persistent capsule directories** (`~/.local/share/devcapsule`,
  `~/.local/state/devcapsule`, `~/.cache/devcapsule`): `/home/devcapsule`,
  [extra tools](../configuration/extra-tools.md) in `~/xtras`, IDE keymaps and
  plugins, agent sign-ins and conversation history, and session logs; see
  [What persists](what-persists.md).

## Start clean on the new computer

In most cases, starting fresh from the clone takes only a few minutes after the
initial image download:

1. **Install DevCapsule** on the new [Linux](../platforms/linux.md) or
   [Windows WSL2](../platforms/windows-wsl2.md) computer by following
   [Install](../getting-started/install.md).
2. **Clone the repository** into your Linux home directory (`git clone ...`)
   and `cd` into it.
3. **Launch the project:**

   ```bash
   devcapsule project run
   ```

   DevCapsule reads the committed manifest and lock, prompts once for any
   unresolved choices on this machine (such as your preferred IDE, download
   trust, or required environment variables), downloads and verifies the exact
   pinned components, and opens the capsule desktop.
4. **Reconnect credentials and agents:** sign coding agents in interactively
   inside the capsule, or bind declared host secrets and environment variables
   on the new computer with `devcapsule project config env set` and `devcapsule
   project config bind`; see
   [Sign in and defaults](../working-with-ai/sign-in-and-defaults.md) and
   [Project versus personal configuration](../configuration/project-versus-personal.md).

## Carry personal preferences over (optional)

When you have customized an IDE profile or shell setup that you do not want to
rebuild by hand, carry over the portable parts rather than copying DevCapsule's
entire internal config tree:

- **Do not copy raw `*.checkout.toml` or `*.resolved.toml` files across
  computers.** Each checkout record validates the exact canonical checkout path
  on disk (`checkout.path`) and references host paths that rarely match another
  machine's username or directory layout. Let `devcapsule project run` (or a
  handful of `devcapsule project config` commands) generate clean records on
  the new host.
- **IDE settings and extensions:** use your IDE's built-in settings export or
  sync feature, or copy just the clean IDE configuration directory (for example
  from a backup archive) onto the new computer and attach it to the checkout
  before launching:

  ```bash
  devcapsule project state adopt --from "$HOME/.devcapsule-profiles/pycharm/config" pycharm/config
  ```

  Or use `devcapsule project config bind <slot> host-directory:PATH` when you
  plan to share that profile across sequential checkouts on the new computer;
  see [IDE preferences and plugins](../configuration/ide-preferences.md). Make
  sure no IDE was running when you archived the directory so you do not copy a
  stale `.lock` file.
- **Dotfiles and `~/xtras`:** keep shell configuration in a dotfiles repository
  you can clone into `/home/devcapsule`, and recreate `~/xtras` from a small
  install script rather than copying compiled binaries blindly. Anything the
  whole project relies on belongs in `.devcapsule/devcapsule.toml` instead of
  `~/xtras`; see [Declare what the project needs](../your-project/declare-needs.md).
- **Credentials and tokens:** treat `~/.claude`, `~/.codex`, `~/.gemini`,
  `~/.ssh`, and saved environment files under `~/.config/devcapsule` as
  secrets. Prefer signing in fresh on the new machine or pulling keys from your
  secret manager rather than copying credential files over untrusted storage.
