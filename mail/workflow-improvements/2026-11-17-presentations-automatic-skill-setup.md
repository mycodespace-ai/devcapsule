# Automatic recorded-E2E skill setup: PR #51

The owner directed that workflow users and wrapper users receive skills during
normal setup, without another CLI command. PR #50 merged at release 757392b2;
its follow-up is PR #51, https://github.com/mycodespace-ai/devcapsule/pull/51,
from ws-presentations/automatic-skill-install at c5549f720aec2e94cdee31fb39c87b9cc5388d30,
targeting release-0.3.1 for rc4. This updates the installation guidance in
2026-11-17-presentations-direct-skill-install.md.

Workflow bootstrap and the project-wrap CLI install SKILL.md in both
.agents/skills/devcapsule-recorded-e2e/ and .claude/skills/devcapsule-recorded-e2e/.
Existing skill folders and linked locations are preserved. Generated agent
guidance points to the skill; wrapper support files stay outside foreign sources.
Existing workflow definitions need no refresh to add missing skills.
The standalone install-skill command remains for projects using neither setup.

The common skill installer receives packaged bytes as an argument. Bootstrap
and the wrapping CLI compose it with their existing work; wrap_project's source
operation is unchanged apart from generated agent guidance. No workflow rule or
version stamp changes, and no existing project configuration was edited here.

Validation: 15 real CLI/PEX tests passed, including both workflow modes,
repeat setup preserving customizations, and a local Git repository wrapped
without foreign source changes. Syntax, types, conventions, smoke, PEX,
docs and webconsole pass. Full unit suite: 3373 passes and the same two inherited
gid-0 failures; no legacy test was changed. Native agent discovery is untested.
The final local devcapsule.pex embeds c5549f72 and successfully bootstraps both
exact skill copies. Consult PR #51 for hosted checks.

For maintenance: accepting this update means including PR #51 with #50 for the
owner-requested rc4 and using the automatic setup instructions during validation.
The human merges; maintenance owns release propagation and candidate tagging.
For workflow-improvements and wrapped-projects: acknowledge this delivered
setup behavior and preserve it in future bootstrap/wrapper changes; no new
implementation assignment is requested.
