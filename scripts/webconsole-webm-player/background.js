// The toolbar button. On a console recording address it replaces the tab with
// the extension's player page; on anything else it says so in the log.
//
// Why a page of the extension and not a <video> added to the open document:
// the raw route answers with `Content-Security-Policy: sandbox; default-src
// 'none'`, and a <video> inside that document, whoever creates it, is refused
// its media fetch. The player page is a different document, outside that
// policy, and the host permissions in the manifest make its request to the
// console carry the console's SameSite=Strict token cookie.

import { EXPECTED, consoleRecording } from './pattern.js';

const LOG_PREFIX = '[DevCapsule WebM player]';
const BADGE_MILLISECONDS = 2500;

chrome.action.onClicked.addListener(async (tab) => {
  const recording = consoleRecording(tab.url);
  if (recording) {
    const player = new URL(chrome.runtime.getURL('player.html'));
    player.searchParams.set('src', recording.raw);
    await chrome.tabs.update(tab.id, { url: player.href });
    return;
  }
  await reportNoMatch(tab);
});

/** Says the pattern did not match: in this worker's log, in the tab's own console, and on the button. */
async function reportNoMatch(tab) {
  const shown = tab.url ?? 'this tab (its address is not readable by the extension)';
  const message = `${LOG_PREFIX} pattern not matched: ${shown} is not ${EXPECTED}`;
  console.warn(message);
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (text) => console.warn(text),
      args: [message],
    });
  } catch {
    // Browser pages (chrome://, the extensions gallery) accept no script; the worker's log has the message.
  }
  await chrome.action.setBadgeText({ tabId: tab.id, text: 'no' });
  setTimeout(() => chrome.action.setBadgeText({ tabId: tab.id, text: '' }).catch(() => {}), BADGE_MILLISECONDS);
}
