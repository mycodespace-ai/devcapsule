"""Exercise replacement console links and retired presentation paths through real processes."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def run_cli(root: Path, *arguments: str, capsule: bool = True, token: bytes | None = b'run-token\n', console_url: str = 'http://127.0.0.1:8787') -> subprocess.CompletedProcess[str]:
    environment = {'PATH': os.defpath, 'HOME': str(root / 'home'),
                   'DEVCAPSULE_CONFIG_HOME': str(root / 'config'), 'PYTHONDONTWRITEBYTECODE': '1'}
    if capsule:
        environment.update(PROJECT_PATH=str(root), DEVCAPSULE_CONTAINER_NAME='test-capsule',
                           DEVCAPSULE_CONSOLE_URL=console_url,
                           DEVCAPSULE_CONSOLE_TOKEN_FILE=str(root / 'token'))
    if token is not None:
        (root / 'token').write_bytes(token)
    return subprocess.run([sys.executable, '-m', 'devcapsule', *arguments], cwd=root,
                          env=environment, capture_output=True, text=True, timeout=120, check=False)


@pytest.mark.parametrize('name', ['document.md', 'movie.webm', 'My run #1'])
def test_paths_always_select_files(tmp_path: Path, name: str) -> None:
    """Existing Markdown, video and presentation paths all open Files without viewer inference."""
    target = tmp_path / name
    if name == 'My run #1':
        target.mkdir()
        (target / 'presentation.json').write_text('{}')
    else:
        target.write_bytes(b'content')
    result = run_cli(tmp_path, 'instance', '--get-link', name)
    assert result.returncode == 0, result.stderr
    expected = {'document.md': 'document.md', 'movie.webm': 'movie.webm', 'My run #1': 'My%20run%20%231'}[name]
    assert result.stdout.strip() == f'http://127.0.0.1:8787/files/{expected}?token=run-token'


@pytest.mark.parametrize('route', ['files', 'records', 'presentations'])
def test_current_console_urls_retain_the_viewer(tmp_path: Path, route: str) -> None:
    """Explicit current-console content URLs retain the viewer and replace an old query token."""
    (tmp_path / 'content').mkdir()
    result = run_cli(tmp_path, 'instance', '--get-link', f'http://127.0.0.1:8787/{route}/content?token=old#chapter')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f'http://127.0.0.1:8787/{route}/content?token=run-token#chapter'


@pytest.mark.parametrize('token', [None, b'\xff\xfe'])
def test_unreadable_token_uses_browser_session(tmp_path: Path, token: bytes | None) -> None:
    """Missing or undecodable tokens retain the existing browser-session fallback."""
    result = run_cli(tmp_path, 'instance', '--get-link', '.', token=token)
    assert result.returncode == 0, result.stderr
    assert 'no readable run token was found' in result.stdout
    assert result.stdout.splitlines()[-1] == 'http://127.0.0.1:8787/files'


@pytest.mark.parametrize('value', [
    'http://other.example/files', 'http://127.0.0.1:9999/files',
    'http://user@127.0.0.1:8787/files', '//other.example/files',
    'http://127.0.0.1:8787/files/%2e%2e/outside',
    'http://127.0.0.1:8787/unknown', '.hidden', '../', 'escape', 'missing',
])
def test_invalid_links_are_refused_without_printing_token(tmp_path: Path, value: str) -> None:
    """External origins, unsupported routes, hidden, missing and escaping paths yield no tokened link."""
    (tmp_path / '.hidden').write_text('secret')
    (tmp_path / 'escape').symlink_to(tmp_path.parent, target_is_directory=True)
    result = run_cli(tmp_path, 'instance', '--get-link', value)
    assert result.returncode == 2
    assert 'run-token' not in result.stdout + result.stderr
    assert result.stdout == ''


def test_help_works_outside_a_capsule(tmp_path: Path) -> None:
    """Instance help has no capsule requirement or filesystem effects."""
    result = run_cli(tmp_path, 'instance', '--help', capsule=False, token=None)
    assert result.returncode == 0, result.stderr
    assert '--get-link PATH-OR-URL' in result.stdout
    assert not list(tmp_path.iterdir())


def test_link_requires_current_capsule(tmp_path: Path) -> None:
    """A host invocation cannot select a console or obtain a run token through this adapter."""
    result = run_cli(tmp_path, 'instance', '--get-link', '.', capsule=False, token=None)
    assert result.returncode == 2
    assert 'inside the current capsule' in result.stderr


@pytest.mark.parametrize('operation', ['guide', 'export', 'install-skill', 'hand-off'])
def test_removed_presentation_commands_have_no_aliases(tmp_path: Path, operation: str) -> None:
    """Each removed public presentation path is rejected instead of retained as an alias."""
    result = run_cli(tmp_path, 'presentations', operation, capsule=False, token=None)
    assert result.returncode == 2
    assert "unknown command 'presentations'" in result.stderr
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('origin', ['', 'file:///tmp', 'http://localhost:invalid', 'http://user@localhost'])
def test_missing_or_invalid_console_origin_is_refused(tmp_path: Path, origin: str) -> None:
    """The adapter refuses unusable capsule origins without printing a token or inventing a URL."""
    result = run_cli(tmp_path, 'instance', '--get-link', '.', console_url=origin)
    assert result.returncode == 2
    assert result.stdout == ''
    assert 'run-token' not in result.stderr
