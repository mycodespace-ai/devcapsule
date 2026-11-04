from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import socket
import time
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.components.codex import runtime_template as codex_runtime_template
from devcapsule.components.codium import runtime_template as codium_runtime_template
from devcapsule.launch.pycharm import (
    DockerMode,
    IdeConfigMode,
    PycharmRunOptions,
    build_run_config,
)
from devcapsule.container_runtime.contract import INFRASTRUCTURE_FAILURE_EXIT_CODE
from devcapsule.platforms import HostOs, Platform
from devcapsule.launch.pycharm._launcher import (
    AttachedResult,
    display_disclosure,
    describe_run_command,
    console_development_source,
    console_disclosure,
    HostUser,
    PycharmRunError,
    PycharmRunConfig,
    SUDOERS_POLICY,
    SUDOERS_POLICY_PATH,
    TempRuntimeFiles,
    build_docker_args,
    cleanup_temp_runtime_files,
    ensure_sudoers_policy_ownership,
    prepare_temp_runtime_files,
    print_storage_summary,
    remove_abandoned_sudoers_volumes,
    run_pycharm,
    write_user_files,
)
from devcapsule.container_runtime.contract import DisplayPlan, Identity, LogsPlan, RuntimePlan
from devcapsule.launch.session_logs import SESSION_LOG_DESTINATION
from devcapsule.materialization import RUNTIME_PLAN_PATH
from devcapsule.host_open import (
    HOST_OPEN_BROWSER,
    HOST_OPEN_INTEGRATION,
    HOST_OPEN_SOCKET_DESTINATION,
    HOST_OPEN_SOCKET_ENV,
)
from devcapsule.project import plan_project

from devcapsule.container_runtime.contract import ConsolePlan
from devcapsule.display_client import display_url

pytestmark = pytest.mark.legacy

def base_env(tmp_path: Path) -> dict[str, str]:
    return {
        "DISPLAY": ":1",
        "HOME": str(tmp_path / "home"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "PYCHARM_GIT_IDENTITY_FROM_HOST": "0",
    }


def external_runtime_plan() -> RuntimePlan:
    return RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000, "developer"),
    )


def test_external_runtime_plan_is_readable_and_mounted_read_only(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=external_runtime_plan(),
            use_image_process=True,
        ),
        env,
    )
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        assert files.runtime_plan_file is not None
        assert files.runtime_plan_file.stat().st_mode & 0o777 == 0o644
        # The plan now records the transport explicitly, even for passthrough,
        # and the web console, which runs whenever the runtime runs.
        written = RuntimePlan.from_file(files.runtime_plan_file)
        assert written.display == DisplayPlan.host_x11()
        assert written.console == ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token")
        assert written.logs == LogsPlan(SESSION_LOG_DESTINATION, segment_bytes=8 * 1024 * 1024, rotations=4)
        assert written == external_runtime_plan().with_display(DisplayPlan.host_x11()).with_console(written.console).with_logs(written.logs)
        args = build_docker_args(config, files, env)
        assert "JAVA_TOOL_OPTIONS=-Dide.browser.jcef.sandbox.enable=false" in args
        assert "SYS_ADMIN" not in args
        assert "seccomp=unconfined" not in args
        assert "apparmor=unconfined" not in args
        assert (
            f"type=bind,src={files.runtime_plan_file},dst={RUNTIME_PLAN_PATH},ro"
            in args
        )
    finally:
        cleanup_temp_runtime_files(files)
    assert files.runtime_plan_file is not None
    assert not files.runtime_plan_file.exists()


def codium_external_runtime_plan() -> RuntimePlan:
    return RuntimePlan.for_component(
        codium_runtime_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000, "developer"),
    )


def codium_interactive_state_mounts(tmp_path: Path) -> dict[str, tuple[Path, str]]:
    return {
        "codium/user-data": (tmp_path / "slots" / "user-data", "/ide-user-data"),
        "codium/extensions": (tmp_path / "slots" / "extensions", "/ide-extensions"),
        "codium/cache": (tmp_path / "slots" / "cache", "/home/devcapsule/.cache"),
    }


def test_plan_driven_surface_mounts_declared_slots_instead_of_pycharm_paths(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=codium_external_runtime_plan(),
            use_image_process=True,
            interactive_state_mounts=codium_interactive_state_mounts(tmp_path),
        ),
        env,
    )

    assert config.ide_config is None
    assert config.plugins is None
    assert config.ide_system is None
    assert config.ide_log is None
    assert config.tool_cache is None

    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        console_token_file=tmp_path / "console-token",
        runtime_plan_file=tmp_path / "runtime-plan",
    )
    args = build_docker_args(config, files, env)

    assert f"type=bind,src={tmp_path / 'slots' / 'user-data'},dst=/ide-user-data" in args
    assert f"type=bind,src={tmp_path / 'slots' / 'extensions'},dst=/ide-extensions" in args
    assert (
        f"type=bind,src={tmp_path / 'slots' / 'cache'},dst=/home/devcapsule/.cache" in args
    )
    assert not any("dst=/ide-config" in value for value in args)
    assert not any("dst=/ide-plugins" in value for value in args)
    assert not any("dst=/ide-project-state" in value for value in args)
    # Renderer sandboxing is retired (product-owner ruling 2026-09-02):
    # codium runs --no-sandbox and keeps the uniform full hardening.
    assert "no-new-privileges" in args
    assert ["--cap-drop", "ALL"] == args[args.index("--cap-drop") : args.index("--cap-drop") + 2]
    assert "--cap-add" not in args
    # No PyCharm state directories are invented on the host for this surface.
    data_namespace = Path(env["XDG_DATA_HOME"]) / "devcapsule" / "projects" / "by-path"
    assert not list(data_namespace.glob("*/components/pycharm"))


def test_interactive_state_mounts_require_a_runtime_plan(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(PycharmRunError, match="external runtime plan"):
        build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="bridge",
                interactive_state_mounts=codium_interactive_state_mounts(tmp_path),
            ),
            base_env(tmp_path),
        )


def test_interactive_state_mounts_must_belong_to_the_plan_component(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(PycharmRunError, match="Interactive state mount 'codex/home'"):
        build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="bridge",
                runtime_plan=codium_external_runtime_plan(),
                use_image_process=True,
                interactive_state_mounts={
                    "codex/home": (tmp_path / "codex", "/home/devcapsule/.codex"),
                },
            ),
            base_env(tmp_path),
        )


def test_no_sudo_launches_keep_full_hardening_on_every_surface(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    for plan in (external_runtime_plan(), codium_external_runtime_plan()):
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="bridge",
                runtime_plan=plan,
                use_image_process=True,
                interactive_state_mounts=(
                    codium_interactive_state_mounts(tmp_path)
                    if plan.component.id == "codium"
                    else {}
                ),
            ),
            env,
        )
        files = TempRuntimeFiles(
            xauth_file=tmp_path / "xauth",
            passwd_file=tmp_path / "passwd",
            group_file=tmp_path / "group",
            console_token_file=tmp_path / "console-token",
            runtime_plan_file=tmp_path / "runtime-plan",
        )

        args = build_docker_args(config, files, env)

        assert "no-new-privileges" in args
        assert "SYS_ADMIN" not in args


def test_sudo_launches_grant_no_capabilities_beyond_dockers_default(
    tmp_path: Path,
) -> None:
    """Regression for the 2026-09-02 sudo-sandbox bug: the sudo posture is
    Docker's default capability set plus the sudo group — no per-surface
    capability grants, and no setuid-helper posture left to crash the zygote.
    """

    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=codium_external_runtime_plan(),
            use_image_process=True,
            interactive_state_mounts=codium_interactive_state_mounts(tmp_path),
            enable_sudo=True,
        ),
        env,
    )
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        console_token_file=tmp_path / "console-token",
        runtime_plan_file=tmp_path / "runtime-plan",
        shadow_file=tmp_path / "shadow",
        sudoers_file=tmp_path / "sudoers",
    )

    args = build_docker_args(config, files, env)

    assert "--group-add" in args
    assert "--cap-add" not in args
    assert "--cap-drop" not in args
    assert "no-new-privileges" not in args


def test_plan_driven_storage_summary_names_the_surface_and_its_slots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=codium_external_runtime_plan(),
            use_image_process=True,
            interactive_state_mounts=codium_interactive_state_mounts(tmp_path),
        ),
        base_env(tmp_path),
    )

    print_storage_summary(config)

    output = capsys.readouterr().err
    assert "codium storage:" in output
    assert "codium/user-data" in output
    assert "PyCharm config" not in output
    # The unsandboxed-renderer disclosure (product-owner ruling 2026-09-02)
    # keys on the --no-sandbox flag the template carries.
    assert "Chromium renderers run unsandboxed" in output
    assert "Docker's outer isolation is unchanged" in output


def test_detached_lifecycle_changes_only_the_docker_process_flags(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=external_runtime_plan(),
            use_image_process=True,
        ),
        env,
    )
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        console_token_file=tmp_path / "console-token",
        runtime_plan_file=tmp_path / "runtime-plan",
    )

    args = build_docker_args(config, files, env)

    # The launcher owns exactly one lifecycle: attached, removed on exit.
    assert args[:2] == ["--rm", "-i"]
    assert "--detach" not in args and "-d" not in args


def test_jcef_disclosure_is_printed_for_component_policy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=external_runtime_plan(),
            use_image_process=True,
        ),
        base_env(tmp_path),
    )

    print_storage_summary(config)

    disclosure = capsys.readouterr().err
    assert "JCEF's inner Chromium sandbox is disabled" in disclosure
    assert "Docker's outer isolation is unchanged" in disclosure


def test_host_browser_bridge_is_explicit_in_plan_mount_environment_and_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    socket_path = tmp_path / "host-open.sock"

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as broker:
        broker.bind(str(socket_path))
        env[HOST_OPEN_SOCKET_ENV] = str(socket_path)
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="bridge",
                runtime_plan=external_runtime_plan(),
                use_image_process=True,
                enable_host_browser=True,
            ),
            env,
        )
        files = TempRuntimeFiles(
            xauth_file=tmp_path / "xauth",
            passwd_file=tmp_path / "passwd",
            group_file=tmp_path / "group",
            console_token_file=tmp_path / "console-token",
            runtime_plan_file=tmp_path / "runtime-plan",
        )
        args = build_docker_args(config, files, env)
        print_storage_summary(config)

    assert config.runtime_plan is not None
    assert config.runtime_plan.host_integrations == (HOST_OPEN_INTEGRATION,)
    assert f"BROWSER={HOST_OPEN_BROWSER}" in args
    assert f"{HOST_OPEN_SOCKET_ENV}={HOST_OPEN_SOCKET_DESTINATION}" in args
    assert (
        f"type=bind,src={socket_path},dst={HOST_OPEN_SOCKET_DESTINATION},ro" in args
    )
    disclosure = capsys.readouterr().err
    assert "Any process running as the" in disclosure
    assert "capsule user can ask the physical host" in disclosure


def test_host_browser_bridge_can_be_disabled_despite_inherited_environment(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    socket_path = tmp_path / "host-open.sock"

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as broker:
        broker.bind(str(socket_path))
        env[HOST_OPEN_SOCKET_ENV] = str(socket_path)
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                docker_mode=DockerMode.none,
                enable_host_browser=False,
            ),
            env,
        )

    assert config.host_browser_socket is None


