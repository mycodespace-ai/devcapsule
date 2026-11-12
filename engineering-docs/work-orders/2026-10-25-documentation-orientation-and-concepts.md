# Work Order: Orientation, Concepts, Persistence And Recipes In The Documentation

Drafted 2026-10-25 from a list the owner brought in: an analysis, made
outside this project, of how a complementary open-source product documents
itself, and eight improvements it suggests for `devcapsule.mycodespace.ai`.
The list was written without this repository's contract or vocabulary; this
order keeps what holds against the documentation as it is at `b19d654`, the
rc6 publication record, and drops or corrects the rest. Workstream:
`maintenance`, by the owner's leave; it joins the documentation round
already booked before the final 0.3.0 tag, the language review mailed to
`project-management` at `9fcfdb8db440`, so the pages are rewritten once.

Evidence read: `docs/` at `b19d654` and the rc6 executable; the content
contract `website/CONTRACT.md`, sections 3.7, 4 and 5.4; the repository
`README.md` landing sections; the eleven user-docs proposals of 2026-09-28
in `engineering-docs/wip/2026-09-12-user-docs/2026-09-28-docs-improvements-for-0216.md`;
the landing-page order of 2026-10-18. Decisions already taken by the owner
are cited where they bind; the rest is decided here and flagged below.

## Current scheduling decision

Owner amendment, 2026-10-29, acknowledged by maintenance on 2026-10-30:
**both Part A and Part B target 0.3.1**. Maintenance retains ownership.
This supersedes the original plan above to combine these proposals with
0.3.0's documentation round. The separate language review, accurate
candidate documentation (C16) and C20 remain 0.3.0 obligations. No existing
documentation is removed and no proposal is cancelled.

## Outcome

A visitor who does not yet trust the product finds, in this order and
without searching: what DevCapsule is and is not; what a capsule is and
which words the documentation uses; what to install and in which order;
where every piece of state lives and what survives replacing the container;
a handful of task-shaped recipes; and how people, interactive agents and
background agents share one repository. The site's landing page shows the
loop in five numbered steps, each badged with who acts.

## What holds, what does not

The outside list made claims about the site that the contract contradicts;
the executor builds on these facts, not on the list.

- The sidebar's first group is **Start here**: the six role pages, in the
  contract's section 4 order (overview, first session, existing repository,
  choose an agent, the boundary, Windows). It is not a section named "Use
  DevCapsule"; that is the overview's title. The areas below it follow the
  order in which the overview first links each directory; **Getting
  started** is first and *Install DevCapsule* is its first page. Nothing is
  out of order inside the areas. The one real gap: a Windows visitor who
  follows the role list reaches *Your first session* before the Windows note.
- **What persists** (`docs/sessions/what-persists.md`) already is the
  "where things live" table, with the host locations. It lacks two answers
  the list asks for: whether a thing is in Git, and what happens when the
  manifest changes and the container is replaced.
- **The configuration entry page** (`docs/configuration/index.md`) already
  defines manifest, platform lock, checkout record, workstation records,
  capability, component and the IDE's role. A concepts page must reuse those
  definitions, not write a second set.
- A **glossary** and **recipes** are items 5 and 6 of the eleven user-docs
  proposals the owner has not yet decided. This order takes the owner's
  handing-over of the list on 2026-10-25 as the decision on those two; the
  other nine stay open, project-management's to put to the owner.
- The landing page is built from the README's section markers (contract
  3.7). There is no numbered-steps section; adding one is a contract
  amendment and a website change, not a content edit.
- "Built with DevCapsule" is the `dogfood` line above the journal cards and
  the footer. Dogfooding is this project's story, which belongs in the
  journal under `engineering-docs/blog/`, not in `docs/`, which describes the
  product for adopters.
- Words the list uses that the documentation does not: "Platform Lock" is
  the platform lock, lower case; "Host Authorization" is an authorization;
  "Project Memory" is the status file and the workstream records;
  "Dockerfiles" never appear; `/opt/xtras` is an alias of `~/xtras` in the
  persistent home, not a mount. No third-party product is named in `docs/`.

## Part A: documentation content

Every command, path and key is verified against the rc6 executable before
it is written. Pages keep the contract's front matter; new pages carry
`weight` and `updated`. No page is marked planned to make room: a page in
this order is written or it is not in this order.

1. **What DevCapsule is not.** The overview `docs/README.md` gains a short
   section after the three starting places, three items, one sentence each,
   in the documentation's own words: not a devcontainer specification or a
   remote editor server, because the IDE runs as a real GUI application in
   the same container as the agents; not a throwaway sandbox, because the
   capsule's home, the IDE's state and `/opt/xtras` survive replacing the
   container; not an unattended pull-request factory, because the point is
   a person in a full IDE beside the agents, behind a boundary the person
   controls. The README's `comparison` section states the same three in one
   sentence each, so `/why/` carries them too. Done: both places read the
   same three distinctions; the fit section's "Not yet" list is unchanged.
