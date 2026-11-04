"""Unit tests of ``devcapsule/recursive_successor_plan.py``: the expected plan of a recursive successor launch.

The Docker arguments come from the real launcher's planning; inspections are constructed.
"""
from __future__ import annotations

from pathlib import Path
import socket

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.container_runtime.contract import Identity, RuntimePlan
from devcapsule.host_open import HOST_OPEN_BROWSER, HOST_OPEN_SOCKET_DESTINATION, HOST_OPEN_SOCKET_ENV
from devcapsule.launch.pycharm import DockerMode, PycharmRunOptions
from devcapsule.launch.pycharm._launcher import TempRuntimeFiles, build_docker_args, build_run_config
from devcapsule.materialization import RUNTIME_PLAN_PATH
from devcapsule.platforms import Platform
from devcapsule.recursive_successor_plan import ExpectedSuccessorPlan, SuccessorPlanError, compare_inspection
from tests.test_recursive_successor_plan import (
    IMAGE_IDENTITY,
    IMAGE_LABELS,
    IMAGE_REFERENCE,
    RUNTIME_PLAN_DIGEST,
    build_plan,
    docker_args,
    matching_inspection,
)


@pytest.mark.parametrize("enable_sudo", [False, True])
def test_plan_models_every_flag_the_real_launcher_emits(tmp_path: Path, enable_sudo: bool) -> None:
    """The plan models every flag the launcher emits, since a launch fails closed on an unmodelled one."""

    project = tmp_path / "project"
    project.mkdir()
    env = {
        "DISPLAY": ":1",
        "HOME": str(tmp_path / "home"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "PYCHARM_GIT_IDENTITY_FROM_HOST": "0",
    }
    browser_socket = tmp_path / "host-open.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as broker:
        broker.bind(str(browser_socket))
        env[HOST_OPEN_SOCKET_ENV] = str(browser_socket)
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="host",
                memory_limit_bytes=8589934592,
                enable_sudo=enable_sudo,
                debug_native=True,
                runtime_plan=RuntimePlan.for_component(
                    pycharm_runtime_template(),
                    project_path="/workspace/project",
                    home="/home/devcapsule",
                    identity=Identity(1000, 1000, "developer"),
                ),
                use_image_process=True,
                additional_environment={
                    "DEVCAPSULE_RECURSIVE_E2E": "1",
                    "DEVCAPSULE_RUN_ID": "b2093d85912fa34ac1324e1da26a9dcd",
                },
                enable_host_browser=True,
                extra_docker_args=[
                    "--pull=never",
                    "--label",
                    "devcapsule.e2e.managed=true",
                    "--label",
                    "devcapsule.e2e.role=successor",
                ],
            ),
            env,
        )
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        console_token_file=tmp_path / "console-token",
        shadow_file=tmp_path / "shadow",
        sudoers_file=tmp_path / "sudoers",
        runtime_plan_file=tmp_path / "runtime-plan",
    )
    args = build_docker_args(config, files, env)

    plan = ExpectedSuccessorPlan.from_docker_args(
        args,
        image_reference=IMAGE_REFERENCE,
        image_identity=IMAGE_IDENTITY,
        image_labels=IMAGE_LABELS,
        runtime_plan_destination=RUNTIME_PLAN_PATH,
        runtime_plan_digest=RUNTIME_PLAN_DIGEST,
    )

    assert plan.network_mode == "host"
    assert plan.memory_limit_bytes == 8589934592
    assert plan.environment["DEVCAPSULE_RECURSIVE_E2E"] == "1"
    assert plan.environment["DEVCAPSULE_RUN_ID"] == "b2093d85912fa34ac1324e1da26a9dcd"
    assert plan.environment["BROWSER"] == HOST_OPEN_BROWSER
    assert plan.environment[HOST_OPEN_SOCKET_ENV] == str(HOST_OPEN_SOCKET_DESTINATION)
    browser_mount = next(
        mount for mount in plan.mounts if mount.destination == str(HOST_OPEN_SOCKET_DESTINATION)
    )
    assert browser_mount.source == str(browser_socket)
    assert browser_mount.read_only is True
    assert plan.labels["devcapsule.e2e.role"] == "successor"
    assert "SYS_PTRACE" in plan.cap_add
    assert RUNTIME_PLAN_PATH in {mount.destination for mount in plan.mounts}
    assert plan.read_only_root is not enable_sudo
    if enable_sudo:
        assert plan.group_add and plan.cap_drop == ()
    else:
        assert plan.cap_drop == ("ALL",)
        assert "no-new-privileges" in plan.security_opt


@pytest.mark.parametrize("spelling", [["--platform=linux/amd64"], ["--platform", "linux/amd64"]])
def test_an_emulated_launch_plans_its_platform_and_the_successor_must_run_it(spelling: list[str]) -> None:
    """An emulated launch's plan names its platform in either Docker spelling, keeps it when retained, and refuses a successor that ran another."""
    # The launcher names the platform when the daemon emulates it; both of
    # Docker's spellings parse, and a successor that ran another is refused.
    plan = build_plan([*docker_args(), *spelling])
    assert plan.platform == "linux/amd64"
    inspection = matching_inspection(plan)
    inspection["ImageManifestDescriptor"] = {"platform": {"os": "linux", "architecture": "amd64"}}
    compare_inspection(plan, inspection)
    inspection["ImageManifestDescriptor"] = {"platform": {"os": "linux", "architecture": "arm64"}}
    with pytest.raises(SuccessorPlanError, match="successor platform does not match the planned --platform"):
        compare_inspection(plan, inspection)
    # The independent inspection reloads the retained plan, platform included;
    # a native plan's retained form is unchanged.
    assert ExpectedSuccessorPlan.from_mapping(plan.to_mapping(show_host_paths=True)) == plan
    assert "platform" not in build_plan(docker_args()).to_mapping()