def test_physical_host_launcher_owns_browser_broker_for_docker_lifetime(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")

    with (
        patch("devcapsule.host_open.in_container", return_value=False),
        patch("devcapsule.host_open.HostOs.current", return_value=HostOs.LINUX),
        patch("devcapsule.launch.pycharm._launcher.shutil.which", return_value=None),
        patch("devcapsule.launch.pycharm._launcher.run_attached") as run,
    ):
        run.return_value = AttachedResult(0, interrupted=False, stopped=True)
        assert run_pycharm(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                docker_mode=DockerMode.none,
                enable_host_browser=True,
            ),
            env,
        ) == 0

    command = run.call_args.args[0]
    socket_mount = next(
        argument
        for argument in command
        if argument.startswith("type=bind,src=")
        and f"dst={HOST_OPEN_SOCKET_DESTINATION}" in argument
    )
    source = Path(
        next(
            field.removeprefix("src=")
            for field in socket_mount.split(",")
            if field.startswith("src=")
        )
    )
    assert not source.exists()


def test_selected_codex_state_and_explicit_secret_are_delivered(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    env["OPENAI_API_KEY"] = "sk-test-never-in-docker-args"
    runtime = RuntimePlan.for_component(
        pycharm_runtime_template(),
        project_path="/workspace/project",
        home="/home/devcapsule",
        identity=Identity(1000, 1000, "developer"),
        ancillary_templates=(codex_runtime_template(),),
    )
    state = tmp_path / "codex-home"
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=runtime,
            use_image_process=True,
            additional_state_mounts={"codex/home": (state, "/home/devcapsule/.codex")},
            secret_environment=("OPENAI_API_KEY",),
        ),
        env,
    )
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        args = build_docker_args(config, files, env)
    finally:
        cleanup_temp_runtime_files(files)

    assert "CODEX_HOME=/home/devcapsule/.codex" in args
    assert "OPENAI_API_KEY" in args
    assert "sk-test-never-in-docker-args" not in args
    assert f"type=bind,src={state.resolve()},dst=/home/devcapsule/.codex" in args


def test_authorized_runtime_effects_build_the_complete_docker_plan(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    docker_socket = tmp_path / "docker.sock"
    docker_socket.touch()
    home = tmp_path / "persistent-home"
    config_dir = tmp_path / "pycharm-config"
    plugins = tmp_path / "pycharm-plugins"
    system = tmp_path / "pycharm-system"
    log = tmp_path / "pycharm-log"
    cache = tmp_path / "pycharm-cache"
    host_user = HostUser(uid=1000, gid=1000, name="developer", group_name="developer")

    with (
        patch("devcapsule.launch.pycharm._launcher.current_host_user", return_value=host_user),
        patch("devcapsule.launch.pycharm._launcher.is_socket", return_value=True),
    ):
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                persistent_home=home,
                ide_config=config_dir,
                plugins=plugins,
                ide_system=system,
                ide_log=log,
                tool_cache=cache,
                docker_mode=DockerMode.host,
                host_docker_socket=docker_socket,
                enable_sudo=True,
                network_mode="host",
                memory_limit_bytes=8 * 1024**3,
                runtime_plan=external_runtime_plan(),
                use_image_process=True,
            ),
            env,
        )
        with patch("devcapsule.launch.pycharm._launcher.write_xauthority"):
            files = prepare_temp_runtime_files(config, env)
        try:
            assert files.sudoers_file is not None
            assert files.sudoers_directory is not None
            sudoers_directory = files.sudoers_directory
            assert sudoers_directory.stat().st_mode & 0o777 == 0o700
            sudoers_file = files.sudoers_file
            assert sudoers_file.read_text(encoding="utf-8") == SUDOERS_POLICY
            assert sudoers_file.stat().st_mode & 0o777 == 0o440
            args = build_docker_args(config, files, env)
            files.sudoers_volume = "capsule-sudoers"
            volume_args = build_docker_args(config, files, env)
            files.sudoers_volume = None
            files.sudoers_file = None
            with pytest.raises(PycharmRunError, match="shadow and sudoers files"):
                build_docker_args(config, files, env)
            files.sudoers_file = sudoers_file
        finally:
            cleanup_temp_runtime_files(files)

    assert ["--network", "host"] == args[args.index("--network") : args.index("--network") + 2]
    assert ["--memory", str(8 * 1024**3)] == args[args.index("--memory") : args.index("--memory") + 2]
    assert ["--user", "1000:1000"] == args[args.index("--user") : args.index("--user") + 2]
    assert "ENABLE_SUDO=1" in args
    assert f"type=bind,src={sudoers_file},dst={SUDOERS_POLICY_PATH},ro" in args
    # On macOS the policy comes from its volume, not the Mac's file.
    assert f"type=volume,src=capsule-sudoers,volume-subpath=policy,dst={SUDOERS_POLICY_PATH},ro" in volume_args
    assert f"type=bind,src={sudoers_file},dst={SUDOERS_POLICY_PATH},ro" not in volume_args
    assert not sudoers_file.exists()
    assert not sudoers_directory.exists()
    assert "DOCKER_HOST=unix:///run/host-docker.sock" in args
    assert f"DEVCAPSULE_CONTAINER_NAME={config.name}" in args
    assert f"type=bind,src={docker_socket.resolve()},dst=/run/host-docker.sock" in args
    for source, destination in (
        (project.resolve(), "/workspace/project"),
        (home.resolve(), "/home/devcapsule"),
        (config_dir.resolve(), "/ide-config"),
        (plugins.resolve(), "/ide-plugins"),
        (system.resolve(), "/ide-project-state/system"),
        (log.resolve(), "/ide-project-state/log"),
        (cache.resolve(), "/home/devcapsule/.cache"),
    ):
        assert f"type=bind,src={source},dst={destination}" in args
    assert "--read-only" not in args
    assert "--privileged" not in args
    assert "SYS_ADMIN" not in args


@pytest.mark.parametrize("host_os,expected_gid", [(HostOs.LINUX, "file"), (HostOs.DARWIN, 0)])
def test_host_docker_group_follows_where_the_socket_is_owned(tmp_path: Path, host_os, expected_gid) -> None:
    # On Linux the capsule joins the socket file's group. Docker Desktop shows
    # its socket inside the VM as root:root 0660, so a Mac host joins group 0
    # and writes no second group for it.
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    docker_socket = tmp_path / "docker.sock"
    docker_socket.touch()
    gid = docker_socket.stat().st_gid if expected_gid == "file" else expected_gid
    host_user = HostUser(uid=501, gid=20, name="developer", group_name="staff")
    with (
        patch("devcapsule.launch.pycharm._launcher.current_host_user", return_value=host_user),
        patch("devcapsule.launch.pycharm._launcher.is_socket", return_value=True),
        patch("devcapsule.launch.pycharm._launcher.HostOs.current", return_value=host_os),
    ):
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.host,
                host_docker_socket=docker_socket,
                network_mode="bridge",
                runtime_plan=external_runtime_plan(),
                use_image_process=True,
            ),
            env,
        )
        with patch("devcapsule.launch.pycharm._launcher.write_xauthority"):
            files = prepare_temp_runtime_files(config, env)
        try:
            args = build_docker_args(config, files, env)
            groups = files.group_file.read_text(encoding="utf-8")
        finally:
            cleanup_temp_runtime_files(files)

    assert config.host_docker_gid == gid
    assert ["--group-add", str(gid)] == args[args.index("--group-add") : args.index("--group-add") + 2]
    assert ("host-docker:x:" in groups) is (gid not in (0, host_user.gid))


@pytest.mark.parametrize("host_os,effective", [(HostOs.LINUX, "host"), (HostOs.DARWIN, "bridge")])
def test_host_networking_falls_back_to_bridge_on_macos(tmp_path: Path, capsys, host_os, effective) -> None:
    # Docker Desktop's host network is its VM's; the contained desktop would
    # listen where the Mac cannot reach it.
    project = tmp_path / "project"
    project.mkdir()
    with patch("devcapsule.launch.pycharm._launcher.HostOs.current", return_value=host_os):
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="host",
                runtime_plan=external_runtime_plan(),
                use_image_process=True,
            ),
            base_env(tmp_path),
        )
    assert config.network_mode == effective
    assert ("host networking is unavailable on macOS" in capsys.readouterr().err) is (effective == "bridge")


def test_unauthorized_runtime_effects_keep_safe_docker_defaults(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    host_user = HostUser(uid=1000, gid=1000, name="developer", group_name="developer")

    with patch(
        "devcapsule.launch.pycharm._launcher.current_host_user",
        return_value=host_user,
    ):
        config = build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="bridge",
                runtime_plan=external_runtime_plan(),
                use_image_process=True,
            ),
            env,
        )
        with patch("devcapsule.launch.pycharm._launcher.write_xauthority"):
            files = prepare_temp_runtime_files(config, env)
        try:
            assert files.sudoers_file is None
            args = build_docker_args(config, files, env)
        finally:
            cleanup_temp_runtime_files(files)

    assert ["--network", "bridge"] == args[args.index("--network") : args.index("--network") + 2]
    assert "ENABLE_SUDO=0" in args
    assert not any(SUDOERS_POLICY_PATH in argument for argument in args)
    assert "DOCKER_HOST=unix:///run/host-docker.sock" not in args
    assert not any("dst=/run/host-docker.sock" in argument for argument in args)
    assert "--memory" not in args
    assert ["--cap-drop", "ALL"] == args[args.index("--cap-drop") : args.index("--cap-drop") + 2]
    assert "no-new-privileges" in args
    assert "--read-only" in args
    assert "--privileged" not in args


def test_sudoers_ownership_helper_is_constrained(tmp_path: Path) -> None:
    policy = tmp_path / "sudoers"
    policy.write_text(SUDOERS_POLICY, encoding="utf-8")
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        console_token_file=tmp_path / "console-token",
        sudoers_file=policy,
    )
    config = cast(
        PycharmRunConfig,
        SimpleNamespace(enable_sudo=True, image="devcapsule-local-pycharm:canonical",
                        capsule_platform=Platform.LINUX_AMD64, daemon_architecture="amd64"),
    )

    with (
        patch("devcapsule.launch.pycharm._launcher.os.chown", side_effect=PermissionError),
        patch("devcapsule.launch.pycharm._launcher.file_owner_uid", return_value=0),
        patch("devcapsule.launch.pycharm._launcher.subprocess.run") as run,
    ):
        run.return_value = SimpleNamespace(returncode=0, stderr="")
        ensure_sudoers_policy_ownership(config, files, {"PATH": "/usr/bin"})

    command = run.call_args.args[0]
    assert command[:3] == ["docker", "run", "--rm"]
    assert ["--network", "none"] == command[command.index("--network") : command.index("--network") + 2]
    assert ["--cap-drop", "ALL"] == command[command.index("--cap-drop") : command.index("--cap-drop") + 2]
    assert ["--cap-add", "CHOWN"] == command[command.index("--cap-add") : command.index("--cap-add") + 2]
    assert "no-new-privileges" in command
    assert "--read-only" in command
    assert "--pull=never" in command
    assert "0:0" == command[-2]


