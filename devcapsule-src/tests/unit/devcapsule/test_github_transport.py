"""Contracts of GitHub request admission, independent of host SSH or credentials."""
import json

import pytest

from devcapsule.github_transport import GitHubRequest, GitHubTransportError, decode_request, parse_git_ssh


@pytest.mark.parametrize('arguments,expected', [
    (['-o', 'SendEnv=GIT_PROTOCOL', 'git@github.com', "git-upload-pack 'acme/widgets.git'"],
     GitHubRequest('git-upload-pack', 'acme/widgets.git')),
    (['-oSendEnv=GIT_PROTOCOL', '-p', '22', 'github.com', "git-receive-pack '/acme/widgets'"],
     GitHubRequest('git-receive-pack', 'acme/widgets')),
])
def test_git_arguments_select_only_the_service_and_repository(arguments: list[str], expected: GitHubRequest) -> None:
    """Git's destination, standard port 22, and v2 request admit a GitHub transfer with no SSH option forwarding."""
    assert parse_git_ssh(arguments) == expected


@pytest.mark.parametrize('command', ["sh 'acme/repo'", "git-upload-pack 'acme/repo'; id", "git-upload-pack 'a/../b'",
                                     "git-upload-pack '-oProxyCommand=whoami'", "git-upload-pack 'acme/x\nwhoami'",
                                     "git-upload-pack 'acme/..'", "git-upload-pack 'acme/$(whoami)'",
                                     "git-upload-pack 'acme/repo", "git-upload-pack 'acme/repo' extra"])
def test_untrusted_git_commands_are_refused(command: str) -> None:
    """A capsule cannot select a shell command, traversal or option-shaped repository."""
    with pytest.raises(GitHubTransportError):
        parse_git_ssh(['git@github.com', command])


@pytest.mark.parametrize('arguments', [['-o', 'ProxyCommand=id', 'git@github.com', "git-upload-pack 'acme/repo'"],
                                     ['-p', '2222', 'git@github.com', "git-upload-pack 'acme/repo'"],
                                     ['-A', 'git@github.com'], []])
def test_capsule_ssh_options_cannot_change_host_execution(arguments: list[str]) -> None:
    """Unsupported options and destinations never become host SSH arguments."""
    with pytest.raises(GitHubTransportError):
        parse_git_ssh(arguments)


@pytest.mark.parametrize('arguments', [
    ['git@example.test', "git-upload-pack 'acme/repo'"],
    ['-p', '2222', 'git@example.test', "git-upload-pack 'acme/repo'"],
])
def test_other_git_hosts_are_not_forwarded_to_the_host(arguments: list[str]) -> None:
    """A different destination, including with a custom port, selects the capsule's ordinary SSH fallback."""
    assert parse_git_ssh(arguments) is None


@pytest.mark.parametrize('document', [{}, {'version': True, 'service': 'git-upload-pack', 'repository': 'a/b'},
                                      {'version': 1, 'service': ['git-upload-pack'], 'repository': 'a/b'},
                                      {'version': 1, 'service': 'git-upload-pack', 'repository': 'a/b', 'host': 'evil'},
                                      {'version': 1, 'service': 'sh', 'repository': 'a/b'},
                                      {'version': 1, 'service': 'git-upload-pack', 'repository': 'a/../b'}])
def test_wire_validation_does_not_trust_the_client_parser(document: object) -> None:
    """The host independently rejects malformed, extended and hostile requests."""
    with pytest.raises(GitHubTransportError):
        decode_request(json.dumps(document).encode())


def test_host_command_keeps_verification_and_disables_forwarding() -> None:
    """The host command preserves SSH identity selection but exposes no general SSH service."""
    command = GitHubRequest('git-upload-pack', 'acme/repo.git').ssh_command('/usr/bin/ssh')
    assert command[0] == '/usr/bin/ssh'
    assert command[-2:] == ('git@github.com', "git-upload-pack 'acme/repo.git'")
    assert '-oStrictHostKeyChecking=yes' in command
    assert '-oBatchMode=yes' in command
    assert '-oForwardAgent=no' in command
    assert '-oClearAllForwardings=yes' in command
    assert '-oPermitLocalCommand=no' in command
    assert '-oControlPath=none' in command


@pytest.mark.parametrize('payload', [
    b'{',
    b'\xff',
    b'[]',
    json.dumps({'version': 1, 'service': 'git-upload-pack', 'repository': 'a/' + 'b' * 255}).encode(),
])
def test_wire_validation_rejects_malformed_and_oversized_repository_payloads(payload: bytes) -> None:
    """Malformed JSON, non-object frames and overlong repository paths are refused on the wire."""
    with pytest.raises(GitHubTransportError):
        decode_request(payload)


def test_valid_wire_request_roundtrips() -> None:
    """Encoding a valid request carries exactly the service and repository contract."""
    request = GitHubRequest('git-receive-pack', 'acme/widgets.git')
    assert decode_request(request.encode()) == request
