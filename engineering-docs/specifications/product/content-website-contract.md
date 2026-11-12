# The Content–Website Contract, Version 1

Owner: `project-management`. Status: **accepted**, 2026-09-28, on both
sides; live at `devcapsule.mycodespace.ai` since 2026-09-28 from
DevCapsule `main` `2ec36b9` and website `6759b9d`. Promoted here from
project-management's open-work directory on 2026-09-30.

**Where the contract lives.** The authoritative text is
[`CONTRACT.md` in the website repository](https://github.com/ccozianu/devcapsule-website/blob/main/CONTRACT.md),
as its task W12 asked; it implements this document with the decisions of
section 11a and records what the consumer added or interpreted, notably the
`legacy: true` manifest field. This document is the producer's record: the
design, its reasoning and the decisions taken. Where the two disagree, the
consumer's text governs the build and the disagreement is a defect to fix
here. The producer's obligations at release time are in the release
runbook, *Documentation Is Part Of The Release*; the authored list of
versions is `docs/versions.yaml` on `main`.

Written at the owner's direction, 2026-09-28, from the problems defined in
[the documentation-currency design issue](../../wip/2026-08-09-project-management/2026-09-28-design-docs-current-at-release.md).
It extends [R-DOCS-003](../../requirements/product/r-docs-003-website-content-carries-front-matter.md),
the producer's proposed requirement, and answers the website repository's
W12, which asks for one authoritative contract there with the producer's
agreement. Nothing here is implemented on either side.

Vocabulary: **producer** is the DevCapsule repository, which authors every
word the site shows; **consumer** is the `devcapsule-website` repository,
which builds, lays out, routes and publishes. **Product documentation** is
the tree under `docs/`. A **version** is one published release of DevCapsule
whose documentation the site serves; **current** is the one of them the
site treats as canonical.

## 1. What The Contract Decides

1. Exactly one tree is versioned: `docs/`. Everything else the site publishes
   exists in one version, taken from `main`.
2. Each version's documentation is built from that version's own source ref,
   and the version number is read from that ref, not typed into pages.
3. A small set of distinguished pages, named by role, are linked from the
   home page and always resolve to the current version.
4. A reader reaches any published version from the home page in two clicks,
   and any page's other versions in one.
5. The owner's support statement for 0.x is shown where versions are listed.
6. Released versions are immutable and are built once.

## 2. Parties And Ownership

| | Producer: DevCapsule | Consumer: devcapsule-website |
|---|---|---|
| Owns | every authored page; the manifest; front matter; editorial and status decisions; the release-time obligations in the runbook | build, layouts, routing, redirects, the versions index, the switcher, banners, caching, publication machinery |
| Never contains | layouts, CSS, navigation code | a second copy of any authored Markdown |
| Changes the contract by | proposing in this document's successor, agreed with the consumer | recording the accepted version in its repository and implementing it |

The authoritative contract text lives in the consumer repository under a
version number, as W12 asks. This document is the producer's proposal for
version 1; once agreed it is referenced from R-DOCS-003 and from the
consumer's README.

## 3. Two Kinds Of Content, Decided By Location

**Versioned: `docs/`.** Every Markdown page under `docs/` is product
documentation and is built once per version from that version's source.
Nothing else in the tree is.

**Unversioned: everything else the site publishes**, always from `main`:

- `README.md`, the landing page;
- `engineering-docs/blog/`, the journal;
- `engineering-docs/releases/*/notes.md`, the release notes, if the
  release-notes artifact is adopted; the site renders them as one list.

Consequence, a migration item for the producer: pages under `docs/` that are
not product documentation leave it before the migration. Today that is the
five pages under `docs/product/` (announcements, pitch, press release) and
the Docker4PyCharm guide. They move to an unversioned location the consumer
publishes as historical material, for instance `engineering-docs/product/`
with `status: historical`, or they stop being published. Location decides
whether a page is versioned; front matter decides its status within that.

## 4. Inputs The Consumer Reads

### 4.1 The manifest, `docs/versions.yaml` on `main`

Authoritative for which versions exist, their sources, their statuses and
which is current. Shape, extending R-DOCS-003 part 2 with three fields:

```yaml
contract: 1
current: "0.2.15"
notice: >
  DevCapsule 0.x is for early adopters. We publish the documentation of every
  released version, and we ask you to run the current release: it is the one
  we fix. Whether we patch a release older than two weeks is at our
  discretion. A support policy with defined windows will come with V1.
versions:
  - version: devel
    source: main
    status: development
  - version: "0.2.15"
    source: v0.2.15
    status: supported
  - version: "0.2.14"
    source: v0.2.14
    status: deprecated
  - version: "0.2.12"
    source: a989155385026b2e5f80cedb5edc8e1e0f4a6bbd
    source-version: 0.2.14.dev0
    status: deprecated
    note: Its guides were written after the tag; this is the commit that holds them.
```

- `contract`: the contract version this manifest is written to. The consumer
  refuses a manifest whose `contract` it does not implement, naming both.
- `notice`: the support statement shown on the versions index. Markdown, one
  paragraph, authored here so the producer owns every published word.
- `source-version`: the version the source ref declares when it is not the
  entry's `version`; see 4.2. Absent means they must agree.
- `version`, `source`, `status`, `note`, `current`: as R-DOCS-003 defines
  them. `source` is any ref the producer repository resolves; for a released
  version it is the final tag unless a documentation-correction ref exists,
  see section 9.

### 4.2 The version, read from the source

For each entry the consumer checks out `source` and reads
`[project] version` from `devcapsule-src/pyproject.toml` at that ref. This is
the only file outside `docs/` the consumer reads from a version's source.

- A release version `X.Y.Z` must equal the entry's `version`.
- A development version `X.Y.Z.devN` is allowed only for the entry whose
  `version` is `devel`.
- Otherwise the build fails naming the entry, the ref, and both versions,
  unless the entry's `source-version` equals what the ref declares. This
  covers the 0.2.12 case. On `devel`, `source-version` names the release
  most recently promoted. The promotion helper writes it so a release
  checkout passes the check that reads each checkout as `main`. Keep it
  on `main`, where the declared development version already passes.

The 2026-10-27 release documentation work order amends this producer copy.
The `devel` use of `source-version` and the pre-tag documentation ref are
proposals for the consumer's authoritative contract. They use its existing
source-version check; they require no consumer code change.

### 4.3 The versioned tree at each ref

The consumer takes `docs/` from the ref and nothing else besides the version
file. Every page carries the front matter of R-DOCS-003 part 1, with one
added field:

| Field | Required | Values | Meaning |
|---|---|---|---|
| `role` | no | one of the contract's role names, section 5.3 | This page is the version's page for that role. At most one page per role per version. |

### 4.4 Version tokens in versioned pages

A versioned page never types a version. It writes tokens, which the consumer
substitutes from the version read in 4.2:

| Token | Renders as | Example at 0.2.15 |
|---|---|---|
| `{{version}}` | the version | `0.2.15` |
| `{{tag}}` | `v` and the version | `v0.2.15` |
| `{{release_url}}` | the GitHub release page for the tag | `https://github.com/ccozianu/devcapsule/releases/tag/v0.2.15` |
| `{{download_url}}` | the release's download base | `https://github.com/ccozianu/devcapsule/releases/download/v0.2.15` |

A literal string matching a DevCapsule version, `v?0\.\d+\.\d+(\.dev\d+)?`,
in a versioned page fails the build naming the file and line. This is what
turns "the guide still says v0.2.12" from a convention into an error. For
`devel`, tokens render the development version and the page carries the
unreleased banner; the download URL is rendered but is not expected to exist.

Unversioned pages are exempt: the journal and the release notes name
versions because they are about them.

### 4.5 Unversioned content

As the consumer reads it today, plus R-DOCS-003 front matter on every page
except `README.md`. The landing page's stable section identities (W07) are
HTML comment markers (`<!-- website:hero -->`, `<!-- website:demo -->`,
`<!-- website:benefits -->`, `<!-- website:continuity -->`,
`<!-- website:fit -->`, `<!-- website:dogfood -->`, `<!-- website:why -->`,
`<!-- website:comparison -->`, `<!-- website:contribute -->`, and the
self-closing `<!-- website:social ... -->` marker before the first section).
Images and self-hosted videos (`.webm`, `.mp4`) referenced by `README.md` or
other content pages are copied into `/content-assets/<key>/…`; `website:demo`
replaces the hero's right-hand schematic figure with an inline, expandable
product recording, poster image, provenance caption and step summary, and
`website:continuity` renders the engineering-continuity handoff section after
`benefits`. See `CONTRACT.md` sections 3.7, 5.1 and 5.5 in the consumer
repository.

## 5. Outputs The Consumer Produces

### 5.1 Routes

| Route | Content | Versioned |
|---|---|---|
| `/` | landing page from `README.md` | no |
| `/blog/`, `/blog/<date>-<slug>/` | journal | no |
| `/releases/`, `/releases/<tag>/` | release notes, if adopted | no |
| `/docs/` | the versions index, section 5.2 | no |
| `/docs/<version>/` and `/docs/<version>/<path>/` | that version's documentation | yes |
| `/docs/current/` and `/docs/current/<path>/` | a full copy of the current version; the canonical URL of every page that exists in it | yes, by alias |

`/docs/current/` is a copy, not a redirect, so the URL a reader bookmarks and
a search engine indexes stays valid across releases while its content moves.
Every other version's pages declare the same path in `current` as canonical
when it exists there, and carry the status banner and robots behaviour
R-DOCS-003 assigns to the status.

### 5.2 The versions index, `/docs/`

Generated from the manifest, in this order: the `notice`; the current
version, linked to `/docs/current/`; then the versions grouped by status as
R-DOCS-003 lists them, each linked to `/docs/<version>/` with its status and
`note`. Development versions last. This is the page a reader who wants a
specific version lands on from the home page.

### 5.3 Roles: the distinguished pages

The home page does not link documentation by path. It links by role, and the
consumer resolves each role to `/docs/current/<path>/` of the page that
declares that role in the current version. Contract version 1 defines four
roles:

| Role | Meaning | Today's page |
|---|---|---|
| `overview` | the documentation front door | `docs/README.md` |
| `getting-started` | the first session | `docs/guides/first-session.md` |
| `your-project` | bringing an existing project | `docs/guides/your-project.md` |
| `windows` | the platform note for Windows | `docs/guides/windows-wsl2.md` |

Rules: the current version must define every role the landing page uses, or
the build fails naming the role; an older version may lack a role, and the
switcher then links to that version's index; a role appears at most once per
version. The landing page's hero button, the README's "start here" link and
the journal's references all use role links, so a renamed file or a new
first-session guide changes nothing outside the versioned tree. This also
gives W07 the stable identities it wants for the documentation side.

### 5.4 Navigation to a version

From the home page: the documentation entry names the current version and
links to `/docs/current/`; beside it, "all versions" links to `/docs/`. From
`/docs/`, every version is one click away. On every documentation page, the
switcher lists every version where the same path exists, the version's index
where it does not, and marks the reader's current one. Two clicks from the
home page to any version; one click between versions of a page.

## 6. Build And Caching

1. A released version's output depends only on (its source commit, the
   consumer revision, the contract version). It is built once and reused
   until one of those changes. Its source ref is a tag or a pinned commit,
   so it does not move.
