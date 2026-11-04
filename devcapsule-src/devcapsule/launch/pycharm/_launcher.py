"""Translated PyCharm launcher for DevCapsule."""

from __future__ import annotations

import grp
import json
import logging
import os
import pwd
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from threading import Event
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...docker_arguments import inline_environment_names, redact_environment
from ...platforms import HostOs, Platform
from ...container_runtime.contract import (
    CONTAINED_DISPLAY_TRANSPORT,
    INFRASTRUCTURE_FAILURE_EXIT_CODE,
    DISPLAY_TRANSPORTS,
    HOST_X11_DISPLAY_TRANSPORT,
    ConsolePlan,
    DisplayPlan,
    LogsPlan,
    RuntimePlan,
)
from ... import logs
from ..session_logs import (
    LAUNCHER_LOG_COMPONENT,
    SESSION_LOG_DESTINATION,
    mark_session_ended,
    session_logs_root,
    session_manifest,
    write_session_manifest,
)
from ...display_client import (
    CONSOLE_LABEL_TEXT,
    CONSOLE_TOKEN_DESTINATION,
    CONSOLE_URL_ENV,
    CONTAINER_CONSOLE_PORT,
    CONTAINER_DISPLAY_PORT,
    DISPLAY_TOKEN_DESTINATION,
    allocate_loopback_port,
    console_origin,
    console_url,
    default_opener,
    display_url,
    new_run_token,
    print_only_opener,
    watch_display_ready,
)
from ...host_daemon import (
    current_container,
    daemon_architecture,
    docker_socket,
    is_host_backed,
    requires_translation,
    translate_bind_sources,
)
from ...host_open import (
    HOST_OPEN_BROWSER,
    HOST_OPEN_INTEGRATION,
    HOST_OPEN_SOCKET_DESTINATION,
    HOST_OPEN_SOCKET_ENV,
    HostOpenError,
    host_open_bridge,
)
from ..command_output import render_command
from ...build_info import BuildInfoError, current_build_info
from ...images.contract import WEBCONSOLE_RECIPE, WebConsoleAvailability
from ...materialization import RUNTIME_PLAN_PATH
from ...commands._console_channel import ChannelWatcher
from ...configuration.console_channel import LISTING_FILE, listing_document, write_complete
from ...runtime_configuration import CHANNEL_PATH, CONFIGURATION_PATH, CONTEXT_PATH, LaunchConfiguration
from ...project import ProjectMountError
from ...runtime import (
    plan_shared_runtime,
    resolve_existing_or_create,
    SharedRuntimeOptions,
)


class PycharmRunError(Exception):
    """User-facing PyCharm launcher error."""


class DockerMode(str, Enum):
    host = "host"
    dind = "dind"
    none = "none"


class IdeConfigMode(str, Enum):
    shared = "shared"
    project = "project"
    custom = "custom"


@dataclass(frozen=True)
class HostUser:
    uid: int
    gid: int
    name: str
    group_name: str


@dataclass
class TempRuntimeFiles:
    xauth_file: Path
    passwd_file: Path
    group_file: Path
    shadow_file: Path | None = None
    sudoers_directory: Path | None = None
    sudoers_file: Path | None = None
    token_file: Path | None = None
    runtime_plan_file: Path | None = None
    display_token_file: Path | None = None
    console_token_file: Path | None = None
    launch_context_file: Path | None = None
    # The console's configuration channel: a directory the capsule writes
    # requests into and reads the launch-time listing from; CHANNEL_PATH inside.
    configuration_directory: Path | None = None
    # On macOS, the Docker volume that holds the root-owned sudo policy.
    sudoers_volume: str | None = None


SUDOERS_POLICY_PATH = "/etc/sudoers.d/devcapsule-development-sudo"
SUDOERS_POLICY = "%ide-sudo ALL=(ALL:ALL) NOPASSWD: ALL\n"
SUDOERS_VOLUME_FILE = "policy"
"""The policy's name inside its macOS volume."""
SUDOERS_VOLUME_LABEL = "devcapsule.purpose=development-sudo-policy"
ABANDONED_SUDOERS_VOLUME_AGE = timedelta(days=1)
"""How old a policy volume no container uses must be to count as a killed launch's."""



LOCAL_BASE_GUIDE_URL = "https://devcapsule.mycodespace.ai/docs/current/configuration/local-base/"


def web_console_notice(availability: WebConsoleAvailability) -> str:
    """One true statement in place of the console link on a base without one.

    Names the base, the recipe the console needs, the one command that builds
    a base with it from this launcher's own source, and the guide that says
    how to select the built base for a checkout.
    """

    base = availability.base or "an image without DevCapsule recipe labels"
    try:
        revision = current_build_info().source_revision
    except BuildInfoError:
        revision = "unknown"
    provenance = (
        f"--source-revision {revision}"
        if re.fullmatch(r"[0-9a-f]{40,64}", revision)
        else "--allow-local-source"
    )
    return (
        f"Web console: none on this base ({base}; the console needs base recipe "
        f"{WEBCONSOLE_RECIPE} or later); the capsule runs without it.\n"
        f"  To build a base that has it:  devcapsule images build --type base "
        f"--recipe ubuntu-24.04 {provenance}\n"
        f"  Then select it for this checkout; the steps: {LOCAL_BASE_GUIDE_URL}"
    )


@dataclass
class PycharmRunOptions:
    project: Path
    # The lock's platform: what the capsule runs as.
    capsule_platform: Platform
    # Project configuration is complete; only the legacy command inherits
    # ambient launcher options. Host observations and explicit secret sources
    # remain available in either mode.
    inherit_legacy_configuration: bool = True
    command_report: Callable[[str], None] | None = None
    profile: str | None = None
    image: str | None = None
    name: str | None = None
    global_settings: Path | None = None
    persistent_home: Path | None = None
    project_state: Path | None = None
    project_state_root: Path | None = None
    ide_system: Path | None = None
    ide_log: Path | None = None
    tool_cache: Path | None = None
    config_mode: IdeConfigMode | None = None
    ide_config: Path | None = None
    project_mount: str | None = None
    plugins: Path | None = None
    use_ssh_agent: bool = False
    git_user_name: str | None = None
    git_user_email: str | None = None
    git_identity_from_host: str | None = None
    git_token_file: Path | None = None
    git_token_env: str | None = None
    git_token_username: str | None = None
    git_token_hosts: str | None = None
    docker_mode: DockerMode | None = None
    host_docker_socket: Path | None = None
    debug_native: bool = False
    writable_root: bool = False
    enable_sudo: bool | None = None
    ide_sudo_gid: str | None = None
    ignore_config_lock: bool = False
    network_mode: str = "host"
    memory_limit_bytes: int | None = None
    # The CPU count the capsule may use, Docker's --cpus; None leaves it unlimited.
    cpus: int | None = None
    runtime_plan: RuntimePlan | None = None
    launch_configuration: LaunchConfiguration | None = None
    use_image_process: bool = False
    # When non-empty, the interactive surface's state comes from these
    # runtime-plan-declared slot mounts and the named PyCharm state fields
    # (ide_config, plugins, ide_system, ide_log, tool_cache) stay unused.
    interactive_state_mounts: dict[str, tuple[Path, str]] = field(default_factory=dict)
    additional_state_mounts: dict[str, tuple[Path, str]] = field(default_factory=dict)
    additional_environment: dict[str, str] = field(default_factory=dict)
    secret_environment: tuple[str, ...] = ()
    extra_docker_args: list[str] = field(default_factory=list)
    enable_host_browser: bool = False
    # How the surface gets a display. ``host-x11`` is the historical
    # passthrough (host X socket and session credential bound into the
    # capsule); ``contained`` is the capsule's own desktop reached through a
    # browser, which requires an image carrying the display stack and an
    # external runtime plan. The caller decides; see commands/project.py.
    display_transport: str = HOST_X11_DISPLAY_TRANSPORT
    # Test seam: how the contained display's URL is opened once ready.
    open_display_url: Callable[[str], None] | None = None
    open_console_url: Callable[[str], None] | None = None
    # Whether the base promises a web console, read from its labels by the
    # caller (commands/project.py); without it the launcher announces the
    # absence once and plans no console: no port, no token, no wait.
    web_console: WebConsoleAvailability = WebConsoleAvailability(True, None)


@dataclass
class PycharmRunConfig:
    image: str
    name: str
    project: Path
    global_settings: Path
    persistent_home: Path
    project_state: Path
    # None exactly when interactive_state_mounts drives the surface's state.
    ide_system: Path | None
    ide_log: Path | None
    tool_cache: Path | None
    ide_config: Path | None
    ide_config_mode: str
    plugins: Path | None
    project_mount: str
    docker_mode: str
    host_docker_socket: Path
    host_docker_gid: int | None
    use_ssh_agent: bool
    git_user_name: str
    git_user_email: str
    git_token_file: Path | None
    git_token_env: str
    git_token_username: str
    git_token_hosts: str
    debug_native: bool
    writable_root: bool
    enable_sudo: bool
    ide_sudo_gid: int
    ignore_config_lock: bool
    network_mode: str
    memory_limit_bytes: int | None
    runtime_plan: RuntimePlan | None
    use_image_process: bool
    capsule_platform: Platform
    # The Docker daemon's, asked once per launch: it decides emulation.
    daemon_architecture: str
    cpus: int | None = None
    launch_configuration: LaunchConfiguration | None = None
    host_browser_socket: Path | None = None
    display_transport: str = HOST_X11_DISPLAY_TRANSPORT
    # Contained display only: the host loopback port Docker publishes (or the
    # bridge listens on directly under host networking) and the per-run token.
    display_host_port: int | None = None
    display_token: str = ""
    open_display_url: Callable[[str], None] | None = None
    # The web console, whenever the runtime runs: the host loopback port
    # Docker publishes (or the console listens on directly under host
    # networking) and its per-run token. None without a runtime plan.
    console_host_port: int | None = None
    console_token: str = ""
    open_console_url: Callable[[str], None] | None = None
    web_console: WebConsoleAvailability = WebConsoleAvailability(True, None)
    # This session's log directory on the host, bound into the capsule at
    # SESSION_LOG_DESTINATION: the launcher's own log, the supervisor's, and
    # one file per supervised child (see devcapsule.logs).
    session_id: str = ""
    session_log_directory: Path | None = None
    log_budget_bytes: int = logs.DEFAULT_BUDGET_BYTES
    interactive_state_mounts: tuple[tuple[str, str, str], ...] = ()
    additional_state_mounts: tuple[tuple[str, str, str], ...] = ()
    additional_environment: tuple[tuple[str, str], ...] = ()
    secret_environment: tuple[str, ...] = ()
    extra_docker_args: list[str] = field(default_factory=list)
    libgl_always_software: str = "1"
    mesa_loader_driver_override: str = "llvmpipe"
    libgl_dri3_disable: str = "1"


HOST_NETWORK_UNAVAILABLE_ON_MACOS = (
    "Warning: host networking is unavailable on macOS: Docker Desktop's host network "
    "is its virtual machine's, out of the Mac's reach. This launch uses bridge networking; "
    "services on the Mac are reachable from the capsule as host.docker.internal."
)


