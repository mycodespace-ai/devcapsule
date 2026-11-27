# Work Order: Test improvements — declared public surfaces, no patching of project modules, and the discovery module as the first move

Origin: owner and `maintenance` pair, in conversation on 2026-11-08, over one highlighted test,
`test_rider_discovery_uses_linux_release_with_checksum` in `devcapsule-src/tests/test_dotnet_rider_components.py`.
Status: delivered to `project-management` by mail on 2026-11-08; the owner asks that a `test-improvements`
workstream be opened from it. Not assigned. Implementation has not started.
Coordination owner: `project-management`. Implementation owner and target: the new workstream, on `main`.
Requirements: none. This is a process and code-quality order; it changes no product behaviour.
Supersedes nothing. It gives a home to the follow-ups queued in the maintenance status under
*Unit-test conventions — 2026-11-03*: the measured refactor of the legacy test debt, module by module.

## Outcome

Unit tests in this repository establish their preconditions by constructing inputs and calling one public
operation of the unit, never by replacing the unit's private parts from outside. Every module that a unit test
exercises says what is public. The gate refuses a test that patches a project module, so the cheap way to write
a test and the right way become the same way. The pattern is removed from the suite one module at a time, with
the owner choosing each module, and the first module is `devcapsule/components/discovery.py`, where the pattern
was born.

## What exists today

