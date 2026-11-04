
from tests.launch_preparation import run_until_prepared
"""Cross-boundary configuration invariants, partitioned by contract condition.

The predecessor fixture is released data, not produced by the implementation
under test. Only external Docker/GUI effects are replaced in CLI journeys.
"""
from copy import deepcopy
from datetime import date
import io
import math
import stat
from pathlib import Path
import tomllib

import pytest

from devcapsule.configuration.file_formats import (
    ConfigurationFileKind,
    validate_file_format,
    render_toml,
    table,
)
from devcapsule.configuration.review import (
    HostAccess,
    review_configuration,
)
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
    canonical_digest,
)
from devcapsule.configuration.storage import (
    load_toml,
    atomic_write,
    manifest_for,
)
from devcapsule.configuration.freshness import (
    stale_resolution_inputs,
)
from devcapsule.configuration.operations import (
    InitializeRequest,
    ProvidedAnswer,
    initialize_project,
)
from devcapsule.launch.pycharm import DockerMode, PycharmRunOptions, build_run_config
from devcapsule.platforms import Platform
from tests.test_pycharm import base_env
from tests.test_upgrade_recovery import checkout, invoke, install_external_fakes

pytestmark = pytest.mark.legacy


def replace_document(path, edit):
    document = load_toml(path)
    edit(document)
    path.write_text(render_toml(document))


def artifacts(checkout):
    project, record, resolution = checkout
    return {
        ConfigurationFileKind.manifest: project / '.devcapsule/devcapsule.toml',
        ConfigurationFileKind.lock: project / '.devcapsule/devcapsule.linux-amd64.lock',
        ConfigurationFileKind.checkout: record,
        ConfigurationFileKind.resolution: resolution,
    }


@pytest.mark.parametrize('artifact', list(ConfigurationFileKind))
@pytest.mark.parametrize('version', [None, False, True, 0, 1.0, '1', 2, 99])
def test_schema_admission_distinguishes_version_from_truthiness(artifact, version):
    if artifact is ConfigurationFileKind.manifest and version == 2:
        # The manifest's second schema, 2026-10-24; every other file stays at 1.
        validate_file_format({artifact.value: version}, artifact, 'test input')
        return
    with pytest.raises(ProjectConfigurationError, match='unsupported'):
        validate_file_format({artifact.value: version}, artifact, 'test input')
    validate_file_format({artifact.value: 1}, artifact, 'test input')


@pytest.mark.parametrize('artifact', [kind for kind in ConfigurationFileKind if kind is not ConfigurationFileKind.resolution])
@pytest.mark.parametrize('command', [
    ('config', 'show'), ('run',), ('init', '--regenerate'),
])
def test_unsupported_input_refuses_without_side_effects(checkout, monkeypatch, artifact, command):
    # The resolution is not an input since 0.3.0 rc4: run derives it; see
    # test_an_unreadable_resolution_is_replaced_by_the_launch in test_contract.
    paths = artifacts(checkout)
    replace_document(paths[artifact], lambda d: d.update({artifact.value: 99}))
    before = {p: p.read_bytes() for p in paths.values()}
    events = []
    launch = install_external_fakes(monkeypatch, events)
    assert invoke(checkout[0], *command) == 2
    assert {p: p.read_bytes() for p in before} == before
    assert events == [] and launch.call_count == 0


@pytest.mark.parametrize('command', [
    ('config', 'set', 'editor.theme', 'dark'),
    ('config', 'bind', 'home', 'host-directory:.'),
    ('config', 'authorize', 'host-browser', 'false'),
    ("config", "forget", 'host-browser'),
    ('state', 'adopt', 'home', '--from', '.'),
])
def test_every_edit_admits_checkout_before_replacing_it(checkout, command):
    project, record, resolution = checkout
    replace_document(record, lambda d: d.update({'devcapsule-checkout-schema-version': 99}))
    before = record.read_bytes(), resolution.read_bytes()
    assert invoke(project, *command) == 2
    assert (record.read_bytes(), resolution.read_bytes()) == before


@pytest.mark.parametrize('path', [(), ('project',), ('checkout',), ('configuration',),
                                  ('configuration', 'bindings'), ('state',)])
def test_unknown_checkout_fields_are_never_discarded(checkout, path):
    project, record, _ = checkout
    def edit(document):
        node = document
        for key in path:
            node = node.setdefault(key, {})
        node['future-setting'] = 'uninterpreted'
    replace_document(record, edit)
    before = record.read_bytes()
    assert invoke(project, 'config', 'authorize', 'host-browser', 'false') == 2
    assert record.read_bytes() == before


