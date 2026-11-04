from devcapsule import cli

from tests.launch_preparation import run_until_prepared
"""Configuration lifecycle proof obligations, independent of branch coverage.

Cases establish state transitions through the public CLI and assert the
required behavior at the original audit counterexamples. G-numbers refer to the maintenance
configuration-correctness argument. External Docker/GUI effects alone are faked.
"""

from itertools import permutations
import io
import shutil

import pytest

from devcapsule.configuration.nodes import (
    build_node_registry,
)
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
)
from devcapsule.configuration.storage import (
    load_toml,
    checkout_record_paths,
    manifest_for,
    manifest_source_digest,
)
from devcapsule.configuration.freshness import (
    stale_resolution_inputs,
)
from devcapsule.configuration.values import (
    normalize_configuration_value,
)
from devcapsule.configuration.operations import (
    InitializeRequest,
    ProvidedAnswer,
    initialize_project,
)
from tests.test_upgrade_recovery import (
    checkout,  # The released v0.2.11 fixture, with isolated XDG homes.
    install_external_fakes,
    invoke,
    replace_answers,
)

pytestmark = pytest.mark.legacy


def declare_values(project, extra=''):
    path = project / '.devcapsule/devcapsule.toml'
    path.write_text(path.read_text() + '''
[configuration.values."editor.theme"]
type = "string"
''' + extra)


def test_second_checkout_cannot_inherit_the_first_checkouts_authority(checkout, tmp_path):
    project, record, _ = checkout
    assert load_toml(record)['authorization']['host-browser']['value'] is True
    original = record.read_bytes()
    second = tmp_path / 'second checkout'
    shutil.copytree(project, second)
    assert invoke(second, 'config', 'show') == 0  # listed from nothing, registered by nobody
    assert invoke(second, 'checkout', 'register', 'second') == 0
    manifest = load_toml(second / '.devcapsule/devcapsule.toml')
    second_record, _ = checkout_record_paths(manifest, second)
    assert second_record != record
    assert load_toml(second_record).get('authorization', {}) == {}
    assert run_until_prepared(second) == 3  # No base consent inherited either.
    assert invoke(second, 'config', 'authorize', 'base-image', 'default') == 0
    assert run_until_prepared(second) == 0
    assert 'host-browser' not in load_toml(second_record)['authorization']
    assert record.read_bytes() == original


@pytest.mark.parametrize('kind,raw,expected', [
    ('string', 'text', 'text'), ('string', '', None), ('string', False, None),
    ('integer', '-12', -12), ('integer', 0, 0), ('integer', True, None), ('integer', 1.5, None),
    ('boolean', 'TRUE', True), ('boolean', 'false', False), ('boolean', 1, None), ('boolean', 'yes', None),
    ('memory-size', '8GiB', '8GiB'), ('memory-size', '0GiB', None), ('memory-size', '8GB', '8GiB'), ('memory-size', '8 gigs', None),
    ('string', 'default', None), ('string', 'none', None),
])
def test_scalar_value_domain_partition(kind, raw, expected):
    manifest = {'configuration': {'values': {'test.value': {'type': kind}}}}
    if expected is None:
        with pytest.raises(ProjectConfigurationError):
            normalize_configuration_value(manifest, 'test.value', raw)
    else:
        normalized = normalize_configuration_value(manifest, 'test.value', raw)
        assert normalized == expected
        assert type(normalized) is type(expected)


@pytest.mark.parametrize('initial', ['absent', 'value', 'omitted'])
@pytest.mark.parametrize('action', ['set', 'omit', 'unset'])
def test_ordinary_node_transition_table(checkout, initial, action):
    project, record, resolution = checkout
    declare_values(project)
    if initial != 'absent':
        assert invoke(project, 'config', 'set', 'editor.theme', 'dark' if initial == 'value' else 'none') == 0
    assert run_until_prepared(project) == 0
    before_record, before_resolution = record.read_bytes(), resolution.read_bytes()
    old_authorizations = load_toml(record)['authorization']
    args = ('set', 'editor.theme', 'default') if action == 'unset' else (
        'set', 'editor.theme', 'light' if action == 'set' else 'none'
    )
    result = invoke(project, 'config', *args)
    if action == 'unset' and initial == 'absent':
        # Forgetting an answer that was never given changes nothing and says so.
        assert result == 0
        assert load_toml(record) == load_toml(record) and 'editor.theme' not in load_toml(record).get('configuration', {}).get('values', {})
    else:
        assert result == 0
        config = load_toml(record).get('configuration', {})
        assert config.get('values', {}).get('editor.theme') == ('light' if action == 'set' else None)
        assert ('editor.theme' in config.get('omitted-values', [])) == (action == 'omit')
    assert load_toml(record)['authorization'] == old_authorizations
    assert resolution.read_bytes() == before_resolution
    assert run_until_prepared(project) == 0


