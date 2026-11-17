"""Exercise CLI syntax changes through real processes with private project and home inputs."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def run_cli(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "devcapsule", *arguments], cwd=project,
        env={"PATH": os.defpath, "HOME": str(project / "home"),
             "DEVCAPSULE_CONFIG_HOME": str(project / "config"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=120, check=False,
    )


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_runtime_check_help_does_not_run_diagnostics(tmp_path: Path, flag: str) -> None:
    """A help request outside a project prints usage without invoking runtime diagnostics."""
    completed = run_cli(tmp_path, "pycharm", "check-runtime", flag)

    assert completed.returncode == 0, completed.stderr
    assert "usage: devcapsule pycharm check-runtime" in completed.stdout
    assert "Run the current PyCharm runtime dependency check." in completed.stdout
    assert completed.stderr == ""
    assert list(tmp_path.iterdir()) == []


def test_bootstrap_installs_a_complete_portable_kit_and_preserves_customization(tmp_path: Path) -> None:
    """Workflow setup delivers importable helpers and provenance for both agents, preserving edited kits on rerun."""
    completed = run_cli(tmp_path, "bootstrap")
    assert completed.returncode == 0, completed.stderr
    roots = [tmp_path / name / "skills/devcapsule-recorded-e2e" for name in (".agents", ".claude")]
    for root in roots:
        assert (root / "SKILL.md").is_file()
        provenance = json.loads((root / "kit-version.json").read_text())
        assert provenance["package"] == "devcapsule"
        assert provenance["version"]
        assert {p.name for p in (root / "presentation_tools").iterdir()} == {
            "README.md", "__init__.py", "example.py", "producer.py", "recording.py",
        }
        imported = subprocess.run(
            [sys.executable, "-I", "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); "
             "from presentation_tools.producer import Script; "
             "from presentation_tools.recording import Recording; "
             "import presentation_tools.example; "
             "assert 'devcapsule' not in sys.modules and 'tests' not in sys.modules", str(root)],
            cwd=tmp_path, env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, timeout=120, check=False,
        )
        assert imported.returncode == 0, imported.stderr

    customized = roots[0] / "presentation_tools/recording.py"
    customized.write_text("# user customization\n")
    before = {p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()}
    repeated = run_cli(tmp_path, "bootstrap")
    assert repeated.returncode == 0, repeated.stderr
    assert {p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()} == before
