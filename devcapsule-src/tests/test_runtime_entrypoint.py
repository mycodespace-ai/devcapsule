from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pytest

from devcapsule.container_runtime.components.jetbrains import plan as plan_jetbrains
from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import (
    ComponentRuntimeTemplate,
    Identity,
    RuntimePlan,
    RuntimePlanError,
)
from devcapsule.container_runtime.entrypoint import main, run
from devcapsule.container_runtime.filesystem import FilesystemPlan, plan_filesystem, prepare_filesystem
from devcapsule.container_runtime.graphics import environment as graphics_environment
from devcapsule.container_runtime.identity import foreground_command
from devcapsule.container_runtime.supervisor import SupervisedChild

pytestmark = pytest.mark.legacy


def runtime_document(tmp_path: Path) -> dict[str, object]:
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


def test_contract_parses_versioned_runtime_plan(tmp_path: Path) -> None:
    plan = RuntimePlan.from_json(json.dumps(runtime_document(tmp_path)))
    assert plan.identity.uid == 1000
    assert plan.component.adapter == "jetbrains"
    assert plan.slots_by_name()["jetbrains/config"] == str(tmp_path / "config")


def test_component_declares_persistence_and_generates_generic_runtime_plan() -> None:
    template = ComponentRuntimeTemplate.from_json(json.dumps(pycharm_runtime_template().to_mapping()))
    assert template.persistence.home == "required"
    assert template.persistence.xdg == "home-relative"
    assert template.persistence.state_slots[0].kind == "durable"
    assert template.logical_slot_name("config") == "pycharm/config"

    runtime = RuntimePlan.for_component(
        template,
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000),
    )
    assert runtime.slots_by_name()["pycharm/config"] == "/ide-config"
    assert runtime.slots_by_name()["pycharm/cache"] == "/home/devcapsule/.cache"


def test_home_only_component_needs_no_runtime_special_case() -> None:
    template = ComponentRuntimeTemplate.from_mapping(
        {
            "version": 1,
            "component": {
                "id": "home-tool",
                "adapter": "fixture",
                "configuration": {},
                "persistence": {
                    "home": "required",
                    "xdg": "home-relative",
                    "state_slots": [],
                },
            },
        }
    )
    runtime = RuntimePlan.for_component(
        template,
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000),
    )
    assert runtime.state_slots == ()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda doc: doc.update(version=2), "unsupported runtime plan version"),
        (lambda doc: doc.update(identity={"uid": True, "gid": 1}), "identity.uid"),
        (lambda doc: doc.update(state_slots=[{"name": "same", "path": "/a"}, {"name": "same", "path": "/b"}]), "duplicate state slot"),
        (lambda doc: doc["component"].update(id="Tool/unsafe"), "component.id"),  # type: ignore[index]
    ],
)
def test_contract_rejects_invalid_input(tmp_path: Path, change: object, message: str) -> None:
    document = runtime_document(tmp_path)
    change(document)  # type: ignore[operator]
    with pytest.raises(RuntimePlanError, match=message):
        RuntimePlan.from_mapping(document)


def test_component_contract_requires_explicit_home_overlay() -> None:
    document = pycharm_runtime_template().to_mapping()
    persistence = document["component"]["persistence"]  # type: ignore[index]
    cache = persistence["state_slots"][-1]  # type: ignore[index]
    cache.pop("home_overlay")
    with pytest.raises(RuntimePlanError, match="must declare home_overlay"):
        ComponentRuntimeTemplate.from_mapping(document)


def test_generic_filesystem_plan_uses_persistent_home_and_declared_slots(tmp_path: Path) -> None:
    plan = plan_filesystem(RuntimePlan.from_mapping(runtime_document(tmp_path)))
    assert plan.environment["XDG_CONFIG_HOME"] == str(tmp_path / "home" / ".config")
    assert str(tmp_path / "plugins") in plan.directories
    assert plan.environment["XDG_RUNTIME_DIR"] == "/tmp/devcapsule-runtime-1000"


def test_filesystem_assigns_only_new_directories_when_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    new = existing / "new"
    changed: list[tuple[Path, int, int]] = []
    monkeypatch.setattr("devcapsule.container_runtime.filesystem.os.geteuid", lambda: 0)
    monkeypatch.setattr(
        "devcapsule.container_runtime.filesystem.os.chown",
        lambda path, uid, gid: changed.append((Path(path), uid, gid)),
    )
    prepare_filesystem(
        FilesystemPlan(
            (str(existing), str(existing / ".ssh"), str(new)),
            {"HOME": str(existing), "XDG_RUNTIME_DIR": str(new)},
        ),
        RuntimePlan.from_mapping(runtime_document(tmp_path)).identity,
    )
    assert changed == [(existing / ".ssh", 1000, 1001), (new, 1000, 1001)]


