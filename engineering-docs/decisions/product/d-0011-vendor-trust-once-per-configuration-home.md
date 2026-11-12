---
id: D-0011
title: Vendor Terms And Trust Are Given Once Per Configuration Home, Bound To A Verified Channel
status: accepted
date-proposed: 2026-10-01
date-decided: 2026-10-01
decided-by: Costin Cozianu
requirements: [R-UPGRADE-001, R-COMPAT-001, R-PRODUCT-001]
supersedes: the per-checkout acquisition authorization of D-0010 and D-0001, identified below
superseded-by:
---

# D-0011: Vendor Terms And Trust Are Given Once Per Configuration Home, Bound To A Verified Channel

## Context

DevCapsule does not distribute the commercial or per-user-licensed software
it integrates. It facilitates the user's own download from the vendor:
`AcquisitionContract` puts an explicit authorization in front of the
download and DevCapsule never redistributes the result. That is the one
obligation with legal weight. Around it the product had grown four
different questions under the single word "consent": run this base image;
download this vendor product; prepare a version set DevCapsule has not
validated; give the capsule host network or display. The questions the
user can answer were defaulted, the ones they cannot were asked repeatedly,
and the answers were stored in the checkout record, so a vendor's terms were
accepted again for every checkout of every project. The owner's test: asked
to consent to the latest Claude Code upgrade, what is a user supposed to
do, inspect Anthropic's code? A prompt the user cannot answer is not
consent. Users learn to type yes.

Problem statement, candidates and the code facts are in project-management's
consent design issue of 2026-10-01
(`engineering-docs/wip/2026-08-09-project-management/2026-10-01-design-consent-and-vendor-trust.md`).
This record settles the three of its five questions the owner ruled on
today; the other two remain open there.

## Options Considered

### Option A: keep per-checkout acquisition authorization

Cost: the vendor's terms are re-accepted per checkout, per project and
after some version changes, with no new information for the user each
time. The prompt has already lost its meaning.

### Option B: signed software as the trust basis

Cost: none of the integrated vendors signs the artifacts DevCapsule
acquires in a way the launcher could verify today. Waiting for signatures
means keeping option A indefinitely.

### Option C: one home-level statement per vendor product, provenance tested by channel

Cost: a new record under the launcher's config root and a rule for what
re-opens it; older clients keep their own behaviour. The trust statement is
only as honest as the channel definition, which must be stated to the user.

## Decision

1. **Vendor terms are accepted once per vendor product per DevCapsule home, in its `settings.toml`.** Not per
   project, not per checkout, not per version. The acceptance is re-asked
   only when the terms are known to have changed, which today means the
   component's `terms_url` changed.
2. **Trust is bound to a verified channel, not to signatures.** A channel is
   a vendor, an origin and an integrity method: `registry.npmjs.org` with
   the registry's SHA-512 integrity for npm packages; the vendor origin
   named by the component's discovery with the resolution matrix's pinned
   SHA-256 for the others. The user approves a channel once per DevCapsule home.
   Anything resolved through that channel with integrity verified is
   approved without a prompt. Anything that leaves the channel asks, and
   asks loudly: a local file, a mirror, an origin change, an integrity
   method weaker than the one approved. That last prompt must never become
   routine.
3. **The record is per DevCapsule home, in its `settings.toml`**, in the owner's words: "I trust this vendor, and I agree for
   DevCapsule to download this software, in all its versions and
   incarnations, on my behalf." One statement covers the terms and the
   provenance for that vendor product. The record is the user's, never the
   project's: a manifest can require a vendor product; it cannot carry the
   user's acceptance of it.

## Rationale

The statement "it came from the vendor" does not need signatures to be
honest. It needs a definition the code can verify, and the code already
verifies more than the prompts admit: the npm channel refuses any artifact
that is not an HTTPS `registry.npmjs.org` URL with a SHA-512 integrity, and
every other acquisition is pinned to a vendor origin and digest. That is
the same basis every package manager without signatures rests on. The limit
is to be said in the prompt in one sentence: trusting `@anthropic-ai` on
`registry.npmjs.org` is trusting the registry operator and Anthropic's
publishing credentials, not Anthropic's source.

Asking once per configuration home matches where the obligation sits. The user,
not the project, accepts the vendor's terms; a second project launched from the same
home adds nothing to that acceptance.

## Consequences

- The per-checkout `acquisition` authorization nodes of D-0001 and D-0010
  are superseded as the place consent lives. Older clients keep reading the
  checkout record. A newer client that finds a configuration home acceptance stops
  asking, and nothing migrates, so R-COMPAT-001 holds without an exception.
- Inside a capsule the configuration home record is on the host. It rides the
  existing read-only configuration mount, which ties this to the in-capsule
  project-command fix targeted at 0.2.16 (bug record of 2026-09-24).
- The Antigravity channel's origin is a bare Cloud Run hostname, not a
  vendor-owned domain. "I trust this vendor" cannot be stated honestly for
  it; that channel stays a per-version question until the origin is the
  vendor's domain, and the prompt says why.
- Where a vendor publishes npm provenance attestations, the channel's
  integrity method may be upgraded to the attested build and the user's
  approval carries over unchanged. Whether any integrated CLI publishes
  them is to be verified, not assumed.
- R-UPGRADE-001's "acquisition consent ... remain enforced" stays true and
  gains a precise meaning: enforced per vendor product per home through the
  settings record, with the channel as the provenance test. The
  requirement's refinement and the fate of the remaining questions, what
  stays a question at all (host access as the visible decision, the
  recommended base asking nothing, upgrades as scheduling plus disclosure),
  are open with the owner in the design issue.
- Implementation belongs to `component-upgrades`, which owns component
  wiring under the routing rule of 2026-10-01. No release carries it until
  the owner names one.

### Owner refinement, 2026-10-01: DevCapsule's own base image is a channel

Later the same day the owner ruled on the base image: the user is offered
to trust `https://devcapsule.mycodespace.ai`, a TLS-anchored domain that
names the GitHub project and the Docker Hub repository the bases are
published to. That is a channel in this record's sense. Vendor:
DevCapsule. Origin: the site, naming `github.com/ccozianu/devcapsule` and
`docker.io/mycodespaceai/devcapsule-base`. Integrity: the digest the
launcher's resolution matrix pins, so every pull is content-addressed.
Trusted once per configuration home like any vendor; a base from another
registry, or a local image the user built, is a departure from the channel
and asks.

Two facts belong in the prompt. A user who downloaded and ran the launcher
has already trusted DevCapsule, since the launcher ships the digests; the
old base-image authorization for a DevCapsule-built base was redundant,
and this statement makes the trust explicit rather than adding a check.
And what is trusted in practice is the GitHub and Docker Hub accounts
behind those names, the same shape as the registry case above.

Consequence for the website: as the channel's origin it should carry a
page listing the published base digests with their recipe tags, so the
anchor is verifiable rather than decorative. A `user-docs` or `website`
item, not a gate on this decision.

## Reopen If

A vendor begins signing the artifacts DevCapsule acquires in a verifiable
way, which would let the channel's integrity method carry the signature; a
channel compromise shows the origin-and-integrity test insufficient for a
vendor the users trust; or a vendor's terms demand per-version acceptance.


## Amendment, 2026-10-28: the caller selects the home

The configuration-home work order of 2026-10-27 changes the acceptance scope.
`DEVCAPSULE_CONFIG_HOME` names the home; its `settings.toml` holds defaults
and accepted channels. The default home remains the XDG configuration directory.
The `home trust` commands act on it without a project. The channel test and
per-checkout denials remain as decided above.
