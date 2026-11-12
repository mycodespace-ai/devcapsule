"""Legacy tests of ``tests/test_capability_minimums.py`` marked expected to fail on 2026-11-04, moved verbatim.

Mirror of ``devcapsule/legacy_refactoring/capability_minimums.py``, a temporary target that holds no code.
Each test here reads a precondition from outside itself, against *Unit Tests* rule 2; the
maintenance workstream rewrites each against its real unit and this file shrinks to nothing.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from devcapsule import cli
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.configuration import owner_commands
from tests.test_capability_minimums import MANIFEST, project, snapshot, write_project
from devcapsule.runtime_configuration import CONTEXT_PATH

IN_CAPSULE = CONTEXT_PATH.is_file()
"""The marker holds only inside a capsule, where these tests inherit its state; elsewhere they are the tests they were."""


@pytest.mark.xfail(IN_CAPSULE, reason="TODO: fix the wrong approach to testing")
def test_offered_agent_still_needs_consent_and_can_be_omitted(project: Path, tmp_path: Path, capsys) -> None:
    """Legacy test, moved verbatim and expected to fail: it inherits the capsule's mounted launcher settings instead of constructing its own home."""
    write_project(project, MANIFEST.replace('"python>=3.14", ', ''))
    assert cli.main(["project", "--path", str(project), "init", "--ide", "frontend-ide", "--authorize", "base-image", "default"]) == 0
    owner_commands.offer_tools(project, ["claude-code-agent"])
    before = snapshot(tmp_path)
    assert cli.main(["project", "--path", str(project), "run", "--print-command", "--no-update-check"]) == 3
    assert "claude-code" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
    assert cli.main(["project", "--path", str(project), "config", "omit", "claude-code-agent"]) == 0
    prepared = prepare_launch(project, RunFlags(), interactive=False, print_only=True)
    assert "claude-code" not in prepared.selected.lock["components"]
