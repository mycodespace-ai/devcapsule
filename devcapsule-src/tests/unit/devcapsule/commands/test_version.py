"""Unit tests of ``devcapsule/commands/version.py``: JSON and human-readable build identity output."""

from __future__ import annotations

import json

import pytest

from devcapsule.build_info import BuildInfo
from devcapsule.commands.version import VersionCommand


SAMPLE_BUILD = BuildInfo(
    schema_version=2,
    version="1.2.3",
    source_repository="https://github.com/example/devcapsule",
    source_revision="d" * 40,
    source_url=f"https://github.com/example/devcapsule/commit/{'d' * 40}",
    build_mnemonic="v1.2.3",
)


def test_version_json_emits_machine_readable_build_info(capsys: pytest.CaptureFixture[str]) -> None:
    """``version --json`` prints the ``BuildInfo`` mapping as JSON on stdout and returns 0."""
    status = VersionCommand.invoke("devcapsule version", ["--json"], build_info=SAMPLE_BUILD)

    assert status == 0
    assert json.loads(capsys.readouterr().out) == SAMPLE_BUILD.to_mapping()


def test_version_text_prints_mnemonic_package_version_and_source_identity(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``version`` without ``--json`` prints the mnemonic, package version, repository, revision, and URL."""
    status = VersionCommand.invoke("devcapsule version", [], build_info=SAMPLE_BUILD)

    assert status == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "DevCapsule v1.2.3 (package 1.2.3)",
        "Source repository: https://github.com/example/devcapsule",
        f"Source revision: {'d' * 40}",
        f"Source URL: https://github.com/example/devcapsule/commit/{'d' * 40}",
    ]
