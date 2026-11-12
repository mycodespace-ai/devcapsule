"""Executable policy obligations, using the real catalog and isolated file stores.

Tests assert ownership, mandatory closure, lossless opaque data and transaction
outcomes, rather than how the implementation happens to compute them.
"""
from __future__ import annotations

from tests.launch_preparation import run_until_prepared

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any

import pytest

from devcapsule import cli
from devcapsule.configuration import capability_commands as commands
from devcapsule.configuration.capabilities import CapabilityPolicy, LocalCapabilities
from devcapsule.configuration.capability_selection import generate_lock, selected_lock, usable_lock
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml, render_checkout
from devcapsule.configuration.manifest import current_manifest
from devcapsule.configuration.storage import checkout_record_paths, load_toml, lock_for, manifest_for
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy

MATRIX = MATRICES[Platform.LINUX_AMD64]


def declaration(**capabilities: Any) -> dict[str, Any]:
    return {"devcapsule-schema-version": 1,
            "project": {"creator": "mailto:developer@example.test", "slug": "sample", "name": "Sample", "mount": "/workspace/sample"},
            "capabilities": capabilities}


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "project"
    (root / ".devcapsule").mkdir(parents=True)
    manifest = declaration(need=["python", "python-ide"])
    (root / ".devcapsule/devcapsule.toml").write_text(render_toml(manifest))
    (root / ".devcapsule/devcapsule.linux-amd64.lock").write_text(MATRIX.resolve(["python", "python-ide"]).render_lock())
    return root


def shared_bytes(project: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in (project / ".devcapsule").iterdir() if path.is_file()}


@pytest.mark.parametrize("committed", [False, True])
@pytest.mark.parametrize("lock_bytes", [None, b"", b'# authored lock\r\ndevcapsule-lock-format-version = 1\r\n'])
def test_manifest_only_promotion_recovers_without_touching_lock(
    project: Path, monkeypatch: pytest.MonkeyPatch, committed: bool, lock_bytes: bytes | None,
) -> None:
    manifest_path, lock_path, journal = commands.paths(project)
    if lock_bytes is None:
        lock_path.unlink()
    else:
        lock_path.write_bytes(lock_bytes)
    before = manifest_path.read_bytes()
    from devcapsule.configuration.manifest import current_manifest
    candidate = current_manifest(load_toml(manifest_path), manifest_path).document()
    candidate["recommendations"] = {"cpus": 4}
    real_write = commands.atomic_write

    def interrupted_write(path: Path, content: str, mode: int = 0o600) -> None:
        assert path != lock_path, "a manifest-only edit must not replace the lock"
        if path == manifest_path:
            if committed:
                real_write(path, content, mode)
            raise RuntimeError("simulated interruption")
        real_write(path, content, mode)

    with monkeypatch.context() as patcher:
        patcher.setattr(commands, "atomic_write", interrupted_write)
        with pytest.raises(RuntimeError, match="simulated interruption"):
            commands.promote(project, candidate)
    assert journal.exists()
    commands.recover(project)
    commands.recover(project)
    assert not journal.exists()
    assert (lock_path.read_bytes() if lock_path.exists() else None) == lock_bytes
    if committed:
        assert load_toml(manifest_path) == candidate
    else:
        assert manifest_path.read_bytes() == before


def test_manifest_only_promotion_keeps_crlf_lock_bytes(project: Path) -> None:
    manifest_path, lock_path, journal = commands.paths(project)
    original = lock_path.read_bytes().replace(b"\n", b"\r\n")
    lock_path.write_bytes(original)
    commands.promote(project, current_manifest(load_toml(manifest_path), manifest_path).document())
    assert lock_path.read_bytes() == original
    assert not journal.exists()


@pytest.mark.parametrize("value", [None, "python", 3, [None], [3], [""], [" python"], ["python\x00"], {}])
def test_invalid_required_names_are_never_admitted(value: object) -> None:
    with pytest.raises(ProjectConfigurationError, match="array"):
        CapabilityPolicy.read(declaration(required=value))


@pytest.mark.parametrize("values", [
    {"need": [], "required": []},
    {"required": ["python"], "optional": ["python"]},
])
def test_ambiguous_or_invalid_policy_is_refused(values: dict[str, Any]) -> None:
    with pytest.raises(ProjectConfigurationError):
        CapabilityPolicy.read(declaration(**values))


def test_normalization_keeps_unknown_optional_intent() -> None:
    policy = CapabilityPolicy.read(declaration(required=["python", "python"], optional=["future-tool"], **{"sdk-major": {"python": 3}}))
    assert policy.document() == {"required": ["python"], "optional": ["future-tool"]}
    assert CapabilityPolicy.read({"capabilities": policy.document()}) == policy


@pytest.mark.parametrize("value", [
    {"unknown": []}, {"selected": ["python"], "without": ["python"]},
    {"lock": 4}, {"selected": "python"}, {"without": [False]},
])
def test_invalid_local_selections_are_refused(value: dict[str, Any]) -> None:
    with pytest.raises(ProjectConfigurationError):
        LocalCapabilities.read({"capabilities": value})


