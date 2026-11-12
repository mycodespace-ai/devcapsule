"""Integration tests of ``devcapsule version``: the real command line, in a process whose environment the test builds."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from devcapsule.build_info import build_info_json, build_info_text, current_build_info

pytestmark = pytest.mark.integration


def version(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run ``devcapsule version`` in a new process with a search path, a home and a configuration home under ``tmp_path``."""
    environment = {
        "PATH": os.defpath,
        "HOME": str(tmp_path / "home"),
        "DEVCAPSULE_CONFIG_HOME": str(tmp_path / "config"),
    }
    return subprocess.run(
        [sys.executable, "-m", "devcapsule", "version", *arguments],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=120, check=False,
    )


def test_version_json_prints_the_build_info_of_the_distribution_it_runs_from(tmp_path: Path) -> None:
    """``version --json`` prints, as one JSON line, the build information of the distribution this test imports too."""
    completed = version(tmp_path, "--json")

    assert completed.returncode == 0
    assert completed.stdout == build_info_json(current_build_info()) + "\n"
    assert completed.stderr == ""


def test_version_prints_the_build_info_as_text_without_the_flag(tmp_path: Path) -> None:
    """``version`` prints the same build information as the four lines a person reads."""
    completed = version(tmp_path)

    assert completed.returncode == 0
    assert completed.stdout == build_info_text(current_build_info()) + "\n"
    assert completed.stderr == ""
