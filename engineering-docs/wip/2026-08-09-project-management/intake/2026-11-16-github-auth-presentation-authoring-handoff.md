# Deliver presentation authoring support to adopter projects

From: github-auth
To: project-management
Date: 2026-11-16

## Request and routing

The owner requests that all findings from the SSH-proxy showcase and portability
audit be handed over together. This consolidates and supplements
`2026-11-16-presentation-authoring-portability.md` (coordination `1b693680`)
and the console observation `2026-11-16-interactive-presentations.md`
(coordination `f044d306`). It does not withdraw either earlier item.
Accepting means recording the adopter-authoring need and assigning its delivery
across documentation, packaging, recording and console ownership. Priority,
release target and interface are for project-management and the owner to decide.

## New owner evidence

The owner reports successful reuse of the E2E recording apparatus in a separate
project running DevCapsule 0.3.0: its agent was pointed at this repository and
instructed to clone the tooling ad hoc. Recording worked. Adding presentations
and the rest of the setup was too much work. This is owner-reported evidence,
not an independently repeated run, and does not establish that 0.3.0 shipped
presentation viewing or authoring support. It demonstrates that reuse is already
possible; the unmet need is a supported, discoverable route with little agent
setup rather than repeatedly reconstructing the process from this source tree.

## Observed behavior and reusable pieces

- The current console recursively discovers regular `presentation.json` files
  below its mounted project. No registration, restart or website build is needed.
  Hidden directories, node_modules and symlinks are skipped; scanning has a
  20,000-directory limit. Outside worktrees are not discovered.
- `/presentations/<project-relative-folder>` is the viewer route. Authenticated
  `/api/project/raw` serves the named metadata and media, including byte ranges.
  The website example under `website/_site/assets/presentations/` is generated
  website output, not a required authoring or installation location.
- Local recording evidence belongs outside dist under a project-visible folder;
  DevCapsule uses `devcapsule-src/tests/e2e/evidence/<scenario>/<run>/`.
  Development examples also exist in `devcapsule-webconsole/resources/presentations/`.
  Markdown scripts alone are not discoverable presentations.
- Scripted replay with a script and numbered actions/reasons generates metadata
  after encoding. Scriptless replay does not. Interactive serve/ctl does not,
  even with a script; its action log lacks the timing/frame data needed afterward.
  Ordinary E2E execution therefore does not guarantee a presentation.
- `devcapsule-src/tests/e2e/scenario_presentation.py` is reusable standard-library
  Python. The recorder also depends on IDE/browser smoke helpers and initializes
  disposable DevCapsule projects; it is not yet a supported adapter for an
  arbitrary project's own test journey.
- Step playback uses ranges of one recorded video, with screenshots and captions;
  it does not require separately encoding one video per step. Retaining recorder
  frame counts and screenshots avoids hand-reconstructing chapter boundaries.

## Shipped-product audit

Inspected the actual merged PEX, SHA-256
`af7fa02ca2c2737f3a1678226341312682b71cfdd37eb892f29a42ad5c31b78c`,
including its nested web-console bundle. The viewer HTML/JS/CSS are shipped.
The recorder, metadata producer, scenario scripts, PRESENTATIONS.md and authoring
instructions are not. None of 16 packaged bootstrap documents/templates points
to the producer or presentation.json. There is no presentation authoring CLI.
The browser-automation component supplies browser tools, not this authoring kit.
This is a delivery/discoverability gap, not a demonstrated viewer-contract defect.
No portable kit or new product interface was implemented by this audit.

## Completed example and durable documentation

On `ws-github-auth/ssh-proxy`, commits `d94973f8` and `b084b320` contain:

- `devcapsule-webconsole/PRESENTATIONS.md`: discovery, source locations,
  generation behavior and the cross-project support matrix.
- `engineering-docs/development/running-e2e-scenario-recordings.md`: authoring
  procedure and an agent task brief with honest source-tooling prerequisites.
- `devcapsule-src/tests/e2e/scripts/github-ssh-proxy.md`: six-step script.
- `engineering-docs/wip/2026-11-16-github-auth/evidence/`: showcase.md,
  present-showcase.py, presentation-timing.json and portability-audit.json.
  The producer is specific to the retained recording and validates its checksum;
  it is an example, not a general recording framework.

The real 45.42-second SSH-proxy recording now has six playable chapters in the
live console. Chromium verified listing, screenshots, captions, all six playback
boundaries and authenticated byte-range serving. All 39 existing producer tests
and the documentation contract passed. Raw media and generated metadata remain
ignored local evidence at
`devcapsule-src/tests/e2e/evidence/github-ssh-proxy/20261116T103152Z-af7fa02c/`.
No token or cookie is part of this handoff. This proves the existing viewer and
producer in our source checkout, not installation-only authoring in another project.

## Proposed outcome and acceptance

Provide discoverable, versioned Markdown instructions and a scenario template,
a supported metadata generator/validator, and recording/timing integration for
project-owned E2E journeys, with an explicit interactive route. Reuse the existing
producer and viewer where appropriate. Decide packaging and command/API shape
before implementation; this handoff selects neither.

Acceptance should use only an installed candidate and an unrelated project.
Tell its agent to write a Markdown scenario, record a real feature journey and
make a captioned step presentation available in that capsule's web console.
The agent must discover the installed guidance, generate validated metadata,
retain evidence outside build output, and demonstrate listing and step playback.
It must not need a DevCapsule source clone, tests.e2e imports, manual timing
reconstruction or knowledge from this conversation. Record compatibility with
older capsules separately; the reported 0.3.0 reuse is not a compatibility promise.
