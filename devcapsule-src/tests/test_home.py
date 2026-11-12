"""The project-independent home command contract."""
import io
from pathlib import Path
import tomllib

import pytest

from devcapsule import cli, runtime_configuration
from devcapsule.configuration.storage import load_settings, settings_path, settings_source
from devcapsule.configuration.trust import channels_for, HomeTrust
from devcapsule.configuration.home_channels import known_channels
from devcapsule.platforms import Platform, XdgHomes
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    root = tmp_path / "chosen"
    monkeypatch.setenv("DEVCAPSULE_CONFIG_HOME", str(root))
    return root


def test_empty_show_and_list_do_not_create_home(home: Path, capsys) -> None:
    assert cli.main(["home", "show"]) == 0
    output = capsys.readouterr().out
    assert str(home) in output and "DEVCAPSULE_CONFIG_HOME" in output
    assert "minimum-devcapsule: (not recorded)" in output
    assert "Defaults: none" in output and "No accepted channels" in output
    assert cli.main(["home", "trust", "list"]) == 0
    assert not home.exists()


def test_setup_show_and_withdraw(home: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("importlib.metadata.version", lambda name: "0.3.0")
    for channel in ("devcapsule-base", "claude-code"):
        assert cli.main(["home", "trust", "accept", channel, "--yes"]) == 0
    for name, value in (("memory", "8GiB"), ("cpus", "4")):
        assert cli.main(["home", "default", name, value]) == 0
    capsys.readouterr()
    assert cli.main(["home", "show"]) == 0
    output = capsys.readouterr().out
    assert "minimum-devcapsule: 0.3.0" in output and "devcapsule-settings-schema-version: 1" in output
    assert "memory = 8GiB" in output and "cpus = 4" in output
    assert "claude-code: Anthropic — Claude Code; from https://downloads.claude.ai; accepted " in output
    assert cli.main(["home", "trust", "list"]) == 0
    assert "claude-code" in capsys.readouterr().out
    assert cli.main(["home", "trust", "withdraw", "claude-code"]) == 0
    before = settings_path().read_bytes(), settings_path().stat().st_mtime_ns
    assert cli.main(["home", "trust", "withdraw", "claude-code"]) == 0
    assert "No acceptance recorded" in capsys.readouterr().out
    assert (settings_path().read_bytes(), settings_path().stat().st_mtime_ns) == before
    assert load_settings()["defaults"] == {"cpus": 4, "memory": "8GiB"}


def test_accept_confirmation_and_unknown_channel(home: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("N\n"))
    assert cli.main(["home", "trust", "accept", "devcapsule-base"]) == 0
    output = capsys.readouterr().out
    assert "Accept for this DevCapsule home? [y/N]" in output
    assert str(home) in output and "Anyone who uses this home" in output
    assert not home.exists()
    assert cli.main(["home", "trust", "accept", "unknown", "--yes"]) == 2
    error = capsys.readouterr().err
    assert "Unknown channel" in error and "devcapsule-base" in error and "claude-code" in error
    assert not home.exists()
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
    assert cli.main(["home", "trust", "accept", "claude-code"]) == 0
    assert "https://www.anthropic.com/legal/commercial-terms" in capsys.readouterr().out
    assert "claude-code" in load_settings()["trust"]["channels"]


def test_matrix_channel_equals_rendered_lock_and_saved_acceptance(home: Path) -> None:
    matrix = MATRICES[Platform.current()]
    lock = tomllib.loads(matrix.resolve(["python-ide", "claude-code-agent"]).render_lock())
    channel = channels_for(lock)["claude-code"]
    assert known_channels()["claude-code"] == channel
    assert cli.main(["home", "trust", "accept", "claude-code", "--yes"]) == 0
    assert HomeTrust.read(load_settings()).covers(channel)


@pytest.mark.parametrize(("name", "kind", "directory"), [
    ("home", "durable", "data"), ("pycharm/log", "state", "state"), ("pycharm/cache", "cache", "cache"),
])
def test_managed_bindings_and_diagnostics_share_named_home(
    home: Path, name: str, kind: str, directory: str,
) -> None:
    from devcapsule.configuration.bindings import ConfigurationBindingDeclaration, managed_binding_path
    from devcapsule.diagnostics import _managed_slot_path
    from devcapsule.recursive_successor import _managed_binding_path
    from devcapsule.project import project_namespace

    project = home.parent / "project"
    slot = name.split("/")[-1]
    declaration = ConfigurationBindingDeclaration(name, "/target", "ordinary", False, "test", kind, "pycharm", slot)
    suffix = Path("home") if name == "home" else Path("components/pycharm") / slot
    expected = home / directory / "projects/by-path" / project_namespace(project) / suffix
    assert managed_binding_path(project, declaration) == expected
    assert _managed_binding_path(project, declaration) == expected
    assert _managed_slot_path(project, declaration, {"DEVCAPSULE_CONFIG_HOME": str(home)}) == expected
    assert not home.exists()


def test_default_replace_remove_and_invalid_values(home: Path) -> None:
    assert cli.main(["home", "default", "cpus", "2"]) == 0
    assert cli.main(["home", "default", "cpus", "4"]) == 0
    assert load_settings()["defaults"]["cpus"] == 4
    before = settings_path().read_bytes()
    for name, value in (("cpus", "0"), ("memory", "bad"), ("other", "2")):
        assert cli.main(["home", "default", name, value]) == 2
        assert settings_path().read_bytes() == before
    assert cli.main(["home", "default", "cpus", "none"]) == 0
    assert load_settings()["defaults"] == {}


def test_capsule_reads_the_mounted_settings_until_it_writes_its_own(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """A capsule reads the launcher's settings from the mount; its own home, data, state and cache stay its own."""
    assert cli.main(["home", "default", "cpus", "4"]) == 0
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    capsys.readouterr()
    mounted = tmp_path / "mounted"
    mounted.mkdir()
    (mounted / "settings.toml").write_bytes(settings_path().read_bytes())
    monkeypatch.delenv("DEVCAPSULE_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "capsule-home"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    context = tmp_path / "context.json"
    context.write_text('{"format": 1}')
    monkeypatch.setattr(runtime_configuration, "CONTEXT_PATH", context)
    monkeypatch.setattr(runtime_configuration, "HOME_PATH", mounted)
    before = (mounted / "settings.toml").read_bytes()
    own = tmp_path / "capsule-home" / ".config" / "devcapsule" / "settings.toml"
    assert settings_path() == own and settings_source() == mounted / "settings.toml"
    state = XdgHomes.from_environment().state
    assert state.is_relative_to(tmp_path) and not state.is_relative_to(mounted)
    assert cli.main(["home", "show"]) == 0
    output = capsys.readouterr().out
    assert f"DevCapsule home: {own.parent}" in output and f"mounted read-only: {mounted / 'settings.toml'}" in output
    assert "cpus = 4" in output and "devcapsule-base" in output
    assert cli.main(["home", "trust", "list"]) == 0
    assert "devcapsule-base" in capsys.readouterr().out
    # A write inside the capsule starts from the launcher's settings, creates the
    # capsule's own home and never touches the mount; reads take the own from then on.
    assert cli.main(["home", "default", "cpus", "2"]) == 0
    assert own.is_file() and (mounted / "settings.toml").read_bytes() == before
    assert settings_source() == own
    capsys.readouterr()
    assert cli.main(["home", "show"]) == 0
    output = capsys.readouterr().out
    assert "cpus = 2" in output and "mounted read-only" not in output and "devcapsule-base" in output
    assert cli.main(["home", "trust", "withdraw", "devcapsule-base"]) == 0
    assert "devcapsule-base" not in load_settings().get("trust", {}).get("channels", {})
    assert (mounted / "settings.toml").read_bytes() == before
    # A home the capsule names is its own, mount or no mount.
    monkeypatch.setenv("DEVCAPSULE_CONFIG_HOME", str(tmp_path / "nested"))
    assert settings_source() == tmp_path / "nested" / "settings.toml"
    assert cli.main(["home", "trust", "list"]) == 0
    assert "No accepted channels" in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [["default", "cpus", "2"], ["trust", "accept", "devcapsule-base"],
                                       ["trust", "withdraw", "devcapsule-base"]])
def test_deleted_project_spellings(home: Path, capsys, arguments: list[str]) -> None:
    assert cli.main(["project", "config", *arguments]) == 2
    assert "unknown command" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("arguments", [["show"], ["trust", "list"], ["default", "cpus", "2"],
                                       ["trust", "accept", "devcapsule-base", "--yes"], ["trust", "withdraw", "devcapsule-base"]])
def test_malformed_settings_refuse_every_home_command(home: Path, arguments: list[str], capsys) -> None:
    home.mkdir()
    path = home / "settings.toml"
    path.write_text('minimum-devcapsule = "9.0.0"\ndefaults = false\n')
    before = path.read_bytes()
    assert cli.main(["home", *arguments]) == 2
    assert "requires DevCapsule 9.0.0" in capsys.readouterr().err
    assert path.read_bytes() == before


@pytest.mark.parametrize("content", ['broken = [', 'minimum-devcapsule = "0.3.0"\ndevcapsule-settings-schema-version = 1\ndefaults = false',
                                     'minimum-devcapsule = "0.3.0"\ndevcapsule-settings-schema-version = 1\ntrust = false'])
def test_malformed_settings_stop_run_before_project_discovery(home: Path, content: str, capsys) -> None:
    home.mkdir()
    path = home / "settings.toml"
    path.write_text(content)
    assert cli.main(["project", "run", "--print-command"]) == 2
    assert str(path) in capsys.readouterr().err
    assert list(home.iterdir()) == [path] and path.read_text() == content
