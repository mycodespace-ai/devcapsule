"""Host IDE plans depend only on supplied observations and documents."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from devcapsule.compat import CliError
from devcapsule.configuration.trust import HomeTrust
from devcapsule.host_ide import (
    EXTENSION, HostIdeInputs, acquisition_plan, attach_command, headless, merge_settings,
    needs_extension, profile, readiness_commands, release_archive, required_settings, vscode_channel,
)
from devcapsule.platforms import HostOs, XdgHomes


def inputs() -> HostIdeInputs:
    """All paths and host facts are synthetic, with no host discovery."""
    homes = XdgHomes(Path('/test/config'), Path('/test/data'), Path('/test/state'), Path('/test/cache'))
    return HostIdeInputs(homes, HostOs.LINUX, 'amd64', False, None, (), HomeTrust())


def test_path_code_wins_without_trust() -> None:
    """An installed PATH CLI takes precedence over a managed copy and needs no download consent."""
    plan = acquisition_plan(replace(inputs(), path_code='/bin/code', installed=(Path('/managed/code'),)), print_only=False)
    assert plan.code == '/bin/code' and plan.metadata_url is None


def test_managed_code_is_reused_without_trust() -> None:
    """An already unpacked managed CLI is reused when PATH has none."""
    plan = acquisition_plan(replace(inputs(), installed=(Path('/managed/code'),)), print_only=False)
    assert plan.code == '/managed/code' and plan.metadata_url is None


def test_missing_code_requires_home_trust() -> None:
    """No download is planned when this home has not accepted Microsoft's terms and channel."""
    with pytest.raises(CliError, match='home trust accept vscode'):
        acquisition_plan(inputs(), print_only=False)


@pytest.mark.parametrize(('host_os', 'arch', 'target'), [
    (HostOs.LINUX, 'amd64', 'linux-x64'), (HostOs.LINUX, 'arm64', 'linux-arm64'),
    (HostOs.DARWIN, 'amd64', 'darwin'), (HostOs.DARWIN, 'arm64', 'darwin-arm64'),
])
def test_trusted_acquisition_uses_the_host_platform(host_os: HostOs, arch: str, target: str) -> None:
    """Each supported host gets its own stable-update endpoint, independent of the capsule platform."""
    trust = HomeTrust().with_channel(vscode_channel(), accepted_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    plan = acquisition_plan(replace(inputs(), os=host_os, architecture=arch, trust=trust), print_only=False)
    assert plan.metadata_url == f'https://update.code.visualstudio.com/api/update/{target}/stable/latest'
    assert plan.code is None


def test_print_only_plans_a_command_without_download_or_trust() -> None:
    """Printing names code without requiring a network lookup or accepting a channel."""
    plan = acquisition_plan(inputs(), print_only=True)
    assert plan.code == 'code' and plan.metadata_url is None


def test_wsl_without_windows_code_fails_even_with_a_managed_linux_copy() -> None:
    """WSL must use Windows Code on PATH and never download or reuse a Linux desktop."""
    with pytest.raises(CliError, match='Windows VS Code'):
        acquisition_plan(replace(inputs(), wsl=True, installed=(Path('/managed/code'),)), print_only=False)


@pytest.mark.parametrize('changes', [
    {'url': 'http://download.example.test/code'}, {'url': 'https://user@download.example.test/code'},
    {'sha256hash': 'not-a-digest'}, {'productVersion': '../../escape'},
])
def test_invalid_release_metadata_is_refused(changes: dict) -> None:
    """Unsafe URLs, missing digests and path-escaping versions cannot become an acquisition plan."""
    document = {'url': 'https://download.example.test/code', 'sha256hash': 'ab' * 32, 'productVersion': '1.2.3'}
    with pytest.raises(CliError):
        release_archive({**document, **changes})


def test_profile_uses_only_the_given_config_home() -> None:
    """VS Code user data and extensions occupy separate directories in the given DevCapsule config home."""
    config = profile(inputs().homes)
    assert config.user_data == inputs().homes.config / 'host-ide/vscode/user-data'
    assert config.extensions == inputs().homes.config / 'host-ide/vscode/extensions'


def test_attach_command_encodes_container_identity_and_mount() -> None:
    """The attach URI names the supplied container and mount with an isolated new window."""
    config = profile(inputs().homes)
    command = attach_command('/bin/code', config, 'capsule-ü', '/workspace/my project')
    uri = command[-1]
    encoded, path = uri.removeprefix('vscode-remote://attached-container+').split('/', 1)
    assert json.loads(bytes.fromhex(encoded)) == {'containerName': '/capsule-ü'}
    assert path == 'workspace/my%20project'
    assert command[:-1] == (*config.command('/bin/code'), '--new-window', '--folder-uri')


@pytest.mark.parametrize(('wsl', 'docker_os', 'expected'), [
    (True, 'Ubuntu', {'dev.containers.executeInWSL': True}),
    (True, 'Docker Desktop', {'dev.containers.executeInWSL': False}), (False, 'Ubuntu', {}),
])
def test_wsl_execution_tracks_the_daemon(wsl: bool, docker_os: str, expected: dict) -> None:
    """Only a WSL distro daemon needs Docker commands executed inside WSL."""
    assert required_settings(wsl=wsl, docker_operating_system=docker_os) == expected


def test_settings_merge_retains_user_values() -> None:
    """Required settings change without losing unrelated user settings, including JSONC values."""
    text = '{// user preference\n"editor.fontSize": 19,"url":"https://example.test",}'
    merged = merge_settings(text, {'dev.containers.executeInWSL': True})
    assert json.loads(merged) == {'editor.fontSize': 19, 'url': 'https://example.test', 'dev.containers.executeInWSL': True}


def test_settings_without_changes_keep_their_bytes() -> None:
    """A profile with no required changes retains its formatting and comments."""
    text = '{ /* personal */ "editor.fontSize": 19, }'
    assert merge_settings(text, {}) == text


def test_invalid_settings_are_not_replaced() -> None:
    """Invalid user settings produce an error rather than an empty replacement document."""
    with pytest.raises(CliError, match='left unchanged'):
        merge_settings('{broken', {})


@pytest.mark.parametrize(('extensions', 'expected'), [('', True), (EXTENSION.upper() + '\nother.extension\n', False)])
def test_extension_check_is_case_insensitive(extensions: str, expected: bool) -> None:
    """An installed Dev Containers extension is reused; an absent one needs installation."""
    assert needs_extension(extensions) is expected


@pytest.mark.parametrize(('host_os', 'env', 'wsl', 'expected'), [
    (HostOs.LINUX, {}, False, True), (HostOs.LINUX, {'DISPLAY': ':1'}, False, False),
    (HostOs.LINUX, {'WAYLAND_DISPLAY': 'wayland-0'}, False, False),
    (HostOs.LINUX, {}, True, False), (HostOs.DARWIN, {}, False, False),
])
def test_headless_detection_respects_native_and_windows_desktops(host_os: HostOs, env: dict, wsl: bool, expected: bool) -> None:
    """Only Linux without a desktop or WSL's Windows desktop needs a printed attach command."""
    assert headless(host_os, env, wsl=wsl) is expected


def test_readiness_requires_running_container_and_project_mount() -> None:
    """Readiness uses Docker identity and the project directory, never the display transport."""
    assert readiness_commands('capsule', '/workspace/project') == (
        ('docker', 'inspect', '-f', '{{.State.Running}}', 'capsule'),
        ('docker', 'exec', 'capsule', 'test', '-d', '/workspace/project'),
    )
