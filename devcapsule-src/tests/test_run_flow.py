"""``project run`` derives, reports and asks: the flow before the launch, without Docker."""

from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import io
import json
from pathlib import Path
import tomllib

import pytest

from devcapsule import cli
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.compat import DecisionPending
from devcapsule.configuration.capability_commands import paths
from devcapsule.configuration.docker_arguments import arguments_path, read_arguments
from devcapsule.configuration.storage import checkout_record_paths, load_toml, registered_checkouts, settings_path

pytestmark = pytest.mark.legacy


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--require", "node", "--creator", "mailto:owner@example.test"]) == 0
    return root


def config(root: Path, *arguments: str) -> int:
    return cli.main(["project", "--path", str(root), "config", *arguments])


def record(root: Path) -> dict:
    return load_toml(checkout_record_paths(load_toml(paths(root)[0]), root)[0])


def test_without_a_terminal_a_pending_ide_ends_with_status_three_and_writes_nothing(project: Path, tmp_path: Path) -> None:
    with pytest.raises(DecisionPending) as failure:
        prepare_launch(project, RunFlags(), interactive=False)
    message = str(failure.value)
    assert "ide ide: Your IDE for this checkout" in message and "--ide IDE" in message
    assert "Nothing was written" in message
    assert not any(path.name.endswith(".resolved.toml") for path in (tmp_path / "xdg_config_home").rglob("*.toml"))


def test_print_only_never_asks(project: Path) -> None:
    assert config(project, "authorize", "base-image", "default") == 0
    with pytest.raises(DecisionPending):
        prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO("1\n"), print_only=True)


