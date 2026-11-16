# GitHub SSH proxy delivery

Implementation: [PR #47](https://github.com/mycodespace-ai/devcapsule/pull/47),
`ws-github-auth/ssh-proxy` into `release-0.3.1`. The human merges the release.
Review: [PR #44](https://github.com/mycodespace-ai/devcapsule/pull/44), merged at
`9638cb11` after acceptance of `455d3acc` in round 2.
The GitHub CLI is available and both remote states were verified on 2026-11-16.

The implementation PR description below was published after the required gate;
its known failures remain disclosed. No new E2E recording was made or uploaded.

## Published implementation description

Adds opt-in host SSH authentication for GitHub clone, fetch and push inside capsules. With `github-ssh` authorized, the outside launcher runs host OpenSSH for validated GitHub Git requests. Capsule Git connects through a private Unix socket; private keys and the host SSH agent stay on the host. Non-GitHub destinations use capsule SSH.

**Target: `release-0.3.1`, as directed by the owner.** Package/workflow version files and the documentation version manifest match that release. Unrelated mainline documents are excluded. The release branch is already included through merge history; this PR does not bring the next development version into the release.

The initial transport supports Linux/WSL with native Docker, including the tested rootless Docker setup. Host key trust and noninteractive host SSH authentication are prerequisites. The grant covers all GitHub repositories available to the host identity. Docker Desktop, HTTPS/gh API credentials, Git LFS authentication, signing and arbitrary SSH aliases/options remain outside this slice.

Pair Review: GPT-6 Codex with Antigravity Gemini 4 Hydrogen High (`gemini-4-hydrogen-high`, high effort). Review #44 was accepted after round 2 at `455d3acc` and merged at `9638cb11`. It corrects error attribution and authorization/lifetime disclosure, and strengthens parser, process cleanup and refusal tests. Both assessments are on #44.

Validation on combined review merge `9638cb11`:

- 64 focused unit/integration cases passed, including real local Git clone/fetch/push through the broker.
- Full build reached 3,320 passing unit cases; **two inherited recursive-launch tests fail** because this capsule's Docker socket group ID is zero. One skip, one xfail, one xpass; 191 deselected by the standard suite. The same failures occurred in the reviewer's independent run. No tests were disabled.
- Types passed on 351 files; conventions found zero breaches.
- Separate CLI smoke, PEX build/smoke, documentation contract (249 pages), console types and all 474 console tests passed.
- The rebuilt PEX completed a real read-only GitHub `ls-remote` using an empty HOME and the inherited host proxy. Missing-socket control exited 128. No GitHub write, container launch or host-launcher replacement occurred.

**The local full gate is not green.** The owner-directed PR cleanup and release retarget do not waive these release-acceptance failures. The known failures are `test_public_dry_run_is_unique_redacted_and_cleans_owned_staging` and `test_contained_display_dry_run_forwards_no_host_x11` in `tests/test_recursive_orchestrator.py`.

Earlier physical-host relaunch and recorded recursive E2E passed: a fresh capsule without SSH files or agent cloned the real repository through the inherited host proxy; missing-socket access failed. That recording predates the final review corrections. The retained movie and six-step presentation are local evidence, not GitHub attachments. See the [procedure](https://github.com/mycodespace-ai/devcapsule/blob/ws-github-auth/ssh-proxy/engineering-docs/wip/2026-11-16-github-auth/evidence/showcase.md).

Limits: process-lifecycle integration tests depend on Linux `/proc`, scheduling and a documented 0.5-second fixture-startup allowance. The broker's runtime I/O is not proof of strict Host Inputs separation across the whole subsystem. Desktop transport and broader effect separation remain follow-ups. The human merges this PR into the release; maintenance carries the release to main.
