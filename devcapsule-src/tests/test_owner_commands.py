"""The owner's commands: require, offer, drop and recommend, over the one manifest writer."""

from __future__ import annotations

from pathlib import Path
import json
import tomllib
from typing import Any

import pytest

from devcapsule import cli
from devcapsule.configuration import owner_commands
from devcapsule.configuration.capability_commands import paths
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.manifest_document import render_manifest
from devcapsule.configuration.storage import load_toml
from devcapsule.configuration.storage import checkout_record_paths
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy

MATRIX = MATRICES[Platform.LINUX_AMD64]


def identity() -> dict:
    return {"creator": "mailto:owner@example.test", "slug": "sample", "name": "Sample", "mount": "/workspace/sample"}


@pytest.fixture
def legacy_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A 0.2.x project: schema 1, ``need`` with the IDE inside, a lock holding the IDE."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "legacy"
    (root / ".devcapsule").mkdir(parents=True)
    (root / ".devcapsule/devcapsule.toml").write_text(
        "# The owner's note\n\n" + render_toml({"devcapsule-schema-version": 1, "project": identity(),
                                               "capabilities": {"need": ["python", "python-ide"]}})
    )
    (root / ".devcapsule/devcapsule.linux-amd64.lock").write_text(MATRIX.resolve(["python", "python-ide"]).render_lock())
    return root


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project in the required form, created by init without an IDE."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--require", "python", "--creator", "mailto:owner@example.test"]) == 0
    return root


def manifest_text(root: Path) -> str:
    return paths(root)[0].read_text()


def test_require_tool_adds_regenerates_the_lock_and_writes_schema_two(project: Path, capsys) -> None:
    assert cli.main(["project", "--path", str(project), "config", "require", "node", "postgresql-client",
                     "--because", "the API and its database"]) == 0
    out = capsys.readouterr().out
    assert "Required node, postgresql-client" in out and "Required: python node postgresql-client" in out
    manifest = load_toml(paths(project)[0])
    assert manifest["devcapsule-schema-version"] == 2
    assert manifest["capabilities"] == {"required": ["python", "node", "postgresql-client"],
                                        "reasons": {"node": "the API and its database", "postgresql-client": "the API and its database"}}
    lock = load_toml(paths(project)[1])
    assert "postgresql-client" in lock["components"] and "interactive-surface" not in lock["components"]
    text = manifest_text(project)
    assert "[capabilities]\nrequired = [" in text and '"required"' not in text


def test_require_tool_and_drop_removes_it(project: Path) -> None:
    owner_commands.require_tools(project, ["dotnet"])
    manifest = load_toml(paths(project)[0])
    assert manifest["capabilities"]["required"] == ["dotnet", "python"]
    owner_commands.drop_tools(project, ["dotnet", "python"])
    manifest = load_toml(paths(project)[0])
    assert manifest["capabilities"] == {"required": []}
    with pytest.raises(ProjectConfigurationError, match="Not declared"):
        owner_commands.drop_tools(project, ["python"])


def test_offer_moves_a_tool_out_of_required_and_drops_its_major(project: Path) -> None:
    owner_commands.offer_tools(project, ["browser-automation"], because="end-to-end tests")
    manifest = load_toml(paths(project)[0])
    assert manifest["capabilities"]["optional"] == ["browser-automation"]
    assert manifest["capabilities"]["reasons"] == {"browser-automation": "end-to-end tests"}
    with pytest.raises(ProjectConfigurationError, match="Unknown tool"):
        owner_commands.offer_tools(project, ["python=3"])
    owner_commands.offer_tools(project, ["python"])
    assert load_toml(paths(project)[0])["capabilities"] == {"optional": ["browser-automation", "python"], "required": [],
                                                            "reasons": {"browser-automation": "end-to-end tests"}}


@pytest.mark.parametrize("name", ["codex-agent", "codex", "claude-code-agent"])
def test_agent_names_are_project_capabilities(project: Path, name: str) -> None:
    expected = "codex-agent" if name == "codex" else name
    owner_commands.require_tools(project, [name])
    assert expected in load_toml(paths(project)[0])["capabilities"]["required"]
    owner_commands.offer_tools(project, [name])
    assert expected in load_toml(paths(project)[0])["capabilities"]["optional"]


@pytest.mark.parametrize("name", ["python=3", "python>=3.12", "codex=1"])
def test_cli_version_forms_are_refused_before_writes(project: Path, name: str) -> None:
    before = manifest_text(project)
    with pytest.raises(ProjectConfigurationError, match="Unknown tool"):
        owner_commands.require_tools(project, [name])
    assert manifest_text(project) == before