def run_pycharm(options: PycharmRunOptions, env: Mapping[str, str] | None = None) -> int:
    """Run PyCharm through the translated Python launcher."""

    try:
        runtime_env = host_backed_runtime_environment(
            dict(os.environ if env is None else env)
        )
        with host_open_bridge(
            runtime_env,
            enabled=options.enable_host_browser,
        ) as browser_socket:
            if browser_socket is None:
                runtime_env.pop(HOST_OPEN_SOCKET_ENV, None)
            else:
                runtime_env[HOST_OPEN_SOCKET_ENV] = str(browser_socket)
            config = build_run_config(options, runtime_env)
            begin_session_logs(config, runtime_env)
            prepare_home_mount_points(config)
            files = prepare_temp_runtime_files(config, runtime_env)
            try:
                if config.enable_sudo:
                    ensure_sudoers_policy_ownership(config, files, runtime_env)
                docker_args = build_docker_args(config, files, runtime_env)
                docker_args = translate_for_external_daemon(docker_args, runtime_env)
                print_storage_summary(config)
                if config.enable_sudo:
                    print_sudo_warning()
                command = ["docker", "run", *docker_args, config.image]
                if not config.use_image_process:
                    command.extend(["/opt/pycharm/bin/pycharm.sh", config.project_mount])
                if options.command_report is not None:
                    options.command_report(describe_run_command(command, config, files))
                    return 0  # Cleanup still runs; no container or display watcher.
                stop_watching = Event()
                if config.display_transport == CONTAINED_DISPLAY_TRANSPORT:
                    assert config.display_host_port is not None
                    url = display_url(config.display_host_port, config.display_token)
                    print(
                        f"Contained display: {url}\n"
                        "  (opens in your browser once the capsule is ready; closing the tab "
                        "does not end the session)",
                        file=sys.stderr,
                        flush=True,
                    )
                    watch_display_ready(
                        config.display_host_port,
                        url,
                        config.open_display_url or default_opener(runtime_env),
                        stop_watching,
                    )
                if config.runtime_plan is not None and not config.web_console.available:
                    print(web_console_notice(config.web_console), file=sys.stderr, flush=True)
                if config.console_host_port is not None:
                    console = console_url(config.console_host_port, config.console_token)
                    print(
                        f"Web console: {console}\n"
                        "  (the capsule as a page; the link works for this run only)",
                        file=sys.stderr,
                        flush=True,
                    )
                    # One page opens by itself: the desktop when there is one,
                    # else the console. The other is announced, not opened.
                    opener = config.open_console_url or (
                        print_only_opener(CONSOLE_LABEL_TEXT)
                        if config.display_transport == CONTAINED_DISPLAY_TRANSPORT
                        else default_opener(runtime_env, label=CONSOLE_LABEL_TEXT)
                    )
                    watch_display_ready(
                        config.console_host_port, console, opener, stop_watching, label=CONSOLE_LABEL_TEXT,
                    )
                # The session log outlives the session on the host: mask the
                # inline environment values of the extra arguments, as the
                # printed command does; Docker receives the command unchanged.
                _session_events.info("docker run: %s", shlex.join(
                    redact_environment(command, inline_environment_names(config.extra_docker_args))))
                watcher = channel_watcher(config, files)
                if watcher is not None:
                    watcher.start()
                try:
                    result = run_attached(
                        command, runtime_env, container_name=config.name, on_interrupt=stop_watching.set,
                    )
                finally:
                    stop_watching.set()
                    if watcher is not None:
                        watcher.stop()
                exit_code = INTERRUPTED_EXIT_CODE if result.interrupted else result.exit_code
                if not result.stopped:
                    _session_events.info(
                        "session end unknown: interrupted from the terminal (Ctrl+C); container %s may still be running",
                        config.name,
                    )
                else:
                    if result.interrupted:
                        _session_events.info(
                            "session end: interrupted from the terminal (Ctrl+C); docker run exit code %d",
                            result.exit_code,
                        )
                    else:
                        _session_events.info("session end: docker run exit code %d", result.exit_code)
                    end_session_logs(config, exit_code)
                print(session_result_text(config, result), file=sys.stderr, flush=True)
                return exit_code
            finally:
                remove_sudoers_policy_volume(files.sudoers_volume, runtime_env)
                cleanup_temp_runtime_files(files)
    except HostOpenError as exc:
        raise PycharmRunError(str(exc)) from exc


_session_events = logs.events_logger(LAUNCHER_LOG_COMPONENT)

INTERRUPTED_EXIT_CODE = 130
"""What the launcher returns after Ctrl+C: 128 + SIGINT, as shells report it."""

INTERRUPT_STOP_SECONDS = 60.0
"""How long the launcher waits for the capsule to stop after Ctrl+C before it
asks the daemon; the supervisor's own grace is seconds, so this is generous."""

DAEMON_STOP_SECONDS = 30.0
"""How long the launcher waits after asking the daemon to stop the capsule."""


@dataclass(frozen=True)
class AttachedResult:
    """How the attached ``docker run`` ended."""

    exit_code: int
    """The client's exit code: the capsule's own, or INTERRUPTED_EXIT_CODE when
    the launcher stopped waiting for it."""
    interrupted: bool
    """The terminal interrupted the session with Ctrl+C."""
    stopped: bool
    """The client returned, so the capsule has stopped. False only when the
    launcher stopped waiting for it, in which case the capsule may still run."""


def run_attached(
    command: Sequence[str],
    env: Mapping[str, str],
    *,
    container_name: str,
    on_interrupt: Callable[[], None] = lambda: None,
) -> AttachedResult:
    """Run the capsule in the foreground and wait through Ctrl+C for its end.

    The terminal delivers SIGINT to the whole foreground group: the docker
    client gets it and forwards it into the capsule, whose supervisor stops
    its children within its grace period and exits; then the client returns
    the capsule's exit code. ``subprocess.run`` would instead kill the client
    a quarter of a second after the interrupt and raise, which is how Ctrl+C
    used to end in a traceback with the capsule's end unknown. So the client
    is waited for explicitly: the first Ctrl+C is announced and waited
    through; a capsule that has not stopped within INTERRUPT_STOP_SECONDS is
    stopped through the daemon; a second Ctrl+C stops the waiting and says
    what may still be running.
    """

    process = subprocess.Popen(command, env=env)
    try:
        return AttachedResult(process.wait(), interrupted=False, stopped=True)
    except KeyboardInterrupt:
        pass
    try:
        on_interrupt()
        print(
            "Interrupted from the terminal (Ctrl+C); the capsule is stopping. "
            "Press Ctrl+C again to stop waiting for it.",
            file=sys.stderr, flush=True,
        )
        try:
            return AttachedResult(process.wait(timeout=INTERRUPT_STOP_SECONDS), interrupted=True, stopped=True)
        except subprocess.TimeoutExpired:
            print(
                f"The capsule has not stopped after {INTERRUPT_STOP_SECONDS:g}s; asking the daemon to stop it.",
                file=sys.stderr, flush=True,
            )
            subprocess.run(
                ["docker", "stop", "--time", "10", container_name],
                check=False, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=DAEMON_STOP_SECONDS,
            )
            return AttachedResult(process.wait(timeout=DAEMON_STOP_SECONDS), interrupted=True, stopped=True)
    except (KeyboardInterrupt, subprocess.TimeoutExpired, OSError):
        process.kill()
        exit_code = process.wait()
        if exit_code >= 0:
            return AttachedResult(exit_code, interrupted=True, stopped=True)
        return AttachedResult(INTERRUPTED_EXIT_CODE, interrupted=True, stopped=False)


def session_result_text(config: PycharmRunConfig, result: AttachedResult) -> str:
    """The one statement that ends a session on the terminal, and where its logs are.

    The terminal no longer carries the components' output, so this is what a
    user reads at the end: what happened, and the files on this computer
    that hold the detail.
    """

    if result.interrupted and not result.stopped:
        head = (
            "Session interrupted from the terminal; the capsule may still be running. "
            f"Stop it with: docker stop {config.name}"
        )
    elif result.interrupted:
        head = "Session interrupted from the terminal (Ctrl+C); the capsule stopped."
    elif result.exit_code == 0:
        head = "Session ended: the IDE exited and the capsule stopped."
    elif result.exit_code == INFRASTRUCTURE_FAILURE_EXIT_CODE:
        head = "Session failed: a capsule component died; the supervisor's log names it."
    else:
        head = f"Session ended with exit code {result.exit_code}."
    lines = [head]
    directory = config.session_log_directory
    if directory is None:
        lines.append("Session logs: none; this session logged to the console only.")
        return "\n".join(lines)
    try:
        files = sorted(path for path in directory.iterdir() if path.is_file()) if directory.is_dir() else []
    except OSError:
        files = []
    lines.append("Session logs on this computer:")
    lines.extend(f"  {path}" for path in files or [directory])
    return "\n".join(lines)


def _session_display_metadata(config: PycharmRunConfig) -> dict[str, object]:
    if config.display_transport != CONTAINED_DISPLAY_TRANSPORT:
        return {"transport": config.display_transport}
    container_port = (
        config.runtime_plan.display.port
        if config.runtime_plan is not None and config.runtime_plan.display is not None
        else CONTAINER_DISPLAY_PORT
    )
    return {
        "transport": CONTAINED_DISPLAY_TRANSPORT,
        "host-port": config.display_host_port,
        "container-port": container_port,
    }


def _session_console_metadata(config: PycharmRunConfig) -> dict[str, object]:
    if config.console_host_port is None:
        return {"enabled": False}
    container_port = (
        config.runtime_plan.console.port
        if config.runtime_plan is not None and config.runtime_plan.console is not None
        else CONTAINER_CONSOLE_PORT
    )
    return {
        "enabled": True,
        "host-port": config.console_host_port,
        "container-port": container_port,
    }


def _session_ide_logs(config: PycharmRunConfig) -> list[dict[str, str]]:
    if not config.interactive_state_mounts:
        if config.ide_log is None:
            return []
        return [{
            "slot": "pycharm/log",
            "family": "jetbrains",
            "host-path": str(config.ide_log),
            "container-path": "/ide-project-state/log",
        }]
    if config.runtime_plan is None:
        return []
    mounts = {name: (source, destination) for name, source, destination in config.interactive_state_mounts}
    component = config.runtime_plan.component
    configuration = component.configuration
    if component.adapter == "jetbrains":
        mapping = configuration.get("state_slot_mapping")
        local_slot = mapping.get("log") if isinstance(mapping, dict) else None
        if isinstance(local_slot, str):
            slot_name = component.slot_name(local_slot)
            if slot_name in mounts:
                source, destination = mounts[slot_name]
                return [{
                    "slot": slot_name,
                    "family": "jetbrains",
                    "host-path": source,
                    "container-path": destination,
                }]
    elif component.adapter == "vscode":
        mapping = configuration.get("state_slot_mapping")
        local_slot = mapping.get("user-data") if isinstance(mapping, dict) else None
        if isinstance(local_slot, str):
            slot_name = component.slot_name(local_slot)
            if slot_name in mounts:
                source, destination = mounts[slot_name]
                return [{
                    "slot": slot_name,
                    "family": "vscode",
                    "host-path": str(Path(source) / "logs"),
                    "container-path": f"{destination.rstrip('/')}/logs",
                }]
    elif component.adapter == "eclipse":
        local_slot = configuration.get("workspace_slot")
        if isinstance(local_slot, str):
            slot_name = component.slot_name(local_slot)
            if slot_name in mounts:
                source, destination = mounts[slot_name]
                return [{
                    "slot": slot_name,
                    "family": "eclipse",
                    "host-path": str(Path(source) / ".metadata"),
                    "container-path": f"{destination.rstrip('/')}/.metadata",
                }]
    return []


