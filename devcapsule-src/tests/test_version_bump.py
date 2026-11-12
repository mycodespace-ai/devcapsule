from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.legacy


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bump-version.py"
SPEC = importlib.util.spec_from_file_location("devcapsule_bump_version", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
VERSION_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERSION_MODULE)


def project(tmp_path: Path, *, version: str = "1.2.3") -> Path:
    root = tmp_path / "devcapsule-src"
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[build-system]\nrequires = ["setuptools"]\n\n[project]\n'
        f'name = "devcapsule"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    return root


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        ("patch", "1.2.4"),
        ("minor", "1.3.0"),
        ("major", "2.0.0"),
        ("1.4.2", "1.4.2"),
    ],
)
def test_bump_updates_the_single_authored_version(
    tmp_path: Path, requested: str, expected: str
) -> None:
    root = project(tmp_path)

    assert VERSION_MODULE.bump_version(requested, root) == ("1.2.3", expected)

    assert VERSION_MODULE.checked_version(root) == expected
    assert f'version = "{expected}"' in (root / "pyproject.toml").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("requested", ["1.2.3", "1.2.2", "v1.2.4", "banana"])
def test_bump_rejects_non_advancing_or_invalid_versions(
    tmp_path: Path, requested: str
) -> None:
    root = project(tmp_path)

    with pytest.raises(VERSION_MODULE.VersionError):
        VERSION_MODULE.bump_version(requested, root)

    assert VERSION_MODULE.checked_version(root) == "1.2.3"


def test_check_rejects_malformed_version(tmp_path: Path) -> None:
    root = project(tmp_path, version="1.2.3rc1")

    with pytest.raises(VERSION_MODULE.VersionError, match="MAJOR.MINOR.PATCH"):
        VERSION_MODULE.checked_version(root)


def test_check_rejects_ambiguous_version_authorship(tmp_path: Path) -> None:
    root = project(tmp_path)
    path = root / "pyproject.toml"
    path.write_text(
        path.read_text(encoding="utf-8") + 'version = "9.9.9"\n', encoding="utf-8"
    )

    with pytest.raises(VERSION_MODULE.VersionError, match="exactly one"):
        VERSION_MODULE.checked_version(root)


def definition(path: Path, version: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ndefinition: devcapsule\nversion: {version}\n---\n\n# Workflow\n\n"
        "### Changes\n\n#### Unreleased\n\n- a rule\n\n#### 1.2.3\n\n- older\n",
        encoding="utf-8",
    )


def test_bump_stamps_both_definition_copies_and_closes_unreleased(tmp_path: Path) -> None:
    root = project(tmp_path)
    copies = [root / relative for relative in VERSION_MODULE.DEFINITION_COPIES]
    for copy in copies:
        definition(copy, "1.2.3")

    assert VERSION_MODULE.bump_version("patch", root) == ("1.2.3", "1.2.4")

    for copy in copies:
        text = copy.read_text(encoding="utf-8")
        assert text.startswith("---\ndefinition: devcapsule\nversion: 1.2.4\n---\n")
        assert "#### Unreleased" not in text
        assert "#### 1.2.4\n\n- a rule" in text
        assert "#### 1.2.3\n\n- older" in text


def test_check_rejects_a_definition_copy_that_lags_the_package(tmp_path: Path) -> None:
    root = project(tmp_path)
    definition(root / VERSION_MODULE.DEFINITION_COPIES[0], "1.0.0")

    with pytest.raises(VERSION_MODULE.VersionError, match="frontmatter declares version '1.0.0'"):
        VERSION_MODULE.checked_version(root)


def test_development_versions_are_accepted_and_order_before_their_release(
    tmp_path: Path,
) -> None:
    root = project(tmp_path, version="1.2.4.dev0")

    assert VERSION_MODULE.checked_version(root) == "1.2.4.dev0"
    # Finishing the cycle: the release the development version works toward.
    assert VERSION_MODULE.next_version("1.2.4.dev0", "1.2.4") == "1.2.4"
    # Reopening after a release: the next development version.
    assert VERSION_MODULE.next_version("1.2.4", "1.2.5.dev0") == "1.2.5.dev0"
    with pytest.raises(VERSION_MODULE.VersionError, match="must be greater"):
        VERSION_MODULE.next_version("1.2.4", "1.2.4.dev0")
    with pytest.raises(VERSION_MODULE.VersionError, match="MAJOR.MINOR.PATCH"):
        VERSION_MODULE.checked_version(project(tmp_path / "other", version="1.2.4.dev"))
