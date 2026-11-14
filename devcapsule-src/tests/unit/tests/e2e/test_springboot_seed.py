"""Unit tests for ``tests.e2e.springboot_seed``."""
from __future__ import annotations

from pathlib import Path

from tests.e2e.springboot_seed import materialize


def test_materialize_writes_maven_spring_boot_layout_and_placeholder_marker(tmp_path: Path) -> None:
    """``materialize`` writes the Maven project, Spring Boot Java sources, static UI, and reports the placeholder line."""
    workspace = tmp_path / "springboot-workspace"

    info = materialize(workspace)

    assert isinstance(info["controller_placeholder_line"], int)
    assert info["controller_placeholder_line"] > 1
    assert (workspace / "pom.xml").is_file()
    assert (workspace / ".mvn" / "maven.config").is_file()
    assert (workspace / "src" / "main" / "java" / "io" / "devcapsule" / "demo" / "SprintController.java").is_file()
    assert (workspace / "src" / "main" / "resources" / "static" / "index.html").is_file()
    assert (workspace / "run-stack.sh").is_file()
