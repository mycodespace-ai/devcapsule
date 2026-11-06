# Local Workflow: The Reasons

*For humans.* This file explains [`WORKFLOW-LOCAL.md`](WORKFLOW-LOCAL.md). It
carries no rule. For each section it repeats the rule, states its intended
effect, and gives the motivation, most of which is an owner direction with a
date.

## The Two Halves

**Rule.** `WORKFLOW.md` binds where it speaks; this file binds where it is
silent; the root `WORKFLOW.md` is the source of the packaged definition.

**Intended effect.** Contributors can rely on the generic half being the same
everywhere and find the project's own facts in one place.

**Motivation.** DevCapsule is also the project that develops the generic
definition, so its root `WORKFLOW.md` is the source rather than an installed
copy. That is an exception by the definition's own rule and is recorded as
one. Everything else in the local file is what any adopting project would
record.

## Version Scheme

**Rule.** PEP 440; `X.Y.Z.dev0` between releases; the release branch's first
commit sets or confirms `X.Y.Z`; `main` reopens at the next patch; candidate
and local markers are never authored; one authored copy, mirrored by two
frontmatters, set by one command.

**Intended effect.** The source always orders correctly against the release it
works toward, and the three copies of the version never disagree.

**Motivation.** The `dev0` form is what pip and NumPy carry on their main
branches; the suffix stays `dev0` because the commit identifies the build.
Candidate builds are stamped from their tags and local builds from their
environment, so authoring either in the source would make the source lie about
what it is. One command sets all three copies and the gate checks they agree,
because a mismatch between the declaration and the definition's frontmatter is
reported as a defect by the tooling.

## Release Policy And Documentation Refs

**Rule.** The operator guide is the policy; default ref spelling; GitHub
Actions builds candidates; a resolved main disposition gates each candidate;
downloaded-artifact smoke evidence is required; a release includes its
documentation. The integration tests run before a candidate exists: the
workflow runs those it can, and for those that need a Docker daemon it
looks in the tagged revision for the record of a run, and refuses the
candidate when the record is missing, is about another revision or says
the run failed. Promote the manifest on the release branch before the final
tag and merge it to `main`. Fork `docs-<version>` at the promotion commit
with `git push origin HEAD:refs/heads/docs-X.Y.Z`. Its `docs/` tree must
match the final tag, which the final-tag job checks. These branches carry
later documentation corrections and are never merged or rebased.

**Intended effect.** A release is reproducible from its tag, its documentation
is published for its version, and a released version's guides can be corrected
after the fact without touching its source. Creating the documentation ref
before the tag lets the content check resolve the promoted manifest during
candidate validation. The download guard prevents premature publication.

**Motivation.** The documentation obligations date from 2026-09-28, when the
owner found the website unpublished since 2026-09-21 and the guides pinned to
an old version. The `docs-<version>` ref exists because the definition closes a
release branch after its final tag while the website publishes each version's
documentation from that version's own source; the branch is where a released
version's guides are corrected. It is never merged because it is not source
and never rebased because the website reads it. The candidate gate does not
apply because nothing executable changes; the website's build check does
because that is what the branch feeds.

**Rule, the throwaway copy.** Each merge of `release-X.Y.Z` into `main` is a
pull request from `4PR-NNN-release-X.Y.Z`, a branch created at the release
branch's tip for that pull request alone; nothing is committed to it and no
tag points into it.

**Intended effect.** The active release branch survives every merge into
`main`, the candidate gate's ancestry check holds because the merge commit's
second parent is the release branch's tip, and nothing that could be
deleted or mistaken for a release ref starts with `release-`.

**Motivation.** Owner decision of 2026-10-18. Since 2026-10-15 the repository
deletes a pull request's head branch on merge, and the release branch is the
one ref that must survive its merges, since it carries the cycle from the cut
to the final tag. The name reads in the order it means: a throwaway, for one
pull request, made off that release branch; the order matters so that no
branch of the kind begins with the `release-` prefix the definition reserves.
The first copy of the 0.3.0 cycle was spelled `release-0.3.0-4PR-1` before
the order was fixed. The copy is an integration ref, never a release ref,
which is why nothing is committed to it and why the candidate workflow looks
only at `release-X.Y.Z` when it checks a tag.