def test_sudoers_ownership_helper_failure_is_actionable(tmp_path: Path) -> None:
    policy = tmp_path / "sudoers"
    policy.write_text(SUDOERS_POLICY, encoding="utf-8")
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        console_token_file=tmp_path / "console-token",
        sudoers_file=policy,
    )
    config = cast(
        PycharmRunConfig,
        SimpleNamespace(enable_sudo=True, image="devcapsule-local-pycharm:canonical",
                        capsule_platform=Platform.LINUX_AMD64, daemon_architecture="amd64"),
    )

    with (
        patch("devcapsule.launch.pycharm._launcher.os.chown", side_effect=PermissionError),
        patch("devcapsule.launch.pycharm._launcher.subprocess.run") as run,
    ):
        run.return_value = SimpleNamespace(returncode=1, stderr="daemon denied helper")
        with pytest.raises(PycharmRunError, match="daemon denied helper"):
            ensure_sudoers_policy_ownership(config, files, {})


def _macos_sudo_files(tmp_path: Path) -> tuple[PycharmRunConfig, TempRuntimeFiles]:
    policy = tmp_path / "sudoers"
    policy.write_text(SUDOERS_POLICY, encoding="utf-8")
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        sudoers_file=policy,
    )
    config = cast(
        PycharmRunConfig,
        SimpleNamespace(enable_sudo=True, image="devcapsule-local-pycharm:canonical", name="capsule",
                        capsule_platform=Platform.LINUX_AMD64, daemon_architecture="arm64"),
    )
    return config, files


def test_macos_sudo_policy_is_written_into_a_volume_by_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Docker Desktop shares Mac files as the Mac user: no chown makes a
    # bind-mounted policy root's, so the policy lives in a volume.
    monkeypatch.setattr(HostOs, "current", classmethod(lambda cls: HostOs.DARWIN))
    config, files = _macos_sudo_files(tmp_path)

    with (
        patch("devcapsule.launch.pycharm._launcher.os.chown") as chown,
        patch("devcapsule.launch.pycharm._launcher.subprocess.run") as run,
    ):
        run.return_value = SimpleNamespace(returncode=0, stderr="", stdout="")
        ensure_sudoers_policy_ownership(config, files, {"PATH": "/usr/bin"})

    chown.assert_not_called()
    assert files.sudoers_volume == "capsule-sudoers"
    listed, create, write = (call.args[0] for call in run.call_args_list)
    assert listed == ["docker", "volume", "ls", "--quiet", "--filter",
                      "label=devcapsule.purpose=development-sudo-policy"]
    assert create == ["docker", "volume", "create", "--label", "devcapsule.purpose=development-sudo-policy",
                      "capsule-sudoers"]
    assert write[:4] == ["docker", "run", "--rm", "-i"]
    assert "--platform=linux/amd64" in write
    assert ["--network", "none"] == write[write.index("--network") : write.index("--network") + 2]
    assert ["--cap-drop", "ALL"] == write[write.index("--cap-drop") : write.index("--cap-drop") + 2]
    assert "--cap-add" not in write
    assert ["--user", "0:0"] == write[write.index("--user") : write.index("--user") + 2]
    assert {"--read-only", "--pull=never", "no-new-privileges"} <= set(write)
    assert "type=volume,src=capsule-sudoers,dst=/policy" in write
    assert write[-1].startswith("umask 0337;")
    assert write[-1].endswith("/policy/policy")
    assert run.call_args_list[2].kwargs["input"] == SUDOERS_POLICY


def test_macos_sudo_policy_failure_removes_its_volume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(HostOs, "current", classmethod(lambda cls: HostOs.DARWIN))
    config, files = _macos_sudo_files(tmp_path)

    with patch("devcapsule.launch.pycharm._launcher.subprocess.run") as run:
        run.side_effect = [
            SimpleNamespace(returncode=0, stderr="", stdout=""),
            SimpleNamespace(returncode=0, stderr=""),
            SimpleNamespace(returncode=125, stderr="no such image"),
            SimpleNamespace(returncode=0, stderr=""),
        ]
        with pytest.raises(PycharmRunError, match="no such image"):
            ensure_sudoers_policy_ownership(config, files, {})

    assert run.call_args_list[-1].args[0] == ["docker", "volume", "rm", "--force", "capsule-sudoers"]
    assert files.sudoers_volume is None


def test_only_an_old_policy_volume_counts_as_abandoned() -> None:
    # A concurrent launch's fresh volume is unused until its capsule starts.
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()
    with patch("devcapsule.launch.pycharm._launcher.subprocess.run") as run:
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="killed-sudoers\nconcurrent-sudoers\n"),
            SimpleNamespace(returncode=0, stdout=f"killed-sudoers {old}\nconcurrent-sudoers {fresh}\n"),
            SimpleNamespace(returncode=0),
        ]
        remove_abandoned_sudoers_volumes({})

    assert run.call_args_list[-1].args[0] == ["docker", "volume", "rm", "killed-sudoers"]


def test_sudo_banner_is_printed_after_complete_policy_preparation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")

    with (
        patch("devcapsule.launch.pycharm._launcher.shutil.which", return_value=None),
        patch(
            "devcapsule.launch.pycharm._launcher.ensure_sudoers_policy_ownership",
            side_effect=lambda _config, files, _env: setattr(files, "sudoers_volume", "capsule-sudoers"),
        ) as ensure,
        patch("devcapsule.launch.pycharm._launcher.remove_sudoers_policy_volume") as remove,
        patch("devcapsule.launch.pycharm._launcher.run_attached") as run,
    ):
        run.return_value = AttachedResult(0, interrupted=False, stopped=True)
        assert (
            run_pycharm(
                PycharmRunOptions(
                    project=project,
                    capsule_platform=Platform.LINUX_AMD64,
                    image="devcapsule-local-pycharm:canonical",
                    docker_mode=DockerMode.none,
                    network_mode="bridge",
                    enable_sudo=True,
                ),
                env,
            )
            == 0
        )

    ensure.assert_called_once()
    assert "DEVELOPMENT SUDO IS ENABLED" in capsys.readouterr().err
    command = run.call_args.args[0]
    assert any(SUDOERS_POLICY_PATH in argument and "src=capsule-sudoers" in argument for argument in command)
    # The policy volume outlives nothing but the session.
    assert remove.call_args.args[0] == "capsule-sudoers"


def test_sudo_policy_preparation_failure_cleans_files_without_enabled_banner(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")

    with (
        patch("devcapsule.launch.pycharm._launcher.shutil.which", return_value=None),
        patch(
            "devcapsule.launch.pycharm._launcher.ensure_sudoers_policy_ownership",
            side_effect=PycharmRunError("sudo policy failed"),
        ),
        patch(
            "devcapsule.launch.pycharm._launcher.cleanup_temp_runtime_files",
            wraps=cleanup_temp_runtime_files,
        ) as cleanup,
    ):
        with pytest.raises(PycharmRunError, match="sudo policy failed"):
            run_pycharm(
                PycharmRunOptions(
                    project=project,
                    capsule_platform=Platform.LINUX_AMD64,
                    image="devcapsule-local-pycharm:canonical",
                    docker_mode=DockerMode.none,
                    network_mode="bridge",
                    enable_sudo=True,
                ),
                env,
            )

    files = cleanup.call_args.args[0]
    assert files.sudoers_file is not None
    assert files.sudoers_directory is not None
    assert all(
        path is None or not path.exists()
        for path in (
            files.xauth_file,
            files.passwd_file,
            files.group_file,
            files.shadow_file,
            files.sudoers_file,
        )
    )
    assert not files.sudoers_directory.exists()
    assert "DEVELOPMENT SUDO IS ENABLED" not in capsys.readouterr().err


def test_bound_secret_must_exist_on_host(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(PycharmRunError, match="is not set on the host"):
        build_run_config(
            PycharmRunOptions(
                project=project,
                capsule_platform=Platform.LINUX_AMD64,
                docker_mode=DockerMode.none,
                secret_environment=("OPENAI_API_KEY",),
            ),
            base_env(tmp_path),
        )


def test_image_process_uses_oci_command_and_cleans_all_temporary_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    image = "devcapsule-local-pycharm:canonical"
    with (
        patch("devcapsule.launch.pycharm._launcher.shutil.which", return_value=None),
        patch("devcapsule.launch.pycharm._launcher.run_attached") as run,
    ):
        run.return_value = AttachedResult(0, interrupted=False, stopped=True)
        assert (
            run_pycharm(
                PycharmRunOptions(
                    project=project,
                    capsule_platform=Platform.LINUX_AMD64,
                    project_mount="/workspace/project",
                    image=image,
                    docker_mode=DockerMode.none,
                    network_mode="bridge",
                    runtime_plan=external_runtime_plan(),
                    use_image_process=True,
                ),
                env,
            )
            == 0
        )

    command = run.call_args.args[0]
    assert command[-1] == image
    assert "/opt/pycharm/bin/pycharm.sh" not in command
    temporary_sources = [
        Path(next(part.removeprefix("src=") for part in argument.split(",") if part.startswith("src=")))
        for argument in command
        if argument.startswith("type=bind,src=")
        and any(
            destination in argument
            for destination in (
                "dst=/tmp/.docker.xauth",
                "dst=/etc/passwd",
                "dst=/etc/group",
                f"dst={RUNTIME_PLAN_PATH}",
            )
        )
    ]
    assert len(temporary_sources) == 4
    assert all(not path.exists() for path in temporary_sources)


def test_launch_preparation_failure_cleans_runtime_and_identity_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    with (
        patch("devcapsule.launch.pycharm._launcher.shutil.which", return_value=None),
        patch(
            "devcapsule.launch.pycharm._launcher.cleanup_temp_runtime_files",
            wraps=cleanup_temp_runtime_files,
        ) as cleanup,
    ):
        with pytest.raises(PycharmRunError, match="variable is empty or unset"):
            run_pycharm(
                PycharmRunOptions(
                    project=project,
                    capsule_platform=Platform.LINUX_AMD64,
                    project_mount="/workspace/project",
                    image="devcapsule-local-pycharm:canonical",
                    docker_mode=DockerMode.none,
                    network_mode="bridge",
                    git_token_env="MISSING_TOKEN",
                    runtime_plan=external_runtime_plan(),
                    use_image_process=True,
                ),
                env,
            )

    files = cleanup.call_args.args[0]
    assert files.runtime_plan_file is not None
    assert all(
        path is None or not path.exists()
        for path in (
            files.xauth_file,
            files.passwd_file,
            files.group_file,
            files.runtime_plan_file,
        )
    )


def test_runtime_plan_serialization_failure_leaves_no_temporary_files(tmp_path: Path) -> None:
    runtime_directory = tmp_path / "runtime"
    config = cast(
        PycharmRunConfig,
        SimpleNamespace(enable_sudo=False, runtime_plan=external_runtime_plan(), display_transport="host-x11",
                        console_host_port=None),
    )
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
        patch.object(RuntimePlan, "to_json", side_effect=ValueError("serialization failed")),
    ):
        with pytest.raises(ValueError, match="serialization failed"):
            prepare_temp_runtime_files(
                config,
                {"XDG_RUNTIME_DIR": str(runtime_directory)},
            )

    assert runtime_directory.is_dir()
    assert list(runtime_directory.iterdir()) == []


def test_generated_passwd_home_matches_persistent_container_home(tmp_path: Path) -> None:
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth",
        passwd_file=tmp_path / "passwd",
        group_file=tmp_path / "group",
        console_token_file=tmp_path / "console-token",
    )
    config = cast(PycharmRunConfig, SimpleNamespace(host_docker_gid=None, enable_sudo=False))

    with patch(
        "devcapsule.launch.pycharm._launcher.current_host_user",
        return_value=HostUser(uid=1000, gid=1000, name="developer", group_name="developer"),
    ):
        write_user_files(config, files)

    assert "developer:x:1000:1000:PyCharm Docker User:/home/devcapsule:/bin/bash" in files.passwd_file.read_text()
    assert "/ide-global-settings/home" not in files.passwd_file.read_text()


