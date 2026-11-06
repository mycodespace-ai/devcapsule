# Integration Tests

[Development](README.md) · [Developer environment](developer-environment.md) · [Source layout](source-layout.md) · [Unit tests](unit-tests.md) · [End-to-end tests](e2e-tests.md)

An integration test exercises a subsystem together with the real external
things it uses, the built executable, a subprocess, git, the file system
in its real layout or the Docker daemon, while the test still constructs
its inputs and fakes the services it is not testing. What makes a test
end-to-end is different: the product driven through its user entry point
with nothing faked. Owner direction, 2026-11-06; before it the guide drew
the line at Docker, which is where the hosted runner stops, not where
integration stops.

Integration tests run on demand, as the end-to-end suites do; the gate and
the unit selection do not run them. They run before a candidate is
produced: the candidate workflow runs the ones that need no Docker against
the release executable, and the ones that need Docker carry the `docker`
marker and run where a daemon is known, with their run recorded on
`main` in the test-run record the gate reads, as *Release Policy* rule 9
in `WORKFLOW-LOCAL.md` says.
The test controls its inputs even here: an image the test runs or
inspects is named by digest and is present before the test starts, which
the session establishes, not the test; building a base, which is slow,
reaches the network and is not deterministic, stays end-to-end.

## The built executable

```text
cd devcapsule-src
.venv/bin/python -m nox -s integration
```

The session builds `dist/devcapsule-local.pex` and runs
`pytest -m integration tests/integration`. The one module there,
`test_pex_runtime.py`, proves what only the packaged form can prove:

- the built executable dispatches the in-container `runtime` entrypoint and
  the recursive preflight from the same bytes;
- it bootstraps the packaged workflow definition into a project;
- it exposes the recursive-host public interface and the exact host argument
  that `xdg-open` dispatches through it;
- it reports a self-contained source identity, repository and revision;
- a clean revision builds with the version the tag derives, the rule the
  release backend relies on.

These tests take the executable from the `built_pex` fixture, so
`DEVCAPSULE_PEX_UNDER_TEST` points them at a downloaded candidate during
release acceptance, the same way it does for the end-to-end suites. The
`integration` marker keeps them out of the unit selection.

## The CLI smoke

The gate's `run_smoke` and `smoke_pex` steps run every command tree's
`--help` through the source CLI and then through the built executable,
including the commands that must exit with a usage error and the one
retired command whose diagnostic must still answer. No assertion beyond the
exit code: the point is that every entry point imports and parses on the
packaged form, which a unit test cannot show.

## Two gate checks that are not tests

`nox -s typecheck` is the only place the package, the tests, the noxfile
and the release scripts are read together, so a changed signature is
caught where it is used. It tests no subsystem against anything, and
neither does the documentation contract below; both are checks of the
gate, listed here because a reader looking for them looks here.

`nox -s docs-contract`, also a step of the gate, runs the pinned website's
own `check:content` against this checkout as the content source: the
versions manifest, the front matter, the roles, the version tokens, and
every version's tree are assembled exactly as a publication would assemble
them, without writing the site. It is skipped with a notice where the
website submodule is not initialized or npm is absent, which is the case on
the hosted runner. The contract it checks is
[the content–website contract](../specifications/product/content-website-contract.md).

## Where the next integration test goes

A test of a subsystem against the real things it uses belongs in
`tests/integration/` with the `integration` marker, and the `built_pex`
fixture when it needs the executable. One that needs the Docker daemon
carries the `docker` marker too, so the candidate workflow leaves it out
and `nox -s integration` on a host with a daemon runs it. A proof that
drives the product as a user does, with nothing faked, belongs in
`tests/e2e/`; see [End-to-end tests](e2e-tests.md).
