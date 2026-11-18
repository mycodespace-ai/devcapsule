# Work item: the GitHub CLI as a component

Sent: 2026-10-09

From: `project-management`, to `component-catalog`. Owner direction taken in
this checkout on 2026-10-09. Items from `project-management` are routing
decisions; raise disagreement with the human rather than forwarding.

## What is handed over

Make the GitHub CLI, `gh`, a DevCapsule component, so that a capsule can carry
it without manual installation. Today `gh` exists in two checkouts only, hand
installed through a conda environment under `/opt/xtras`, and the install
path asked the user to page through and accept a terms-of-service text. The
owner wants agents and humans to open, comment on and merge pull requests
from inside a capsule without that ceremony.

## Evidence

- `gh` is MIT licensed, copyright GitHub Inc. The licence grants the rights to
  use, copy, publish, distribute and sublicense. Redistribution of the binary
  is permitted; the licence text and copyright notice must travel with it.
  Source: `https://raw.githubusercontent.com/cli/cli/trunk/LICENSE`.
- Upstream publishes, per release, a plain tarball and a checksums file with
  no installer and no interaction. For v2.102.0:
  `gh_2.102.0_linux_amd64.tar.gz` (15.3 MB), `gh_2.102.0_checksums.txt`,
  plus `.deb` and `.rpm`. The tarball holds a single static binary at
  `bin/gh` and man pages. Source: `https://github.com/cli/cli/releases`.
- The terms-of-service prompt the owner met belongs to Anaconda's default
  channels (`conda-anaconda-tos` plugin, 2025), not to `gh`. The copy here
  came from `conda-forge`, which has no such terms; the prompt fires for the
  conda installation as a whole. Without conda there is no prompt.

## What accepting means

1. A component with the GitHub releases as its discovery channel, a pinned
   version with the sha256 from the checksums file, the tarball as the
   artifact, and `bin/gh` on the path. Carry the MIT licence text with the
   component.
2. A capability name for it, proposed `github-cli`, local-selectable like an
   agent. The owner has not said whether it is also a project optional; the
   default is a developer-local choice.
3. The authentication design, which is the real work: `gh auth login` is
   interactive, and a token must survive capsule restarts and never land in
   configuration or records. Treat it like the agent consent and secret
   bindings the configuration contract already has. State the chosen shape
   in the component's implementation note before the first smoke.
4. A smoke that proves `gh auth status` and one read-only API call from inside
   a fresh capsule, with the token supplied through the chosen binding.
5. The local workflow's *GitHub Integration: Owner Through The UI* section is
   stale since the owner's 2026-10-08 direction to use `gh`; it is the
   owner's to reword and is not part of this item. Do not change it here.

## Why it belongs to you

An IDE or a tool is a component, and `component-catalog` accepts and tests new
components, by the owner's routing rule of 2026-10-01. No release target is
assigned; the 0.3.0 scope decision is still open in project-management, and
this item's position in your order of work is yours to record.