def begin_session_logs(config: PycharmRunConfig, env: Mapping[str, str]) -> None:
    """Open the launcher's log, write the session manifest, prune old sessions.

    Nothing here may stop the launch: a log directory that cannot be written
    is reported on the console and the session runs without files.
    """

    directory = config.session_log_directory
    logs.configure(
        LAUNCHER_LOG_COMPONENT, directory, environ=env,
        segment_bytes=logs.segment_bytes_for(config.log_budget_bytes), rotations=logs.ROTATIONS,
    )
    if directory is None:
        return
    component = config.runtime_plan.component.id if config.runtime_plan is not None else "pycharm"
    try:
        write_session_manifest(directory, session_manifest(
            session_id=config.session_id, project=config.project, project_mount=config.project_mount,
            image=config.image, container_name=config.name, component=component,
            budget_bytes=config.log_budget_bytes,
            network_mode=config.network_mode,
            display=_session_display_metadata(config),
            console=_session_console_metadata(config),
            ide_logs=_session_ide_logs(config),
        ))
    except OSError as error:
        print(f"devcapsule launcher: cannot write the session manifest in {directory} ({error})", file=sys.stderr)
    _session_events.info(
        "session %s start: image %s, container %s, project %s", config.session_id, config.image, config.name, config.project,
    )
    removed = logs.prune_sessions(directory.parent, budget_bytes=config.log_budget_bytes, current=directory.name)
    if removed:
        _session_events.info(
            "removed %d older session log directories to fit the %s budget: %s",
            len(removed), logs.format_size(config.log_budget_bytes), ", ".join(removed),
        )


def end_session_logs(config: PycharmRunConfig, exit_code: int | None) -> None:
    """Record the session's end in its manifest, so a later launch may prune it."""

    directory = config.session_log_directory
    if directory is None:
        return
    try:
        mark_session_ended(directory, exit_code)
    except OSError as error:
        print(f"devcapsule launcher: cannot record the session's end in {directory} ({error})", file=sys.stderr)


def describe_run_command(command: list[str], config: PycharmRunConfig,
                         files: TempRuntimeFiles) -> str:
    comments = [
        "Diagnostic Docker command; the project container has NOT been started.",
        "Preparation may have acquired/built the selected image and prepared state directories.",
        "This is not a standalone replay script. Review dependencies before manual execution.",
        "Use the same host and Docker context/environment (including DOCKER_HOST if set).",
        "Project and persistent-state mounts refer to existing host paths; edits can change host access.",
        "The following local staging files are removed when this command returns.",
        "Bind sources in the command may be translated to external Docker-daemon host paths.",
    ]
    for label, path in (
        ("Xauthority", files.xauth_file if config.display_transport != CONTAINED_DISPLAY_TRANSPORT else None),
        ("User identity", files.passwd_file), ("Group identity", files.group_file),
        ("Shadow file", files.shadow_file), ("Sudo policy", files.sudoers_file),
        ("Git token file", files.token_file), ("Runtime plan", files.runtime_plan_file),
        ("Display token", files.display_token_file), ("Console token", files.console_token_file),
        ("Launch context", files.launch_context_file), ("Configuration channel", files.configuration_directory),
    ):
        if path is not None:
            comments.append(f"Temporary {label}: {path}")
    if config.session_log_directory is not None:
        comments.append(
            f"Session logs: {config.session_log_directory} (bound at {SESSION_LOG_DESTINATION}; "
            f"checkout budget {logs.format_size(config.log_budget_bytes)}, {logs.BUDGET_ENV})"
        )
    if config.host_browser_socket is not None:
        comments.append("Host-browser socket requires a live broker; a broker owned by this invocation stops on return.")
    if config.display_transport == CONTAINED_DISPLAY_TRANSPORT:
        comments.append("Contained display needs its temporary token file; the chosen host port is not reserved for later use.")
    if config.console_host_port is not None:
        comments.append("The web console needs its temporary token file; the chosen host port is not reserved for later use.")
    if config.secret_environment:
        comments.append("Required environment variables (values omitted): " + ", ".join(config.secret_environment))
    comments.append("No successful-use history was recorded. Manual execution and any edits are your responsibility.")
    names = inline_environment_names(config.extra_docker_args)
    if names:
        comments.append("Inline environment values are redacted; use project run to launch the saved arguments.")
    return render_command(redact_environment(command, names), comments)


def host_backed_runtime_environment(env: Mapping[str, str]) -> dict[str, str]:
    """Stage transient launch files where an external daemon can read them.

    The launcher writes an Xauthority, passwd/group, and runtime plan and binds
    them into the container it starts. `XDG_RUNTIME_DIR` normally points at a
    container-local tmpfs, which an external daemon cannot see, so those binds
    would arrive empty. Move the staging directory somewhere backed by a mount.
    """

    from devcapsule.platforms import XdgHomes
    runtime_env = dict(env)
    homes = XdgHomes.from_environment(env)
    if homes.chosen_by == "DEVCAPSULE_CONFIG_HOME":
        runtime_env["XDG_RUNTIME_DIR"] = str(homes.state / "runtime")
        Path(runtime_env["XDG_RUNTIME_DIR"]).mkdir(mode=0o700, parents=True, exist_ok=True)
    if not requires_translation(runtime_env):
        return runtime_env
    container = current_container(runtime_env)
    existing = runtime_env.get("XDG_RUNTIME_DIR")
    if existing and is_host_backed(Path(existing), container):
        return runtime_env
    staging = homes.data / "launch-staging"
    try:
        staging.mkdir(parents=True, exist_ok=True)
        staging.chmod(0o700)
    except OSError as exc:
        raise PycharmRunError(f"Cannot prepare a host-backed staging directory: {exc}") from exc
    if not is_host_backed(staging, container):
        raise PycharmRunError(
            f"This launch runs inside a container against an external Docker daemon, but "
            f"{staging} is not backed by any mount of this container, so the daemon cannot "
            "read the launcher's transient files. Set XDG_RUNTIME_DIR to a mounted directory, "
            "or run the launch from the host."
        )
    runtime_env["XDG_RUNTIME_DIR"] = str(staging)
    return runtime_env


def translate_for_external_daemon(
    docker_args: list[str],
    env: Mapping[str, str],
) -> list[str]:
    """Rewrite bind sources when launching from inside a container.

    On the host this is a no-op. Inside a container whose Docker socket comes
    from an external daemon, the daemon resolves bind sources in the host
    filesystem, where this process's paths do not exist. Docker would create
    them as empty directories, so translate them or fail loudly.
    """

    if not requires_translation(env):
        return docker_args
    container = current_container(env)
    translated = translate_bind_sources(docker_args, container)
    print(
        "Launching from inside a container against an external Docker daemon; "
        "bind sources were translated to their host paths.",
        file=sys.stderr,
    )
    return translated


