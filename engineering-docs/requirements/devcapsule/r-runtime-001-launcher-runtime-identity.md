---
id: R-RUNTIME-001
title: Identical Launcher And Container Runtime By Default
type: requirement
kind: concrete-requirement
status: accepted
priority: wanted
source_of_truth: repo
verification:
  - tests
  - e2e
external_refs: []
---

# R-RUNTIME-001: Identical Launcher And Container Runtime By Default

## Statement

Unless the user explicitly chooses otherwise, the DevCapsule CLI must use
the corresponding base selected by project/platform resolution and install
its own executable into the materialized environment. The launcher outside
Docker and runtime support inside Docker must be byte-identical.

A launcher change must not reuse a cached environment carrying a different
runtime executable. Selecting a different base alone does not imply selecting
a different runtime. The base and CLI need not have matching release numbers.

Explicit user overrides are permitted. This requirement does not prescribe a
new command spelling or make such an override implicit.

## Rationale

The owner adopted this default in
[D-0009](../../decisions/product/d-0009-launcher-delivers-identical-runtime.md)
after the successful v0.2.11 implementation. It removes the base/CLI content
dependency cycle and keeps runtime-plan production and execution in one build.

## Implementation And Limits

- `devcapsule/runtime_artifact.py` selects the invoking packaged executable.
- `devcapsule/materialization.py` installs it at
  `/opt/devcapsule/bin/devcapsule.pex` and incorporates its SHA-256 in the
  formation descriptor. The shared base is not modified in place.
- The delivered executable is reachable through `/usr/local/bin/devcapsule`.
  An ordinary configuration value with runtime effect `devcapsule.command-name`
  can select `devcapsule0` instead for development checkouts. This changes the
  public name only; internal absolute-path execution and byte identity remain.
  The command selection participates in formation identity. An old cached
  image without the public command contract cannot satisfy the repaired plan.
- Source-form launchers can explicitly select a built PEX using
  `DEVCAPSULE_RUNTIME_PEX`; running that PEX directly gives the ordinary
  identical-executable path. Source Python files are not themselves a PEX.
- A packaged launcher that runs on the capsule platform takes precedence
  over `DEVCAPSULE_RUNTIME_PEX`. That variable is otherwise a source-development
  selection, not a general packaged-launcher runtime override.
- Since the `linux-arm64` workstream (2026-11-04, unreleased): a packaged
  launcher that cannot run inside the capsule, a macOS executable launching
  Linux capsules, delivers the runtime `DEVCAPSULE_RUNTIME_PEX` names instead,
  and stops with that remedy when it is unset. The variable may name a
  directory holding one runtime per capsule platform as
  `devcapsule-<platform>`; the lock's platform selects. This is the explicit
  user choice D-0009 admits, not a new default: the outside and inside bytes
  differ, so the delivered runtime must be the launcher's build, the same
  version, and the same source revision wherever both record one. A local
  build without a recorded revision can be matched by version only. A
  release shipping macOS launchers would reopen D-0009, whose *Reopen If*
  names this case.

## Verification

Existing coverage for the default, delivered with v0.2.11:

- `tests/test_runtime_artifact.py` checks executable selection, explicit
  source-runtime selection, and formation identity changing with runtime bytes.
- `tests/e2e/test_component_cache.py` checks the installed executable's SHA-256,
  image label, runtime invocation, and inside/outside version metadata for both
  fixture surface families.

The 0.2.14 runtime-command repair extends those Docker checks to execute the
public command by name as a non-root user and bootstrap workflow files. Both
PyCharm/VSCodium formations and normal/development command names are covered;
configuration and cache-identity tests cover recommendation/override semantics.
These fixture-image checks do not stand in for actual IDE-terminal acceptance.

Future changes must preserve these properties. Any additional override
interface needs its own explicit-selection and default-regression coverage;
this record does not claim that interface has been validated.

The macOS delivery path is covered by `tests/test_runtime_artifact.py`: the
named runtime and the directory form, refusal of a foreign or missing runtime,
of a plain PEX on a non-Linux host, and of a runtime from another build. The
IDE smoke compares the capsule's runtime digest with the runtime the workspace's
lock selects. Neither is a release validation of macOS launchers.