2. **What a capsule is.** A new page `docs/getting-started/what-a-capsule-is.md`,
   weight 0, so it leads the Getting started area ahead of *Install*. It has
   two parts. First, the three places, as a table and, if the executor can
   draw it faithfully in text, a diagram: *in your repository* (the
   manifest, the platform lock, and the workflow files when the project
   uses the DevCapsule workflow); *on your computer* (the checkout record,
   the workstation records, the durable directories, the image cache, Docker);
   *in the capsule* (the IDE, the agents, the project folder, the persistent
   home with `~/xtras`, a disposable root filesystem). Second, the words,
   two or three sentences each: capsule, capability, component, IDE,
   manifest, platform lock, checkout record, workstation record, the
   boundary, authorization, trust, `/opt/xtras`, workstream. Definitions
   that already exist on the configuration entry page are reused verbatim or
   shortened, never reworded into a second meaning. Done: every word links to
   the page that owns it; the first-session page's lead names this page and
   *Install* as the steps before it.
3. **What persists, completed.** The table on `docs/sessions/what-persists.md`
   gains two columns, *In Git?* and *Survives replacing the container?*, and
   the page gains a short section, *When the manifest changes*: the next
   `run` re-resolves components and may build a new image; the home, the
   IDE's state and `/opt/xtras` are the same directories as before; the
   container's own filesystem is new. Three bullets, verified by doing it
   once with the rc6 executable. Done: the section's claims match
   `project info` and one observed replacement.
4. **Recipes.** A new area `docs/recipes/`, linked from the overview after
   *Collaboration* so it sits there in the sidebar, with an index page and
   four recipes, each a page a reader copies from top to bottom: a Python
   project with PyCharm and Claude Code; a Java project with IntelliJ IDEA
   and the PostgreSQL client; a tool only you need, which points to
   *Extra tools* and adds the one `ln -s` the reader asked for; handing a
   task from one agent to another through the status file. Recipes name
   only capabilities the rc6 catalog has; the outside list's Scala recipe is
   dropped for that reason. The fifth suggestion, verification commands for
   agents, is one paragraph in the fourth recipe pointing to the workflow's
   *Validation Commands*. Done: every command block in the area was run
   against rc6 on a scratch project.
5. **Background agents on the same repository.** One section at the end of
   `docs/collaboration/working-in-workstreams.md`: an issue-to-pull-request
   service running Claude Code or Codex reads the same `AGENTS.md` the
   capsule's agents read, so the rules are shared without a second file; a
   background job that does not join the workflow writes no status file and
   never touches `coordination`, which is what keeps it from colliding with
   the workstreams; a client for such a service installed under
   `/opt/xtras` keeps its token in the capsule's home, not on the host. No
   product is named; no rule is added to `WORKFLOW.md`. Done: the section
   says nothing `WORKFLOW.md` does not already allow.

## Part B: the site

Part B follows Part A and is not a gate of the final 0.3.0 tag. Each item
amends `website/CONTRACT.md` under its section 11a and is implemented in the
website repository, then pinned here.

1. **The Windows note moves up.** The role order of contract section 4
   becomes overview, Windows, first session, existing repository, choose an
   agent, the boundary, so the Start here list reads in the order a visitor
   needs it. The home page's three pillars, the header and the footer are
   unaffected: they resolve roles by name. Done: the live sidebar shows the
   new order and the contract check passes on `main`.
2. **The loop in five steps.** A new landing section, `steps`, rendered as a
   numbered strip under the pillars: a list of five items, each
   `**Who.** What happens`. The README's content: *The project's owner*
   declares capabilities in the manifest; *you* answer what the launcher
   asks, since a project can recommend host access and only you can grant
   it; *the launcher* resolves components, builds the image from cached
   stages and starts the IDE and the agents in one container; *you and the
   agent* work in the same environment, the IDE for judgment, the agent for
   the routine, the status file for the handoff; *you* stop and come back,
   or replace the container, with the home and the tools intact. Done: the
   strip renders on `/` at phone width; a README without the section renders
   the page as today.
3. **One dogfooding story.** A journal entry under `engineering-docs/blog/`
   that walks one real 0.3.0 work order from its file to the candidate it
   shipped in: the capabilities and components order, PR #275, its three
   slices #276, #277 and #279 implemented by one agent and reviewed by
   another, the full gate, the owner's merges, rc5. It links the live
   `AGENTS.md`, `WORKFLOW.md` and the maintenance status file. The
   `dogfood` line links the entry. Done: every number in the entry is
   traceable to a record it links.

## Acceptance evidence

- `scripts/website.sh build` passes from the repository root with the
  website submodule at its pinned revision, for Part A; for Part B, at the
  revision that implements the amendments.
- The documentation contract check reports every new page under its area
  and no planned marker on a page this order writes.
- The commands of Part A, items 3 and 4, were run against the rc6 executable
  on a scratch project, and the status file says so with the date.
- The maintenance status file records what was accepted and what was
  dropped from the outside list, by item.

## Decisions taken here, for the owner to reverse if wrong

- Attached to `maintenance` and merged with the language review into one
  documentation round before the final tag; Part B after it.
- The glossary and recipes proposals, items 5 and 6 of the eleven, count as
  decided by this order; the nine others remain open.
- No separate concepts area: the words live on a Getting started page so
  they precede *Install*, which the sidebar cannot express otherwise.
- The persistence contract extends the existing page rather than adding a
  reference page.
- Dogfooding is a journal entry, not a documentation page.
- Third-party products are not named in `docs/`.

## Stopping points

Before amending the content contract, since the website is a separate
repository with its own review; before publishing any Part A change to the
live site, which happens through the pinned revision and the owner's merge
of `main`; before the final tag, as the release overview already says.
