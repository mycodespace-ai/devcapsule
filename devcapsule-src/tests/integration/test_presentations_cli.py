"""Integration tests of ``devcapsule presentations``: real CLI subprocesses with explicit environments."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def _run_presentations(
    tmp_path: Path, *arguments: str, extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": os.defpath,
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(tmp_path / "home"),
        "DEVCAPSULE_CONFIG_HOME": str(tmp_path / "config"),
    }
    if extra_env:
        environment.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "devcapsule", "presentations", *arguments],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=120, check=False,
    )


def test_guide_and_export_supply_an_importable_standalone_kit(tmp_path: Path) -> None:
    """``presentations guide`` and ``export`` deliver the guide and a stdlib-only kit, refusing overwrites."""
    guide = _run_presentations(tmp_path, "guide")
    assert guide.returncode == 0, guide.stderr
    assert "# Run an E2E scenario with recording and presentation" in guide.stdout

    kit = tmp_path / "kit"
    exported = _run_presentations(tmp_path, "export", str(kit))
    assert exported.returncode == 0, exported.stderr
    assert f"Presentation tools: {kit / 'presentation_tools'}" in exported.stdout
    assert (kit / "presentation_tools" / "README.md").read_text(encoding="utf-8") + "\n" == guide.stdout

    isolated = subprocess.run(
        [
            sys.executable, "-I", "-c",
            (
                "import sys; sys.path.insert(0, sys.argv[1]); "
                "from presentation_tools.producer import Script; "
                "from presentation_tools.recording import Recording; "
                "import presentation_tools.example; "
                "assert 'devcapsule' not in sys.modules and 'tests' not in sys.modules"
            ),
            str(kit),
        ],
        cwd=tmp_path, env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert isolated.returncode == 0, isolated.stderr

    refused = _run_presentations(tmp_path, "export", str(kit))
    assert refused.returncode == 2
    assert "cannot export presentation tools" in refused.stderr


def test_hand_off_reads_environment_and_handles_token_states(tmp_path: Path) -> None:
    """``presentations hand-off`` prints a tokenized link, falls back cleanly on missing or non-UTF-8 tokens, and refuses missing decks or origins."""
    project = tmp_path / "project"
    evidence = project / "evidence" / "run-001"
    evidence.mkdir(parents=True)
    (evidence / "presentation.json").write_text("{}", encoding="utf-8")
    token_file = tmp_path / "console-token"
    token_file.write_text("secret-token\n", encoding="utf-8")

    with_token = _run_presentations(
        tmp_path, "hand-off", str(evidence),
        extra_env={
            "PROJECT_PATH": str(project),
            "DEVCAPSULE_CONSOLE_URL": "http://127.0.0.1:8787",
            "DEVCAPSULE_CONSOLE_TOKEN_FILE": str(token_file),
        },
    )
    assert with_token.returncode == 0, with_token.stderr
    assert with_token.stdout.strip() == "http://127.0.0.1:8787/presentations/evidence/run-001?token=secret-token"

    token_file.write_bytes(b"\xff\xfe\xfd")
    corrupt_token = _run_presentations(
        tmp_path, "hand-off", str(evidence),
        "--project", str(project), "--console-url", "http://127.0.0.1:8787", "--token-file", str(token_file),
    )
    assert corrupt_token.returncode == 0, corrupt_token.stderr
    assert "no readable run token was found" in corrupt_token.stdout
    assert corrupt_token.stdout.splitlines()[-1] == "http://127.0.0.1:8787/presentations/evidence/run-001"

    missing_url = _run_presentations(
        tmp_path, "hand-off", str(evidence), "--project", str(project), "--token-file", str(tmp_path / "absent"),
    )
    assert missing_url.returncode == 2
    assert "HTTP(S) console URL" in missing_url.stderr

    empty_dir = project / "evidence" / "empty"
    empty_dir.mkdir(parents=True)
    missing_deck = _run_presentations(
        tmp_path, "hand-off", str(empty_dir),
        "--project", str(project), "--console-url", "http://127.0.0.1:8787",
    )
    assert missing_deck.returncode == 2
    assert "no presentation.json" in missing_deck.stderr
