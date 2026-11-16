---
status: fixed
severity: untriaged
target: 0.3.1
owner: maintenance
opened: 2026-11-10
requirements: []
---

# A video opened from the web console's Files page does not play: the raw route's policy blocks the browser's own player

## Symptom and expected behavior

Opening a `.webm` file from the web console's Files page in Chrome shows a
video player with a play button and a length of `0:00`. Pressing play does
nothing. The browser console reports:

```text
Loading media from 'http://127.0.0.1:40441/api/project/raw?path=engineering-docs%2Fblog%2Fassets%2F2026-10-04-intellij%2Ffirst-session.webm'
violates the following Content Security Policy directive: "default-src 'none'".
Note that 'media-src' was not explicitly set, so 'default-src' is used as a
fallback. The action has been blocked.
```

By the owner's report, most other files open from the same page without a
problem.

Expected: the video plays and seeks. This is promised behavior, not a wish:

- `docs/sessions/web-console.md`, the **Files** bullet: "Videos, audio,
  PDFs, images, and plain-text source or configuration files open in the
  browser".
- `engineering-docs/releases/v0.3.1/changelog.md`: "a recording or an image
  opens in the browser" and "The raw route seeks by byte range, so long
  videos play from any point."
- The slice's brief,
  `engineering-docs/wip/2026-09-18-maintenance/evidence/2026-11-08-console-files-page/implementor-brief.md`:
  a `/files/<path>.webm` link "can be pasted in chat and plays in the
  browser".

No requirement ID covers the Files page; `R-CONSOLE-001` speaks of the
console and its records only, so `requirements` is empty.

## Environment and evidence

Observed by the owner on 2026-11-10, in Chrome on the host, against the
console of this project's capsule started with the `v0.3.1-rc2` executable
(`be0140ca`). The Chrome version was not recorded. The file is
`engineering-docs/blog/assets/2026-10-04-intellij/first-session.webm`,
10,522,080 bytes.

Read on `main` at `aabace3c`; `devcapsule-webconsole/` is identical on
`release-0.3.1`:

- `devcapsule_webconsole/app.py`, `RAW_SECURITY_HEADERS`: every response of
  `/api/project/raw` carries
  `Content-Security-Policy: sandbox; default-src 'none'; style-src 'unsafe-inline'`.
- `devcapsule_webconsole/static/console.js`, `fileViewUrl`: a file that is
  not Markdown is linked to `/api/project/raw?path=…`. The Files listing
  uses it for every file row, and `pages.files` uses it to redirect a
  `/files/<file>` address, so a pasted link fails the same way.
- The same file, `recordUrl`: a Markdown link in Records to a project file
  that is not Markdown also resolves to the raw route.
- `tests/test_files_page.py`,
  `test_raw_route_serves_full_file_in_chunks_with_accept_ranges`, asserts
  this exact policy on a `.webm` response, and `tests/files-script.cjs`
  asserts that `/files/docs/demo.webm` redirects to the raw route. Both
  pass. They check headers and addresses; nothing observes a browser
  playing the file.

One experiment separates the causes. On the console's `/files` page, with
the same session, this line was pasted into the browser's console:

```js
document.body.appendChild(Object.assign(document.createElement('video'), {controls: true, src: '/api/project/raw?path=engineering-docs%2Fblog%2Fassets%2F2026-10-04-intellij%2Ffirst-session.webm'}))
```

The player appeared below the listing and the video played. The same line
pasted while the raw address was the open document reproduced the policy
error. So the file, the route's streaming and the token are sound when a
console page embeds the raw address; the failure belongs to the raw
response opened as a document.

## Cause

When the browser navigates to a `video/webm` response, Chrome does not
render the response body. It builds a small document of its own that holds
a `<video>` element pointing back at the same address, and the element
fetches the file again. That document inherits the response's
`Content-Security-Policy`. The policy has no `media-src`, so
`default-src 'none'` governs media, and the element's fetch is refused.

Text and images are drawn from the navigation response itself and make no
second fetch, which agrees with the report that other files open. Which
file types the owner opened was not recorded.

The policy is right for what it was written for: an SVG or any other
active document opened from the raw route must not run code or reach the
console's origin. It was not written with the browser's media document in
mind, and the tests could not show the gap because they stop at the
headers.

## Proposed fix

The Files page plays video and audio itself, and the raw route stays as it
is.

- `/files/<path>` for a video or audio file renders, in the console's own
  page, the breadcrumbs, a `<video controls>` or `<audio controls>` whose
  source is the raw address, and the download link. It no longer redirects
  to the raw route for those files.
- `fileViewUrl` gives `/files/<path>` for a video or audio file, so the
  listing rows lead there. `recordUrl` does the same, so a link in a
  Markdown record to a recording plays too.
- `/api/project/raw` is unchanged: the policy, `sandbox`, `nosniff`, the
  byte ranges and the download disposition all stay. A raw response
  fetched as media by a console page is not a document, so its policy does
  not apply; the console page is same-origin, so the token cookie travels.
  This is the arrangement the experiment above exercised.
