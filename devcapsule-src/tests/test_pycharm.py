from __future__ import annotations

from pathlib import Path
import time
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest

from devcapsule.components.pycharm import runtime_template as pycharm_runtime_template
from devcapsule.launch.pycharm import DockerMode, PycharmRunOptions, build_run_config
from devcapsule.container_runtime.contract import INFRASTRUCTURE_FAILURE_EXIT_CODE
from devcapsule.platforms import Platform
from devcapsule.launch.pycharm._launcher import (
    AttachedResult,
    describe_run_command,
    console_development_source,
    console_disclosure,
    HostUser,
    PycharmRunError,
    PycharmRunConfig,
    TempRuntimeFiles,
    build_docker_args,
    cleanup_temp_runtime_files,
    prepare_temp_runtime_files,
    print_storage_summary,
    write_user_files,
)
from devcapsule.container_runtime.contract import DisplayPlan, Identity, LogsPlan, RuntimePlan
from devcapsule.launch.session_logs import SESSION_LOG_DESTINATION

from devcapsule.container_runtime.contract import ConsolePlan

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


def test_web_console_runs_the_checkouts_source_under_the_self_hosting_exception(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "devcapsule-webconsole" / "devcapsule_webconsole").mkdir(parents=True)
    (project / "devcapsule-webconsole" / "devcapsule_webconsole" / "__init__.py").write_text("", encoding="utf-8")
    config = contained_config(tmp_path)
    assert config.runtime_plan is not None and config.runtime_plan.console is not None
    assert config.runtime_plan.console.source_path == "/workspace/project/devcapsule-webconsole"
    assert console_development_source(tmp_path / "other", "/workspace/other") == ""


def test_console_disclosure_states_where_it_listens(tmp_path: Path) -> None:
    contained = contained_config(tmp_path)
    text = console_disclosure(contained)
    assert "Web console:" in text and "read-only" in text
    assert f"container port 6081, published to host loopback port {contained.console_host_port}" in text
    direct = contained_config(tmp_path, network_mode="host")
    assert f"host loopback port {direct.console_host_port} (host networking)" in console_disclosure(direct)


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
