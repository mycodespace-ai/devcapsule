# Pair Review Loop

<a id="the-review-partner-loop"></a>

**Pair Review** is the short name. Previously called the review-partner loop.

How a slice is built by two agent pairs of different engines in this
repository: the rule is topic 9.11 of [`WORKFLOW.md`](../../WORKFLOW.md),
the local arrangements are *Pair Review Loop In This Checkout* in
[`WORKFLOW-LOCAL.md`](../../WORKFLOW-LOCAL.md). This document carries what
the rules leave to practice: the brief template, the round brief, the
assessment comment, the invocation recipes, and the record of the loops
run so far. Keep it current with every loop.

## How to ask for it

The human says, in chat: *implement <the slice> with Pair Review,
with <engine, model> as the review partner.* The agent that receives
it is the implementor. It restates the slice, names the open choices, and
starts when the human says so. Any of the three capsule agents can be
either side.

## The shape

```dot
digraph loop {
  rankdir=LR; node [shape=box];
  owner [label="human\nbrief, decisions, merges PRn"];
  impl [label="implementor pair\nslice as PRn, stacked when needed"];
  rev [label="review partner\nanother engine\nPRn.1 from <branch>-review\nin its own worktree"];
  gate [label="full gate\nin each pair's checkout"];
  main [label="integration branch", shape=folder];
  owner -> impl [label="the slice"];
  impl -> rev [label="written brief:\nscope, files, questions,\nvalidation, delivery"];
  rev -> impl [label="PRn.1: findings,\nevidence, proposals\nnot implemented"];
  impl -> rev [label="round brief,\nat most three", style=dashed];
  impl -> gate; rev -> gate;
  impl -> owner [label="PRn ready;\njudgments listed"];
  owner -> main [label="merge commit"];
}
```

1. The implementor builds the slice on `ws-<workstream>/<slice>` and opens
   PRn with a body that holds a diagram when the change has structure, what
   changed, the judgments for the human, and the validation with counts.
2. The implementor writes the brief, commits it under the workstream's
   `evidence/` directory, creates or resets the review worktree on
   `ws-<workstream>/<slice>-review`, and starts the review partner.
3. The review partner opens PRn.1 against PRn's branch. While it runs, the
   implementor tails its event stream and tells the human in chat when it
   started, what it committed, when its gate ran and when it ended; the
   human reads progress where the human is, not in a log (owner direction,
   2026-10-28, after a print-mode run that was silent for 36 minutes).
4. The implementor reads the diff, posts the assessment, merges or pushes
   back with a round brief. Three rounds at most.
5. The implementor runs the full gate on PRn's branch, records it in PRn and
   in the status file, and hands PRn to the human.

## The brief template

One file. Replace every `<...>`. Every section below earned its place in a
loop; leave none out.

```markdown
# Review brief for the <engine> + <model> pair: PR<n>.1 on <the slice>

<One paragraph: which pair opened PR<n>, its number, title, branch and
base; which earlier reviews of this series exist. Your job is one
improvement pull request against that branch.>

## Your checkout

You are in the git worktree at <absolute path>, on the branch
`<slice branch>-review`, branched from `<slice branch>`. Work only there.
Do not touch the main checkout at <absolute path of the implementor's
checkout>.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`,
<the work order>, <the workstream status file, naming the section that
records this slice's judgments>, <the module whose docstring is the
contract>.

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against
<owner/repository>. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists. Run unit tests and mypy from
`devcapsule-src` with `PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-<engine>"`.
This PR touches: <the files, grouped by package, new ones marked>. The gate
type-checks `tests/` too. Run `nox -s build` before your final push and
report its result.

<What the review partner must not run: images, capsules, the console
smoke; who runs them instead and where the evidence lands.>

## The task

Review the diff of PR <n> against its base:

    gh pr diff <n>

<What to read first inside the diff: the contract, the module docstring,
the sibling contract.>

Improve it on your branch, focused on exactly three things, in this order:

1. Correctness of the new and modified lines: <the concrete list of
   behaviours to check, written as questions a careful engineer would ask:
   validation and refusals, bounded reads, atomic writes, ordering,
   malformed input, files that vanish mid-scan, what a careless or hostile
   agent could put there, what a host-side command could do to the wrong
   checkout>.
2. Clarity of the new and modified lines. The standard is "obviously no
   deficiencies".
3. Test coverage of the new and modified lines. Add tests where a branch is
   not exercised. Every test must fail if the line it covers is broken. Do
   not pad.
