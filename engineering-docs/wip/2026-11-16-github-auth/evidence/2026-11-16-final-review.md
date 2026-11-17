# Final Pair Review and release target

Date: 2026-11-16. Implementor: GPT-6 Codex.
Reviewer: Antigravity Gemini 4 Hydrogen High (`gemini-4-hydrogen-high`, high effort).
Owner direction: complete the existing Pair Review and target release-0.3.1.

## Review outcome

Continued conversation `6280de13-6b45-4215-8e97-af6b466fbd61` with the committed
round-2 brief in an independent review worktree and virtual environment.
The streaming log ended with REVIEW_COMPLETE and ANTIGRAVITY_EXIT=0.
Its aggregate JSON still carries the earlier conversation's idle-timeout error;
actual commands, new commit, push and hosted review were independently verified.
The reviewer committed `455d3acc`; its 64 focused cases, mypy on 149 files and
conventions passed. Its full unit run had 3320 passed, two failed, one skipped,
191 deselected, one xfailed and one xpassed.

The implementor read the complete eight-file review diff and final correction
diff. Production corrections improve diagnostics and disclosure and remove dead
code. Tests cover hostile input, denial, fallback, socket permissions, process
group termination and cleanup. Round 2 bounds the whole readiness handshake,
closes client pipes, parameterizes unit inputs and states the deadline fixture's
0.5-second startup precondition. Assessment comments are on PR #44.
PR #44 merged through gh with a merge commit at `9638cb11`.

The reviewer checked the release launcher/authorization interaction. Its claim
of whole-subsystem Host Inputs compliance was too broad: broker/bridge/relay
still read clocks, processes and socket/filesystem state. The implementor's
assessment explicitly limits that claim. A larger effect-separation change and
a tighter send/operation deadline remain follow-ups, not completed corrections.

## Combined validation at 9638cb11

Commands ran from devcapsule-src. The full gate used:

```sh
PYTEST_ADDOPTS='--basetemp=/var/tmp/gpi' DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 .venv/bin/python -m nox -s build
```

Types passed on 351 files. Conventions: 98 legacy files, 1308 legacy tests,
67 conforming files, three command-line debt files, zero breaches.
Unit result: **3320 passed, 2 failed, 1 skipped, 191 deselected, 1 xfailed,
1 xpassed**, 80.36 seconds. The two failures are inherited:

- tests/test_recursive_orchestrator.py::test_public_dry_run_is_unique_redacted_and_cleans_owned_staging
- tests/test_recursive_orchestrator.py::test_contained_display_dry_run_forwards_no_host_x11

Both reject host Docker group ID zero in this rootless capsule. They match the
previously reproduced release baseline and the reviewer's independent run.
The formerly failing staging-path fixture passed with /var/tmp scratch.
No tests were disabled. The full gate is not green.

The combined branch's focused suite passed **64 cases** in 4.16 seconds,
including the proxy integration tests using real local Git operations.
The remaining gate sessions ran separately because build stops at pytest:

```sh
PYTEST_ADDOPTS='--basetemp=/var/tmp/gpw' DEVCAPSULE_DIFF_BASE=upstream/release-0.3.1 .venv/bin/python -m nox -s smoke pex docs-contract webconsole
```

All four passed: CLI smoke, PEX packaging/executable smoke, docs contract
(249 pages), console types (nine files), and **474 console tests**.

The rebuilt PEX completed git ls-remote over the inherited host proxy from an
empty temporary HOME with system/global Git configuration disabled. It returned
canonical HEAD `dac6b9d4033512d6ee47b9317faab51bad431c4f` with exit zero.
Pointing the adapter at a missing socket failed with exit 128.
No actual GitHub write, Docker launch or physical-host restart occurred.
Earlier recorded full E2E predates these review corrections and remains retained.

Local PEX: devcapsule-src/dist/devcapsule-local.pex. SHA-256:
`2dafaf3a3f0cdd5a4215a1b264d36571b5316a1ace770768e94361f19fcf6ec9`.
It is a validation artifact, not a published candidate or installed launcher.
Raw logs and probe result are in /var/tmp/github-auth-review-cycle; the reviewer
unit log is /var/tmp/github-auth-review-unit.log. They are disposable.

## Release targeting and delivery

PR #47's hosted base is release-0.3.1, verified after editing it with gh.
Package version, both workflow version stamps and docs/versions.yaml match the
release exactly. The release is an ancestor; no main synchronization was needed.
Three unrelated main-only documents and their index entries were removed from
this release-targeted tree. Their mainline copies remain in main's history.
The bump command refused a lower version, so the exact release version files
were restored for the explicit retarget; no workflow rule or manifest changed.

The owner-requested PR cleanup proceeded with the known failures stated in its
body after the required gate run. It does not waive release acceptance.
The human merges #47 into the release; maintenance propagates it to main.
No release branch was modified and no release or main merge was performed.

Main propagation constraint: this published branch retains its original mainline
ancestry. A later merge back to main must preserve main's development version and
these main-only documents, plus their blog/index entries, rather than propagate
the release-target cleanup as deletions on main:

- engineering-docs/blog/2026-11-13-thirteen-hours-thirty-five-tests.md
- engineering-docs/implementation-notes/devcapsule/2026-11-08-testing-the-macos-launcher-on-cloud-mac-hardware.md
- engineering-docs/work-orders/2026-11-08-test-improvements.md
