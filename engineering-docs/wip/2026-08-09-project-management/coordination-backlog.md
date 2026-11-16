# Coordination Backlog

Owned by: `project-management`

Cross-workstream coordination work and accepted follow-ups. Each entry states
its own release commitment. Older undecided entries gain no V1 commitment
merely by appearing here. An assigned item is carried by its owning workstream;
this list retains only the coordination obligation.

## Accepted Work Retained After Intake Closure

Confirmed by the owner, 2026-10-09. These entries preserve work from the 23
closed intake messages. They are not new questions to repeat at each session.
Read the matching entry when its revisit condition applies. An unresolved
release placement is not permission to mark a committed gate as later.

The workflow already permits priority `later` (not for this release), and
acknowledgement with an item's place in the work recorded. It does not define
automatic reminders or a mandatory trigger field. The revisit conditions below
are this workstream's scheduling notes, not a new generic workflow rule.
No accepted commitment is postponed by this explanation.

### Upgrade Experience: First Release After 0.3.1

Owner: `component-upgrades`; project-management retains release coordination.
Priority: `gating` for the first release after 0.3.1, whether 0.3.2 or 0.4.0;
not a gate for 0.3.1. Owner decision, 2026-11-16, in
[Upgrades In The First Release After 0.3.1](2026-11-16-decision-upgrades-next-release.md).

Before successor scope selection/cut, carry this obligation into its overview
with ownership and agreed closure criteria. Before final acceptance, require
upgrade acceptance evidence or a new explicit owner decision changing scope.
The first task is to reconcile existing upgrades with the embedded Codex and
Antigravity prompts and version persistence across launch/recreation. Detailed
implementation and acceptance design remain with component-upgrades and the owner.
The original September 3 intake is acknowledged and delivered onward.

### Configuration Presentation

Owner for implementation: `component-upgrades`, within the upgrade experience.
Priority: `wanted`. Release placement: unresolved; no new 0.3.0 gate.
Revisit when the broader upgrade-design slice is scoped; compare the integrated
base/configuration contract before assigning implementation.

Owner rulings of 2026-09-13/14: render configuration according to the schema it
was configured against; only mention a newer schema, rather than present new
nodes as recorded state. Offer the pinned base, the newest known recommendation
when different, and the current checkout choice, clearly marked as an override
when appropriate. Name the supported action for each choice. Launch must explain
when an override selects a different base. Preserve these outcomes when newer
commands supersede old spellings. Implementation is not claimed complete.

### Component Status Reliability

Owner: `component-upgrades`. Priority: `wanted`, toward V1, not a release gate.
Revisit when that workstream scopes its R-UPGRADE-002 follow-up after its current
consent slice, or if a concrete service incident requires earlier attention.

[R-UPGRADE-002](../../requirements/product/r-upgrade-002-status-operational-reliability.md)
is the canonical accepted contract: 48-hour observations, independent monitoring,
verified notification routes and failure drills. Provider, routes, thresholds,
operational owner and supported-adapter window are design decisions there.
Do not repeat whether to adopt the already accepted requirement.

### Repository IDE Files

Owner: `project-management`. Priority: `wanted`. Target: 0.3.0, no gate.
Resolved 2026-10-23 by the owner's reversal below; executed by `maintenance`.

Owner ruling of 2026-10-01: ignore this repository's .idea files. Untrack them
without deleting local files, add a root ignore entry, and document the rule
in the developer brief or local workflow. Other projects may track their own.
Keep current IDE edits out of the intake-disposition commit. No tooling feature
is requested, and this reconciliation does not execute the untracking.

Owner reversal of 2026-10-23, after the sort of the directory: the ruling of
2026-10-01 was never executed, and the churn came from the module files
PyCharm generates from every `pyproject.toml`, not from hand-written
settings. The rule now: track what PyCharm itself does not ignore, so other
checkouts run and debug without friction; JetBrains' `.idea/.gitignore` is
the contract; `misc.xml` stays ignored, since it names the workstation's
SDK and a tracked copy makes the IDE add files to VCS on its own; shared run
configurations live under `.idea/runConfigurations/` in the module-SDK form,
which JetBrains documents as the portable one. DevCapsule takes no
responsibility for IDE settings across ecosystems and relies on the IDE
cooperating with Git. The rule is in `DEVELOPING.md`, *IDE project files*.
Executed by `maintenance` on `ws-maintenance/idea-tracking`.

