from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from devcapsule.recursive_successor_plan import (
    REDACTED_HOST_PATH,
    ExpectedSuccessorPlan,
    SuccessorPlanError,
    compare_inspection,
)

pytestmark = pytest.mark.legacy


RUNTIME_PLAN_DESTINATION = "/etc/devcapsule/runtime-plan.json"
RUNTIME_PLAN_DIGEST = "a" * 64
IMAGE_REFERENCE = "devcapsule-local-pycharm:2145e28bc7b8aca0eee0"
IMAGE_IDENTITY = "sha256:" + "f3" * 32
HOST_PROJECT = "/host/home/costin/projects/devcapsule"
HOST_RUNTIME_PLAN = "/host/run/user/1000/staging/runtime-plan.json"

IMAGE_LABELS = {
    "devcapsule.materialization.identity": "2145e28bc7b8aca0eee0a839050d626b",
    "devcapsule.materialization.base-identity": "sha256:" + "0c" * 32,
    "devcapsule.materialization.recipe-version": "4",
    "devcapsule.component.id": "pycharm",
    "devcapsule.component.version": "2025.2",
    "org.opencontainers.image.vendor": "irrelevant",
}


def docker_args() -> list[str]:
    """The translated arguments a Stage 6 launch actually hands to ``docker run``."""

    return [
        "--detach",
        "--name",
        "devcapsule-e2e-b2093d85912fa34ac1324e1da26a9dcd-successor",
        "--workdir",
        "/workspace/devcapsule",
        "--env",
        "DISPLAY",
        "--env",
        "HOME=/home/devcapsule",
        "--env",
        "DEVCAPSULE_RECURSIVE_E2E=1",
        "--env",
        "DEVCAPSULE_RUN_ID=b2093d85912fa34ac1324e1da26a9dcd",
        "--env",
        "DOCKER_HOST=unix:///run/host-docker.sock",
        "--mount",
        f"type=bind,src={HOST_PROJECT},dst=/workspace/devcapsule",
        "--mount",
        f"type=bind,src={HOST_RUNTIME_PLAN},dst={RUNTIME_PLAN_DESTINATION},ro",
        "--tmpfs",
        "/tmp:rw,exec,nosuid,nodev,size=2g",
        "--ipc",
        "private",
        "--network",
        "host",
        "--pids-limit",
        "4096",
        "--user",
        "1000:1000",
        "--group-add",
        "999",
        "--memory",
        "8589934592",
        "--pull=never",
        "--label",
        "devcapsule.e2e.managed=true",
        "--label",
        "devcapsule.e2e.role=successor",
    ]


def build_plan(args: list[str] | None = None) -> ExpectedSuccessorPlan:
    return ExpectedSuccessorPlan.from_docker_args(
        docker_args() if args is None else args,
        image_reference=IMAGE_REFERENCE,
        image_identity=IMAGE_IDENTITY,
        image_labels=IMAGE_LABELS,
        runtime_plan_destination=RUNTIME_PLAN_DESTINATION,
        runtime_plan_digest=RUNTIME_PLAN_DIGEST,
    )