def test_required_and_optional_are_independent_of_locality() -> None:
    policy = CapabilityPolicy(("python",), ("browser-automation",), (("python", "3"),))
    lock = generate_lock(policy, MATRIX)
    assert "interactive-surface" not in lock["components"]
    assert set(lock["components"]) == {"playwright"}
    assert lock["capability-providers"] == {"python": [], "browser-automation": ["playwright"]}
    checkout = {"capabilities": {"selected": ["python-ide", "codex-agent"],
                                "lock": MATRIX.resolve(["python-ide", "codex-agent"]).render_lock()}}
    manifest = declaration(**policy.document())
    before = deepcopy((manifest, lock, checkout))
    effective = selected_lock(manifest, lock, checkout)
    assert set(effective["components"]) == {"interactive-surface", "pycharm", "codex", "playwright"}
    assert (manifest, lock, checkout) == before


def test_unknown_optional_provider_is_removed_without_altering_shared_input() -> None:
    policy = CapabilityPolicy(("python",), ("future-tool",))
    lock = tomllib.loads(MATRIX.resolve(["python", "python-ide"]).render_lock())
    lock["components"]["future"] = {"version": "500", "opaque": {"new-field": [1, 2]}}
    lock["capability-providers"] = {"python": [], "future-tool": ["future"]}
    before = deepcopy(lock)
    result, warnings = usable_lock(policy, lock, LocalCapabilities(("python-ide",)))
    assert set(result["components"]) == {"interactive-surface", "pycharm"}
    assert len(warnings) == 1 and "future-tool" in warnings[0] and "does not support" in warnings[0]
    assert lock == before
    regenerated = generate_lock(policy, MATRIX, previous=lock)
    assert regenerated["components"]["future"] == before["components"]["future"]
    assert regenerated["capability-providers"]["future-tool"] == ["future"]


@pytest.mark.parametrize("required,optional", [(["future-tool"], []), (["python"], ["future-tool"])])
def test_writers_cannot_introduce_unknown_names(required: list[str], optional: list[str]) -> None:
    with pytest.raises(ProjectConfigurationError):
        generate_lock(CapabilityPolicy(tuple(required), tuple(optional)), MATRIX)


def test_missing_required_provider_fails_but_optional_provider_warns() -> None:
    lock = generate_lock(CapabilityPolicy(("python",)), MATRIX)
    result, warnings = usable_lock(CapabilityPolicy(("python",), ("browser-automation",)), lock)
    assert warnings and "playwright" in warnings[0]
    assert result["components"] == {}
    with pytest.raises(ProjectConfigurationError, match="Required capability.*browser-automation"):
        usable_lock(CapabilityPolicy(("python", "browser-automation")), lock)


def test_omitting_optional_sdk_cannot_remove_mandatory_dependency() -> None:
    policy = CapabilityPolicy(("dotnet-ide",), ("dotnet",))
    lock = generate_lock(policy, MATRIX)
    result, _ = usable_lock(policy, lock, LocalCapabilities(without=("dotnet",)))
    assert "dotnet-sdk" in result["components"]  # Rider's mandatory dependency wins.
    del lock["components"]["dotnet-sdk"]
    with pytest.raises(ProjectConfigurationError, match="Required capability.*dotnet-ide"):
        usable_lock(policy, lock, LocalCapabilities(without=("dotnet",)))


@pytest.mark.parametrize("minimum", ["3.14", "4"])
def test_python_minimum_is_a_hard_constraint(minimum: str) -> None:
    with pytest.raises(ProjectConfigurationError, match=f"python {minimum} or newer"):
        generate_lock(CapabilityPolicy(("python",), minimums=(("python", minimum),)), MATRIX)


def test_unknown_base_cannot_claim_a_required_sdk() -> None:
    policy = CapabilityPolicy(("python",), minimums=(("python", "3"),))
    lock = generate_lock(policy, MATRIX)
    lock["base"]["reference"] = "example.invalid/base@sha256:" + "a" * 64
    with pytest.raises(ProjectConfigurationError, match="selected base cannot establish"):
        usable_lock(policy, lock)


def test_legacy_lock_is_not_re_resolved() -> None:
    lock = {"resolution-matrix-version": "embedded-18", "opaque": {"old": True}}
    actual, warnings = usable_lock(CapabilityPolicy(("python-ide",)), lock)
    assert actual == lock and actual is not lock and not warnings


def test_personal_pins_do_not_make_a_composed_legacy_lock_current() -> None:
    from devcapsule.configuration.capability_selection import compose_lock
    from devcapsule.configuration.fingerprints import resolution_source_digests
    from devcapsule.configuration.manifest import current_manifest
    from tests.test_upgrade_recovery import FIXTURE
    root = FIXTURE / "project/.devcapsule"
    manifest = current_manifest(load_toml(root / "devcapsule.toml"), "fixture").document()
    shared = load_toml(root / "devcapsule.linux-amd64.lock")
    checkout = {"capabilities": {"selected": ["codex-agent"],
                                "lock": MATRIX.resolve(["python-ide", "codex-agent"]).render_lock()}}
    before = deepcopy((manifest, shared, checkout))
    composed = compose_lock(manifest, shared, checkout)
    assert composed["resolution-matrix-version"] == shared["resolution-matrix-version"]
    assert composed["capability-providers"] == {"codex-agent": ["codex"]}
    actual, warnings = usable_lock(CapabilityPolicy.read(manifest), composed, LocalCapabilities.read(checkout))
    assert actual == composed and not warnings
    assert "capability-baseline" not in resolution_source_digests(manifest, composed, checkout)
    assert (manifest, shared, checkout) == before


@pytest.mark.parametrize("version", ["vendor-v1", "embedded-next"])
def test_unrecognized_matrix_version_cannot_hide_a_missing_requirement(version: str) -> None:
    lock = generate_lock(CapabilityPolicy(("python",)), MATRIX)
    lock["resolution-matrix-version"] = version
    with pytest.raises(ProjectConfigurationError, match="Required capability 'browser-automation'.*playwright"):
        usable_lock(CapabilityPolicy(("python", "browser-automation")), lock)


