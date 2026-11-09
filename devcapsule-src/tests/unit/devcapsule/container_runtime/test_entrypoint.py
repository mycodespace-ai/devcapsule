"""Unit tests of ``devcapsule/container_runtime/entrypoint.py``: console child placement across launch modes."""

from __future__ import annotations

import os
from pathlib import Path

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.console import CONSOLE_CHILD, CommandWrapper, console_child
from devcapsule.container_runtime.contract import (
    CONTAINED_DISPLAY_TRANSPORT,
    ConsolePlan,
    DisplayPlan,
    Identity,
    RuntimePlan,
)
from devcapsule.container_runtime.display import ContainedDisplay, NOVNC_CHILD, XVNC_CHILD
from devcapsule.container_runtime.entrypoint import ConsoleBuilder, SupervisorFactory, run
from devcapsule.container_runtime.supervisor import SupervisedChild


class RecordingSupervisor:
    """Supervisor stand-in that records supervised children and returns a fixed status."""

    def __init__(self, children: tuple[SupervisedChild, ...], **_kwargs: object) -> None:
        self.children = children

    def run(self) -> int:
        return 42


def recording_supervisor_factory() -> tuple[SupervisorFactory, list[RecordingSupervisor]]:
    """A supervisor factory for ``run`` and the list it appends each supervisor it makes to."""
    recorded: list[RecordingSupervisor] = []

    def make_supervisor(children: tuple[SupervisedChild, ...], **kwargs: object) -> RecordingSupervisor:
        instance = RecordingSupervisor(children, **kwargs)
        recorded.append(instance)
        return instance

    return make_supervisor, recorded


def console_builder_with_interpreter(tmp_path: Path) -> ConsoleBuilder:
    """A console builder whose base interpreter is an empty file under ``tmp_path``, so a console child is made."""
    python = tmp_path / "python"
    python.touch()
    return lambda plan, as_user: console_child(plan, as_user, console_python=python)


def make_plan(tmp_path: Path, *, with_display: bool) -> RuntimePlan:
    plan = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home=str(tmp_path / "home"),
        identity=Identity(1000, 1000, "developer"),
    ).with_console(ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token"))
    if not with_display:
        return plan
    display = DisplayPlan(
        transport=CONTAINED_DISPLAY_TRANSPORT,
        listen_address="127.0.0.1",
        port=6080,
        token_path="/run/devcapsule-display-token",
    )
    return RuntimePlan.from_mapping({**plan.to_mapping(), "display": display.to_mapping()})


def fake_display(_plan: RuntimePlan, _runtime_dir: str, as_user: CommandWrapper) -> ContainedDisplay:
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


def test_run_places_console_after_contained_display_and_before_foreground_surface(tmp_path: Path) -> None:
    """With a contained display and console, ``run`` orders display children, ``console``, and foreground IDE."""
    make_supervisor, recorded = recording_supervisor_factory()

    status = run(
        make_plan(tmp_path, with_display=True),
        environ={},
        prepare_display=fake_display,
        build_console_child=console_builder_with_interpreter(tmp_path),
        supervisor_factory=make_supervisor,
    )

    assert status == 42
    children = recorded[0].children
    assert [child.name for child in children] == [XVNC_CHILD, NOVNC_CHILD, CONSOLE_CHILD, "pycharm"]
    assert all(not child.foreground for child in children[:-1])
    assert children[-1].foreground is True


def test_run_places_console_before_foreground_surface_without_display(tmp_path: Path) -> None:
    """Without a contained display, ``run`` starts ``console`` in background and the surface in foreground."""
    make_supervisor, recorded = recording_supervisor_factory()

    status = run(
        make_plan(tmp_path, with_display=False),
        environ={},
        build_console_child=console_builder_with_interpreter(tmp_path),
        supervisor_factory=make_supervisor,
    )

    assert status == 42
    children = recorded[0].children
    assert [child.name for child in children] == [CONSOLE_CHILD, "pycharm"]
    assert children[0].foreground is False and children[1].foreground is True


def test_run_suppresses_contained_display_and_keeps_console_in_job_mode(tmp_path: Path) -> None:
    """In headless ``job`` mode, ``run`` omits display children even if declared and supervises ``[console, job]``."""
    make_supervisor, recorded = recording_supervisor_factory()

    status = run(
        make_plan(tmp_path, with_display=True),
        job=("pytest", "-q"),
        environ={},
        prepare_display=fake_display,
        build_console_child=console_builder_with_interpreter(tmp_path),
        supervisor_factory=make_supervisor,
    )

    assert status == 42
    children = recorded[0].children
    assert [child.name for child in children] == [CONSOLE_CHILD, "job"]
    assert children[0].foreground is False and children[1].foreground is True


def test_run_writes_the_session_environment_into_the_given_mapping_only(tmp_path: Path) -> None:
    """``run`` with ``environ`` puts the filesystem's and the display's variables there and leaves ``os.environ`` as it was."""
    make_supervisor, _recorded = recording_supervisor_factory()
    environ: dict[str, str] = {}
    process_environment_before = dict(os.environ)

    run(
        make_plan(tmp_path, with_display=True),
        environ=environ,
        prepare_display=fake_display,
        build_console_child=console_builder_with_interpreter(tmp_path),
        supervisor_factory=make_supervisor,
    )

    assert environ["DISPLAY"] == ":99"
    assert environ["XAUTHORITY"] == "/tmp/Xauthority"
    assert "XDG_RUNTIME_DIR" in environ
    assert dict(os.environ) == process_environment_before
