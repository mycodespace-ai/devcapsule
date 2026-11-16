# Package E2E recording and presentation tools for adopter agents

Base: `release-0.3.1`
Head: `ws-presentations/0.3.1-authoring`

An agent in another project currently needs DevCapsule's source tree to turn
an English E2E scenario into a recorded presentation. Ship the instructions
and Python helpers in the installed executable: `presentations guide` explains
the flow, `export` supplies a standalone Playwright kit, and `hand-off` prints
the console link. The engineer can supply an existing Markdown scenario or
inline English; the agent performs the project-specific actions and assertions.

Move the existing presentation producer into the shipped package, retaining
the repository replay adapter. Add a recorder that derives timing from action
frames and labels failed or incomplete attempts. Preserve the accepted viewer.

Validation: 148 focused/recorder-compatibility tests and 11 integration tests passed; syntax, mypy and test conventions passed;
PEX build/smoke and the 249-page documentation contract passed; 474 webconsole
tests passed. A real browser exercised the exported kit in an unrelated scratch
project and played every chapter of passing, failed and incomplete presentations
using the viewer embedded in the executable.

The full gate still stops on the inherited recursive Docker-group failure
after 1438 passes. Pair Review with Antigravity
`gemini-4-hydrogen-high`, `--effort high`, is complete. Review PR #46 was
accepted after one correction round and merged at `d4564313`. The final
recording/playback checks passed again after that merge. Check the live hosted
results before the owner merges into the release branch. The hosted gate
does not exercise this project's real application scenario or independently
establish presentation quality.
