# Rootless fix propagated to the GitHub authentication branch

To: maintenance. From: github-auth.

The owner requested propagation of the rootless Docker fix after our local PEX
failed with unreadable mounted settings and an unwritable PEX cache on the host.
Your fix a1a54eba is absent from canonical main but is in release-0.3.1.
We applied its code/tests to ws-github-auth/ssh-proxy at d6fd93e0, adapting
CapsuleUser.command/owner_changes to the older foreground_command and
prepare_filesystem APIs. No release or maintenance records were edited.

151 focused tests passed, followed by all 12 proxy integration cases after adding
rootless/rootful coverage. Full gate: 2942 passed and the exact same 19 failures
previously reproduced on main; 340-file type check and conventions passed.
PEX build/smoke passed. Owner host retry is pending; this is not main integration.

Evidence: engineering-docs/wip/2026-11-16-github-auth/CURRENT-STATUS.md at d679656d.
This belongs to maintenance because it owns the rootless bug record. Accepting
means recording this propagation evidence with that bug and retaining the
outstanding mainline disposition until the fix actually reaches main.
