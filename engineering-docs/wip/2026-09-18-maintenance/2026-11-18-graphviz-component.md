# Graphviz component for 0.3.1

Requirements: R-TOOLS-001, R-PRODUCT-001, R-CONFIG-001, R-UPGRADE-001.

## Scope and owner decision

The owner requested Graphviz as a component available to projects everywhere,
then selected `maintenance-031` on 2026-11-17. The local Conda installation
from the earlier misunderstanding does not deliver this requirement.
`ws-maintenance/graphviz-031` starts from release `7ad956d4` and merges release
`3a5aea22` (CLI PR52) and `5fcd1684` (documentation PR55). Its delivery target
is `release-0.3.1` through [PR56](https://github.com/mycodespace-ai/devcapsule/pull/56).
The concurrent recursive-test fixture pair owns its own branch and review.

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
  [Machine-readable amd64 report](evidence/graphviz-0.3.1/linux-amd64.json).
  Its final image renders DOT to SVG, PNG and PDF as uid/gid 1000:1000,
  plus `neato` and `sfdp` to SVG, without a mounted personal installation.
  `/opt/graphviz/.build` is absent.
- New component/discovery/grouped-copy checks and the existing materialization
  tests pass. The moved catalog and loader integration tests pass: 24 cases.
  Real CLI require/offer initialization passes: two cases on the native host.
- The full gate on the combined release tree passes: 3,417 unit tests, 474
  web-console tests, types (368 files), conventions, CLI/PEX smoke and the
  documentation contract. Test conventions report 97 remaining legacy files,
  1,277 legacy tests and zero breaches. The built PEX also initializes an
  isolated project requiring Graphviz without an experimental flag.
- Live Graphviz discovery reports 16.1.1 available with no newer candidate.
- Native amd64 and arm64 build/render jobs pass in
  [Actions run 44207529778](https://github.com/mycodespace-ai/devcapsule/actions/runs/44207529778)
  on source `9b94f6c1`. The [arm64 report](evidence/graphviz-0.3.1/linux-arm64.json)
  names its exact base, source checksum, non-root identity and all five renders.
  Both matrices now admit Graphviz without `--unverified`. Hosted Python and
  website checks passed in run `44207529935`.
- PATH is contributed once per component, so composing Graphviz with agent
  components does not repeat its prefix for every build dependency.

## Remaining delivery

PR56 targets `release-0.3.1`; the human merges. Final-head CI is rechecked after
recording the native arm64 edge. No scope or implementation choice is pending.
Main propagation, candidate production and downloaded-candidate acceptance
remain release-driver work; this component validation is not candidate acceptance.

The owner's original configuration remains preserved by the named stash and
`.git/graphviz-031-preservation.json`, outside feature commits. Its original
bytes are restored after source delivery. The website branch and commit are
retained. The mistaken local Conda installation and only its own command links
were removed after the scope correction; its explicit package export remains
available for recovery. No personal installation was used by native CI.
