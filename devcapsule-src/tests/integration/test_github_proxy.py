"""GitHub proxy process and socket integration; no GitHub account or network is used.

A fixture SSH executable stands in for the remote SSH service. Git itself and
its upload/receive services are real, as are the proxy, pipes and command line.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import selectors
import shlex
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from typing import IO

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
    git_bin = shutil.which('git')
    assert git_bin is not None
    subprocess.run([git_bin, 'init', '--bare', '--initial-branch=main', str(bare)], env=env, check=True, capture_output=True)
    # This stand-in uses only the validated service; the repository is fixed by the fixture.
    program = f"import os, shlex, sys\nservice = shlex.split(sys.argv[-1])[0]\nos.execv({git_bin!r}, ['git', service.removeprefix('git-'), {str(bare)!r}])\n"
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


def _process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # An orphaned grandchild cannot be waitpid'd by the broker and stays a
    # zombie until PID 1 reaps it; treat 'Z' as terminated, not running.
    try:
        status = Path(f'/proc/{pid}/status').read_text(encoding='utf-8')
    except OSError:
        return False
    for line in status.splitlines():
        if line.startswith('State:') and line.split(':', 1)[1].lstrip().startswith('Z'):
            return False
    return True


def _wait_pids_stopped(pids: list[int], timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    remaining = list(pids)
    while remaining and time.monotonic() < deadline:
        remaining = [pid for pid in remaining if _process_running(pid)]
        if remaining:
            time.sleep(0.02)
    assert not remaining, f"Processes still running after cleanup: {remaining}"


def _read_ready_line(stream: IO[bytes], expected: bytes, timeout: float = 5.0) -> None:
    fd = stream.fileno()
    received = bytearray()
    deadline = time.monotonic() + timeout
    with selectors.DefaultSelector() as selector:
        selector.register(fd, selectors.EVENT_READ)
        while len(received) < len(expected):
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError(
                    f"Timed out waiting {timeout}s for ready signal {expected!r}; received {bytes(received)!r}"
                )
            chunk = os.read(fd, len(expected) - len(received))
            if not chunk:
                break
            received.extend(chunk)
    assert bytes(received) == expected


def test_operation_deadline_stops_a_stalled_ssh_process(tmp_path: Path) -> None:
    """A stalled host SSH process and its descendant are terminated within the deadline (assumes fixture startup completes within 0.5s)."""
    pid_file = tmp_path / 'pids'
    program = (
        "import os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "grandchild = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"Path({str(pid_file)!r}).write_text(f'{{os.getpid()}}\\n{{grandchild.pid}}\\n')\n"
        "time.sleep(60)\n"
    )
    with _broker(tmp_path, program, operation_timeout=0.5) as (path, env):
        result = _client(path, env)
    assert result.returncode != 0
    assert b'connection ended' in result.stderr
    assert pid_file.exists(), "Fixture did not finish recording PIDs before the 0.5s operation deadline."
    pids = [int(line) for line in pid_file.read_text().splitlines() if line]
    assert len(pids) == 2
    _wait_pids_stopped(pids)


def test_broker_shutdown_cancels_active_ssh_process_group(tmp_path: Path) -> None:
    """Closing the broker terminates an active host SSH transfer so no process in its group remains running."""
    started = tmp_path / 'started'
    program = (
        "import os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "grandchild = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"Path({str(started)!r}).write_text(f'{{os.getpid()}}\\n{{grandchild.pid}}\\n')\n"
        "sys.stdout.buffer.write(b'ready\\n')\n"
        "sys.stdout.buffer.flush()\n"
        "time.sleep(60)\n"
    )
    client: subprocess.Popen[bytes] | None = None
    try:
        with _broker(tmp_path, program, operation_timeout=30) as (path, env):
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            client = subprocess.Popen(
                [sys.executable, '-m', 'devcapsule', 'github-ssh', '--',
                 'git@github.com', "git-upload-pack 'acme/repo.git'"],
                env={**env, SOCKET_ENV: str(path)},
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            assert client.stdout is not None
            _read_ready_line(client.stdout, b'ready\n', timeout=5.0)
        returncode = client.wait(timeout=5)
        client.communicate(timeout=5)
        assert returncode != 0
    finally:
        if client is not None:
            if client.poll() is None:
                client.kill()
                client.communicate(timeout=5)
            for pipe in (client.stdin, client.stdout, client.stderr):
                if pipe is not None and not pipe.closed:
                    pipe.close()
    pids = [int(line) for line in started.read_text().splitlines() if line]
    assert len(pids) == 2
    _wait_pids_stopped(pids)


def test_capsule_adapter_refuses_when_proxy_is_not_authorized(tmp_path: Path) -> None:
    """Without an authorized proxy socket in the environment, GitHub SSH fails rather than running SSH."""
    result = subprocess.run(
        [sys.executable, '-m', 'devcapsule', 'github-ssh', '--',
         'git@github.com', "git-upload-pack 'acme/repo.git'"],
        env=_environment(tmp_path),
        input=b'', capture_output=True, timeout=15,
    )
    assert result.returncode != 0
    assert b'No authorized GitHub proxy' in result.stderr


def test_capsule_adapter_falls_back_to_capsule_ssh_for_other_hosts(tmp_path: Path) -> None:
    """Non-GitHub destinations execute the capsule's own ssh binary without touching the proxy."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    ssh_stub = bin_dir / 'ssh'
    args_file = tmp_path / 'ssh_args'
    ssh_stub.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        f"Path({str(args_file)!r}).write_text(json.dumps(sys.argv[1:]))\n"
        "sys.exit(4)\n"
    )
    ssh_stub.chmod(0o700)
    env = _environment(tmp_path)
    env['PATH'] = f"{bin_dir}:{env['PATH']}"
    result = subprocess.run(
        [sys.executable, '-m', 'devcapsule', 'github-ssh', '--',
         '-p', '2222', 'git@example.test', "git-upload-pack 'acme/repo.git'"],
        env=env, input=b'', capture_output=True, timeout=15,
    )
    assert result.returncode == 4
    assert args_file.read_text() == '["-p", "2222", "git@example.test", "git-upload-pack \'acme/repo.git\'"]'


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
@pytest.mark.parametrize('rootless', [False, True])
def test_launcher_exposes_the_socket_only_with_the_grant(tmp_path: Path, enabled: bool, rootless: bool) -> None:
    """Rootless and rootful plans carry the adapter/socket only with authorization and use the corresponding identity."""
    from devcapsule.launch.pycharm._launcher import PycharmRunOptions, DockerMode, TempRuntimeFiles, build_run_config, build_docker_args
    from devcapsule.platforms import Platform
    from devcapsule.github_proxy import GIT_SSH_COMMAND, SOCKET_DESTINATION

    project = tmp_path / 'project'
    project.mkdir()
    with _broker(tmp_path, 'raise AssertionError("no transfer expected")\n') as (path, env):
        env = {**env, 'DISPLAY': ':1', 'PYCHARM_GIT_IDENTITY_FROM_HOST': '0', SOCKET_ENV: str(path)}
        config = build_run_config(PycharmRunOptions(project=project, capsule_platform=Platform.LINUX_AMD64,
                                  docker_mode=DockerMode.none, enable_sudo=False, network_mode='bridge',
                                  enable_github_ssh=enabled, rootless_docker=rootless), env)
        files = TempRuntimeFiles(xauth_file=tmp_path / 'xauth', passwd_file=tmp_path / 'passwd', group_file=tmp_path / 'group')
        args = build_docker_args(config, files, env)
    assert (f'GIT_SSH_COMMAND={GIT_SSH_COMMAND}' in args) is enabled
    assert (f'{SOCKET_ENV}={SOCKET_DESTINATION}' in args) is enabled
    assert (f'type=bind,src={path},dst={SOCKET_DESTINATION},ro' in args) is enabled
    assert args[args.index('--user') + 1] == ('0:0' if rootless else f'{os.getuid()}:{os.getgid()}')
    assert not any('.ssh' in arg or 'SSH_AUTH_SOCK=' in arg for arg in args)


def test_launcher_rejects_environment_conflicts_with_github_ssh(tmp_path: Path) -> None:
    """Additional environment cannot override GitHub SSH transport variables when enabled."""
    from devcapsule.launch.pycharm._launcher import PycharmRunError, PycharmRunOptions, DockerMode, build_run_config
    from devcapsule.platforms import Platform

    project = tmp_path / 'project'
    project.mkdir()
    with _broker(tmp_path, 'raise AssertionError("no transfer expected")\n') as (path, env):
        env = {**env, 'DISPLAY': ':1', 'PYCHARM_GIT_IDENTITY_FROM_HOST': '0', SOCKET_ENV: str(path)}
        with pytest.raises(PycharmRunError, match="GitHub SSH"):
            build_run_config(
                PycharmRunOptions(
                    project=project, capsule_platform=Platform.LINUX_AMD64,
                    docker_mode=DockerMode.none, enable_sudo=False, network_mode='bridge',
                    enable_github_ssh=True, additional_environment={'GIT_SSH_COMMAND': 'ssh'},
                ),
                env,
            )
