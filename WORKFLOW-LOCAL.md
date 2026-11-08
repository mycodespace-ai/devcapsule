# Local Workflow: DevCapsule

This file is the project's own half of the workflow. `WORKFLOW.md` binds
wherever it speaks. This file binds wherever `WORKFLOW.md` is silent. See topic
4.2 in `WORKFLOW.md`. The reasons for the rules below are in
[`WORKFLOW-LOCAL-humane.md`](WORKFLOW-LOCAL-humane.md), which is *for humans*.

DevCapsule develops the generic definition. Its root `WORKFLOW.md` is the
source of the packaged one, not an installed copy. See *Exceptions*.

## Integration Branch

`main`.

## Version Scheme

1. Versions follow PEP 440.
2. Between releases the source carries `X.Y.Z.dev0`, the development form of
   the release it works toward. The suffix stays `dev0`.
3. The release branch's first commit sets the release version `X.Y.Z`, or
   confirms it when the product owner has already set it.
4. At the cut, `main` reopens with the next development version: the next
   patch, unless the owner names another, set by a pull request to `main`
   as soon as the release branch exists. `main` is then ahead of every
   candidate and of the final release for the whole cycle, and the merges
   of the release branch into `main` before each candidate tag carry no
   version conflict after the first. Owner decision, 2026-10-18.
5. Candidate builds are stamped `X.Y.ZrcN` from their tags. Local builds carry
   a local marker. Never author either in the source.
6. The single authored copy is `[project] version` in
   `devcapsule-src/pyproject.toml`. The frontmatter of `WORKFLOW.md` and of the
   packaged definition mirror it.
7. Set all three with one command, from `devcapsule-src`:

   ```text
   .venv/bin/python -m nox -s bump -- <major|minor|patch|X.Y.Z[.devN]>
   ```

8. `nox -s build` checks that the copies agree.

## Release Policy

1. The [operator guide for releasing a new version](engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md),
   owned by `project-management`, is the release policy.
2. Refs use the default spelling: `release-X.Y.Z`, `vX.Y.Z-rcN`, `vX.Y.Z`.
3. GitHub Actions builds and publishes candidates.
4. Each candidate is gated on a resolved main disposition: ancestry, patch
   equivalence, or the documented evidence record the guide describes.
5. Acceptance requires downloaded-artifact smoke evidence.
6. The acceptance record lives under `engineering-docs/releases/`.
7. Since 2026-09-28 a release includes its documentation. The guide's
   *Documentation Is Part Of The Release* names the obligations. Documentation
   is published per [the content–website contract, version 1](engineering-docs/specifications/product/content-website-contract.md).
   `docs/versions.yaml` on `main` is the authored list of documented versions.
   Promote it on the release branch before the final tag and merge it to `main`.
8. Merge the release branch into `main` through a throwaway copy. Create
   the copy at the release branch's tip, named `4PR-NNN-release-X.Y.Z`, for
   one pull request. NNN counts from 1 within the release. Commit nothing to
   the copy. Point no tag into it. The candidate workflow checks tags against
   `release-X.Y.Z` alone. Owner decision, 2026-10-18.
9. The integration tests run before a candidate is produced. The
   candidate workflow runs the ones that need no Docker against the
   release executable. The ones marked `docker` run where a daemon is
   known, and their run is recorded in the test-run record,
   `engineering-docs/releases/vX.Y.Z/test-runs.json` on `main`, which the
   gate reads as it reads the acceptance record: the kind, the source
   revision, the tests, the environment, the operator, the date, the
   result and the evidence. The candidate workflow refuses a candidate
   when the record has no run on the candidate's source revision or that
   run reports a failure. Owner direction, 2026-11-06.
10. At least one end-to-end test runs for every release, against the
   accepted candidate's bytes, and its run is recorded in the test-run
   record with the candidate's checksum. The final tag points at the
   accepted candidate's commit, so the final is the candidate's source
   and frozen inputs rebuilt under the final version, and the candidate's
   bytes are the ones the end-to-end tests saw. The release notes carry a section
   *End-to-end tests run*, rendered from the record, naming each test
   that ran; when fewer than all end-to-end tests ran, the record and the
   section give the argument for the selection. The final-tag job
   refuses the release when the record has no end-to-end run on the
   accepted candidate, names a test the revision does not have, omits the
   argument for a subset, or when the notes' section differs from the
   rendering. Owner direction, 2026-11-06.

