"""Unit tests of ``devcapsule/commands/version.py``: JSON and human-readable build identity output."""

from __future__ import annotations

import json

import pytest

from devcapsule.build_info import BuildInfo
from devcapsule.commands import version
from devcapsule.commands.version import VersionCommand


SAMPLE_BUILD = BuildInfo(
    schema_version=2,
    version="1.2.3",
    source_repository="https://github.com/example/devcapsule",
    source_revision="d" * 40,
    source_url=f"https://github.com/example/devcapsule/commit/{'d' * 40}",
    build_mnemonic="v1.2.3",
)


@pytest.fixture
def running_sample_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``SAMPLE_BUILD`` the build the command finds itself running."""
    monkeypatch.setattr(version, "current_build_info", lambda: SAMPLE_BUILD)


def test_version_json_emits_machine_readable_build_info(
    capsys: pytest.CaptureFixture[str], running_sample_build: None,
) -> None:
    """``version --json`` prints the running build's ``BuildInfo`` mapping as JSON on stdout and returns 0."""
    status = VersionCommand.invoke("devcapsule version", ["--json"])

    assert status == 0
    assert json.loads(capsys.readouterr().out) == SAMPLE_BUILD.to_mapping()


def test_version_text_prints_mnemonic_package_version_and_source_identity(
    capsys: pytest.CaptureFixture[str], running_sample_build: None,
) -> None:
    """``version`` without ``--json`` prints the running build's mnemonic, package version, repository, revision, and URL."""
    status = VersionCommand.invoke("devcapsule version", [])

    assert status == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "DevCapsule v1.2.3 (package 1.2.3)",
        "Source repository: https://github.com/example/devcapsule",
        f"Source revision: {'d' * 40}",
        f"Source URL: https://github.com/example/devcapsule/commit/{'d' * 40}",
    ]
