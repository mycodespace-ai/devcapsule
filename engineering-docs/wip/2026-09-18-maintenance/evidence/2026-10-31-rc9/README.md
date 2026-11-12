# RC9 component refresh and release preparation

The owner selected agent upgrades on 2026-10-31 and requested stable IDE
updates, particularly the JetBrains security updates. This is preparation
for v0.3.0-rc9, not acceptance of the final release.

## Component selection

| Component | Previous default | RC9 default |
|---|---|---|
| Codex | 0.163.0 | 0.166.0 |
| Claude Code | 2.1.302 | 2.1.314 |
| Antigravity CLI | 1.4.2 | 1.4.12 |
| PyCharm | 2026.2.0.1 | 2026.2.4 |
| IntelliJ IDEA | 2026.2.3 | 2026.2.4 |
| Rider | 2026.2.3.1 | 2026.2.4 |
| VSCodium | 1.126.04524 | 1.143.17232 |
| Visual Studio Code | 1.143.1 | 1.144.0 |
| Eclipse Java | 2026-09-R | unchanged |

Sources: the [Codex npm channel](https://registry.npmjs.org/@openai/codex/latest),
[Claude release channel](https://downloads.claude.ai/claude-code-releases/latest),
[Antigravity Linux manifest](https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json),
[JetBrains release feed](https://data.services.jetbrains.com/products/releases?code=PCP,IIU,RD&latest=true&type=release),
[VSCodium releases](https://github.com/VSCodium/vscodium/releases),
[Microsoft stable feed](https://update.code.visualstudio.com/api/update/linux-x64/stable/latest),
and [Eclipse packages](https://www.eclipse.org/downloads/packages/).
The Eclipse 2026-12 milestone is a development build and was excluded.
All nine complete artifacts passed vendor integrity and applicable size checks;
[artifacts.json](artifacts.json) records the URLs, sizes and verified digests.
These are stable-channel selections; this record does not claim a particular
CVE is fixed without an advisory establishing it.

The catalog advances to embedded-30. Earlier pins and edges remain available
for existing locks. The repository's shared schema-1 configuration is retained:
`project init --regenerate` would also migrate its requirements/IDE contract,
which is outside this component refresh. The running baseline
`/usr/local/bin/devcapsule0`, version 0.3.0rc8, source `8d41fabe9f7e`, validated
that existing manifest and lock with `project config check --manifest
.devcapsule/devcapsule.toml --lock .devcapsule/devcapsule.linux-amd64.lock
--json` (exit 0). No project configuration file was edited.

## Agent startup

The four agent downloads passed their vendor integrity checks: npm SHA-512,
Claude's manifest SHA-256 and size, and Antigravity's manifest SHA-512.
SHA-256 values in the catalog were computed from those same complete bytes.

[The probe](agent-startup.sh) ran in a disposable container on
`mycodespaceai/devcapsule-base:v0.3.0.rc6`, image
`sha256:465cd9065654561151a4435bef90a5e15f6a51a1369c16794203529bb5848a4f`,
with host networking. It installed the two npm tarballs through explicitly
named file dependencies, matching production's offline npm layout, and ran
all three CLIs as a fresh uid-1000 user. No account state was supplied.

[The log](agent-startup.log) records Codex 0.166.0, its feature listing and
`exec --help`; Claude Code 2.1.314 and `--help`; Antigravity 1.4.12, help and
changelog. Claude's headless probe returned the expected unauthenticated
result, with zero API usage; its debug line confirms the seeded
`bypassPermissions` default was loaded. The three seed files were
byte-identical after execution. Authenticated actions, model access and
first-use account notices are still downloaded-candidate acceptance work.

Initial probe setup errors were corrected before this successful run: the
artifact bind needed the host source of the nested cache mount; Codex's npm
platform package needed its explicit dependency alias; and the script needed
a file input independent of the child CLIs' standard input.

## Build and documentation checks

The 101 existing resolution/initialization tests pass with regenerated golden
locks and updated default-version expectations. Release-document tests pass
(92). The website build and check pass (252 pages, 21,031 local links, assets
and anchors) after adding the required metadata block to the release notes.

The initial full gate used a long host-mounted scratch path: Unix sockets
exceeded their path limit and a host-isolation fixture received a mountable
path. The rerun uses `/opt/devcapsule-gate/rc9`; the directory first had to be
created with the development user's ownership. These setup failures did not
require product changes. The full gate then passed: 2,644 unit tests (40 deselected, one expected
failure and one non-strict unexpected pass), 18 packaging integration tests,
type and syntax checks, CLI/PEX smoke, documentation contract, and 357
web-console tests. All five updated IDEs completed the graphical startup checks below.

## Graphical startup checks

The built local PEX is identified by [startup-build.json](startup-build.json).
The smoke harness uses fresh projects and the pinned recipe-11 base, verifies
the desktop and token-protected console endpoints, finds an IDE X11 window,
keeps rendered pixels, and checks that the child runtime has exactly the
selected PEX's SHA-256. Host networking follows the local validation policy.

The first run (`20261031T011008Z-702c9c`) completed VSCodium and PyCharm,
including cleanup, then its runner ended with SIGTERM (exit 143) before
IntelliJ startup; there was no failing test assertion. Its interrupted
IntelliJ fixture and records were removed. The remaining surfaces completed in run `20261031T011314Z-518a42`: three
passed, three deselected, exit 0. Both runs used the same PEX checksum.

| Surface | Retained facts and screenshot | Observation |
|---|---|---|
| VSCodium | [facts](codium/facts.json), [desktop](codium/desktop.png) | Welcome/editor shell with fixture project |
| PyCharm | [facts](pycharm/facts.json), [desktop](pycharm/desktop.png) | First-use agreement |
| VS Code | [facts](vscode/facts.json), [desktop](vscode/desktop.png) | Welcome/sign-in screen |
| Rider | [facts](rider/facts.json), [desktop](rider/desktop.png) | Splash/window then first-use agreement |
| IntelliJ | [facts](intellij/facts.json), [desktop](intellij/desktop.png) | Splash/window then first-use agreement |

Rider's .NET 10.0.401 SDK also [built](rider/dotnet-build.txt) and
[ran](rider/dotnet-run.txt) the package-free C# fixture. Its
[component browser](rider/component-browser.json) and IntelliJ's
[component browser](intellij/component-browser.json) rendered test HTML.
The local PEX is a dirty-source preparation build with `source_revision:
unknown`, not a published candidate; its checksum identifies the exact tested
artifact. The catalog's later edits only replace provisional evidence strings
with these observations; the pins and runtime behavior are unchanged.

VSCodium shows its welcome/editor shell and the fixture project. The three
JetBrains screenshots show their first-use agreements. These are startup observations, not proof of
a saved edit, account entitlement, licensing, or persistence after relaunch.

## Release obligations

The preparation promotes 0.3.0 documentation, deprecates 0.2.15 and marks
0.2.14/0.2.12 unsupported. Adopter notes accompany the promotion. `docs-0.3.0` is published at promotion commit `68b21a18`. The promotion
is carried by a release review slice; its documentation ref must exist
before hosted PR checks, which fetch docs-* refs. This ordering makes the
source available to CI while owner release integration remains pending. The docs tree must match the accepted
final tag.

The human merges the preparation into release and its main propagation.
Only after that disposition is resolved may rc9 be tagged and the published
PEX downloaded and checked. C17, the remaining nine documentation proposals,
and downloaded-candidate acceptance retain their recorded dispositions;
preparing a candidate does not silently close them.

## Cookie fix reconciliation checkpoint

PR #330 merged to release at `36b5e660`, carrying `3af21584`. Merging that
release tip into the preparation branch conflicted only in the maintenance
status State line; both sessions' records are retained. No source conflict
needed resolution. The full combined `nox -s build` gate passed: 2,644 unit
tests (40 deselected, one expected failure, one non-strict unexpected pass),
18 packaging tests, 374 console tests, type/syntax checks, CLI/PEX smoke and
documentation contract. Scratch was `/opt/devcapsule-gate/rc9-cookie`.

Docs-only commit `7a813b80` publishes the fix's three guide corrections on
`docs-0.3.0`. Its docs tree equals this preparation branch's docs tree. The
website build/check passed: 252 pages and 21,031 links/assets/anchors.

At this checkpoint the base refresh still awaited the owner; these source
checks alone did not prove delivery to ordinary capsules or concurrent
browser acceptance. The subsequent base-first decision and delivery below
resolve that gap. Console authentication uses port-suffixed cookies; noVNC
authentication uses its WebSocket token URL.

## Published base and concurrent authentication

The owner selected **base-first** at 02:14:16 UTC on 2026-10-31. The strict
public-source builder embeds commit `12a30fa60322de585810048881ee166fcdb26854`.
The supported `images build --type base --recipe ubuntu-24.04 --network host`
command verified that public source and fetched the console from it. No
`--allow-local-source` flag was used for this public base. The builder's
`v0.3.0-local-linux-x86_64` mnemonic denotes an untagged build; its source
revision is known and public. No candidate tag was invented.

Published tag: `mycodespaceai/devcapsule-base:v0.3.0-base-20261031`.
Registry digest: `sha256:d7047ced8556cd35964fcc058a1101cf2b5b202f7a5daa2fdd434dcda5ed82c9`.
The registry pull matches the built image ID. The installed console security
module matches the fixed source byte-for-byte. Of six filesystem layers,
only the console layer differs from rc6. [Base identity](base-refresh.json)
retains the builder identity, PEX checksum, labels, layer digests and console
checksum. Catalog embedded-31 retains old pins and selects this one for new
resolutions. The builder commit also supplies the catalog's recipe-source
permalink, since the builder has no release tag.

The first full gate found that the catalog invariant test assumed every pin
had a higher recipe number. The test now requires identical contracts for
same-recipe rebuilds and retains the additive rule across recipe versions.
The provenance regression check ensures the new pin links to its exact
public builder commit. The 112 focused catalog, initialization and contract
tests pass.

The opt-in [concurrent authentication regression test](../../../../../devcapsule-src/tests/e2e/test_concurrent_auth.py)
passed on two ordinary fresh VSCodium projects using the new default pin,
with no base override and host networking. It ran with the ide-smoke Python
environment, `pytest --no-cov -m e2e tests/e2e/test_concurrent_auth.py`, and
`DEVCAPSULE_PEX_UNDER_TEST` selecting the captured local validation PEX.
The runtime PEX differs from the public base builder: its catalog includes
the newly published digest, and its dirty-source identity is explicitly
`unknown`. This is pre-candidate validation, not downloaded-RC acceptance.

[Browser facts](concurrent-auth/facts.json) record distinct console ports and
cookie names, one shared browser context, repeated tokenless console
navigation/reload, noVNC reload/disconnect/reconnect, and refusal of sibling
console cookies, console URL tokens and WebSocket tokens. Both desktops
remained connected. [Layer lineage](concurrent-auth/base-lineage.json)
confirms that both materialized environments contain every layer of the
published base. [Cleanup A](concurrent-auth/cleanup-a.json) and
[cleanup B](concurrent-auth/cleanup-b.json) confirm container removal.
No launcher log, cookie value or tokened URL is retained here.

| Capsule | Console after authentication checks | Connected desktop |
|---|---|---|
| A | [Console](concurrent-auth/console-0.png) | [VSCodium desktop](concurrent-auth/desktop-0.png) |
| B | [Console](concurrent-auth/console-1.png) | [VSCodium desktop](concurrent-auth/desktop-1.png) |

Console screenshots establish authenticated page rendering; they do not
establish completion of every overview probe or acceptance of every console
feature. The browser run verifies host-network sessions; automated console
Host-header tests separately cover browser ports differing from internal
ports. Main propagation and downloaded-candidate acceptance remain.

Final validation after the pin/provenance/test corrections: full build gate
passed with 2,645 unit tests (41 deselected, one expected failure and one
non-strict unexpected pass), 18 packaging tests, 374 console tests,
type/syntax checks, CLI/PEX smoke and documentation contract. Website build
and check passed: 252 pages and 21,031 links/assets/anchors. The browser test
is marked `ide_smoke` so the standard non-browser E2E suite excludes it;
run it explicitly with the command above. The cookie-delivery hold is
resolved; owner release/main integration precedes the candidate tag.

## Downloaded RC9 verification

[RC9](https://github.com/ccozianu/devcapsule/releases/tag/v0.3.0-rc9) was
published successfully by [run 41181720227](https://github.com/ccozianu/devcapsule/actions/runs/41181720227)
after #331 merged into main `4b59b10d`. The annotated candidate tag points
to release `475427da033633ff5ee0e44e09face700630bf36`; the mainline candidate
gate reports no unintegrated commits. Publicly downloaded assets match
[the release manifest](published/release-manifest.json), version `0.3.0rc9`,
mnemonic `v0.3.0-rc9` and PEX SHA-256
`413b1d45bac9c39b6fa5fab68090e43550c9e255108de48b387c50a715c4fcf2`.
[Verification ledger](published/verification.json).

With DEVCAPSULE_PEX_UNDER_TEST selecting that downloaded PEX, the nox e2e
session passed **8 tests**, 15 deselected, in 129.38 seconds. It covers
component-cache reuse/invalidation, exact launcher delivery, external runtime
removal, runtime/display lifecycle and self-contained execution on a clean
machine without Python/network. Build networking was explicitly host; the
base and early-exit image overrides selected the published fixed-base digest.

The separately selected concurrent-auth test passed **1 test** in 22.90
seconds, using the default catalog base without an override. It repeats the
shared-browser checks above against the downloaded release, not a local PEX.
[Browser facts](published/concurrent-auth/facts.json),
[base lineage](published/concurrent-auth/base-lineage.json), and
[cleanup A](published/concurrent-auth/cleanup-a.json) /
[cleanup B](published/concurrent-auth/cleanup-b.json) retain the result.
Both test project records were also removed.

| Capsule | Authenticated console | Reconnected desktop |
|---|---|---|
| A | [Console](published/concurrent-auth/console-0.png) | [Desktop](published/concurrent-auth/desktop-0.png) |
| B | [Console](published/concurrent-auth/console-1.png) | [Desktop](published/concurrent-auth/desktop-1.png) |

The host-network/overview-probe limits above still apply. This closes the
cookie bug's delivery and regression criteria, not final release acceptance
or all provider/editor workflows. Existing locks are not automatically
rewritten. Raw launcher logs, cookies and tokened URLs are not retained.

## Final promotion audit — 2026-10-31

The owner requested final publication after successfully restarting on RC9
and the new base. The initial restart had retained a saved RC0 local-base
override; `project config authorize base-image default` on the host corrected
it. [Live restart evidence](final-audit/live-restart.json) verifies the actual
base layers and installed security-module checksum as well as the RC9 PEX.
The session uses host-X11; the earlier two-capsule test supplies noVNC proof.
No project configuration was edited by the agent.

Additional checks against the published RC9:

- [Runtime inspection](final-audit/runtime-inspection.json): `config show`,
  `versions show` and `info` emit valid JSON from root, descendant and `/opt`;
  the unknown-subcommand diagnostic precedes the launcher guard.
- [Recursive proof](final-audit/recursive.log): the existing attached-successor
  regression passes in 8.66 seconds. [Adapter](final-audit/recursive-published.py)
  selects the downloaded PEX for every CLI operation and uses its supported
  `init --regenerate` to prepare an isolated fresh clone with this capsule's
  choices. Existing lifecycle/inspection/cleanup assertions are unchanged.
- [Packaged regressions](final-audit/packaged-tests.log): 18 passed, comprising
  all 17 unpacked-cache tests and the universal-network-node regression.
  PEX interpreter mode pre-imported the packaged `devcapsule-0.3.0rc9` wheel;
  only pytest and its dependencies came from the development environment.
- [Fresh Codium network proof](final-audit/network-runonce.log): saved network
  access denied, no project recommendation, one-time `--authorize network host`
  accepted, real IDE window and host network inspected, container/project
  cleaned. [Driver](final-audit/network-runonce.py). Initial harness attempts
  failed before launch because init adds a justified recommendation and the
  helper has no cwd argument; the final driver removes the recommendation
  with the CLI and selects the project with `--path`. No product fix needed.
- [Freshness](final-audit/freshness.json): retain RC9's exact tested pins;
  newly available Claude 2.1.316 is a 0.3.1 follow-up. The other two feeds
  still match RC9. Documentation check passes and notes/docs match the tag.

Final scope is still awaiting the owner's explicit disposition of C17 and
the nine September 28 proposal decisions, separately from the already deferred
October 25 work. Provider/editor acceptance beyond the established coverage
also needs an explicit outcome. The prepared promotion record remains a draft
outside Git; no final tag exists. No credentials or tokened URLs are retained.

## Owner acceptance — 2026-10-31

After requesting final publication, the owner answered "Yes to both questions,
let's move ahead" to the remaining scope/provider dispositions. C17 and the
nine September 28 documentation proposals move to 0.3.1 planning. RC9 is
accepted with the documented provider/editor limits, without asserting
additional unobserved actions. This supersedes the pending final-audit
paragraph above. [Canonical promotion record](../../../../releases/v0.3.0.json).
Final publication follows its human-merged mainline integration.