## Documentation Refs

Owner grant of 2026-09-28, exercised by `project-management`.

1. The project declares one ref kind of its own: `docs-<version>`.
2. Fork a `docs-<version>` branch from the release branch at the promotion
   commit, before the final tag. Push it with
   `git push origin HEAD:refs/heads/docs-X.Y.Z` immediately after that commit.
   Keep its `docs/` tree equal to the final tag's documentation.
   The final-tag job verifies this equality.
3. Commit only documentation changes to it: changes under `docs/` and nothing
   else.
4. Never merge it anywhere. Never rebase it.
5. Name it in `docs/versions.yaml` as that version's `source` for as long as
   it exists. Without it, the version's source is its final tag.
6. The candidate gate does not apply to it. The website's build check does.
7. Anyone may commit to it on the owner's or `project-management`'s direction.
   `user-docs` normally authors the corrections.

## Blog Entries

When the human says "write a blog entry on topic X":

1. Create `engineering-docs/blog/YYYY-MM-DD-short-topic.md`. Use the date of
   writing. The website reads the date from the filename.
2. Begin with the front matter block the blog README describes: `description`
   and, until the owner releases the entry, `draft: true`. Then `# Title` and
   plain Markdown prose. Use existing entries as examples. Add no other
   website markup.
3. Attribute quoted material. Identify any editing of quotations. Link
   repository evidence by a mainline commit SHA.
4. Add the entry to `engineering-docs/blog/README.md` and to root `index.md`.

The website picks up these files. Its [publishing instructions](website/PUBLISHING.md)
define deployment. There is no blog proposal, schedule, or approval procedure.

## Validation Commands

Every command runs from `devcapsule-src`. The environment is the virtual
environment under `devcapsule-src/.venv`. `nox`, `pytest`, `mypy`, and the
package's dependencies live there and nowhere else on the machine, inside a
capsule as well as on a host. The kinds are the definition's; see *Validation*
in [`INFORMATION-MODEL.md`](devcapsule-src/devcapsule/assets/project_workflow/definition/INFORMATION-MODEL.md).

- **Environment**: if `.venv` is absent, create it:

  ```text
  cd devcapsule-src
  python3.12 -m venv .venv
  .venv/bin/python -m pip install -r dev-requirements.txt
  .venv/bin/python -m pip install -e . --no-deps
  ```

  Inside a capsule `/tmp` is a 2 GB tmpfs that the gate's scratch overflows.
  Run with `PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest"` or
  another directory with room.
- **Unit tests**: `.venv/bin/python -m nox -s tests`, with coverage. One
  module while working: `.venv/bin/python -m pytest -q tests/<module>.py`.
  See [unit tests](engineering-docs/development/unit-tests.md).
- **Advisory diff coverage**: from `devcapsule-src`, run
  `.venv/bin/python -m pytest tests/ --cov-report=xml:coverage.xml`, then
  `.venv/bin/diff-cover coverage.xml --compare-branch=origin/main`.
  Fetch and name the actual target branch. Keep execution serial. Do not
  apply a failing coverage percentage. See [unit tests](engineering-docs/development/unit-tests.md).
- **Integration tests**: `.venv/bin/python -m nox -s integration`. An
  integration test runs a subsystem with the real external things it
  uses, the built executable, a subprocess, git or the Docker daemon, and
  fakes the services it does not test. Run it on demand, as the
  end-to-end suites are run; the gate and the unit selection do not run
  it. A test that needs the Docker daemon carries the `docker` marker.
  `nox -s typecheck` and `nox -s docs-contract` are checks of the gate,
  not tests. See
  [integration tests](engineering-docs/development/integration-tests.md).
- **End-to-end tests**: `.venv/bin/python -m nox -s e2e`, plus
  `pex_clean_machine`, `recursive_dogfood_e2e`, and `ide-smoke`. An
  end-to-end test drives the product through its user entry point, fakes
  nothing, and reads the result from outside. Each needs Docker and is
  opt-in. At least one runs for every release. Evidence lands under
  `devcapsule-src/dist/e2e-evidence/`. See
  [end-to-end tests](engineering-docs/development/e2e-tests.md).
