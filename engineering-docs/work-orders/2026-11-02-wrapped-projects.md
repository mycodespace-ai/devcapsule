# Work Order: Wrapped Projects

Origin: product-owner direction, 2026-11-02, after a conversation at an AI expo with a
high-school FIRST Robotics team whose Java robot code is private on GitHub.
Status: accepted the same day by the `wrapped-projects` workstream, which this order opens.
Coordination owner: `project-management`. Implementation owner: `wrapped-projects`.
Release target: the next minor after 0.3.0, to be fixed by the owner at the first stopping point.
Requirements: R-CONFIG-001 (the manifest) and R-SCOPE-001 (what is shared with the capsule);
a new requirement for the wrapped-project shape is a deliverable of this order.

## Outcome

A developer can give DevCapsule a repository that is not theirs and does not carry a DevCapsule
configuration, and work on it inside a capsule: browse it in the IDE, build it, run its tests,
debug it, and let a coding agent do the same. Nothing is imposed on the foreign repository. The
DevCapsule configuration lives in a small wrapper repository of the developer's own, and the
foreign code is a Git submodule of that wrapper.

The three commands the developer types, in an empty directory:

```bash
git init
devcapsule project wrap https://github.com/Mechanical-Advantage/RobotCode2025Public
devcapsule project run
```

`wrap` adds the repository as a submodule, looks at what it finds there, writes the manifest
and the lock, and writes the guidance an agent needs. `run` opens the capsule with the IDE on
the foreign code. `wrap` is repeatable: a wrapper may hold several foreign repositories.
The developer never writes TOML.

The showcase, and the first acceptance target, is an FRC learning project: a wrapper around
FRC team 6328 Mechanical-Advantage's public robot code, Java built with Gradle and WPILib's
GradleRIO plugin, MIT licensed. A team that keeps its own code private can use that wrapper to
learn from the best team's code in an afternoon instead of following installation instructions.

The showcase wrapper has its own repository, created by the owner on 2026-11-02 and kept
under the personal account: `git@github.com:ccozianu/devcapsule-sample-frc-learning.git`.
The wrapper produced by the three commands is pushed there. It does not join this repository
as a submodule: the owner ruled on 2026-11-05 that the sample projects leave the repository,
and that which samples users get to try, and in what form, is decided later.

The second audience is anyone who wants to read, build or debug an open-source project whose
development setup is a chore, and the maintainer who receives a message saying: instead of an
afternoon of setup, `devcapsule project run`.

## Decisions already taken

The owner ruled these on 2026-11-02.

1. **A wrapper is an ordinary project.** There is no new project kind. The manifest of a wrapper
   is a schema-2 manifest that additionally names its wrapped sources. The owner's standing rule
   applies: an unjustified concept is deleted outright, never replaced by a smaller one.
2. **Several JDKs live in the base image.** Temurin 25 stays the default under `/opt/java/current`
   and on `PATH`. The base additionally carries a Temurin 17 under `/opt/java/jdk-17...`. A wrapped
   source names the JDK line it builds with, and that selection reaches the IDE, the terminal and
   the agent: either `JAVA_HOME` and `PATH` set for the whole capsule when every wrapped source
   agrees, or set just in time by the instruction the agent reads when it works in that source.
   The owner's view: current agents follow such an instruction reliably, so the instruction is
   an acceptable first delivery and the global setting is the refinement.
3. **The foreign repository is never edited through the wrapper's upstream pointer.** When the
   developer intends to change the code, the submodule points at a fork they control; when they
   only learn, it may point at the upstream. `wrap` takes the URL it is given and records which
   case this is. Pull requests go to the fork, never unsolicited to the upstream.
4. **One concrete use case first.** The FRC wrapper is the acceptance target. The general case is
   designed so that it works, but nothing is built that the showcase does not exercise.
5. **The pair.** Claude (Fable 5.1) designs and implements; Codex is the review partner under the
   Pair Review Loop as the local workflow file applies it.

Amended by the owner on 2026-11-02, in chat, after reading slice 1:

6. **The launcher infers nothing from a foreign tree.** Detecting Gradle, or any build tool, special-cases
   one ecosystem into the product and bakes in facts about someone else's tool that rot. `wrap`
   takes what the developer names, `--require CAPABILITY` and `--java LINE`, and declares that. Item 2
   of the `project wrap` deliverable and the showcase's detection table are superseded; the showcase
   command is `wrap <url> --require java --java 17`.
