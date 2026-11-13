# Review brief for the Codex + GPT-6 Astra pair: PR26.1 on the removal of PR #18's test-only parameters

The Claude Code + Claude Fable 5.2 pair opened PR #26 ("Remove the test-only
parameters of PR #18; tests set the host at its source") on the branch
`ws-maintenance/host-inputs-at-source`, targeting `release-0.3.1`. It is a
follow-up to the merged PR #18 and its review, PR #19. No earlier review of
PR #26 exists. Your job is one improvement pull request, PR26.1, against
`ws-maintenance/host-inputs-at-source`.

## Your checkout

You are in the git worktree at `/home/devcapsule/worktrees/maintenance-review`,
on the branch `ws-maintenance/host-inputs-at-source-review`, branched from
`ws-maintenance/host-inputs-at-source`. Work only there. Do not touch the
implementor's checkout at `/workspace/301e4208ef81-ChatGPT_Codex`, and run no
test there.

Read first, in this order:

1. `AGENTS.md`, `WORKFLOW.md` topic 9.11, `WORKFLOW-LOCAL.md` (*Unit Tests*
   rules 1 to 7, *Pair Review Loop In This Checkout*, *Commit Authorship*),
   `WORKFLOW-LOCAL-humane.md` (*Unit Tests*).
2. `engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md`, the
   section "PR #18's test-only parameters removed; the tests set the host at
   its source — 2026-11-11". It holds the findings this slice answers, the
   four judgments taken for the owner, and the proposals not implemented.
   The section "Whole-file legacy test retirement and 4-file refurbishment
   for 0.3.1" below it records what PR #18 did and why.
3. `engineering-docs/bugs/devcapsule/2026-11-10-unit-tests-read-the-capsules-mounted-launcher-settings.md`.
   It explains the 17 unit tests that fail in this capsule on every branch.
4. `devcapsule-src/devcapsule/container_runtime/entrypoint.py`, whose module
   docstring is the contract of the largest change.

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
    .venv/bin/python -m pytest --no-cov -q tests/unit/devcapsule/container_runtime tests/unit/devcapsule/commands/test_version.py tests/unit/devcapsule/test_console_tools.py tests/unit/devcapsule/test_build_info.py
    .venv/bin/python -m pytest --no-cov -q -m integration tests/integration/test_console_decisions_cli.py
    .venv/bin/python -m pytest --no-cov -q tests/test_runtime_entrypoint.py tests/test_contained_display.py tests/test_eclipse_component.py tests/test_vscode_component.py tests/test_runtime_diagnose.py
    DEVCAPSULE_DIFF_BASE=origin/release-0.3.1 .venv/bin/python -m nox -s tests

Facts of this capsule that you must know before you read a result:

- `nox -s tests` ends with 17 failed here, on this branch and on
  `release-0.3.1` alike. The bug record of item 3 names the six files and the
  counts. A failure outside that list is a finding. Because of them
  `nox -s build` cannot pass in this capsule; do not run it. The hosted run
  is the authority for the whole suite.
- One unit test downloads 1.5 GB into its scratch under `/tmp`, a 2 GB
  tmpfs. Run the unit session once, as the last command. Before it, run
  `df -h /tmp`, and delete only the `/tmp/pytest-of-*/pytest-<N>` directories
  that your own earlier runs left. Use the default scratch: no `--basetemp`,
  no `/opt/devcapsule-gate`, nothing under `/home/devcapsule`.
- Run commands in the foreground and one at a time. Two pytest sessions at
  once collide in `/tmp`.
- You are inside a capsule: `DEVCAPSULE_CONTAINER_NAME` is set,
  `/opt/devcapsule-webconsole` and `/ide-config` exist. The hosted runner has
  none of them. A test that passes here for that reason is the defect class
  this slice exists to remove.

Read the hosted check of the head before you start and again before your
final report:

    gh pr checks 26 -R mycodespace-ai/devcapsule

State its result in your pull request body. If it is red or pending when you
finish, say so in the first line of the body.

Do not build images, start capsules or run the end-to-end sessions.

## The task

Review the diff of PR #26 against its base:

    gh pr diff 26 -R mycodespace-ai/devcapsule

The code of before PR #18 is at `b84b06e9^1`; `git show b84b06e9^1:<path>`
shows any file as 0.3.0 shipped it.

What the change does. PR #18 added twenty keyword parameters to eight
production signatures so that no refurbished test would patch a
`devcapsule.*` attribute. No production caller passes them. PR #26 removes
seventeen and restores the bodies of before PR #18. The mirror tests now set
each host input where the code reads it, with `monkeypatch`, on public names
only: `os.geteuid`, `os.chown`, `socket.create_connection`, `os.environ`; the
constants `CONSOLE_PYTHON`, `LAUNCHER_CONSOLE_SOURCE`, `RUNTIME_ROOT` and
`RUNTIME_PLAN_PATH`; and, in `test_entrypoint.py` only, `entrypoint.Supervisor`,
`entrypoint.prepare_contained_display` and `logs.configure`.

Improve it on your branch, focused on these four things, in this order.

