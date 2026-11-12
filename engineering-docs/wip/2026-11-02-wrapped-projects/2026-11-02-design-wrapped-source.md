# Design: the wrapped source

Date: 2026-11-02. Status: for the owner's ruling at the first stopping point of
[the work order](../../work-orders/2026-11-02-wrapped-projects.md). Each section
ends with the recommendation and, where one exists, the alternative in a line.

## 1. What the manifest says

Schema 2 names seven root tables and tolerates any other as an extension that its
writer carries along (`configuration/manifest_schemas.py`). The declaration is one
new root table, `[sources]`, one entry per wrapped source, keyed by the source's
path in the wrapper:

```toml
[sources."RobotCode2025Public"]
java = "17"
```

```toml
[sources."RobotCode2026Public"]
upstream = "https://github.com/Mechanical-Advantage/RobotCode2026Public"
java = "17"
```

- The key is the submodule path. The origin URL is not repeated: `.gitmodules` holds
  it and Git keeps it true. The manifest holds only what DevCapsule adds.
- `upstream`, when present, says the submodule's origin is the developer's fork of
  that upstream, so changes and pull requests go to the origin and the upstream is
  read-only. Absent, the origin is the upstream itself and the intent is to learn:
  no changes are pushed anywhere. This is the work order's fork rule, as one key.
- A toolchain key is named after the capability it refines: `java = "17"` says this
  source builds with the Java 17 line. The project-level requirement stays the
  capability, `capabilities.required = ["java"]`; the per-source key says which line,
  since the requirement syntax knows only `NAME>=VERSION` and a 25 would satisfy `>=17`
  while GradleRIO rejects it. Other capabilities get the same form later, `python =
  "3.11"`, when a source needs them; nothing is built for them now.
- A launcher older than this feature reads the table as an extension and ignores it:
  the capsule runs, without the JDK selection. Slice 1 proves the round trip through
  every manifest-writing command.

Recommendation: `[sources."<path>"]` with `upstream` and `java`. Alternative: put the
selection under `[capabilities]` as a new key; rejected because the selection is per
source, not per project, and a wrapper with two sources on different lines is real.

## 2. How the JDK reaches the build

The base image installs Temurin 17 beside Temurin 25, each under its versioned
directory, with two stable names the manifest and the instructions can rely on across
base updates:

```text
/opt/java/current -> /opt/java/jdk-25.0.4+7     unchanged, on PATH
/opt/java/25      -> /opt/java/jdk-25.0.4+7
/opt/java/17      -> /opt/java/jdk-17.0.x+y
```

Two deliveries, in the order the owner ruled:

1. **The instruction.** `wrap` writes into the wrapper's `AGENTS.md`, per source, the
   exact line: `export JAVA_HOME=/opt/java/17; export PATH="$JAVA_HOME/bin:$PATH"`,
   to run before any build, test or run in that source. The `README.md` carries the
   same line for the human at the IDE terminal. This works on the first base that
   carries the JDK, with no runtime change.
2. **The capsule environment.** When every wrapped source names the same line, the
   runtime plan carries `JAVA_HOME` and the `PATH` prefix for the whole session, so
   the IDE terminal, Gradle's daemon and IntelliJ's JDK detection see 17 without
   anyone typing the line. When sources disagree, the capsule stays on `current` and
   the instruction governs. The plan's environment is an existing contract
   (`container_runtime/contract.py`); the addition is one more source of entries.

What is not done: no `gradle.properties`, `.sdkmanrc` or `.java-version` is written
into the foreign tree. The foreign tree stays clean; that is the point.

Recommendation: both, instruction in slice 1, environment in slice 2 with the base.
Alternative: only the environment; rejected because two sources on different lines
would have no answer.

## 3. What the IDE opens, and where the agent starts

The IDE opens the wrapper root, as it does for every project, and the agent starts
there. The reason is the agent: Claude Code and Codex read `AGENTS.md` from the
working directory up to the Git root, and the submodule is its own Git root. An IDE
that opened the submodule would start the agent inside it, blind to the wrapper's
guidance, and the only fix would be a file inside the foreign tree.

For IntelliJ to import the Gradle project automatically from the wrapper root, `wrap`
writes a minimal `.idea/gradle.xml` in the wrapper that links each Gradle source, and
names the project JDK from the declared line. These files are the wrapper's, not the
foreign tree's, and they are the same files IntelliJ writes itself after a manual
"link Gradle project". Whether the link file is needed at all, or a one-time click is
acceptable, is decided by the slice 2 launch and recorded.

Recommendation: open the wrapper root; link Gradle through the wrapper's own IDE
files. Alternative: open the single source directly when there is one; rejected for
the agent reason above.

## 4. What `wrap` detects, for the showcase

In the submodule just added, in this order, first match wins:

| Found | Declared |
|---|---|
| `gradlew` and a `build.gradle` or `build.gradle.kts` naming `edu.wpi.first.GradleRIO` | `java` required, `java-ide` recommended; `java = "17"` for GradleRIO 2025 and 2026 |
| `gradlew` without GradleRIO | `java` required, `java-ide` recommended; the line from the Gradle version in `gradle/wrapper/gradle-wrapper.properties`: Gradle 8.x gets `17`, Gradle 9.x gets `25` |
| anything else | nothing declared; `wrap` says so and names `project config require` |

The GradleRIO rule is a fact about WPILib: its 2025 and 2026 releases ship and require
JDK 17. The Gradle rule is a fact about Gradle's Java compatibility table. Both are
data in one small module with the source of each fact beside it, so a new WPILib year
is a one-line change. Maven, Node and Python detection are not built now; the work
order names one use case.

## 5. The submodule, done right the first time

`wrap` runs `git submodule add <url> <path>`, then moves `.git/modules/<path>` into
`<path>/.git` and unsets `core.worktree`, so the submodule's Git directory is inside
the tree the capsule mounts. This is the known trap from the dogfood checkout; `wrap`
removes it for every adopter. The `README.md` it writes tells a cloner of the wrapper
to run `git submodule update --init`, which produces the same embedded layout on a
fresh clone.

## 6. Slices

1. **The declaration and `wrap`.** `[sources]` read and written and reported by
   `project config show`; `project wrap URL [--path NAME] [--upstream URL]`; the
   `AGENTS.md` and `README.md` it writes; the detection module; the user page draft;
   R-CONFIG-001 extended; unit and built-CLI tests. No base change. Validation: the
   gate, plus the three commands run against the showcase repository on the host side
   up to the manifest and lock.
2. **The base and the capsule.** Temurin 17 in the base with the stable names; the
   environment entries in the runtime plan; the IntelliJ link; the acceptance run of
   the work order inside a capsule. Starts after the owner's go at the second stopping
   point.

Each slice is one pull request with its Codex review, as the local Pair Review Loop
says.

## 7. The downloaded internet stays downloaded

One build of the showcase pulls Gradle itself and a few hundred megabytes of
dependencies into `~/.gradle`. The capsule's home is already a persistent mount per
checkout (`persistence.py`), so the cache survives sessions with no new mechanism, and
the second launch builds offline-fast. The cost is paid once per wrapper checkout, not
once per session. Nothing to build here; the acceptance run records the second-launch
build time beside the first to prove it.
