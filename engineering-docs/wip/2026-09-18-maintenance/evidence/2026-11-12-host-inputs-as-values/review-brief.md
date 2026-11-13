# Review brief for the Codex + GPT-6 Astra pair: PR26.2 on the rewrite of PR #26 with host inputs as values

The Claude Code + Claude Fable 5.2 pair rewrote PR #26 on the branch
`ws-maintenance/host-inputs-at-source`, targeting `release-0.3.1`. Your pair
reviewed the first version as PR #27 (PR26.1), which was merged. The owner
then rejected that design. Commit `60cab937` replaces it, and the next
commits add the rule the owner asked for, *Host Inputs* in
`WORKFLOW-LOCAL.md`. No review of the rewrite exists. Your job is one
improvement pull request, PR26.2, against
`ws-maintenance/host-inputs-at-source`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/maintenance-review`,
on the branch `ws-maintenance/host-inputs-at-source-review-2`, branched from
`ws-maintenance/host-inputs-at-source`. Work only there. Do not touch the
implementor's checkout at `/workspace/301e4208ef81-ChatGPT_Codex`, and run no
test there.

Read first, in this order:

1. `AGENTS.md`, `WORKFLOW.md` topic 9.11, `WORKFLOW-LOCAL.md` (*Unit Tests*
   rules 1 to 7, *Host Inputs* rules 1 to 7, *Pair Review Loop In This
   Checkout*, *Commit Authorship*), `WORKFLOW-LOCAL-humane.md` (*Unit Tests*
   and *Host Inputs*).
2. `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md`, the
   section "PR #26 rewritten: host inputs are values, and no touched test
   patches — 2026-11-12". It holds the direction, the evidence table of 43
   planted faults, the four judgments taken for the owner and the proposals
   not implemented.
3. `engineering-docs/bugs/devcapsule/2026-11-10-unit-tests-read-the-capsules-mounted-launcher-settings.md`.
   It explains the 17 unit tests that fail in this capsule on every branch.
4. `devcapsule-src/devcapsule/container_runtime/session.py` and
   `entrypoint.py`. Their module docstrings are the contract of the largest
   change.

## GitHub CLI

In every shell that uses `gh`, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account. Pass
`-R mycodespace-ai/devcapsule` to every `gh` command. Do not edit `.bashrc`
or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists. Run everything from
`devcapsule-src`. These are the commands, verbatim:

    DEVCAPSULE_DIFF_BASE=origin/release-0.3.1 .venv/bin/python -m nox -s typecheck
    .venv/bin/python -m pytest --no-cov -q tests/unit/devcapsule/container_runtime tests/unit/devcapsule/test_console_tools.py tests/unit/devcapsule/test_build_info.py
    .venv/bin/python -m pytest --no-cov -q -m integration tests/integration/test_console_decisions_cli.py tests/integration/test_version_cli.py tests/integration/test_runtime_entrypoint_cli.py
    .venv/bin/python -m pytest --no-cov -q tests/test_contained_display.py tests/test_eclipse_component.py tests/test_vscode_component.py tests/test_runtime_diagnose.py
    DEVCAPSULE_DIFF_BASE=origin/release-0.3.1 .venv/bin/python -m nox -s tests

Facts of this capsule that you must know before you read a result:

- `nox -s tests` ends with 17 failed here, on this branch and on
  `release-0.3.1` alike. The bug record of item 3 names the six files and the
  counts. A failure outside that list is a finding. Because of them
  `nox -s build` cannot pass in this capsule; do not run it. The hosted run
  is the authority for the whole unit suite.
- The hosted pull-request gate runs the unit suite only. It does not run a
  test marked `integration`. The three integration files of this change run
  in this capsule, by the third command, and in the release workflow.
- One unit test downloads 1.5 GB into its scratch under `/tmp`, a 2 GB
  tmpfs. Run the unit session once, as the last command. Before it, run
  `df -h /tmp`, and delete only the `/tmp/pytest-of-*/pytest-<N>` directories
  that your own earlier runs left. Use the default scratch: no `--basetemp`,
  no `/opt/devcapsule-gate`, nothing under `/home/devcapsule`.
- Run commands in the foreground and one at a time. Two pytest sessions at
  once collide in `/tmp`.
- You are inside a capsule: `DEVCAPSULE_CONTAINER_NAME` is set,
  `/opt/devcapsule-webconsole`, `/etc/devcapsule/home` and `/ide-config`
  exist. The hosted runner has none of them. A test that passes here for
  that reason is the defect class this slice exists to remove.
- When you plant a fault, set `PYTHONDONTWRITEBYTECODE=1`. Without it a
  same-size edit restored within a second leaves the faulty bytecode live.

Read the hosted check of the head before you start and again before your
final report:

    gh pr checks 26 -R mycodespace-ai/devcapsule

State its result in your pull request body. If it is red or pending when you
finish, say so in the first line of the body.

Do not build images, start capsules or run the end-to-end sessions.

## The task

Review the diff of PR #26 against its base:

    gh pr diff 26 -R mycodespace-ai/devcapsule

`git diff e401b825 HEAD` shows the rewrite against the version you reviewed.
The code of before PR #18 is at `b84b06e9^1`; `git show b84b06e9^1:<path>`
shows any file as 0.3.0 shipped it.

What the change does. The first version patched each host input where the
code read it. The rewrite removes the reads from the inner modules:

- `container_runtime/identity.py`: `CapsuleUser(identity, caller_uid)`, with
  `command` and `owner_changes`.
- `container_runtime/filesystem.py`: `create_directories` returns what it
  created; `prepare_filesystem(plan, user)` performs the owner changes.
- `container_runtime/console.py`: `ConsoleInstallation(python,
  launcher_source)`, with `of_image`, `package_path` and `child`; public
  `probe_address`.
- `container_runtime/session.py`, new: `Session(plan, job, user, console)`
  decides the filesystem plan, the launch, the environment, the display,
  the profile lock, the log settings and the children.
- `container_runtime/entrypoint.py`: `run` reads `os.geteuid()` and
  `os.environ`, builds the session and performs its answers.
- `console_tools.py`: `DecisionTools(in_capsule, console, runtime_plan_path)`;
  `commands/project.py` builds it from the environment.
- `build_info.py`: `distribution_build_info` and `embedded_build_info` take
  their locations as values; `build_info_text`; `commands/version.py` prints.
- The legacy file `tests/test_runtime_entrypoint.py` is refurbished whole
  into mirror files and deleted. The mirror files and three integration
  files hold no `monkeypatch` use.

Improve it on your branch, focused on these five things, in this order.

1. **Correctness of the new and modified lines.**
   - Is a session the session of 0.3.0 in behaviour? Compare `entrypoint.run`
     and `Session` with `b84b06e9^1:devcapsule-src/devcapsule/container_runtime/entrypoint.py`.
     Account for every difference in the order of effects: the log
     configuration, the directories and their owners, each update of
     `os.environ`, the launch files, the display, the profile lock, the
     supervisor.
   - `Session.environment(existing)` merges the planned variables and the
     graphics defaults. Does a variable the process already has still win or
     lose exactly as before? Does the display's environment still arrive
     after it?
   - `Session` and its neighbours are frozen dataclasses with
     `cached_property`. Is that sound here: no `slots`, no hash or equality
     surprise, no cached value that should have been recomputed?
   - `filesystem.RUNTIME_ROOT` is gone and the runtime directory is a literal
     again. Is the path a real session gets the path of 0.3.0?
   - `tests/conftest.py` no longer patches `console.LAUNCHER_CONSOLE_SOURCE`.
     Can any test, legacy ones included, now reach this capsule's real
     `/opt/devcapsule/webconsole` or `/opt/devcapsule-webconsole`?
   - Does any caller still import a removed name: `foreground_command`,
     `console_child`, `console_package_path`, `RUNTIME_ROOT`, `log_rotation`
     or `logged_children` of `entrypoint`, `console_decisions_command`,
     `run_console_decisions`? Look in `devcapsule/`, `scripts/`,
     `noxfile.py`, `devcapsule-webconsole/`, `engineering-docs/` and every
     test.
   - Does `devcapsule version` print what 0.3.0 printed, with and without
     `--json`, from a source checkout and from a built executable?
2. **Clarity of the new and modified lines.** The standard is "obviously no
   deficiencies". Read `Session` as a stranger would: is every property's
   name the question `run` asks, and is `run` a sequence a reader can check
   against the module docstring line by line?
3. **Test coverage of the new and modified lines.** Plant faults of your own
   in the touched production code and report which test catches each, and in
   which tier: mirror, legacy unit, integration, none. Do not only repeat
   the 43 of the status section. Five recorded faults are caught by nothing:
   the readiness probe's timeout, twice; `checkout decisions` dropping its
   arguments; the uid and gid swapped in the one `os.chown` call; the build
   record looked for outside the package. Close each one you can close
   without a patch and without a test-only parameter. Say for each of the
   others why it cannot be closed that way. Every test must fail if the line
   it covers is broken. Do not pad.
4. **Every new or changed test against *Unit Tests* in `WORKFLOW-LOCAL.md`.**
   It lives in the mirror and names its unit; it establishes its own
   precondition, calls one public operation and asserts a promised
   postcondition; its docstring states the contract. For each, name what
   would make it fail for a reason that is not a bug. Group tests that share
   one pattern, and name every distinct cause. Ask in particular:
   - The three integration files start real programs. Would any give another
     result as root, on macOS, on the hosted runner of the release workflow,
     outside a capsule, on a slow machine, or when two run at once? Name
     every wait, port, signal and fixed path they depend on.
   - The readiness tests open real sockets on loopback. Can another process
     change their result?
   - Which refactoring of a unit, with its behaviour unchanged, would turn a
     mirror test red?
   A finding here is a finding; "confined to tests" does not dismiss it.
5. **The changed code and its tests against *Host Inputs* in
   `WORKFLOW-LOCAL.md`, rules 1 to 6.** The rule was written after the code.
   Hold the code to it without mercy. Name every read of the host outside an
   entry layer, every parameter default that reads it, every parameter that
   only a test passes, every constructor that does more than store, every
   decision taken inside an entry layer, and every patch in a new or changed
   test. These deviations are known; judge each, and find the others:
   - `build_info.current_build_info()` and `is_built_distribution()` take no
     argument and read the package's own location.
   - `ConsoleInstallation.of_image()` names two paths of the image.
   - `entrypoint.run` branches twice on an answer of the session.
   - The command classes read `os.environ` in `run`; the framework gives
     them no constructor.
   - The fixture of the legacy file `tests/test_contained_display.py` patches
     `entrypoint.os.geteuid`. Its test functions did not change.
   - `display.py` and `diagnose.py` read the host themselves. They are
     outside this change.
   Then review the rule itself, as an agent that must follow it tomorrow
   with no other context. For each of the seven rules, say whether you
   could act on it alone, and name each case in this code base where two
   careful agents would read it differently. Put this under "On the rule"
   in the pull request body. Do not edit the rule.

Stay inside the scope: the modules listed above, their mirror tests, the
three integration files `tests/integration/test_console_decisions_cli.py`,
`test_version_cli.py` and `test_runtime_entrypoint_cli.py`, and the helpers
of `tests/test_contained_display.py`. Do not retire another legacy file. Do
not change `display.py`, `diagnose.py`, the command framework or the hosted
workflows. Do not change `WORKFLOW.md`, `WORKFLOW-LOCAL.md` or their
companions. Your own tests follow *Host Inputs* rule 5: no `monkeypatch`,
no `unittest.mock`, no assignment to a module or class attribute.

The direction itself, host inputs as values and no patch, is the owner's
decision. If you believe a patch or a parameter was the better design at
one place, argue it under "Proposals not implemented" and do not put it
back.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md` or the
  `evidence/` directory. Do not run `devcapsule workflow publish` or
  `devcapsule0 workflow publish`.