def matching_inspection(plan: ExpectedSuccessorPlan) -> dict[str, Any]:
    """A ``docker inspect`` result that satisfies the plan exactly."""

    return {
        "Name": f"/{plan.name}",
        "Image": IMAGE_IDENTITY,
        "RestartCount": 0,
        "State": {"Running": True},
        "Config": {
            "Image": IMAGE_REFERENCE,
            "User": "1000:1000",
            "WorkingDir": "/workspace/devcapsule",
            "Labels": {**IMAGE_LABELS, **plan.labels},
            "Env": [
                "HOME=/home/devcapsule",
                "DEVCAPSULE_RECURSIVE_E2E=1",
                "DEVCAPSULE_RUN_ID=b2093d85912fa34ac1324e1da26a9dcd",
                "DOCKER_HOST=unix:///run/host-docker.sock",
                "DISPLAY=:0",
                "PATH=/usr/bin",
            ],
        },
        "HostConfig": {
            "NetworkMode": "host",
            "IpcMode": "private",
            "Privileged": False,
            "ReadonlyRootfs": False,
            "CapAdd": None,
            "CapDrop": None,
            "SecurityOpt": None,
            "GroupAdd": ["999"],
            "Memory": 8589934592,
            "PidsLimit": 4096,
            "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
            "Tmpfs": {"/tmp": "rw,exec,nosuid,nodev,size=2g"},
        },
        "Mounts": [
            {
                "Type": "bind",
                "Source": HOST_PROJECT,
                "Destination": "/workspace/devcapsule",
                "RW": True,
            },
            {
                "Type": "bind",
                "Source": HOST_RUNTIME_PLAN,
                "Destination": RUNTIME_PLAN_DESTINATION,
                "RW": False,
            },
        ],
    }


def rejected(inspection: dict[str, Any]) -> str:
    plan = build_plan()
    with pytest.raises(SuccessorPlanError) as error:
        compare_inspection(plan, inspection)
    return str(error.value)


def test_plan_models_the_complete_translated_launch() -> None:
    plan = build_plan()

    assert plan.name.endswith("-successor")
    assert plan.working_dir == "/workspace/devcapsule"
    assert plan.user == "1000:1000"
    assert plan.group_add == ("999",)
    assert plan.network_mode == "host"
    assert plan.ipc_mode == "private"
    assert plan.pids_limit == 4096
    assert plan.memory_limit_bytes == 8589934592
    assert plan.read_only_root is False
    assert plan.privileged is False
    assert plan.environment["DEVCAPSULE_RECURSIVE_E2E"] == "1"
    assert plan.secret_environment == ("DISPLAY",)
    assert plan.tmpfs == {"/tmp": "rw,exec,nosuid,nodev,size=2g"}
    assert [mount.destination for mount in plan.mounts] == [
        RUNTIME_PLAN_DESTINATION,
        "/workspace/devcapsule",
    ]
    assert plan.labels == {
        "devcapsule.e2e.managed": "true",
        "devcapsule.e2e.role": "successor",
    }
    assert plan.runtime_plan_digest == RUNTIME_PLAN_DIGEST


def test_plan_pins_only_managed_image_labels() -> None:
    plan = build_plan()

    assert plan.image_labels["devcapsule.materialization.identity"] == (
        IMAGE_LABELS["devcapsule.materialization.identity"]
    )
    assert "org.opencontainers.image.vendor" not in plan.image_labels


def test_plan_requires_a_formation_identity() -> None:
    with pytest.raises(SuccessorPlanError, match="materialization.identity"):
        ExpectedSuccessorPlan.from_docker_args(
            docker_args(),
            image_reference=IMAGE_REFERENCE,
            image_identity=IMAGE_IDENTITY,
            image_labels={"devcapsule.component.id": "pycharm"},
            runtime_plan_destination=RUNTIME_PLAN_DESTINATION,
            runtime_plan_digest=RUNTIME_PLAN_DIGEST,
        )


def test_plan_requires_the_checkout_runtime_plan_mount() -> None:
    args = docker_args()
    dropped = next(index for index, value in enumerate(args) if RUNTIME_PLAN_DESTINATION in value)
    del args[dropped - 1 : dropped + 1]

    with pytest.raises(SuccessorPlanError, match="runtime plan"):
        build_plan(args)


def test_plan_rejects_an_unmodelled_docker_flag() -> None:
    with pytest.raises(SuccessorPlanError, match="unmodelled Docker flag"):
        build_plan([*docker_args(), "--cgroup-parent", "/evil"])


def test_plan_round_trips_through_its_retained_form() -> None:
    plan = build_plan()

    restored = ExpectedSuccessorPlan.from_mapping(
        json.loads(plan.to_json(show_host_paths=True))
    )

    assert restored == plan
    assert restored.digest() == plan.digest()


