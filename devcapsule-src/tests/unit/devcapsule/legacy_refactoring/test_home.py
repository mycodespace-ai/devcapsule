"""Legacy tests of ``tests/test_home.py`` marked expected to fail on 2026-11-04, moved verbatim but for one path.

The path to ``devcapsule-src`` is taken from this file's place in the mirror, four levels deeper
than the legacy file's.
Mirror of ``devcapsule/legacy_refactoring/home.py``, a temporary target that holds no code.
Each test here reads a precondition from outside itself, against *Unit Tests* rule 2; the
maintenance workstream rewrites each against its real unit and this file shrinks to nothing.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from devcapsule.runtime_configuration import CONTEXT_PATH

IN_CAPSULE = CONTEXT_PATH.is_file()
"""The marker holds only inside a capsule, where these tests inherit its state; elsewhere they are the tests they were."""


@pytest.mark.parametrize("folder", ["devcapsule", "tests", "docs"])
@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_replaced_scope_word_is_absent(folder: str) -> None:
    """Legacy test, moved verbatim and expected to fail: it walks the checkout's resources, ignored directories included, instead of constructing its input."""
    package = Path(__file__).resolve().parents[4]  # devcapsule-src; parents[1] in the legacy file's place
    root = package.parent / "docs" if folder == "docs" else package / folder
    forbidden = "work" + "station"
    failures = []
    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or ".pytest_cache" in path.parts:
            continue
        if path.is_relative_to(package / "tests" / "resources" / "compat"):
            continue
        try:
            text = path.read_text()
        except UnicodeError:
            continue
        if forbidden in text.lower():
            failures.append(str(path.relative_to(root)))
    assert failures == []