def test_jetbrains_adapter_generates_properties_and_foreground_command(tmp_path: Path) -> None:
    launch = plan_jetbrains(RuntimePlan.from_mapping(runtime_document(tmp_path)))
    assert launch.command == ("/opt/jetbrains/pycharm/bin/pycharm.sh", "/workspace/project")
    assert launch.properties_environment_variable == "PYCHARM_PROPERTIES"
    assert f"idea.plugins.path={tmp_path / 'plugins'}\n" in launch.properties


def test_pycharm_component_disables_jcef_sandbox_before_startup() -> None:
    runtime = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000),
    )
    launch = plan_jetbrains(runtime)

    assert "ide.browser.jcef.sandbox.enable=false\n" in launch.properties
    assert runtime.component.environment == {
        "JAVA_TOOL_OPTIONS": "-Dide.browser.jcef.sandbox.enable=false"
    }


def test_jetbrains_adapter_requires_declared_slot(tmp_path: Path) -> None:
    document = runtime_document(tmp_path)
    configuration = document["component"]["configuration"]  # type: ignore[index]
    configuration["state_slot_mapping"]["log"] = "missing"  # type: ignore[index]
    with pytest.raises(RuntimePlanError, match="log mapping"):
        plan_jetbrains(RuntimePlan.from_mapping(document))


def test_graphics_preserves_explicit_environment() -> None:
    assert graphics_environment({"LIBGL_ALWAYS_SOFTWARE": "0"})["LIBGL_ALWAYS_SOFTWARE"] == "0"


def test_identity_adds_gosu_only_when_root(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = RuntimePlan.from_mapping(runtime_document(Path("/tmp/test")))
    monkeypatch.setattr("devcapsule.container_runtime.identity.os.geteuid", lambda: 0)
    assert foreground_command(("ide",), plan.identity) == ("gosu", "1000:1001", "ide")
    monkeypatch.setattr("devcapsule.container_runtime.identity.os.geteuid", lambda: 1000)
    assert foreground_command(("ide",), plan.identity) == ("ide",)


class SupervisorCapture:
    """Stands in for the Supervisor to observe what the entrypoint declares."""

    instances: list["SupervisorCapture"] = []

    def __init__(
        self, children: tuple[SupervisedChild, ...], *, log_owner: tuple[int, int] | None = None,
        segment_bytes: int = 10 * 1024 * 1024, rotations: int = 4,
    ) -> None:
        self.children = children
        self.log_owner = log_owner
        self.segment_bytes = segment_bytes
        self.rotations = rotations
        SupervisorCapture.instances.append(self)

    def run(self) -> int:
        return 42


@pytest.fixture()
def captured_supervisor(monkeypatch: pytest.MonkeyPatch) -> type[SupervisorCapture]:
    SupervisorCapture.instances = []
    monkeypatch.setattr("devcapsule.container_runtime.entrypoint.Supervisor", SupervisorCapture)
    monkeypatch.setattr("devcapsule.container_runtime.identity.os.geteuid", lambda: 1000)
    return SupervisorCapture


def test_entrypoint_prepares_properties_and_supervises_foreground(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_supervisor: type[SupervisorCapture]
) -> None:
    document = runtime_document(tmp_path)
    document["ancillary_components"] = [
        {
            "id": "codex",
            "adapter": "ancillary",
            "configuration": {},
            "environment": {"CODEX_HOME": str(tmp_path / "codex-home")},
        }
    ]
    runtime = RuntimePlan.from_mapping(document)

    assert run(runtime) == 42

    properties_path = tmp_path / "idea.properties"
    assert properties_path.read_text(encoding="utf-8").startswith(
        f"idea.config.path={tmp_path / 'config'}\n"
    )
    (supervisor,) = captured_supervisor.instances
    (child,) = supervisor.children
    assert child.name == "jetbrains"
    assert child.foreground is True
    assert child.command == ("/opt/jetbrains/pycharm/bin/pycharm.sh", "/workspace/project")
    assert os.environ["PYCHARM_PROPERTIES"] == str(properties_path)
    assert os.environ["CODEX_HOME"] == str(tmp_path / "codex-home")


def test_entrypoint_dispatches_vscode_adapter_components(
    tmp_path: Path, captured_supervisor: type[SupervisorCapture]
) -> None:
    runtime = RuntimePlan.from_mapping(
        {
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
                    "state_slot_mapping": {
                        "user-data": "user-data",
                        "extensions": "extensions",
                    },
                },
            },
        }
    )

    assert run(runtime) == 42

    (supervisor,) = captured_supervisor.instances
    (child,) = supervisor.children
    assert child.name == "codium"
    assert child.foreground is True
    assert child.command == (
        "/opt/codium/codium",
        f"--user-data-dir={tmp_path / 'user-data'}",
        f"--extensions-dir={tmp_path / 'extensions'}",
        "--no-sandbox",
        "/workspace/project",
    )