4. Every new or changed test against *Unit Tests* in `WORKFLOW-LOCAL.md`:
   it lives in the mirror and names its unit; it establishes its own
   precondition, calls one public operation and asserts a promised
   postcondition; its docstring states the contract. For each, name what
   would make it fail for a reason that is not a bug. A finding here is a
   finding; "confined to tests" does not dismiss it.
5. The changed code and its tests against *Host Inputs* in
   `WORKFLOW-LOCAL.md`, rules 1 to 6: name every read of the host outside
   an entry layer, every parameter default that reads it, every parameter
   that only a test passes, every constructor that does more than store,
   every decision taken inside an entry layer, and every patch in a new or
   changed test.

Stay inside the PR's scope: <the scope in one sentence>. Do not change
<the neighbours>. Do not widen <the contract>; if you believe it is wrong,
say why in the PR body and keep your change minimal.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md`, the
  `evidence/` directory, or run `devcapsule workflow publish`.
- Do not commit the `website` submodule pointer, `.idea/` files,
  `*.egg-info`, `.nox/`, `dist/` or `__pycache__`.
- Do not merge anything. Do not push to `main` or to any branch other than
  your review branch.
- Do not rebase or force-push. Do not build images or run capsules.

## Deliverable

1. Commits on `<slice branch>-review`, each message naming the component
   and the evidence, ending with your `Co-Authored-By:` line:
   `Co-Authored-By: <model name> <engine> <attribution address>`.
2. Push the branch and open one pull request with
   `gh pr create --base <slice branch> --head <slice branch>-review`.
   Title: "Correctness, clarity and coverage review of #<n> (PR<n>.1)".
   The body lists each finding as: what was wrong or unclear, where, what
   you changed, how the test proves it. Separate "changed" from
   "considered and left alone, because". List the proposals you did not
   implement. State the gate result with counts and what was skipped. If
   you find nothing to change, say so in the PR body and open the PR with
   the added tests only, or, if there are none, say that in your final
   report instead of opening an empty PR.
3. Print the PR URL as the last line of your output, or "NO PR" if you
   opened none.

Write the PR body and your report at about 80% ASD-STE100: one fact per
sentence, about twenty words, active voice. Every claim about behavior
must be backed by a test or a command you ran.

If you cannot proceed, because of a blocker like network or credentials,
stop and say exactly what blocked you. Do not work around a blocker.
```

## The round brief

Short, and only about the change requested. It continues the same review
session where the engine allows it.

```markdown
Round <k> of the review of your PR<n>.1 (<URL>) is posted as a comment by
the first pair. Read it with:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh && gh pr view <n.1> --comments

<Which findings are accepted as written.> One change is requested: <the
change, where, and the test that proves it>.

Make that change on your branch `<slice branch>-review` in this worktree,
run the focused tests and `mypy devcapsule`, run the build gate as before,
commit with a message naming the component and the evidence plus your
Co-Authored-By line, push, update the PR body's gate result, and reply on
the PR with one comment that says what changed and the gate result. The
same limits as before apply: no status files, no publish, no merges, no
rebase or force-push. Print the comment URL as the last line.
```

## The assessment comment

Posted by the implementor on PRn.1, one per round, labelled by pair.

Accepted without a round:

```text
**Accepted at `<sha>` (<pair>, no round needed).** Verified in the review
worktree: <what the implementor ran, with counts>. <Why each finding is
real and each fix the right size, in one sentence each.> Merging into
`<slice branch>` with a merge commit; the gate <and any real-session check>
repeat on the merged branch.
```

Pushed back:

```text
**Round <k> (<pair>).** <What is accepted as it is.> One regression from
finding <i> blocks the merge: <the failure, reproduced, with the command
and its output>. Please <the change>; add <the tests>. Nothing else to
change.
```

Then the merge, by the implementor:

```text
gh pr merge <n.1> --merge --subject "Merge PR #<n.1>: correctness, clarity and coverage review of #<n> (PR<n>.1)" --body "<pair> review of <the slice>, accepted <without a round | after k rounds>. <The findings in one sentence each.>"
```

## Invocation recipes

The review partner runs detached in its worktree so that the implementor's
session can wait for it. `$S` is the implementor's session scratchpad; the
log ends with an exit line the implementor waits for.

Codex, the form every loop so far ran, with the brief on standard input:

```text
cd ~/worktrees/<workstream>-review && nohup setsid bash -c "codex exec -m <model> -s danger-full-access -c 'projects.\"$HOME/worktrees/<workstream>-review\".trust_level=\"trusted\"' - < $S/<brief>.md > $S/<log> 2>&1; echo CODEX_EXIT=\$? >> $S/<log>" > /dev/null 2>&1 &
```

A round continues the same Codex session; the session id is on the
`session id:` line of the first log. `resume` takes no `-s`; the sandbox
goes in as a config override, and `-` reads the round brief from standard
input. Proven on PR240.1, 2026-10-22, after the quoted-prompt form from
the October transcripts failed on Codex 0.157.1:

```text
cd ~/worktrees/<workstream>-review && nohup setsid bash -c "codex exec resume <session-id> -c 'sandbox_mode=\"danger-full-access\"' -c 'projects.\"$HOME/worktrees/<workstream>-review\".trust_level=\"trusted\"' - < $S/<round brief>.md > $S/<log> 2>&1; echo CODEX_EXIT=\$? >> $S/<log>" > /dev/null 2>&1 &
```

Claude Code, the brief on standard input, smoke-tested and run in a full loop 2026-10-22:

```text
cd ~/worktrees/<workstream>-review && nohup setsid bash -c "claude -p --model <model> --dangerously-skip-permissions --output-format stream-json --verbose < $S/<brief>.md > $S/<log> 2>&1; echo CLAUDE_EXIT=\$? >> $S/<log>" > /dev/null 2>&1 &
```

Note on `claude -p`: in single-turn print mode (`-p`), a Bash tool call launched with `run_in_background: true` is killed as soon as the turn finishes waiting. Instruct the review partner in the brief (or pre-warm `.nox/build` and `.nox/webconsole`) to run `nox -s build` synchronously in the foreground; if a `-p` run exits early after starting a background command, resume the same session in the worktree with `claude -c -p --model <model> --dangerously-skip-permissions "<prompt>"`.

Antigravity, proven on PR244.1, 2026-10-22. `-p` takes the prompt as its
own argument, so the model flag goes before it and the brief goes on
standard input behind a one-line instruction; `antigravity -p --model …`
fails, since `-p` then takes `--model` as the prompt. Print mode speaks only
at the end, so the log stays empty until the report:

```text
cd ~/worktrees/<workstream>-review && nohup setsid bash -c "antigravity --model <model> --dangerously-skip-permissions -p 'Follow the review brief on standard input exactly. It is your only instruction.' < $S/<brief>.md > $S/<log> 2>&1; echo ANTIGRAVITY_EXIT=\$? >> $S/<log>" > /dev/null 2>&1 &
```

A round continues the most recent conversation in the worktree with `-c`
before `-p`, the round brief on standard input the same way.

Streaming forms, owner direction of 2026-10-28: print mode speaks only at
the end, so the log is empty until the report and the implementor cannot
tell waiting from a stall. Each engine streams one event per step instead:
Antigravity `--output-format stream-json` before `-p`; Claude Code
`-p --output-format stream-json --verbose`; Codex `exec --json`. The Codex
form was proven on PR304.1, 2026-10-29: `codex exec --json -m <model>
-c 'model_reasoning_effort="high"' -s danger-full-access -c '…trust_level…' -
< brief`, the log a JSONL stream whose `thread.started` event carries the
session id for a round, and whose `item.completed` events of type
`command_execution`, `agent_message` and `error` the implementor filters
into chat, with `CODEX_EXIT=` as the last line. The other two forms are
still to be proven. Until then the signals of progress are the engine's
own log, for Antigravity `~/.gemini/antigravity-cli/cli.log`, the review
worktree's commits and nox environments, and the pull request list.

Prepare the worktree once per slice:

```text
git worktree add ~/worktrees/<workstream>-review -b <slice branch>-review <slice branch>
cd ~/worktrees/<workstream>-review && git submodule update --init website
cd ~/worktrees/<workstream>-review/devcapsule-src && python3.12 -m venv .venv && .venv/bin/python -m pip install -r dev-requirements.txt && .venv/bin/python -m pip install -e . --no-deps
mkdir -p /opt/devcapsule-gate/pytest-<engine>
```

Without the `website` submodule the gate skips the documentation contract
and reports no page count; both pairs of PR304.1 hit this on 2026-10-29.

A later slice resets the same worktree: fetch the slice branch, reset the
worktree hard to it, create the new review branch. Remove the worktree
when the workstream pauses, and say so in its open threads.

## Record of the loops run

