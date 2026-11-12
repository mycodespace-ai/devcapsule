"""Unit tests of ``devcapsule/container_runtime/session.py``: what one session prepares, sets and supervises."""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule import logs
from devcapsule.components.eclipse import DEFINITION as ECLIPSE
from devcapsule.container_runtime.components import eclipse
from devcapsule.container_runtime.console import CONSOLE_CHILD, ConsoleInstallation
from devcapsule.container_runtime.contract import (
    ConsolePlan,
    DisplayPlan,
    Identity,
    RuntimePlan,
    RuntimePlanError,
)
from devcapsule.container_runtime.identity import CapsuleUser
from devcapsule.container_runtime.session import JOB_CHILD, Session
from devcapsule.container_runtime.supervisor import SupervisedChild

DEVELOPER = Identity(1000, 1001, "developer")

DISPLAY_CHILDREN = (
    SupervisedChild(name="xvnc", command=("Xvnc", ":99")),
    SupervisedChild(name="novnc", command=("websockify", "6080")),
)
"""Two children as a prepared display hands them over; a session only places them."""

IDE_COMMAND = ("/opt/jetbrains/pycharm/bin/pycharm.sh", "/workspace/project")


def jetbrains_document(tmp_path: Path) -> dict[str, object]:
    """A runtime plan document for a JetBrains surface whose home, slots and properties file lie under ``tmp_path``."""
    return {
        "version": 1,
        "project_path": "/workspace/project",
        "home": str(tmp_path / "home"),
        "identity": {"uid": 1000, "gid": 1001, "user": "developer"},
        "state_slots": [
            {"name": "jetbrains/config", "path": str(tmp_path / "config")},
            {"name": "jetbrains/system", "path": str(tmp_path / "system")},
            {"name": "jetbrains/plugins", "path": str(tmp_path / "plugins")},
            {"name": "jetbrains/log", "path": str(tmp_path / "log")},
        ],
        "component": {
            "id": "jetbrains",
            "adapter": "jetbrains",
            "configuration": {
                "installation_path": "/opt/jetbrains/pycharm",
                "launcher": "bin/pycharm.sh",
                "properties_path": str(tmp_path / "idea.properties"),
                "properties_environment_variable": "PYCHARM_PROPERTIES",
                "state_slot_mapping": {
                    "config": "config",
                    "system": "system",
                    "plugins": "plugins",
                    "log": "log",
                },
            },
        },
    }


def vscode_document(tmp_path: Path) -> dict[str, object]:
    """A runtime plan document for a VS Code-family surface whose home and slots lie under ``tmp_path``."""
    return {
        "version": 1,
        "project_path": "/workspace/project",
        "home": str(tmp_path / "home"),
        "identity": {"uid": 1000, "gid": 1001, "user": "developer"},
        "state_slots": [
            {"name": "codium/user-data", "path": str(tmp_path / "user-data")},
            {"name": "codium/extensions", "path": str(tmp_path / "extensions")},
        ],
        "component": {
            "id": "codium",
            "adapter": "vscode",
            "configuration": {
                "installation_path": "/opt/codium",
                "launcher": "codium",
                "additional_arguments": ["--no-sandbox"],
                "state_slot_mapping": {"user-data": "user-data", "extensions": "extensions"},
            },
        },
    }


def image_with_console(tmp_path: Path) -> ConsoleInstallation:
    """An image whose console interpreter exists, as an empty file nothing executes, and with no launcher package."""
    python = tmp_path / "console-python"
    python.touch()
    return ConsoleInstallation(python, tmp_path / "launcher-webconsole")


def image_without_console(tmp_path: Path) -> ConsoleInstallation:
    """An image from before the console: no interpreter and no launcher package."""
    return ConsoleInstallation(tmp_path / "absent-console-python", tmp_path / "launcher-webconsole")


def session_of(
    document: dict[str, object],
    console: ConsoleInstallation,
    *,
    job: tuple[str, ...] | None = None,
    caller_uid: int = 1000,
) -> Session:
    """The session of ``document``'s plan, prepared by ``caller_uid`` on an image with ``console``."""
    plan = RuntimePlan.from_mapping(document)
    return Session(plan, job, CapsuleUser(plan.identity, caller_uid), console)


