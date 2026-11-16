"""GitHub proxy process and socket integration; no GitHub account or network is used.

A fixture SSH executable stands in for the remote SSH service. Git itself and
its upload/receive services are real, as are the proxy, pipes and command line.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shlex
import socket
import struct
import subprocess
import sys
import tempfile
from collections.abc import Iterator

import pytest

from devcapsule.github_proxy import GitHubBroker, MAX_REQUEST, SOCKET_ENV

pytestmark = pytest.mark.integration
SOURCE = Path(__file__).resolve().parents[2]


def _environment(root: Path) -> dict[str, str]:
    return {'PATH': os.defpath, 'HOME': str(root), 'PYTHONPATH': str(SOURCE),
            'DEVCAPSULE_CONFIG_HOME': str(root / 'config'), 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 'Proxy test',
            'GIT_COMMITTER_NAME': 'Proxy test', 'GIT_AUTHOR_EMAIL': 'test@example.test',
            'GIT_COMMITTER_EMAIL': 'test@example.test', 'GIT_TERMINAL_PROMPT': '0'}


def _program(root: Path, body: str) -> Path:
    path = root / 'ssh-fixture'
    path.write_text(f'#!{sys.executable}\n' + body)
    path.chmod(0o700)
    return path


@contextmanager
def _broker(root: Path, body: str, **kwargs: float) -> Iterator[tuple[Path, dict[str, str]]]:
    env = _environment(root)
    # A short explicit socket path works under either Unix sockaddr path limit.
    with tempfile.TemporaryDirectory(prefix='gh-test-', dir='/tmp') as temporary:
        path = Path(temporary) / 's'
        with GitHubBroker(path, ssh=str(_program(root, body)), environment=env, **kwargs):
            yield path, env
        assert not path.exists()


def _client(path: Path, env: dict[str, str], payload: bytes = b'') -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, '-m', 'devcapsule', 'github-ssh', '--',
                           'git@github.com', "git-upload-pack 'acme/repo.git'"],
                          env={**env, SOCKET_ENV: str(path)}, input=payload,
                          capture_output=True, timeout=15)


def test_binary_streams_and_nonzero_exit_are_preserved(tmp_path: Path) -> None:
    """Large binary input, stdout, stderr and failure status survive the proxy without mixing."""
    payload = bytes(range(256)) * 2048
    program = "import sys\ndata = sys.stdin.buffer.read()\nsys.stdout.buffer.write(data)\nsys.stderr.buffer.write(b'diagnostic\\n')\nsys.exit(7)\n"
    with _broker(tmp_path, program) as (path, env):
        result = _client(path, env, payload)
    assert result.returncode == 7
    assert result.stdout == payload
    assert result.stderr == b'diagnostic\n'


def test_real_git_clone_fetch_and_push_through_capsule_adapter(tmp_path: Path) -> None:
    """Real Git clone, fetch and push transfer repository objects through the broker."""
    env = _environment(tmp_path)
    bare = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', '--initial-branch=main', str(bare)], env=env, check=True, capture_output=True)
    # This stand-in uses only the validated service; the repository is fixed by the fixture.
    program = f"import os, shlex, sys\nservice = shlex.split(sys.argv[-1])[0]\nos.execv('/usr/bin/git', ['git', service.removeprefix('git-'), {str(bare)!r}])\n"
    with _broker(tmp_path, program) as (path, _):
        git_env = {**env, SOCKET_ENV: str(path), 'GIT_SSH_VARIANT': 'ssh',
                   'GIT_SSH_COMMAND': shlex.join([sys.executable, '-m', 'devcapsule', 'github-ssh', '--'])}
        clone = tmp_path / 'clone'
        def git(*args: str) -> subprocess.CompletedProcess[bytes]:
            return subprocess.run(['git', *args], env=git_env, capture_output=True, check=True, timeout=20)
        git('-c', 'init.defaultBranch=main', 'clone', 'git@github.com:acme/repo.git', str(clone))
        (clone / 'binary').write_bytes(bytes(range(256)) * 1024)
        git('-C', str(clone), 'add', 'binary')
        git('-C', str(clone), 'commit', '-m', 'Fixture commit')
        git('-C', str(clone), 'push', 'origin', 'main')
        second = tmp_path / 'second'
        git('clone', 'ssh://git@github.com/acme/repo.git', str(second))
        git('-C', str(second), 'fetch', 'origin')
        assert (second / 'binary').read_bytes() == (clone / 'binary').read_bytes()
        assert git('--git-dir', str(bare), 'rev-parse', 'main').stdout == git('-C', str(clone), 'rev-parse', 'HEAD').stdout


@pytest.mark.parametrize('payload', [b'{"version":1,"service":"sh","repository":"acme/repo"}',
                                     b'{"version":1,"service":"git-upload-pack","repository":"a/b; id"}',
                                     b'{' ])
def test_invalid_requests_never_start_host_ssh(tmp_path: Path, payload: bytes) -> None:
    """Host admission refuses hostile wire bytes even when the capsule adapter is bypassed."""
    marker = tmp_path / 'started'
    with _broker(tmp_path, f"from pathlib import Path\nPath({str(marker)!r}).touch()\n") as (path, _):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(path))
            connection.sendall(struct.pack('!I', len(payload)) + payload)
            assert connection.recv(1) == b''
    assert not marker.exists()


def test_oversized_handshake_is_refused_without_reading_body(tmp_path: Path) -> None:
    """An excessive length prefix cannot allocate a body or spawn SSH."""
    with _broker(tmp_path, 'raise AssertionError("must not execute")\n') as (path, _):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(path))
            connection.sendall(struct.pack('!I', MAX_REQUEST + 1))
            assert connection.recv(1) == b''


def test_operation_deadline_stops_a_stalled_ssh_process(tmp_path: Path) -> None:
    """A stalled host SSH process is killed and the capsule receives failure within the bound."""
    with _broker(tmp_path, 'import time\ntime.sleep(60)\n', operation_timeout=0.2) as (path, env):
        result = _client(path, env)
    assert result.returncode != 0
    assert b'connection ended' in result.stderr


def test_broker_shutdown_closes_incomplete_requests(tmp_path: Path) -> None:
    """Stopping the launcher interrupts a client that never completed its handshake."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(2)
        with _broker(tmp_path, 'raise AssertionError("must not execute")\n') as (path, _):
            connection.connect(str(path))
            connection.sendall(b'\x00')
        try:
            assert connection.recv(1) == b''
        except ConnectionResetError:
            pass  # Closing with unread input may report reset instead of EOF.


