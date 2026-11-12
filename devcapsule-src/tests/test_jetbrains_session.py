"""IntelliJ profile ownership and stale IPC recovery across PID namespaces."""
import os
from pathlib import Path
import socket

import pytest

from devcapsule.components.intellij import DEFINITION
from devcapsule.container_runtime.components.jetbrains import session_lock, recover_dead_socket
from devcapsule.container_runtime.contract import RuntimePlan, Identity, RuntimePlanError

pytestmark = pytest.mark.legacy


def paths(tmp_path: Path) -> tuple[Path, Path]:
    config, system = tmp_path / "c", tmp_path / "s"
    config.mkdir()
    system.mkdir()
    return config / ".lock", system / ".port"


def test_dead_socket_recovers_even_when_old_pid_is_alive_here(tmp_path: Path) -> None:
    lock, port = paths(tmp_path)
    # This namespace's live PID must not make a dead prior-capsule socket live.
    lock.write_text(str(os.getpid()))
    settings = lock.parent / "settings.xml"
    settings.write_text("retained settings")
    with socket.socket(socket.AF_UNIX) as previous:
        previous.bind(str(port))
    recover_dead_socket(lock, port)
    assert not port.exists() and not lock.exists()
    assert settings.read_text() == "retained settings"


def test_live_socket_and_its_pid_lock_are_never_removed(tmp_path: Path) -> None:
    lock, port = paths(tmp_path)
    lock.write_text("42")
    with socket.socket(socket.AF_UNIX) as current:
        current.bind(str(port))
        current.listen(1)
        with pytest.raises(RuntimePlanError, match="socket is live"):
            recover_dead_socket(lock, port)
        assert port.is_socket() and lock.read_text() == "42"


def test_unrecognized_lock_is_left_intact(tmp_path: Path) -> None:
    lock, port = paths(tmp_path)
    lock.write_text("not a PID")
    with socket.socket(socket.AF_UNIX) as previous:
        previous.bind(str(port))
    with pytest.raises(RuntimePlanError, match="unexpected format"):
        recover_dead_socket(lock, port)
    assert port.is_socket() and lock.exists()


def test_symlink_endpoint_is_never_followed_or_removed(tmp_path: Path) -> None:
    lock, port = paths(tmp_path)
    target = tmp_path / "socket"
    with socket.socket(socket.AF_UNIX) as previous:
        previous.bind(str(target))
    port.symlink_to(target)
    lock.write_text("42")
    recover_dead_socket(lock, port)
    assert port.is_symlink() and target.is_socket() and lock.exists()


def test_profile_guard_excludes_a_second_session_and_releases_on_exit(tmp_path: Path) -> None:
    document = RuntimePlan.for_component(DEFINITION.runtime_template(), project_path="/project",
                                         home="/home/test", identity=Identity(os.getuid(), os.getgid())).to_mapping()
    slots = document["state_slots"]
    assert isinstance(slots, list)
    for slot in slots:
        assert isinstance(slot, dict)
        directory = tmp_path / slot["name"].split("/")[-1]
        directory.mkdir()
        slot["path"] = str(directory)
    runtime = RuntimePlan.from_mapping(document)
    with session_lock(runtime):
        with pytest.raises(RuntimePlanError, match="already owned"):
            with session_lock(runtime):
                pytest.fail("a second session acquired the same profile")
    with session_lock(runtime):
        pass