1. **Correctness of the new and modified lines.**
   - Is each restored function the function of before PR #18 in behaviour?
     Compare `entrypoint.run`, `console_child`, `prepare_filesystem` and
     `foreground_command` with `b84b06e9^1`, and account for every difference.
   - Does any caller still pass a removed parameter or import a removed name
     (`ConnectionProbe`, `ChownFunc`, `SupervisorFactory`, `SupervisorRunner`,
     `LogConfigurer`, `DisplayPreparer`, `ConsoleBuilder`)? Look in
     `devcapsule/`, `scripts/`, `noxfile.py`, `devcapsule-webconsole/` and
     every test, legacy ones included.
   - `filesystem.RUNTIME_ROOT` is new. Is it read at call time? Is `/tmp`
     what a real session still gets? `container_runtime/diagnose.py` writes
     the same path as a literal; is that a defect of this change or a
     neighbour to leave?
   - `run` calls `logs.configure` without `environ=` again. Does the log level
     still come from the process environment?
   - `console_child` lost `launcher_source`, which PR #16 added. Is the
     precedence of `D-0017` intact: the plan's checkout source, then the
     launcher's package, then the base's copy? Does `tests/conftest.py` still
     keep every test away from the capsule's real `/opt/devcapsule/webconsole`?
   - Is the new sentence in `images/contract.py` true? Read where
     `launch/pycharm/_launcher.py` plans a console without having read labels.
2. **Clarity of the new and modified lines.** The standard is "obviously no
   deficiencies". Read the fixtures `host` in `test_entrypoint.py`,
   `base_python` in `test_console.py` and `enter_capsule` in
   `test_console_tools.py` as a stranger would.
3. **Test coverage of the new and modified lines.** Plant faults of your own
   in the touched production code and report which test catches each; do not
   only repeat the 26 of the status section. Add a test where a line of the
   touched code is run by no test of the gate. Every test must fail if the
   line it covers is broken. Do not pad. Two gaps are known and recorded:
   the one line by which `CheckoutDecisionsCommand.run` delegates, and the
   default record locations of `current_build_info`.
4. **Every new or changed test against *Unit Tests* in `WORKFLOW-LOCAL.md`.**
   It lives in the mirror and names its unit; it establishes its own
   precondition, calls one public operation and asserts a promised
   postcondition; its docstring states the contract. For each, name what
   would make it fail for a reason that is not a bug. Group tests that share
   one isolation pattern, and name every distinct cause. Ask in particular:
   - Does any test patch a private name, or a name the unit does not read?
   - Does replacing `os.environ`, `os.geteuid` or `os.chown` for one test
     reach pytest's own work, another fixture, or the next test?
   - Would any of these tests give another result as root, on macOS, where
     IPv6 is off, where `/tmp` is not writable, outside a capsule, or on the
     hosted runner?
   - Which refactoring of the unit, with its behaviour unchanged, would turn
     a test red?
   A finding here is a finding; "confined to tests" does not dismiss it.

Stay inside the scope: the signatures PR #18 changed, their mirror tests, the
integration file `tests/integration/test_console_decisions_cli.py` and the one
docstring in `images/contract.py`. Do not retire another legacy file. Do not
change `current_build_info` or the signature of `console_decisions_command`.
Do not change `WORKFLOW.md`, `WORKFLOW-LOCAL.md` or their companions.

The first judgment of the status section, that a production signature has a
parameter only when production passes it, is the owner's to decide. If you
believe the parameters were the better design, argue it under "Proposals not
implemented" and do not put them back.

## What you must not do

- Do not edit `CURRENT-STATUS.md` files, `intake-dispositions.md` or the
  `evidence/` directory. Do not run `devcapsule workflow publish` or
  `devcapsule0 workflow publish`.
- Do not commit the `website` submodule pointer, `.idea/` files,
  `.devcapsule/` files, `*.egg-info`, `.nox/`, `dist/` or `__pycache__`.
  Stage explicit paths; never `git add -A` or `git commit -a`.
- Do not merge anything. Do not push to `main`, `release-0.3.1`,
  `ws-maintenance/host-inputs-at-source` or any branch other than
  `ws-maintenance/host-inputs-at-source-review`.
- Do not rebase or force-push. Do not build images or run capsules.

## Deliverable

1. Commits on `ws-maintenance/host-inputs-at-source-review`. Keep the human's
   author identity, `Costin Cozianu <ccozianu@gmail.com>`; check it with
   `git var GIT_AUTHOR_IDENT`. Each message names the component and the
   evidence and ends, after a blank line, with your trailer as *Commit
   Authorship* prescribes, for example
   `Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>`; read your
   session's model identity and do not copy the example blindly.
2. Push the branch with
   `git push -u origin ws-maintenance/host-inputs-at-source-review` and open
   one pull request with
   `gh pr create -R mycodespace-ai/devcapsule --base ws-maintenance/host-inputs-at-source --head ws-maintenance/host-inputs-at-source-review`.
   Title: `Correctness, clarity and coverage review of #26 (PR26.1)`.
   The body lists:
   - the hosted check's result for the head you reviewed;
   - each finding as: what was wrong or unclear, where, what you changed, how
     a test proves it;
   - per *Unit Tests* rule 7, for the new and changed tests, what would make
     each fail for a reason that is not a bug;
   - "Considered and left alone, because";
   - "Proposals not implemented";
   - the result of each validation command, with counts, and what you did
     not run.
   If you find nothing to change, say so in your final report and open no
   empty pull request.
3. Print the pull request's URL as the last line of your output, or `NO PR`
   if you opened none.

Write the body and your report at about 80% ASD-STE100: one fact per
sentence, about twenty words, active voice. Back every claim about behaviour
with a test or a command you ran.

If you cannot proceed, because of a blocker like network or credentials,
stop and say exactly what blocked you. Do not work around a blocker.
