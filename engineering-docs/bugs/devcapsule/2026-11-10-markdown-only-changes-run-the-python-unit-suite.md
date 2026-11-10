---
status: confirmed
severity: minor
target: none
owner: maintenance
opened: 2026-11-10
requirements: []
---

# Markdown-only changes run the whole Python unit suite: the hosted path filter lists too few non-inputs, and the local gate has no filter

## Symptom and expected behavior

Reported by the owner on 2026-11-10. Pull request #23 changes 13 files, all
Markdown. Every push to it ran the hosted Python job, about four minutes
each time, and the documented local gate ran the whole suite for the same
change, twelve minutes in the owner's capsule.

Expected: a change that no unit test can observe does not spend the Python
job. The hosted workflow already routes by path for that purpose, through
`.github/ci-paths.yml`; the route should skip the job whenever every changed
file is a file no test reads. The local gate should offer the same economy,
or the documents should say when the unit run may be left out.

## Environment and evidence

Confirmed on 2026-11-10 on `ws-maintenance/pile-of-ideas`, from
`release-0.3.1` at `c4bd458b`.

Cost:

- Hosted, job *Python 3.12* of *Tests and coverage*: 223 s at `f69e9996`
  and 229 s at `fd0b5a61`. Two earlier pushes were cancelled by newer ones.
- Local, `nox -s tests` in the owner's capsule: 733.88 s.

Why the hosted route chose the Python job. The filter names the paths that
are not test inputs, and any changed file it does not name runs the suite.
Of the 13 files:

| Changed file | Listed as a non-input | Read by a unit test |
|---|---|---|
| `WORKFLOW.md` | no | one test, marked expected to fail |
| `WORKFLOW-humane.md` | no | none |
| `engineering-docs/pile-of-ideas/` (3 files) | no, a new subtree | none |
| `engineering-docs/releases/v0.3.1/README.md`, `bugs.md` | no, `releases/` is kept whole | none |
| `devcapsule-src/devcapsule/assets/project_workflow/definition/WORKFLOW.md` | no, package data | ten tests |
| `devcapsule-src/devcapsule/assets/project_workflow/README.md` | no, package data | one scan, marked expected to fail |
| `engineering-docs/README.md`, `index.md`, one file under `engineering-docs/wip/`, one under `engineering-docs/bugs/` | yes | none |

One file of the 13 is a real input: the packaged definition. Without it the
job would still have run, for the seven files in the first four rows.

Which repository Markdown files the unit suite reads. Measured by running
the unit selection once with an audit hook on `open` events
(`sys.addaudithook`), keeping paths that end in `.md` under the repository
root and attributing each to the running test through
`pytest_runtest_logstart`. Sixty files were opened:

- `devcapsule-src/devcapsule/assets/project_workflow/definition/`, four
  files, by ten tests: seven in `tests/test_workflow_bootstrap.py`, two in
  `tests/test_cli.py`, one scan in
  `tests/unit/devcapsule/legacy_refactoring/test_home.py`.
- `WORKFLOW.md` at the root, by
  `test_packaged_workflow_is_the_root_reusable_definition`, marked expected
  to fail and flaky.
- `engineering-docs/releases/v0.2.14/notes.md`, by
  `test_notes_accepts_the_0_2_14_notes_as_published` in
  `tests/test_release_docs.py`. No other file under `releases/` was opened.
- Fifty files under `docs/`, and four more under `devcapsule-src/`, by the
  three parameters of `test_replaced_scope_word_is_absent` in
  `legacy_refactoring/test_home.py`, marked expected to fail.

Nothing else was opened: not `WORKFLOW-humane.md`, `WORKFLOW-LOCAL.md`,
`AGENTS.md`, `CURRENT-STATUS.md` or `index.md` at the root, and nothing
under `engineering-docs/` except that one notes file.

A second finding from the same run: the filter lists `docs/**/*.md` as a
non-input of the Python route, yet a test reads fifty of those files. The
listing is harmless only while that test stays marked expected to fail.

Limits of the measurement:

- It ran in the main checkout's virtual environment with the capsule's
  mounted launcher settings hidden, not in the environment Nox builds.
  Fifty-seven tests failed or errored there before finishing, in seven
  modules: `test_recursive_host.py`, `test_console_channel.py`,
  `test_host_open.py`, `test_recursive_orchestrator.py`,
  `test_jetbrains_session.py`, `unit/devcapsule/launch/pycharm/test_launcher.py`
  and `unit/devcapsule/test_recursive_successor_plan.py`. None of the seven
  names a Markdown file or a repository path.
- It sees the test process only. A file read by a program a test starts is
  not counted.
- It covers the unit selection, not the integration or end-to-end suites.

An observation, not a finding: that run, without coverage, took 65 s, against
733 s for the gate run in the same capsule. The difference is not isolated;
the environment, the coverage measurement and the tests that ended early all
differ.

## Cause

Hosted: `.github/ci-paths.yml` is conservative by design, and its header
says so: an unclassified path runs the job. The cost of that design is paid
whenever a subtree or a root file has not been classified. Root
`WORKFLOW-humane.md` was never listed, `engineering-docs/releases/` is kept
as an input as a whole although one file of it is read, and a new subtree
such as `engineering-docs/pile-of-ideas/` runs the suite until someone
proves it a non-input and lists it.

Local: `nox -s tests` and `nox -s build` take no account of what changed.
*Validation Commands* in `WORKFLOW-LOCAL.md` names no case in which the unit
run may be left out, so an agent that follows it runs the whole suite for
any change.

## Fix notes

Not started. The choices are the owner's.

- Hosted, the small step: list the proven non-inputs.
  `engineering-docs/pile-of-ideas/**` and `WORKFLOW-humane.md` are read by
  no test. `engineering-docs/releases/**` could be narrowed to the file the
  suite reads, or the test could construct its notes file, as *Unit Tests*
  rule 2 asks.
- Root `WORKFLOW.md` is read by one test that is expected to fail. Whether
  it is an input depends on what becomes of that test.
- `tests/test_ci_reporting.py` runs the routing script with each kind of
  input; a change to the filter goes with its tests.
- The measurement above could be kept as a script, so that the filter's
  lists rest on a check that can be repeated and not on memory.
- Local: either a documented rule for when the unit run may be left out, or
  the same routing applied to the local gate.

## Verification target and close criteria

1. A pull request that changes only files no unit test reads does not run
   the hosted Python job; one that changes a packaged definition file still
   does.
2. The local workflow says what to run for such a change, and an agent
   following it does not run the unit suite for it.
3. The `docs/**/*.md` listing and the test that reads those files no longer
   contradict each other.

Reopen if a Markdown-only change is again seen to run the unit suite without
a test that reads one of its files.
