# Design: What DevCapsule Promises About Pinned Components When Upstream Withdraws A File

Status: tabled by the owner on 2026-11-08; the owner's position below is
the standing direction, the mechanisms proposed here are not adopted.

Date: 2026-11-07; owner's position 2026-11-08

## Owner's position, 2026-11-08

The owner tabled the design as a fundamentally hard problem on which they
have ideas of their own, and set the position the product works toward:

- DevCapsule does its very best to help adopters run identical bytes when
  they want that and have the resources for it, such as space in Docker or
  other repositories.
- DevCapsule also helps adopters keep their projects running in up-to-date,
  security-patched development environments.
- When it can do neither, it does not fail silently: it tells the adopter
  and offers options.

The repin of libsoup for 0.3.1 (PR #10) stands on its own. The rest of this
note is the first cut as written before the ruling, kept for the reopening.

Author: Claude Code (Claude Fable 5.1) for `maintenance`, at the owner's
request after the Eclipse libsoup bug of 2026-11-07.

Related: D-0007 (the resolution matrix as accumulated verified
combinations), D-0011 (vendor trust once per configuration home),
R-UPGRADE-001 (component version sets), the bug record
`engineering-docs/bugs/devcapsule/2026-11-07-eclipse-amd64-libsoup-urls-return-404.md`.

## What happened

A project that requires Eclipse on Linux x86-64 could not start on a
machine with an empty component cache. Two packages of Eclipse's WebKitGTK
closure were pinned by URL and SHA-256 to build `3.4.4-5ubuntu0.8` of
libsoup. Ubuntu shipped a security update on 2026-10-08 and, as its archive
always does, removed the previous build. The pinned URLs answered 404 for a
month before anyone noticed, because every machine of ours held the files
in its cache. The 0.3.0 executable is affected and cannot be repaired; 0.3.1
repins. The next security update to any package in the closure repeats the
failure.

A launch that fails because a third party cleaned its shelf is a broken
contract with the adopter. This note proposes what the contract should say
instead, and what the product does to keep it.

## The promise as the documentation makes it today

No page promises "identical bytes". The promise is made through the lock:

- *Taking a project to another machine*: the committed lock carries "exact
  component versions and SHA-256 digests"; a clone gets the same
  environment.
- *Vendor software and trust*: "every artifact download is still verified
  against the SHA-256 checksum pinned in the lock"; a changed integrity
  method requires a fresh acceptance.
- *Component upgrades* and *Component freshness*: upgrades are explicit,
  `versions preview` then `versions select`; "the base image and other
  components stay pinned as they are"; the matrix flag states whether
  "that exact combination" was verified; recovery archives allow rollback.
- R-UPGRADE-001: "exact pinning and integrity through the acquisition
  engine"; "stale/unavailable guidance cannot become a current upgrade".
- The contributor README: "locks exact versions and SHA-256 checksums,
  never a moving installer. Updates require a reviewed catalog pin."
- Public wording everywhere: "reproducible", not "identical".

All of it is right about what the launcher verifies. None of it says what
happens when the pinned file is gone, and the launcher's answer today is to
fail.

## The reality the promise has to fit

Pinned files come from three kinds of place, and they behave differently.

1. **Vendors who keep every published artifact.** npm, GitHub releases,
   JetBrains' CDN, Microsoft's VS Code update service, Anthropic's and
   Google's release buckets. A pinned URL stays valid for years. A
   withdrawal is rare and deliberate, usually a security pull, and is the
   case D-0007 already calls retirement.
2. **Distribution archives that keep one build per series.** Ubuntu's
   archive and its ports mirror. A pinned URL is valid until the next
   stable or security update of that package, typically weeks to months.
   Every Eclipse closure package is in this class. So is anything we may
   later take from Debian, Fedora or Alpine.
3. **Files we publish ourselves.** The base images on Docker Hub, the
   launcher on GitHub releases. We decide how long they stay.

We can promise exact bytes forever only in class 3, and only for as many
releases as we have the storage and the will to keep. In class 1 the
promise holds in practice but is the vendor's to break. In class 2 the
promise is false within months, by the archive's design, and the product
has to say so and behave accordingly.

## The proposed contract

Three sentences the documentation can carry, and the product can keep.

1. **What we pin, we verify.** Every download is checked against the exact
   checksum in the lock, as today. A file that fails the check is refused.
   This does not change.
2. **What we pin, we watch.** DevCapsule notices when a pinned file is no
   longer served and tells the adopter before the failure, or at worst at
   the failure, with the repair in hand. A release is not accepted while
   any of its pinned files is missing from its origin.
3. **What we cannot keep, we help you keep.** The component cache is the
   adopter's archive of the exact bytes they accepted. It can live on
   storage they control and be shared across their machines; what the
   current lock references is never deleted without asking.

And one sentence about what the product never does: it never substitutes a
file silently. A pin changes only in the lock, by an explicit step the
adopter took or accepted, with the previous set kept for rollback.

## How the product keeps it

### At acquisition: detect, explain, offer the repair

When a pinned download answers 404 or 410, the launcher stops treating it
as a network error. It reports, in one message: the component, the package,
the pinned build, the origin, and whether the origin serves a replacement.
For class 2 origins it can answer the last question itself by reading the
archive's signed index for the same package name, which is how the arm64
closure's pins and the 0.3.1 repin were made. The message ends with the
command that repairs the lock.

The repair is the existing upgrade path, widened: `versions preview` learns
to preview "the current build of a withdrawn package" and `versions select`
applies it. The lock changes explicitly, with the new URL, version and
checksum from the signed index; the recovery archive of the previous set is
kept as today; the matrix flag reports the combination as unvalidated unless
the matrix already knows the new build, exactly as `--unvalidated` does for
Codex. Trust is unchanged: the origin is the same archive, the integrity
method is still a checksum, so no new acceptance is needed under D-0011.

An interactive launch may offer the repair in place and continue. A
non-interactive or offline launch fails with the message and the command,
as consent prompts fail today. Nothing rewrites a committed file without a
yes.

### Before the failure: the watcher

Two mechanisms, one for us and one for the adopter.

- **A release gate.** Candidate validation fetches the headers of every
  pinned URL in the embedded matrix, on every platform the matrix knows,
  and fails the candidate if any is gone. Cheap, a few hundred HEAD
  requests, and it would have caught libsoup on 2026-10-08 at the next
  candidate instead of a month later. A scheduled run of the same check
  against the latest final release gives us the signal between releases.
- **The compatibility feed.** The feed the website serves (0.3.1 carries
  the reader) gains a per-pin status: served, withdrawn, replaced-by. The
  launcher's freshness check, which already compares pinned versions with
  upstream, reads it and shows "withdrawn upstream, repair available" in
  `versions show` and in the launch prompt, before the adopter hits an
  empty cache. For class 2 origins the feed is written by the scheduled
  check above; for class 1 it is written by hand when a vendor pulls a
  release.

### The adopter's archive

The cache already stores every acquired file under its checksum. What is
missing is the documented promise and two behaviors:

- A configurable cache location in the home's `settings.toml`, so a team
  can point it at a shared or backed-up volume, and a documented statement
  that this is their archive of the accepted bytes.
- A retention rule the adopter can read: files referenced by any lock of
  any registered checkout are kept; `cleanup` lists the rest and asks.

Nothing here hosts a copy on our side. If the owner wants a mirror of the
class 2 files for the current release only, it is a separate decision with
a storage line; this note does not propose it.

### What changes in the documentation

- *Vendor software and trust* gains a short section, "When a pinned file
  is no longer served", with the three sentences and the repair command.
- *Component upgrades* gains the withdrawn-package case beside the Codex
  example, and names the preview and select flow as the repair.
- *Component freshness* documents the new status values.
- *Taking a project to another machine* adds one sentence: a lock from an
  older launcher can name files an archive has since replaced; the
  launcher says so and offers the repair.
- *Cleanup and uninstall* documents the cache as the adopter's archive and
  the retention rule.
- The contributor README's "never a moving installer" stays true and
  gains "pins advance by reviewed repin or by the adopter's explicit
  repair; never by substitution at launch".
- R-UPGRADE-001 gains the withdrawn-file case as a trigger of the upgrade
  loop, so "unavailable guidance cannot become a current upgrade" is read
  as it was meant: the product does not upgrade on its own.

## What this costs

The gate is a script and a workflow step, small. The feed status and the
freshness display ride on the 0.3.1 feed work. The repair flow is the real
slice: the acquisition engine has to classify the failure, read a signed
APT index on the adopter's machine, and hand a candidate pin to the
existing preview and select commands, with tests that construct their own
index files. One cycle of work for one engineer, in Python, reviewable.

## Decisions the owner is asked to make

1. Adopt the three-sentence contract and the "never silently" rule as the
   product's position, or amend them.
2. Order of the slices: the gate first (prevents the next occurrence),
   then the feed status, then the repair flow; or the repair flow first
   because it is the adopter-facing fix.
3. Whether the interactive launch may apply the repair in place after a
   yes, or must always stop and let the adopter run the command.
4. Whether any of this lands in 0.3.1 beyond the repin, or all of it is
   0.3.2 work.
