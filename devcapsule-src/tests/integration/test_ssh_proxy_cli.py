"""Integration tests of the ``ssh-proxy`` authorization on the command line, with its retired name ``github-ssh``.

Every test starts the real program, ``sys.executable -m devcapsule``, in an
environment it builds: a project made by ``project init`` under the test's
directory and a named home beside it. No command here launches a capsule,
reads a key or reaches the network.

A checkout "as an earlier launcher left it" is the record this launcher
writes, with its ``ssh-proxy`` entry moved by the test to ``github-ssh`` and
bound to the digest that the earlier launcher recorded for that name.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from devcapsule.configuration.file_formats import canonical_digest, render_toml
from devcapsule.configuration.storage import load_toml

pytestmark = pytest.mark.integration

RETIRED_NAME_ON_THE_COMMAND_LINE = (
    "Note: authorization 'github-ssh' is 'ssh-proxy' now. The old name still works "
    "and will be removed in a later release."
)


class Project:
    """One project with its named home, and the ``config`` commands a developer runs on it."""

    def __init__(self, directory: Path) -> None:
        self.root = directory / "project"
        self.home = directory / "devcapsule-home"
        self.root.mkdir()
        self.environment = {
            "PATH": os.defpath, "HOME": str(directory / "home"),
            "DEVCAPSULE_CONFIG_HOME": str(self.home), "PYTHONDONTWRITEBYTECODE": "1",
        }

    def devcapsule(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """``devcapsule project --path ROOT ARGUMENTS``, with standard error kept apart from standard output."""
        return subprocess.run(
            [sys.executable, "-m", "devcapsule", "project", "--path", str(self.root), *arguments],
            cwd=self.root, env=self.environment, capture_output=True, text=True, timeout=300, check=False,
        )

    def config(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self.devcapsule("config", *arguments)

    @property
    def record(self) -> Path:
        """The checkout's record in the named home."""
        (found,) = self.home.rglob("devcapsule.checkout.toml")
        return found

    def recorded(self) -> dict[str, Any]:
        """The authorization table of the checkout's record as it is on disk."""
        return dict(load_toml(self.record).get("authorization", {}))

    def as_an_earlier_launcher_left_it(self, value: bool) -> None:
        """Record ``github-ssh`` as ``value`` the way a launcher before the rename did, and no ``ssh-proxy``."""
        granted = self.config("authorize", "ssh-proxy", "true" if value else "false")
        assert granted.returncode == 0, granted.stderr
        document = load_toml(self.record)
        del document["authorization"]["ssh-proxy"]
        document["authorization"]["github-ssh"] = {
            "value": value,
            "recommendation-digest": canonical_digest({"name": "github-ssh", "recommendation": "home-default"}),
        }
        self.record.write_text(render_toml(document), encoding="utf-8")
        assert set(self.recorded()) == {"github-ssh"}


@pytest.fixture
def project(tmp_path: Path) -> Project:
    """A project that requires Node, registered in a home that has accepted nothing."""
    project = Project(tmp_path)
    created = project.devcapsule("init", "--require", "node", "--creator", "mailto:owner@example.test")
    assert created.returncode == 0, created.stderr
    return project


@pytest.mark.parametrize("given,recorded,shown", [
    ("id_work", "id_work", "id_work"), ("~/keys/deploy", "~/keys/deploy", "~/keys/deploy"),
    ("default", "default", "default"), ("true", True, "true"), ("false", False, "false"), ("none", False, "false"),
])
def test_authorize_records_the_ssh_proxy_with_the_key_given_and_no_note(project: Project, given: str, recorded: Any, shown: str) -> None:
    """``config authorize ssh-proxy`` records a key's name or path as given, ``default`` as that word, and
    the bools and ``none`` as a bool. The current name earns no note. No key is looked for: the home has none."""
    result = project.config("authorize", "ssh-proxy", given)

    assert result.returncode == 0, result.stderr
    assert f"Authorized ssh-proxy for this checkout: {shown}" in result.stdout
    assert result.stderr == ""
    assert project.recorded()["ssh-proxy"]["value"] == recorded


def test_authorize_refuses_a_relative_key_path_and_records_nothing(project: Project) -> None:
    """A key path that is neither absolute nor under ``~/`` is refused with the rule, and no answer is recorded."""
    result = project.config("authorize", "ssh-proxy", "keys/deploy")

    assert result.returncode != 0
    assert "Authorization 'ssh-proxy': a key path is absolute or begins with '~/'" in result.stderr
    assert project.recorded() == {}