@pytest.mark.parametrize("pinned", ["pycharm", "absent-ide"])
def test_pinned_ide_is_kept_only_when_its_provider_is_present(pinned: str) -> None:
    lock = generate_lock(CapabilityPolicy(("python",)), MATRIX)
    lock["components"]["interactive-surface"] = pinned
    actual, _ = usable_lock(CapabilityPolicy(("python",)), lock)
    assert actual["components"] == {}


def test_retaining_a_pinned_ide_does_not_waive_a_missing_requirement() -> None:
    lock = generate_lock(CapabilityPolicy(("python", "python-ide")), MATRIX)
    actual, _ = usable_lock(CapabilityPolicy(("python",)), lock)
    assert actual["components"]["interactive-surface"] == "pycharm"
    assert actual["components"]["pycharm"] == lock["components"]["pycharm"]
    with pytest.raises(ProjectConfigurationError, match="Required capability 'browser-automation'.*playwright"):
        usable_lock(CapabilityPolicy(("python", "browser-automation")), lock)


def test_command_migration_and_personal_choices_preserve_ownership(project: Path) -> None:
    commands.configure(project, required=["python"], optional=["browser-automation"])
    shared = shared_bytes(project)
    commands.configure(project, local=["python-ide", "codex-agent"], without=["browser-automation"])
    assert shared_bytes(project) == shared
    manifest = load_toml(project / ".devcapsule/devcapsule.toml")
    _, lock = lock_for(project, manifest)
    assert set(lock["components"]) == {"interactive-surface", "pycharm", "codex"}
    commands.configure(project, local=["eclipse-ide"], without=[])
    _, lock = lock_for(project, manifest)
    assert set(lock["components"]) == {"interactive-surface", "eclipse", "playwright"}
    assert shared_bytes(project) == shared


@pytest.mark.parametrize("kwargs", [
    {"required": ["python>=4"]},
    {"optional": ["unknown"]},
    {"required": ["python"], "local": ["python-ide"]}, {},
    {"required": ["python>=3", "python>=4"]}, {"required": ["python>=x"]},
    {"without": ["python"]}, {"local": ["unknown"]},
])
def test_rejected_edits_leave_all_shared_bytes_intact(project: Path, kwargs: dict[str, Any]) -> None:
    before = shared_bytes(project)
    with pytest.raises(ProjectConfigurationError):
        commands.configure(project, **kwargs)
    assert shared_bytes(project) == before


def test_check_and_preview_never_register_or_write(project: Path) -> None:
    before = shared_bytes(project)
    assert "valid" in commands.check(project)
    assert "Preview" in commands.configure(project, required=["python"], preview=True)
    assert "Preview" in commands.configure(project, local=["codex-agent"], preview=True)
    assert shared_bytes(project) == before
    manifest = load_toml(project / ".devcapsule/devcapsule.toml")
    assert not checkout_record_paths(manifest, project)[0].exists()


@pytest.mark.parametrize("committed", [False, True])
def test_interrupted_shared_edit_recovers_to_one_complete_endpoint(project: Path, committed: bool) -> None:
    manifest_path, lock_path, journal = commands.paths(project)
    before_manifest, before_lock = manifest_path.read_text(), lock_path.read_text()
    new_manifest = declaration(required=["python"])
    new_lock = generate_lock(CapabilityPolicy.read(new_manifest), MATRIX)
    after_manifest, after_lock = render_toml(new_manifest), render_toml(new_lock)
    journal.write_text(render_toml({"before-manifest": before_manifest, "before-lock": before_lock,
                                       "after-manifest": after_manifest, "after-lock": after_lock}))
    lock_path.write_text(after_lock)
    if committed:
        manifest_path.write_text(after_manifest)
    with pytest.raises(ProjectConfigurationError, match="Interrupted"):
        commands.check(project)
    commands.recover(project)
    assert manifest_path.read_text() == (after_manifest if committed else before_manifest)
    assert lock_path.read_text() == (after_lock if committed else before_lock)
    assert not journal.exists()
    commands.recover(project)  # idempotent


