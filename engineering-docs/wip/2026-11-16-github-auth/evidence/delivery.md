# Prepared delivery

No PR has been opened. WORKFLOW-LOCAL.md, GitHub Integration rules 4–6,
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

Validation: combined local candidate passed 75 focused tests, type checking and
convention checks; source/PEX authenticated read-only GitHub probe passed; local
Git clone/fetch/push, smoke/PEX/docs and 458 console tests passed. Full gate remains
blocked by 19 failures also reproduced on unchanged main. Physical-host launch
acceptance is outstanding. See the workstream review assessment for exact limits.

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
4. Fetch that merged branch, run required validation and physical-host acceptance:
   authorize `github-ssh` once, launch with the rebuilt outside PEX, and exercise
   GitHub reads plus a push to an explicitly chosen disposable repository.
5. The owner merges the implementation PR into main; fetch and verify main's tree
   before recording integration. No release or installation has been performed.
