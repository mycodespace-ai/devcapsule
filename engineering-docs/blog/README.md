# The DevCapsule Development Blog

Entries about developing DevCapsule that are worth a wider audience than
the engineering records: how a decision was reached, what a bug taught,
how a human and an agent divide the work. The product owner opened this
folder on 2026-09-06 with the view that the development of DevCapsule is
an exercise as valuable as the software itself.

For the simple file conventions, see
[Blog Entries in the local workflow](../../WORKFLOW-LOCAL.md#blog-entries).

Every entry begins with a YAML front matter block carrying `description`,
one sentence of at most 200 characters that the website shows as the
entry's summary, and `draft: true` while the owner has not released it;
a draft is excluded from production builds and shown labelled in preview.
Nothing else framework-specific belongs in an entry. The block is authored
here, per [R-DOCS-003](../requirements/product/r-docs-003-website-content-carries-front-matter.md).

## House style

An entry is written for a reader, not for the record. Five rules, from the
competitive comparison of 2026-10-18, whose first copy opened with twenty
lines of provenance:

1. The first screen says what the reader gets: a lede of at most two
   sentences, and a **TL;DR** when the entry is long.
2. Provenance, method, versions and status go at the end, in a closing
   *About this entry* section. Nothing of that kind sits above the fold.
3. The entry is written in a person's voice. The controlled-language rule
   of the workflow applies to records, not here.
4. The agent drafts and the owner edits. An entry is not released until
   the owner has made that pass; `draft: true` until then.
5. A copy of an engineering record is a draft, not an entry. Restructure it
   for the reader first, and offer the cuts rather than copying the whole.

## Entries

- [Diagnosing a capsule from both sides](2026-10-28-diagnosing-a-capsule-from-both-sides.md) — why a port check misses a frozen browser desktop, how `devcapsule project diagnose` probes a live session from outside and inside a nested PyCharm capsule, and a 29-second recording; draft for owner review.
- [Where DevCapsule sits: a competitive comparison, October 2026](2026-10-18-where-devcapsule-sits.md) — the time-boxed, best-effort comparison with agent sandboxes, dev containers and cloud agents, each shortcoming linked to its roadmap item.
- [An AI takes our IDEs for a test drive](2026-10-04-an-ai-takes-intellij-for-a-test-drive.md) — IntelliJ, .NET/Rider and Eclipse, two desktop fixes caught in screenshots, and three original test movies; draft for owner review.
- [The workflow explains itself](2026-10-03-the-workflow-explains-itself.md) — a preamble for adopters, an information model for people, a merge rule, and a bug filed against ourselves; draft for owner review.
- [What I have been up to lately](2026-09-30-what-i-have-been-up-to-lately.md) — the LinkedIn announcement of 2026-09-28, reproduced for linking from shorter-limit channels.
- [Why give DevCapsule a spin before V1?](2026-09-21-why-try-devcapsule-before-v1.md) — invitation to early adopters and contributors; draft for owner review.
- [Lessons learned in AI autonomy — Part 2: the AI perspective](2026-09-19-lessons-learned-in-ai-autonomy-part-2.md) — Astra's account of the website experiment; draft for owner review.
- [Lessons learned in AI autonomy over a simple, straightforward task](2026-09-19-lessons-learned-in-ai-autonomy.md) — website experiment retrospective; draft awaiting owner editorial review.
- [When should a tool refuse? Taking stock of DevCapsule's refusal UX](2026-09-06-when-should-a-tool-refuse.md)
- [I asked for user docs](2026-09-16-i-asked-for-user-docs.md) — second entry, first-person version reviewed by the product owner.
- [Does the subscription include Navier–Stokes?](2026-09-16-does-the-subscription-include-navier-stokes.md) — alternative second entry: Costin and his AI partner Astra as golf-course buddies.
