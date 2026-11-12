from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import socket
import stat
from typing import cast

import pytest

from devcapsule.container_runtime.contract import RuntimePlan
from devcapsule.recursive_dogfood import (
    ContainerInspection,
    Finding,
    Mount,
    PreflightReport,
)
from devcapsule.recursive_host import (
    GROUP_DESTINATION,
    PASSWD_DESTINATION,
    RUNTIME_PLAN_DESTINATION,
    SHADOW_DESTINATION,
    SUDOERS_DESTINATION,
    XAUTHORITY_DESTINATION,
    HostContextError,
    HostDaemonLaunchContext,
    MountRequirement,
    PathAccess,
    PathKind,
    RecursiveStagingArea,
)

pytestmark = pytest.mark.legacy


@dataclass
class HostLayout:
    home: Path
    project: Path
    cache: Path
    runtime_plan: Path
    x11: Path
    xauthority: Path
    docker_socket: Path
    outside: Path
    container: ContainerInspection
    socket_handle: socket.socket


@pytest.fixture
def host_layout(tmp_path: Path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    cache = home / ".cache"
    x11 = tmp_path / "x11"
    outside = tmp_path / "outside"
    for directory in (home, project, cache, x11, outside):
        directory.mkdir(parents=True)
    runtime_plan = tmp_path / "runtime-plan.json"
    runtime_plan.write_text("{}\n", encoding="utf-8")
    xauthority = tmp_path / "xauthority"
    xauthority.write_bytes(b"test-xauthority-cookie")
    docker_socket = tmp_path / "docker.sock"
    socket_handle = socket.socket(socket.AF_UNIX)
    socket_handle.bind(str(docker_socket))
    mounts = (
        Mount("/host/home", str(home), "bind", True),
        Mount("/host/cache", str(cache), "bind", True),
        Mount("/host/project", str(project), "bind", True),
        Mount("/host/runtime-plan.json", str(runtime_plan), "bind", False),
        Mount("/host/x11", str(x11), "bind", False),
        Mount("/host/xauthority", str(xauthority), "bind", False),
        Mount("/var/run/docker.sock", str(docker_socket), "bind", True),
    )
    container = ContainerInspection(
        identity="a" * 64,
        name="dogfood-current",
        image="sha256:" + "b" * 64,
        source_revision="c" * 40,
        network_mode="host",
        mounts=mounts,
        upper_directory="/docker/overlay/current/diff",
    )
    layout = HostLayout(
        home,
        project,
        cache,
        runtime_plan,
        x11,
        xauthority,
        docker_socket,
        outside,
        container,
        socket_handle,
    )
    try:
        yield layout
    finally:
        socket_handle.close()


def requirement(
    purpose: str, path: Path, access: PathAccess, kind: PathKind
) -> MountRequirement:
    return MountRequirement(purpose, path, access, kind)


def launch_context(
    layout: HostLayout,
    *,
    extra: tuple[MountRequirement, ...] = (),
) -> HostDaemonLaunchContext:
    return HostDaemonLaunchContext.from_requirements(
        layout.container,
        persistent_home=layout.home,
        requirements=(
            requirement("project", layout.project, PathAccess.write, PathKind.directory),
            requirement(
                "current-runtime-plan", layout.runtime_plan, PathAccess.read, PathKind.file
            ),
            requirement("x11", layout.x11, PathAccess.read, PathKind.directory),
            requirement(
                "xauthority", layout.xauthority, PathAccess.read, PathKind.file
            ),
            requirement(
                "host-docker", layout.docker_socket, PathAccess.write, PathKind.socket
            ),
            *extra,
        ),
    )


def successful_preflight(layout: HostLayout) -> PreflightReport:
    return PreflightReport(
        findings=(Finding("pass", "preflight", "Ready."),),
        facts={},
        mounts=layout.container.mounts,
        container=layout.container,
    )


def successor_runtime_plan() -> RuntimePlan:
    return RuntimePlan.from_mapping(
        {
            "version": 1,
            "project_path": "/workspace/successor-project",
            "home": "/home/devcapsule",
            "identity": {"uid": 1000, "gid": 1000, "user": "developer"},
            "state_slots": [],
            "component": {"id": "pycharm", "adapter": "jetbrains", "configuration": {}},
        }
    )


def test_longest_approved_nested_mount_wins(host_layout: HostLayout) -> None:
    selected = host_layout.cache / "artifact"
    selected.write_text("data", encoding="utf-8")
    context = launch_context(
        host_layout,
        extra=(requirement("cache", host_layout.cache, PathAccess.write, PathKind.directory),),
    )

    translated = context.translate(
        selected, access=PathAccess.write, kind=PathKind.file
    )

    assert str(translated.host_path) == "/host/cache/artifact"
    assert translated.mount_destination == str(host_layout.cache)


def test_unapproved_nested_mount_cannot_fall_back_to_approved_parent(
    host_layout: HostLayout,
) -> None:
    selected = host_layout.cache / "artifact"
    selected.write_text("data", encoding="utf-8")
    context = launch_context(host_layout)

    with pytest.raises(HostContextError, match="not explicitly approved"):
        context.translate(selected, access=PathAccess.read, kind=PathKind.file)


def test_symlink_within_one_mount_translates_canonical_target(host_layout: HostLayout) -> None:
    target = host_layout.home / "state" / "item"
    target.parent.mkdir()
    target.write_text("data", encoding="utf-8")
    (host_layout.home / "state-link").symlink_to(target.parent, target_is_directory=True)
    context = launch_context(host_layout)

    translated = context.translate(
        host_layout.home / "state-link" / "item",
        access=PathAccess.read,
        kind=PathKind.file,
    )

    assert translated.container_path == target
    assert str(translated.host_path) == "/host/home/state/item"


def test_symlink_crossing_mount_boundary_fails_closed(host_layout: HostLayout) -> None:
    target = host_layout.project / "item"
    target.write_text("data", encoding="utf-8")
    (host_layout.home / "project-link").symlink_to(host_layout.project, target_is_directory=True)
    context = launch_context(host_layout)

    with pytest.raises(HostContextError, match="across a Docker mount boundary"):
        context.translate(
            host_layout.home / "project-link" / "item",
            access=PathAccess.read,
            kind=PathKind.file,
        )


def test_traversal_and_unmapped_paths_fail_closed(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    traversal = host_layout.home / ".." / "project"

    with pytest.raises(HostContextError, match="absolute, normalized"):
        context.translate(traversal, access=PathAccess.read, kind=PathKind.directory)
    with pytest.raises(HostContextError, match="not backed by a Docker mount"):
        context.translate(
            host_layout.outside,
            access=PathAccess.read,
            kind=PathKind.directory,
        )


def test_deleted_path_fails_closed(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    deleted = host_layout.home / "deleted"

    with pytest.raises(HostContextError, match="missing or inaccessible"):
        context.translate(deleted, access=PathAccess.read, kind=PathKind.file)


def test_file_and_socket_mounts_are_typed(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)

    runtime = context.translate(
        host_layout.runtime_plan,
        access=PathAccess.read,
        kind=PathKind.file,
    )
    docker = context.translate(
        host_layout.docker_socket,
        access=PathAccess.write,
        kind=PathKind.socket,
    )

    assert str(runtime.host_path) == "/host/runtime-plan.json"
    assert str(docker.host_path) == "/var/run/docker.sock"
    with pytest.raises(HostContextError, match="not a directory"):
        context.translate(
            host_layout.runtime_plan,
            access=PathAccess.read,
            kind=PathKind.directory,
        )


def test_read_only_mount_rejects_writable_bind_plan(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)

    with pytest.raises(HostContextError, match="read-only"):
        context.plan_bind(
            host_layout.x11,
            "/tmp/.X11-unix",
            read_only=False,
            kind=PathKind.directory,
        )


def test_malformed_inspected_host_source_is_rejected(host_layout: HostLayout) -> None:
    mounts = tuple(
        Mount("relative/host/home", item.destination, item.kind, item.writable)
        if item.destination == str(host_layout.home)
        else item
        for item in host_layout.container.mounts
    )
    malformed = ContainerInspection(
        host_layout.container.identity,
        host_layout.container.name,
        host_layout.container.image,
        host_layout.container.source_revision,
        host_layout.container.network_mode,
        mounts,
        host_layout.container.upper_directory,
    )

    with pytest.raises(HostContextError, match="absolute normalized host path"):
        HostDaemonLaunchContext.from_requirements(
            malformed,
            persistent_home=host_layout.home,
            requirements=(),
        )


def test_bind_plan_keeps_successor_destination_and_redacts_host_source(
    host_layout: HostLayout,
) -> None:
    context = launch_context(host_layout)
    plan = context.plan_bind(
        host_layout.project,
        "/workspace/successor-project",
        read_only=False,
        kind=PathKind.directory,
    )

    value = plan.to_mapping()
    assert value["container_source"] == str(host_layout.project)
    assert value["host_source"] == "<redacted-host-path>"
    assert value["successor_destination"] == "/workspace/successor-project"
    assert "/host/project" not in json.dumps(value)
    assert plan.to_mapping(show_host_paths=True)["host_source"] == "/host/project"
    with pytest.raises(HostContextError, match="successor destination"):
        context.plan_bind(
            host_layout.project,
            "/workspace/../host",
            read_only=False,
            kind=PathKind.directory,
        )


def test_context_report_redacts_every_host_mapping(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    value = context.to_mapping()
    encoded = json.dumps(value)
    approved = cast(list[dict[str, object]], value["approved_mounts"])
    translated = context.translate(
        host_layout.project,
        access=PathAccess.read,
        kind=PathKind.directory,
    )

    assert "/host/home" not in encoded
    assert "/host/project" not in encoded
    assert "/var/run/docker.sock" not in encoded
    assert all(item["source"] == "<redacted-host-path>" for item in approved)
    assert "/host/project" not in repr(context)
    assert "/host/project" not in repr(translated)
    assert "/host/project" not in repr(host_layout.container.mounts)
    assert "/docker/overlay/current/diff" not in repr(host_layout.container)


def test_recursive_factory_requires_successful_preflight_and_approves_state(
    host_layout: HostLayout,
) -> None:
    state = host_layout.home / "successor-state"
    state.mkdir()
    context = HostDaemonLaunchContext.for_recursive_dogfood(
        successful_preflight(host_layout),
        persistent_home=host_layout.home,
        project=host_layout.project,
        runtime_plan=host_layout.runtime_plan,
        docker_socket=host_layout.docker_socket,
        x11_socket_directory=host_layout.x11,
        xauthority=host_layout.xauthority,
        state_paths=(state,),
    )

    state_bind = context.plan_bind(
        state,
        "/ide-project-state",
        read_only=False,
        kind=PathKind.directory,
    )
    assert str(state_bind.source.host_path) == "/host/home/successor-state"
    failed = PreflightReport(
        findings=(Finding("error", "preflight", "Unsafe."),),
        facts={},
        mounts=host_layout.container.mounts,
        container=host_layout.container,
    )
    with pytest.raises(HostContextError, match="successful recursive preflight"):
        HostDaemonLaunchContext.for_recursive_dogfood(
            failed,
            persistent_home=host_layout.home,
            project=host_layout.project,
            runtime_plan=host_layout.runtime_plan,
            docker_socket=host_layout.docker_socket,
            x11_socket_directory=host_layout.x11,
            xauthority=host_layout.xauthority,
        )


def test_staging_prepares_restrictive_host_backed_launch_files_and_cleans_up(
    host_layout: HostLayout,
) -> None:
    context = launch_context(host_layout)
    run_id = "1" * 32
    run_root = context.workspace_root / run_id

    with RecursiveStagingArea(context, run_id) as staging:
        files = staging.prepare_launch_files(
            successor_runtime_plan(),
            xauthority=host_layout.xauthority,
            host_docker_gid=998,
            sudo_gid=44000,
            shadow_last_change=21000,
        )
        by_name = files.by_name()

        assert stat.S_IMODE(staging.run_root.stat().st_mode) == 0o700
        assert stat.S_IMODE(staging.staging_root.stat().st_mode) == 0o700
        assert stat.S_IMODE(staging.ownership_marker.stat().st_mode) == 0o600
        assert {
            name: stat.S_IMODE(item.container_path.stat().st_mode)
            for name, item in by_name.items()
        } == {
            "runtime-plan": 0o644,
            "passwd": 0o644,
            "group": 0o644,
            "xauthority": 0o600,
            "shadow": 0o600,
            "sudoers-policy": 0o440,
        }
        assert by_name["xauthority"].container_path.read_bytes() == b"test-xauthority-cookie"
        assert by_name["sudoers-policy"].requires_root_owner is True
        assert "host-docker:x:998:developer" in by_name["group"].container_path.read_text()
        assert "ide-sudo:x:44000:developer" in by_name["group"].container_path.read_text()
        assert RuntimePlan.from_file(by_name["runtime-plan"].container_path).project_path == (
            "/workspace/successor-project"
        )
        assert {item.destination for item in files.bind_mounts} == {
            RUNTIME_PLAN_DESTINATION,
            PASSWD_DESTINATION,
            GROUP_DESTINATION,
            XAUTHORITY_DESTINATION,
            SHADOW_DESTINATION,
            SUDOERS_DESTINATION,
        }
        assert all(str(item.source.host_path).startswith("/host/home/") for item in files.bind_mounts)
        sanitized = json.dumps(files.to_mapping())
        assert "/host/home" not in sanitized
        assert "test-xauthority-cookie" not in sanitized
        assert XAUTHORITY_DESTINATION not in sanitized

    assert not run_root.exists()


def test_staging_cleans_up_after_preparation_failure(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    run_id = "2" * 32
    area = RecursiveStagingArea(context, run_id)

    with pytest.raises(PermissionError):
        with area:
            area.staging_root.chmod(0o500)
            area.prepare_launch_files(
                successor_runtime_plan(),
                xauthority=host_layout.xauthority,
                host_docker_gid=998,
            )

    assert not area.run_root.exists()


def test_staging_cleans_up_after_bind_planning_failure(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    run_id = "3" * 32
    area = RecursiveStagingArea(context, run_id)

    with pytest.raises(HostContextError, match="successor destination"):
        with area:
            context.plan_bind(
                host_layout.project,
                "/workspace/../host",
                read_only=False,
                kind=PathKind.directory,
            )

    assert not area.run_root.exists()


def test_staging_cleans_up_after_later_launch_failure(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    area = RecursiveStagingArea(context, "7" * 32)

    with pytest.raises(RuntimeError, match="launch failed"):
        with area:
            area.prepare_launch_files(
                successor_runtime_plan(),
                xauthority=host_layout.xauthority,
                host_docker_gid=998,
            )
            raise RuntimeError("launch failed")

    assert not area.run_root.exists()


def test_keep_on_failure_preserves_only_owned_run_until_explicit_cleanup(
    host_layout: HostLayout,
) -> None:
    context = launch_context(host_layout)
    area = RecursiveStagingArea(context, "4" * 32, keep_on_failure=True)

    with pytest.raises(RuntimeError, match="later failure"):
        with area:
            raise RuntimeError("later failure")

    assert area.run_root.is_dir()
    area.cleanup()
    assert not area.run_root.exists()


def test_cleanup_refuses_mismatched_ownership_marker(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    area = RecursiveStagingArea(context, "5" * 32, keep_on_failure=True)
    with pytest.raises(RuntimeError, match="preserve for inspection"):
        with area:
            raise RuntimeError("preserve for inspection")
    area.ownership_marker.write_text(
        '{"schema_version":1,"run_id":"someone-else"}\n', encoding="utf-8"
    )

    with pytest.raises(HostContextError, match="does not match"):
        area.cleanup()

    assert area.run_root.exists()


def test_preexisting_run_workspace_is_never_reused_or_deleted(host_layout: HostLayout) -> None:
    context = launch_context(host_layout)
    run_id = "6" * 32
    existing = context.workspace_root / run_id
    existing.mkdir(parents=True)
    sentinel = existing / "personal-file"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(HostContextError, match="already exists"):
        with RecursiveStagingArea(context, run_id):
            pass

    assert sentinel.read_text(encoding="utf-8") == "keep"
