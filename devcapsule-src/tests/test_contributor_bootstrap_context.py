from __future__ import annotations

from pathlib import Path, PurePosixPath

from devcapsule.recursive_dogfood import ContainerInspection, Mount
from devcapsule.recursive_host import HostDaemonLaunchContext
from tests.e2e.test_contributor_bootstrap import ContributorDockerContext
import pytest

pytestmark = pytest.mark.legacy


def test_contributor_host_uses_direct_owned_workspace_path(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    context = ContributorDockerContext(
        mode="contributor-host",
        docker="docker",
        docker_environment={},
        image_id="sha256:" + "a" * 64,
        workspace_root=tmp_path,
        owner_identity="host-test",
    )

    assert context.bind_source(run_root) == PurePosixPath(str(run_root))


def test_recursive_contributor_translates_through_inspected_mount(tmp_path: Path) -> None:
    persistent_home = tmp_path / "home"
    persistent_home.mkdir()
    run_root = persistent_home / ".local/share/devcapsule/e2e-workspaces/run"
    run_root.mkdir(parents=True)
    container = ContainerInspection(
        identity="b" * 64,
        name="current-capsule",
        image="sha256:" + "c" * 64,
        source_revision=None,
        network_mode="host",
        mounts=(Mount("/host/persistent-home", str(persistent_home), "bind", True),),
        upper_directory=None,
    )
    host_context = HostDaemonLaunchContext.from_requirements(
        container,
        persistent_home=persistent_home,
        requirements=(),
    )
    context = ContributorDockerContext(
        mode="recursive-container",
        docker="docker",
        docker_environment={},
        image_id="sha256:" + "d" * 64,
        workspace_root=host_context.workspace_root,
        owner_identity=container.identity,
        recursive_host=host_context,
    )

    assert context.bind_source(run_root) == PurePosixPath(
        "/host/persistent-home/.local/share/devcapsule/e2e-workspaces/run"
    )
