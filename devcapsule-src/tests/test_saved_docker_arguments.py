from __future__ import annotations

from tests.launch_preparation import run_until_prepared
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from devcapsule import cli
from devcapsule.configuration.docker_arguments import arguments_path, read_arguments, read_environment, replace_arguments
from devcapsule.configuration.execution import ExecutionConfiguration
from devcapsule.configuration.storage import registered_checkouts
from devcapsule.docker_arguments import redact_environment
from devcapsule.materialization import parse_locked_environment
from tests.test_checkout_environment import project, config
from tests.test_project_commands import initialize_codium_project, LOCKED_BASE

pytestmark = pytest.mark.legacy


def test_saved_args_replace_list_clear_and_share_hidden_env(project, tmp_path, capsys, monkeypatch):
    path = arguments_path(registered_checkouts()[0].record_path)
    args = ['--gpus', 'all', '--volume', f'{tmp_path}/space dir:/data:ro',
            '--label', 'literal=$(touch NO_SHELL)', '--env', 'TOKEN=sensitive=with spaces']
    assert config(project, 'docker-args', 'set', '--', *args) == 0
    assert read_arguments(path) == args
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    capsys.readouterr()
    assert config(project, 'docker-args', 'list', '--json') == 0
    report = capsys.readouterr().out
    assert 'sensitive' not in report
    assert json.loads(report) == {'path': str(path), 'arguments': redact_environment(args)}
    assert config(project, 'docker-args', 'list') == 0
    text = capsys.readouterr().out
    assert 'sensitive' not in text and 'TOKEN=<redacted>' in text and f'{tmp_path}/space dir:/data:ro' in text
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    with patch('getpass.getpass', return_value='hidden replacement'):
        assert config(project, 'env', 'set', 'TOKEN') == 0
    assert read_arguments(path) == [*args[:-2], '--env', 'TOKEN=hidden replacement']
    assert config(project, 'env', 'unset', 'TOKEN') == 0
    assert read_arguments(path) == args[:-2]
    assert config(project, 'docker-args', 'set', '--', '--gpus=all') == 0
    assert read_arguments(path) == ['--gpus=all']
    assert config(project, 'docker-args', 'clear') == 0
    assert config(project, 'docker-args', 'clear') == 0
    assert not path.exists()
    capsys.readouterr()
    assert config(project, 'docker-args', 'list') == 0
    assert 'No saved Docker options.' in capsys.readouterr().out


@pytest.mark.parametrize('args', [['--network=host'], ['--memory', '2g'], ['--user', 'root'], ['-m2g'], ['-u1000'], ['-dit']])
def test_launcher_owned_options_refused_without_changing_saved_list(project, args, capsys):
    assert config(project, 'docker-args', 'set', '--', '--gpus', 'all') == 0
    path = arguments_path(registered_checkouts()[0].record_path)
    before = path.read_bytes()
    assert config(project, 'docker-args', 'set', '--', *args) == 2
    assert 'composed by the launcher' in capsys.readouterr().err
    assert path.read_bytes() == before


def test_malformed_store_can_be_replaced_or_removed(project, capsys):
    assert config(project, 'docker-args', 'set', '--', '--gpus', 'all') == 0
    path = arguments_path(registered_checkouts()[0].record_path)
    path.write_text('broken secret')
    assert config(project, 'docker-args', 'list') == 2
    assert 'broken secret' not in str(capsys.readouterr())
    assert config(project, 'docker-args', 'set', '--', '--gpus=all') == 0
    assert read_arguments(path) == ['--gpus=all']
    path.write_text('broken secret')
    assert config(project, 'docker-args', 'clear') == 0
    assert not path.exists()


@pytest.mark.parametrize('tokens', [ ['--env', 'TOKEN=sentinel'], ['--env=TOKEN=sentinel'],
                                    ['-e', 'TOKEN=sentinel'], ['-eTOKEN=sentinel'], ['-e=TOKEN=sentinel'] ])
def test_all_env_spellings_are_masked(tokens):
    assert 'sentinel' not in str(redact_environment(tokens))
    assert '<redacted>' in str(redact_environment(tokens))
    assert redact_environment(['--env', 'TOKEN', '--env-file', 'private.env']) == ['--env', 'TOKEN', '--env-file', 'private.env']