2. A content change on `main` rebuilds only `devel`, the unversioned pages,
   the versions index, the switcher and the `current` copy.
3. A manifest change re-assembles the index, the switcher, the banners and
   `current`; it rebuilds a version only if that entry's source changed.
4. The build fails as a whole when any version fails, naming the version and
   the file; a partial site is never published.

How the consumer achieves this is its own; the contract states the behaviour
so that the number of versions does not set the build time.

## 7. Compatibility And Diagnostics

- The manifest's `contract` and the consumer's implemented contract must
  agree. Additive changes, a new optional field or a new role, keep the
  number; anything a version-1 producer would break on gets version 2 and a
  compatibility decision recorded on both sides.
- Every failure names the file, field, version or role that caused it. A
  missing front matter block, an unknown key, an unresolvable source, a
  version mismatch, a typed version string, a duplicate role and a missing
  required role are each a distinct, named failure.
- Shared examples: a minimal conforming content tree and manifest live in
  the consumer repository as fixtures, and the producer's `nox` gate runs the
  consumer's check against the producer's real tree at the pinned consumer
  revision, so a producer change that would break the site fails here first.

## 8. The Publication Interface

The consumer exposes one operation: build the site for a producer content
revision, in a mode, for an origin. The content revision fixes `main`'s
unversioned pages and the manifest; the manifest fixes every version's
source. When and by whom that operation runs is the release runbook's
business, not the contract's: the runbook's obligations, from the
documentation-currency issue, are that the release's `docs/` is true before
the final tag, that the manifest promotes the version before it, and that
publication follows the final tag. The interface here is what makes the last
of those automatable.