@pytest.mark.parametrize("name", ["frontend-ide", "pycharm"])
def test_ide_names_are_refused_as_project_tools(project: Path, name: str) -> None:
    before = manifest_text(project)
    with pytest.raises(ProjectConfigurationError, match="each developer's"):
        owner_commands.require_tools(project, [name])
    assert manifest_text(project) == before


def test_a_sole_provider_component_id_names_its_tool(project: Path) -> None:
    owner_commands.offer_tools(project, ["playwright"])
    assert load_toml(paths(project)[0])["capabilities"]["optional"] == ["browser-automation"]
    with pytest.raises(ProjectConfigurationError, match="Unknown tool 'nodejs'"):
        owner_commands.require_tools(project, ["nodejs"])


def test_preview_writes_nothing(project: Path) -> None:
    before = {path: path.read_bytes() for path in (project / ".devcapsule").iterdir()}
    assert owner_commands.require_tools(project, ["node"], preview=True).startswith("Preview")
    assert owner_commands.require_environment(project, ["X"], preview=True).startswith("Preview")
    assert owner_commands.recommend(project, "memory", "6g", preview=True).startswith("Preview")
    assert {path: path.read_bytes() for path in (project / ".devcapsule").iterdir()} == before


def test_environment_require_offer_drop_with_reasons(project: Path, capsys) -> None:
    lock_before = paths(project)[1].read_bytes()
    assert cli.main(["project", "--path", str(project), "config", "require", "env", "POSTGRES_HOST", "POSTGRES_PASSWORD",
                     "--because", "the owner supplies the database"]) == 0
    assert cli.main(["project", "--path", str(project), "config", "offer", "env", "SMTP_HOST"]) == 0
    out = capsys.readouterr().out
    assert "Required environment: POSTGRES_HOST (the owner supplies the database), POSTGRES_PASSWORD (the owner supplies the database)" in out
    assert "this command stores declarations only" in out
    manifest = load_toml(paths(project)[0])
    assert manifest["environment"] == {"required": {"POSTGRES_HOST": {"reason": "the owner supplies the database"},
                                                    "POSTGRES_PASSWORD": {"reason": "the owner supplies the database"}},
                                       "optional": {"SMTP_HOST": {}}}
    assert paths(project)[1].read_bytes() == lock_before, "an environment edit leaves the lock's bytes alone"
    # Offering a required name moves it and keeps its reason; dropping removes it.
    owner_commands.offer_environment(project, ["POSTGRES_PASSWORD"])
    manifest = load_toml(paths(project)[0])
    assert manifest["environment"]["optional"]["POSTGRES_PASSWORD"] == {"reason": "the owner supplies the database"}
    owner_commands.drop_environment(project, ["POSTGRES_HOST", "POSTGRES_PASSWORD", "SMTP_HOST"])
    assert "environment" not in load_toml(paths(project)[0])
    with pytest.raises(ProjectConfigurationError, match="Not declared"):
        owner_commands.drop_environment(project, ["SMTP_HOST"])
    with pytest.raises(ProjectConfigurationError, match="ASCII identifiers"):
        owner_commands.require_environment(project, ["POSTGRES-HOST"])


def test_recommend_ide_memory_cpus_and_none(project: Path, capsys) -> None:
    assert cli.main(["project", "--path", str(project), "config", "recommend", "ide", "codium"]) == 0
    assert cli.main(["project", "--path", str(project), "config", "recommend", "memory", "6G", "--because", "the index"]) == 0
    assert cli.main(["project", "--path", str(project), "config", "recommend", "cpus", "4"]) == 0
    out = capsys.readouterr().out
    assert "Recommended ide = frontend-ide" in out and "Recommended memory = 6GiB" in out
    manifest = load_toml(paths(project)[0])
    assert manifest["recommendations"] == {"ide": "frontend-ide", "memory": "6GiB", "cpus": 4, "reasons": {"memory": "the index"}}
    owner_commands.recommend(project, "memory", "none")
    assert load_toml(paths(project)[0])["recommendations"] == {"ide": "frontend-ide", "cpus": 4}
    with pytest.raises(ProjectConfigurationError, match="recommends no memory"):
        owner_commands.recommend(project, "memory", "none")
    with pytest.raises(ProjectConfigurationError, match="Unknown IDE"):
        owner_commands.recommend(project, "ide", "emacs")
    with pytest.raises(ProjectConfigurationError, match="positive integer"):
        owner_commands.recommend(project, "cpus", "two")
    with pytest.raises(ProjectConfigurationError, match="Unknown recommendation"):
        owner_commands.recommend(project, "swap", "1g")


