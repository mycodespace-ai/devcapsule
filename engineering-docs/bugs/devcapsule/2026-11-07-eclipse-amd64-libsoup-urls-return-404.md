---
status: fixed
severity: major
target: 0.3.1
owner: maintenance
opened: 2026-11-07
requirements: []
---

# Eclipse cannot be acquired from scratch on amd64: the libsoup package URLs return 404

## Symptom and expected behavior

A project that requires Eclipse on a Linux x86-64 host whose component
cache does not hold the Eclipse closure cannot acquire it: two packages of
the pinned WebKitGTK dependency closure, `libsoup-3.0-0` and
`libsoup-3.0-common` at build `3.4.4-5ubuntu0.8`, are no longer served by
the Ubuntu archive. Every other pinned package in the closure is still
served. Expected: a pinned closure acquires in full on a clean machine for
as long as the release is supported, or the pin advances with the archive.

## Environment and evidence

Noted by PR #338 on 2026-11-04 as found along the way, for `maintenance`:
Ubuntu removed `libsoup` `3.4.4-5ubuntu0.8` on 2026-10-08. Confirmed on
2026-11-07 at the 0.3.1 cut, `main` at `31e8fec7`:

- `devcapsule/components/eclipse_native_pin.py` pins the amd64 closure
  with the two URLs
  `https://archive.ubuntu.com/ubuntu/pool/main/libs/libsoup3/libsoup-3.0-0_3.4.4-5ubuntu0.8_amd64.deb`
  and `.../libsoup-3.0-common_3.4.4-5ubuntu0.8_all.deb`; both answer 404.
- The archive's pool listing holds one amd64 build of `libsoup-3.0-0`,
  `3.4.4-5ubuntu0.10`, and serves it and its `common` package with 200.
- The arm64 closure in `devcapsule/components/linux_arm64_pins.py` already
  pins `3.4.4-5ubuntu0.10` from `ports.ubuntu.com`, served with 200.

The 0.3.0 release executable is affected the same way: its pins are the
same build. An adopter whose cache holds the closure from an earlier
acquisition is not affected until the cache is emptied.

## Cause

The closure pins exact archive URLs, and the Ubuntu archive keeps one
build of a package per series: a security or stable update replaces the
previous build's files. Nothing in the project watches the archive, so a
replaced build is found when an acquisition fails.

## Disposition

Fixed on `release-0.3.1` on 2026-11-07, the first slice of the 0.3.1 cycle
(branch `ws-maintenance/eclipse-libsoup-repin`): both packages repinned at
`3.4.4-5ubuntu0.10`, the hashes read from the signed `noble-updates` index
(InRelease verified with `gpgv` against the archive signing key; the index
hash matched; the downloaded files matched), the architecture-independent
`common` package's hash equal to the arm64 closure's pin. The embedded
matrix advanced to `embedded-32` and the golden locks were regenerated, as
every pin advance does. `main` receives the fix with the next pre-candidate
merge of the release branch (*Release Fixes And Main*, merge). Closed when
a fresh amd64 Eclipse acquisition with an empty cache succeeds on a
downloaded candidate; the 0.3.0 executable stays affected.

The original plan: repin the two packages at `3.4.4-5ubuntu0.10` with the
served files' SHA-256, as the arm64 closure does; verify by a fresh amd64
Eclipse acquisition on a downloaded candidate with an empty cache. The
same repin applies to `main`. Whether the launcher should fall back to the
archive's current build when a pinned one is gone is a design question for
the owner, not part of this fix: the pin is the consent the adopter gave.