def build_run_config(options: PycharmRunOptions, env: Mapping[str, str]) -> PycharmRunConfig:
    host_environment = env
    if not options.inherit_legacy_configuration:
        env = {
            key: value for key, value in env.items()
            if not key.startswith(("PYCHARM_", "DOCKER4IDES_"))
            and key not in {"DEVCAPSULE_HOME_DIR", "IMAGE", "DOCKER_MODE", "DOCKER_IN_DOCKER",
                            "GITHUB_TOKEN_FILE", "GITHUB_TOKEN_ENV", "GITHUB_USER"}
        }
    from devcapsule.platforms import XdgHomes
    homes = XdgHomes.from_environment(env)
    base_data_dir = (homes.data / "pycharm-docker" if homes.chosen_by == "DEVCAPSULE_CONFIG_HOME"
                     else homes.data.parent / "pycharm-docker")
    profile = options.profile or env.get("DOCKER4IDES_PYCHARM_PROFILE", "")
    host_user = current_host_user()

    docker_mode = options.docker_mode.value if options.docker_mode is not None else initial_docker_mode(env)

    git_identity_from_host = env.get("PYCHARM_GIT_IDENTITY_FROM_HOST", "auto")
    if options.git_identity_from_host is not None:
        git_identity_from_host = options.git_identity_from_host
    git_identity_from_host = normalize_git_identity_mode(git_identity_from_host)

    ide_config_mode = resolve_ide_config_mode(options, env)

    ignore_config_lock = parse_bool_env(
        env.get("PYCHARM_IGNORE_CONFIG_LOCK", "0"),
        "PYCHARM_IGNORE_CONFIG_LOCK",
    )
    if options.ignore_config_lock:
        ignore_config_lock = True

    enable_sudo = (
        options.enable_sudo if options.enable_sudo is not None
        else parse_bool_env(env.get("PYCHARM_ENABLE_SUDO", "0"), "PYCHARM_ENABLE_SUDO")
    )

    ide_sudo_gid_text = options.ide_sudo_gid or env.get("PYCHARM_IDE_SUDO_GID", "44000")
    if not ide_sudo_gid_text.isdigit():
        raise PycharmRunError("PYCHARM_IDE_SUDO_GID must be a numeric group ID.")
    ide_sudo_gid = int(ide_sudo_gid_text)

    writable_root = options.writable_root
    if enable_sudo:
        writable_root = True

    if options.display_transport not in DISPLAY_TRANSPORTS:
        raise PycharmRunError(
            f"Unknown display transport {options.display_transport!r}; "
            f"choose one of: {', '.join(sorted(DISPLAY_TRANSPORTS))}."
        )
    if options.network_mode not in {"bridge", "host", "none"}:
        raise PycharmRunError("The Docker network mode must be bridge, host, or none.")
    if options.network_mode == "host" and not HostOs.current().host_network_reachable:
        # Docker Desktop's host network is its VM's: a listener on loopback
        # there is unreachable from the Mac (observed on 29.3.1), so the
        # desktop and console would never answer. Bridge is the narrower grant.
        print(HOST_NETWORK_UNAVAILABLE_ON_MACOS, file=sys.stderr)
        options = replace(options, network_mode="bridge")
    if options.use_image_process and options.runtime_plan is None:
        raise PycharmRunError("Using the image process requires an external runtime plan.")
    contained_display = options.display_transport == CONTAINED_DISPLAY_TRANSPORT
    if contained_display:
        if options.runtime_plan is None or not options.use_image_process:
            raise PycharmRunError("The contained display requires the image process and an external runtime plan.")
        if options.network_mode == "none":
            raise PycharmRunError(
                "The contained display cannot be reached under Docker network mode 'none': "
                "nothing can be published from it. Use bridge (or host) networking, or "
                "authorize 'host-x11' to run on the host X session instead."
            )
    elif not env.get("DISPLAY"):
        raise PycharmRunError("DISPLAY is not set; host X11 passthrough needs an active X session.")

    global_settings_default = base_data_dir / "state"

    try:
        runtime_plan = plan_shared_runtime(
            SharedRuntimeOptions(
                project=options.project,
                profile=profile or None,
                global_settings=options.global_settings or env.get("PYCHARM_GLOBAL_SETTINGS_DIR"),
                project_state=options.project_state or env.get("PYCHARM_PROJECT_STATE_DIR"),
                project_state_root=options.project_state_root or env.get("PYCHARM_PROJECT_STATE_ROOT") or None,
                project_mount=options.project_mount or env.get("PYCHARM_PROJECT_MOUNT"),
            ),
            env,
            explicit_profile_root_env_var="DOCKER4IDES_PYCHARM_PROFILE_ROOT",
            profile_dir_prefix="docker-pycharm-",
            default_global_settings=global_settings_default,
            default_project_state=lambda project_plan: base_data_dir / "project-state" / project_plan.project_id,
        )
    except (ProjectMountError, ValueError) as exc:
        raise PycharmRunError(str(exc)) from exc

    project = runtime_plan.project
    if options.launch_configuration is not None:
        snapshot = options.launch_configuration
        if (snapshot.document.get("launcher-root") != str(project)
                or snapshot.document.get("runtime-root") != runtime_plan.project_mount
                or not snapshot.directory.is_dir()):
            raise PycharmRunError("Launch configuration must describe this project's host and runtime paths and an existing configuration directory.")
    if not project.is_dir():
        raise PycharmRunError(f"Project directory does not exist: {project}")

    profile_root = runtime_plan.profile_root
    plugins_default = profile_root / "plugins" if profile_root else base_data_dir / "plugins"
    global_settings = runtime_plan.global_settings
    project_state = runtime_plan.project_state

    from devcapsule.platforms import XdgHomes
    homes = XdgHomes.from_environment(env)
    data_namespace = homes.data / "projects" / "by-path" / runtime_plan.project_id
    state_namespace = homes.state / "projects" / "by-path" / runtime_plan.project_id
    cache_namespace = homes.cache / "projects" / "by-path" / runtime_plan.project_id

    legacy_global_settings = (
        options.global_settings is not None
        or bool(env.get("PYCHARM_GLOBAL_SETTINGS_DIR"))
        or bool(profile)
    )
    persistent_home = resolve_existing_or_create(
        options.persistent_home
        or env.get("DEVCAPSULE_HOME_DIR")
        or (global_settings / "home" if legacy_global_settings else data_namespace / "home")
    )

    plan_driven_surface = bool(options.interactive_state_mounts)
    if plan_driven_surface and options.runtime_plan is None:
        raise PycharmRunError("Interactive state mounts require an external runtime plan.")

    ide_config: Path | None
    plugins: Path | None
    ide_system: Path | None
    ide_log: Path | None
    tool_cache: Path | None
    if plan_driven_surface:
        # The runtime plan's declared slots replace every named PyCharm
        # state location; nothing here may invent surface state paths.
        ide_config = plugins = ide_system = ide_log = tool_cache = None
    else:
        ide_config_arg = options.ide_config if options.ide_config is not None else env.get("PYCHARM_IDE_CONFIG_DIR", "")
        if ide_config_mode == "shared":
            ide_config = resolve_existing_or_create(
                global_settings / "config"
                if legacy_global_settings
                else data_namespace / "components" / "pycharm" / "config"
            )
        elif ide_config_mode == "project":
            ide_config = resolve_existing_or_create(project_state / "config")
        else:
            if not ide_config_arg:
                raise PycharmRunError(
                    "--ide-config or PYCHARM_IDE_CONFIG_DIR is required when PYCHARM_IDE_CONFIG_MODE=custom."
                )
            ide_config = resolve_existing_or_create(ide_config_arg)

        plugins = resolve_existing_or_create(
            options.plugins
            or env.get("PYCHARM_PLUGIN_DIR")
            or (plugins_default if options.profile else data_namespace / "components" / "pycharm" / "plugins")
        )

        legacy_project_state = options.project_state is not None or options.project_state_root is not None
        ide_system = resolve_existing_or_create(
            options.ide_system
            or (project_state / "system"
            if legacy_project_state
            else cache_namespace / "components" / "pycharm" / "system")
        )
        ide_log = resolve_existing_or_create(
            options.ide_log
            or (project_state / "log"
            if legacy_project_state
            else state_namespace / "components" / "pycharm" / "log")
        )
        tool_cache = resolve_existing_or_create(
            options.tool_cache
            or (project_state / "home" / ".cache"
            if legacy_project_state
            else cache_namespace / "components" / "pycharm" / "cache")
        )

        if not ignore_config_lock and ide_config_mode != "project" and (ide_config / ".lock").exists():
            raise PycharmRunError(config_lock_message(ide_config, project, project_state))

    # Inside a container the daemon's socket is wherever it was mounted, which
    # DOCKER_HOST already names. Preferring it over the host default keeps a
    # containerized launch working without the developer restating it.
    host_docker_socket = Path(
        options.host_docker_socket or env.get("HOST_DOCKER_SOCKET") or docker_socket(env)
    )
    host_docker_gid: int | None = None
    if docker_mode == "host":
        if not is_socket(host_docker_socket):
            raise PycharmRunError(
                f"Host Docker socket is not available: {host_docker_socket}\n"
                "Start Docker on the host, set HOST_DOCKER_SOCKET, or launch with --docker-in-docker / --no-docker."
            )
        host_docker_socket = host_docker_socket.resolve()
        # Where the host decides the socket's group inside containers (Docker
        # Desktop: root), the capsule user joins it; a capsule granted the
        # daemon already holds root on its virtual machine, so the group adds
        # no authority. Elsewhere the host socket file's group applies.
        socket_gid = HostOs.current().docker_socket_gid
        host_docker_gid = socket_gid if socket_gid is not None else host_docker_socket.stat().st_gid

    if enable_sudo:
        while ide_sudo_gid in {0, host_user.gid, host_docker_gid}:
            ide_sudo_gid += 1

    git_user_name = options.git_user_name or env.get("PYCHARM_GIT_USER_NAME", "")
    git_user_email = options.git_user_email or env.get("PYCHARM_GIT_USER_EMAIL", "")
    if git_identity_from_host in {"1", "auto"}:
        git_user_name, git_user_email = apply_host_git_identity(
            git_identity_from_host,
            git_user_name,
            git_user_email,
        )

    git_token_file = options.git_token_file or env.get("PYCHARM_GIT_TOKEN_FILE") or env.get("GITHUB_TOKEN_FILE")

    if options.runtime_plan is not None:
        if options.runtime_plan.project_path != runtime_plan.project_mount:
            raise PycharmRunError(
                "The external runtime plan project path does not match the Docker project mount."
            )
        if options.runtime_plan.home != "/home/devcapsule":
            raise PycharmRunError("The external runtime plan home must be /home/devcapsule.")

    runtime_slots = options.runtime_plan.slots_by_name() if options.runtime_plan is not None else {}
    ancillary_ids = {
        component.id for component in options.runtime_plan.ancillary_components
    } if options.runtime_plan is not None else set()
    interactive_ids = (
        {options.runtime_plan.component.id} if options.runtime_plan is not None else set()
    )
    additional_state_mounts = _validated_state_mounts(
        options.additional_state_mounts,
        allowed_ids=ancillary_ids,
        runtime_slots=runtime_slots,
        label="Additional",
        ownership="a declared ancillary component",
    )
    interactive_state_mounts = _validated_state_mounts(
        options.interactive_state_mounts,
        allowed_ids=interactive_ids,
        runtime_slots=runtime_slots,
        label="Interactive",
        ownership="the plan's interactive component",
    )
    host_browser_socket: Path | None = None
    configured_browser_socket = env.get(HOST_OPEN_SOCKET_ENV)
    if options.enable_host_browser and configured_browser_socket:
        candidate = Path(configured_browser_socket)
        if not candidate.is_absolute() or ".." in candidate.parts or not is_socket(candidate):
            raise PycharmRunError("The authorized host-browser socket is absent or unsafe.")
        host_browser_socket = candidate

    selected_runtime_plan = options.runtime_plan
    if host_browser_socket is not None and selected_runtime_plan is not None:
        selected_runtime_plan = selected_runtime_plan.with_host_integration(
            HOST_OPEN_INTEGRATION
        )
    display_host_port: int | None = None
    display_token = ""
    console_host_port: int | None = None
    console_token = ""
    if selected_runtime_plan is not None:
        if contained_display:
            display_host_port = allocate_loopback_port()
            display_token = new_run_token()
            # Under host networking the bridge is on the host's loopback
            # directly; otherwise it listens on the container's interfaces
            # and Docker publishes it to host loopback (T4 of the design note).
            listen_address = "127.0.0.1" if options.network_mode == "host" else "0.0.0.0"
            container_port = display_host_port if options.network_mode == "host" else CONTAINER_DISPLAY_PORT
            selected_runtime_plan = selected_runtime_plan.with_display(
                DisplayPlan.contained(listen_address, container_port, DISPLAY_TOKEN_DESTINATION)
            )
        else:
            selected_runtime_plan = selected_runtime_plan.with_display(DisplayPlan.host_x11())
        # The web console runs whenever the runtime runs on a base that has
        # one, with or without a display, reached like the display: one
        # loopback port, one token. On a base without it nothing is planned,
        # and the launch announces the absence once beside the links.
        # Allocation releases its socket. The OS can return the display's
        # port again before either listener starts.
        if options.web_console.available:
            for _ in range(10):
                console_host_port = allocate_loopback_port()
                if console_host_port != display_host_port:
                    break
            else:
                raise PycharmRunError("Could not allocate distinct display and web console ports; retry the launch.")
            console_token = new_run_token()
            console_listen = "127.0.0.1" if options.network_mode == "host" else "0.0.0.0"
            console_port = console_host_port if options.network_mode == "host" else CONTAINER_CONSOLE_PORT
            selected_runtime_plan = selected_runtime_plan.with_console(ConsolePlan(
                console_listen, console_port, CONSOLE_TOKEN_DESTINATION,
                source_path=console_development_source(project, runtime_plan.project_mount),
            ))
    session_id = logs.new_session_id()
    session_log_path = session_logs_root(project, env) / session_id
    session_log_directory: Path | None
    try:
        session_log_directory = resolve_existing_or_create(session_log_path)
        if requires_translation(env) and not is_host_backed(session_log_directory, current_container(env)):
            raise OSError("the session log directory is not backed by a mount visible to the external Docker daemon")
    except OSError as error:
        print(
            f"devcapsule launcher: cannot use session logs at {session_log_path} ({error}); logging to the console only",
            file=sys.stderr,
        )
        session_log_directory = None
    try:
        log_budget_bytes = logs.budget_from_environment(env)
    except logs.LogBudgetError as error:
        log_budget_bytes = logs.DEFAULT_BUDGET_BYTES
        print(
            f"devcapsule launcher: {error}; using the default log budget of {logs.format_size(log_budget_bytes)}",
            file=sys.stderr,
        )
    if selected_runtime_plan is not None and session_log_directory is not None:
        selected_runtime_plan = selected_runtime_plan.with_logs(LogsPlan(
            SESSION_LOG_DESTINATION, segment_bytes=logs.segment_bytes_for(log_budget_bytes), rotations=logs.ROTATIONS,
        ))
    fixed_environment = selected_runtime_plan.component_environment() if selected_runtime_plan else {}
    if host_browser_socket is not None and (
        "BROWSER" in fixed_environment or HOST_OPEN_SOCKET_ENV in fixed_environment
    ):
        raise PycharmRunError(
            "Component runtime metadata conflicts with the host-browser integration."
        )
    additional_environment: list[tuple[str, str]] = []
    for name, value in sorted(options.additional_environment.items()):
        if not name.isascii() or not name.isidentifier() or name.upper() != name:
            raise PycharmRunError(
                f"Additional environment name {name!r} must be an uppercase identifier."
            )
        if not value or "\x00" in value:
            raise PycharmRunError(
                f"Additional environment variable {name!r} must have a non-empty value."
            )
        if name in fixed_environment:
            raise PycharmRunError(
                f"Additional environment variable {name!r} conflicts with component runtime metadata."
            )
        if name in options.secret_environment:
            raise PycharmRunError(
                f"Additional environment variable {name!r} conflicts with a secret binding."
            )
        additional_environment.append((name, value))
    for name in options.secret_environment:
        if name in fixed_environment:
            raise PycharmRunError(
                f"Secret environment variable {name!r} conflicts with component runtime metadata."
            )
        if name not in host_environment:
            raise PycharmRunError(
                f"Bound secret environment variable {name!r} is not set on the host."
            )

    return PycharmRunConfig(
        image=options.image or env.get("IMAGE", "pycharm-isolated:latest"),
        name=options.name or f"pycharm-isolated-{host_user.name}-{int(time.time())}",
        project=project,
        global_settings=global_settings,
        persistent_home=persistent_home,
        project_state=project_state,
        ide_system=ide_system,
        ide_log=ide_log,
        tool_cache=tool_cache,
        ide_config=ide_config,
        ide_config_mode=ide_config_mode,
        plugins=plugins,
        project_mount=runtime_plan.project_mount,
        docker_mode=docker_mode,
        host_docker_socket=host_docker_socket,
        host_docker_gid=host_docker_gid,
        use_ssh_agent=options.use_ssh_agent,
        git_user_name=git_user_name,
        git_user_email=git_user_email,
        git_token_file=Path(git_token_file).expanduser().resolve() if git_token_file else None,
        git_token_env=options.git_token_env or env.get("PYCHARM_GIT_TOKEN_ENV") or env.get("GITHUB_TOKEN_ENV", ""),
        git_token_username=options.git_token_username
        or env.get("PYCHARM_GIT_TOKEN_USERNAME")
        or env.get("GITHUB_USER", "x-access-token"),
        git_token_hosts=options.git_token_hosts or env.get("PYCHARM_GIT_TOKEN_HOSTS", "github.com"),
        debug_native=options.debug_native,
        writable_root=writable_root,
        enable_sudo=enable_sudo,
        ide_sudo_gid=ide_sudo_gid,
        ignore_config_lock=ignore_config_lock,
        network_mode=options.network_mode,
        memory_limit_bytes=options.memory_limit_bytes,
        cpus=options.cpus,
        runtime_plan=selected_runtime_plan,
        launch_configuration=options.launch_configuration,
        use_image_process=options.use_image_process,
        host_browser_socket=host_browser_socket,
        display_transport=options.display_transport,
        display_host_port=display_host_port,
        display_token=display_token,
        open_display_url=options.open_display_url,
        console_host_port=console_host_port,
        session_id=session_id,
        session_log_directory=session_log_directory,
        log_budget_bytes=log_budget_bytes,
        console_token=console_token,
        open_console_url=options.open_console_url,
        web_console=options.web_console,
        capsule_platform=options.capsule_platform,
        daemon_architecture=daemon_architecture(),
        interactive_state_mounts=tuple(interactive_state_mounts),
        additional_state_mounts=tuple(additional_state_mounts),
        additional_environment=tuple(additional_environment),
        secret_environment=tuple(sorted(set(options.secret_environment))),
        extra_docker_args=list(options.extra_docker_args),
        libgl_always_software=env.get("PYCHARM_LIBGL_ALWAYS_SOFTWARE", env.get("LIBGL_ALWAYS_SOFTWARE", "1")),
        mesa_loader_driver_override=env.get(
            "PYCHARM_MESA_LOADER_DRIVER_OVERRIDE",
            env.get("MESA_LOADER_DRIVER_OVERRIDE", "llvmpipe"),
        ),
        libgl_dri3_disable=env.get("PYCHARM_LIBGL_DRI3_DISABLE", env.get("LIBGL_DRI3_DISABLE", "1")),
    )