Rule 9 is from 2026-11-06. Until then the Docker-backed proofs ran only
at the final acceptance, against the downloaded final candidate, so every
candidate before it was published with integration tests nobody had run,
and a candidate is what testers download. The owner's rule is that a
candidate is not produced without them, and since the hosted runner may
not run Docker, the proof of a run elsewhere must be something the
workflow can find in the source it is building. A record in the tagged
revision, naming that revision, is the simplest such thing: commit the
record, then tag; change anything after, and the record names the wrong
revision and the workflow says so. The workflow's own run of the
Docker-free tests stays, since a run on the hosted runner is the stronger
evidence of the two.

## Blog Entries

**Rule.** On request, write a dated entry under `engineering-docs/blog/` with
the blog front matter, attribute quotations, link evidence by mainline SHA, and
index it.

**Intended effect.** The human's request supplies the topic and occasion, and
the website picks the entry up without further ceremony.

**Motivation.** The website reads the date from the filename and the draft flag
from the front matter, so those two facts are the only website-specific
requirements. Mainline SHAs keep evidence links stable when branches are
deleted. There is no proposal, schedule, or approval procedure because the blog
is the owner's voice, released by the owner.

## Validation Commands

The 0.3.0 CI order adds advisory changed-line coverage to the existing serial
unit suite. Use the PR's actual target when comparing; low coverage informs
review without blocking it. Test and reporting failures still block their
checks. Parallel execution is deliberately deferred beyond 0.3.0.

**Rule.** Every command runs from `devcapsule-src` in its `.venv`; the kinds
are the definition's; each has a command runnable as written; the gate is
`nox -s build`. An integration test runs a subsystem with the real things
it uses, the executable, a subprocess, git, the Docker daemon, and fakes
what it is not testing; it runs on demand, and a test that needs the
daemon says so with a marker; the type check and the documentation
contract are checks of the gate, not tests.

**Intended effect.** Any agent on any machine can build and test the project
without guessing, and "the tool is missing" is a finding only after following
the section.

**Motivation.** The definition makes this section required because it is what
lets a contributor act without asking. The `.venv` is the only place the tools
live so that a check never depends on what else is installed. The `/tmp`
remark exists because a capsule's `/tmp` is a 2 GB tmpfs that the gate's
scratch overflows, which cost a resumed session a failed gate before the cause
was found.

The integration sentences are from 2026-11-06. Until then the guide said an
integration test crosses a packaging or process boundary without Docker,
and counted the type check and the documentation contract among them.
The owner found the ordinary meaning better: a subsystem tested together
with the real services it uses, some of them faked when they are not what
is being tested. Docker had got into the definition because the hosted
runner has no daemon the project trusts, which is a fact about where the
gate runs, not about what an integration test is. A test of the image
build against the real daemon with a Dockerfile the test wrote, or of a
container start from an image named by digest, is an integration test;
building a real base is not, because it is slow, reaches the network and
does not give the same answer twice. The marker exists so the candidate
workflow can leave the daemon tests out without anyone editing a list.

## Unit Tests

**Rule.** A unit test file is named after its module and mirrors the
package tree; a test is a precondition it establishes, one call to a public
operation, and a postcondition the unit promises; every test says in a
docstring what contract it tests; existing files are marked legacy and only
shrink, a touched test is fixed and moved; the gate checks what a machine
can check and the reviewer checks the rest. A unit test's result depends
on nothing the test did not build: not the clock, not another process,
not a service, local or remote, not the host it runs on. A unit that needs
the time is handed the time. A test starts another program only when
running that program is the unit's job, and then with inputs the test
chose. What the test can work out in its own process, a digest of a file
it just wrote for instance, it works out there. A test that needs a
program for what the program does is an integration test and runs on
demand.

