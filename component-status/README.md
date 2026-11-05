# Component discovery compatibility service

Requirements: R-UPGRADE-001. Owner-approved extension, 2026-09-21.

DevCapsule maintains vendor adapters; vendors have not promised to preserve all
the interfaces those adapters read. The compatibility service helps installed
clients explain failures without confusing unavailable metadata with healthy or
unhealthy installed software.

Start with [How DevCapsule checks component freshness](../docs/guides/component-freshness.md)
for vendor sources, user decisions and the difference between available releases,
support, security and observation age. This document is the operator runbook.

## Publication and stable addresses

The **Component update status** GitHub Action runs daily, on relevant mainline
changes, and on manual dispatch from `main`. It publishes two files in one
fast-forward commit on the project-owned `component-status` branch:

- [Human status page](https://github.com/mycodespace-ai/devcapsule/tree/component-status):
  GitHub renders that branch's generated `README.md`.
- [Compatibility feed v1](https://raw.githubusercontent.com/mycodespace-ai/devcapsule/component-status/compatibility-v1.json).

Launchers from 0.3.1 on read the feed from the website, at
`https://devcapsule.mycodespace.ai/status/compatibility-v1.json`; earlier
launchers read the branch of the repository they were built from. A launcher
that cannot fetch the feed uses the copy it last fetched, then the snapshot
`scripts/build-pex.sh` built into it from `policy-v1.json`, and reports
which one answered; see [component freshness](../docs/updates/component-freshness.md).

These addresses become live after the first successful mainline workflow run.
Publication needs the repository's automatically issued `GITHUB_TOKEN` with
`contents: write`; repository rules must allow that workflow to create/advance
this branch. It does not deploy GitHub Pages or replace either existing website.
No personal token, external server, release tag or change to `main` is needed.
A denied publication fails visibly and leaves the previous feed in place.

The feed expires after three days. Clients reject stale guidance, and readers
can inspect the page's expiry timestamp; neither behavior alerts an operator.
GitHub may delay scheduled runs or disable schedules in inactive public repositories;
operators should watch the workflow and its artifact. See GitHub's
[schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
and [workflow token permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).

There is currently no independent monitor or verified owner notification route.
A component probe failure is published as inconclusive and does **not** fail the
action. A publication failure fails the action, but this alone does not ensure
owner email; a job that never starts cannot report failure. The intended V1
48-hour freshness objective, persistent-failure alerting and independent detection
are accepted follow-up in
[R-UPGRADE-002](../engineering-docs/requirements/product/r-upgrade-002-status-operational-reliability.md).
The current 72-hour expiry does not satisfy that operational objective.

Until that follow-up is implemented, the owner must inspect action runs and the
public resources manually. After merging this workflow to main, verify its first
run and both public URLs; no separate action installation is needed. If the run
does not start, inspect GitHub Actions settings and dispatch it through the UI.
For a failed publication, inspect permissions/rules for the generated branch,
repair through the UI, rerun and confirm the public timestamps and source revision.
An uploaded artifact alone does not prove that publication succeeded.

Keep the branch and v1 endpoint for all clients that use them. Additive fields
are allowed. Do not change existing field meanings or add incompatible status
values under format 1. A future incompatible schema gets a new filename, while
the publisher continues to emit v1. Publication preserves unrelated files on
the branch so adding v2 does not erase v1. Never use this branch for authored
source or workstream records.

## Observations and diagnoses

`policy-v1.json` is the authored input. Its probe baselines exercise the shipped
discovery adapters for all six curated components on the supported Linux amd64
platform. Baselines are probe inputs, not assertions about a user's installed
version. The backend records result, adapter ID, baseline, candidates, last
successful probe and consecutive failures. One failure leaves other observations
publishable. Failed checks never automatically create or renew a diagnosis.

The page explicitly limits probe success to that adapter, baseline, platform
and runner. New adapter success does not certify older adapters. When replacing
an adapter, retain its old identity in affected diagnoses and bump
`ComponentDefinition.discovery_adapter_id()` in the replacement. This identity
is independent of the CLI release, including different development builds of
the same release. Keep retired probe implementations if ongoing direct probing
of them is needed; the initial job probes the current implementation only.

Maintainers investigate failures and edit `advisories` through ordinary review.
The initial policy has no diagnoses: all live sources responded during local
validation. Do not publish hypothetical issues or unreleased fixes as facts.

First distinguish a failed vendor response from a client/network or platform
problem. Record the symptom and time, compare the public probe observation and
retry as appropriate. HTTP success with an unexpected shape is still an
inconclusive check. Do not diagnose a permanent interface change from one timeout.

For a confirmed incident:

1. Record the actual GitHub issue and its actionable workaround discussion.
2. Identify affected component, exact adapter IDs, CLI versions and platforms.
3. Use `known-issue` while unresolved. Once a final CLI release containing the
   fix is actually available, use `cli-update-required` and its exact version
   in `fixed_in`. Verify affected selectors exclude unaffected installations.
4. Set `reviewed_at` and `expires_at` in UTC, at most 90 days apart. These are
   human-maintained review times; scheduled publication never renews them.
5. Merge and inspect the workflow's generated artifact/status page. Renew,
   correct or remove diagnoses after review; preserve guidance for older
   affected clients even when current probes pass.

Each advisory has this shape (illustrative only; issue 123 is a placeholder):

```json
{
  "id": "postgresql-endpoint-change",
  "component": "postgresql-client",
  "adapters": ["postgresql-client-v1"],
  "cli_versions": ["0.2.14"],
  "platforms": ["linux-amd64"],
  "status": "known-issue",
  "message": "The upstream version feed changed; see the issue for workarounds.",
  "issue_url": "https://github.com/mycodespace-ai/devcapsule/issues/123",
  "reviewed_at": "2026-09-21T00:00:00Z",
  "expires_at": "2026-10-21T00:00:00Z"
}
```

Adapter IDs always match exactly. `cli_versions` and `platforms` allow `"*"`
explicitly; otherwise each entry matches the exact reported version/platform.
There is no inferred semver range: development/RC versions are distinct.
`cli-update-required` additionally requires `fixed_in: "X.Y.Z"`. Only links to
issues in this repository are accepted; release links are constructed locally.
Messages are bounded single-line text. Unsupported schemas, malformed fields,
duplicate IDs, invalid times or URLs make the feed unusable for guidance.

The generated envelope contains `format: 1`, UTC `generated_at`/`expires_at`,
`source_revision`, `cli_version`, `advisories` and `observations`. Clients consume
only the advisory contract. Observations never authorize upgrades or supply
replacement download URLs, commands, code or configuration.

## Client behavior

On a vendor exception, HTTP error or unrecognized metadata shape, a check fetches
the one fixed feed URL, at most once for all failed components. It sends no
checkout path, configuration, credentials or component/version query parameters.
Responses are size/time bounded. Matching uses the installed adapter ID, CLI
version and selected platform locally. Unknown diagnoses leave status unknown.

Valid metadata is cached beside checkout check state. Network or parse failure
can use that cache, clearly labelled, within its original validity period.
Stale/future feed times and expired diagnoses cannot yield a current upgrade
recommendation. A failed check retains applicable notices and the previous
successful check timestamp/result. It changes no software selection and never
blocks ordinary offline launch. Noninteractive launch and `--no-update-check`
make no automatic vendor or fallback-service requests.

Clients shipped before this fallback existed cannot discover it retroactively;
they need one normal CLI upgrade. Restoring update discovery does not itself
upgrade a component. In particular PostgreSQL remains base-supplied, and its
major-only lock cannot establish which minor version or distro backports are
installed.

## Local review

From `devcapsule-src`, generate a preview using metadata only:

```sh
python -m devcapsule.component_status_publisher \
  --policy ../component-status/policy-v1.json \
  --output /tmp/devcapsule-component-status-preview \
  --revision local-preview
```

The publisher uses the standard library and source package; it installs no
vendor software. `--previous PATH` carries forward observation history. Run
`tests/test_component_status.py`, the distribution/version-set suites, and the
repository `nox -s build` gate. The workflow's actual Git publication and a
released client's fetch of the public endpoint require post-merge acceptance.
