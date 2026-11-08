"""Unit tests of ``devcapsule/build_info.py``: built-artifact detection versus source runs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from devcapsule.build_info import BuildInfoError, is_built_distribution


class _MissingResource:
    def joinpath(self, _name: str) -> "_MissingResource":
        return self

    def read_text(self, *, encoding: str = "utf-8") -> str:
        raise FileNotFoundError(encoding)


class _TextResource:
    def __init__(self, text: str) -> None:
        self._text = text

    def joinpath(self, _name: str) -> "_TextResource":
        return self

    def read_text(self, *, encoding: str = "utf-8") -> str:
        return self._text


def test_is_built_distribution_returns_false_without_embedded_build_info(tmp_path: Path) -> None:
    """Without ``_build_info.json`` in package resources or beside ``build_info.py``, ``is_built_distribution`` returns False."""
    with (
        patch("devcapsule.build_info.files", return_value=_MissingResource()),
        patch("devcapsule.build_info.__file__", str(tmp_path / "build_info.py")),
    ):
        assert is_built_distribution() is False


def test_is_built_distribution_returns_true_with_valid_embedded_build_info() -> None:
    """A valid embedded ``_build_info.json`` marks the running process as a built distribution."""
    payload = json.dumps(
        {
            "schema_version": 2,
            "version": "0.3.1rc2",
            "build_mnemonic": "v0.3.1-rc2",
            "source_repository": "https://github.com/example/devcapsule",
            "source_revision": "a" * 40,
            "source_url": f"https://github.com/example/devcapsule/commit/{'a' * 40}",
        }
    )
    with patch("devcapsule.build_info.files", return_value=_TextResource(payload)):
        assert is_built_distribution() is True


def test_is_built_distribution_refuses_malformed_embedded_build_info() -> None:
    """A malformed ``_build_info.json`` raises ``BuildInfoError`` instead of pretending to be a source run."""
    with (
        patch("devcapsule.build_info.files", return_value=_TextResource("{not-json")),
        pytest.raises(BuildInfoError),
    ):
        is_built_distribution()