def test_ide_config_option_implies_custom_config_mode(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    custom_config = tmp_path / "custom-config"

    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            ide_config=custom_config,
            docker_mode=DockerMode.none,
        ),
        base_env(tmp_path),
    )

    assert config.ide_config_mode == "custom"
    assert config.ide_config == custom_config.resolve()


def test_explicit_shared_config_mode_ignores_env_ide_config_dir(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["PYCHARM_IDE_CONFIG_DIR"] = str(tmp_path / "env-config")

    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            config_mode=IdeConfigMode.shared,
            docker_mode=DockerMode.none,
        ),
        env,
    )

    assert config.ide_config_mode == "shared"
    project_id = plan_project(project).project_id
    assert config.ide_config == (
        tmp_path / "data" / "devcapsule" / "projects" / "by-path" / project_id / "components" / "pycharm" / "config"
    ).resolve()


def test_env_ide_config_dir_implies_custom_when_mode_is_unset(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["PYCHARM_IDE_CONFIG_DIR"] = str(tmp_path / "env-config")

    config = build_run_config(PycharmRunOptions(project=project, capsule_platform=Platform.LINUX_AMD64, docker_mode=DockerMode.none), env)

    assert config.ide_config_mode == "custom"
    assert config.ide_config == (tmp_path / "env-config").resolve()


def test_profile_sets_global_settings_and_plugins_defaults(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")

    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            profile="codex",
            docker_mode=DockerMode.none,
        ),
        env,
    )

    profile_root = tmp_path / "config" / "docker-pycharm-codex"
    assert config.global_settings == (profile_root / "state").resolve()
    assert config.plugins == (profile_root / "plugins").resolve()


def test_project_state_root_mirrors_project_path_under_root_parent(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "myProjects" / "example"
    project.mkdir(parents=True)

    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_state_root=workspace / ".state",
            docker_mode=DockerMode.none,
        ),
        base_env(tmp_path),
    )

    assert config.project_state == (workspace / ".state" / "myProjects" / "example").resolve()


def test_explicit_project_state_overrides_project_state_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_state=tmp_path / "explicit-state",
            project_state_root=tmp_path / ".state",
            docker_mode=DockerMode.none,
        ),
        base_env(tmp_path),
    )

    assert config.project_state == (tmp_path / "explicit-state").resolve()


def test_dogfood_legacy_roots_map_to_persistent_home_and_component_slots(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    global_settings = tmp_path / "docker-pycharm-codex" / "state"
    plugins = tmp_path / "docker-pycharm-codex" / "plugins"
    project_state = tmp_path / ".state" / "project"

    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            global_settings=global_settings,
            plugins=plugins,
            project_state=project_state,
            docker_mode=DockerMode.none,
        ),
        base_env(tmp_path),
    )

    assert config.persistent_home == (global_settings / "home").resolve()
    assert config.ide_config == (global_settings / "config").resolve()
    assert config.plugins == plugins.resolve()
    assert config.ide_system == (project_state / "system").resolve()
    assert config.ide_log == (project_state / "log").resolve()
    assert config.tool_cache == (project_state / "home" / ".cache").resolve()


def test_persistent_home_defaults_to_checkout_scoped_xdg_data(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            docker_mode=DockerMode.none,
        ),
        base_env(tmp_path),
    )

    project_id = plan_project(project).project_id
    assert config.persistent_home == (
        tmp_path / "data" / "devcapsule" / "projects" / "by-path" / project_id / "home"
    ).resolve()


def test_launcher_owned_docker_options_are_refused_in_passthrough() -> None:
    """Docker keeps the last occurrence of a single-instance option, so a raw
    passthrough repetition would silently override the resolved plan; ruled
    2026-09-02: launcher-owned single-instance options are refused, repeatable
    ones pass through."""

    from devcapsule.launch.pycharm import reject_launcher_owned_docker_options

    for option in ("--network", "--network=host", "-m", "--memory=2g", "--shm-size=1g", "--user", "--privileged", "--pull=always",
                   "-m2g", "-u1000", "-dit", "-ti"):  # attached and clustered short spellings included
        with pytest.raises(PycharmRunError, match="composed by the launcher"):
            reject_launcher_owned_docker_options(["-v", "/x:/y", option])
    with pytest.raises(PycharmRunError, match="Raw docker option '-m'"):
        reject_launcher_owned_docker_options(["-m2g"])
    with pytest.raises(PycharmRunError, match="Raw docker option '-i'"):
        reject_launcher_owned_docker_options(["-ti"])

    with pytest.raises(PycharmRunError, match="shared-memory-size in its runtime template"):
        reject_launcher_owned_docker_options(["--shm-size", "1g"])

    reject_launcher_owned_docker_options(
        ["-v", "/x:/y", "--volume", "/a:/b", "--env", "FOO=bar", "--mount", "type=tmpfs,dst=/z", "--cap-add", "NET_ADMIN",
         "-eNAME=value", "-e=NAME=value", "-v/src:/dst:ro", "-eit=m", "-t", "-P", "-"]  # values after -e/-v are never read as flags
    )


# --- Contained display (contained-display design note, T4/T6/T7) ---


def contained_config(tmp_path: Path, network_mode: str = "bridge", **overrides: object) -> PycharmRunConfig:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    env = base_env(tmp_path)
    env.pop("DISPLAY")  # the contained display needs no host X session at all
    options: dict[str, object] = dict(
        project=project,
        capsule_platform=Platform.LINUX_AMD64,
        project_mount="/workspace/project",
        docker_mode=DockerMode.none,
        network_mode=network_mode,
        runtime_plan=external_runtime_plan(),
        use_image_process=True,
        display_transport="contained",
    )
    options.update(overrides)
    return build_run_config(PycharmRunOptions(**options), env)  # type: ignore[arg-type]


def test_contained_display_publishes_a_token_gated_port_and_shares_no_x_session(tmp_path: Path) -> None:
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    config = contained_config(tmp_path)
    assert config.display_transport == "contained"
    assert config.display_host_port is not None and 1024 < config.display_host_port < 65536
    assert len(config.display_token) == 48 and int(config.display_token, 16) >= 0
    assert config.runtime_plan is not None and config.runtime_plan.display == DisplayPlan.contained(
        "0.0.0.0", 6080, "/run/devcapsule-display-token"
    )
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority") as xauthority,
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        xauthority.assert_not_called()
        assert files.display_token_file is not None
        assert files.display_token_file.stat().st_mode & 0o777 == 0o600
        assert files.display_token_file.read_text(encoding="utf-8") == config.display_token + "\n"
        args = build_docker_args(config, files, env)
        joined = " ".join(args)
        assert "/tmp/.X11-unix" not in joined
        assert "XAUTHORITY" not in joined
        assert "DISPLAY" not in args
        assert "_JAVA_AWT_WM_NONREPARENTING=1" not in args
        assert f"type=bind,src={files.display_token_file},dst=/run/devcapsule-display-token,ro" in args
        assert f"127.0.0.1:{config.display_host_port}:6080" == args[args.index("--publish") + 1]
        assert RuntimePlan.from_file(files.runtime_plan_file).display == config.runtime_plan.display  # type: ignore[arg-type]
        # The token never appears on the docker command line.
        assert config.display_token not in joined
    finally:
        cleanup_temp_runtime_files(files)
    assert not (tmp_path / "runtime").exists() or list((tmp_path / "runtime").iterdir()) == []


def test_contained_display_under_host_networking_listens_on_host_loopback_directly(tmp_path: Path) -> None:
    env = base_env(tmp_path)
    config = contained_config(tmp_path, network_mode="host")
    assert config.runtime_plan is not None and config.runtime_plan.display == DisplayPlan.contained(
        "127.0.0.1", config.display_host_port, "/run/devcapsule-display-token"  # type: ignore[arg-type]
    )
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        args = build_docker_args(config, files, env)
        assert "--publish" not in args
        assert "/tmp/.X11-unix" not in " ".join(args)
    finally:
        cleanup_temp_runtime_files(files)


def test_contained_display_refuses_network_none_and_names_the_alternatives(tmp_path: Path) -> None:
    with pytest.raises(PycharmRunError, match="network mode 'none'.*host-x11"):
        contained_config(tmp_path, network_mode="none")


def test_contained_display_requires_the_image_process_and_a_plan(tmp_path: Path) -> None:
    with pytest.raises(PycharmRunError, match="contained display requires the image process"):
        contained_config(tmp_path, use_image_process=False, runtime_plan=None)


def test_unknown_display_transport_is_refused(tmp_path: Path) -> None:
    with pytest.raises(PycharmRunError, match="Unknown display transport 'xephyr'"):
        contained_config(tmp_path, display_transport="xephyr")


def test_host_x11_passthrough_still_needs_a_host_display_and_binds_it(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env.pop("DISPLAY")
    with pytest.raises(PycharmRunError, match="DISPLAY is not set"):
        build_run_config(PycharmRunOptions(project=project, capsule_platform=Platform.LINUX_AMD64, project_mount="/workspace/project"), env)
    env = base_env(tmp_path)
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=external_runtime_plan(),
            use_image_process=True,
        ),
        env,
    )
    assert config.display_transport == "host-x11"
    assert config.runtime_plan is not None and config.runtime_plan.display == DisplayPlan.host_x11()
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority") as xauthority,
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        xauthority.assert_called_once()
        assert files.display_token_file is None
        args = build_docker_args(config, files, env)
        assert "type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix,ro" in args
        assert "XAUTHORITY=/tmp/.docker.xauth" in args
        assert "DISPLAY" in args
        published = [args[index + 1] for index, item in enumerate(args) if item == "--publish"]
        assert published == [f"127.0.0.1:{config.console_host_port}:6081"]  # the console only; no display port
    finally:
        cleanup_temp_runtime_files(files)


def test_display_disclosure_states_the_transport(tmp_path: Path) -> None:
    contained = contained_config(tmp_path)
    text = display_disclosure(contained)
    assert "Contained desktop" in text
    assert f"published to host loopback port {contained.display_host_port}" in text
    assert "No host X socket, credential, or DISPLAY is shared" in text
    assert "boundary test is waived" in display_disclosure(
        build_run_config(
            PycharmRunOptions(
                project=tmp_path / "project",
                capsule_platform=Platform.LINUX_AMD64,
                project_mount="/workspace/project",
                docker_mode=DockerMode.none,
                network_mode="bridge",
            ),
            base_env(tmp_path),
        )
    )


