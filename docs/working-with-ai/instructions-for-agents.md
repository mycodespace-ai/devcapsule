---
description: Give every agent the same durable context with an instructions file at the project root, and what belongs in it.
weight: 3
updated: 2026-11-18
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

## Record a scenario

From the project root, install the workflow and its recording skill:

```bash
devcapsule bootstrap project
```

`devcapsule project wrap` also installs the kit in the wrapper repository.
Setup creates `.agents/skills/devcapsule-recorded-e2e/` for Codex and Antigravity
and `.claude/skills/devcapsule-recorded-e2e/` for Claude Code. Each folder contains
`SKILL.md`, `kit-version.json`, and `presentation_tools/` with the guide,
Python helpers, and example. No DevCapsule source checkout or export command
is needed. Setup installs resources; it does not install browsers or run tests.

Start a new agent session, then ask:

> Run the end-user scenario in tests/e2e/login.md and record a presentation
> with videos of what happened.

If the agent does not discover the skill, tell it to read the installed
`SKILL.md` directly. It should follow the adjacent `presentation_tools/README.md`,
use the project's actual test driver, and report passed, failed, or incomplete
with the evidence. A recording alone does not prove the test passed.
Use [console content links](../sessions/web-console.md#link-to-project-content)
to hand off the result.

### Keep or update an existing kit

Bootstrap and wrap preserve existing skill folders, including customizations
and symlinked locations. Re-running setup does not upgrade a preserved kit.
Check `kit-version.json` for its version. An older installation might contain
only `SKILL.md` or refer to removed commands.

To migrate it, review and move that skill folder to a backup outside the agent
skill directories. Rerun `devcapsule bootstrap project`, then reconcile your
custom instructions with the new kit. Repeat for each discovery location you
use. Existing workflow definitions stay unchanged unless you explicitly pass
`--refresh-workflow-definition`; that flag does not refresh preserved skills.
Keep the chosen kit under your project's normal commit policy.

After upgrading the host executable, launch a new capsule to get its runtime
CLI. Replacing the host executable does not change a capsule already running.

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
