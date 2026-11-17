# PR #50 now includes direct skill installation

Supersedes the manual export/copy installation described in
`2026-11-17-presentations-rc4-skill.md`.

At the owner's request, PR #50 now includes commit `7e5e8c6b845bef5c96fadc0771d3b0ec4426d383`:

```sh
devcapsule presentations install-skill .agents/skills/devcapsule-recorded-e2e
```

Use `.claude/skills/devcapsule-recorded-e2e` for Claude Code. The command installs
only SKILL.md, creates parents, and refuses an existing destination. The skill
exports version-matched Python helpers when executing a scenario. Documentation
covers agent locations, an optional AGENTS.md reference and equivalent English
requests. The authored version remains 0.3.1 and the PR still targets release-0.3.1
for the owner-requested rc4. The human merges it; maintenance retains release
propagation and tagging. No workstream switch is implied.

Validation: 24 focused tests and 13 CLI/PEX integration tests pass; syntax,
types, conventions, smoke, PEX, docs contract and webconsole pass. Full local
unit suite has 3370 passes and the same two inherited recursive-orchestrator
gid-0 failures. Hosted checks are on PR #50; consult the current head before
integration. Native skill discovery and natural-language selection have not
been tested in fresh sessions of the three agents.

The rebuilt local dist/devcapsule.pex embeds commit 7e5e8c6b and successfully
installed the exact packaged skill into a separate scratch project. This is a
local build, not rc4.

Accepting this update means using the direct-install instructions when
presenting and validating the skill in the release.
