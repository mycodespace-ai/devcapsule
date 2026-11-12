"""Execute the base's console install script with local tools, without Docker or downloads."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from devcapsule.images import tooling

pytestmark = pytest.mark.legacy


@pytest.mark.integration
@pytest.mark.parametrize("failure", ["", "revision", "runtime-lock", "build-lock", "package", "import", "help"])
def test_console_install_checks_each_stage_before_continuing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    root = tmp_path / "console"
    python = root / "venv" / "bin" / "python"
    monkeypatch.setattr(tooling, "WEBCONSOLE_ROOT", str(root))
    monkeypatch.setattr(tooling, "WEBCONSOLE_VENV_PYTHON", str(python))
    tools = tmp_path / "tools"
    tools.mkdir()
    log = tmp_path / "calls.jsonl"
    stub = f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["INSTALL_TEST_LOG"], "a") as stream:
    stream.write(json.dumps([name, *args]) + "\\n")
failure = os.environ["INSTALL_TEST_FAILURE"]
if name == "git" and "rev-parse" in args:
    print("wrong" if failure == "revision" else os.environ["INSTALL_TEST_REVISION"])
elif name == "python3":
    target = pathlib.Path(args[-1]) / "bin" / "python"
    target.parent.mkdir(parents=True)
    target.write_text(pathlib.Path(__file__).read_text())
    target.chmod(0o755)
elif name == "python":
    if args[0] == "-c":
        stage = "import"
    elif "--help" in args:
        stage = "help"
    elif args[-1].endswith("requirements-build.txt"):
        stage = "build-lock"
    elif args[-1].endswith("requirements.txt"):
        stage = "runtime-lock"
    else:
        stage = "package"
    if stage == failure:
        sys.exit(9)
'''
    for name in ("git", "python3"):
        tool = tools / name
        tool.write_text(stub, encoding="utf-8")
        tool.chmod(0o755)
    # Shell metacharacters must reach git literally, never as shell syntax.
    repository = "https://github.com/example/$(printf altered)"
    revision = "a" * 40
    script = tooling.webconsole_tooling_component(repository, revision).args
    result = subprocess.run(script, text=True, capture_output=True, env={
        **os.environ, "PATH": f"{tools}:{os.environ['PATH']}", "TMPDIR": str(tmp_path),
        "INSTALL_TEST_LOG": str(log), "INSTALL_TEST_FAILURE": failure, "INSTALL_TEST_REVISION": revision,
    }, timeout=10)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    checkout = Path(calls[0][2])
    subproject = str(checkout / "devcapsule-webconsole")
    pip = ["python", "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check"]
    expected = [
        ["git", "-C", str(checkout), "init", "-q"],
        ["git", "-C", str(checkout), "fetch", "-q", "--depth", "1", repository, revision],
        ["git", "-C", str(checkout), "checkout", "-q", "--detach", "FETCH_HEAD"],
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        ["python3", "-m", "venv", str(root / "venv")],
        [*pip, "--require-hashes", "-r", f"{subproject}/requirements.txt"],
        [*pip, "--require-hashes", "-r", f"{subproject}/requirements-build.txt"],
        [*pip, "--no-deps", "--no-build-isolation", subproject],
        ["python", "-c", "import devcapsule_webconsole, fastapi, uvicorn"],
        ["python", "-m", "devcapsule_webconsole", "--help"],
    ]
    stop_after = {"revision": 4, "runtime-lock": 6, "build-lock": 7, "package": 8, "import": 9, "help": 10}
    assert calls == expected[:stop_after.get(failure, len(expected))]
    if failure:
        assert result.returncode != 0
    else:
        assert result.returncode == 0, result.stderr
        assert not checkout.exists()