### Release And V1 Obligations

The [0.3.0 proposal](2026-09-27-0216-release-planning.md) owns the current release
commitments and cut decisions. The [V1 ledger](v1-scope-ledger.md) owns the legacy
capability gate. Their planning events are the revisit triggers. First-session
UX, release automation and forced configuration remain with maintenance;
consent remains with component-upgrades. These are assigned work, not new
adoption votes. The eleven user-docs proposals still require an owner decision
before 0.3.0; L1-L13 and chosen delivery still gate V1.

## Ecosystem Bootstrap: 0.9, After Project-Type Templating

Owner decision, 2026-10-11: move ecosystem-aware bootstrap from 0.3.0 to 0.9.
Maintenance retains the bug; project-management coordinates the prerequisite
project-type templating, whose implementation owner remains to be selected.
Revisit at 0.9 planning with that dependency explicit, not during routine 0.3.0
planning. This is the bootstrap feature numbered 7 in the later release-work
list, distinct from agenda item 7 (mycodespace/checkout naming) below.

The user's intended ecosystem (Java/Maven, Scala/sbt, Python/nox, Node/npm or
Node/Yarn, for example) determines tooling discovery and environment setup.
Project utilities should be on PATH throughout the capsule by default.
Exceptional project types may use `devcapsule project shell` inside the capsule
to activate the required environment. The [accepted decision](2026-10-11-decision-project-operations-and-bootstrap.md)
preserves the details, dependency and separate 0.3.0 workflow obligation.

For 0.3.0, workflow-improvements owns the generic rule requiring the agent to
establish and maintain project build, test, run and debug instructions with the
human in WORKFLOW-LOCAL.md. This remains necessary when all execution is
delegated to the agent. It does not wait for bootstrap automation.

## Pagefind: Catalog Proposal Closed, Website Owns Integration

Owner decision, 2026-10-10. Do not create a Pagefind DevCapsule component for
the website's build dependency. The website must declare a pinned npm dependency
and lockfile and build without global Pagefind or /opt/xtras when it implements
W10 search. The personal xtras install was temporary experimental convenience.
Playwright's already delivered component is a separate decision.

Handoff `2026-10-10-project-management-pagefind-project-dependency.md` delivered
to website at coordination `5b05eeecda11`, with portable-build, static-output
browser-search and atomic-publication acceptance criteria. No new delivery date
is assigned. This is a routing record, not an open catalog decision or another
project-management implementation task. Consult website's acknowledgement at
its next publication rather than reopen the dropped catalog proposal.

## Pre-V1 Work: Tentatively 0.9, Excluded From 0.3.0

Owner decision, 2026-10-10: postpone items 7, 8 and 12 from the consolidated
agenda until before V1, tentatively 0.9, definitely not 0.3.0. Priority: `later`
relative to the current release. Coordination owner: `project-management`.
Implementation owners are assigned at pickup. The intake messages are
acknowledged with this place in the work; none is marked implemented.

Revisit when planning 0.9 or another final pre-V1 cycle, whichever comes first.
Check again before V1 acceptance so a changed version sequence cannot lose
these items. Keep them off the 0.3.0 agenda unless the owner explicitly changes
this direction. This is a postponement within the pre-V1 plan, not the ledger's
`deferred` verdict, which means outside V1. Tentative 0.9 is not a release date.

### Item 7: mycodespace And Checkout Naming

Revisit the proposed [mycodespace direction](../../design-notes/devcapsule/2026-09-24-mycodespace-lifetime-namespace-and-archive.md)
with the owner: lifetime project namespace, one-action materialization, owned
archive, runnable retained environments and the workspace/submodule relationship.
Direction and any first implementation slice remain undecided; postponement
does not approve the entire proposal.