## 9. Resolutions Proposed For The Open Details

**Typed versions (P5.1).** Resolved by tokens and the build check, 4.4.

**Documentation corrections to a released version (P5.2).** The definition
closes a release branch after its final tag. Rather than bend that rule, the
producer's local workflow declares one project-owned ref kind:
`docs-<version>`, forked from the release branch at the promotion commit
before the final tag. The final-tag job checks that its `docs/` tree equals
the tag's. It carries later documentation-only commits, is never merged
anywhere, and is named in the manifest as that version's `source` from
promotion. The candidate gate does not apply to it; the
consumer's build check does. This needs one entry in `WORKFLOW-LOCAL.md`,
which is where the definition says project refs are declared, and no change
to the definition. Until such a ref exists for a version, its source is the
final tag.

**0.2.12.** Published from the commit that holds its guides, with
`source-version` recording the mismatch, as the manifest example shows. If
the owner prefers not to publish it, the entry is simply omitted.

**The lifecycle clock (P5.3).** Closed by the owner's decision D1; the
`notice` carries it.

## 10. Migration, In Order

Consumer first, because the producer's migration lands only with the pin
that implements it:

1. Consumer: contract version 1 recorded; manifest parsing with the version
   check; front matter with `role`; tokens and the typed-version check; the
   per-version build with caching; the versions index; role resolution;
   the switcher and banners; the shared fixtures and the check command.
