"""``project run --ide IDE --force``: one named departure from a project's required IDE, for one launch.

Work order of 2026-10-28, *Explicit IDE requirement override*. A project may
require an IDE; a developer may launch another one once, with ``--force``,
warned and recorded, never saved. The fixture is the order's: PyCharm
required, PyCharm saved for the checkout, an unrelated mandatory tool.
"""

from __future__ import annotations

import io
from pathlib import Path
import tomllib

import pytest

from devcapsule import cli
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.compat import DecisionPending
from devcapsule.configuration.capabilities import IDE_REQUIREMENT, CapabilityPolicy, LocalCapabilities, RequirementDeparture
from devcapsule.configuration.capability_commands import paths
from devcapsule.configuration.capability_selection import usable_lock
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.history import history_directory
from devcapsule.configuration.storage import checkout_record_paths, load_toml
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES
from devcapsule.version_sets import state_directory

pytestmark = pytest.mark.legacy

MATRIX = MATRICES[Platform.LINUX_AMD64]
CREATOR = "mailto:owner@example.test"


def invoke(root: Path, *arguments: str) -> int:
    return cli.main(["project", "--path", str(root), *arguments])


def record_path(root: Path) -> Path:
    return checkout_record_paths(load_toml(paths(root)[0]), root)[0]


def shared_bytes(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted((root / ".devcapsule").iterdir())}


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    return tmp_path


@pytest.fixture
def project(home: Path) -> Path:
    """The order's fixture: PyCharm required beside an unrelated mandatory tool, PyCharm saved, the base trusted."""
    root = home / "project"
    root.mkdir()
    assert invoke(root, "init", "--require", "python", "--require", "python-ide", "--require", "codex-agent",
                  "--ide", "python-ide", "--creator", CREATOR, "--authorize", "base-image", "default") == 0
    saved = load_toml(record_path(root))
    assert saved["capabilities"]["selected"] == ["python-ide"]
    return root


@pytest.fixture
def free_project(home: Path) -> Path:
    """A project that requires no IDE, with PyCharm saved: an ordinary override needs no force."""
    root = home / "free"
    root.mkdir()
    assert invoke(root, "init", "--require", "python", "--ide", "python-ide", "--creator", CREATOR,
                  "--authorize", "base-image", "default") == 0
    return root


def test_the_fixture_launches_its_required_ide_plainly(project: Path) -> None:
    prepared = prepare_launch(project, RunFlags(), interactive=False)
    assert prepared.selected.resolution["runtime"]["component"] == "pycharm"
    assert prepared.selected.departures == ()
    assert "departures" not in prepared.selected.resolution
    assert "codex" in prepared.selected.lock["components"]


def test_a_conflicting_ide_without_force_is_refused_naming_the_override(project: Path, tmp_path: Path) -> None:
    resolution = checkout_record_paths(load_toml(paths(project)[0]), project)[1]
    before = (shared_bytes(project), record_path(project).read_bytes(), resolution.read_bytes())
    with pytest.raises(ProjectConfigurationError) as refused:
        prepare_launch(project, RunFlags(ide="codium"), interactive=False)
    message = str(refused.value)
    assert "The project requires python-ide (pycharm); frontend-ide (codium) is another IDE" in message
    assert f"run --ide codium --force" in message and str(project) in message
    assert "saved IDE stay as they are" in message
    assert (shared_bytes(project), record_path(project).read_bytes(), resolution.read_bytes()) == before


