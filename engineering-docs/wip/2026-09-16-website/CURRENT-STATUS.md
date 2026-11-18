# Workstream Current Status: Website

Mnemonic: `website`

Start date: `2026-09-16`

State: landing page copy in review for DevCapsule main, 2026-11-18

Definition read: WORKFLOW.md@781c9e39df58, WORKFLOW-LOCAL.md@94a29cb6eedb

Branch association: `ws-website/content-update`

Integration target: DevCapsule `main`. Website PR #1 is merged into its `main`
at `b55ea0a`, with the same tree as previewed implementation `c508b91`.

Delivery method: reviewable SSH-pushed branches; the owner creates/merges PRs
and performs final GitHub backend wiring. The owner has now authorized making
the site live at `devcapsule.mycodespace.ai` before finishing the review.
No force-push or mainline implementation is needed.

## Landing page copy (2026-11-18)

The owner supplied equivalent README patches for main and release-0.3.1.
The website slice began at the current mainline, `79b98bfe`. Review the
single mainline change with the pinned website renderer. The homepage
continues to feature the step-by-step presentation integrated in PR #59.

After 0.3.1, check the release documentation version declaration and align
the producer and consumer contract wording. After the successor upgrade
release, draft the article for the bounded adopter pilot. Project management
owns the pilot plan and the owner reviews it before outreach or publication.

## Planned Next Step

Review and merge the landing page copy pull request.

## Presentations on the website (2026-11-15)

The owner resumed this workstream to bring the console presentation viewer to
the website. The working branch synchronized with canonical `upstream/main`;
`origin/main` had diverged and is the older fork. The viewer implementation is
on the website repository branch `presentations`. This branch supplies the
recorded `todo-fastapi-postgres-react` presentation from the release checkout;
the website discovers its document and media at build time. The website branch is pushed at `c57a50c`, and this branch pins it for review.
The website change and this content must be integrated together. No publication
has occurred.

The four incoming items were acknowledged in the disposition log. Journal video
support remains a later website task; W10 records the Pagefind dependency
constraint. Next: complete the website checks, integrate the website branch,
advance the parent website pin, validate against the final content, and deliver
through the normal review and publication process. The site build, production-mode link check, content contract, 23 tests, 63
browser audits and clean-clone update check passed. A relocation-only README
from the older fork was restored to canonical upstream content after the merge.
The initial parent gate compared against the old fork; the rerun used upstream
and passed types and test conventions, but reported test failures and errors.
One reproduced error is a launcher-only command refusing inside this capsule.
The run was stopped at 92% after it stalled; other failures remain untriaged.
The full gate has not passed.

## Producer Migration (2026-09-28)

2026-10-01, at the owner's direction: the developer documentation was split
out of `DEVELOPING.md`, now a brief with a table of contents, into
`engineering-docs/development/`: environment, source layout, and the unit,
integration and end-to-end test documents, each written from the suite as
it is (sixty unit modules, one integration module, eight end-to-end tests,
their fixtures, resources, markers and sessions). Indexed; the runbook's
link into the brief follows the move; the two anchors other documents use
in the brief were kept.

2026-10-01, on this branch at the owner's direction, outside this
workstream's subject: the IDE smoke, `nox -s ide-smoke`, with
`tests/e2e/ide_session.py` and `tests/e2e/test_ide_comes_alive.py`. Per IDE
surface it initializes a fresh project with the executable under test,
launches it, and proves the IDE came alive: desktop URL answers, an X11
window of the IDE's class exists, and optionally a Playwright screenshot.
Verified against the shipped 0.2.15 executable from inside this capsule:
VSCodium passed in 16 s, PyCharm in 64 s, every container and record
removed afterwards; the full build gate passed with the new test deselected
by its marker. Evidence under `devcapsule-src/dist/e2e-evidence/ide-smoke/`.
The product half belongs to maintenance or the catalog workstream when the
owner routes it; it rides this branch only because the owner said so.

External state, 2026-09-30: this capsule's `/opt/xtras` holds Pagefind
1.5.2 and Playwright 1.63.0 with Chromium under `/opt/xtras/playwright/browsers`,
launchers in `/opt/xtras/bin`, `PLAYWRIGHT_BROWSERS_PATH` exported from the
persistent shell profiles; personal installs at the owner's direction, mailed
to project-management as a future-component request. Pagefind indexed the
built site in 0.14 s; the website's W10 search bar would use it.