@pytest.mark.parametrize('branch', ['project', 'checkout', 'configuration', 'authorization', 'state', 'host'])
def test_malformed_checkout_table_is_an_actionable_error(checkout, branch):
    project, record, _ = checkout
    replace_document(record, lambda d: d.update({branch: 'not a table'}))
    before = record.read_bytes()
    assert run_until_prepared(project) == 2
    assert record.read_bytes() == before


def test_invalid_unrelated_answers_survive_an_edit_until_repaired(checkout):
    project, record, _ = checkout
    replace_document(record, lambda d: d['authorization'].update({
        'development-sudo': {'value': 17, 'recommendation-digest': 'stale', 'note': 'keep'},
        'host-x11': {},
    }))
    original = load_toml(record)['authorization']
    assert invoke(project, 'config', 'authorize', 'host-browser', 'false') == 0
    saved = load_toml(record)['authorization']
    assert saved['development-sudo'] == original['development-sudo']
    assert saved['host-x11'] == original['host-x11']
    assert run_until_prepared(project) == 3  # the invalid answers are pending decisions
    assert invoke(project, 'config', 'authorize', 'development-sudo', 'false') == 0
    assert invoke(project, 'config', 'authorize', 'host-x11', 'false') == 0
    assert run_until_prepared(project) == 0


@pytest.mark.parametrize('value', ['text\n"\\', True, False, 0, -3, 1.25, float('inf'),
                                  float('-inf'), [1, {'a.b': ['quoted', True]}]])
def test_checkout_writer_round_trips_every_supported_scalar(value):
    document = {'key': value, 'nested': {'with.dots': value}, 'empty': {}}
    assert tomllib.loads(render_toml(document)) == document


def test_checkout_writer_nan_and_unsupported_scalar():
    assert math.isnan(tomllib.loads(render_toml({'x': float('nan')}))['x'])
    with pytest.raises(ProjectConfigurationError, match='left intact'):
        render_toml({'date': date(2026, 9, 20)})
    assert table({}, 'missing', 'table') == {}


@pytest.mark.parametrize('name,allow,deny,attribute', [
    ('docker-daemon', 'host-socket', 'none', 'docker_daemon'),
    ('network', 'host', 'bridge', 'network'),
    ('development-sudo', True, False, 'development_sudo'),
    ('host-browser', True, False, 'host_browser'),
    ('host-x11', True, False, 'host_x11'),
])
def test_permission_precedence_is_typed_and_preserves_denial(name, allow, deny, attribute):
    default = HostAccess()
    granted = default.overlay({name: allow})
    denied = granted.overlay({name: deny})
    assert getattr(denied, attribute) == deny
    assert getattr(denied.overlay({}), attribute) == deny
    assert getattr(denied.overlay({name: allow}), attribute) == allow
    assert default == HostAccess()  # Immutable overlays cannot mutate a prior plan.
    for invalid in (None, 1, [], {}, 'false' if isinstance(allow, bool) else False):
        with pytest.raises(ProjectConfigurationError):
            granted.overlay({name: invalid})


def test_unknown_host_decisions_are_reported_together():
    with pytest.raises(ProjectConfigurationError) as failure:
        HostAccess().overlay({'future-host': True, 'development-sudo': 'false'})
    assert 'future-host' in str(failure.value) and 'development-sudo' in str(failure.value)


@pytest.mark.parametrize('action', ['unset', 'replace-then-unset'])
def test_removing_a_decision_cannot_reveal_a_legacy_grant(checkout, monkeypatch, action):
    project, record, _ = checkout
    replace_document(record, lambda d: d.update({'host': {'development-sudo': True}}))
    if action == 'replace-then-unset':
        assert invoke(project, 'config', 'authorize', 'development-sudo', 'false') == 0
        assert 'development-sudo' not in load_toml(record).get('host', {})
    assert invoke(project, "config", "forget", 'development-sudo') == 0
    assert run_until_prepared(project) == 0
    launch = install_external_fakes(monkeypatch, [])
    assert invoke(project, 'run') == 0
    assert launch.call_args.args[0].enable_sudo is False


