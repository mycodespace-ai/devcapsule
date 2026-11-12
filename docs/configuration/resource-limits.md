---
description: Set capsule memory and CPU limits per launch, per checkout, as a project recommendation, or as a home default, along with project-declared values.
weight: 5
updated: 2026-10-30
---
# Resource limits

The launcher owns two container limits on every capsule: `memory` and `cpus`.
For each limit, `project run` uses the first value present in this order:

1. One-shot launch flag (`run --memory` or `run --cpus`)
2. Checkout answer (`project config set`)
3. Project recommendation (`project config recommend` in `.devcapsule/devcapsule.toml`)
4. Home default (`home default` in `settings.toml`)

When none of those four sets a value, DevCapsule passes no Docker limit for
that resource.

```bash
devcapsule project config set memory 8GiB
devcapsule project config set cpus 4
devcapsule home default memory 8GiB
devcapsule project config recommend memory 6G --because "the test suite builds a 4 GB index"
devcapsule project run --memory 12g
```

- `project config set` records the value for this checkout; `project config set
  memory default` (or `cpus default`) forgets your checkout override so project
  and home defaults apply again. These two limits do not accept `none` as a
  checkout value.
- `home default` sets the default for every project launched from your active
  [configuration home](home.md) that has no project recommendation or checkout
  override; `home default memory none` (or `cpus none`) removes it.
- `project config recommend` writes the project's recommendation (and optional
  `--because` reason) into `.devcapsule/devcapsule.toml` for checkouts that set
  no value of their own.
- `project run --memory` and `--cpus` apply to one launch; add `--save` to
  record them in your checkout once launch checks pass.

Memory accepts positive integer sizes with `B`, `K`, `M`, `G`, or `T` units
(such as `6g`, `6G`, `6GB`, `6GiB`, or `6144m`) and stores canonical binary
forms (`B`, `KiB`, `MiB`, `GiB`, `TiB`), so `6g` normalizes to `6GiB` and
`6144m` to `6144MiB`. `cpus` must be a positive integer—fractional values such
as `1.5` are rejected. `project config show` prints each active limit and its
source.

For other Docker flags that DevCapsule does not own directly, use [saved Docker
arguments](project-versus-personal.md#saved-docker-arguments). Options owned by
the launcher or IDE runtime template remain reserved: for example, raw
`--shm-size` is refused because the IDE template sets shared-memory size, and
`project run --name NAME` overrides the container name for a single launch.

## Values a project declares

A project can also declare typed configuration values (`string`, `integer`,
`boolean`, or `memory-size`) in `.devcapsule/devcapsule.toml`:

```toml
[configuration.values."build.workers"]
type = "integer"
description = "Parallel build jobs; the integration suite needs at least 4."
```

Set or clear them with the same checkout command—`devcapsule project config set
build.workers 4` or `devcapsule project config set build.workers default`—or
pass `--set build.workers 4` during `project init`. DevCapsule validates each
value against its declared type. `default` follows the project's recommendation;
it does not force the value to be absent. For an optional declared value,
`project config set build.workers none` explicitly omits it. A declaration with
`required = true` rejects `none`.

Declared values never grant host access or
software downloads; see [Granting and
withdrawing](../containment/granting-and-withdrawing.md) for authorizations.

Older manifests could declare a memory value under a custom name such as
`runtime.memory-limit` with `runtime-effect = "docker.memory-limit"`. The
launcher still honors that recommendation and any saved answer as `memory`,
while `project config set runtime.memory-limit SIZE` refuses and directs you to
`project config set memory SIZE` (and `project config set memory default` clears
the legacy answer).
