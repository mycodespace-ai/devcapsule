"""Graphviz selection through real CLI processes in an isolated configuration home."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("declaration,field", [("--require", "required"), ("--offer", "optional")])
def test_a_project_can_declare_graphviz_on_its_native_capsule_platform(
    tmp_path: Path, declaration: str, field: str,
) -> None:
    """Project initialization writes a shared Graphviz declaration and matching pinned platform lock."""
    project = tmp_path / "project"
    project.mkdir()
    platform = Platform.current()
    expected = tomllib.loads(MATRICES[platform].resolve(
        ["frontend-ide", "graphviz"], allow_unverified=True,
    ).render_lock())
    environment = {"PATH": os.defpath, "HOME": str(tmp_path / "home"),
                   "DEVCAPSULE_CONFIG_HOME": str(tmp_path / "configuration")}
    trusted = subprocess.run(
        [sys.executable, "-m", "devcapsule", "home", "trust", "accept", "devcapsule-base"],
        env=environment, cwd=project, text=True, capture_output=True, timeout=30,
    )
    assert trusted.returncode == 0, trusted.stdout + trusted.stderr
    result = subprocess.run(
        [sys.executable, "-m", "devcapsule", "project", "--path", str(project), "init",
         "--creator", "https://example.test/graphviz", "--ide", "frontend-ide",
         declaration, "graphviz", "--platform", platform.value, "--unverified",
         "--authorize", "base-image", expected["base"]["reference"]],
        env=environment, cwd=project, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = tomllib.loads((project / ".devcapsule/devcapsule.toml").read_text())
    lock = tomllib.loads((project / f".devcapsule/devcapsule.{platform.value}.lock").read_text())
    assert "graphviz" in manifest["capabilities"][field]
    graphviz = lock["components"]["graphviz"]
    assert graphviz["platform"] == platform.value
    assert graphviz["delivery-policy"] == "local-materialization"
    assert graphviz["artifacts"]["source"]["sha256"]
