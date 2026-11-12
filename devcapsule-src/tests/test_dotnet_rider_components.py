"""SDK resolution, archive safety, and Rider's independent runtime contract."""
from copy import deepcopy
import io
from pathlib import Path
import tarfile
import tomllib

import pytest

from devcapsule.compat import CliError
from devcapsule.components import discovery
from devcapsule.components.directory_artifacts import extract_tar_directory
from devcapsule.components.dotnet_sdk import DEFINITION as SDK
from devcapsule.components.rider import DEFINITION as RIDER
from devcapsule.materialization import parse_locked_environment, _ancillary_contributions, _prepare_locked_artifact
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy


def lock(needs):
    return tomllib.loads(MATRICES[Platform.LINUX_AMD64].resolve(needs).render_lock())


def test_rider_requires_sdk_and_keeps_its_own_state():
    document = lock(['dotnet-ide'])
    environment = parse_locked_environment(document)
    assert environment.component_id == 'rider'
    assert [a.component_id for a in environment.ancillary_artifacts] == ['dotnet-sdk']
    assert lock(['dotnet-ide', 'dotnet'])['components'] == document['components']
    template = RIDER.runtime_template()
    assert template.component.configuration['launcher'] == 'bin/rider.sh'
    assert template.component.configuration['properties_environment_variable'] == 'RIDER_PROPERTIES'
    assert template.logical_slot_name('config') == 'rider/config'
    assert template.component.configuration['recover_stale_directory_lock'] is True
    del document['components']['dotnet-sdk']
    with pytest.raises(CliError, match='requires.*dotnet-sdk'):
        parse_locked_environment(document)


def test_sdk_is_additive_to_another_ide_and_installs_a_complete_directory(tmp_path):
    document = lock(['frontend-ide', 'dotnet'])
    environment = parse_locked_environment(document)
    assert environment.component_id == 'codium'
    artifact, = environment.ancillary_artifacts
    assert artifact.artifact_format == 'tar-gz-directory'
    archive = tmp_path / 'sdk.tar.gz'
    with tarfile.open(archive, 'w:gz') as package:
        for name in ['dotnet', 'sdk/10.0.401/MSBuild.dll', 'shared/Microsoft.NETCore.App/10.0.12/coreclr.so']:
            entry = tarfile.TarInfo(name); entry.size = 3; entry.mode = 0o6755
            package.addfile(entry, io.BytesIO(b'sdk'))
    root = _prepare_locked_artifact(archive, artifact, tmp_path / 'unpacked', cache_root=tmp_path / 'cache')
    assert root.is_relative_to(tmp_path / 'cache' / 'unpacked' / artifact.sha256)  # unpacked once, by digest
    assert (root / 'sdk/10.0.401/MSBuild.dll').read_bytes() == b'sdk'
    assert (root / 'dotnet').stat().st_mode & 0o7777 == 0o755
    contribution, = _ancillary_contributions(((root, artifact),), ())
    assert contribution.exports == ('/opt/dotnet',)
    assert ('PATH', '/opt/dotnet:${PATH}') in artifact.environment
    # PATH is expanded by Docker, never overwritten with a literal ${PATH} at runtime.
    assert 'PATH' not in SDK.runtime_template().component.environment
    assert SDK.runtime_template().persistence.state_slots == ()


@pytest.mark.parametrize('name,kind', [('../escape', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE),
    ('a\\b', tarfile.REGTYPE), ('link', tarfile.SYMTYPE), ('hard', tarfile.LNKTYPE), ('device', tarfile.CHRTYPE)])
def test_toolchain_tar_rejects_escape_links_and_special_files_before_writing(tmp_path, name, kind):
    archive = tmp_path / 'bad.tar.gz'
    with tarfile.open(archive, 'w:gz') as package:
        entry = tarfile.TarInfo(name); entry.type = kind; entry.linkname = '../outside'
        package.addfile(entry)
    with pytest.raises(CliError, match='Unsafe'):
        extract_tar_directory(archive, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


@pytest.mark.parametrize('field,value', [('platform', 'linux-arm64'), ('delivery-policy', 'base-image'),
                                        ('version', None), ('url', ''), ('sha256', 42)])
def test_sdk_rejects_malformed_lock_metadata(field, value):
    metadata = deepcopy(lock(['frontend-ide', 'dotnet'])['components']['dotnet-sdk'])
    metadata[field] = value
    with pytest.raises(CliError):
        SDK.locked_artifacts(metadata, 'linux-amd64')


def test_sdk_discovery_excludes_preview_and_eol_releases(monkeypatch):
    monkeypatch.setattr(discovery, 'read_json', lambda _: {'releases-index': [
        {'support-phase': 'go-live', 'latest-sdk': '11.0.100-rc.1'},
        {'support-phase': 'active', 'latest-sdk': '10.0.401'},
        {'support-phase': 'maintenance', 'latest-sdk': '9.0.318'},
        {'support-phase': 'eol', 'latest-sdk': '99.0.999'},
    ]})
    report = SDK.discovery_channel().check('10.0.100', 'linux-amd64')
    assert [v.version for v in report.candidates] == ['10.0.401']


def test_rider_discovery_uses_linux_release_with_checksum(monkeypatch):
    monkeypatch.setattr(discovery, 'read_json', lambda _: {'RD': [{'type': 'release', 'version': '2026.2.3.1',
        'downloads': {'linux': {'link': 'https://vendor/rider.tar.gz', 'checksumLink': 'https://vendor/checksum'}}}]})
    assert RIDER.discovery_channel().check('2026.2.3', 'linux-amd64').candidates[0].version == '2026.2.3.1'