@pytest.mark.parametrize('order', list(permutations(['ordinary', 'binding', 'authorization'])))
def test_independent_changes_commute_and_require_one_final_resolve(checkout, order):
    project, record, resolution = checkout
    declare_values(project)
    assert run_until_prepared(project) == 0
    project_files = {p: p.read_bytes() for p in (project / '.devcapsule').iterdir()}
    previous_resolution = resolution.read_bytes()
    commands = {
        'ordinary': ('set', 'editor.theme', 'dark'),
        'binding': ('bind', 'home', f'host-directory:{project}'),
        'authorization': ('authorize', 'development-sudo', 'false'),
    }
    for kind in order:
        assert invoke(project, 'config', *commands[kind]) == 0
        assert resolution.read_bytes() == previous_resolution
    assert {p: p.read_bytes() for p in project_files} == project_files
    assert run_until_prepared(project) == 0
    resolved = load_toml(resolution)
    assert resolved['configuration']['values'] == {'editor.theme': 'dark'}
    assert resolved['state']['bindings'] == {'home': str(project)}
    assert resolved['authorization']['development-sudo'] is False
    # Recovery is idempotent after choices settle; it does not ask again.
    settled = resolution.read_bytes()
    assert run_until_prepared(project) == 0
    assert resolution.read_bytes() == settled


def test_a_failed_second_edit_does_not_undo_the_first_or_publish_it(checkout):
    project, record, resolution = checkout
    declare_values(project)
    assert run_until_prepared(project) == 0
    previous_resolution = resolution.read_bytes()
    assert invoke(project, 'config', 'set', 'editor.theme', 'dark') == 0
    after_first = record.read_bytes()
    assert invoke(project, 'config', 'authorize', 'host-x11', 'invalid') == 2
    assert record.read_bytes() == after_first
    assert resolution.read_bytes() == previous_resolution
    assert run_until_prepared(project) == 0
    assert load_toml(resolution)['configuration']['values']['editor.theme'] == 'dark'


@pytest.mark.parametrize('artifact,field', [
    ('devcapsule.toml', 'devcapsule-schema-version'),
    ('devcapsule.linux-amd64.lock', 'devcapsule-lock-format-version'),
])
def test_unknown_project_schema_is_refused_without_mutation(checkout, artifact, field):
    project, record, resolution = checkout
    path = project / '.devcapsule' / artifact
    path.write_text(path.read_text().replace(f'{field} = 1', f'{field} = 99'))
    before = {p: p.read_bytes() for p in (path, record, resolution)}
    assert run_until_prepared(project) == 2
    assert {p: p.read_bytes() for p in before} == before


def test_unknown_checkout_schema_cannot_be_rewritten(checkout):
    project, record, resolution = checkout
    record.write_text(record.read_text().replace('devcapsule-checkout-schema-version = 1',
                                               'devcapsule-checkout-schema-version = 99'))
    before = record.read_bytes(), resolution.read_bytes()
    result = invoke(project, 'config', 'authorize', 'development-sudo', 'false')
    assert (result, record.read_bytes(), resolution.read_bytes()) == (2, *before)


def test_an_unreadable_resolution_is_replaced_by_the_launch(checkout, monkeypatch):
    # The resolution is the launch's own derived artifact since 0.3.0 rc4: run
    # derives it again from the inputs, so a file of an unknown schema is
    # overwritten, never an obstacle.
    project, _, resolution = checkout
    resolution.write_text(resolution.read_text().replace('devcapsule-resolved-schema-version = 1',
                                                       'devcapsule-resolved-schema-version = 99'))
    events = []
    launch = install_external_fakes(monkeypatch, events)
    assert invoke(project, 'run') == 0
    assert launch.call_count == 1
    assert load_toml(resolution)['devcapsule-resolved-schema-version'] == 1


