"""Unit tests of ``devcapsule/build_info.py``: stamped build records, source-form identity, and PEX inspection."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from devcapsule.build_info import (
    BuildInfo,
    BuildInfoError,
    build_info_json,
    current_build_info,
    read_pex_build_info,
)


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


def test_current_build_info_returns_stamped_record_when_present(tmp_path: Path) -> None:
    """When a stamped ``_build_info.json`` candidate exists, ``current_build_info`` returns its parsed ``BuildInfo``."""
    record = tmp_path / "_build_info.json"
    expected = BuildInfo(2, "2.3.4", "https://github.com/example/devcapsule", "c" * 40,
                         f"https://github.com/example/devcapsule/commit/{'c' * 40}", "v2.3.4")
    record.write_text(build_info_json(expected), encoding="utf-8")

    info = current_build_info(record_paths=(tmp_path / "missing.json", record))

    assert info == expected


def test_current_build_info_derives_source_form_from_authored_pyproject(tmp_path: Path) -> None:
    """Without ``_build_info.json``, ``current_build_info`` derives ``v<version>-local`` from ``pyproject.toml``."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "devcapsule"\nversion = "9.8.7"\n', encoding="utf-8")

    info = current_build_info(
        record_paths=(tmp_path / "absent.json",),
        pyproject_path=pyproject,
        installed_version="0.0.1",
    )

    assert info == BuildInfo(
        schema_version=2,
        version="9.8.7",
        source_repository="unknown",
        source_revision="unknown",
        source_url="unknown",
        build_mnemonic="v9.8.7-local",
    )


def test_current_build_info_falls_back_to_installed_version_outside_checkout(tmp_path: Path) -> None:
    """Without ``_build_info.json`` or ``pyproject.toml``, ``current_build_info`` uses installed package metadata."""
    info = current_build_info(
        record_paths=(tmp_path / "absent.json",),
        pyproject_path=tmp_path / "absent" / "pyproject.toml",
        installed_version="4.5.6",
    )

    assert info.version == "4.5.6"
    assert info.build_mnemonic == "v4.5.6-local"
    assert info.source_revision == "unknown"


def test_current_build_info_raises_on_malformed_build_record(tmp_path: Path) -> None:
    """A present but malformed ``_build_info.json`` raises ``BuildInfoError`` instead of demoting to source form."""
    malformed = tmp_path / "_build_info.json"
    malformed.write_text("not json", encoding="utf-8")

    with pytest.raises(BuildInfoError, match="not valid JSON"):
        current_build_info(record_paths=(malformed,))
