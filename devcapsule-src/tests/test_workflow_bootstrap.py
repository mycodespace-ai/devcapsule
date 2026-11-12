from __future__ import annotations

from datetime import date
from importlib.resources import files
from pathlib import Path

import pytest

from devcapsule.workflow_bootstrap import (
    WorkflowBootstrapError,
    bootstrap_project,
    definition_version,
    project_workflow_declaration,
    project_workflow_type,
)

pytestmark = pytest.mark.legacy


REPO_ROOT = Path(__file__).resolve().parents[2]


def declaration(root: Path, workflow_type: str | None = None) -> None:
    config = root / ".devcapsule" / "devcapsule.toml"
    config.parent.mkdir(parents=True)
    selected = "" if workflow_type is None else f'workflow-type = "{workflow_type}"\n'
    config.write_text(
        selected + '[project]\nname = "Example Project"\nslug = "example"\n',
        encoding="utf-8",
    )


@pytest.mark.flaky
@pytest.mark.xfail(
    reason="release-discipline coverage for workflow definitions is pending",
    strict=False,
)
def test_packaged_workflow_is_the_root_reusable_definition() -> None:
    packaged = (
        files("devcapsule.assets.project_workflow")
        .joinpath("definition", "WORKFLOW.md")
        .read_text(encoding="utf-8")
    )

    assert packaged == (REPO_ROOT / "WORKFLOW.md").read_text(encoding="utf-8")


def test_single_stream_bootstrap_installs_definition_and_instance(tmp_path: Path) -> None:
    declaration(tmp_path)
    existing = tmp_path / "engineering-docs" / "design-notes" / "idea.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("# Existing idea\n", encoding="utf-8")

    report = bootstrap_project(tmp_path, today=date(2026, 8, 21))

    assert report.workflow_type == "single-stream"
    assert (tmp_path / "WORKFLOW.md").is_file()
    assert "Read `WORKFLOW.md`" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert (tmp_path / "INFORMATION-MODEL.md").read_text(encoding="utf-8").startswith("# Information Model\n")
    assert (tmp_path / "PREAMBLE.md").read_text(encoding="utf-8").startswith("# Preamble\n\n*For humans.*")
    local = (tmp_path / "WORKFLOW-LOCAL.md").read_text(encoding="utf-8")
    assert local.startswith("# Local Workflow: Example Project\n")
    assert "## Version Scheme" in local and "## Exceptions" in local
    status = (tmp_path / "CURRENT-STATUS.md").read_text(encoding="utf-8")
    assert "Workflow type: `single-stream`" in status
    assert "Initial project orientation" in status
    assert "Example Project" in (tmp_path / "README.md").read_text(encoding="utf-8")
    index = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "Reusable human/agent workflow" in index
    assert "engineering-docs/design-notes/idea.md" in index
    assert (tmp_path / "engineering-docs" / "wip").is_dir()
    assert (tmp_path / "engineering-docs" / "archive").is_dir()
    assert ".idea/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_existing_project_state_is_preserved_and_legacy_handoff_is_migrated(
    tmp_path: Path,
) -> None:
    declaration(tmp_path)
    readme = "# Existing\n\n## Current State And Next Step\n\nCurrent stage: Research.\n"
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("custom agent rules\n", encoding="utf-8")

    first = bootstrap_project(tmp_path, today=date(2026, 8, 21))

    assert Path("AGENTS.md") in first.preserved
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "custom agent rules\n"
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == readme
    status = (tmp_path / "CURRENT-STATUS.md").read_text(encoding="utf-8")
    assert "Initialized from the pre-WORKFLOW DevCapsule handoff" in status
    assert "Current stage: Research." in status

    second = bootstrap_project(
        tmp_path,
        refresh_workflow_definition=True,
        today=date(2026, 8, 21),
    )

    assert Path("AGENTS.md") in second.refreshed
    assert "Read `WORKFLOW.md`" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert Path("INFORMATION-MODEL.md") in second.refreshed
    assert Path("PREAMBLE.md") in second.refreshed
    assert (tmp_path / "CURRENT-STATUS.md").read_text(encoding="utf-8") == status
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == readme


def test_multiple_streams_bootstrap_initializes_reserved_workstream(
    tmp_path: Path,
) -> None:
    declaration(tmp_path, "multiple-streams")

    report = bootstrap_project(tmp_path, today=date(2026, 8, 21))

    assert report.workflow_type == "multiple-streams"
    registry = (tmp_path / "CURRENT-STATUS.md").read_text(encoding="utf-8")
    assert "`project-management`" in registry
    handoff_root = tmp_path / "engineering-docs/wip/2026-08-21-project-management"
    assert (handoff_root / "CURRENT-STATUS.md").is_file()
    assert (handoff_root / "intake/README.md").is_file()
    assert (handoff_root / "intake-dispositions.md").is_file()
    index = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "Project management current status" in index
    assert "Maintenance current status" in index
    assert "`maintenance`" in registry
    maintenance_root = tmp_path / "engineering-docs/wip/2026-08-21-maintenance"
    assert (maintenance_root / "CURRENT-STATUS.md").is_file()
    assert "Name: `maintenance`" in (maintenance_root / "CURRENT-STATUS.md").read_text(
        encoding="utf-8"
    )
    assert "# Intake: `maintenance`" in (maintenance_root / "intake/README.md").read_text(
        encoding="utf-8"
    )
    assert (maintenance_root / "intake-dispositions.md").is_file()
    bug_template = (tmp_path / "engineering-docs/bugs/_template.md").read_text(
        encoding="utf-8"
    )
    assert bug_template.startswith("---\nstatus: reported\n")

    repeated = bootstrap_project(tmp_path, today=date(2030, 1, 1))
    assert not repeated.created
    assert handoff_root.is_dir()
    assert not (tmp_path / "engineering-docs/wip/2030-01-01-project-management").exists()
    assert not (tmp_path / "engineering-docs/wip/2030-01-01-maintenance").exists()