def test_run_pycharm_announces_the_display_url_and_opens_it_when_ready(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env.pop("DISPLAY")
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    opened: list[str] = []
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def fake_docker_run(command: list[str], env: dict[str, str], **_kwargs: object) -> AttachedResult:
        # "The capsule is up": the published port answers, so the watcher opens
        # the URL; then docker run returns as the session ends.
        deadline = time.monotonic() + 10
        while not opened and time.monotonic() < deadline:
            time.sleep(0.05)
        return AttachedResult(0, interrupted=False, stopped=True)

    with (
        patch("devcapsule.launch.pycharm._launcher.allocate_loopback_port", side_effect=[port, 1]),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
        patch("devcapsule.launch.pycharm._launcher.run_attached", side_effect=fake_docker_run),
        patch("devcapsule.launch.pycharm._launcher.current_host_user", return_value=HostUser(1000, 1000, "dev", "dev")),
    ):
        try:
            exit_code = run_pycharm(
                PycharmRunOptions(
                    project=project,
                    capsule_platform=Platform.LINUX_AMD64,
                    project_mount="/workspace/project",
                    docker_mode=DockerMode.none,
                    network_mode="bridge",
                    runtime_plan=external_runtime_plan(),
                    use_image_process=True,
                    display_transport="contained",
                    open_display_url=opened.append,
                ),
                env,
            )
        finally:
            listener.close()
    assert exit_code == 0
    (url,) = opened
    assert url.startswith(f"http://127.0.0.1:{port}/vnc.html?autoconnect=1&resize=remote&path=websockify%3Ftoken%3D")
    captured = capsys.readouterr()
    assert f"Contained display: {url}" in captured.err


def test_launcher_mounts_live_configuration_directory_and_private_snapshot_read_only(tmp_path):
    import json
    from devcapsule.launch.pycharm._launcher import channel_watcher, describe_run_command
    from devcapsule.runtime_configuration import CHANNEL_PATH, CONFIGURATION_PATH, CONTEXT_PATH, LaunchConfiguration
    project = tmp_path / "project"
    project.mkdir()
    records = tmp_path / "records"
    records.mkdir()
    document = {"format": 1, "launcher-root": str(project), "runtime-root": "/workspace/project",
                "checkout-file": "devcapsule.checkout.toml", "running": {"identity": "captured-at-launch"}}
    home = tmp_path / "chosen-home"
    home.mkdir()
    (home / "settings.toml").write_text('minimum-devcapsule = "0.3.0"\ndevcapsule-settings-schema-version = 1\n')
    document["configuration-home"] = str(home)
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    config = build_run_config(PycharmRunOptions(
        project=project, capsule_platform=Platform.LINUX_AMD64, project_mount="/workspace/project", docker_mode=DockerMode.none,
        runtime_plan=external_runtime_plan(), use_image_process=True,
        launch_configuration=LaunchConfiguration(records, document),
    ), env)
    with patch("devcapsule.launch.pycharm._launcher.write_xauthority"), patch("devcapsule.launch.pycharm._launcher.write_user_files"):
        files = prepare_temp_runtime_files(config, env)
    try:
        assert files.launch_context_file is not None
        assert files.launch_context_file.stat().st_mode & 0o777 == 0o600
        assert json.loads(files.launch_context_file.read_text()) == document
        args = build_docker_args(config, files, env)
        assert f"type=bind,src={records},dst={CONFIGURATION_PATH},ro" in args
        assert f"type=bind,src={home}/settings.toml,dst=/etc/devcapsule/home/settings.toml,ro" in args
        assert not any("DEVCAPSULE_CONFIG_HOME" in arg for arg in args)
        assert not any(f"src={home}," in arg for arg in args)
        assert f"type=bind,src={files.launch_context_file},dst={CONTEXT_PATH},ro" in args
        assert not any("src=" + str(records / "devcapsule.checkout.toml") in arg for arg in args)
        # The console's channel: a private directory, mounted writable, with the launch listing when run computed one.
        assert files.configuration_directory is not None and files.configuration_directory.stat().st_mode & 0o777 == 0o700
        assert f"type=bind,src={files.configuration_directory},dst={CHANNEL_PATH}" in args
        assert not (files.configuration_directory / "listing.json").exists()
        watcher = channel_watcher(config, files)
        assert watcher is not None and watcher.checkout_record == records / "devcapsule.checkout.toml" and watcher.root == project
    finally:
        cleanup_temp_runtime_files(files)
    assert not files.launch_context_file.exists() and not files.configuration_directory.exists()
    listing = {"schema-version": 2, "rows": [], "pending": [], "notes": []}
    config = build_run_config(PycharmRunOptions(
        project=project, capsule_platform=Platform.LINUX_AMD64, project_mount="/workspace/project", docker_mode=DockerMode.none,
        runtime_plan=external_runtime_plan(), use_image_process=True,
        launch_configuration=LaunchConfiguration(records, document, listing),
    ), env)
    with patch("devcapsule.launch.pycharm._launcher.write_xauthority"), patch("devcapsule.launch.pycharm._launcher.write_user_files"):
        files = prepare_temp_runtime_files(config, env)
    try:
        assert files.configuration_directory is not None
        written = json.loads((files.configuration_directory / "listing.json").read_text())
        assert written["format"] == 1 and written["listing"] == listing and written["at"]
        assert "Temporary Configuration channel:" in describe_run_command(["docker", "run"], config, files)
    finally:
        cleanup_temp_runtime_files(files)


def test_web_console_runs_whenever_the_runtime_runs_behind_its_own_token(tmp_path: Path) -> None:
    """The console mirrors the display: one loopback port, one per-run token,
    the token mounted read-only and never on the command line (R-CONSOLE-001)."""
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    config = contained_config(tmp_path)
    assert config.console_host_port is not None and 1024 < config.console_host_port < 65536
    assert config.console_host_port != config.display_host_port
    assert len(config.console_token) == 48 and config.console_token != config.display_token
    assert config.runtime_plan is not None
    assert config.runtime_plan.console == ConsolePlan("0.0.0.0", 6081, "/run/devcapsule-console-token")
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        assert files.console_token_file is not None
        assert files.console_token_file.stat().st_mode & 0o777 == 0o600
        assert files.console_token_file.read_text(encoding="utf-8") == config.console_token + "\n"
        args = build_docker_args(config, files, env)
        joined = " ".join(args)
        assert f"type=bind,src={files.console_token_file},dst=/run/devcapsule-console-token,ro" in args
        published = [args[index + 1] for index, item in enumerate(args) if item == "--publish"]
        assert published == [f"127.0.0.1:{config.display_host_port}:6080", f"127.0.0.1:{config.console_host_port}:6081"]
        # The origin crosses into the capsule so an agent can hand the human a link; the token does not.
        assert f"DEVCAPSULE_CONSOLE_URL=http://127.0.0.1:{config.console_host_port}" in args
        assert config.console_token not in joined
        assert RuntimePlan.from_file(files.runtime_plan_file).console == config.runtime_plan.console  # type: ignore[arg-type]
        description = describe_run_command(args, config, files)
        assert f"Temporary Console token: {files.console_token_file}" in description
        assert "The web console needs its temporary token file" in description
        assert config.console_token not in description
        assert config.console_token not in config.runtime_plan.to_json()
    finally:
        cleanup_temp_runtime_files(files)
    assert not files.console_token_file.exists()


def test_no_web_console_is_planned_on_a_base_without_one(tmp_path: Path) -> None:
    """On a base before recipe 11 the launcher plans no console at all: no
    port, no token, no console section in the runtime plan, no published
    port and no origin in the capsule, so nothing waits for a console that
    cannot answer (bug of 2026-10-18)."""
    from devcapsule.images.contract import WebConsoleAvailability

    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    config = contained_config(tmp_path, web_console=WebConsoleAvailability(False, "ubuntu-24.04@9"))
    assert config.console_host_port is None and config.console_token == ""
    assert config.runtime_plan is not None and config.runtime_plan.console is None
    assert config.display_host_port is not None  # the display is untouched
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        assert files.console_token_file is None
        args = build_docker_args(config, files, env)
        published = [args[index + 1] for index, item in enumerate(args) if item == "--publish"]
        assert published == [f"127.0.0.1:{config.display_host_port}:6080"]
        assert not any(item.startswith("DEVCAPSULE_CONSOLE_URL=") for item in args)
        assert "devcapsule-console-token" not in " ".join(args)
    finally:
        cleanup_temp_runtime_files(files)


def test_web_console_notice_names_the_base_the_command_and_the_guide() -> None:
    """The line printed in place of the link: the base, the recipe the console
    needs, the one build command with this launcher's own source revision, and
    the guide for selecting the built base; a source-form launcher offers
    --allow-local-source instead."""
    from devcapsule.build_info import BuildInfo
    from devcapsule.images.contract import WebConsoleAvailability
    from devcapsule.launch.pycharm._launcher import LOCAL_BASE_GUIDE_URL, web_console_notice

    revision = "53ebc17705bf99461bbbbf3c4a128228a14c0d51"
    released = BuildInfo(
        schema_version=2, version="0.3.0rc0", source_repository="https://github.com/ccozianu/devcapsule",
        source_revision=revision, source_url=f"https://github.com/ccozianu/devcapsule/commit/{revision}",
        build_mnemonic="v0.3.0-rc0",
    )
    with patch("devcapsule.launch.pycharm._launcher.current_build_info", return_value=released):
        notice = web_console_notice(WebConsoleAvailability(False, "ubuntu-24.04@9"))
    lines = notice.splitlines()
    assert lines[0] == (
        "Web console: none on this base (ubuntu-24.04@9; the console needs base recipe 11 or later); "
        "the capsule runs without it."
    )
    assert lines[1].strip() == (
        f"To build a base that has it:  devcapsule images build --type base --recipe ubuntu-24.04 --source-revision {revision}"
    )
    assert lines[2].strip().endswith(LOCAL_BASE_GUIDE_URL)
    assert LOCAL_BASE_GUIDE_URL.startswith("https://devcapsule.mycodespace.ai/docs/current/")
    source_form = BuildInfo(
        schema_version=2, version="0.3.1.dev0", source_repository="https://github.com/ccozianu/devcapsule",
        source_revision="unknown", source_url="unknown", build_mnemonic="v0.3.1.dev0-local-linux-x86_64",
    )
    with patch("devcapsule.launch.pycharm._launcher.current_build_info", return_value=source_form):
        notice = web_console_notice(WebConsoleAvailability(False, None))
    assert "--allow-local-source" in notice and "--source-revision" not in notice
    assert "an image without DevCapsule recipe labels" in notice


def test_web_console_under_host_networking_listens_on_host_loopback_directly(tmp_path: Path) -> None:
    config = contained_config(tmp_path, network_mode="host")
    assert config.runtime_plan is not None and config.runtime_plan.console == ConsolePlan(
        "127.0.0.1", config.console_host_port, "/run/devcapsule-console-token"  # type: ignore[arg-type]
    )
    env = base_env(tmp_path)
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        args = build_docker_args(config, files, env)
        assert "--publish" not in args
        assert f"DEVCAPSULE_CONSOLE_URL=http://127.0.0.1:{config.console_host_port}" in args
        assert f"type=bind,src={files.console_token_file},dst=/run/devcapsule-console-token,ro" in args
    finally:
        cleanup_temp_runtime_files(files)


@pytest.mark.parametrize("network_mode", ["bridge", "host"])
def test_console_retries_a_port_already_selected_for_the_display(tmp_path: Path, network_mode: str) -> None:
    with patch("devcapsule.launch.pycharm._launcher.allocate_loopback_port", side_effect=[41000, 41000, 41001]):
        config = contained_config(tmp_path, network_mode=network_mode)
    assert config.display_host_port == 41000
    assert config.console_host_port == 41001
    assert config.runtime_plan is not None and config.runtime_plan.console is not None
    assert config.runtime_plan.console.port == (41001 if network_mode == "host" else 6081)


def test_console_port_retries_are_bounded(tmp_path: Path) -> None:
    with patch("devcapsule.launch.pycharm._launcher.allocate_loopback_port", return_value=41000) as allocate:
        with pytest.raises(PycharmRunError, match="distinct display and web console ports"):
            contained_config(tmp_path)
    assert allocate.call_count == 11  # one display allocation, ten console attempts


def test_console_mount_requires_its_token_file(tmp_path: Path) -> None:
    config = contained_config(tmp_path)
    files = TempRuntimeFiles(
        xauth_file=tmp_path / "xauth", passwd_file=tmp_path / "passwd", group_file=tmp_path / "group",
        display_token_file=tmp_path / "display-token", runtime_plan_file=tmp_path / "plan",
    )
    with pytest.raises(PycharmRunError, match="web console requires a generated token file"):
        build_docker_args(config, files, base_env(tmp_path))


@pytest.mark.parametrize("failure", ["write", "chmod", "later"])
def test_console_token_is_removed_when_preparation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    config = contained_config(tmp_path)
    runtime = tmp_path / "runtime"
    env = {**base_env(tmp_path), "XDG_RUNTIME_DIR": str(runtime)}
    write_text = Path.write_text
    chmod = Path.chmod

    def fail_write(path: Path, data: str, **kwargs: object) -> int:
        if path.name.startswith("devcapsule-console-token."):
            raise OSError("token write failed")
        return write_text(path, data, encoding="utf-8")

    def fail_chmod(path: Path, mode: int) -> None:
        if path.name.startswith("devcapsule-console-token."):
            raise OSError("token chmod failed")
        chmod(path, mode)

    if failure == "write":
        monkeypatch.setattr(Path, "write_text", fail_write)
    elif failure == "chmod":
        monkeypatch.setattr(Path, "chmod", fail_chmod)
    message = "identity failed" if failure == "later" else f"token {failure} failed"
    with patch("devcapsule.launch.pycharm._launcher.write_user_files",
               side_effect=OSError(message) if failure == "later" else None):
        with pytest.raises(OSError, match=message):
            prepare_temp_runtime_files(config, env)
    assert list(runtime.iterdir()) == []


@pytest.mark.parametrize("report_only", [False, True])
def test_console_launcher_cleans_up_after_command_reporting_or_docker_failure(
    tmp_path: Path, report_only: bool,
) -> None:
    from unittest.mock import Mock

    config = contained_config(tmp_path)
    runtime = tmp_path / "runtime"
    env = {**base_env(tmp_path), "XDG_RUNTIME_DIR": str(runtime)}
    report = Mock()
    options = PycharmRunOptions(project=config.project, capsule_platform=Platform.LINUX_AMD64, command_report=report if report_only else None)
    with (
        patch("devcapsule.launch.pycharm._launcher.build_run_config", return_value=config),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
        patch("devcapsule.launch.pycharm._launcher.watch_display_ready") as watch,
        patch("devcapsule.launch.pycharm._launcher.run_attached", side_effect=OSError("docker failed")) as docker,
    ):
        if report_only:
            assert run_pycharm(options, env) == 0
            docker.assert_not_called()
            watch.assert_not_called()
            report.assert_called_once()
            assert "Temporary Console token:" in report.call_args.args[0]
            assert config.console_token not in report.call_args.args[0]
        else:
            with pytest.raises(OSError, match="docker failed"):
                run_pycharm(options, env)
            assert watch.call_count == 2
            assert watch.call_args.args[3].is_set()
    assert list(runtime.iterdir()) == []


def test_web_console_runs_the_checkouts_source_under_the_self_hosting_exception(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "devcapsule-webconsole" / "devcapsule_webconsole").mkdir(parents=True)
    (project / "devcapsule-webconsole" / "devcapsule_webconsole" / "__init__.py").write_text("", encoding="utf-8")
    config = contained_config(tmp_path)
    assert config.runtime_plan is not None and config.runtime_plan.console is not None
    assert config.runtime_plan.console.source_path == "/workspace/project/devcapsule-webconsole"
    assert console_development_source(tmp_path / "other", "/workspace/other") == ""


def test_web_console_is_absent_without_a_runtime_plan(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = build_run_config(
        PycharmRunOptions(project=project, capsule_platform=Platform.LINUX_AMD64, project_mount="/workspace/project", docker_mode=DockerMode.none),
        base_env(tmp_path),
    )
    assert config.console_host_port is None and config.console_token == ""
    assert console_disclosure(config) == ""
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, base_env(tmp_path))
    try:
        assert files.console_token_file is None
        assert "devcapsule-console-token" not in " ".join(build_docker_args(config, files, base_env(tmp_path)))
    finally:
        cleanup_temp_runtime_files(files)


def test_console_disclosure_states_where_it_listens(tmp_path: Path) -> None:
    contained = contained_config(tmp_path)
    text = console_disclosure(contained)
    assert "Web console:" in text and "read-only" in text
    assert f"container port 6081, published to host loopback port {contained.console_host_port}" in text
    direct = contained_config(tmp_path, network_mode="host")
    assert f"host loopback port {direct.console_host_port} (host networking)" in console_disclosure(direct)


@pytest.mark.parametrize("display_transport", ["contained", "host-x11"])
@pytest.mark.parametrize("custom_console_opener", [False, True])
def test_run_pycharm_announces_the_console_url_and_opens_it_only_without_a_desktop(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], display_transport: str, custom_console_opener: bool,
) -> None:
    from threading import Event
    from unittest.mock import Mock

    project = tmp_path / "project"
    project.mkdir()
    env = base_env(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    display_opener = Mock()
    console_opener = Mock()
    default_console_opener = Mock()
    tokens = ["a" * 48, "b" * 48]
    stops: list[Event] = []

    def ready(port: int, url: str, opener: object, stop: Event, **kwargs: object) -> None:
        from typing import Callable

        stops.append(stop)
        assert not stop.is_set()
        cast(Callable[[str], None], opener)(url)

    with (
        patch("devcapsule.launch.pycharm._launcher.allocate_loopback_port", side_effect=[41000, 41001]),
        patch("devcapsule.launch.pycharm._launcher.new_run_token", side_effect=tokens),
        patch("devcapsule.launch.pycharm._launcher.watch_display_ready", side_effect=ready) as watcher,
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.run_attached", return_value=AttachedResult(7, interrupted=False, stopped=True)),
        patch("devcapsule.launch.pycharm._launcher.default_opener", return_value=default_console_opener) as default,
    ):
        assert run_pycharm(PycharmRunOptions(
            project=project, capsule_platform=Platform.LINUX_AMD64, project_mount="/workspace/project", docker_mode=DockerMode.none,
            network_mode="bridge", runtime_plan=external_runtime_plan(), use_image_process=True,
            display_transport=display_transport, open_display_url=display_opener,
            open_console_url=console_opener if custom_console_opener else None,
        ), env) == 7
    contained = display_transport == "contained"
    console_port, token = (41001, tokens[1]) if contained else (41000, tokens[0])
    url = f"http://127.0.0.1:{console_port}/?token={token}"
    output = capsys.readouterr().err
    assert f"Web console: {url}\n" in output
    assert watcher.call_count == (2 if contained else 1)
    assert watcher.call_args.args[:2] == (console_port, url)
    assert watcher.call_args.kwargs == {"label": "Web console"}
    assert all(stop is stops[0] and stop.is_set() for stop in stops)
    assert list((tmp_path / "runtime").iterdir()) == []
    if contained:
        display_opener.assert_called_once_with(display_url(41000, tokens[0]))
    else:
        display_opener.assert_not_called()
    if custom_console_opener:
        console_opener.assert_called_once_with(url)
        default.assert_not_called()
    elif contained:
        assert f"Web console is ready; open it in a browser: {url}" in output
        default.assert_not_called()
    else:
        assert default.call_args.kwargs == {"label": "Web console"}
        default_console_opener.assert_called_once_with(url)


@pytest.mark.parametrize("enabled", [False, True])
def test_console_environment_contains_only_the_origin(tmp_path: Path, enabled: bool) -> None:
    from dataclasses import replace
    from devcapsule.display_client import console_origin, console_url
    from devcapsule.launch.pycharm._launcher import _console_environment_args

    config = replace(contained_config(tmp_path), console_host_port=41001 if enabled else None,
                     console_token="private/token?value")
    assert _console_environment_args(config) == (
        ["--env", "DEVCAPSULE_CONSOLE_URL=http://127.0.0.1:41001"] if enabled else []
    )
    assert console_origin(41001) == "http://127.0.0.1:41001"
    assert console_url(41001, config.console_token) == "http://127.0.0.1:41001/?token=private%2Ftoken%3Fvalue"


def session_config(tmp_path: Path, **environment: str) -> tuple[PycharmRunConfig, dict[str, str]]:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    env = base_env(tmp_path)
    env["XDG_STATE_HOME"] = str(tmp_path / "state")
    env["XDG_RUNTIME_DIR"] = str(tmp_path / "runtime")
    env.update(environment)
    config = build_run_config(
        PycharmRunOptions(
            project=project,
            capsule_platform=Platform.LINUX_AMD64,
            project_mount="/workspace/project",
            docker_mode=DockerMode.none,
            network_mode="bridge",
            runtime_plan=external_runtime_plan(),
            use_image_process=True,
        ),
        env,
    )
    return config, env


@pytest.mark.parametrize("named_home", [False, True])
def test_every_launch_gets_a_session_log_directory_bound_into_the_capsule(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], named_home: bool
) -> None:
    import re

    from devcapsule.launch.session_logs import session_logs_root
    from devcapsule.project import project_namespace

    config, env = session_config(tmp_path, **({"DEVCAPSULE_CONFIG_HOME": str(tmp_path / "chosen")} if named_home else {}))
    directory = config.session_log_directory
    assert directory is not None and directory.is_dir()
    assert directory.parent == session_logs_root(config.project, env)
    state = tmp_path / "chosen" / "state" if named_home else tmp_path / "state" / "devcapsule"
    assert directory.parent == state / "projects" / "by-path" / project_namespace(config.project) / "logs"
    if named_home:
        assert not (tmp_path / "state").exists()
    assert directory.name == config.session_id and re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{4}", config.session_id)
    # 256 MiB by default, one thirty-second of it per segment, four rotations.
    assert config.log_budget_bytes == 256 * 1024 * 1024
    assert config.runtime_plan is not None
    assert config.runtime_plan.logs == LogsPlan(SESSION_LOG_DESTINATION, segment_bytes=8 * 1024 * 1024, rotations=4)
    with (
        patch("devcapsule.launch.pycharm._launcher.write_xauthority"),
        patch("devcapsule.launch.pycharm._launcher.write_user_files"),
    ):
        files = prepare_temp_runtime_files(config, env)
    try:
        args = build_docker_args(config, files, env)
        assert f"type=bind,src={directory},dst={SESSION_LOG_DESTINATION}" in args
        assert f"DEVCAPSULE_LOG_DIR={SESSION_LOG_DESTINATION}" in args
        assert (f"Session logs: {directory} (bound at {SESSION_LOG_DESTINATION}; checkout budget 256 MiB, DEVCAPSULE_LOG_BUDGET)"
                in describe_run_command(args, config, files))
    finally:
        cleanup_temp_runtime_files(files)
    print_storage_summary(config)
    assert f"Session logs:           {directory} (budget 256 MiB)" in capsys.readouterr().err


