# DevCapsule 0.3.0 changelog, since 0.2.15

Maintained by the agent driving the release and updated at every candidate,
from the merged pull requests and the bug records, for adopters: what is
new and what is fixed since 0.2.15. Records, workflow rules and the
project's own housekeeping are left out on purpose. The adopter notes for
the final release, `notes.md`, are written from this file.

Candidate 8 was tagged 2026-10-26 at `8d41fab`; candidate 7 was tagged 2026-10-25 at `73bbe53`; candidate 6 on 2026-10-25 at `2ed8ecf`; candidate 5 on 2026-10-25 at `03ed348`; candidate 4 on 2026-10-24 at `78a9c66`; candidate 3 on 2026-10-24 at `a22a215`; candidate 2 was tagged
2026-10-22 at `e5b5a8b`, candidate 1 on 2026-10-19 at `7016cdd` and
candidate 0 on 2026-10-18 at `53ebc17`.

## New

- **The web console.** Every capsule serves a small read-only website
  about itself, reached through one link the launcher prints beside the
  desktop link, valid for that run only. Pages for what the inspection
  commands report, configuration, versions, project; the capsule's
  processes and its use of CPU and memory against its limits; the
  project's Markdown records rendered, with `dot` blocks drawn as
  diagrams; decisions an agent hands to you, answered in the browser and
  written where the agent reads them; notifications from the checkout's
  environment, with a bell. Needs base recipe 10 or later; older bases
  print a notice and run without it.
- **Session logs, on by default.** Every launch gets a log directory on
  your computer, named on the `Session logs:` line, with one file per
  component, the launcher's and the supervisor's included, at a WARNING
  baseline. Inside the capsule it is `/var/log/devcapsule`, named by
  `DEVCAPSULE_LOG_DIR`. Files rotate in place with compression, and one
  budget per checkout bounds the whole. They survive the browser tab,
  Ctrl+C, the IDE's exit and the container's removal.
- **Three more IDE surfaces and browser automation.** IntelliJ IDEA
  (`java-ide`), Eclipse IDE for Java Developers (`eclipse-ide`) and
  JetBrains Rider with a pinned .NET SDK (`dotnet-ide`, `dotnet`), each
  accepted with a recorded graphical smoke. Playwright with a
  component-installed Chromium (`browser-automation`) for tests and
  agents inside the capsule.
- **Shared versus personal capabilities, and commands for every
  configuration change.** A project declares required capabilities and
  optional enhancements; a developer keeps personal IDE, agent and tool
  choices and omissions local to the checkout. `project config
  capabilities` replaces either set after validating the candidate, with
  `--preview` to look before writing; `project config need` adds
  capabilities and regenerates the lock; `project config check` validates
  the project contract, or candidate files, without writing or launching.
  `project config list` and `project versions show` answer `--json`.
- **One launch may depart from a required IDE.** A project may require
  an IDE, for instance one that develops a plugin for it. `project run
  --ide IDE --force` launches another IDE for that session: the launcher
  warns which required IDE it sets aside, the plan records the departure,
  and nothing is saved, so the next plain `run` launches the required IDE
  again. Without `--force` the conflicting IDE is refused with that
  command named; `--force` grants no consent and skips no check.
- **Checkout notifications and decisions from the command line.**
  `project checkout notifications` lists, posts, reads and dismisses what
  the environment tells the developer; `project checkout decisions`
  builds a decision page for the console and `hand-off` prints the text
  for chat, so an agent sees one CLI. The console's origin reaches the
  capsule as `DEVCAPSULE_CONSOLE_URL`.
- **Bases named by what they promise.** A base is identified by its
  family and recipe, `ubuntu-24.04@11`, the contract its consumers rely
  on; the tool that built it is provenance, shown but not identity. The
  `devcapsule images` package carries the contract and a compatibility
  report.
- **Faster image rebuilds.** Directory inputs are named build contexts
  read in place and archives unpack once by digest, so a rebuild of the
  real IDE tree transfers 1.29 MB where it transferred 3.69 GB.
- **In-capsule project commands.** Inside a capsule every `project`
  subcommand finds the capsule's project, and each command declares the
  access it needs; the ones that need launcher-owned state say so and
  name the command to run outside.
- **Agent versions.** Codex 0.163.0, Claude Code 2.1.302 and Antigravity
  CLI 1.4.2, each verified against its vendor's checksum and started on
  the base with DevCapsule's seeded settings. Existing locks keep their
  pins until a checkout chooses to follow the project again.

