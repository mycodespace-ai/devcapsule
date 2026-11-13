"""Integration tests of the console's configuration channel: real requests, answered by real ``config`` commands.

The launcher answers a request file by running ``devcapsule project config``
as a process of its own. So these tests run processes: the launcher's sweep
of a request directory, the commands it starts, and ``project run`` on a
pseudo-terminal where the launch asks about a kept request.

What it takes for them to pass, and why the legacy file they replace,
``tests/test_console_channel.py``, passed under ``nox -s tests`` and failed
under ``.venv/bin/python -m pytest``:

- The interpreter that runs pytest must be able to import ``devcapsule``:
  every process here is ``sys.executable -m devcapsule`` or a ``-c`` program
  that imports it. Nothing else is needed of the interpreter.
- Every process gets an environment the test builds, with a named home,
  ``DEVCAPSULE_CONFIG_HOME``, under the test's directory. The launcher hands
  that variable on to the commands it starts.
- The legacy file named no home. Its ``config`` commands were processes too,
  and a process started inside a capsule with no named home and no settings
  of its own reads the launcher's settings, mounted at
  ``/etc/devcapsule/home``. Those settings carry ``minimum-devcapsule``, and
  the command compares it with the version of the ``devcapsule``
  distribution installed in its interpreter. ``nox -s tests`` installs the
  current version in its own environment, so the command went on. A
  checkout's ``.venv`` that was installed long ago and never reinstalled
  still says an old version, 0.2.15 in the case found, so every command was
  refused with "requires DevCapsule 0.3.0; this launcher is 0.2.15" and the
  tests saw ``refused`` where they expected ``recorded``. Outside a capsule
  there is no mounted home and the legacy file passed with either
  interpreter.
- No command needs the network. The launch tests put a stand-in where
  ``docker`` is, which answers that no image is local and refuses to pull,
  so a launch ends there, after its questions and its writes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pty
import select
import stat
import subprocess
import sys
import time
import tomllib
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

ANSWER_WHILE_STOPPING = """
import sys
from pathlib import Path
from devcapsule.commands._console_channel import handle_request
print(handle_request(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[1]), stopping=True)["status"])
"""
"""The launcher answering one request file while it stops, as a program: print the result's status."""

STAND_IN_DOCKER = """#!/bin/sh
# Stands where docker is. No image is local, and nothing else is done: a launch ends at its first pull.
if [ "$1 $2" = "image inspect" ]; then
    echo "[]"
    echo "Error response from daemon: No such image: $3" >&2
    exit 1
fi
echo "the stand-in for docker was asked to: $*" >&2
exit 97
"""

ASKED_AT = "2026-10-24T10:00:00+00:00"
KEPT_PROMPT = "Enter = keep it for later:"
"""The end of the question a launch puts for a request kept from the console."""


