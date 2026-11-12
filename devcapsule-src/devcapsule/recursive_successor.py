"""Detached successor launch and inspection for the recursive dogfood milestone."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable, Mapping, Sequence

from devcapsule.build_info import current_build_info
from devcapsule.launch.pycharm import DockerMode, PycharmRunOptions
from devcapsule.launch.pycharm._launcher import (
    PycharmRunError,
    build_docker_args,
    build_run_config,
    cleanup_temp_runtime_files,
    prepare_temp_runtime_files,
)
from devcapsule.container_runtime.contract import CONTAINED_DISPLAY_TRANSPORT, RuntimePlan, RuntimePlanError
from devcapsule.display_client import display_url, select_display_transport
from devcapsule.environment_realization import realize_environment
from devcapsule.materialization import RUNTIME_PLAN_PATH as SUCCESSOR_RUNTIME_PLAN_PATH
from devcapsule.configuration.capability_selection import lock_platform
from devcapsule.configuration.storage import (
    atomic_write,
)
from devcapsule.configuration.bindings import (
    configuration_binding_declarations,
    managed_binding_path,
)
from devcapsule.configuration.execution import (
    fresh_resolved_project,
)
from devcapsule.project_runtime_plan import project_runtime_plan
from devcapsule.recursive_dogfood import (
    RUNTIME_PLAN_PATH,
    PreflightReport,
    docker_socket_path,
    run_recursive_preflight,
)
from devcapsule.recursive_host import (
    HostContextError,
    HostDaemonLaunchContext,
    MountRequirement,
    PathAccess,
    PathKind,
)
from devcapsule.recursive_successor_plan import (
    ExpectedSuccessorPlan,
    SuccessorPlanError,
    compare_inspection,
)


WORKSPACE_ROOT = Path("/home/devcapsule/.local/share/devcapsule/e2e-workspaces")
OWNER_MARKER = ".devcapsule-e2e-owner.json"
MILESTONE_MANIFEST = "milestone-manifest.json"
EXPECTED_PLAN = "expected-plan.json"
SUCCESSOR_ROLE = "successor"
# Files an attached launch leaves in the run directory beside the manifest.
CONTAINER_ID_FILE = "container.id"
SUCCESSOR_LOG = "successor.log"
RUN_ID_ENV = "DEVCAPSULE_RUN_ID"
RUN_ID_PATTERN = re.compile(r"[0-9a-f]{16,64}")


class RecursiveSuccessorError(Exception):
    """A retained recursive successor could not be launched or inspected safely."""


@dataclass(frozen=True)
class SuccessorResult:
    run_id: str
    container_id: str
    container_name: str
    image_id: str
    state: str
    checks: Mapping[str, str]
    # The contained display's per-run URL, or None under host X11 passthrough.
    # The launcher's own terminal shows the successor's log, not a desktop, so
    # the URL is reported here for the operator to open.
    display_url: str | None = None
    # The container's exit status once the attached launch has ended; None
    # while it runs.
    exit_code: int | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "container_id": self.container_id,
            "container_name": self.container_name,
            "image_id": self.image_id,
            "display_url": self.display_url,
            "state": self.state,
            "exit_code": self.exit_code,
            "checks": dict(self.checks),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def launch_successor(
    checkout: Path,
    run_id: str,
    *,
    runtime_plan_path: Path = RUNTIME_PLAN_PATH,
    environ: Mapping[str, str] | None = None,
    workspace_root: Path = WORKSPACE_ROOT,
    on_running: Callable[[SuccessorResult], None] | None = None,
    container_id_timeout: float = 120.0,
) -> SuccessorResult:
    """Launch one retained successor using the normal resolved-project Docker planner.

    The launch is the ordinary attached one: this call returns only when the
    successor container has exited, exactly as ``project run`` returns when
    a developer's capsule ends. Once the container runs and its inspection
    passes, ``on_running`` receives the running report (the command prints
    it), the run manifest records ``stage-6-running``, and the call blocks.
    On exit the manifest records ``stage-6-exited`` with the exit code,
    Docker has already removed the container (``--rm``), and the successor's
    own output is retained in ``successor.log`` under the run directory.
    """

    env = dict(os.environ if environ is None else environ)
    run_root, manifest = _load_owned_run(workspace_root, run_id)
    try:
        current_runtime_plan = RuntimePlan.from_file(runtime_plan_path)
    except RuntimePlanError as exc:
        raise RecursiveSuccessorError("current capsule runtime plan is malformed") from exc
    preflight_env = dict(env)
    # Stage 5 deliberately isolates HOME for checkout-local configuration. The
    # preflight still has to validate the actual home declared by the current
    # capsule's external runtime contract.
    preflight_env["HOME"] = current_runtime_plan.home
    report = run_recursive_preflight(
        checkout,
        runtime_plan_path=runtime_plan_path,
        environ=preflight_env,
    )
    if not report.ready or report.container is None:
        raise RecursiveSuccessorError("recursive preflight is not ready for successor launch")

    selected = fresh_resolved_project(checkout)
    realized = realize_environment(selected)
    runtime_plan = project_runtime_plan(selected, realized.locked)
    source_revision = current_build_info().source_revision
    name = successor_container_name(run_id)
    options = _resolved_run_options(
        selected,
        realized.image.reference,
        runtime_plan,
        name=name,
        run_id=run_id,
        source_revision=source_revision,
        image_labels=realized.image.labels,
    )
    config = build_run_config(options, env)
    successor_display_url: str | None = None
    if config.display_transport == CONTAINED_DISPLAY_TRANSPORT and config.display_host_port is not None:
        successor_display_url = display_url(config.display_host_port, config.display_token)

    staging = run_root / "staging"
    try:
        staging.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RecursiveSuccessorError(
            "successor staging already exists; inspect or clean up the retained run first"
        ) from exc
    staging.chmod(0o700)
    launch_env = dict(env)
    launch_env["XDG_RUNTIME_DIR"] = str(staging)
    files = prepare_temp_runtime_files(config, launch_env)
    launched = False
    container_id: str | None = None
    process: subprocess.Popen[bytes] | None = None
    try:
        args = build_docker_args(config, files, launch_env)
        context = _launch_context(report, config.persistent_home, args)
        host_args = _translate_bind_sources(args, context)
        if files.sudoers_file is not None:
            _make_root_owned(files.sudoers_file, launch_env)
        plan = _expected_plan(host_args, files, realized)
        _write_expected_plan(run_root, plan)
        _write_manifest(
            run_root,
            {
                **manifest,
                "state": "stage-6-launching",
                "launch": {
                    "source_revision": source_revision,
                    "container_name": name,
                    "expected_image_id": realized.image.identity,
                    "expected_plan_digest": plan.digest(),
                    "role": SUCCESSOR_ROLE,
                },
            },
        )
        # Docker writes the container ID to the cidfile as soon as the container
        # is created, which is how an attached launch learns the identity it
        # must inspect while it runs.
        cidfile = run_root / CONTAINER_ID_FILE
        cidfile.unlink(missing_ok=True)
        successor_log = run_root / SUCCESSOR_LOG
        with successor_log.open("ab") as log:
            process = subprocess.Popen(
                ["docker", "run", "--cidfile", str(cidfile), *host_args, config.image],
                env=launch_env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        container_id = _wait_for_container_id(
            process, cidfile, successor_log, timeout=container_id_timeout
        )
        inspection = _inspect_container(container_id, launch_env)
        checks = _validate_inspection(
            inspection,
            plan,
            run_id=run_id,
            source_revision=source_revision,
        )
        launched = True
        launch_record = {
            "source_revision": source_revision,
            "container_id": container_id,
            "container_name": name,
            "image_id": realized.image.identity,
            "formation_identity": realized.image.labels.get(
                "devcapsule.materialization.identity", ""
            ),
            "expected_plan_digest": plan.digest(),
            "role": SUCCESSOR_ROLE,
            "lifecycle": "attached",
            "successor_log": SUCCESSOR_LOG,
            "staging_retained": True,
        }
        _write_manifest(run_root, {**manifest, "state": "stage-6-running", "launch": launch_record})
        running = SuccessorResult(
            run_id,
            container_id,
            name,
            realized.image.identity,
            "running",
            checks,
            successor_display_url,
        )
        if on_running is not None:
            on_running(running)
        exit_code = process.wait()
        _write_manifest(
            run_root,
            {
                **manifest,
                "state": "stage-6-exited",
                "launch": {**launch_record, "exit_code": exit_code, "container_removed": True},
            },
        )
        return SuccessorResult(
            run_id,
            container_id,
            name,
            realized.image.identity,
            "exited",
            checks,
            successor_display_url,
            exit_code,
        )
    except (HostContextError, OSError, PycharmRunError) as exc:
        raise RecursiveSuccessorError(str(exc)) from exc
    finally:
        if launched:
            # The container has exited, or is being stopped by the same signal
            # that interrupted the wait; the bind-mounted identity files are
            # no longer needed. The staging directory, manifest and log stay
            # as the run's evidence.
            cleanup_temp_runtime_files(files)
        else:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30.0)
                except subprocess.TimeoutExpired:
                    process.kill()
            if container_id is not None and re.fullmatch(r"[0-9a-f]{64}", container_id):
                remove_successor_container(run_id, environ=launch_env)
            cleanup_temp_runtime_files(files)
            try:
                staging.rmdir()
            except OSError:
                pass


def _wait_for_container_id(
    process: "subprocess.Popen[bytes]",
    cidfile: Path,
    successor_log: Path,
    *,
    timeout: float,
    poll_interval: float = 0.2,
) -> str:
    """The successor's container ID, read from Docker's cidfile once it exists.

    Fails if the attached ``docker run`` exits first, quoting the end of the
    successor log, or if the ID does not appear within ``timeout`` seconds.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            candidate = cidfile.read_text(encoding="utf-8").strip()
        except OSError:
            candidate = ""
        if re.fullmatch(r"[0-9a-f]{64}", candidate):
            return candidate
        if process.poll() is not None:
            raise RecursiveSuccessorError(
                f"successor exited with status {process.returncode} before reporting its container ID"
                + _log_tail(successor_log)
            )
        if time.monotonic() >= deadline:
            raise RecursiveSuccessorError(
                f"successor did not report its container ID within {timeout:g} seconds"
                + _log_tail(successor_log)
            )
        time.sleep(poll_interval)


