"""Legacy tests of ``tests/test_capability_commands_v2.py`` marked expected to fail on 2026-11-04, moved verbatim.

Mirror of ``devcapsule/legacy_refactoring/capability_commands_v2.py``, a temporary target that holds no code.
Each test here reads a precondition from outside itself, against *Unit Tests* rule 2; the
maintenance workstream rewrites each against its real unit and this file shrinks to nothing.
"""
from __future__ import annotations

import pytest
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.compat import DecisionPending
from tests.test_run_flow import project, config
from tests.test_capability_commands_v2 import matrix, snapshot
from devcapsule.runtime_configuration import CONTEXT_PATH

IN_CAPSULE = CONTEXT_PATH.is_file()
"""The marker holds only inside a capsule, where these tests inherit its state; elsewhere they are the tests they were."""


@pytest.mark.parametrize("origin", ["project", "checkout", "run"])
@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_resolution_grants_no_consent_and_no_partial_save(project, matrix, tmp_path, origin):
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    assert config(project, "ide", "frontend-ide") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    assert config(project, "add", "assistant") == 0
    if origin == "project":
        assert config(project, "recommend", "assistant", "claude-code") == 0
        assert config(project, "use", "assistant", "default") == 0
    elif origin == "checkout":
        assert config(project, "use", "assistant", "claude-code") == 0
    before = snapshot(tmp_path)
    flags = RunFlags(providers=(("assistant", "claude-code"),) if origin == "run" else (), memory="6g", save=True)
    with pytest.raises(DecisionPending, match="claude"):
        prepare_launch(project, flags, interactive=False)
    assert snapshot(tmp_path) == before
