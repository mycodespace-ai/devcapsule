# Release 0.3.1: Scope, Driver And Cut

Date: 2026-11-07
Decision: product owner, in the maintenance session, once the repository's
move to the `mycodespace-ai` organization and the website's links were done.
Status: accepted; the cut and the work are with `maintenance`.

## Decision

1. **Cut now.** The release branch `release-0.3.1` is cut from `main` at
   `31e8fec71f2901f5e2e9893d35a6481215471ba9`, the merge of PR #7, the
   first commit of `main` in the organization that carries every merged
   pull request. The first commit on the branch sets the version to
   `0.3.1`; `main` reopens at `0.3.2.dev0` by a pull request at the cut
   (`WORKFLOW-LOCAL.md`, *Version Scheme*, rule 4).
2. **Driver: `maintenance`**, as for 0.2.14, 0.2.15 and 0.3.0.
3. **A minor release, not a patch.** The owner's words: "we have plenty
   for a minor release: we have the mac platform ability and we have some
   of the wrap functionality". The headline: DevCapsule runs on an Apple
   Silicon Mac, built from source, with capsules native on `linux-arm64` on
   a published arm64 base; and `project wrap` brings someone else's
   repository into a project.
4. **In scope: what `main` carries at the cut**, listed in
   [the release overview](../../releases/v0.3.1/README.md). The remaining
   wrapped-projects slices are not pulled in by the cut; a slice that lands
   on `main` during the cycle reaches the release only by the owner's
   direction, as in 0.3.0.
5. **Left to the owner, named in the overview, not decided by the cut:**
   whether 0.3.1 publishes a macOS or an arm64 executable, since the
   candidate workflow builds the Linux x86-64 executable alone and PR #338
   left publication to the owner; the home of the compatibility feed on
   the website's domain, which the maintenance status of 2026-11-05 says
   needs a ruling before the first candidate; the agent and IDE freshness
   upgrade, whose attempt is a slice of the cycle.
6. **Stopping points where the owner is consulted:** before each candidate
   tag; before the final tag. Scope changes go by this record's reopen
   rule: a new dated ruling under *Decision*, the old one kept.

## Why

The macOS port and the arm64 capsules are a platform ability DevCapsule did
not have, and `wrap` is a new command with its own manifest table. Either
is more than a patch carries. Both are on `main`, gated and documented, and
the repository's move is complete, so a candidate of what exists is worth
validating now, as the 0.3.0 cut reasoned. Main's work and the release's
stabilization run concurrently under the runbook.