2026-09-30, at the owner's explicit direction and from this checkout rather
than a project-management selection, the owner overruling the workstream
ceremony for three project-management documents: the contract promoted from
its open-work directory to `engineering-docs/specifications/product/`,
marked accepted and naming the website's `CONTRACT.md` as authoritative;
`WORKFLOW-LOCAL.md` and the release runbook now link it, and the local
*Release Policy* says a release includes its documentation and names
`docs/versions.yaml`; R-DOCS-003 set to accepted with a *Delivered* note.
The website's own `CONTRACT.md` still links the contract at its old
open-work path, a one-line fix for that project.

**Done, 2026-09-30.** PR #152 merged the migration at `main` `2ec36b9`.
The owner ran the test deployment and the production promotion; the live
site's `build-info.json` records content revision `2ec36b9`, website
revision `6759b9d`, contract 1, current 0.2.15, clean sources, built
2026-09-28 21:08 UTC and served since 21:45 UTC. Checked live on
2026-09-30: the home page, `/docs/`, `/docs/current/`, the current
first-session guide rendering `v0.2.15` from its token, `/docs/0.2.14/`,
`/releases/`, `/journal/`, `/sitemap.xml`. This closes W07-C (the README
carries the markers), W08-C (manifest and front matter) and W12-C (the
contract accepted on both sides). The owner declared the effort done and
this workstream pauses; W04-C, W09-C and W11-C remain its retained tasks,
and W00's sitemap submission is the website project's.

Resumed 2026-09-28 at the owner's "just do it" after project-management's
work order and the website repository's execution of all six slices of its
own order, `publication` at `31e85b1`. Definition read: the 0.2.14 entry in
full; the branch is current with `main`. Taken and decided: the 2026-09-21
definition-changed notice, done by this publication; the 2026-09-28 producer
migration work order, acknowledged as this section. The work order's section
3, delivered in this one change so that no build sees half a contract:

- `docs/versions.yaml`, contract 1, the owner's approved notice, `devel` from
  `main`, 0.2.15 supported and current from `docs-0.2.15` (carried there at
  `9e43ec7`), 0.2.14 and 0.2.12 deprecated as `legacy: true` with their notes.
- Front matter on the six journal entries, authored descriptions, `draft:
  true` on the two 2026-09-19 retrospectives; the blog README and the local
  workflow's blog conventions amended to require it.
- The README restructured with the contract's landing identities: hero,
  benefits, fit, dogfood, why, comparison, contribute; the prose kept, the
  "Is it for you" and "Contribute" sections new; documentation links point
  into the new tree.
- The three quoted descriptions from user-docs, cherry-picked.
- The website pin advanced to `6759b9d`, the website's `main` after the
  owner merged the stacked slices and the colour-schemes follow-up; the
  first pin, `31e85b1`, was the `publication` tip before those merges.
- The parent Website workflow checks out with full history and tags and
  fetches `docs-*` branches into local refs, so the manifest's sources,
  `docs-0.2.15`, `v0.2.14` and a bare commit, resolve on the hosted runner;
  a shallow single-branch checkout resolved none of them.
- The gate: `nox -s docs-contract` and a step in `build` run the website's
  `check:content` against this checkout, skipped with a notice where the
  submodule or npm is absent.

Validated here: `nox -s docs-contract` passed, 176 pages, all six roles
resolved, 0.2.14 and 0.2.12 reused as legacy; `./scripts/website.sh build`
passed its check on 180 pages and 13432 links; the full build gate,
`nox -s build` with its scratch under `/opt/devcapsule-gate`, passed on the
committed tree: 1089 tests, 20 deselected, one existing xfail and one xpass,
mypy clean on 174 files, the docs-contract step inside the gate passing on
176 pages, the local and exact-revision PEX built and smoked; log
`/opt/devcapsule-gate/build-ws-website.log`. Not validated: the test site and
production, which are the owner's two publication runs after the merge.
The registry row now names the `ws-` branch, per the deferred rename.

