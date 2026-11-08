# Implementor brief for the Antigravity + Gemini 4 Argon (High) pair: the web console's Files page, slice 2 of release 0.3.1

The product owner ordered this slice on 2026-11-08 for release 0.3.1 and
named the pairs: you implement, the Claude Code + Claude Fable 5.1 pair
reviews (Pair Review Loop, `WORKFLOW.md` topic 9.11, applied by
`WORKFLOW-LOCAL.md` *Pair Review Loop In This Checkout*). You build one
slice on one branch and open its pull request, PRn, against
`release-0.3.1`. The reviewer then opens PRn.1 against your branch; you
read its diff, post the assessment comment and merge it or push back, at
most three rounds. This brief is your only instruction. Where it decides,
take the decision as made; where it is silent, choose the simplest thing
that keeps the console's existing rules, and list the choice in the pull
request body under *Judgments*.

## Your checkout

You are in the git worktree at `/home/costin/worktrees/maintenance-files-page`
(also reachable as `~/worktrees/maintenance-files-page`), on the branch
`ws-maintenance/console-files-page`, created from `origin/release-0.3.1`.
Work only there. Do not touch the main checkout at
`/workspace/301e4208ef81-ChatGPT_Codex`, any other worktree under
`~/worktrees`, the status files, or published state.

Read first, in this order: `AGENTS.md`, `WORKFLOW.md`, `WORKFLOW-LOCAL.md`
(in full, including *Unit Tests*, *Commit Authorship*, *GitHub Integration*
and *Pair Review Loop In This Checkout*), `devcapsule-webconsole/README.md`
(its *Boundaries* are binding), `devcapsule-webconsole/devcapsule_webconsole/app.py`,
`devcapsule-webconsole/devcapsule_webconsole/security.py`,
`devcapsule-webconsole/devcapsule_webconsole/static/console.js` (the
records page, `pages.records`, is the pattern to follow),
`devcapsule-webconsole/devcapsule_webconsole/static/records.html`,
`devcapsule-webconsole/tests/conftest.py`, `tests/test_records.py`,
`tests/test_security.py`, `tests/decisions-script.cjs` with the test that
runs it in `tests/test_decisions.py`, and `docs/sessions/web-console.md`.

## GitHub CLI

In every shell you run, first execute:

    . /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh

Then `gh` is logged in to github.com as the owner's account against
`mycodespace-ai/devcapsule`. Do not edit `.bashrc` or any shell profile.

## Validation environment

Your worktree's `devcapsule-src/.venv` exists, built as *Validation
Commands* say. Run everything from `devcapsule-src` with
`PYTEST_ADDOPTS="--basetemp=/opt/devcapsule-gate/pytest-antigravity"`:

    .venv/bin/python -m nox -s webconsole     # the console: mypy --strict and its tests
    .venv/bin/python -m nox -s tests          # the runtime's unit session and the conventions gate
    .venv/bin/python -m nox -s typecheck
    .venv/bin/python -m nox -s build          # the full gate, before your final push

Run them in the foreground and wait. Do not build images, start capsules
or run the e2e suites. The console is a separate distribution with its own
hash-pinned dependencies: add no dependency, Python or JavaScript. No
build step, no Node in the capsule; Node is used only by the existing page
tests when present on the machine.

## The slice

A developer opens the console and browses the project's files as they
are, directory by directory, and opens or downloads any file with the
right media type, so a link such as
`/files/engineering-docs/blog/assets/2026-10-21-eclipse-debug/eclipse-hello-time-debug.webm`
can be pasted in chat and plays in the browser. No frills: a listing
table, breadcrumbs, view and download links. No tree widget, no library,
no editing, no upload, no delete, no search.

### 1. The listing API

`GET /api/project/tree?path=<relative directory>`; an empty or absent
`path` is the project root. The response is JSON:

```json
{"path": "docs", "entries": [
  {"name": "assets", "kind": "directory", "size": null, "modified": "2026-11-08T10:11:12Z"},
  {"name": "guide.md", "kind": "file", "size": 1234, "modified": "2026-11-08T10:11:12Z"},
  {"name": "escape.md", "kind": "link", "size": null, "modified": "2026-11-08T10:11:12Z"}
]}
```

Rules:

- Directories first, then files, each group sorted by `name.casefold()`.
  Every entry is listed, dotfiles and `.git` included: the files as they
  are.
