# Recorded-E2E skill for rc4

From: presentations
To: maintenance
Date: 2026-11-17

The owner switched to presentations and requested the recorded-E2E skill for rc4.
PR #50 targets release-0.3.1: https://github.com/mycodespace-ai/devcapsule/pull/50
The human merges it; verify live checks first. The skill ships through the
existing presentations export command and reads the installed guide. No workflow
upgrade, source-version change, recorder or viewer change. Export/PEX validation:
11 integration tests pass, skill source/export validators pass, types/conventions,
smoke/PEX/docs and 474 webconsole tests pass. Local unit suite has 3367 passes and
the two inherited gid-0 failures; see PR and presentations status for details.

After merge, maintenance owns release-to-main propagation (preserve main's
0.3.2.dev0 as before), candidate validation and rc4. No tag is cut by this handoff.
The canonical installation instructions are in the shipped presentation_tools
README.md; the skill is SKILL.md alongside it. The user needs no workflow-file
update. PR #43's release and main integration were verified and status corrected.