Next: the owner merges this branch, the website's stacked PRs, then runs the
parent Website workflow (test site and candidate) and the website's Publish
workflow (production). After publication: W07-C closes, since the README
carries the markers; W08-C is delivered by the manifest and front matter;
W12-C by the accepted contract. The retained tasks below then reduce to
W04-C, W09-C and W11-C.

## Synchronization And Pause (2026-09-18)

The owner requested synchronization with main and a switch to project-management.
The clean website branch fast-forwarded to fetched main `042c094`; no conflicts
or implementation edits were required. Existing Open Threads below remain the
handoff: owner verdict, then closure records through the normal PR route.
Branch-name migration to `ws-website/` remains due before the next release
candidate under WORKFLOW-LOCAL.md's transition exception. No migration or
additional website work was requested in this synchronization task.

Validation: `nox -s build` passed, including all nine packaging integration
checks. The dirty-tree policy skipped the public revision-bearing PEX; the
local validation artifact passed. Pause records are sent separately through
`ws-website/outbox` for the owner to merge; production was not rechecked during
this Git-only task. The target project-management branch has divergent local
and remote histories; owner direction is pending before switching or merging
there.

## Task Contract And Current Stage

The [website autonomy work order](../../work-orders/2026-09-16-website-autonomy.md)
is the contract. The owner explicitly selected this fresh-context experiment,
delegating design and implementation after initial setup. Implementation is
complete through hosted production. The owner accepted the experiment as
successful with A− and requested the follow-up inventory below. Publication
before final review was separately authorized; acceptance is now settled.
Further implementation awaits selection of a bounded follow-up slice.

The site presents the root README substance, current user guides, and the
development blog. Other engineering/developer references lead to GitHub.
Current v0.2.12 guides remain the accepted interim content; their V1 rewrite is
still user-docs work. No product requirement or source-content rewrite was made.

## Review And Continuation

The owner subsequently requested removal of authorship giveaways within the
articles, so that the AI narrator could credibly have been written by either
participant. Part 2 no longer claims to have written Part 1 or describes being
asked to write the follow-up. Its link to the earlier, explicitly attributed
Part 1 draft was removed with that passage. A few passages of self-assessment
were rephrased; the development events and qualifications are retained.
Both article bodies were reviewed for further explicit authorship claims;
the owner-requested ambiguous introductory notes and narrative perspectives
remain. This concerns clues in the articles, not concealment of public Git
history. Earlier editorial commits are now on fetched main; the working branch
fast-forwarded before this follow-up. Diff review, whitespace checks, and the
website build/link checks passed. Human evaluation remains pending.