def test_io_failure_before_commit_rolls_back(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before = shared_bytes(project)
    real_write = commands.atomic_write
    def fail_manifest(path: Path, content: str, *, mode: int = 0o600) -> None:
        if path.name == "devcapsule.toml":
            raise OSError("injected disk failure")
        real_write(path, content, mode=mode)
    monkeypatch.setattr(commands, "atomic_write", fail_manifest)
    with pytest.raises(OSError, match="injected"):
        commands.configure(project, required=["python"])
    assert shared_bytes(project) == before


def test_cli_check_and_capability_mutation(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    prefix = ["project", "--path", str(project), "config"]
    assert cli.main([*prefix, "check"]) == 3  # the base consent is pending
    assert cli.main([*prefix, "require", "python"]) == 0
    assert cli.main([*prefix, "ide", "python-ide"]) == 0
    assert cli.main([*prefix, "capabilities", "--recover"]) == 0


def prepare_launch(project: Path) -> None:
    prefix = ["project", "--path", str(project), "config"]
    assert cli.main([*prefix, "authorize", "base-image", "default"]) == 0
    assert cli.main([*prefix, "authorize", "host-x11", "false"]) == 0
    assert run_until_prepared(project) == 0


def test_optional_only_contribution_does_not_block_next_launch(project: Path) -> None:
    from devcapsule.configuration.execution import ExecutionConfiguration
    commands.configure(project, required=["python"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    before = ExecutionConfiguration.load(project).project
    manifest_path, lock_path, _ = commands.paths(project)
    # A fixture authored by a hypothetical newer contributor/launcher.
    manifest, lock = load_toml(manifest_path), load_toml(lock_path)
    manifest["capabilities"]["optional"] = ["future-tool"]
    lock["components"]["future"] = {"version": "500"}
    lock["capability-providers"]["future-tool"] = ["future"]
    manifest_path.write_text(render_toml(manifest))
    lock_path.write_text(render_toml(lock))
    shared = shared_bytes(project)
    after = ExecutionConfiguration.load(project).project
    assert after.lock["components"] == before.lock["components"]
    assert after.resolution["runtime"] == before.resolution["runtime"]
    assert shared_bytes(project) == shared
    # Required changes are not blessed by that optional-only reconciliation.
    manifest["capabilities"]["required"] = ["python>=4"]
    manifest_path.write_text(render_toml(manifest))
    with pytest.raises(ProjectConfigurationError, match="python>=4"):
        ExecutionConfiguration.load(project)


def test_local_answers_still_require_explicit_resolution(project: Path) -> None:
    from devcapsule.configuration.execution import ExecutionConfiguration
    commands.configure(project, required=["python"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    assert cli.main(["project", "--path", str(project), "config", "authorize", "development-sudo", "true"]) == 0
    with pytest.raises(ProjectConfigurationError, match="stale"):
        ExecutionConfiguration.load(project)


def test_new_project_creation_has_no_implicit_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "fresh"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--require", "python", "--offer", "browser-automation",
                     "--ide", "eclipse-ide", "--creator", "mailto:owner@example.test",
                     "--authorize", "base-image", "default"]) == 0
    manifest, lock = load_toml(commands.paths(root)[0]), load_toml(commands.paths(root)[1])
    assert manifest["capabilities"] == {"required": ["python"], "optional": ["browser-automation"]}
    assert set(lock["components"]) == {"playwright"}
    assert set(lock_for(root, manifest)[1]["components"]) == {"interactive-surface", "eclipse", "playwright"}
    assert cli.main(["project", "--path", str(root), "init"]) != 0
    assert cli.main(["project", "--path", str(root), "config", "need", "node"]) != 0


@pytest.mark.parametrize("arguments", [
    {"creator": None}, {"require": ("python-ide",)}, {"require": ("python=0",)},
    {"agents": ("unknown",)}, {"project_mount": "relative/path"},
])
def test_new_project_failure_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arguments: dict[str, Any]) -> None:
    from devcapsule.compat import CliError
    from devcapsule.configuration.operations import InitializeRequest, initialize_project
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "fresh"
    root.mkdir()
    kwargs: dict[str, Any] = dict(directory=root, creator="mailto:owner@example.test", require=("python",), interactive=False)
    kwargs.update(arguments)
    with pytest.raises(CliError):
        initialize_project(InitializeRequest(**kwargs))
    assert list(root.iterdir()) == []
    assert not (tmp_path / "config").exists()


def test_local_reselection_retains_unrelated_version_pins(project: Path) -> None:
    from devcapsule.configuration.file_formats import canonical_digest, selected_version_lock
    commands.configure(project, required=["python"], optional=["browser-automation"])
    commands.configure(project, local=["python-ide", "codex-agent"])
    manifest = load_toml(commands.paths(project)[0])
    input_path, _ = checkout_record_paths(manifest, project)
    checkout = load_toml(input_path)
    lock = lock_for(project, manifest)[1]
    lock["components"]["playwright"]["version"] = "fixture-local-pin"
    lock["components"]["codex"]["version"] = "fixture-agent-pin"
    checkout["version-set"] = {"format": 1, "lock": render_toml(lock), "recommendation-digest": canonical_digest(load_toml(commands.paths(project)[1]))}
    input_path.write_text(render_toml(checkout))
    before = shared_bytes(project)
    commands.configure(project, local=["eclipse-ide", "codex-agent"])
    selected = selected_version_lock(load_toml(input_path))
    assert selected is not None
    assert selected["components"]["playwright"]["version"] == "fixture-local-pin"
    assert selected["components"]["codex"]["version"] == "fixture-agent-pin"
    assert "pycharm" not in selected["components"]
    assert shared_bytes(project) == before


@pytest.mark.parametrize("fault", ["malformed", "manifest-conflict", "lock-conflict"])
def test_recovery_never_overwrites_independent_edits(project: Path, fault: str) -> None:
    manifest, lock, journal = commands.paths(project)
    values = {"before-manifest": manifest.read_text(), "after-manifest": "candidate-manifest",
              "before-lock": lock.read_text(), "after-lock": "candidate-lock"}
    if fault == "malformed":
        values = {"something-else": "unknown"}
    if fault == "manifest-conflict":
        manifest.write_text("independent edit")
    if fault == "lock-conflict":
        lock.write_text("independent lock")
    journal.write_text(render_toml(values))
    before = shared_bytes(project)
    with pytest.raises(ProjectConfigurationError):
        commands.recover(project)
    assert shared_bytes(project) == before


def test_recovery_of_interrupted_initial_creation(tmp_path: Path) -> None:
    root = tmp_path / "fresh"
    (root / ".devcapsule").mkdir(parents=True)
    manifest, lock, journal = commands.paths(root)
    lock.write_text("candidate-lock")
    journal.write_text(render_toml({"before-manifest": "", "before-lock": "",
                                       "after-manifest": "candidate-manifest", "after-lock": "candidate-lock"}))
    assert cli.main(["project", "--path", str(root), "config", "capabilities", "--recover"]) == 0
    assert not lock.exists() and not manifest.exists() and not journal.exists()


@pytest.mark.parametrize("record", [{}, {"lock": "[bad"}, {"lock": "[components]\n"}])
def test_incomplete_local_pins_are_actionable(project: Path, record: dict[str, Any]) -> None:
    commands.configure(project, required=["python"])
    manifest, lock = load_toml(commands.paths(project)[0]), load_toml(commands.paths(project)[1])
    with pytest.raises(ProjectConfigurationError, match="pins|provider"):
        selected_lock(manifest, lock, {"capabilities": {"selected": ["python-ide"], **record}})


def test_a_local_ide_replaces_the_ide_a_legacy_need_list_recommends(project: Path) -> None:
    # The IDE in a schema-1 ``need`` list reads as the project's recommendation
    # (manifest_schemas.upgrade); each developer may choose another.
    commands.configure(project, local=["eclipse-ide"])
    _, manifest = manifest_for(project)
    assert manifest["recommendations"]["ide"] == "python-ide"
    assert lock_for(project, manifest)[1]["components"]["interactive-surface"] == "eclipse"


def test_wrong_lock_platform_is_refused() -> None:
    with pytest.raises(ProjectConfigurationError, match="Unsupported lock platform"):
        usable_lock(CapabilityPolicy(("python",)),
                    {"resolution-matrix-version": "embedded-28", "capability-providers": {}, "platform": "unknown"})


def test_supplied_versions_are_explicit() -> None:
    lock = tomllib.loads(MATRIX.resolve(["dotnet-ide"]).render_lock())
    assert MATRIX.supplied_version("dotnet", lock) == "10.0.401"
    assert MATRIX.supplied_version("java", lock) == "25.0.4+7"
    assert MATRIX.supplied_version("docker-cli", lock) is None


def test_cannot_preserve_missing_opaque_optional_provider() -> None:
    with pytest.raises(ProjectConfigurationError, match="conflicts or is missing"):
        generate_lock(CapabilityPolicy(("python",), ("future",)), MATRIX,
                      previous={"capability-providers": {"future": ["missing"]}})


def test_choose_local_ide_before_resolving_required_only_project(project: Path) -> None:
    commands.configure(project, required=["python"])
    with pytest.raises(ProjectConfigurationError, match="Choose your IDE"):
        lock_for(project, load_toml(commands.paths(project)[0]))


def test_pending_local_activation_is_not_overwritten(project: Path) -> None:
    manifest = load_toml(commands.paths(project)[0])
    record, _ = checkout_record_paths(manifest, project)
    record.parent.mkdir(parents=True)
    record.with_suffix(".activation.toml").write_text("pending")
    with pytest.raises(ProjectConfigurationError, match="activation needs recovery"):
        commands.configure(project, local=["codex-agent"])


def test_local_base_cannot_claim_minimum_guarantee(project: Path) -> None:
    from devcapsule.configuration.model import Configuration
    commands.configure(project, required=["python>=3"])
    commands.configure(project, local=["python-ide"])
    manifest = load_toml(commands.paths(project)[0])
    checkout = load_toml(checkout_record_paths(manifest, project)[0])
    checkout["authorization"] = {"base-image": {"image-id": "sha256:" + "a" * 64}}
    with pytest.raises(ProjectConfigurationError, match="local base override"):
        Configuration(manifest, lock_for(project, manifest)[1], checkout)


def test_optional_download_failure_reduces_only_this_run(project: Path) -> None:
    from devcapsule.configuration.execution import ExecutionConfiguration
    from devcapsule.environment_realization import omit_unavailable_optional
    commands.configure(project, required=["python"], optional=["browser-automation"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    selected = ExecutionConfiguration.load(project).project
    before = deepcopy(selected)
    from devcapsule.components.catalog import COMPONENTS
    url = COMPONENTS["playwright"].locked_artifacts(selected.lock["components"]["playwright"], "linux-amd64")[0].url
    smaller = omit_unavailable_optional(selected, url)
    assert smaller is not None
    assert "playwright" not in smaller.lock["components"]
    assert smaller.checkout["capabilities"]["without"] == ["browser-automation"]
    assert selected == before
    assert "playwright" in ExecutionConfiguration.load(project).project.lock["components"]
    assert omit_unavailable_optional(selected, "https://unknown.invalid/file") is None


def test_required_download_and_digest_errors_are_not_optional(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from devcapsule.configuration.execution import ExecutionConfiguration
    from devcapsule.environment_realization import omit_unavailable_optional
    from devcapsule.materialization import acquire_artifact, ArtifactSpec, ArtifactUnavailable
    from devcapsule.compat import CliError
    from urllib.error import URLError
    commands.configure(project, required=["python"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    selected = ExecutionConfiguration.load(project).project
    assert omit_unavailable_optional(selected, "any-url") is None
    payload = tmp_path / "payload"
    payload.write_bytes(b"wrong hash")
    with pytest.raises(CliError, match="digest mismatch") as error:
        acquire_artifact(ArtifactSpec("1", payload.as_uri(), "a" * 64), tmp_path / "cache")
    assert not isinstance(error.value, ArtifactUnavailable)
    def unavailable(*args: Any, **kwargs: Any) -> None:
        raise URLError("offline")
    monkeypatch.setattr("devcapsule.materialization.urlopen", unavailable)
    with pytest.raises(ArtifactUnavailable) as download:
        acquire_artifact(ArtifactSpec("1", "https://fixture.invalid/file", "b" * 64), tmp_path / "cache")
    assert download.value.url == "https://fixture.invalid/file"


def test_project_run_retries_optional_download_without_certifying_full_set(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from devcapsule.commands import project as command_module
    from devcapsule.materialization import ArtifactUnavailable, ImageDetails, parse_locked_environment
    from devcapsule.components.catalog import COMPONENTS
    commands.configure(project, required=["python"], optional=["browser-automation"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    shared = shared_bytes(project)
    realized_sets: list[set[str]] = []
    launches: list[Any] = []
    def realize(selected: Any, **kwargs: Any) -> Any:
        realized_sets.append(set(selected.lock["components"]))
        if "playwright" in selected.lock["components"]:
            url = COMPONENTS["playwright"].locked_artifacts(selected.lock["components"]["playwright"], "linux-amd64")[0].url
            raise ArtifactUnavailable(url, "fixture unavailable")
        return SimpleNamespace(image=ImageDetails("fixture/image", "sha256:" + "a" * 64, {"devcapsule.base.display": "contained"}, "linux", "amd64"),
                               locked=parse_locked_environment(selected.lock), created=False)
    def launch(options: Any) -> int:
        launches.append(options)
        return 0
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("A reduced run must not certify the full stored configuration")
    monkeypatch.setattr(command_module, "realize_environment", realize)
    monkeypatch.setattr(command_module, "offer_upgrades", lambda *args, **kwargs: True)
    monkeypatch.setattr(command_module, "run_pycharm", launch)
    monkeypatch.setattr(command_module, "record_known_good_configuration", forbidden)
    assert cli.main(["project", "--path", str(project), "run", "--no-update-check"]) == 0
    assert len(realized_sets) == 2 and "playwright" not in realized_sets[-1]
    assert len(launches) == 1
    assert shared_bytes(project) == shared


def test_run_does_not_degrade_required_download_failure(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from devcapsule.commands import project as command_module
    from devcapsule.materialization import ArtifactUnavailable
    commands.configure(project, required=["python"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    def unavailable(*args: Any, **kwargs: Any) -> None:
        raise ArtifactUnavailable("https://fixture.invalid/ide", "offline")
    monkeypatch.setattr(command_module, "realize_environment", unavailable)
    monkeypatch.setattr(command_module, "offer_upgrades", lambda *args, **kwargs: True)
    assert cli.main(["project", "--path", str(project), "run", "--no-update-check"]) != 0


def test_init_without_an_ide_leaves_the_checkout_waiting_for_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "fresh"
    root.mkdir()
    prefix = ["project", "--path", str(root), "init"]
    assert cli.main([*prefix, "--ide", "python-ide"]) != 0  # no creator
    assert cli.main([*prefix, "--require", "python", "--creator", "mailto:owner@example.test"]) == 0
    out = capsys.readouterr().out
    assert "no IDE or personal capability selected yet" in out and "Choose your IDE" in out
    assert commands.check(root).startswith("Configuration contract valid")
    from devcapsule.configuration.operations import InitializeRequest, initialize_project
    with pytest.raises(ProjectConfigurationError, match="does not exist"):
        initialize_project(InitializeRequest(directory=root / "absent", creator="x", interactive=False))


def test_a_local_ide_overlays_the_surface_a_legacy_lock_pinned() -> None:
    manifest = current_manifest(declaration(need=["python", "python-ide"]), "manifest").document()
    shared = tomllib.loads(MATRIX.resolve(["python", "python-ide"]).render_lock())
    checkout = {"capabilities": {"selected": ["eclipse-ide"], "lock": MATRIX.resolve(["eclipse-ide"]).render_lock()}}
    assert selected_lock(manifest, shared, checkout)["components"]["interactive-surface"] == "eclipse"


def test_a_hand_written_required_ide_still_refuses_a_conflicting_local_ide() -> None:
    manifest = declaration(required=["python", "python-ide"])
    manifest["devcapsule-schema-version"] = 2
    shared = tomllib.loads(MATRIX.resolve(["python", "python-ide"]).render_lock())
    checkout = {"capabilities": {"selected": ["eclipse-ide"], "lock": MATRIX.resolve(["eclipse-ide"]).render_lock()}}
    with pytest.raises(ProjectConfigurationError, match="Local IDE 'eclipse-ide' conflicts with the project's required IDE 'python-ide'.*--ide eclipse-ide --force"):
        selected_lock(manifest, shared, checkout)


def test_local_tools_without_an_ide_preserve_shared_ide(project: Path) -> None:
    commands.configure(project, local=["codex-agent"])
    _, manifest = manifest_for(project)
    assert lock_for(project, manifest)[1]["components"]["interactive-surface"] == "pycharm"
    commands.configure(project, local=[])
    assert "codex" not in lock_for(project, manifest)[1]["components"]


def test_wrong_platform_local_version_set_is_refused(project: Path) -> None:
    manifest = load_toml(commands.paths(project)[0])
    record, _ = checkout_record_paths(manifest, project)
    checkout = tomllib.loads(render_checkout(manifest, project, {}, {}))
    lock = load_toml(commands.paths(project)[1])
    lock["platform"] = "other-platform"
    checkout["version-set"] = {"format": 1, "lock": render_toml(lock), "recommendation-digest": "fixture"}
    record.parent.mkdir(parents=True)
    record.write_text(render_toml(checkout))
    with pytest.raises(ProjectConfigurationError, match="another platform"):
        lock_for(project, manifest)


def test_baseline_evidence_must_cover_required_capabilities() -> None:
    from devcapsule.configuration.fingerprints import resolution_source_digests
    manifest = declaration(required=["python"])
    manifest["devcapsule-schema-version"] = 2
    with pytest.raises(ProjectConfigurationError, match="provider evidence is incomplete"):
        resolution_source_digests(manifest, {"resolution-matrix-version": "embedded-28", "capability-providers": {}, "components": {}}, {})


def test_base_override_cannot_bypass_minimum_constraint(project: Path) -> None:
    from devcapsule.configuration.execution import ExecutionConfiguration
    from devcapsule.environment_realization import realize_environment
    from devcapsule.compat import CliError
    commands.configure(project, required=["python>=3"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    selected = ExecutionConfiguration.load(project).project
    with pytest.raises(CliError, match="minimum-version guarantee"):
        realize_environment(selected, base_override="unverified/local:base")
    def stop_at_obtain(reference: str) -> Any:
        raise RuntimeError("reached image lookup")
    with pytest.raises(RuntimeError, match="reached image lookup"):
        realize_environment(selected, base_override=selected.lock["base"]["reference"], obtain_image=stop_at_obtain)


def test_required_dependency_download_is_never_omitted(project: Path) -> None:
    from devcapsule.configuration.execution import ExecutionConfiguration
    from devcapsule.environment_realization import omit_unavailable_optional
    from devcapsule.components.catalog import COMPONENTS
    commands.configure(project, required=["python", "browser-automation"], optional=["postgresql-client"])
    commands.configure(project, local=["python-ide"])
    prepare_launch(project)
    selected = ExecutionConfiguration.load(project).project
    url = COMPONENTS["playwright"].locked_artifacts(selected.lock["components"]["playwright"], "linux-amd64")[0].url
    assert omit_unavailable_optional(selected, url) is None
    # An artifact with no optional declaration is never silently waived either.
    selected.lock["components"]["codex"] = tomllib.loads(MATRIX.resolve(["python-ide", "codex-agent"]).render_lock())["components"]["codex"]
    url = COMPONENTS["codex"].locked_artifacts(selected.lock["components"]["codex"], "linux-amd64")[0].url
    assert omit_unavailable_optional(selected, url) is None


def test_removing_a_local_licensed_agent_retains_inactive_consent(project: Path) -> None:
    from devcapsule.configuration.authorization import authorization_declarations
    from devcapsule.configuration.execution import ExecutionConfiguration
    commands.configure(project, required=["python"])
    commands.configure(project, local=["python-ide", "claude-code-agent"])
    manifest = load_toml(commands.paths(project)[0])
    lock = lock_for(project, manifest)[1]
    acquisitions = [entry.name for entry in authorization_declarations(manifest, lock).values() if entry.kind == "acquisition"]
    assert acquisitions
    for name in acquisitions:
        assert cli.main(["project", "--path", str(project), "config", "authorize", name, "true"]) == 0
    prepare_launch(project)
    record = checkout_record_paths(manifest, project)[0]
    consent = deepcopy(load_toml(record)["authorization"])
    commands.configure(project, local=["python-ide"])
    assert run_until_prepared(project) == 0
    ExecutionConfiguration.load(project)
    assert load_toml(record)["authorization"] == consent


@pytest.mark.parametrize("changes,message", [
    ({"artifact_format": "unknown"}, "artifact format"),
    ({"artifact_format": "tar-gz-member"}, "archive member"),
    ({"artifact_format": "npm-package"}, "npm package"),
    ({"destination": "relative/path"}, "absolute"),
    ({"sha256": "invalid"}, "SHA-256"),
])
def test_offline_artifact_validation_protects_every_capability(changes: dict[str, Any], message: str) -> None:
    from dataclasses import replace
    from devcapsule.components.interface import LockedArtifactDeclaration
    from devcapsule.materialization import validate_locked_artifact
    from devcapsule.compat import CliError
    artifact = LockedArtifactDeclaration("example", "1", "https://example.test/a.tar.gz", "a" * 64, "/opt/tool", artifact_format="file")
    with pytest.raises(CliError, match=message):
        validate_locked_artifact(replace(artifact, **changes))


def test_check_rejects_corrupt_optional_pin_without_writing(project: Path) -> None:
    from devcapsule.compat import CliError
    commands.configure(project, required=["python"], optional=["dotnet"])
    manifest, lock, _ = commands.paths(project)
    candidate = load_toml(lock)
    candidate["components"]["dotnet-sdk"]["sha256"] = "invalid"
    candidate_path = project / "candidate.lock"
    candidate_path.write_text(render_toml(candidate))
    before = shared_bytes(project)
    with pytest.raises(CliError, match="SHA-256"):
        commands.check(project, manifest_path=manifest, lock_path=candidate_path)
    assert shared_bytes(project) == before


def test_omitting_then_restoring_an_optional_keeps_the_version_set_pin(project: Path) -> None:
    from devcapsule.configuration.file_formats import canonical_digest, selected_version_lock
    commands.configure(project, required=["python"], optional=["browser-automation"])
    commands.configure(project, local=["python-ide"])
    manifest = load_toml(commands.paths(project)[0])
    input_path, _ = checkout_record_paths(manifest, project)
    checkout = load_toml(input_path)
    lock = lock_for(project, manifest)[1]
    lock["components"]["playwright"]["version"] = "fixture-local-pin"
    checkout["version-set"] = {"format": 1, "lock": render_toml(lock), "recommendation-digest": canonical_digest(load_toml(commands.paths(project)[1]))}
    checkout["authorization"] = {"host-x11": {"value": False, "recommendation-digest": "fixture"}}
    input_path.write_text(render_toml(checkout))
    before = shared_bytes(project)
    commands.configure(project, without=["browser-automation"])
    assert "playwright" not in lock_for(project, manifest)[1]["components"]
    selected = selected_version_lock(load_toml(input_path))
    assert selected is not None
    assert selected["components"]["playwright"]["version"] == "fixture-local-pin"  # persistent intent survives the omission
    commands.configure(project, without=[])
    assert lock_for(project, manifest)[1]["components"]["playwright"]["version"] == "fixture-local-pin"
    assert load_toml(input_path)["authorization"] == checkout["authorization"]
    assert shared_bytes(project) == before


def test_locally_selecting_a_project_optional_tool_follows_the_shared_pin(project: Path) -> None:
    commands.configure(project, required=["python"], optional=["browser-automation"])
    _, lock_path, _ = commands.paths(project)
    lock = load_toml(lock_path)
    lock["components"]["playwright"]["version"] = "fixture-shared-pin"
    lock_path.write_text(render_toml(lock))
    commands.configure(project, local=["python-ide", "browser-automation"])
    manifest = load_toml(commands.paths(project)[0])
    assert lock_for(project, manifest)[1]["components"]["playwright"]["version"] == "fixture-shared-pin"


def test_corrupt_local_pins_are_refused_without_changing_the_record(project: Path) -> None:
    commands.configure(project, local=["codex-agent"])
    manifest = load_toml(commands.paths(project)[0])
    input_path, _ = checkout_record_paths(manifest, project)
    checkout = load_toml(input_path)
    checkout["capabilities"]["lock"] = "[bad"
    input_path.write_text(render_toml(checkout))
    before = input_path.read_bytes()
    with pytest.raises(ProjectConfigurationError, match="pins"):
        commands.configure(project, local=["codex-agent", "claude-code-agent"])
    assert input_path.read_bytes() == before


def test_new_project_may_select_an_agent_before_choosing_an_ide(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "fresh"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--require", "python",
                     "--creator", "mailto:owner@example.test"]) == 0
    assert cli.main(["project", "--path", str(root), "config", "add", "codex-agent"]) == 0
    manifest = load_toml(commands.paths(root)[0])
    with pytest.raises(ProjectConfigurationError, match="Choose your IDE"):
        lock_for(root, manifest)
    commands.configure(root, local=["codex-agent", "python-ide"])
    assert set(lock_for(root, manifest)[1]["components"]) == {"interactive-surface", "pycharm", "codex"}


def test_unavailable_local_selection_is_named_as_a_selection() -> None:
    lock = generate_lock(CapabilityPolicy(("python",)), MATRIX)
    with pytest.raises(ProjectConfigurationError, match="Selected capability 'codex-agent'"):
        usable_lock(CapabilityPolicy(("python",)), lock, LocalCapabilities(("codex-agent",)))



def version_set_with(project: Path, **pins: str) -> tuple[dict[str, Any], Path]:
    """Record an explicit version set equal to the effective lock, with sentinel component versions."""
    from devcapsule.configuration.file_formats import canonical_digest
    manifest = load_toml(commands.paths(project)[0])
    input_path, _ = checkout_record_paths(manifest, project)
    checkout = load_toml(input_path)
    lock = lock_for(project, manifest)[1]
    for component, version in pins.items():
        lock["components"][component]["version"] = version
    checkout["version-set"] = {"format": 1, "lock": render_toml(lock), "recommendation-digest": canonical_digest(load_toml(commands.paths(project)[1]))}
    input_path.write_text(render_toml(checkout))
    return manifest, input_path


def test_deselecting_a_project_optional_tool_keeps_its_version_set_pin(project: Path) -> None:
    from devcapsule.configuration.file_formats import selected_version_lock
    commands.configure(project, required=["python"], optional=["browser-automation"])
    commands.configure(project, local=["python-ide", "browser-automation"])
    manifest, input_path = version_set_with(project, playwright="fixture-local-pin")
    commands.configure(project, local=["python-ide"])
    selected = selected_version_lock(load_toml(input_path))
    assert selected is not None
    assert selected["components"]["playwright"]["version"] == "fixture-local-pin"  # the project still wants it
    assert lock_for(project, manifest)[1]["components"]["playwright"]["version"] == "fixture-local-pin"


def test_deselecting_an_agent_removes_its_pin_from_the_version_set(project: Path) -> None:
    from devcapsule.configuration.file_formats import selected_version_lock
    commands.configure(project, required=["python"])
    commands.configure(project, local=["python-ide", "codex-agent"])
    manifest, input_path = version_set_with(project, codex="fixture-agent-pin", pycharm="fixture-ide-pin")
    commands.configure(project, local=["python-ide"])
    selected = selected_version_lock(load_toml(input_path))
    assert selected is not None
    assert "codex" not in selected["components"]
    assert selected["components"]["pycharm"]["version"] == "fixture-ide-pin"
    assert selected["components"]["interactive-surface"] == "pycharm"
    assert set(lock_for(project, manifest)[1]["components"]) == {"interactive-surface", "pycharm"}