| Date | Workstream | Implementor | Review partner | Slices and reviews | Outcome |
|---|---|---|---|---|---|
| 2026-11-12 | maintenance, the rewrite of PR #26 with host inputs as values and no patch in a touched test (`0.3.1`) | Claude Code, Claude Fable 5.2 pair | Codex, gpt-6-astra (high) pair | #26/#28 | accepted at `04770142` without a round, merged at `83d238b8`; the first loop whose brief holds the code to *Host Inputs* and asks the reviewer to review the rule itself, as an agent that must follow it with no other context; the reviewer restored 0.3.0's order of launch file and launch variable, replaced two integration oracles that repeated the implementation, proved the real owner change by passing the caller's uid as a value, and closed three of the implementor's five uncaught faults with integration tests and no patch; its "On the rule" table named seven places where two agents would read the rule differently, recorded in the `maintenance` status for the owner's ruling; 12 planted faults of its own, 4 caught by mirror tests, 1 by a legacy unit test, 5 by integration tests, 2 by nothing; the capsule's 17 standing failures unchanged; brief committed under `evidence/2026-11-12-host-inputs-as-values/review-brief.md` |
| 2026-11-11 | maintenance, PR #18's test-only parameters removed and the tests set the host at its source (follow-up to #18, `0.3.1`) | Claude Code, Claude Fable 5.2 pair | Codex, gpt-6-astra (high) pair | #26/#27 | accepted at `1b5d3fc7` without a round, merged at `60ad2c5a`; the first loop whose brief asks for the hosted check's result and names the capsule's standing unit failures, and whose review started only on a green hosted run; the reviewer corrected a docstring that claimed more than the launcher enforces, ended each process-wide test patch with its action, read the session environment when the supervisor is made, replaced an expected value derived from the constant under test, and added a test of the default build-record lookup that the implementor had recorded as impossible; 13 planted faults of its own and 25 of the implementor's 26 caught by the unit files, the last by the integration file; GitHub runs no check on a pull request into a slice branch, so the hosted run of #26 after the merge is the one that counts; the capsule's 17 standing failures keep `nox -s build` from passing as one session, its parts were run one by one; four proposals recorded in the `maintenance` status; brief committed under `evidence/2026-11-11-host-inputs-at-source/review-brief.md` |
| 2026-11-08 / 2026-11-09 | maintenance, launcher-delivered web console (`D-0017`, 0.3.1 candidate 2 blocker, stacked on #18) | Antigravity, Gemini 4 Argon (High) pair | Claude Code, Claude Fable 5.1 pair | #16/#17 | accepted at `e23e22c7` without a round, merged at `9919f4ce`, and rebased onto PR #18 (`ws-maintenance/webconsole-legacy-tests`) per owner decision `stacked-delivery-branch = force-push-pr-16`; the reviewer removed the dead per-start `import psutil` subprocess probe (`WEBCONSOLE_RECIPE` 11 settles compatibility on the host) and unified console package precedence in `console_package_path`, fixed `extract_webconsole_bundle` to mask `external_attr >> 16` with `S_IFMT` so typeless regular zip entries (`ZipFile.writestr`) extract, pinned `match=` on every bundle refusal test (99% bundle coverage), tightened `DEVCAPSULE_DEV_WEBCONSOLE` to `1`/`true`/`0`/`false`, and aligned `D-0017` and the bug record; stacked gate 2904 unit tests, 40 integration (3 skipped), 458 webconsole, 332 mypy files, 104 legacy / 44 conforming files with 0 breaches, 249 contract pages, plus live base-Python HTTP check; remaining unimplemented proposals recorded in `maintenance` status; brief committed under `evidence/2026-11-08-webconsole-delivery/review-brief.md` |
| 2026-11-09 | maintenance, whole-file legacy test retirement and 4-file refurbishment (`0.3.1` prerequisite) | Antigravity, Gemini 4 Argon (High) pair | Claude Code, Claude Fable 5.1 pair | #18/#19 | accepted at `4aac5dfc` without a round, merged at `a1aad17f`; completed `__all__` in `console.py`, `entrypoint.py` and `materialization.py`, dropped a dead `subprocess` import in `project.py`, stated basename pairing and mirror test deletion refusal across rule 5, the companion, the developer guide and the checker with 4 new checker tests, proved `entrypoint.run` writes session variables only into the supplied `environ`, and restored interpreter-path matching in `test_console_tools.py`; hosted CI on `e301367d` caught `/ide-config` state-slot paths in `test_entrypoint.py` (masked inside the PyCharm capsule), resolved by confining `make_plan` to `tmp_path` and injecting `runtime_root`, `caller_uid`, and `configure_logs` across `filesystem.py`, `identity.py`, and `entrypoint.run` (`test_filesystem.py` added, implementing PR #19's third proposal with zero global state); gate 2842 unit, 36 integration (1 skipped), 458 webconsole, 330 mypy files, 104 legacy / 43 conforming files with 0 breaches, 249 contract pages; two remaining proposals recorded in `maintenance` status; brief committed under `evidence/2026-11-08-webconsole-legacy-tests/review-brief.md` |
| 2026-11-08 | maintenance, the web console's Files page (slice 2 of 0.3.1) | Antigravity, Gemini 4 Argon (High) pair | Claude Code, Claude Fable 5.1 pair | #12/#13 | accepted at `49bb2e8e` without a round, merged at `83949a30`; the first loop with the pairs reversed at the owner's word, the reviewer's pair writing the implementor brief from the owner's order; the reviewer removed a raw-route branch that detected its own test and repointed the legacy permission test at the streaming open, and smoked the routes against a standalone console; gate on the merged branch 458 console tests, 2825 unit tests, 0 breaches, 249 contract pages; both briefs committed under the workstream's evidence; the Antigravity stream-json form relayed one event per tool step, proving that form |
| 2026-10-30 | maintenance, user-docs 0.3.0 CLI alignment Batch 1 (`reference`, `updates`, `troubleshooting`) | Antigravity, Gemini 4 Argon (High) pair | Codex, gpt-6-astra (high) pair | #319/#320 | accepted at `71243a0c` without a revision round, merged at `0c0006c4`; 10-file audit with 106 CLI `--help` and scratch probes; 13 source-verified fixes across 9 files (`omit --unverified` vs. `recommend`, `docker-args` shared store, direct `state adopt` directory semantics, `DEVCAPSULE_CONFIG_HOME` disabling in-capsule settings fallback, secret vs. directory bindings and channel IDs, `project info --json` types and text sections, all 11 freshness adapters, schema-2 `config show --json`, offline rollback base-image prerequisite, `launcher-updates.md` component-channel check vs. GitHub releases, `already fully initialized` vs. `Honored existing`, JetBrains `log` slot, and `checkouts/NAME.checkout.toml` cleanup paths); two CLI help/migration-hint gaps filed as a `maintenance` bug; 192 contract pages, 23 website tests, 196 HTML pages, 14,441 links/anchors, and 92 `release_docs` tests passed |
| 2026-10-30 | maintenance, CI path gating and advisory diff coverage | GPT-6 Codex | Claude Code, Claude Fable 5.1 | #312/#314 | accepted at `2dd3f14e` without a revision round; commit pin, real test inputs, large-PR fallback and routing/nested-path tests; 70 focused tests and reviewer full gate passed; stream-json/verbose invocation proven; native GUI warning verified by closed probe #313 |
| 2026-10-29 | maintenance, the explicit IDE requirement override (0.3.0) | Claude Code, Claude Fable 5.1 pair | Codex, gpt-6-astra (high) pair | #304/#306 | accepted at `6dd56fee` without a round, merged at `3bfb3a16`; the reviewer found the software-approval offer running before the IDE request was checked, the advertised override failing for a saved IDE that already conflicted with a later requirement, the optional-download recovery rebuilding the plan without the departure, and the local-base minimum guards reading the departed IDE's minimum; four fixes, 15 tests; one proposal, the legacy-lock replacement defect, filed as a bug; the first loop on Codex's `exec --json` event stream, relayed in chat as the owner directed; the review's docs check failed on a `versions.yaml` line the implementor's merge of `main` had dropped, fixed on the base before the review PR opened; the brief committed under the workstream's evidence |
| 2026-10-28 | maintenance, VS Code as an IDE surface (0.3.0) | Antigravity, Gemini 4 Argon (High) pair, then Claude Code, Claude Fable 5.1 pair | Antigravity, Gemini 4 Argon (High) pair | #301/#302 | accepted at `bd3c6ade` without a round, merged at `241e7b10`; the implementing session was cut by a power outage with the slice uncommitted and its smoke unfinished, and the second pair took it over, committed it, ran the recorded IDE smoke from a temporary clone inside a capsule and opened the PR; the reviewer found the lock's version, url and sha256 unchecked, an empty-credential or whitespace URL establishing a trust channel, the discovery accepting a hostless URL by prefix, and `config ide` reporting the recommendation rather than the composed lock; 2544 unit tests on the merged branch; print mode was silent for 36 minutes, which produced the owner's direction on streaming output and on relaying progress; the brief committed under the workstream's evidence |
| 2026-10-28 | maintenance, the configuration home and the home commands (0.3.0) | Codex, gpt-6-astra pair | Claude Code, Claude Fable 5.1 pair | #299/#300 | accepted at `36bec84` without a round, merged at `e83c0881`; the implementor was dispatched from the project-management session with the work order as its brief and stopped twice on blockers, the evidence location and an undeclared dependency, both cleared from the dispatching side; the reviewer reproduced every launcher-owned write failing inside a capsule under the launcher's exported home and replaced the order's in-capsule refusal with a read of the mounted settings until the capsule has its own; 2515 unit tests on the merged branch; all briefs committed under the workstream's evidence |
| 2026-10-27 | maintenance, session diagnostics snapshot and export | Antigravity, Gemini 4 Argon (High) pair | Codex, gpt-6-astra pair | #293/#295 | accepted at `c190d1cf` without a round and merged at `5cc52392`; nine hardenings (bare/quoted/`%`-encoded and structured JSON credential redaction, live container verification across unfinished sessions, bounded `O_NOFOLLOW`/`O_NONBLOCK` manifest and IDE log reads with a 4,096-entry cap, shared `dir_fd`-pinned mode-`0600` output helper, WebSocket Ping/split-frame greeting buffering, tar-slip session/slot path validation, and CLI `OSError` diagnostics) with 33 new focused regression checks (42 total); post-merge gate 2380 unit / 17 packaging / 357 webconsole, 189 docs pages, plus real-container E2E fault-injection check passed; three unimplemented proposals recorded in `maintenance` status; the brief committed under the workstream's evidence |
| 2026-10-30 | maintenance, user documentation 0.3.0 CLI alignment and prose review (Batch 3: README, getting-started, your-project, containment) | Antigravity, Gemini 4 Argon (High) pair | Codex, gpt-6-astra (high) pair | #323/#324 | accepted at `f218a6d5` without a round, merged at `18728ce8`; ten source-verified fixes across all 10 files (embedded SCIE Python runtime in `install.md` per `build-pex.sh:279`, `authorize network/docker-daemon default` grant vs. deny distinction in `granting-and-withdrawing.md` per `authorization.py:54,333`, one-run `--authorize` host-access scope in `the-boundary.md` per `_run_flow.py:153`, `development-sudo` capability/security-opt behavior per `_launcher.py:1706`, schema-2 manifest table reference and `drop env`/`--preview`/`recommend cpus` in `declare-needs.md` per `manifest_schemas.py:57`, and shared `docker-args`/`config env` replacement semantics in `services-and-ports.md`); `docs-contract` 192 pages, `website.sh build && check` 23 tests / 196 HTML pages / 14,449 links-anchors, 92 `release_docs` tests, and `smoke` passed; one Batch 5 follow-up (`docs/sessions/what-persists.md:8`) recorded; brief committed under `evidence/2026-10-30-docs-batch-3/review-brief.md` |
| 2026-10-27 | maintenance, release documentation automation (C20 for 0.3.0) | Codex, gpt-6-astra pair | Claude Code, Claude Fable 5.1 pair | #294/#296 | accepted at `59d56c2` after one round, merged at `7bb8883`; the implementor was dispatched from the project-management session with the work order as its brief, and corrected the order's sequence from the final-tag protocol, promotion before the last candidate; the reviewer found the placeholder rule refusing the 0.2.14 notes as published and the manifest reader refusing a candidate listed as development, both proven against the repository's own files; the round was on a placeholder wrapped across lines, which the reviewer's first rule had let through; 2430 unit tests on the merged branch; both briefs committed under the workstream's evidence |
| 2026-10-26 | maintenance, the manifest's two schemas as classes | Claude Code, Claude Fable 5.1 pair | Codex, gpt-6-astra pair | #289/#290 | accepted at `94d2108` without a round; the reviewer made schema admission lossless (explicit empty fields, duplicates and reasons kept so `manifest_for` reproduces the file), validated the schema-1 policy before migration, refused a plain `init` write to a schema-1 file, tightened the legacy-lock rule for evidenced locks with unrecognized generations, and corrected a remedy the order had named but admission made unreachable; 2338 unit tests on the merged branch; the brief committed under the workstream's evidence |
| 2026-10-24 | project-management, the CLI UX redesign work order | Claude Fable 5.1 pair | Codex, gpt-6-astra pair | #258/#259 | the first loop on a document rather than code; accepted at `30ecdca` after one round; the reviewer reproduced 23 catalogued deficiencies with 67 CLI invocations and no container, overturned two of the draft's claims and added two reproduced gaps and thirteen owner questions; the round was on review notes written into the user-facing part, moved to the decisions part; the briefs committed under the workstream's evidence |
| 2026-10-23 | maintenance, general saved Docker arguments | GPT-6 Codex | Claude Code, Claude Fable 5.1 | #253/#255 | accepted at `af39c59` after two rounds; persistent session-log masking, conservative refusal of ambiguous environment edits, overlapping candidate masking, attached launcher-owned short flags; 319 independent focused tests; reviewer gate 1769 unit / 17 packaging / 293 webconsole, 188 docs pages; separate environment spellings documented, no GPU execution |
| 2026-10-30 | maintenance, user documentation 0.3.0 CLI alignment and prose review (Batch 4: everyday-development, working-with-ai) | Antigravity, Gemini 4 Argon (High) pair | Codex, gpt-6-astra (high) pair | #325/#326 | accepted at `5f734995` without a round, merged at `65fa4958`; fifteen source-verified fixes across all 10 files (including residual `GIT_USER_NAME`/`GIT_USER_EMAIL` forwarding vs. generic `container_runtime` in `git.md`, linked-worktree `.git` and same-UID agent slot scope, `--force` rejecting `--save` per `_run_flow.py:85`, `/opt/xtras` -> `/home/devcapsule/xtras` symlink per `materialization.py:627`, all three Playwright env vars, `config restore` offer-only scope per `project.py:1740`, `config unbind` before `omit` per `bindings.py:131`, managed-only `_seed_component_state` per `project.py:2638`, Antigravity origin/credential scope per `trust.py:144` & `antigravity_cli.py:147`, and `bash -n` shell syntax fix in `hosted-and-local-models.md`); `docs-contract` 192 pages, `website.sh build && check` 23 tests / 196 HTML pages / 14,471 links-anchors, 92 `release_docs` tests, and `smoke` passed; unimplemented proposals recorded; brief committed under `evidence/2026-10-30-docs-batch-4/review-brief.md` |
| 2026-10-23 | maintenance, checkout environment for 0.3.0 | GPT-6 Codex | Claude Code, Claude Fable 5.1 | #253/#254 | accepted at `65bed97` without a round; record lookup without recovery, early validation, file diagnostics, idempotent removal and coverage; review gate 1745 unit / 17 packaging / 293 webconsole, 188 docs pages; host-mounted scratch broke an unrelated unmountable-path test, tmpfs scratch passed; keep gate logs outside pytest basetemp |
| 2026-10-09 to 2026-10-10 | capsule-webconsole | Claude Fable 5.1 pair | Codex, gpt-6-astra pair | #184/#185, #186/#187, #188/#189, #190/#191, #192/#193, #194/#195, #196/#197, #199/#200, #201/#202, #203/#204, #205/#206 | every review merged; one round on #185 and one on #200; stacked branches kept consistent by merging, after a GitHub rebase of a base had broken the stack once |
| 2026-10-11 | maintenance, session diagnostics | Claude Fable 5.1 pair | Codex, gpt-6-astra pair | #207/#208; #209/#210, #211, #212 | #208 merged without a round with five real gaps; #210's proposals became a design change; #212 used the third round; the owner changed the design once between rounds and the loop absorbed it |
| 2026-10-12 | maintenance | | | | the process record sent to the trading-research sample project's `project-management` as an intake item; it is the source of the lessons below |
| 2026-10-30 | maintenance, 0.3.0 user documentation CLI alignment — Batch 5 (`sessions/`, `collaboration/`, `platforms/`) | Antigravity, Gemini 4 Argon (High) pair | Codex, gpt-6-astra pair | #327/#328 | accepted at `59bc1bae` without a round, merged at `edcab618`; file-by-file review across all 9 pages (`several-projects.md` and `another-machine.md` stubs retired) fixed 8 files (`256 MiB` default session-log budget, `HomeDefaults` keys `memory`/`cpus` and URL-encoded `<creator>/<slug>` paths, `project list` host vs in-capsule behavior and `DEVCAPSULE_CONFIG_HOME` isolated-home guidance, home-wide console `trust` scope, `env set` leading-dash rule, `HttpOnly; SameSite=Strict` RFC 6265 host-shared cookie behavior on `127.0.0.1`, `--workstream` subcommand scope, and `project-management` non-forwardability); 92 `release_docs` tests, 17 shell fences, 26 CLI checks, 40 request-classification checks, `docs-contract`, and website check (`196` HTML pages, `14,462` links/anchors) passed; one unimplemented runtime proposal (instance/port-isolated console auth cookies) recorded in `maintenance` status; the brief committed under `evidence/2026-10-30-docs-batch-5/review-brief.md` |
| 2026-10-22 | maintenance, e2e scenario video recorder | Antigravity, Gemini 4 Argon (High) pair | Claude Code, Claude Fable 5.1 pair | #236/#241 | #241 (PR236.1) merged without a round: ten concrete fixes (`ActionStep` and `seed_files` path/symlink validation, `ffmpeg` stderr log file and pipe/process reaping, extracted `start_controller_server` with HTTP 400/504 and atomic `controller.json`, `ide-smoke --scenario` CLI flag guards) and 50 new unit tests with a 17-point mutation check; three unimplemented proposals recorded in `maintenance` status |
| 2026-10-22 | maintenance, release 0.3.0, C10 | Claude Fable 5.1 pair | Antigravity, Gemini 4 Argon (High) pair | #244/#246 | one round, on three of the reviewer's own proposals taken as defects; the first Antigravity review in the workstream, its form proven and recorded above; the briefs committed under the workstream's evidence |
| 2026-10-22 | maintenance, release 0.3.0 | Claude Fable 5.1 pair | Codex, gpt-6-astra pair | #240/#242 | the first loop under topic 9.11; one round, on a name special-case where the declaration carried the fact; the briefs committed under the workstream's evidence; the resume form corrected |
| 2026-10-30 | maintenance, user-docs 0.3.0 CLI alignment Batch 2 (`configuration`) | Antigravity, Gemini 4 Argon (High) pair | Codex, gpt-6-astra (high) pair | #321/#322 | accepted at `a082a710` without a revision round, merged at `b7849132`; 10-file audit with 46 `--help` invocations and 68 isolated scratch CLI probes; 11 source-verified fixes across all 10 files (required-IDE `--force` departure links, shared `docker-args`/`env` file and `--from-host` blocking, console auto-applied restrictive `authorize` table and 4-token `env set`, conditional read-only `settings.toml` mount and empty `DEVCAPSULE_CONFIG_HOME`, `project info` runtime allowlist vs. `config show` declared inputs, generic `/opt/xtras/bin` example, immediate directory check on `bind`/`adopt`/`init --bind` and `unbind` semantics, `default` vs. `none` on declared values vs. `memory`/`cpus`, `images list` columns vs. `devcapsule.source.revision` label and `--allow-local-source` console limit, re-acceptance origin replacement and bare `config approve` exit `1`, and provider-recommendation / omitted-offer / numeric `+` metadata rules); two CLI hint proposals (`_launcher.py:160-163` missing `--tag` and `project.py:1138` retired `config resolve` hint) recorded in `maintenance` status; 192 contract pages, 23 website tests, 196 HTML pages, 14,425 links/anchors, and 92 `release_docs` tests passed |

The reviews' briefs of these loops lived in the implementors' session
scratchpads and are gone; their structure is the template above. From
2026-10-22 briefs are committed under the workstream's `evidence/`.

## What the loops taught

- The brief is the reviewer's only context. What it leaves out, the
  reviewer does not know. Files in reading order and concrete questions get
  concrete findings.
- A reviewer that runs its own gate and reports counts and limits is
  trustworthy; one that only summarizes is not.
- "Proposals not implemented" is the most valuable section. The strongest
  findings were about lifecycle and failure: signals, reaping, crashes
  mid-rotation. Twice a proposal was a defect in the design.
- The implementor must read the diff. Twice the summary was right and the
  diff needed a merge decision the summary did not state.
- Accepting without a round and pushing back are both decisions with
  reasons; both go into the record.
- A rebase of a stacked branch's base rewrites history the branches above
  it carry; merge commits keep a stack consistent.
- A document has readers the way a module has callers. When the slice is a
  document, the brief names each part's reader; a reviewer that writes its
  notes into a part addressed to the user has changed that part's reader,
  and the round is spent moving the notes to where the decider reads them.
- A round took twenty to forty minutes of wall time, most of it the
  reviewer's own gate. Three rounds were enough every time.
