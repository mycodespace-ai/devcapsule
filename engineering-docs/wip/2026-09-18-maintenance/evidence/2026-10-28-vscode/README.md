# VS Code evidence: the recorded IDE smoke, 2026-10-28

`vscode-ide-smoke.webm` is the desktop recording of
`tests/e2e/test_ide_comes_alive.py` for the `vscode` surface, run inside
this capsule from a temporary clone of `ws-maintenance/0.3.0-vscode` at
`d74666ff` (`~/worktrees/vscode-e2e-tmp`), against the executable the
session built from that clone, on the recommended v0.3.0-rc6 base, with
`nox -s ide-smoke -- --display --surface vscode`. The test initialized a
fresh project with `--ide vscode-ide --require node` and the consent
`--authorize vscode-download true`, launched it, read the desktop URL and
the web console URL from the launcher, and proved from outside the
container that an X11 top-level window of class `code code` titled
`e2e-ide-vscode-fa15be38 - Visual Studio Code` owned the capsule's display.
The run took 87.5 seconds: Visual Studio Code 1.143.1 was downloaded from
Microsoft and verified, the `devcapsule-local-vscode` formation was built,
the capsule started, the window appeared, and the browser recorded the
desktop. `vscode-ide-smoke-desktop.png` is the canvas when the IDE was
judged alive, 645 distinct colours on the coarse grid, the welcome dialog
over the workbench. `vscode-ide-smoke-facts.json` is the test's record;
`vscode-ide-smoke-launcher.log` is the launcher's output with the run
tokens redacted. The raw evidence directory was
`dist/e2e-evidence/ide-smoke/20261028T120534Z-f872c9` in the clone.

The implementing Antigravity session had been cut by a power outage with
its smoke unfinished and the slice uncommitted; the matrix's verified edge
for `vscode` 1.143.1 now carries this run's evidence and says no relaunch
or persistence check has run. `review-brief.md` is the brief the review
partner, the Antigravity and Gemini 4 Argon (High) pair, received for
PR301.1, on standard input behind a one-line `-p` instruction.