def test_ordinary_evidence_redacts_daemon_side_sources() -> None:
    plan = build_plan()

    evidence = plan.to_json()

    assert HOST_PROJECT not in evidence
    assert HOST_RUNTIME_PLAN not in evidence
    assert REDACTED_HOST_PATH in evidence
    assert RUNTIME_PLAN_DESTINATION in evidence


def test_digest_changes_when_a_retained_source_is_tampered_with() -> None:
    plan = build_plan()
    tampered = json.loads(plan.to_json(show_host_paths=True))
    for mount in tampered["mounts"]:
        if mount["destination"] == RUNTIME_PLAN_DESTINATION:
            mount["source"] = "/host/tmp/attacker/runtime-plan.json"

    assert ExpectedSuccessorPlan.from_mapping(tampered).digest() != plan.digest()


def test_matching_successor_passes_every_modelled_check() -> None:
    plan = build_plan()

    checks = compare_inspection(plan, matching_inspection(plan))

    assert set(checks) == {
        "container_identity",
        "image_identity",
        "labels",
        "formation_identity",
        "runtime_identity",
        "environment",
        "mounts",
        "security_settings",
        "resource_limits",
        "restart_policy",
        "running",
    }
    assert set(checks.values()) == {"pass"}


def test_pass_through_environment_values_are_never_compared() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    inspection["Config"]["Env"] = [
        value for value in inspection["Config"]["Env"] if not value.startswith("DISPLAY=")
    ]

    assert compare_inspection(plan, inspection)["environment"] == "pass"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(Name="/devcapsule-e2e-other-successor"), "deterministic run name"),
        (lambda value: value.update(Image="sha256:" + "ff" * 32), "image ID"),
        (lambda value: value["Config"].update(Image="ubuntu:24.04"), "image reference"),
        (lambda value: value["Config"]["Labels"].update({"devcapsule.e2e.role": "control"}), "label"),
        (
            lambda value: value["Config"]["Labels"].update(
                {"devcapsule.materialization.identity": "0" * 32}
            ),
            "image label",
        ),
        (lambda value: value["Config"].update(User="0:0"), "runtime user"),
        (lambda value: value["Config"].update(WorkingDir="/root"), "working directory"),
        (
            lambda value: value["Config"].update(
                Env=[
                    "HOME=/root",
                    "DEVCAPSULE_RECURSIVE_E2E=1",
                    "DEVCAPSULE_RUN_ID=b2093d85912fa34ac1324e1da26a9dcd",
                    "DOCKER_HOST=unix:///run/host-docker.sock",
                ]
            ),
            "environment value for 'HOME'",
        ),
        (
            lambda value: value["Config"].update(
                Env=[
                    "HOME=/home/devcapsule",
                    "DEVCAPSULE_RECURSIVE_E2E=1",
                    "DEVCAPSULE_RUN_ID=ffffffffffffffffffffffffffffffff",
                    "DOCKER_HOST=unix:///run/host-docker.sock",
                ]
            ),
            "environment value for 'DEVCAPSULE_RUN_ID'",
        ),
        (
            lambda value: value["Config"].update(Env=["HOME=/home/devcapsule"]),
            "environment is missing",
        ),
        (lambda value: value["HostConfig"].update(NetworkMode="bridge"), "network mode"),
        (lambda value: value["HostConfig"].update(IpcMode="host"), "IPC mode"),
        (lambda value: value["HostConfig"].update(Privileged=True), "privileged state"),
        (lambda value: value["HostConfig"].update(ReadonlyRootfs=True), "root filesystem mode"),
        (lambda value: value["HostConfig"].update(CapAdd=["SYS_ADMIN"]), "CapAdd"),
        (lambda value: value["HostConfig"].update(CapDrop=["ALL"]), "CapDrop"),
        (
            lambda value: value["HostConfig"].update(SecurityOpt=["seccomp=unconfined"]),
            "SecurityOpt",
        ),
        (lambda value: value["HostConfig"].update(GroupAdd=["999", "0"]), "GroupAdd"),
        (lambda value: value["HostConfig"].update(Memory=0), "memory limit"),
        (lambda value: value["HostConfig"].update(PidsLimit=0), "PID limit"),
        (
            lambda value: value["HostConfig"].update(RestartPolicy={"Name": "always"}),
            "restart policy",
        ),
        (lambda value: value["HostConfig"].update(Tmpfs={"/tmp": "rw,exec,size=8g"}), "tmpfs"),
        (lambda value: value.update(RestartCount=2), "restarted since launch"),
        (lambda value: value["State"].update(Running=False), "not running"),
    ],
)
def test_every_modelled_deviation_is_rejected(mutation: Any, message: str) -> None:
    plan = build_plan()
    inspection = copy.deepcopy(matching_inspection(plan))
    mutation(inspection)

    assert message in rejected(inspection)


