"""Run the version command from private source and stamped package layouts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def distribution(tmp_path: Path) -> Path:
    """Copy the package without caches and give this source checkout its own authored version."""
    source = Path(__file__).resolve().parents[2] / "devcapsule"
    shutil.copytree(source, tmp_path / "devcapsule", ignore=shutil.ignore_patterns("__pycache__", "_build_info.json"))
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "devcapsule"\nversion = "9.8.7"\n', encoding="utf-8",
    )
    return tmp_path


def version(distribution: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Start the real CLI with the private distribution first on its import path and a fresh environment."""
    return subprocess.run(
        [sys.executable, "-m", "devcapsule", "version", *arguments],
        cwd=distribution,
        env={"PATH": os.defpath, "HOME": str(distribution / "home"),
             "DEVCAPSULE_CONFIG_HOME": str(distribution / "config"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=120, check=False,
    )


@pytest.mark.parametrize("stamped", [False, True], ids=["source", "stamped-package"])
@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
def test_version_reports_the_running_distributions_record(
    distribution: Path, stamped: bool, as_json: bool,
) -> None:
    """Version prints the authored source identity or the package's stamp, in the requested format with one final newline."""
    expected = {
        "schema_version": 2,
        "version": "9.8.7",
        "build_mnemonic": "v9.8.7-local",
        "source_repository": "unknown",
        "source_revision": "unknown",
        "source_url": "unknown",
    }
    if stamped:
        expected.update({
            "version": "1.2.3", "build_mnemonic": "v1.2.3",
            "source_repository": "https://github.com/example/fixture",
            "source_revision": "a" * 40,
            "source_url": "https://github.com/example/fixture/commit/" + "a" * 40,
        })
        (distribution / "devcapsule" / "_build_info.json").write_text(json.dumps(expected), encoding="utf-8")
    # A record beside the package must never take precedence over the package's own record or source identity.
    (distribution / "_build_info.json").write_text('{"wrong-location": true}', encoding="utf-8")

    completed = version(distribution, *(("--json",) if as_json else ()))

    assert completed.returncode == 0, completed.stderr
    if as_json:
        assert completed.stdout == json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n"
    else:
        assert completed.stdout == (
            f"DevCapsule {expected['build_mnemonic']} (package {expected['version']})\n"
            f"Source repository: {expected['source_repository']}\n"
            f"Source revision: {expected['source_revision']}\n"
            f"Source URL: {expected['source_url']}\n"
        )
    assert completed.stderr == ""