def test_the_refusal_comes_before_any_materialization_through_the_cli(project: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from devcapsule.commands import project as command_module
    def never(*args, **kwargs):
        raise AssertionError("materialization must not start")
    monkeypatch.setattr(command_module, "realize_environment", never)
    monkeypatch.setattr(command_module, "offer_software_approvals", lambda start: True)
    assert invoke(project, "run", "--ide", "frontend-ide", "--no-update-check") == 2
    assert "--ide frontend-ide --force" in capsys.readouterr().err
    assert invoke(project, "run", "--ide", "codium", "--print-command") == 2
    assert "--ide codium --force" in capsys.readouterr().err


@pytest.mark.parametrize("spelling", ["codium", "frontend-ide"])
def test_force_selects_the_requested_ide_and_keeps_the_rest(project: Path, spelling: str) -> None:
    before = (shared_bytes(project), record_path(project).read_bytes())
    prepared = prepare_launch(project, RunFlags(ide=spelling, force=True), interactive=False)
    selected = prepared.selected
    assert selected.departures == (RequirementDeparture(IDE_REQUIREMENT, "python-ide", "frontend-ide"),)
    components = selected.lock["components"]
    assert components["interactive-surface"] == "codium" and "codium" in components
    assert "pycharm" not in components, "the replaced IDE must not accompany the selected surface"
    assert "codex" in components, "an unrelated mandatory tool is preserved"
    assert selected.resolution["runtime"]["component"] == "codium"
    assert selected.resolution["departures"] == {IDE_REQUIREMENT: {"required": "python-ide", "launched": "frontend-ide"}}
    # The persistent documents are untouched: the requirement, the lock and the saved IDE.
    assert (shared_bytes(project), record_path(project).read_bytes()) == before
    assert CapabilityPolicy.read(selected.manifest).required == ("codex-agent", "python", "python-ide")
    assert LocalCapabilities.read(load_toml(record_path(project))).selected == ("python-ide",)
    # The launch's own copy of the checkout selects the surface; it is in memory only.
    assert LocalCapabilities.read(selected.checkout).selected == ("codex-agent", "frontend-ide") or \
        LocalCapabilities.read(selected.checkout).selected == ("frontend-ide",)


def test_the_launch_listing_shows_the_departure(project: Path) -> None:
    from devcapsule.commands._run_flow import launch_listing_document
    prepared = prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False)
    document = launch_listing_document(prepared.selected)
    assert document["departures"] == [{"policy": IDE_REQUIREMENT, "required": "python-ide", "launched": "frontend-ide"}]
    ide_rows = [row for row in document["rows"] if row["kind"] == "ide"]
    assert ide_rows == [{**ide_rows[0], "name": "frontend-ide",
                         "source": "this launch (--force); the project requires python-ide"}]
    assert ide_rows[0]["effective"].startswith("codium")
    assert any(note.startswith("Departure: the project's required IDE python-ide") for note in document["notes"])
    # The checkout's own listing, as config show reports it, knows no departure.
    plain = launch_listing_document(prepare_launch(project, RunFlags(), interactive=False).selected)
    assert "departures" not in plain and [row["name"] for row in plain["rows"] if row["kind"] == "ide"] == ["python-ide"]


def test_a_following_plain_launch_returns_to_the_required_ide(project: Path) -> None:
    forced = prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False)
    assert tomllib.loads(forced.selected.resolution_path.read_text())["runtime"]["component"] == "codium"
    plain = prepare_launch(project, RunFlags(), interactive=False)
    assert plain.selected.resolution["runtime"]["component"] == "pycharm"
    assert plain.selected.departures == () and "departures" not in plain.selected.resolution
    assert tomllib.loads(plain.selected.resolution_path.read_text())["runtime"]["component"] == "pycharm"


def test_force_never_selects_a_replacement_by_itself(project: Path, free_project: Path) -> None:
    with pytest.raises(ProjectConfigurationError, match="--force names no departure"):
        prepare_launch(project, RunFlags(force=True), interactive=False)
    with pytest.raises(ProjectConfigurationError, match="nothing to set aside: python-ide is the project's required IDE"):
        prepare_launch(project, RunFlags(ide="pycharm", force=True), interactive=False)
    with pytest.raises(ProjectConfigurationError, match="nothing to set aside: the project requires no IDE"):
        prepare_launch(free_project, RunFlags(ide="codium", force=True), interactive=False)


