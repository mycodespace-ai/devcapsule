# Prepared delivery

No PR has been opened or edited by this agent; remote PR existence has not been
verified. The implementation branch is pushed through merge `7fc77f24` and its validation records, including the
recorded E2E procedure. A pre-existing PR from that branch receives the pushed
commits automatically, but its description and attachments have not been updated. WORKFLOW-LOCAL.md, GitHub Integration rules 4–6,
requires a passing unit gate before PR opening/updating, and assigns GitHub
operations to the human when its prescribed gh installation is absent. The
current environment has both blockers. Preserve both branches until the gate
is resolved in a suitable environment and the owner performs PR delivery.

## Implementation PR draft

Base: `main`. Head: `ws-github-auth/ssh-proxy`.

Title: Add opt-in host GitHub SSH authentication for capsules

Body:

Git operations currently require installing SSH credentials inside each capsule.
This adds an opt-in `github-ssh` authorization: the outside launcher owns a Unix
socket broker that runs host OpenSSH for validated GitHub upload/receive requests,
while capsule Git uses the shipped PEX adapter. Private keys remain on the host.
Linux/WSL with native Docker is supported first; Docker Desktop is refused.
Host trust and unlocked encrypted keys are prerequisites. The capability grants
Git access to all repositories available to that host identity.

Validation: the physical-host relaunch and recorded recursive E2E passed on
rootless Linux Docker. A fresh VSCodium capsule, with no SSH files or agent,
cloned `git@github.com:mycodespace-ai/devcapsule.git` through the inherited host
broker. Independent checks confirmed the expected commit, SSH origin, clean tree,
read-only socket mount from the same host source, and exact runtime PEX checksum.
A missing-socket control failed with exit 128. The container, workspace and
checkout records were removed. No real GitHub push was performed.

The [recorded E2E procedure](engineering-docs/wip/2026-11-16-github-auth/evidence/showcase.md)
records the tested build and evidence. The 38-second WebM and full desktop capture
are retained locally under `devcapsule-src/tests/e2e/evidence/github-ssh-proxy-pre-merge/`;
they are not uploaded or attached to a PR. Tested PEX SHA-256:
`33c3c7bc7fe6ff6772eedee06424c95afcf4aebddca20ab99f9a31a7c103d35b`.

The full release-0.3.1 tip `10e7fda3` is merged by `7fc77f24`, preserving
both histories and including the release's other changes. A fresh capsule launched
with the rebuilt merged PEX repeated SSH clone acceptance successfully, including
IDE/console readiness, no child credentials, exact PEX bytes, missing-socket
negative control and cleanup. Evidence:
`devcapsule-src/tests/e2e/evidence/github-ssh-proxy-release-merge/20261116T100132Z/`.
Merged PEX SHA-256:
`af7fa02ca2c2737f3a1678226341312682b71cfdd37eb892f29a42ad5c31b78c`.
That unrecorded repeat used the earlier host broker. A subsequent host relaunch
now supplies the merged PEX to both parent and child. New recorded acceptance
`20261116T103152Z-af7fa02c` passed clone, missing-socket refusal, restored read,
independent Git/Docker checks and cleanup. The new 45.42-second video is at
`devcapsule-src/tests/e2e/evidence/github-ssh-proxy/20261116T103152Z-af7fa02c/scenario-video.webm`
in the primary checkout. The earlier video remains preserved separately. Neither
video has been uploaded or attached to a PR. The latest recording also has a
six-step presentation served directly by the running console from that evidence
folder. Its authored script and reproducible metadata producer are versioned; the
media and generated presentation remain local. Discovery, captions and each step's
playback boundary passed real-browser validation.

Latest validation: 41 focused cases passed; types passed over 350 files and
conventions reported zero breaches. Unit gate: 3309 passed, 3 failed, 1 skipped,
187 deselected, 1 xfailed, 1 xpassed. CLI smoke, PEX packaging/smoke, docs contract,
console types and 474 console tests passed. Integration: 149 passed, 12 skipped,
3 failed initially; the socket-length case passed when rerun with shorter scratch,
leaving two failures. All five remaining unit/integration failures reproduce on
untouched release-0.3.1; maintenance received the reproduction details. This is
not a passing full gate. See the workstream status for exact IDs and scope.

Pair: GPT-6 Codex with Antigravity Gemini 4 Hydrogen High
(`gemini-4-hydrogen-high`). Local round 1 accepted at `388f62a3`; formal review PR
must be merged into this branch before mainline delivery.

## Review PR draft

Base: `ws-github-auth/ssh-proxy`. Head: `ws-github-auth/ssh-proxy-review`.

Title: Review GitHub SSH proxy diagnostics and lifecycle coverage

Body:

Gemini Hydrogen review separates capsule SSH failures from broker failures,
clarifies disclosure and dry-run lifetime, removes an unused frame helper,
declares the public review API and strengthens parser, authorization and process
cleanup coverage. Round 1 addresses test environment independence and cleanup.
The implementor accepted `388f62a3` locally after a conflict-free temporary merge
passed 75 focused cases. The reviewer branch alone lacks the parent's later node
registry refurbishment and console-table fix; validate the merged candidate.
Full gate and owner-operated PR delivery remain outstanding.

## Resume sequence

1. Fetch canonical upstream and recheck workflow synchronization and live state.
2. Resolve the known full-gate environment failures without disabling tests;
   run the required gate on the combined candidate before PR opening/updating.
3. The owner creates the implementation and review PRs, then merges the review
   into the implementation branch. Record the formal assessment at its SHA.
4. Fetch that merged branch and run required validation. The physical-host clone
   acceptance above used the implementation without review corrections; repeat
   relevant acceptance against the merged executable. A real GitHub write test
   remains separate and requires an explicitly selected disposable repository.
5. The owner merges the implementation PR into main; fetch and verify main's tree
   before recording integration. No release or installation has been performed.


## Owner delivery links

- [Implementation comparison](https://github.com/mycodespace-ai/devcapsule/compare/main...ws-github-auth/ssh-proxy?expand=1)
- [Review comparison](https://github.com/mycodespace-ai/devcapsule/compare/ws-github-auth/ssh-proxy...ws-github-auth/ssh-proxy-review?expand=1)

Use the body above when the gate and GitHub-operation prerequisites are resolved.
The branch push does not upload the local recording or change a PR description.