def test_a_removed_binding_never_reaches_the_launch(checkout, monkeypatch):
    project, record, resolution = checkout
    assert invoke(project, 'config', 'add', 'codex-agent') == 0
    assert invoke(project, 'config', 'bind', 'home', f'host-directory:{project}') == 0
    assert invoke(project, 'config', 'bind', 'codex/openai-api-key', 'host-environment:OPENAI_API_KEY') == 0
    assert run_until_prepared(project) == 0
    assert invoke(project, 'config', 'unbind', 'home') == 0
    assert invoke(project, 'config', 'unbind', 'codex/openai-api-key') == 0
    launch = install_external_fakes(monkeypatch, [])
    assert invoke(project, 'run') == 0
    options = launch.call_args.args[0]
    assert options.persistent_home is None and options.secret_environment == ()
    # The plan the launch derived carries neither either.
    derived = load_toml(resolution)
    assert 'bindings' not in derived.get('state', {}) and 'secret' not in derived


def test_project_launch_cannot_inherit_unbound_paths_or_credentials(checkout, tmp_path):
    project, _, _ = checkout
    env = base_env(tmp_path)
    unbound = tmp_path / 'unbound'
    env.update({
        'DEVCAPSULE_HOME_DIR': str(unbound), 'PYCHARM_IDE_CONFIG_DIR': str(unbound),
        'PYCHARM_PLUGIN_DIR': str(unbound), 'GITHUB_TOKEN_FILE': str(unbound / 'secret'),
        'PYCHARM_GIT_TOKEN_ENV': 'UNBOUND_TOKEN', 'PYCHARM_ENABLE_SUDO': 'invalid',
        'DOCKER_MODE': 'invalid',
    })
    config = build_run_config(PycharmRunOptions(
        project=project, capsule_platform=Platform.LINUX_AMD64, inherit_legacy_configuration=False,
        docker_mode=DockerMode.none, enable_sudo=False, network_mode='bridge',
    ), env)
    assert config.persistent_home != unbound and config.ide_config != unbound and config.plugins != unbound
    assert config.git_token_file is None and config.git_token_env == ''
    assert config.enable_sudo is False and config.docker_mode == 'none' and config.network_mode == 'bridge'
    assert not unbound.exists()


