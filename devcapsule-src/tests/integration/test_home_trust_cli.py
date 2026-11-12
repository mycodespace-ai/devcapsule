"""Integration tests of the home's trust as a developer meets it: real commands, and a real terminal.

A channel is accepted once per home, and every command that asks about a
checkout reads that home. So these tests run the launcher as processes, in
an environment the test builds: a project created by ``project init``, and a
named home under the test's directory that has accepted nothing. The last
test puts the launch on a pseudo-terminal, because the launch asks only when
its input is a terminal.

No command here needs Docker or the network: each ends before the launch
reaches either.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import time

import pytest

from devcapsule.configuration.storage import load_toml

pytestmark = pytest.mark.integration

ACCEPT_COMMAND = "devcapsule home trust accept devcapsule-base"


class Checkout:
    """One project with a named home, and the launcher run on them as a process."""

    def __init__(self, directory: Path) -> None:
        self.project = directory / "project"
        self.home = directory / "devcapsule-home"
        self.project.mkdir()
        self.environment = {
            "PATH": os.defpath, "HOME": str(directory / "home"), "DEVCAPSULE_CONFIG_HOME": str(self.home),
            "PYTHONDONTWRITEBYTECODE": "1",
        }

    @property
    def settings(self) -> Path:
        """The home's settings file, which holds what the home trusts."""
        return self.home / "settings.toml"

    def launcher(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """``devcapsule ARGUMENTS`` with no terminal; standard error is joined to standard output."""
        return subprocess.run(
            [sys.executable, "-m", "devcapsule", *arguments], cwd=self.project, env=self.environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300, check=False,
        )

    def project_command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """``devcapsule project ARGUMENTS`` for this project."""
        return self.launcher("project", "--path", str(self.project), *arguments)

    def at_a_terminal(self, answers: list[tuple[str, str]], *arguments: str) -> tuple[int, str]:
        """Run ``devcapsule ARGUMENTS`` on a pseudo-terminal; return its exit status and all it showed.

        ``answers`` are the developer's, in order: each is typed when the
        terminal's output ends with the prompt paired with it.
        """
        terminal, launcher_side = pty.openpty()
        process = subprocess.Popen(
            [sys.executable, "-m", "devcapsule", *arguments], cwd=self.project, env=self.environment,
            stdin=launcher_side, stdout=launcher_side, stderr=launcher_side, close_fds=True,
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
            status = process.wait(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
            os.close(terminal)
        return status, shown.decode(errors="replace")


@pytest.fixture
def checkout(tmp_path: Path) -> Checkout:
    """A project that requires Node, with PyCharm chosen on its checkout, in a home that has accepted nothing.

    The checkout has not authorized its base image, so the base is for the
    home's trust of DevCapsule's channel to answer.
    """
    checkout = Checkout(tmp_path)
    created = checkout.project_command("init", "--require", "node", "--creator", "mailto:owner@example.test")
    assert created.returncode == 0, created.stdout
    chosen = checkout.project_command("config", "ide", "python-ide")
    assert chosen.returncode == 0, chosen.stdout
    return checkout


def test_accepting_the_base_channel_for_the_home_settles_the_checkouts_pending_base(checkout: Checkout) -> None:
    """Before the acceptance ``config check`` exits 3 and names the command that accepts, and ``config trust
    list`` shows the channel as not yet accepted in this home's settings file. ``home trust accept`` states what
    is trusted and records it in that file. After it ``config check`` exits 0, ``config show`` gives the home's
    trust as the source of the base, and the JSON listing shows the channel trusted."""
    pending = checkout.project_command("config", "check")
    assert pending.returncode == 3 and ACCEPT_COMMAND in pending.stdout, pending.stdout
    listed = checkout.project_command("config", "trust", "list")
    assert listed.returncode == 0, listed.stdout
    assert f"Trust record: {checkout.settings}" in listed.stdout
    assert any(line.split()[:3] == ["devcapsule-base", "not", "yet"] for line in listed.stdout.splitlines()), listed.stdout

    accepted = checkout.launcher("home", "trust", "accept", "devcapsule-base", "--yes")

    assert accepted.returncode == 0, accepted.stdout
    assert "Trust DevCapsule to supply the base images" in accepted.stdout
    assert f"Recorded for this DevCapsule home: {checkout.settings}" in accepted.stdout
    assert load_toml(checkout.settings)["trust"]["channels"]["devcapsule-base"]["vendor"] == "DevCapsule"
    settled = checkout.project_command("config", "check")
    assert settled.returncode == 0, settled.stdout
    shown = checkout.project_command("config", "show")
    assert shown.returncode == 0 and "home trust (devcapsule-base)" in shown.stdout, shown.stdout
    as_json = checkout.project_command("config", "trust", "list", "--json")
    assert as_json.returncode == 0, as_json.stdout
    assert [(row["channel"], row["trusted"]) for row in json.loads(as_json.stdout)["channels"]] == [("devcapsule-base", True)]


def test_withdrawing_the_channel_leaves_the_base_pending_again_and_a_second_withdrawal_changes_nothing(checkout: Checkout) -> None:
    """``home trust withdraw`` removes the acceptance from the home: ``config check`` exits 3 again. Withdrawing
    a channel that is not accepted exits 0 and says so."""
    assert checkout.launcher("home", "trust", "accept", "devcapsule-base", "--yes").returncode == 0
    assert checkout.project_command("config", "check").returncode == 0

    withdrawn = checkout.launcher("home", "trust", "withdraw", "devcapsule-base")

    assert withdrawn.returncode == 0 and "Withdrew devcapsule-base" in withdrawn.stdout, withdrawn.stdout
    assert "devcapsule-base" not in load_toml(checkout.settings).get("trust", {}).get("channels", {})
    assert checkout.project_command("config", "check").returncode == 3
    again = checkout.launcher("home", "trust", "withdraw", "devcapsule-base")
    assert again.returncode == 0 and "No acceptance recorded for devcapsule-base" in again.stdout, again.stdout


def test_a_developer_who_answers_no_at_the_terminal_is_told_how_to_accept_later_and_nothing_is_recorded(checkout: Checkout) -> None:
    """``project run`` on a terminal asks whether to accept DevCapsule's channel for the home. Answered no, it
    says how to accept later, ends with exit status 3 before anything is launched, and writes no settings file."""
    status, shown = checkout.at_a_terminal(
        [("Accept for this DevCapsule home? [y/N]:", "n\n")],
        "project", "--path", str(checkout.project), "run", "--no-update-check",
    )

    assert status == 3, shown
    assert "Trust DevCapsule to supply the base images" in shown
    assert f"Not accepted. Accept later: {ACCEPT_COMMAND}" in shown
    assert "Nothing was written." in shown
    assert not checkout.settings.exists()