**Intended effect.** A reader sees which unit a test tests from its path
and what it tests from its first line. A test fails only when the unit
breaks its contract, never because a release moved, a lock was regenerated,
or the capsule that runs it has already accepted a vendor's terms. The
same test gives the same answer on a laptop, on the hosted runner and
inside a capsule, at noon and at midnight, with Docker and without. When
it fails, the unit broke its promise, and the reader knows which unit.

**Motivation.** On 2026-11-03 the gate failed eighteen tests in the owner's
own capsule. None was a bug. Thirteen read the owner's accepted trust
record through the launcher's mounted settings, because the isolation
fixture moved the home and the product's fallback did not know. Four
asserted the repository's own lock, byte for byte, down to the release
candidate that built the base. One scanned every file under `tests/` and
found a forbidden word inside a sample project's virtualenv. These tests
had been written by three different models under pair review, and the
reviewer had named one of them "the right test". A test that copies the
value it finds is a change detector, not a contract: both a bug and an
intentional change fail it, and the fix is always to update the string.
The triple forces the precondition into the open, which is exactly what
the thirteen had left to chance. The mirror makes the unit obvious before
the first line is read. The legacy marker turns 1525 existing tests into a
debt that is paid at the moment someone is already in the file, rather than
a rewrite nobody will order. The gate carries the mechanical part because a
rule an agent must read is a rule an agent can skim.

The isolation sentences were added on 2026-11-06, when the owner and the
agent compared notes before repairing those tests. The oldest example
is from 2026-09-22: a test of the coordination claim failed on the hosted
runner and passed on the rerun, at the same revision. It called the claim
operation twice and expected the second call to change nothing. That is
true when both calls fall within the same second and false when they
straddle one, and a git subprocess runs between them. The operation
already took the time as a parameter; the test had not used it. The owner
declined a quick fix and kept the test as a sample of how not to test.
The thirteen of 2026-11-03 are the same mistake with a different hidden
input, the trust record of the capsule that ran them. Hence the general
form: anything that can change the answer is an input, and a unit test
either sets it or the unit never reads it. The line on other programs
is drawn by two questions, does the test control every input of that
program, and is running it what the unit is for. A digest of a file the
test wrote passes the first and fails the second, so it is computed in
process. Git on a scratch repository can pass both, and even then its
commit dates come from the clock unless the test sets them. A Docker
build passes neither.

## Reasoning And Code Navigation

**Rule.** Start from the contract, state the uncertainty, navigate from the
entry point, search by pattern only as a last resort and say why, and never
treat a match as proof.

**Intended effect.** An agent reads the code that answers the question rather
than the code that matches a word.

**Motivation.** Pattern searches are cheap and feel productive, and they are
the most common way an agent convinces itself that a contract holds when it
has only found a name. Reasoning from the contract first makes the code read
targeted, which is both cheaper and more reliable.

## Publication Refs

**Rule.** `component-status` and `badges` are generated branches their actions
advance by fast-forward; never a workstream, never merged, never force-pushed;
nothing generated is committed to `main`.

**Intended effect.** The compatibility feed, the status page and the coverage
badge publish without a human and without touching `main`, so every
first-parent commit on `main` is a pull-request merge.

**Motivation.** A generated branch that anyone could select as a workstream
would eventually receive authored commits; keeping it out of the workflow's
vocabulary keeps the action the only writer. The badge moved off `main` on
2026-10-15 by owner direction: its direct pushes were the one thing that
prevented a repository rule requiring pull requests on `main`, and they
interleaved single-parent commits with the merge record.

## Host Capabilities

**Rule.** The `[host.*]` tables declare what the checkout needs with
justifications; the coordination baseline records the hosting facts.

**Intended effect.** Every host access this project takes is declared and
justified in one place.

**Motivation.** The product's own containment model asks adopters to declare
host access; the project holds itself to the same rule.

### Dogfooding CLI Selection

**Rule.** The configuration recommends `devcapsule0`; the shipped runtime is
`devcapsule0` and the development installation is `devcapsule`; use each
deliberately; never fall back silently.

