from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from devcapsule.launch.pycharm._launcher import (
    PycharmRunError,
    host_backed_runtime_environment,
    translate_for_external_daemon,
)
from devcapsule.host_daemon import (
    HostDaemonError,
    current_container,
    docker_socket,
    host_path,
    in_container,
    requires_translation,
    socket_is_external,
    translate_bind_sources,
)
from devcapsule.recursive_dogfood import ContainerInspection, Mount

pytestmark = pytest.mark.legacy


HOST_PROJECT = "/home/developer/work/project"
HOST_HOME = "/home/developer/.local/share/devcapsule/home"


def container(*extra: Mount) -> ContainerInspection:
    return ContainerInspection(
        identity="c" * 64,
        name="devcapsule-current",
        image="sha256:" + "ab" * 32,
        source_revision=None,
        network_mode="host",
        mounts=(
            Mount(source=HOST_PROJECT, destination="/workspace/project", kind="bind", writable=True),
            Mount(source=HOST_HOME, destination="/home/devcapsule", kind="bind", writable=True),
            *extra,
        ),
        upper_directory="/var/lib/docker/overlay2/abc/diff",
    )


def mountinfo(tmp_path: Path, *targets: str) -> Path:
    path = tmp_path / "mountinfo"
    lines = [
        f"36 35 0:32 / {target} rw,relatime shared:15 - tmpfs tmpfs rw"
        for target in targets
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_host_launch_needs_no_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("devcapsule.host_daemon.in_container", lambda *a, **k: False)

    assert requires_translation({}) is False


def test_container_marker_detection(tmp_path: Path) -> None:
    marker = tmp_path / ".dockerenv"

    assert in_container(marker) is False
    marker.write_text("", encoding="utf-8")
    assert in_container(marker) is True


def test_socket_from_docker_host_is_used() -> None:
    assert docker_socket({"DOCKER_HOST": "unix:///run/host-docker.sock"}) == Path(
        "/run/host-docker.sock"
    )
    assert docker_socket({}) == Path("/var/run/docker.sock")
    # A non-unix endpoint falls back rather than guessing a path.
    assert docker_socket({"DOCKER_HOST": "tcp://10.0.0.1:2376"}) == Path("/var/run/docker.sock")


def test_bind_mounted_socket_is_external(tmp_path: Path) -> None:
    info = mountinfo(tmp_path, "/run/host-docker.sock", "/tmp")

    assert socket_is_external(Path("/run/host-docker.sock"), info) is True


def test_inner_daemon_socket_is_not_external(tmp_path: Path) -> None:
    # docker-in-docker creates its socket as an ordinary file, not a mount.
    info = mountinfo(tmp_path, "/tmp", "/run")

    assert socket_is_external(Path("/var/run/docker.sock"), info) is False


def test_absent_mountinfo_is_treated_as_not_external(tmp_path: Path) -> None:
    assert socket_is_external(Path("/var/run/docker.sock"), tmp_path / "absent") is False


def test_paths_map_through_their_deepest_mount() -> None:
    inspection = container()

    assert str(host_path(Path("/workspace/project"), inspection)) == HOST_PROJECT
    assert (
        str(host_path(Path("/workspace/project/backend/app"), inspection))
        == f"{HOST_PROJECT}/backend/app"
    )
    assert str(host_path(Path("/home/devcapsule/.cache"), inspection)) == f"{HOST_HOME}/.cache"


def test_deepest_mount_wins_over_a_parent_mount() -> None:
    inspection = container(
        Mount(source="/host/cache", destination="/home/devcapsule/.cache", kind="bind", writable=True)
    )

    assert str(host_path(Path("/home/devcapsule/.cache/x"), inspection)) == "/host/cache/x"


def test_unbacked_path_fails_loudly_instead_of_creating_an_empty_directory() -> None:
    with pytest.raises(HostDaemonError) as error:
        host_path(Path("/opt/not-mounted/thing"), container())

    message = str(error.value)
    assert "not backed by any mount" in message
    assert "empty directory" in message


def test_translation_rewrites_only_bind_sources() -> None:
    args = [
        "--name",
        "child",
        "--mount",
        "type=bind,src=/workspace/project,dst=/workspace/project",
        "--mount",
        "type=bind,src=/home/devcapsule/.cache,dst=/home/devcapsule/.cache,ro",
        "--tmpfs",
        "/tmp:rw",
        "--env",
        "SRC=/workspace/project",
    ]

    translated = translate_bind_sources(args, container())

    assert translated[3] == f"type=bind,src={HOST_PROJECT},dst=/workspace/project"
    assert translated[5] == f"type=bind,src={HOST_HOME}/.cache,dst=/home/devcapsule/.cache,ro"
    # Non-mount arguments are untouched, including values that look like paths.
    assert translated[6:] == ["--tmpfs", "/tmp:rw", "--env", "SRC=/workspace/project"]


def test_volume_mounts_are_left_alone() -> None:
    args = ["--mount", "type=volume,dst=/var/lib/docker"]

    assert translate_bind_sources(args, container()) == args


def test_unidentifiable_container_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(HostDaemonError, match="no running containers"):
        current_container({})


def test_rejected_inspection_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "permission denied")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(HostDaemonError, match="rejected container inspection"):
        current_container({"DEVCAPSULE_CONTAINER_NAME": "devcapsule-current"})


