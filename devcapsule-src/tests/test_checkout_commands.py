"""The checkout's verbs: ide, agent, tool, set, default, env, docker-args, deny, forget, unbind, show, check."""

from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import json
import os
import re
from pathlib import Path
import tomllib

import pytest

from devcapsule import cli
from devcapsule.configuration.storage import checkout_record_paths, load_toml, registered_checkouts
from devcapsule.configuration.docker_arguments import arguments_path, read_arguments
from devcapsule.configuration.capability_commands import paths

pytestmark = pytest.mark.legacy


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--require", "node", "--offer", "browser-automation",
                     "--creator", "mailto:owner@example.test"]) == 0
    return root


def run(root: Path, *arguments: str) -> int:
    return cli.main(["project", "--path", str(root), "config", *arguments])


def record(root: Path) -> dict:
    manifest = load_toml(paths(root)[0])
    return load_toml(checkout_record_paths(manifest, root)[0])


def test_show_and_check_write_nothing_and_check_exits_three_on_pending(project: Path, capsys, tmp_path: Path) -> None:
    manifest = load_toml(paths(project)[0])
    input_path, resolution_path = checkout_record_paths(manifest, project)
    before = input_path.read_bytes()
    assert run(project, "show") == 0
    out = capsys.readouterr().out
    assert "KIND" in out and any(line.split()[:2] == ["ide", "(none)"] for line in out.splitlines()) and "choose one:" in out
    assert run(project, "check") == 3
    err = capsys.readouterr().err
    assert "Pending decisions:" in err and "config ide IDE" in err
    assert input_path.read_bytes() == before and not resolution_path.exists()
    # An unregistered checkout is listed too, from nothing.
    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / ".devcapsule").mkdir()
    for name in ("devcapsule.toml", "devcapsule.linux-amd64.lock"):
        (other / ".devcapsule" / name).write_bytes((project / ".devcapsule" / name).read_bytes())
    assert run(other, "show") == 0
    assert "no record yet" in capsys.readouterr().out
    assert len(registered_checkouts()) == 1


def test_show_json_carries_the_listing(project: Path, capsys) -> None:
    assert run(project, "show", "--json") == 0
    document = json.loads(capsys.readouterr().out)
    assert document["schema-version"] == 2
    assert {row["kind"] for row in document["rows"]} >= {"ide", "capability", "memory", "cpus", "access"}
    assert run(project, "check", "--json") == 3
    assert "(none)" in json.loads(capsys.readouterr().out)["pending"]


def test_ide_agent_and_tool_verbs_edit_the_selection(project: Path, capsys) -> None:
    assert run(project, "ide", "codium") == 0
    assert "frontend-ide (codium)" in capsys.readouterr().out
    assert run(project, "add", "codex") == 0
    assert run(project, "add", "claude-code-agent") == 0
    assert record(project)["capabilities"]["selected"] == ["claude-code-agent", "codex-agent", "frontend-ide"]
    assert run(project, "omit", "codex-agent") == 0
    assert run(project, "ide", "python-ide") == 0
    assert record(project)["capabilities"]["selected"] == ["claude-code-agent", "python-ide"]
    assert run(project, "omit", "browser-automation") == 0
    assert record(project)["capabilities"]["without"] == ["browser-automation"]
    assert run(project, "restore", "browser-automation") == 0
    assert record(project)["capabilities"]["without"] == []
    assert run(project, "omit", "node") == 2
    assert "cannot be omitted" in capsys.readouterr().err
    assert run(project, "ide", "emacs") == 2
    assert "Unknown IDE" in capsys.readouterr().err
    assert run(project, "add", "python-ide") == 2


def test_set_memory_cpus_default_and_declared_values(project: Path, capsys, monkeypatch) -> None:
    assert run(project, "set", "memory", "6g") == 0
    assert "Set memory = 6GiB" in capsys.readouterr().out
    assert run(project, "set", "cpus", "4") == 0
    assert record(project)["configuration"]["values"] == {"memory": "6GiB", "cpus": 4}
    assert run(project, "set", "cpus", "default") == 0
    assert "cpus" not in record(project)["configuration"]["values"]
    assert run(project, "set", "memory", "none") == 2
    assert run(project, "set", "memroy", "1g") == 2
    assert "Did you mean 'memory'?" in capsys.readouterr().err
    assert cli.main(["home", "default", "cpus", "2"]) == 0
    assert cli.main(["home", "default", "swap", "2"]) == 2
    home = tomllib.loads((Path(os.environ["XDG_CONFIG_HOME"]) / "devcapsule" / "settings.toml").read_text())
    assert home["defaults"] == {"cpus": 2}
    assert run(project, "show") == 0
    out = capsys.readouterr().out
    assert "home default" in out
    assert cli.main(["home", "default", "cpus", "none"]) == 0
    assert tomllib.loads((Path(os.environ["XDG_CONFIG_HOME"]) / "devcapsule" / "settings.toml").read_text())["defaults"] == {}


