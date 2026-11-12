from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import uuid

import pytest

from devcapsule.recursive_successor import (
    EXPECTED_PLAN,
    MILESTONE_MANIFEST,
    OWNER_MARKER,
    RecursiveSuccessorError,
    inspect_successor,
    successor_container_name,
)
from devcapsule.recursive_successor_plan import ExpectedSuccessorPlan

pytestmark = pytest.mark.legacy


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_REVISION = "0" * 40


def command(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def recommended_base() -> str:
    selected = os.environ.get("DEVCAPSULE_EARLY_EXIT_E2E_IMAGE")
    if selected:
        return selected
    lock_path = REPO_ROOT / ".devcapsule" / "devcapsule.linux-amd64.lock"
    with lock_path.open("rb") as stream:
        lock = tomllib.load(stream)
    return str(lock["base"]["reference"])


def runtime_plan() -> dict[str, object]:
    return {
        "version": 1,
        "project_path": "/workspace/project",
        "home": "/tmp/devcapsule-e2e-home",
        "identity": {"uid": 0, "gid": 0, "user": "root"},
        "state_slots": [
            {"name": "pycharm/config", "path": "/tmp/devcapsule-e2e-config"},
            {"name": "pycharm/system", "path": "/tmp/devcapsule-e2e-system"},
            {"name": "pycharm/plugins", "path": "/tmp/devcapsule-e2e-plugins"},
            {"name": "pycharm/log", "path": "/tmp/devcapsule-e2e-log"},
        ],
        "component": {
            "id": "pycharm",
            "adapter": "jetbrains",
            "configuration": {
                "installation_path": "/tmp",
                "launcher": "devcapsule-e2e-pycharm.sh",
                "properties_path": "/tmp/devcapsule-e2e-idea.properties",
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


@pytest.mark.e2e
def test_externally_removed_capsule_is_reported_as_failed(tmp_path: Path, built_pex: Path) -> None:
    """A real DevCapsule removed behind the launcher's back cannot inspect as healthy."""

    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI is required for the explicit E2E suite"
    command(docker, "version")
    image = recommended_base()
    image_result = command(docker, "image", "inspect", image, check=False)
    assert image_result.returncode == 0, (
        f"E2E image {image!r} is not available locally; pull it explicitly or set "
        "DEVCAPSULE_EARLY_EXIT_E2E_IMAGE"
    )
    image_inspection = json.loads(image_result.stdout)[0]

    run_id = uuid.uuid4().hex
    name = successor_container_name(run_id)
    ownership = {
        "devcapsule.e2e.managed": "true",
        "devcapsule.e2e.run-id": run_id,
        "devcapsule.e2e.source-revision": SOURCE_REVISION,
        "devcapsule.e2e.role": "successor",
    }
    create_args = [docker, "create", "--name", name, "--network", "none"]
    create_args.extend(("--env", f"DEVCAPSULE_RUN_ID={run_id}"))
    for label, value in ownership.items():
        create_args.extend(("--label", f"{label}={value}"))
    # Exercise the selected release even if the base embeds an older runtime
    # (or, with recipe 7, no runtime at all). Docker cp works across host sockets.
    create_args.extend(("--entrypoint", "/tmp/devcapsule-e2e.pex", image,
                        "runtime", "/tmp/devcapsule-e2e-runtime-plan.json"))
    created = command(*create_args)
    container_id = created.stdout.strip()
    assert len(container_id) == 64

    plan_path = tmp_path / "runtime-plan.json"
    plan_path.write_text(json.dumps(runtime_plan()), encoding="utf-8")
    launcher_path = tmp_path / "devcapsule-e2e-pycharm.sh"
    launcher_path.write_text("#!/bin/sh\nexec sleep 300\n", encoding="utf-8")
    launcher_path.chmod(0o755)
    removed = False
    try:
        command(docker, "cp", str(built_pex), f"{container_id}:/tmp/devcapsule-e2e.pex")
        command(
            docker,
            "cp",
            str(plan_path),
            f"{container_id}:/tmp/devcapsule-e2e-runtime-plan.json",
        )
        command(docker, "cp", str(launcher_path), f"{container_id}:/tmp/devcapsule-e2e-pycharm.sh")
        command(docker, "start", container_id)
        reflected_run_id = command(docker, "exec", container_id, "printenv", "DEVCAPSULE_RUN_ID")
        assert reflected_run_id.stdout.strip() == run_id
        copied_digest = command(docker, "exec", container_id, "sha256sum", "/tmp/devcapsule-e2e.pex").stdout.split()[0]
        assert copied_digest == hashlib.sha256(built_pex.read_bytes()).hexdigest()
        copied_identity = json.loads(command(docker, "exec", container_id, "/tmp/devcapsule-e2e.pex", "version", "--json").stdout)
        assert copied_identity == json.loads(command(str(built_pex), "version", "--json").stdout)
        running = command(docker, "inspect", "--format", "{{.State.Running}}", container_id)
        if running.stdout.strip() != "true":
            logs = command(docker, "logs", container_id, check=False)
            pytest.fail(f"test-owned DevCapsule did not stay running: {logs.stderr}")

        run_root = tmp_path / run_id
        run_root.mkdir()
        (run_root / OWNER_MARKER).write_text(
            json.dumps({"schema_version": 1, "run_id": run_id}), encoding="utf-8"
        )
        expected = ExpectedSuccessorPlan(
            name=name,
            image_reference=image,
            image_identity=str(image_inspection["Id"]),
            working_dir="",
            user="",
            group_add=(),
            labels=ownership,
            image_labels={
                str(key): str(value)
                for key, value in (image_inspection["Config"].get("Labels") or {}).items()
                if str(key).startswith("devcapsule.")
            },
            environment={"DEVCAPSULE_RUN_ID": run_id},
            secret_environment=(),
            mounts=(),
            tmpfs={},
            network_mode="none",
            ipc_mode="private",
            pids_limit=None,
            memory_limit_bytes=None,
            read_only_root=False,
            privileged=False,
            cap_add=(),
            cap_drop=(),
            security_opt=(),
            runtime_plan_destination="/tmp/devcapsule-e2e-runtime-plan.json",
            runtime_plan_digest=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        )
        (run_root / EXPECTED_PLAN).write_text(
            expected.to_json(show_host_paths=True) + "\n", encoding="utf-8"
        )
        (run_root / MILESTONE_MANIFEST).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "state": "stage-6-running",
                    "launch": {
                        "source_revision": SOURCE_REVISION,
                        "container_id": container_id,
                        "container_name": name,
                        "image_id": str(image_inspection["Id"]),
                        "expected_plan_digest": expected.digest(),
                        "role": "successor",
                    },
                }
            ),
            encoding="utf-8",
        )

        removed_result = command(docker, "rm", "--force", name)
        removed = True
        assert removed_result.stdout.strip() == name
        assert command(docker, "inspect", container_id, check=False).returncode != 0

        with pytest.raises(
            RecursiveSuccessorError,
            match="cannot inspect the exact successor container",
        ):
            inspect_successor(run_id, workspace_root=tmp_path, readiness_timeout=0.0)

        retained = json.loads((run_root / MILESTONE_MANIFEST).read_text(encoding="utf-8"))
        assert retained["launch"]["container_id"] == container_id
    finally:
        if not removed:
            command(docker, "rm", "--force", container_id, check=False)
