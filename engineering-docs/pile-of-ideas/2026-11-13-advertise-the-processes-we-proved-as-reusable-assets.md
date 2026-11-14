# Advertise the processes we proved while dogfooding as reusable assets

From: Costin Cozianu, 2026-11-13, written up with Claude.

While building DevCapsule with DevCapsule we worked out several development
processes, then tested, verified and validated them on our own work. Each one
is a trusted process we can hand to someone else. The idea: package them as
reusable assets and advertise them as such.

An asset must be usable in two places:

- Inside a DevCapsule project, where the user gets it almost for free from
  our tooling.
- Outside a DevCapsule project. How is to be decided; see part 3.

Examples of what we have:

- The pair review process: one agent pair implements, a review partner of a
  different engine reviews, and pull requests carry every step.
- Unit testing for real, in the sense of Parnas's modularity: a test belongs
  to one module and constructs its own inputs.
- End-to-end tests with video recording, driven by scripts written in human
  language.

Why it could be worth doing: any of these can be implemented rather cheaply
these days, so the implementation is not what we offer. What we offer is that
they are at our users' fingertips, already implemented and already tested on
real work. That is a big thing.

## 1. Name the assets and say what each one is

Decide which processes qualify, and what an asset consists of: the rule text,
the tooling that carries it out, the evidence that it worked for us. The three
examples above are the starting list, not the whole list.

## 2. Inside a DevCapsule project: almost for free

A user of a DevCapsule project gets each asset from our tooling with little
or no setup.

## 3. Outside a DevCapsule project

To be decided. One possibility: the `devcapsule` command line, integrated
with the user's own agent command line. This part is the least settled of the
four.

## 4. Advertise them

Present the assets on the website and in the documentation as a reason to
choose DevCapsule, each with the evidence from our own use.

## What exists today

Added by Claude from the code and records on `release-0.3.1`, as input to
part 1. The three examples are at three different distances from a user.

- Pair review ships already. It is topic 9.11 of the workflow definition
  that `devcapsule bootstrap project` installs into an adopter's repository
  (`devcapsule-src/devcapsule/assets/project_workflow/definition/WORKFLOW.md`).
  How this checkout applies it, with the engines named, is the section *Pair
  Review Loop In This Checkout* of `WORKFLOW-LOCAL.md`, which is not shipped.
- The unit test rules do not ship. They are the sections *Unit Tests* and
  *Host Inputs* of this repository's `WORKFLOW-LOCAL.md`, with the checkers
  and guards that enforce them in `devcapsule-src`. They are written for this
  project's layout and for Python.
- The recorded end-to-end scenarios do not ship. The recorder is test code,
  `devcapsule-src/tests/e2e/scenario_recorder.py`, run through
  `nox -s ide-smoke -- --scenario`; one scenario exists,
  `eclipse-hello-time-debug`. A scenario is a JSON file of recorded actions
  that an agent authors through the recorder's interactive mode. The guide is
  `engineering-docs/development/running-e2e-scenario-recordings.md`.

## Not checked

- How far the scenario format is from a script in human language. I read the
  implementation note, not the scenario file or the recorder.
- Whether the recorder can drive anything other than an IDE in a capsule's
  contained display, which decides what it is worth to a user's own project.
- Which other processes from our dogfooding would qualify.
- What the website and the user documentation already say about any of
  these.
