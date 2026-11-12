---
status: confirmed
severity: minor
target: none
owner: maintenance
opened: 2026-10-30
requirements: [R-COMPAT-001, R-CONFIG-001]
---

# `project config show --help` advertises JSON schema 1 while emitting schema 2, and retired `project config default|trust` spellings print no replacement hint

## Symptom

Found by the review partner of PR #319 (`Codex / gpt-6-astra`, PR #320) on
2026-10-30 while verifying Batch 1 of the `0.3.0` user-documentation CLI
alignment against `release-0.3.0` (`9eb500da`):

1. **`project config show --help` schema mismatch:** Running
   `devcapsule project config show --help` prints:
   `--json  Emit stable machine-readable JSON instead of text: schema-version 1, the contract the capsule web console reads.`
   Running `devcapsule project config show --json` on a host checkout (or in a
   capsule with a captured listing) emits `"schema-version": 2`. Only legacy
   in-capsule fallbacks without a captured listing emit schema `1`.
2. **Missing replacement hint on moved `home` commands:** Other retired
   `project config` spellings (`config list`, `config resolve`, `config need`,
   `config agent add`, `config tool omit`) exit with status `2` and print a
   one-line replacement command. Running `devcapsule project config default
   memory 4g` or `devcapsule project config trust accept vscode` exits with
   status `2` and an `argparse` invalid-choice message without naming
   `devcapsule home default` or `devcapsule home trust`.

## Cause, as far as read

1. `ConfigShowCommand` (`devcapsule-src/devcapsule/commands/project.py`) shares
   `STABLE_JSON_HELP` (`devcapsule-src/devcapsule/commands/framework.py:53`),
   whose string hardcodes `schema-version 1`, whereas
   `devcapsule-src/devcapsule/configuration/listing.py:60` sets
   `"schema-version": 2`.
2. `ConfigGroup` (`devcapsule-src/devcapsule/commands/project.py:1833`) has no
   retired stub for `default`, and `ConfigTrustGroup`
   (`devcapsule-src/devcapsule/commands/project.py:1355`) registers only `list`
   without retired stubs for `accept` or `withdraw` pointing to `devcapsule home
   trust`.

## User-Documentation Handling in `0.3.0`

Per the work-order rule against documenting broken CLI behavior as intended,
`docs/reference/cli.md` and `docs/updates/component-upgrades.md` (updated in PR
#319 / #320) accurately state both the schema-2 `config show --json` output and
that `project config default` and mutating `project config trust` are absent in
favor of `devcapsule home default` and `devcapsule home trust`.