Keep the checkout-naming proposal with it: use the directory's last component
when unique among live checkouts; retain vanished records as missing without
letting them occupy the default slot; expose directory-to-record mappings.
D-0004 remains the current contract until the owner decides a change. Showing
a checkout name in project info does not decide how that name is assigned.

### Item 8: OpenCode Evaluation

Schedule and assign a bounded OpenCode/local-model evaluation. Identify the
model, runtime, hardware and context needs; prove a small useful coding task
and resumption; assess project instructions, persistence and explicit host
boundaries. Gemma remains a candidate, not a selected model. Record evidence
and gaps for user-docs before considering component integration. No installation
or integration is authorized by this postponement.

### Item 12: Routine Documentation Cleanup

- Intake READMEs: project-management's pointer is already thin; inspect remaining
  stale copies, particularly sample-projects, and route corrections to their
  owners. Treat recursive-e2e's archived copy as history rather than a live
  protocol. Do not revive its workstream for this cleanup.
- Contract wording: reconcile the producer specification's literal-version rule
  with the authoritative website contract and existing checks, including the
  loopback-address boundary and tokenized links. The docs-0.2.15 copy already
  landed; do not repeat that delivery. This is wording reconciliation, not a
  new version-check implementation or a 0.3.0 documentation gate.

The four original messages are recoverable in Git at
`967e9f9a3622d3b84c42eec6df004267a1abf143` under this workstream's intake:
`2026-09-25-maintenance-mycodespace-and-checkout-naming.md`,
`2026-09-15-user-docs-opencode-evaluation.md`,
`2026-08-17-workflow-improvements-obsolete-intake-readmes.md`, and
`2026-09-28-user-docs-contract-version-check-and-docs-0215.md`.

### Item 13: Search Discoverability, The Rest Of The SEO Objective