def test_recommend_host_access_needs_the_reason_and_writes_the_curated_table(project: Path) -> None:
    with pytest.raises(ProjectConfigurationError, match="--because"):
        owner_commands.recommend(project, "network", "host")
    with pytest.raises(ProjectConfigurationError, match="accepts exactly 'host'"):
        owner_commands.recommend(project, "network", "bridge", because="x")
    owner_commands.recommend(project, "network", "host", because="the dev servers share localhost")
    owner_commands.recommend(project, "development-sudo", "true", because="apt in the capsule")
    manifest = load_toml(paths(project)[0])
    assert manifest["host"] == {
        "network": {"mode": {"recommended": {"value": "host", "justification": "the dev servers share localhost"}}},
        "privilege": {"development-sudo": {"recommended": {"value": True, "justification": "apt in the capsule"}}},
    }
    owner_commands.recommend(project, "network", "none")
    assert load_toml(paths(project)[0])["host"] == {
        "privilege": {"development-sudo": {"recommended": {"value": True, "justification": "apt in the capsule"}}},
    }
    owner_commands.recommend(project, "development-sudo", "none")
    assert "host" not in load_toml(paths(project)[0])


def test_an_owner_edit_converts_a_legacy_manifest_and_keeps_its_leading_comment(legacy_project: Path) -> None:
    owner_commands.require_tools(legacy_project, ["node"])
    text = manifest_text(legacy_project)
    assert text.startswith("# The owner's note\n\ndevcapsule-schema-version = 2\n")
    manifest = tomllib.loads(text)
    assert "need" not in manifest["capabilities"]
    # The IDE in ``need`` becomes the project's recommendation; the regenerated
    # lock is project-only, as every lock written since rc4.
    assert manifest["capabilities"]["required"] == ["node", "python"]
    assert manifest["recommendations"] == {"ide": "python-ide"}
    assert "interactive-surface" not in load_toml(paths(legacy_project)[1])["components"]


def test_an_unrelated_command_never_rewrites_a_legacy_manifest(legacy_project: Path) -> None:
    before = manifest_text(legacy_project)
    assert cli.main(["project", "--path", str(legacy_project), "config", "check"]) in (0, 3)
    assert cli.main(["project", "--path", str(legacy_project), "config", "ide", "python-ide"]) == 0
    assert cli.main(["project", "--path", str(legacy_project), "config", "show"]) == 0
    assert manifest_text(legacy_project) == before


def test_drop_offered_tool_removes_only_its_declaration_and_reason(project: Path) -> None:
    owner_commands.require_tools(project, ["python"], because="backend")
    owner_commands.offer_tools(project, ["playwright"], because="browser tests")
    owner_commands.drop_tools(project, ["playwright"])
    assert load_toml(paths(project)[0])["capabilities"] == {
        "required": ["python"], "reasons": {"python": "backend"},
    }
    assert "playwright" not in load_toml(paths(project)[1])["components"]
    owner_commands.drop_tools(project, ["python"])
    assert load_toml(paths(project)[0])["capabilities"] == {"required": []}


@pytest.mark.parametrize("name,value,keys", [
    ("docker-daemon", "host-socket", ("docker", "mode", "recommended")),
    ("network", "host", ("network", "mode", "recommended")),
    ("development-sudo", "true", ("privilege", "development-sudo", "recommended")),
    ("host-browser", "true", ("browser", "host-open", "recommended")),
])
def test_each_host_recommendation_and_removal_preserves_siblings(project: Path, name, value, keys) -> None:
    owner_commands.recommend(project, "memory", "1g", because="index")
    before = load_toml(paths(project)[0])
    before["host"] = {keys[0]: {"extension": {"keep": True}}}
    paths(project)[0].write_text(render_toml(before))
    lock_before = paths(project)[1].read_bytes()
    owner_commands.recommend(project, name, value, because="owner reason")
    manifest = load_toml(paths(project)[0])
    node = manifest["host"]
    for key in keys:
        node = node[key]
    assert node == {"value": True if value == "true" else value, "justification": "owner reason"}
    owner_commands.recommend(project, name, "none")
    assert load_toml(paths(project)[0]) == before
    assert paths(project)[1].read_bytes() == lock_before