7. **Higher-level project capabilities are the next design.** A project, wrapped or not, can be made
   to do things: browse, build, test, debug, manage its development. Each is settled or unsettled; an
   unsettled one is not an error but a standing task the status surfaces ("we can browse the code
   but cannot build yet") and the agent takes up with the user. The `java` line of a source is an
   early form of the build's environment. A design note on this precedes any further slice.

## Deliverables

### The wrapped-source declaration

The manifest names each wrapped source: its path in the wrapper, its origin URL, whether that
origin is an upstream or the developer's fork, and the toolchain it builds with, the JDK line
for a Java source. Older launchers must still read a wrapper's manifest; schema 2 tolerates
unknown root tables, and the declaration must stay within that tolerance or come with a schema
change the owner has ruled on. The exact table and keys are the workstream's to choose and to
record in R-CONFIG-001.

Done means a manifest with the declaration round-trips through every command that rewrites the
manifest without losing it, and `project config show` reports it.

### `project wrap`

`devcapsule project wrap URL [--path NAME] [--fork]` in a Git repository:

1. Adds the repository as a submodule at the path, the repository's name by default, with the
   embedded Git directory the capsule needs, so the submodule works from inside the capsule on
   the first run.
2. Superseded by amendment 6: requires the capabilities the developer names and declares the Java
   line the developer gives; infers nothing from the source.
3. Writes or extends the manifest and lock as `init` would: the required capabilities, the
   recommended IDE, the wrapped-source declaration. A second `wrap` adds a source to an existing
   manifest and reconciles the capabilities.
4. Writes the wrapper's `AGENTS.md` and `README.md` when absent: what this wrapper is, which
   directories are foreign and under whose control, how to build, test and run each, which JDK
   each uses and how to select it, and where changes go. The files are portable, in the owner's
   words agent-neutral; nothing is written for one agent product.
5. Does not install the project workflow. `project bootstrap` stays available for a wrapper
   whose owner wants it.

Done means the three commands above, in an empty directory on a machine with DevCapsule
installed, produce a wrapper whose next `run` opens the capsule; and the wrapper repository
contains only `.devcapsule/`, `.gitmodules`, the submodule, `AGENTS.md` and `README.md`.

### The capsule's behaviour on a wrapper

1. The IDE opens on the foreign code. With one wrapped source, IntelliJ opens that source as
   the project so the Gradle import happens. With several, the behaviour is the workstream's
   choice, backed by evidence from a real launch, and recorded.
2. The JDK selection reaches the build. Inside the capsule, the source's Gradle wrapper builds
   with the declared JDK whether the developer types the command in the IDE terminal or an agent
   runs it from the instruction.
3. The base image carries the JDK lines the catalog lists, Temurin 17 and 25 at delivery, under
   `/opt/java/`, with 25 current. Adding a line is a catalog change, not a design change.

Done means the acceptance evidence below.

### Documentation and records

A page under `docs/your-project/`, *Someone else's repository*, with the three commands, what
`wrap` writes, the fork rule and the JDK rule; the CLI reference updated; a requirement for the
wrapped-project shape under `engineering-docs/requirements/product/`; R-CONFIG-001 extended for
the declaration; the release notes entry. Nothing is advertised before it runs.

## Acceptance evidence

On the built executable, from an empty directory, with the showcase repository:

1. The three commands run without prompts beyond those `init` and `run` already ask.
2. Inside the capsule, `./gradlew build -x spotlessCheck` in the wrapped source succeeds with
   the declared JDK, from the IDE terminal and from an agent told only to build the project.
3. IntelliJ opens with the robot code imported as a Gradle project and navigable.
4. The wrapper repository holds nothing but the files named above; the foreign repository's
   working tree is clean after the launch.
5. A second `wrap` of another Mechanical-Advantage Java repository into the same wrapper
   leaves the first intact and both buildable.
6. A launcher older than this feature reads the wrapper's manifest and runs the capsule,
   without the JDK selection.
7. The repository gate from WORKFLOW-LOCAL.md passes; the base image rebuild is recorded with
   its evidence.

Preparation evidence, 2026-11-02, inside the 0.3.0 capsule, on a shallow clone of
RobotCode2025Public at its current default branch: Gradle 8.11 under Temurin 25.0.4+7 fails
before compiling anything, with `Unsupported class file major version 69` in the build script's
semantic analysis. The same build under a Temurin 17 is the second experiment; its result is
recorded in the workstream's status file.

## Execution decisions and stopping points

The workstream owns the manifest representation, the detection rules, code placement and test
design. It records a short design note before implementing, with the manifest shape, the JDK
selection mechanism and the IDE opening rule, and the owner reads it in the IDE on the
workstream's branch.

Stopping points where the owner is consulted:

1. After the design note and the Temurin 17 experiment, before implementation: the manifest
   shape and the release target.
2. Before the base image change: a base rebuild is costly and publishes a new reference; the
   owner says when.
3. Any need to change the manifest schema, the capability requirement syntax (today only
   `NAME>=VERSION`), or what is shared with the capsule.
4. Simulation of the robot code, which needs native libraries and a display, is out of scope
   until the owner names it.

## Evidence and starting points

Mainline evidence was read at `origin/main` 31d44fa473a86f608110caa53ee38c6aef40a717, the merge of the 0.3.0 final acceptance.
The capsule this was written in runs the shipped DevCapsule 0.3.0, source revision
475427da033633ff5ee0e44e09face700630bf36, with Temurin 25.0.4+7 as the only JDK.

Relevant source: `devcapsule-src/devcapsule/commands/project.py` (the `init` command and the
`config` group), `configuration/operations.py` (`initialize_project`),
`configuration/manifest_schemas.py` (schema 2 tolerates unknown root tables),
`configuration/capabilities.py` (the requirement form), `images/tooling.py` and `images/base.py`
(the Temurin component), `components/intellij.py`. The user page
`docs/your-project/existing-repository.md` is where the new page sits beside.
The sample-projects workstream's submodule practice and the memory of embedded Git directories
in submodules are the known traps.