@pytest.mark.parametrize('value', [False, True, None])
def test_explicit_sudo_decision_overrides_legacy_environment(value, tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    env = base_env(tmp_path)
    env['PYCHARM_ENABLE_SUDO'] = '1'
    config = build_run_config(PycharmRunOptions(project=project, capsule_platform=Platform.LINUX_AMD64, docker_mode=DockerMode.none,
                                               enable_sudo=value), env)
    assert config.enable_sudo is (True if value is None else value)


@pytest.mark.parametrize('field,value', [('memory-limit-bytes', '8GiB'), ('memory-limit-bytes', True),
                                      ('cpus', 0), ('component', []), ('project-mount', 3), ('image', [])])
def test_an_invalid_derived_plan_is_refused_as_a_value(checkout, field, value):
    # Since 0.3.0 rc4 the launch derives its plan and never reads a stored one
    # as an input; the plan's own validation is what refuses a bad value.
    from devcapsule.configuration.resolution import Resolution
    project, _, resolution = checkout
    document = load_toml(resolution)
    document['runtime'][field] = value
    with pytest.raises(ProjectConfigurationError):
        Resolution(document)


def test_a_tampered_stored_plan_does_not_reach_the_launch(checkout, monkeypatch):
    project, _, resolution = checkout
    replace_document(resolution, lambda d: d.update({'state': {'bindings': {'home': str(project)}}}))
    launch = install_external_fakes(monkeypatch, [])
    assert invoke(project, 'run') == 0
    assert launch.call_args.args[0].persistent_home is None
    assert 'bindings' not in load_toml(resolution).get('state', {})


@pytest.mark.parametrize('scoped', [False, True])
def test_metadata_only_changes_are_fresh_but_runtime_changes_are_stale(checkout, scoped):
    project, record, resolution = checkout
    if scoped:
        assert run_until_prepared(project) == 0
    _, manifest = manifest_for(project)
    lock = load_toml(project / '.devcapsule/devcapsule.linux-amd64.lock')
    original = deepcopy(manifest)
    manifest['workflow'] = {'mode': 'multiple-streams'}
    manifest['project']['name'] = 'New display name'
    assert stale_resolution_inputs(manifest, lock, load_toml(record), load_toml(resolution)) == ()
    manifest['project']['mount'] = '/different'
    assert stale_resolution_inputs(manifest, lock, load_toml(record), load_toml(resolution)) == ('manifest',)
    assert original != manifest


def test_two_nodes_cannot_control_one_runtime_effect(checkout):
    project, _, resolution = checkout
    manifest = project / '.devcapsule/devcapsule.toml'
    replace_document(manifest, lambda d: d.update({'configuration': {'values': {
        name: {'type': 'memory-size', 'runtime-effect': 'docker.memory-limit'} for name in ('first', 'second')
    }}}))
    before = resolution.read_bytes()
    assert run_until_prepared(project) == 2
    assert resolution.read_bytes() == before


def test_missing_required_nodes_are_batched_across_init_families(checkout, capsys):
    project, record, resolution = checkout
    manifest = project / '.devcapsule/devcapsule.toml'
    replace_document(manifest, lambda d: d.update({'configuration': {'values': {
        name: {'type': 'integer', 'required': True} for name in ('first', 'second')
    }}}))
    record.unlink()
    resolution.unlink()
    assert invoke(project, 'init') == 2
    message = capsys.readouterr().err
    assert all(name in message for name in ('base-image', 'first', 'second'))
    assert not record.exists() and not resolution.exists()


def test_invalid_nodes_are_batched_within_and_across_families(checkout):
    project, record, _ = checkout
    manifest = load_toml(project / '.devcapsule/devcapsule.toml')
    lock = load_toml(project / '.devcapsule/devcapsule.linux-amd64.lock')
    document = load_toml(record)
    document['configuration'] = {'bindings': {
        'host-directory': {'home': '/absent-one', 'pycharm/config': '/absent-two'},
        'host-environment': {'unknown-secret-a': 'A', 'unknown-secret-b': 'B'},
    }}
    document['state'] = {'adopted': {'unknown-state': '/absent-three'}}
    review = review_configuration(manifest, lock, document)
    message = review.render(project)
    assert not review.ready
    assert all(name in message for name in ('home', 'pycharm/config', 'unknown-secret-a',
                                            'unknown-secret-b', 'unknown-state'))


@pytest.mark.parametrize('name', ['creator', 'name', 'require', 'slug', 'project-mount'])
def test_required_configuration_cannot_inherit_an_identity_answer(checkout, name):
    project, record, resolution = checkout
    replace_document(project / '.devcapsule/devcapsule.toml', lambda d: d.update({
        'configuration': {'values': {name: {'type': 'integer', 'required': True}}},
    }))
    record.unlink()
    resolution.unlink()
    output = io.StringIO()
    initialize_project(InitializeRequest(directory=project, interactive=True,
                       answers=(ProvidedAnswer('authorize', 'base-image', 'default'),)),
                       input_stream=io.StringIO('7\n'), output_stream=output)
    assert load_toml(record)['configuration']['values'][name] == 7
    assert output.getvalue().count(f'{name}:') == 1


@pytest.mark.parametrize('family,name,value', [
    ('set', 'editor.theme', 'dark'), ('bind', 'home', 'host-directory:.'),
    ('authorize', 'development-sudo', 'false'),
])
def test_init_and_individual_edits_have_the_same_local_effect(checkout, family, name, value):
    project, record, _ = checkout
    replace_document(project / '.devcapsule/devcapsule.toml', lambda d: d.update({
        'configuration': {'values': {'editor.theme': {'type': 'string'}}},
    }))
    if family == 'bind':
        value = f'host-directory:{project}'
    before = record.read_bytes()
    assert invoke(project, 'config', family, name, value) == 0
    direct = load_toml(record)
    record.write_bytes(before)
    assert invoke(project, 'init', f'--{family}', name, value) == 0
    assert load_toml(record) == direct


def test_init_retains_a_current_local_base_without_reasking(checkout, monkeypatch):
    from devcapsule.materialization import ImageDetails
    from devcapsule.configuration import operations as project_operations
    project, record, resolution = checkout
    image = ImageDetails('my-local-base:old', 'sha256:' + 'd' * 64, {
        'devcapsule.image.managed': 'true', 'devcapsule.metadata.version': '1',
        'devcapsule.image.kind': 'base',
    }, 'linux', 'amd64')
    lock = load_toml(project / '.devcapsule/devcapsule.linux-amd64.lock')
    replace_document(record, lambda d: d['authorization'].update({'base-image': {
        'reference': 'my-local-base:old', 'image-id': image.identity, 'lock-digest': canonical_digest(lock),
    }}))
    resolution.unlink()  # A normal repair must not mistake a saved local base for no answer.
    monkeypatch.setattr(project_operations, 'required_local_image', lambda reference: image)
    output = io.StringIO()
    initialize_project(InitializeRequest(directory=project, interactive=True),
                       input_stream=io.StringIO(''), output_stream=output)
    assert output.getvalue() == ''
    assert load_toml(record)['authorization']['base-image']['reference'] == 'my-local-base:old'


@pytest.mark.parametrize('mount', ['relative', '/', '/etc', '/workspace/../etc', '/workspace,src=/'])
def test_project_mount_is_validated_before_resolution_or_materialization(checkout, monkeypatch, mount):
    project, _, resolution = checkout
    replace_document(project / '.devcapsule/devcapsule.toml', lambda d: d['project'].update({'mount': mount}))
    saved = resolution.read_bytes()
    events = []
    launch = install_external_fakes(monkeypatch, events)
    assert run_until_prepared(project) == 2
    assert invoke(project, 'run') == 2
    assert resolution.read_bytes() == saved and not events and launch.call_count == 0


@pytest.mark.parametrize('sources', [{'manifest': []}, {'manifest-scope': 'future-scope'}])
def test_unsupported_fingerprint_representation_is_refused_as_a_value(checkout, sources):
    from devcapsule.configuration.resolution import Resolution
    project, _, resolution = checkout
    document = load_toml(resolution)
    document['sources'] = sources
    with pytest.raises(ProjectConfigurationError):
        Resolution(document)


def test_incomplete_assessment_cannot_be_serialized_or_treated_as_compatible(checkout):
    from devcapsule.configuration.resolution import (
        render_resolution,
        same_effective_resolution,
    )
    project, record, resolution = checkout
    _, manifest = manifest_for(project)
    lock = load_toml(project / '.devcapsule/devcapsule.linux-amd64.lock')
    document = load_toml(record)
    document['authorization'].pop('base-image')
    review = review_configuration(manifest, lock, document)
    with pytest.raises(ProjectConfigurationError, match='incomplete'):
        render_resolution(manifest, lock, document, review)
    assert not same_effective_resolution(manifest, lock, document, load_toml(resolution))


@pytest.mark.parametrize('mutation', ['missing', 'reserved-mount', 'different-surface'])
def test_the_launch_derives_a_coherent_plan_whatever_the_stored_one_says(checkout, monkeypatch, mutation):
    # The stored plan is the launch's own output since 0.3.0 rc4: missing or
    # tampered, it is derived again from the inputs before anything runs.
    project, _, resolution = checkout
    if mutation == 'missing':
        resolution.unlink()
    else:
        replace_document(resolution, lambda d: d['runtime'].update(
            {'project-mount': '/etc'} if mutation == 'reserved-mount' else {'component': 'codium'}))
    events = []
    launch = install_external_fakes(monkeypatch, events)
    assert invoke(project, 'run') == 0
    assert launch.call_count == 1
    derived = load_toml(resolution)['runtime']
    assert derived['component'] == 'pycharm' and derived['project-mount'] != '/etc'


@pytest.mark.parametrize('scoped', [False, True])
def test_unused_toml_native_metadata_does_not_enter_runtime_dependencies(checkout, scoped):
    project, _, _ = checkout
    if scoped:
        assert run_until_prepared(project) == 0
    path = project / '.devcapsule/devcapsule.toml'
    path.write_text('review-date = 2026-09-20\n' + path.read_text())
    assert invoke(project, 'config', 'show') == 0


@pytest.mark.parametrize('fail', [False, True])
def test_private_atomic_replace_preserves_the_previous_file_on_failure(tmp_path, monkeypatch, fail):
    destination = tmp_path / 'record.toml'
    destination.write_text('previous')
    replace = Path.replace
    def observed_replace(source, target):
        assert stat.S_IMODE(source.stat().st_mode) == 0o600
        assert source.read_text() == 'next'
        assert destination.read_text() == 'previous'
        if fail:
            raise OSError('injected replacement failure')
        return replace(source, target)
    monkeypatch.setattr(Path, 'replace', observed_replace)
    if fail:
        with pytest.raises(OSError, match='replacement failure'):
            atomic_write(destination, 'next')
    else:
        atomic_write(destination, 'next')
    assert destination.read_text() == ('previous' if fail else 'next')
    assert list(tmp_path.iterdir()) == [destination]