def test_legacy_memory_name_redirects_to_memory(project: Path, capsys) -> None:
    manifest_path = paths(project)[0]
    manifest_path.write_text(manifest_path.read_text() + '\n[configuration.values."runtime.memory-limit"]\ntype = "memory-size"\nruntime-effect = "docker.memory-limit"\n')
    assert run(project, "set", "runtime.memory-limit", "8GiB") == 2
    assert "config set memory SIZE" in capsys.readouterr().err
    assert run(project, "set", "memory", "8GiB") == 0


def test_env_set_from_host_unset_and_list(project: Path, capsys) -> None:
    assert run(project, "env", "set", "POSTGRES_HOST", "db.example.org") == 0
    assert run(project, "env", "set", "POSTGRES_PASSWORD", "--from-host") == 0
    assert run(project, "env", "set", "BOTH", "x", "--from-host") == 2
    assert run(project, "env", "list") == 0
    out = capsys.readouterr().out
    assert "POSTGRES_HOST  (saved)" in out and "POSTGRES_PASSWORD  (from the host)" in out and "db.example.org" not in out
    manifest = load_toml(paths(project)[0])
    saved = read_arguments(arguments_path(checkout_record_paths(manifest, project)[0]))
    assert saved == ["--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_HOST=db.example.org"]
    assert run(project, "env", "unset", "POSTGRES_HOST") == 0
    capsys.readouterr()
    assert run(project, "env", "list", "--json") == 0
    assert json.loads(capsys.readouterr().out)["from-host"] == ["POSTGRES_PASSWORD"]
    assert run(project, "env", "set", "OLD", "v") == 0
    assert run(project, "show") == 0
    out = capsys.readouterr().out
    assert re.search(r"^env\s+OLD\s+set\s+checkout", out, re.M)


def test_env_without_a_terminal_needs_a_value(project: Path, capsys, monkeypatch) -> None:
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert run(project, "env", "set", "SECRET") == 2
    assert "terminal is required" in capsys.readouterr().err


def test_docker_args_set_list_clear(project: Path, capsys) -> None:
    assert run(project, "docker-args", "set", "--", "--gpus", "all", "--env", "K=secret") == 0
    assert run(project, "docker-args", "list") == 0
    out = capsys.readouterr().out
    assert "--gpus all" in out and "K=<redacted>" in out
    assert run(project, "docker-args", "set", "--", "--memory", "2g") == 2
    assert "config set memory SIZE" in capsys.readouterr().err
    assert run(project, "docker-args", "set", "--", "--cpus", "2") == 2
    assert run(project, "docker-args", "set") == 2
    assert run(project, "docker-args", "clear") == 0
    capsys.readouterr()
    assert run(project, "docker-args", "list", "--json") == 0
    assert json.loads(capsys.readouterr().out)["arguments"] == []
    assert run(project, "docker-args", "set", "--", "--gpus", "all") == 0


def test_authorize_deny_forget_and_the_wording(project: Path, capsys) -> None:
    assert run(project, "authorize", "network", "host") == 0
    out = capsys.readouterr().out
    assert "Authorized network for this checkout: host" in out
    assert "What this grants:" in out and "exact recorded image" not in out
    assert run(project, "deny", "docker-daemon") == 0
    assert "Denied docker-daemon for this checkout: none" in capsys.readouterr().out
    assert record(project)["authorization"]["docker-daemon"]["value"] == "none"
    assert run(project, "deny", "base-image") == 2
    assert run(project, "forget", "network") == 0
    assert "network" not in record(project)["authorization"]
    assert run(project, "forget", "network") == 2
    assert run(project, "authorize", "base-image", "default") == 0
    assert "exact recorded image" in capsys.readouterr().out
    assert run(project, "forget", "docker-daemon") == 0


