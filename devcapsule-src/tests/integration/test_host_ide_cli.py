"""Real CLI and entry-layer processes with private homes and fake code/Docker executables.
No test starts a container, downloads an editor, or uses a real graphical session.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import shlex
import tomllib
from zipfile import ZipFile

from devcapsule.build_info import build_info_json, current_build_info

import pytest

pytestmark = pytest.mark.integration


class Host:
    def __init__(self, root: Path):
        self.root = root
        self.project = root / 'project'
        self.project.mkdir()
        self.tools = root / 'tools'
        self.tools.mkdir()
        self.home = root / 'config'
        self.calls = root / 'calls.jsonl'
        self.environment = {
            'PATH': str(self.tools) + os.pathsep + os.defpath, 'HOME': str(root / 'home'),
            'DEVCAPSULE_CONFIG_HOME': str(self.home), 'CALLS': str(self.calls),
            'DOCKER_HOST': 'unix://' + str(root / 'fake-docker.sock'),
            'HTTP_PROXY': 'http://127.0.0.1:9', 'HTTPS_PROXY': 'http://127.0.0.1:9',
            'PYTHONDONTWRITEBYTECODE': '1',
        }
        self.program('code', '''
with open(os.environ['CALLS'], 'a') as f: f.write(json.dumps(['code', *sys.argv[1:]]) + '\\n')
if '--list-extensions' in sys.argv:
    print(os.environ.get('EXTENSIONS', ''))
if '--install-extension' in sys.argv:
    sys.exit(int(os.environ.get('INSTALL_STATUS', '0')))
''')
        self.program('docker', '''
args = sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f: f.write(json.dumps(['docker', *args]) + '\\n')
if args == ['info', '--format', '{{json .SecurityOptions}}']: print('[]')
elif args == ['version', '--format', '{{.Server.Arch}}']: print('amd64')
elif args == ['info', '--format', '{{.OperatingSystem}}']: print(os.environ.get('DAEMON_OS', 'Ubuntu'))
elif args[:2] == ['image', 'inspect']:
    if os.environ.get('IMAGE_IDENTITY'):
        entrypoint, cmd = [], []
        if args[-1].startswith('devcapsule-local-') and os.environ.get('CANONICAL_LABELS_FILE'):
            info = json.loads(Path(os.environ['CANONICAL_LABELS_FILE']).read_text())
            labels, entrypoint, cmd = info['labels'], info['entrypoint'], info['cmd']
        else:
            labels = {'devcapsule.image.managed': 'true', 'devcapsule.metadata.version': '1', 'devcapsule.image.kind': 'base'}
        print(json.dumps([{'Id': os.environ['IMAGE_IDENTITY'], 'Os': 'linux', 'Architecture': 'amd64',
                           'Size': 1, 'RepoTags': [args[-1]],
                           'Config': {'Labels': labels, 'Entrypoint': entrypoint, 'Cmd': cmd}}]))
        sys.exit(0)
    print('[]'); print('Error response from daemon: No such image: ' + args[-1], file=sys.stderr); sys.exit(1)
elif args[:2] == ['inspect', '-f']:
    print('true' if Path(os.environ['CALLS'] + '.running').exists() else 'false')
elif args[:1] == ['exec']:
    assert args[2:] == ['test', '-d', '/workspace/project'], args
    if os.environ.get('MOUNT_READY', '1') == '0': sys.exit(1)
elif args[:1] == ['run']:
    Path(os.environ['CALLS'] + '.running').touch()
    for _ in range(60):
        if '--folder-uri' in Path(os.environ['CALLS']).read_text(): break
        time.sleep(0.05)
    Path(os.environ['CALLS'] + '.running').unlink()
else:
    print('unexpected docker invocation: ' + repr(args), file=sys.stderr); sys.exit(97)
''')
        self.program('xauth', '''
if sys.argv[1] == 'nlist': print('0000 test-cookie')
else: Path(sys.argv[2]).write_text(sys.stdin.read())
''')

    def program(self, name: str, body: str) -> Path:
        program = self.tools / name
        program.write_text(f'#!{sys.executable}\nimport os, sys, json, time\nfrom pathlib import Path\n' + body)
        program.chmod(0o755)
        return program

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, '-m', 'devcapsule', 'project', '--path', str(self.project), *args],
                              env=self.environment, cwd=self.project, text=True, capture_output=True, timeout=60)

    def script(self, text: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, '-c', text], env=self.environment, cwd=self.project,
                              text=True, capture_output=True, timeout=30)

    def prepare(self, print_only: bool = False) -> subprocess.CompletedProcess[str]:
        return self.script(f'''
import os, json
from devcapsule.commands._host_ide import prepare_host_ide
from devcapsule.configuration.trust import HomeTrust
from devcapsule.platforms import XdgHomes
print(json.dumps(prepare_host_ide(XdgHomes.from_environment(), HomeTrust(), 'capsule', '/workspace/project',
                                 print_only={print_only!r}, environment=dict(os.environ))))
''')

    def recorded(self) -> list[list[str]]:
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def init(self, ide: str = 'vscode') -> None:
        result = self.cli('init', '--require', 'python', '--creator', 'mailto:test@example.test')
        assert result.returncode == 0, result.stdout + result.stderr
        chosen = self.cli("config", "ide", ide)
        assert chosen.returncode == 0, chosen.stdout + chosen.stderr
        approved = self.cli("config", "authorize", "base-image", "default")
        assert approved.returncode == 0, approved.stdout + approved.stderr


@pytest.fixture
def host(tmp_path: Path) -> Host:
    return Host(tmp_path)


def test_cli_host_ide_defaults_to_denied_and_can_be_authorized_then_denied(host: Host) -> None:
    """The real configuration commands expose the user-owned node and persist both grant and denial."""
    host.init()
    shown = host.cli('config', 'show', '--json')
    assert shown.returncode == 0, shown.stderr
    row = next(row for row in json.loads(shown.stdout)['rows'] if row['name'] == 'host-ide')
    assert row['effective'] == 'false'
    granted = host.cli('config', 'authorize', 'host-ide', 'true')
    assert granted.returncode == 0, granted.stderr
    denied = host.cli('config', 'deny', 'host-ide')
    assert denied.returncode == 0, denied.stderr
    shown = host.cli('config', 'show', '--json')
    row = next(row for row in json.loads(shown.stdout)['rows'] if row['name'] == 'host-ide')
    assert row['effective'] == 'false'


def test_run_once_host_ide_avoids_container_consent_and_preserves_project_files(host: Host) -> None:
    """Printing a split launch reaches image lookup without VS Code consent and writes no project or home choice."""
    host.init()
    before = {p: p.read_bytes() for root in (host.project, host.home) for p in root.rglob('*') if p.is_file()}
    result = host.cli('run', '--authorize', 'host-ide', 'true', '--print-command', '--no-update-check')
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'is not on this machine' in result.stderr
    assert 'trust vscode' not in result.stderr and 'vscode-download' not in result.stderr
    assert all(p.read_bytes() == content for p, content in before.items())
    assert not any(call[0] == 'code' for call in host.recorded())
    assert not (host.home / 'host-ide').exists()


def test_denying_host_ide_flag_does_not_bypass_software_approvals(host: Host) -> None:
    """Passing --authorize host-ide false retains container VS Code consent and gating."""
    host.init()
    result = host.cli('run', '--authorize', 'host-ide', 'false', '--no-update-check')
    assert result.returncode != 0
    assert 'trust vscode' in result.stderr
    assert 'is not on this machine' not in result.stderr


def test_print_command_generates_distinct_container_names_across_launches(host: Host) -> None:
    """Split launches without --name assign unique container names matching their attach URIs."""
    import hashlib
    from devcapsule.configuration.host_ide import runtime_lock as host_ide_runtime_lock
    from devcapsule.materialization import (
        CANONICAL_NAME_LABEL, IMAGE_KIND_LABEL, MANAGED_LABEL, MATERIALIZED_KIND, METADATA_VERSION,
        METADATA_VERSION_LABEL, canonical_image_name, canonical_json, formation_descriptor, formation_identity,
        parse_locked_environment,
    )
    from devcapsule.platforms import Platform
    from devcapsule.resolution_matrix import MATRICES

    host.init()
    composed_lock = tomllib.loads(
        MATRICES[Platform.LINUX_AMD64].resolve(['python', 'vscode-ide']).render_lock()
    )
    terminal_lock = host_ide_runtime_lock(composed_lock, MATRICES[Platform.LINUX_AMD64])
    locked = parse_locked_environment(terminal_lock)
    pex = host.root / 'runtime.pex'
    with ZipFile(pex, 'w') as archive:
        archive.writestr('pkg/devcapsule/_build_info.json', build_info_json(current_build_info()))
    base_identity = 'sha256:' + '0' * 64
    descriptor = formation_descriptor(
        platform=locked.platform,
        base_identity=base_identity,
        artifact=locked.artifact,
        ancillary_artifacts=locked.ancillary_artifacts,
        recipe_id=locked.recipe_id,
        recipe_version=locked.recipe_version,
        component_id=locked.component_id,
        runtime_sha256=hashlib.sha256(pex.read_bytes()).hexdigest(),
    )
    canonical_name = canonical_image_name(descriptor, locked.component_id)
    labels = {
        MANAGED_LABEL: 'true',
        METADATA_VERSION_LABEL: METADATA_VERSION,
        IMAGE_KIND_LABEL: MATERIALIZED_KIND,
        CANONICAL_NAME_LABEL: canonical_name,
        'devcapsule.materialization.identity': formation_identity(descriptor),
        'devcapsule.materialization.base-identity': base_identity,
        'devcapsule.pex.sha256': descriptor['runtime']['pex-sha256'],
        'devcapsule.materialization.recipe-version': descriptor['recipe']['version'],
        'devcapsule.component.id': locked.component_id,
        'devcapsule.component.version': locked.artifact.version,
        'devcapsule.component.sha256': locked.artifact.sha256,
        'devcapsule.materialization.descriptor': canonical_json(descriptor),
    }
    labels_file = host.root / 'canonical-labels.json'
    labels_file.write_text(json.dumps({
        'labels': labels,
        'entrypoint': descriptor['runtime']['entrypoint'],
        'cmd': descriptor['runtime']['command'],
    }))
    host.environment['DEVCAPSULE_RUNTIME_PEX'] = str(pex)
    host.environment['IMAGE_IDENTITY'] = base_identity
    host.environment['CANONICAL_LABELS_FILE'] = str(labels_file)
    host.environment['DISPLAY'] = ':99'
    names: list[str] = []
    for _ in range(2):
        result = host.cli(
            'run', '--authorize', 'host-ide', 'true', '--authorize', 'host-x11', 'true',
            '--print-command', '--no-update-check',
        )
        assert result.returncode == 0, result.stdout + result.stderr
        lines = [line for line in result.stdout.replace('\\\n', ' ').splitlines() if line.strip()]
        docker_tokens = next(shlex.split(line) for line in lines if '--name ' in line)
        code_tokens = next(shlex.split(line) for line in lines if '--folder-uri ' in line)
        name = docker_tokens[docker_tokens.index('--name') + 1]
        uri = code_tokens[code_tokens.index('--folder-uri') + 1]
        encoded = uri.removeprefix('vscode-remote://attached-container+').split('/', 1)[0]
        assert name.startswith('devcapsule-')
        assert json.loads(bytes.fromhex(encoded).decode('utf-8')) == {'containerName': '/' + name}
        names.append(name)
    assert names[0] != names[1]


def test_codium_is_refused_before_host_code_or_docker(host: Host) -> None:
    """A VSCodium selection fails loudly before editor provisioning or container work."""
    host.init('codium')
    result = host.cli('run', '--authorize', 'host-ide', 'true', '--no-update-check')
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'host-ide currently supports vscode only' in result.stderr
    assert host.recorded() == []


def test_profile_setup_installs_extension_in_isolated_home(host: Host) -> None:
    """The real code subprocess receives only the isolated profile, and a missing extension is installed before attach."""
    settings = host.home / 'host-ide/vscode/user-data/User/settings.json'
    settings.parent.mkdir(parents=True)
    settings.write_text('{"editor.fontSize": 19}')
    result = host.prepare()
    assert result.returncode == 0, result.stderr
    calls = host.recorded()
    assert [c[-1] for c in calls] == ['--list-extensions', 'ms-vscode-remote.remote-containers']
    assert all(f'--user-data-dir={settings.parents[1]}' in c for c in calls)
    assert all(f'--extensions-dir={host.home / "host-ide/vscode/extensions"}' in c for c in calls)
    assert settings.read_text() == '{"editor.fontSize": 19}'
    assert '--folder-uri' in json.loads(result.stdout)


def test_existing_extension_is_reused(host: Host) -> None:
    """An installed extension is listed but not reinstalled."""
    host.environment['EXTENSIONS'] = 'ms-vscode-remote.remote-containers'
    result = host.prepare()
    assert result.returncode == 0, result.stderr
    assert len(host.recorded()) == 1


def test_extension_install_failure_stops_preparation(host: Host) -> None:
    """Failed extension provisioning returns a clear failure before any container or attach command runs."""
    host.environment['INSTALL_STATUS'] = '7'
    result = host.prepare()
    assert result.returncode != 0 and 'Could not prepare host VS Code' in result.stderr
    assert not any(c[0] == 'docker' or '--folder-uri' in c for c in host.recorded())


def test_print_preparation_never_runs_code_or_creates_profile(host: Host) -> None:
    """Printing the attach command performs no install, profile write or code invocation."""
    result = host.prepare(print_only=True)
    assert result.returncode == 0, result.stderr
    assert '--folder-uri' in json.loads(result.stdout)
    assert host.recorded() == []
    assert not host.home.exists()


def test_missing_host_code_fails_with_trust_guidance_before_network(host: Host) -> None:
    """A missing CLI in an untrusted home fails with the acceptance command before attempting a download."""
    (host.tools / 'code').unlink()
    result = host.prepare()
    assert result.returncode != 0 and 'home trust accept vscode' in result.stderr
    assert not host.home.exists()


def test_wsl_missing_code_gives_windows_installation_guidance(host: Host) -> None:
    """A WSL process without code gets actionable Windows setup guidance without a Linux acquisition."""
    (host.tools / 'code').unlink()
    host.environment['WSL_DISTRO_NAME'] = 'TestDistro'
    result = host.prepare()
    assert result.returncode != 0 and 'Install VS Code on Windows' in result.stderr
    assert not host.home.exists()


@pytest.mark.parametrize(('daemon', 'expected'), [('Ubuntu', True), ('Docker Desktop', False)])
def test_wsl_settings_follow_the_real_daemon_query(host: Host, daemon: str, expected: bool) -> None:
    """The entry layer queries Docker and atomically records the matching WSL execution setting."""
    host.environment.update(WSL_DISTRO_NAME='TestDistro', DAEMON_OS=daemon)
    result = host.prepare()
    assert result.returncode == 0, result.stderr
    settings = json.loads((host.home / 'host-ide/vscode/user-data/User/settings.json').read_text())
    assert settings['dev.containers.executeInWSL'] is expected


def launch_script(transport: str, print_only: bool) -> str:
    return f'''
import os
from pathlib import Path
from devcapsule.commands._host_ide import prepare_host_ide
from devcapsule.configuration.trust import HomeTrust
from devcapsule.platforms import XdgHomes, Platform
from devcapsule.launch.pycharm import run_pycharm, PycharmRunOptions, DockerMode
from devcapsule.components.xfce_terminal import DEFINITION
from devcapsule.container_runtime.contract import RuntimePlan, Identity
from devcapsule.images.contract import WebConsoleAvailability
command = prepare_host_ide(XdgHomes.from_environment(), HomeTrust(), 'capsule', '/workspace/project',
                           print_only={print_only!r}, environment=dict(os.environ))
plan = RuntimePlan.for_component(DEFINITION.runtime_template(), project_path='/workspace/project',
                                 home='/home/devcapsule', identity=Identity(os.getuid(), os.getgid(), 'tester'))
raise SystemExit(run_pycharm(PycharmRunOptions(
    project=Path.cwd(), capsule_platform=Platform.LINUX_AMD64, image='test-environment', name='capsule',
    project_mount='/workspace/project', docker_mode=DockerMode.none, git_identity_from_host='0',
    runtime_plan=plan, use_image_process=True, display_transport={transport!r},
    web_console=WebConsoleAvailability(False, 'fixture'), host_ide_command=command,
    command_report=print if {print_only!r} else None, network_mode='bridge',
)))
'''


@pytest.mark.parametrize('transport', ['contained', 'host-x11'])
def test_attach_waits_for_container_and_mount_on_both_transports(host: Host, transport: str) -> None:
    """Real watcher threads attach after Docker reports a running container and project directory on either display transport."""
    host.environment['DISPLAY'] = ':test'
    result = host.script(launch_script(transport, False))
    assert result.returncode == 0, result.stdout + result.stderr
    calls = host.recorded()
    attached = next(i for i, call in enumerate(calls) if '--folder-uri' in call)
    assert any(call[:2] == ['docker', 'run'] for call in calls[:attached])
    assert ['docker', 'exec', 'capsule', 'test', '-d', '/workspace/project'] in calls[:attached]
    assert any('--install-extension' in call for call in calls[:attached])


def test_headless_attach_prints_the_command_without_starting_an_editor(host: Host) -> None:
    """A ready container on headless Linux keeps running and announces the exact attach command."""
    result = host.script(launch_script('contained', False))
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'no host display' in result.stderr and 'vscode-remote://attached-container+' in result.stderr
    assert not any('--folder-uri' in call for call in host.recorded())


def test_launcher_prints_both_commands_without_provisioning_or_launch(host: Host) -> None:
    """Print mode produces Docker and host attach commands but starts neither subprocess."""
    result = host.script(launch_script('contained', True))
    assert result.returncode == 0, result.stdout + result.stderr
    tokens = shlex.split(result.stdout.replace(chr(92) + chr(10), ""))
    assert any(tokens[i:i + 2] == ['docker', 'run'] for i in range(len(tokens)))
    assert ' --folder-uri vscode-remote://' in result.stdout
    assert not any(call[0] == 'code' or call[:2] == ['docker', 'run'] for call in host.recorded())


def test_no_attach_when_the_project_mount_never_becomes_ready(host: Host) -> None:
    """The watcher stops with the container and never opens a host window for an absent project directory."""
    host.environment.update(DISPLAY=':test', MOUNT_READY='0')
    result = host.script(launch_script('contained', False))
    assert result.returncode == 0, result.stdout + result.stderr
    assert not any('--folder-uri' in call for call in host.recorded())


@pytest.fixture
def vendor_proxy(tmp_path: Path):
    """A local TLS vendor stand-in reached through urllib's ordinary HTTPS proxy and CA settings."""
    import hashlib
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import io
    import ssl
    import tarfile
    from threading import Thread

    certificate = tmp_path / 'vendor.pem'
    key = tmp_path / 'vendor.key'
    generated = subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
        '-keyout', str(key), '-out', str(certificate), '-subj', '/CN=update.code.visualstudio.com',
        '-addext', 'subjectAltName=DNS:update.code.visualstudio.com,DNS:vscode.download.prss.microsoft.com',
    ], capture_output=True, text=True, timeout=30)
    assert generated.returncode == 0, generated.stderr
    body = (f'#!{sys.executable}\nimport json, os, sys\n'
            "with open(os.environ['CALLS'], 'a') as f: f.write(json.dumps(['code', *sys.argv[1:]]) + '\\n')\n"
            "if '--list-extensions' in sys.argv: print('ms-vscode-remote.remote-containers')\n").encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        member = tarfile.TarInfo('VSCode-linux-x64/bin/code')
        member.size, member.mode = len(body), 0o755
        archive.addfile(member, io.BytesIO(body))
    payload = buffer.getvalue()
    metadata = {'productVersion': '1.2.3', 'url': 'https://vscode.download.prss.microsoft.com/code.tar.gz',
                'sha256hash': hashlib.sha256(payload).hexdigest()}
    requests: list[str] = []
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(certificate, key)

    class Vendor(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_CONNECT(self):
            self.send_response(200)
            self.end_headers()
            with tls.wrap_socket(self.connection, server_side=True) as connection:
                stream = connection.makefile('rb')
                line = stream.readline().decode()
                path = line.split()[1]
                requests.append(path)
                while stream.readline().strip():
                    pass
                data = json.dumps(metadata).encode() if path.startswith('/api/update/') else payload
                connection.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(data)).encode()
                                   + b'\r\nConnection: close\r\n\r\n' + data)
                stream.close()
            self.close_connection = True

    server = ThreadingHTTPServer(('127.0.0.1', 0), Vendor)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {'HTTPS_PROXY': f'http://127.0.0.1:{server.server_port}', 'SSL_CERT_FILE': str(certificate)}, metadata, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def trusted_acquisition(host: Host) -> subprocess.CompletedProcess[str]:
    """Start the real acquisition entry point with explicit home trust, using only the test's HTTPS service."""
    return host.script('''
import os, json
from devcapsule.commands._host_ide import prepare_host_ide
from devcapsule.configuration.trust import HomeTrust
from devcapsule.host_ide import vscode_channel
from devcapsule.platforms import XdgHomes
trust = HomeTrust().with_channel(vscode_channel())
print(json.dumps(prepare_host_ide(XdgHomes.from_environment(), trust, 'capsule', '/workspace/project',
                                 print_only=False, environment=dict(os.environ))))
''')