def test_missing_planned_mount_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    inspection["Mounts"] = [
        entry for entry in inspection["Mounts"] if entry["Destination"] != RUNTIME_PLAN_DESTINATION
    ]

    message = rejected(inspection)

    assert "missing planned mounts" in message
    assert RUNTIME_PLAN_DESTINATION in message


def test_unplanned_extra_mount_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    inspection["Mounts"].append(
        {
            "Type": "bind",
            "Source": "/host/home/costin/.ssh",
            "Destination": "/home/devcapsule/.ssh",
            "RW": True,
        }
    )

    message = rejected(inspection)

    assert "unplanned mounts" in message
    assert "/home/devcapsule/.ssh" in message
    assert "/host/home/costin/.ssh" not in message


def test_unplanned_volume_mount_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    inspection["Mounts"].append(
        {"Type": "volume", "Name": "leaked", "Destination": "/var/lib/docker", "RW": True}
    )

    assert "unplanned mounts" in rejected(inspection)


def test_unplanned_tmpfs_mount_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    inspection["Mounts"].append(
        {"Type": "tmpfs", "Destination": "/var/tmp", "RW": True}
    )

    assert "unplanned tmpfs mounts" in rejected(inspection)


def test_relaxed_read_only_mount_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    for entry in inspection["Mounts"]:
        if entry["Destination"] == RUNTIME_PLAN_DESTINATION:
            entry["RW"] = True

    message = rejected(inspection)

    assert "read-only mode" in message
    assert RUNTIME_PLAN_DESTINATION in message


def test_substituted_bind_source_is_rejected_without_leaking_it() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    for entry in inspection["Mounts"]:
        if entry["Destination"] == RUNTIME_PLAN_DESTINATION:
            entry["Source"] = "/host/tmp/attacker/runtime-plan.json"

    message = rejected(inspection)

    assert "retained translated source" in message
    assert "/host/tmp/attacker" not in message
    assert HOST_RUNTIME_PLAN not in message


def test_mount_type_substitution_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    for entry in inspection["Mounts"]:
        if entry["Destination"] == "/workspace/devcapsule":
            entry["Type"] = "volume"

    assert "unplanned type" in rejected(inspection)


@pytest.mark.parametrize(
    "inspection",
    [
        {},
        {"Name": "/x", "Config": "nonsense"},
        {"Name": "/x", "Config": {}, "HostConfig": {}},
    ],
)
def test_malformed_inspection_is_rejected(inspection: dict[str, Any]) -> None:
    with pytest.raises(SuccessorPlanError):
        compare_inspection(build_plan(), inspection)


def test_malformed_mount_set_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    inspection["Mounts"] = "nonsense"

    assert "malformed mount set" in rejected(inspection)


def test_duplicate_mount_destination_is_rejected() -> None:
    plan = build_plan()
    inspection = matching_inspection(plan)
    inspection["Mounts"].append(dict(inspection["Mounts"][0]))

    assert "declared more than once" in rejected(inspection)
