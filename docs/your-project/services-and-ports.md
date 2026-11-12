---
description: Run databases, caches, and companion services alongside a capsule and reach web applications inside the capsule from your host browser.
weight: 4
updated: 2026-10-30
---
# Services and ports

By default, a capsule runs on Docker's `bridge` network: outbound internet
connections work normally, and only the capsule's per-run desktop port (plus
the [web console](../sessions/web-console.md) port on base recipe `11` or
newer) is published on `127.0.0.1` with a one-run token. DevCapsule does not
publish application ports automatically.

## Reaching a web server running inside the capsule

Choose the option that matches how much of your host network you want to share:

### 1. Preview inside the capsule (zero configuration)

Start your server in the IDE terminal. If it listens on the capsule's
loopback or all interfaces, open `http://localhost:<port>` from a browser or
Playwright test inside the capsule. This needs no host port publishing.

### 2. Publish specific ports to `127.0.0.1` on the host (`bridge` network)

To open your app in your **host** browser while keeping Docker bridge
isolation, pass `--publish` (`-p`) bound to `127.0.0.1` either for one session
or saved privately for this checkout:

```bash
# One launch only:
devcapsule project run -- --publish=127.0.0.1:3000:3000

# Or save for every launch of this checkout:
devcapsule project config docker-args set -- --publish=127.0.0.1:3000:3000
devcapsule project run
```

When publishing over `bridge`:

- **Always prefix `127.0.0.1:`** (`127.0.0.1:3000:3000`, not `3000:3000`),
  to keep the published port local to your computer. Omitting the address
  normally publishes on all host interfaces.
- **Bind the server inside the capsule to `0.0.0.0`** (for example, `vite
  --host 0.0.0.0` or `python3 -m http.server --bind 0.0.0.0 3000`). A server
  listening only on container `127.0.0.1` rejects connections forwarded across
  the Docker bridge.
- Remember that `docker-args set` replaces the checkout's saved argument list
  (including saved `config env` entries). Inspect it with `devcapsule project
  config docker-args list` before replacing it, then supply the complete list.
  Reapply needed environment values with `config env set`. `docker-args clear`
  also removes all saved arguments and environment entries ([Saved Docker
  arguments](../configuration/project-versus-personal.md#saved-docker-arguments)).

### 3. Share the host network namespace (`network host`)

When an application opens dynamic callback ports or talks to several local
services, authorize `network host` for the checkout:

```bash
devcapsule project config authorize network host
devcapsule project run
```

With `network host`, `localhost` inside the capsule is your host's `localhost`:
servers listening on `127.0.0.1:3000` inside the capsule open directly at
`http://localhost:3000` in your host browser without `0.0.0.0` binds, and the
capsule shares your host's network interfaces. To keep the grant to one
launch, use `devcapsule project run --authorize network host` instead.

Return to bridge networking on the next launch with `devcapsule project config
deny network`. `config forget network` removes your answer, so a project
recommendation can prompt again. Raw `--network` options are refused; use
`--authorize network host` or `--authorize network bridge`.

## Running databases, caches, and message brokers

The capsule stops when you exit the IDE. Keep service data in persistent
storage, and choose whether services should outlive that session.

### Option A: Run services on the host (or host Docker Compose)

Start your database or service stack from a host terminal so
its lifecycle and volumes stay independent of IDE restarts:

- **With `network host`:** connect from the capsule to `localhost:5432` (or
  `127.0.0.1:6379`) directly.
- **On the default `bridge` network:** map the host gateway into the capsule:

  ```bash
  devcapsule project config docker-args set -- --add-host=host.docker.internal:host-gateway
  ```

  Then point your app inside the capsule at `host.docker.internal:5432` (ensure
  the host service listens on the Docker bridge interface as well as
  `127.0.0.1` and requires authentication).

Declare your application's connection variables without committing credentials.
This example uses `localhost` for host networking:

```bash
devcapsule project config require postgresql-client --because "migrations and psql run inside the capsule"
devcapsule project config require env POSTGRES_HOST POSTGRES_PASSWORD --because "connects to local development Postgres"
devcapsule project config env set POSTGRES_HOST localhost
devcapsule project config env set POSTGRES_PASSWORD
```

For the bridge setup above, set `POSTGRES_HOST` to `host.docker.internal`
instead. Use the variable names your application expects; declaring a name
does not configure the application or `psql` automatically.

### Option B: Start service containers from inside the capsule

If your test suite starts containers itself or you run
`docker compose` from the IDE terminal:

1. Require or offer the Docker CLI in the manifest (`devcapsule project config
   require docker-cli`).
2. Authorize the host Docker socket on checkouts that run those tests:

   ```bash
   devcapsule project config authorize docker-daemon host-socket
   ```

Understand two consequences of `docker-daemon host-socket`:

- **Security:** control of the host Docker socket is equivalent to root-level
  control over your host Docker daemon ([The
  boundary](../containment/the-boundary.md)).
- **Sibling containers, not nested ones:** containers started through
  `host-socket` run alongside the capsule on your host daemon. Bind mounts use
  host paths, and under default `bridge` networking their published ports
  appear on the host rather than on the capsule's `localhost` (pair with
  `network host` or `--add-host=host.docker.internal:host-gateway` when tests
  inside the capsule connect to published ports).

### Option C: Embedded or user-space databases inside the capsule

You can install and run an embedded database with your application's
dependencies inside the capsule. Keep its data files inside your mounted project directory (gitignored) or under
`/home/devcapsule` so they survive container replacement; files under `/tmp`
disappear when the session ends ([What persists](../sessions/what-persists.md)).
