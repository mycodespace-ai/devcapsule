"""GitHub-only Git SSH requests: validate values before any host process starts.

The capsule selects a Git service and repository, never a host command or SSH
option. Host OpenSSH owns host verification and authentication, and key
selection too unless the launcher names one key (``devcapsule.ssh_identity``).
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shlex
from typing import Sequence

__all__ = ["GitHubRequest", "GitHubTransportError", "parse_git_ssh", "decode_request"]


class GitHubTransportError(ValueError):
    """A request cannot cross the authorized GitHub boundary."""


@dataclass(frozen=True)
class GitHubRequest:
    service: str
    repository: str

    def validate(self) -> None:
        """Require a GitHub repository and one of Git's two transfer services."""
        if self.service not in {"git-upload-pack", "git-receive-pack"}:
            raise GitHubTransportError("Only Git fetch and push services are allowed.")
        if (len(self.repository) > 256 or
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", self.repository) or
                self.repository.split("/")[-1] in {".", ".."}):
            raise GitHubTransportError("Expected a GitHub OWNER/REPOSITORY path.")

    def encode(self) -> bytes:
        """Serialize a validated request; no host paths or credentials cross."""
        self.validate()
        return json.dumps({"version": 1, "service": self.service,
                           "repository": self.repository}, separators=(",", ":")).encode()

    def ssh_command(self, executable: str, identity: Path | None) -> tuple[str, ...]:
        """Use host SSH configuration with noninteractive, verified authentication.

        ``identity`` is the one key file to offer, or None to let host OpenSSH
        choose. With a key, OpenSSH considers configured identities only.
        Host configuration may supply additional identities or certificates.
        The agent may hold a configured key
        unlocked; ``BatchMode`` asks for no passphrase.
        """
        self.validate()
        # -i takes the path as it is; -oIdentityFile= would split it at a space.
        # Suppress implicit default files even if the selected file disappeared after launch.
        selected = () if identity is None else ("-oIdentityFile=none", "-oIdentitiesOnly=yes", "-i", str(identity))
        return (executable, "-T", "-oBatchMode=yes", "-oStrictHostKeyChecking=yes",
                "-oClearAllForwardings=yes", "-oForwardAgent=no", "-oPermitLocalCommand=no",
                "-oControlMaster=no", "-oControlPath=none", "-oRemoteCommand=none",
                *selected, "git@github.com", f"{self.service} '{self.repository}'")


def decode_request(payload: bytes) -> GitHubRequest:
    """Validate the entire wire request, including field types and version."""
    try:
        value = json.loads(payload)
    except (ValueError, UnicodeError) as error:
        raise GitHubTransportError("Invalid GitHub request JSON.") from error
    if (not isinstance(value, dict) or set(value) != {"version", "service", "repository"} or
            type(value["version"]) is not int or value["version"] != 1 or
            not isinstance(value["service"], str) or not isinstance(value["repository"], str)):
        raise GitHubTransportError("Unsupported GitHub request.")
    request = GitHubRequest(value["service"], value["repository"])
    request.validate()
    return request


def parse_git_ssh(arguments: Sequence[str]) -> GitHubRequest | None:
    """Parse Git's OpenSSH invocation; other hosts use the capsule's own SSH.

    Git's protocol-v2 SendEnv request is accepted, but the broker deliberately
    negotiates protocol v0 rather than accepting arbitrary client environment.
    An explicit port is accepted only when it is GitHub's standard SSH port.
    Host SSH configuration can select ssh.github.com:443 as usual.
    """
    args = list(arguments)
    port: str | None = None
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option in {"-o", "-p"} and args:
            value = args.pop(0)
            if option == "-p":
                port = value
            elif value != "SendEnv=GIT_PROTOCOL":
                raise GitHubTransportError("Unsupported SSH option for the GitHub proxy.")
        elif option == "-oSendEnv=GIT_PROTOCOL":
            continue
        else:
            raise GitHubTransportError("Unsupported SSH option for the GitHub proxy.")
    if not args:
        raise GitHubTransportError("Missing SSH destination.")
    destination = args.pop(0)
    if destination not in {"github.com", "git@github.com"}:
        return None
    if port not in {None, "22"} or len(args) != 1:
        raise GitHubTransportError("Expected GitHub's SSH destination and one Git service.")
    try:
        command = shlex.split(args[0])
    except ValueError as error:
        raise GitHubTransportError("Malformed Git service command.") from error
    if len(command) != 2:
        raise GitHubTransportError("Expected a Git service and repository only.")
    request = GitHubRequest(command[0], command[1].removeprefix("/"))
    request.validate()
    return request