def test_run_once_ide_and_memory_leave_the_record_alone(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("B", "from-host")
    assert config(project, "authorize", "base-image", "default") == 0
    prepared = prepare_launch(project, RunFlags(ide="codium", memory="6g", cpus="2", environment=("A=1", "B")),
                              interactive=False)
    assert prepared.selected.resolution["runtime"]["component"] == "codium"
    assert prepared.memory_override == 6 * 1024**3 and prepared.cpus_override == 2
    assert prepared.environment_tokens == ["--env", "A=1", "--env", "B"]
    assert "capabilities" not in record(project)
    assert "memory" not in record(project).get("configuration", {}).get("values", {})
    assert prepared.selected.resolution_path.is_file()


def test_save_records_the_flags_as_the_checkouts_answers(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("B", "from-host")
    assert config(project, "authorize", "base-image", "default") == 0
    prepared = prepare_launch(project, RunFlags(ide="frontend-ide", capabilities=("codex",), memory="6g",
                                                environment=("A=1", "B"), authorize=(("network", "host"),), save=True),
                              interactive=False)
    saved = record(project)
    assert saved["capabilities"]["selected"] == ["codex-agent", "frontend-ide"]
    assert saved["configuration"]["values"]["memory"] == "6GiB"
    assert saved["authorization"]["network"]["value"] == "host"
    assert read_arguments(arguments_path(checkout_record_paths(load_toml(paths(project)[0]), project)[0])) == [
        "--env", "B", "--env", "A=1"]
    assert prepared.memory_override is None and prepared.environment_tokens == []
    assert "Recorded the flags given" in prepared.notes[0]


def test_a_second_checkout_is_registered_under_its_directory_name(project: Path, tmp_path: Path) -> None:
    assert config(project, "ide", "python-ide") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    second = tmp_path / "second-copy"
    second.mkdir()
    (second / ".devcapsule").mkdir()
    for name in ("devcapsule.toml", "devcapsule.linux-amd64.lock"):
        (second / ".devcapsule" / name).write_bytes((project / ".devcapsule" / name).read_bytes())
    with pytest.raises(DecisionPending):  # its own record: no IDE; the base's channel is the home's question
        prepare_launch(second, RunFlags(), interactive=False)
    prompts = io.StringIO()
    prepared = prepare_launch(second, RunFlags(ide="python-ide", authorize=()), interactive=True,
                              input_stream=io.StringIO("y\n"), output_stream=prompts)
    assert "Accept for this DevCapsule home?" in prompts.getvalue()
    assert load_toml(settings_path())["trust"]["channels"]["devcapsule-base"]["vendor"]
    names = {item.checkout_name: item.checkout_path for item in registered_checkouts()}
    assert names == {"default": project.resolve(), "second-copy": second.resolve()}
    assert prepared.selected.checkout_path.name == "second-copy.checkout.toml"


def test_interactive_questions_record_answers_where_the_config_family_would(project: Path, capsys) -> None:
    assert config(project, "require", "env", "POSTGRES_HOST", "--because", "the owner's database") == 0
    assert config(project, "recommend", "network", "host", "--because", "ports") == 0
    assert config(project, "recommend", "docker-daemon", "host-socket", "--because", "compose") == 0
    capsys.readouterr()
    prompts = io.StringIO()
    # In listing order: IDE by number; network: once; docker-daemon: deny; the base's channel: yes; env value.
    answers = io.StringIO("3\no\nd\ny\ndb.example.org\n")
    prepared = prepare_launch(project, RunFlags(), interactive=True, input_stream=answers, output_stream=prompts)
    transcript = prompts.getvalue()
    assert "Choose one:" in transcript and "3. frontend-ide" in transcript
    assert "removes network namespace isolation" in transcript
    assert "POSTGRES_HOST: the owner's database" in transcript
    assert "db.example.org" not in transcript
    saved = record(project)
    assert saved["capabilities"]["selected"] == ["frontend-ide"]
    assert saved["authorization"]["docker-daemon"]["value"] == "none"
    assert "network" not in saved["authorization"]
    assert prepared.host_overrides == {"network": "host"}
    assert "base-image" not in saved.get("authorization", {})  # the channel is trusted for the home, not consented per checkout
    assert "devcapsule-base" in load_toml(settings_path())["trust"]["channels"]
    assert read_arguments(arguments_path(checkout_record_paths(load_toml(paths(project)[0]), project)[0])) == [
        "--env", "POSTGRES_HOST=db.example.org"]
    assert prepared.selected.resolution["runtime"]["component"] == "codium"


def test_not_now_keeps_the_secure_default_and_asks_again_next_time(project: Path) -> None:
    assert config(project, "ide", "python-ide") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    assert config(project, "recommend", "network", "host", "--because", "ports") == 0
    prompts = io.StringIO()
    prepared = prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO("\n"), output_stream=prompts)
    assert "Not now; the secure default applies" in prompts.getvalue()
    assert prepared.host_overrides == {} and "network" not in record(project).get("authorization", {})
    # Without a terminal the ask is a note, never a stop.
    prepared = prepare_launch(project, RunFlags(), interactive=False)
    assert any("network host" in note and "not granted this run" in note for note in prepared.notes)


def test_a_closed_terminal_mid_question_stops_without_more_writes(project: Path) -> None:
    assert config(project, "authorize", "base-image", "default") == 0
    with pytest.raises(DecisionPending, match="terminal closed"):
        prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO(""), output_stream=io.StringIO())


def test_run_exits_three_until_preparation_has_its_answers(project: Path, capsys) -> None:
    assert cli.main(["project", "--path", str(project), "run", "--print-command"]) == 3
    err = capsys.readouterr().err
    assert "needs answers" in err and "--ide IDE" in err
    assert config(project, "ide", "python-ide") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    capsys.readouterr()
    assert run_until_prepared(project) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert checkout_record_paths(load_toml(paths(project)[0]), project)[1].is_file()
    from devcapsule.commands.framework import render_command_listing
    from devcapsule.commands.project import ConfigGroup
    assert "  resolve " not in render_command_listing(ConfigGroup.subcommands())


def test_run_help_has_the_flags_and_force_names_the_ide_departure(capsys) -> None:
    assert cli.main(["project", "run", "--help"]) == 0
    text = capsys.readouterr().out
    for flag in ("--ide", "--with", "--memory", "--cpus", "--env", "--save", "--print-command", "--force"):
        assert flag in text
    import re
    assert re.search(r"although\s+the\s+project\s+requires\s+another\s+IDE", text)
    assert "--force-config" not in text
    assert cli.main(["project", "run", "--force-config"]) == 2
    assert "--force-config is retired" in capsys.readouterr().err


def snapshot(directory: Path) -> dict[Path, bytes]:
    return {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()}


