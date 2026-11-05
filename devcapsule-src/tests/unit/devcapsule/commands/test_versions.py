"""Unit tests of ``devcapsule/commands/_versions.py``: the ``check`` command's feed override.

The project context is a stub whose start path is ``tmp_path``; the effect module is monkeypatched so no
workspace is read.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from devcapsule.commands import _versions


class Context:
    """A project context whose start path is a fixed directory."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def start_path(self) -> Path:
        return self.root


@pytest.mark.parametrize("argv,expected", [
    (["check"], None),
    (["check", "--status-url", "https://test.example/feed.json"], "https://test.example/feed.json"),
])
def test_check_passes_its_status_url_to_the_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                   capsys: pytest.CaptureFixture[str], argv: list[str], expected: str | None) -> None:
    """``versions check`` hands ``--status-url`` to ``version_sets.check`` as ``status_url``, and ``None`` without it."""
    received: dict[str, Any] = {}

    def check(start: Path, *, status_url: str | None = None) -> str:
        received.update(start=start, status_url=status_url)
        return "report"

    monkeypatch.setattr(_versions.version_sets, "check", check)
    assert _versions.VersionsGroup.invoke("devcapsule project versions", argv, Context(tmp_path)) == 0
    assert received == {"start": tmp_path, "status_url": expected}
    assert capsys.readouterr().out.strip() == "report"
