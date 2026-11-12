# Design: project capabilities, settled and unsettled

Date: 2026-11-03. Status: for the owner's ruling; it answers amendment 7 of
[the work order](../../work-orders/2026-11-02-wrapped-projects.md) and the
Socratic exchange of 2026-11-02. Each section ends with the recommendation
and, where one exists, the alternative in a line. The four questions put to
the owner are answered here as recommendations, marked **Q1** to **Q4**.

## 1. The floor and the ceiling

At the minimum DevCapsule is a reproducible room: a base image, components,
possibly none, the source tree mounted, a persistent home, explicit host
boundaries, and something running inside, IntelliJ or vim or a shell. The
minimum promises the room and nothing about what happens in it. Nothing
below may make the vim case need one more declaration.

At the maximum DevCapsule is a complete description of how work happens in a
project, such that a newcomer, human or agent, is productive on the first run
without asking anyone. Between the two lie layers, each optional:

1. what is installed: components, versions, the lock; done;
2. how the project is operated: build, test, debug, browse, manage; this note;
3. how humans and agents work here: the workflow definition, records,
   decisions, the console hand-off; partly built;
4. how capsules relate: wrappers, samples, the recursive dogfood; begun.

## 2. Two kinds of capability, one word or two (Q1)

A capability today names a tool the capsule must have: `java`, `node`,
`codex-agent`. What amendment 7 names is something the project can be made
to do, with the recipe and the environment it needs. The two relate: the
second needs the first and names it.

Recommendation: keep the owner's word in prose, *a higher-level capability*,
and give it its own table and verb so no command is ambiguous: `[operations]`
in the manifest, `project operation` on the command line. A developer who
types `config require build` must get a clear refusal, not a tool named
`build`. Alternative: `[capabilities.project]` under the tools; rejected
because `capabilities.required` already means tools and the two would be
read together by every older launcher.

## 3. The minimal set

The owner's list, in the owner's order, and nothing added:

| Operation | Settled means |
|---|---|
| `browse` | the code opens navigably in the IDE; for Gradle, the import happened; for vim, nothing to settle |
| `build` | the software builds, in the broad sense that covers packaging an interpreted project |
| `test` | the tests run, or the project says it has none, by choice |
| `debug` | a process, or a test, starts under the debugger |
| `manage` | how development is managed: branches, pull requests, validation |

Every operation is either settled or unsettled. Unsettled is not an error. A
project may start with `browse` alone, an old project without today's
tooling, and the status says so: *we can browse the code but cannot build
yet*. That sentence is the agent's standing task, taken up with the user.

## 4. The record

One table per operation, per project, or per wrapped source when the project
wraps several:

```toml
[operations.build]
command = "./gradlew build -x spotlessCheck"
directory = "."
environment = { JAVA_HOME = "/opt/java/17", PATH = "/opt/java/17/bin:$PATH" }
needs = ["java"]
settled = 2026-11-02
proved-at = "3ea1eb0"

[sources."RobotCode2025Public".operations.test]
command = "./gradlew test"
needs = ["java"]
settled = 2026-11-02
proved-at = "3ea1eb0"
```

- `command`, `directory` (relative to the source, `.` by default) and
  `environment` are the recipe. `needs` names the tool capabilities, which
  must be required or offered by the project; the launcher refuses a recipe
  whose needs the project does not declare.
- `settled` is the date the human accepted it, after a run that proved it;
  `proved-at` is the source's revision at that run. An entry without
  `settled` does not exist: a proposal lives in the dialogue, never in the
  manifest, so the manifest never carries a guess (the lesson of the deleted
  detection).
- **Q4**: keep the date and the revision, not the log. The run is
  reproducible by the recipe itself; a log would rot and bloat the manifest.
- The `java` key on a source, invented in slice 1, becomes the build's
  `environment` and is removed from `[sources]` before any release ships it.
- Unknown keys inside an entry are carried, as everywhere in schema 2.

Recommendation: this shape. Alternative: one table of named commands without
state; rejected because the state is the whole point.

## 5. What the status surfaces

- `project info` and `config show` list every operation of every source with
  `settled <date>` or `unsettled`, and one line of summary: *browse settled,
  build unsettled, test unsettled*.
- The generated `AGENTS.md` carries a section *Unsettled* naming each one
  and the standing instruction: find out with the user, from the source's
  own files and the owner's notes, propose with evidence, settle only through
  the command, write nothing into the source.
- The console shows the same list; a settlement is a decision it can hand
  off.

## 6. The commands

```text
devcapsule project operation list [--source NAME]
devcapsule project operation settle NAME [--source NAME] --command CMD [--directory DIR] [--env VAR=VALUE]... [--needs CAPABILITY]... [--proved-at REVISION]
devcapsule project operation forget NAME [--source NAME]
devcapsule project operation run NAME [--source NAME]
```

`settle` writes the record through the one manifest writer after the
human's acceptance; the agent runs it when the human says yes, or the human
runs it. `run` executes the recipe inside the capsule with its environment,
so the human and the agent use one command and the proof is reproducible.
`run` is the only operation command the capsule runtime needs; the others
are owner commands.

## 7. The discovery dialogue, the wrap workflow

The first session of a wrapper, as the guidance directs it:

1. The agent reads `AGENTS.md`: the sources, the unsettled operations, the
   owner's notes.
2. For `build` first, it reads the source's own files, tries the build in a
   scratch of the capsule, and brings the human the recipe with the run's
   result, as a decision hand-off when the console is there, in chat
   otherwise.
3. The human accepts, corrects or defers. Acceptance is the `settle` command.
4. Then `test`, `debug`, `browse`, `manage`, in whatever order the human
   wants, or not at all. Deferred stays unsettled and visible.

The owner's notes are the *extra instructions outside the source tree* of the
amendment: a section of the generated `AGENTS.md` between two markers that
regeneration preserves, so a human can write "the simulation needs a
display; skip it" once and every agent reads it. Alternative: a separate
notes file; rejected because the agent reads one file first and the notes
belong beside the rules.

## 8. Browse and manage (Q2, Q3)

**Q2**: `browse` belongs to the project. The project says what to import
(`[sources."X".operations.browse] gradle = "."`); the IDE component consumes
it, IntelliJ by linking the Gradle project, vim by ignoring it. Nothing is
written into the foreign tree.

**Q3**: `manage` is the workflow definition where there is one, the
`[workflow]` table, and otherwise the project's own stated conventions: a
settled `manage` names the branch model, where pull requests go (the fork
rule of `[sources]` is part of it) and the validation command. For a learning
wrapper it is settled as *learn only; no branches, no pull requests*, which
is a legitimate answer, not an absence.

## 9. Slices

1. **The record and the commands.** `[operations]` read, written, listed;
   `operation settle`, `forget`, `list`, `run`; the status surfaces; the
   guidance's *Unsettled* section and the owner's notes; the `java` key
   folded into `build`'s environment. No base change.
2. **The dialogue.** The console's decision hand-off for a settlement; the
   first-session instruction in the guidance proven on the showcase inside a
   capsule.
3. **The base and browse.** Temurin 17 under the stable names, the session
   environment from the settled operations, the IntelliJ link; the former
   slice 2, unchanged in substance.

Each slice is one pull request with its Codex review. Slice 1 starts after
this note is ruled.