def copy_project(project: Path, target: Path) -> Path:
    import shutil
    shutil.copytree(project / '.devcapsule', target / '.devcapsule')
    return target


@pytest.mark.parametrize('second', [False, True])
@pytest.mark.parametrize('print_only', [False, True])
def test_save_with_pending_consent_writes_nothing(project: Path, tmp_path: Path, second: bool, print_only: bool) -> None:
    root = copy_project(project, tmp_path / 'second') if second else project
    before = snapshot(tmp_path)
    with pytest.raises(DecisionPending, match='trust devcapsule-base'):
        prepare_launch(root, RunFlags(ide='python-ide', memory='6g', environment=('PRIVATE=value',),
                                     authorize=(('network', 'host'),), save=True),
                       interactive=False, print_only=print_only)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('answers', ['1\n', '1\nn\n'])
def test_partial_terminal_review_saves_no_answers(project: Path, tmp_path: Path, answers: str) -> None:
    second = copy_project(project, tmp_path / 'second')
    before = snapshot(tmp_path)
    with pytest.raises(DecisionPending):
        prepare_launch(second, RunFlags(memory='6g', save=True), interactive=True,
                       input_stream=io.StringIO(answers), output_stream=io.StringIO())
    assert snapshot(tmp_path) == before


def test_resolve_pending_consent_writes_nothing_in_a_second_checkout(project: Path, tmp_path: Path) -> None:
    second = copy_project(project, tmp_path / 'second')
    before = snapshot(tmp_path)
    assert run_until_prepared(second) == 3
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('name', ['same', 'default', '.hidden'])
def test_registration_collision_is_distinct_and_stable(project: Path, tmp_path: Path, name: str) -> None:
    first = copy_project(project, tmp_path / 'one' / name)
    second = copy_project(project, tmp_path / 'two' / name)
    flags = RunFlags(ide='python-ide', authorize=(('base-image', 'default'),), save=True)
    one = prepare_launch(first, flags, interactive=False)
    before = one.selected.checkout_path.read_bytes()
    two = prepare_launch(second, flags, interactive=False)
    again = prepare_launch(second, RunFlags(), interactive=False)
    assert two.selected.checkout_path == again.selected.checkout_path
    assert one.selected.checkout_path != two.selected.checkout_path
    assert one.selected.checkout_path.read_bytes() == before
    assert two.selected.checkout_path.name == {'same': 'same-2.checkout.toml', 'default': 'default-3.checkout.toml', '.hidden': 'hidden-2.checkout.toml'}[name]
    assert len({item.checkout_name for item in registered_checkouts()}) == 3
    assert any('Registered this checkout:' in note for note in two.notes)


@pytest.mark.parametrize('saved_set', [False, True])
def test_run_once_agent_reaches_plan_but_not_next_show(project: Path, capsys, saved_set: bool) -> None:
    from devcapsule.configuration.derivation import load_state
    from devcapsule.configuration.file_formats import canonical_digest, render_toml
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    path = checkout_record_paths(load_toml(paths(project)[0]), project)[0]
    if saved_set:
        state = load_state(project, load_toml(paths(project)[0]))
        document = record(project)
        document['version-set'] = {'format': 1, 'lock': render_toml(state.composed_lock()),
                                   'recommendation-digest': canonical_digest(state.shared_lock)}
        path.write_text(render_toml(document))
    before = path.read_bytes()
    prepared = prepare_launch(project, RunFlags(capabilities=('codex',)), interactive=False)
    assert 'codex' in prepared.selected.lock['components']
    assert load_toml(prepared.selected.resolution_path) == prepared.selected.resolution
    assert path.read_bytes() == before
    capsys.readouterr()
    assert config(project, 'show', '--json') == 0
    assert not [row for row in json.loads(capsys.readouterr().out)['rows'] if row['kind'] == 'agent']


