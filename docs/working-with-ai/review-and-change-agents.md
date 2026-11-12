---
description: Reviewing what an agent did before you keep it, and switching between agents on the same project without losing state.
weight: 5
updated: 2026-10-30
---
# Review and change agents

Review the agent's changes before you commit or merge them. Use Git, your
IDE, and the project's checks. You can ask another agent to review the work.

## Reviewing an agent's work before keeping it

1. **Keep a recovery point outside the capsule.** Commit your current work,
   then push it to a remote or keep an independent backup. A local commit
   alone is not protected from processes that can write `.git`. A linked
   Git worktree shares repository data and is not an independent backup.
   Keep the backup or remote outside the agent's write permissions.
2. **Inspect every modified and untracked file.** Use your IDE's Git diff tool
   or run these checks in the terminal:

   ```bash
   git status --short
   git diff
   git diff --staged
   ```

   Watch for unintended edits to lockfiles, CI definitions, `.devcapsule/`, or
   skipped tests, plus stray scratch files left in the tree.
3. **Run the project's checks yourself.** Execute your unit tests, linter, and
   type checker in the capsule terminal rather than relying solely on the
   agent's summary—especially for newly added tests, which can mirror a flawed
   assumption in the implementation.
4. **Discard or refine cleanly.** Revert unwanted hunks with `git restore -p`
   (and remove untracked scratch files after previewing `git clean -nd`), or
   ask a second agent to review the diff before you commit and push.

## Running multiple agents or switching on a checkout

Claude Code (`claude`), OpenAI Codex (`codex`), and the Antigravity CLI
(`antigravity`) install into separate `/opt/...` prefixes and keep independent
persistent state directories (`~/.claude`, `~/.codex`, `~/.gemini`). You can
keep more than one enabled on the same checkout—for instance, implementing a
feature with one agent and asking another to critique the branch.

Manage your checkout's agents from a host terminal in the project directory (or
request `add`, `omit`, and `restore` from the running session's [web
console](../sessions/web-console.md)). The launcher records accepted requests
immediately. The running environment changes only after you stop the capsule
and launch it again:

```bash
# Try an agent for a single launch without saving it to the checkout
devcapsule project run --with codex-agent

# Add an agent to this checkout's saved selection (shared manifest unchanged)
devcapsule project config add claude-code-agent

# Remove a checkout-added agent, or omit an agent offered by the project
devcapsule project config omit antigravity-agent

# Re-enable a project-offered agent that you previously omitted
devcapsule project config restore antigravity-agent
```

(Capability names and unambiguous component aliases—`claude-code`, `codex`,
`antigravity-cli`—both work on `add`, `omit`, and `restore`. Required
capabilities declared with `require` in `.devcapsule/devcapsule.toml` cannot be
omitted.)

Use `restore` only for project offers. To bring back a checkout addition that
you removed, use `add` again. If an agent has an explicit secret binding,
remove it with `config unbind` before omitting the agent; see
[Sign in and defaults](sign-in-and-defaults.md#binding-api-keys-explicitly).

### Your sign-in and settings stay intact when you switch

Running `devcapsule project config omit <agent>` removes that agent from the
next environment selection. It does not delete its saved state or old images.
Its persistent directory under your [configuration home](../configuration/home.md)
keeps settings and session files for later use. Omitting an agent is not a
way to revoke its provider credentials or hide files from another agent.
