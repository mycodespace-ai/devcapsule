"""Unit tests for ``tests.e2e.todo_seed``."""
from __future__ import annotations

from pathlib import Path

from tests.e2e.todo_seed import BACKEND_TYPED_SNIPPET, write_seed_project


def test_write_seed_project_materializes_backend_frontend_and_edit_markers(tmp_path: Path) -> None:
    """``write_seed_project`` writes the Todo layout and returns the exact line where ``BACKEND_TYPED_SNIPPET`` produces valid Python."""
    workspace = tmp_path / "todo-workspace"

    markers = write_seed_project(workspace)

    assert markers["backend_edit_line"] > 1
    assert markers["frontend_edit_line"] > 1
    assert (workspace / ".vscode" / "settings.json").is_file()
    assert (workspace / "backend" / "main.py").is_file()
    assert (workspace / "frontend" / "src" / "App.jsx").is_file()
    assert (workspace / "run-stack.sh").is_file()
    assert (workspace / "query-db.sh").is_file()
    lines = (workspace / "backend" / "main.py").read_text(encoding="utf-8").splitlines(keepends=True)
    insert_at = markers["backend_edit_line"] - 1
    completed = "".join([*lines[:insert_at], BACKEND_TYPED_SNIPPET, *lines[insert_at:]])
    compile(completed, "backend/main.py", "exec")
