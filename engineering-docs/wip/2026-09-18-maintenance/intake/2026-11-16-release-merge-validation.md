# Release 0.3.1 validation after full merge into github-auth

From: github-auth
To: maintenance
Date: 2026-11-16

The owner requested the entire release-0.3.1 branch be merged into github-auth,
not just the earlier adapted rootless fix. Merge 7fc77f24 has second parent
10e7fda3d0487ad57d2e440bf9ce67e32634ae08. The combined unit suite has 3309 passes
and three failures; types (350 files), conventions, CLI smoke, docs and all 474
web-console tests pass. Integration has 149 passes, 12 skips and three initial
failures; one was our overly long basetemp and passes with a short path.

Please acknowledge the remaining release-owned validation work. All five IDs below
were reproduced against an untouched git archive of release tip 10e7fda3 in the
same rootless capsule. The print-command case used a separately built PEX from
that archive, v0.3.1-local-linux-x86_64. No tests were disabled or weakened.

## Unit cases (also present before the merge)

- tests/test_host_daemon.py::test_unmountable_staging_fails_loudly:
  expects PycharmRunError but none is raised under the current persistent-home
  scratch path. This is a fixture/path assumption to investigate.
- tests/test_recursive_orchestrator.py::test_public_dry_run_is_unique_redacted_and_cleans_owned_staging
- tests/test_recursive_orchestrator.py::test_contained_display_dry_run_forwards_no_host_x11
  Both dry-run cases create sockets with gid 0 inside the rootless capsule;
  recursive_host._positive_id rejects their host Docker group ID.

## Integration cases

- tests/integration/test_print_command_cli.py::test_print_command_names_a_base_image_that_is_not_here_and_pulls_nothing:
  expected Docker calls all to start with 'image inspect ', but the rootless fix
  also runs 'info --format {{json .SecurityOptions}}'. The separately built
  unmodified release PEX produces exactly the same failure. Decide whether to
  defer the identity query or update the read-only-probe contract and its oracle.
- tests/integration/test_runtime_entrypoint_cli.py::test_filesystem_applies_distinct_user_and_group_ids_to_new_directories:
  the fixture treats UID 0 as permission to chown to gid 1. This capsule is root
  inside a user namespace with dropped capabilities and cannot perform it.
  The subprocess returns PermissionError at filesystem.py:68. Test setup must
  establish the capability or the test must run in a suitable declared environment.

## Reproduction and evidence

Use the declared devcapsule-src working directory and virtualenv. A short
PYTEST_ADDOPTS basetemp such as /home/devcapsule/.cache/gm avoids AF_UNIX path
length failures. The unit gate ran with DEVCAPSULE_DIFF_BASE=upstream/main.
The integration session was nox -s integration. The untouched-release snapshot
selected these exact five IDs; only the print-command test needed its built PEX
via DEVCAPSULE_PEX_UNDER_TEST. Source/PEX provenance and local logs are in the
github-auth status under Full release merge. Source changes are not included in
this mail; maintenance owns the disposition. The proxy's 12 integration cases
and the merged identity/filesystem/authorization focused slice passed.