def _log_tail(path: Path, lines: int = 20) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    kept = text.splitlines()[-lines:]
    return (":\n" + "\n".join(kept)) if kept else ""


def successor_container_name(run_id: str) -> str:
    """Derive the only Docker container name owned by one random E2E run key."""

    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise RecursiveSuccessorError("run ID must contain 16 to 64 lowercase hex digits")
    return f"devcapsule-e2e-{run_id}-successor"


def successor_runtime_environment(run_id: str) -> dict[str, str]:
    """Expose a run's identity to software running inside its successor."""

    successor_container_name(run_id)
    return {"DEVCAPSULE_RECURSIVE_E2E": "1", RUN_ID_ENV: run_id}


def remove_successor_container(
    run_id: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Remove only the successor name derived from the caller-held run key."""

    name = successor_container_name(run_id)
    env = dict(os.environ if environ is None else environ)
    return subprocess.run(
        ["docker", "rm", "--force", name],
        check=False,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def inspect_successor(
    run_id: str,
    *,
    environ: Mapping[str, str] | None = None,
    workspace_root: Path = WORKSPACE_ROOT,
    readiness_timeout: float = 45.0,
) -> SuccessorResult:
    """Inspect exact retained successor identity and probe its selected toolchain."""

    env = dict(os.environ if environ is None else environ)
    run_root, manifest = _load_owned_run(workspace_root, run_id)
    launch = manifest.get("launch")
    if not isinstance(launch, dict):
        raise RecursiveSuccessorError("run manifest has no successor launch evidence")
    if manifest.get("state") == "stage-6-exited":
        raise RecursiveSuccessorError(
            f"successor has exited with status {launch.get('exit_code')} and Docker removed it; "
            "launch it again to inspect it"
        )
    required = (
        "container_id",
        "container_name",
        "image_id",
        "source_revision",
        "expected_plan_digest",
    )
    if not all(isinstance(launch.get(key), str) and launch[key] for key in required):
        raise RecursiveSuccessorError("run manifest has incomplete successor launch evidence")
    container_id = str(launch["container_id"])
    plan = _load_expected_plan(run_root, str(launch["expected_plan_digest"]))
    if str(launch["container_name"]) != plan.name or str(launch["image_id"]) != plan.image_identity:
        raise RecursiveSuccessorError("run manifest and retained successor plan disagree on identity")
    inspection = _inspect_container(container_id, env)
    checks = _validate_inspection(
        inspection,
        plan,
        run_id=run_id,
        source_revision=str(launch["source_revision"]),
    )
    deadline = time.monotonic() + readiness_timeout
    while True:
        probe = _probe_successor(container_id, plan, env)
        if probe.returncode == 0:
            break
        if time.monotonic() >= deadline:
            detail = probe.stderr.strip()
            raise RecursiveSuccessorError(
                "successor readiness probe failed" + (f": {detail}" if detail else "")
            )
        time.sleep(1.0)
    try:
        versions = json.loads(probe.stdout)
    except json.JSONDecodeError as exc:
        raise RecursiveSuccessorError("successor readiness probe returned malformed evidence") from exc
    if not isinstance(versions, dict) or not all(
        isinstance(value, str) and value for value in versions.values()
    ):
        raise RecursiveSuccessorError("successor readiness probe returned incomplete evidence")
    if versions.pop("runtime_plan_sha256", None) != plan.runtime_plan_digest:
        raise RecursiveSuccessorError(
            "successor runtime plan does not match the digest recorded at launch"
        )
    if versions.pop("runtime_plan_writable", None) != "no":
        raise RecursiveSuccessorError("successor runtime plan is not mounted read-only")
    if versions.pop("run_id", None) != run_id:
        raise RecursiveSuccessorError("successor does not expose its exact run ID")
    checks = {**checks, "runtime_plan": "pass", "run_identity": "pass", **versions}
    _write_manifest(
        run_root,
        {
            **manifest,
            "state": "stage-6-inspection-passed",
            "inspection": {"checks": checks},
        },
    )
    return SuccessorResult(
        run_id,
        container_id,
        str(launch["container_name"]),
        str(launch["image_id"]),
        "inspection-passed",
        checks,
    )


def _resolved_run_options(
    selected: Any,
    image: str,
    runtime_plan: Any,
    *,
    name: str,
    run_id: str,
    source_revision: str,
    image_labels: Mapping[str, str] | None = None,
) -> PycharmRunOptions:
    runtime = selected.resolution.get("runtime", {})
    state_root = selected.resolution.get("state", {})
    state = dict(state_root.get("adopted", {}))
    state.update(state_root.get("bindings", {}))
    authorization = selected.resolution.get("authorization", {})
    memory_limit = runtime.get("memory-limit-bytes")
    if memory_limit is not None and (
        not isinstance(memory_limit, int) or isinstance(memory_limit, bool) or memory_limit <= 0
    ):
        raise RecursiveSuccessorError("resolved runtime memory limit is invalid")
    if authorization.get("docker-daemon") != "host-socket":
        raise RecursiveSuccessorError("successor checkout has not authorized the host Docker socket")
    if authorization.get("network") != "host":
        raise RecursiveSuccessorError("successor checkout has not authorized host networking")
    if authorization.get("development-sudo") is not True:
        raise RecursiveSuccessorError("successor checkout has not authorized development sudo")
    secret_root = selected.resolution.get("secret", {})
    secret_bindings = secret_root.get("bindings", {}) if isinstance(secret_root, dict) else {}
    secret_environment = (
        secret_bindings.get("host-environment", {})
        if isinstance(secret_bindings, dict)
        else {}
    )
    if not isinstance(secret_environment, dict):
        raise RecursiveSuccessorError("resolved secret environment bindings are invalid")
    # The successor chooses its display the way `project run` does: from the
    # image's display stack and the checkout's recorded host-x11 answer.
    display_transport, _reason = select_display_transport(
        image_labels or {}, host_x11_answer=authorization.get("host-x11")
    )
    return PycharmRunOptions(
        project=selected.root,
        capsule_platform=lock_platform(selected.lock),
        project_mount=str(runtime["project-mount"]),
        image=image,
        name=name,
        persistent_home=Path(state["home"]) if "home" in state else None,
        ide_config=Path(state["pycharm/config"]) if "pycharm/config" in state else None,
        plugins=Path(state["pycharm/plugins"]) if "pycharm/plugins" in state else None,
        ide_system=Path(state["pycharm/system"]) if "pycharm/system" in state else None,
        ide_log=Path(state["pycharm/log"]) if "pycharm/log" in state else None,
        tool_cache=Path(state["pycharm/cache"]) if "pycharm/cache" in state else None,
        docker_mode=DockerMode.host,
        host_docker_socket=docker_socket_path(os.environ.get("DOCKER_HOST")),
        enable_sudo=True,
        network_mode="host",
        memory_limit_bytes=memory_limit,
        runtime_plan=runtime_plan,
        use_image_process=True,
        additional_state_mounts=_additional_component_state_mounts(
            selected.root,
            selected.lock,
            state,
            runtime_plan,
        ),
        additional_environment=successor_runtime_environment(run_id),
        enable_host_browser=True,
        display_transport=display_transport,
        secret_environment=tuple(sorted(str(value) for value in secret_environment.values())),
        extra_docker_args=[
            "--pull=never",
            "--label",
            "devcapsule.e2e.managed=true",
            "--label",
            f"devcapsule.e2e.run-id={run_id}",
            "--label",
            f"devcapsule.e2e.source-revision={source_revision}",
            "--label",
            f"devcapsule.e2e.role={SUCCESSOR_ROLE}",
        ],
    )


def _additional_component_state_mounts(
    root: Path,
    lock: Mapping[str, Any],
    configured_state: Mapping[str, Any],
    runtime_plan: Any,
) -> dict[str, tuple[Path, str]]:
    declarations = configuration_binding_declarations(lock)
    ancillary_ids = {component.id for component in runtime_plan.ancillary_components}
    mounts: dict[str, tuple[Path, str]] = {}
    for name, declaration in declarations.items():
        if declaration.component_id not in ancillary_ids:
            continue
        configured = configured_state.get(name)
        source = (
            Path(str(configured)).expanduser().resolve()
            if configured is not None
            else _managed_binding_path(root, declaration)
        )
        source.mkdir(parents=True, exist_ok=True, mode=0o700)
        if configured is None:
            source.chmod(0o700)
        mounts[name] = (source, declaration.container_path)
    return mounts


def _managed_binding_path(root: Path, declaration: Any) -> Path:
    return managed_binding_path(root, declaration)


def _launch_context(
    report: PreflightReport,
    persistent_home: Path,
    docker_args: Sequence[str],
) -> HostDaemonLaunchContext:
    if report.container is None:
        raise RecursiveSuccessorError("preflight has no current-container identity")
    requirements = []
    for index, (source, read_only) in enumerate(_bind_sources(docker_args)):
        kind = _path_kind(source)
        requirements.append(
            MountRequirement(
                f"successor-bind-{index}",
                source,
                PathAccess.read if read_only else PathAccess.write,
                kind,
            )
        )
    return HostDaemonLaunchContext.from_requirements(
        report.container,
        persistent_home=persistent_home,
        requirements=requirements,
    )


def _bind_sources(docker_args: Sequence[str]) -> list[tuple[Path, bool]]:
    sources: list[tuple[Path, bool]] = []
    for index, value in enumerate(docker_args[:-1]):
        if value != "--mount":
            continue
        fields = docker_args[index + 1].split(",")
        if "type=bind" not in fields:
            continue
        source_values = [field.removeprefix("src=") for field in fields if field.startswith("src=")]
        if len(source_values) != 1:
            raise RecursiveSuccessorError("planned bind mount has no unique source")
        sources.append((Path(source_values[0]), "ro" in fields))
    return sources


def _translate_bind_sources(
    docker_args: Sequence[str],
    context: HostDaemonLaunchContext,
) -> list[str]:
    translated = list(docker_args)
    for index, value in enumerate(translated[:-1]):
        if value != "--mount":
            continue
        fields = translated[index + 1].split(",")
        if "type=bind" not in fields:
            continue
        source_indexes = [position for position, field in enumerate(fields) if field.startswith("src=")]
        if len(source_indexes) != 1:
            raise RecursiveSuccessorError("planned bind mount has no unique source")
        position = source_indexes[0]
        source = Path(fields[position].removeprefix("src="))
        result = context.translate(
            source,
            access=PathAccess.read if "ro" in fields else PathAccess.write,
            kind=_path_kind(source),
        )
        fields[position] = f"src={result.host_path}"
        translated[index + 1] = ",".join(fields)
    return translated


def _path_kind(path: Path) -> PathKind:
    if path.is_socket():
        return PathKind.socket
    if path.is_dir():
        return PathKind.directory
    if path.is_file():
        return PathKind.file
    raise RecursiveSuccessorError("planned bind source is missing or unsupported")


def _make_root_owned(path: Path, env: Mapping[str, str]) -> None:
    completed = subprocess.run(
        ["sudo", "-n", "chown", "0:0", str(path)],
        check=False,
        env=dict(env),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0 or path.stat().st_uid != 0:
        raise RecursiveSuccessorError("could not prepare the root-owned sudo policy")


def _inspect_container(container_id: str, env: Mapping[str, str]) -> Mapping[str, Any]:
    completed = subprocess.run(
        ["docker", "inspect", container_id],
        check=False,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RecursiveSuccessorError("cannot inspect the exact successor container")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RecursiveSuccessorError("Docker returned malformed successor inspection") from exc
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise RecursiveSuccessorError("Docker returned ambiguous successor inspection")
    return value[0]


def _expected_plan(
    host_args: Sequence[str],
    files: Any,
    realized: Any,
) -> ExpectedSuccessorPlan:
    if files.runtime_plan_file is None:
        raise RecursiveSuccessorError("successor launch plan carries no checkout runtime plan")
    try:
        digest = hashlib.sha256(Path(files.runtime_plan_file).read_bytes()).hexdigest()
    except OSError as exc:
        raise RecursiveSuccessorError("cannot digest the staged successor runtime plan") from exc
    try:
        return ExpectedSuccessorPlan.from_docker_args(
            host_args,
            image_reference=realized.image.reference,
            image_identity=realized.image.identity,
            image_labels=realized.image.labels,
            runtime_plan_destination=SUCCESSOR_RUNTIME_PLAN_PATH,
            runtime_plan_digest=digest,
        )
    except SuccessorPlanError as exc:
        raise RecursiveSuccessorError(str(exc)) from exc


def _write_expected_plan(run_root: Path, plan: ExpectedSuccessorPlan) -> None:
    """Retain the exact translated plan; only this owner-private copy holds host sources."""

    atomic_write(
        run_root / EXPECTED_PLAN,
        plan.to_json(show_host_paths=True) + "\n",
        mode=0o600,
    )


def _load_expected_plan(run_root: Path, expected_digest: str) -> ExpectedSuccessorPlan:
    try:
        plan = ExpectedSuccessorPlan.from_mapping(_load_json(run_root / EXPECTED_PLAN))
    except SuccessorPlanError as exc:
        raise RecursiveSuccessorError(str(exc)) from exc
    if plan.digest() != expected_digest:
        raise RecursiveSuccessorError(
            "retained successor plan does not match the digest recorded at launch"
        )
    return plan


def _validate_inspection(
    inspection: Mapping[str, Any],
    plan: ExpectedSuccessorPlan,
    *,
    run_id: str,
    source_revision: str,
) -> dict[str, str]:
    ownership = {
        "devcapsule.e2e.managed": "true",
        "devcapsule.e2e.run-id": run_id,
        "devcapsule.e2e.source-revision": source_revision,
        "devcapsule.e2e.role": SUCCESSOR_ROLE,
    }
    if any(plan.labels.get(key) != value for key, value in ownership.items()):
        raise RecursiveSuccessorError("retained successor plan does not claim exact run ownership")
    try:
        return compare_inspection(plan, inspection)
    except SuccessorPlanError as exc:
        raise RecursiveSuccessorError(str(exc)) from exc


def _probe_successor(
    container_id: str,
    plan: ExpectedSuccessorPlan,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    script = r'''set -eu
test "${DEVCAPSULE_RECURSIVE_E2E:-}" = 1
test "${DOCKER_HOST:-}" = unix:///run/host-docker.sock
test -S /run/host-docker.sock
if [ -n "${DEVCAPSULE_HOST_OPEN_SOCKET:-}" ]; then
  test "${BROWSER:-}" = "/opt/devcapsule/bin/devcapsule.pex host-open"
  test -S "$DEVCAPSULE_HOST_OPEN_SOCKET"
fi
test -d /opt/claude
test "${DISABLE_UPDATES:-}" = 1
pgrep -fa pycharm >/dev/null
# The PEX scie re-execs through its unpacked interpreter, so PID 1's argv
# shows a cache path rather than the /opt binary; the stable supervisor
# signature is the runtime subcommand applied to the mounted plan.
tr '\0' ' ' </proc/1/cmdline | grep -q ' runtime __RUNTIME_PLAN_PATH__'
supervised=0
for pid in $(pgrep -f pycharm); do
  if [ "$(cut -d' ' -f4 "/proc/$pid/stat" 2>/dev/null)" = 1 ]; then supervised=1; fi
done
test "$supervised" = 1
python3 - <<'PY'
import hashlib, json, os, subprocess
commands = {
    "claude": ["claude", "--version"],
    "codex": ["codex", "--version"],
    "node": ["node", "--version"],
    "java": ["javac", "--version"],
    "maven": ["mvn", "--version"],
}
result = {}
for name, command in commands.items():
    output = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE).stdout.splitlines()
    result[name] = output[0]
result["java_home"] = os.environ["JAVA_HOME"]
result["maven_home"] = os.environ["MAVEN_HOME"]
result["run_id"] = os.environ["DEVCAPSULE_RUN_ID"]
plan_path = "__RUNTIME_PLAN_PATH__"
with open(plan_path, "rb") as handle:
    result["runtime_plan_sha256"] = hashlib.sha256(handle.read()).hexdigest()
options = ""
selected = ""
with open("/proc/self/mountinfo", encoding="utf-8") as handle:
    for line in handle:
        fields = line.split(" ")
        point = fields[4]
        if (plan_path == point or plan_path.startswith(point.rstrip("/") + "/")) and len(point) >= len(selected):
            selected = point
            options = fields[5]
result["runtime_plan_writable"] = "no" if "ro" in options.split(",") else "yes"
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
PY'''.replace("__RUNTIME_PLAN_PATH__", plan.runtime_plan_destination)
    return subprocess.run(
        ["docker", "exec", container_id, "/bin/bash", "-lc", script],
        check=False,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _load_owned_run(workspace_root: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise RecursiveSuccessorError("run ID must contain 16 to 64 lowercase hex digits")
    root = workspace_root.expanduser().resolve() / run_id
    if not root.is_dir() or root.is_symlink():
        raise RecursiveSuccessorError("retained run workspace is absent or unsafe")
    marker = _load_json(root / OWNER_MARKER)
    if marker.get("schema_version") != 1 or marker.get("run_id") != run_id:
        raise RecursiveSuccessorError("retained run ownership marker does not match")
    manifest = _load_json(root / MILESTONE_MANIFEST)
    if manifest.get("schema_version") != 1 or manifest.get("run_id") != run_id:
        raise RecursiveSuccessorError("retained run manifest does not match")
    return root, manifest


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecursiveSuccessorError(f"required retained run file is absent or malformed: {path.name}") from exc
    if not isinstance(value, dict):
        raise RecursiveSuccessorError(f"required retained run file is not an object: {path.name}")
    return value


def _write_manifest(run_root: Path, value: Mapping[str, Any]) -> None:
    atomic_write(
        run_root / MILESTONE_MANIFEST,
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        mode=0o600,
    )