- `kind` is `directory`, `file`, `link` for a symbolic link of any target,
  `other` for anything else (a FIFO, a socket, a device). The listing does
  not follow links: use `lstat`. `size` is the byte size of a `file`,
  `null` otherwise. `modified` is the entry's mtime in UTC, ISO 8601 with a
  `Z`.
- Confinement is the existing one, extended: the directory is named
  through `confine`, then opened the way `read_project_bytes` opens, by
  descriptor from the root with `O_DIRECTORY | O_NOFOLLOW` at each step,
  and scanned with `os.scandir` on that descriptor, so a directory
  replaced by a link mid-request is refused. Put this in `security.py`
  beside `read_project_bytes`, as a public operation named in the module's
  `__all__` or docstring (*Unit Tests* rule 4), returning plain data the
  route serializes.
- Responses: `403` with the existing `PathRefused` text for an escape, `404`
  for a path that does not exist or is not a directory, `403` for another
  `OSError`, as the raw route does. The token gate covers it like every
  route.

### 2. The page

`GET /files` and `GET /files/{path:path}` serve one static page,
`files.html`, with `data-page="files"`; the script reads the directory
from the URL, as `pages.records` does. `GET /filetree` and
`GET /filetree/{path:path}` redirect (307) to the `/files` form, so both
names the owner used work.

The page shows, in the console's existing markup and stylesheet:

- Breadcrumbs: the project root as a link to `/files`, then each directory
  of the path as a link to its `/files/...` URL.
- A table with columns Name, Size, Modified. A directory's name links to
  its `/files/...` page. A file's name links to its view URL: a `.md`
  file to `/records/<path>`, every other file to
  `/api/project/raw?path=<encoded path>`. Each file row also has a
  `download` link, the raw URL with `&download=1`. A `link` entry's name
  links to the raw URL, which already refuses an escaping target; an
  `other` entry is shown without a link. Sizes in human units (B, KiB,
  MiB, GiB with one decimal). An empty directory says so.
- The page title and the `<h1>` name the directory. Errors go through the
  existing `fail` helper.

Add `<a href="/files">Files</a>` after Records in the navigation of every
page, the new one included. Add the route to `PAGES` and the pattern route
for the path, as `/records/{record:path}` is added.

### 3. The raw route, hardened for media and downloads

`/api/project/raw` keeps its confinement, its CSP sandbox and `nosniff`
headers and its media-type rules, and gains:

- **Range requests**, so a video player can seek and a large file is not
  read whole for every request: honour a single `bytes=` range (first-last,
  first-, -suffix), answer `206` with `Content-Range` and `Content-Length`,
  `416` with `Content-Range: bytes */<size>` when unsatisfiable, always
  send `Accept-Ranges: bytes`, and stream the body from the descriptor the
  safe open returns, in chunks, instead of reading all bytes into memory.
  Multiple ranges are answered as the full `200` body. Keep
  `read_project_bytes` for the callers that want bytes; give the route a
  sibling operation that opens the file the same safe way and yields it.
- **`download=1`** as a query parameter: adds
  `Content-Disposition: attachment; filename*=UTF-8''<percent-encoded basename>`
  (and a plain `filename=` fallback with non-ASCII replaced). Without it,
  nothing changes.
- **Media types** for well-known extensions, added to `RAW_CONTENT_TYPES`
  and tested: `.webm` `video/webm`, `.mp4` `video/mp4`, `.mkv`
  `video/x-matroska`, `.mp3` `audio/mpeg`, `.ogg` `audio/ogg`, `.wav`
  `audio/wav`, `.pdf` `application/pdf`, `.webp` `image/webp`, `.gif`,
  `.png`, `.jpg`/`.jpeg` their image types, `.yaml`/`.yml`, `.lock`,
  `.cfg`, `.ini`, `.py`, `.js`, `.mjs`, `.cjs`, `.css`, `.sh`, `.csv`,
  `.log`, `.xml` as `text/plain; charset=utf-8`. The existing rules stand:
  HTML is never served as HTML, SVG keeps its image type under the sandbox,
  unknown is `application/octet-stream`. Check which of these
  `mimetypes.guess_type` already gives and keep the table to what the
  function would otherwise get wrong, with one test per listed extension.

### 4. Documentation

