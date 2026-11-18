"""Recursive preparation against real filesystem staging and Unix socket ownership."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import socket
import sys

import pytest

from devcapsule.container_runtime.contract import RuntimePlan
from devcapsule.recursive_dogfood import (
    RECURSIVE_E2E_ENABLED_ENV,
    ContainerInspection,
    Finding,
    Mount,
    PreflightError,
    PreflightReport,
    recursive_e2e_launch_environment,
    require_recursive_e2e_project,
)
from devcapsule.recursive_host import HostContextError, HostDaemonLaunchContext, RecursiveStagingArea
from devcapsule.recursive_orchestrator import (
    RecursiveE2EError,
    prepare_recursive_e2e_dry_run,
)

pytestmark = pytest.mark.integration


@dataclass
class RecursiveFixture:
    project: Path
    home: Path
    runtime_plan: Path
    xauthority: Path
    docker_socket: Path
    report: PreflightReport
    socket_handle: socket.socket


@pytest.fixture
def recursive_fixture(tmp_path: Path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    home.mkdir()
    (project / "devcapsule-src").mkdir()
    (project / "devcapsule-src" / "pyproject.toml").write_text(
        '[project]\nname = "devcapsule"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    runtime_plan = tmp_path / "runtime-plan.json"
    plan = RuntimePlan.from_mapping(
        {
            "version": 1,
            "project_path": "/workspace/project",
            "home": str(home),
            "identity": {"uid": 1000, "gid": 1000, "user": "developer"},
            "state_slots": [],
            "component": {
                "id": "pycharm",
                "adapter": "jetbrains",
                "configuration": {},
            },
        }
    )
    runtime_plan.write_text(plan.to_json() + "\n", encoding="utf-8")
    xauthority = tmp_path / "xauthority"
    xauthority.write_bytes(b"test-xauthority-cookie")
    docker_socket = tmp_path / "docker.sock"
    socket_handle = socket.socket(socket.AF_UNIX)
    socket_handle.bind(str(docker_socket))
    mounts = (
        Mount("/host/private/project", str(project), "bind", True),
        Mount("/host/private/home", str(home), "bind", True),
        Mount("/host/private/runtime-plan", str(runtime_plan), "bind", False),
        Mount("/host/private/xauthority", str(xauthority), "bind", False),
        Mount("/host/private/docker.sock", str(docker_socket), "bind", True),
        Mount("/host/private/x11", "/tmp/.X11-unix", "bind", False),
    )
    container = ContainerInspection(
        identity="a" * 64,
        name="dogfood-current",
        image="sha256:" + "b" * 64,
        source_revision="c" * 40,
        network_mode="host",
        mounts=mounts,
        upper_directory="/host/private/overlay/diff",
    )
    report = PreflightReport(
        findings=(Finding("pass", "preflight", "Ready."),),
        facts={},
        mounts=mounts,
        container=container,
    )
    fixture = RecursiveFixture(
        project,
        home,
        runtime_plan,
        xauthority,
        docker_socket,
        report,
        socket_handle,
    )
    try:
        yield fixture
    finally:
        socket_handle.close()


def environment(fixture: RecursiveFixture) -> dict[str, str]:
    return {
        "DOCKER_HOST": f"unix://{fixture.docker_socket}",
        "XAUTHORITY": str(fixture.xauthority),
    }


def test_recursive_project_identity_uses_packaging_metadata(tmp_path: Path) -> None:
    """Only DevCapsule metadata identifies the checkout, including from its source directory."""
    project = tmp_path / "project"
    distribution_root = project / "devcapsule-src"
    distribution_root.mkdir(parents=True)
    metadata = distribution_root / "pyproject.toml"
    metadata.write_text('[project]\nname = "another-project"\n', encoding="utf-8")

    with pytest.raises(PreflightError, match="repository self-test"):
        require_recursive_e2e_project(project)

    metadata.write_text('[project]\nname = "devcapsule"\n', encoding="utf-8")

    assert require_recursive_e2e_project(distribution_root) == project.resolve()


def test_normal_project_launch_derives_only_a_downgradable_readiness_marker(
    recursive_fixture: RecursiveFixture,
) -> None:
    """Readiness requires this checkout, host Docker access and no explicit opt-out."""
    enabled = recursive_e2e_launch_environment(
        recursive_fixture.project,
        docker_daemon="host-socket",
        disabled=False,
    )
    disabled = recursive_e2e_launch_environment(
        recursive_fixture.project,
        docker_daemon="host-socket",
        disabled=True,
    )
    unauthorized = recursive_e2e_launch_environment(
        recursive_fixture.project,
        docker_daemon="none",
        disabled=False,
    )

    assert enabled == {RECURSIVE_E2E_ENABLED_ENV: "1"}
    assert disabled == {RECURSIVE_E2E_ENABLED_ENV: "0"}
    assert unauthorized == {RECURSIVE_E2E_ENABLED_ENV: "0"}


@pytest.mark.skipif(sys.platform != "linux", reason="the recursive dogfood flow is Linux-only")
def test_public_dry_run_is_unique_redacted_and_cleans_owned_staging(
    recursive_fixture: RecursiveFixture,
) -> None:
    """Independent preparations redact host paths and remove their owned staging directories."""
    first = prepare_recursive_e2e_dry_run(
        recursive_fixture.report,
        checkout=recursive_fixture.project,
        runtime_plan_path=recursive_fixture.runtime_plan,
        environ=environment(recursive_fixture),
    )
    second = prepare_recursive_e2e_dry_run(
        recursive_fixture.report,
        checkout=recursive_fixture.project,
        runtime_plan_path=recursive_fixture.runtime_plan,
        environ=environment(recursive_fixture),
    )

    assert first.run_id != second.run_id
    assert first.cleanup_complete is True
    assert second.cleanup_complete is True
    assert first.to_mapping()["docker_mutation_performed"] is False
    encoded = first.to_json()
    assert "/host/private" not in encoded
    assert "<redacted-host-path>" in encoded
    workspace = recursive_fixture.home / ".local/share/devcapsule/e2e-workspaces"
    assert not (workspace / first.run_id).exists()
    assert not (workspace / second.run_id).exists()


@pytest.mark.skipif(sys.platform != "linux", reason="the recursive dogfood flow is Linux-only")
def test_public_dry_run_cleans_after_preparation_failure(
    recursive_fixture: RecursiveFixture,
) -> None:
    """An oversized Xauthority file fails preparation and removes the owned workspace."""
    recursive_fixture.xauthority.write_bytes(b"x" * (1024 * 1024 + 1))
    run_id = "d" * 32

    with pytest.raises(RecursiveE2EError, match="Xauthority material exceeds the 1 MiB staging limit"):
        prepare_recursive_e2e_dry_run(
            recursive_fixture.report,
            checkout=recursive_fixture.project,
            runtime_plan_path=recursive_fixture.runtime_plan,
            environ=environment(recursive_fixture),
            run_id=run_id,
        )

    run_root = (
        recursive_fixture.home
        / ".local/share/devcapsule/e2e-workspaces"
        / run_id
    )
    assert not run_root.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="the recursive dogfood flow is Linux-only")
def test_keep_on_failure_preserves_only_the_owned_run(
    recursive_fixture: RecursiveFixture,
) -> None:
    """An oversized Xauthority file preserves the named workspace only when requested."""
    recursive_fixture.xauthority.write_bytes(b"x" * (1024 * 1024 + 1))
    run_id = "e" * 32

    with pytest.raises(RecursiveE2EError, match="Xauthority material exceeds the 1 MiB staging limit.*preserved owned workspace") as failure:
        prepare_recursive_e2e_dry_run(
            recursive_fixture.report,
            checkout=recursive_fixture.project,
            runtime_plan_path=recursive_fixture.runtime_plan,
            environ=environment(recursive_fixture),
            keep_on_failure=True,
            run_id=run_id,
        )

    run_root = (
        recursive_fixture.home
        / ".local/share/devcapsule/e2e-workspaces"
        / run_id
    )
    assert failure.value.preserved_workspace == run_root
    assert run_root.is_dir()


@pytest.mark.skipif(sys.platform != "linux", reason="the recursive dogfood flow is Linux-only")
def test_contained_display_dry_run_forwards_no_host_x11(
    recursive_fixture: RecursiveFixture, tmp_path: Path
) -> None:
    """A capsule on its own desktop has no host X socket or credential to forward."""

    from devcapsule.container_runtime.contract import DisplayPlan

    plan = RuntimePlan.from_file(recursive_fixture.runtime_plan).with_display(
        DisplayPlan.contained("127.0.0.1", 40000, "/run/devcapsule-display-token")
    )
    recursive_fixture.runtime_plan.write_text(plan.to_json() + "\n", encoding="utf-8")
    container = recursive_fixture.report.container
    assert container is not None
    mounts = tuple(m for m in container.mounts if m.destination not in ("/tmp/.X11-unix", str(recursive_fixture.xauthority)))
    report = PreflightReport(
        findings=recursive_fixture.report.findings,
        facts={},
        mounts=mounts,
        container=ContainerInspection(
            identity=container.identity,
            name=container.name,
            image=container.image,
            source_revision=container.source_revision,
            network_mode=container.network_mode,
            mounts=mounts,
            upper_directory=container.upper_directory,
        ),
    )
    result = prepare_recursive_e2e_dry_run(
        report,
        checkout=recursive_fixture.project,
        runtime_plan_path=recursive_fixture.runtime_plan,
        environ={"DOCKER_HOST": f"unix://{recursive_fixture.docker_socket}"},  # no XAUTHORITY at all
    )
    assert "xauthority" not in result.staged_launch.by_name()
    assert not [bind for bind in result.bind_mounts if bind.destination == "/tmp/.X11-unix"]
    assert result.cleanup_complete is True


def staging_context(fixture: RecursiveFixture) -> HostDaemonLaunchContext:
    return HostDaemonLaunchContext.for_recursive_dogfood(
        fixture.report,
        persistent_home=fixture.home,
        project=fixture.project,
        runtime_plan=fixture.runtime_plan,
        docker_socket=fixture.docker_socket,
        x11_socket_directory=None,
        xauthority=None,
        state_paths=(),
    )


@pytest.mark.parametrize("docker_gid", [0, 998, 1000])
def test_staged_groups_accept_zero_without_duplicate_entries(
    recursive_fixture: RecursiveFixture, docker_gid: int,
) -> None:
    """Zero, distinct and primary Docker groups grant membership with one entry per GID."""
    fixture = recursive_fixture
    plan = RuntimePlan.from_file(fixture.runtime_plan)
    with RecursiveStagingArea(staging_context(fixture), "f" * 32) as staging:
        staging.prepare_launch_files(
            plan, xauthority=None, host_docker_gid=docker_gid, shadow_last_change=21000,
        )
        rows = [line.split(":") for line in (staging.staging_root / "group").read_text().splitlines()]
        gids = [int(row[2]) for row in rows]
        assert len(gids) == len(set(gids))
        group = next(row for row in rows if int(row[2]) == docker_gid)
        if docker_gid != plan.identity.gid:
            assert plan.identity.user in group[3].split(",")
        assert next(row for row in rows if row[0] == "root")[2] == "0"


@pytest.mark.parametrize("docker_gid", [-1, True, 1.5])
def test_staging_rejects_invalid_docker_group(
    recursive_fixture: RecursiveFixture, docker_gid: int,
) -> None:
    """Accepting group zero does not admit negative, boolean or fractional group IDs."""
    fixture = recursive_fixture
    with RecursiveStagingArea(staging_context(fixture), "f" * 32) as staging:
        with pytest.raises(HostContextError, match="host Docker group ID must be a non-negative integer"):
            staging.prepare_launch_files(
                RuntimePlan.from_file(fixture.runtime_plan),
                xauthority=None, host_docker_gid=docker_gid, shadow_last_change=21000,
            )