- **Smoke test**: `.venv/bin/python -m nox -s smoke` starts the built
  executable and proves its commands answer. `nox -s ide-smoke` launches each
  IDE surface in a fresh project and proves from the outside that the IDE
  comes alive: the desktop URL answers and the IDE owns a window.
  Rider: `nox -s ide-smoke -- --display --surface rider --component-browser`
  builds and runs a package-free C# fixture with the selected SDK and retains
  noVNC pixels. `--agent` additionally requires a saved edit and visual
  recognition. It fails if Rider licensing prevents editor access.
  Eclipse: `nox -s ide-smoke -- --agent --surface eclipse --component-browser`
  requires a noVNC editor save, checks the saved file independently, and keeps
  the Playwright movie. Use `--display` instead of `--agent` for startup only.
- **Web console**: `.venv/bin/python -m nox -s webconsole` type-checks and
  tests `devcapsule-webconsole/`, the capsule web console, in its own
  environment built from that directory's hash-pinned
  `requirements-dev.txt`. The console is a separate distribution; it never
  shares the runtime's environment. See its [README](devcapsule-webconsole/README.md).
- **Gate**: `.venv/bin/python -m nox -s build`, before a checkpoint and
  before integration: distribution version, Python and shell syntax, type
  check, unit tests, CLI smoke, the executable built and smoked, the
  documentation contract, then the web console session. The integration
  and end-to-end suites are not in it. The [developer brief](DEVELOPING.md)
  says when they run.

## Unit Tests

Owner direction, 2026-11-03, after eighteen tests failed in the owner's
capsule for reasons that were not bugs.

1. A unit test file mirrors the module it tests:
   `tests/unit/<path>/test_<name>.py` tests `<path>/<name>.py` or
   `<path>/_<name>.py` under `devcapsule-src`. The unit under test is that
   module. A test of a heavier suite lives outside the mirror and carries
   that suite's marker at module level.
2. A test is a Hoare triple. It establishes its precondition in its own
   fixtures or asserts it first; a precondition inherited from the
   repository's checkout, the host or the capsule that runs the test is not
   a precondition. It performs one action: a call to one public operation
   of the unit, or the raise it expects. It verifies a postcondition the
   unit promises, never a value copied from a run. Release identifiers,
   version strings and digests are not assertions of the unit suite.
   The outcome of a unit test is a function of the inputs the test
   constructs. The clock, another process, a service on any host, the
   network, the environment and the state of the host are inputs: the
   test sets them, or the unit does not read them. A unit that needs the
   time takes it as a parameter, and the test passes the instant. A unit
   test starts another program only when running that program is the
   unit's contract, and then with inputs the test controls. A test
   computes in its own process what it can compute there. A test that
   needs a program for what the program does is an integration test.
3. Every test function has a docstring stating, in plain English, the
   contract or the part of it under test. One line is enough when the body
   is already plain; the reviewer decides that, not the author.
4. A unit with no declared public surface is not testable under rule 2
   until it declares one: `__all__`, or a module docstring that names the
   public operations and leaves the rest private.
5. Existing test files carry `pytestmark = pytest.mark.legacy`. Do not
   add, change or delete individual test functions in a legacy file. When
   a change edits a test in a legacy file or adds or changes tests in its
   mirror, refurbish the entire legacy file to rules 1 to 4, move its
   tests to their mirrors, and delete the legacy file. Fix or replace a
   legacy test that a legitimate change breaks; never mark it expected to
   fail or deselect it. Add no marker other than `legacy` to a legacy
   file.
6. The gate holds rules 1, 3 and 5: `scripts/validate_unittests_follow_conventions.py` runs in
   the `tests` and `build` sessions and in `tests.yml`, comparing legacy
   files with the pull request's base. Its summary line counts the legacy
   files and tests; the count goes down and never up.
7. In a Pair Review Loop, the brief instructs the reviewer to verify rules
   1 to 4 on every new or changed test, and to name for each what would
   make it fail for a reason that is not a bug.

## Reasoning And Code Navigation

1. Start with the behavior's contract: ownership, inputs, preconditions,
   invariants, and postconditions.
