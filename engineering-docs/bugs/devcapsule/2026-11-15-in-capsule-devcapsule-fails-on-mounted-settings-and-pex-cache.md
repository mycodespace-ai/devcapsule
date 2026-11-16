---
status: closed
severity: blocking
target: 0.3.1
owner: maintenance
opened: 2026-11-15
closed: 2026-11-15
requirements: [R-CONFIG-001]
---

# Inside a capsule on another machine, `devcapsule` warns on `/home/devcapsule/.cache/pex` and aborts with `Permission denied` reading `/etc/devcapsule/home/settings.toml`

Filed at owner direction on 2026-11-15 as `blocking` for `0.3.1` (owner
asked for a critical bug; `blocking` is the highest controlled severity).

## Symptom and expected behavior

Running `devcapsule project run` inside a DevCapsule container on another
machine on the `release-0.3.1` checkout (built/shipped with `0.3.1rc2`, PEX
hash `1d29272670cc14c12d13dc7ca49a8a6e984928ee`) fails before command
dispatch with:

```text
/tmp/devcapsule-pex-root/unzipped_pexes/3/1d29272670cc14c12d13dc7ca49a8a6e984928ee/.bootstrap/pex/pex_root.py:51: PEXWarning: PEX_ROOT is configured as /home/devcapsule/.cache/pex but that path is un-writeable,
falling back to a temporary PEX_ROOT of /tmp/pex-root.fer2osf_.readonly-fallback which will hurt performance.
 pex_warnings.warn(
/tmp/devcapsule-pex-root/unzipped_pexes/3/1d29272670cc14c12d13dc7ca49a8a6e984928ee/.bootstrap/pex/pex_root.py:51: PEXWarning: PEX_ROOT is configured as /home/devcapsule/.cache/pex but that path is un-writeable,
falling back to a temporary PEX_ROOT of /tmp/pex-root.itnvs2aq.readonly-fallback which will hurt performance.
 pex_warnings.warn(
devcapsule: Cannot read /etc/devcapsule/home/settings.toml: [Errno 13] Permission denied: '/etc/devcapsule/home/settings.toml'
```

Expected:

- The `devcapsule` scie/PEX executable inside a capsule uses its configured
  runtime root (`/tmp/devcapsule-pex-root`) or a writable cache without
  emitting `PEXWarning` and falling back to ephemeral `/tmp/pex-root.*`
  directories on every invocation.