@pytest.mark.parametrize("value", ["host", "bridge"])
def test_a_changed_recommendation_keeps_the_answer_and_never_asks(project: Path, tmp_path: Path, capsys, monkeypatch, value: str) -> None:
    """Answer 23 of the work order (slice 4): a recorded host answer is kept; the listing discloses what changed."""
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    assert config(project, 'recommend', 'network', 'host', '--because', 'old reason') == 0
    assert config(project, 'authorize', 'network', value) == 0
    assert config(project, 'authorize', 'docker-daemon', 'none') == 0
    old = record(project)['authorization']
    assert config(project, 'recommend', 'network', 'host', '--because', 'new reason') == 0
    before = snapshot(tmp_path)
    prompts = io.StringIO()
    prepared = prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO(''), output_stream=prompts)
    assert prompts.getvalue() == '' and prepared.selected.resolution['authorization']['network'] == value
    assert any('new reason' in note and f'network: {value}' in note for note in prepared.notes)
    assert record(project)['authorization'] == old
    assert {path: data for path, data in snapshot(tmp_path).items() if 'resolved' not in str(path)} == \
        {path: data for path, data in before.items() if 'resolved' not in str(path)}
    capsys.readouterr()
    assert config(project, 'show') == 0
    shown = capsys.readouterr().out
    assert 'kept;' in shown and 'new reason' in shown
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    assert invoke(project, 'run', '--no-update-check') == 0
    assert launch.call_args.args[0].network_mode == value
    assert 'new reason' in capsys.readouterr().out


def test_run_once_override_answers_a_renewal_without_saving_it(project: Path) -> None:
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    assert config(project, 'recommend', 'network', 'host', '--because', 'old') == 0
    assert config(project, 'authorize', 'network', 'host') == 0
    assert config(project, 'recommend', 'network', 'host', '--because', 'new') == 0
    before = record(project)
    prepared = prepare_launch(project, RunFlags(authorize=(('network', 'bridge'),)), interactive=False)
    assert prepared.host_overrides == {'network': 'bridge'}
    assert record(project) == before


def test_print_only_complete_plan_writes_nothing(project: Path, tmp_path: Path) -> None:
    assert config(project, 'authorize', 'base-image', 'default') == 0
    before = snapshot(tmp_path)
    prepared = prepare_launch(project, RunFlags(ide='python-ide', memory='6g', save=True), print_only=True)
    assert prepared.selected.resolution['runtime']['component'] == 'pycharm'
    assert snapshot(tmp_path) == before


