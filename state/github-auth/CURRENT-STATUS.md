# Workstream Current Status: GitHub Authentication

Mnemonic: `github-auth`

Start date: 2026-11-16

State: paused; merged-build recording and live six-step presentation passed; inherited gate failures and owner-operated PR delivery remain.

Definition read: WORKFLOW.md@781c9e39df58, WORKFLOW-LOCAL.md@94a29cb6eedb

Branch association: `ws-github-auth/ssh-proxy`, from canonical `upstream/main` at `1942f396`.

Integration target: `main`

Delivery method: pull request with Pair Review; the human merges.

Requirements: R-PRODUCT-002 (explicit host boundaries), R-PRODUCT-003 (durable memory).

## Goal and accepted scope

GitHub Git operations inside a capsule use the host's existing SSH authentication
through a proxy owned by the outside launcher. Private keys remain on the host.
The owner selected the new `github-auth` workstream and Git over SSH first on
2026-11-16 through the console decision. HTTPS and `gh` API authentication are
outside this slice. Review partner: Antigravity, `gemini-4-hydrogen-high`.

## Current state

At the owner's request, the active checkout is now
`/workspace/301e4208ef81-ChatGPT_Codex`, on `ws-github-auth/ssh-proxy`.
The earlier worktree is detached at `9e5bf073` and retains the built PEX and
previous evidence. The website submodule's prior commit remains on its
`presentations` branch; the active checkout uses the tracked submodule revision.
Canonical main is unchanged after fetch, so synchronization is unnecessary for
this recording-only task. No open bug is owned by github-auth; mail and intake
are empty. The owner requested a new recorded E2E against the merged build.

## Implementation and evidence

The initial Linux/WSL implementation includes the GitHub-only request validator,
launcher-owned Unix socket broker, capsule Git adapter, optional `github-ssh`
authorization, launch mount/environment wiring and user documentation. It does not
copy private keys or forward the host agent. The socket grants all GitHub Git
repositories available to the host identity. Docker Desktop transport is deferred
and explicitly refused. GitHub aliases, Git LFS authentication, SSH signing and
HTTPS/API credentials are not implemented in this slice.

Focused validation: 42 tests pass, including real Git clone/fetch/push through a
fixture SSH process, binary streaming, refusal, deadline, shutdown and authorized
Docker arguments. Initial mypy over the touched import graph passed (157 files).
The full build gate reached the unit suite: 20 failed, 2917 passed, 1 skipped,
14 xfailed and 7 xpassed. A selected rerun on an archive of unchanged
`upstream/main` reproduced 19 of those failures; the added authorization exposed
one exact-vocabulary legacy test. That file was refurbished into its proper
module mirror, preserving its contracts in 20 passing cases. The original gate
attempt failed in pytest setup because
`/opt` is read-only and `/opt/devcapsule-gate` does not exist. Scratch now uses
`/home/devcapsule/.cache/devcapsule-gate/github-auth` per the local rule allowing
another directory with space. No Docker containers or real credential files changed.

Additional checks: CLI smoke, PEX build and smoke, and documentation contract
pass. The console gate identified a mirrored authorization-table omission; after
alignment, all 458 console tests pass. A read-only live `git ls-remote` through
both the source adapter and the built PEX returned GitHub HEAD `1942f396`.
That used the current capsule's already-installed SSH credentials on the broker
side; it is not physical-host/capsule acceptance evidence.

The implementation and review branches are pushed to canonical upstream.
Gemini Hydrogen completed local round 1 at `388f62a3`. Its corrections remain
on the separate review branch for PR delivery. A temporary combined merge passed
75 focused cases, type checking and conventions (zero breaches), then was aborted.
Git connectivity integrity and authenticated fetch/push checks pass. The original
checkout remains untouched. Review evidence and prepared PR text are indexed below.

## Planned next step

Resolve the inherited gate failures with maintenance, then complete the pending
review PR and implementation PR through the owner-operated GitHub workflow.
The full release merge and requested combined validation are complete. Review
corrections remain separate and require validation after integration.

## Rootless Docker fix propagation

The owner's first host relaunch failed with an unwritable PEX cache and permission
denied on `/etc/devcapsule/home/settings.toml`. Fetched canonical `release-0.3.1`
and identified `a1a54eba3098eb3c80fd78ef3e483d1bb5314466`, merged in PR #38 and
recorded as owner-verified on the target host by `8bd56eb3`. Neither current main
nor this feature branch included it. Main has no new commits to synchronize.

