# CLI syntax implementation

Work order: [CLI syntax and discovery](../../work-orders/2026-11-17-cli-syntax-and-discovery.md).
Baseline: `010813be`, `ws-maintenance/cli-syntax`. Implementation started 2026-11-17.

## Scope and sequence

1. RC4: side-effect-free PyCharm dependency-check help, complete versioned recording
   kit installation, remove the presentations command group with its replacement
   instance link adapter, and update affected callers and instructions.
2. After 0.3.1: the remaining public tree, project/global selectors, detailed
   reports, recursive advanced help, removal of unused PyCharm code, and consumer
   migration. Synchronize this slice with main. Do not select a release number.

Each slice gets its own implementation PR and Pair Review; only the owner merges
into the release or main. No release tagging or container launch is implied.

The initial help/kit slice is delivered in [PR52](https://github.com/mycodespace-ai/devcapsule/pull/52).
Antigravity `gemini-4-hydrogen` reviewed it in PR53; accepted after one correction
round at `d0f2e8bb`, merged into the implementation branch at `ec38720d`.
The review added staged installation with real partial-write cleanup coverage
and blank-version validation. It preserved existing symlink behavior.
Presentation-command removal and instruction migration still await the link choice.

## Production boundary

The preliminary help/installation edits are confined to
`commands/_pycharm.py`, `commands/project.py`, `presentation_authoring.py`, and
`workflow_bootstrap.py`. The last two implement the explicitly granted full-kit
installation change. The kit takes explicit resource bytes and version provenance;
existing skill directories and symlinked locations remain untouched.

Remaining planned adapter files: `cli.py`, `commands/framework.py`,
`commands/project.py`, `commands/home.py`, `commands/bootstrap.py`,
`commands/workflow.py`, `commands/presentations.py`, `commands/pycharm.py`,
`commands/_pycharm.py`, `commands/_versions.py`, a new `commands/instance.py`,
and `devcapsule-webconsole/devcapsule_webconsole/cli.py`. New helper modules,
if needed, stay under `commands/` and only parse, dispatch, compose reports, or
format existing console routes. Document any extension before editing it.

Recording instructions under `presentation_tools/` change with their installed
resource use. Other production files may receive mechanical command-string
updates only; enumerate them with the caller inventory before that migration.
Reachability evidence must name any legacy PyCharm module proposed for deletion.
No domain behavior, report schema, console route, configuration layout, defaults,
consent or access rule changes are authorized.

## Decisions pending

The owner has been asked through the capsule decision page and chat:
root-only `--project` placement; retention of existing global/instance verbs;
and automatic viewer choice for file paths versus Files-only path links.
These are the work order's explicit stopping points. No answer is presumed.
Plain configuration JSON remains unchanged; the proposed detailed envelope is
`configuration` plus `information`, each holding its existing report document.

## Command inventory

The current source exposes 116 tree entries, including hidden retired diagnoses.
The work order's previous run reported 102 help invocations but did not retain
that list in its review record. This inventory includes every current entry;
forwarded decision/runtime commands and live callers need a separate inventory.
Removed names have no compatibility aliases. Rows marked pending are proposals.

| Existing path | Destination | Disposition |
|---|---|---|
| `bootstrap` | `workflow bootstrap` | move |
| `bootstrap project` | `workflow bootstrap` | move |
| `github-ssh` | `github-ssh` | retain hidden |
| `home` | `config -g` | move; verb choice pending |
| `home show` | `config -g show` | move; verb choice pending |
| `home trust` | `config -g trust` | move; verb choice pending |
| `home trust list` | `config -g trust list` | move; verb choice pending |
| `home trust accept` | `config -g trust accept` | move; verb choice pending |
| `home trust withdraw` | `config -g trust withdraw` | move; verb choice pending |
| `home default` | `config -g default` | move; verb choice pending |
| `host-open` | `host-open` | retain hidden |
| `images` | `images` | retain |
| `images list` | `images list` | retain |
| `images build` | `images build` | retain |
| `presentations` | `installed recording kit` | remove command |
| `presentations guide` | `installed recording kit` | remove command |
| `presentations export` | `installed recording kit` | remove command |
| `presentations install-skill` | `installed recording kit` | remove command |
| `presentations hand-off` | `instance --get-link PATH-OR-URL` | move; route choice pending |
| `project` | `top-level command tree` | remove group |
| `project info` | `config show --detailed` | compose existing reports |
| `project diagnose` | `diagnose` | move |
| `project list` | `list` | move |
| `project init` | `init` | move |
| `project wrap` | `init --wrap URL` | move |
| `project checkout` | `instance` | move; verb choice pending |
| `project checkout register` | `config --register NAME` | move |
| `project checkout notifications` | `instance notifications` | move; verb choice pending |
| `project checkout notifications list` | `instance notifications list` | move; verb choice pending |
| `project checkout notifications post` | `instance notifications post` | move; verb choice pending |
| `project checkout notifications read` | `instance notifications read` | move; verb choice pending |
| `project checkout notifications dismiss` | `instance notifications dismiss` | move; verb choice pending |
| `project checkout decisions` | `instance decisions` | move; verb choice pending |
| `project config` | `config` | move |
| `project config show` | `config show` | move |
| `project config list` | `config list` | move; currently hidden, check alias/retirement before retaining |
| `project config check` | `config check` | move |
| `project config ide` | `config ide` | move |
| `project config add` | `config add` | move |
| `project config omit` | `config omit` | move |
| `project config restore` | `config restore` | move |
| `project config use` | `config use` | move |
| `project config agent` | `config agent` | move; currently hidden, check alias/retirement before retaining |
| `project config agent add` | `config agent add` | move; currently hidden, check alias/retirement before retaining |
| `project config agent remove` | `config agent remove` | move; currently hidden, check alias/retirement before retaining |
| `project config tool` | `config tool` | move; currently hidden, check alias/retirement before retaining |
| `project config tool omit` | `config tool omit` | move; currently hidden, check alias/retirement before retaining |
| `project config tool restore` | `config tool restore` | move; currently hidden, check alias/retirement before retaining |
| `project config set` | `config set` | move |
| `project config authorize` | `config authorize` | move |
| `project config deny` | `config deny` | move |
| `project config forget` | `config forget` | move |
| `project config bind` | `config bind` | move |
| `project config unbind` | `config unbind` | move |
| `project config trust` | `config trust` | move |
| `project config trust list` | `config trust list` | move |
| `project config console` | `config console` | move |
| `project config console list` | `config console list` | move |
| `project config console apply` | `config console apply` | move |
| `project config console discard` | `config console discard` | move |
| `project config env` | `config env` | move |
| `project config env set` | `config env set` | move |
| `project config env unset` | `config env unset` | move |
| `project config env list` | `config env list` | move |
| `project config docker-args` | `config docker-args` | move |
| `project config docker-args set` | `config docker-args set` | move |
| `project config docker-args list` | `config docker-args list` | move |
| `project config docker-args clear` | `config docker-args clear` | move |
| `project config approve` | `config approve` | move |
| `project config resolve` | `config resolve` | move; currently hidden, check alias/retirement before retaining |
| `project config require` | `config require` | move |
| `project config offer` | `config offer` | move |
| `project config drop` | `config drop` | move |
| `project config recommend` | `config recommend` | move |
| `project config capabilities` | `config capabilities` | move; currently hidden, check alias/retirement before retaining |
| `project config need` | `config need` | move; currently hidden, check alias/retirement before retaining |
| `project config unset` | `config unset` | move; currently hidden, check alias/retirement before retaining |
| `project config set-env` | `config set-env` | move; currently hidden, check alias/retirement before retaining |
| `project config unset-env` | `config unset-env` | move; currently hidden, check alias/retirement before retaining |
| `project config list-env` | `config list-env` | move; currently hidden, check alias/retirement before retaining |
| `project config set-extra-docker-args` | `config set-extra-docker-args` | move; currently hidden, check alias/retirement before retaining |
| `project config list-extra-docker-args` | `config list-extra-docker-args` | move; currently hidden, check alias/retirement before retaining |
| `project config remove-extra-docker-args` | `config remove-extra-docker-args` | move; currently hidden, check alias/retirement before retaining |
| `project versions` | `config software` | move; operations in advanced help |
| `project versions show` | `config software show` | move; operations in advanced help |
| `project versions check` | `config software check` | move; operations in advanced help |
| `project versions preview` | `config software preview` | move; operations in advanced help |
| `project versions select` | `config software select` | move; operations in advanced help |
| `project versions history` | `config software history` | move; operations in advanced help |
| `project versions rollback` | `config software rollback` | move; operations in advanced help |
| `project versions follow-project` | `config software follow-project` | move; operations in advanced help |
| `project versions propose` | `config software propose` | move; operations in advanced help |
| `project versions dismiss` | `config software dismiss` | move; operations in advanced help |
| `project versions defer` | `config software defer` | move; operations in advanced help |
| `project state` | `config --set-state SLOT DIR` | remove group |
| `project state adopt` | `config --set-state SLOT DIR` | move |
| `project recursive-e2e` | `recursive-e2e` | move |
| `project recursive-e2e preflight` | `recursive-e2e preflight` | move |
| `project recursive-e2e run` | `recursive-e2e run` | move |
| `project recursive-e2e launch-successor` | `recursive-e2e launch-successor` | move |
| `project recursive-e2e inspect-successor` | `recursive-e2e inspect-successor` | move |
| `project run` | `run` | move |
| `pycharm` | `—` | remove; delete only implementation without remaining callers |
| `pycharm build` | `—` | remove; delete only implementation without remaining callers |
| `pycharm check-runtime` | `—` | remove; delete only implementation without remaining callers |
| `runtime` | `runtime` | retain (advanced) |
| `version` | `version` | retain |
| `workflow` | `workflow` | retain |
| `workflow mail` | `workflow mail` | retain |
| `workflow mail send` | `workflow mail send` | retain |
| `workflow mail check` | `workflow mail check` | retain |
| `workflow mail take` | `workflow mail take` | retain |
| `workflow publish` | `workflow publish` | retain |
| `workflow status` | `workflow status` | retain |
| `workflow claim` | `workflow claim` | retain |
| `workflow brief` | `workflow brief` | retain |

## Preliminary validation and resumption

29 focused unit tests and 3 subprocess integration tests pass. The full gate
passed version/syntax/types/conventions and stopped with 3374 unit passes and
3 environment-dependent legacy failures (two gid-0 recursive fixtures and the
unmountable-staging fixture run under mount-backed home scratch). Docs contract:
249 pages passed. No PEX acceptance or reviewer acceptance is claimed.

The installed kit now has all helpers and version provenance. Instructions still
use the existing commands until the removal/link slice can be completed; that
migration is not finished. Pending owner answers remain in capsule state.
Claude Fable 5.2 responds normally; the prescribed bypass flag refuses root.
The requested exception is a read-only reviewer, with fixes applied by the
implementor and sent back for re-review. No exception has been presumed.

## Review partner change

The owner selected Antigravity `gemini-4-hydrogen` in place of Claude. Its
prescribed launch succeeds and reports that exact model. The Claude launch
exception question is superseded. Run Pair Review on the independent initial
help/kit slice while the three syntax choices await the owner. This first PR
targets `release-0.3.1`; it does not declare the full RC4 cleanup complete.
