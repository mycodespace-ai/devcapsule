# Review brief: CLI syntax work order

Reviewer requested by owner: Claude `fable-5.2`.
Scope: read-only review of `engineering-docs/work-orders/2026-11-17-cli-syntax-and-discovery.md`.

Read the work order in full. Read the required repository orientation files.
Inspect relevant existing CLI adapters and consumers only where a concrete uncertainty needs evidence.
Do not implement, edit, commit, push, create a PR, launch a container, or send coordination mail.
This is a document review, not an implementation pair-review PR loop.
Do not run the full gate. Your environment is available if needed for read-only inspection.

The owner's decisions and strict syntax-only boundary are binding.
The user wants a smaller CLI with modifiers and advanced help; do not substitute your preferred design.
The earlier six-question questionnaire was rejected; its recommendations were not adopted.

Find contradictions, vocabulary problems, missing dispositions, and hidden behavior changes.
Pay particular attention to instance versus host checkout operations, global configuration,
the installed recording skill after removing presentations, detailed JSON, generic console links,
explicit project selection, and internal consumers of renamed commands.
Report only concrete issues with motivation and a recommended decision.
Distinguish product choices from editorial corrections and routine implementation choices.
Say what can proceed and what must wait. Do not exaggerate hypothetical compatibility risk.
Give a concise review in your final response, citing source paths where useful.
State the model identity that actually ran; do not infer it from the requested name.

For later implementation review, local Unit Tests rule 7 requires assessing test conventions,
behavioral value, and isolation; this review writes no tests and makes no claim of test validation.
GitHub is not needed. If later requested, activate the supplied CLI environment:
`source /opt/xtras/miniconda3/etc/profile.d/conda.sh && conda activate gh`.

Review against the work order as written, then give your own judgment.
