"""Unit tests of ``devcapsule/build_info.py``: stamped build records, source-form identity, built-artifact detection, and PEX inspection."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from devcapsule.build_info import (
    BuildInfo,
    BuildInfoError,
    build_info_json,
    build_info_text,
    distribution_build_info,
    embedded_build_info,
    read_pex_build_info,
)

SAMPLE_BUILD = BuildInfo(
    schema_version=2,
    version="1.2.3",
    source_repository="https://github.com/example/devcapsule",
    source_revision="d" * 40,
    source_url=f"https://github.com/example/devcapsule/commit/{'d' * 40}",
    build_mnemonic="v1.2.3",
)


def stamped_package(directory: Path, text: str) -> Path:
    """A package directory holding ``_build_info.json`` with ``text``, as ``scripts/build-pex.sh`` leaves one."""
    directory.mkdir(parents=True)
    (directory / "_build_info.json").write_text(text, encoding="utf-8")
    return directory


def not_installed() -> str:
    """Stand for installed metadata that a test expects nobody to ask for."""
    raise AssertionError("the installed version was asked for")


def test_build_info_json_is_the_records_mapping() -> None:
    """``build_info_json`` serializes every field of the record, and ``BuildInfo.from_json`` reads it back."""
    text = build_info_json(SAMPLE_BUILD)

    assert json.loads(text) == SAMPLE_BUILD.to_mapping()
    assert BuildInfo.from_json(text) == SAMPLE_BUILD


def test_build_info_text_shows_the_build_then_where_its_source_is() -> None:
    """``build_info_text`` is four lines: the mnemonic with the package version, then repository, revision and URL."""
    assert build_info_text(SAMPLE_BUILD).splitlines() == [
        "DevCapsule v1.2.3 (package 1.2.3)",
        "Source repository: https://github.com/example/devcapsule",
        f"Source revision: {'d' * 40}",
        f"Source URL: https://github.com/example/devcapsule/commit/{'d' * 40}",
    ]


def test_public_build_identity_requires_matching_github_commit_url() -> None:
    """``has_public_revision`` is True only when ``source_url`` matches ``<github-repo>/commit/<hex-sha>``."""
    revision = "a" * 40
    repo = "https://github.com/example/devcapsule"
    public = BuildInfo(1, "1.0.0", repo, revision, f"{repo}/commit/{revision}")
    assert public.has_public_revision is True


@pytest.mark.parametrize(
    ("repo", "revision", "url"),
    [
        ("https://github.com/example/devcapsule", "a" * 40, "unknown"),
        ("https://example.com/example/devcapsule", "a" * 40, f"https://example.com/example/devcapsule/commit/{'a' * 40}"),
        ("https://github.com/example/devcapsule", "not-hex", "https://github.com/example/devcapsule/commit/not-hex"),
    ],
)
def test_public_build_identity_is_false_without_github_commit_coordinates(
    repo: str, revision: str, url: str,
) -> None:
    """``has_public_revision`` is False when repository, revision, or commit URL lacks canonical GitHub form."""
    info = BuildInfo(1, "1.0.0", repo, revision, url)
    assert info.has_public_revision is False


@pytest.mark.parametrize(
    "mnemonic",
    ("v1.2.3", "v1.2.3-local", "v1.2.3-local-linux-x86_64", "v026", "local-v026"),
)
def test_from_mapping_accepts_release_local_and_legacy_mnemonics(mnemonic: str) -> None:
    """Schema-2 build records accept release tags, ``-local`` labels, and v026-era compatibility labels."""
    mapping = {
        "schema_version": 2,
        "version": "1.0.0",
        "build_mnemonic": mnemonic,
        "source_repository": "unknown",
        "source_revision": "unknown",
        "source_url": "unknown",
    }
    assert BuildInfo.from_mapping(mapping).build_mnemonic == mnemonic


def test_from_mapping_rejects_unrecognizable_mnemonic() -> None:
    """Schema-2 build records reject a ``build_mnemonic`` outside the release/local grammar."""
    mapping = {
        "schema_version": 2,
        "version": "1.0.0",
        "build_mnemonic": "development",
        "source_repository": "unknown",
        "source_revision": "unknown",
        "source_url": "unknown",
    }
    with pytest.raises(BuildInfoError, match="build_mnemonic"):
        BuildInfo.from_mapping(mapping)


def test_read_pex_build_info_reads_embedded_record_without_executing_artifact(tmp_path: Path) -> None:
    """``read_pex_build_info`` parses the single ``devcapsule/_build_info.json`` zip member from a PEX archive."""
    pex = tmp_path / "devcapsule.pex"
    revision = "b" * 40
    value = {
        "schema_version": 1,
        "version": "1.0.0",
        "source_repository": "https://github.com/example/devcapsule",
        "source_revision": revision,
        "source_url": f"https://github.com/example/devcapsule/commit/{revision}",
    }
    with ZipFile(pex, "w") as archive:
        archive.writestr(".deps/package.whl/devcapsule/_build_info.json", json.dumps(value))

    assert read_pex_build_info(pex) == BuildInfo.from_mapping(value)


def test_read_pex_build_info_rejects_pex_without_embedded_record(tmp_path: Path) -> None:
    """``read_pex_build_info`` raises ``BuildInfoError`` when a PEX archive lacks ``devcapsule/_build_info.json``."""
    pex = tmp_path / "devcapsule.pex"
    with ZipFile(pex, "w") as archive:
        archive.writestr("PEX-INFO", "{}")

    with pytest.raises(BuildInfoError, match="exactly one"):
        read_pex_build_info(pex)


def test_distribution_build_info_returns_stamped_record_when_present(tmp_path: Path) -> None:
    """When a package location holds a stamped ``_build_info.json``, ``distribution_build_info`` returns it, whatever pyproject says, and leaves the installed version unasked."""
    expected = BuildInfo(2, "2.3.4", "https://github.com/example/devcapsule", "c" * 40,
                         f"https://github.com/example/devcapsule/commit/{'c' * 40}", "v2.3.4")
    package = stamped_package(tmp_path / "package", build_info_json(expected))

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "devcapsule"\nversion = "9.8.7"\n', encoding="utf-8")

    info = distribution_build_info(
        package_locations=(tmp_path / "unstamped", package),
        pyproject_path=pyproject,
        installed_version=not_installed,
    )

    assert info == expected


def test_distribution_build_info_derives_source_form_from_authored_pyproject(tmp_path: Path) -> None:
    """Without ``_build_info.json``, ``distribution_build_info`` derives ``v<version>-local`` from ``pyproject.toml`` and leaves the installed version unasked."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "devcapsule"\nversion = "9.8.7"\n', encoding="utf-8")

    info = distribution_build_info(
        package_locations=(tmp_path / "unstamped",),
        pyproject_path=pyproject,
        installed_version=not_installed,
    )

    assert info == BuildInfo(
        schema_version=2,
        version="9.8.7",
        source_repository="unknown",
        source_revision="unknown",
        source_url="unknown",
        build_mnemonic="v9.8.7-local",
    )