def test_begin_session_logs_writes_the_manifest_and_the_launcher_log_and_prunes_old_sessions(tmp_path: Path) -> None:
    import json
    import logging

    from devcapsule import logs
    from devcapsule.launch.pycharm._launcher import begin_session_logs

    config, env = session_config(tmp_path, DEVCAPSULE_LOG_BUDGET="16M")
    directory = config.session_log_directory
    assert directory is not None
    for index in range(3):
        old = directory.parent / f"20200101-0000{index:02d}-aaaa"
        old.mkdir()
        (old / "devcapsule-pycharm.log").write_bytes(b"x" * (6 * 1024 * 1024))
    try:
        begin_session_logs(config, env)
        handler = next(h for h in logging.getLogger().handlers if isinstance(h, logs._SessionFileHandler))
        assert handler._file is not None and handler._file.path == directory / "devcapsule-launcher.log"
        assert (handler._file._segment, handler._file._rotations) == (1024 * 1024, 4)
        manifest = json.loads((directory / "session.json").read_text(encoding="utf-8"))
        assert manifest["session"] == config.session_id
        assert manifest["container"] == config.name and manifest["image"] == config.image
        assert manifest["component"] == "pycharm"
        assert manifest["logs"] == {
            "directory": SESSION_LOG_DESTINATION, "pattern": "devcapsule-<component>.log",
            "budget-bytes": 16 * 1024 * 1024, "segment-bytes": 1024 * 1024, "rotations": 4,
        }
        assert manifest["launcher"]["version"]
        record = (directory / "devcapsule-launcher.log").read_text(encoding="utf-8")
        assert f"session {config.session_id} start: image {config.image}, container {config.name}" in record
        # 18 MiB of old sessions against a 16 MiB budget: the oldest goes, the next fits.
        assert "removed 1 older session log directories to fit the 16 MiB budget: 20200101-000000-aaaa" in record
        assert sorted(entry.name for entry in directory.parent.iterdir()) == [
            "20200101-000001-aaaa", "20200101-000002-aaaa", directory.name,
        ]
    finally:
        logs.reset()


