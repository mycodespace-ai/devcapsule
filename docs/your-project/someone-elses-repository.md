---
description: Work on a repository that is not yours, and carries no DevCapsule configuration, by wrapping it as a submodule of a small project of your own.
weight: 3
updated: 2026-11-02
---
# Someone else's repository

The first slice provides the declaration, `project wrap`, and generated
guidance. The base image's additional JDK, automatic session selection,
and capsule acceptance are planned for slice 2. The commands below describe
the intended workflow; the complete capsule workflow is not yet validated.

A project you want to read, build or debug is not yours to configure: an
open-source project with an afternoon of setup instructions, or a robotics
team's public code you want to learn from. Do not send them a pull request
with a DevCapsule configuration. Wrap the repository instead: a small
repository of your own holds the configuration, and theirs is a Git submodule
of it. Nothing is written into their tree.

```bash
mkdir frc-learning && cd frc-learning && git init
~/.local/bin/devcapsule project wrap https://github.com/Mechanical-Advantage/RobotCode2025Public --require java --java 17
~/.local/bin/devcapsule project run
```

`wrap` adds the submodule, requires what you name, writes the manifest and
the lock, and writes an `AGENTS.md` and a `README.md` that say what is foreign,
under whose control, and which Java to use. `run` opens the capsule with the
IDE on the wrapper; the code is in the submodule. Commit what `wrap` produced;
anyone who clones the wrapper must initialize its submodules before running it.

## What you tell `wrap`

The launcher infers nothing from a foreign tree. You name what every
checkout must have, `--require java`, as you would with `init`, and the Java
line the source builds with, `--java 17`. The line matters because a build
such as WPILib's refuses any other JDK; the generated `AGENTS.md` names it,
and the matching JDK must exist under `/opt/java/<line>`. The additional JDK
in the base and the session-wide selection are planned for the next slice.

Name nothing and the source is still wrapped, with its build unsettled: the
`AGENTS.md` tells the agent to find out with you, from the source's own
files, before assuming. The IDE is recommended separately,
`devcapsule project config recommend ide java-ide`, as for any project.

## Learning or changing

`wrap URL` with the upstream's URL means you intend to learn: the submodule
is read-only in intent, and nothing is pushed. `wrap URL --upstream UPSTREAM`
means `URL` is your fork of `UPSTREAM`: your changes and pull requests go to
the fork, and the upstream is never written to unless its maintainers ask.
The `AGENTS.md` carries the same rule for the agent.

## Several repositories

Run `wrap` once per repository. The second run extends the manifest and
regenerates the two files. `--path NAME` picks the directory when the
repository's name will not do. A run interrupted by a network failure is
finished by running it again when Git registered the submodule from the same
URL. A registered source with a missing directory is initialized again.
A registered path with another URL is refused, even when its directory is
missing. Paths through symlinks are refused.

Git can leave a partial clone before it registers the submodule. In that
case, inspect the path, `.gitmodules`, and Git's modules directory before
retrying. `wrap` reports the failure and removes no files. If initialization
stops at a prompt, the added submodule remains for a rerun.

The generated guidance escapes repository names, paths, and URLs as text.
`wrap` replaces a guidance file only when its entire first line equals the
generated marker. It keeps the owner's other files.

## What `wrap` does not do

It does not install the project workflow; `project bootstrap` remains
available. It does not run the foreign project's build, tests or setup; those
run inside the capsule, from the submodule's directory, with its own tools.
It does not add the project's dependencies to the lock; the Gradle cache
lives in the capsule's persistent home, so the first build's downloads are
paid once per checkout.

**Next: [choose a coding agent](../working-with-ai/choose-an-agent.md) or
[declare project needs](declare-needs.md).**