def test_named_container_is_translated_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    inspection = {
        "Id": "c" * 64,
        "Name": "/devcapsule-current",
        "Image": "sha256:" + "ab" * 32,
        "Config": {"Labels": {}},
        "HostConfig": {"NetworkMode": "host"},
        "Mounts": [
            {
                "Type": "bind",
                "Source": HOST_PROJECT,
                "Destination": "/workspace/project",
                "RW": True,
            }
        ],
    }

    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, json.dumps([inspection]), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.requires_translation", lambda env: True
    )

    translated = translate_for_external_daemon(
        ["--mount", "type=bind,src=/workspace/project,dst=/workspace/project"],
        {"DEVCAPSULE_CONTAINER_NAME": "devcapsule-current"},
    )

    assert translated == ["--mount", f"type=bind,src={HOST_PROJECT},dst=/workspace/project"]


def test_staging_moves_off_a_container_local_tmpfs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_home = tmp_path / "data"
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.requires_translation", lambda _env: True
    )
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.current_container",
        lambda _env: container(
            Mount(source="/host/data", destination=str(data_home), kind="bind", writable=True)
        ),
    )

    staged = host_backed_runtime_environment(
        {"XDG_RUNTIME_DIR": "/tmp/devcapsule-runtime-1000", "XDG_DATA_HOME": str(data_home)}
    )

    # /tmp is a container-local tmpfs the daemon cannot see, so staging moves.
    assert staged["XDG_RUNTIME_DIR"] == str(data_home / "devcapsule" / "launch-staging")
    assert Path(staged["XDG_RUNTIME_DIR"]).is_dir()


def test_already_host_backed_staging_is_kept(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.requires_translation", lambda _env: True
    )
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.current_container",
        lambda _env: container(
            Mount(source="/host/runtime", destination=str(runtime), kind="bind", writable=True)
        ),
    )

    staged = host_backed_runtime_environment({"XDG_RUNTIME_DIR": str(runtime)})

    assert staged["XDG_RUNTIME_DIR"] == str(runtime)


def test_unmountable_staging_fails_loudly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.requires_translation", lambda _env: True
    )
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.current_container",
        lambda _env: container(),
    )

    with pytest.raises(PycharmRunError, match="not backed by any mount"):
        host_backed_runtime_environment({"XDG_DATA_HOME": str(tmp_path / "nowhere")})


def test_host_launch_keeps_its_runtime_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "devcapsule.launch.pycharm._launcher.requires_translation", lambda _env: False
    )

    assert host_backed_runtime_environment({"XDG_RUNTIME_DIR": "/tmp/x"})["XDG_RUNTIME_DIR"] == "/tmp/x"


def test_launcher_leaves_host_launches_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("devcapsule.host_daemon.in_container", lambda *a, **k: False)
    args = ["--mount", "type=bind,src=/workspace/project,dst=/workspace/project"]

    assert translate_for_external_daemon(list(args), {}) == args
