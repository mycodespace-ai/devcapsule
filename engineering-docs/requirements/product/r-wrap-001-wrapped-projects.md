---
id: R-WRAP-001
title: Wrapped Projects
type: requirement
kind: concrete-requirement
status: accepted
priority: wanted
source_of_truth: repo
verification: [tests, manual]
external_refs: []
---

# R-WRAP-001: Wrapped Projects

## Statement

Owner direction, 2026-11-02, from the wrapped-projects work order. A
developer can work in a capsule on a repository that is not theirs and
carries no DevCapsule configuration, without imposing anything on it: the
configuration lives in a small wrapper repository of their own, and the
foreign repository is a Git submodule of it.

### The wrapper is an ordinary project

There is no new project kind. The wrapper's manifest is a schema-2 manifest
that additionally names its wrapped sources under `[sources."<path>"]`
(R-CONFIG-001). Every command that works on a project works on a wrapper.

### One command wraps a repository

`devcapsule project wrap URL` adds the repository as a submodule with its Git
directory embedded in the tree the capsule mounts, reads what the source
needs, initializes or extends the manifest and lock, declares the source, and
writes the wrapper's `AGENTS.md` and `README.md` from the manifest. The
developer writes no TOML. The command is repeatable for several repositories
and finishes what an interrupted run left.

### The foreign tree stays clean

Nothing is written inside a wrapped source: no DevCapsule files, no IDE
files, no toolchain selection files. The guidance names the toolchain to
select; the capsule selects it. The intent recorded for each source, learning
from the upstream or changing a fork, governs where changes and pull requests
go; the upstream is never written to unless its maintainers ask.

### The toolchain reaches the build

A wrapped source names the Java line it builds with. The capsule's base
carries the lines the catalog lists; the selection reaches the agent through
the wrapper's guidance first and the capsule's session environment second.

## Verification

Unit tests over the declaration, the detection rules and the wrap operation
with local repositories; the acceptance evidence of the work order on the
showcase, an FRC learning wrapper around Mechanical-Advantage's public robot
code, inside a capsule whose base carries Java 17.