def prepare_home_mount_points(config: PycharmRunConfig) -> None:
    """Pre-create home-overlay mount points inside the persistent home source.

    The container runtime creates a missing bind-mount target as root, and a
    root-owned directory in the developer's home source outlives the mount —
    violating the ownership invariant the owner ruled on 2026-09-02:
    everything under $HOME belongs to the user, whatever mechanism created
    it. Creating the mount points here, as the invoking user, keeps the
    daemon out of that business. An entry some earlier launch already left
    behind with foreign ownership cannot be repaired without host privilege,
    so it is reported instead of silently mounted over.
    """

    home = Path("/home/devcapsule")
    destinations = [
        destination
        for _name, _source, destination in (
            *config.interactive_state_mounts,
            *config.additional_state_mounts,
        )
    ]
    if not config.interactive_state_mounts and config.tool_cache is not None:
        # The legacy named-field surface path mounts the tool cache at a
        # fixed home-overlay destination (_surface_state_mount_args).
        destinations.append("/home/devcapsule/.cache")
    for destination in destinations:
        path = Path(destination)
        if home not in path.parents:
            continue
        # The runtime-plan contract holds overlay slots to direct children
        # of home, so the parent here is the home source itself.
        mount_point = config.persistent_home / path.relative_to(home)
        try:
            mount_point.mkdir(mode=0o700, exist_ok=True)
            owner = mount_point.stat().st_uid
        except OSError as exc:
            raise PycharmRunError(
                f"Cannot prepare home mount point {mount_point}: {exc}"
            ) from exc
        if owner != os.getuid():
            print(
                f"WARNING: {mount_point} is owned by uid {owner}, not you; an "
                "earlier launch let the container runtime create it. The mount "
                "will cover it, but restoring the home invariant needs it "
                "removed with host privilege.",
                file=sys.stderr,
            )


def _surface_state_mount_args(config: PycharmRunConfig) -> list[str]:
    """Mount the interactive surface's state: plan-declared slots, or the
    named PyCharm locations when no plan-driven mounts were provided."""

    if config.interactive_state_mounts:
        args: list[str] = []
        for _logical_name, source, destination in config.interactive_state_mounts:
            args.extend(["--mount", f"type=bind,src={source},dst={destination}"])
        return args
    return [
        "--mount",
        f"type=bind,src={config.ide_config},dst=/ide-config",
        "--mount",
        f"type=bind,src={config.ide_system},dst=/ide-project-state/system",
        "--mount",
        f"type=bind,src={config.ide_log},dst=/ide-project-state/log",
        "--mount",
        f"type=bind,src={config.tool_cache},dst=/home/devcapsule/.cache",
        "--mount",
        f"type=bind,src={config.plugins},dst=/ide-plugins",
    ]


def _validated_state_mounts(
    mounts: Mapping[str, tuple[Path, str]],
    *,
    allowed_ids: set[str],
    runtime_slots: Mapping[str, str],
    label: str,
    ownership: str,
) -> list[tuple[str, str, str]]:
    validated: list[tuple[str, str, str]] = []
    for logical_name, (source, destination) in sorted(mounts.items()):
        namespace, separator, _local_name = logical_name.partition("/")
        planned_destination = runtime_slots.get(logical_name)
        if not separator or namespace not in allowed_ids:
            raise PycharmRunError(
                f"{label} state mount {logical_name!r} is not owned by {ownership}."
            )
        if planned_destination is not None and planned_destination != destination:
            raise PycharmRunError(
                f"{label} state mount {logical_name!r} conflicts with the external runtime plan."
            )
        destination_path = Path(destination)
        if not destination_path.is_absolute() or ".." in destination_path.parts:
            raise PycharmRunError(
                f"{label} state mount {logical_name!r} must use an absolute container destination."
            )
        resolved_source = resolve_existing_or_create(source)
        validated.append((logical_name, str(resolved_source), destination))
    return validated


def build_docker_args(
    config: PycharmRunConfig,
    files: TempRuntimeFiles,
    env: Mapping[str, str],
) -> list[str]:
    # One lifecycle for every launch: the launcher stays attached and Docker
    # removes the container when it exits. A launch that must outlive its
    # launcher is not a case this product has; the recursive dogfood holds
    # its successor's launcher open exactly as a developer holds `project run`.
    host_user = current_host_user()
    args = [
        "--rm",
        "-i",
        *config.capsule_platform.docker_platform_args(config.daemon_architecture),
        "--name",
        config.name,
        "--workdir",
        config.project_mount,
        *_display_environment_args(config),
        "--env",
        f"PROJECT_PATH={config.project_mount}",
        "--env",
        f"DEVCAPSULE_CONTAINER_NAME={config.name}",
        # The console's host-side origin, so an agent inside can hand the human
        # a link; the token stays in its file and in the browser's cookie.
        *_console_environment_args(config),
        *_session_log_environment_args(config, env),
        "--env",
        "HOME=/home/devcapsule",
        "--env",
        "XDG_CONFIG_HOME=/home/devcapsule/.config",
        "--env",
        "XDG_CACHE_HOME=/home/devcapsule/.cache",
        "--env",
        "XDG_DATA_HOME=/home/devcapsule/.local/share",
        "--env",
        "IDE_GLOBAL_SETTINGS_PATH=/home/devcapsule",
        "--env",
        "IDE_CONFIG_PATH=/ide-config",
        "--env",
        "IDE_PROJECT_STATE_PATH=/ide-project-state",
        "--env",
        f"IDE_UID={host_user.uid}",
        "--env",
        f"IDE_GID={host_user.gid}",
        "--env",
        f"IDE_USER={host_user.name}",
        "--env",
        f"LIBGL_ALWAYS_SOFTWARE={config.libgl_always_software}",
        "--env",
        f"MESA_LOADER_DRIVER_OVERRIDE={config.mesa_loader_driver_override}",
        "--env",
        f"LIBGL_DRI3_DISABLE={config.libgl_dri3_disable}",
        "--mount",
        f"type=bind,src={config.project},dst={config.project_mount}",
        "--mount",
        f"type=bind,src={config.persistent_home},dst=/home/devcapsule",
        *_surface_state_mount_args(config),
        *_display_mount_args(config, files),
        *_console_mount_args(config, files),
        *_session_log_mount_args(config),
        "--mount",
        f"type=bind,src={files.passwd_file},dst=/etc/passwd,ro",
        "--mount",
        f"type=bind,src={files.group_file},dst=/etc/group,ro",
        "--tmpfs",
        "/tmp:rw,exec,nosuid,nodev,size=2g",
        "--tmpfs",
        "/run:rw,nosuid,nodev,size=128m",
        "--tmpfs",
        "/var/tmp:rw,exec,nosuid,nodev,size=1g",
        *(
            ["--shm-size", shared_memory]
            if (shared_memory := declared_shared_memory_size(config)) is not None
            else []
        ),
        "--ipc",
        "private",
        "--network",
        config.network_mode,
        "--pids-limit",
        "4096",
    ]

    if config.runtime_plan is not None:
        for name, value in sorted(config.runtime_plan.component_environment().items()):
            args.extend(["--env", f"{name}={value}"])
    if config.host_browser_socket is not None:
        args.extend(
            [
                "--env",
                f"BROWSER={HOST_OPEN_BROWSER}",
                "--env",
                f"{HOST_OPEN_SOCKET_ENV}={HOST_OPEN_SOCKET_DESTINATION}",
                "--mount",
                (
                    f"type=bind,src={config.host_browser_socket},"
                    f"dst={HOST_OPEN_SOCKET_DESTINATION},ro"
                ),
            ]
        )
    for name, value in config.additional_environment:
        args.extend(["--env", f"{name}={value}"])
    for name in config.secret_environment:
        args.extend(["--env", name])

    for _logical_name, source, destination in config.additional_state_mounts:
        args.extend(["--mount", f"type=bind,src={source},dst={destination}"])

    if config.enable_sudo:
        if files.shadow_file is None or files.sudoers_file is None:
            raise PycharmRunError(
                "Development sudo requires generated shadow and sudoers files."
            )
        args.extend(["--mount", f"type=bind,src={files.shadow_file},dst=/etc/shadow,ro"])
        policy_source = (
            f"type=volume,src={files.sudoers_volume},volume-subpath={SUDOERS_VOLUME_FILE}"
            if files.sudoers_volume
            else f"type=bind,src={files.sudoers_file}"
        )
        args.extend(["--mount", f"{policy_source},dst={SUDOERS_POLICY_PATH},ro"])
    if files.runtime_plan_file is not None:
        args.extend(
            [
                "--mount",
                f"type=bind,src={files.runtime_plan_file},dst={RUNTIME_PLAN_PATH},ro",
            ]
        )
    if config.launch_configuration is not None:
        if files.launch_context_file is None:
            raise PycharmRunError("Project launch requires its captured configuration context.")
        args.extend([
            "--mount", f"type=bind,src={config.launch_configuration.directory},dst={CONFIGURATION_PATH},ro",
            "--mount", f"type=bind,src={files.launch_context_file},dst={CONTEXT_PATH},ro",
        ])
        home = config.launch_configuration.document.get("configuration-home")
        if home:
            from devcapsule.runtime_configuration import HOME_PATH
            settings = Path(str(home)) / "settings.toml"
            if settings.is_file():
                args.extend(["--mount", f"type=bind,src={settings},dst={HOME_PATH}/settings.toml,ro"])
        if files.configuration_directory is not None:
            args.extend(["--mount", f"type=bind,src={files.configuration_directory},dst={CHANNEL_PATH}"])
    if config.git_user_name:
        args.extend(["--env", f"GIT_USER_NAME={config.git_user_name}"])
    if config.git_user_email:
        args.extend(["--env", f"GIT_USER_EMAIL={config.git_user_email}"])

    append_docker_mode_args(args, config, host_user)

    if not config.writable_root and config.docker_mode != "dind":
        args.append("--read-only")
    if config.debug_native and config.docker_mode != "dind":
        args.extend(["--cap-add", "SYS_PTRACE", "--security-opt", "seccomp=unconfined"])

    if config.use_ssh_agent:
        ssh_auth_sock = env.get("SSH_AUTH_SOCK", "")
        if not ssh_auth_sock or not is_socket(Path(ssh_auth_sock)):
            raise PycharmRunError("--ssh-agent was requested, but SSH_AUTH_SOCK is not a socket.")
        args.extend(
            [
                "--mount",
                f"type=bind,src={ssh_auth_sock},dst=/run/host-ssh-agent.sock",
                "--env",
                "SSH_AUTH_SOCK=/run/host-ssh-agent.sock",
            ]
        )

    git_token_file = resolve_git_token_file(config, files, env)
    if git_token_file:
        args.extend(
            [
                "--mount",
                f"type=bind,src={git_token_file},dst=/run/secrets/git-token,ro",
                "--env",
                "GIT_TOKEN_FILE=/run/secrets/git-token",
                "--env",
                f"GIT_TOKEN_USERNAME={config.git_token_username}",
                "--env",
                f"GIT_TOKEN_HOSTS={config.git_token_hosts}",
            ]
        )

    if config.memory_limit_bytes is not None:
        if config.memory_limit_bytes <= 0:
            raise PycharmRunError("The container memory limit must be positive.")
        args.extend(["--memory", str(config.memory_limit_bytes)])
    if config.cpus is not None:
        if config.cpus <= 0:
            raise PycharmRunError("The container CPU count must be positive.")
        args.extend(["--cpus", str(config.cpus)])
    args.extend(config.extra_docker_args)
    return args


