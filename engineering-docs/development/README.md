# Development

How DevCapsule is built and tested, for contributors and agents. The
[developer brief](../../DEVELOPING.md) at the repository root is the short
entry point; the documents here carry the detail, one subject each.

| Document | Answers |
|---|---|
| [Developer environment](developer-environment.md) | How to set up a checkout, run the gate, build the executable, and tell the shipped CLI from the development one |
| [Source layout](source-layout.md) | Where things live in the repository and inside the `devcapsule` package, and which boundaries are enforced |
| [Unit tests](unit-tests.md) | What `nox -s tests` runs, how the suite is organized, its fixtures and resources, and what the hosted runner does |
| [Integration tests](integration-tests.md) | A subsystem with the real external things it uses, the services it does not test faked: the built executable, subprocesses, git, the Docker daemon; where the `docker` marker and the candidate rule apply; the gate checks that are not tests |
| [End-to-end tests](e2e-tests.md) | The Docker-backed suites, each with its entry point, what it proves, what it needs, and the evidence it leaves |
| [Running E2E scenario recordings](running-e2e-scenario-recordings.md) | How to replay or author a recorded IDE scenario from a shell with `nox -s ide-smoke -- --scenario` |
| [Pair Review Loop](review-partner-loop.md) | How a slice is built by two agent pairs of different engines: the brief template, the round brief, the assessment comment, the invocation recipes per engine, and the record of the loops run |

Placement rule: a document here describes how the project is developed and
verified today. Requirements, decisions, specifications and release records
keep their own homes under `engineering-docs/`; see
[its README](../README.md).