@pytest.mark.parametrize("name", ["ide", "memory", "cpus"])
def test_remove_one_ordinary_recommendation_keeps_the_other_values_and_reasons(project: Path, name: str) -> None:
    for key, value in (("ide", "pycharm"), ("memory", "512mb"), ("cpus", "2")):
        owner_commands.recommend(project, key, value, because=key)
    expected = load_toml(paths(project)[0])["recommendations"]
    del expected[name]
    del expected["reasons"][name]
    owner_commands.recommend(project, name, "none")
    assert load_toml(paths(project)[0])["recommendations"] == expected


def test_owner_edits_preserve_unknown_declaration_metadata(project: Path) -> None:
    manifest = load_toml(paths(project)[0])
    manifest["workflow-type"] = "multiple-streams"
    manifest["capabilities"]["extension"] = {"keep": 1.5}
    manifest["environment"] = {"required": {"DB_HOST": {"reason": "db", "extension": {"keep": True}}},
                               "optional": {"MAIL_HOST": {"extension": "smtp"}}}
    paths(project)[0].write_text(render_manifest(manifest))
    owner_commands.require_tools(project, ["node"])
    assert load_toml(paths(project)[0])["capabilities"]["extension"] == {"keep": 1.5}
    owner_commands.offer_environment(project, ["DB_HOST"], because="optional db")
    owner_commands.require_environment(project, ["NEW"])
    result = load_toml(paths(project)[0])
    # The root key of schema 1 folds into [workflow].mode and is not written again.
    assert "workflow-type" not in result and result["workflow"]["mode"] == "multiple-streams"
    assert result["environment"] == {
        "required": {"NEW": {}},
        "optional": {"DB_HOST": {"reason": "optional db", "extension": {"keep": True}},
                     "MAIL_HOST": {"extension": "smtp"}},
    }


@pytest.mark.parametrize("pending_ide", [False, True])
def test_tool_edit_does_not_change_checkout_answers_when_not_ready(project: Path, pending_ide: bool) -> None:
    if pending_ide:
        assert cli.main(["project", "--path", str(project), "config", "ide", "python-ide"]) == 0
    record, resolution = checkout_record_paths(load_toml(paths(project)[0]), project)
    before = record.read_bytes()
    report = owner_commands.require_tools(project, ["node"])
    assert "Your checkout is not ready to run yet" in report
    assert record.read_bytes() == before
    assert not resolution.exists()


@pytest.mark.parametrize("verb", ["require", "offer", "drop"])
def test_owner_tool_help_has_no_removed_version_syntax(capsys, verb: str) -> None:
    assert cli.main(["project", "config", verb, "tool", "--help"]) == 0
    output = capsys.readouterr().out
    assert "TOOL[=MAJOR]" not in output
    assert "python=3" not in output


@pytest.mark.parametrize("kind", ["tool", "env", "recommendation"])
def test_invalid_reason_is_refused_without_writing(project: Path, kind: str) -> None:
    before = {path: path.read_bytes() for path in (project / ".devcapsule").iterdir()}
    with pytest.raises(ProjectConfigurationError, match="must be a string"):
        if kind == "tool":
            owner_commands.require_tools(project, ["node"], because="bad\x00reason")
        elif kind == "env":
            owner_commands.require_environment(project, ["DB_HOST"], because="bad\x00reason")
        else:
            owner_commands.recommend(project, "memory", "1g", because="bad\x00reason")
    assert {path: path.read_bytes() for path in (project / ".devcapsule").iterdir()} == before


def test_host_recommendation_edit_keeps_its_enables_metadata(project: Path) -> None:
    owner_commands.recommend(project, "network", "host", because="old reason")
    manifest = load_toml(paths(project)[0])
    manifest["host"]["network"]["mode"]["recommended"]["enables"] = ["dev-server"]
    paths(project)[0].write_text(render_manifest(manifest))
    owner_commands.recommend(project, "network", "host", because="new reason")
    assert load_toml(paths(project)[0])["host"]["network"]["mode"]["recommended"] == {
        "value": "host", "justification": "new reason", "enables": ["dev-server"],
    }


@pytest.mark.parametrize("value", ["python", "codex", "codex-agent", "unknown-ide"])
def test_recommend_ide_refuses_non_surfaces(project: Path, value: str) -> None:
    before = paths(project)[0].read_bytes()
    with pytest.raises(ProjectConfigurationError, match="Unknown IDE"):
        owner_commands.recommend(project, "ide", value)
    assert paths(project)[0].read_bytes() == before


@pytest.mark.parametrize("value,canonical", [("12b", "12B"), ("512K", "512KiB"), ("6GB", "6GiB"), ("2t", "2TiB")])
def test_recommend_memory_stores_canonical_units(project: Path, value: str, canonical: str) -> None:
    owner_commands.recommend(project, "memory", value)
    assert load_toml(paths(project)[0])["recommendations"]["memory"] == canonical


