---
status: fixing
severity: blocking
target: 0.3.1
owner: maintenance
opened: 2026-11-08
requirements: [R-CONSOLE-001]
---

# Web console changes in `v0.3.1-rc1` do not reach capsules: the PEX omits the console package and the self-hosting override shadows it

## Symptom and expected behavior

In a capsule launched by `v0.3.1-rc1` (`accdec5b`), the web console's new Files
page routes return `404 Not Found`:

- `GET /files` returns `404` (`{"detail":"Not Found"}`).
- `GET /filetree` returns `404` (`{"detail":"Not Found"}`).
- `GET /api/project/tree` returns `404` (`{"detail":"Not Found"}`).

Expected: every capsule launched by `v0.3.1-rc1` on a recipe-11 base serves the
Files page merged in PR #12 (`ec8af13a`), for adopter projects and for
self-hosting checkouts alike.

## Environment and reproduction

Reproduced on 2026-11-08 inside `pycharm-isolated-costin-1794143516` launched
by `v0.3.1-rc1` (`build_mnemonic: v0.3.1-rc1`, SHA-256 `711d239c…`, source
revision `accdec5bb36626875b0564afbcbf20f67f9d961b`) on Ubuntu 24.04 recipe-11:

1. Launch a project capsule with the `v0.3.1-rc1` executable on any pinned
   recipe-11 base (`linux-amd64` `sha256:d7047ced…`, `linux-arm64`
   `sha256:7d322680…`, or a local pre-PR-#12 recipe-11 base).
2. Authenticate with the run's console token on `GET /` (`200 OK`).
3. Request `/files`, `/filetree`, or `/api/project/tree`. Each returns `404`.

## Evidence

- `scripts/build-pex.sh` packages `devcapsule-src/devcapsule` into
  `devcapsule.pex`. It does not package `devcapsule-webconsole/`.
- `devcapsule/materialization.py` installs `/opt/devcapsule/bin/devcapsule.pex`
  into the materialized image (`D-0009`). It does not install
  `devcapsule_webconsole`.
- `devcapsule/container_runtime/console.py` runs
  `/opt/devcapsule-webconsole/venv/bin/python -m devcapsule_webconsole`. For
  every adopter project (`console.source_path == ""`), Python imports the
  package baked into the base image at base-build time.
- `v0.3.1-rc1` keeps the pre-PR-#12 base pins in `resolution_matrix.py`:
  `linux-amd64` `sha256:d7047ced…` (built `2026-10-31`) and `linux-arm64`
  `sha256:7d322680…` (built `2026-11-04` at `b3f10b7d`). Neither base contains
  PR #12 (`ec8af13a`, merged `2026-11-08`).
- In this capsule's base (`sha256:da255c81…`),
  `/opt/devcapsule-webconsole/venv/lib/python3.12/site-packages/devcapsule_webconsole/static/`
  has `mtime` `2026-10-19` and lacks `files.html`.
- In addition, `console_development_source()` in
  `devcapsule/launch/pycharm/_launcher.py` sets
  `PYTHONPATH={project_mount}/devcapsule-webconsole` whenever the mounted
  project contains `devcapsule-webconsole/devcapsule_webconsole/__init__.py`.
  In this capsule (`PID 35`), the checkout sat on `ws-maintenance/e2e_videos-2`
  (`2026-10-22`), so the older branch shadowed the console. Conversely, on a
  `release-0.3.1` checkout, that same override masks the missing base/launcher
  delivery.

## Cause and hypothesis

Two architectural couplings caused the defect (no remaining diagnostic
uncertainty):

1. **Base-only console code delivery.** Unlike the runtime CLI (`D-0009`),
   `devcapsule_webconsole`'s pure-Python and static files are installed only
   during `images build --type base`, alongside the compiled third-party venv
   (`fastapi`, `uvicorn`, `pydantic`, `psutil`). Any change to
   `devcapsule-webconsole/` requires rebuilding, pushing, and repinning both
   `linux-amd64` and `linux-arm64` base images before tagging a candidate, or
   else the candidate ships without the console change.
2. **Unconditional self-hosting `PYTHONPATH` override.**
   `console_development_source()` overrides a built PEX's console whenever the
   mounted project is a DevCapsule checkout. That breaks candidate testing on
   older branches and hides missing candidate delivery on newer branches.

## Verification target and close criteria

Owner `maintenance` works on the fix on `ws-maintenance/webconsole-delivery`
for `0.3.1` (candidate 2).

Close when:

1. The owner selects the delivery mechanism (launcher-delivered console package
   on the base's `/opt/devcapsule-webconsole/venv` vs rebuilt and repinned
   bases with a gate check) and the self-hosting override rule.
2. Unit and integration tests verify that a built `devcapsule.pex` delivers the
   current `devcapsule_webconsole` (including `/files`, `/filetree`, and
   `/api/project/tree`) without relying on a DevCapsule checkout mount.
3. A fresh non-DevCapsule project launched by the downloaded `v0.3.1-rc2`
   executable on the pinned recipe-11 base serves `200 OK` on `/files` and
   `/api/project/tree`, and redirects `/filetree` to `/files`.

Reopen if a change under `devcapsule-webconsole/` merges and a built PEX on the
pinned base fails to serve it.