def test_force_with_save_is_refused_before_any_write(project: Path) -> None:
    before = (shared_bytes(project), record_path(project).read_bytes())
    with pytest.raises(ProjectConfigurationError, match="cannot be combined with --save"):
        prepare_launch(project, RunFlags(ide="codium", force=True, save=True), interactive=False)
    assert (shared_bytes(project), record_path(project).read_bytes()) == before


def test_an_override_without_a_requirement_conflict_needs_no_force(free_project: Path) -> None:
    prepared = prepare_launch(free_project, RunFlags(ide="codium"), interactive=False)
    assert prepared.selected.resolution["runtime"]["component"] == "codium"
    assert prepared.selected.departures == ()
    assert LocalCapabilities.read(load_toml(record_path(free_project))).selected == ("python-ide",)


def test_consent_still_blocks_a_forced_launch_and_writes_nothing(project: Path) -> None:
    """Visual Studio Code needs Microsoft's channel accepted; --force does not accept it."""
    resolution = checkout_record_paths(load_toml(paths(project)[0]), project)[1]
    before = (shared_bytes(project), record_path(project).read_bytes(), resolution.read_bytes())
    with pytest.raises(DecisionPending) as pending:
        prepare_launch(project, RunFlags(ide="vscode", force=True), interactive=False)
    assert "vscode" in str(pending.value) and "Nothing was written" in str(pending.value)
    assert (shared_bytes(project), record_path(project).read_bytes(), resolution.read_bytes()) == before
    # Answered at the terminal, the forced launch derives; the acceptance is the home's or the checkout's, never a waiver.
    prompts = io.StringIO()
    prepared = prepare_launch(project, RunFlags(ide="vscode", force=True), interactive=True,
                              input_stream=io.StringIO("y\ny\n"), output_stream=prompts)
    assert prepared.selected.resolution["runtime"]["component"] == "vscode"
    assert prepared.selected.departures == (RequirementDeparture(IDE_REQUIREMENT, "python-ide", "vscode-ide"),)
    assert LocalCapabilities.read(load_toml(record_path(project))).selected == ("python-ide",)


def test_a_real_dependency_on_the_replaced_ide_is_explained_and_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    from devcapsule.components.codex import CodexComponent
    policy = CapabilityPolicy(("codex-agent", "python", "python-ide"))
    shared = tomllib.loads(MATRIX.resolve(["python", "python-ide", "codex-agent"]).render_lock())
    forced = tomllib.loads(MATRIX.resolve(["python", "frontend-ide", "codex-agent"]).render_lock())
    lock = {**shared, "components": {**shared["components"], **forced["components"]}, "materialization": forced["materialization"],
            "capability-providers": {"python": [], "python-ide": ["pycharm"], "codex-agent": ["codex"], "frontend-ide": ["codium"]}}
    local = LocalCapabilities(("frontend-ide",))
    departed = policy.departing((RequirementDeparture(IDE_REQUIREMENT, "python-ide", "frontend-ide"),))
    usable, _ = usable_lock(departed, lock, local)
    assert usable["components"]["interactive-surface"] == "codium" and "pycharm" not in usable["components"]
    monkeypatch.setattr(CodexComponent, "required_components", lambda self: ("pycharm",))
    with pytest.raises(ProjectConfigurationError, match="Capability 'codex-agent' needs pycharm, an IDE that cannot accompany the selected IDE codium"):
        usable_lock(departed, lock, local)


def test_departing_sets_aside_only_the_named_requirement() -> None:
    policy = CapabilityPolicy(("python", "python-ide"), ("browser-automation",), (("python", "3.12"), ("python-ide", "2026")))
    departed = policy.departing((RequirementDeparture(IDE_REQUIREMENT, "python-ide", "frontend-ide"),))
    assert departed == CapabilityPolicy(("python",), ("browser-automation",), (("python", "3.12"),))
    assert policy.departing((RequirementDeparture(IDE_REQUIREMENT, "java-ide", "frontend-ide"),)) is policy
    assert policy.departing(()) is policy