**Intended effect.** A test against released behavior and a test against
current work are never confused.

**Motivation.** Owner direction of 2026-09-24. A development capsule that runs
inside DevCapsule has two launchers available, and a silent fallback from one
to the other is how a passing check stops meaning anything.

### Keep The Development Checkout Launchable

**Rule.** Commands are the only writers of configuration; validate with the
running `devcapsule0` before and after any change; an inspection is not a
validation; self-hosting is a managed exception with an identifiable baseline
and an independent recovery path; 0.3 distinguishes mandatory from optional
needs.

**Intended effect.** The shared checkout can always be launched by a known
launcher, and a contribution from a newer launcher degrades gracefully rather
than breaking older ones.

**Motivation.** On 2026-10-04 a component commit changed the shared need and
lock and made the checkout depend on a launcher that had not shipped; the
owner recovered by hand with an incidental build. The 2026-10-05 correction,
"be liberal in what we accept and conservative in what we produce", reframed
compatibility as a contract between contributors with different launchers
rather than a frozen vocabulary. Command-only writes exist because a hand edit
can produce a document no command would have written and no reader can
explain. The validation steps exist because the running instance is the only
launcher known to work. The inspection remark exists because `config list` was
mistaken for a validator. Rule 9 is R-CONFIG-001, now implemented on `main`.

### Local Launch Networking

**Rule.** Host networking for local development and release-validation
launches, as standing authorization; declared network modes in tests stay;
record any fallback.

**Intended effect.** Local launches reach host-bound development services
without a permission dialogue every time.

**Motivation.** Owner direction of 2026-09-24. The authorization is standing
because asking for it on every launch is ceremony without information; it is
local because the product's defaults for other projects are a separate
decision.

## GitHub Integration: The CLI When The Human Provides It

**Rule.** If the human has put GitHub's CLI at
`/opt/xtras/miniconda3/envs/gh/bin/gh`, the agent activates it through
conda's bootstrap script in each shell call, checks once per session that it
is logged in, and then opens, updates and consults pull requests and posts
reviews as comments; a failed login check stops the agent and asks the human
to log in. If the CLI is absent, the human does GitHub, and the agent hands
over the compare link from which one click opens the pull request. Merging
stays the human's either way.

**Intended effect.** Pull-request work happens from the capsule when the
tool is there, without the agent probing for credentials, and degrades to
a one-click handoff when it is not. An expired token is reported, never
worked around.

The details have reasons. Activation is repeated in every shell call because
shell state does not persist between an agent's calls, and the owner forbids
the usual `conda init` edit of the shell profile. Detection is a file test
because the earlier rule was made to stop agents probing for tools. Reviews
are comments because GitHub refuses the approval of a pull request opened
under the same account, which every pull request here is. The compare link
is the one-click path GitHub offers to open a pull request between two
branches.

**Motivation.** Owner direction of 2026-10-21, replacing the direction of
2026-09-21 made when no `gh` installation existed and probing for one wasted
sessions. Since 2026-10-08 the owner had been installing `gh` in the
checkout's extra tools and directing agents in chat, session after session,
to use it; the rule makes that standing. It names the exact path so that
detection is a file test, not a search. It is a local arrangement, a hack of
this project's own, until the GitHub CLI is a proper DevCapsule component.

<a id="review-partners-in-this-checkout"></a>

## Pair Review Loop In This Checkout

**Rule.** Apply the Pair Review Loop, or Pair Review, in this checkout.
The engines are the three agent command lines signed in once in the
capsule; a pair is named by engine and model; the review partner gets a
worktree under `~/worktrees`, its own venv and its own gate scratch; it runs
detached with the brief as its prompt, in the recorded form for its engine;
the GitHub CLI rule applies to it; assessment comments carry one of two
labels; briefs are committed under the workstream's evidence; the developer
document holds the template, the recipes and the record.

**Intended effect.** A human can say "implement this with Pair Review,
with that engine as the review partner" and any of the three agents
can run it from the files alone, with the same artifacts as the loops that
came before.

