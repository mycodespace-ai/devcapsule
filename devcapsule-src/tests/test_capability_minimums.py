"""Slice 1 acceptance: hand-written requirements and rc4 file compatibility."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tomllib

import pytest

from devcapsule import cli
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.configuration import owner_commands
from devcapsule.configuration.capabilities import CapabilityPolicy, LocalCapabilities, meets_minimum, version_parts
from devcapsule.configuration.capability_selection import compose_lock, generate_lock, usable_lock
from devcapsule.configuration.derivation import load_state
from devcapsule.configuration.file_formats import ProjectConfigurationError, canonical_digest, render_toml
from devcapsule.configuration.storage import checkout_record_paths, load_toml, recommendation_lock_for, settings_path
from devcapsule.configuration.trust import HomeTrust, channels_for
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import Capability, MATRICES, ResolutionMatrix, _BasePin, _ComponentPin, _VerifiedEdge

pytestmark = pytest.mark.legacy

MATRIX = MATRICES[Platform.LINUX_AMD64]
GOLDEN = Path(__file__).parent / "resources" / "golden_locks"
MANIFEST = '''devcapsule-schema-version = 2
[project]
name = "Minimums"
slug = "minimums"
creator = "mailto:owner@example.test"
mount = "/workspace/minimums"
[capabilities]
required = ["python>=3.14", "java>=21", "playwright>=1.21"]
[recommendations]
ide = "frontend-ide"
'''


def snapshot(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    root = tmp_path / "project"
    (root / ".devcapsule").mkdir(parents=True)
    return root


def write_project(root: Path, text: str) -> tuple[Path, Path]:
    manifest_path = root / ".devcapsule/devcapsule.toml"
    lock_path = root / ".devcapsule/devcapsule.linux-amd64.lock"
    manifest_path.write_text(text)
    return manifest_path, lock_path


@pytest.mark.parametrize("actual,minimum,accepted", [
    ("25.0.4+7", "21", True), ("v22.23.1", "22.23.1", True),
    ("1.10", "1.9", True), ("1.9", "1.10", False),
    ("3.12", "3.12.0", True), ("3.12.0.0", "3.12", True),
    ("3.12", "3.14", False), ("25.0.4+7", "25.0.4+99", True),
])
def test_dotted_integer_comparison(actual: str, minimum: str, accepted: bool) -> None:
    assert meets_minimum(actual, minimum) is accepted


@pytest.mark.parametrize("value", ["3.14rc1", "3.14-rc.1", "3.x", "3..1", "3.14.*", "", "3.14+beta"])
def test_unsupported_version_forms_are_explicit(value: str) -> None:
    with pytest.raises(ProjectConfigurationError, match="[Uu]nsupported"):
        version_parts(value)
    with pytest.raises(ProjectConfigurationError, match="[Uu]nsupported"):
        CapabilityPolicy.read({"capabilities": {"required": [f"python>={value}"]}})


@pytest.mark.parametrize("value", ["python=3", "python>3", "python<=3", "python>=3,<4", "python >=3"])
def test_only_minimum_relation_is_supported(value: str) -> None:
    with pytest.raises(ProjectConfigurationError, match="[Uu]nsupported"):
        CapabilityPolicy.read({"capabilities": {"required": [value]}})


def test_owners_three_requirements_refuse_python_before_writes(project: Path, tmp_path: Path, capsys) -> None:
    manifest_path, lock_path = write_project(project, MANIFEST)
    lock_path.write_text(MATRIX.resolve(["python", "java", "playwright"], project_only=True).render_lock())
    before = snapshot(tmp_path)
    assert cli.main(["project", "--path", str(project), "init", "--regenerate"]) == 2
    assert "no base supplies python 3.14 or newer; the Ubuntu 24.04 bases supply 3.12" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
    assert cli.main(["project", "--path", str(project), "config", "check"]) == 2
    assert "python>=3.14" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
    assert CapabilityPolicy.read(load_toml(manifest_path)).required == ("java", "playwright", "python")


def test_owners_java_and_playwright_resolve_show_and_preserve_minimums(project: Path, capsys) -> None:
    manifest_path, lock_path = write_project(project, MANIFEST.replace('"python>=3.14", ', ''))
    assert cli.main(["project", "--path", str(project), "init"]) == 0
    lock = load_toml(lock_path)
    assert MATRIX.supplied_version("java", lock) == "25.0.4+7"
    assert lock["components"]["playwright"]["version"] == "1.63.0"
    assert load_toml(manifest_path)["capabilities"]["required"] == ["java>=21", "playwright>=1.21"]
    assert cli.main(["project", "--path", str(project), "config", "show"]) == 0
    shown = capsys.readouterr().out
    java = next(line for line in shown.splitlines() if line.split()[:2] == ["capability", "java"])
    playwright = next(line for line in shown.splitlines() if line.split()[:2] == ["capability", "playwright"])
    assert "supplied by the base, 25.0.4+7" in java and "project (required, >=21)" in java
    assert "playwright 1.63.0" in playwright and "project (required, >=1.21)" in playwright
    assert playwright.count("1.63.0") == 1
    assert cli.main(["project", "--path", str(project), "config", "show", "--json"]) == 0
    rows = {row["name"]: row for row in json.loads(capsys.readouterr().out)["rows"] if row["kind"] == "capability"}
    assert rows["java"]["source"] == "project (required, >=21)"
    assert rows["java"]["effective"] == "supplied by the base, 25.0.4+7"
    assert rows["playwright"]["source"] == "project (required, >=1.21)"
    assert rows["playwright"]["effective"] == "playwright 1.63.0"
    owner_commands.require_tools(project, ["node"])
    assert load_toml(manifest_path)["capabilities"]["required"] == ["java>=21", "node", "playwright>=1.21"]


def test_minimum_is_part_of_new_digest() -> None:
    plain = generate_lock(CapabilityPolicy.read(tomllib.loads(MANIFEST.replace('"python>=3.14", ', '').replace('>=21', ''))), MATRIX)
    minimum = generate_lock(CapabilityPolicy.read(tomllib.loads(MANIFEST.replace('"python>=3.14", ', ''))), MATRIX)
    assert plain["capabilities-digest"] != minimum["capabilities-digest"]


def test_provider_order_dependencies_and_minimum_filter() -> None:
    # Synthetic catalog: the second provider qualifies only after filtering.
    base = _BasePin("test", "test", {"python": "3.12"}, {"reference": "test@sha256:aa"})
    matrix = ResolutionMatrix(
        platform=Platform.LINUX_AMD64, matrix_version="test", bases=(base,),
        components={"first": (_ComponentPin("first", "1.2", {"version": "1.2"}),),
                    "second": (_ComponentPin("second", "1.10", {"version": "1.10"}),)},
        edges=(_VerifiedEdge("first", "1.2", "test", "fixture"), _VerifiedEdge("second", "1.10", "test", "fixture")),
        couplings=(), capability_table={"compiler": Capability(("first", "second")), "python": Capability()}, materialization={},
    )
    assert matrix.providers("compiler") == ("first", "second")
    assert matrix.resolve_provider("compiler") == "first"
    lock = tomllib.loads(matrix.resolve(["compiler>=1.9"], project_only=True).render_lock())
    assert set(lock["components"]) == {"second"}
    with pytest.raises(ProjectConfigurationError, match="first 1.2, second 1.10"):
        matrix.resolve(["compiler>=2"], project_only=True, allow_unverified=True)
    assert MATRIX.providers("dotnet-ide") == ("rider",)
    assert MATRIX.component_closure("dotnet-ide") == ("dotnet-sdk", "rider")
    lock["components"]["first"] = {"version": "1.2"}
    lock["capability-providers"] = {"compiler": ["second"]}
    assert matrix.supplied_version("compiler", lock) == "1.10"



def test_newest_base_below_minimum_is_not_selected() -> None:
    base = _BasePin("older", "test", {"python": "3.14"}, {"reference": "older@sha256:aa"})
    matrix = ResolutionMatrix(
        platform=Platform.LINUX_AMD64, matrix_version="test",
        bases=(base, replace(base, mnemonic="newer", satisfies={"python": "3.12"}, lock_table={"reference": "newer@sha256:bb"})),
        components={}, edges=(), couplings=(), capability_table={"python": Capability()}, materialization={},
    )
    lock = tomllib.loads(matrix.resolve(["python>=3.14"], project_only=True).render_lock())
    assert lock["base"]["reference"] == "older@sha256:aa"


def test_provider_without_version_composes_without_a_minimum() -> None:
    manifest = {"capabilities": {"required": ["python"]}}
    shared = generate_lock(CapabilityPolicy.read(manifest), MATRIX)
    pins = generate_lock(CapabilityPolicy(("codex-agent",)), MATRIX)
    del pins["components"]["codex"]["version"]
    checkout = {"capabilities": {"selected": ["codex-agent"], "lock": render_toml(pins)}}
    composed = compose_lock(manifest, shared, checkout)
    usable, _ = usable_lock(CapabilityPolicy.read(manifest), composed, LocalCapabilities.read(checkout))
    assert usable["components"]["codex"] == pins["components"]["codex"]
    assert MATRIX.supplied_version("codex-agent", usable) is None
    with pytest.raises(ProjectConfigurationError, match="unknown version"):
        usable_lock(CapabilityPolicy(("codex-agent",), minimums=(("codex-agent", "1"),)), composed)


def test_saved_version_set_below_minimum_stops_run_with_three(project: Path, tmp_path: Path, capsys, monkeypatch) -> None:
    import io
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    manifest_path, lock_path = write_project(project, MANIFEST.replace('"python>=3.14", ', ''))
    assert cli.main(["project", "--path", str(project), "init", "--ide", "frontend-ide", "--authorize", "base-image", "default"]) == 0
    manifest = load_toml(manifest_path)
    state = load_state(project, manifest)
    old = state.composed_lock()
    old["components"]["playwright"]["version"] = "1.20"
    document = deepcopy(state.checkout)
    document["version-set"] = {"format": 1, "lock": render_toml(old), "recommendation-digest": canonical_digest(load_toml(lock_path))}
    assert state.input_path is not None
    state.input_path.write_text(render_toml(document))
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    before = snapshot(tmp_path)
    assert invoke(project, "run", "--memory", "6g", "--save", "--no-update-check") == 3
    message = capsys.readouterr().err
    assert "playwright>=1.21" in message and "1.20" in message and "versions follow-project --apply" in message
    assert snapshot(tmp_path) == before
    launch.assert_not_called()


def test_rc4_documents_keep_launch_and_old_digest(project: Path, tmp_path: Path, capsys) -> None:
    # These bytes use rc4 shapes. Pins come from the existing golden rc4 lock.
    manifest_path, lock_path = write_project(project, '''devcapsule-schema-version = 2
[project]
name = "Minimums"
slug = "minimums"
creator = "mailto:owner@example.test"
mount = "/workspace/minimums"
[capabilities]
required = ["python"]
optional = ["browser-automation"]
[capabilities.sdk-major]
python = 3
[recommendations]
ide = "frontend-ide"
''')
    manifest = load_toml(manifest_path)
    shared = tomllib.loads((GOLDEN / "intellij-browser.lock").read_text())
    shared["components"].pop("interactive-surface")
    shared["components"].pop("intellij")
    shared["materialization"] = {}
    shared["capability-providers"] = {"python": [], "browser-automation": ["playwright"]}
    shared["capabilities-digest"] = canonical_digest({"required": ["python"], "optional": ["browser-automation"], "sdk-major": {"python": 3}})
    lock_path.write_text(render_toml(shared))
    pins_text = (GOLDEN / "codium-agents.lock").read_text()
    pins = tomllib.loads(pins_text)
    record_path = checkout_record_paths(manifest, project)[0]
    record_path.parent.mkdir(parents=True)
    record_path.write_text(render_toml({
        "devcapsule-checkout-schema-version": 1,
        "project": {"creator": "mailto:owner@example.test", "slug": "minimums"},
        "checkout": {"path": str(project)},
        "capabilities": {"selected": ["claude-code-agent", "codex-agent", "frontend-ide"], "without": [], "lock": pins_text},
    }))
    settings_path().write_text('''devcapsule-settings-schema-version = 1
minimum-devcapsule = "0.3.0"
[trust.channels.devcapsule-base]
vendor = "DevCapsule"
origins = ["docker.io/mycodespaceai/devcapsule-base", "https://devcapsule.mycodespace.ai"]
integrity = "the SHA-256 digest the launcher pins"
accepted = "2026-10-24T10:00:00+00:00"
[trust.channels.claude-code]
vendor = "Anthropic"
origins = ["https://downloads.claude.ai"]
integrity = "the SHA-256 the launcher pins"
terms-url = "https://www.anthropic.com/legal/commercial-terms"
accepted = "2026-10-24T10:00:00+00:00"
''')
    trusted = HomeTrust.read(load_toml(settings_path()))
    assert all(trusted.covers(channel) for channel in channels_for(pins).values())
    before = snapshot(tmp_path)
    loaded = recommendation_lock_for(project, manifest)[1]
    assert loaded == shared
    prepared = prepare_launch(project, RunFlags(), interactive=False, print_only=True)
    expected = {**shared["components"], **pins["components"]}
    assert prepared.selected.lock["components"] == expected
    assert prepared.selected.resolution["runtime"]["component"] == "codium"
    assert len([note for note in prepared.notes if "SDK major" in note]) == 1
    assert snapshot(tmp_path) == before
    assert cli.main(["project", "--path", str(project), "config", "check"]) == 0
    report = capsys.readouterr().out
    assert report.count("SDK major") == 1
    assert report.startswith("Note: The SDK major constraint was removed")
    assert report.index("Note:") < report.index("Configuration contract valid")
    assert "Warning:" not in report
    assert snapshot(tmp_path) == before
    owner_commands.recommend(project, "memory", "6g")
    assert "sdk-major" not in load_toml(manifest_path)["capabilities"]
    assert lock_path.read_bytes() == before[lock_path]


@pytest.mark.parametrize("value", [{"python": 3}, {"python": True}, {"future": "opaque"}])
def test_old_table_is_ignored_and_never_written(value: dict) -> None:
    policy = CapabilityPolicy.read({"capabilities": {"required": ["python"], "sdk-major": value}})
    assert policy.document() == {"required": ["python"], "optional": []}


@pytest.mark.parametrize("arguments", [
    ("require", "node"), ("offer", "codex-agent"), ("drop", "java"),
    ("require", "env", "DB"), ("offer", "env", "DB"), ("drop", "env", "DB"),
    ("recommend", "ide", "python-ide"), ("recommend", "network", "host", "--because", "ports"),
])
def test_every_owner_preview_leaves_all_files_unchanged(project: Path, tmp_path: Path, arguments: tuple[str, ...]) -> None:
    manifest_path, lock_path = write_project(project, MANIFEST.replace('"python>=3.14", ', '') + '\n[environment.required.DB]\nreason = "database"\n')
    lock_path.write_text(render_toml(generate_lock(CapabilityPolicy.read(load_toml(manifest_path)), MATRIX)))
    before = snapshot(tmp_path)
    assert cli.main(["project", "--path", str(project), "config", *arguments, "--preview"]) == 0
    assert snapshot(tmp_path) == before


def test_owner_drop_recognizes_a_handwritten_component_alias(project: Path) -> None:
    manifest_path, lock_path = write_project(project, MANIFEST.replace('"python>=3.14", ', ''))
    lock_path.write_text(render_toml(generate_lock(CapabilityPolicy.read(load_toml(manifest_path)), MATRIX)))
    owner_commands.drop_tools(project, ["playwright"])
    assert load_toml(manifest_path)["capabilities"]["required"] == ["java>=21"]


def test_an_unpinned_base_version_cannot_claim_a_minimum() -> None:
    policy = CapabilityPolicy.read({"capabilities": {"required": ["docker-cli>=20"]}})
    with pytest.raises(ProjectConfigurationError, match="bases supply unknown"):
        generate_lock(policy, MATRIX)
    lock = tomllib.loads(MATRIX.resolve(["docker-cli"], project_only=True).render_lock())
    with pytest.raises(ProjectConfigurationError, match="unknown version"):
        usable_lock(policy, lock)