def test_the_cli_carries_force_to_the_plan_and_back_to_the_saved_ide(project: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from tests.test_upgrade_recovery import install_external_fakes
    events: list = []
    launch = install_external_fakes(monkeypatch, events)
    before = (shared_bytes(project), record_path(project).read_bytes())
    assert invoke(project, "run", "--ide", "codium", "--force", "--no-update-check") == 0
    captured = capsys.readouterr()
    assert "WARNING: --force sets aside the project's required IDE python-ide for this launch; frontend-ide (codium) runs" in captured.err
    assert "Not recorded as known-good" in captured.out
    options = launch.call_args.args[0]
    assert options.runtime_plan.component.id == "codium"
    assert options.docker_mode.value == "none"
    assert options.network_mode == "bridge" and not options.enable_sudo
    assert options.display_transport == "contained" and not options.enable_host_browser
    assert "codex" in {item.id for item in options.runtime_plan.ancillary_components}
    assert "pycharm" not in {item.id for item in options.runtime_plan.ancillary_components}
    assert options.launch_configuration.listing["departures"][0]["required"] == "python-ide"
    assert options.launch_configuration.document["running"]["lock"]["components"]["interactive-surface"] == "codium"
    assert (shared_bytes(project), record_path(project).read_bytes()) == before
    assert not history_directory(load_toml(paths(project)[0])).exists(), "a departed launch is no known-good generation"
    assert not (state_directory(project) / "known-good").exists(), "a departed launch proves no version set"
    # The next plain launch is the ordinary one.
    assert invoke(project, "run", "--no-update-check") == 0
    assert launch.call_args.args[0].runtime_plan.component.id == "pycharm"
    assert "WARNING: --force" not in capsys.readouterr().err
    assert (shared_bytes(project), record_path(project).read_bytes()) == before


@pytest.mark.parametrize("ending", ["failed", "interrupted"])
def test_a_failed_or_interrupted_forced_launch_leaves_no_waiver(project: Path, monkeypatch: pytest.MonkeyPatch, ending: str) -> None:
    from tests.test_upgrade_recovery import install_external_fakes
    launch = install_external_fakes(monkeypatch, [])
    before = (shared_bytes(project), record_path(project).read_bytes())
    if ending == "failed":
        launch.side_effect = lambda options: 1
        assert invoke(project, "run", "--ide", "codium", "--force", "--no-update-check") == 1
    else:
        launch.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            invoke(project, "run", "--ide", "codium", "--force", "--no-update-check")
    assert (shared_bytes(project), record_path(project).read_bytes()) == before
    launch.side_effect = lambda options: 0
    assert invoke(project, "run", "--no-update-check") == 0
    assert launch.call_args.args[0].runtime_plan.component.id == "pycharm"


def test_print_command_follows_the_same_override_path(project: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from tests.test_upgrade_recovery import install_external_fakes
    launch = install_external_fakes(monkeypatch, [])
    before = (shared_bytes(project), record_path(project).read_bytes())
    resolution = checkout_record_paths(load_toml(paths(project)[0]), project)[1]
    resolution_before = resolution.read_bytes()
    assert invoke(project, "run", "--ide", "codium", "--print-command") == 2, "the print path refuses the conflict too"
    assert "--ide codium --force" in capsys.readouterr().err
    assert invoke(project, "run", "--ide", "codium", "--force", "--print-command") == 0
    err = capsys.readouterr().err
    assert "WARNING: --force sets aside the project's required IDE python-ide" in err
    assert launch.call_args.args[0].runtime_plan.component.id == "codium"
    assert launch.call_args.args[0].command_report is not None
    assert resolution.read_bytes() == resolution_before
    assert (shared_bytes(project), record_path(project).read_bytes()) == before
    assert invoke(project, "run", "--ide", "codium", "--force", "--save", "--print-command") == 2
    assert "cannot be combined with --save" in capsys.readouterr().err
    assert (shared_bytes(project), record_path(project).read_bytes()) == before


def test_a_saved_conflicting_ide_names_the_override(project: Path) -> None:
    """A checkout whose saved IDE conflicts with a requirement added later is refused with the override named."""
    from devcapsule.configuration.capability_selection import selected_lock
    manifest = load_toml(paths(project)[0])
    shared = load_toml(paths(project)[1])
    checkout = {"capabilities": {"selected": ["frontend-ide"], "lock": MATRIX.resolve(["frontend-ide"]).render_lock()}}
    with pytest.raises(ProjectConfigurationError, match="Local IDE 'frontend-ide' conflicts with the project's required IDE 'python-ide'.*--ide frontend-ide --force"):
        selected_lock(manifest, shared, checkout)


@pytest.mark.parametrize("arguments", [
    ("--ide", "codium"), ("--force",), ("--ide", "pycharm", "--force"),
    ("--ide", "codium", "--force", "--save"),
])
def test_invalid_override_precedes_software_approval_writes(
    project: Path, monkeypatch: pytest.MonkeyPatch, arguments: tuple[str, ...],
) -> None:
    from devcapsule.commands import project as command_module
    from unittest.mock import Mock
    approvals = Mock(return_value=True)
    monkeypatch.setattr(command_module, "offer_software_approvals", approvals)
    before = {path: path.read_bytes() for path in project.parent.rglob("*.toml")}
    assert invoke(project, "run", *arguments, "--no-update-check") == 2
    approvals.assert_not_called()
    assert {path: path.read_bytes() for path in project.parent.rglob("*.toml")} == before


def test_optional_download_retry_keeps_the_departure(
    project: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devcapsule.commands import project as command_module
    from devcapsule.components.catalog import COMPONENTS
    from devcapsule.configuration.capability_commands import configure
    from devcapsule.configuration.storage import ResolvedProject
    from devcapsule.materialization import ArtifactUnavailable
    from tests.test_upgrade_recovery import install_external_fakes

    configure(project, optional=["browser-automation"])
    launch = install_external_fakes(monkeypatch, [])
    realize = command_module.realize_environment
    attempts: list[ResolvedProject] = []

    def retry(selected: ResolvedProject, **kwargs):
        attempts.append(selected)
        if "playwright" in selected.lock["components"]:
            artifact = COMPONENTS["playwright"].locked_artifacts(selected.lock["components"]["playwright"], "linux-amd64")[0]
            raise ArtifactUnavailable(artifact.url, "fixture unavailable")
        return realize(selected, **kwargs)

    monkeypatch.setattr(command_module, "realize_environment", retry)
    before = (shared_bytes(project), record_path(project).read_bytes())
    assert invoke(project, "run", "--ide", "codium", "--force", "--no-update-check") == 0
    assert len(attempts) == 2
    reduced = attempts[-1]
    assert "playwright" not in reduced.lock["components"]
    assert "codex" in reduced.lock["components"] and "pycharm" not in reduced.lock["components"]
    assert reduced.departures == attempts[0].departures
    assert reduced.resolution["departures"] == attempts[0].resolution["departures"]
    assert launch.call_args.args[0].runtime_plan.component.id == "codium"
    assert launch.call_args.args[0].launch_configuration.listing["departures"][0]["required"] == "python-ide"
    assert (shared_bytes(project), record_path(project).read_bytes()) == before
    assert not history_directory(load_toml(paths(project)[0])).exists()
    assert not (state_directory(project) / "known-good").exists()


def test_forced_launch_from_a_saved_version_set(project: Path) -> None:
    from devcapsule.configuration.derivation import load_state
    from devcapsule.configuration.file_formats import canonical_digest, render_toml
    state = load_state(project, load_toml(paths(project)[0]))
    document = load_toml(record_path(project))
    document["version-set"] = {"format": 1, "lock": render_toml(state.composed_lock()),
                               "recommendation-digest": canonical_digest(state.shared_lock)}
    record_path(project).write_text(render_toml(document))
    before = record_path(project).read_bytes()
    selected = prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False).selected
    assert selected.resolution["runtime"]["component"] == "codium"
    assert selected.resolution["departures"][IDE_REQUIREMENT]["required"] == "python-ide"
    assert "pycharm" not in selected.lock["components"]
    assert "codex" in selected.lock["components"]
    assert record_path(project).read_bytes() == before
    assert prepare_launch(project, RunFlags(), interactive=False).selected.resolution["runtime"]["component"] == "pycharm"


def test_checkout_show_after_forced_launch_has_no_departure(project: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import json
    from devcapsule import runtime_configuration
    monkeypatch.setattr(runtime_configuration, "CHANNEL_PATH", project / "no-runtime-channel")
    selected = prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False).selected
    assert "departures" in load_toml(selected.resolution_path)
    capsys.readouterr()
    assert invoke(project, "config", "show", "--json") == 0
    listing = json.loads(capsys.readouterr().out)
    assert "departures" not in listing
    assert [row["name"] for row in listing["rows"] if row["kind"] == "ide"] == ["python-ide"]
    assert "departures" in load_toml(selected.resolution_path), "inspection must not replace the launch plan"


def test_force_can_recover_a_saved_ide_that_conflicts_with_a_later_requirement(
    project: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devcapsule.configuration.file_formats import render_toml
    from tests.test_upgrade_recovery import install_external_fakes
    # This is the record a developer already had when the owner added the requirement.
    selected = prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False, print_only=True).selected
    record_path(project).write_text(render_toml(selected.checkout))
    before = record_path(project).read_bytes()
    launch = install_external_fakes(monkeypatch, [])
    assert invoke(project, "run", "--ide", "codium", "--force", "--no-update-check") == 0
    assert launch.call_args.args[0].runtime_plan.component.id == "codium"
    assert record_path(project).read_bytes() == before
    assert invoke(project, "run", "--no-update-check") == 2, "the unchanged saved choice still conflicts"


@pytest.mark.parametrize("required_ide", ["python-ide", "pycharm"])
def test_departed_minimum_and_canonical_ide_comparison(project: Path, required_ide: str) -> None:
    from devcapsule.configuration.file_formats import render_toml
    manifest_path = paths(project)[0]
    manifest = load_toml(manifest_path)
    manifest["capabilities"]["required"] = ["python>=3", f"{required_ide}>=9999", "codex-agent"]
    manifest_path.write_text(render_toml(manifest))
    with pytest.raises(ProjectConfigurationError, match="nothing to set aside"):
        prepare_launch(project, RunFlags(ide="python-ide", force=True), interactive=False)
    selected = prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False).selected
    assert selected.resolution["runtime"]["component"] == "codium"
    assert selected.resolution["departures"][IDE_REQUIREMENT]["required"] == required_ide
    # Only the IDE's minimum is waived; an impossible Python minimum still refuses.
    manifest["capabilities"]["required"][0] = "python>=9999"
    manifest_path.write_text(render_toml(manifest))
    with pytest.raises(ProjectConfigurationError, match="python.*9999"):
        prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False)


