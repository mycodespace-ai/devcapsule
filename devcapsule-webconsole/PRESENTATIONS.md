# Presentations: a recorded scenario as slides

A recorded end-to-end scenario leaves a folder: one recording, a screenshot
per action, logs. The presentation page shows such a folder to a person who
wants to follow what happened: an overview slide, then one slide per step of
the scenario's script, each with the step's text, its screenshot and a button
that plays only that step's part of the recording, with captions.

`/presentations/<folder>` presents the project folder `<folder>`, and
`/presentations`, linked from the top band of every page, lists the project's
presentations as cards. The Files page offers the link on any folder that
holds a `presentation.json`.

The page is `static/presentation.html` with `static/presentation.js` and
`static/presentation.css`. It reads `<folder>/presentation.json`, the
recording and the screenshots through `/api/project/raw`, as media of a
console page, so the raw route's policy for opened documents does not apply
to them. It writes nothing.

## Finding the presentations

The content root is the console's **mounted project directory**, not a fixed
presentation asset directory and not the host's whole filesystem. A URL such as
`/presentations/website/_site/assets/presentations/todo-fastapi-postgres-react`
means that exact folder relative to the project root. The website build is one
possible source of content; it is not required for a console presentation.

In this repository the relevant locations are:

| Location relative to the project root | Purpose |
| --- | --- |
| `devcapsule-src/tests/e2e/evidence/<scenario-id>/` | Local recorded runs, ignored by Git and preserved across clean builds. A run subdirectory is also discovered. |
| `devcapsule-webconsole/resources/presentations/` | Retained sample media for developing the console; not bundled in its distribution. |
| `website/_site/assets/presentations/` | Generated website assets, when a website build is present in this checkout. |
| `devcapsule-src/tests/e2e/scripts/` | Authored scenario text; these Markdown files alone are not presentations. |

A recording in another worktree outside the mounted project is not discovered.
Keep its complete presentation folder under this mount to make it available;
linking to an outside directory does not work because discovery and file serving
refuse symbolic links. Git tracking is not required. Writing a valid
`presentation.json` beside the media and reloading **Presentations** is enough:
there is no registration command, website build or console restart to perform.

`GET /api/project/presentations` answers
`{"folders": ["path/of/a/folder", …], "complete": true}`: the folders below
the project root that hold a regular file named `presentation.json`, sorted.
The search (`find_project_folders` in `security.py`) opens each directory by
descriptor from its parent and enters no symbolic link, so it stays inside
the mount. It does not enter a directory whose name starts with a dot or a
`node_modules` directory, and it visits at most 20,000 directories; when it
stops there, `complete` is false and the list page says a presentation may
be missing. The project root itself is not a presentation.

The list page reads and checks each folder's document as the deck would, so
a card states the title, the summary, the number of steps and the length the
document gives, and a folder whose document breaks the contract shows the
refusal in place of a card.

## The folder

| File | What it is |
| --- | --- |
| `presentation.json` | The document below. Its presence makes the folder a presentation. |
| the recording | One video file the browser plays, named by `video.file`. |
| the poster | One image for the overview slide, named by `video.poster`. |
| the screenshots | One image per step, named by each step's `screenshot`. |

Every file name is relative to the folder and stays inside it. A folder may
hold anything else; the page reads only what the document names.

## `presentation.json`

```json
{
  "schema_version": 1,
  "scenario_id": "todo-fastapi-postgres-react",
  "title": "Full-stack work in one capsule",
  "overview": {
    "summary": "What the viewer is about to see.",
    "intent": "Why the scenario exists.",
    "illustrates": ["One thing it shows.", "Another."],
    "stack": [{"name": "Editor", "detail": "VSCodium"}]
  },
  "video": {"file": "scenario-video.webm", "poster": "poster.png", "duration": 39.75},
  "steps": [
    {
      "title": "Open the workspace",
      "action": "What the user does.",
      "expected": "What the viewer should see.",
      "screenshot": "step-004.png",
      "start": 0,
      "end": 2.917,
      "captions": [{"start": 0, "end": 1.25, "text": "Shown while this part plays."}]
    }
  ]
}
```

- `schema_version` is `1`. `title`, `overview.summary`, `video` and at least
  one step are required; `overview.intent`, `overview.illustrates`,
  `overview.stack` and `scenario_id` are optional.
- Times are seconds of the recording. `video.duration` is its length.
- Steps are in order and do not overlap: each starts at or after the end of
  the one before, and none ends after the recording. A step's captions are in
  order, do not overlap, and stay inside the step.
- A text may mark `` `code` ``, `**strong**` and `*emphasis*`. Nothing else is
  interpreted; every text reaches the page as text, never as HTML.

The page checks all of this before it shows anything. A document that breaks
the contract is refused whole, and the page names every breach.

