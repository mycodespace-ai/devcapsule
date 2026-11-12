---
status: fixing
severity: blocking
target: 0.3.1
owner: maintenance
opened: 2026-11-10
requirements: []
---

# Unit tests read the developer's real launcher settings inside a capsule: the consent and trust tests fail or prove nothing there

## Symptom and expected behavior

`nox -s tests`, run inside the owner's capsule on 2026-11-10, ends with 17
failed, 2893 passed, 14 expected to fail and 7 unexpectedly passed. The same
17 tests fail on the untouched `v0.3.1-rc2` tree, `be0140ca`, in the same
environment. The hosted runner passes the same suite on the same code.

Every one of the 17 is a consent, trust or launch-flow test that expects a
decision to be pending and finds it already made:

| File | Failing tests |
|---|---|
| `tests/test_run_flow.py` | 8 |
| `tests/test_trust.py` | 3 |
| `tests/configuration/test_contract.py` | 2 |
| `tests/test_ide_requirement_override.py` | 2 |
| `tests/test_capability_policy.py` | 1 |
| `tests/test_owner_commands.py` | 1 |

Three of them show what is lost:

- `test_consent_still_blocks_a_forced_launch_and_writes_nothing`
  (`tests/test_ide_requirement_override.py`) checks that `--force` does not
  skip the consent to Microsoft's channel for Visual Studio Code. No pending
  decision is raised.
- `test_second_checkout_cannot_inherit_the_first_checkouts_authority`
  (`tests/configuration/test_contract.py`) checks that a second checkout
  stops for base-image consent. Launch preparation returns 0 instead of 3,
  and the listing names the source of the consent: `home trust
  (devcapsule-base)`.
- `test_trust_write_is_private_atomic_and_keeps_previous_record_on_failure`
  (`tests/test_trust.py`) accepts a channel, then finds no settings file in
  the test's own home: the write it exists to test did not happen.

Expected: the outcome of a unit test is a function of the inputs the test
constructs, *Unit Tests* rule 2 of `WORKFLOW-LOCAL.md`. The suite gives the
same result inside any capsule, on any host and on the hosted runner,
whatever the developer has accepted in their own launcher settings.

## Environment and evidence

Confirmed on 2026-11-10 in the owner's DevCapsule capsule, launcher
`v0.3.1-rc2`, on branch `ws-maintenance/pile-of-ideas` at `c4bd458b` plus
Markdown changes only, and on an extract of the tag `v0.3.1-rc2`.

- The capsule mounts the host's launcher settings read-only:
  `/etc/devcapsule/home/settings.toml` is
  `/home/costin/.config/devcapsule/settings.toml` on the host, mounted `ro`.
- That file records three accepted channels: `claude-code`, accepted
  2026-11-01; `devcapsule-base` and `vscode`, both accepted 2026-11-08. Its
  last change is 2026-11-08; no test run wrote to it.
- With the mounted home pointed at an empty directory, by setting
  `devcapsule.runtime_configuration.HOME_PATH` in the test process, all 17
  pass: `17 passed in 1.35s`.
- With the same change, `tests/unit/devcapsule/legacy_refactoring` gives 15
  unexpectedly passed and 4 expected to fail. The four that still fail are
  one in `test_console_channel.py` and three in
  `test_repository_manifest_compatibility.py`, which read the repository's
  own configuration, a different cause.
- The full gate at the 0.3.1 cut, 2026-11-07 on `c449342f`, passed with 2825
  unit tests, 14 expected to fail and 7 unexpectedly passed. The two channels
  accepted on 2026-11-08 turned the 17 red.
- Hosted run for pull request #23 at `f69e9996`: success. The runner is not
  a capsule and has no launch context file.
- The two diagnostic runs above used the main checkout's virtual
  environment, whose installed metadata still says 0.2.15; the gate run used
  the environment Nox built. The 17 failures are from the gate run.

### A unit test downloads vendor artifacts

Found on 2026-11-10 while running the suite for another change.
`test_offered_agent_still_needs_consent_and_can_be_omitted`, in
`tests/unit/devcapsule/legacy_refactoring/test_capability_minimums.py`, runs
`project run --print-command` and expects it to stop for consent to the
Claude Code channel. In the owner's capsule the mounted settings have
accepted that channel, so the launch preparation goes on to acquire the
project's artifacts from the network, into the test's own cache under its
temporary directory:

- 1,490 MB in that one test's directory after the run, among them four
  files of 326, 205, 187 and 114 MB under
  `user/cache/devcapsule/artifacts/sha256/`. The largest carries the digest
  `426c3381…bf61f`, the Claude Code 2.1.321 `linux-x64` build pinned for
  0.3.1.
- The test process was observed in that test for more than ten minutes,
  with a download file growing and an HTTPS connection open. The whole run
  took 727 s without coverage; the gate run of the same day took 733 s with
  it. A run with the mounted settings hidden took 70 s, though 41 of its
  tests ended early for an unrelated reason, a temporary path too long for
  a Unix socket.
- The test is marked expected to fail inside a capsule, so it reports as an
  expected failure after the download and nothing looks wrong.
- pytest keeps the temporary roots of its last three runs under
  `/tmp/pytest-of-<user>`. Inside a capsule `/tmp` is a 2 GB tmpfs, so the
  second or third run of the suite fills it; it did on 2026-11-10, with
  `No space left on device`.

So the twelve minutes of the local unit gate, and the overflow of `/tmp`
that `WORKFLOW-LOCAL.md` warns about, come largely from this cause.

## Cause

`settings_source` in `devcapsule/configuration/storage.py` returns the
home's own `settings.toml` when it exists, and otherwise the launcher's
mounted settings when `mounted_settings_path` in
`devcapsule/runtime_configuration.py` offers them. That function answers
`/etc/devcapsule/home/settings.toml` whenever the launch context file
`/etc/devcapsule/launch-context.json` exists and no home is named through
`DEVCAPSULE_CONFIG_HOME`.

The autouse fixture `private_user_directories` in `tests/conftest.py` moves
`HOME` and every XDG directory under the test's `tmp_path` and deletes
`DEVCAPSULE_CONFIG_HOME`. A test's home therefore starts with no settings of
its own and names no home, which is exactly the case that falls back to the
mount. Inside a capsule every such test reads the developer's real
acceptances.

The cause was diagnosed on 2026-11-03 and again on 2026-11-04, and
`engineering-docs/development/unit-tests.md` records it under
`private_user_directories` for "the 0.3.1 fixture slice". The fix was queued
and not made. Thirteen tests failing for it then were marked expected to
fail and moved to `tests/unit/devcapsule/legacy_refactoring/`; the fixture
stayed as it was, so the next acceptance in the owner's settings broke the
next set of tests.

## Why it blocks 0.3.1

The owner's rating of 2026-11-10: this is fixed before 0.3.1 ships.

- The tests it disables are the ones that prove consent is still required:
  for a forced IDE, for a second checkout, for a vendor channel, for a
  partial answer. In the capsule where DevCapsule is developed, a regression
  in any of them cannot turn a test red, because the test is red already or
  never reaches the check.
- The project is developed inside its capsules, by agents that run the gate
  there. A gate with 17 standing failures teaches every pair to read past
  failures, and the release procedure's own gate cannot pass from a capsule.
- It grows without anyone touching the code: each channel a developer
  accepts changes which tests fail.
- It makes a unit test download more than a gigabyte of vendor software on
  every run, which is most of the local gate's twelve minutes and what
  fills the capsule's `/tmp`.

This supersedes, for this cause, the disposition in the 0.3.1 bug table
that the tests expected to fail inside a capsule are not a release gate.

## Scope

In this record:

- The isolation fixture: no test of the unit suite reads the mounted
  launcher settings unless the test constructs that mount itself.
- The 17 tests failing today.
- The expected-to-fail marks on tests whose only cause was the mount; 15
  tests under `tests/unit/devcapsule/legacy_refactoring/` pass once the
  mount is hidden.

Not in this record:

- The tests that read the repository's own manifest and lock, and the
  release-dependent fixtures of
  [the 2026-10-31 record](2026-10-31-release-dependent-test-fixtures.md).
- The refurbishment of the legacy test files to rules 1 to 4, which the
  standing order of *Unit Tests* rule 5 governs file by file.

## Fix notes