def test_project_predating_maintenance_gets_it_with_todays_date(
    tmp_path: Path,
) -> None:
    """A multiple-streams project initialized before the maintenance workstream
    existed is not incomplete: bootstrap adds it under the adoption exception,
    dated today rather than at the project-management start date."""
    declaration(tmp_path, "multiple-streams")
    bootstrap_project(tmp_path, today=date(2026, 8, 21))
    import shutil

    shutil.rmtree(tmp_path / "engineering-docs/wip/2026-08-21-maintenance")

    report = bootstrap_project(tmp_path, today=date(2026, 9, 18))

    created = {str(path) for path in report.created}
    assert "engineering-docs/wip/2026-09-18-maintenance/CURRENT-STATUS.md" in created
    assert not (tmp_path / "engineering-docs/wip/2026-08-21-maintenance").exists()
    assert (tmp_path / "engineering-docs/wip/2026-08-21-project-management").is_dir()


def test_incomplete_existing_multiple_streams_instance_is_rejected(
    tmp_path: Path,
) -> None:
    declaration(tmp_path, "multiple-streams")
    (tmp_path / "CURRENT-STATUS.md").write_text(
        "# Existing registry without project management\n", encoding="utf-8"
    )

    with pytest.raises(WorkflowBootstrapError, match="incompletely initialized"):
        bootstrap_project(tmp_path, today=date(2026, 8, 21))

    assert not (tmp_path / "WORKFLOW.md").exists()


def test_invalid_declared_workflow_type_fails_before_writing(tmp_path: Path) -> None:
    declaration(tmp_path, "parallel-magic")

    with pytest.raises(WorkflowBootstrapError, match="invalid workflow-type"):
        bootstrap_project(tmp_path)

    assert not (tmp_path / "WORKFLOW.md").exists()


def test_missing_workflow_type_means_single_stream(tmp_path: Path) -> None:
    declaration(tmp_path)
    assert project_workflow_type(tmp_path) == "single-stream"


def packaged_definition_version() -> str:
    text = (
        files("devcapsule.assets.project_workflow")
        .joinpath("definition", "WORKFLOW.md")
        .read_text(encoding="utf-8")
    )
    version = definition_version(text)
    assert version != "unversioned"
    return version


def test_bootstrap_declares_the_installed_definition_version(tmp_path: Path) -> None:
    declaration(tmp_path, "multiple-streams")

    report = bootstrap_project(tmp_path, today=date(2026, 9, 18))

    assert Path(".devcapsule/devcapsule.toml") in report.updated
    declared = project_workflow_declaration(tmp_path)
    assert declared.mode == "multiple-streams"
    assert declared.definition == "devcapsule"
    assert declared.version == packaged_definition_version()
    toml = (tmp_path / ".devcapsule/devcapsule.toml").read_text(encoding="utf-8")
    assert 'workflow-type = "multiple-streams"' in toml  # the legacy key is left alone
    assert toml.count("[workflow]") == 1

    repeated = bootstrap_project(tmp_path, today=date(2026, 9, 19))
    assert Path(".devcapsule/devcapsule.toml") in repeated.preserved


def test_misdeclared_version_is_reported_unless_the_definition_is_refreshed(
    tmp_path: Path,
) -> None:
    declaration(tmp_path, "single-stream")
    bootstrap_project(tmp_path, today=date(2026, 9, 18))
    config = tmp_path / ".devcapsule/devcapsule.toml"
    text = config.read_text(encoding="utf-8").replace(
        f'version = "{packaged_definition_version()}"', 'version = "0.0.1"'
    )
    config.write_text(text, encoding="utf-8")

    with pytest.raises(WorkflowBootstrapError, match="declares workflow version '0.0.1'"):
        bootstrap_project(tmp_path, today=date(2026, 9, 18))

    bootstrap_project(tmp_path, today=date(2026, 9, 18), refresh_workflow_definition=True)
    assert project_workflow_declaration(tmp_path).version == packaged_definition_version()


def test_mode_comes_from_the_table_and_must_agree_with_the_legacy_key(
    tmp_path: Path,
) -> None:
    config = tmp_path / ".devcapsule" / "devcapsule.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[workflow]\nmode = "multiple-streams"\n[project]\nname = "x"\n',
        encoding="utf-8",
    )
    assert project_workflow_type(tmp_path) == "multiple-streams"

    config.write_text(
        'workflow-type = "single-stream"\n[workflow]\nmode = "multiple-streams"\n',
        encoding="utf-8",
    )
    with pytest.raises(WorkflowBootstrapError, match="must agree"):
        project_workflow_type(tmp_path)


def test_definition_version_reads_frontmatter_only() -> None:
    assert definition_version("---\ndefinition: devcapsule\nversion: 1.2.3\n---\n# X\n") == "1.2.3"
    assert definition_version("# Human / Agent Iteration Workflow\n") == "unversioned"
    assert definition_version("---\ndefinition: devcapsule\n---\nversion: 9.9.9\n") == "unversioned"