Both September 19 retrospectives received an owner-requested style and flow
revision for a human authorship-identification exercise. Events, claims,
qualifications, narrative perspectives, titles and existing
links are preserved; no new anecdotes or factual assertions were introduced.
Reviewed both revisions against the originals for meaning. The website build
and its local link/structure checks passed. This is an editorial save point;
the experiment and workstream state are unchanged. Next: owner reading and
external reader evaluation, then any further editorial changes before publication.
No reader-test result or deployment is claimed. The checkout already contains
fetched main; the remote website mailbox was checked via Git and was empty
(the `devcapsule` command is unavailable on this shell's PATH).
At the owner's subsequent request, both introductory attribution notes now
present authorship as either Costin Cozianu or Gpt-6-Astra for the reader
exercise, identifying the human and AI perspectives respectively. Only these
notes changed in that follow-up; article bodies remain unchanged. Diff review
and whitespace checks passed; no publication was triggered.

The owner also requested [Part 2 from the AI's perspective](../../blog/2026-09-19-lessons-learned-in-ai-autonomy-part-2.md).
It is an agent-authored draft for editorial review, with independent reflection
on decision quality, operational assumptions, validation scope and resource use.
Part 1 is unchanged; both entries remain content-owned here. Blog and root
indexes include Part 2. No publishing workflow was triggered.

Owner-requested retrospective drafted on 2026-09-19:
[Lessons learned in AI autonomy over a simple, straightforward task](../../blog/2026-09-19-lessons-learned-in-ai-autonomy.md).
Written in the owner's voice and explicitly awaiting his editorial review;
no invented dialogue or claim of reviewed publication. The article preserves
the accepted A− verdict and treats analytics as second-stage scope. Blog and
root documentation indexes are updated. Relevant validation: website build
and local link/structure checks pass with the new article. No website deployment
was triggered. Next editorial step is owner review before publication; the
remaining website backlog and ownership migration are unchanged.

Preview: **http://127.0.0.1:8080/**, running on loopback in this host-networked
capsule. The owner confirmed localhost access and authorized trying subsequent
ports if occupied. The development server watches content and presentation;
refresh the browser after it reports a rebuild. This is a local preview, not a
hosted deployment.

Restart from this checkout's root:

```sh
git submodule update --init website
./scripts/website.sh install
./scripts/website.sh preview
```

Use the printed URL if 8080 is occupied. `PORT=8090` changes the starting port.
Build/check on demand: `./scripts/website.sh build`.

Next step: review/merge the direct website backlog handoff and parent pointer;
then agree producer-side W12-C and the website contract before further content
structure changes. Review the autonomy blog draft separately. W00 remains the
website project's first priority; no new implementation is started by migration.

Urgent exception authorized 2026-09-19: implement the W00 prerequisite to serve
Google's ownership verification file. Website branch `google-site-verification`
at `4a9ba02` adds the exact response at `/googledda808d7513923e5.html`, copies it
unchanged at build time, and lets validated verification files pass page checks
and promotion without canonical rewriting. The parent pins that implementation.
All 12 website tests, production-mode build, 582 link/asset checks and an exact
source/output comparison pass. The candidate round-trip test preserves the file.
No visual checks or container builds were needed. Public deployment and Search
Console verification were pending at that checkpoint; see the owner update below.
The existing required parent `nox -s build` integration gate also passed;
the dirty-tree policy skipped the revision-bearing PEX.

Update from the owner after publication: Google verification succeeded and
Search Console reports indexing data is processing. This is owner-reported
progress; indexing is not yet established. The verification fix is merged in
website main at `2f7cc75`. Continue W00 from the website backlog, retaining the
verification file in future deployments and checking older rollback candidates.

The owner accepted the experiment as successful with an A−, explicitly valuing
the agent's recognition of shortcomings. That verdict is now recorded; do not
ask for it again. On 2026-09-19 the owner specifically requested task items in
this workstream. This supersedes the earlier plan to archive immediately and the
earlier limitation against keeping a parent workstream website backlog. The owner
subsequently authorized the direct backlog handoff recorded below;
website implementation work now belongs to the standalone website project.

Resume: clean checkout switched from project-management to the registered website
branch for this explicit continuation, then fast-forwarded to origin/main d71559a.
The older branch name remains covered by WORKFLOW-LOCAL.md's adoption exception.
Mail take with explicit --workstream website reported no mail; intake is empty.
No existing open bug record was owned by website at review start. No project-
management implementation or workstream state was changed.

Workflow synchronization, 2026-09-19: merged fetched main `3f573b5` into the
published working branch without rewriting history; reread AGENTS.md,
WORKFLOW.md and WORKFLOW-LOCAL.md under the declared `0.2.14.dev0` definition.
Mail take again found no website mail. The open website-owned bug is the W01
test-publication input defect linked below. Website source and deployments were
not changed or revalidated during this workflow-only task.

Inter-workstream items now use `devcapsule workflow mail` on `coordination`;
our own status, registry row and bug records still travel `ws-website/outbox`.
The existing unmerged records delivery is preserved. The new coordination
section conflicts with leftover main/outbox intake prose elsewhere in
WORKFLOW.md and AGENTS.md. Following the owner's explicit instruction and the
new section, use mail for delivery and working-branch commits for decisions.
Reported the contradictory guidance to `workflow-improvements` by mail as
`2026-09-19-website-mail-protocol-stale-guidance.md`; our intake README now
describes the new mechanism.

Validation after synchronization: `nox -s build` passed (633 tests, one expected
failure, and nine packaging integration checks). The local PEX passed; the
revision-bearing PEX was skipped under the gate's dirty-tree policy.

Final live check on 2026-09-18: production and test homepage, documentation,
first-session guide and journal all return HTTP 200 over validated HTTPS.
Production canonical URLs are correct and the visible build time is
2026-09-18T00:43:08.793Z. Its build-info records content
`5a4b35435ee3e1cb460b48d292f15e5efe5228be`, implementation
`0691956e3aa383b74c9fb87f4d46140136b8a0b6`, and candidate
`website-candidate-35292339140-1`. Anonymous public candidate metadata matches
production source revisions and archive checksum provenance. The previous
production TLS hostname mismatch is resolved.

The test site's newer 00:57 UTC build uses production canonical URLs. This is
servable but does not meet the current candidate packaging checks. Record input
simplification as maintenance; production's earlier valid candidate is correct.
Future candidate runs must retain the test origin and root base path.

All implementation and timestamp changes are on remote main. Final handoff
updates live on website `experiment-handoff` and parent `website/initial-cut`.
The workstream stays open for the owner-requested follow-up inventory.
Experiment acceptance is recorded above; no independent website session is claimed.

The owner rejected personal-token renewal overhead and selected public GitHub
Release assets. The parent workflow publishes a candidate prerelease only after
successful test deployment, using built-in GITHUB_TOKEN with contents: write
only in the candidate job. Tags use website-candidate-RUN_ID-ATTEMPT and cannot
replace the latest CLI release. Production downloads public assets anonymously,
validates SHA-256/source metadata/archive paths and promotes without rebuilding.
The only generated-page changes are canonical origins and promotion provenance.
Releases remain available until deleted; Actions artifact/log retention is no
longer a promotion/rollback dependency. The former CANDIDATE_READ_TOKEN proposal
is superseded; do not ask the owner to create or renew it.

On 2026-09-17, both checkout HEADs matched fetched remote main (parent `8233dab`,
website `b55ea0a`). The parent integration is merged. The owner reports the test
site works well; HTTPS manifest and GitHub API independently confirm test run
`35187865183`, content `8233dab98bf85710bb73ebd3e66ef0b29880eaf4`, website
`b55ea0a378725080bc7cf13b2c78844b2d225c52`, with successful build and deploy.
Only `mycodespace.ai` is owned; all `codespace.ai` spellings were human typos.
Test is `test-devcapsule.mycodespace.ai`; production is `devcapsule.mycodespace.ai`.
Experiment acceptance is successful, A−. Administrative finalization is deferred
while the owner is assembling follow-up tasks in this workstream.

## Delivered Structure

- Public `ccozianu/devcapsule-website`, included as Git submodule `website/`,
  owns Eleventy 3.1.6, styles/layouts, navigation, build/import/preview scripts,
  tests, and its own developer instructions and single-stream handoff.
- Content remains authoritative here: root README, `docs/**/*.md`, and blog
  articles under `engineering-docs/blog/`. No manually maintained content copy
  was introduced in the website repository.
- Root `scripts/website.sh` is the small parent build/update interface.
  `.github/workflows/website.yml` prepares manual artifact builds and explicit
  owner-triggered Pages publication. Content merges and releases do not deploy.
- Standalone website development consumes an explicit `CONTENT_DIR` or an
  ignored, nonrecursive DevCapsule checkout. No parent gitlink update is needed
  to work independently on the website.
- Each output records content/implementation revisions, dirty indicators, a
  consumed-content digest, mode and base path in `build-info.json`. Relative
  links/anchors become local routes; engineering references use the content SHA.
- The website's DevCapsule manifest selects Node/VSCodium and includes a
  generated Linux platform lock. Host networking is recommended for preview
  and subject to developer authorization. No host Docker access is requested.
- Independent future presentation work belongs in that project. The initial
  submodule implementation is part of this workstream, as the work order allows;
  no second workstream was opened and no independent pair transition is claimed.

## Validation Evidence

- Parent `./scripts/website.sh build`: 16 HTML pages and 582 local
  links/assets/anchors checked, plus document headings, image labels and
  revision metadata. Passed.
- Four focused routing/rendering tests: relative links, GitHub permalinks,
  missing targets, heading slugs, literal template syntax, subpath deployment.
  Passed.
- Chromium desktop (1440px) and mobile (390px): 12 representative page/viewport
  audits passed without automated WCAG A/AA violations, page overflow or JS
  errors. Keyboard skip link, section anchors, and no-JavaScript navigation pass.
- Inspected desktop homepage, guide and mobile rendered screenshots. A separate
  320px reflow check passed; clipboard output exactly matched the code example.
  These checks inform review; they do not establish owner satisfaction.
- Clean standalone clone: `npm ci`, build and link check passed. A paragraph
  change reached generated output and changed its content digest; a CSS change
  reached output without changing content or its digest. `/devcapsule/` link
  checks and production canonical/robots metadata passed. No parent submodules
  were initialized in that test.
- Website DevCapsule manifest and lock generated/validated using this repo's
  resolver and configuration validators. A separate capsule launch was not run.
- Required parent gate: `devcapsule-src/.venv/bin/python -m nox -s build` passed,
  including compilation, shell syntax, type checks, tests, CLI/PEX smoke and
  nine packaging integration checks. The dirty-tree gate intentionally skipped
  the public revision-bearing PEX; its local PEX passed. No runtime source changed.
- Hosted test deployment, public candidate metadata and production promotion/HTTPS
  are now independently verified on 2026-09-18; details are in continuation above.
- Release promotion: eleven website tests pass, covering credential-free downloads,
  archive corruption/unsafe paths, source validation and byte preservation.
  A clean build of the deployed sources passed packaging, simulated anonymous
  download, promotion and all 582 local links across 16 pages. Both workflows
  pass actionlint 1.7.12. No page appearance or parent runtime source changed.

The required parent `nox -s build` gate passed again, including all nine
packaging integration checks. Its dirty-tree policy skipped the public revision
PEX; the local PEX build and smoke checks passed.

Timestamp validation: all 11 unit tests, the build and 582 local links pass.
Twelve desktop/mobile browser audits pass without overflow or automated WCAG
A/AA violations. Additional desktop/mobile/320px checks without JavaScript
confirm that the visible timestamp matches the manifest; footer screenshots
were visually inspected. Existing promotion tests confirm builtAt is preserved.

## Setup, Access And Budget

The starting checkout was clean. Accepted `origin/main` was `02eb470`; local
main was strictly behind (0 local-only, 102 remote-only). Registration, work
order, and empty intake were verified there. The published website starting
branch fast-forwarded from `6e87fc7` without rewriting history. Its preparation
from user-docs was the narrow exception already documented in the work order.

The owner created `ccozianu/devcapsule-website` with initial README commit
`ed4c18eebb96994966f3f98e1822878e0e723f75`. SSH clone and push dry run succeeded.
The owner instructed SSH-only operation without app access; do not request
GitHub app credentials again. He explicitly accepts running build/trigger
scripts by hand and defers final GitHub backend wiring to delivery. The
website's [publication instructions](../../../website/PUBLISHING.md) give
the exact final sequence, including submodule handling after a squash merge.

No paid hosting, API usage purchase, cloud provisioning, model download, or
production publication was performed. Node dependencies, Playwright Chromium,
and the checkout-local Python validation environment were installed for the
required checks. Expected Pages/standard public-runner hosting cost is $0;
no paid services are enabled by this work.

The agreed account ceiling remains the subscription-month allowance and three
reported resets. The tools expose no allowance/reset balance or reset control;
actual remaining allowance is unknown. This chat is the stated exceptional
warning channel; no other contact was supplied or used. At rendering, browser
validation and delivery milestones, remaining work appeared feasible inside
the authorized ceiling. No anticipated overrun or reset need was identified.
An abrupt platform cutoff invisible to the agent cannot guarantee warning.

## Inventory Validation (2026-09-19)

Read-only checks inspected both live sites' metadata/robots and discovery URLs,
and the current build/promotion implementation. No deployment or product source
was changed. Corrected pre-existing website-document relative links in this
status file while validating the records. Reviewed links resolve except the
unchanged index entry into an uninitialized sample-project submodule.
The required nox build gate passed, including nine packaging integration checks;
the dirty-tree policy skipped the public revision PEX, as expected. Mail and the
pre-existing website bug queue were empty. The confirmed publishing-input defect
is now recorded with owner website; follow-up details were subsequently transferred to the website backlog.

## Content And Integration Tasks Retained In DevCapsule

The owner authorized direct submodule edits as a one-time handoff exception on
2026-09-19. Detailed W00–W13 website tasks now live in the website project's
[authoritative backlog](../../../website/BACKLOG.md), including newly formalized
W12. This parent no longer owns those implementation tasks. Website uses its
own single-stream status for continuation; this checkout remains selected to
DevCapsule's website workstream. No autonomous workstream switch is implied.

DevCapsule owns authored content and editorial decisions. The website owns
functionality, appearance, rendering and publishing design. The parent retains
its content, the following producer obligations, and the small integration that
pins/invokes website tooling. These are open tasks, not implemented changes.
`-C` IDs correspond to the linked website task, with distinct acceptance criteria.
W00 remains the highest website priority; this split does not reprioritize it.

| Parent task | Website dependency |
|---|---|
| I01 — Parent publication integration | [W01](../../../website/BACKLOG.md#w01--p1-make-the-test-publication-action-hard-to-misuse), [W05](../../../website/BACKLOG.md#w05--p1-verify-the-public-result-after-deployment), [W06](../../../website/BACKLOG.md#w06--p2-make-rollback-and-candidate-retention-operationally-reliable) |
| W04-C — Content PR validation | [W04](../../../website/BACKLOG.md#w04--p1-validate-website-changes-before-the-manual-publishing-run), W12 |
| W07-C — Landing content structure | [W07](../../../website/BACKLOG.md#w07--p2-remove-brittle-coupling-to-readme-wording-and-paragraph-order), W12 |
| W08-C — Editorial status and version | [W08](../../../website/BACKLOG.md#w08--p2-make-content-status-and-version-explicit), W12 |
| W09-C — Descriptions and social artwork | [W09](../../../website/BACKLOG.md#w09--p2-improve-discovery-and-link-previews), W12 |
| W11-C — Guide and demonstration content | [W11](../../../website/BACKLOG.md#w11--p2-validate-the-experience-with-people-and-browsers-beyond-this-setup) |
| W12-C — Producer contract requirements and acceptance | [W12](../../../website/BACKLOG.md#w12--gating-define-the-contentwebsite-contract) |

### I01 — Maintain the parent integration with website publishing

- [ ] Apply website-owned interface changes to the parent caller, workflow and
  submodule pin when ready. Existing publishing implementation happens to run
  here; that does not make its behavior or backlog content-owned.
- Done means: parent invocations select the intended content/website revisions
  and expose the website's agreed publication/verification/recovery behavior.
  Keep substantive website logic in its owner repository where practical; agree
  the interface before moving code. The parent still owns its GitHub permissions
  and release-namespace integration. No workflow is changed by this migration.
- Verify: targeted caller/configuration checks and an agreed test publication;
  coordinate with W01/W05/W06 rather than duplicating their implementation tests.

### W04-C — Validate content changes before publication

- [ ] Invoke website-supplied conformance/build/link checks on relevant content PRs
  against a declared website revision. Do not duplicate the check implementation.
- Done means: a broken authored link or incompatible content is caught before
  merge with useful author feedback, without deployment or exposing write tokens.
- Verify: representative valid and invalid content changes through the parent PR
  check; website owns its browser/layout checks and presentation PR workflow.

### W07-C — Agree and author stable landing content structure

- [ ] Agree section identities and editorial structure with W12, then adjust the
  authored README/metadata if needed without duplicating prose in the website.
- Done means: product meaning and ordering remain content-owned; ordinary wording
  changes do not require coordinating literal heading strings with the builder.
- Verify: representative editorial changes against the W07 consumer implementation
  and agreed contract, reviewed for meaning as well as build success.

### W08-C — Decide publication status, supported version and freshness

- [ ] Decide which authored pages are public, draft or historical; supply explicit
  status/version metadata under W12. A fresh site build is not a guide review.
- Done means: editorial publication decisions and supported versions are recorded
  in content; website W08 renders/enforces them. Preserve intended historical
  references. The accepted guide rewrite remains user-docs work; send actionable
  changes through coordination mail rather than editing its workstream records.
- Verify: owner review of current/draft/historical examples and generated output.

### W09-C — Supply editorial descriptions and social assets

- [ ] Author concise approved descriptions and select/provide relevant social
  artwork for the homepage, guides and articles under the agreed metadata fields.
- Done means: accurate authored copy/assets are available to W09's generator;
  sitemap, canonical and social-tag mechanics stay website-owned.
- Verify: owner reviews representative text/artwork in generated share previews.

### W11-C — Improve guide and product demonstration content from evidence

- [ ] Supply authentic DevCapsule screenshots/demo content if selected, and route
  substantive guide corrections from newcomer tasks to the content owner.
- Done means: content matches supported product behavior and addresses observed
  reader problems; do not infer a required video or rewrite without owner scope.
- Verify: representative user tasks/content review with W11; website owns browser,
  performance, visual layout and standalone website-environment verification.

### W12-C — Agree the producer side of the content–website contract

- [ ] Define author needs and acceptable metadata/structure, review the website's
  canonical contract, and reference the agreed version from DevCapsule guidance.
- Done means: one authoritative contract in the website repository, with explicit
  content-owner acceptance, compatibility/migration rules and examples that both
  sides can use. Implementation observations are not silently made requirements.
- Verify: a new maintainer can author and preview a conforming example from the
  written instructions without reconstructing our conversation or parser code.

### Migration Record And Remaining Editorial Work

- Full task evidence and acceptance criteria moved to website/BACKLOG.md. Mixed
  items have producer tasks above and links from the website backlog. No copied
  implementation backlog remains here.
- The publishing-input bug moved to the website's engineering-docs/bugs/website/;
  the original parent record is a retired transfer pointer, not a claim of a fix.
- W00 records the owner's successful Google verification and processing report;
  indexing remains unverified and Bing/sitemap work is still open. W13 is planned
  second-stage functionality, not an initial implementation defect.
- The owner-requested autonomy retrospective remains DevCapsule-authored content,
  awaiting editorial review before website publication.
- Validation: all 14 destination IDs and six producer counterparts were checked;
  W09's original scope is unchanged. Local documentation links resolve apart
  from the unchanged index reference into an uninitialized sample submodule.
  The required parent `nox -s build` gate passed, including nine packaging
  integration tests; dirty-tree policy skipped the revision-bearing PEX.
- Delivery: website branch `backlog-handoff`, then the parent `website/initial-cut`
  PR containing its gitlink and companion records. Keep those parent records
  with the pointer update so main does not link to a backlog absent from its
  pinned submodule. No publication workflow needs running for this records-only
  migration; the blog remains subject to separate editorial approval.
- The workflow does not define a cross-repository mailbox transfer. The explicit
  owner exception authorizes direct edits in the submodule; commit/push its
  authoritative records first, then pin them here. Ordinary messages to other
  DevCapsule workstreams still use coordination mail. No second local selection
  or permanent exception to workstream routing is introduced.

## Open Threads

- Presentations: review and merge the website branch first, then update the
  parent pin to its merged revision, complete the parent gate in a suitable
  launcher environment, and deliver the parent branch. Review the test site
  before any production publication. The website viewer is a copied adaptation
  and must follow future console changes.

- Awaiting the owner: reader-test feedback and selection of the next bounded
  content/parent-integration task. The experiment's A− verdict is settled.
- Awaiting delivery: merge the website pause/routing outbox, then remove the
  legacy remote branch alias. The new working branch is `ws-website/initial-cut`.
- Unresolved: producer-side W12-C and the website contract before content
  structure changes; closure remains deferred. Website-owned W00–W13 stay in
  the submodule backlog, with producer obligations retained here.
- Existing publication decisions stand: content here, presentation in the
  website repository, public candidates, no personal deployment token, manual
  production approval. Exact experiment expenditure is unknown.
- Deliberately not preserved: speculative reader verdicts, a chat transcript,
  duplicate backlog copies, or an assumption that the old preview still runs.

## Documents

- [Design idea: site search with Pagefind](2026-09-30-design-site-search-pagefind.md) — saved 2026-09-30, deferred; not 0.2.16 unless time is left (W10).
- [Work order](../../work-orders/2026-09-16-website-autonomy.md)
- [Transferred test publication input bug](../../bugs/website/2026-09-19-test-publishing-accepts-inconsistent-settings.md)
- [Website developer guide](../../../website/README.md)
- [Publication and exact final steps](../../../website/PUBLISHING.md)
- [Website independent handoff](../../../website/CURRENT-STATUS.md)
- [Website-owned backlog](../../../website/BACKLOG.md)
- [Intake](intake/README.md)
- [Disposition log](intake-dispositions.md)