def test_init_cannot_treat_repository_recommendations_as_developer_answers(checkout):
    project, record, resolution = checkout
    path = project / '.devcapsule/devcapsule.toml'
    path.write_text(path.read_text() + '''
[host.docker.mode.recommended]
value = "host-socket"
justification = "Repository requests Docker access."
''')
    record.unlink()
    resolution.unlink()
    assert invoke(project, 'init', '--authorize', 'base-image', 'default') == 0
    # The only decision supplied was base-image consent. Nothing answered
    # the host-Docker question, so there must be no grant for that node.
    assert load_toml(record)['authorization'].get('docker-daemon', {}).get('value') != 'host-socket'


def test_workflow_metadata_is_not_a_configuration_dependency(checkout):
    project, record, resolution = checkout
    _, manifest = manifest_for(project)
    lock = load_toml(project / '.devcapsule/devcapsule.linux-amd64.lock')
    manifest['workflow'] = {'definition': 'devcapsule', 'version': '0.2.14.dev0', 'mode': 'single-stream'}
    assert stale_resolution_inputs(manifest, lock, load_toml(record), load_toml(resolution)) == ()


def test_resolution_cannot_publish_an_ambiguous_node_tree(checkout):
    project, _, resolution = checkout
    declare_values(project, '''
[configuration.values.home]
type = "string"
''')
    manifest = load_toml(project / '.devcapsule/devcapsule.toml')
    lock = load_toml(project / '.devcapsule/devcapsule.linux-amd64.lock')
    with pytest.raises(ProjectConfigurationError, match='declared twice'):
        build_node_registry(manifest, lock)
    before = resolution.read_bytes()
    result = run_until_prepared(project)
    assert (result, resolution.read_bytes()) == (2, before)


def test_edit_must_preserve_unknown_content_or_refuse_without_writing(checkout):
    project, record, _ = checkout
    record.write_text(record.read_text() + '\n[extension]\nretained = "developer data"\n')
    before = record.read_bytes()
    result = invoke(project, 'config', 'authorize', 'development-sudo', 'false')
    assert (result == 2 and record.read_bytes() == before) or (
        result == 0 and load_toml(record).get('extension') == {'retained': 'developer data'}
    )


def test_init_elicits_a_required_ordinary_value_once(checkout):
    project, record, resolution = checkout
    declare_values(project, '''
[configuration.values."service.port"]
type = "integer"
required = true
''')
    record.unlink()
    resolution.unlink()
    output = io.StringIO()
    # Repository content and the base are already answered. Only the required
    # local value is asked; init does not re-ask project-authoring questions.
    initialize_project(
        InitializeRequest(directory=project, interactive=True,
                          answers=(ProvidedAnswer('authorize', 'base-image', 'default'),)),
        input_stream=io.StringIO('5432\n'), output_stream=output,
    )
    assert load_toml(record)['configuration']['values']['service.port'] == 5432
    assert output.getvalue().count('service.port') == 1


def test_legacy_host_values_are_typed_before_authorization(checkout, monkeypatch):
    project, record, _ = checkout
    record.write_text(record.read_text() + '\n[host]\ndevelopment-sudo = "false"\n')
    result = run_until_prepared(project)
    if result == 0:
        launch = install_external_fakes(monkeypatch, [])
        assert invoke(project, 'run') == 0
        assert launch.call_args.args[0].enable_sudo is False
    assert result == 2


def test_independent_invalid_values_are_reported_together(checkout, capsys):
    project, record, _ = checkout
    declare_values(project, '''
[configuration.values."service.port"]
type = "integer"
''')
    record.write_text(record.read_text() + '\n[configuration.values]\n"editor.theme" = false\n"service.port" = "invalid"\n')
    assert run_until_prepared(project) == 2
    message = capsys.readouterr().err
    assert 'editor.theme' in message and 'service.port' in message


