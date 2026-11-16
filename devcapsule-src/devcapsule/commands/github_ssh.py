"""Git's capsule-side SSH adapter for the authorized launcher proxy."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from devcapsule.commands.framework import Command
from devcapsule.compat import CliError
from devcapsule.github_transport import GitHubTransportError, parse_git_ssh
from devcapsule.github_proxy import SOCKET_ENV, relay_git


class GitHubSshCommand(Command):
    name = "github-ssh"
    hidden = True
    help = "Git SSH transport through the authorized host GitHub proxy."
    passthrough_dest = "ssh_arguments"

    @classmethod
    def run(cls, arguments: argparse.Namespace, context: object | None) -> int:
        try:
            request = parse_git_ssh(arguments.ssh_arguments)
            if request is None:
                return subprocess.run(["ssh", *arguments.ssh_arguments], check=False).returncode
            path = os.environ.get(SOCKET_ENV)
            if not path:
                raise GitHubTransportError("No authorized GitHub proxy. Enable github-ssh on the host launcher.")
            return relay_git(Path(path), request, stdin=sys.stdin.buffer,
                             stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)
        except (OSError, GitHubTransportError) as error:
            raise CliError(f"GitHub proxy: {error} Host keys must be trusted and encrypted keys unlocked on the host.") from error


COMMAND = GitHubSshCommand