## Where the document comes from

Generation and discovery are separate. The console only reads existing files;
opening **Presentations** does not turn a video into a presentation.

| Recording mode | Generates `presentation.json`? |
| --- | --- |
| Scripted scenario replay with a `script` and numbered actions | Yes, after successful video encoding, from the script and measured frame counts. |
| Replay without a `script` | No; it produces a recording only. |
| Interactive `serve` / `ctl` | No, even when a scenario names a script; this path does not call the presentation producer. |
| Ordinary E2E or IDE smoke run | No general presentation-generation guarantee. |

Use the shared producer instead of assembling the generated JSON by hand.
`devcapsule-src/tests/e2e/scenario_presentation.py` takes the
overview and the steps from the scenario's script, the captions from the
scenario's actions, and the times from the count of frames the recorder had
taken after each action. What a scenario's author provides is described in
[running scenario recordings](../engineering-docs/development/running-e2e-scenario-recordings.md),
section 5. Any other producer may write the document; the contract above is
all the page knows.

An existing interactive recording needs authored step text and retained frame
boundaries before it can be presented. The action log alone has no timestamps.
The [SSH proxy showcase procedure](../engineering-docs/wip/2026-11-16-github-auth/evidence/showcase.md)
gives a concrete producer for the retained run, with chapter timings tied to its
movie checksum. It adds metadata to the original recording without rerunning Git
or changing the movie. This is not automatic interactive-mode support.

## Use in projects other than DevCapsule

The viewer works for any mounted project on a launcher that carries these console
pages. It does not require this repository's layout, Nox sessions or website. Put
the complete media folder and valid `presentation.json` inside that project's
mount and reload **Presentations**. Markdown alone is not a presentation: it still
needs recorded media, screenshots and timings in the generated document.

The launcher also ships the portable authoring kit. The earlier source-only
limitation was closed by the authoring delivery in 0.3.1rc3; the optional agent
skill is added for rc4.

| Support | Delivery |
| --- | --- |
| Console discovery, slides, captions and segment playback | Embedded console bundle. |
| Playwright and its browser runtime | Optional `browser-automation` capability. |
| Agent recording instructions | `devcapsule presentations guide`. |
| Standalone producer, recorder and Python example | `devcapsule presentations export <new-directory>`, under `presentation_tools/`. |
| `devcapsule-recorded-e2e` skill | `SKILL.md` in that export; copy it to the agent's skill directory. No workflow-file update required. |
| Project-specific application setup, actions and assertions | The adopter project's instructions and driver. |
| This repository's IDE harness and replay scenarios | Repository development tooling; not required by the portable kit. |

The exported helpers retain real recording timing and generate the existing
`presentation.json` contract. They do not provision applications or turn every
E2E invocation into a presentation automatically. See the
[installed authoring guide](../devcapsule-src/devcapsule/presentation_tools/README.md)
and [agent invocation](../engineering-docs/development/running-e2e-scenario-recordings.md#6-asking-an-agent-in-another-project).

## What the page does

- **Slides.** The overview, then one per step. The chips at the bottom, the
  arrow keys, Page Up and Page Down, and Home change the slide. The address
  ends in `#<step number>`, so a link opens on a step.
- **Show this step.** Plays the recording from the step's start to its end
  and stops on its last frame. The step's captions are listed under
  *Moments*; the one being played is lit, and selecting one plays from there.
- **Play all.** Plays the recording through. The slide follows the time, and
  the recording waits a moment on each new step so its title can be read.
- **Speed.** Half speed by default, because recordings of scripted actions
  run faster than a person reads; 0.75× and 1× are offered.
- **Space** plays, pauses and resumes. **Larger video** puts the recording
  above the text at the page's full width.

When the recording's own length differs from `video.duration` by more than
half a second, the page says so: a scenario recorded again without a new
`presentation.json` is the likely cause. A recording that does not state its
length cannot be compared.

## Trying a change

From `devcapsule-src`:

```sh
.venv/bin/python -m nox -s webconsole-preview
```

serves this checkout's console on `http://127.0.0.1:8787` and prints two
links carrying a token made for the run: the console's home, and the sample
presentation. The console is installed editable, so an edit to a page, a
script or a stylesheet shows on a browser reload; an edit to the Python
needs the command run again. `-- --port <n>` chooses another port and
`-- --project <path>` another DevCapsule project. Ctrl+C ends it.

The sample is `resources/presentations/todo-fastapi-postgres-react/`: the
recording, the poster and seven screenshots of the 2026-11-13 run of the
`todo-fastapi-postgres-react` scenario, with the `presentation.json` that
`scenario_presentation.py` makes from the scenario, its script and that
run's frame counts. It is the folder to open when changing the page. The
resources are not part of the distribution.
