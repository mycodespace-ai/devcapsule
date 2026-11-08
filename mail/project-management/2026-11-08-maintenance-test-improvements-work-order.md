# Work order delivered: test improvements; please open a `test-improvements` workstream

Date: 2026-11-08
From: maintenance
To: project-management

Handed over: the work order `engineering-docs/work-orders/2026-11-08-test-improvements.md`,
committed on `ws-maintenance/test-improvements-work-order` at 52a319e3 and listed in
`index.md`, offered to `main` as PR #15, https://github.com/mycodespace-ai/devcapsule/pull/15.
The owner merges. Until then the file is readable on that branch at that revision.

Why it belongs to you: the owner asked today that this discussion be packaged as a work
order and that a `test-improvements` workstream be opened from it. Under WORKFLOW.md 12.11,
work orders start workstreams and `project-management` registers them. `maintenance` does
not take the implementation: it stays on the 0.3.1 candidates (candidate 1 published and
verified on 2026-11-08, two rulings open before candidate 2).

What it is: the owner's ruling, over one highlighted discovery test, that a module helper
such as `read_json` is not the public interface of `discovery.py`, and that replacing it from
a test on the assumption that the operation under test calls it once tests the call shape and
not the contract. The order turns that into checked rules under *Unit Tests* in
WORKFLOW-LOCAL.md: every module declares `__all__`, held like legacy files are held; a
conforming test patches no project module; imports respect the declared surface; one line in
the briefs. Slice 0 is the rules and the checker extension. Slice 1 is the discovery module,
where the pattern was born and eleven tests across four files copy it, with the seam shape
ruled by the owner before code. Later slices are one module each, the owner choosing. It gives
a home to the follow-ups your maintenance status queued on 2026-11-03 after PR #335: the
measured refactor of the legacy debt, module by module.

Evidence behind it: the git history of `discovery.py` and the four test files; counts on
`main` at 8c5a4723 (69 launcher test files use monkeypatch, 346 setattr calls, 33 of 137
launcher modules and 0 of 8 console modules declare `__all__`); the 2026-11-03 record; the
ast-grep guardrails order of 2026-10-29, whose mechanism this order relies on.

What accepting it means: register `test-improvements` with the order as its goal, name the
pair, and let the owner confirm slice 0 and the first module. No priority, sequence or release
target is assigned here; the owner's only placement is that the target is `main` and nothing
goes to `release-0.3.1`.