@pytest.mark.parametrize("value,recorded", [("true", True), ("false", False)])
def test_authorize_under_the_retired_name_records_the_current_one_with_a_note(project: Project, value: str, recorded: bool) -> None:
    """``config authorize github-ssh`` with either of its old values still works: the answer is recorded
    as ``ssh-proxy``, and standard error says the name changed and will be removed."""
    result = project.config("authorize", "github-ssh", value)

    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == RETIRED_NAME_ON_THE_COMMAND_LINE
    assert f"Authorized ssh-proxy for this checkout: {value}" in result.stdout
    assert set(project.recorded()) == {"ssh-proxy"} and project.recorded()["ssh-proxy"]["value"] is recorded


def test_deny_under_the_retired_name_denies_the_current_one_with_a_note(project: Project) -> None:
    """``config deny github-ssh`` records the denial of ``ssh-proxy`` and gives the same note."""
    result = project.config("deny", "github-ssh")

    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == RETIRED_NAME_ON_THE_COMMAND_LINE
    assert "Denied ssh-proxy for this checkout: false." in result.stdout
    assert set(project.recorded()) == {"ssh-proxy"} and project.recorded()["ssh-proxy"]["value"] is False


@pytest.mark.parametrize("value,shown", [(True, "true"), (False, "false")])
def test_a_checkout_an_earlier_launcher_left_is_listed_by_its_answer_and_told_to_record_it_again(
    project: Project, value: bool, shown: str,
) -> None:
    """``config show`` of a checkout that records ``github-ssh`` lists ``ssh-proxy`` at the recorded value,
    says under which name it was found, and gives the command that records it again. Nothing is rewritten."""
    project.as_an_earlier_launcher_left_it(value)

    listed = project.config("show")

    assert listed.returncode == 0, listed.stderr
    (row,) = (line for line in listed.stdout.splitlines() if line.startswith("access") and " ssh-proxy " in line)
    assert row.split()[2] == shown
    assert "checkout (recorded as github-ssh, a name to be removed)" in row
    assert (
        "This checkout records 'github-ssh', which is 'ssh-proxy' now. The old name still works and will be "
        f"removed in a later release. Record the answer again: devcapsule project --path {project.root} "
        f"config authorize ssh-proxy {shown}"
    ) in listed.stdout
    assert "github-ssh" not in {line.split()[1] for line in listed.stdout.splitlines() if line.startswith("access")}
    assert set(project.recorded()) == {"github-ssh"}


def test_recording_the_answer_again_removes_the_retired_entry_and_the_report(project: Project) -> None:
    """The command the listing gives leaves one entry, ``ssh-proxy``, and a listing that mentions the old name nowhere."""
    project.as_an_earlier_launcher_left_it(True)

    again = project.config("authorize", "ssh-proxy", "true")

    assert again.returncode == 0 and again.stderr == ""
    assert set(project.recorded()) == {"ssh-proxy"} and project.recorded()["ssh-proxy"]["value"] is True
    assert "github-ssh" not in project.config("show").stdout


@pytest.mark.parametrize("name,noted", [("ssh-proxy", False), ("github-ssh", True)])
def test_forget_under_either_name_removes_the_answer_an_earlier_launcher_recorded(project: Project, name: str, noted: bool) -> None:
    """``config forget`` by the current name or the retired one removes the ``github-ssh`` entry, so the
    secure default applies; only the retired name earns the note."""
    project.as_an_earlier_launcher_left_it(True)

    result = project.config("forget", name)

    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == (RETIRED_NAME_ON_THE_COMMAND_LINE if noted else "")
    assert "Forgot ssh-proxy for this checkout." in result.stdout
    assert project.recorded() == {}


def test_forget_with_no_answer_under_either_name_is_refused(project: Project) -> None:
    """With nothing recorded for the proxy, ``config forget ssh-proxy`` says so and fails."""
    result = project.config("forget", "ssh-proxy")

    assert result.returncode != 0
    assert "'ssh-proxy' has no recorded answer for this checkout." in result.stderr


def test_a_launch_takes_the_retired_name_for_one_run_with_the_note(project: Project) -> None:
    """``project run --authorize github-ssh true`` is read as ``ssh-proxy`` for that run: the note is given,
    the grant is announced under the current name, and the launch stops only where this project's would
    without the flag, at the IDE and the base channel it has not been told. Nothing is recorded."""
    result = project.devcapsule("run", "--no-update-check", "--authorize", "github-ssh", "true")

    assert result.stderr.splitlines()[0] == RETIRED_NAME_ON_THE_COMMAND_LINE
    assert result.stderr.splitlines()[1] == "Run-once authorization: ssh-proxy = true"
    assert result.returncode == 3 and "the launch of this checkout needs answers:" in result.stderr
    assert "github-ssh" not in result.stderr.replace(RETIRED_NAME_ON_THE_COMMAND_LINE, "")
    assert project.recorded() == {}