def test_unusable_session_directory_does_not_add_a_mount_or_stop_launch(tmp_path, capsys):
    from devcapsule import logs
    from devcapsule.launch.pycharm import _launcher as launcher

    blocked = tmp_path / "blocked-state"
    blocked.write_text("not a directory")
    # Existing IDE storage still has to be writable; this regression isolates
    # the new session directory from that pre-existing launch requirement.
    with patch.object(launcher, "session_logs_root", return_value=blocked):
        config, env = session_config(tmp_path)
    assert config.session_log_directory is None
    assert config.runtime_plan is not None and config.runtime_plan.logs is None
    try:
        with (
            patch.object(launcher, "build_run_config", return_value=config),
            patch.object(launcher, "write_xauthority"),
            patch.object(launcher, "write_user_files"),
            patch.object(launcher, "watch_display_ready"),
            patch.object(launcher, "run_attached", return_value=AttachedResult(7, interrupted=False, stopped=True)) as docker,
        ):
            assert run_pycharm(PycharmRunOptions(project=config.project, capsule_platform=Platform.LINUX_AMD64), env) == 7
        command = docker.call_args.args[0]
        assert not any(SESSION_LOG_DESTINATION in arg for arg in command)
        assert "cannot use session logs" in capsys.readouterr().err
    finally:
        logs.reset()


@pytest.mark.parametrize("override,expected", [("debug", "DEBUG"), (" Info ", "INFO"), ("loud", "WARNING")])
def test_session_log_level_reaches_the_capsule(tmp_path, override, expected):
    config, env = session_config(tmp_path, DEVCAPSULE_LOG_LEVEL=override)
    with patch("devcapsule.launch.pycharm._launcher.write_xauthority"), patch("devcapsule.launch.pycharm._launcher.write_user_files"):
        files = prepare_temp_runtime_files(config, env)
    try:
        assert f"DEVCAPSULE_LOG_LEVEL={expected}" in build_docker_args(config, files, env)
    finally:
        cleanup_temp_runtime_files(files)


@pytest.mark.parametrize("backed", [True, False])
def test_session_logs_with_an_external_daemon(tmp_path, backed, capsys):
    from devcapsule.launch.pycharm import _launcher as launcher
    from devcapsule.recursive_dogfood import ContainerInspection, Mount

    # All existing launch storage is mounted; the optional state root may be
    # outside those mounts. Use the real translation, only fake inspection.
    mounts = [Mount(source="/tmp/.X11-unix", destination="/tmp/.X11-unix", kind="bind", writable=True)]
    if backed:
        mounts.append(Mount(source="/host/checkout", destination=str(tmp_path), kind="bind", writable=True))
    inspection = ContainerInspection(
        identity="c" * 64, name="outer", image="sha256:" + "ab" * 32,
        source_revision=None, network_mode="host", mounts=tuple(mounts), upper_directory=None,
    )
    with (
        patch.object(launcher, "requires_translation", return_value=True),
        patch.object(launcher, "current_container", return_value=inspection),
    ):
        config, env = session_config(tmp_path)
        if backed:
            assert config.session_log_directory is not None
            with patch.object(launcher, "write_xauthority"), patch.object(launcher, "write_user_files"):
                files = prepare_temp_runtime_files(config, env)
            try:
                args = launcher.translate_for_external_daemon(build_docker_args(config, files, env), env)
                relative = config.session_log_directory.relative_to(tmp_path)
                assert f"type=bind,src=/host/checkout/{relative},dst={SESSION_LOG_DESTINATION}" in args
                assert config.session_log_directory.is_dir()  # launcher still writes through its own path
            finally:
                cleanup_temp_runtime_files(files)
        else:
            assert config.session_log_directory is None
            assert config.runtime_plan is not None and config.runtime_plan.logs is None
            assert "not backed by a mount" in capsys.readouterr().err


def test_session_log_masks_inline_environment_values_of_extra_arguments(tmp_path, capsys):
    """The launcher log keeps the docker run line but never a saved or one-off inline env value."""
    from dataclasses import replace
    from devcapsule import logs
    from devcapsule.launch.pycharm import _launcher as launcher

    config, env = session_config(tmp_path)
    config = replace(config, extra_docker_args=[
        "--gpus", "all", "--env", "APP_SECRET=saved-sentinel-value", "-eOTHER=one-off-sentinel", "--env", "PLAIN",
    ])
    commands: list[list[str]] = []

    class Client:
        def __init__(self, command, env):
            commands.append(list(command))

        def wait(self, timeout=None):
            return 0

    try:
        with (
            patch.object(launcher, "build_run_config", return_value=config),
            patch.object(launcher, "write_xauthority"),
            patch.object(launcher, "write_user_files"),
            patch.object(launcher, "watch_display_ready"),
            patch.object(launcher.subprocess, "Popen", Client),
        ):
            assert run_pycharm(PycharmRunOptions(project=config.project, capsule_platform=Platform.LINUX_AMD64), env) == 0
        # Docker receives the literal arguments, in order, before the image.
        [command] = commands
        image = command.index(config.image)
        assert command[image - len(config.extra_docker_args):image] == config.extra_docker_args
        assert config.session_log_directory is not None
        record = (config.session_log_directory / "devcapsule-launcher.log").read_text()
        assert "docker run: " in record
        assert "--gpus all" in record and "APP_SECRET=<redacted>" in record and "-eOTHER=<redacted>" in record
        assert "--env PLAIN" in record
        assert "saved-sentinel-value" not in record and "one-off-sentinel" not in record
        assert "saved-sentinel-value" not in capsys.readouterr().err
    finally:
        logs.reset()


def test_interrupted_launch_ends_with_a_result_and_the_log_paths(tmp_path, capsys):
    """Ctrl+C ends with a result, not a traceback (the first-session report of 2026-09-15, C10)."""
    from devcapsule import logs
    from devcapsule.launch.pycharm import _launcher as launcher

    config, env = session_config(tmp_path)
    stops = []
    stopped_before_return = False

    class Client:
        waits = 0

        def wait(self, timeout=None):
            nonlocal stopped_before_return
            self.waits += 1
            if self.waits == 1:
                assert stops and not any(stop.is_set() for stop in stops)
                raise KeyboardInterrupt
            stopped_before_return = bool(stops) and all(stop.is_set() for stop in stops)
            return 143

    try:
        with (
            patch.object(launcher, "build_run_config", return_value=config),
            patch.object(launcher, "write_xauthority"),
            patch.object(launcher, "write_user_files"),
            patch.object(launcher, "watch_display_ready", side_effect=lambda port, url, opener, stop, **kw: stops.append(stop)),
            patch.object(launcher.subprocess, "Popen", return_value=Client()),
        ):
            assert run_pycharm(PycharmRunOptions(project=config.project, capsule_platform=Platform.LINUX_AMD64), env) == launcher.INTERRUPTED_EXIT_CODE
        assert stopped_before_return
        assert stops and all(stop.is_set() for stop in stops)
        assert list((tmp_path / "runtime").iterdir()) == []
        assert config.session_log_directory is not None
        record = (config.session_log_directory / "devcapsule-launcher.log").read_text()
        assert "session end: interrupted from the terminal (Ctrl+C); docker run exit code 143" in record
        err = capsys.readouterr().err
        assert "Session interrupted from the terminal (Ctrl+C); the capsule stopped." in err
        assert "Session logs on this computer:" in err
        assert f"  {config.session_log_directory / 'devcapsule-launcher.log'}" in err
        assert f"  {config.session_log_directory / 'session.json'}" in err
    finally:
        logs.reset()


def test_run_attached_waits_through_ctrl_c_for_the_capsules_end(capsys) -> None:
    from devcapsule.launch.pycharm import _launcher as launcher

    events: list[str] = []

    class Client:
        """A docker client whose first wait is interrupted and whose second returns."""
        waits = 0
        killed = False

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise KeyboardInterrupt
            events.append(f"wait:{capsys.readouterr().err.strip()}")
            assert timeout == launcher.INTERRUPT_STOP_SECONDS
            return 143

        def kill(self):
            self.killed = True

    client = Client()
    with patch.object(launcher.subprocess, "Popen", return_value=client) as popen:
        result = launcher.run_attached(
            ["docker", "run", "image"],
            {"PATH": "/usr/bin"},
            container_name="capsule",
            on_interrupt=lambda: events.append(f"interrupt:{capsys.readouterr().err}"),
        )
    assert popen.call_args.kwargs["env"] == {"PATH": "/usr/bin"}
    assert result == AttachedResult(143, interrupted=True, stopped=True)
    assert not client.killed
    assert events[0] == "interrupt:"
    assert events[1].startswith("wait:Interrupted from the terminal (Ctrl+C); the capsule is stopping.")


def test_run_attached_asks_the_daemon_when_the_capsule_lingers(capsys) -> None:
    import subprocess as sp
    from devcapsule.launch.pycharm import _launcher as launcher

    class Client:
        waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise KeyboardInterrupt
            if self.waits == 2:
                raise sp.TimeoutExpired("docker", timeout)
            assert timeout == launcher.DAEMON_STOP_SECONDS
            return 143

    with (
        patch.object(launcher.subprocess, "Popen", return_value=Client()),
        patch.object(launcher.subprocess, "run") as stop,
    ):
        result = launcher.run_attached(["docker", "run", "image"], {}, container_name="capsule")
    assert result == AttachedResult(143, interrupted=True, stopped=True)
    assert stop.call_args.args[0] == ["docker", "stop", "--time", "10", "capsule"]
    assert "asking the daemon to stop it" in capsys.readouterr().err