## Fixed

- Inside a capsule, configuration inspection failed from `/opt` and from
  the mounted project (2026-09-24).
- Inside a capsule, `project <unknown>` was refused as launcher-only
  instead of as unknown (2026-09-26).
- Detached successor containers exited and were never cleaned up; the
  recursive successor is now launched attached, like every capsule
  (2026-08-15), and it launches from a fresh workspace (2026-10-04).
- The unpacked archive cache could lose concurrent work and trust an
  incomplete entry; publication is serialized and completed entries are
  validated (2026-10-08).
- Relaunching IntelliJ mistook a reused container PID for the previous
  IDE and refused on a stale directory lock (2026-10-04).
- Clearing an optional omission lost a local version pin; omitted
  optional pins stay in the persistent selection (2026-10-06).
- An unreleased component in the shared lock prevented released
  launchers from opening the checkout; a compatibility guard now keeps
  the shared configuration readable by the latest release (2026-10-04).
- Website links failed with `xdg-open` when no browser handler was
  available; the host-open bridge is verified and the record closed
  (2026-09-24).

## Documentation

The documentation is versioned and published per release at
[devcapsule.mycodespace.ai](https://devcapsule.mycodespace.ai), 43 pages
in thirteen areas for 0.2.15, with the pages this release adds: the web
console, diagnostics and logs, capabilities, the IDE surfaces, component
upgrades and freshness, and the developer documents on the unit,
integration and end-to-end suites.

## Fixed in candidate 1

- On the published base, `ubuntu-24.04@9`, candidate 0 printed a web
  console link, the capsule then said this base has no web console, and
  three minutes later the launcher reported that the console did not
  answer and suggested opening the link (2026-10-18). The launcher now
  reads the base's labels first; on a base without the console it prints
  what is missing, the one command that builds a base with it and the
  guide, and plans no console at all: no port, no token, no wait. The
  console needs a base of recipe 11 or later; a published one is a gate
  before the final release, and
  [building and selecting a local base](https://devcapsule.mycodespace.ai/docs/current/configuration/local-base/)
  is the way to have it before then.

## Fixed in candidate 2

- **The terminal during a session is quiet, and the session ends with a
  result.** The IDE's and the display stack's own output, with its
  harmless ERROR labels, goes to the session's log files only; the
  terminal carries the launcher's lines, the desktop and console links and
  the ready line, the supervisor's warnings when a component dies, and at
  the end one result line, `Session ended`, `Session failed` or `Session
  interrupted`, followed by the path of every log file of the session on
  your computer (2026-09-15, C10).
- **Ctrl+C ends the session with that result, not a traceback.** The
  launcher waits for the capsule to stop, asks Docker after a minute, and
  on a second Ctrl+C stops waiting and names the container to stop; it
  returns 130 as shells report an interrupted command (2026-09-15, C10).
- **`project run --authorize network host` works on every project.** The
  `network` authorization is a node on every project, with Docker's
  bridge as the default, whether or not the project recommends host
  networking; a recommendation attaches the project's justification
  (2026-10-05).
- The configuration listing attributed an unanswered workstation default
  to the manifest; it names the workstation default now.

## New in candidate 3

- **Saved Docker arguments for each checkout.** `project config
  set-extra-docker-args -- OPTIONS...` saves the extra `docker run` options
  a development scenario needs, GPUs, mounts, environment variables, once
  per checkout on the launcher host; `project run` passes them after its
  own options and before anything given after `run --`, so returning to
  that work is `project run` again. `list-extra-docker-args` shows the list
  with inline environment values masked, `remove-extra-docker-args` clears
  it. `set-env NAME` takes a value from a hidden prompt, out of shell
  history; `list-env` and `unset-env` edit the same list. The list is a
  private file outside Git and outside anything mounted or snapshotted;
  launcher-owned options such as `--network` and `--memory` are refused in
  every spelling. [Project versus personal](https://devcapsule.mycodespace.ai/docs/current/configuration/project-versus-personal/)
  documents it (2026-10-23).
- **Software approvals at launch, once for the whole list.** When the
  project's lock brings new versions of vendor software you approved
  before, from the same vendors under the same terms, `project run` shows
  the list and asks one y/n instead of one question per component; any
  other key stops the launch and names `project config approve`, which
  approves from the command line and inside scripts. The page
  [Software approvals](https://devcapsule.mycodespace.ai/docs/current/configuration/software-approvals/)
  says what an approval by name leaves alone (2026-10-22).

## New in candidate 5

A capability names what the project needs. A component provides it. Coding
agents use this same model. The IDE owns the container's lifetime and can
use its display.

`config require`, `offer` and `drop` take capabilities directly.
`config require 'java>=21'` requires Java 21 or newer. Quote minimums in the
shell. The lock pins the exact version. `init --require` accepts the same
minimum. Repeat `init --with CAPABILITY` to add personal capabilities.

`config recommend frontend-ide codium` recommends a provider under
`[capabilities.resolution]`. A resolution recommendation takes no reason.
It grants no trust or host access.

`config add`, `omit` and `restore` select capabilities for your checkout.
`config use CAPABILITY COMPONENT` chooses among providers. `default` removes
that choice. `run --with` and `--use` apply choices to one launch. `--save`
records them.

The SDK major is removed. Old manifests remain readable with a note.
The next owner write drops the old table. An unchanged manifest keeps its
old lock current until the next shared edit.

The rc4 aliases and replaced agent and tool commands now return status 2.
Each names its replacement in one line and writes nothing. Initialization's
old agent flag points to `init --with`. `config capabilities --recover` remains available.

Candidate 4 ignores the new resolution table and uses the catalog's first
provider. Each current capability has only one provider. Minimums and
component aliases introduce vocabulary that candidate 4 cannot read.
Existing rc4 files remain readable by candidate 5.

The configuration documentation now starts with the project, checkout and
workstation records. The detail pages use the capability model and current
commands.

## New in candidate 4

The CLI redesign separates project requirements from personal choices.
The owner settled the scope in the
[CLI UX redesign work order](../../work-orders/2026-10-24-cli-ux-redesign.md)
on 2026-10-24.

- **Shared declarations and personal tools.** `project init --require node
  --offer browser-automation --ide frontend-ide --agent codex-agent` writes
  tools to the shared manifest and lock. It records the IDE and agent in
  the checkout. Initialization can still ask for per-checkout base consent.
  Owner commands are `config require`, `offer` and `drop` for tools and
  environment declarations, plus `recommend` for supported defaults.
  Tool edits update the manifest and lock together. Environment declarations
  and recommendations update only the manifest. The writer uses bare keys
  where possible and omits empty tables. The workflow declaration stays in
  the manifest. Schema-1 files remain readable; new schema-2 files need this
  launcher. [Capabilities](https://devcapsule.mycodespace.ai/docs/current/configuration/capabilities/).
- **Configuration inspection.** `config show` lists effective values,
  sources and pending decisions without writing. On the host, `config check`
  exits 3 for any pending decision. Candidate-file checks validate only
  the candidate contract. Inside a capsule, host decisions cannot be assessed.
- **Checkout commands and resource limits.** Personal commands cover IDEs,
  agents, tool omissions, values, authorizations, environment variables and
  bindings. `config env` and `config docker-args` edit the same private list.
  Memory and CPUs need no project declaration. Their precedence is the run
  flag, checkout answer, project recommendation, then workstation default.
  With none set, DevCapsule imposes no limit. CPUs must be a positive integer.
  Shared-memory size remains fixed by the IDE's runtime template.
  [Resource limits](https://devcapsule.mycodespace.ai/docs/current/configuration/resource-limits/).
- **Launch preparation.** `project run` derives the plan without a separate
  resolve step. It asks for missing required answers at a terminal.
  Without one, missing required answers produce status 3 before answers are saved.
  Unanswered host recommendations use secure defaults instead.
  IDE, agent, resource, environment and host-access flags apply to one launch.
  `--save` records them after the required review succeeds.
  `--trust` persists workstation acceptance without `--save`.
  A second checkout gets a separate record with a directory-derived name.
  Incompatible saved version sets require an explicit replacement.
  A base without a contained desktop still requires explicit X11 consent.
- **Workstation trust.** An accepted channel covers the same vendor and
  terms across versions and projects, within the accepted origins.
  `config trust list|accept|withdraw` manages that record.
  Existing matching per-checkout consents remain valid, including after trust
  withdrawal. The channels come from the checkout's selected lock, so a
  personally added agent's channel can be accepted. Changed host
  recommendations do not replace recorded answers. [Vendor software and trust](https://devcapsule.mycodespace.ai/docs/current/configuration/software-approvals/).
- **Console configuration requests.** A console-capable base shows the
  listing captured at launch, its timestamp, and later request results.
  The attached launcher validates and records supported requests for the next
  launch. Grants, trust acceptance, bindings and replacement Docker arguments
  require host confirmation. `config console list|apply|discard` handles them.
  Noninteractive launches leave those requests pending.
  The console cannot edit shared declarations or workstation resource defaults.
  Nothing reconfigures the running capsule.
- **Compatibility spellings.** Most old spellings are hidden from parent
  help, but several still execute and can write files. `config need` and the
  old shared-policy flags refuse with replacements. `run --force` is ignored
  with a note; `run --force-config` is an unrecognized argument.
  `init --less-pedantic` remains accepted. The
  [command reference](https://devcapsule.mycodespace.ai/docs/current/reference/cli/)
  lists each retained form and its behavior.

## New in candidate 8

- **`project init --regenerate` migrates the manifest.** A manifest
  written in schema 1 is rewritten as schema 2 beside the regenerated
  lock: `need` becomes `required`, the IDE it named becomes the project's
  IDE recommendation, which every checkout without an IDE choice gets by
  default and may change, the removed SDK-major table and the old
  `workflow-type` key are dropped, and everything else is carried as it
  was. The leading comment block of the file is kept; comments elsewhere
  are not, and the report says so. A schema-2 manifest is left as it is.
  No other command rewrites a schema-1 manifest; a plain `init` refuses to
  append a recommendation to one and names `--regenerate` (2026-10-26).
- A manifest that requires two IDEs cannot be migrated; the launcher says
  so and the owner removes one by hand first.
- Locks written by launchers before 0.3.0 keep running as records, as
  before; locks of this cycle are checked against the project's
  requirements as before.

Candidate 8 carries candidate 5's gaps unchanged.

## New in candidate 7

- **The published base carries the web console.** The default base is
  now `ubuntu-24.04@11`, published as `mycodespaceai/devcapsule-base:v0.3.0.rc6`.
  A project lock regenerated with this candidate, `devcapsule project
  init --regenerate`, moves to it and every checkout of that project
  gets the console at its next launch, after the one-time trust question
  for the base channel on each workstation. Existing locks keep their
  recipe-9 base and run as before, without a console; a local base is no
  longer needed to have one (2026-10-25).
- The lock's base table records the recipe's source path, so the
  authorization prompt links the recipe the base was built from. Older
  launchers read the new lock.

Candidate 7 carries candidate 5's gaps unchanged.

## Fixed in candidate 6

- **The console's configuration page works again.** In candidate 5 the
  web console's configuration page ran `config list`, retired by that
  candidate, and showed its refusal instead of the configuration; the page
  and the launcher's in-capsule hints call `config show` now (2026-10-25).

Candidate 6 carries candidate 5's gaps unchanged.

## Not in candidate 5

Shared-memory passthrough remains incomplete against the redesign. The
`--print-command` path can still materialize images and write caches; use
`config show` or `config check` for read-only inspection. `init` still asks
per-checkout consent for the base and the agent downloads without a
terminal even when the channels are trusted; pass `--authorize base-image
default` and the download consents, or run it at a terminal.

Planned for later candidates: diagnostics snapshot and export, obsolete
image and cache cleanup, and release-notes automation.
Outside 0.3.0: installed-IDE reuse with an empty launcher cache, browser
evidence for diagnostics, console materialized views, and ecosystem-aware bootstrap.

## Not in candidate 4

Shared-memory passthrough remains incomplete against the redesign.
Candidate 5 completes the retirement of `init --less-pedantic` and the old
force options; the retired-spelling entry above records the replacement rule.
The `--print-command` path can still materialize images and write caches;
use `config show` or `config check` for read-only inspection.

Planned for later candidates: diagnostics snapshot and export, obsolete
image and cache cleanup, and release-notes automation.
Outside 0.3.0: installed-IDE reuse with an empty launcher cache, browser
evidence for diagnostics, console materialized views, and ecosystem-aware bootstrap.

## Not in candidate 3

Planned for later candidates of this cycle: forced configuration, `project config resolve --force` and
`project run --force-config`; the diagnostics snapshot and export command;
the manifest's schema version 2 for the `required`/`optional` vocabulary;
cleanup of obsolete images and cached files; release-notes automation.
Out of 0.3.0: consent and vendor trust, installed-IDE reuse with an empty
launcher cache, browser evidence for diagnostics, the console's
materialized views, ecosystem-aware bootstrap.
