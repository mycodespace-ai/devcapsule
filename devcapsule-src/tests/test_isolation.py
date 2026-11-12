"""Run the shared fixtures against disposable stand-ins for the user's homes."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import DOCKER_MARKERS

pytestmark = pytest.mark.legacy

pytest_plugins = ["pytester"]


@pytest.mark.parametrize("exported_xdg", [False, True], ids=["laptop", "capsule"])
def test_user_directory_isolation(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, exported_xdg: bool,
) -> None:
    # Copy the real conftest so pytest, including autouse ordering and inherited
    # markers, is what we exercise. Never inherit the developer's homes here.
    pytester.makeconftest(Path(__file__).with_name("conftest.py").read_text())
    owner = pytester.path / "owner"
    owner.mkdir()
    monkeypatch.setenv("HOME", str(owner))
    for key, leaf in (("XDG_CACHE_HOME", ".cache"), ("XDG_CONFIG_HOME", ".config"),
                      ("XDG_DATA_HOME", ".local/share"), ("XDG_STATE_HOME", ".local/state"),
                      ("XDG_RUNTIME_DIR", "runtime")):
        directory = owner / leaf
        directory.mkdir(parents=True)
        if exported_xdg:
            monkeypatch.setenv(key, str(directory))
        else:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    for key in ("PEX_ROOT", "SCIE_BASE"):
        monkeypatch.delenv(key, raising=False)
    pytester.makeini("[pytest]\nmarkers =\n" + "\n".join(
        f"    {marker}: fixture probe only; no Docker" for marker in (*DOCKER_MARKERS, "integration")
    ))
    pytester.makepyfile('''
        import hashlib
        import os
        from pathlib import Path
        import pytest
        from devcapsule import version_sets
        from devcapsule.materialization import ArtifactSpec, cache_root
        from devcapsule.platforms import XdgHomes

        inherited = dict(os.environ)
        owner_cache = cache_root()
        payload = b"retained fixture bytes"
        digest = hashlib.sha256(payload).hexdigest()
        relative = Path("artifacts/sha256") / digest
        cached = owner_cache / relative
        cached.parent.mkdir(parents=True)
        cached.write_bytes(payload)

        @pytest.mark.parametrize("case", range(2))
        def test_cache_is_empty_and_private(tmp_path, monkeypatch, case):
            root = cache_root()
            assert root.is_relative_to(tmp_path)
            assert not root.exists() or not list(root.iterdir())
            spec = ArtifactSpec("fixture", "file:///unused", digest)
            monkeypatch.setattr(version_sets, "_specs", lambda lock: (spec,))
            state = tmp_path / "retained"
            version_sets._retain({}, state, acquire=False)
            assert not (state / relative).exists()  # No read from the owner's cache.
            retained = state / relative
            retained.parent.mkdir(parents=True)
            retained.write_bytes(payload)
            cached.unlink()
            try:
                assert version_sets._restore_artifacts({}, state) == []
                assert (root / relative).read_bytes() == payload
                assert not cached.exists()  # No write into the owner's cache.
            finally:
                cached.write_bytes(payload)

        @pytest.mark.integration
        def test_other_homes_are_private(tmp_path):
            homes = XdgHomes.from_environment()
            for directory in (Path.home(), homes.config, homes.data, homes.state,
                              Path(os.environ["XDG_RUNTIME_DIR"])):
                assert directory.is_relative_to(tmp_path)
            assert list(tmp_path.iterdir()) == []

        def test_build_tool_caches_stay_inherited():
            # pex and the scie launcher keep the developer's content-addressed
            # caches: a clean revision build must not download Python per test.
            assert os.environ["PEX_ROOT"] == str(owner_cache.parent / "pex")
            assert os.environ["SCIE_BASE"] == str(owner_cache.parent / "nce")

        @pytest.fixture
        def chosen_cache(tmp_path, monkeypatch):
            monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "chosen"))
            return tmp_path / "chosen" / "devcapsule"

        def test_explicit_fixture_wins(chosen_cache):
            assert cache_root() == chosen_cache

        @pytest.mark.parametrize("marker", [
            pytest.param(None, marks=getattr(pytest.mark, name))
            for name in ("e2e", "base_build_e2e", "recursive_e2e", "contributor_e2e", "ide_smoke")
        ])
        def test_docker_suites_keep_inherited_homes(marker):
            assert cache_root() == owner_cache
            for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                        "XDG_STATE_HOME", "XDG_RUNTIME_DIR"):
                assert os.environ.get(key) == inherited.get(key)

        @pytest.mark.e2e
        class TestInheritedMarker:
            def test_class_marker_keeps_cache(self):
                assert cache_root() == owner_cache
    ''')
    result = pytester.runpytest_subprocess("-q", "-o", "addopts=", "--strict-markers", timeout=30)
    result.assert_outcomes(passed=11)