@pytest.mark.parametrize("during_print", [False, True])
def test_run_attached_stops_waiting_on_a_second_ctrl_c(capsys, during_print: bool) -> None:
    from contextlib import nullcontext
    from devcapsule.launch.pycharm import _launcher as launcher

    class Client:
        waits = 0
        killed = False

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1 or (not during_print and self.waits == 2):
                raise KeyboardInterrupt
            return -9

        def kill(self):
            self.killed = True

    client = Client()
    interrupts = 0

    def record_interrupt() -> None:
        nonlocal interrupts
        interrupts += 1

    print_patch = patch("builtins.print", side_effect=KeyboardInterrupt) if during_print else nullcontext()
    with patch.object(launcher.subprocess, "Popen", return_value=client), print_patch:
        result = launcher.run_attached(
            ["docker", "run", "image"], {}, container_name="capsule", on_interrupt=record_interrupt,
        )
    assert result == AttachedResult(launcher.INTERRUPTED_EXIT_CODE, interrupted=True, stopped=False)
    assert client.killed
    assert interrupts == 1


@pytest.mark.parametrize("daemon_wait_outcome", ["timeout", "interrupt", "stop_oserror"])
def test_run_attached_stops_waiting_when_daemon_stop_fails_or_is_interrupted(
    daemon_wait_outcome: str,
) -> None:
    import subprocess as sp
    from devcapsule.launch.pycharm import _launcher as launcher

    class Client:
        waits = 0
        killed = False

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise KeyboardInterrupt
            if self.waits == 2:
                raise sp.TimeoutExpired("docker", timeout)
            if self.waits == 3 and not self.killed:
                assert timeout == launcher.DAEMON_STOP_SECONDS
                if daemon_wait_outcome == "timeout":
                    raise sp.TimeoutExpired("docker", timeout)
                raise KeyboardInterrupt
            return -9

        def kill(self):
            self.killed = True

    client = Client()
    stop_effect = OSError("daemon unavailable") if daemon_wait_outcome == "stop_oserror" else SimpleNamespace(returncode=1)
    with (
        patch.object(launcher.subprocess, "Popen", return_value=client),
        patch.object(launcher.subprocess, "run", side_effect=stop_effect if isinstance(stop_effect, Exception) else None, return_value=stop_effect) as stop,
    ):
        result = launcher.run_attached(["docker", "run", "image"], {}, container_name="capsule")
    assert result == AttachedResult(launcher.INTERRUPTED_EXIT_CODE, interrupted=True, stopped=False)
    assert client.killed
    assert stop.call_args.kwargs["timeout"] == launcher.DAEMON_STOP_SECONDS


def test_run_attached_reports_stopped_when_kill_races_the_clients_own_exit() -> None:
    from devcapsule.launch.pycharm import _launcher as launcher

    class Client:
        waits = 0
        killed = False

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits <= 2:
                raise KeyboardInterrupt
            return 143

        def kill(self):
            self.killed = True

    client = Client()
    with patch.object(launcher.subprocess, "Popen", return_value=client):
        result = launcher.run_attached(["docker", "run", "image"], {}, container_name="capsule")
    assert result == AttachedResult(143, interrupted=True, stopped=True)
    assert client.killed


def test_run_attached_returns_the_capsules_exit_code_when_nothing_interrupts() -> None:
    from devcapsule.launch.pycharm import _launcher as launcher

    interrupts = 0

    def record_interrupt() -> None:
        nonlocal interrupts
        interrupts += 1

    client = SimpleNamespace(wait=lambda timeout=None: 7)
    with patch.object(launcher.subprocess, "Popen", return_value=client):
        assert launcher.run_attached(
            ["docker"], {}, container_name="c", on_interrupt=record_interrupt,
        ) == AttachedResult(7, interrupted=False, stopped=True)
    assert interrupts == 0


@pytest.mark.parametrize("result,head", [
    (AttachedResult(0, interrupted=False, stopped=True), "Session ended: the IDE exited and the capsule stopped."),
    (AttachedResult(INFRASTRUCTURE_FAILURE_EXIT_CODE, interrupted=False, stopped=True),
     "Session failed: a capsule component died; the supervisor's log names it."),
    (AttachedResult(7, interrupted=False, stopped=True), "Session ended with exit code 7."),
    (AttachedResult(143, interrupted=True, stopped=True), "Session interrupted from the terminal (Ctrl+C); the capsule stopped."),
    (AttachedResult(130, interrupted=True, stopped=False),
     "Session interrupted from the terminal; the capsule may still be running. Stop it with: docker stop "),
])
def test_session_result_names_the_outcome_and_every_log_file(tmp_path: Path, result, head) -> None:
    from devcapsule.launch.pycharm import _launcher as launcher

    config, _env = session_config(tmp_path)
    assert config.session_log_directory is not None
    config.session_log_directory.mkdir(parents=True, exist_ok=True)
    for name in ("devcapsule-launcher.log", "devcapsule-supervisor.log", "devcapsule-pycharm.log", "session.json"):
        (config.session_log_directory / name).write_text("", encoding="utf-8")
    (config.session_log_directory / "second-session").mkdir()
    text = launcher.session_result_text(config, result)
    lines = text.splitlines()
    assert lines[0].startswith(head)
    if not result.stopped:
        assert lines[0].endswith(config.name)
    assert lines[1] == "Session logs on this computer:"
    assert lines[2:] == [
        f"  {config.session_log_directory / name}"
        for name in ("devcapsule-launcher.log", "devcapsule-pycharm.log", "devcapsule-supervisor.log", "session.json")
    ]


def test_session_result_without_a_log_directory_says_so(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace
    from devcapsule.launch.pycharm import _launcher as launcher

    config, _env = session_config(tmp_path)
    text = launcher.session_result_text(replace(config, session_log_directory=None), AttachedResult(0, False, True))
    assert text.splitlines() == [
        "Session ended: the IDE exited and the capsule stopped.",
        "Session logs: none; this session logged to the console only.",
    ]
    assert config.session_log_directory is not None
    config.session_log_directory.mkdir(parents=True, exist_ok=True)
    empty_lines = [
        "Session ended: the IDE exited and the capsule stopped.",
        "Session logs on this computer:",
        f"  {config.session_log_directory}",
    ]
    assert launcher.session_result_text(config, AttachedResult(0, False, True)).splitlines() == empty_lines
    (config.session_log_directory / "devcapsule-launcher.log").write_text("", encoding="utf-8")
    monkeypatch.setattr(Path, "iterdir", lambda self: (_ for _ in ()).throw(PermissionError("unreadable")))
    assert launcher.session_result_text(config, AttachedResult(0, False, True)).splitlines() == empty_lines


def test_the_log_budget_knob_sets_the_segment_and_reports_nonsense(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config, _env = session_config(tmp_path, DEVCAPSULE_LOG_BUDGET="1G")
    assert config.log_budget_bytes == 1024 ** 3
    assert config.runtime_plan is not None and config.runtime_plan.logs is not None
    assert (config.runtime_plan.logs.segment_bytes, config.runtime_plan.logs.rotations) == (10 * 1024 * 1024, 4)
    print_storage_summary(config)
    assert "(budget 1 GiB)" in capsys.readouterr().err
    for value, message in (
        ("lots", "DEVCAPSULE_LOG_BUDGET: 'lots' is not a size"),
        ("1M", "DEVCAPSULE_LOG_BUDGET must be at least 16 MiB"),
        ("9" * 5000, "DEVCAPSULE_LOG_BUDGET: size contains too many digits"),
    ):
        fallback, _ = session_config(tmp_path, DEVCAPSULE_LOG_BUDGET=value)
        assert fallback.log_budget_bytes == 256 * 1024 ** 2
        assert fallback.runtime_plan is not None and fallback.runtime_plan.logs is not None
        assert fallback.runtime_plan.logs.segment_bytes == 8 * 1024 ** 2
        warning = capsys.readouterr().err
        assert message in warning
        assert warning.count("using the default log budget of 256 MiB") == 1


def test_the_launcher_records_the_sessions_end_in_its_manifest(tmp_path: Path) -> None:
    import json

    from devcapsule import logs
    from devcapsule.launch.pycharm import _launcher as launcher
    from devcapsule.launch.session_logs import mark_session_ended

    assert "130" in (mark_session_ended.__doc__ or "") and "None" not in (mark_session_ended.__doc__ or "")
    config, env = session_config(tmp_path)
    assert config.session_log_directory is not None
    try:
        with (
            patch.object(launcher, "build_run_config", return_value=config),
            patch.object(launcher, "write_xauthority"),
            patch.object(launcher, "write_user_files"),
            patch.object(launcher, "watch_display_ready"),
            patch.object(launcher, "run_attached", return_value=AttachedResult(7, interrupted=False, stopped=True)),
        ):
            assert run_pycharm(PycharmRunOptions(project=config.project, capsule_platform=Platform.LINUX_AMD64), env) == 7
        manifest = json.loads((config.session_log_directory / "session.json").read_text(encoding="utf-8"))
        assert manifest["session"] == config.session_id and manifest["exit-code"] == 7
        assert manifest["ended-at"].endswith("Z") and logs.session_ended(config.session_log_directory)
        with (
            patch.object(launcher, "build_run_config", return_value=config),
            patch.object(launcher, "write_xauthority"),
            patch.object(launcher, "write_user_files"),
            patch.object(launcher, "watch_display_ready"),
            patch.object(launcher, "run_attached", return_value=AttachedResult(143, interrupted=True, stopped=True)),
        ):
            assert run_pycharm(PycharmRunOptions(project=config.project, capsule_platform=Platform.LINUX_AMD64), env) == launcher.INTERRUPTED_EXIT_CODE
        manifest = json.loads((config.session_log_directory / "session.json").read_text(encoding="utf-8"))
        assert manifest["exit-code"] == launcher.INTERRUPTED_EXIT_CODE and manifest["ended-at"]
    finally:
        logs.reset()


def test_interrupted_launch_with_unstopped_capsule_leaves_session_manifest_unended(tmp_path: Path) -> None:
    import json

    from devcapsule import logs
    from devcapsule.launch.pycharm import _launcher as launcher

    config, env = session_config(tmp_path)
    assert config.session_log_directory is not None
    try:
        with (
            patch.object(launcher, "build_run_config", return_value=config),
            patch.object(launcher, "write_xauthority"),
            patch.object(launcher, "write_user_files"),
            patch.object(launcher, "watch_display_ready"),
            patch.object(
                launcher,
                "run_attached",
                return_value=AttachedResult(launcher.INTERRUPTED_EXIT_CODE, interrupted=True, stopped=False),
            ),
        ):
            assert run_pycharm(PycharmRunOptions(project=config.project, capsule_platform=Platform.LINUX_AMD64), env) == launcher.INTERRUPTED_EXIT_CODE
        manifest = json.loads((config.session_log_directory / "session.json").read_text(encoding="utf-8"))
        assert "ended-at" not in manifest and "exit-code" not in manifest
        assert not logs.session_ended(config.session_log_directory)
        record = (config.session_log_directory / "devcapsule-launcher.log").read_text(encoding="utf-8")
        assert f"session end unknown: interrupted from the terminal (Ctrl+C); container {config.name} may still be running" in record
    finally:
        logs.reset()