- Which files are video or audio has one owner today, `raw_content_type`
  in `app.py`. The page should learn the answer from the server rather
  than keep a second extension table in JavaScript, where a mismatch would
  either leave a type on the broken path or wrap a player around a file
  that is not media. One way: each file entry of `/api/project/tree`
  carries its media type, and for a `/files/<file>` address the page reads
  the entry from the parent directory's listing.

Tests, each constructing its own input:

- `tests/files-script.cjs`: `/files/docs/demo.webm` renders a `video`
  element whose `src` is the raw address and replaces no location; the
  listing row of a video links to `/files/…`; a file that is neither video
  nor audio still redirects to the raw route. The present assertion that
  the video address redirects to raw encodes the defect and changes.
- The same for an audio file and for a Markdown link to a recording in
  Records.
- `tests/test_files_page.py`: the tree entry's media type, if that is the
  means chosen.

The raw route's header tests stay as they are.

### Alternative considered, not proposed

Serve `video/*` and `audio/*` from the raw route with a policy that allows
`media-src 'self'`. It is the smaller change, and it is unverified in two
places. Under `sandbox` the browser's media document has an opaque origin,
and the token cookie is `SameSite=Strict` (`security.py`,
`_setting_cookie`), so the player's request would probably arrive without
the token and be refused. Removing `sandbox` for those types avoids that
and gives up, for them, the isolation the Files slice kept on purpose.
Neither variant was tried in a browser.

## Fixed on the branch, 2026-11-14

The human asked the web console pair for the fix in session. It is on
`ws-capsule-webconsole/video-in-files`, cut from `release-0.3.1` at
`27985163`, and follows the proposal above; `target` is set from that
branch's base. `severity` is still the owner's to rate, and `owner` is
unchanged: closing needs the observation below on a built executable.

- `/api/project/tree` gives each regular file's entry a `type`, the media
  type `raw_content_type` serves the file as; other entries have `null`.
- `/files/<path>` for a file whose type is `video/…` or `audio/…` shows the
  breadcrumbs, the player and the download link in the console's page. The
  page reads the type from the listing of the file's directory. Any other
  file leaves for the raw route as before, or for Records when Markdown, and
  now keeps the address's fragment.
- A listing row links a video or audio file to `/files/<path>`.
- A link in a Markdown record to a file that is not Markdown leads to
  `/files/<path>`, not to the raw route. This is wider than "a link to a
  recording": a record's renderer cannot ask the server for each target's
  type, so every such link takes the Files address, which plays a recording
  and sends anything else on to the raw route after two small requests.
  Images embedded in a record still load from the raw route directly.
- `/api/project/raw` is unchanged.

Not covered: a symbolic link to a recording. A link's row still leads to
the raw route, and a link has no `type`.

Checked on the branch: `nox -s webconsole`, whose tests now assert the tree
entry's type against the raw route's `Content-Type`, the player for a video
and for an audio address, the listing rows, the unchanged redirect of other
files and the record link. In headless Chromium against
`nox -s webconsole-preview`: a `.webm` opened from the listing played,
played on from a position set at 25 s, and loaded from its pasted
`/files/…` address in a second tab; the browser console showed no
`Content Security Policy` message; a JSON file still went to the raw route
and a raw range request still carried the policy unchanged. This is not
the close criterion: that asks for Chrome and an executable that carries
the fix. Audio was not played in a browser.

## Not verified

- **Audio.** The mechanism is the same and the failure is expected; it was
  not observed.
- **PDF.** The user documentation promises that PDFs open in the browser.
  Whether Chrome's PDF viewer loads under the raw route's `sandbox` was
  not checked. Opening one PDF from `/files` answers it; if it fails, it
  is a second defect of the same route with a different fix, and this
  record should say so or a second record should be filed.
- **Other browsers.** Only Chrome was observed.

## Verification target and close criteria

A browser observation is part of closing this record, since the automated
tests passed while the defect shipped. On an executable that carries the
fix, in Chrome, with the console of a running capsule:

1. Open a video from the Files listing: it plays, and dragging the
   position plays from the new point.
2. Paste the `/files/<path>.webm` address into a new tab of the same
   session: it plays.
3. The browser console shows no `Content Security Policy` message for
   either.
4. Open a raw SVG and a raw text file: both still carry the unchanged
   policy.

Reopen if a later change to the raw route's headers or to `fileViewUrl`
sends video or audio back to the raw address as a document.

## Disposition

Filed 2026-11-10 from the `project-management` checkout at the owner's
direction, after the owner reported the symptom and ran the experiment
above. Delivered to `maintenance` by mail the same day, with this record in
full, because the Files page ships in `v0.3.1-rc2` and the filing branch
is not near integration. Severity and target are the owner workstream's
and the human's to set; nothing here assigns them.
