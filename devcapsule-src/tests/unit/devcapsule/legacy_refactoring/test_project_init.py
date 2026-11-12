"""Legacy tests of ``tests/test_project_init.py`` marked expected to fail on 2026-11-04, moved verbatim.

Mirror of ``devcapsule/legacy_refactoring/project_init.py``, a temporary target that holds no code.
Each test here reads a precondition from outside itself, against *Unit Tests* rule 2; the
maintenance workstream rewrites each against its real unit and this file shrinks to nothing.
"""
from __future__ import annotations

from tests.launch_preparation import run_until_prepared
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from devcapsule import cli
from tests.test_project_init import full_init_command, isolated_env, read_toml
from devcapsule.runtime_configuration import CONTEXT_PATH

IN_CAPSULE = CONTEXT_PATH.is_file()
"""The marker holds only inside a capsule, where these tests inherit its state; elsewhere they are the tests they were."""


@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_a_selected_agent_brings_its_own_acquisition_gate(tmp_path: Path, capsys) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    project = tmp_path / "fresh-project"
    project.mkdir()
    with patch.dict(os.environ, isolated_env(tmp_path), clear=False):
        assert cli.main(full_init_command(project)) == 0
        capsys.readouterr()

        # The agent is the developer's; resolving without its vendor's channel names the channel (D-0011).
        assert cli.main(["project", "--path", str(project), "config", "add", "claude-code-agent"]) == 0
        assert run_until_prepared(project) == 3
        assert "home trust accept claude-code" in capsys.readouterr().err

        assert cli.main(["project", "--path", str(project), "config", "authorize", "claude-code-download", "true"]) == 0
        assert run_until_prepared(project) == 0
        from devcapsule.configuration.storage import lock_for
        lock = lock_for(project, read_toml(project / ".devcapsule" / "devcapsule.toml"))[1]
        assert lock["components"]["claude-code"]["version"]