def _session_log_environment_args(config: PycharmRunConfig, env: Mapping[str, str]) -> list[str]:
    args = []
    if config.session_log_directory is not None:
        args.extend(["--env", f"{logs.DIRECTORY_ENV}={SESSION_LOG_DESTINATION}"])
    try:
        level = logs.level_from_environment(env)
    except logs.LogLevelError:
        level = logs.DEFAULT_LEVEL  # begin_session_logs reports the bad value once
    args.extend(["--env", f"{logs.LEVEL_ENV}={logging.getLevelName(level)}"])
    return args


def _session_log_mount_args(config: PycharmRunConfig) -> list[str]:
    """The session's host-backed log directory, writable, so the logs outlive the container."""
    if config.session_log_directory is None:
        return []
    return ["--mount", f"type=bind,src={config.session_log_directory},dst={SESSION_LOG_DESTINATION}"]


def _console_environment_args(config: PycharmRunConfig) -> list[str]:
    if config.console_host_port is None:
        return []
    return ["--env", f"{CONSOLE_URL_ENV}={console_origin(config.console_host_port)}"]


def _display_environment_args(config: PycharmRunConfig) -> list[str]:
    if config.display_transport == CONTAINED_DISPLAY_TRANSPORT:
        # The entrypoint sets DISPLAY and XAUTHORITY to the capsule's own
        # X server; nothing about the host session crosses the boundary.
        return []
    return [
        "--env",
        "DISPLAY",
        "--env",
        "XAUTHORITY=/tmp/.docker.xauth",
        # Both are host-X-socket workarounds: MIT-SHM cannot cross the
        # container boundary, and the host's window manager may not reparent.
        "--env",
        "QT_X11_NO_MITSHM=1",
        "--env",
        "_JAVA_AWT_WM_NONREPARENTING=1",
    ]


def _console_mount_args(config: PycharmRunConfig, files: TempRuntimeFiles) -> list[str]:
    """The console's token mount and, off host networking, its published port."""
    if config.console_host_port is None:
        return []
    if files.console_token_file is None:
        raise PycharmRunError("The web console requires a generated token file.")
    args = ["--mount", f"type=bind,src={files.console_token_file},dst={CONSOLE_TOKEN_DESTINATION},ro"]
    if config.network_mode != "host":
        args.extend(["--publish", f"127.0.0.1:{config.console_host_port}:{CONTAINER_CONSOLE_PORT}"])
    return args


def _display_mount_args(config: PycharmRunConfig, files: TempRuntimeFiles) -> list[str]:
    if config.display_transport == CONTAINED_DISPLAY_TRANSPORT:
        if files.display_token_file is None or config.display_host_port is None:
            raise PycharmRunError("The contained display requires a generated token file and a host port.")
        args = [
            "--mount",
            f"type=bind,src={files.display_token_file},dst={DISPLAY_TOKEN_DESTINATION},ro",
        ]
        if config.network_mode != "host":
            args.extend(
                ["--publish", f"127.0.0.1:{config.display_host_port}:{CONTAINER_DISPLAY_PORT}"]
            )
        return args
    return [
        "--mount",
        "type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix,ro",
        "--mount",
        f"type=bind,src={files.xauth_file},dst=/tmp/.docker.xauth,ro",
    ]


def append_docker_mode_args(args: list[str], config: PycharmRunConfig, host_user: HostUser) -> None:
    if config.docker_mode == "host":
        print_host_docker_warning(config)
        args.extend(
            [
                "--user",
                f"{host_user.uid}:{host_user.gid}",
                "--group-add",
                str(config.host_docker_gid),
                "--env",
                "ENABLE_DIND=0",
                "--env",
                f"ENABLE_SUDO={int(config.enable_sudo)}",
                "--env",
                f"IDE_SUDO_GID={config.ide_sudo_gid}",
                "--env",
                "DOCKER_HOST=unix:///run/host-docker.sock",
                "--mount",
                f"type=bind,src={config.host_docker_socket},dst=/run/host-docker.sock",
            ]
        )
        append_sudo_or_restrictions(args, config)
    elif config.docker_mode == "dind":
        print_dind_warning(config)
        args.extend(
            [
                "--privileged",
                "--env",
                "ENABLE_DIND=1",
                "--env",
                f"ENABLE_SUDO={int(config.enable_sudo)}",
                "--env",
                f"IDE_SUDO_GID={config.ide_sudo_gid}",
                "--mount",
                "type=volume,dst=/var/lib/docker",
            ]
        )
        if config.enable_sudo:
            args.extend(["--group-add", str(config.ide_sudo_gid)])
    else:
        args.extend(
            [
                "--user",
                f"{host_user.uid}:{host_user.gid}",
                "--env",
                "ENABLE_DIND=0",
                "--env",
                f"ENABLE_SUDO={int(config.enable_sudo)}",
                "--env",
                f"IDE_SUDO_GID={config.ide_sudo_gid}",
            ]
        )
        append_sudo_or_restrictions(args, config)


def launches_unsandboxed_renderers(config: PycharmRunConfig) -> bool:
    """True when the plan's surface launches Chromium renderers unsandboxed.

    Renderer sandboxing is retired (product-owner ruling 2026-09-02; see
    engineering-docs/design-notes/devcapsule/renderer-sandboxing.md); the
    surface carries --no-sandbox as template data and the launch disclosure
    keys on it.
    """

    if config.runtime_plan is None:
        return False
    additional = config.runtime_plan.component.configuration.get("additional_arguments")
    return isinstance(additional, list) and "--no-sandbox" in additional


# Docker options the launcher composes exactly once per launch, with the
# sanctioned lever (if any) a developer should use instead. Docker keeps the
# last occurrence of a single-instance option, so a raw passthrough
# repetition would silently override the resolved plan rather than error;
# these are refused at the door instead. Repeatable options (--mount, --env,
# --volume, --cap-add, ...) pass through untouched. The scan matches option
# tokens only; a *value* that happens to spell one of these names is
# conservatively refused too, which is acceptable for a deliberate escape
# hatch.
LAUNCHER_OWNED_DOCKER_OPTIONS: dict[str, str] = {
    "--rm": "the launcher owns the container lifecycle",
    "--detach": "the launcher owns the container lifecycle",
    "-d": "the launcher owns the container lifecycle",
    "--interactive": "the launcher owns the container lifecycle",
    "-i": "the launcher owns the container lifecycle",
    "--name": "use 'devcapsule project run --name NAME'",
    "--user": "the launcher derives the container identity from the host user",
    "-u": "the launcher derives the container identity from the host user",
    "--network": "authorize it: '--authorize network host' or the config family",
    "--net": "authorize it: '--authorize network host' or the config family",
    "--memory": "set it: 'devcapsule project config set memory SIZE'",
    "-m": "set it: 'devcapsule project config set memory SIZE'",
    "--cpus": "set it: 'devcapsule project config set cpus N'",
    "-c": "set the CPU count instead: 'devcapsule project config set cpus N'",
    "--cpu-shares": "set the CPU count instead: 'devcapsule project config set cpus N'",
    "--cpuset-cpus": "set the CPU count instead: 'devcapsule project config set cpus N'",
    "--shm-size": "the surface declares shared-memory-size in its runtime template",
    "--ipc": "the launcher owns IPC isolation",
    "--pids-limit": "the launcher owns the PID budget",
    "--privileged": "privilege comes from the docker-daemon and development-sudo authorizations",
    "--pull": "the launcher pins '--pull=never' to the materialized image",
}


CLUSTERED_SHORT_DOCKER_FLAGS = frozenset("ditP")
"""docker run's boolean short flags, which may share one token: -d, -i, -t, -P."""


def reject_launcher_owned_docker_options(options: Sequence[str]) -> None:
    """Refuse raw docker options the launcher already composes exactly once."""

    for option in options:
        name = option.split("=", 1)[0]
        remedy = LAUNCHER_OWNED_DOCKER_OPTIONS.get(name)
        if remedy is None and option.startswith("-") and not option.startswith("--") and len(option) > 2:
            # Attached short spellings: -m2g, -u1000, -dit, -ti. Docker lets
            # boolean short flags cluster, so walk past the known ones; the
            # first other letter owns the rest of the token as its value
            # (-eNAME=value, -vSRC:DST) and is never inspected further.
            for letter in option[1:]:
                name = f"-{letter}"
                remedy = LAUNCHER_OWNED_DOCKER_OPTIONS.get(name)
                if remedy is not None or letter not in CLUSTERED_SHORT_DOCKER_FLAGS:
                    break
        if remedy is not None:
            raise PycharmRunError(
                f"Raw docker option {name!r} is composed by the launcher and cannot "
                f"pass through; {remedy}."
            )


def declared_shared_memory_size(config: PycharmRunConfig) -> str | None:
    """The surface's declared /dev/shm size, validated, or None.

    Chromium-family surfaces outgrow Docker's 64MB default (renderers
    SIGTRAP intermittently under software rendering — owner-confirmed
    2026-09-02); the component declares what it needs and the launcher
    passes it through as --shm-size.
    """

    if config.runtime_plan is None:
        return None
    value = config.runtime_plan.component.configuration.get("shared-memory-size")
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*[mg]", value):
        raise PycharmRunError(
            "The surface's shared-memory-size must be a size like '512m' or '1g'; "
            f"found {value!r}."
        )
    return value


def append_sudo_or_restrictions(args: list[str], config: PycharmRunConfig) -> None:
    # Hardening is uniform across surfaces: renderer sandboxing is retired
    # (product-owner ruling 2026-09-02), so no surface narrows the capsule's
    # posture; see
    # engineering-docs/design-notes/devcapsule/renderer-sandboxing.md.
    if config.enable_sudo:
        args.extend(["--group-add", str(config.ide_sudo_gid)])
    else:
        args.extend(["--cap-drop", "ALL", "--security-opt", "no-new-privileges"])