@pytest.mark.parametrize("command", [["init"], ["config", "require"], ["config", "offer"], ["config", "drop"], ["config", "recommend"]])
def test_owner_help_discloses_schema_two_compatibility(capsys, command) -> None:
    assert cli.main(["project", *command, "--help"]) == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "rc3 and older launchers cannot read" in help_text


def test_declare_source_writes_the_table_and_leaves_the_lock_bytes_alone(project: Path, capsys) -> None:
    lock_before = paths(project)[1].read_bytes()
    assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
    capsys.readouterr()
    text = owner_commands.declare_source(project, "RobotCode2025Public", java="17")
    assert text.splitlines()[0] == "Declared source RobotCode2025Public; the manifest is updated."
    assert "learn from it" in text and "Java 17" in text
    manifest = load_toml(paths(project)[0])
    assert manifest["sources"] == {"RobotCode2025Public": {"java": "17"}}
    assert paths(project)[1].read_bytes() == lock_before
    assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
    assert "source      RobotCode2025Public  java 17" in capsys.readouterr().out.replace("  ", "  ")


def test_declare_source_again_replaces_known_keys_and_keeps_unknown_ones(project: Path) -> None:
    owner_commands.declare_source(project, "robot", upstream="https://example.test/up", java="17")
    manifest_path = paths(project)[0]
    manifest_path.write_text(manifest_path.read_text().replace('java = "17"', 'java = "17"\nfuture = "kept"'))
    text = owner_commands.declare_source(project, "robot", java="21")
    assert text.splitlines()[0] == "Redeclared source robot; the manifest is updated."
    assert load_toml(manifest_path)["sources"] == {"robot": {"java": "21", "future": "kept"}}


def test_declare_source_preview_and_refusals_write_nothing(project: Path) -> None:
    before = manifest_text(project)
    assert owner_commands.declare_source(project, "robot", java="17", preview=True).startswith("Preview; nothing written.")
    with pytest.raises(ProjectConfigurationError, match="source path"):
        owner_commands.declare_source(project, "../robot")
    with pytest.raises(ProjectConfigurationError, match="Java line"):
        owner_commands.declare_source(project, "robot", java="17.0")
    with pytest.raises(ProjectConfigurationError, match="upstream"):
        owner_commands.declare_source(project, "robot", upstream="  ")
    assert manifest_text(project) == before


@pytest.mark.parametrize("fields", [
    {"path": ""}, {"path": "../escape"}, {"path": 3},
    {"upstream": 3}, {"upstream": "bad\x00url"}, {"upstream": " "},
    {"java": 17}, {"java": "0"}, {"java": "17\n"},
])
def test_declare_source_refuses_malformed_inputs_without_touching_files(project: Path, fields: dict[str, Any]) -> None:
    manifest_path, lock_path, _ = paths(project)
    before = manifest_path.read_bytes(), lock_path.read_bytes()
    with pytest.raises(ProjectConfigurationError):
        owner_commands.declare_source(project, **{"path": "vendor/robot", **fields})
    assert (manifest_path.read_bytes(), lock_path.read_bytes()) == before


def test_sources_survive_other_owner_edits_and_do_not_change_pending_decisions(project: Path, capsys) -> None:
    assert cli.main(["project", "--path", str(project), "config", "show", "--json"]) == 0
    baseline = json.loads(capsys.readouterr().out)
    owner_commands.declare_source(project, 'vendor/robot.code', upstream="https://example.test/up", java="17")
    owner_commands.declare_source(project, "notes")
    manifest_path, lock_path, _ = paths(project)
    manifest_path.write_text(manifest_path.read_text().replace('java = "17"', 'java = "17"\nfuture = { extra = true }'))
    sources = load_toml(manifest_path)["sources"]
    owner_commands.recommend(project, "memory", "4g")
    assert load_toml(manifest_path)["sources"] == sources
    lock = lock_path.read_bytes()
    owner_commands.declare_source(project, "notes", preview=True)
    assert lock_path.read_bytes() == lock
    assert cli.main(["project", "--path", str(project), "config", "show", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["pending"] == baseline["pending"]
    assert [row for row in document["rows"] if row["kind"] == "source"] == [
        {"kind": "source", "name": "notes", "effective": "no toolchain declared", "source": "project: upstream, read-only", "pending": "", "command": ""},
        {"kind": "source", "name": "vendor/robot.code", "effective": "java 17", "source": "project: fork of https://example.test/up", "pending": "", "command": ""},
    ]
