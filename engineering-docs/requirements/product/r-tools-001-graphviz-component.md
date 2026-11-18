---
id: R-TOOLS-001
title: Graphviz as a selectable capsule component
type: requirement
kind: concrete-requirement
status: repo-validated
priority: gating
target: 0.3.1
source_of_truth: repo
verification:
  - catalog and lock contract tests
  - offline component image build and rendering
---

# R-TOOLS-001: Graphviz as a selectable capsule component

## Statement

A project can require or offer the `graphviz` capability. Its selected component
supplies Graphviz under `/opt/graphviz`, with `dot`, `neato`, `sfdp` and the other
packaged command-line tools on `PATH`, independently of the selected IDE.
Graphviz supports the Linux amd64 and arm64 capsule platforms, including
capsules launched from supported macOS hosts.

Selection records exact source and platform dependency URLs and SHA-256 hashes
in the platform lock. Image construction uses those acquired artifacts offline.
Build-only source, development packages and package-manager state stay outside
the final installation export. SVG, PNG and PDF rendering must work in a fresh
component image without relying on a developer's `/opt/xtras` installation.

The component participates in the existing upstream availability check.
Discovery does not change component pins or installed tools automatically.

## Owner decision

On 2026-11-17 the owner clarified that Graphviz must be a reusable DevCapsule
component rather than a local capsule installation, and selected
`maintenance-031`: implementation through maintenance, targeting 0.3.1.

## Validation and limits

The maintenance status and its Graphviz implementation record retain build and
rendering evidence per architecture. An untested platform must remain explicitly
unverified; an amd64 render is not arm64 acceptance. Release publication and
downloaded-candidate acceptance remain separate release-driver tasks.

Related: R-PRODUCT-001, R-PRODUCT-002, R-CONFIG-001, R-UPGRADE-001.