@pytest.mark.parametrize('enabled', [False, True])
def test_launcher_exposes_the_socket_only_with_the_grant(tmp_path: Path, enabled: bool) -> None:
    """The Docker plan carries the Git adapter and broker mount only after explicit authorization."""
    from devcapsule.launch.pycharm._launcher import PycharmRunOptions, DockerMode, TempRuntimeFiles, build_run_config, build_docker_args
    from devcapsule.platforms import Platform
    from devcapsule.github_proxy import GIT_SSH_COMMAND, SOCKET_DESTINATION

    project = tmp_path / 'project'
    project.mkdir()
    with _broker(tmp_path, 'raise AssertionError("no transfer expected")\n') as (path, env):
        env = {**env, 'DISPLAY': ':1', 'PYCHARM_GIT_IDENTITY_FROM_HOST': '0', SOCKET_ENV: str(path)}
        config = build_run_config(PycharmRunOptions(project=project, capsule_platform=Platform.LINUX_AMD64,
                                  docker_mode=DockerMode.none, enable_sudo=False, network_mode='bridge',
                                  enable_github_ssh=enabled), env)
        files = TempRuntimeFiles(xauth_file=tmp_path / 'xauth', passwd_file=tmp_path / 'passwd', group_file=tmp_path / 'group')
        args = build_docker_args(config, files, env)
    assert (f'GIT_SSH_COMMAND={GIT_SSH_COMMAND}' in args) is enabled
    assert (f'{SOCKET_ENV}={SOCKET_DESTINATION}' in args) is enabled
    assert (f'type=bind,src={path},dst={SOCKET_DESTINATION},ro' in args) is enabled
    assert not any('.ssh' in arg or 'SSH_AUTH_SOCK=' in arg for arg in args)
