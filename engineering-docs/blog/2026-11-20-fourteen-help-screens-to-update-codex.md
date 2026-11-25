---
description: "A developer and their agent read fourteen help screens to learn how to update Codex in a capsule. Where the gap came from, why review never saw it, and what we propose to build."
---
# Adventures in How not What ...
## Fourteen help screens to update Codex



On November 19 a project owner asked the agent in their capsule to update Codex. The two of them read fourteen `--help` screens, pieced together a sequence of six commands, and still could not say whether it was right.

This is what they had to discover:

```sh
# in a terminal on the host, in the project checkout; not in the capsule, where the agent is
devcapsule project versions check                      # ask the vendor channels what is available
devcapsule project versions preview codex latest       # show what would change; prints a preview identity
devcapsule project versions select <preview-identity>  # download, build, select for the next launch
                                                       #   (plus --unvalidated if the preview says so)
devcapsule project run                                 # relaunch; the running capsule keeps the old Codex
devcapsule project versions show                       # confirm what is running
devcapsule project versions propose codex.patch        # optional: offer the update to the team
```

To the implementor, every line of this has a reason. The work order wanted updates that are explicit, reversible and never silent, and each command is one of those guarantees with a name. `check` only looks, so it is safe at any time. `preview` downloads nothing and resolves the moving label `latest` to exact artifacts, so what you select is what you were shown. `select` prepares the new set beside the old one, so a failed download costs nothing. The ordinary `run` is what certifies a set as known-good, and that is what gives `rollback` something to return to. `propose` is separate because a personal update must never edit the project's committed lock. Seen from inside the engine, this is one command per state transition, and collapsing two of them would give up a guarantee.

The user has one intent and it has one verb, which is not on the list. They are asked to drive a five-step state machine whose states they have never heard of, to copy an identity from one command's output into the next, to leave the capsule where they asked the question, and to relaunch. Nothing names the first step. Each safeguard is worth having. But the user has to go through all of them, every time, to get a newer Codex, and has to work out the sequence first from ten one-line descriptions in alphabetical order.

**TL;DR**

- Nobody wrote a wrong line. Every help string under `devcapsule project versions` is accurate. What is missing is the path between the commands, and a missing path does not show up in a diff.
- The gap is as old as the feature. The work order of September 21 asked for a "discoverable path" and gave no way to check for one. The agent that built it wrote down that the experience was unproven, and that sentence had nowhere to go.
- Three later reviews touched these commands. Each had a diff, a command group or a grammar as its scope. None had a user's sentence.
- The proposal: before a release, do on purpose what that developer's agent did by accident. Give a fresh agent the shipped executable and one sentence of intent, and read what it went through.

## What the report found

The developer's sentence was "update codex inside this capsule". The CLI has no verb called update or upgrade. The commands that do the job are listed alphabetically, so the two that silence reminders come before the two that change a version:

```text
check  defer  dismiss  follow-project  history  preview  propose  rollback  select  show
```

Nothing states that the order is check, preview, select, relaunch. The report recovered it from side remarks: `select` takes an identity "printed by preview", so preview comes first. The `component` argument of `preview` has no description at all. Nobody could tell from help whether `latest` is a valid version. And only `show` works inside a capsule, which the developer learned when `check` refused.

