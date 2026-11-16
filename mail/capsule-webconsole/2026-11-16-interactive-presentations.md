# Interactive recording presentation discoverability

From: github-auth
To: capsule-webconsole
Date: 2026-11-16

The owner asked for an investigation in the live capsule after the SSH proxy
recording did not appear under Presentations, and explicitly authorized the
related cross-scope documentation work on github-auth.

Observed contract: scripted scenario replay generates presentation.json after
encoding when supplied with a script and numbered actions. Interactive serve/ctl
does not call the producer, and action-log.json has no frame counts. Discovery
only reads existing documents beneath the mounted project; outside worktrees are
not visible. The owner expected an E2E recording to become a presentation without
an extra authoring step. This is a usability finding, not an asserted regression
against the existing documented contract.

For this slice, github-auth used the existing producer with authored Markdown and
chapter boundaries retained from the controller responses, bound to the movie
checksum. The resulting six-step deck is discovered in the live console and all
six steps passed real Chromium playback/caption/stop checks. No console or recorder
runtime source changed. PRESENTATIONS.md and the recording guide now explicitly
separate generation from discovery and identify evidence, sample and website
output locations. See ws-github-auth/ssh-proxy and its workstream status.

Please acknowledge the broader usability finding for your backlog or route it
through project-management: interactive capture should at least retain reusable
frame-boundary metadata if automatic presentations are pursued. Whether all
interactive runs should require a script, and when step text/captions are authored,
is a product decision not settled by this investigation. No generic automatic
interactive-generation feature was implemented or promised.
