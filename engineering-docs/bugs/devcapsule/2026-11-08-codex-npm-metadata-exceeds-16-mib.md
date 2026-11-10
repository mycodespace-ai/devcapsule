---
status: fixed
severity: major
target: 0.3.1
owner: maintenance
opened: 2026-11-08
requirements: []
---

# Codex status and version checks fail: the npm registry document exceeds the channel's 16 MiB cap

## Symptom and expected behavior

Every check of the Codex component against its distribution fails with
`Distribution check unavailable at https://registry.npmjs.org/@openai%2Fcodex:
metadata exceeds 16 MiB. Retry 'project versions check'; saved choices are
unchanged.` The retry fails the same way. Two surfaces are affected:

- The published compatibility feed reports Codex as `inconclusive`. Its
  last successful probe was on 2026-10-01 at 06:52 UTC; the feed generated
  on 2026-11-08 at 01:56 UTC counts 45 consecutive failures.
- `project versions check` in the shipped launcher reports the same error
  for Codex, so an adopter cannot learn from the launcher whether the
  pinned Codex is current, deprecated or withdrawn.

Expected: the channel answers for Codex as it does for every other
component, reporting the pinned version's status and the registry's latest
version, and the feed shows Codex `ok`.

## Environment and evidence

Confirmed on 2026-11-08 against `release-0.3.1` at `02e27f81` and `main` at
`8c5a4723`:

- `devcapsule/components/npm_channel.py`, `NpmChannel._metadata`, reads
  the registry's full package document with `urlopen`, no `Accept` header,
  and refuses a body over 16 MiB. `check()` reads from that document only
  the version list, each version's `deprecated` field and `dist-tags.latest`.
- The full document for `@openai/codex` measured 18,722,679 bytes on
  2026-11-08. The registry's abbreviated document, requested with
  `Accept: application/vnd.npm.install-v1+json`, measured 5,441,541 bytes
  and carries `versions`, per-version `deprecated` and `dist-tags`. The
  single-version document at `/latest` measured 3,515 bytes.
- The channel is Codex's only distribution channel
  (`devcapsule/components/codex.py`, `distribution_channel`). The publisher
  (`component_status_publisher.py`) and the launcher's version check
  (`version_sets.py`) both call it.
- `release-0.3.0` carries the same reader with the same cap, so the 0.3.0
  executable is affected the same way.
- Feed evidence: `compatibility-v1.json` on the organization's
  `component-status` branch, generated `2026-11-08T01:56:40Z`, source
  revision `8c5a4723`, row `codex / codex-v1`.

## Cause

The channel reads the whole package document to answer two small
questions. The document grows with every Codex release, since the registry
lists every published version with its full manifest and the package
releases often. It crossed the channel's 16 MiB cap between 2026-10-01 and
2026-10-02, and nothing in the project noticed: the feed records the
failure as `inconclusive` and keeps publishing, and no alert reads the
consecutive-failure count.

## Disposition

Filed 2026-11-08 by the owner's direction in the maintenance session:
"we cannot afford to have the connection to Codex publishing broken";
fixed for 0.3.1, on `release-0.3.1`, as a slice of the cycle, and on
`main` with the next pre-candidate merge.

Plan: `check()` asks the registry for the abbreviated document, with the
`Accept` header above, and keeps the cap; the abbreviated form carries
every field `check()` reads. `select()` already fetches single-version
documents and needs no change. If the pair prefers a bounded read, two
single-version documents, `/latest` and the pinned version, answer the
same two questions in a few kilobytes each, with a 404 on the pinned
version meaning withdrawn; the owner rules at the pull request. A unit test
in the mirror constructs the abbreviated document and asserts the report,
with no network and no patching of project modules. Verification on a
downloaded candidate: `project versions check` on a Codex project reports
the pinned version's status and the registry's latest; and the first feed
published from `main` after the merge shows Codex `ok` with the failure
count reset. The 0.3.0 executable stays affected; 0.3.1 is the remedy.

## Fix and verification

Fixed on `ws-maintenance/codex-npm-metadata` (2026-11-09):

- `NpmChannel._metadata` in `devcapsule-src/devcapsule/components/npm_channel.py`
  now sends `Accept: application/vnd.npm.install-v1+json` when fetching the
  package-wide document (`version == ""` in `check()`), while keeping full
  single-version fetches (`version != ""` in `select()`) and the 16 MiB cap
  unchanged, and declares `__all__` plus an injectable `opener` collaborator.
- Mirror Hoare-triple unit tests in
  `devcapsule-src/tests/unit/devcapsule/components/test_npm_channel.py` verify
  the outgoing `Accept` header, available/current-is-latest/withdrawn/deprecated
  classifications, the 16 MiB cap, and full single-version `select()` requests
  without network or module monkeypatching.
- Live probe on 2026-11-09 against `https://registry.npmjs.org/@openai%2Fcodex`:
  abbreviated payload measured `5,456,187` bytes (`5.20 MiB`, `5,786` versions),
  and `CodexComponent().distribution_channel().check("0.166.0", ...)` returned
  `0.166.0` `available` with candidate `0.167.0` `available` on both
  `linux-amd64` and `linux-arm64`.
- Close once verified via `project versions check` on the downloaded
  `v0.3.1-rc2` executable and once the next `component-status` publication from
  `main` reports Codex `ok`.
