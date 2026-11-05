---
description: Accept vendor download channels and DevCapsule base images once for your configuration home, or manage per-checkout software approvals.
weight: 7
updated: 2026-10-30
---
# Vendor software and trust

Some software inside a capsule—such as Visual Studio Code, Claude Code, and the
Antigravity CLI—is downloaded directly from its vendor under that vendor's
terms rather than redistributed by DevCapsule. DevCapsule's own base images
arrive from its published repository, content-addressed by the SHA-256 digest
pinned in the lock.

When a launch lacks matching consent, DevCapsule asks whether your active
[configuration home](home.md) trusts that **channel**. The prompt names the
vendor, product, download origins, integrity check, and license terms URL.
Accepting a channel covers current and future pinned versions from that vendor
across every project launched from that home, as long as the origins and terms
stay within what you accepted.

## At launch

When a checkout has not yet consented to the published base channel, an
interactive `project run` asks:

```text
Trust DevCapsule to supply the base images from docker.io/mycodespaceai/devcapsule-base, https://devcapsule.mycodespace.ai, verified by the SHA-256 digest the launcher pins. This covers every version and every project launched from this DevCapsule home, `<path>`. Anyone who uses this home uses this acceptance. Changed terms or a different channel require another decision.
  A launcher you downloaded already carries these digests; this makes the trust explicit. You trust the mycodespace-ai/devcapsule GitHub account and the mycodespaceai Docker Hub account.
Accept for this DevCapsule home? [y/N]:
```

Answering **y** stages channel trust with the rest of your launch answers and
saves them once review and plan validation succeed. Answering **N** (or running
without an interactive terminal) stops the launch with exit status `3` and
prints the exact CLI command to accept later. Existing per-checkout consents
continue to work without becoming home-wide trust—for example, `project init
--ide` can record base consent for that checkout alone.

For `antigravity-cli`, artifacts download from shared Google Cloud Storage
(`https://storage.googleapis.com`) rather than a product-dedicated domain; the
trust prompt notes that trust applies to the named deployment and its
publishing credentials because the lock's URL alone does not prove Google owns
it.

## From the command line

```bash
devcapsule home trust list
devcapsule project config trust list
devcapsule home trust accept devcapsule-base
devcapsule home trust withdraw devcapsule-base
devcapsule project run --trust devcapsule-base
```

- `project config trust list` (and `--json`, `schema-version: 1`) inspects a
  project checkout, prints the trust record path (`settings.toml`), and shows
  each channel used by that checkout's selected software (`devcapsule-base`,
  `vscode`, `claude-code`, `antigravity-cli`) alongside any previously accepted
  channels. If a channel was accepted under different origins or terms, it
  appears as not covered alongside what was previously accepted.
- `home trust list` prints every channel accepted in the active home without
  needing a project directory.
- `home trust accept CHANNEL` prints the channel statement and terms before
  prompting `[y/N]` (pass `--yes` in scripts), using the launcher's embedded
  component pins.
- `project run --trust CHANNEL` accepts a channel from the checkout's selected
  lock and records it in `settings.toml` once launch review succeeds, even
  without `--save`.
- `home trust withdraw CHANNEL` removes the home-wide acceptance from
  `[trust.channels]` in `settings.toml` (any separate per-checkout consent
  still applies to that checkout until forgotten or denied).

Adding a vendor capability with `project config add` adds its channel to
`project config trust list` whenever vendor download consent applies. Codex is
installed from npm tarballs pinned in the lock and requires no separate vendor
channel prompt.

## Acceptance scope

Channel trust binds a vendor, allowed HTTPS/registry origins, an integrity
method, and a terms URL, while every artifact download is still verified
against the SHA-256 checksum pinned in the lock. A new origin or changed terms
URL requires a fresh acceptance. Re-accepting adds origins to the accepted set
only when the vendor, terms URL, and integrity method remain unchanged.
Otherwise, the new acceptance replaces the previous entry.

Because channel trust lives in the home's `settings.toml`, anyone launching
from that home shares its accepted channels. A single checkout can still block
a vendor download explicitly—for example, `devcapsule project config authorize
claude-code-download false` overrides home trust with a denial on that
checkout.

Channel trust grants no host access, selects no base override, and adds no
project capability; those choices stay with their own commands.

## Per-checkout approvals and departures

An image outside DevCapsule's published base repository, a [locally built base
image](local-base.md), or vendor software approved for a single checkout
instead of the whole home uses per-checkout authorization:

```bash
devcapsule project config authorize base-image default
devcapsule project config authorize claude-code-download true
devcapsule project config approve
```

`authorize base-image default` consents to the exact base digest currently
pinned in the checkout's lock. It does not accept a channel for the whole home.
After a lock update changes software authorized per checkout, `project config
approve` lists pending version approvals. With no names or `--all`, it exits
with status `1` when approvals remain, or `0` when none remain.

Use `project config approve claude-code-download` or `project config approve
--all` to record approvals. The command refuses when other required decisions
also need attention. Matching home channel trust covers version upgrades
without a separate approval; see [Component upgrades](../updates/component-upgrades.md).
