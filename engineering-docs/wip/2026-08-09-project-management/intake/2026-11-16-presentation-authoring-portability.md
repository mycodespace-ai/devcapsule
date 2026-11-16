# Presentation authoring is not delivered to adopter projects

From: github-auth
To: project-management
Date: 2026-11-16

The owner asked whether an LLM in a project other than DevCapsule receives enough
Markdown instructions and Python support to create recorded console presentations
with minimal work. This follow-up audit crosses packaging, recorder and console
ownership; please acknowledge and assign the delivery work.

Evidence from delivered PEX SHA-256 af7fa02ca2c2737f3a1678226341312682b71cfdd37eb892f29a42ad5c31b78c:
- The nested console bundle contains presentation HTML/JS/CSS. The viewer is generic
  and discovers valid presentation.json folders within any mounted project.
- No scenario_recorder.py, scenario_presentation.py, PRESENTATIONS.md, authoring
  guide, scripts or other tests/e2e files are in the PEX.
- The 16 packaged bootstrap documents/templates contain no presentation.json or
  recorder guidance. CLI help contains no presentation authoring operation.
- browser-automation supplies Playwright/browser tools, not this authoring kit.
- The repository's producer is standard-library Python; its IDE recording harness
  instead initializes disposable DevCapsule smoke projects and is not an adapter
  for arbitrary project E2E tests. Interactive recording does not emit metadata.

The existing six-step SSH presentation works in our live console, but that is not
an installed-product authoring acceptance test. Documentation now makes the gap
explicit and offers an honest agent task brief that requires source tooling.
Evidence is indexed in github-auth's status at evidence/portability-audit.json.

Proposed delivery outcome, subject to ownership and product decisions:
1. Ship discoverable agent-facing Markdown instructions, a scenario template and
   the schema/contract with a versioned authoring toolkit.
2. Expose a supported generator/validator and recording/timing integration for a
   project's own E2E harness, including an explicit interactive path.
3. Make the documented route discoverable without searching the DevCapsule source.
4. Prove it in an unrelated fixture project using only an installed candidate:
   discover support, author the script, record a real journey, generate metadata,
   verify console listing/step playback/captions, and retain build-safe evidence.
   No DevCapsule source checkout, tests.e2e imports or hand-reconstructed timings.

No toolkit interface or delivery mechanism was selected or implemented in this
audit. This is a feature-delivery gap, not a claim that the existing viewer violates
its documented contract. capsule-webconsole separately received the interactive
recording usability observation as 2026-11-16-interactive-presentations.md.
