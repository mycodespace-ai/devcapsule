# The configuration channel

The console's one way to change the next launch. Answer 7 of the CLI UX
redesign work order (`engineering-docs/work-orders/2026-10-24-cli-ux-redesign.md`,
2026-10-24): the launcher is the only writer of the user's records, so the
console and the launcher communicate through a directory the launcher
mounts into the capsule for the run, writable, at
`/run/devcapsule-configuration` (`--configuration`,
`$DEVCAPSULE_CONSOLE_CONFIGURATION`). Answer 16: the launcher writes the
listing it computed at launch into the same directory, so inspection inside
the capsule shows the truth with its time.

Writers publish complete JSON files. The launcher writes a temporary file,
then renames it into place. The console uses an exclusive hard link from a
complete temporary file, then removes the temporary name. Readers refuse
symbolic links, non-regular files, invalid JSON and documents over 256 KiB.
Files planted by other capsule processes need not follow this protocol.

## Files

| File | Writer | Content |
| --- | --- | --- |
| `listing.json` | launcher, once, at launch | `{"format": 1, "at": "<ISO 8601 UTC>", "listing": <the config show --json document>}` |
| `NNNNNN-VERB-UUID.request.json` | console | `{"format": 1, "requested": "<time>", "arguments": [<config tokens>]}` |
| `NNNNNN-VERB-UUID.result.json` | launcher, beside the request | `{"format": 1, "status": "recorded" \| "refused" \| "deferred", "text": "<what happened>", "at": "<time>"}` |

`NNNNNN` is the console's sequence number, six digits from `000001`; `VERB`
is the request's first token, lower case. `UUID` is 32 random hexadecimal
digits. The suffix prevents collisions between concurrent writers and runs.
A restarted console continues the sequence from existing request names.
The launcher handles requests in name order. Both sides also read legacy
names without the UUID. A duplicate legacy id receives a new host id when
an earlier request with that id still awaits confirmation. The result names
that host id. Neither request replaces the other. A request is the argument tokens of
one `devcapsule project config` command, without `--path`: the launcher
names the project.

## What the launcher does with a request

- **Recorded at once**, with the command's own validation and output, when
  the verb keeps the checkout's own choices or narrows what the next launch
  reaches: `ide`, `add`, `omit`, `restore`, `use`, `set`, `deny`, literal `env set NAME VALUE`,
  `env unset`, `unbind`, `trust withdraw`, `docker-args clear`. Explicit
  secure authorizations also apply: `network bridge|none`, `docker-daemon
  none`, and `development-sudo|host-browser|host-x11|github-ssh false|none`.
- **Deferred** when the verb widens what the next launch reaches:
  `authorize`, `trust accept`, `bind`, `forget`, `docker-args set`, and
  `env set` forms other than an explicit literal value. `forget` can restore
  workstation vendor trust after removing a download denial. `env set --from-host` exposes
  the named host variable at the next launch. Abbreviated options also
  require confirmation. Literal values starting with `-` are conservatively
  deferred. Anything running
  inside the capsule can write to the mounted directory, not only the
  console, so a widening is never taken from it unconfirmed. The launcher
  keeps it as the console's request beside the checkout record; the user
  confirms or discards it on the host, at the next `devcapsule project run`
  or with `devcapsule project config console apply|discard ID`.
- **Refused**, with the reason, for anything else: a read-only verb, a
  workstation default, an owner's command, an unknown verb, a malformed
  document.

Adding a capability records a selection. Vendor consent still applies at the
next launch. Capability rows use the kind `capability`; only the IDE row uses
`ide`.

The console checks the verb before writing, so a typo is refused on the
page; the launcher validates the whole command again. The result's `text`
includes the command output or the reason. Sending alone confirms no change. A request timestamp must be an ISO time
with a time zone. Tokens must contain valid Unicode without control characters.

The watcher's child receives record-location and locale variables, not host secrets or
Python injection settings. It has no controlling terminal and reads EOF on
standard input. The launcher kills its process group after 120 seconds.
An explicitly confirmed host command keeps the host environment, including
its Docker context. At shutdown, the worker finishes its active command and saves remaining
valid requests for host confirmation. It starts no further commands.
A full deferred queue refuses new requests before it exceeds the 256 KiB
reader limit. Result text is limited to 16,384 characters, with a truncation
notice. Deferred requests live outside the mounted records tree. Their store is keyed
by project identity and canonical checkout path. Re-registration under another
name keeps them. A second checkout does not inherit them.

A missing listing in an existing channel is an inspection error. A listing
with another project, checkout name or launcher path is also an error.
Older launchers without a channel retain the read-only recorded-input view.
Readers show malformed results with the local outcome `unknown`. This is not a launcher reply and does not prove whether
the command ran; inspect configuration on the host before retrying.

## Routes

- `GET /api/configuration`: the runtime CLI's `config show --json`, which
  inside a capsule with the channel is the launcher's listing at launch
  with `at`, `console-requests` and `launcher-command`; each pending row
  gains `request`, the config tokens its host command implies; `channel`
  says whether the channel has a readable launch listing.
- `GET /api/configuration/requests`: every request of this run with its
  result, in order.
- `POST /api/configuration/requests`, same origin only, body
  `{"command": "<config tokens>"}`: writes one request; `201` with the
  request, `422` with the reason, `403` from another origin, `413` when
  too large, `500` when the directory cannot be written.

Inside the capsule, `devcapsule project config show` prints the same
listing labelled "At launch, <time>" and, below it, the requests asked on
the console since, each with the launcher's result.

The launch listing includes DevCapsule's exposure description and the project's reason for each host-access row. The page displays both beside each other.
The page shows host commands for earlier deferred requests. It does not
submit those confirmations back through the capsule. It stops automatic
polling after about two minutes without an answer and explains that no
change is confirmed. A failed outcome read stays visible. Refresh the page
to inspect later results. The page cannot prove that a stopped launcher
saved a request; inspect the host's `config console list` before retrying.