def test_shipped_cli_recommendation_override_and_omission(checkout, capsys):
    project, record, resolution = checkout
    declaration = project / '.devcapsule/devcapsule.toml'
    declaration.write_text(declaration.read_text() + '\n[configuration.values."runtime.devcapsule-command"]\n'
        'type = "string"\nruntime-effect = "devcapsule.command-name"\nrecommended = "devcapsule0"\n')
    original = record.read_bytes()
    assert run_until_prepared(project) == 0
    assert load_toml(resolution)['runtime']['devcapsule-command'] == 'devcapsule0'
    assert record.read_bytes() == original  # Derived recommendation is not a local answer.
    assert invoke(project, 'config', 'show') == 0
    assert 'project recommendation' in capsys.readouterr().out
    assert invoke(project, 'config', 'set', 'runtime.devcapsule-command', 'devcapsule') == 0
    assert run_until_prepared(project) == 0
    assert load_toml(resolution)['runtime']['devcapsule-command'] == 'devcapsule'
    for invalid in ('../devcapsule', '/bin/sh', 'arbitrary-name'):
        before = record.read_bytes()
        assert invoke(project, 'config', 'set', 'runtime.devcapsule-command', invalid) == 2
        assert record.read_bytes() == before
    assert invoke(project, 'config', 'set', 'runtime.devcapsule-command', 'default') == 0
    assert run_until_prepared(project) == 0
    assert load_toml(resolution)['runtime']['devcapsule-command'] == 'devcapsule0'
    assert invoke(project, 'config', 'set', 'runtime.devcapsule-command', 'none') == 0
    assert run_until_prepared(project) == 0
    assert 'devcapsule-command' not in load_toml(resolution)['runtime']
    assert invoke(project, "config", "set", 'runtime.devcapsule-command', "default") == 0
    assert run_until_prepared(project) == 0
    assert load_toml(resolution)['runtime']['devcapsule-command'] == 'devcapsule0'


def test_reserved_shipped_cli_name_carries_the_effect_without_the_attribute(checkout):
    # Released clients before 0.2.14 reject any runtime-effect they do not
    # know, so the repository manifest must not spell this one; the name
    # alone selects the effect here.
    project, record, resolution = checkout
    declaration = project / '.devcapsule/devcapsule.toml'
    declaration.write_text(declaration.read_text() + '\n[configuration.values."runtime.devcapsule-command"]\n'
        'type = "string"\nrecommended = "devcapsule0"\n')
    assert run_until_prepared(project) == 0
    assert load_toml(resolution)['runtime']['devcapsule-command'] == 'devcapsule0'
    assert invoke(project, 'config', 'set', 'runtime.devcapsule-command', 'arbitrary-name') == 2


def test_reserved_shipped_cli_name_rejects_a_different_effect():
    manifest = {'configuration': {'values': {'runtime.devcapsule-command': {
        'type': 'memory-size', 'runtime-effect': 'docker.memory-limit',
    }}}}
    with pytest.raises(ProjectConfigurationError, match='reserved for runtime effect'):
        build_node_registry(manifest, {})


def test_unknown_runtime_effect_names_the_running_version():
    manifest = {'configuration': {'values': {'runtime.future': {
        'type': 'string', 'runtime-effect': 'devcapsule.not-yet-invented',
    }}}}
    with pytest.raises(ProjectConfigurationError) as error:
        build_node_registry(manifest, {})
    message = str(error.value)
    assert "'devcapsule.not-yet-invented' is not supported by DevCapsule " in message
    assert 'supported: devcapsule.command-name, docker.memory-limit' in message
    assert 'may require a newer DevCapsule' in message


@pytest.mark.parametrize('recommended', ['default', 'none', '../bin/devcapsule', 7, False])
def test_invalid_shipped_cli_recommendation_is_rejected(recommended):
    manifest = {'configuration': {'values': {'runtime.devcapsule-command': {
        'type': 'string', 'runtime-effect': 'devcapsule.command-name', 'recommended': recommended,
    }}}}
    with pytest.raises(ProjectConfigurationError):
        build_node_registry(manifest, {})


