---
status: confirmed
severity: blocking
target: 0.3.1
owner: maintenance
opened: 2026-11-13
requirements: []
---

# This repository's own project configuration predates 0.3: the committed manifest and lock are not what the release writes

## Symptom and expected behavior

The committed `.devcapsule/devcapsule.toml` is a schema-1 manifest and the
committed `.devcapsule/devcapsule.linux-amd64.lock` was generated from the
resolution matrix `embedded-28`. 0.3.1 ships `embedded-33` and writes
schema-2 manifests. The owner's checkout carries an uncommitted rewrite of
both files, made by a launcher on 2026-11-04, which is itself two matrix
generations behind the release.

Expected: the repository that ships 0.3.1 commits the project
configuration that a 0.3.1 launcher writes for it, a schema-2 manifest and
a lock from the release's matrix, written by a DevCapsule command and
validated as *Keep The Development Checkout Launchable* in
`WORKFLOW-LOCAL.md` requires.

Owner's rating, 2026-11-13: blocking for 0.3.1. A refreshed `.devcapsule`
is committed before the release ships.

## Environment and evidence

Read on 2026-11-13 in the owner's capsule, launcher `v0.3.1-rc2`, on
`ws-maintenance/launch-phases` at `ed232fea`.

| | Committed | Uncommitted in the owner's checkout | 0.3.1 |
|---|---|---|---|
| Manifest schema | 1, `need = [...]` with `python-ide` | 2, `required = [...]`, the IDE recommended | 2 |
| Last written | manifest `3dbe4cb9`, 2026-10-04; lock `dedb485b`, 2026-10-25 | both files, 2026-11-04 00:34 | |
| Matrix | `embedded-28` | `embedded-31` | `embedded-33` |
| Base digest | `8c97d308…` | `d7047ced…` | `d7047ced…`, what `project init` gives today |
| IDE in the lock | PyCharm 2026.2.0.1 | none, the project no longer requires one | |
| Antigravity CLI | 1.4.2 | 1.4.12 | |
| Claude Code | 2.1.302 | 2.1.314 | 2.1.321 |
| Codex | 0.163.0 | 0.166.0 | 0.167.0 |

The uncommitted manifest also drops the top-level `workflow-type` key and
the hand-written comment that explains why `runtime.devcapsule-command`
declares no `runtime-effect`.

Which command wrote the uncommitted files is not recorded. The lock's base
table carries the build name `v0.3.0-local-linux-x86_64`.

Consequences seen while the files differed:

- Three tests that read these files failed in the owner's checkout and
  passed on the hosted runner, which sees the commit. They are deleted in
  pull request #29; `tests/unit/devcapsule/configuration/test_capability_commands.py`
  reads a frozen copy of the committed pair instead,
  `tests/resources/compat/repository-2026-10-25/`.
- `tests/test_base_contract.py` still reads `.devcapsule/`. It passes with
  the uncommitted files and with the committed ones.

## Fix notes

- Only a DevCapsule command writes these files, and inside a capsule a
  command that changes the capsule's own project is refused: the refresh
  runs on the host, with the launcher that is to be the release's.
  `project init --regenerate` rewrites the lock from the embedded matrix
  and migrates a schema-1 manifest to schema 2, keeping its leading
  comments; see `docs/reference/cli.md`.
- Record the writing executable, its `version --json`, the validation
  command and its result, as the local rule asks. Validate with
  `config check` before and after.
- The uncommitted files of 2026-11-04 are not the fix: they are from
  `embedded-31`. Regenerate; do not commit them as they are.
- A schema-2 manifest cannot be read by launchers older than 0.3.0. The
  owner ruled on 2026-11-12 that compatibility with 0.2.14, 0.2.15 and
  earlier may be dropped.
- Decide whether the IDE stays a recommendation, as the uncommitted
  manifest has it, or is required again; and whether the comment on
  `runtime.devcapsule-command` is kept.
- After the refresh, check `tests/test_base_contract.py` on the new files.
  The frozen copy under `tests/resources/compat/` is not regenerated.

## Progress, 2026-11-13: the refresh checked on a copy; the write waits for the host

The owner asked for `.devcapsule` to be committed. The files in the
checkout were still the pair of 2026-11-04, so nothing is committed yet:
the first fix note stands.

The proposed result, checked before it is applied, as the local rule asks.
Executable: `/usr/local/bin/devcapsule0`, SHA-256 `2c3ace0f…`,
`version --json` gives `0.3.1rc2`, `v0.3.1-rc2`, source revision
`be0140ca`. Its matrix is `embedded-33`, the one `release-0.3.1` carries at
`82b9c07e`; `resolution_matrix.py` is unchanged since the candidate.

- On a copy of the checkout's uncommitted pair, in a scratch directory with
  a home of its own, `project init --regenerate` exits 0. The manifest
  comes out byte for byte as it went in. The lock changes in three places:
  the matrix, `embedded-31` to `embedded-33`; Claude Code, 2.1.314 to
  2.1.321; Codex, 0.166.0 to 0.167.0. The base and the Antigravity CLI stay.
- `project config check` on the regenerated copy: "Configuration contract
  valid", exit 3 for the decisions an empty home has not taken.
- On a copy of the committed pair the same command stops, exit 2, and asks
  for the base and the two download authorizations: that manifest requires
  an IDE. This path was not followed further.
- `devcapsule0 project config check` on the checkout as it is: "Configuration
  contract valid", exit 0; host decisions cannot be assessed inside the
  capsule.

The write itself is refused inside the capsule, as designed:

    devcapsule: This command needs launcher-owned configuration or state.
    Inside this capsule that configuration is read-only. Run outside the
    capsule: devcapsule project --path
    /home/costin/work.provisional/costin3/myProjects/devcapsule init --regenerate

The regenerated copy was not copied over the checkout's files: only a
DevCapsule command writes them. Next: that command on the host with the
candidate's launcher, `config check` there, then the commit of the two
files. The manifest that results keeps the IDE as a recommendation and is
without the comment on `runtime.devcapsule-command`, unless the owner
decides otherwise first.

## Verification target and close criteria

1. The committed manifest is schema 2 and the committed lock names the
   matrix of the release candidate that carries it.
2. `config check` with that candidate's launcher passes on a clean
   checkout of the release branch, and the record of the refresh names the
   executable and the command.
3. A launch of this repository's capsule from that clean checkout starts.
4. `nox -s tests` passes on the commit, on the hosted runner and inside the
   capsule.

Reopen if a later candidate's matrix moves and the committed lock is left
behind before the final tag.
