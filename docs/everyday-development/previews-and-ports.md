---
description: Reaching a web application that runs in the capsule from your computer's browser, and publishing a port on purpose.
weight: 4
updated: 2026-10-30
---
# Previews and ports

Suppose your application listens on port 3000 inside the capsule. Opening
`http://localhost:3000` on your computer does not reach it by default.
The capsule uses Docker's `bridge` network and publishes its desktop and
[web console](../sessions/web-console.md) on host loopback addresses.
Publish your application's port separately.

Pick one of three ways to preview your application depending on your workflow:

## 1. Publish a specific port to `127.0.0.1` on your computer (`bridge` network)

To keep default network isolation and expose only the port you choose on your
host's loopback address, pass `--publish=127.0.0.1:<host-port>:<capsule-port>`
either for one launch or as a saved checkout argument. Run these commands
from your host terminal:

```bash
# Expose port 3000 on host 127.0.0.1 for this session only
devcapsule project run -- --publish=127.0.0.1:3000:3000

# Or save it for this checkout across launches
devcapsule project config docker-args set -- --publish=127.0.0.1:3000:3000
devcapsule project run
```

Then start your server inside the capsule bound to **`0.0.0.0`** (all container
interfaces), not container `127.0.0.1`:

```bash
# Serve static files from the current directory
python3 -m http.server --bind 0.0.0.0 3000
```

Now open `http://127.0.0.1:3000` (or `http://localhost:3000`) in your host
browser. Keep three details in mind:

- **Include `127.0.0.1:` in `--publish=127.0.0.1:3000:3000`.** Writing
  `--publish=3000:3000` without `127.0.0.1:` normally binds `0.0.0.0:3000` on
  your host and exposes your development server to other devices on your local
  network.
- **Binding to `0.0.0.0` enables forwarding.** A server listening only on
  container `127.0.0.1` cannot accept traffic sent to its bridge interface.
  The host and other containers on the same bridge can also reach that
  interface directly. A loopback publish address limits the published host
  port; it does not isolate the application from those peers.
- **`docker-args set` replaces the entire saved list** (including saved `config
  env` entries). Check `devcapsule project config docker-args list` first, pass
  all `--publish=...` flags you want to keep in one command, and reapply any
  saved environment variables with `config env set` ([Saved Docker
  arguments](../configuration/project-versus-personal.md#saved-docker-arguments)).

`-p 127.0.0.1:3000:3000` is the short form of the publish option.
`devcapsule project config docker-args clear` removes all saved Docker
arguments, including environment entries. Both changes take effect on the
next launch.

## 2. Share `localhost` with host networking (`network host`)

If your app spins up dynamic ports, runs OAuth callback servers expecting exact
`localhost` origins without `0.0.0.0` flags, or talks to multiple local
services on your host, grant `network host` for one launch or for the checkout:

```bash
# One session only
devcapsule project run --authorize network host

# Or save for this checkout
devcapsule project config authorize network host
devcapsule project run
```

With `network host`, the capsule and your computer share one network namespace:
a server listening on `127.0.0.1:3000` inside the capsule opens directly at
`http://localhost:3000` in your host browser without `--publish` or `--host
0.0.0.0` flags. Docker ignores publish options in host network mode.
A port already used on the host can cause an address-in-use error.
Return to bridge isolation on the
next launch with `devcapsule project config deny network` (raw `--network`
Docker flags are refused; use `--authorize network host` or `bridge`).

## 3. Preview inside the capsule desktop (`browser-automation`)

When your project includes `browser-automation` (or you add it locally with
`devcapsule project config add browser-automation`), Chromium is installed
inside the capsule alongside Python Playwright (`$DEVCAPSULE_PLAYWRIGHT_PYTHON`
and `$PLAYWRIGHT_BROWSERS_PATH`). Headed Playwright runs and browser checks
inside the capsule connect directly to `http://localhost:3000` on the capsule
desktop without publishing any port to your host.

For database connections and companion services, see
[Services and ports](../your-project/services-and-ports.md).
