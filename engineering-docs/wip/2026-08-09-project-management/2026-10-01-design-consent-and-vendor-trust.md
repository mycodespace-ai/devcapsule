# Design Issue: Consent That Means Something

Date opened: 2026-10-01. Owner: `project-management` for the problem
statement; the owner expects the fix to belong to `component-upgrades`,
which owns component wiring under the routing rule of the same day.
Status: **work in progress; problems stated, candidates marked, nothing
decided.** This document records what the owner and the agent worked
through in conversation on 2026-10-01 so that it is not lost before the
owner rules. Solutions, where they appear, are candidates.

## Current disposition, 2026-10-09

The opening status and candidate discussion below are historical. The owner
subsequently ruled on consent in component-upgrades:
[D-0011](../../decisions/product/d-0011-vendor-trust-once-per-configuration-home.md),
[D-0012](../../decisions/product/d-0012-host-access-asked-only-when-recommended.md)
and [D-0013](../../decisions/product/d-0013-provenance-sidecar-for-local-records.md)
are the decision records. The owner assigned their implementation to the next
release on 2026-10-01, now 0.3.0. Project-management acknowledged that assignment
on 2026-10-09. This note does not reopen those choices or claim implementation.
Consult component-upgrades' published state for its remaining design and work.

Requirements touched: R-UPGRADE-001 (its "acquisition consent ... remain
enforced"), R-COMPAT-001 (a re-asked consent triggered by a client change is
a defect), R-PRODUCT-001.

## The Occasion

Release planning for 0.2.16 put candidate C1 on the table: the base-image
change already on `main`, which among other things re-bound base-image
consent from a digest of the whole lock to the image itself. Reading it, the
owner observed that the project has been conflating two different things,
compatibility as the resolution matrix records it and consent as the user
gives it, and that consent prompts "have been too numerous and
automatically given". The owner's test case: if the product asks "give me
your consent for the latest Claude upgrade", what is the user supposed to
do? Inspect Anthropic's code and decide the CLI does not ship spyware? A
prompt the user cannot answer is not consent. It is liability transfer, and
it trains the user to type yes: the boy who cried wolf.

## P1. One word, four questions

Today "consent" or "authorize" covers four questions with different
meanings, and the code treats them with inverted priority.

| What is asked | Code | Required? | Can the user answer it? |
|---|---|---|---|
| Run this base image | `AuthorizationDeclaration` named `base-image` | yes | Only "is this the base DevCapsule recommends"; the user has no other basis |
| Download this vendor product under its terms | `AcquisitionContract` per component: Claude Code, PyCharm, VSCodium, the agent CLIs | yes | Yes, once: "I accept this vendor's terms". Not per version, not per project |
| Prepare a version set DevCapsule has not validated | the `select-upgrade` confirmation in `_upgrade_prompt.py` | asked on upgrade | Yes: it is a risk disclosure with a real choice |
| Give the capsule host network or the host display | `network`, `host-x11` declarations, `kind = "host"` | no, defaulted | Yes, and it is the one choice with security meaning for the user's machine |

The questions the user can answer are defaulted. The ones the user cannot
answer are asked repeatedly. Answers to all of them are stored in the
checkout record (`checkout.authorization`), so a vendor's terms are accepted
again for every checkout of every project.

## P2. The legal shape, stated plainly

DevCapsule does not distribute the commercial or per-user-licensed software
it integrates. It facilitates the user's own download from the vendor:
`AcquisitionContract` exists because "acceptance travels with the download,
so DevCapsule puts this explicit authorization in front of it and never
redistributes the result". The Eclipse entry survey of 2026-09-09 recorded
the same model for the IDEs: acquired, not shipped; no DevCapsule artifact
contains IDE bytes.

So the obligation that is real, legal or near-legal, is exactly one: the
user, not DevCapsule, accepts the vendor's terms before the vendor's bytes
land on the user's machine. Everything else asked under the same word is
DevCapsule's own caution, and caution that cannot be acted on is noise.

**Candidate C-TERMS.** Vendor terms are accepted once per vendor product per
user. Not per project, not per checkout, not per version. Re-ask only when
the terms are known to have changed, which today means the `terms_url`
changes; a vendor that versions its terms at a stable URL is not detectable
and is not re-asked. The record moves from the checkout file to the user's
XDG configuration, keyed by vendor and product, carrying the terms URL and
the date. Older clients keep reading the checkout record; a newer client
that finds a user-level acceptance stops asking (R-COMPAT-001).

