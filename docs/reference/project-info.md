---
description: Every section and JSON field of devcapsule project info, on the host and inside a running capsule.
weight: 3
updated: 2026-10-30
---
# `project info` fields

`devcapsule project info` reports a checkout's selected software, container
environment variables, persistent storage mounts, and temporary paths. It is
offline and read-only: it never resolves locks, creates directories, contacts
Docker, or exposes secret values.

```sh
devcapsule project info
devcapsule project info --json
```

Pass `--path PROJECT` before `info` to inspect another directory:
`devcapsule project --path /path/to/repo info --json`.

## Host context vs. running-capsule context

`project info` runs in two modes, reported in `Context` (and `context` in JSON):

| Context value | When you see it | Where the data comes from |
|---|---|---|
| `host selection (next launch)` | On the host, or inside a capsule when `--path` targets a checkout other than this capsule's launched project root. | Derived directly from `.devcapsule/devcapsule.toml`, the selected platform lock, and your checkout record. |
| `running capsule (captured at launch)` | Inside a capsule on its own launched project checkout. | Read from the read-only launch snapshot mounted into the container, paired with allowlisted variables from the current process environment and a live comparison against the host's current lock. |

Key differences between the two modes:

- **Running vs. next launch:** Inside a capsule, `components` and `base`
  describe the software running in *this* container, not edits made on the host
  after launch. The report adds `running-selection` (the version-set identity)
  and checks the mounted host configuration to report `next-launch-components`
  and `selection-changed` (or `next-launch-unavailable` with the reason if the
  host lock cannot be read).
- **Environment values:** On the host, `environment` shows what the lock and
  component templates configure (`source: "configured"`), ending `PATH` with
  `<base-image PATH>` because the image is not inspected. Inside a capsule,
  `environment` reports actual values from an explicit allowlist of non-secret
  process variables (`source: "observed in this process"`), including runtime
  values such as `DISPLAY`, `DEVCAPSULE_CONTAINER_NAME`,
  `DEVCAPSULE_CONSOLE_URL`, and `DEVCAPSULE_LOG_DIR`.
- **Storage backing paths:** `Persistence` always shows backing paths from the
  host launcher's point of view (`container_path -> host_backing_path`),
  captured at launch when viewed inside a capsule. Capsules started by older
  launchers that did not record storage backing omit those rows and print a
  note advising a relaunch.

## Text sections

The text report starts with `Project`, `Context`, `Checkout`, `Checkout name`,
and `Source in capsule`. `Components` lists component versions; `Base` shows
the selected lock's image reference. Inside a capsule, `Next launch components`
marks the selection as changed or unchanged, or `Next launch unavailable`
explains why comparison failed.

`Environment` lists each variable's value, purpose, and source. `Persistence`
lists container paths, host backing paths, scope, storage kind, and lifetime.
`Temporary` lists paths lost with the container. Notes follow those sections.
Use `--json` for logical slot names and fields such as `running-selection`.

## Top-level JSON structure

`devcapsule project info --json` prints a UTF-8 JSON object with
`"schema-version": 1`:

| Field | Present | Type | Meaning |
|---|---|---|---|
| `schema-version` | Always | integer | Format version (`1`). |
| `context` | Always | string | `"host selection (next launch)"` or `"running capsule (captured at launch)"`. |
| `project` | Always | object | `name`, `creator`, and `slug` from `.devcapsule/devcapsule.toml`. |
| `checkout` | Always | object | `launcher-path` (host checkout root), `runtime-path` (mount path inside the capsule, such as `/workspace/app`), `name` (`"default"` or the name set with `project checkout register`), and `registered` (`true` when a checkout record was loaded; captured at launch inside a capsule, and absent from older snapshots without storage information). |
| `components` | Always | object | Map of component ID to version string (for example `{"codium": "1.99.2", "claude-code": "2.1.76"}`). |
| `base` | Always | object | `reference` and `build-mnemonic` from the selected lock; a missing lock field becomes `null`. These fields do not report a checkout-local base override; use `versions show` for that. |
| `running-selection` | Capsule only | string | Version-set identity that started this container, expressed as a SHA-256 hex string. |
| `next-launch-components` | Capsule (when readable) | object | Component-to-version map currently selected on the host for the next launch. |
| `selection-changed` | Capsule (when readable) | boolean | `true` when the host's next-launch lock differs from the running container's lock. |
| `next-launch-unavailable` | Capsule (on error) | string | Explanation when the host's current lock or checkout selection cannot be evaluated from inside the capsule. |
| `environment` | Always | array | Ordered list of non-secret environment entries (`name`, `value`, `purpose`, `source`). |
| `persistence` | Always | array | Persistent mounts in the capsule (`name`, `path`, `backing`, `scope`, `kind`, `lifecycle`). |
| `temporary` | Always | array | Objects with string keys `path` and `lifecycle`, for `/tmp`, `/run`, `/var/tmp`, and `/dev/shm`. |
| `notes` | Always | array of strings | Plain-language caveats about storage lifetimes, `/opt/xtras`, secret omission, and pre-launch limits. |

## `environment` entries and secret safety

Each object in `environment` has four string keys:

- `name`: environment variable name (such as `HOME`, `PROJECT_PATH`, `PATH`,
  `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `DEVCAPSULE_LOG_DIR`, or
  `DEVCAPSULE_CONSOLE_URL`).
- `value`: configured or observed value.
- `purpose`: short human description of why DevCapsule sets or tracks it.
- `source`: `"configured"`, `"configured; base PATH suffix is not inspected"`,
  or `"observed in this process"`.

`project info` uses a fixed variable allowlist (`HOME`, `PROJECT_PATH`, `PATH`,
`XDG_*`, agent config paths, display/opener endpoints, `DEVCAPSULE_*` session
identifiers, and managed IDE runtime variables). It never dumps arbitrary
process variables, `project config env` values, `host-environment:` secret
bindings, or web-console run tokens. Even `XAUTHORITY` reports only its file
path, never credential bytes.

## `persistence` entries

Each object in `persistence` describes one directory that survives container
removal:

| Key | Values | Meaning |
|---|---|---|
| `name` | `project`, `home`, `<component>/<slot>`, `xtras`, `logs` | Logical slot name. `home` and `<component>/<slot>` can use an existing host directory through `project config bind` or `project state adopt`; neither copies its contents. |
| `path` | Absolute container path | Mount point inside the capsule (such as `/workspace/my-app`, `/home/devcapsule`, `/ide-config`, `/opt/xtras`, `/var/log/devcapsule`). |
| `backing` | Absolute host path | Directory on the host computer holding the data (under `$DEVCAPSULE_CONFIG_HOME` when set, otherwise XDG data, state, or cache directories, or your bound path). |
| `scope` | `"this checkout"` or `"explicit storage; may be shared"` | Whether the directory is private to this checkout or points to an adopted/bound host directory. |
| `kind` | `"source"`, `"durable"`, `"state"`, `"cache"` | Storage class: Git checkout (`source`), user data and settings (`durable`), operational state and logs (`state`), or rebuildable caches (`cache`). |
| `lifecycle` | String | What survives container replacement, whether caches may be cleared, and the default log-budget guidance. This text does not report the active budget; `session.json` records it, and retention is a target, not a hard cap. |

Compare `persistence` with `temporary` (`/tmp`, `/run`, `/var/tmp`, `/dev/shm`)
when deciding where to store build outputs or tools: anything written outside
the `persistence` paths disappears as soon as the container stops, and the
container root filesystem itself is normally read-only.