**Motivation.** Owner direction of 2026-10-22, after the agent was asked to
extract the mechanism from the sessions of 2026-10-09 to 2026-10-12. No API
key is used because the capsule's agents are signed in once by the human and
read the repository as their context; the process record of 2026-10-12 lists
the trade-offs against API clients. The worktree exists because the reviewer
must not disturb the implementor's checkout, and the separate scratch because
two gates in one scratch corrupt each other. The Codex form is the one every
loop so far ran; the Claude form was smoke-tested on 2026-10-22; the
Antigravity form is read from its help and is recorded as unproven so that
the first pair to run it knows to verify and record it. The briefs are
committed from now on because the earlier ones lived in a session scratchpad
and died with the capsule, which is why the template had to be rebuilt from
transcripts.

## Commit Authorship

**Rule.** The human's author identity with a `Co-authored-by` trailer per
contributing agent, naming the actual model; verify before pushing; no
rewriting of merged history.

**Intended effect.** Authorship reflects who directed the work and which agent
contributed, and attribution is honest about the model.

**Motivation.** Owner direction of 2026-09-22. Pushing credentials and the
person who clicks merge are not authorship. The model name is read from the
active session because configured defaults and prior sessions have produced
wrong attributions.

## Workflow Definition Changes

**Rule.** Every change to the definition or the local file is written in the
controlled style, in the topic it belongs to, with its reason in the humane
companion in the same commit, a *Changes* entry for every change of meaning,
the parsed headings kept, and the packaged copy regenerated at the release.

**Intended effect.** The rule files stay short and uniform for agents, the
reasons stay complete for humans, and the two never drift apart.

**Motivation.** Owner direction of 2026-10-09, taken the day the
controlled-language edition merged to `main`. The same-commit rule is the
hand-operated form of the dependency that topic 12.12 of `WORKFLOW.md`
describes; when the web console's view registry tracks a paragraph's
dependency on its rule and marks it stale, the rule relaxes to keeping that
dependency fresh. The edition cut the agent's
required session-start reading by about a quarter and the share of sentences
over twenty words from a third to a tenth, while a fidelity quiz answered from
the new text alone came back complete. Those gains last only if every later
change keeps the split; a single reason written into the rule file is the
first step back to the mixed prose the edition replaced. The same-commit rule
exists because a companion paragraph added later is a paragraph never added.
Regeneration at the release matches the definition's own rule that the version
is the release: adopters receive the edition that shipped. The owner took this
decision in project-management, low ceremony, although the subject is
`workflow-improvements`' business, because the rule had to exist before the
next definition change rather than after it.

## Integration Method And Exceptions

**Rule.** Merge commits since 2026-10-03, enforced by the hosting platform
since 2026-10-15 together with head-branch deletion on merge; the recorded exceptions:
release-fix propagation by judgment, the root definition as source, two
adoption exceptions, and pre-`ws-` branch names.

**Intended effect.** Every departure from the generic rules is visible, dated,
reasoned, and has an end condition.

**Motivation.** The synchronization of `release-0.3.0` with `main` during
the cycle, on 2026-10-22 twice, each on the owner's word, exists because the cycle produced workflow rules on `main`,
the GitHub CLI rule and the Pair Review Loop, that the release checkout
must follow too, and `main` had received nothing else outside the
candidate process; the merge kept the release version where `main` carries
the next development version. The release-fix exception exists because the generic rule's
blanket merge-only policy would hold unrelated work back or leave `main`
without a fix; the owner ruled on 2026-09-22 that engineering judgment chooses
merge, cherry-pick, or evidence that `main` lacks the bug, with the disposition
recorded on the bug. The adoption exceptions record history rather than
rewriting it. The branch-name exception records a migration the owner deferred
past 0.2.14 so that candidates were not held for a rename. The platform
enforcement and head-branch deletion came on 2026-10-15, when the owner
settled that a merged branch's record is its merge commit: the second parent
is the merged head and the message names the branch, so the branch itself is
deleted without loss and the branch listing stops growing.
