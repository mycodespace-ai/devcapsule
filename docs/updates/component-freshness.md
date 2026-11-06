---
description: What an update check can and cannot establish, which vendor feeds DevCapsule reads, and how the maintained status fallback works.
aliases:
  - /docs/guides/component-freshness/
weight: 3
updated: 2026-10-30
---
# How DevCapsule checks component freshness

In {{tag}}, DevCapsule checks upstream vendor metadata for supported catalog
components and falls back to a maintained compatibility feed when a vendor
endpoint fails or changes format.

## What an update check establishes

`devcapsule project versions check` keeps six facts distinct instead of rolling
them into one badge:

| Fact | What it tells you |
|---|---|
| Available version | A vendor endpoint advertises a release for your platform. |
| Support or withdrawal | The upstream source explicitly marks a version supported, deprecated, or unlisted. |
| Security notice | The distribution channel carries an explicit security notice; version age alone never fabricates one. |
| DevCapsule validation | Whether the embedded resolution matrix has verified that exact combination. A vendor release does not provide that evidence. |
| Local successful use | Whether an ordinary session on this checkout exited with status `0` using that exact version set. |
| Observation age | When the check last ran and when it last succeeded. A network failure leaves older observations stamped with their original time. |

A newer upstream version does not make your pinned version broken or unsafe,
and `"no update reported"` does not certify that software is free of
vulnerabilities—DevCapsule does not query an external CVE database. Read the
text beside each status label: `available` is not a security endorsement, and
`unknown` can appear when upstream support status is not published even though
a newer version was found.

## Where the signals come from

Each discovery adapter reads public vendor metadata rather than downloading
installers:

| Component | Upstream metadata read | What it covers and its limits |
|---|---|---|
| PyCharm | [JetBrains release JSON](https://data.services.jetbrains.com/products/releases?code=PY&latest=true&type=release) | Latest release version, download URL, and SHA-256 link; carries no general support window or security feed. |
| IntelliJ IDEA | [JetBrains release JSON](https://data.services.jetbrains.com/products/releases?code=IIU&latest=true&type=release) | Latest release version and platform download/checksum links; no general support window or security feed. |
| Rider | [JetBrains release JSON](https://data.services.jetbrains.com/products/releases?code=RD&latest=true&type=release) | Latest release version and platform download/checksum links; no general support window or security feed. |
| Eclipse | [Eclipse package index](https://www.eclipse.org/downloads/packages/) | Latest stable Java package for the platform; availability does not establish installed-version support. |
| VSCodium | [GitHub latest-release JSON](https://api.github.com/repos/VSCodium/vscodium/releases/latest) | Latest stable, non-draft release containing the platform archive. |
| Visual Studio Code | [Microsoft stable update JSON](https://update.code.visualstudio.com/api/update/linux-x64/stable/latest) | Latest stable `tar.gz` archive URL and SHA-256 checksum for the platform. |
| Codex | [npm package metadata](https://registry.npmjs.org/@openai%2fcodex) | `latest` dist-tag, exact versions, and npm deprecation strings. Unlisting means absent from npm, not that an already cached copy stops working. |
| Claude Code | [Anthropic latest pointer](https://downloads.claude.ai/claude-code-releases/latest) and release `manifest.json` | Current `latest` release channel and platform artifact checksums (not the separate `stable` channel). |
| Antigravity CLI | [Platform updater manifest](https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json) | Current version and download metadata for the platform. |
| PostgreSQL client | [PostgreSQL version JSON](https://www.postgresql.org/versions.json) | Latest upstream minor version and major-version end-of-life dates. |
| .NET SDK | [Microsoft release index](https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json) | Latest stable SDK from active or maintenance channels; selection needs a reviewed lock update. |
| Playwright | [PyPI package metadata](https://pypi.org/pypi/playwright/json) | Latest release with a non-yanked wheel; selection needs matching wheel and browser pins. |

PostgreSQL client comes from the base image, whose lock records only the major
version. Because the lock cannot tell which Ubuntu package revision or security
backport is inside the base, the check reports major-version support dates
without inventing minor-version upgrade prompts.

Today, **Codex** supports end-to-end preview, preparation, and local selection
through `devcapsule project versions`. The remaining adapters report upstream
availability and notices; there is no `"upgrade everything"` command.

## Running a check

From your checkout on the host:

```sh
devcapsule project versions show
devcapsule project versions check
```

`versions show` is completely offline and also works inside a capsule, where it
separates the running container's software from the host's next-launch
selection. `versions check` runs on the host and queries feeds for components
in your selected lock. It saves observations without changing that selection.
Interactive `devcapsule project run` refreshes the check after a day, or when
the selected version set changes. Pass `--no-update-check` to skip the live
check for one launch while keeping cached critical notices active. Non-interactive launches never poll
upstream feeds.

To try a newer Codex version on one checkout, follow
[Try a component upgrade and recover](component-upgrades.md#preview-then-choose).
When an upstream channel carries a critical security or deprecation notice,
interactive `project run` asks how you want to proceed rather than swapping
tools behind your back.

## Maintained status fallback when a vendor check fails

Vendor release endpoints change from time to time without warning. When an
adapter hits an HTTP error, timeout, or unexpected payload shape, the launcher
fetches DevCapsule's versioned fallback feed and links to the
[maintained component status page](https://github.com/mycodespace-ai/devcapsule/tree/component-status):

- Matching happens locally against the adapter ID, launcher version, and
  platform. DevCapsule sends no project metadata or installed component list.
- A matching maintainer diagnosis can point to a newer DevCapsule release that
  fixes the adapter, or link to an open issue and workaround.
- Updating the `devcapsule` launcher fixes the check; it never alters your
  project lock or upgrades components on its own.
- If no current diagnosis matches, status stays `unknown` with the timestamp of
  the last good check. Transient network errors never block an offline launch.

The feed is read from the DevCapsule website,
`https://devcapsule.mycodespace.ai/status/compatibility-v1.json`. Three sources
answer in turn, and the report says which one did:

1. The published feed, fetched once per check with an eight-second timeout
   and a one-megabyte bound. A successful fetch is kept in your cache home,
   `~/.cache/devcapsule/compatibility-v1.json` by default, and shared by every
   project on the machine.
2. The cached feed, when the fetch fails. Like the published one it is valid
   for three days from its generation.
3. The feed built into the launcher at release time, when nothing is cached.
   It is a snapshot of the maintainers' diagnoses as of the build; each applies
   within its own review window, and the report names it as built in.

The launcher starts and the check completes whichever of the three answers,
or none. To read a different publication, for example a test site, set
`DEVCAPSULE_STATUS_URL` for every check, or pass `--status-url` to one
`devcapsule project versions check`.

## Current service limits before V1

A scheduled GitHub Action probes the adapters once a day and publishes fresh
observations alongside maintainer-reviewed diagnoses on the `component-status`
branch. Feed timestamps and diagnosis review windows expire independently—a
republished feed does not extend an unreviewed diagnosis, and expired or
malformed feed data never triggers an upgrade prompt.

Before V1, this status feed is best-effort rather than an externally monitored
service:

| Area | Shipped in {{tag}} | Planned for V1 |
|---|---|---|
| Observation freshness | Daily probe; published feed expires after 72 hours. | Fresh observation for every supported component within 48 hours. |
| Upstream probe failure | Recorded as inconclusive with history preserved. | Bounded retries, maintainer alerting on sustained failure, and published guidance. |
| Feed publication or scheduler failure | Readers can see stale timestamps; no external watchdog yet. | Independent external monitoring and verified maintainer alert delivery. |