2. State what is known and the specific uncertainty the next code read must
   resolve.
3. Navigate from the responsible entry point through its types, imports, and
   calls. Read enough surrounding implementation to understand the behavior.
   Use direct file navigation and exact-name lookup.
4. Use regular-expression searches only as a last resort, when reasoned
   navigation and literal lookup cannot locate the implementation. Explain
   that gap before searching.
5. A search match is a navigation aid. It is never evidence that a contract is
   satisfied. Do not substitute repeated pattern searches for reasoning.

## Publication Refs

1. `component-status` and `badges` are project-owned generated publication
   branches. Never select one as an editing workstream. Never merge one into
   `main`. Never force-push one. Commit nothing generated to `main`.
2. The `component-status.yml` action may create `component-status` and advance
   it by fast-forward commits that contain the compatibility feed and the
   GitHub-rendered status page. See
   [service operations](component-status/README.md).
3. The `tests.yml` action may create `badges` and advance it by fast-forward
   commits that contain `coverage.svg`, the coverage badge of the mainline run
   it reports on. `README.md` links the badge by its raw address on that
   branch.
4. Authored policy and implementation of both follow ordinary workstream PR
   delivery.

## Host Capabilities

1. The `[host.*]` tables in `.devcapsule/devcapsule.toml` declare what this
   checkout needs from the machine, each with its justification: the Docker
   socket, to run peer DevCapsule instances during the full test suite; host
   networking, for host-bound development services; development sudo.
2. The *Coordination Baseline* in root `CURRENT-STATUS.md` records the hosting
   facts: the canonical repository and owner-operated pull-request delivery.
3. The GitHub integration rules below govern agent access and the UI handoff.

### Dogfooding CLI Selection

Owner direction, 2026-09-24.

1. This project's configuration recommends
   `runtime.devcapsule-command = "devcapsule0"`.
2. A newly materialized development capsule exposes the shipped runtime as
   `devcapsule0` and leaves `devcapsule` for the development installation.
3. Use the shipped command deliberately when testing its released behavior.
   Use the development CLI or an explicit built PEX for current work.
4. Do not fall back silently to the shipped CLI when development setup is
   missing.
5. Other projects keep the standard command unless they opt into this
   exception. See `DEVELOPING.md` for checkout overrides and resolution.

### Keep The Development Checkout Launchable

Owner correction, 2026-10-05: be liberal in what we accept and conservative in
what we produce. Compatibility is a contract between contributors with
different launchers. It is not a rule that one frozen release must understand
every shared declaration. This supersedes the narrower 2026-10-04 rule.

1. DevCapsule commands are the only writers of this project's configuration:
   the shared manifest, platform locks, checkout configuration, and generated
   resolutions. Do not edit them with an editor, a script, a TOML library, or
   Git-file restoration. Use the DevCapsule command. Add a supported command
   when the operation is missing. Keep manifest, locks, and resolutions
   consistent through that operation. This rule covers the working project,
   not test fixtures.
2. Before any configuration change, identify the writing executable. Run
   configuration validation with at least `devcapsule0` from the running
   instance. Record its path, `version --json`, the validation command, and
   the result.
3. Check the proposed result before you apply it to the working project. Then
   validate the written result.
4. Also validate against the intended next-launch host executable when it is
   available. The in-capsule check is a minimum. It does not prove which
   executable the host will use.
5. Do not substitute validation with the code under development alone.
6. An inspection command is not automatically a validator. In the current
   runtime, `devcapsule0 project config list` reports recorded launcher
   configuration, and `config resolve` writes a resolution and requires the
   launcher context. Neither is a read-only candidate validation inside the
   capsule.
7. If the required validation or mutation operation is absent, implement it
   through the owning workstream before changing the working configuration.
   Record the gap. Do not bypass it with direct file edits. Do not call an
   inspection a successful check.
8. Self-hosting is a managed exception. DevCapsule may develop inside
   DevCapsule with a newer development executable. Keep the known working
   `devcapsule0` baseline identifiable. Validate the transition with it.
   Record any compatibility gap and the explicit development-build exception.
   Retain an independent host restart and recovery path. A development build
   must not validate away its own bootstrap dependency or replace the user's
   host launcher.