Applied that fix's deliverable/test patch, without release version changes or
another workstream's records, under the owner's explicit propagation request and
WORKFLOW-LOCAL.md's release-fix propagation exception. The branch predates the
release's CapsuleUser refactor: adapted its `command` correction to the existing
`foreground_command`, and its `owner_changes` correction to `prepare_filesystem`.
Rootless launches use container 0:0 (the host user's mapped identity), map the
Docker socket group and home accordingly, and avoid redundant gosu/chown under
dropped capabilities. Rootful behavior is preserved. The available Docker daemon
reports `name=rootless`; no container was launched for this propagation.

Checks so far: 151 focused tests passed, then all 12 GitHub proxy integration
cases passed after extending socket-grant coverage to both daemon modes. The
full gate's type check passed over 340 files; conventions found zero breaches.
New pure identity tests and filesystem preparation tests cover the adaptation.
Full gate: 19 failed, 2942 passed, 1 skipped, 78 deselected, 14 xfailed,
7 xpassed. All 19 failure IDs match the previously reproduced mainline/environment
baseline exactly; no new failure IDs. Packaging/smoke is run separately because
the full gate stops at pytest. The separate PEX build and executable smoke passed (14 seconds). The imported
rootless detector reports True against the available daemon. Fix commit: `d6fd93e0`.
The rebuilt artifact identity follows below. The owner subsequently relaunched
successfully; the resumed-session observations are recorded below.
Mainline integration and the separate Gemini review branch remain pending.

## Earlier host relaunch handoff (superseded artifact)

The owner explicitly chose a development-build self-hosting experiment. The normal
host launcher is not replaced and remains the recovery route; no saved project
configuration is changed by the run-once command. Reuse the same checkout and its
existing persistent state. The original checkout still has only its pre-existing
website gitlink modification. Main remains unchanged; synchronization can wait.

Build: `.venv/bin/python -m nox -s pex` passed, including shell syntax, packaging
and executable smoke. Built from clean `d6fd93e0ba6c18915ace45b9dfef2881068d7b39` with the rootless Docker fix.
The local PEX reports `v0.3.2.dev0-local-linux-x86_64` with revision `unknown` by
local-build policy; the clean Git revision and checksum here identify its inputs
and bytes independently. It contains the committed implementation, including the
node-registry and console-table fixes. Review corrections at `388f62a3` remain on
the separate review branch and are not included; their PR merge is still pending.

SHA-256: `33c3c7bc7fe6ff6772eedee06424c95afcf4aebddca20ab99f9a31a7c103d35b`.

Capsule artifact: `/home/devcapsule/worktrees/github-auth/devcapsule-src/dist/devcapsule-local.pex`.
Host artifact (from Docker mount inspection):
`/home/costin/.local/share/devcapsule/projects/by-path/fe326e03c822-devcapsule/home/worktrees/github-auth/devcapsule-src/dist/devcapsule-local.pex`.
Checksum and build metadata are saved beside it, outside Git.

Retry the same command with the replacement file. After exiting Codex and stopping
the current capsule normally, run on the host:

```sh
cd /opt/costin3/myProjects/devcapsule
/home/costin/.local/share/devcapsule/projects/by-path/fe326e03c822-devcapsule/home/worktrees/github-auth/devcapsule-src/dist/devcapsule-local.pex project run \
  --no-update-check \
  --authorize github-ssh true \
  --authorize network host \
  --authorize docker-daemon host-socket
```

Keep that outside launcher running throughout the resumed session: it owns the
broker. Host OpenSSH must already authenticate noninteractively to GitHub and
trust its host key. A key without a passphrase needs no SSH agent.

Inside the relaunched capsule:

```sh
cd /workspace/301e4208ef81-ChatGPT_Codex
codex resume 01a1e25b-6b76-72d0-b311-614d6adca912
```

The session file exists under ~/.codex/sessions and Docker inspection shows
~/.codex backed by the persistent Codex component home. Installed CLI help
supports explicit session IDs. Conversation/history is resumable; process state
and outstanding tool sessions are not. The feature checkout remains
`/home/devcapsule/worktrees/github-auth`, on `ws-github-auth/ssh-proxy`.

Resume checks before E2E: read this record, fetch upstream, inspect live workflow
state, claim the slice, check the PEX checksum, verify
`DEVCAPSULE_GITHUB_SOCKET=/run/devcapsule-github.sock` and that it is a socket,
then perform an authenticated GitHub read through the adapter. Fresh E2E homes
must have no copied key; the recording harness must authorize github-ssh for its
fresh project. Do not use this current capsule's manually installed key as proof
of the proxy. No E2E container was launched during handoff preparation.

## Resumed-session readiness, 2026-11-16

The owner resumed inside the rebuilt capsule. Running `/opt/devcapsule/bin/devcapsule.pex`
and the saved local PEX both match the SHA-256 above. Runtime identity is 0:0 and
Docker reports `name=rootless`. The canonical proxy socket exists, and Git's SSH
command points to the shipped `github-ssh` adapter.

A read-only `git ls-remote git@github.com:mycodespace-ai/devcapsule.git HEAD`
returned `1942f396dd11ffabb64784eb7279f283181e32dd`. Repeating it from a fresh empty
HOME with system/global Git configuration disabled and the adapter explicitly
selected also passed. Pointing that invocation at a missing socket failed with
exit 128. This demonstrates proxy authentication independently of the manually
installed capsule key; it does not yet prove a new child capsule's inheritance.

Docker mount inspection resolves the inherited socket to the outside launcher's
host socket, and resolves both the persistent E2E workspace root and PEX directory
to host-backed paths. Docker access, Git, pytest and nox are available. No new
container was started for this preflight. Canonical main was fetched: this branch
is ten commits ahead and zero behind, so no synchronization is needed. Mail and
intake remain empty.

Recording preparation remains: author the GitHub showcase scenario and its Markdown
procedure, explicitly grant github-ssh in its fresh project, and prepare Playwright.
This capsule has neither local Playwright nor FFmpeg nor `/opt/playwright`; the
existing recorder supports Chromium/FFmpeg in a child with `browser-automation`.
The scenario must request that component, verify a real SSH Git checkout from
outside the recorded UI, retain video/screenshots/action evidence, and clean up.
No nested E2E or recording has run yet. No additional host credentials or restart
are indicated by the preflight. The outside launcher must stay running.

## Recorded E2E acceptance, 2026-11-16

One fresh VSCodium capsule, with browser-automation and explicit github-ssh
consent, was launched by the saved PEX from this capsule. The outer physical-host
launcher remained alive. Child and parent Docker inspection showed the same host
broker source, mounted read-only at the canonical socket. The child had no SSH
files or agent; its delivered runtime checksum matched the tested PEX.

Through the actual recorded terminal, Git cloned the canonical repository over
SSH. Independent Git inspection of the host-backed checkout confirmed expected
HEAD `1942f396dd11ffabb64784eb7279f283181e32dd`, the SSH origin, a clean tree and
the README. A missing-socket read failed with exit 128. Ordinary proxy access
succeeded again afterward. This proves recursive proxy inheritance on this
rootless Linux host. No GitHub write was made.

Evidence preserved at `devcapsule-src/tests/e2e/evidence/github-ssh-proxy-pre-merge/`.
The 38.17-second WebM, full desktop capture, poster, action trace, `run.json`,
`verification.json` and `result.json` are retained outside Git. The test-owned
container, fresh workspace and checkout records are independently confirmed gone.
The controller gained optional per-scenario surface needs/consents and a bounded
interactive phase; the product PEX was not changed. All 62 existing recorder tests
passed. See the procedure for the on-screen empty-directory check correction and
a minor final command/output overlap, both retained in the original recording.

Full gate for the recorder change: 19 failed, 2942 passed, 1 skipped, 78 deselected,
14 xfailed and 7 xpassed. All 19 failure IDs exactly match the recorded baseline.
Types passed over 340 files; the corrected convention check found zero breaches. The initial attempt
used the stale default origin/main comparison and stopped on three unrelated
convention differences. The corrected run used DEVCAPSULE_DIFF_BASE=upstream/main. Its log is retained at
`~/.cache/devcapsule-gate/github-auth-showcase-build-upstream.log`.

## Full release merge, 2026-11-16

The owner authorized merging release-0.3.1 into this published feature branch.
Use a merge, preserving both histories. Canonical main remains unchanged and needs
no separate synchronization. The fetched release tip is `10e7fda3` (PR #40).
Resolve the overlap with the earlier port by taking the release's CapsuleUser and
filesystem implementation; retain the feature's extra mixed-ID/rootless coverage
on those APIs, combine authorization coverage and review history, and keep the
feature branch's development version. No release ref or other checkout is edited.

The imported workflow now keeps scenario recordings outside build output. Copied
the completed first recording to `devcapsule-src/tests/e2e/evidence/github-ssh-proxy-pre-merge/`
before rebuilding so the evidence survives a clean build. The imported host-input
and test rules also apply to this combined tree. The combined unit gate reports 3309 passed, 3 failed, 1 skipped, 187 deselected,
1 xfailed and 1 xpassed. The three failure IDs are a subset of the previous 19:
unmountable staging and the two recursive dry-run cases (host Docker gid 0).
No new failure ID. Types and conventions passed. All 41 focused identity,
filesystem, authorization and proxy integration cases passed. The first focused
invocation used the repository root instead of devcapsule-src and triggered the
new repository-input guard on an editable-install metadata path; correcting the
working directory followed the declared validation setup. No guard was disabled.
Merge commit: `7fc77f24df45135770160c35f193c9abb78cd9c0`, with parents
`ab1e30f9` and `10e7fda3`. The complete fetched release tip is an ancestor, not a
patch port. Packaging and executable smoke passed, as did CLI smoke, documentation
contracts, console types and all 474 console tests. Integration initially returned
149 passed, 12 skipped and 3 failed; shortening the scratch path fixed the Unix
socket path-length failure (targeted rerun: 1 passed). Two failures remain.

All five remaining failures (three unit, two integration) reproduce on an untouched
archive of release `10e7fda3`, with its own separately built PEX where required:

- `test_host_daemon.py::test_unmountable_staging_fails_loudly`: persistent-home
  scratch is mountable, contrary to the fixture expectation.
- `test_recursive_orchestrator.py::test_public_dry_run_is_unique_redacted_and_cleans_owned_staging`
  and `test_contained_display_dry_run_forwards_no_host_x11`: Docker socket gid 0
  is rejected by the recursive host positive-ID check.
- `test_print_command_cli.py::test_print_command_names_a_base_image_that_is_not_here_and_pulls_nothing`:
  rootless detection adds Docker info to the fixture's expected image-inspect calls.
- `test_runtime_entrypoint_cli.py::test_filesystem_applies_distinct_user_and_group_ids_to_new_directories`:
  the rootless/dropped-capability environment cannot chown gid 1 despite uid 0.

The gate is not green. Sent these reproductions to maintenance as
`2026-11-16-release-merge-validation.md` on coordination (`815e42e7`). Logs remain
under `~/.cache/devcapsule-gate/github-auth-release-*`. No tests were disabled.

### Rebuilt merged artifact and acceptance

Built with `.venv/bin/python -m nox -s pex` from clean merge `7fc77f24`.
The artifact path and host path in the earlier handoff remain valid; its bytes
and adjacent checksum/build metadata are now replaced. SHA-256:
`af7fa02ca2c2737f3a1678226341312682b71cfdd37eb892f29a42ad5c31b78c`.
Review corrections at `388f62a3` are still excluded.

A new VSCodium capsule launched with that merged PEX passed real GitHub SSH clone
acceptance: expected HEAD `1942f396`, SSH origin, clean tree, no child SSH files or
agent, canonical read-only host broker mount, and exact delivered PEX checksum.
The IDE window and console token guard passed. A missing-socket control failed
with exit 128. The test container, workspace and checkout records were removed.
Evidence and executable reproduction script are retained outside Git at
`devcapsule-src/tests/e2e/evidence/github-ssh-proxy-release-merge/20261116T100132Z/`.
This repeat saved machine-readable evidence; the earlier showcase video remains
preserved separately and depicts the earlier PEX, not the merged build.

The outside launcher/broker is still the earlier `33c3c7bc` PEX. Its GitHub broker
and transport sources are unchanged by the merge. This run validates the merged
child launcher/runtime against that live broker; a physical-host restart with the
merged PEX has not been performed. Canonical main is unchanged, so separate main
synchronization remains unnecessary for this slice.

## New merged-build recording, 2026-11-16

The owner requested a new recording after selecting the feature branch in the
primary checkout. The running capsule's PEX now matches the merged artifact:
`af7fa02ca2c2737f3a1678226341312682b71cfdd37eb892f29a42ad5c31b78c`, built from
`7fc77f24`. This supersedes the earlier outer-broker restart limitation.

One fresh VSCodium capsule with browser-automation and explicit github-ssh consent
passed the recorded journey. The real terminal showed zero SSH files, no agent,
and a connected proxy, cloned the canonical repository, and displayed its SSH
origin and commit. The missing-socket read failed with exit 128; the normal proxy
read then succeeded. Each network command finished before the next command.
Independent Docker and Git checks verified both capsule runtimes' checksum, the
same read-only host socket, no child SSH mount/files/agent, expected GitHub HEAD
`1942f396`, clean tree, and README. Container, workspace and checkout records were
independently confirmed removed. No GitHub write was made.

New evidence in this primary checkout:
`devcapsule-src/tests/e2e/evidence/github-ssh-proxy/20261116T103152Z-af7fa02c/`.
The movie is `scenario-video.webm`: 545 frames at 12 fps, 45.42 seconds,
2,116,032 bytes; SHA-256
`57457f07f8b40fcbfa3e3d2dff4a99584829f616b68b6c6e4552587dec6ba5ee`.
Full capture, poster, screenshots, action trace, executable reproduction scripts,
run provenance, verification and cleanup results are retained alongside it.
Host directory:
`/opt/costin3/myProjects/devcapsule/devcapsule-src/tests/e2e/evidence/github-ssh-proxy/20261116T103152Z-af7fa02c/`.
Evidence is outside build output and ignored by Git. Prior recordings remain in
the earlier detached worktree; no prior evidence was overwritten.

This task changed records only and used the already validated merged PEX; the
full gate was not rerun. Its inherited failures and pending review corrections
remain as documented above. The new E2E and encoding passed on their first run.
The initial script-extraction command used the wrong working-directory-relative
path and was corrected before any E2E launch; no failed product run was discarded.

## Live console presentation, 2026-11-16

The owner explicitly authorized investigating presentation behavior in this
checkout and documenting the cross-scope findings while adding the SSH showcase.
The workstream selection remains github-auth. No main synchronization is needed:
this follows the same fetched main and the same validated recording.

The live console discovers `presentation.json` beneath its mounted project and
serves named media through `/api/project/raw`. It does not generate metadata.
Scripted replay generates the document when given a script and numbered actions;
interactive serve/ctl does not. The earlier recording was interactive. The
example URL under website/_site names website output relative to the project;
there is no single required presentation assets directory. Outside worktrees and
symbolic links are not discovery paths. These distinctions and source locations
are now explicit in PRESENTATIONS.md and the scenario-recording guide.

Added a six-step Markdown script and a producer using the shared presentation
module. The chapter boundaries come from the recorded controller responses and
are bound to the existing movie checksum. The producer writes presentation.json
beside run `20261116T103152Z-af7fa02c`; no recording was rerun or altered. It is
visible immediately on the current console's Presentations page, with route:
`/presentations/devcapsule-src/tests/e2e/evidence/github-ssh-proxy/20261116T103152Z-af7fa02c#overview`.
This is local evidence served from the project mount, not a website publication.

Validation: authenticated with the supplied session token and then a cookie,
confirmed discovery, inspected the overview, and played all six steps in real
Chromium. Each screenshot loaded, its caption appeared, and playback stopped at
the selected boundary. Byte-range media requests returned 206 with matching bytes;
no browser errors occurred. The 39 existing presentation-producer tests and the
docs-contract check passed. Browser screenshots and structured results are under
the run's `presentation-check/`. No runtime source or PEX changed; the previously
recorded full-gate limitations still apply.

Sent the broader usability finding to capsule-webconsole as
`2026-11-16-interactive-presentations.md`. Automatic presentations for interactive
runs remain a product/design follow-up, not an implemented feature of this slice.
The tracked script, timing input and producer make this retained deck reproducible;
media and generated metadata remain ignored evidence. Tokens and cookies are not
in Git, the presentation document, or browser screenshots.

## Cross-project presentation portability audit, 2026-11-16

The owner asked whether agents in unrelated projects receive the same Markdown
instructions and Python support with little setup. Inspected the actual merged
PEX and its nested console bundle, package inclusion, CLI help, bootstrap assets
and browser-automation component. The viewer's HTML/JS/CSS are shipped and accept
presentation folders under any project's mount. The authoring guide, contract,
scenario scripts, recorder and metadata producer are not in that PEX. None of the
16 packaged bootstrap documents/templates refers to presentation.json or the
recorder. Browser automation supplies the browser tools, not the authoring kit.
The CLI has no presentation authoring command. This is a packaging/discoverability
gap; successful playback in this source checkout did not establish adopter setup.

PRESENTATIONS.md now carries a support matrix. The scenario guide includes a
realistic agent brief and explicitly requires provisioned source tooling today.
The generator itself uses Python's standard library; the recorder also depends
on the repository's IDE smoke infrastructure and creates disposable test projects.
The retained SSH producer is run-specific, not a portable recording framework.
No new commands, workflow refresh, packaged assets or runtime code were introduced.

Sent the cross-workstream delivery gap to project-management as
`2026-11-16-presentation-authoring-portability.md`, with suggested acceptance:
using only an installed candidate and an unrelated project, an agent discovers
the guide/templates, records the project's journey, generates validated metadata,
and exposes a presentation with working step playback without cloning DevCapsule.
Ownership and packaging/interface choices remain for that workstream and the owner.
This audit does not claim future capsules already have that authoring support.
Structured artifact observations are in evidence/portability-audit.json.

## Consolidated handoff and branch delivery, 2026-11-16

The owner reports that an agent in a separate project running DevCapsule 0.3.0
successfully reused this repository's recorder through an ad-hoc clone. Adding
presentations and the remaining setup was too much work. This is owner-reported
reuse evidence, not an independently repeated test or proof of shipped 0.3.0
presentation support.

At the owner's request, sent the complete findings and this new evidence to
project-management as `2026-11-16-github-auth-presentation-authoring-handoff.md`
on coordination at `b61ff973196a`. The self-contained item covers source locations,
discovery, scripted versus interactive generation, reusable Python, installed-PEX
omissions, the tested SSH presentation, durable documentation and proposed
installation-only acceptance in an unrelated project. It supplements the earlier
messages without selecting a toolkit interface, release or implementation owner.

Refreshed the implementation PR draft around the final merged build, latest movie,
presentation and portability findings. All authored changes are committed and
pushed on the implementation branch; raw media remains intentionally ignored.
Canonical main was fetched and is still fully included, so no synchronization
was needed. No source or runtime behavior changed in this handoff. The existing
full-gate limitations remain; no new E2E or full gate was run for this record update.
The prescribed GitHub CLI remains absent. Under WORKFLOW-LOCAL.md's GitHub rules
4–5, the owner must edit the remote PR after resolving the gate prerequisites.
A push updates any existing PR's commits, not its description or attachments;
remote PR existence remains unverified.

## Open Threads

- Host relaunch, recursive inheritance and recorded fresh-project E2E passed.
  Full-gate environment and owner-operated GitHub PR delivery remain open.
- Engineering choices: initial transport must account for Linux/rootless Docker
  permissions; Docker Desktop cannot bind ordinary host Unix sockets.
- Physical-host relaunch is observed working; Docker Desktop transport remains deferred.
- PR description draft now includes the successful recorded E2E and current
  validation limits. No PR was created or edited by this agent; remote PR existence
  remains unverified. The recording is retained locally, not attached to GitHub.
- GitHub CLI is absent at the policy-prescribed path. PR creation/merging remains
  owner-operated under WORKFLOW-LOCAL.md; prepare reviewed commits and compare links.
- Reviewer worktree removed at pause; pushed `ws-github-auth/ssh-proxy-review`
  preserves its commit. Review corrections are not yet merged into implementation.
- Unimplemented review proposals and exact baseline failure IDs are in the assessment.
- Deliberately not preserved: scratch logs/venvs, credentials or console decision tokens in Git.

## Workstream document index

- [Recorded E2E procedure and console presentation](evidence/showcase.md)
- [Presentation producer for the retained run](evidence/present-showcase.py)
- [Recorded chapter boundaries](evidence/presentation-timing.json)
- [Installed-artifact portability audit](evidence/portability-audit.json)
- [SSH proxy scenario script](../../../devcapsule-src/tests/e2e/scripts/github-ssh-proxy.md)
- [Review brief](evidence/review-brief.md)
- [Review follow-up 1](evidence/round-1.md)
- [Intake](intake/README.md)
- [Intake decisions](intake-dispositions.md)

- [Review assessment](evidence/review-assessment.md)
- [Prepared PR delivery](evidence/delivery.md)