def test_saved_args_precede_one_offs_and_are_read_each_launch(tmp_path, capsys):
    root = tmp_path / 'project'
    initialize_codium_project(root)
    assert config(root, 'authorize', 'base-image', LOCKED_BASE) == 0
    assert run_until_prepared(root) == 0
    selected = ExecutionConfiguration.load(root).project
    before = selected.resolution_path.read_bytes()
    saved = ['--gpus', 'all', '--volume', '/example/key:/home/devcapsule/key:ro', '--env=APP_SECRET=stored-value']
    assert config(root, 'docker-args', 'set', '--', *saved) == 0
    realized = SimpleNamespace(image=SimpleNamespace(labels={}, reference='devcapsule-local-codium:fixture'), created=False, locked=parse_locked_environment(selected.lock))
    with patch('devcapsule.commands.project.realize_environment', return_value=realized), patch('devcapsule.commands.project.run_pycharm', return_value=0) as launch:
        assert cli.main(['project', '--path', str(root), 'run', '--', '-eAPP_SECRET=one-off-value']) == 0
        assert launch.call_args.args[0].extra_docker_args == ['--pull=never', *saved, '-eAPP_SECRET=one-off-value']
        assert config(root, 'docker-args', 'clear') == 0
        assert cli.main(['project', '--path', str(root), 'run']) == 0
        assert launch.call_args.args[0].extra_docker_args == ['--pull=never']
    assert selected.resolution_path.read_bytes() == before
    output = str(capsys.readouterr())
    assert 'stored-value' not in output and 'one-off-value' not in output


LABEL_OPERAND = ['--label', '-eTOKEN=label-only', '--env', 'TOKEN=before']
"""A valid docker run list: the label's value looks like an env option; Docker gave the container TOKEN=before."""


def test_env_conveniences_refuse_an_ambiguous_operand_before_writing(project, capsys):
    path = arguments_path(registered_checkouts()[0].record_path)
    assert config(project, 'docker-args', 'set', '--', *LABEL_OPERAND) == 0
    before = path.read_bytes()
    for operation in (('env', 'set', 'TOKEN', 'after'), ('env', 'unset', 'TOKEN'), ('env', 'list',), ('env', 'list', '--json')):
        capsys.readouterr()
        assert config(project, *operation) == 2
        output = capsys.readouterr()
        assert 'argument 2 may be' in output.err and 'docker-args set' in output.err
        assert 'label-only' not in output.err + output.out and 'before' not in output.err + output.out
        assert path.read_bytes() == before
    # An unresolved span can hide the next real option's identity, so another name is refused too.
    for operation in (('env', 'set', 'OTHER', 'value'), ('env', 'unset', 'OTHER')):
        assert config(project, *operation) == 2
        assert 'argument 2 may be' in capsys.readouterr().err
        assert path.read_bytes() == before
    # The list itself stays literal and is still reported, masked conservatively.
    capsys.readouterr()
    assert config(project, 'docker-args', 'list', '--json') == 0
    assert json.loads(capsys.readouterr().out)['arguments'] == ['--label', '-eTOKEN=<redacted>', '--env', 'TOKEN=<redacted>']


def test_env_conveniences_keep_adjacent_env_options_and_other_arguments(project):
    path = arguments_path(registered_checkouts()[0].record_path)
    saved = ['--env', 'A=1', '-eB=2', '--env=C=3', '-e', 'D=4', '--gpus', 'all', '--env', 'A=5', '-eE', '-eF=6']
    assert config(project, 'docker-args', 'set', '--', *saved) == 0
    # -eE names no value: Docker passes the host's E through, which the store reports as None.
    assert read_environment(path) == {'A': '5', 'B': '2', 'C': '3', 'D': '4', 'E': None, 'F': '6'}
    assert config(project, 'env', 'set', 'A', 'new') == 0  # first occurrence keeps its place, the repeat goes
    assert read_arguments(path) == ['--env', 'A=new', '-eB=2', '--env=C=3', '-e', 'D=4', '--gpus', 'all', '-eE', '-eF=6']
    assert config(project, 'env', 'unset', 'B') == 0
    assert config(project, 'env', 'unset', 'F') == 0  # right after -eE, never that option's operand
    assert read_arguments(path) == ['--env', 'A=new', '--env=C=3', '-e', 'D=4', '--gpus', 'all', '-eE']
    # A list ending in a bare flag: the convenience never appends behind it.
    assert config(project, 'docker-args', 'set', '--', '--gpus', 'all', '--read-only') == 0
    assert config(project, 'env', 'set', 'X', '1') == 0
    assert read_arguments(path) == ['--env', 'X=1', '--gpus', 'all', '--read-only']
    assert read_environment(path) == {'X': '1'}
    assert config(project, 'env', 'unset', 'X') == 0
    assert read_arguments(path) == ['--gpus', 'all', '--read-only']


def test_attached_launcher_owned_short_options_are_refused_when_launching_saved_arguments(tmp_path, capsys):
    root = tmp_path / 'project'
    initialize_codium_project(root)
    assert config(root, 'authorize', 'base-image', LOCKED_BASE) == 0
    assert run_until_prepared(root) == 0
    selected = ExecutionConfiguration.load(root).project
    replace_arguments(arguments_path(selected.checkout_path), ['-eNAME=value', '-m2g'])  # written behind the command's back
    with patch('devcapsule.commands.project.offer_upgrades') as upgrades, \
            patch('devcapsule.commands.project.realize_environment') as realize, \
            patch('devcapsule.commands.project.run_pycharm') as launch:
        assert cli.main(['project', '--path', str(root), 'run']) == 2
    assert "Raw docker option '-m' is composed by the launcher" in capsys.readouterr().err
    assert not upgrades.called and not realize.called and not launch.called