- Inside a capsule, the container user can read the launcher-mounted
  `/etc/devcapsule/home/settings.toml` (when mounted for that user's capsule),
  or `devcapsule` surfaces a clear diagnostic / degrades safely rather than
  aborting every `devcapsule` subcommand at startup in `cli._dispatch`
  (including commands that do not need mounted launcher settings, or commands
  about to be refused by `CapsuleAccess`).

## Environment and evidence

Reported by the owner on 2026-11-15 on another machine running from the
`release-0.3.1` checkout (`9cb20ed9`), in another project.

`docker info` on the affected host confirms **rootless Docker**:

- `Operating System`: `Ubuntu 24.04.5 LTS` (`x86_64`, Kernel `7.0.0-43-generic`)
- `Server Version`: `29.9.3` (`Docker Root Dir: /opt/docker/data`, `Context: default`)
- `Security Options`: `seccomp` (`Profile: builtin`), `rootless`, `cgroupns`
- `CDI spec directories`: includes `/home/costin/.config/cdi` and `/run/user/1000/cdi` (host user UID `1000`)

Code and local verification on `release-0.3.1` (`9cb20ed9`, inside this
capsule where `/opt/devcapsule/bin/devcapsule.pex` is `0.3.1rc2` with the same
PEX hash `1d29272670cc14c12d13dc7ca49a8a6e984928ee`):

1. **Unconditional `load_settings()` at CLI startup (`devcapsule-src/devcapsule/cli.py:65-66`):**
   - `_dispatch` calls `load_settings()` before resolving the command or
     evaluating `CapsuleAccess`.
   - When inside a capsule (`/etc/devcapsule/launch-context.json` exists),
     `DEVCAPSULE_CONFIG_HOME` is unset or empty, and
     `$XDG_CONFIG_HOME/devcapsule/settings.toml` does not exist,
     `settings_source()` (`devcapsule-src/devcapsule/configuration/storage.py:97-111`)
     calls `mounted_settings_path()`
     (`devcapsule-src/devcapsule/runtime_configuration.py:250-260`), which
     returns `/etc/devcapsule/home/settings.toml`.
   - `build_docker_args()` (`devcapsule-src/devcapsule/launch/pycharm/_launcher.py:1454-1459`)
     bind-mounts the host launcher's `settings.toml` read-only at
     `/etc/devcapsule/home/settings.toml`. On the host, `write_settings()`
     (`storage.py:197`) creates `settings.toml` via `atomic_write(..., mode=0o600)`.
   - Because `/etc/devcapsule/home` is `0755`, `mounted.exists()` (`stat()`)
     succeeds even when the caller lacks read access; `load_toml()`
     (`storage.py:60-66`) then raises `ProjectConfigurationError` wrapping
     `[Errno 13] Permission denied`, exiting `2` before any command runs.

2. **PEX ignores `--runtime-pex-root` after scie boot (`devcapsule-src/scripts/build-pex.sh:114, 312`):**
   - `build-pex.sh` builds the scie with `--runtime-pex-root /tmp/devcapsule-pex-root`,
     which appears in `PEX-INFO` (`"pex_root": "/tmp/devcapsule-pex-root"`).
   - `SCIE=inspect /opt/devcapsule/bin/devcapsule.pex` shows the `configure`
     binding unpacks to `/tmp/devcapsule-pex-root/unzipped_pexes/3/1d29272670cc14c12d13dc7ca49a8a6e984928ee`,
     then `boot.commands[""]` executes Python on that unzipped PEX without
     setting `PEX_ROOT` in `env`.
   - Inside Python, `Variables.PEX_ROOT` defaults to `$XDG_CACHE_HOME/pex`,
     which inside a capsule is `/home/devcapsule/.cache/pex` (from
     `XDG_CACHE_HOME=/home/devcapsule/.cache` in `_launcher.py:1351` and
     `container_runtime/filesystem.py:29`).
   - Verified locally: running `HOME=/nonexistent XDG_CACHE_HOME=/nonexistent/.cache /opt/devcapsule/bin/devcapsule.pex --help`
     reproduces the exact `PEXWarning` (`PEX_ROOT is configured as .../pex but that path is un-writeable, falling back to a temporary PEX_ROOT of /tmp/pex-root....readonly-fallback`).
   - Verified locally: running with `PEX_ROOT=/tmp/devcapsule-pex-root` and
     `DEVCAPSULE_CONFIG_HOME=/tmp/test-dc-home-check` suppresses the warning
     and bypasses `/etc/devcapsule/home/settings.toml`.

## Cause and remaining uncertainty

`docker info` confirms the affected host runs **rootless Docker** (`Security Options: rootless`) for host user UID `1000`:

1. Under rootless Docker, host UID `1000` (owner of `~/.config/devcapsule/settings.toml`
   with mode `0600`, persistent `/home/devcapsule`, `/home/devcapsule/.cache`,
   and the project checkout) is mapped to **container UID `0` (`root`)**.
2. `append_docker_mode_args()` (`_launcher.py:1596, 1633`) unconditionally passes
   `--user {host_user.uid}:{host_user.gid}` (`1000:1000`) to `docker run`
   (in `none` and `host` docker modes). Inside a rootless container, container
   UID `1000` maps to a subordinate host UID, **not** host UID `1000`.
3. Consequently, bind-mounted host files owned by host UID `1000` appear inside
   the container as owned by `0:0` (`root:root`). The container process running
   as container UID `1000` cannot read `0600` `/etc/devcapsule/home/settings.toml`
   (`[Errno 13] Permission denied`) and cannot write `/home/devcapsule/.cache/pex`
   (triggering the `PEXWarning` fallback to `/tmp/pex-root.*.readonly-fallback`).
   By the same mechanism, host-owned bind mounts (`/home/devcapsule`, project
   checkout) are owned by container `0:0` rather than the container user.

**Remaining uncertainty:** It is not yet observed which Docker mode (`none`,
`host`, or `dind`) the outer capsule used on that host, or why `pex_root.py:51`
emitted the `PEXWarning` twice with two different fallback directories
(`fer2osf_` and `itnvs2aq`) in a single invocation.

## Reproduction

1. On the affected machine, capture inside the failing container:
   ```sh
   id
   env | grep -E 'DEVCAPSULE|PEX|XDG|HOME'
   ls -ln /etc/devcapsule/home/settings.toml /home/devcapsule /home/devcapsule/.cache
   ```
   And on the host:
   ```sh
   id
   ls -ln ~/.config/devcapsule/settings.toml
   docker info --format '{{.SecurityOptions}}'
   ```
2. Locally inside any capsule, the two individual failure modes reproduce with:
   - Unwritable cache: `HOME=/nonexistent XDG_CACHE_HOME=/nonexistent/.cache devcapsule0 --help`
   - Unreadable mounted settings: a `0600` `/etc/devcapsule/home/settings.toml`
     owned by a different UID causes `devcapsule0 ...` to exit `2` at
     `cli._dispatch` -> `load_settings()`.

## Workaround

- Run `devcapsule project run` on the **host** instead of inside the container, or
- Inside the container, set both environment variables to writable locations:
  ```sh
  export PEX_ROOT=/tmp/devcapsule-pex-root
  export DEVCAPSULE_CONFIG_HOME=/tmp/devcapsule-home
  devcapsule project run
  ```
  (Or configure them via `devcapsule project config env set` on the host.)

## Verification target, fix notes, and close criteria

- **Fix implemented on `ws-maintenance/0.3.1-rootless-docker` (2026-11-15):**
  - `host_daemon.security_options_indicate_rootless()` and
    `host_daemon.daemon_is_rootless()` inspect `docker info --format '{{json .SecurityOptions}}'`
    and activate rootless handling **only** when the daemon reports `rootless`;
    rootful Linux, macOS, and offline/unconfigured environments keep existing behavior untouched.
  - Entry layers (`ProjectRunCommand._run` and `recursive_successor.launch_successor`)
    read `daemon_is_rootless()` once and pass `uid=0, gid=0, user="root"` to
    `project_runtime_plan(...)` plus `rootless_docker=True` to `PycharmRunOptions`.
  - When `config.rootless_docker` is `True`:
    - `build_docker_args()` and `append_docker_mode_args()` pass `--user 0:0`,
      `IDE_UID=0`, `IDE_GID=0`, and `IDE_USER=root` (mapping host socket GID to
      `0` in `host` Docker mode when owned by the host user's GID).
    - `write_user_files()` maps `root:x:0:0:...:/home/devcapsule:/bin/bash` and
      root group entries without subordinate UID/GID entries.
    - `ensure_sudoers_policy_ownership()` accepts host-user-created policy files
      without host `chown 0:0` or container helper failures (because host UID files
      already map to container `0:0`), and `recursive_successor` skips `_make_root_owned()`.
    - `CapsuleUser.command()` and `CapsuleUser.owner_changes()` (and `logs.own`,
      `display._own`, and both `entrypoint.sh` scripts) skip redundant `gosu 0:0` /
      same-UID `chown 0:0` calls that `--cap-drop ALL` would otherwise refuse.
- **Validation and closure (2026-11-15):**
  - `validate_unittests_follow_conventions.py --base release-0.3.1` (`0` breaches), `nox -s typecheck` (`344` files), `nox -s tests` (`3267 passed`), `nox -s smoke`, and `nox -s docs-contract` (`249 pages`) passed on `ws-maintenance/0.3.1-rootless-docker` (`a1a54eba`).
  - Owner transported `devcapsule-local.pex` (`v0.3.1-local-linux-x86_64`, SHA-256 `7921e3bbd6abbe5ade7790d5c9020383d6117aa109608fa2714206246fde5d40`, built from `a1a54eba`) to the affected Ubuntu 24.04.5 LTS rootless Docker host and confirmed it worked on the rootless Docker installation (PR #38 merged into `release-0.3.1` at `2a3d6f61`).
- **Remaining note:** `scie` `boot.commands[""]` still unpacks without exporting `PEX_ROOT`; once
  `/home/devcapsule/.cache` is writable under rootless `0:0`, the default `$XDG_CACHE_HOME/pex` path
  stops falling back to `/tmp/pex-root.*` on writable capsule homes.
- **Reopen criteria:** Reopen if a capsule launched with the merged `0.3.1` executable on rootless Docker again fails with `/etc/devcapsule/home/settings.toml` permission denied or `/home/devcapsule/.cache/pex` unwritable, or if non-rootless behavior regresses.
