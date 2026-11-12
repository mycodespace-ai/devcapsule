---
description: How each agent signs in inside the capsule, the no-approval defaults DevCapsule seeds for it, where those settings live and how to change them.
weight: 2
updated: 2026-10-30
---
# Sign in and defaults

Agents authenticate from a terminal inside the running capsule using your own
provider account or API key. Each agent's settings and local session files
live in a persistent directory for that checkout. DevCapsule creates managed
agent directories with mode `0700`. Processes running as the same capsule
user can still read them.

## Signing in interactively

| Agent | Command in the capsule terminal | Persistent slot inside the capsule |
|---|---|---|
| Claude Code | `claude` (follow the sign-in flow) | `/home/devcapsule/.claude` (`CLAUDE_CONFIG_DIR`, slot `claude-code/home`) |
| OpenAI Codex | `codex login` (or `codex login --device-auth`; check with `codex login status`) | `/home/devcapsule/.codex` (`CODEX_HOME`, slot `codex/home`) |
| Antigravity CLI | `antigravity` (follow its authentication flow) | `/home/devcapsule/.gemini` (settings and sessions, slot `antigravity-cli/home`; credentials use its keyring or arrive per run) |

When an agent prints or opens an OAuth URL:

- **Without `host-browser`:** copy the URL out through the desktop tab's left
  sidebar clipboard box, open it in your computer's browser, and paste any
  authorization code back the same way ([Clipboard, keys and
  browser](../everyday-development/clipboard-and-browser.md)).
- **With `host-browser` authorized** (`devcapsule project config authorize
  host-browser true` or one-run `devcapsule project run --authorize
  host-browser true`): links opened through `BROWSER` or `xdg-open` reach your
  host browser through DevCapsule's URL-only broker. A printed URL does not open
  automatically. This authorization does not forward OAuth callback ports;
  use the agent's device or code flow, or configure the needed
  [network access](../everyday-development/previews-and-ports.md).

The managed directories above are stored under your local DevCapsule data
directory (`projects/by-path/<checkout>/components/<agent>/home`). They stay
outside the repository. A directory you explicitly bind or adopt can live
elsewhere.

## Binding API keys explicitly

DevCapsule never forwards `OPENAI_API_KEY`, `GEMINI_API_KEY`, or
`ANTHROPIC_API_KEY` from your host shell automatically. Use an explicit binding
or environment setting for API-key authentication.

Select the agent first. Run the following `devcapsule` commands in a host
terminal from the project directory. A binding stores the variable's name,
not its value. The variable need not exist when you bind it, but it must be
exported in the host shell that runs `devcapsule project run`.

- **Codex (`OPENAI_API_KEY`):** bind the declared secret input to your host
  environment variable. Alternatively, `codex login --with-api-key` reads a
  key from standard input inside the capsule:

  ```bash
  devcapsule project config bind codex/openai-api-key host-environment:OPENAI_API_KEY
  # Withdraw later with:
  devcapsule project config unbind codex/openai-api-key
  ```

- **Antigravity CLI (`GEMINI_API_KEY` for headless `gemini` provider flows):**

  ```bash
  devcapsule project config bind antigravity-cli/gemini-api-key host-environment:GEMINI_API_KEY
  ```

- **Other provider variables (such as `ANTHROPIC_API_KEY`):** store a literal
  per-checkout value with hidden input (`devcapsule project config env set
  ANTHROPIC_API_KEY`) or pass it for one run (`devcapsule project run --env
  ANTHROPIC_API_KEY`).

Through the web console, `bind` waits for host confirmation with `config
console apply ID` or the next interactive launch. `unbind` is recorded
immediately. Both affect future launches; stop the current capsule to end
its access to an already supplied key.

Environment delivery exposes keys to capsule processes and Docker inspection.
Interactive sign-in avoids that environment exposure, but does not hide
credentials from other agents running as the same user.

## The defaults DevCapsule seeds

Before an agent's first launch in a checkout, DevCapsule seeds minimal settings
so tools run without interactive permission prompts inside the container.
These defaults apply to managed state; explicitly bound or adopted
directories keep their existing contents.

| Agent | File in the capsule | Seeded settings |
|---|---|---|
| Claude Code | `~/.claude/settings.json` | `{"permissions": {"defaultMode": "bypassPermissions"}, "skipDangerousModePermissionPrompt": true}` |
| OpenAI Codex | `~/.codex/config.toml` | `approval_policy = "never"`, `sandbox_mode = "danger-full-access"`, and `use_legacy_landlock = true` |
| Antigravity CLI | `~/.gemini/antigravity-cli/settings.json` | `{"toolPermission": "always-proceed"}` |

Claude Code also runs with `DISABLE_UPDATES=1` so the binary matches the
pinned artifact in your lock rather than self-updating inside the container;
update agents through DevCapsule ([Component
upgrades](../updates/component-upgrades.md)).

### Changing or opting out of seeded defaults

DevCapsule treats these files as initial defaults, never forced overrides:

- **Claude Code and Antigravity CLI:** on launch, DevCapsule merges only
  missing keys into a valid JSON file. Change `permissions.defaultMode` or
  `toolPermission` to another value and your choice stays; deleting the key
  restores the capsule default on the next launch. Malformed JSON files are left
  untouched with a warning.
- **OpenAI Codex:** `~/.codex/config.toml` is written **once**, only when the
  file does not exist yet. Edit or remove keys (including `use_legacy_landlock`
  if a newer Codex build marks it deprecated) freely. Keep any top-level keys
  you add **above the first `[table]` header**. Keys below a table header
  belong to that table.

Model entitlements and rate limits come from your vendor account; upgrading an
agent binary in DevCapsule does not by itself change which models your plan can
access.