def test_config_list_is_data_only_and_show_carries_the_review(checkout, capsys):
    # Owner direction 2026-10-24 (the CLI UX work order, principle 6): the
    # listing shows the effective value, its source and what is pending, and
    # writes nothing; `list` is the same listing as `show`.
    project, record, resolution = checkout
    # The fixture's base has no contained desktop: host X11 needs consent first.
    assert invoke(project, 'config', 'authorize', 'host-x11', 'true') == 0
    assert run_until_prepared(project) == 0
    capsys.readouterr()
    assert invoke(project, 'config', 'show') == 0
    listing = capsys.readouterr().out
    assert 'KIND' in listing and 'SOURCE' in listing and 'PENDING' in listing
    assert 'Nothing is pending.' in listing
    assert 'Configuration review' not in listing and 'resolve explicitly' not in listing
    assert invoke(project, 'config', 'show') == 0
    shown = capsys.readouterr().out
    assert shown == listing
    assert str(record) in shown
    # A record edited behind the plan's back is simply the next launch's input.
    table = dict(load_toml(record)['authorization'])
    table['host-browser'] = {**table['host-browser'], 'value': False}
    replace_answers(project, record, table)
    assert invoke(project, 'config', 'show') == 0
    assert 'Nothing is pending.' in capsys.readouterr().out
    # A missing required decision is a pending row with its command.
    replace_answers(project, record, {name: value for name, value in table.items() if name != 'base-image'})
    assert invoke(project, 'config', 'show') == 0
    shown = capsys.readouterr().out
    assert 'Pending decisions:' in shown and 'home trust accept devcapsule-base' in shown
    assert invoke(project, 'config', 'check') == 3


def test_home_defaults_stale_only_the_home_input(checkout):
    from devcapsule.configuration.storage import load_settings
    from devcapsule.configuration.execution import ExecutionConfiguration
    project, record, resolution = checkout
    # This fixture contains a plan written by the released 0.2.11 launcher,
    # which recorded the whole schema-1 file's digest; a reader of the file
    # passes that digest beside the schema-2 reading, as the adapters do.
    _, manifest = manifest_for(project)
    digest = manifest_source_digest(project)
    lock = load_toml(project / '.devcapsule/devcapsule.linux-amd64.lock')
    local, previous = load_toml(record), load_toml(resolution)
    assert previous['sources'].get('home-config', 'absent') == 'absent'
    assert stale_resolution_inputs(manifest, lock, local, previous, load_settings(), source_digest=digest) == ()
    assert cli.main(['home', 'default', 'cpus', '2']) == 0
    assert stale_resolution_inputs(manifest, lock, local, previous, load_settings(), source_digest=digest) == ('home-config',)
    assert run_until_prepared(project) == 0
    current = ExecutionConfiguration.load(project).project.resolution
    assert current['runtime']['cpus'] == 2
    assert cli.main(['home', 'default', 'cpus', '3']) == 0
    assert stale_resolution_inputs(manifest, lock, load_toml(record), current, load_settings()) == ('home-config',)
    assert cli.main(['home', 'default', 'cpus', 'none']) == 0
    assert stale_resolution_inputs(manifest, lock, local, previous, load_settings(), source_digest=digest) == ()


def test_old_base_listing_reports_host_x11_without_changing_consent(checkout, capsys):
    import json
    project, record, resolution = checkout
    before = record.read_bytes(), resolution.read_bytes()
    assert invoke(project, 'config', 'show', '--json') == 0
    rows = json.loads(capsys.readouterr().out)['rows']
    x11 = next(row for row in rows if row['name'] == 'host-x11')
    # Answer 4 of the CLI UX work order: host X11 only by explicit consent,
    # on a base without a contained desktop too; the row asks for it.
    assert x11['effective'] == 'host X11 (needs your consent)'
    assert x11['source'] == 'no contained desktop on this base'
    assert 'with your consent' in x11['pending'] and 'config authorize host-x11 true' in x11['command']
    assert (record.read_bytes(), resolution.read_bytes()) == before


def test_old_base_with_x11_denied_is_pending_in_listing(checkout, capsys):
    import json
    project, record, _ = checkout
    assert invoke(project, 'config', 'deny', 'host-x11') == 0
    before = record.read_bytes()
    capsys.readouterr()
    assert invoke(project, 'config', 'check', '--json') == 3
    rows = json.loads(capsys.readouterr().out)['rows']
    x11 = next(row for row in rows if row['name'] == 'host-x11')
    assert x11['effective'] == 'unavailable'
    assert 'no contained desktop' in x11['pending']
    assert 'config authorize host-x11 true' in x11['command']
    assert record.read_bytes() == before