def test_bind_and_unbind_need_an_ide_and_return_to_the_managed_default(project: Path, tmp_path: Path, capsys) -> None:
    home = tmp_path / "bound-home"
    home.mkdir()
    assert run(project, "ide", "frontend-ide") == 0
    assert run(project, "bind", "home", f"host-directory:{home}") == 0
    assert record(project)["configuration"]["bindings"]["host-directory"]["home"] == str(home)
    assert run(project, "unbind", "home") == 0
    assert "home" not in record(project)["configuration"].get("bindings", {}).get("host-directory", {})
    assert run(project, "unbind", "home") == 2


def test_every_config_leaf_is_listed_or_hidden_with_its_replacement() -> None:
    from devcapsule.commands.framework import render_command_listing
    from devcapsule.commands.project import ConfigGroup
    listing = render_command_listing(ConfigGroup.subcommands())
    for visible in ("show", "check", "ide", "add", "omit", "restore", "use", "set", "authorize", "deny", "forget", "bind",
                    "unbind", "env", "docker-args", "require", "offer", "drop", "recommend"):
        assert f"  {visible} " in listing, visible
    for hidden in ("set-env", "list-env", "unset-env", "set-extra-docker-args", "capabilities", "need", "unset", "agent", "tool", "list"):
        assert f"  {hidden} " not in listing, hidden


@pytest.mark.parametrize("verb", ["show", "check"])
def test_inspection_refuses_activation_without_recovery(project, capsys, verb):
    from devcapsule.configuration.file_formats import render_toml
    manifest = load_toml(paths(project)[0])
    input_path, resolution = checkout_record_paths(manifest, project)
    journal = input_path.with_suffix(".activation.toml")
    journal.write_text(render_toml({"before-checkout": input_path.read_text(),
                                  "after-checkout": "uncommitted", "before-resolution": "recovered", "after-resolution": "new"}))
    before = {p: p.read_bytes() for p in (input_path, journal)}
    assert run(project, verb) == 2
    assert "project run" in capsys.readouterr().err
    assert not resolution.exists()
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("value", ["4", "default"])
def test_cpu_edit_preserves_legacy_memory_and_other_answers(project, value):
    from devcapsule.configuration.file_formats import render_toml
    manifest_path = paths(project)[0]
    manifest_path.write_text(manifest_path.read_text() + '\n[configuration.values."runtime.memory-limit"]\ntype = "memory-size"\nruntime-effect = "docker.memory-limit"\n')
    manifest = load_toml(manifest_path)
    input_path, _ = checkout_record_paths(manifest, project)
    document = load_toml(input_path)
    document["configuration"] = {"values": {"runtime.memory-limit": "3GiB", "cpus": 2}}
    input_path.write_text(render_toml(document))
    assert run(project, "set", "cpus", value) == 0
    expected = {"runtime.memory-limit": "3GiB"}
    if value != "default":
        expected["cpus"] = 4
    assert record(project)["configuration"]["values"] == expected


@pytest.mark.parametrize("contents", ['defaults = "bad"', '[defaults]\ncpus = 0',
                                      'devcapsule-settings-schema-version = 99', '[defaults'])
def test_malformed_home_is_refused_without_writes(project, tmp_path, capsys, contents):
    from devcapsule.configuration.storage import settings_path, load_settings
    from devcapsule.configuration.file_formats import ProjectConfigurationError
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ProjectConfigurationError):
        load_settings()
    for verb in ("show", "check"):
        assert run(project, verb) == 2
        assert str(path) in capsys.readouterr().err
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_check_candidate_json_keeps_contract(project, capsys):
    capsys.readouterr()
    assert run(project, "check", "--manifest", str(paths(project)[0]), "--json") == 0
    assert json.loads(capsys.readouterr().out)["contract"].startswith("Configuration contract valid")


def test_corrupt_saved_arguments_are_not_reported_as_empty(project, capsys):
    assert run(project, "env", "set", "TOKEN", "private") == 0
    path = arguments_path(checkout_record_paths(load_toml(paths(project)[0]), project)[0])
    path.write_text('corrupt-private-sentinel')
    capsys.readouterr()
    for verb in ("show", "check"):
        assert run(project, verb) == 2
        output = capsys.readouterr()
        assert "Invalid saved Docker arguments" in output.err
        assert "corrupt-private-sentinel" not in output.out + output.err
    assert path.read_text() == 'corrupt-private-sentinel'