*Unit Tests* in `WORKFLOW-LOCAL.md` (owner direction of 2026-11-03, PR #335) states the rules a conforming
test follows: mirror placement, the Hoare triple with the precondition established by the test, a docstring,
and, in rule 4, that a unit with no declared public surface is not testable until it declares one. The gate's
checker, `devcapsule-src/scripts/validate_unittests_follow_conventions.py`, holds placement, docstrings and the
shrinking of legacy files. It does not hold rule 4, and no rule names patching at all.

The preamble of the project workflow definition names the discipline this order serves: that the best interface
hides the decision most likely to change, which is what information hiding has meant since Parnas said it. The
ast-grep guardrails order (2026-10-29) names the mechanism that defeats it: an agent reproduces whatever pattern
it finds, so spread compounds. Both are in the repository. Neither reaches a pair at the moment it writes a test.

The highlighted test shows the result. It is named for a checksum it never checks. It has no docstring. It
reaches the adapter by replacing `discovery.read_json`, a module helper, with a lambda that discards the address
it is asked for. Its one assertion indexes into a tuple that may be empty. The history is verified:

- The discovery module and the first tests that patch its helper arrived in one commit on 2026-09-21.
- Every later component that changed the module added a test copying the patch: Rider and Eclipse on
  2026-10-04, VS Code on 2026-10-28. Eleven tests across four files patch `discovery.read_json` or
  `discovery.read_metadata`.
- The module declares no `__all__`. Its docstring states a purpose, not operations. The component status
  module imports `read_metadata` from it, so a private transport helper became a shared one by accident.
- The assumption behind the patch, that the public operation calls the helper exactly once, is already false:
  the Claude Code adapter reads a latest pointer with one helper and a manifest with the other, at a
  different address, and the parametrized test in `test_component_status.py` answers both with the same
  document because its lambdas ignore the address. The test cannot tell which feed answered which question.
- The 2026-11-03 record already notes that pair review had endorsed a dissected test by name and dismissed
  its private monkeypatch as "confined to tests".

Measured on `main` at 8c5a4723, 2026-11-08:

| Measure | Launcher (`devcapsule-src`) | Web console |
|---|---|---|
| test files that use `monkeypatch` | 69 | — |
| `monkeypatch.setattr` calls | 346 | 22 |
| modules declaring `__all__` | 33 of 137 | 0 of 8 |

The most patched targets, by the first name of the target expression: `status` 16, `offer` 15,
`runtime_configuration` 14, `discovery` 11, `command_module` 11, `scenario_recorder` 9; by dotted string,
`sys.stdin` 43 and `devcapsule.container_runtime` 27. These numbers are the baseline the workstream measures
against; they are not targets in themselves.

## Decisions already taken

1. **The owner's ruling on the pattern.** A module helper such as `read_json` is not part of the public
   interface of `discovery.py`. Replacing it from a test, on the assumption that the operation under test calls
   it once and by that name, tests the implementation's call shape and not the unit's contract. The pattern is
   refused for conforming tests, not reviewed case by case.
2. **The gate holds it, not the reviewer.** The owner's judgment, consistent with the ast-grep order: this is the
   hardest kind of rule for a language model to follow from a statement of belief, because the models have
   learned from a corpus in which patching is the dominant idiom and it is the path of least change. A belief in
   the preamble does not act at the moment of writing. A gate line does. The rule therefore becomes a checked
   rule under *Unit Tests*, and the briefs carry it in one line.
3. **The pairs copy what they find, so the corpus must contain the right shape.** The first refactored module is
   the worked example that later pairs copy. It is the discovery module, because the pattern was born there and
   the seam is cheapest to add.
4. **A `test-improvements` workstream is opened for this.** `maintenance` stays on the release candidates of
   0.3.1 and does not take the implementation. The target is `main`; nothing in this order goes to
   `release-0.3.1`.
5. **From the 2026-11-03 record, unchanged:** the refactor of the legacy debt proceeds module by module, with the
   owner choosing the module; a legacy file only loses tests; a test you change is brought to the rules and
   moved to the mirror. Frameworks for contracts and property-based testing are decided inside the first
   implementing slice, not before it.
6. **Design is the owner's.** Separating fetching from interpretation in the discovery module changes a module
   boundary. The executing pair proposes the shape with the two candidates below and the owner rules before
   code is written. The same holds for every later module.

## Deliverables, in slices

Each slice is one pull request to `main` through the Pair Review Loop, with the unit session run on the branch
as pushed before the pull request opens.

### Slice 0: the rules and the gate

1. **Rule 8 under *Unit Tests* in `WORKFLOW-LOCAL.md`.** A conforming test does not set, replace or mock any
   attribute of a module of this project, whether by `monkeypatch.setattr`, `unittest.mock.patch` or
   assignment. It establishes its precondition by constructing the unit's inputs and calling one public
   operation. Patching the standard library or a third-party module is permitted and is named in the
   docstring, so the reviewer sees it. When a pair cannot test a unit without patching it, the required move is
   to stop and report that the unit has no seam, under rule 4; the report goes to the owner as a design
   question, and no test is written around it.
2. **Rule 4 made checkable.** Every module under `devcapsule-src/devcapsule/` and under the web console
   package declares `__all__`. Since 104 launcher modules and all 8 console modules lack one today, the rule
   is held the way legacy files are held: the checker compares with the pull request's base, a module the
   pull request touches must declare its surface, and the count of undeclared modules goes down and never up.
   The checker's summary line reports it beside the legacy counts.
3. **Imports respect the surface.** A `from devcapsule.<module> import <name>` in project code or in a test,
   where the imported module declares `__all__`, names only members of that `__all__`. Held by the checker from
   the base, the same way. The first known breach is the component status module's import of `read_metadata`;
   slice 1 removes it.
4. **The checker extension.** `validate_unittests_follow_conventions.py` gains the three checks above, each
   with a valid and an invalid case in its own mirror test file, in triple form. A breach prints one line naming
   the file, the rule and what to do instead. The checker stays a single script run by the `tests` and `build`
   sessions and the hosted `tests.yml` step; no new tool is introduced here. If the ast-grep guardrails order
   is executed first, the pattern rules may move there; this order does not wait for it.
5. **The house convention for units with effects**, one section in
   `engineering-docs/development/unit-tests.md`: a unit that reads the network, the filesystem, the clock or a
   process takes the effect's result, or the effect itself, at its public boundary, or splits into a pure
   interpretation and a thin fetcher with its own small contract. The section points at the discovery module
   as the worked example once slice 1 lands. One paragraph on what a fake is for and what it is not: a fake
   stands in for a collaborator the unit receives, never for a part of the unit itself.
6. **The brief.** The brief template in `engineering-docs/development/review-partner-loop.md` and rule 7 of
   *Unit Tests* gain one line for the implementor: no patching of project modules; if the unit offers no seam,
   report the missing surface instead of building one in the test. The reviewer checks it mechanically: no
   `setattr` or `patch` whose target starts with the project's package name in any new or changed test.

Done means: the three checks run in the gate against the measured baseline with zero breaches on `main`; a
deliberately patched mirror test and a deliberately undeclared touched module each fail the gate with the rule's
message, output captured in the pull request.

### Slice 1: the discovery module

1. **Public surface declared.** `discovery.py` declares `__all__`. The transport helpers are either private to
   it or moved to a module whose purpose is transport, with its own `__all__`; the component status module
   imports from wherever that is, by name in that `__all__`.
2. **Fetching separated from interpretation.** Two candidate shapes, for the owner to choose between before
   code is written:
   - *Documents in, reports out.* Each adapter is a function, or an object with one operation, from a vendor
     document already read to a `ChannelReport`. A thin fetcher reads the addresses the adapter names and
     calls it. A two-feed adapter, such as Claude Code's, takes its two documents by name.
   - *A reader passed in.* The adapter keeps its `check(current, platform)` operation and receives the reader
     at construction, with the production reader as the default supplied by the caller that wires the
     catalog, not by the adapter module.
   Either way a test constructs a document and calls the one public operation. Nothing in `devcapsule` is
   patched.
3. **The transport contract tested once.** Size bound, timeout, user agent and the JSON decode are tested
   against bytes the test constructs, through the reader's public operation. The present test that patches
   `urlopen` on the module goes with the rest.
4. **The eleven tests moved.** The eleven patching tests across `test_component_status.py`,
   `test_dotnet_rider_components.py`, `test_eclipse_component.py` and `test_vscode_component.py` are brought to
   rules 1 to 4 and 8 and moved to the mirror, each a triple with a docstring. The highlighted test becomes true
   to its name: one test that a release with a Linux download and checksum link is reported, one that a release
   missing the checksum link is refused. The two-feed adapter is tested with two named documents and with the
   version mismatch between them refused. The legacy count in the checker's summary goes down by eleven.
5. **The framework decision.** `exact_version` and `_available` are the trial for property-based testing, and
   the adapter contract is the trial for a contracts library, if the pair proposes one. The pair records the
   decision, with its measurement, in the workstream status; a "no, plain pytest" is a valid decision.

Done means: `grep -rn "monkeypatch.setattr(discovery" devcapsule-src/tests` finds nothing; the mirror holds the
tests; `nox -s build` and `nox -s typecheck` pass; the discovery adapters' observable behaviour, the reports
they produce for the same documents, is unchanged, shown by the moved tests passing against both the old and
the new module before the old one is deleted.

### Slice 2 and after: one module per slice, the owner choosing

The owner names the next module from the measured table, or from an incident. Each slice declares the module's
surface, adds or exposes the seam the owner has chosen, moves that module's legacy tests to the mirror in triple
form, and reports the two counts, legacy tests and undeclared modules, before and after. A slice that finds a
missing seam stops and asks, as rule 8 requires. The workstream keeps a one-table ledger in its status: module,
patch sites before, tests moved, seam shape chosen, pull request.

The web console is in scope for rule 4 and rule 8 from slice 0 onward: it has eight modules, none declaring a
surface yet, and 22 patch sites, so the whole package is one or two slices. Its first module is the owner's
choice as well.

## Acceptance evidence

1. The hosted run for each pull request, linked from the pull request body, with the checker's summary line
   quoted: legacy files and tests, undeclared modules, breaches zero.
2. Slice 0: the captured gate output for the two deliberate breaches.
3. Slice 1: the grep above empty; the eleven tests listed by new path; the before-and-after report equality
   shown in the pull request body, by the method the pair chose and names.
4. Each later slice: the ledger row, and the two counts going down.
5. The workstream's status file carries the owner's seam rulings as decisions, by module.

## Execution decisions and stopping points

The implementing workstream owns: the wording of the checker's messages, the placement of the transport
module, the structure of the mirror test files, and whether a fake collaborator lives in the mirror's conftest
or beside its test.

Stop and consult the owner before:

- choosing the seam shape for the discovery module, and for every module after it;
- adding any testing framework or library;
- changing a module's observable behaviour while moving its tests, however small;
- touching `release-0.3.1` or any branch of a release;
- extending the rules to the integration or end-to-end suites, which this order does not cover;
- deciding that a module's surface is "everything", which is not a declaration.

The owner names the workstream, confirms its first slice, and chooses every module after the first.

## Mainline evidence read before writing

On `main` at 8c5a4723 and the worktree of 2026-11-08: `WORKFLOW.md` sections 2.5, 8 and 12.11;
`WORKFLOW-LOCAL.md` *Unit Tests*; `engineering-docs/development/unit-tests.md` and `review-partner-loop.md`;
`devcapsule-src/scripts/validate_unittests_follow_conventions.py`; `devcapsule-src/devcapsule/components/discovery.py`
and `component_status.py`; the four test files named above; the maintenance status section *Unit-test
conventions — 2026-11-03*; the ast-grep guardrails order; the project workflow preamble's *What We Believe*;
the git history of `discovery.py` and of the four test files. The counts in the table come from `grep` over the
two test trees and the two packages at that revision.

## Pushback recorded with the draft

The pair first held that the highlighted test, being marked `legacy` and untouched since the rule of
2026-11-03, breached nothing, and that the fault was the unit's missing seam rather than the test. The owner
answered that tests here are written with the module they test, so the test and the seam are one decision, and
that a test added later copies the pattern of the tests written with the module; the history above confirmed
both. The pair's point survives only as the order's first deliverable: the seam has to exist before the test can
be right, so the rule tells the pair to stop and ask for it rather than patch around it.