- Do not commit the `website` submodule pointer, `.idea/` files,
  `.devcapsule/` files, `*.egg-info`, `.nox/`, `dist/` or `__pycache__`.
  Stage explicit paths; never `git add -A` or `git commit -a`.
- Do not merge anything. Do not push to `main`, `release-0.3.1`,
  `ws-maintenance/host-inputs-at-source` or any branch other than
  `ws-maintenance/host-inputs-at-source-review-2`.
- Do not rebase or force-push. Do not build images or run capsules.

## Deliverable

1. Commits on `ws-maintenance/host-inputs-at-source-review-2`. Keep the
   human's author identity, `Costin Cozianu <ccozianu@gmail.com>`; check it
   with `git var GIT_AUTHOR_IDENT`. Each message names the component and the
   evidence and ends, after a blank line, with your trailer as *Commit
   Authorship* prescribes, for example
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`; read your
   session's model identity and do not copy the example blindly.
2. Push the branch with
   `git push -u origin ws-maintenance/host-inputs-at-source-review-2` and
   open one pull request with
   `gh pr create -R mycodespace-ai/devcapsule --base ws-maintenance/host-inputs-at-source --head ws-maintenance/host-inputs-at-source-review-2`.
   Title: `Correctness, clarity and coverage review of the rewrite of #26 (PR26.2)`.
   The body lists:
   - the hosted check's result for the head you reviewed;
   - each finding as: what was wrong or unclear, where, what you changed, how
     a test proves it;
   - your planted faults, each with the tier that catches it;
   - per *Unit Tests* rule 7, for the new and changed tests, what would make
     each fail for a reason that is not a bug;
   - "Host Inputs, rule by rule": each deviation, judged;
   - "On the rule";
   - "Considered and left alone, because";
   - "Proposals not implemented";
   - the result of each validation command, with counts, and what you did
     not run.
   If you change no file, still report: open no pull request, and print the
   same sections as your final message.
3. Print the pull request's URL as the last line of your output, or `NO PR`
   if you opened none.

Write the body and your report at about 80% ASD-STE100: one fact per
sentence, about twenty words, active voice. Back every claim about behaviour
with a test or a command you ran.

If you cannot proceed, because of a blocker like network or credentials,
stop and say exactly what blocked you. Do not work around a blocker.