def test_acquisition_verifies_unpacks_and_reuses_managed_code(host: Host, vendor_proxy) -> None:
    """The entry point downloads verified bytes over HTTPS, publishes a complete installation and reuses it offline."""
    environment, _metadata, requests = vendor_proxy
    (host.tools / 'code').unlink()
    host.environment.update(environment)
    result = trusted_acquisition(host)
    assert result.returncode == 0, result.stdout + result.stderr
    installed = host.home / 'data/host-ide/vscode/1.2.3/bin/code'
    assert installed.is_file() and os.access(installed, os.X_OK)
    assert len(requests) == 2
    assert json.loads(result.stdout)[0] == str(installed)
    host.environment['HTTPS_PROXY'] = 'http://127.0.0.1:9'
    reused = host.prepare()
    assert reused.returncode == 0, reused.stderr
    assert json.loads(reused.stdout)[0] == str(installed)
    assert not list((host.home / 'data/host-ide/vscode').glob('.unpack-*'))


def test_bad_archive_digest_never_publishes_an_installation(host: Host, vendor_proxy) -> None:
    """A checksum mismatch fails before extraction, code execution or publication of a version directory."""
    environment, metadata, requests = vendor_proxy
    metadata['sha256hash'] = '0' * 64
    (host.tools / 'code').unlink()
    host.environment.update(environment)
    result = trusted_acquisition(host)
    assert result.returncode != 0 and 'SHA-256 mismatch' in result.stderr
    assert len(requests) == 2
    assert not (host.home / 'data/host-ide/vscode/1.2.3').exists()
    assert not list((host.home / 'cache/host-ide/vscode').glob('.download-*'))
    assert host.recorded() == []