OVERLAPPING = {
    'long': ['--label', '--env', '--env', 'TOKEN=hidden-real-sentinel'],
    'short': ['--label', '-e', '-e', 'TOKEN=hidden-real-sentinel'],
    'mixed': ['--label', '-e', '--env', 'TOKEN=hidden-real-sentinel'],
}
"""Valid lists whose first env token is the label's operand and whose second is the real option Docker applies."""


@pytest.mark.parametrize('args', OVERLAPPING.values(), ids=OVERLAPPING.keys())
def test_overlapping_ambiguous_split_tokens_are_masked_and_named(args):
    from devcapsule.docker_arguments import ambiguous_environment_options, environment_options, inline_environment_names
    assert 'hidden-real-sentinel' not in str(redact_environment(args))
    assert redact_environment(args) == [*args[:3], 'TOKEN=<redacted>']
    assert 'hidden-real-sentinel' not in str(redact_environment(args, {'TOKEN'}))
    assert inline_environment_names(args) == {'TOKEN'}
    assert list(environment_options(args)) == []  # nothing is settled: neither candidate is edited
    assert [start for start, _, _ in ambiguous_environment_options(args)] == [1, 2]


@pytest.mark.parametrize('args', OVERLAPPING.values(), ids=OVERLAPPING.keys())
def test_overlapping_ambiguous_split_tokens_refuse_conveniences_and_launch_literally(project, args, capsys, tmp_path):
    path = arguments_path(registered_checkouts()[0].record_path)
    assert config(project, 'docker-args', 'set', '--', *args) == 0
    assert read_arguments(path) == args
    before = path.read_bytes()
    for operation in (('env', 'set', 'TOKEN', 'after'), ('env', 'unset', 'TOKEN'), ('env', 'set', 'OTHER', 'x'), ('env', 'list',), ('env', 'list', '--json')):
        capsys.readouterr()
        assert config(project, *operation) == 2
        output = capsys.readouterr()
        assert 'argument 2 may be' in output.err and 'docker-args set' in output.err
        assert 'hidden-real-sentinel' not in output.out + output.err
        assert path.read_bytes() == before
    capsys.readouterr()
    assert config(project, 'docker-args', 'list') == 0
    text = capsys.readouterr().out
    assert 'hidden-real-sentinel' not in text and 'TOKEN=<redacted>' in text
    # The same tokens reach the launcher untouched, and the narration masks the value.
    root = tmp_path / 'codium'
    initialize_codium_project(root)
    assert config(root, 'authorize', 'base-image', LOCKED_BASE) == 0
    assert run_until_prepared(root) == 0
    assert config(root, 'docker-args', 'set', '--', *args) == 0
    selected = ExecutionConfiguration.load(root).project
    realized = SimpleNamespace(image=SimpleNamespace(labels={}, reference='devcapsule-local-codium:fixture'), created=False, locked=parse_locked_environment(selected.lock))
    with patch('devcapsule.commands.project.realize_environment', return_value=realized), patch('devcapsule.commands.project.run_pycharm', return_value=0) as launch:
        assert cli.main(['project', '--path', str(root), 'run']) == 0
    assert launch.call_args.args[0].extra_docker_args == ['--pull=never', *args]
    output = str(capsys.readouterr())
    assert 'hidden-real-sentinel' not in output and 'TOKEN=<redacted>' in output


@pytest.mark.parametrize('tokens', [['--env', 'TOKEN'], ['-e', 'TOKEN'], ['--env=TOKEN'], ['-eTOKEN'], ['-e=TOKEN']])
def test_pass_through_redaction_keeps_names_without_reading_host_values(tokens, monkeypatch):
    monkeypatch.setenv('TOKEN', 'private-host-sentinel')
    assert redact_environment(tokens) == tokens
    assert redact_environment(tokens, {'TOKEN'}) == tokens


@pytest.mark.parametrize('option', ['--cpus', '--cpus=2', '--cpu-shares', '--cpu-shares=128',
                                   '--cpuset-cpus', '--cpuset-cpus=0', '-c', '-c128', '-tc128'])
def test_cpu_docker_spellings_are_refused_without_writes(project, option, capsys):
    assert config(project, 'docker-args', 'set', '--', '--gpus', 'all') == 0
    path = arguments_path(registered_checkouts()[0].record_path)
    before = path.read_bytes()
    assert config(project, 'docker-args', 'set', '--', option) == 2
    assert 'config set cpus N' in capsys.readouterr().err
    assert path.read_bytes() == before
