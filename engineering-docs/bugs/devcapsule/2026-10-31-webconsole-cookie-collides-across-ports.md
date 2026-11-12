---
status: closed
severity: blocking
target: 0.3.0
owner: maintenance
opened: 2026-10-31
requirements: [R-CONSOLE-001]
---

# Concurrent web consoles on `127.0.0.1` overwrite one another's authentication cookie across ports

## Symptom

Surfaced during Pair Review of Batch 5 of the `0.3.0` user-documentation CLI
alignment (`PR #327` / `PR #328`, 2026-10-30) and rated blocking for `0.3.0` by
the owner on 2026-10-31:

1. Start Capsule A (`http://127.0.0.1:41273/?token=TOKEN_A`) and open its web
   console in a browser. `TokenGate` sets
   `Set-Cookie: devcapsule-console-token=TOKEN_A; Path=/; HttpOnly; SameSite=Strict`.
2. Start Capsule B (another project or registered worktree on the same host,
   `http://127.0.0.1:41274/?token=TOKEN_B`) and open its web console in another
   tab of the **same** browser profile. `TokenGate` responds with
   `Set-Cookie: devcapsule-console-token=TOKEN_B; Path=/; HttpOnly; SameSite=Strict`,
   replacing `devcapsule-console-token` in the browser's cookie jar for every
   port on `127.0.0.1`.
3. Switch back to Capsule A's console tab: the next internal navigation link
   (`/configuration`, `/processes`, `/decisions`, `/static/*`) or background
   `/api/*` fetch carries `Cookie: devcapsule-console-token=TOKEN_B` with no
   `?token=` query parameter, and `TokenGate` refuses it with `HTTP 403`
   (`devcapsule web console: missing or invalid run token`). Reopening Capsule
   A's `?token=TOKEN_A` URL restores Capsule A while breaking Capsule B in turn.
4. In addition, `http.cookies.SimpleCookie.load()` in `security.py` aborts on
   JSON or bracketed cookies set on `127.0.0.1` by sibling local web
   applications (for example `g_state={"i_l":0}` or `filter[a]=1` from an
   application running on `127.0.0.1:3000`), silently returning `{}` or raising
   `CookieError` and discarding a valid console token cookie that follows in
   the same `Cookie` header.

## Cause, from the code