2. Producer, one change: move the non-documentation pages out of `docs/`;
   add front matter to every published page and `role` to the four entry
   pages; replace typed versions in the guides with tokens on `main`; add
   `docs/versions.yaml` with the bootstrap the owner sketched; point the
   README's documentation links at roles; bump the consumer pin.
3. Producer, for the already released versions: 0.2.15 and 0.2.14 carry a
   first-session guide that describes 0.2.12. Either they are published as
   they are, banners and all, or `docs-0.2.15` and `docs-0.2.14` refs carry
   corrected guides. The owner decides; the contract supports both.
4. Producer: the runbook gains the three obligations of section 8, and the
   gate runs the consumer's check.

## 11. Decisions For The Owner

1. Adopt the location rule: `docs/` is the versioned tree and the product
   pages leave it. Where they go, or whether they stay published.
2. Adopt the four roles as contract version 1, or amend the set.
3. Accept `docs-<version>` project refs for post-release documentation
   corrections, declared in `WORKFLOW-LOCAL.md`, as the answer to P5.2.
4. Publish 0.2.12 from its guides' commit, or omit it.
5. For 0.2.15 and 0.2.14: publish the guides as they are, or correct them on
   `docs-<version>` refs before the first versioned publication.
6. Approve this as the producer's proposal for contract version 1, to be
   delivered to the consumer repository; the delivery mechanism across the
   two repositories is itself open, P7.

## 11a. Decisions Taken (2026-09-28, under the owner's autonomy grant)

The owner granted `project-management` the decisions of section 11 on
2026-09-28. Taken, with the reasoning in
[the content work order](../../work-orders/2026-09-28-visitor-content-and-producer-migration.md),
section 5: (1) the location rule stands and the product drafts leave
`docs/`; (2) contract version 1 has six roles, adding `agents` and
`containment` to the four above; (3) `docs-<version>` project refs are
adopted; (4) 0.2.12 is published from its guides' commit; (5) 0.2.15's guides
are corrected on `docs-0.2.15`, 0.2.14 is published as it is with a note;
(6) this document goes to the consumer repository as the producer's
proposal. One additive element joins version 1: front matter
`status: planned`, a published stub labelled "coming soon", so the ideal
documentation structure is visible before every page is written. Section 5.3's
role table is superseded by the six-role list; the rules stand.

## 12. Acceptance

The contract is satisfied when the consumer's build, at the pinned revision,
on the producer's `main`: fails on each named failure in section 7 when the
shared fixtures provoke it; serves `/docs/`, `/docs/current/` and one
directory per listed version with the banners and canonicals of R-DOCS-003;
resolves every role on the landing page to the current version; renders
tokens to the version read from each source; and, with a manifest listing
three versions, rebuilds only `devel` when a `main` page changes. And when a
reader, from the home page, reaches the 0.2.14 first-session guide in two
clicks and switches to the 0.2.15 one in one.
