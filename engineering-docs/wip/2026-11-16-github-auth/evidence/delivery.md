# Prepared delivery

No PR has been opened or edited by this agent; remote PR existence has not been
verified. The implementation branch includes merge `7fc77f24`, the merged-build recording,
the six-step presentation, and the cross-project authoring audit. A pre-existing PR from that branch receives the pushed
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

The full release-0.3.1 tip `10e7fda3` is merged by `7fc77f24`, preserving
both histories. The recorded acceptance uses the merged PEX for both parent and
child after a physical-host relaunch. Tested PEX SHA-256:
`af7fa02ca2c2737f3a1678226341312682b71cfdd37eb892f29a42ad5c31b78c`.

The [recorded E2E procedure](engineering-docs/wip/2026-11-16-github-auth/evidence/showcase.md)
identifies the retained 45.42-second movie at
`devcapsule-src/tests/e2e/evidence/github-ssh-proxy/20261116T103152Z-af7fa02c/scenario-video.webm`.
The live console serves a six-step presentation from that folder. Its Markdown
script, recorded chapter boundaries and metadata producer are versioned. Chromium
verified discovery, screenshots, captions, all six playback boundaries and media
byte ranges. Media and generated metadata remain local, outside build output;
they have not been uploaded or attached to GitHub.

Documentation now explains presentation discovery and generation. A shipped-PEX
audit confirms that the viewer is included, but authoring instructions and Python
helpers remain repository tooling. Interactive recording does not generate the
metadata automatically. The owner reports successfully borrowing the recorder
for another project on 0.3.0 by cloning source ad hoc; that is evidence of reuse,
not shipped authoring support. A consolidated handoff to project-management
contains the gaps, reusable pieces and proposed installation-only acceptance.
No portable authoring toolkit is claimed or implemented by this change.

Latest validation: 41 focused cases passed; types passed over 350 files and
conventions reported zero breaches. Unit gate: 3309 passed, 3 failed, 1 skipped,
187 deselected, 1 xfailed, 1 xpassed. CLI smoke, PEX packaging/smoke, docs contract,
console types and 474 console tests passed. Integration: 149 passed, 12 skipped,
3 failed initially; the socket-length case passed when rerun with shorter scratch,
leaving two failures. All five remaining unit/integration failures reproduce on
untouched release-0.3.1; maintenance received the reproduction details. This is
not a passing full gate. The subsequent presentation-only change passed all 39
existing producer tests and the documentation contract. See the workstream status
for exact failure IDs and scope.

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
