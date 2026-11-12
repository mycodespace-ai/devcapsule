"""Legacy tests of ``tests/test_environment_realization.py`` marked expected to fail on 2026-11-04, moved verbatim.

Mirror of ``devcapsule/legacy_refactoring/environment_realization.py``, a temporary target that holds no code.
Each test here reads a precondition from outside itself, against *Unit Tests* rule 2; the
maintenance workstream rewrites each against its real unit and this file shrinks to nothing.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock
import pytest
from devcapsule.compat import CliError
from devcapsule.environment_realization import realize_environment
from tests.test_environment_realization import resolved_project, select_claude_code
from devcapsule.runtime_configuration import CONTEXT_PATH

IN_CAPSULE = CONTEXT_PATH.is_file()
"""The marker holds only inside a capsule, where these tests inherit its state; elsewhere they are the tests they were."""


@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_realize_environment_requires_explicit_claude_download_authorization(
    tmp_path: Path,
) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    selected = resolved_project(tmp_path)
    select_claude_code(selected, authorized=False)
    obtain = Mock()
    materialize = Mock()

    with pytest.raises(CliError, match="claude-code-download"):
        realize_environment(selected, obtain_image=obtain, materialize=materialize)

    obtain.assert_not_called()
    materialize.assert_not_called()
