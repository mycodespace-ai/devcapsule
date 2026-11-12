"""Public information command: read-only discovery, storage and disclosure."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tomllib

import pytest

from devcapsule import cli, runtime_configuration
from devcapsule.configuration.file_formats import render_toml
from devcapsule.configuration.storage import checkout_record_paths
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy


@pytest.fixture
def project(tmp_path, monkeypatch):
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    monkeypatch.delenv("DEVCAPSULE_CONTAINER_NAME", raising=False)
    monkeypatch.setattr(runtime_configuration, "CONTEXT_PATH", tmp_path / "no-runtime")
    root = tmp_path / "project"
    config = root / ".devcapsule"
    config.mkdir(parents=True)
    manifest = {"devcapsule-schema-version": 1,
                "project": {"creator": "mailto:info@example.test", "slug": "info", "name": "Info fixture", "mount": "/workspace/info"},
                "capabilities": {"need": ["python", "python-ide", "codex-agent", "claude-code-agent", "antigravity-agent"]}}
    (config / "devcapsule.toml").write_text(render_toml(manifest))
    # Use the shipping lock schema without network access or initialization.
    lock = MATRICES[Platform.current()].resolve(manifest["capabilities"]["need"], allow_unverified=True).render_lock()
    (config / f"devcapsule.{Platform.current().value}.lock").write_text(lock)
    return root, manifest, tomllib.loads(lock)


def tree(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def information(root, capsys):
    assert cli.main(["project", "--path", str(root), "info", "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def test_info_without_registration_is_read_only_and_ignores_host_secrets(project, tmp_path, monkeypatch, capsys):
    root, _, lock = project
    nested = root / "src" / "pkg"
    nested.mkdir(parents=True)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-appear")
    monkeypatch.setenv("UNDECLARED_SECRET", "must-not-appear-either")
    monkeypatch.setenv("PATH", "/host/private-bin")
    before = tree(tmp_path)
    report = information(nested, capsys)
    assert report == information(root, capsys)
    assert tree(tmp_path) == before
    assert not report["checkout"]["registered"]
    assert report["components"]["codex"] == lock["components"]["codex"]["version"]
    assert "must-not-appear" not in json.dumps(report) and "/host/private-bin" not in json.dumps(report)
    persistence = {row["name"]: row for row in report["persistence"]}
    assert persistence["xtras"]["backing"] == persistence["home"]["backing"] + "/xtras"
    assert persistence["logs"]["path"] == "/var/log/devcapsule" and persistence["logs"]["kind"] == "state"
    assert persistence["logs"]["backing"].endswith("/logs") and "log budget (256 MiB" in persistence["logs"]["lifecycle"]
    assert persistence["codex/home"]["path"] == "/home/devcapsule/.codex"
    assert {row["path"] for row in report["temporary"]} >= {"/tmp", "/run", "/var/tmp"}
    assert not (tmp_path / "xdg_data_home").exists()
    assert cli.main(["project", "--path", str(nested), "info"]) == 0
    assert "/opt/xtras" in capsys.readouterr().out


def test_info_home_binding_and_default_checkout_isolation(project, tmp_path, capsys):
    root, manifest, _ = project
    other = tmp_path / "other"
    shutil.copytree(root, other)
    first = information(root, capsys)
    second = information(other, capsys)
    home = lambda report: next(row for row in report["persistence"] if row["name"] == "home")
    assert home(first)["backing"] != home(second)["backing"]
    record, _ = checkout_record_paths(manifest, root)
    record.parent.mkdir(parents=True)
    record.write_text(render_toml({"devcapsule-checkout-schema-version": 1,
        "project": {"creator": manifest["project"]["creator"], "slug": manifest["project"]["slug"]},
        "checkout": {"path": str(root)},
        "configuration": {"bindings": {"host-directory": {"home": "/external/shared-home"}}}}))
    before = tree(tmp_path)
    report = information(root, capsys)
    assert report["checkout"]["registered"] is True
    assert report["checkout"]["name"] == "default"
    assert home(report)["backing"] == "/external/shared-home"
    assert "shared" in home(report)["scope"]
    assert tree(tmp_path) == before


def test_info_outside_a_project_requires_discovery(project, tmp_path, capsys):
    assert cli.main(["project", "--path", str(tmp_path), "info"]) == 2
    assert "Traceback" not in capsys.readouterr().err


@pytest.mark.parametrize("name", ["dogfood", "devcapsule"])
def test_info_names_a_named_checkout_from_its_record_location(project, capsys, name):
    """The checkout's name is where its record lives, not a key in the record:
    a record under ``checkouts/`` is named after its file, ``devcapsule`` included."""
    root, manifest, _ = project
    from devcapsule.configuration.storage import checkout_directory
    assert information(root, capsys)["checkout"] == {
        "launcher-path": str(root), "runtime-path": "/workspace/info", "name": "default", "registered": False,
    }
    record = checkout_directory(manifest) / "checkouts" / f"{name}.checkout.toml"
    record.parent.mkdir(parents=True)
    record.write_text(render_toml({"devcapsule-checkout-schema-version": 1,
        "project": {"creator": manifest["project"]["creator"], "slug": manifest["project"]["slug"]},
        "checkout": {"path": str(root)}}))
    report = information(root, capsys)
    assert report["checkout"] == {
        "launcher-path": str(root), "runtime-path": "/workspace/info", "name": name, "registered": True,
    }
    assert cli.main(["project", "--path", str(root), "info"]) == 0
    text = capsys.readouterr().out
    assert f"Checkout: {root}\nCheckout name: {name}\n" in text
