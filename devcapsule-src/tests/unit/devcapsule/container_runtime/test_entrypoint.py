"""Unit tests of ``devcapsule/container_runtime/entrypoint.py``: the children ``run`` supervises and the environment it gives them."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import os
from pathlib import Path

import pytest

from devcapsule import logs
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime import console, entrypoint, filesystem
from devcapsule.container_runtime.console import CONSOLE_CHILD, CommandWrapper
from devcapsule.container_runtime.contract import (
    CONTAINED_DISPLAY_TRANSPORT,
    ConsolePlan,
    DisplayPlan,
    Identity,
    RuntimePlan,
)
from devcapsule.container_runtime.display import ContainedDisplay, NOVNC_CHILD, XVNC_CHILD
from devcapsule.container_runtime.entrypoint import run
from devcapsule.container_runtime.supervisor import SupervisedChild

SUPERVISOR_STATUS = 42


@dataclass
class SessionHost:
    """What ``run`` reads from and leaves on the host, as one test built and observes it."""

    environ: dict[str, str] = field(default_factory=dict)
    supervised: list[tuple[SupervisedChild, ...]] = field(default_factory=list)
    environment_at_start: dict[str, str] = field(default_factory=dict)

    @contextmanager
    def process(self) -> Iterator[None]:
        """Replace process inputs only during the action, before pytest resumes."""
        with pytest.MonkeyPatch.context() as process:
            process.setattr(os, "environ", self.environ)
            process.setattr(os, "geteuid", lambda: 1000)
            yield


def fake_display(_plan: RuntimePlan, _runtime_dir: str, as_user: CommandWrapper) -> ContainedDisplay:
    """Stand-in for ``prepare_contained_display``: two infrastructure children and their environment, no X server."""
    return ContainedDisplay(
        children=(
            SupervisedChild(name=XVNC_CHILD, command=as_user(("Xvnc",))),
            SupervisedChild(name=NOVNC_CHILD, command=as_user(("websockify",))),
        ),
        environment={"DISPLAY": ":99", "XAUTHORITY": "/tmp/Xauthority"},
        display_number=99,
        xauthority_path="/tmp/Xauthority",
        rfb_socket_path="/tmp/rfb.sock",
        openbox_configuration_path="/tmp/openbox.xml",
        panel_configuration_path="/tmp/tint2rc",
    )


@pytest.fixture
def host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SessionHost:
    """A host built for one ``run``.

    Within ``host.process()``, the environment is an empty mapping and the
    caller is not root. The image paths lie under ``tmp_path``: a runtime
    root, an empty interpreter file, and an absent launcher package. The display, the
    supervisor and the log setup are stand-ins, so no program starts and the
    root logger stays as it was.
    """
    session = SessionHost()

    class RecordingSupervisor:
        def __init__(self, children: tuple[SupervisedChild, ...], **_settings: object) -> None:
            session.supervised.append(children)
            session.environment_at_start = dict(os.environ)

        def run(self) -> int:
            return SUPERVISOR_STATUS

    python = tmp_path / "base-python"
    python.touch()
    monkeypatch.setattr(filesystem, "RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setattr(console, "CONSOLE_PYTHON", str(python))
    monkeypatch.setattr(console, "LAUNCHER_CONSOLE_SOURCE", str(tmp_path / "absent-launcher-webconsole"))
    monkeypatch.setattr(entrypoint, "prepare_contained_display", fake_display)
    monkeypatch.setattr(entrypoint, "Supervisor", RecordingSupervisor)
    monkeypatch.setattr(logs, "configure", lambda *_arguments, **_settings: None)
    return session


def make_plan(tmp_path: Path, *, with_display: bool) -> RuntimePlan:
    """Construct a ``RuntimePlan`` with a console whose project, home, state slots, and properties file all live under ``tmp_path``."""
    base = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path=str(tmp_path / "project"),
        home=str(tmp_path / "home"),
        identity=Identity(1000, 1000, "developer"),
    ).with_console(ConsolePlan("0.0.0.0", 6081, str(tmp_path / "console-token")))
    document = base.to_mapping()
    document["state_slots"] = [
        {"name": slot.name, "path": str(tmp_path / "slots" / slot.name.replace("/", "-"))}
        for slot in base.state_slots
    ]
    component = document["component"]
    assert isinstance(component, dict)
    configuration = component["configuration"]
    assert isinstance(configuration, dict)
    configuration["properties_path"] = str(tmp_path / "jetbrains.properties")
    if with_display:
        document["display"] = DisplayPlan(
            transport=CONTAINED_DISPLAY_TRANSPORT,
            listen_address="127.0.0.1",
            port=6080,
            token_path=str(tmp_path / "display-token"),
        ).to_mapping()
    return RuntimePlan.from_mapping(document)


def test_run_places_console_after_contained_display_and_before_foreground_surface(
    tmp_path: Path, host: SessionHost,
) -> None:
    """With a contained display and console, ``run`` orders display children, ``console``, and foreground IDE."""
    plan = make_plan(tmp_path, with_display=True)
    with host.process():
        status = run(plan)

    assert status == SUPERVISOR_STATUS
    (children,) = host.supervised
    assert [child.name for child in children] == [XVNC_CHILD, NOVNC_CHILD, CONSOLE_CHILD, "pycharm"]
    assert all(not child.foreground for child in children[:-1])
    assert children[-1].foreground is True


def test_run_places_console_before_foreground_surface_without_display(tmp_path: Path, host: SessionHost) -> None:
    """Without a contained display, ``run`` starts ``console`` in background and the surface in foreground."""
    plan = make_plan(tmp_path, with_display=False)
    with host.process():
        status = run(plan)

    assert status == SUPERVISOR_STATUS
    (children,) = host.supervised
    assert [child.name for child in children] == [CONSOLE_CHILD, "pycharm"]
    assert children[0].foreground is False and children[1].foreground is True


def test_run_suppresses_contained_display_and_keeps_console_in_job_mode(tmp_path: Path, host: SessionHost) -> None:
    """In headless ``job`` mode, ``run`` omits display children even if declared and supervises ``[console, job]``."""
    plan = make_plan(tmp_path, with_display=True)
    with host.process():
        status = run(plan, job=("pytest", "-q"))

    assert status == SUPERVISOR_STATUS
    (children,) = host.supervised
    assert [child.name for child in children] == [CONSOLE_CHILD, "job"]
    assert children[0].foreground is False and children[1].foreground is True
    assert children[1].command == ("pytest", "-q")
    assert children[1].working_directory == str(tmp_path / "project")


def test_run_gives_the_session_its_environment_before_the_children_start(tmp_path: Path, host: SessionHost) -> None:
    """Before supervision, ``run`` sets session paths and display variables, supplies graphics defaults, and preserves graphics overrides."""
    plan = make_plan(tmp_path, with_display=True)
    host.environ["LIBGL_ALWAYS_SOFTWARE"] = "0"
    with host.process():
        run(plan)

    assert host.environment_at_start["HOME"] == str(tmp_path / "home")
    assert host.environment_at_start["XDG_RUNTIME_DIR"] == str(tmp_path / "runtime" / "devcapsule-runtime-1000")
    assert host.environment_at_start["DISPLAY"] == ":99"
    assert host.environment_at_start["XAUTHORITY"] == "/tmp/Xauthority"
    assert host.environment_at_start["PYCHARM_PROPERTIES"] == str(tmp_path / "jetbrains.properties")
    assert host.environment_at_start["NO_AT_BRIDGE"] == "1"
    assert host.environment_at_start["LIBGL_ALWAYS_SOFTWARE"] == "0"
    assert (tmp_path / "jetbrains.properties").is_file()
