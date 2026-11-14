# Workstream Current Status: Capsule Web Console

Mnemonic: `capsule-webconsole`

Start date: 2026-10-09

State: active; the fix for a video opened from Files awaits the owner as a pull request from `ws-capsule-webconsole/video-in-files` to `release-0.3.1`; the presentations slice of 2026-11-14 was merged into `release-0.3.1` as #34; before it, slice 8 and the test-isolation fix await the owner with the second iteration: PR5 (#192), PR6 (#194), PR7 (#196), PR8 (#199), PR9 (#201), PR10 (#203) and PR11 (#205), stacked, each with its Codex review merged

Definition read: WORKFLOW.md@2b576adb1a40, WORKFLOW-LOCAL.md@7362bae8ec82

Branch association: `ws-capsule-webconsole/video-in-files` (2026-11-14, from `release-0.3.1` at `27985163`, see Current State); `ws-capsule-webconsole/presentations` (2026-11-14, merged into `release-0.3.1` as #34); `ws-capsule-webconsole/live-resources` (PR5, #192, from `main`); `ws-capsule-webconsole/records` (PR6, #194, stacked on PR5); `ws-capsule-webconsole/decisions` (PR7, stacked on PR6); the first iteration's branches `first-slice`, `console-app`, `runtime-base` and `project-info-checkout-name` are merged and closed

Integration target: `main`

Delivery method: pull request, merge commit

Requirements: `R-CONSOLE-001`

Work order: [the capsule web console](../../work-orders/2026-10-09-capsule-webconsole.md), issued 2026-10-09 by `project-management`; its DOT and materialized-views amendments are in intake, and the amended text is on `project-management`'s branch until its next integration

## Goal And Scope

Every capsule serves a web console on a token-gated loopback port, whenever
the runtime runs, with or without a display. The console shows what the
`devcapsule` commands report, as HTML: the configuration, the versions, the
project information, and live process and resource data from inside the
capsule. Later slices render the repository's records and workflow state and
host the decision pages the workflow's human-input rules allow.

Owner decisions of 2026-10-09 that shape the work:

1. The console lives in the base image for every adopter. It is not a
   component and not a selectable capability. A headless user reaches it
   with an SSH port forward.
2. Architecture: a static web structure plus a FastAPI application for
   dynamic data. The console is a separate process, not part of the runtime
   PEX. It reads the mounted project and calls the runtime CLI's `--json`
   outputs as its API.
3. No existing open-source console is adopted as the framework. Glances or a
   similar tool may become an optional component later, linked from the
   console, but the configuration, records and workflow pages are ours and
   no product renders them.

## Current State

**2026-11-14, a video opened from Files plays.** Asked for by the owner in
session, after the presentations slice was merged as #34.

- The defect and its cause:
  [the bug record](../../bugs/devcapsule/2026-11-10-console-video-opened-from-files-does-not-play.md),
  filed on `ws-project-management/coordination` and brought to this branch
  with its fix recorded, `status: fixed`.
- The fix is the record's proposal: the Files page plays a video or audio
  file itself at `/files/<path>`, the tree route says which files those are,
  and the raw route is unchanged. A link in a record to a file that is not
  Markdown now leads to `/files/<path>`.
- Branch: `ws-capsule-webconsole/video-in-files`, from `release-0.3.1` at
  `27985163`; its pull request targets `release-0.3.1`.
- Checked: `nox -s webconsole`, `nox -s tests`, and the page in headless
  Chromium against the preview. Not checked: Chrome with a built
  executable, which the record's close criteria ask for; audio in a
  browser; a symbolic link to a recording, which the fix does not cover.
- The record's copy on `ws-project-management/coordination` still says
  `confirmed`; that branch's integration will meet this version.

**2026-11-14, presentations: a recorded scenario as slides beside its recording.**
Ordered by the owner in session, in four parts, after a recorded end-to-end
scenario proved too fast to follow and had no captions.

- The page: `/presentations/<folder>` shows a folder that holds a
  `presentation.json` as an overview slide and one slide per step, each with
  the script's text, the screenshot and a button that plays only that step's
  part of the one recording, with captions, at half speed by default; Play
  all runs the recording through. `/presentations` lists the project's
  presentations and is linked from the top band and from Home; Files offers
  the link on such a folder. Contract and behaviour:
  [PRESENTATIONS.md](../../../devcapsule-webconsole/PRESENTATIONS.md).
- The preview: `nox -s webconsole-preview` serves the checkout's console on
  loopback and logs its links, the sample presentation among them.
- The generator: a replay writes `presentation.json` itself from the
  scenario's script, its numbered actions and the recorder's frame counts
  (`devcapsule-src/tests/e2e/scenario_presentation.py`); the author's side
  is section 5 of
  [running scenario recordings](../../development/running-e2e-scenario-recordings.md).
- Branch: `ws-capsule-webconsole/presentations`, on top of `bd2f4d1c`, the
  head of `ws-maintenance/e2e-scenario-evidence`, because the generator
  changes the recorder files that branch added. Pull request #33 merged
  that branch into `release-0.3.1` on 2026-11-14 with no other change, so
  this branch's pull request targets `release-0.3.1` and shows this slice
  alone. The release line is not `main`, this workstream's usual target:
  the slice reaches `main` when the release line does. The two console
  commits touch only files that are identical on `main`, should the owner
  want them there sooner.
- Checked: `nox -s webconsole` (473 passed), `nox -s tests` (3262 passed),
  `nox -s typecheck`, the docs contract, and the page in Chromium. Not
  checked: `nox -s build`, and a new recording, which needs Docker; the
  generator was run on the 2026-11-13 run's frame counts instead and
  reproduced the hand-written sample.
- Left open: the top band is crowded and the owner wants its navigation
  reorganized later; `scenario-video.webm` does not state its length,
  because `ffmpeg` writes it to a pipe; the bug record
  `2026-11-10-console-video-opened-from-files-does-not-play` is untouched,
  since a video opened from Files still goes to the raw route.

**2026-10-10, PR11: every test gets an empty artifact cache of its own.**
The owner's plain `pytest` run filled a 2 GB `/tmp`. Diagnosed with one
command each: `cache_root()` follows `XDG_CACHE_HOME`, which a capsule
exports as the developer's real cache, 7.2 GB here; the `checkout`
fixture of `tests/test_upgrade_recovery.py` and four fixtures in
`tests/test_project_commands.py` and `tests/configuration/test_history.py`
redirect the other XDG homes but not the cache; and `_retain` in
`version_sets.py` copies every locked artifact, the 1.2 GB PyCharm
tarball among them, from that cache into each resolving test's state.
One test's two cases wrote 2.4 GB in 7 s, and 68 KB with an empty cache;
the unit suite wrote 3.7 GB per run, and pytest keeps three runs. The
test, its fixture and the retention step date from 2026-09-20 and 21,
on `main` since; the gate's many runs from a capsule made it visible.
The fix, by the owner's direction and stacked on PR10: one autouse
fixture in the root `tests/conftest.py`, beside `host_launch_by_default`
which exists for the same reason, points `XDG_CACHE_HOME` at an empty
directory under `tmp_path` for every test without a Docker marker. The
unit suite now writes 37 MB and runs in 28 s instead of 74 s.

**PR #205 is open against PR10's branch. Its review, PR #206 by the Codex
and gpt-6-astra pair, was merged without a round.** The fixture, now
`private_user_directories`, gives every non-Docker test private `HOME` and
every XDG directory under its `tmp_path`, not only the cache; a regression
test runs the real conftest under pytester for both inherited layouts, a
laptop without exported XDG paths and a capsule with them, proving that
retention reads and restoration writes stay private, that a test's own
fixture still wins, and that the Docker-marked suites keep their inherited
directories; the Docker marker list is pinned to `pyproject.toml`. The
measurements used a synthetic artifact, never the real cache. Gate on the
merged branch below.

**Follow-up, 2026-10-10.** The owner's plain `nox -s build` still left 900 MB
under `/tmp`: the widened fixture had moved `~/.cache/pex` and
`~/.cache/nce` under each test's scratch, so the three clean-revision
builds of the integration session downloaded the scie launcher and its
Python again and unpacked them per case, 872 MB and 145 s for the session.
Both are build tools' content-addressed caches, not DevCapsule state; the
fixture now pins `PEX_ROOT` and `SCIE_BASE` to the inherited cache before
the homes move, with the regression test asserting both. Measured after:
the integration session 134 MB and 43 s, and a plain `nox -s build`
leaves 175 MB under `/tmp/pytest-of-<user>` (36 unit, 134 integration,
7 console) in 2 minutes. The Codex pair reviewed the pins commit as a
round on #205 and accepted it: the helper matches pex 2.97.1's and
scie-jump 1.11.2's own cache defaults on both Linux layouts, no other tool
cache fills the private home beyond 1.3 MB of pip metadata, and each
regression assertion fails when its pin is removed.

Judgments recorded for PR11:

- Hermetic in both directions: the real cache was read by tests, and
  `_restore_artifacts` could have written fixture bytes into it on a
  machine with a partial cache. A test that wants a particular cache sets
  the variable itself, after the fixture, as `test_version_sets.py` does.
- The Docker-marked suites keep the real cache: their base builds would
  download every artifact again.
- Not fixed here: the artifact path under the state home nears the NTFS
  260-character limit under a Windows profile. A state-layout question for
  the owner of version sets; see Open Threads.

**2026-10-09, slice 8, workflow half (PR10).** The rule: topic 8.8 of
this repository's `WORKFLOW.md`, "Handing a decision to the human", five
sentences, with a pointer in `AGENTS.md`; the shipped definition under
`devcapsule-src/devcapsule/assets/project_workflow/definition/` has
another layout and belongs to workflow-improvements, which gets the same
text at its next sync (noted in Open Threads). One CLI for agents:
`devcapsule project checkout decisions from-table | check | hand-off`
runs the console's installed module inside a capsule, the mounted source
first when the runtime plan names one, and outside a capsule says where
the module is. The first real decision: the 38 undecided items of
project-management's intake, as one document in this capsule's decisions
directory, with its table and hand-off text under
`evidence/2026-10-09-intake-pass/`; this capsule runs no console, so the
hand-off here names the page, and the owner's next launch on a base with
the console lists it under the bell.

**PR #203 is open against PR9's branch. Its review, PR #204 by the Codex
and gpt-6-astra pair, was merged without a round.** Five findings, all
accepted: an unreadable plan with invalid UTF-8 falls back to the
installed console; an interpreter that cannot start is the CLI's refusal,
not a traceback; the wrapper's passthrough is proven on exact arguments;
the rule was rewritten so outcomes are recorded under topics 8.2, 8.3 and
12.7 before any deletion, unanswered items stay pending, and intake
decisions use 8.2's acknowledge-or-forward instead of the builder's
defaults; and the Unreleased entry and the humane paragraph that
WORKFLOW-LOCAL requires accompany the rule. That last rule reached the
first real decision: the intake pass was regenerated with acknowledge and
forward per item, in the capsule's state and in the evidence. Gate on the
merged branch below.

Judgments recorded for slice 8's workflow half:

- The rule lives in this repository's copy by the owner's word; the
  shipped definition is another workstream's file.
- The wrapper runs the console's module rather than importing it: the
  console is not in the runtime PEX by binding decision 2, and the
  subprocess boundary stays the contract.
- The decision document is capsule state and is not committed; the table
  and the hand-off text are evidence of the mechanism, as for the sample.

**2026-10-09, slice 8, console half (PR9).** The hand-off:
`python -m devcapsule_webconsole.decisions hand-off <decisions-dir>/<id>.json`
prints a decision as chat text, every item numbered with its options by
key, ending with the link `$DEVCAPSULE_CONSOLE_URL/decisions/<id>?token=…`
from the launcher's origin and the mounted token file; without the origin
the text says the console is not reachable, without a readable token the
link goes out bare. Notifications in the console: `/api/notifications` is
the runtime CLI's listing with the pending decisions merged in, read and
dismiss go back through the CLI, same-origin only, the CLI's refusal is a
422 and its failure a 502; a bell on every page shows the unread count and
the newest five, polled every 30 seconds; the `/notifications` page lists
everything with mark-read and dismiss, a decision entry linking to its
page. Browser run against this checkout with the real CLI and a scratch
store: three unread under the bell, the page listed them, read and dismiss
went through the CLI and the page refreshed; screenshots
`notifications-*.png` under `evidence/2026-10-09-console-pages/`, the
hand-off text under `evidence/2026-10-09-decision-sample/hand-off.txt`.

**PR #201 is open against PR8's branch. Its review, PR #202 by the Codex
and gpt-6-astra pair, was merged without a round.** Six findings, all
accepted: the console's selected decisions directory now reaches the
CLI's listing through its environment hook, so the bell and the decision
pages cannot disagree; the hand-off keeps multiline fields and
double-digit items aligned and refuses a non-JSON path instead of
silently taking a sibling; the badge hides at zero; the bell exposes its
state, closes on Escape and clears the unread emphasis when polling
fails; the texts say what the console writes; 42 more tests including a
Node run of the notifications page. One more fix of ours from the
browser check on the merged branch: a page action now refreshes the bell
at once instead of waiting for the 30-second timer; screenshot
`notifications-merged.png`. Gate on the merged branch below.

Judgments recorded for slice 8's console half:

- The console renders the CLI's listing and never reads the notifications
  directory itself: one source of truth, and the subprocess boundary stays
  the console's contract, as for configuration and versions.
- The bell polls, every 30 seconds, one small request. A push channel
  waits for the notification system the owner deferred.
- The link carries the token: the launcher already prints it on the host,
  the cookie is a session cookie, and the hand-off text says the link
  belongs in the chat and never in a record.
- The console's writes are three, all into capsule state; the docs say so
  in place of "one write".

**2026-10-09, slice 8, runtime half (PR8).** The launcher passes
`DEVCAPSULE_CONSOLE_URL`, the console's host-side origin without the
token, into the capsule, so an agent can end a decision hand-off with a
link; `project info` names the value. A notifications store,
`devcapsule/notifications.py`: one JSON file per notification under
`$XDG_STATE_HOME/devcapsule/notifications/`, the checkout's state beside
the decisions directory, never a record; validation names its field,
reads are bounded and never follow a link, writes are atomic. The listing
merges unanswered decisions as the kind `decision` and never copies them.
A `notifications` group under `project checkout` lists, posts, reads and
dismisses; inside a capsule it acts on the capsule's own state whatever
`--path` says, on the host it finds the checkout's persistent home as
`project info` reports it.

**PR #199 is open against PR7's branch. Its review, PR #200 by the Codex
and gpt-6-astra pair, was merged after one round.** Eight findings, all
accepted: the store pins every path component below a resolved base
without following links, so a link an agent plants in the persistent home
cannot send a host command into another checkout; temporary files are
exclusive and 0600; the encoded size is checked before any write; links
stay on the console's origin, refusing `//` and backslashes; decisions are
read under their own 1 MiB limit with their metadata and answer envelopes
validated, invalid ones listed as errors; the modification time comes from
the descriptor that was read; every filesystem failure is the command's
refusal; and 60 more tests. The round: the first version of finding 1
refused a HOME that is a symbolic link, or an override through one, as
"Not a directory"; the environment-named base is now resolved before
pinning, with two tests. Gate on the merged branch below.

Judgments recorded for slice 8's runtime half:

- Under `project checkout`, not `project`: the store is keyed by the
  checkout through the persistent home the launcher mounts, and the
  workflow's vocabulary makes a checkout one clone with one workstream.
- `CapsuleAccess.INDEPENDENT` for every leaf: the writes go to capsule
  state only, so the vocabulary of refusing inside a capsule does not
  apply, and an agent inside must be able to post.
- Decisions are merged at listing time, never copied; `read` and
  `dismiss` refuse a decision and say how it is settled.
- The token never enters the environment: the origin is enough for a
  link once the hand-off command adds the token from its file, and the
  browser's cookie carries it afterwards.

**2026-10-09, slice 7: decision pages (deliverable 5).** The contract is
`devcapsule-webconsole/DECISIONS.md`: an agent writes `<id>.json` into the
capsule's decisions directory, `$XDG_STATE_HOME/devcapsule/decisions` by
default; the console lists and renders it, the human chooses, the console
writes `<id>.answer.json` beside it, and the agent reads the answer,
records the outcome in the normal files and deletes both. A decision has
a title, who asks, a markdown context, and items, each with a summary,
records cited as paths, two or more options, and single or multiple
choice. `python -m devcapsule_webconsole.decisions from-table` builds a
decision from a markdown table, so any agent can produce one; `check`
validates a document and its answer. The answer route is the console's one
write: same-origin only, on top of the `SameSite=Strict` cookie, and a
refusal writes nothing. Run by hand with two intake items as a sample: the
page rendered, a browser answered it, the answer file holds the choices;
see [evidence/2026-10-09-decision-sample](evidence/2026-10-09-decision-sample/).

**PR #196 is open against PR6's branch. Its review, PR #197 by the Codex
and gpt-6-astra pair, was merged without a round.** Eight findings, all
accepted: the answer's temporary file is created exclusively, so a planted
symlink cannot redirect the write into a record; decision and answer reads
open regular files only, never following a link, bounded at 1 MiB; the
answer route requires exactly one `Origin` equal to the console's and
checks the 64 KiB limit per chunk; JSON refusals and validation refusals
are separate, so a refusal names the real fault; `format` must be the
integer 1, timestamps must be ISO 8601, and a stored answer without one is
refused rather than given the current time; the table builder keeps empty
edge cells and requires unique columns and a separator row; the page shows
the title as a heading, resolves record links from the project root and
treats an item keyed `constructor` correctly. 56 more tests, including a
Node run of the page script against the real renderer. Re-checked in a
browser on the merged branch: the sample decision rendered with its
heading and record links, a submission wrote the answer file with mode
0600, safe because the console child runs as the capsule identity, the
agent's own user; screenshots `decisions-merged-*.png` under
`evidence/2026-10-09-console-pages/`.

Judgments recorded for slice 7:

- The answer lands under XDG state inside the capsule, never in the
  project. The first use is project-management's intake pass, and nothing
  the console writes may become a record by accident.
- The console never deletes a decision or an answer: discarding is the
  agent's step after it has recorded the outcome, so the human can submit
  again until then and the latest answer stands.
- The contract is one JSON object with a table-shaped item list, and the
  table builder is part of the package, which is the "small enough to
  produce from a markdown table" test of the work order.
- Markdown in a decision renders with the same settings as a record: no
  raw HTML, no active links from the content.

**2026-10-09, slice 6: records and DOT (deliverable 4).** Any markdown file
in the project renders in the browser: `index.md` is the front page, a
record's relative links are rewritten to stay inside the console, a fenced
`dot` block renders as a Graphviz diagram, and images and other linked
files are served raw through a new bytes route confined like the text one.
The renderers are vendored browser builds, `markdown-it` 15.0.2 (the
website's) and `viz.js` 3.31.0, with their provenance and digests in
`VENDORED.md` and a test that checks the digests. Run by hand against this
checkout: the index renders with its 283 links rewritten, and this status
file renders with its DOT stack diagram drawn.

**PR #194 is open against PR5's branch. Its review, PR #195 by the Codex
and gpt-6-astra pair, was merged without a round.** Six findings, all
accepted: the wheel omitted the vendored renderers, so a capsule's
installed console would have had none, now packaged and tested; raw
responses carry a sandbox policy and `nosniff`, so an opened SVG cannot
use the console's origin; Graphviz output is shown as an image, so a DOT
`URL` attribute cannot become an active link; record links are decoded
once, query-only links and raw fragments are kept, invalid targets become
inert; headings have fragment targets; and more coverage of the raw route
and the bytes reader. Re-checked in a browser on the merged branch: the
diagram renders as an image, headings carry ids, raw responses carry the
headers.

Judgments recorded for slice 6:

- Raw HTML inside a record is not rendered (`html: false`): a record is the
  project's own text, but the console's origin carries the run token in a
  cookie, and no project file may run as a page in that origin. For the same
  reason the raw route serves HTML and scripts as plain text.
- A link to a `.md` file goes to the records page; any other relative link
  goes to the raw route; absolute URLs, root paths and fragments are left as
  written. A link that climbs above the project is left as written too, and
  the server refuses it.
- The page is one static file for every record path; the script reads the
  path from the URL. No server-side rendering, no template engine.
- DOT only, as the owner decided; a block in any other diagram notation is
  shown as code.

**2026-10-09, slice 5: live processes and resources (deliverable 3).** The
owner merged #184 and #190, so the first iteration is on `main`, and
directed the second iteration, deliverables 3, 4 and 5. This slice adds a
monitor module to the console: psutil for the processes, each with its CPU
share over a short interval and its resident memory; the cgroup v2 root for
the capsule's CPU time against its quota or the host's CPUs, its memory
charge against its limit, and its process count. Two `GET` routes serve the
readings and a Processes page refreshes them every three seconds, with a
pause. psutil joins the console's hash-pinned set, so base recipe 11
rebuilds the console venv; an older base runs the previous console. Run by
hand against this capsule: the page renders the real readings.

**PR #192 is open against `main`. Its review, PR #193 by the Codex and
gpt-6-astra pair, was merged without a round.** Eight findings, all
accepted: psutil's cached process objects shared CPU baselines between
concurrent requests, now per-request CPU-time deltas with an identity
check; a reused pid could stand for another process; the host's cgroup
root could pass as the capsule's; reset counters gave negative rates;
denied processes vanished instead of showing null CPU; the page's pause
raced its refresh; the pid meter counts tasks, now labelled so; and a
recipe 10 base now runs its installed console instead of mounted slice-5
source it cannot import, with a probe that says why.

Judgments recorded for slice 5:

- CPU use is a rate over a quarter second, measured on the server at each
  request, against the CPUs the capsule may use: its quota when it has one,
  the host's count otherwise. Memory is the cgroup's current charge against
  `memory.max`, unlimited shown as such.
- Outside a cgroup v2 root the resource reading says it is unavailable,
  with every figure null; the process list still works. A host-run console
  therefore shows processes and no meters, and says why.
- The process list omits a process that ends during the sample and shows
  one it may not fully read without the fields it could not read.
- The dependency change bumps the base recipe to 11: the self-hosting
  source mount cannot add a dependency to the image's venv, so a capsule
  with the recipe 10 base runs the console without the monitor's module.

**2026-10-09, evening: integration state.** The owner merged #184 to
`main`, then #186 into `ws-capsule-webconsole/first-slice` and #188 into
`ws-capsule-webconsole/console-app`, after those branches had been merged
below them. `main` therefore carries slice 1 only; the two merges put
nothing new on `main`. PR4's branch descends from all three slices; `main`
was merged into it and #190 was retargeted to `main`, so it carries slices
2, 3 and 4 together. The owner merges it.

**2026-10-09, slice 4: `project info` names the checkout from its record's
location.** The owner moved the defect found in slice 2 from `maintenance`
to this workstream. One helper, `checkout_name_for`, derives the name from
where the record lives, and `config list`, `project info`, the launch
context and the checkout registry all use it. The text report of
`project info` gains a `Checkout name:` line. Inside a capsule the name
comes from the mounted record, so a context captured by an older launcher
reports it right without a relaunch. Verified against this capsule's real
records: `project info` and `config list` now both say `devcapsule-2nd-home`.
The console's home page shows the right name with no change of its own.

**PR #190 is open against PR3's branch. Its review, PR #191 by the Codex
and gpt-6-astra pair, was merged without a round.** No behavior change:
the captured name is computed once, the helper and the runtime property
state the name's provenance precisely, and coverage gained the captured
fields before the runtime override, older contexts with and without
captured information or the recorded name, the registry with an explicit
environment, and the registered default checkout's name. The gate on the
merged branch is recorded below.

Judgments recorded for slice 4:

- `configured_information` takes the name as a required argument instead of
  reading a key no writer puts in the record. The callers know the record's
  location; the information module does not.
- An unregistered checkout is named `default`, the name its first `config
  list` would give the record it materializes.
- The runtime report overrides the captured name rather than trusting it,
  because every context captured before this fix says `default`.

**2026-10-09, slice 3: the console runs and is reached.** The runtime plan
gained a `console` section, like the display's: a listen address, a port
and the token path, plus an optional `source_path` for the self-hosting
exception. The launcher allocates a host loopback port and a per-run token
whenever a runtime plan is launched, with or without a display, mounts the
token read-only, publishes the port off host networking, prints the console
URL, and watches readiness. The entrypoint starts the console as a supervised
child beside the display's children, or alone in a headless job. Base recipe
10 installs the console under `/opt/devcapsule-webconsole`: a venv built at
image build from the subproject's hash-pinned files, the package itself from
the same public revision as the runtime, fetched with git so the commit hash
verifies the content. The smoke of deliverable 1 is an end-to-end test with
and without a display, and the IDE smoke rows gained "console answers". A
user page documents the console link, the token and the SSH forward.

**PR #188 is open against PR2's branch. Its review, PR #189 by the Codex
and gpt-6-astra pair, was merged without a round.** Seven findings, all
accepted: two released sockets could hand the console the display's port,
now retried; the readiness probe for an IPv6 wildcard listener used IPv4;
the base installer expanded the source identity as shell code, now quoted
and executed with stubs in seven integration cases; an unknown source
identity reached the base builder, now refused before the build with a
message naming the published-source PEX; the opener test could pass
without opening, replaced by a deterministic one; coverage of token-file
failures, cleanup and contract edges; and two corrections to the user page.
The gate on the merged branch and the smoke rerun are recorded below.

Judgments recorded for slice 3:

- One page opens by itself. With a contained display the desktop opens and
  the console is announced as ready, not opened; two tabs for one run would
  be noise. Without a desktop the console opens, so a headless or
  passthrough run still lands the developer on one page. The owner can
  flip this.
- The console runs whenever a runtime plan is launched. There is no option
  to turn it off, because the work order makes it part of every capsule;
  an older base without the console is announced and skipped, not refused,
  since the runtime is launcher-supplied and runs on any base with the
  display label.
- The self-hosting exception is mechanical: when the launched project
  carries `devcapsule-webconsole/devcapsule_webconsole/`, the console child
  runs that source ahead of the image's copy through `PYTHONPATH`, with the
  image's interpreter and dependencies, and says so. No separate mount: the
  project is already mounted. Any other project runs the base's console.
- The base fetches the console's source with `git fetch` by commit, which
  verifies the content against the hash; an archive download would not.
  The build toolchain is hash-pinned too, in `requirements-build.txt`, so
  the venv install fetches nothing unpinned.
- The console's readiness timeout is 60 s, three times the display's:
  FastAPI's import on a cold host is slower than an X server's start.

**2026-10-09, slice 2: the console subproject.** `devcapsule-webconsole/`
is a second distribution: a FastAPI application, a static tree and tests,
with hash-pinned runtime and development requirement sets. It serves the
home, configuration, versions and project pages from the runtime CLI's
`--json` documents, read by running the CLI. Every request carries the run
token or is refused, static files included; the token arrives in the printed
URL and is kept in a cookie. File reads resolve inside the project mount
only. Every route is `GET`. A new nox session, `webconsole`, type-checks and
tests it in its own environment, and the build gate queues that session.
Run by hand against this capsule's real CLI, all four pages render; the
screenshots are under [evidence/2026-10-09-console-pages](evidence/2026-10-09-console-pages/).

**PR #186 is open against PR1's branch. Its review, PR #187 by the Codex
and gpt-6-astra pair, was merged without a round.** Seven findings, all
accepted: a time-of-check race on the project-file route, closed with
descriptor-anchored `O_NOFOLLOW` reads; a malformed cookie header crashing
the gate; a non-object or non-finite JSON document passing through the
reader; token characters an unquoted cookie cannot carry; the nox session
picking the runtime's mypy configuration instead of the console's strict
one; tighter types; and 37 added tests, 89 in all. The gate on the merged
branch is recorded below.

Judgments recorded for slice 2:

- The console does not import the runtime. Its API is a subprocess call
  per document, uncached, so a change made with a command is on the page at
  the next reload, as deliverable 2 asks.
- The token is carried three ways: the query parameter from the printed URL,
  the cookie the console sets in answer to it, and a header for scripts. A
  valid query token sets the cookie `HttpOnly; SameSite=Strict`. Comparison
  is constant-time.
- Path confinement refuses any `..` component, an absolute path, a NUL, and
  a symbolic link that resolves outside the mount. The project-file route is
  the foundation of deliverable 4; in this slice it serves UTF-8 text only.
- The console takes the CLI executable as an explicit argument. The shipped
  PEX has a fixed path, but the command name is `devcapsule0` in a
  self-hosting capsule, so guessing from PATH would be wrong there.
- The subproject has its own environment and nox session, never the
  runtime's: FastAPI's dependency set would otherwise be pinned twice.
- Pages are static HTML with one script that builds the DOM from the
  documents with `textContent` only. No template engine, no build step.
- The identity block on the home page composes `project info` and
  `versions show`; see the open thread on the checkout name.

**2026-10-09, slice 1: the JSON contract.** `config list --json` and
`versions show --json` exist, with schema version 1, on the host and inside a
capsule. The text reports render from the same documents, so the two cannot
disagree. The work order's three mail items are accepted as the goal and
dispositioned. R-CONSOLE-001 is accepted, as the work order asked for the
first integration. The user documentation names the flags. The build gate
ran on this branch before the checkpoint; see *Validation And External State*.

**PR #184 is open against `main`. Its review, PR #185 by the Codex and
gpt-6-astra pair, was merged into the branch after one round.** The review
found one regression #184 had introduced: the next-launch identity was
computed outside the error boundary, so a malformed local selection hid the
running session. It also found a pre-existing confusion of a named checkout
called `devcapsule` with the default checkout, now fixed on both sides of
the mount with a `checkout-name` field in the launch context. The one
round asked for validation of that optional field beside its neighbours;
the pair delivered it with five rejection cases. The pair's gate and this
workstream's gate on the merged branch are recorded below.

Judgments recorded for this slice:

- Inside a capsule, `config list --json` carries the mounted checkout record
  and the launcher command, not the table's rows. The text report does the
  same. The rows are computed against the host: a binding row checks a host
  directory and a secret row checks the launching shell's environment, and
  neither is observable from the capsule. A row computed here would state
  something false about the host. The console's configuration page renders
  the record in a capsule and the rows on a host.
- The JSON shape rule, written beside the schema constants: adding a key
  keeps the version; renaming, removing or retyping one bumps it.
- One help text for every stable `--json` flag, shared from the command
  framework, names the console as the reader.
- `versions show` gained `--json`; `check`, `history` and the rest did not.
  The work order leaves further flags to the page that needs them.

### How the work runs

The owner's instructions of 2026-10-09, given at the switch, are an exception
to the human-input rule for this iteration. The agent implements the work
order's first iteration, deliverables 1 and 2, without stopping for
decisions. Stopping points become written proposals in the pull request.
Two limits stay: no write operation beyond deliverable 5's answer file, and
no reach beyond the loopback port and the run token. The owner merges to
`main`; the agent never does.

The slices are stacked pull requests, each reviewed by a second agent pair
before the next one starts:

```dot
digraph stack {
  rankdir=LR; node [shape=box];
  main -> "PR1 json contract" -> "PR2 console subproject" -> "PR3 runtime and base" [dir=back];
  "PR1 json contract" -> "PR1.1 review" [dir=back, style=dashed];
  "PR2 console subproject" -> "PR2.1 review" [dir=back, style=dashed];
  "PR3 runtime and base" -> "PR3.1 review" [dir=back, style=dashed];
}
```

- PR1, this branch: `--json` on `config list` and `versions show`.
- PR2, on PR1's branch: the `devcapsule-webconsole/` subproject with the
  token gate, path confinement, and the home, configuration, versions and
  project pages.
- PR3, on PR2's branch: the runtime child, port and token wiring, base
  recipe 10, the development mount, the fresh-capsule smoke and the IDE
  smoke column.
- Each PRn.1 is written by the Codex and gpt-6-astra pair from a
  `-review` branch off PRn's branch, aimed at clarity, correctness and test
  coverage of PRn's lines. This workstream reviews it in PR comments and
  merges it into PRn's branch, or pushes back, at most three rounds, then
  waits for the owner. PRn+1 starts only after PRn.1 is settled.

## Planned Next Step

1. PR5, #192: deliverable 3.
2. PR6, #194, on PR5's branch: deliverable 4.
3. PR7, on PR6's branch: deliverable 5, this branch.
4. Done: a base rebuild from PR7's revision and the console smoke with the
   records and decision probes; see Validation below.
5. Slice 8, directed by the owner on 2026-10-09 after reviewing #196: the
   decision pages need a hand-off and a home. Three stacked PRs on PR7's
   branch, each with its Codex review:
   - PR8, runtime: the launcher passes `DEVCAPSULE_CONSOLE_URL`, the
     host-side console origin without the token, into the capsule; a
     `notifications` group under `project checkout` with `list`, `post`,
     `read` and `dismiss` over a store at
     `$XDG_STATE_HOME/devcapsule/notifications/`, the checkout's state
     beside the decisions directory; the listing merges unanswered
     decisions as the `decision` kind, never copying them.
   - PR9, console: a bell in the header with the unread count, a dropdown
     with the top items and a `/notifications` page; read and dismiss
     through the CLI as further writes into capsule state only; a
     `decisions` group under `project checkout` that runs the console's
     installed module, so an agent sees one CLI; `hand-off` prints the
     numbered text for chat and a closing line with the tokened link,
     which the cookie then carries for every later request.
   - PR10, workflow: done on `ws-capsule-webconsole/hand-off-rule`; see
     Current State.
6. Deliverable 6, materialized views, in a third iteration.

The first iteration is on `main`: #184 and #190, merged 2026-10-09. On resumption, after the owner's merges or push-backs, the
next iteration is deliverables 3 and 4 in the order this workstream
chooses, then 5, then 6.

Done in the first iteration:

1. PR1, #184: `--json` on `config list` and `versions show`.
2. Done in PR2: the console subproject, runnable on a host against the installed
   CLI, with its unit tests.
3. PR3: deliverable 1's runtime and base work, with the smokes. Propose the
   base-release trigger in that pull request.

Later iterations: deliverables 3 and 4 in the order this workstream chooses,
then 5, then 6.

## Validation And External State

- Slice 5 console session: strict mypy on 7 files, 100 tests. Build gate on
  PR5's branch, 2026-10-09: 1,329 unit cases, 17 packaged integrations,
  type check, smokes, documentation contract, then the console session;
  successful. Manual run against this capsule: the Processes page renders
  the real readings; screenshot under `evidence/2026-10-09-console-pages/`.
- Slice 6 console session: strict mypy on 7 files, 138 tests. Build gate on
  PR6's branch, 2026-10-09: 1,333 unit cases, 17 packaged integrations, type
  check, smokes, documentation contract, then the console session;
  successful. Manual run against this checkout: records index
  and this status file rendered in a browser, DOT drawn; screenshots under
  `evidence/2026-10-09-console-pages/`.
- Slice 7 console session: strict mypy on 8 files, 182 tests. Build gate on
  PR7's branch, 2026-10-09: 1,333 unit cases, 17 packaged integrations, type
  check, smokes, documentation contract, then the console session;
  successful. Manual run: a sample decision built from a table,
  served, answered in a browser, written back; evidence under
  `evidence/2026-10-09-decision-sample/`.
- PR11 on its first base, `main`, 2026-10-10: 1,329 unit cases, 17 packaged
  integrations, type check, smokes, documentation contract, then the
  console session with 89 tests; successful, with 2.2 MB of pytest
  scratch. Rebased onto PR10's branch.
- PR11 with the build-tool cache pins at `5cdf216`, 2026-10-10, a plain
  `nox -s build` writing to `/tmp` as the owner runs it: 1,477 unit cases,
  17 packaged integrations, type check, smokes, documentation contract,
  then the console session with 290 tests; successful in 2 minutes, with
  175 MB left under `/tmp/pytest-of-<user>`.
- Build gate on the merged PR11 branch at `12e9e33`, 2026-10-10: 1,477 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 290 tests;
  successful, with 7.6 MB of pytest scratch.
- PR11 on the stacked branch at `135ecbb`, 2026-10-10: 1,474 unit cases, 17
  packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 290 tests;
  successful, with 7.6 MB of pytest scratch.
- Build gate on the merged PR10 branch at `405e884`, 2026-10-09: 1,474 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 290 tests;
  successful. `check` on the regenerated decision document: 38 items,
  unanswered.
- Slice 8 workflow half, PR10 branch, 2026-10-09: 1,454 unit cases, 17
  packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 290 tests;
  successful. `check` on the real decision document: 38 items, unanswered.
- Build gate on the merged PR9 branch at `db7d85d`, 2026-10-09: 1,449 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 290 tests;
  successful.
- Slice 8 console half, PR9 branch, 2026-10-09: console session with strict
  mypy on 8 files and 248 tests; build gate: 1,449 unit cases, 17 packaged integrations, type check of package and tests, smokes, documentation contract, then the console session; successful.
- Build gate on the merged PR8 branch at `e97aaeb`, 2026-10-09: 1,449 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 238 tests;
  successful.
- Slice 8 runtime half, PR8 branch, 2026-10-09: 1,362 unit cases, 17 packaged integrations, type check of package and tests, smokes, documentation contract, then the console session with 238 tests; successful.
- Console smoke on the base built from `ec7c1b7` with PR8's PEX: passed with the display and headless; inside the capsule `DEVCAPSULE_CONSOLE_URL` is the console's host-side origin without the token. See the `pr8-*` files under `evidence/2026-10-09-console-smoke/`.
- Build gate on the merged PR7 branch at `06d4943`, 2026-10-09: 1,333 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 238 tests;
  successful.
- Base recipe 11 rebuilt from PR7's revision `ec7c1b7`, 2026-10-09: the
  built-base test passed; the console smoke, now probing the records page,
  the raw route, the packaged renderer and the decisions listing, passed
  with the display and headless; and inside the capsule with the display a
  decision written to the default directory was listed, answered through
  the `POST` route and read back as the answer file. See the `decisions-*`
  files under `evidence/2026-10-09-console-smoke/`.
- Build gate on the merged PR6 branch at `615bb86`, 2026-10-09: 1,333 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 156 tests;
  successful.
- Build gate on the merged PR5 branch at `a427a09`, 2026-10-09: 1,333 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session with 117 tests;
  successful.
- Base recipe 11 built locally from the public PEX of `9ac19b8`: the built-base
  test passed with psutil importable offline; the console smoke, now probing
  the monitor routes, passed with the display and headless. See the `r11-*`
  files under `evidence/2026-10-09-console-smoke/`.
- Slice 1 unit modules: 468 passed with `PYTEST_ADDOPTS` scratch under
  `/opt/devcapsule-gate/pytest`; `/tmp` overflowed at 2 GB first.
- `mypy devcapsule`: no issues in 112 files.
- Build gate `nox -s build` on this branch, 2026-10-09: 1,262 unit cases, 10
  packaged integrations, type check, source and PEX smokes, documentation
  contract; successful.
- Review PR #185 gate, by the Codex pair in its worktree: 1,276 unit cases, 10
  packaged integrations, type check, smokes; documentation contract skipped
  there, the website submodule being absent from a worktree.
- Build gate on the merged branch at `0ec121e`, 2026-10-09: 1,276 unit cases, 10
  packaged integrations, type check, smokes, documentation contract; successful.
- Console session `nox -s webconsole` on PR2's branch: mypy clean on 6
  source files, 52 tests passed.
- Build gate on PR2's branch, 2026-10-09: 1,276 unit cases, 10 packaged
  integrations, type check, smokes, documentation contract, then the console
  session; successful.
- Review PR #187 gate, by the Codex pair in its worktree: runtime unit cases,
  packaged integrations, type check, smokes, then the console session with
  strict mypy and 89 tests; documentation contract skipped there.
- Build gate on the merged PR2 branch at `7013555`, 2026-10-09: 1,276 unit
  cases, 10 packaged integrations, type check, smokes, documentation
  contract, then the console session with strict mypy and 89 tests;
  successful.
- Slice 3 unit modules: 219 passed across the launcher, runtime, display,
  base image and successor plan modules; mypy on the package and tests clean.
- Build gate on PR3's branch, 2026-10-09: 1,299 unit cases, 10 packaged
  integrations, type check, smokes, documentation contract, then the console
  session; successful.
- Base recipe 10 built locally as `devcapsule-base-e2e:webconsole-161638` from the public PEX of
  `7659c6d`, over host networking: the built-base test passed, the venv
  imports the console offline. The console smoke passed with the contained
  display and headless: home and configuration 200, tokenless 403, `..` and
  absolute paths 403, a file inside the mount 200. See
  [evidence/2026-10-09-console-smoke](evidence/2026-10-09-console-smoke/).
- IDE smoke, codium, on the built base: passed, with the new "console
  answers" fact at 200 and the tokenless probe refused.
- Build gate on PR4's branch, 2026-10-09: 1,329 unit cases, 17 packaged
  integrations, type check of package and tests, smokes, documentation
  contract, then the console session; successful.
- Review PR #191 gate, by the Codex pair in its worktree: 1,329 unit cases, 17
  packaged integrations, type check, smokes, then the console session;
  documentation contract skipped there.
- Build gate on the merged PR4 branch at `4505ffa`, 2026-10-09: 1,329 unit
  cases, 17 packaged integrations, type check of package and tests, smokes,
  documentation contract, then the console session; successful.
- Review PR #189 gate, by the Codex pair in its worktree: 1,327 unit cases, 17
  packaged integrations, type check, smokes, then the console session;
  documentation contract skipped there.
- Build gate on the merged PR3 branch at `0e5737e`, 2026-10-09: 1,327 unit
  cases, 17 packaged integrations including the seven installer-script
  cases, type check of package and tests, smokes, documentation contract,
  then the console session; successful.
- Console smoke rerun with the merged branch's executable on the recipe 10
  base, 2026-10-09: passed with the contained display and headless, same
  facts; see the `merged-*` files in the evidence directory.
- Manual run against this capsule's real CLI on loopback port 8765 with a
  fresh token: tokenless request refused, cookie set from the query token,
  traversal refused, four pages rendered and screenshotted with the website's
  Playwright into `evidence/2026-10-09-console-pages/`. The server was
  stopped afterwards.
- No containers or images in use.

## Open Threads

- Resolved in slice 4: `project info` named every checkout `default`. The
  defect was mailed to `maintenance` first; the owner moved the fix here the
  same day, and a second mail supersedes the first.
- Base-release cadence, proposal for the owner with PR3: a change under
  `devcapsule-webconsole/` that an adopter should see is a base-release
  trigger, the same as a change to the display stack, because the console
  ships only inside the base. Concretely, add to the release policy: a
  release whose range touches `devcapsule-webconsole/` or
  `images/base.py` publishes a base image, and the console's version in
  `pyproject.toml` is bumped in that range. Development needs no release:
  the self-hosting exception runs the checkout's source.
- Dependencies in the base: Ubuntu's `python3-fastapi` and friends are old;
  a hash-pinned venv at image build is the plan, like Playwright's.
- The work order on `main` lacks deliverable 6; the amended text is on
  `project-management`'s branch. The mail item carries its substance.
- Mailed to `project-management` on 2026-10-10, at the owner's request:
  `2026-10-10-capsule-webconsole-reconcile-testing-approach-with-practice.md`,
  a decision to take and record on the project's testing tiers, what gates
  a pull request and a merge, the gate's time and scratch budget, and the
  hermeticity rule, against the practice the owner summarized; the
  evidence is this workstream's PR11.
- Windows path length, raised by the owner on 2026-10-10: the retained
  artifact path `<state>/devcapsule/version-sets/<64 hex>/artifacts/sha256/<64
  hex>` runs to about 150 characters before the profile prefix, and NTFS
  still enforces 260 without the long-path opt-in. Not this workstream's
  layout; to be mailed to the workstream that owns version sets once the
  owner names it.
- The hand-off rule, topic 8.8, is in this repository's `WORKFLOW.md` only.
  The shipped definition under `devcapsule-src/devcapsule/assets/` has
  another layout and belongs to workflow-improvements; it takes the same
  text at that workstream's next sync so adopters get it with 0.3.0.
- Notifications are local for now, by the owner's decision of 2026-10-09: a
  mechanism between the human and the DevCapsule environment of one
  checkout, stored in that checkout's state home. Project-wide
  notifications are a realistic future use the owner named, a coordinator
  telling every collaborator "submit your PRs by Friday", and they create
  a dilemma for the store and the command's name that slice 8 does not
  resolve. When they come, they are a second source merged into the same
  listing, carried by the coordination branch or another shared channel,
  and the local store stays what it is.
- Deliberately not preserved: the exploration of adopting Glances, Netdata,
  Cockpit or a Docker dashboard as the framework; the reasons are summarized
  in decision 3 above.

## Workstream Document Index

- [Intake decisions](intake-dispositions.md) and [intake](intake/README.md) — coordination