Unlike the Web Same-Origin Policy (`Origin`, `localStorage`, CORS), HTTP
cookies are not isolated by port (RFC 6265 §4.1.2.3, §5.1.3, §8.5: *"Cookies do
not provide isolation by port"*), and `SameSite=Strict` keys on site
(`http://127.0.0.1`) without port. `TokenGate` in
`devcapsule-webconsole/devcapsule_webconsole/security.py` used a single
hardcoded cookie name (`TOKEN_COOKIE = "devcapsule-console-token"`) on every
port, and parsed the incoming `Cookie` header with `http.cookies.SimpleCookie`.

Note also that under default `bridge` networking every container runs
`devcapsule-webconsole` on internal `--port 6081` published to a distinct host
loopback port (`127.0.0.1:<host_port>:6081`), so scoping by the container's CLI
`--port` would still collide across bridge-mode capsules; the browser-facing
port arrives on every HTTP request in the `Host` header (`127.0.0.1:<host_port>`).

## Expected behaviour

- Each console scopes its session cookie name to the browser-facing port in the
  incoming HTTP `Host` header (`devcapsule-console-token-<port>`, falling back
  to `devcapsule-console-token` only when the origin carries no explicit port).
- Opening a second (or third) capsule's console on `127.0.0.1` in the same
  browser profile leaves all previously opened consoles authenticated.
- Sibling local-application cookies on `127.0.0.1` (JSON, bracketed, or
  attribute-like names) and HTTP/2 split `Cookie` headers do not prevent
  `TokenGate` from reading its own `devcapsule-console-token-<port>` cookie.
- Diagnostic redaction (`devcapsule-src/devcapsule/_redaction.py`) scrubs both
  bare `devcapsule-console-token=` and suffixed `devcapsule-console-token-<port>=`
  values while keeping the cookie name and port readable.

## Verification target

1. Automated tests in `devcapsule-webconsole/tests/test_security.py`:
   - Two `create_app` instances on `127.0.0.1:41273` and `127.0.0.1:41274`
     sharing one `127.0.0.1` cookie jar keep independent
     `devcapsule-console-token-<port>` cookies and refuse each other's cookies.
   - Two live loopback `uvicorn` HTTP servers sharing one standard-library
     `http.cookiejar.CookieJar` authenticate sequentially via `?token=` and
     then serve `/configuration` and `/processes` concurrently without `403`.
   - IPv4, IPv6 (`[::1]:41273` vs `[::1]`), `localhost`, malformed/duplicate
     `Host` headers, HTTP/2 split `Cookie` headers, and non-RFC2109 neighbor
     cookies (`g_state={"i_l":0}`, `filter[a]=1`, `$bad=attr`).
2. Diagnostic redaction regression test in `devcapsule-src/tests/test_diagnostics.py`
   for both bare and port-suffixed console cookies.
3. For non-self-hosting user projects that consume the published recipe-11 base
   image (`docker.io/mycodespaceai/devcapsule-base`, where `/opt/devcapsule-webconsole`
   is installed at base-image build time from the runtime's source revision;
   self-hosting DevCapsule checkouts already mount `devcapsule-webconsole/`
   live), rebuild and pin the published recipe-11 base from clean public source
   containing this fix before RC9 under the owner's 2026-10-31 **base-first**
   decision, and verify on a downloaded `0.3.0` candidate.

## Close criteria

- Fix merged into `release-0.3.0` and propagated to `main` under the `0.3.0`
  release flow.
- Published `ubuntu-24.04@11` base pin updated from clean public source
  carrying the updated `devcapsule-webconsole/` (so non-self-hosting projects
  receive the port-scoped cookie without building a local base), and verified
  before the final `v0.3.0` tag.

## Fix, 2026-10-31

Implemented on `ws-maintenance/0.3.0-webconsole-port-cookie` targeting
`release-0.3.0`:

- `devcapsule-webconsole/devcapsule_webconsole/security.py`: added
  `token_cookie_name(port)`, `_scope_port(scope)` (strict RFC 3986 `Host` port
  extraction with ASCII/injection guards and portless fallback), and
  `_cookie_values(raw_headers, cookie_name)` (`;`-pair extraction across all
  `Cookie` headers, replacing `SimpleCookie.load()`).
- `devcapsule-src/devcapsule/_redaction.py`: widened `_CONSOLE_COOKIE_RE` to
  scrub suffixed `devcapsule-console-token-<port>=` cookies while preserving the
  cookie name and port.
- `docs/sessions/web-console.md`, `docs/sessions/several-projects.md`,
  `docs/troubleshooting/diagnostics-and-logs.md`, and
  `devcapsule-webconsole/README.md`: replaced the multi-profile workaround note
  with the port-scoped cookie behavior.

## Base delivery — 2026-10-31

The owner chose **base-first** at 02:14:16 UTC in decision
`2026-10-31-rc9-base-refresh`, replacing the bootstrap-candidate sequence
above. The supported strict-public-source PEX builder identifies commit
`12a30fa60322de585810048881ee166fcdb26854`; `images build --type base`
verified that commit on GitHub and fetched the console from that exact SHA.
The image is published as `mycodespaceai/devcapsule-base:v0.3.0-base-20261031`,
digest `sha256:d7047ced8556cd35964fcc058a1101cf2b5b202f7a5daa2fdd434dcda5ed82c9`.
A registry pull resolves to the built image ID. Its installed console security
module matches the fixed source byte-for-byte. Only the console filesystem
layer differs from the rc6 base. Catalog embedded-31 selects it for new
resolutions and retains the rc6 pin for existing locks. Existing capsules
must be relaunched with the updated base; installing a launcher does not
rewrite an existing lock.

[Base identity evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/base-refresh.json).
Main propagation and downloaded-candidate acceptance remain release gates.

Two real fresh-project capsules on the new default base passed the shared
browser test: tokenless console navigation/reload, noVNC reload/reconnect,
and refusal of sibling console and desktop credentials. Published-base layer
lineage and cleanup passed. See the [concurrent-authentication evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#published-base-and-concurrent-authentication).

## Closed — 2026-10-31

The fix is in release `475427da` and main `4b59b10d` through #329/#331.
Published RC9 embeds source `475427da033633ff5ee0e44e09face700630bf36` and
selects the rebuilt base above. Its downloaded PEX checksum is
`413b1d45bac9c39b6fa5fab68090e43550c9e255108de48b387c50a715c4fcf2`.
The shared-browser regression passes against that exact downloaded artifact
on two fresh non-self-hosting projects using the default catalog pin.
Both consoles remain authenticated on tokenless navigation/reload; both
noVNC sessions reconnect; sibling cookies and URL/WebSocket tokens are
refused. Containers and project records were removed after the check.
[Sanitized evidence](../../wip/2026-09-18-maintenance/evidence/2026-10-31-rc9/README.md#downloaded-rc9-verification)
includes base layer lineage. The browser test uses host networking;
Host-header cases remain separately covered by the automated console tests.
NoVNC uses its own WebSocket token URL; it does not use the console cookie.