9. For 0.3, [R-CONFIG-001](engineering-docs/requirements/product/r-config-001-conservative-writers-tolerant-readers.md)
   requires mandatory needs to be distinguished from optional enhancements. An
   unavailable optional capability produces a warning and a usable reduced
   local environment. An unmet mandatory need produces an actionable refusal.
   Degradation preserves the shared declaration and the guarantees of
   mandatory capabilities. Conservative writers preserve unrelated choices and
   compatible representations. This applies to adopter repositories that
   receive newer contributions, not only to self-hosting. Until that behavior
   is implemented, keep the current required-only checkout compatible. The
   existing vocabulary guards are an interim regression defense.

### Local Launch Networking

Owner direction, 2026-09-24.

1. Always use host networking for this project's local development and
   release-validation launches, including launches from inside a DevCapsule:
   the RC runner's `--network host`, or
   `devcapsule project run --authorize network host`.
2. This is standing authorization for those launches. Do not ask for it
   repeatedly.
3. Prefer the run-once option over rewriting a checkout's saved configuration.
4. A test that exercises bridge networking, denied host access, or network
   isolation keeps its declared network mode.
5. If host networking cannot be used, record the concrete reason and the
   fallback. Do not substitute bridge networking silently.
6. This is a local operating rule, not a change to product defaults or to
   other projects' permissions.

## GitHub Integration: The CLI When The Human Provides It

Owner direction, 2026-10-21. It replaces the direction of 2026-09-21. It
stands until the GitHub CLI is a DevCapsule component.

1. The human may install GitHub's CLI as the conda environment `gh` under
   `/opt/xtras/miniconda3`. Detect it by the file
   `/opt/xtras/miniconda3/envs/gh/bin/gh`. Do not search the `PATH` for it.
2. Activate it in every shell call that uses it:

   ```text
   source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh
   ```

   Do not edit the shell profile. Do not run `conda init`.
3. Before the first use in a session, check the login:

   ```text
   source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh \
     && gh auth status -h github.com
   ```

   Run the check once per session. If it fails, stop and ask the human to
   run `gh auth login -h github.com`. Do not retry. Do not use another
   credential. Treat a later failure in the session the same way.
4. After the check passes, the agent may create, update and consult pull
   requests and post reviews on this repository with the CLI. Post a review
   as a comment, `gh pr review --comment`. The human merges into `main` and
   into a release branch. Before opening or updating a pull request, run
   the unit session on the branch as it will be pushed, and open or update
   none whose gate is likely to fail. A change to records alone is not an
   exception. Owner direction, 2026-11-06.
5. When the file is absent, the human does GitHub: opening, updating and
   merging pull requests; dispatching workflows; changing repository or
   publication settings. Prepare and validate the change, commit and push
   the branch over SSH, and give the human the compare link:

   ```text
   https://github.com/mycodespace-ai/devcapsule/compare/<base>...<head>?expand=1
   ```

   `<base>` is the branch the pull request targets. `<head>` is the pushed
   branch.
6. In both cases, use ordinary Git over the SSH remote for fetch and branch
   delivery. Do not push to `main` in place of pull request integration.
   After the human reports a merge, re-verify `main` through an SSH fetch.
7. Keep this rule until the owner changes it or the component replaces it.

<a id="review-partners-in-this-checkout"></a>

## Pair Review Loop In This Checkout

Owner direction, 2026-10-22. It applies the Pair Review Loop, topic 9.11
of `WORKFLOW.md`, in this checkout.

1. The engines are the agent command lines on the capsule's `PATH`, signed
   in once by the human: `claude` (Anthropic), `codex` (OpenAI) and
   `antigravity` (Google). Use no API key.
2. Name a pair by its engine and the model that ran, in the brief, the pull
   request bodies and the assessment comments, as *Commit Authorship* names
   it in the trailer.
3. Give the review partner a git worktree under `~/worktrees/<workstream>-review`
   on the review branch, with its own `devcapsule-src/.venv` built as
   *Validation Commands* say, and its scratch at
   `/opt/devcapsule-gate/pytest-<engine>`.
