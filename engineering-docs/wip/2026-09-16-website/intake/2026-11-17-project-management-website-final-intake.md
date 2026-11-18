# Finish the documentation version-check fix

From: project-management
Date: 2026-11-17

The owner chose A: after 0.3.1, verify the existing release-documentation version declaration works and align the producer and website contract wording. Fix remaining discrepancies, then close the task. Do not redesign the checker or add a 0.3.1 gate.

Source: owner console answer at 2026-11-17T01:17:38Z.

## Original Intake

# The content contract check fails on a release branch

Date: 2026-10-18
From: maintenance, driving release 0.3.0
To: project-management, owner of the content–website contract

## What is handed over

A gap in [the content–website contract, version 1](../../specifications/product/content-website-contract.md),
section 4.2, found by the first gate on `release-0.3.0`. The website's
check, which `nox -s build` runs with the checkout as the content
directory, treats that checkout as `main` and requires the `devel` entry's
source to declare a development version. On a release branch the source
declares the release version, as the version scheme requires from the
branch's first commit, so the gate fails on every release branch with:

```text
Content contract 1 violated: version devel (source main): the source declares
release version 0.3.0; devel needs a development version, or source-version: "0.3.0"
```

The runbook's obligation that the release branch's `docs/` passes the
website's build check before the final tag cannot be met without a rule
for this case.

## What maintenance did

On `release-0.3.0` the manifest's `devel` entry carries
`source-version: "0.3.0"`, the form the check itself names, with a comment
that the line is release-branch metadata and is not carried to `main`,
where the source declares a development version. The contract says the
field's only intended use is the 0.2.12 case, so this is a judgment where
the contract is silent, recorded in the maintenance status file.

## Why it belongs to project-management

The contract is owned there, and the durable rule is a product choice:
either the check learns what a release branch is (the content directory
declaring a release version is checked as that version's source, not as
`main`), or the contract names a manifest form for release branches, or
the `source-version` line becomes the documented practice. The check lives
in the website repository at the pinned consumer revision, so the fix may
need `website` as well.

## What accepting it would mean

Decide the rule and record it in the contract; direct the check change if
one is chosen. Until then, every release branch under contract 1 carries
the line maintenance added, and each merge to `main` leaves it out.

## Evidence

Gate log `/opt/devcapsule-gate/2026-10-18-release-0.3.0-build-1.log` in
the maintenance capsule; `website/scripts/contract.mjs`,
`checkDeclaredVersion`, at the pinned revision; the 0.3.0 release overview
under `engineering-docs/releases/v0.3.0/`.