def prepare_temp_runtime_files(config: PycharmRunConfig, env: Mapping[str, str]) -> TempRuntimeFiles:
    runtime_parent = Path(env.get("XDG_RUNTIME_DIR", "/tmp"))
    runtime_parent.mkdir(parents=True, exist_ok=True)
    files = TempRuntimeFiles(
        xauth_file=make_temp(runtime_parent, "pycharm-docker-xauth."),
        passwd_file=make_temp(runtime_parent, "pycharm-docker-passwd."),
        group_file=make_temp(runtime_parent, "pycharm-docker-group."),
    )
    try:
        if config.display_transport == CONTAINED_DISPLAY_TRANSPORT:
            files.display_token_file = make_temp(runtime_parent, "devcapsule-display-token.")
            files.display_token_file.write_text(config.display_token + "\n", encoding="utf-8")
            files.display_token_file.chmod(0o600)
        else:
            write_xauthority(files.xauth_file, env)
        if config.console_host_port is not None:
            files.console_token_file = make_temp(runtime_parent, "devcapsule-console-token.")
            files.console_token_file.write_text(config.console_token + "\n", encoding="utf-8")
            files.console_token_file.chmod(0o600)
        write_user_files(config, files)
        if config.enable_sudo:
            files.sudoers_directory = Path(
                tempfile.mkdtemp(prefix="devcapsule-sudoers.", dir=runtime_parent)
            )
            files.sudoers_directory.chmod(0o700)
            files.sudoers_file = files.sudoers_directory / "policy"
            files.sudoers_file.write_text(SUDOERS_POLICY, encoding="utf-8")
            files.sudoers_file.chmod(0o440)
        if config.runtime_plan is not None:
            files.runtime_plan_file = make_temp(runtime_parent, "devcapsule-runtime-plan.")
            files.runtime_plan_file.write_text(config.runtime_plan.to_json() + "\n", encoding="utf-8")
            files.runtime_plan_file.chmod(0o644)
        if config.launch_configuration is not None:
            files.launch_context_file = make_temp(runtime_parent, "devcapsule-launch-context.")
            files.launch_context_file.write_text(json.dumps(config.launch_configuration.document) + "\n", encoding="utf-8")
            files.launch_context_file.chmod(0o600)
            files.configuration_directory = Path(tempfile.mkdtemp(prefix="devcapsule-configuration.", dir=runtime_parent))
            files.configuration_directory.chmod(0o700)
            if config.launch_configuration.listing is not None:
                write_complete(files.configuration_directory / LISTING_FILE,
                               listing_document(config.launch_configuration.listing))
        return files
    except BaseException:
        cleanup_temp_runtime_files(files)
        raise


def make_temp(parent: Path, prefix: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=prefix, dir=parent)
    os.close(fd)
    return Path(name)