def test_pending_environment_remedy_is_executable(project, capsys, monkeypatch):
    import shlex
    manifest_path = paths(project)[0]
    manifest_path.write_text(manifest_path.read_text() + '\n[environment.required.TOKEN]\nreason = "login"\n')
    capsys.readouterr()
    assert run(project, "check", "--json") == 3
    output = json.loads(capsys.readouterr().out)
    assert output["contract"].startswith("Configuration contract valid")
    row = next(row for row in output["rows"] if row["name"] == "TOKEN")
    command = shlex.split(row["command"])[1:]
    assert command[-1] == "VALUE"
    command[-1] = "private-sentinel"
    assert cli.main(command) == 0
    monkeypatch.delenv("TOKEN", raising=False)
    assert run(project, "env", "set", "TOKEN", "--from-host") == 0
    capsys.readouterr()
    assert run(project, "check", "--json") == 3
    row = next(row for row in json.loads(capsys.readouterr().out)["rows"] if row["name"] == "TOKEN")
    assert row["effective"] == "unset" and "host" in row["pending"]
    monkeypatch.setenv("TOKEN", "host-private-sentinel")
    assert run(project, "show", "--json") == 0
    output = capsys.readouterr().out
    row = next(row for row in json.loads(output)["rows"] if row["name"] == "TOKEN")
    assert not row["pending"] and "host-private-sentinel" not in output


@pytest.mark.parametrize("name", ["base-image", "claude-code-download", "antigravity-download"])
def test_deny_required_consent_never_writes(project, name, capsys):
    from devcapsule.configuration.authorization import authorization_declarations
    from devcapsule.configuration.storage import lock_for
    assert run(project, "ide", "codium") == 0
    assert run(project, "add", "claude-code") == 0
    assert run(project, "add", "antigravity-cli") == 0
    manifest = load_toml(paths(project)[0])
    assert authorization_declarations(manifest, lock_for(project, manifest)[1])[name].required
    input_path = checkout_record_paths(load_toml(paths(project)[0]), project)[0]
    before = input_path.read_bytes()
    assert run(project, "deny", name) == 2
    assert "not a host access that can be denied" in capsys.readouterr().err
    assert input_path.read_bytes() == before


def test_legacy_need_allows_agent_and_optional_tool_edits(project):
    from devcapsule.configuration.file_formats import render_toml
    from devcapsule.configuration.capability_selection import generate_lock
    from devcapsule.configuration.capabilities import CapabilityPolicy
    from devcapsule.platforms import Platform
    from devcapsule.resolution_matrix import MATRICES
    manifest_path, lock_path, _ = paths(project)
    document = load_toml(manifest_path)
    document["devcapsule-schema-version"] = 1  # the legacy form belongs to schema 1
    document["capabilities"] = {"need": ["node", "frontend-ide"], "optional": ["browser-automation"]}
    manifest_path.write_text(render_toml(document))
    from devcapsule.configuration.manifest import current_manifest
    lock_path.write_text(render_toml(generate_lock(current_manifest(document, manifest_path).policy, MATRICES[Platform.current()])))
    before = manifest_path.read_bytes(), lock_path.read_bytes()
    assert run(project, "add", "codex") == 0
    assert record(project)["capabilities"]["selected"] == ["codex-agent"]
    assert run(project, "omit", "browser-automation") == 0
    assert record(project)["capabilities"]["without"] == ["browser-automation"]
    assert (manifest_path.read_bytes(), lock_path.read_bytes()) == before


@pytest.fixture
def runtime_project(project, tmp_path, monkeypatch):
    """A real RuntimeConfiguration with separate project and read-only record mounts."""
    import shutil
    from devcapsule import runtime_configuration
    assert run(project, "ide", "codium") == 0
    manifest = load_toml(paths(project)[0])
    input_path, _ = checkout_record_paths(manifest, project)
    inside = tmp_path / "inside"
    shutil.copytree(project, inside)
    context_path = tmp_path / "launch-context.json"
    context_path.write_text(json.dumps({
        "format": 1, "launcher-root": str(project), "runtime-root": str(inside),
        "checkout-file": input_path.name, "project": manifest["project"],
        "running": {"identity": "fixture", "origin": "project recommendation", "base": {},
                    "lock": load_toml(paths(project)[1])},
    }))
    monkeypatch.setattr(runtime_configuration, "CONTEXT_PATH", context_path)
    monkeypatch.setattr(runtime_configuration, "CONFIGURATION_PATH", input_path.parent)
    monkeypatch.setattr(runtime_configuration, "CHANNEL_PATH", tmp_path / "absent-channel")
    return inside