def test_entrypoint_rejects_unknown_adapters(tmp_path: Path) -> None:
    document = runtime_document(tmp_path)
    document["component"]["adapter"] = "fixture"  # type: ignore[index]

    with pytest.raises(RuntimePlanError, match="unsupported component adapter"):
        run(RuntimePlan.from_mapping(document))


def test_entrypoint_headless_job_takes_the_foreground_slot(
    tmp_path: Path, captured_supervisor: type[SupervisorCapture]
) -> None:
    runtime = RuntimePlan.from_mapping(runtime_document(tmp_path))

    assert run(runtime, job=("pytest", "-q")) == 42

    (supervisor,) = captured_supervisor.instances
    (child,) = supervisor.children
    assert child.name == "job"
    assert child.foreground is True
    assert child.command == ("pytest", "-q")
    assert child.working_directory == "/workspace/project"
    # Headless preparation is the same as interactive minus the GUI child.
    assert (tmp_path / "idea.properties").is_file()


def test_entrypoint_main_accepts_forwarded_arguments(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert "usage: devcapsule runtime RUNTIME_PLAN.json" in capsys.readouterr().out

    assert main([]) == 2
    assert "usage: devcapsule runtime RUNTIME_PLAN.json" in capsys.readouterr().err

    assert main([str(tmp_path / "missing.json")]) == 2
    assert "cannot read runtime plan" in capsys.readouterr().err

    assert main([str(tmp_path / "missing.json"), "--", "true"]) == 2
    assert "cannot read runtime plan" in capsys.readouterr().err

    assert main([str(tmp_path / "missing.json"), "--"]) == 2
    assert "usage: devcapsule runtime RUNTIME_PLAN.json" in capsys.readouterr().err


def test_contract_round_trips_the_logs_section(tmp_path: Path) -> None:
    from devcapsule.container_runtime.contract import LogsPlan

    document = runtime_document(tmp_path)
    document["logs"] = {"directory": "/var/log/devcapsule"}
    plan = RuntimePlan.from_mapping(document)
    assert plan.logs == LogsPlan("/var/log/devcapsule")
    assert plan.to_mapping()["logs"] == {"directory": "/var/log/devcapsule"}
    assert RuntimePlan.from_mapping(plan.to_mapping()) == plan
    assert RuntimePlan.from_mapping(runtime_document(tmp_path)).logs is None
    assert "logs" not in RuntimePlan.from_mapping(runtime_document(tmp_path)).to_mapping()
    assert RuntimePlan.from_mapping({**document, "logs": None}).logs is None
    assert plan.with_logs(LogsPlan("/elsewhere")).logs == LogsPlan("/elsewhere")


@pytest.mark.parametrize("logs_value, message", [
    ("text", "logs must be an object"),
    ({"directory": "/var/log/devcapsule", "extra": 1}, "logs must not carry extra"),
    ({"directory": "relative"}, "logs.directory must be an absolute normalized container path"),
    ({"directory": "/var/../log"}, "logs.directory must be an absolute normalized container path"),
    ({}, "logs.directory must be"),
])
def test_contract_rejects_malformed_logs(tmp_path: Path, logs_value: object, message: str) -> None:
    with pytest.raises(RuntimePlanError, match=message):
        RuntimePlan.from_mapping({**runtime_document(tmp_path), "logs": logs_value})


def test_entrypoint_gives_every_child_its_own_log_file_when_the_plan_says_where(
    tmp_path: Path, captured_supervisor: type[SupervisorCapture]
) -> None:
    from devcapsule import logs

    document = runtime_document(tmp_path)
    document["logs"] = {"directory": str(tmp_path / "logs")}
    try:
        assert run(RuntimePlan.from_mapping(document)) == 42
        (supervisor,) = captured_supervisor.instances
        assert [child.log_path for child in supervisor.children] == [str(tmp_path / "logs" / "devcapsule-jetbrains.log")]
        assert supervisor.log_owner == (1000, 1001)
        assert (tmp_path / "logs" / "devcapsule-supervisor.log").is_file()
        assert run(RuntimePlan.from_mapping(document), job=("pytest",)) == 42
        assert [child.log_path for child in captured_supervisor.instances[-1].children] == [str(tmp_path / "logs" / "devcapsule-job.log")]

        captured_supervisor.instances.clear()
        assert run(RuntimePlan.from_mapping(runtime_document(tmp_path))) == 42
        (plain,) = captured_supervisor.instances
        assert [child.log_path for child in plain.children] == [None]
        assert plain.log_owner == (1000, 1001)
    finally:
        logs.reset()


def test_contract_carries_the_rotation_both_or_neither(tmp_path: Path) -> None:
    from devcapsule.container_runtime.contract import LogsPlan

    document = runtime_document(tmp_path)
    document["logs"] = {"directory": "/var/log/devcapsule", "segment_bytes": 8388608, "rotations": 4}
    plan = RuntimePlan.from_mapping(document)
    assert plan.logs == LogsPlan("/var/log/devcapsule", 8388608, 4) and plan.logs.rotates
    assert plan.to_mapping()["logs"] == document["logs"]
    assert RuntimePlan.from_mapping(plan.to_mapping()) == plan
    assert not LogsPlan("/var/log/devcapsule").rotates
    assert LogsPlan.from_mapping({"directory": "/var/log/devcapsule", "segment_bytes": 0, "rotations": 0}, "logs") == LogsPlan("/var/log/devcapsule")
    for logs_value, message in (
        ({"directory": "/var/log/devcapsule", "segment_bytes": 0}, "go together"),
        ({"directory": "/var/log/devcapsule", "rotations": 0}, "go together"),
        ({"directory": "/var/log/devcapsule", "segment_bytes": 1}, "go together"),
        ({"directory": "/var/log/devcapsule", "rotations": 1}, "go together"),
        ({"directory": "/var/log/devcapsule", "segment_bytes": -1, "rotations": 1}, "segment_bytes must be a non-negative integer"),
        ({"directory": "/var/log/devcapsule", "segment_bytes": 1, "rotations": True}, "rotations must be a non-negative integer"),
        ({"directory": "/var/log/devcapsule", "segment_bytes": "8M", "rotations": 1}, "segment_bytes must be a non-negative integer"),
    ):
        with pytest.raises(RuntimePlanError, match=message):
            RuntimePlan.from_mapping({**runtime_document(tmp_path), "logs": logs_value})


def test_entrypoint_passes_the_plans_rotation_to_every_writer_and_defaults_without_it(
    tmp_path: Path, captured_supervisor: type[SupervisorCapture]
) -> None:
    from devcapsule import logs
    from devcapsule.container_runtime.entrypoint import log_rotation

    document = runtime_document(tmp_path)
    document["logs"] = {"directory": str(tmp_path / "logs"), "segment_bytes": 2048, "rotations": 3}
    try:
        assert run(RuntimePlan.from_mapping(document)) == 42
        supervisor = captured_supervisor.instances[-1]
        assert [child.name for child in supervisor.children] == ["jetbrains"]
        assert (supervisor.segment_bytes, supervisor.rotations) == (2048, 3)
        handler = next(h for h in logging.getLogger().handlers if isinstance(h, logs._SessionFileHandler))
        assert handler._file is not None and handler._file.path == tmp_path / "logs" / "devcapsule-supervisor.log"
        assert (handler._file._segment, handler._file._rotations) == (2048, 3)

        document["logs"] = {"directory": str(tmp_path / "plain")}
        assert run(RuntimePlan.from_mapping(document)) == 42
        supervisor = captured_supervisor.instances[-1]
        assert (supervisor.segment_bytes, supervisor.rotations) == (logs.MAXIMUM_SEGMENT_BYTES, logs.ROTATIONS)
        assert log_rotation(RuntimePlan.from_mapping(runtime_document(tmp_path))) == (logs.MAXIMUM_SEGMENT_BYTES, logs.ROTATIONS)
    finally:
        logs.reset()
