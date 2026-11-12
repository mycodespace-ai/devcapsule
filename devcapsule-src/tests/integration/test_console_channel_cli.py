"""Integration tests of the console's configuration channel: real requests, answered by real ``config`` commands.

The launcher answers a request file by running ``devcapsule project config``
as a process of its own. So these tests run processes: the launcher's sweep
of a request directory, and the commands it starts, in an environment the
test builds. The home is named and lies under the test's directory, with
nothing accepted in it; the project is created there by ``project init``.

No command here needs Docker or the network.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from devcapsule.configuration.capabilities import LocalCapabilities
from devcapsule.configuration.console_channel import read_document, write_complete
from devcapsule.configuration.storage import load_toml

pytestmark = pytest.mark.integration

SWEEP = """
import sys
from pathlib import Path
from devcapsule.commands._console_channel import sweep
print(sweep(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
"""
"""The launcher's side of the channel, as a program: answer the requests in a directory and print how many."""


class Capsule:
    """One project with its home and its channel directory, and the processes that act on them."""

    def __init__(self, directory: Path) -> None:
        self.project = directory / "project"
        self.home = directory / "devcapsule-home"
        self.channel = directory / "channel"
        self.project.mkdir()
        self.channel.mkdir()
        self.environment = {
            "PATH": os.defpath, "HOME": str(directory / "home"), "DEVCAPSULE_CONFIG_HOME": str(self.home),
            "PYTHONDONTWRITEBYTECODE": "1",
        }

    def run(self, *command: str) -> subprocess.CompletedProcess[str]:
        """Start a Python program in the capsule's environment; standard error is joined to standard output."""
        return subprocess.run(
            [sys.executable, *command], cwd=self.project, env=self.environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300, check=False,
        )

    def config(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """``devcapsule project config ARGUMENTS`` for the project, as the developer would run it on the host."""
        return self.run("-m", "devcapsule", "project", "--path", str(self.project), "config", *arguments)

    @property
    def record(self) -> Path:
        """The checkout's record in the named home."""
        (found,) = self.home.rglob("devcapsule.checkout.toml")
        return found

    def selection(self) -> LocalCapabilities:
        """The capabilities the checkout's record selects, omits and chooses providers for."""
        return LocalCapabilities.read(load_toml(self.record))

    def send(self, identifier: str, *arguments: str) -> dict[str, Any]:
        """Put one request in the channel as the console writes it, let the launcher sweep, and return its result."""
        write_complete(self.channel / f"{identifier}.request.json",
                       {"format": 1, "requested": "2026-10-24T10:00:00+00:00", "arguments": list(arguments)})
        swept = self.run("-c", SWEEP, str(self.channel), str(self.project), str(self.record))
        assert swept.returncode == 0 and swept.stdout.strip() == "1", swept.stdout
        return read_document(self.channel / f"{identifier}.result.json")


@pytest.fixture
def capsule(tmp_path: Path) -> Capsule:
    """A project that requires Node and offers browser automation, registered in a home that has accepted nothing."""
    capsule = Capsule(tmp_path)
    created = capsule.run("-m", "devcapsule", "project", "--path", str(capsule.project), "init",
                          "--require", "node", "--creator", "mailto:owner@example.test")
    assert created.returncode == 0, created.stdout
    offered = capsule.config("offer", "browser-automation")
    assert offered.returncode == 0, offered.stdout
    return capsule


def test_capability_choices_sent_through_the_channel_are_recorded_on_the_checkout(capsule: Capsule) -> None:
    """Each capability choice the console sends is applied at once and reported as recorded: an agent added, an
    offered capability omitted and restored, an IDE selected, and a provider chosen for it. The record holds
    each choice after its request, and no request is kept for a confirmation."""
    assert capsule.send("000001-add", "add", "claude-code-agent")["status"] == "recorded"
    assert "claude-code-agent" in capsule.selection().selected
    assert capsule.send("000002-omit", "omit", "browser-automation")["status"] == "recorded"
    assert "browser-automation" in capsule.selection().without
    assert capsule.send("000003-restore", "restore", "browser-automation")["status"] == "recorded"
    assert "browser-automation" not in capsule.selection().without
    assert capsule.send("000004-ide", "ide", "frontend-ide")["status"] == "recorded"
    assert capsule.send("000005-use", "use", "frontend-ide", "vscode")["status"] == "recorded"
    assert capsule.selection().providers == {"frontend-ide": "vscode"}
    assert list(capsule.home.rglob("requests.json")) == []


@pytest.mark.parametrize(("capability", "component"), [("python-ide", "pycharm"), ("vscode-ide", "vscode")])
def test_a_choice_the_command_refuses_is_refused_through_the_channel_in_the_commands_words(
    capsule: Capsule, capability: str, component: str,
) -> None:
    """A provider choice for a capability with one provider, which ``config use`` refuses with exit 2, comes back
    through the channel as refused, with the text the command printed."""
    direct = capsule.config("use", capability, component)
    assert direct.returncode == 2 and "choice" in direct.stdout, direct.stdout

    refused = capsule.send("000001-use", "use", capability, component)

    assert refused["status"] == "refused"
    assert direct.stdout.strip() in refused["text"]


def test_choices_recorded_through_the_channel_leave_their_vendors_consents_pending(capsule: Capsule) -> None:
    """After the console adds the Claude Code agent and chooses Visual Studio Code, ``config show`` still lists
    both vendors' downloads as pending: the channel records a selection and accepts nothing for it."""
    assert capsule.send("000001-add", "add", "claude-code-agent")["status"] == "recorded"
    assert capsule.send("000002-ide", "ide", "frontend-ide")["status"] == "recorded"
    assert capsule.send("000003-use", "use", "frontend-ide", "vscode")["status"] == "recorded"

    shown = capsule.config("show", "--json")

    assert shown.returncode == 0, shown.stdout
    pending = {row["name"] for row in json.loads(shown.stdout)["rows"] if row["pending"]}
    assert {"claude-code-download", "vscode-download"} <= pending