def test_forced_cli_still_requires_the_requested_channel(project: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from tests.test_upgrade_recovery import install_external_fakes
    launch = install_external_fakes(monkeypatch, [])
    before = {path: path.read_bytes() for path in project.parent.rglob("*.toml")}
    assert invoke(project, "run", "--ide", "vscode", "--force", "--no-update-check") == 3
    assert "vscode" in capsys.readouterr().err
    launch.assert_not_called()
    assert {path: path.read_bytes() for path in project.parent.rglob("*.toml")} == before


def test_schema_one_recommendation_accepts_an_unforced_override(project: Path) -> None:
    from devcapsule.configuration.file_formats import render_toml
    manifest_path = paths(project)[0]
    manifest = load_toml(manifest_path)
    manifest["devcapsule-schema-version"] = 1
    manifest["capabilities"] = {"need": ["python", "python-ide", "codex-agent"]}
    manifest_path.write_text(render_toml(manifest))
    before = (shared_bytes(project), record_path(project).read_bytes())
    selected = prepare_launch(project, RunFlags(ide="codium"), interactive=False).selected
    assert selected.resolution["runtime"]["component"] == "codium"
    assert selected.departures == () and "departures" not in selected.resolution
    assert (shared_bytes(project), record_path(project).read_bytes()) == before


def test_forced_launch_does_not_catch_an_artifact_digest_failure(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    from devcapsule.commands import project as command_module
    from devcapsule.materialization import acquire_artifact, ArtifactSpec
    from tests.test_upgrade_recovery import install_external_fakes
    launch = install_external_fakes(monkeypatch, [])
    payload = tmp_path / "bad-artifact"
    payload.write_bytes(b"incorrect artifact bytes")

    def corrupted(selected, **kwargs):
        assert selected.departures and selected.resolution["runtime"]["component"] == "codium"
        return acquire_artifact(ArtifactSpec("1", payload.as_uri(), "a" * 64), tmp_path / "artifacts")

    monkeypatch.setattr(command_module, "realize_environment", corrupted)
    before = (shared_bytes(project), record_path(project).read_bytes())
    assert invoke(project, "run", "--ide", "codium", "--force", "--no-update-check") == 2
    assert "digest mismatch" in capsys.readouterr().err
    launch.assert_not_called()
    assert (shared_bytes(project), record_path(project).read_bytes()) == before
    assert prepare_launch(project, RunFlags(), interactive=False).selected.resolution["runtime"]["component"] == "pycharm"


@pytest.mark.parametrize("sdk_minimum", [False, True])
def test_local_base_minimum_guards_use_the_launch_policy(project: Path, sdk_minimum: bool) -> None:
    from copy import deepcopy
    from dataclasses import replace
    from devcapsule.compat import CliError
    from devcapsule.configuration.model import Configuration
    from devcapsule.environment_realization import realize_environment

    prepared = prepare_launch(project, RunFlags(ide="codium", force=True), interactive=False)
    selected = prepared.selected
    manifest = deepcopy(selected.manifest)
    manifest["capabilities"]["required"] = ["python>=3" if sdk_minimum else "python", "python-ide>=2026", "codex-agent"]
    checkout = deepcopy(selected.checkout)
    checkout["authorization"]["base-image"] = {"reference": "local/base:approved", "image-id": "sha256:" + "a" * 64}

    if sdk_minimum:
        with pytest.raises(ProjectConfigurationError, match="minimum-version guarantee"):
            Configuration(manifest, selected.lock, checkout, prepared.home, departures=selected.departures)
    else:
        configuration = Configuration(manifest, selected.lock, checkout, prepared.home, departures=selected.departures)
        assert configuration.review().ready
        assert configuration.resolve().document()["departures"] == selected.resolution["departures"]

    looked_up: list[str] = []

    def stop_at_lookup(reference: str):
        looked_up.append(reference)
        raise RuntimeError("reached image lookup")

    candidate = replace(selected, manifest=manifest)
    if sdk_minimum:
        with pytest.raises(CliError, match="minimum-version guarantee"):
            realize_environment(candidate, base_override="local/base:approved", obtain_image=stop_at_lookup)
        assert looked_up == []
    else:
        with pytest.raises(RuntimeError, match="reached image lookup"):
            realize_environment(candidate, base_override="local/base:approved", obtain_image=stop_at_lookup)
        assert looked_up == ["local/base:approved"]
