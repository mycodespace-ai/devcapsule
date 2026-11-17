# Keep chat progress updates; close product supervision proposal

From: project-management
Date: 2026-11-17

The owner chose C: keep the main agent watching and reporting the separately running agent through chat. Reconcile any missing generic progress-reporting guidance with existing workflow rules. The proposed DevCapsule agent-launch/tracking command, Agents page and inactivity notifications are not selected; no agent-supervision workstream is to be opened.

Source: owner console answer at 2026-11-17T01:17:38Z.

## Original Intake

# Agent run supervision: a cooperating agent's progress, visible to the human

Date: 2026-10-28
From: maintenance, at the product owner's request
To: project-management
Status: a work order to scope and place; one part is done, two parts are product work

## What is handed over

A work order in three layers for one problem: when two agents cooperate on
a task, as the review-partner loop of `WORKFLOW.md` topic 9.11 has them do,
the human cannot tell whether the detached partner is making progress. The
owner asked for it on 2026-10-28, during the VS Code slice (PR #301, review
PR #302), after the Antigravity review partner ran for 36 minutes in print
mode with an empty log: print mode speaks only at the end, and the only
signals were the engine's own log under `~/.gemini/antigravity-cli/`, the
review worktree's commits and nox environments, and the pull request list.
The owner's rule, recorded the same day in `WORKFLOW-LOCAL.md` (*Review
Partners In This Checkout*, item 8): whenever two agents cooperate, the one
connected to the human pushes updates to where the human reads, the chat
or the terminal of that session.

## Layer 1, done on 2026-10-28, in the workflow records

Every recorded invocation form of the loop adds the engine's streaming
output, so the log carries one event per step while the partner runs:
Antigravity `--output-format stream-json`, Claude Code
`--output-format stream-json --verbose`, Codex `--json`. The implementor
tails the stream and reports in chat when the partner starts, what it
commits, when its gate runs and when it ends. Recorded in `WORKFLOW-LOCAL.md`
item 4 and 8 and in `engineering-docs/development/review-partner-loop.md`
(the shape, step 3; the streaming forms). The next loop proves the forms.
Nothing here is product code; project-management decides whether the
generic half of the rule belongs in the definition, topic 9.11.

## Layer 2, product: DevCapsule owns the run

A command, provisionally `devcapsule agent run`, that launches a partner
detached in a named worktree with a brief on standard input, keeps its
event stream under the session's log directory beside the launcher's and
the supervisor's files (the session-log contract of 0.3.0), and records
the engine and model, the branch, the brief's path and the pull request it
produces. The diagnostics snapshot and export (`project diagnose`) carry
the agent's trajectory the way they carry the other session logs. The
three engines on the capsule's PATH are the first adapters; the form each
one needs is the one recorded in `WORKFLOW-LOCAL.md`.

## Layer 3, product: supervision in the web console

An *Agents* page from that stream, beside the processes page: alive or
ended, elapsed, time since the last event, the last tool call or command,
commits on its branch, the pull request link. A stall rule, no event for N
minutes with the process alive, posts through the existing checkout
notifications so the console's bell rings and the implementor relays it.
The human then reads progress in two places that already exist, the chat
and the console, and the partner's log stays evidence.

## Placement

Layers 2 and 3 are not 0.3.0 work; the owner said so when ordering this
item. They touch the session-log contract, `project diagnose` and the web
console, which the capsule-webconsole and maintenance workstreams own
between them; project-management places them and names the implementor
and the review partner. The acceptance evidence for both is a loop run
under them, with the human reading progress without opening a log.

## Evidence read before writing

The loop record of 2026-10-28 in `review-partner-loop.md` (#301/#302); the
Antigravity CLI's `--help`, which lists `--output-format text|json|stream-json`
and `--print-timeout`; the session-log and diagnostics contracts as shipped
in the 0.3.0 candidates; the notifications path `checkout notifications
post`, used by the console's bell.