- `docs/sessions/web-console.md`: "seven pages" becomes eight; a **Files**
  bullet in *What is on each page*, in the voice of the others, stating
  that every file of the mounted project is listed and served read-only
  with its media type, that videos and images open in the browser, and
  that `/files/<path>` links can be shared with anyone who has the console
  link; the `updated:` front-matter date becomes `2026-11-08`.
- `devcapsule-webconsole/README.md` *Boundaries*: one sentence on the
  listing (same confinement, nothing hidden, nothing followed) and one on
  the raw route's ranges and download disposition.

### 5. Tests

New tests go in new modules in `devcapsule-webconsole/tests/`:
`test_files_page.py` for the listing operation, the tree route, the Range
and download behaviour and the media types, and `files-script.cjs` for
the page, run from Python the way `test_decisions.py` runs
`decisions-script.cjs` and skipped when Node is absent. Add the new
routes to the parametrized token-gate test in `test_security.py`; change
nothing else in existing test modules.

Every test follows *Unit Tests* rules 1 to 3: it builds its own tree under
`tmp_path` (the `project` fixture is the start; extend it in your module,
not in `conftest.py`), calls one public operation or one route, asserts a
promised postcondition, and has a docstring stating the contract under
test. No release identifiers or digests as assertions. Cover at least:
root and nested listings; ordering; `kind` for a directory, a file, a
link, a FIFO; dotfiles listed; `..`, an absolute path, a link that leaves
the project and a path to a file all refused or not found with the right
status; a directory swapped for a link between confinement and open
(monkeypatch the open, or create the race deterministically) refused; a
full read, a first-last range, an open-ended range, a suffix range, an
unsatisfiable range, a multi-range fallback, the `Accept-Ranges` header on
`200` and `206`; the sandbox and `nosniff` headers still present on `206`
and `416`; `download=1` with an ASCII and a non-ASCII name; each media
type in the table; the page routes serve `files.html` and the redirects
land on `/files`. Every test must fail if the line it covers is broken.
Do not pad.

## What you must not do

- Do not change `eclipse_native_pin.py`, `linux_arm64_pins.py`,
  `resolution_matrix.py`, the golden locks, the version files, or anything
  under `engineering-docs/releases/`: the release records are the
  reviewer's and the owner's.
- Do not merge, rebase or force-push. Do not open the PR against `main`:
  its base is `release-0.3.1`.
- Do not add a dependency, a build step or a vendored library.
- Do not widen the slice: no editing, upload, delete, search, tree widget,
  thumbnails, syntax highlighting, or directory download.
- Do not commit `.devcapsule/devcapsule.toml`, `.devcapsule/*.lock`, or
  anything under `.idea/`. Stage files by name; never `git add -A` or
  `commit -a`. If `git status` shows ` M website`, do not stage it.

## Commit authorship

Before committing, run `git var GIT_AUTHOR_IDENT`; it must be the owner's
identity, Costin Cozianu. Each commit ends with the trailer

    Co-Authored-By: Gemini 4 Argon (High) Antigravity <noreply@google.com>

Commit in sensible steps (the listing operation and its tests; the route
and the page; the raw route's ranges and download; the media types; the
documentation), each message saying what and why in plain English.

## Delivery

1. Run the four validation commands above; `nox -s build` last, after the
   final change.
2. Push: `git push -u origin ws-maintenance/console-files-page`.
3. Open the pull request:

       gh pr create -R mycodespace-ai/devcapsule --base release-0.3.1 --head ws-maintenance/console-files-page --title "Web console: a Files page that lists and serves the project's files" --body-file <your body file>

   The body states: what changed, with the routes and files; the
   judgments you took for the human's review; the validation with its
   counts (console tests, mypy files, unit tests, the conventions gate's
   summary line, the build gate's result) and its limits (no capsule run);
   a paragraph headed *Coverage* that says which new lines are covered by
   which tests and what is not covered and why. Name your pair in the
   body as this brief's title does.
4. Print, as your last line, exactly:

       IMPLEMENTOR DONE: <the pull request URL>

   If you stop on a blocker instead (credentials, network, a gate you
   cannot make pass), print `IMPLEMENTOR BLOCKED: <one line>` as your last
   line and nothing after it. Do not work around a blocker.

## After the review

The reviewer's PRn.1 arrives as a pull request against your branch, named
`ws-maintenance/console-files-page-review`. A round brief will reach you
through the same channel as this brief. Until then, your job ends at
`IMPLEMENTOR DONE`.