@pytest.mark.parametrize("verb", ["show", "check"])
def test_runtime_inspection_uses_recorded_context_and_never_host_assessment(runtime_project, tmp_path, monkeypatch, capsys, verb):
    from devcapsule.commands import project as commands
    def forbidden(*args, **kwargs):
        pytest.fail("Runtime inspection must not assess host inputs")
    monkeypatch.setattr(commands, "_assess", forbidden)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    capsys.readouterr()
    assert run(runtime_project, verb, "--json") == 0
    document = json.loads(capsys.readouterr().out)
    assert document["context"] == "running capsule (next launch, read-only)"
    assert document["checkout"]["runtime-path"] == str(runtime_project)
    assert document["checkout"]["record"]["capabilities"]["selected"] == ["frontend-ide"]
    if verb == "check":
        assert document["contract"].startswith("Configuration contract valid")
        assert "Host decisions cannot be assessed" in document["notes"][0]
    assert run(runtime_project, verb) == 0
    text = capsys.readouterr().out
    assert ("recorded choices" if verb != "check" else "Host decisions cannot be assessed") in text
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_clear_memory_alias_and_undeclared_answers_preserves_other_choices(project):
    from devcapsule.configuration.file_formats import render_toml
    manifest_path = paths(project)[0]
    manifest_path.write_text(manifest_path.read_text() + '\n[configuration.values."runtime.memory-limit"]\ntype = "memory-size"\nruntime-effect = "docker.memory-limit"\nrecommended = "2GiB"\n')
    input_path, _ = checkout_record_paths(load_toml(manifest_path), project)
    document = load_toml(input_path)
    document["configuration"] = {"values": {"cpus": 3, "stray": "old"}, "omitted-values": ["runtime.memory-limit"]}
    input_path.write_text(render_toml(document))
    assert run(project, "set", "memory", "default") == 0
    assert record(project)["configuration"]["values"] == {"cpus": 3, "stray": "old"}
    assert "runtime.memory-limit" not in record(project)["configuration"].get("omitted-values", [])
    assert run(project, "set", "stray", "default") == 0
    assert record(project)["configuration"]["values"] == {"cpus": 3}


def test_inspection_never_writes_in_registered_stale_or_unregistered_states(project, tmp_path, capsys):
    import shutil
    assert run(project, "ide", "codium") == 0
    assert run(project, "authorize", "base-image", "default") == 0
    assert run_until_prepared(project) == 0
    assert run(project, "set", "cpus", "2") == 0
    second = tmp_path / "second-checkout"
    shutil.copytree(project, second)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    for root, expected in ((project, 0), (second, 3)):
        capsys.readouterr()
        assert run(root, "show", "--json") == 0
        json.loads(capsys.readouterr().out)
        assert run(root, "check", "--json") == expected
        checked = json.loads(capsys.readouterr().out)
        assert bool(checked["pending"]) == (expected == 3)
        assert checked["contract"].startswith("Configuration contract valid")
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_home_default_in_a_capsule_writes_the_capsule_s_own_home_not_the_mount(runtime_project, tmp_path, capsys, monkeypatch):
    """A capsule's write creates the capsule's own settings; the launcher's mounted file is never touched."""
    from devcapsule.configuration.storage import load_settings, settings_path, settings_source
    mounted = tmp_path / "mounted"
    mounted.mkdir()
    (mounted / "settings.toml").write_text(
        'devcapsule-settings-schema-version = 1\nminimum-devcapsule = "0.3.0"\n\n[defaults]\ncpus = 8\n')
    monkeypatch.setattr("devcapsule.runtime_configuration.HOME_PATH", mounted)
    assert not settings_path().exists() and settings_source() == mounted / "settings.toml"
    assert load_settings()["defaults"] == {"cpus": 8}
    before = (mounted / "settings.toml").read_bytes()
    assert cli.main(["home", "default", "cpus", "2"]) == 0
    assert f"Home settings: {settings_path()}" in capsys.readouterr().out
    assert (mounted / "settings.toml").read_bytes() == before
    assert settings_source() == settings_path() and load_settings()["defaults"] == {"cpus": 2}