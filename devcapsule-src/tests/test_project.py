from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from devcapsule.project import (
    ProjectMountError,
    default_project_mount,
    normalize_project_mount,
    plan_project,
    project_namespace,
    sanitize_name,
)

pytestmark = pytest.mark.legacy


def test_sanitize_name_matches_shell_launcher_rules() -> None:
    assert sanitize_name("example-project_1.2") == "example-project_1.2"
    assert sanitize_name("--My Project!!--") == "My-Project"
    assert sanitize_name("!!!") == "project"


def test_project_namespace_uses_path_hash_and_sanitized_basename() -> None:
    project_path = "/home/alice/work/My Project!!"
    expected_hash = hashlib.sha256(project_path.encode()).hexdigest()[:12]

    assert project_namespace(project_path) == f"{expected_hash}-My-Project"


def test_default_project_mount_uses_workspace_namespace() -> None:
    assert default_project_mount("abc123-example") == "/workspace/abc123-example"


def test_normalize_project_mount_defaults_to_workspace_project_id() -> None:
    assert normalize_project_mount(None, "abc123-example") == "/workspace/abc123-example"
    assert normalize_project_mount("", "abc123-example") == "/workspace/abc123-example"


def test_normalize_project_mount_trims_one_trailing_slash() -> None:
    assert normalize_project_mount("/workspace/example/", "ignored") == "/workspace/example"


@pytest.mark.parametrize(
    "project_mount",
    [
        "workspace/example",
    ],
)
def test_normalize_project_mount_requires_absolute_path(project_mount: str) -> None:
    with pytest.raises(ProjectMountError, match="absolute"):
        normalize_project_mount(project_mount, "abc123-example")


@pytest.mark.parametrize(
    "project_mount",
    [
        "/",
        "/etc",
        "/etc/project",
        "/ide-global-settings/project",
        "/ide-plugins/project",
        "/ide-project-state/project",
        "/tmp/project",
        "/usr/local/src/project",
        "/var/tmp/project",
    ],
)
def test_normalize_project_mount_rejects_reserved_container_paths(
    project_mount: str,
) -> None:
    with pytest.raises(ProjectMountError, match="reserved"):
        normalize_project_mount(project_mount, "abc123-example")


def test_plan_project_resolves_path_and_default_mount(tmp_path: Path) -> None:
    project_dir = tmp_path / "Example Project"
    project_dir.mkdir()

    plan = plan_project(project_dir)

    assert plan.project_path == project_dir.resolve()
    assert plan.project_id == project_namespace(project_dir.resolve())
    assert plan.project_mount == f"/workspace/{plan.project_id}"


def test_plan_project_accepts_custom_non_reserved_mount(tmp_path: Path) -> None:
    project_dir = tmp_path / "example"
    project_dir.mkdir()

    plan = plan_project(project_dir, "/workspace/custom")

    assert plan.project_mount == "/workspace/custom"
