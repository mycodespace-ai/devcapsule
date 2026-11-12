---
status: confirmed
severity: minor
target: none
owner: maintenance
opened: 2026-10-29
requirements: [R-COMPAT-001, R-CONFIG-001]
---

# An old lock keeps the replaced IDE beside an ordinary IDE override

## Symptom

Found by the review partner of PR #304 (Codex, gpt-6-astra, PR #306) on
2026-10-29, with the v0.2.11 compatibility fixture
`devcapsule-src/tests/resources/compat/v0.2.11`. The fixture's project
declares `python-ide` in the schema-1 `need` list, so the launcher reads it
as a recommendation, and its lock pins PyCharm from before provider
evidence existed. An ordinary override, `project run --ide codium` with no
`--force` and no requirement conflict, ends with status 2: the usable lock
keeps PyCharm beside Codium, and the catalog refuses two interactive
surfaces. A temporary Codium case added to
`test_schema_one_ide_in_need_launches_without_rewriting_manifest`
reproduced it; the committed test covers the current-lock path only.

## Cause, as far as read

`usable_lock` in `configuration/capability_selection.py` returns a lock
without provider evidence unfiltered when the policy has no optional
capabilities and no minimums: "old locks remain records, not requests to
re-resolve". The checkout's pins lay Codium over such a lock in
`compose_lock`, which never removes superseded components, so PyCharm stays
in the components table and reaches the catalog. This rule predates
PR #304; `git show release-0.3.0:devcapsule-src/devcapsule/configuration/capability_selection.py`
shows it unchanged.

## Severity

Minor, by the owner's rating on 2026-10-30: it reaches only checkouts whose lock
predates provider evidence, and a plain launch on them still works.

## Expected

An ordinary IDE override on a project whose lock predates provider evidence
launches the chosen IDE alone, as it does on a lock with evidence.

## Notes

Out of the scope of PR #304, which the reviewer left as a proposal. Rating
the severity is the owner's first job; a fix belongs to a compatibility
slice of `maintenance`.