Owner decision, 2026-10-16: the SEO objective set for V1 on 2026-10-16 is
worked in the 0.9.x timeframe, not now. One part is already issued and runs
on the website's own clock: the website repository's work order
[social metadata and page identity](https://github.com/ccozianu/devcapsule-website/blob/main/engineering-docs/work-orders/2026-10-16-social-metadata-and-page-identity.md)
(W09 there: derived Open Graph and X tags, the `social` field, the landing
marker, optional JSON-LD). Everything else is postponed here, with no
priority among the items and no implementation owner until pickup:

1. The unindexed pages. The Search Console review of 2026-10-16 found 25
   pages indexed and 35 not, several with "temporary processing error" on
   ordinary pages such as `/docs/current/sessions/what-persists/`. Diagnose,
   re-request indexing, and set a re-check date; separate the versioned
   twins and the redirects that correctly point elsewhere from real errors.
2. The versioned twins. Older version pages are self-canonical by the
   contract's design, so a supported version page and its `current` copy
   compete for the same query. Decide whether a supported version page
   canonicalizes to `current`; a contract amendment if so.
3. The producer's companion to W09: delivered 2026-10-16 in PR #219, the
   `website:social` marker in `README.md`, the amendment to R-DOCS-003 and
   the pin at the website's `5dbfe49`, once the website shipped slices 1 to
   4 together. What remains here is the pass over every page's
   `description` for the search result it should earn.
4. Search intent per entry page: which queries each entry page should win,
   and the landing page's links into the documentation chosen for that.
   Content work on the producer side, owned by user-docs at pickup.
5. Measurement: a recurring Search Console reading, the Bing Webmaster
   submission the records never confirm, and a page-performance check,
   under or beside the website's W13 analytics item. The pages are light
   today: the landing page is 16 KB and answers in about 0.3 s.
6. Off-site presence: the repository's GitHub description and topics,
   listings, and where journal entries are posted. The owner's, outside
   both repositories' files.

Correct today and not items: language, viewport, one heading per page,
image alternative text, a 50-entry sitemap and a robots file naming it.

### Item 14: Desktop-Platform Friction, Alternative Designs For V1

Owner decision, 2026-10-16, while reviewing the competitive comparison.
Linux is the platform of choice for development; the project does not
compete with that conviction. The capsule's own desktop in a browser tab,
over noVNC, served the owner's own Windows usage well enough to ship with.
What remains is the unavoidable friction with opinionated desktop
platforms: browser shortcuts that compete with the IDE's, a clipboard that
crosses only through the desktop tab, a frame path that is not native.

The item, for V1: explore alternative designs that remove that friction
without reopening the boundary. The leading candidate is the remoting
built into the VS Code family: VSCodium or VS Code running natively on the
host operating system, with its editor process on the host and its
workspace, terminal, language servers and agents inside the capsule,
connected over SSH into the capsule or directly through Docker tooling to
a shell inside the container. The IDE then renders natively on Windows or
macOS and nothing of the capsule's desktop is needed. JetBrains Gateway
is the same shape for the JetBrains IDEs and is to be assessed alongside.

What the exploration must settle before any implementation: which side
holds the credentials the editor process carries, since the host editor
runs with the host user's keys and sessions while the capsule's rule is
that none of them enter; whether the attach path becomes a boundary node
the developer grants, like `host-x11`, with the same announcement at
launch; how the capsule's session logs, console and workflow tooling
reach an editor that is not inside it; and what persists across sessions
for an editor whose configuration lives on the host. The browser desktop
stays the default and the containment design; the alternative is an
addition for the platforms where the desktop's friction is felt, not a
replacement. Priority: `later`, decided at V1 planning; no implementation
is authorized by this item.

### Item 15: The Capability Catalog Ceiling, Contributed And Federated Components For V1

Owner decision, 2026-10-18, while reviewing the competitive comparison. The
catalog ceiling is a serious limitation today: a project can declare only
the capabilities the catalog knows, and a tool the catalog lacks is a
personal install under `/opt/xtras`, not something a project can require of
every contributor. Improving this is on the roadmap, tentatively for V1,
with two mechanisms, from the same starting point: a developer has tested a
component privately by unpacking it under `/opt/xtras/<name>` and running
it from there.

1. **Contribute it.** The developer submits a pull request to the DevCapsule
   repository that adds `<name>` to the list of components DevCapsule
   monitors for freshness and installs on request: the artifact, its
   version source, its checksum, where it unpacks and what it puts on
   `PATH`. The catalog grows by contribution, reviewed like any change.
2. **Federate it.** The more expedient path: the developer publishes a
   separate feed of components in a repository of their own, in the same
   form the catalog uses, and a project references that feed beside the
   built-in one. A team is then never blocked waiting for the catalog, and
   the trust decision is explicit: a referenced feed is code the developer
   runs on trust, which the project-versus-developer boundary already
   governs for every other declaration.

With the mechanism, the project undertakes to publish an analysis and
justification of its approach to components. DevCapsule does not want to be
yet another `.deb`, `.rpm`, PyPI or Maven repository. Its opinionated view
is that in this day and age software is better delivered as an archive that
is unpacked into one directory and run from there: that is how the catalog
installs every IDE, SDK and agent today, by digest, into a directory of its
own, and it is what makes a component relocatable, removable, cacheable and
auditable. The precedent is old: software as complex as the Oracle database
ran from one directory long before modern tooling made that easy. In the
age of AI there is no reason for software to arrive as an archive plus an
installation script that spreads its files across disconnected places in
the filesystem hierarchy. The analysis is to say where that view holds, what
it costs for software that resists it, and how the two mechanisms above
keep it.

Priority: `later`, decided at V1 planning. No format, schema or command is
decided by this item; the existing freshness feed on the `component-status`
branch and the version-set records are the starting material.

### Item 16: The Workflow, From Workable To State Of The Art, For V1

Owner direction, 2026-10-18, while reviewing the competitive comparison. The
workflow a capsule installs is workable today: status, decisions and next
steps in files, workstreams, mail between them, a decision log, release
refs, and the project uses it to build itself. The comparison says it is
growing toward state-of-the-art engineering practice, and this item is
that growth, for V1: what a human and agent pair gets by default that a
well-run engineering team would recognize. Candidates, not decisions: a
second agent pair's review as the ordinary path for a change, the scheme
recorded in the process item of 2026-10-12; validation kinds declared per
project and printed by the brief, already in the definition; decision
records and design issues as first-class files, already there; the humane
companions and the web console's materialized views, so that the records
are read without being maintained by hand; a release discipline with
candidate gates and acceptance evidence, as this project practices it. The
`workflow-improvements` workstream owns the definition; this item asks it to
state, before V1, which of these are in the installed default and which
stay this project's own practice. Priority: `later`, decided at V1 planning.

### Item 17: Review And Approve The Software You Bring Onto Your Box, For V1

Owner direction, 2026-10-18, while reviewing the competitive comparison.
Today the project declares what it needs and the developer authorizes what
the host gives; the catalog's components are pinned by digest and watched
by the freshness feed; the consent design, D-0011 to D-0013, governs the
base image and vendor trust. What a developer cannot do yet is see and
decide, in one place, what third-party software enters the capsule and why:
the components a project declares, the extras under `/opt/xtras`, and the
dependencies that `npm`, `mvn`, `pip` or `dotnet` pull recursively on the
project's behalf. The capsule is why those can run at all; the item is the
experience of reviewing and approving them. For V1: show provenance for
what the catalog installs, make the consent decisions legible after the
fact, and give the dependency trees the package managers pull a place
where they can be seen and, where it is worth it, pinned or refused. It
touches item 15, contributed and federated components, and the outbound
side of the boundary, which has its own item once 3.4 of the comparison
is settled. Priority: `later`, decided at V1 planning; no command or
format is decided here.

### Item 18: Credentials Stay On The Host, An Authenticating Proxy Outside The Capsule, For V1

Owner decision, 2026-10-18, while reviewing the competitive comparison. The
biggest missing feature of `0.2.16.dev0` is a nice way to handle Git and
GitHub credentials from inside the capsule. Today host SSH keys and cloud
credentials never enter, which is right, and the page that would say how a
push then works is a stub, because there is no good answer yet: an agent's
sign-in token lives in the capsule home, an API key enters only by an
explicit binding, and either can be read by anything in the capsule and sent
anywhere, since the boundary is strong inward and open outward.

The V1 direction: an authenticating proxy outside the capsule. The capsule
holds no credential; an outbound request to a known service leaves through
a host-side proxy that attaches the real credential, and the process inside
sees at most a sentinel value where a tool insists on a non-empty variable.
Git over HTTPS to GitHub is the first case; GitLab is the second, to prove
the generalization; the agents' own API endpoints are the third. Git over
SSH is covered separately by an SSH agent socket forwarded as a boundary
node, so a key can sign without being present. The proxy is started by the
launcher for the session, like the host-open bridge, and announced like
every other host grant.

The owner's condition was that such proxies exist as open source, ready to
configure rather than build. A search on 2026-10-18 found several; none is
evaluated yet, and evaluating licence, maintenance and fit is the item's
first step:

- Docker Sandboxes document the reference behaviour: the credential in the
  host keychain, GitHub's token read from `gh auth token` and cached for 55
  minutes, a `proxy-managed` sentinel in the sandbox's environment, the
  header injected by the host-side proxy
  ([credentials](https://docs.docker.com/ai/sandboxes/security/credentials.md),
  [authentication](https://docs.docker.com/ai/sandboxes/workflows/authentication.md)).
  That is a product, not a component, but it is the behaviour to match.
- [Infisical Agent Vault](https://github.com/Infisical/agent-vault): a vault
  and credential proxy for agents in one binary, open source.
- `sandbox-proxy`, a stdlib-only Go forward proxy that injects credentials
  on the wire with a default-deny mode, and `iron-proxy`, an egress firewall
  that swaps proxy tokens for real credentials at egress, both listed in
  [awesome-agent-runtime-security](https://github.com/bureado/awesome-agent-runtime-security).
- [agent-sandbox](https://github.com/mattolson/agent-sandbox/): secret
  injection in a proxy container with the secret directory mounted into the
  proxy only; `gh api` works with the token on the host.
- [mitmproxy](https://docs.mitmproxy.org/stable/addons/overview): the
  open-source scriptable building block if a purpose-built proxy is the
  better fit; Git over HTTPS to a forge is a narrow protocol.

To settle in the item: which services first and how a project names them;
whether a credential is scoped per repository; whether egress is
default-deny once the proxy exists; how the capsule trusts the proxy's
certificate when interception is needed, which the base image can carry;
and what `project info` and the session logs show about it. Priority:
`later`, decided at V1 planning; no component or design is chosen by this
item. It closes the gap named in section 3.4 of the competitive comparison
and in its recommendation 3.1.

## Notification When A Host Bridge Is Not Granted

Opened: 2026-10-03, from the closure of the
[URL-opening bug record](../../bugs/devcapsule/2026-09-24-url-opening-without-browser-handler.md)
at the owner's ruling. A backlog entry, not a bug: the capsule behaves as
its denial says.

When a capsule has no `host-browser` grant and something asks to open a URL,
the user today gets nothing: `BROWSER` is unset and `xdg-open` finds no
handler. The owner wants this handled by the contained desktop's own
notification mechanism, a graphical notice that host-browser is not granted
and the one command that grants it, rather than by text on a terminal that
the click may not have come from. The contained desktop has no notification
daemon today (no `notify-send`, no daemon in the runtime image); the entry
includes choosing one frugal enough for the desktop the project keeps.
Likely owner: `contained-display`. Priority: `later`; no release target.

## File Locking Protocol

Opened: 2026-08-15

Release target: **undecided (V1 or V2)**

Context: on 2026-08-15 the product owner established that no workstream holds
exclusive editing rights over any file. Exclusivity applies only where a
documented locking protocol exists and is actually used. No such protocol
exists, so today nothing is exclusive.

That is the right default while work is sequential. Under genuine concurrency
it leaves a gap: two workstreams may edit the same file with no mechanism to
coordinate beyond ordinary Git conflict resolution.

A protocol would need to define at least:

- what may be locked, and at what granularity: a file, a directory, or a
  declared area such as a handoff or a requirements register;
- how a lock is taken, recorded, and made visible to another agent that only
  has the repository and no shared runtime;
- how long a lock survives, and how a lock left by an interrupted or abandoned
  session is detected and released without a human arbitrating every case;
- what an agent does when it needs a locked file, including whether it waits,
  proceeds and reconciles later, or escalates; and
- whether locks are advisory or enforced, given that nothing prevents an agent
  from simply editing the file.

Open question to settle before choosing a target: whether ordinary Git conflict
resolution plus clear workstream scoping is sufficient in practice, making a
lock protocol unnecessary complexity. Deciding that it is sufficient is a valid
outcome and should be recorded rather than left implicit.

Related: `WORKFLOW.md` rule 11 currently states a narrower exclusivity for
another workstream's WIP directory and recovery state. Whether that is a
carve-out or a contradiction should be reconciled by `workflow-improvements`
independently of this item, since readers need an answer now.

## Dissolved Stage 7 Items

Opened: 2026-08-27, when the product owner judged `recursive-e2e`'s pending
Stage 7 not consequential enough to gate that workstream's conclusion and
directed its identified items here as decisions to be made, not work already
scheduled. Each leaves this backlog when it gains a release target and an
owner, or a recorded rejection.

### External-Resource Ownership And Reaping

Closed: 2026-10-09, at the owner's direction. No further action is required
on the standalone Stage 7 resource-convention request. Its requester was
archived and the old plan no longer describes current development. Remove
this request from the active decision agenda; do not recreate it as later work.

Maintenance's concrete cleanup defects and its current reuse/reaping work
remain independently owned and tracked. This closure neither resolves those
bugs nor authorizes deleting retained host resources. The persistent-diagnostics
proposal of 2026-10-08 arose from a separate noVNC incident and is not part of
this retired Stage 7 request.

### Retained-Successor Evidence Disposal

Release target: **undecided; cheap either way**

Two exited successor containers (`b2093d85…` and `482c34f2…` runs) and their
run roots remain on the owner's host under a do-not-delete constraint that
existed for Stage 7's benefit. With Stage 7 dissolved, decide when to release
the constraint and remove them — by their exact GUID-derived names, which is
itself a small live exercise of the cleanup rule.

### Successor Persistence And Stability Proof

Release target: **undecided; likely reject**

The bounded second-inspection stability result was never produced: both
retained successors exited while paused, so it needs a fresh launch. Its value
was recursive-dogfood assurance, not adopter-facing persistence — project
state and home persistence are separately covered. Recording rejection is a
valid outcome.

### Non-Interactive Runs

Release target: **undecided — but the product owner ruled on 2026-08-23 that
this blocks V1**; the entry must not bury that ruling.

Delivered to this workstream's intake on 2026-08-27 (written 2026-08-23,
delayed by the outbox failure). Unattended operation has no owner, no
requirement, and no defined behavior for authorization and acquisition
acknowledgements. The decisions it needs are recorded in the intake item:
support versus explicit refusal in V1, the pre-recorded authorization shape if
supported, whether it becomes a requirement and a ledger row, and which
workstream carries it.

**Mechanism decided 2026-08-29.** The product owner ratified the capsule
supervisor for V1 (ledger row *Capsule Supervisor And Multi-IDE Sessions*):
non-interactive runs are the supervisor with no GUI children, so the
"support versus refusal" question is answered — supported, in V1. The owning
workstream is settled 2026-08-30: `contained-display` carries the supervisor
core and with it this item's design work. Still open from the list above: the
pre-recorded authorization and acquisition acknowledgement shape, and the
requirement record.

### Workflow Invariants As Pre-Commit Hooks

Release target: undecided. Owner: none yet, per the 2026-08-29 unowned-rows
ruling; assigned at pickup.

Directed by the product owner on 2026-08-29 while dispositioning the
intake-staleness item. The workflow's mechanical invariants — the intake
exclusive-or, append-only disposition logs, intake naming, the WIP carve-out,
registry agreement — become a `devcapsule workflow verify` check exposed to
adopters as opt-in `pre-commit` local hooks seeded by bootstrap, and to this
repository as a Nox gate session. Design fleshed out in
[the 2026-08-29 note](2026-08-29-workflow-invariants-pre-commit.md). Shares
its delivery path with the initialization-tooling entry below; whichever
workstream picks up one should expect the other.

### Multiple-Stream Initialization Tooling

Release target: undecided. Owner: none yet, per the 2026-08-29 unowned-rows
ruling; assigned at pickup.

Recorded 2026-08-30 at the product owner's direction, dispositioning the
2026-08-16 intake item from `workflow-improvements`. The owner asked that the
reserved `project-management` workstream be "initiated by the tooling on all
devcapsule projects"; the protocol half is done, but the only path that seeds
workflow files today is `devcapsule bootstrap project` running
`docker4pycharm/bootstrap-project.sh`, a script predating the multiple-stream
workflow entirely. The work is product implementation in `devcapsule-src`:
teach the bootstrap to initialize multiple-stream mode, including the reserved
workstream, per `WORKFLOW.md`'s *Initializing Multiple-Stream Mode*. Shares
its delivery path with the pre-commit invariants entry above — the same
bootstrap seeds both.

### Silent Empty Bind-Source Failure

Release target: V1, per the ledger's at-risk homes. Owner: none yet; assigned
at pickup.

At-risk item 6 of the readiness assessment, homed here 2026-08-30. Docker
invents an empty directory when a bind source is missing — a data-shaped
silent failure that recurred twice in one recorded session. Make it
structurally loud once: launches must verify bind sources exist and refuse
with an actionable message rather than let Docker fabricate them.

### Submodule Pointer Publication Ordering

Release target: V1, per the ledger's at-risk homes. Owner: none yet;
`sample-projects` is the natural owner at pickup, since its submodules are
where the failure bites.

At-risk item 7 of the readiness assessment, homed here 2026-08-30. `main`
can currently advertise a submodule pointer that no clone resolves, breaking
the first command an adopter runs. Specify and check the publication order:
the submodule's commit is publicly reachable before the superproject pointer
lands.
