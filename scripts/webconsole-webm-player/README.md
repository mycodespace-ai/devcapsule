# DevCapsule console WebM player

A small Chrome extension for the people who work on DevCapsule. It plays a
`.webm` recording that the web console serves from its raw route, on a console
that cannot play it itself.

**It is temporary.** It works around one defect in consoles built before the
fix, and it goes away with them; see *When to remove it*.

## What it is for

A video opened from the console's Files page went to the raw route:

```text
http://127.0.0.1:<port>/api/project/raw?path=<folder>/<file>.webm
```

Chrome shows a player there, with a length of `0:00`, and the player never
plays. The raw route answers every file with
`Content-Security-Policy: sandbox; default-src 'none'; style-src 'unsafe-inline'`,
and Chrome's own player for a video address is a document that inherits that
policy, so its fetch of the video is refused. The record of the defect is
`engineering-docs/bugs/devcapsule/2026-11-10-console-video-opened-from-files-does-not-play.md`.

The extension's button replaces such a tab with a page of the extension that
holds a `<video>` on the same raw address. That page is not under the raw
route's policy, and the host permissions in the manifest make its request
carry the console's token cookie, so the recording plays and seeks.

## When to remove it

The console was fixed on 2026-11-14 (pull request #35, `6ff6bf18` on
`release-0.3.1`): the Files page plays a video or audio file itself at
`/files/<path>`. A console started from an executable built after that commit
needs no extension. `v0.3.1-rc2` and every earlier executable do not have the
fix.

Delete this folder once no console in use predates the fix. Nothing else in
the repository refers to it: it is not part of the launcher, the console or
any build, and no test covers it.

One case outlasts the fix: a raw address opened as a document still does not
play, because the raw route keeps its policy on purpose. On a fixed console,
open the recording from Files instead of installing this.

## Install

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode**.
3. Choose **Load unpacked** and select this folder.

To remove it, choose **Remove** on its card on the same page.

## Use

1. Open the console with its tokened link once in this browser, so the
   browser holds the console's cookie.
2. Open a `.webm` from the console, or paste its raw address.
3. Click the extension's button, *Play this console .webm*.

The tab becomes the player: the file's path, the video, a **Download** link
and a link to the file's **Folder in the console**.

On any other address the button plays nothing. It writes
`[DevCapsule WebM player] pattern not matched: …` to the page's console and
to the extension's service worker log, and shows `no` on the button for a
moment.

## What it accepts

Only an address that is all of:

- `http`, on `127.0.0.1` or `localhost`, any port;
- the path `/api/project/raw`;
- a `path` parameter that ends in `.webm`.

The player rebuilds the address from the origin and that `path` alone, so a
`token` or a `download=1` the address carried does not travel into it.

## Permissions

- `activeTab` and `scripting`: read the clicked tab's address, and write the
  "pattern not matched" line into that tab's console.
- Host access to `http://127.0.0.1/*` and `http://localhost/*`: without it the
  console's `SameSite=Strict` cookie would not accompany the player's request,
  and the console would refuse it.

The extension stores nothing and contacts nothing but the console the tab was
already on.

## Files

- `manifest.json`: the extension's declaration.
- `pattern.js`: the one place that decides what a console recording address
  is; the button and the player both ask it.
- `background.js`: the button.
- `player.html`, `player.css`, `player.js`: the player page.
