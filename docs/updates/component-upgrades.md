---
description: Try a newer component version for one checkout, inspect the result, and roll back to a known-good set or the project lock.
aliases:
  - /docs/guides/component-upgrades/
weight: 4
updated: 2026-10-30
---
# Try a component upgrade and recover

`devcapsule project versions` lets you test a newer component version on one
checkout, keep a history of combinations that actually launched cleanly, roll
back if something breaks, or export a lock patch for the rest of the team.

Run mutating `versions` commands from your checkout in a host terminal (or pass
`devcapsule project --path /path/to/checkout versions ...`). Update discovery
covers all catalog components: PyCharm, IntelliJ IDEA, Rider, Eclipse,
VSCodium, Visual Studio Code, Codex, Claude Code, Antigravity CLI, PostgreSQL
client, .NET SDK, and Playwright. In {{tag}}, **Codex** supports local preview,
selection, and rollback through these commands; the other adapters report
upstream freshness and delivery limits. See
[How DevCapsule checks component freshness](component-freshness.md) for what
each check measures.

A **version set** is the exact platform, base image, component versions, and
recipe that form one capsule environment. The repository's platform lock
records the shared version set; a local selection belongs only to your checkout
record and stays intact until you roll back or follow the project lock again.

## Inspect from the host or inside the capsule

```sh
devcapsule project versions show
devcapsule project config show
```

Both commands are offline, write nothing, and accept `--json`. `versions show`
uses `schema-version: 1`; the current `config show` listing uses
`schema-version: 2`. Both include `context`. An older capsule without a captured
listing can return the legacy schema-1 `config show` report.

Inside a capsule, `versions show` separates the **running session's version
set** (captured when the container started) from the **host's current selection
for the next launch**. Changing versions on the host never mutates a running
container. Mutating `versions` commands run only on the host; if you invoke one
inside a capsule, it refuses and prints the exact host command with your
checkout's host path.

## Critical notices at launch

During an interactive `devcapsule project run`, the launcher checks component
channels after a day, or when the selected version set changes. If a channel publishes an explicit security or
end-of-support notice (for example, an npm deprecation notice on a Codex
release), `project run` pauses before launching:

```text
Security notice for tool 1.0.0: <vendor explanation>
Source: <distribution channel>
Last checked: <date and time>; cached metadata may be stale.
Choose upgrade (review first), later (seven days), keep (silence this notice), or stop launch [later]:
```

- `upgrade` previews the candidate's version changes, downloads, validation
  status, and rollback path, then selects it for this and subsequent launches if
  you confirm. Vendor trust or acquisition consent is still checked separately,
  and nothing widens host access.
- `later` (or pressing Enter) launches your current version and asks again in
  seven days.
- `keep` silences this notice for the current version and candidate until a new
  notice or candidate appears.
- `stop` cancels the launch.

Network failures never block an ordinary launch. Passing `--no-update-check` to
`project run` skips the live refresh while preserving cached notices.
Non-interactive launches never refresh or prompt; they print any unsilenced
critical notice and continue with the selected version set.

## Check upstream channels explicitly

```sh
devcapsule project versions show
devcapsule project versions check
```

`versions check` queries the selected components' upstream feeds immediately
and saves observations without changing your software selection. When a vendor
endpoint fails, DevCapsule checks its maintained
[component status feed](component-freshness.md#maintained-status-fallback-when-a-vendor-check-fails)
for known adapter issues or workarounds.

## Preview, then choose

For Codex, preview either a specific version or npm's `latest` tag:

```sh
devcapsule project versions preview codex latest
```

`preview` resolves the tag to an exact version and immutable artifact checksums
without downloading binaries or changing your software selection. It saves a
preview record in the home's state directory. The output shows what would
change, whether the combination is matrix-verified, and a `PREVIEW_ID` to pass
to `select`:

```sh
devcapsule project versions select PREVIEW_ID --unvalidated
```

`--unvalidated` acknowledges that the combination has not been verified by
DevCapsule's embedded matrix; it never skips platform, dependency, trust, or
checksum verification. Only Codex changes—the base image and other components
stay pinned as they are.

`select` downloads and verifies the artifacts and builds the environment image
before updating your checkout selection. Running capsules keep their existing
software, and a failed download or build leaves your previous selection active
so you can retry.

```sh
devcapsule project run
```

When an ordinary session exits with status `0` (not a `--force` IDE override),
DevCapsule records that exact version set in local history as known-good for
this checkout.

## Roll back to a known-good set

```sh
devcapsule project versions history
devcapsule project versions rollback
devcapsule project run
```

`rollback` switches back to the most recent *other* version set that completed
a clean session on this checkout, or to a specific identity copied from
`versions history`.

Recovery archives live under `version-sets/<path hash>/artifacts/sha256/` in
your [DevCapsule home's](../configuration/home.md) state directory. The default
root is `~/.local/state/devcapsule`, or `$XDG_STATE_HOME/devcapsule` when set;
a named home uses `$DEVCAPSULE_CONFIG_HOME/state`. `<path hash>` is the full
SHA-256 of the checkout's canonical absolute path, without a trailing newline.
These retained copies are separate from disposable download caches.

Offline rollback needs the base image and either the exact archives or a
matching materialized environment image. A missing base image also requires
`rollback --reacquire`. If recovery resources are missing, rollback keeps your
selection and reports the error. `--reacquire` permits exact downloads, but
withdrawn vendor artifacts might no longer be available.

Rollback switches software versions only: your source tree, host permissions,
persistent home, IDE settings, and agent sign-ins stay untouched. Keep in mind
that rolling back a binary cannot undo config-file migrations an upgraded tool
already wrote inside `~/.codex` or another state directory.

## Follow the project lock again

```sh
devcapsule project versions follow-project
devcapsule project versions follow-project --apply
```

Without flags, `follow-project` diffs your checkout-local version set against
the repository's shared platform lock. Adding `--apply` prepares the project's
version set and clears your local override.

If the shared lock introduces a vendor channel you have not yet accepted in
this home (`devcapsule home trust accept CHANNEL`), or a new version of
software you consented to per checkout (`devcapsule project config approve`),
the command tells you what is needed; `select`, `rollback`, and
`follow-project --apply` also accept `--authorize NAME true` for per-checkout
vendor acquisition consent without touching host permissions.

## Propose a proven upgrade upstream

Once a local version set has exited cleanly at least once on your checkout, you
can export a patch for `.devcapsule/` to share with your team:

```sh
devcapsule project versions propose component-upgrade.patch
git apply --check component-upgrade.patch
```

`propose` writes a new patch file (it refuses to overwrite an existing path)
and never edits the lock, commits, or opens a pull request by itself. If you
tested against a local base image override, the patch notes that the shared
project base was not the one exercised, and any unvalidated edges are marked in
the lock so reviewers see the exact provenance.

## Quiet routine update reminders

```sh
devcapsule project versions defer
devcapsule project versions dismiss
```

Routine reminders for checked candidates appear at most once every seven
days during launches, including non-interactive launches. `defer` quiets checked
candidates and critical notices for seven days. `dismiss` silences both until
a different candidate or a new or revised critical notice appears. Neither
command changes notices printed by an agent's own CLI inside the capsule.