The answer was written down all along. The [user guide](https://github.com/mycodespace-ai/devcapsule/blob/71243a0c934f66b169d76048819021acc8cd6784/docs/updates/component-upgrades.md) gives the sequence in order, `preview codex latest` included. The `versions` help never mentions the guide, and neither the developer nor the agent went looking for one. At a terminal, help is the documentation.

## Who originated it

I went through the history expecting to find the commit where the help went wrong. There isn't one. The ten one-line descriptions in 0.3.1 are byte for byte the ones in the [first commit](https://github.com/mycodespace-ai/devcapsule/commit/4c94bbcaba15fc6a451bbf353536d14e85d65d35) of the feature, on September 21. So the question becomes how they were written and accepted that day, and three parties had a hand in it.

**The work order.** The owner and an agent wrote it [that day](https://github.com/mycodespace-ai/devcapsule/blob/4810922c646fc68be1974bb49eaffa28fa9150fe/engineering-docs/work-orders/2026-09-21-component-upgrades.md). It asked for the right thing: "Deliver a discoverable path to inspect available upgrades, try a chosen version set, and return to a locally known-good version set", with "coherent help and a short practical user guide". It handed "CLI wording" to the executing agent "without repeated approval requests", with the result "reviewed at the end". Then it spent a page on acceptance evidence for rollback, interrupted preparation and revoked permissions. For discoverability it had one sentence, and that sentence was a caution with no procedure attached: "Self-authored tests alone are not proof of a satisfying upgrade experience."

**The implementing agent.** The commit that adds the command module is stamped 26 minutes after the order's. The module's first line is `"""Discoverable project version-set commands"""`. It then proved the journey with a smoke script, and a script that runs check, preview and select in order already knows the order. An author cannot read their own help cold.

The agent knew this, and said so. Its [validation record](https://github.com/mycodespace-ai/devcapsule/blob/fa44a2fb19d84b0106a6bcf5da2ff980dbaa5eb4/engineering-docs/implementation-notes/devcapsule/2026-09-21-component-upgrades-validation.md) states that the run "does not establish [...] owner acceptance of the UX", and that its tests "establish contract behavior across those boundaries, not the subjective quality of an upgrade experience". (The elision is mine; the sentence lists three other things the run did not establish.)

**The review.** The owner merged the pull request [that evening](https://github.com/mycodespace-ai/devcapsule/commit/fa44a2fb19d84b0106a6bcf5da2ff980dbaa5eb4), under seven hours after the work order was committed: 53 files and about five thousand added lines, the scope having grown during the day to cover six components and a compatibility feed. The requirement went in with `status: implemented` and `verification: [tests, manual]`. The manual half, for the experience, was never recorded.

So the origin is the order, and the order was ours. It asked for a property and supplied no test for it. The agent delivered what the tests could prove and disclosed the rest. The review accepted what the tests proved.

## How it slept past the human review

**A diff cannot show what is absent.** Read line by line, the help is fine. "Preview one component change without downloading executables or changing selection" is true. The defect is that no line anywhere says "start here", and no reviewer is shown the lines that were never written.

**Both readers already knew the model.** "Version set", "selection" and "known-good" were settled between the owner and the agent that same day. To the two readers the help had on September 21, it was a summary of what they had just decided. The report's finding 5, vocabulary that assumes the internal model, was invisible to exactly the people who reviewed it.

**The pace.** A dozen lines of help inside five thousand lines of version-set engine, reviewed in one evening. The engine is where the risk was, and it got the attention.

**The disclosure was prose.** "Does not establish owner acceptance of the UX" sat in a validation record. It was not a bug or an open thread, and nobody owned it. Nothing in our workflow turns such a sentence into work, so it stayed a sentence.

**Every later review was scoped by something else.** On October 5 the code learned which `versions` commands run inside a capsule, declared [per command as data](https://github.com/mycodespace-ai/devcapsule/commit/eb70b3279149aff7884ff92bca0d871e68d31e2a). The help was not changed to say so. On October 24 a [review of the CLI experience](https://github.com/mycodespace-ai/devcapsule/blob/57217334e166afa1d565fef85a26b6e17bd68d29/engineering-docs/work-orders/2026-10-24-cli-ux-redesign.md) listed 23 deficiencies in `project config` and `project run`. Of `versions` it noted that one line printed a Python dict and that a flag was spelled differently from its cousin. On November 17 a [CLI syntax review](https://github.com/mycodespace-ai/devcapsule/blob/3a5aea2286c999647ffa0fe78772178291580898/engineering-docs/work-orders/2026-11-17-cli-syntax-and-discovery.md) ran all 102 help pages through the built executable. It was checking that each one printed help, and it found the one that ran diagnostics instead. A Claude session on the same model as the one writing this entry reviewed that order and did not ask the question either.

Two days later a developer's agent asked it, without meaning to.

## What we could build

These are proposals. None is adopted, and the owner decides.

**1. The cold read.** A fresh agent session has never seen the product. That used to be the expensive part of usability testing: finding a reader who does not already know. We can now have one on demand, as often as we like.

The procedure: start a session with the release executable and nothing else. Give it one sentence in the user's words. Let it run `--help` and read-only commands. Ask it for the command sequence, and keep the log: screens read, guesses that failed, questions it could not answer. The report of November 19 is exactly such a log. Fourteen screens, one failed guess (`versions status`), four undefined arguments, three open questions about the lock file. It could be a skill plus a `nox` session, and the human reads one page of transcript.

One caution. An agent is patient, and fourteen screens cost it nothing. It will usually arrive. So the measure is the effort in the log, never whether it succeeded.

**2. Intents in the work order.** An order that adds commands lists the sentences a user will say: "update codex", "go back to what worked yesterday". Each one is an acceptance item, checked by a cold read. The project keeps the list and reruns it for every release candidate, the way the 102 help pages were run.

**3. A lint for what a machine can see.** A unit test walks the command tree. Every positional argument has help text; `component` does not. Every command that refuses inside a capsule says so in its help; the code has declared this per command since October. A group above some size has an order or a typical-flow block. This is plain Python and belongs in the gate.

**4. The rendered help in the pull request.** The PR body carries the `--help` output of every group it changes. The reviewer then reads the page a user will read, in the order the user will read it, instead of strings in a dictionary.

**5. A disclaimer is an open item.** When a validation record says a thing is not established, that sentence becomes an open thread or a bug with an owner before the requirement can be marked implemented. A requirement that lists `manual` verification is not implemented until the manual part is recorded.

**6. Ten minutes for the human.** Before merging a pull request that adds a command, someone who did not write it does one task from help alone. When the only available person designed the feature, as on September 21, the cold read stands in, and the person reads its transcript.

None of this would have made the help good. It would have put fourteen screens in front of the owner on September 21 instead of in front of a user on November 19.

## About this entry

Drafted on 2026-11-20 by Claude (`claude-fable-5-2`) in Claude Code, at the product owner's request. The owner edited the title and released the entry. The source is a report written on 2026-11-19 by a project owner and the Claude Code agent in their capsule, against DevCapsule 0.3.1 at source revision `50fd91c0ea3b`. The report is not in the repository; its findings are summarized here, not quoted. Its command sequence was never executed, by its authors or by me, because a capsule mounts launcher configuration read-only. The user guide agrees with it.

The history comes from the repository: the work order (`4810922c`, 14:00 UTC), the feature (`4c94bbca`, 14:26 UTC), the validation record and guide (`e0d6cc55`, 14:38 UTC), and the merge of pull request #122 (`fa44a2fb`, 20:50 UTC), all on 2026-09-21. The size is measured from the pull request's base to its head. Those commits carry the capsule's default Git identity, and the records do not name the engine that wrote them. The syntax order of November 17 is cited at its merge into `release-0.3.1` (`3a5aea22`), which had not reached `main` when this was written.

The fix is a separate matter: a work order sent to `project-management`, first to validate a replacement design and then to build it.
