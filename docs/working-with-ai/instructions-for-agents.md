---
description: Give every agent the same durable context with an instructions file at the project root, and what belongs in it.
weight: 3
updated: 2026-10-30
---
# Instructions for agents

A short instructions file at the project root gives agents the commands and
rules they need. Commit it with the source so contributors receive the same
instructions.

## One source of truth for all three agents

Keep shared project rules in `AGENTS.md` at the repository root. Ask each
agent to read it at session start. For Claude Code, commit a `CLAUDE.md`
pointer beside it instead of maintaining a second copy of the rules:

```markdown
Read and follow AGENTS.md at the repository root. This project keeps shared
agent instructions in AGENTS.md rather than duplicating them per tool.
```

## What belongs in `AGENTS.md`

Keep `AGENTS.md` concrete and verifiable:

- **Purpose and layout:** two sentences on what the software does and where key
  packages, entrypoints, and architecture docs live.
- **Exact build, lint, and test commands:** the commands that run inside the
  capsule terminal (for example, `pytest -q`, `npm test`, `mvn verify`) so the
  agent checks its own changes without guessing flags.
- **Changes that need human confirmation:** generated files not to hand-edit,
  migrations or public contracts not to break silently, and branches never to
  push directly.
- **Commit and review expectations:** how changes should be scoped, tested, and
  described in commit messages or pull requests.
- **Where active state lives:** any status or decision log the agent should
  read at session start and update before stopping.

Keep instructions short and remove stale rules. Instruction files guide the
agent; they do not restrict what its processes can access. Use the capsule's
mounts and host authorizations to control access
([The boundary](../containment/the-boundary.md)).

DevCapsule's own project workflow ships a structured `AGENTS.md`, `WORKFLOW.md`,
and status-file convention so humans and different coding agents can hand work
off cleanly across branches; see [Working in
workstreams](../collaboration/working-in-workstreams.md) if you want to adopt
it in your repository.