def test_missing_pass_through_variable_blocks_and_does_not_save(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    monkeypatch.delenv('MISSING_SOURCE', raising=False)
    before = snapshot(tmp_path)
    with pytest.raises(DecisionPending, match='MISSING_SOURCE'):
        prepare_launch(project, RunFlags(environment=('MISSING_SOURCE',), save=True), interactive=False)
    assert snapshot(tmp_path) == before


def test_recommended_ide_is_derived_without_a_personal_answer(project: Path) -> None:
    assert config(project, 'recommend', 'ide', 'python-ide', '--because', 'Python project') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    prepared = prepare_launch(project, RunFlags(), interactive=False)
    assert prepared.selected.resolution['runtime']['component'] == 'pycharm'
    assert 'capabilities' not in record(project)


def test_first_cli_run_registers_a_second_checkout_and_launches(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    second = copy_project(project, tmp_path / 'second')
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr('sys.stdin', io.StringIO('y\n'))
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    assert invoke(second, 'run', '--ide', 'python-ide', '--no-update-check') == 0
    assert launch.call_count == 1
    assert len(registered_checkouts()) == 2
    assert 'base-image' not in record(project).get('authorization', {})


def test_first_cli_run_reaches_the_ide_prompt(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr('sys.stdin', io.StringIO('python-ide\ny\n'))
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    assert invoke(project, 'run', '--no-update-check') == 0
    assert launch.call_count == 1
    assert record(project)['capabilities']['selected'] == ['python-ide']


def test_save_with_required_consent_survives_the_second_derivation(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    assert invoke(project, 'run', '--ide', 'python-ide', '--authorize', 'base-image', 'default', '--save', '--no-update-check') == 0
    assert launch.call_count == 1
    assert record(project)['authorization']['base-image']['reference']


@pytest.mark.parametrize('save', [False, True])
def test_cli_second_derivation_carries_only_unsaved_flags(project: Path, monkeypatch: pytest.MonkeyPatch, save: bool) -> None:
    from unittest.mock import Mock
    from devcapsule.commands import project as commands
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    assert config(project, 'authorize', 'base-image', 'default') == 0
    monkeypatch.setenv('PASS_THROUGH', 'from-host')
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    launch = install_external_fakes(monkeypatch, [])
    calls = Mock(wraps=commands.prepare_launch)
    monkeypatch.setattr(commands, 'prepare_launch', calls)
    before = record(project)
    assert invoke(project, 'run', '--ide', 'python-ide', '--with', 'codex', '--memory', '6g', '--cpus', '2',
                  '--env', 'INLINE=value', '--env', 'PASS_THROUGH', '--authorize', 'network', 'host',
                  '--no-update-check', *(['--save'] if save else [])) == 0
    assert calls.call_count == 2
    first_flags, second_flags = (call.args[1] for call in calls.call_args_list)
    assert second_flags == (RunFlags() if save else first_flags)
    assert launch.call_count == 1
    options = launch.call_args.args[0]
    assert options.runtime_plan.component.id == 'pycharm'
    assert 'codex' in {item.id for item in options.runtime_plan.ancillary_components}
    assert options.memory_limit_bytes == 6 * 1024**3 and options.cpus == 2
    assert options.network_mode == 'host'
    tokens = options.extra_docker_args
    assert tokens.count('--env') == 2
    assert tokens[tokens.index('INLINE=value') - 1] == '--env'
    assert tokens[tokens.index('PASS_THROUGH') - 1] == '--env'
    path = checkout_record_paths(load_toml(paths(project)[0]), project)[0]
    if save:
        assert record(project)['capabilities']['selected'] == ['codex-agent', 'python-ide']
        assert record(project)['authorization']['network']['value'] == 'host'
        assert read_arguments(arguments_path(path)) == ['--env', 'PASS_THROUGH', '--env', 'INLINE=value']
    else:
        assert record(project) == before
        assert read_arguments(arguments_path(path)) == []


@pytest.mark.parametrize('new_decision', [False, True])
def test_second_derivation_keeps_once_answers_and_never_prompts(project: Path, monkeypatch: pytest.MonkeyPatch, new_decision: bool) -> None:
    from unittest.mock import Mock
    from devcapsule.commands import project as commands
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    assert config(project, 'recommend', 'network', 'host', '--because', 'ports') == 0
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr('sys.stdin', io.StringIO('o\n'))
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    calls = Mock(wraps=commands.prepare_launch)
    monkeypatch.setattr(commands, 'prepare_launch', calls)
    approvals = Mock(return_value=True)
    monkeypatch.setattr(commands, 'offer_software_approvals', approvals)
    def upgrade(root: Path, *, refresh: bool) -> bool:
        assert approvals.call_count == 1 and calls.call_count == 1
        if new_decision:
            assert config(root, 'require', 'env', 'NEW_INPUT', '--because', 'new requirement') == 0
        else:
            assert config(root, 'set', 'cpus', '3') == 0
            assert config(root, 'set', 'memory', '8g') == 0
        return True
    monkeypatch.setattr(commands, 'offer_upgrades', upgrade)
    assert invoke(project, 'run', '--memory', '6g', '--save') == (3 if new_decision else 0)
    assert calls.call_count == 2 and approvals.call_count == 1
    first_flags, second_flags = (call.args[1] for call in calls.call_args_list)
    assert first_flags.save and not second_flags.save
    assert first_flags.memory == '6g' and second_flags.memory is None
    assert second_flags.authorize == (('network', 'host'),)
    assert calls.call_args_list[1].kwargs['interactive'] is False
    assert 'network' not in record(project)['authorization']
    if new_decision:
        launch.assert_not_called()
    else:
        assert launch.call_args.args[0].network_mode == 'host'
        assert launch.call_args.args[0].cpus == 3
        assert launch.call_args.args[0].memory_limit_bytes == 8 * 1024**3


@pytest.mark.parametrize('print_only', [False, True])
def test_old_base_needs_consent_before_any_materialization_or_write(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, print_only: bool) -> None:
    from tests.test_upgrade_recovery import OLD_BASE, install_external_fakes, invoke
    path = project / '.devcapsule/devcapsule.linux-amd64.lock'
    lock = load_toml(path)
    path.write_text(path.read_text().replace(lock['base']['reference'], OLD_BASE))
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    events: list[str] = []
    launch = install_external_fakes(monkeypatch, events, contained=False)
    before = snapshot(tmp_path)
    assert invoke(project, 'run', '--memory', '6g', '--save', *(['--print-command'] if print_only else [])) == 3
    assert events == [] and launch.call_count == 0
    assert snapshot(tmp_path) == before
    assert invoke(project, 'run', '--authorize', 'host-x11', 'true', '--no-update-check') == 0
    assert launch.call_args.args[0].display_transport == 'host-x11'
    assert 'host-x11' not in record(project)['authorization']


def test_schema_one_ide_in_need_launches_without_rewriting_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_upgrade_recovery import FIXTURE, install_external_fakes, invoke
    for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    root = copy_project(FIXTURE / 'project', tmp_path / 'legacy')
    assert config(root, 'authorize', 'base-image', 'default') == 0
    manifest_path = root / '.devcapsule/devcapsule.toml'
    before = manifest_path.read_bytes()
    assert load_toml(manifest_path)['devcapsule-schema-version'] == 1
    launch = install_external_fakes(monkeypatch, [])
    assert invoke(root, 'run', '--with', 'codex', '--no-update-check') == 0
    options = launch.call_args.args[0]
    assert options.runtime_plan.component.id == 'pycharm'
    assert 'codex' in {item.id for item in options.runtime_plan.ancillary_components}
    assert manifest_path.read_bytes() == before
    assert 'capabilities' not in record(root)


def test_migrated_project_launches_its_recommended_ide_for_an_old_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_upgrade_recovery import FIXTURE, install_external_fakes, invoke
    for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    owner = copy_project(FIXTURE / 'project', tmp_path / 'owner')
    developer = copy_project(FIXTURE / 'project', tmp_path / 'developer')
    assert config(developer, 'authorize', 'base-image', 'default') == 0
    developer_record = checkout_record_paths(load_toml(paths(developer)[0]), developer)[0]
    assert 'capabilities' not in record(developer)
    with monkeypatch.context() as owner_environment:
        for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
            owner_environment.setenv(key, str(tmp_path / 'owner-home' / key.lower()))
        assert invoke(owner, 'init', '--regenerate', '--authorize', 'base-image', 'default') == 0
    for source, target in zip(paths(owner)[:2], paths(developer)[:2]):
        target.write_bytes(source.read_bytes())
    shared = {path: path.read_bytes() for path in paths(developer)[:2]}
    assert load_toml(paths(developer)[0])['recommendations']['ide'] == 'python-ide'
    assert 'interactive-surface' not in load_toml(paths(developer)[1])['components']
    assert config(developer, 'authorize', 'base-image', 'default') == 0
    before = developer_record.read_bytes()
    assert 'capabilities' not in record(developer)
    launch = install_external_fakes(monkeypatch, [])
    assert invoke(developer, 'run', '--no-update-check') == 0
    assert launch.call_count == 1
    assert launch.call_args.args[0].runtime_plan.component.id == 'pycharm'
    assert developer_record.read_bytes() == before
    assert {path: path.read_bytes() for path in shared} == shared


def test_new_required_tool_blocks_a_saved_set_without_replacing_it(project: Path, tmp_path: Path) -> None:
    from devcapsule.configuration.derivation import load_state
    from devcapsule.configuration.file_formats import canonical_digest, render_toml
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    state = load_state(project, load_toml(paths(project)[0]))
    document = record(project)
    document['version-set'] = {'format': 1, 'lock': render_toml(state.composed_lock()),
                               'recommendation-digest': canonical_digest(state.shared_lock)}
    assert state.input_path is not None
    state.input_path.write_text(render_toml(document))
    assert config(project, 'require', 'browser-automation', '--because', 'browser tests') == 0
    before = snapshot(tmp_path)
    with pytest.raises(DecisionPending, match='Saved version set') as failure:
        prepare_launch(project, RunFlags(memory='6g', save=True), interactive=False)
    assert "Required capability 'browser-automation'" in str(failure.value)
    assert 'follow-project --apply' in str(failure.value) and 'select SET' in str(failure.value)
    assert snapshot(tmp_path) == before


def test_interactive_ide_does_not_save_a_run_once_agent(project: Path) -> None:
    prepared = prepare_launch(project, RunFlags(capabilities=('codex',)), interactive=True,
                              input_stream=io.StringIO('python-ide\ny\n'), output_stream=io.StringIO())
    assert 'codex' in prepared.selected.lock['components']
    assert record(project)['capabilities']['selected'] == ['python-ide']


@pytest.mark.parametrize("consent", [("--authorize", "base-image", "default"), ("--trust", "devcapsule-base")])
def test_print_command_preserves_configuration_and_skips_reminder_writes(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consent: tuple[str, ...]) -> None:
    from unittest.mock import Mock
    from devcapsule.commands import project as commands
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    launch = install_external_fakes(monkeypatch, [])
    calls = Mock(wraps=commands.prepare_launch)
    monkeypatch.setattr(commands, 'prepare_launch', calls)
    monkeypatch.setattr('devcapsule.version_sets.reminder', lambda _: pytest.fail('print-only updated reminder state'))
    before = snapshot(tmp_path)
    assert invoke(project, 'run', '--ide', 'python-ide', *consent,
                  '--memory', '6g', '--save', '--print-command') == 0
    assert calls.call_count == 1
    assert launch.call_args.args[0].command_report is not None
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('carrier', [('network', 'host', 'because'), ('invented-memory-limit', '6g')])
def test_invalid_carriers_refuse_before_questions_or_writes(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, carrier: tuple[str, ...]) -> None:
    from tests.test_upgrade_recovery import invoke
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    before = snapshot(tmp_path)
    flag = '--authorize' if carrier[0] == 'network' else '--set'
    assert invoke(project, 'run', flag, *carrier) == 2
    assert snapshot(tmp_path) == before


def test_save_memory_replaces_legacy_answer_and_omission_like_config(project: Path) -> None:
    from devcapsule.configuration.file_formats import render_toml
    manifest_path = paths(project)[0]
    manifest_path.write_text(manifest_path.read_text() + '\n[configuration.values."old.limit"]\ntype = "memory-size"\nruntime-effect = "docker.memory-limit"\n')
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    path = checkout_record_paths(load_toml(manifest_path), project)[0]
    document = record(project)
    document['configuration'] = {'values': {}, 'omitted-values': ['old.limit']}
    path.write_text(render_toml(document))
    original = path.read_bytes()
    assert config(project, 'set', 'memory', '6g') == 0
    expected = record(project)
    path.write_bytes(original)
    prepared = prepare_launch(project, RunFlags(memory='6g', save=True), interactive=False)
    assert record(project) == expected
    assert prepared.selected.resolution['runtime']['memory-limit-bytes'] == 6 * 1024**3


def test_declared_memory_carrier_maps_by_runtime_effect(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    manifest_path = paths(project)[0]
    manifest_path.write_text(manifest_path.read_text() + '\n[configuration.values."old.limit"]\ntype = "memory-size"\nruntime-effect = "docker.memory-limit"\n')
    assert config(project, 'ide', 'python-ide') == 0
    assert config(project, 'authorize', 'base-image', 'default') == 0
    launch = install_external_fakes(monkeypatch, [])
    assert invoke(project, 'run', '--set', 'old.limit', '6g', '--no-update-check') == 0
    assert launch.call_args.args[0].memory_limit_bytes == 6 * 1024**3
    assert 'configuration' not in record(project)


def test_corrupt_saved_arguments_refuse_before_terminal_answers(project: Path, tmp_path: Path) -> None:
    path = checkout_record_paths(load_toml(paths(project)[0]), project)[0]
    private = arguments_path(path)
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text('not json')
    before = snapshot(tmp_path)
    prompts = io.StringIO()
    from devcapsule.configuration.file_formats import ProjectConfigurationError
    with pytest.raises(ProjectConfigurationError, match='Invalid saved Docker arguments'):
        prepare_launch(project, RunFlags(memory='6g', save=True), interactive=True,
                       input_stream=io.StringIO('python-ide\ny\n'), output_stream=prompts)
    assert prompts.getvalue() == ''
    assert snapshot(tmp_path) == before