def test_distribution_build_info_falls_back_to_installed_version_outside_checkout(tmp_path: Path) -> None:
    """Without ``_build_info.json`` or ``pyproject.toml``, ``distribution_build_info`` uses the installed version."""
    info = distribution_build_info(
        package_locations=(tmp_path / "unstamped",),
        pyproject_path=tmp_path / "absent" / "pyproject.toml",
        installed_version=lambda: "4.5.6",
    )

    assert info.version == "4.5.6"
    assert info.build_mnemonic == "v4.5.6-local"
    assert info.source_revision == "unknown"


def test_distribution_build_info_ignores_a_pyproject_of_another_project(tmp_path: Path) -> None:
    """A ``pyproject.toml`` that names another project is no source checkout of this one, and the installed version answers."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "another"\nversion = "9.8.7"\n', encoding="utf-8")

    info = distribution_build_info(
        package_locations=(), pyproject_path=pyproject, installed_version=lambda: "4.5.6",
    )

    assert info.version == "4.5.6"


def test_distribution_build_info_raises_on_malformed_build_record(tmp_path: Path) -> None:
    """A present but malformed ``_build_info.json`` raises ``BuildInfoError`` instead of demoting to source form."""
    package = stamped_package(tmp_path / "package", "not json")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "devcapsule"\nversion = "9.8.7"\n', encoding="utf-8")

    with pytest.raises(BuildInfoError, match="not valid JSON"):
        distribution_build_info(package_locations=(package,), pyproject_path=pyproject, installed_version=not_installed)


def test_embedded_build_info_is_none_without_a_stamped_location(tmp_path: Path) -> None:
    """When no package location holds ``_build_info.json``, ``embedded_build_info`` is ``None``: a source-form run."""
    unstamped = tmp_path / "unstamped"
    unstamped.mkdir()

    assert embedded_build_info((unstamped, tmp_path / "absent")) is None


def test_embedded_build_info_reads_the_record_of_the_first_location(tmp_path: Path) -> None:
    """``_build_info.json`` in the first package location is the build the distribution was stamped with."""
    package = stamped_package(tmp_path / "package", build_info_json(SAMPLE_BUILD))

    assert embedded_build_info((package,)) == SAMPLE_BUILD


def test_embedded_build_info_reads_a_later_location_when_the_first_is_unstamped(tmp_path: Path) -> None:
    """When the first location holds no record, the record of the next one is read."""
    package = stamped_package(tmp_path / "package", build_info_json(SAMPLE_BUILD))

    assert embedded_build_info((tmp_path / "unstamped", package)) == SAMPLE_BUILD


def test_embedded_build_info_refuses_a_malformed_record(tmp_path: Path) -> None:
    """A malformed ``_build_info.json`` raises ``BuildInfoError`` instead of pretending to be a source run."""
    package = stamped_package(tmp_path / "package", "{not-json")

    with pytest.raises(BuildInfoError, match="not valid JSON"):
        embedded_build_info((package,))