4. Run the review partner detached in that worktree, the brief as its
   prompt, its output in a log under the session scratchpad that ends with
   an exit line, and wait for that line. The recorded forms are:
   - Codex: `codex exec -m <model> -s danger-full-access -c 'projects."<worktree>".trust_level="trusted"' - < <brief>`.
     A round continues the same session with the round brief on standard input:
     `codex exec resume <session-id> -c 'sandbox_mode="danger-full-access"' - < <round brief>`,
     the id read from the `session id:` line of the first log; `resume` takes no `-s`.
   - Claude Code: `claude -p --dangerously-skip-permissions < <brief>`.
   - Antigravity: `antigravity --model <model> --dangerously-skip-permissions -p '<one-line instruction to follow the brief on standard input>' < <brief>`;
     the model flag goes before `-p`, which takes the prompt as its own argument. A round continues the
     same conversation with `-c` before `-p`.
   Owner direction, 2026-10-28: every form adds the engine's streaming
   output, so the log carries one event per step while the partner runs
   and not only its final report: Antigravity `--output-format stream-json`,
   Claude Code `--output-format stream-json --verbose`, Codex `--json`.
   The first loop after this direction proves each form and records it in
   the development document.
   Establish any other form with the human and record it here before use.
5. The review partner uses the GitHub CLI as *GitHub Integration* says; the
   brief repeats the activation line. Label the assessment comment
   `**Accepted at <sha> (<pair>, no round needed).**` or `**Round N (<pair>).**`.
   Merge PRn.1 with `gh pr merge --merge`.
6. Commit each brief and each round brief under the workstream's
   `evidence/` directory beside the slice's records. The session scratchpad
   is not kept.
7. The brief template, the assessment forms, the recipes and the record of
   the loops run are in
   [the development document](engineering-docs/development/review-partner-loop.md).
   Keep it current with every loop.
8. Owner direction, 2026-10-28. When two agents cooperate on a task, the
   one connected to the human pushes progress to where the human reads,
   the chat or the terminal of that session: at least when the partner
   starts, at each commit or gate it makes, and when it ends. The
   partner's own log is evidence, not a report.
9. Owner direction, 2026-11-03. The brief carries the reviewer's duty under
   *Unit Tests*, rule 7, for every loop.

## Commit Authorship

Owner direction, 2026-09-22.

1. A commit made with an agent keeps the human's Git author identity and adds
   a `Co-authored-by` trailer for the contributing agent. Pushing credentials
   and the person who merges a PR do not replace commit authorship.
2. Before committing, check `git var GIT_AUTHOR_IDENT`. Use the human's
   intended name and GitHub-associated email, not an inherited container
   placeholder. Set checkout-specific corrections with
   `git config --local user.name` and `git config --local user.email`.
3. For Codex, the co-author display name is the actual model name followed by
   `Codex`, with this project's attribution address `noreply@openai.com`:

   ```text
   Co-authored-by: GPT-6 Astra Codex <noreply@openai.com>
   ```

   That is an example, not a model pin. Read the active session's model
   identity. Do not infer it from a configured default or a prior session. If
   the model cannot be established, ask the human for the displayed model.
4. Credit only agents that contributed.
5. Separate trailers from the message body with a blank line. Verify the saved
   commit's author and trailers before pushing. Preserve trailers when
   composing a squash commit.
6. This applies to future commits. Do not rewrite merged history to add
   attribution.

## Integration Method

Merge commits, as the definition prescribes since 2026-10-03: one merge per
reviewed deliverable, `main` read by first parent, pushed branches synchronized
by merging `main` in. The hosting platform allows merge commits only. It
deletes the head branch on merge. It refuses force pushes to `main` and
deletion of `main`. The merge commit is the record of the branch: its second
parent is the merged head and its message names the source branch. Delete a
merged branch. Owner setting, 2026-11-04: the merge commit's title is the
pull request's title and its message is the pull request's description, so
the description an agent writes, and the coverage block CI appends to it,
are the merge commit's detail as they stand at merge time.
The earlier ruling that `ws-workflow-improvements/v1` rebases onto `main` is
retired. That branch merges like the others. The engineering source is
[merge strategy and commit identity](engineering-docs/implementation-notes/workflow/2026-08-17-merge-strategy-and-commit-identity.md).

## Workflow Definition Changes

Owner direction, 2026-10-09, after the controlled-language edition merged.