def write_xauthority(xauth_file: Path, env: Mapping[str, str]) -> None:
    if shutil.which("xauth"):
        nlist = subprocess.run(
            ["xauth", "nlist", env.get("DISPLAY", "")],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if nlist.stdout:
            family_wild = "".join(f"ffff{line[4:]}" for line in nlist.stdout.splitlines(keepends=True))
            subprocess.run(
                ["xauth", "-f", str(xauth_file), "nmerge", "-"],
                input=family_wild,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
    xauth_file.chmod(0o600)
    if xauth_file.stat().st_size == 0:
        # Deliberately no `xhost +SI:localuser:...` advice here: that command
        # widens host X access control, and this launcher must not teach users
        # to weaken the very boundary the product exists to keep.
        print(
            "Warning: no Xauthority cookie was copied, so PyCharm may be unable to open a window. "
            "Note that host X11 passthrough already hands the capsule your X session credential "
            "(keystroke capture, window capture, input injection, clipboard); a contained display "
            "that closes this exposure is in development.",
            file=sys.stderr,
        )


def write_user_files(config: PycharmRunConfig, files: TempRuntimeFiles) -> None:
    host_user = current_host_user()
    files.passwd_file.write_text(
        "\n".join(
            [
                "root:x:0:0:root:/root:/bin/bash",
                f"{host_user.name}:x:{host_user.uid}:{host_user.gid}:PyCharm Docker User:/home/devcapsule:/bin/bash",
                "",
            ]
        )
    )
    group_lines = [
        "root:x:0:",
        f"{host_user.group_name}:x:{host_user.gid}:",
    ]
    if config.host_docker_gid not in (None, 0, host_user.gid):
        group_lines.append(f"host-docker:x:{config.host_docker_gid}:")
    if config.enable_sudo:
        group_lines.append(f"ide-sudo:x:{config.ide_sudo_gid}:{host_user.name}")
        files.shadow_file = make_temp(files.group_file.parent, "pycharm-docker-shadow.")
        shadow_last_change = int(time.time()) // 86400
        files.shadow_file.write_text(
            "\n".join(
                [
                    f"root:*:{shadow_last_change}:0:99999:7:::",
                    f"{host_user.name}:*:{shadow_last_change}:0:99999:7:::",
                    "",
                ]
            )
        )
        files.shadow_file.chmod(0o600)
    files.group_file.write_text("\n".join([*group_lines, ""]))
    files.passwd_file.chmod(0o644)
    files.group_file.chmod(0o644)


def ensure_sudoers_policy_ownership(
    config: PycharmRunConfig,
    files: TempRuntimeFiles,
    env: Mapping[str, str],
) -> None:
    policy = files.sudoers_file
    if not config.enable_sudo or policy is None:
        raise PycharmRunError("Development sudo requires a generated sudoers policy.")
    if not HostOs.current().chown_reaches_bind_mounts:
        files.sudoers_volume = prepare_sudoers_policy_volume(config, policy, env)
        return
    try:
        os.chown(policy, 0, 0)
    except PermissionError:
        destination = "/run/devcapsule-sudoers-policy"
        command = [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            *config.capsule_platform.docker_platform_args(config.daemon_architecture),
            "--network",
            "none",
            "--read-only",
            "--pids-limit",
            "64",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "CHOWN",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "0:0",
            "--mount",
            f"type=bind,src={policy},dst={destination}",
            "--entrypoint",
            "/bin/chown",
            config.image,
            "0:0",
            destination,
        ]
        completed = subprocess.run(
            command,
            check=False,
            env=dict(env),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip()
            suffix = f": {detail}" if detail else "."
            raise PycharmRunError(
                "Could not prepare the root-owned development-sudo policy" + suffix
            )
    if file_owner_uid(policy) != 0:
        raise PycharmRunError(
            "Development-sudo policy ownership is not root after preparation."
        )


def prepare_sudoers_policy_volume(config: PycharmRunConfig, policy: Path, env: Mapping[str, str]) -> str:
    """Write the sudo policy into a Docker volume as root; return the volume's name.

    sudo ignores a policy root does not own. Docker Desktop shares Mac files
    with its virtual machine as the Mac user: a bind-mounted file is owned by
    that user inside every container, and not even root there can chown it.
    A volume lives on the virtual machine's own disk, where root's ownership
    holds. The session removes it at its end; the next launch removes one a
    killed launch left behind (``remove_abandoned_sudoers_volumes``).
    """

    volume = f"{config.name}-sudoers"
    remove_abandoned_sudoers_volumes(env)
    created = subprocess.run(
        ["docker", "volume", "create", "--label", SUDOERS_VOLUME_LABEL, volume],
        check=False, env=dict(env), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    if created.returncode != 0:
        detail = created.stderr.strip()
        raise PycharmRunError(
            "Could not create the volume for the development-sudo policy" + (f": {detail}" if detail else ".")
        )
    staged = f"/policy/{SUDOERS_VOLUME_FILE}.new"
    command = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--pull=never",
        *config.capsule_platform.docker_platform_args(config.daemon_architecture),
        "--network",
        "none",
        "--read-only",
        "--pids-limit",
        "64",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "0:0",
        "--mount",
        f"type=volume,src={volume},dst=/policy",
        "--entrypoint",
        "/bin/sh",
        config.image,
        "-ec",
        # 0440 root:root, as sudo requires. A policy left by an earlier
        # launch is read-only even to root without capabilities: replace it.
        f"umask 0337; rm -f {staged}; cat > {staged}; mv -f {staged} /policy/{SUDOERS_VOLUME_FILE}",
    ]
    completed = subprocess.run(
        command,
        check=False,
        env=dict(env),
        input=policy.read_text(encoding="utf-8"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        remove_sudoers_policy_volume(volume, env)
        detail = completed.stderr.strip()
        raise PycharmRunError(
            "Could not prepare the root-owned development-sudo policy" + (f": {detail}" if detail else ".")
        )
    return volume


def remove_abandoned_sudoers_volumes(env: Mapping[str, str]) -> None:
    """Remove the policy volumes of launches that ended without removing their own.

    A concurrent launch's volume is in no container's use between its
    creation and its capsule's start, so only a volume older than
    ``ABANDONED_SUDOERS_VOLUME_AGE`` is taken for abandoned; Docker refuses
    to remove one a container still uses.
    """

    listed = subprocess.run(
        ["docker", "volume", "ls", "--quiet", "--filter", f"label={SUDOERS_VOLUME_LABEL}"],
        check=False, env=dict(env), capture_output=True, text=True,
    )
    volumes = listed.stdout.split() if listed.returncode == 0 else []
    if not volumes:
        return
    inspected = subprocess.run(
        ["docker", "volume", "inspect", "--format", "{{.Name}} {{.CreatedAt}}", *volumes],
        check=False, env=dict(env), capture_output=True, text=True,
    )
    cutoff = datetime.now(timezone.utc) - ABANDONED_SUDOERS_VOLUME_AGE
    abandoned = []
    for line in inspected.stdout.splitlines():
        volume, _, created = line.partition(" ")
        try:
            if datetime.fromisoformat(created) < cutoff:
                abandoned.append(volume)
        except ValueError:
            continue  # A creation time Docker did not report is no evidence of age.
    if abandoned:
        subprocess.run(
            ["docker", "volume", "rm", *abandoned],
            check=False, env=dict(env), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def remove_sudoers_policy_volume(volume: str | None, env: Mapping[str, str]) -> None:
    """Remove the policy volume; one a capsule still uses is left for a later launch to find abandoned."""

    if volume:
        subprocess.run(
            ["docker", "volume", "rm", "--force", volume],
            check=False, env=dict(env), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def file_owner_uid(path: Path) -> int:
    return path.stat().st_uid


def resolve_git_token_file(
    config: PycharmRunConfig,
    files: TempRuntimeFiles,
    env: Mapping[str, str],
) -> Path | None:
    git_token_file = config.git_token_file
    if config.git_token_env:
        token = env.get(config.git_token_env, "")
        if not token:
            raise PycharmRunError(
                f"--git-token-env {config.git_token_env} was requested, but that variable is empty or unset."
            )
        token_file = make_temp(Path(env.get("XDG_RUNTIME_DIR", "/tmp")), "pycharm-docker-git-token.")
        token_file.write_text(token)
        token_file.chmod(0o600)
        files.token_file = token_file
        git_token_file = token_file

    if git_token_file:
        git_token_file = git_token_file.expanduser().resolve()
        if not os.access(git_token_file, os.R_OK):
            raise PycharmRunError(f"Git token file is not readable: {git_token_file}")
    return git_token_file


def channel_watcher(config: PycharmRunConfig, files: TempRuntimeFiles) -> ChannelWatcher | None:
    """The watcher answering the console's requests for this run, or ``None`` for a launch without the channel."""
    if files.configuration_directory is None or config.launch_configuration is None:
        return None
    record = config.launch_configuration.directory / str(config.launch_configuration.document["checkout-file"])
    return ChannelWatcher(files.configuration_directory, config.project, record)


def cleanup_temp_runtime_files(files: TempRuntimeFiles) -> None:
    if files.configuration_directory is not None:
        shutil.rmtree(files.configuration_directory, ignore_errors=True)
    for path in [
        files.xauth_file,
        files.passwd_file,
        files.group_file,
        files.shadow_file,
        files.sudoers_file,
        files.token_file,
        files.runtime_plan_file,
        files.display_token_file,
        files.console_token_file,
        files.launch_context_file,
    ]:
        if path:
            path.unlink(missing_ok=True)
    if files.sudoers_directory:
        try:
            files.sudoers_directory.rmdir()
        except FileNotFoundError:
            pass


def initial_docker_mode(env: Mapping[str, str]) -> str:
    if env.get("DOCKER_MODE"):
        return normalize_docker_mode(env["DOCKER_MODE"])
    if env.get("DOCKER_IN_DOCKER"):
        dind = env["DOCKER_IN_DOCKER"]
        if dind in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}:
            return "dind"
        if dind in {"0", "false", "FALSE", "no", "NO", "off", "OFF"}:
            return "none"
        raise PycharmRunError("DOCKER_IN_DOCKER must be 1/0, true/false, yes/no, or on/off.")
    return "host"


def resolve_ide_config_mode(options: PycharmRunOptions, env: Mapping[str, str]) -> str:
    if options.config_mode is not None:
        return options.config_mode.value
    if options.ide_config is not None:
        return "custom"
    if env.get("PYCHARM_IDE_CONFIG_MODE"):
        return normalize_ide_config_mode(env["PYCHARM_IDE_CONFIG_MODE"])
    if env.get("PYCHARM_IDE_CONFIG_DIR"):
        return "custom"
    return "shared"


def normalize_docker_mode(value: str) -> str:
    if value in {"host", "HOST", "docker", "DOCKER", "socket", "SOCKET"}:
        return "host"
    if value in {"dind", "DIND", "docker-in-docker", "DOCKER-IN-DOCKER"}:
        return "dind"
    if value in {"none", "NONE", "off", "OFF", "no", "NO", "false", "FALSE", "0"}:
        return "none"
    raise PycharmRunError("DOCKER_MODE must be host, dind, or none.")


def normalize_git_identity_mode(value: str) -> str:
    if value in {"auto", "AUTO", "default", "DEFAULT"}:
        return "auto"
    if value in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}:
        return "1"
    if value in {"0", "false", "FALSE", "no", "NO", "off", "OFF", ""}:
        return "0"
    raise PycharmRunError("PYCHARM_GIT_IDENTITY_FROM_HOST must be auto, 1/0, true/false, yes/no, or on/off.")


def normalize_ide_config_mode(value: str) -> str:
    if value in {"shared", "SHARED"}:
        return "shared"
    if value in {"project", "PROJECT", "per-project", "PER-PROJECT"}:
        return "project"
    if value in {"custom", "CUSTOM", "explicit", "EXPLICIT"}:
        return "custom"
    raise PycharmRunError("PYCHARM_IDE_CONFIG_MODE must be shared, project, or custom.")


def parse_bool_env(value: str, name: str) -> bool:
    if value in {"1", "true", "TRUE", "yes", "YES", "on", "ON"}:
        return True
    if value in {"0", "false", "FALSE", "no", "NO", "off", "OFF", ""}:
        return False
    raise PycharmRunError(f"{name} must be 1/0, true/false, yes/no, or on/off.")


def apply_host_git_identity(mode: str, name: str, email: str) -> tuple[str, str]:
    if shutil.which("git") is None:
        if mode == "1":
            raise PycharmRunError("--git-identity-from-host was requested, but git is not installed on the host.")
    else:
        if not name:
            name = git_config_value("user.name")
        if not email:
            email = git_config_value("user.email")
    if not name or not email:
        if mode == "1":
            print("Warning: --git-identity-from-host did not find both host user.name and user.email.", file=sys.stderr)
        else:
            print("Warning: no complete Git author identity was provided or found in host global Git config.", file=sys.stderr)
        print(
            "Pass --git-user-name and --git-user-email, or launch with --no-git-identity-from-host to suppress host identity lookup.",
            file=sys.stderr,
        )
    return name, email


def git_config_value(key: str) -> str:
    completed = subprocess.run(
        ["git", "config", "--global", "--get", key],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return completed.stdout.strip()


def is_socket(path: Path) -> bool:
    try:
        mode = path.stat().st_mode
    except FileNotFoundError:
        return False
    return stat.S_ISSOCK(mode)


def current_host_user() -> HostUser:
    uid = os.getuid()
    gid = os.getgid()
    return HostUser(
        uid=uid,
        gid=gid,
        name=pwd.getpwuid(uid).pw_name,
        group_name=grp.getgrgid(gid).gr_name,
    )


def config_lock_message(ide_config: Path, project: Path, project_state: Path) -> str:
    inspect = shlex.join(["devcapsule", "project", "--path", str(project), "config", "show"])
    return f"""PyCharm config directory appears to be locked:
  {ide_config / ".lock"}
Project state:
  {project_state}

One IDE configuration directory can only be used by one live PyCharm process
at a time. Inspect this checkout's 'pycharm/config' binding with:
  {inspect}

For concurrent sessions, bind 'pycharm/config' to a separate directory with
'project config bind', then run 'project run' before launching.
If the lock is stale, confirm no IDE is using that directory before removing
its .lock file and retrying 'devcapsule project run'."""


def print_storage_summary(config: PycharmRunConfig) -> None:
    browser_disclosure = ""
    if config.runtime_plan is not None:
        properties = config.runtime_plan.component.configuration.get("additional_properties", {})
        if isinstance(properties, dict) and properties.get("ide.browser.jcef.sandbox.enable") == "false":
            browser_disclosure = """

Embedded browser security:
  JCEF's inner Chromium sandbox is disabled for V1 container compatibility.
  Embedded content inherits the IDE user's project, state, network, and any
  separately authorized Docker access. Docker's outer isolation is unchanged."""
    host_browser_disclosure = ""
    if config.host_browser_socket is not None:
        host_browser_disclosure = """

Host browser integration:
  Enabled through a URL-only HTTP(S) broker. Any process running as the
  capsule user can ask the physical host to navigate its default browser."""
    host_browser_disclosure += display_disclosure(config) + console_disclosure(config)
    if config.interactive_state_mounts:
        component_id = (
            config.runtime_plan.component.id if config.runtime_plan is not None else "surface"
        )
        sandbox_disclosure = ""
        if launches_unsandboxed_renderers(config):
            sandbox_disclosure = """

Renderer security:
  Chromium renderers run unsandboxed (--no-sandbox) and inherit the capsule
  user's project, state, network, and any separately authorized Docker
  access. Docker's outer isolation is unchanged."""
        slot_lines = "\n".join(
            f"  {logical_name}: {source}"
            for logical_name, source, _destination in config.interactive_state_mounts
        )
        print(
            f"""{component_id} storage:
  Persistent home:       {config.persistent_home}
{slot_lines}
  Session logs:           {config.session_log_directory} (budget {logs.format_size(config.log_budget_bytes)})
  Container project path: {config.project_mount}{browser_disclosure}{sandbox_disclosure}{host_browser_disclosure}""",
            file=sys.stderr,
        )
        return
    print(
        f"""PyCharm storage:
  Persistent home:       {config.persistent_home}
  PyCharm config:         {config.ide_config} ({config.ide_config_mode})
  Shared plugins:         {config.plugins}
  PyCharm system:         {config.ide_system}
  PyCharm logs:           {config.ide_log}
  Tool cache:             {config.tool_cache}
  Session logs:           {config.session_log_directory} (budget {logs.format_size(config.log_budget_bytes)})
  Container project path: {config.project_mount}{browser_disclosure}{host_browser_disclosure}""",
        file=sys.stderr,
    )


def console_disclosure(config: PycharmRunConfig) -> str:
    """The run's web console, stated the way the run manifest records it."""

    if config.console_host_port is None:
        return ""
    where = (
        f"host loopback port {config.console_host_port} (host networking)"
        if config.network_mode == "host"
        else f"container port {CONTAINER_CONSOLE_PORT}, published to host loopback port {config.console_host_port}"
    )
    return f"""

Web console:
  The capsule serves its configuration, versions and project information as
  pages on {where}, behind this run's token. It is read-only."""


def console_development_source(project: Path, project_mount: str) -> str:
    """The mounted path of the checkout's own console source, or empty.

    The self-hosting exception: a DevCapsule checkout that carries the console
    subproject runs that source instead of the base's installed copy, so an
    edit shows on the next run without a base release. Any other project
    returns empty and the base's console runs.
    """

    if (project / "devcapsule-webconsole" / "devcapsule_webconsole" / "__init__.py").is_file():
        return f"{project_mount}/devcapsule-webconsole"
    return ""


def display_disclosure(config: PycharmRunConfig) -> str:
    """The run's display transport, stated the way the run manifest records it."""

    if config.display_transport == CONTAINED_DISPLAY_TRANSPORT:
        where = (
            f"host loopback port {config.display_host_port} (host networking)"
            if config.network_mode == "host"
            else f"container port {CONTAINER_DISPLAY_PORT}, published to host loopback port {config.display_host_port}"
        )
        return f"""

Display:
  Contained desktop: the capsule runs its own X server and serves it to a
  browser through a token-authorized noVNC bridge on {where}.
  No host X socket, credential, or DISPLAY is shared with the capsule."""
    return """

Display:
  Host X11 passthrough: the capsule holds your full X session credential
  (keystroke capture across the session, window capture, input injection,
  clipboard). The session-credential boundary test is waived for this run."""


def print_host_docker_warning(config: PycharmRunConfig) -> None:
    no_docker = shlex.join([
        "devcapsule", "project", "--path", str(config.project), "run",
        "--authorize", "docker-daemon", "none",
    ])
    print(
        f"""========================================================================
HOST DOCKER DAEMON IS CONNECTED TO THIS CAPSULE.

The launcher is mounting the host Docker socket:
  {config.host_docker_socket}

Docker commands inside the capsule operate on the host daemon, giving tools
broad control over host Docker images, containers, networks, and bind mounts.

For a project session with no Docker access, run:
  {no_docker}
========================================================================""",
        file=sys.stderr,
    )


def print_dind_warning(config: PycharmRunConfig) -> None:
    project_run = ["devcapsule", "project", "--path", str(config.project), "run"]
    host_docker = shlex.join([*project_run, "--authorize", "docker-daemon", "host-socket"])
    no_docker = shlex.join([*project_run, "--authorize", "docker-daemon", "none"])
    print(
        f"""========================================================================
DOCKER-IN-DOCKER IS ENABLED FOR THIS CAPSULE.

This launch uses --privileged, a writable root filesystem, and an inner Docker
daemon with separate Docker images, containers, and volumes. The inner daemon
does not manage bridge/iptables networking; inner builds needing network access
must explicitly select host networking.

Ordinary project launch supports host-daemon access or no Docker access:
  {host_docker}
  {no_docker}
========================================================================""",
        file=sys.stderr,
    )


def print_sudo_warning() -> None:
    print(
        """========================================================================
DEVELOPMENT SUDO IS ENABLED FOR THIS PYCHARM CONTAINER.

The mapped IDE user can run passwordless sudo inside the container. The
launcher is also using a writable root filesystem and preserving the default
Docker container capabilities so package installs and similar development
commands can work.

This is a development convenience profile. Use the default launcher profile
when you do not need sudo.
========================================================================""",
        file=sys.stderr,
    )
