# Workstream Current Status: GitHub Authentication

Mnemonic: `github-auth`

Start date: 2026-11-16

State: paused after successful host relaunch preflight; recorded E2E preparation is next.

Definition read: WORKFLOW.md@89de30622697, WORKFLOW-LOCAL.md@d92bdcbb0a01

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

A clean checkout at `/home/devcapsule/worktrees/github-auth` preserves the previous
checkout, its maintenance records commit, and its independent website gitlink.
The branch starts at fetched canonical main: no synchronization is required now.
No open bug is owned by this newly registered workstream. Mail and intake are empty.
The new feature belongs here, not in the maintenance release.

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

Owner chose on 2026-11-16 to exit this capsule, relaunch the same checkout from
the physical host with the new local PEX and github-ssh enabled, then resume Codex.
This supersedes the proposed SSH-to-host harness adaptation. The resumed-session
preflight below verified the broker and executable bytes. Next, write and execute
the recorded E2E scenario using a fresh project and explicit github-ssh authorization.
Observe the Git checkout independently and retain WebM/screenshots/action evidence.
Recursive proxy inheritance is still unproved; do not report success until observed.
The 19 reproduced full-gate failures and formal PR delivery remain open separately.

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

## Host relaunch handoff

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

## Open Threads

- Host relaunch and authenticated proxy preflight passed. The next task is the
  fresh-project recorded E2E; recursive inheritance and recording remain unproved.
  Full-gate environment and owner-operated GitHub PR delivery remain open.
- Engineering choices: initial transport must account for Linux/rootless Docker
  permissions; Docker Desktop cannot bind ordinary host Unix sockets.
- Physical-host relaunch is observed working; Docker Desktop transport remains deferred.
- GitHub CLI is absent at the policy-prescribed path. PR creation/merging remains
  owner-operated under WORKFLOW-LOCAL.md; prepare reviewed commits and compare links.
- Reviewer worktree removed at pause; pushed `ws-github-auth/ssh-proxy-review`
  preserves its commit. Review corrections are not yet merged into implementation.
- Unimplemented review proposals and exact baseline failure IDs are in the assessment.
- Deliberately not preserved: scratch logs/venvs, credentials or console decision tokens in Git.

## Workstream document index

- [Review brief](evidence/review-brief.md)
- [Review follow-up 1](evidence/round-1.md)
- [Intake](intake/README.md)
- [Intake decisions](intake-dispositions.md)

- [Review assessment](evidence/review-assessment.md)
- [Prepared PR delivery](evidence/delivery.md)