1. Every change to `WORKFLOW.md` or to this file follows the same scheme as
   that edition: one rule per sentence, imperative, at about 80% ASD-STE100,
   placed in the topic the rule belongs to.
2. Put no reason, example, or history in the rule file. Put them in the humane
   companion, `WORKFLOW-humane.md` or `WORKFLOW-LOCAL-humane.md`, in the
   section with the same number or name, as a paragraph that repeats the
   rule, states its intended effect, and gives its motivation.
3. Keep the companion paragraph's dependency on its rule fresh: change the
   rule and its paragraph in the same commit until the web console's view
   registry tracks the dependency and marks the paragraph stale. A rule
   without a companion paragraph, or a paragraph without a rule, is a defect.
   See `WORKFLOW.md` topic 12.12.
4. Add or amend the *Unreleased* entry under `### Changes` in `WORKFLOW.md`
   for every rule that changes meaning. Keep the entry's bold-title form, which
   the brief parses.
5. Keep the frontmatter and the `## Validation Commands` heading as the
   tooling expects them.
6. Regenerate the packaged definition under
   `devcapsule-src/devcapsule/assets/project_workflow/definition/` from the
   root files when a release is cut, or earlier on `workflow-improvements`'
   decision.
7. Use the section map at the end of `WORKFLOW-humane.md` when a record cites
   a section name from before this edition. Do not rewrite old records.

## Exceptions

- **The 0.3.0 release branch synchronizes with `main` during the cycle, on
  the owner's word each time.** Owner direction, 2026-10-22: `main` is
  merged into `release-0.3.0`, at `c779dc2` and again at `e03b060` before
  candidate 2, because nothing was developed on `main` outside the
  candidate process and the workflow rules and records written during the
  cycle must bind the release checkout. The version-bearing files keep the
  release side. Topic 11 of the generic definition forbids synchronizing a
  release ref. Ends with the final tag of 0.3.0.
- **`main` reopens at the cut, not after the final tag.** Owner decision,
  2026-10-18, during the 0.3.0 cycle, after the merge of the release
  branch carried the release version onto `main`: a development version
  orders before the release it names under PEP 440, so `main` on the old
  development version sits behind the release branch for the whole cycle.
  *Version Scheme* rule 4 now reopens `main` with the next development
  version at the cut. Topic 11.2.7 of the generic definition says after the
  final tag; its revision is routed to workflow-improvements. Ends when the
  definition incorporates it.
- **Release-fix propagation uses engineering judgment.** Owner direction,
  2026-09-22. It supersedes the generic release rule's blanket merge-only and
  no-cherry-pick restrictions. `main` stays open to other workstreams. Merge a
  release fix when that produces a correct result on `main` without holding
  unrelated work back. Otherwise cherry-pick it, adapt its reasoning to
  `main`'s implementation, or establish with evidence that `main` does not
  have the bug. A conflict alone does not prove that merging is unsuitable.
  Ancestry alone does not prove that the fix works. Record the main
  disposition and its evidence with the bug. Routine method selection needs no
  new owner approval. The
  [release runbook](engineering-docs/implementation-notes/devcapsule/2026-09-01-release-and-validation-process.md)
  describes the gate's evidence paths. Ends when the generic definition
  incorporates this decision; its revision is routed to
  workflow-improvements.
- **The root `WORKFLOW.md` is the source, not an installed copy.** The
  packaged definition under
  `devcapsule-src/devcapsule/assets/project_workflow/definition/` is derived
  from it and need not be byte-identical. The asset README says which
  differences are justified. Ends if the definition is extracted to its own
  repository.
- **Two adoption exceptions in the registry.** `project-management` started
  one day after the mode was initialized. `maintenance` was created on
  2026-09-18 under the adoption exception the definition provides. Both are
  recorded in root `CURRENT-STATUS.md`. Neither ends.
- **Branch names outside the `ws-` vocabulary.** Open workstreams registered
  before 2026-09-18 keep their old branch names until they rename them. Owner
  direction, 2026-09-22, defers the former pre-candidate deadline through the
  0.2.14 release: publish 0.2.14, then complete the migration before
  substantive work on the next release. RC0 and later 0.2.14 candidates are
  not held for it. Each workstream owns its rename. Ends when the renames are
  complete.