class Capsule:
    """One project with its home and its channel directory, and the processes that act on them."""

    def __init__(self, directory: Path) -> None:
        self.project = directory / "project"
        self.home = directory / "devcapsule-home"
        self.channel = directory / "channel"
        self.project.mkdir()
        self.channel.mkdir()
        tools = directory / "tools"
        tools.mkdir()
        docker = tools / "docker"
        docker.write_text(STAND_IN_DOCKER, encoding="utf-8")
        docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
        self.environment = {
            "PATH": f"{tools}{os.pathsep}{os.defpath}", "HOME": str(directory / "home"),
            "DEVCAPSULE_CONFIG_HOME": str(self.home), "PYTHONDONTWRITEBYTECODE": "1",
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

    def ask(self, identifier: str, *arguments: str) -> Path:
        """Put one request in the channel as the console writes it, asked at ``ASKED_AT``."""
        return write_complete(self.channel / f"{identifier}.request.json",
                              {"format": 1, "requested": ASKED_AT, "arguments": list(arguments)})

    def send(self, identifier: str, *arguments: str) -> dict[str, Any]:
        """Put one request in the channel, let the launcher sweep, and return its result."""
        self.ask(identifier, *arguments)
        swept = self.run("-c", SWEEP, str(self.channel), str(self.project), str(self.record))
        assert swept.returncode == 0 and swept.stdout.strip() == "1", swept.stdout
        return read_document(self.channel / f"{identifier}.result.json")

    def saved(self) -> dict[str, Any]:
        """The checkout's record as it is on disk."""
        return load_toml(self.record)

    def planned(self) -> dict[str, Any]:
        """The plan the last launch derived and wrote beside the record."""
        return tomllib.loads(self.record.with_name("devcapsule.resolved.toml").read_text(encoding="utf-8"))

    def kept(self) -> str:
        """What ``config console list`` prints: the requests that await the host's confirmation."""
        listed = self.config("console", "list")
        assert listed.returncode == 0, listed.stdout
        return listed.stdout

    def ready_to_launch(self) -> None:
        """Choose PyCharm and accept DevCapsule's channel for the home, so that a launch has nothing else to ask."""
        assert self.config("ide", "python-ide").returncode == 0
        accepted = self.run("-m", "devcapsule", "home", "trust", "accept", "devcapsule-base", "--yes")
        assert accepted.returncode == 0, accepted.stdout

    def launch_at_a_terminal(self, answers: list[tuple[str, str]], *flags: str) -> str:
        """``project run FLAGS`` on a pseudo-terminal; return all it showed.

        ``answers`` are the developer's, in order: each is typed when the
        terminal's output ends with the prompt paired with it. The launch
        ends where it would pull the base image, at the stand-in for Docker,
        with every question asked and every answer written.
        """
        terminal, launcher_side = pty.openpty()
        process = subprocess.Popen(
            [sys.executable, "-m", "devcapsule", "project", "--path", str(self.project), "run", "--no-update-check", *flags],
            cwd=self.project, env=self.environment, stdin=launcher_side, stdout=launcher_side, stderr=launcher_side,
            close_fds=True,
        )
        os.close(launcher_side)
        shown = b""
        waiting = list(answers)
        deadline = time.monotonic() + 300
        try:
            while time.monotonic() < deadline:
                readable, _, _ = select.select([terminal], [], [], 0.2)
                if readable:
                    try:
                        chunk = os.read(terminal, 4096)
                    except OSError:  # Linux reports the launcher's closed side as an error, not as an empty read.
                        break
                    if not chunk:
                        break
                    shown += chunk
                    if waiting and shown.rstrip().endswith(waiting[0][0].encode()):
                        os.write(terminal, waiting.pop(0)[1].encode())
                elif process.poll() is not None:
                    break
            process.wait(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
            os.close(terminal)
        text = shown.decode(errors="replace")
        assert not waiting, f"the launch never asked {waiting[0][0]!r}:\n{text}"
        assert "the stand-in for docker was asked to: image pull" in text, text
        return text


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


def test_a_widening_sent_through_the_channel_is_kept_and_shown_on_the_host_until_confirmed(capsule: Capsule) -> None:
    """A request to put the capsule on the host's network is not applied: its result is ``deferred`` and names
    the command that applies it, and the checkout's record has no answer for the network. On the host,
    ``config show`` lists the request with what it stands for, and ``config console list`` with when it was asked."""
    deferred = capsule.send("000001-authorize", "authorize", "network", "host")

    assert deferred["status"] == "deferred" and "config console apply 000001-authorize" in deferred["text"]
    assert "network" not in capsule.saved().get("authorization", {})
    shown = capsule.config("show")
    assert shown.returncode == 0, shown.stdout
    assert "000001-authorize" in shown.stdout and "confirm or discard: config authorize network host" in shown.stdout
    assert f"000001-authorize  asked {ASKED_AT}: config authorize network host" in capsule.kept()


def test_config_check_counts_a_kept_request_among_the_pending_decisions(capsule: Capsule) -> None:
    """A checkout with nothing pending passes ``config check`` with exit status 0. With one request kept from
    the console the same command exits 3."""
    capsule.ready_to_launch()
    settled = capsule.config("check")
    assert settled.returncode == 0, settled.stdout

    capsule.send("000001-authorize", "authorize", "network", "host")

    assert capsule.config("check").returncode == 3


def test_console_apply_runs_the_kept_request_as_its_command_and_forgets_it(capsule: Capsule) -> None:
    """``config console apply ID`` on the host runs the kept request: it prints the command's own output and
    that the request was applied and forgotten, the record then holds the answer, and nothing is kept."""
    capsule.send("000001-authorize", "authorize", "network", "host")

    applied = capsule.config("console", "apply", "000001-authorize")

    assert applied.returncode == 0, applied.stdout
    assert "Authorized network for this checkout: host" in applied.stdout and "Applied and forgot" in applied.stdout
    assert capsule.saved()["authorization"]["network"]["value"] == "host"
    assert "000001-authorize" not in capsule.kept()


def test_a_kept_request_that_its_command_refuses_stays_kept(capsule: Capsule) -> None:
    """A kept request for an authorization that does not exist is refused by the command when applied, with
    exit status 2, and still awaits on the host."""
    assert capsule.send("000001-authorize", "authorize", "quantum", "x")["status"] == "deferred"

    refused = capsule.config("console", "apply", "000001-authorize")

    assert refused.returncode == 2, refused.stdout
    assert "000001-authorize" in capsule.kept()


def test_console_discard_forgets_a_kept_request_without_applying_it(capsule: Capsule) -> None:
    """``config console discard ID`` forgets the request and changes nothing of the record. Discarding it
    again, or applying a request that was never kept, exits 2."""
    capsule.send("000001-bind", "bind", "home", "~/capsule-home")
    before = capsule.record.read_bytes()

    discarded = capsule.config("console", "discard", "000001-bind")

    assert discarded.returncode == 0, discarded.stdout
    assert "000001-bind" not in capsule.kept() and capsule.record.read_bytes() == before
    assert capsule.config("console", "discard", "000001-bind").returncode == 2
    assert capsule.config("console", "apply", "000009-never-asked").returncode == 2


@pytest.mark.parametrize(("node", "value", "recorded"), [
    ("network", "bridge", "bridge"), ("docker-daemon", "none", "none"), ("host-browser", "false", False),
])
def test_an_authorization_of_the_secure_value_is_recorded_without_the_hosts_confirmation(
    capsule: Capsule, node: str, value: str, recorded: object,
) -> None:
    """``authorize`` with the value that grants nothing is applied at once by the real command: the result is
    ``recorded``, the record holds the value, and nothing is kept for the host."""
    assert capsule.send("000001-authorize", "authorize", node, value)["status"] == "recorded"

    assert capsule.saved()["authorization"][node]["value"] == recorded
    assert "000001-authorize" not in capsule.kept()


@pytest.mark.parametrize("save", [False, True])
def test_a_kept_request_applied_at_the_launchs_question_is_used_by_that_launch_and_recorded(capsule: Capsule, save: bool) -> None:
    """A launch on a terminal asks about the kept request, saying when the console asked and what. Answered
    ``a``, the request's command runs: the Docker daemon is authorized in the record and in the plan of this
    very launch, and nothing is kept. ``--memory`` given beside it is recorded with ``--save`` and not without,
    so applying the request neither loses nor writes the launch's own flags."""
    capsule.ready_to_launch()
    capsule.send("000001-authorize", "authorize", "docker-daemon", "host-socket")

    shown = capsule.launch_at_a_terminal([(KEPT_PROMPT, "a\n")], "--memory", "6g", *(["--save"] if save else []))

    assert f"The console asked at {ASKED_AT}: config authorize docker-daemon host-socket" in shown
    assert capsule.saved()["authorization"]["docker-daemon"]["value"] == "host-socket"
    assert capsule.planned()["authorization"]["docker-daemon"] == "host-socket"
    assert capsule.saved().get("configuration", {}).get("values", {}) == ({"memory": "6GiB"} if save else {})
    assert "000001-authorize" not in capsule.kept()


def test_a_kept_request_left_at_the_launchs_question_stays_kept_and_the_launch_goes_on(capsule: Capsule) -> None:
    """Answered with Enter, the request is neither applied nor discarded: the launch says it was kept and how
    to apply or discard it later, goes on, and the request still awaits with the record unchanged."""
    capsule.ready_to_launch()
    capsule.send("000001-authorize", "authorize", "network", "host")

    shown = capsule.launch_at_a_terminal([(KEPT_PROMPT, "\n")])

    assert "Kept. Apply or discard later:" in shown and "config console apply 000001-authorize" in shown
    assert "network" not in capsule.saved().get("authorization", {})
    assert "000001-authorize" in capsule.kept()


def test_a_kept_forget_applied_at_the_launch_removes_the_grant_and_keeps_the_flags_saved_beside_it(capsule: Capsule) -> None:
    """The checkout had authorized the host's network, and the console asked to forget that answer. Applied at
    the launch's question, the grant is gone from the record and from this launch's plan, and the memory given
    with ``--save`` in the same launch is recorded."""
    capsule.ready_to_launch()
    assert capsule.config("authorize", "network", "host").returncode == 0
    assert capsule.send("000001-forget", "forget", "network")["status"] == "deferred"

    capsule.launch_at_a_terminal([(KEPT_PROMPT, "a\n")], "--memory", "6g", "--save")

    assert "network" not in capsule.saved().get("authorization", {})
    assert "network" not in capsule.planned()["authorization"]
    assert capsule.saved()["configuration"]["values"] == {"memory": "6GiB"}


def test_a_request_kept_because_the_launcher_was_stopping_is_applied_at_the_next_launch_beside_its_flags(capsule: Capsule) -> None:
    """A request the launcher would apply at once is kept when it arrives while the launcher stops. At the
    next launch it is asked; applied there, its value and the one given with ``--save`` are both recorded."""
    capsule.ready_to_launch()
    request = capsule.ask("000001-set", "set", "cpus", "2")
    stopping = capsule.run("-c", ANSWER_WHILE_STOPPING, str(request), str(capsule.project), str(capsule.record))
    assert stopping.returncode == 0 and stopping.stdout.strip() == "deferred", stopping.stdout

    capsule.launch_at_a_terminal([(KEPT_PROMPT, "a\n")], "--memory", "6g", "--save")

    assert capsule.saved()["configuration"]["values"] == {"memory": "6GiB", "cpus": 2}
