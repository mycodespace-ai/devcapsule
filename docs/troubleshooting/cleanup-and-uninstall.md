---
description: How to inspect DevCapsule storage, remove unused Docker images and caches, reset one checkout's state, or uninstall DevCapsule completely.
weight: 3
updated: 2026-10-30
---
# Cleanup and uninstall

DevCapsule keeps checkout configuration and persistent storage in your
configuration home and uses Docker's local image store. Run the cleanup steps
below in the host terminal that launches your capsules, with the same
`DEVCAPSULE_CONFIG_HOME` or XDG settings.

## See what DevCapsule is using

Before deleting files or images, inspect the active home, registered
checkouts, and local Docker images:

```bash
devcapsule home show
devcapsule project list
devcapsule images list --include-legacy
```

For one checkout, run these commands inside its repository:

```bash
devcapsule project config show --json
devcapsule project info --json
```

`config show --json` gives the checkout-record path in `checkout.input`.
`info --json` gives persistent mount paths in `persistence[].backing`,
including IDE and agent state, caches, and session logs. To select another
repository, put `--path /path/to/repo` before `config` or `info`; see
[Project info](../reference/project-info.md).

By default, a DevCapsule home spreads files across four XDG directories
(`~/.config/devcapsule`, `~/.local/share/devcapsule`,
`~/.local/state/devcapsule`, and `~/.cache/devcapsule`). The corresponding
`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, and `XDG_CACHE_HOME`
variables can change those roots. When `DEVCAPSULE_CONFIG_HOME` is set,
configuration sits in that directory. Data, state, and cache use its `data/`,
`state/`, and `cache/` subdirectories; see
[The configuration home](../configuration/home.md).

## Reclaim disk space safely

Most disk usage comes from Docker images and downloaded component archives.
You can remove unused copies while keeping project files and personal state.
Keep recovery resources when you need offline rollback.

### Unused Docker images

`devcapsule images list --include-legacy` lists managed base images,
materialized IDE environments, and transitional images with legacy labels.
Materialized images have tags such as `devcapsule-local-pycharm:<hash>`.

Stop sessions that use an image before removing it. Replace `IMAGE_TAG` below
with an unused tag from the listing:

```bash
docker image rm IMAGE_TAG
```

A later launch can need downloads or a rebuild after you remove an image.
Keep the base image and either the matching environment image or retained
archives for offline [rollback](../updates/component-upgrades.md#roll-back-to-a-known-good-set).
Removing the base image requires `versions rollback --reacquire` even when
component archives remain.

### Downloaded component and tool caches

Verified downloads live under `artifacts/` in the cache root. Per-checkout
caches live under `projects/by-path/<checkout id>/` in that same root.
Stop launches and running sessions before clearing caches.

For the default XDG home, clear the cache with:

```bash
rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/devcapsule"
```

For a named home, remove `"$DEVCAPSULE_CONFIG_HOME/cache"` instead. Future
launches recreate needed caches, which can require network access.

Version history and retained recovery archives are separate, under
`version-sets/<path hash>/` in the state root. `<path hash>` is the full SHA-256
of the canonical checkout path, without a trailing newline. It differs from
`<checkout id>` in the storage paths reported by `info`. Deleting that directory
removes the checkout's upgrade previews, observations, successful-use history,
and retained archives. Keep it if you want known-good rollback choices.

### Old session logs

Session logs use `projects/by-path/<checkout id>/logs/` in the state root.
At launch, DevCapsule removes eligible old sessions toward the
`DEVCAPSULE_LOG_BUDGET` target (`256M` by default). Protected sessions can keep
usage above that target. You can lower it to `16M`, or manually delete ended
session directories; see
[Diagnostics and logs](diagnostics-and-logs.md#how-much-disk-this-takes).

## Reset or remove one checkout

Checkout configuration is separate from persistent IDE and agent storage.
Before removing a clone, inspect it from the host and record the paths above.

1. Stop every running session for that checkout with `Ctrl+C` in its launcher
   terminal, or `docker stop CONTAINER_NAME`.
2. To reset managed IDE and agent state, remove this checkout's
   `projects/by-path/<checkout id>/` directories under data, state, and cache.
   This deletes sign-ins, settings, extra tools under the managed home, and
   logs. Keep explicitly bound or adopted directories unless you also intend
   to erase their contents. Keep the source checkout listed as `project`.
3. To forget configuration choices too, first run
   `devcapsule project config docker-args clear`. This also clears saved
   environment entries. Run `devcapsule project config console list` and
   discard each pending request with `devcapsule project config console discard ID`.
4. Delete the checkout input file reported by `config show --json` and its
   resolved companion. The default names are `devcapsule.checkout.toml` and
   `devcapsule.resolved.toml`. Named checkouts use
   `checkouts/NAME.checkout.toml` and `checkouts/NAME.resolved.toml` under the
   project's configuration directory. Other checkouts can share that parent
   directory; keep their records.
5. If you also want to remove upgrade history and recovery archives, remove
   this checkout's `version-sets/<path hash>/` directory described above.

## Uninstall DevCapsule completely

1. **Stop running capsules.** Press `Ctrl+C` in each `devcapsule project run`
   terminal. Normal sessions use `docker run --rm`, which removes their
   containers on exit. Check `docker ps` for containers still running.
2. **Remove DevCapsule Docker images.** Before deleting the executable, run
   `devcapsule images list --include-legacy`. Pass unused tags or image IDs
   to `docker image rm`.
3. **Remove DevCapsule host directories.** For the default XDG home:

   ```bash
   rm -rf \
     "${XDG_CONFIG_HOME:-$HOME/.config}/devcapsule" \
     "${XDG_DATA_HOME:-$HOME/.local/share}/devcapsule" \
     "${XDG_STATE_HOME:-$HOME/.local/state}/devcapsule" \
     "${XDG_CACHE_HOME:-$HOME/.cache}/devcapsule"
   ```

   Also remove custom homes you created with `DEVCAPSULE_CONFIG_HOME`.
   Bound or adopted directories outside those homes remain in their original
   locations. Remove them separately only if you intend to delete their data.
4. **Remove the executable.** Delete `~/.local/bin/devcapsule`, or the path
   where you installed it. `command -v devcapsule` shows the current command.

Committed `.devcapsule/` files belong to their Git repositories. Uninstalling
the launcher does not remove them.
