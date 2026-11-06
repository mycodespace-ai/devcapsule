# Integration Tests

[Development](README.md) · [Developer environment](developer-environment.md) · [Source layout](source-layout.md) · [Unit tests](unit-tests.md) · [End-to-end tests](e2e-tests.md)

An integration test here crosses a packaging or process boundary and still
runs without Docker: it executes the built executable, a subprocess, or an
external tool, and reads what came back. Four kinds exist. The gate runs
three of them; the tests of the built executable run on demand, as the
end-to-end suites do, and in the release workflow against the release
executable.

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

## The type check

`nox -s typecheck` is an integration check in the sense that matters: it is
the only place the package, the tests, the noxfile and the release scripts
are read together, so a changed signature is caught where it is used.

## The documentation contract

`nox -s docs-contract`, also a step of the gate, runs the pinned website's
own `check:content` against this checkout as the content source: the
versions manifest, the front matter, the roles, the version tokens, and
every version's tree are assembled exactly as a publication would assemble
them, without writing the site. It is skipped with a notice where the
website submodule is not initialized or npm is absent, which is the case on
the hosted runner. The contract it checks is
[the content–website contract](../specifications/product/content-website-contract.md).

## Where the next integration test goes

A test that needs the executable but not Docker belongs in
`tests/integration/` with the `integration` marker and the `built_pex`
fixture. A test that needs Docker belongs in `tests/e2e/`; see
[End-to-end tests](e2e-tests.md).