def with_console(document: dict[str, object]) -> dict[str, object]:
    return {**document, "console": ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token").to_mapping()}


def with_contained_display(document: dict[str, object]) -> dict[str, object]:
    return {**document, "display": DisplayPlan.contained("127.0.0.1", 6080, "/run/devcapsule-display-token").to_mapping()}


def test_launch_of_a_jetbrains_surface_carries_its_properties_file_and_the_variable_that_names_it(
    tmp_path: Path,
) -> None:
    """For a JetBrains component, ``launch`` is the IDE command, the properties text to write, and the variable naming that file."""
    session = session_of(jetbrains_document(tmp_path), image_without_console(tmp_path))

    launch = session.launch

    properties_path = str(tmp_path / "idea.properties")
    assert launch.command == IDE_COMMAND
    assert list(launch.files) == [properties_path]
    assert launch.files[properties_path].startswith(f"idea.config.path={tmp_path / 'config'}\n")
    assert launch.environment == {"PYCHARM_PROPERTIES": properties_path}


def test_launch_of_a_vscode_surface_is_its_command_alone(tmp_path: Path) -> None:
    """For a VS Code-family component, ``launch`` is the editor command over its slots, with no file and no variable."""
    session = session_of(vscode_document(tmp_path), image_without_console(tmp_path))

    launch = session.launch

    assert launch.command == (
        "/opt/codium/codium",
        f"--user-data-dir={tmp_path / 'user-data'}",
        f"--extensions-dir={tmp_path / 'extensions'}",
        "--no-sandbox",
        "/workspace/project",
    )
    assert launch.files == {} and launch.environment == {}


def test_launch_of_an_eclipse_surface_is_the_command_its_adapter_plans(tmp_path: Path) -> None:
    """For an Eclipse component, ``launch`` is the command of the Eclipse adapter, with no file and no variable."""
    plan = RuntimePlan.for_component(
        ECLIPSE.runtime_template(), project_path="/workspace/project", home=str(tmp_path / "home"), identity=DEVELOPER,
    )
    session = Session(plan, None, CapsuleUser(DEVELOPER, 1000), image_without_console(tmp_path))

    launch = session.launch

    assert launch.command == eclipse.plan(plan).command
    assert launch.files == {} and launch.environment == {}


def test_launch_refuses_a_component_whose_adapter_the_runtime_does_not_know(tmp_path: Path) -> None:
    """A plan whose component names an unknown adapter raises ``RuntimePlanError`` when its launch is asked for."""
    document = jetbrains_document(tmp_path)
    document["component"]["adapter"] = "fixture"  # type: ignore[index]
    session = session_of(document, image_without_console(tmp_path))

    with pytest.raises(RuntimePlanError, match="unsupported component adapter: fixture"):
        session.launch


def test_environment_sets_the_session_paths_every_components_variables_and_the_surfaces_own(
    tmp_path: Path,
) -> None:
    """``environment`` carries the home and runtime directory, an ancillary component's variable, and the surface's properties variable."""
    document = jetbrains_document(tmp_path)
    document["ancillary_components"] = [
        {
            "id": "codex",
            "adapter": "ancillary",
            "configuration": {},
            "environment": {"CODEX_HOME": str(tmp_path / "codex-home")},
        }
    ]
    session = session_of(document, image_without_console(tmp_path))

    environment = session.environment({})

    assert environment["HOME"] == str(tmp_path / "home")
    assert environment["XDG_RUNTIME_DIR"] == "/tmp/devcapsule-runtime-1000"
    assert environment["CODEX_HOME"] == str(tmp_path / "codex-home")
    assert environment["PYCHARM_PROPERTIES"] == str(tmp_path / "idea.properties")


def test_environment_supplies_the_graphics_defaults_a_process_does_not_have(tmp_path: Path) -> None:
    """In a process that sets no graphics variable, ``environment`` turns the accessibility bridge off and software rendering on."""
    session = session_of(jetbrains_document(tmp_path), image_without_console(tmp_path))

    environment = session.environment({})

    assert environment["NO_AT_BRIDGE"] == "1"
    assert environment["LIBGL_ALWAYS_SOFTWARE"] == "1"


def test_environment_keeps_a_graphics_setting_the_process_already_has(tmp_path: Path) -> None:
    """A graphics variable of the existing environment keeps its value in what ``environment`` sets."""
    session = session_of(jetbrains_document(tmp_path), image_without_console(tmp_path))

    environment = session.environment({"LIBGL_ALWAYS_SOFTWARE": "0"})

    assert environment["LIBGL_ALWAYS_SOFTWARE"] == "0"
    assert environment["NO_AT_BRIDGE"] == "1"


def test_environment_lets_a_components_variable_decide_a_graphics_setting(tmp_path: Path) -> None:
    """A graphics variable a component declares wins over the default and over the existing environment."""
    document = jetbrains_document(tmp_path)
    document["ancillary_components"] = [
        {"id": "gpu", "adapter": "ancillary", "configuration": {}, "environment": {"LIBGL_ALWAYS_SOFTWARE": "0"}}
    ]
    session = session_of(document, image_without_console(tmp_path))

    environment = session.environment({"LIBGL_ALWAYS_SOFTWARE": "1"})

    assert environment["LIBGL_ALWAYS_SOFTWARE"] == "0"


def test_environment_names_only_what_the_session_sets(tmp_path: Path) -> None:
    """A variable of the existing environment that the session does not decide is not among those ``environment`` sets."""
    session = session_of(jetbrains_document(tmp_path), image_without_console(tmp_path))

    environment = session.environment({"PATH": "/usr/bin", "LANG": "C.UTF-8"})

    assert "PATH" not in environment and "LANG" not in environment


def test_an_interactive_session_shows_the_contained_display_its_plan_selects(tmp_path: Path) -> None:
    """With a contained display in the plan and no job, ``shows_contained_display`` is true."""
    session = session_of(with_contained_display(jetbrains_document(tmp_path)), image_without_console(tmp_path))

    assert session.shows_contained_display is True


def test_a_headless_job_shows_no_display_even_when_the_plan_selects_one(tmp_path: Path) -> None:
    """With a job, ``shows_contained_display`` is false although the plan carries a contained display."""
    session = session_of(
        with_contained_display(jetbrains_document(tmp_path)), image_without_console(tmp_path), job=("pytest", "-q"),
    )

    assert session.shows_contained_display is False


@pytest.mark.parametrize("display", [None, DisplayPlan.host_x11().to_mapping()])
def test_a_session_shows_no_contained_display_unless_its_plan_selects_one(
    tmp_path: Path, display: dict[str, object] | None,
) -> None:
    """Without a display section, or with the host's X11, ``shows_contained_display`` is false."""
    document = jetbrains_document(tmp_path)
    if display is not None:
        document["display"] = display
    session = session_of(document, image_without_console(tmp_path))

    assert session.shows_contained_display is False


def test_an_interactive_jetbrains_session_holds_the_profile_lock(tmp_path: Path) -> None:
    """For a JetBrains surface and no job, ``holds_profile_lock`` is true."""
    session = session_of(jetbrains_document(tmp_path), image_without_console(tmp_path))

    assert session.holds_profile_lock is True


def test_a_headless_job_holds_no_profile_lock(tmp_path: Path) -> None:
    """With a job, ``holds_profile_lock`` is false: no IDE opens the profile."""
    session = session_of(jetbrains_document(tmp_path), image_without_console(tmp_path), job=("pytest",))

    assert session.holds_profile_lock is False


def test_a_surface_that_is_not_jetbrains_holds_no_profile_lock(tmp_path: Path) -> None:
    """For a VS Code-family surface, ``holds_profile_lock`` is false."""
    session = session_of(vscode_document(tmp_path), image_without_console(tmp_path))

    assert session.holds_profile_lock is False


def test_children_start_the_display_then_the_console_then_the_surface(tmp_path: Path) -> None:
    """Given a display's children and a plan with a console, ``children`` orders display, ``console``, surface, the surface alone in the foreground."""
    session = session_of(with_console(jetbrains_document(tmp_path)), image_with_console(tmp_path))

    children = session.children(DISPLAY_CHILDREN)

    assert [child.name for child in children] == ["xvnc", "novnc", CONSOLE_CHILD, "jetbrains"]
    assert [child.foreground for child in children] == [False, False, False, True]
    assert children[:2] == DISPLAY_CHILDREN
    assert children[-1].command == IDE_COMMAND


def test_children_without_a_display_are_the_console_and_the_surface(tmp_path: Path) -> None:
    """Given no display children, ``children`` is the background ``console`` and the foreground surface."""
    session = session_of(with_console(jetbrains_document(tmp_path)), image_with_console(tmp_path))

    children = session.children(())

    assert [child.name for child in children] == [CONSOLE_CHILD, "jetbrains"]
    assert [child.foreground for child in children] == [False, True]


def test_children_of_a_headless_session_are_the_console_and_the_job_in_the_project(tmp_path: Path) -> None:
    """With a job, the foreground child is named ``job``, runs the job's command, and starts in the plan's project."""
    session = session_of(
        with_console(jetbrains_document(tmp_path)), image_with_console(tmp_path), job=("pytest", "-q"),
    )

    children = session.children(())

    assert [child.name for child in children] == [CONSOLE_CHILD, JOB_CHILD]
    assert children[-1].foreground is True
    assert children[-1].command == ("pytest", "-q")
    assert children[-1].working_directory == "/workspace/project"


def test_children_of_a_plan_without_a_console_are_the_surface_alone(tmp_path: Path) -> None:
    """For a plan with no console section, ``children`` is the one foreground surface, on an image that has a console too."""
    session = session_of(jetbrains_document(tmp_path), image_with_console(tmp_path))

    children = session.children(())

    assert children == (SupervisedChild(name="jetbrains", command=IDE_COMMAND, foreground=True),)


def test_children_leave_the_console_out_on_an_image_that_has_none(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """On an image without the console interpreter, ``children`` is the surface alone and stderr says the capsule runs without a console."""
    session = session_of(with_console(jetbrains_document(tmp_path)), image_without_console(tmp_path))

    children = session.children(())

    assert [child.name for child in children] == ["jetbrains"]
    assert "the capsule runs without one" in capsys.readouterr().err


def test_children_all_run_as_the_capsule_user_when_root_prepares_the_session(tmp_path: Path) -> None:
    """For a root caller, the console's and the surface's commands both start with ``gosu`` and the capsule user's ``uid:gid``."""
    session = session_of(with_console(jetbrains_document(tmp_path)), image_with_console(tmp_path), caller_uid=0)

    console, surface = session.children(())

    assert console.command[:2] == ("gosu", "1000:1001")
    assert surface.command == ("gosu", "1000:1001", *IDE_COMMAND)


def test_a_job_runs_as_the_capsule_user_when_root_prepares_the_session(tmp_path: Path) -> None:
    """For a root caller and a job, the job's command starts with ``gosu`` and the capsule user's ``uid:gid``."""
    session = session_of(
        jetbrains_document(tmp_path), image_without_console(tmp_path), job=("pytest", "-q"), caller_uid=0,
    )

    (job,) = session.children(())

    assert job.command == ("gosu", "1000:1001", "pytest", "-q")


def test_children_each_get_their_own_log_file_when_the_plan_says_where_logs_go(tmp_path: Path) -> None:
    """With a logs directory in the plan, every child's ``log_path`` is ``devcapsule-<name>.log`` in it."""
    document = with_console(jetbrains_document(tmp_path))
    document["logs"] = {"directory": "/var/log/devcapsule"}
    session = session_of(document, image_with_console(tmp_path))

    children = session.children(DISPLAY_CHILDREN)

    assert [child.log_path for child in children] == [
        "/var/log/devcapsule/devcapsule-xvnc.log",
        "/var/log/devcapsule/devcapsule-novnc.log",
        "/var/log/devcapsule/devcapsule-console.log",
        "/var/log/devcapsule/devcapsule-jetbrains.log",
    ]


def test_children_get_no_log_file_when_the_plan_has_no_logs_section(tmp_path: Path) -> None:
    """Without a logs section, every child's ``log_path`` stays unset."""
    session = session_of(with_console(jetbrains_document(tmp_path)), image_with_console(tmp_path))

    children = session.children(DISPLAY_CHILDREN)

    assert [child.log_path for child in children] == [None, None, None, None]


def test_the_log_files_belong_to_the_capsule_user(tmp_path: Path) -> None:
    """``log_owner`` is the plan identity's uid and gid, whoever prepares the session."""
    session = session_of(jetbrains_document(tmp_path), image_without_console(tmp_path), caller_uid=0)

    assert session.log_owner == (1000, 1001)


def test_the_log_directory_is_the_plans_or_none(tmp_path: Path) -> None:
    """``log_directory`` is the directory of the plan's logs section."""
    document = jetbrains_document(tmp_path)
    document["logs"] = {"directory": "/var/log/devcapsule"}

    assert session_of(document, image_without_console(tmp_path)).log_directory == "/var/log/devcapsule"


def test_a_plan_without_a_logs_section_has_no_log_directory(tmp_path: Path) -> None:
    """Without a logs section, ``log_directory`` is ``None``."""
    assert session_of(jetbrains_document(tmp_path), image_without_console(tmp_path)).log_directory is None


def test_log_rotation_is_the_plans_when_the_launcher_derived_one(tmp_path: Path) -> None:
    """With a segment size and a rotation count in the plan, ``log_rotation`` is that pair."""
    document = jetbrains_document(tmp_path)
    document["logs"] = {"directory": "/var/log/devcapsule", "segment_bytes": 2048, "rotations": 3}

    assert session_of(document, image_without_console(tmp_path)).log_rotation == (2048, 3)


@pytest.mark.parametrize("logs_section", [None, {"directory": "/var/log/devcapsule"}])
def test_log_rotation_is_the_default_when_the_plan_carries_none(
    tmp_path: Path, logs_section: dict[str, object] | None,
) -> None:
    """Without a logs section, or with one that names only a directory, ``log_rotation`` is the module defaults of ``devcapsule.logs``."""
    document = jetbrains_document(tmp_path)
    if logs_section is not None:
        document["logs"] = logs_section

    assert session_of(document, image_without_console(tmp_path)).log_rotation == (
        logs.MAXIMUM_SEGMENT_BYTES, logs.ROTATIONS,
    )
