// The one place that knows what a web console recording address looks like.
// The button (background.js) and the player page (player.js) both ask here, so
// the player never loads an address the button would not have accepted.

const RAW_ROUTE = '/api/project/raw';
const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost']);
const PLAYABLE = /\.webm$/i;

/** The shape of an accepted address, for messages. */
export const EXPECTED = `http://127.0.0.1:<port>${RAW_ROUTE}?path=<file>.webm`;

/**
 * The recording an address names, or null when it is not the console's raw
 * route on a loopback host with a `path` ending in `.webm`.
 *
 * `raw` is rebuilt from the origin and the path alone, so nothing else the
 * address carried (a `download=1`, a `token`) travels into the player.
 */
export function consoleRecording(address) {
  let url;
  try {
    url = new URL(address);
  } catch {
    return null;
  }
  const path = url.searchParams.get('path');
  if (
    url.protocol !== 'http:' ||
    !LOOPBACK_HOSTS.has(url.hostname) ||
    url.pathname !== RAW_ROUTE ||
    !path ||
    !PLAYABLE.test(path)
  ) {
    return null;
  }
  const raw = new URL(RAW_ROUTE, url.origin);
  raw.searchParams.set('path', path);
  return { origin: url.origin, path, raw: raw.href };
}