**Owner's preference, 2026-10-01.** A per-workstation record under
`$XDG_CONFIG_HOME/devcapsule`, beside the `projects/` checkout records the
launcher already keeps there, in which the user states: "I trust this
vendor, and I agree for DevCapsule to download this software, in all its
versions and incarnations, on my behalf." One statement covers the terms
(P2) and the provenance (P3) for that vendor product; it is given once on
the workstation and never again per project, checkout or version. What
re-opens it is a change in the terms URL or a departure from the approved
channel, never a client upgrade (R-COMPAT-001). The record is the user's,
never the project's: a manifest can require a vendor product, but it
cannot carry the user's acceptance of it.

## P3. "I trust this vendor", without signed software

The owner's proposal: let the user state "I trust this vendor; as long as
you know the component or the upgrade came from this vendor, consider it
approved." The obstacle named at once: nothing we integrate is signed.

The agent's finding: the statement does not need signatures to be honest.
It needs a definition of "came from this vendor" that matches what the code
can verify, and the code verifies more than the prompts admit.

- npm packages: the artifact must be an HTTPS URL on `registry.npmjs.org`
  and must carry the registry's SHA-512 integrity; both are enforced in
  `npm_channel.py` before anything runs.
- JetBrains, VSCodium, Claude, Antigravity, PostgreSQL: each discovery
  class pins one vendor origin, and the resolution matrix pins the exact
  URL and SHA-256 per version, verified on download.

**Candidate C-CHANNEL.** The unit of trust is a **channel**: vendor, origin,
integrity method. The user approves a channel once, per user. Anything
resolved through that channel with integrity verified is approved without
a prompt. Anything outside it asks, and asks loudly: a local file, a
mirror, an origin change, an integrity method weaker than the one approved.
That last case is what a compromise looks like, so it is the one prompt
that must never become routine.

The statement's limit, to be said in the prompt in one sentence: trusting
`@anthropic-ai` on `registry.npmjs.org` is trusting the registry operator
and Anthropic's publishing credentials, not Anthropic's source. Registry
account takeovers are a recurring supply-chain story. This is the same
basis every package manager without signatures rests on, and it is
honest.

**Known gap.** The Antigravity origin is a bare Cloud Run hostname, not a
vendor-owned domain. "I trust this vendor" cannot be stated honestly for
that channel until the origin is a domain the vendor owns; until then it
stays a per-version question or the channel is marked as such.

**Tightening later, same user statement.** npm supports provenance
attestations through Sigstore for packages that opt in. Whether any of the
agent CLIs publish them is to be verified, not assumed. Where one does,
the channel's integrity method upgrades from "registry hash" to "attested
build" and the user's approval carries over unchanged.

## P4. What stays a question, and what stops being one

**Candidate C-ASK.** Ask only when the answer is a decision the user is
competent to make and it changes what happens; remember it at the widest
safe scope.

- Vendor terms: C-TERMS, once per vendor product per user.
- Vendor provenance: C-CHANNEL, once per channel per user.
- DevCapsule's own base, recommended by the project: no consent. Ask only
  for a base DevCapsule did not build, or one selected locally.
- Upgrades: a scheduling choice, now or later or keep, plus the
  validation-gap disclosure when the matrix has not verified the
  combination. Never called consent.
- Host network and host display: a visible, per-checkout, once decision,
  because it is the one the user can judge and the one that matters to
  their machine.

The matrix's "verified combination" remains a separate fact from all of
the above. It is DevCapsule's validation, disclosed, never a thing the user
consents to.

## P5. Evidence to collect in 0.2.16, before any of this is built

Candidate C1's acceptance should count the prompts a fresh user meets from
download to a running IDE and record each with its wording. That is the
baseline this design needs and it costs the release driver nothing extra.
Recorded in the 0.2.16 proposal's C1 row.

## What this document does not decide

Whether R-UPGRADE-001's "acquisition consent remains enforced" is refined
to C-TERMS and C-CHANNEL; whether the host-access declarations become
required; where the user-level record lives; and the release that carries
any of it. Those are the owner's rulings, expected in the
`component-upgrades` workstream.
