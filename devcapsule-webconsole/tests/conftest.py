"""Fixtures: a project tree, a run token, and a fake runtime CLI.

The fake CLI is a Python script that answers the three ``project`` commands
with canned documents and records every invocation, so tests can check both
what the console asked and what it served. Its exit status and output are
steerable through environment variables.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import textwrap
from typing import Any, Iterator
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from devcapsule_webconsole.app import create_app
from devcapsule_webconsole.security import token_cookie_name
from devcapsule_webconsole.settings import Settings

TOKEN = "0123456789abcdef0123456789abcdef0123456789abcdef"

CONFIGURATION = {
    "schema-version": 1, "context": "host selection (next launch)",
    "project": {"creator": "mailto:dev@example.test", "slug": "sample"},
    "checkout": {"name": "default", "launcher-path": "/home/dev/sample",
                 "input": "/home/dev/.config/devcapsule/projects/x/sample/devcapsule.checkout.toml",
                 "resolution": "/home/dev/.config/devcapsule/projects/x/sample/devcapsule.resolved.toml"},
    "rows": [{"kind": "value", "name": "runtime.memory-limit", "status": "unset-optional",
              "source": "manifest (declared, no value)", "value": "-"},
             {"kind": "resolution", "name": "generated", "status": "fresh", "source": "resolution",
              "value": "/home/dev/.config/devcapsule/projects/x/sample/devcapsule.resolved.toml"}],
}
VERSIONS = {
    "schema-version": 1, "context": "host selection (next launch)",
    "selected": {"identity": "set-aaaa", "origin": "project recommendation", "platform": "linux-amd64",
                 "base": {"reference": "docker.io/example/base@sha256:ab"}, "components": {"codex": "1.0.0"},
                 "local-base-override": None},
    "project-recommendation": None,
    "validation": {"evidence": [], "not-yet-validated": ["codex 1.0.0 on base v9"]},
    "local-use": {"zero-exit-launch-recorded": False},
}
INFORMATION = {
    "schema-version": 1, "context": "host selection (next launch)",
    "project": {"name": "Sample", "creator": "mailto:dev@example.test", "slug": "sample"},
    "checkout": {"launcher-path": "/home/dev/sample", "runtime-path": "/workspace/sample", "name": "default", "registered": True},
    "components": {"codex": "1.0.0"}, "base": {"reference": "docker.io/example/base@sha256:ab", "build-mnemonic": "v0.2.15"},
    "environment": [{"name": "HOME", "value": "/home/devcapsule", "purpose": "home", "source": "configured"}],
    "persistence": [], "temporary": ["/tmp"], "notes": ["note"],
}

FAKE_CLI = textwrap.dedent(
    '''
    import json, os, sys
    log = os.environ["FAKE_CLI_LOG"]
    with open(log, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(sys.argv[1:]) + "\\n")
    if os.environ.get("FAKE_CLI_EXIT", "0") != "0":
        sys.stderr.write("devcapsule: the fixture refused\\n")
        sys.exit(int(os.environ["FAKE_CLI_EXIT"]))
    if os.environ.get("FAKE_CLI_GARBAGE"):
        sys.stdout.write("not json\\n")
        sys.exit(0)
    documents = json.loads(os.environ["FAKE_CLI_DOCUMENTS"])
    key = " ".join(argument for argument in sys.argv[1:] if argument not in ("project", "--json") and not argument.startswith("/") and argument != "--path")
    sys.stdout.write(json.dumps(documents[key]))
    '''
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".devcapsule").mkdir(parents=True)
    (root / ".devcapsule" / "devcapsule.toml").write_text('[project]\nslug = "sample"\n', encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# Guide\n\nText.\n", encoding="utf-8")
    (root / "image.bin").write_bytes(b"\xff\xfe\x00binary")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")
    (root / "escape.md").symlink_to(outside)
    return root


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[tuple[str, ...], Path]:
    script = tmp_path / "fake-devcapsule.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    log = tmp_path / "cli-log.jsonl"
    monkeypatch.setenv("FAKE_CLI_LOG", str(log))
    monkeypatch.setenv("FAKE_CLI_DOCUMENTS", json.dumps({
        "config show": CONFIGURATION, "versions show": VERSIONS, "info": INFORMATION,
    }))
    monkeypatch.delenv("FAKE_CLI_EXIT", raising=False)
    monkeypatch.delenv("FAKE_CLI_GARBAGE", raising=False)
    return (sys.executable, str(script)), log


@pytest.fixture
def settings(project: Path, fake_cli: tuple[tuple[str, ...], Path]) -> Settings:
    return Settings(project=project, cli=fake_cli[0], token=TOKEN, decisions=project.parent / "decisions")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as client:
        yield client


def invocations(log: Path) -> list[list[str]]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def with_token(client: TestClient) -> TestClient:
    client.cookies.set(token_cookie_name(urlsplit(str(client.base_url)).port), TOKEN)
    return client


def document_env(**documents: Any) -> dict[str, str]:
    return {"FAKE_CLI_DOCUMENTS": json.dumps(documents)}


__all__ = ["TOKEN", "CONFIGURATION", "VERSIONS", "INFORMATION", "invocations", "with_token", "os"]
