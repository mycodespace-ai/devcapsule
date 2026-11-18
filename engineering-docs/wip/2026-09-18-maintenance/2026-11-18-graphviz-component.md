# Graphviz component for 0.3.1

Requirements: R-TOOLS-001, R-PRODUCT-001, R-CONFIG-001, R-UPGRADE-001.

## Scope and owner decision

The owner requested Graphviz as a component available to projects everywhere,
then selected `maintenance-031` on 2026-11-17. The local Conda installation
from the earlier misunderstanding does not deliver this requirement.
`ws-maintenance/graphviz-031` starts from release `7ad956d4`; its delivery target
is `release-0.3.1`. The concurrent CLI pair owns its own branch and review.

## Implementation

`graphviz` is an additive capability and catalog component. Its platform lock
pins Graphviz 16.1.1 source, the upstream SHA-256 and Ubuntu 24.04 build-package
URLs and SHA-256 values. The same source is used on amd64 and arm64. Upstream
provides Ubuntu amd64 binaries but no matching arm64 release, so building the
official source avoids selecting unrelated versions on the two architectures.

The build runs in a separate contribution stage with networking disabled.
Pinned development packages are installed there; the existing base provides
the compiler and make. Pango/Cairo enable text, PNG and PDF output. GTS supplies
the triangulation required by default `sfdp`, and its runtime library and
libltdl are copied under `/opt/graphviz/lib` with their license notices.
Graphviz's install prefix and library search path are `/opt/graphviz`.
Sources and package inputs are removed before exporting that directory.
The final base and its package-manager state are unchanged by this contribution.

A small trusted component build-recipe interface declares the installation
commands and filesystem exports. Other components retain their existing paths.
Grouped input copies prevent dependency-rich builds exceeding Docker's layer
depth limit; the ordinary file-copy renderer is unchanged.

The component's discovery adapter reads official stable GitLab release metadata
through a supplied reader. It reports availability without claiming support,
selecting a new version or modifying an installed component. The backend's
probe policy includes Graphviz.

The matrix advances to `embedded-34`. Existing lock fixtures differ only in
that informational version and its generated comment. The old resolution-matrix
test hard-coded the catalog vocabulary; changing it requires retiring the whole
legacy file. Decision tests moved to its unit mirror with explicit synthetic
inputs; catalog snapshots and real loader checks moved to integration.

## Validation

- Offline amd64 source build on the exact pinned recipe-11 base passed.
  [Machine-readable report](evidence/graphviz-0.3.1/linux-amd64.json).
  Its final image renders DOT to SVG, PNG and PDF as uid/gid 1000:1000,
  plus `neato` and `sfdp` to SVG, without a mounted personal installation.
  `/opt/graphviz/.build` is absent.
- New component/discovery/grouped-copy checks and the existing materialization
  tests pass. The moved catalog and loader integration tests pass: 24 cases.
  Real CLI require/offer initialization passes: two cases on the native host.
- The pre-synchronization full gate passes: 3,376 unit tests, two expected
  failures, 474 web-console tests, types, conventions, CLI/PEX smoke and
  documentation contract. Test conventions report 97 remaining legacy files,
  1,277 legacy tests and zero breaches.
- Live Graphviz discovery reports 16.1.1 available with no newer candidate.
- `.github/workflows/graphviz-component.yml` builds and renders on native
  amd64 and arm64 runners. Native arm64 evidence is pending; the matrix does
  not yet claim that platform verified for Graphviz.

## Remaining delivery

Merge the newly advanced release tip carrying CLI PR52, validate that combined
tree and open the feature PR into `release-0.3.1`. Record native arm64 CI
evidence before adding its verified matrix edge. The human merges the feature
PR. Main propagation, candidate production and downloaded-candidate acceptance
remain release-driver work; this component validation is not candidate acceptance.

The checkout's original configuration is preserved in the named stash and
`.git/graphviz-031-preservation.json`; the website branch and commit are retained.
No transcript, tokened decision URL or capsule decision JSON belongs in Git.