- The fix queued on 2026-11-03 is that the fixture sets
  `DEVCAPSULE_CONFIG_HOME` to the test's private home, so that
  `mounted_settings_path` answers `None`. It has not been tried. What was
  tried is the other lever, the mounted home path, as evidence of the cause.
- `tests/test_home.py` and `tests/test_checkout_commands.py` name
  `mounted_settings_path` or `settings_source`. Check that tests of the
  fallback itself build their own mount and still exercise it after the fix.
- Rule 5 forbids marking a legacy test expected to fail or deselecting it,
  and the fixture is not a legacy test file: the fix belongs in
  `tests/conftest.py`, not in the 17 tests.
- A guard worth adding: one test that builds a mounted settings file with an
  accepted channel and asserts that a default test home does not see it.

## Progress, 2026-11-12

On `ws-maintenance/launch-phases`, pull request #29, not merged. The cause
stands: the shared fixture still gives a home that falls back to the mount.
What changed is that the tests which failed now say what their home is.

- The 17 failing tests pass inside the owner's capsule. Ten, which call
  `prepare_launch` or the file's `accept` helper, hand in the home's
  settings as a value, `home={}`. `load_state`, `prepare_launch`,
  `accept_channel` and `write_settings` take that value; left out, they
  read the home as before. Seven, which drive the command line, get a named
  home from their own file's fixture, `DEVCAPSULE_CONFIG_HOME` under the
  test's directory, in five legacy files.
- The test that downloaded vendor artifacts is rewritten. It was the one
  test of `tests/unit/devcapsule/legacy_refactoring/test_capability_minimums.py`
  and drove the command line. It is now two tests of the launch review that
  build their checkout in memory, and its file is deleted. The network guard
  of `tests/conftest.py`, new in pull request #26, fails any unit test that
  tries the network.
- The product changed too, on the owner's word: `project run
  --print-command` no longer pulls the base image, downloads artifacts or
  builds the environment. It prints the command of an environment that is
  on the machine, and otherwise names what a launch would fetch and exits 2.
- Two more marked tests are rewritten and their holding-pen files deleted.
  The one test of `test_console_channel.py` became six tests in memory and
  four integration tests that run the channel as processes. The one test
  of `test_capability_commands_v2.py`, three cases, became four tests of
  the launch review in memory: a provider the project recommends, the
  checkout chose or the command line names accepts no channel, and a
  pending save stages nothing.
- The three marked tests of `test_repository_manifest_compatibility.py`
  never failed for this cause. They read this repository's own
  `.devcapsule` files and failed wherever a launcher had rewritten them,
  in a capsule or not. They are deleted with their legacy file, on the
  owner's word, and replaced by
  `tests/unit/devcapsule/configuration/test_capability_commands.py`, which
  reads frozen copies.
- `nox -s tests` passes inside the owner's capsule: 3105 passed, 3 expected
  to fail, 10 unexpectedly passed, in 170 seconds where it took 815.

Against the close criteria: 1 holds for the owner's capsule as it is today.
2 and 3 do not. Eight marks remain, on 11 cases, in four files. Nine
cases pass now. Two still fail inside the capsule for this cause, behind
their mark, because they take fixtures from legacy files that were not
changed: one in `test_environment_realization.py`, one in
`test_project_init.py`. They are in mirror files whose legacy twins stand,
so the gate refuses a change to them until those twins are retired; it
accepts the deletion of a whole holding-pen file whose tests are rewritten
elsewhere. 4 does not hold:
`private_user_directories` is unchanged, and a test that uses neither a
named home nor a handed-in one still reads the mount. The next channel the
developer accepts can turn other tests red.

## Verification target and close criteria

1. `nox -s tests` passes inside a capsule whose mounted settings carry
   accepted channels, the owner's capsule as it is today, with no failure
   and no new expected-to-fail mark.
2. The same run with empty mounted settings, and the hosted run, give the
   same counts.
3. No expected-to-fail mark remains whose reason is the mounted settings:
   each such test passes unmarked or is rewritten under rule 5.
   No unit test opens a network connection in that run.
4. `engineering-docs/development/unit-tests.md` describes
   `private_user_directories` as a private home without the exception.

Reopen if a unit test's outcome is again seen to depend on what the
developer has accepted in their launcher settings.
