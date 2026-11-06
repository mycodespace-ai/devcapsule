"""Slice 2: owner/developer commands, provider precedence, consent and rc4 files."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import tomllib

import pytest

from devcapsule import cli
from devcapsule.commands._run_flow import RunFlags, prepare_launch
from devcapsule.compat import DecisionPending
from devcapsule.components.catalog import COMPONENTS, INTERACTIVE_SURFACES
from devcapsule.components.intellij import IntelliJComponent
from devcapsule.components.postgresql_client import PostgresqlClientComponent
from devcapsule.configuration.capabilities import CapabilityPolicy, LocalCapabilities, resolution_recommendations
from devcapsule.configuration.capability_commands import check_documents, paths
from devcapsule.configuration.capability_selection import generate_lock, selected_lock
from devcapsule.configuration.derivation import load_state
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml, canonical_digest
from devcapsule.configuration.manifest_document import render_manifest
from devcapsule.configuration.storage import checkout_record_paths, load_toml
from devcapsule.materialization import SURFACE_MATERIALIZATIONS
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES, Capability
from tests.test_run_flow import project, config, record

pytestmark = pytest.mark.legacy


@pytest.fixture
def matrix(monkeypatch):
    """Synthetic choices only; all other contracts and artifact pins stay real."""
    original = MATRICES[Platform.LINUX_AMD64]
    matrix = original
    monkeypatch.setattr(matrix, "_capability_table", dict(matrix._capability_table))
    matrix._capability_table["frontend-ide"] = Capability(("codium", "intellij"), ide=True)
    matrix._capability_table["assistant"] = Capability(("codex", "claude-code"))
    return matrix


def snapshot(root: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_owner_minimum_replacement_drop_and_alias_bytes(project, capsys):
    assert config(project, "require", "java>=21", "playwright>=1.21", "--because", "the build") == 0
    text = paths(project)[0].read_text()
    assert 'required = ["node", "java>=21", "playwright>=1.21"]' in text
    assert config(project, "require", "java>=25") == 0
    assert '"java>=25"' in paths(project)[0].read_text()
    assert '"java>=21"' not in paths(project)[0].read_text()
    assert config(project, "drop", "java") == 0
    assert "java" not in CapabilityPolicy.read(load_toml(paths(project)[0])).required
    before = snapshot(project)
    assert config(project, "require", "python>=3.14") == 2
    assert "bases supply 3.12" in capsys.readouterr().err
    assert snapshot(project) == before


@pytest.mark.parametrize("command", [
    ("require", "java>=21"), ("offer", "codex-agent"), ("drop", "node"),
    ("require", "env", "DB"), ("offer", "env", "SMTP"), ("drop", "env", "DB"),
    ("recommend", "frontend-ide", "intellij"), ("recommend", "frontend-ide", "none"),
])
def test_owner_preview_has_no_writes(project, tmp_path, matrix, command, capsys):
    assert config(project, "require", "env", "DB") == 0
    assert config(project, "recommend", "frontend-ide", "codium") == 0
    before = snapshot(tmp_path)
    assert config(project, *command, "--preview") == 0
    assert "Preview" in capsys.readouterr().out
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("verb", ["require", "offer"])
def test_ide_refusal_points_to_recommend(project, tmp_path, verb, capsys):
    before = snapshot(tmp_path)
    assert config(project, verb, "frontend-ide") == 2
    assert "recommend ide" in capsys.readouterr().err
    assert snapshot(tmp_path) == before


def test_resolution_table_has_no_reason_and_rejects_invalid_component(project, matrix, tmp_path, capsys):
    assert config(project, "recommend", "frontend-ide", "intellij") == 0
    document = load_toml(paths(project)[0])
    assert document["devcapsule-schema-version"] == 2
    assert document["capabilities"]["resolution"] == {"frontend-ide": "intellij"}
    assert "reasons" not in document["capabilities"]
    assert "resolution" not in document.get("recommendations", {})
    before = snapshot(tmp_path)
    assert config(project, "recommend", "frontend-ide", "codex") == 2
    assert "does not provide" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
    assert config(project, "require", "java") == 0
    assert "reasons" not in load_toml(paths(project)[0])["capabilities"]
    assert config(project, "recommend", "frontend-ide", "none") == 0
    assert "resolution" not in load_toml(paths(project)[0])["capabilities"]


def test_shared_lock_pins_only_the_recommended_provider_and_check_refuses_bad_resolution(project, matrix):
    assert config(project, "offer", "assistant") == 0
    assert config(project, "recommend", "assistant", "claude-code") == 0
    manifest, lock = (load_toml(p) for p in paths(project)[:2])
    assert set(lock["components"]) == {"claude-code"}
    assert lock["capability-providers"]["assistant"] == ["claude-code"]
    assert check_documents(manifest, lock) == ()
    manifest["capabilities"]["resolution"]["assistant"] = "playwright"
    with pytest.raises(ProjectConfigurationError, match="does not provide"):
        check_documents(manifest, lock)
    manifest["capabilities"]["resolution"] = {"missing": "codex"}
    with pytest.raises(ProjectConfigurationError, match="does not know"):
        check_documents(manifest, lock)


def test_provider_precedence_and_default_checkout_pins(project, matrix, capsys):
    assert config(project, "ide", "frontend-ide") == 0
    assert load_state(project, load_toml(paths(project)[0])).composed_lock()["components"]["interactive-surface"] == "codium"
    assert config(project, "recommend", "frontend-ide", "intellij") == 0
    # Reading keeps personal pins; an explicit reset adopts the new default.
    assert load_state(project, load_toml(paths(project)[0])).composed_lock()["components"]["interactive-surface"] == "codium"
    assert config(project, "use", "frontend-ide", "default") == 0
    assert load_state(project, load_toml(paths(project)[0])).composed_lock()["components"]["interactive-surface"] == "intellij"
    assert config(project, "use", "frontend-ide", "codium") == 0
    assert record(project)["capabilities"]["providers"] == {"frontend-ide": "codium"}
    assert config(project, "show", "--json") == 0
    output = capsys.readouterr().out
    document = json.loads(output[output.index('{\n'):])
    row = next(row for row in document["rows"] if row["name"] == "frontend-ide")
    assert (row["provider"], row["provider-source"]) == ("codium", "checkout")
    assert config(project, "use", "frontend-ide", "default") == 0
    assert "providers" not in record(project)["capabilities"]
    assert config(project, "show", "--json") == 0
    output = capsys.readouterr().out
    row = next(row for row in json.loads(output[output.index('{\n'):])["rows"] if row["name"] == "frontend-ide")
    assert (row["provider"], row["provider-source"]) == ("intellij", "project recommends")
    assert row["effective"].startswith("intellij ")
    assert config(project, "recommend", "frontend-ide", "none") == 0
    assert config(project, "use", "frontend-ide", "default") == 0
    assert load_state(project, load_toml(paths(project)[0])).composed_lock()["components"]["interactive-surface"] == "codium"


def test_add_omit_restore_and_single_provider_refusal(project, tmp_path, capsys):
    assert config(project, "add", "postgresql-client") == 0
    assert record(project)["capabilities"]["selected"] == ["postgresql-client"]
    assert config(project, "omit", "postgresql-client") == 0
    assert record(project)["capabilities"]["selected"] == []
    assert config(project, "offer", "browser-automation") == 0
    assert config(project, "omit", "browser-automation") == 0
    assert record(project)["capabilities"]["without"] == ["browser-automation"]
    assert config(project, "restore", "browser-automation") == 0
    assert record(project)["capabilities"]["without"] == []
    for arguments in (("use", "browser-automation", "playwright"), ("use", "node", "default"),
                      ("omit", "node"), ("add", "node"), ("add", "frontend-ide")):
        before = snapshot(tmp_path)
        assert config(project, *arguments) == 2
        assert snapshot(tmp_path) == before
    assert "playwright" in capsys.readouterr().err


@pytest.mark.parametrize("save", [False, True])
def test_run_choices_reach_plan_and_save_only_when_requested(project, matrix, save):
    assert config(project, "ide", "frontend-ide") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    path = checkout_record_paths(load_toml(paths(project)[0]), project)[0]
    before = path.read_bytes()
    prepared = prepare_launch(project, RunFlags(capabilities=("postgresql-client", "codex-agent"),
                             providers=(("frontend-ide", "intellij"),), save=save), interactive=False)
    assert prepared.selected.lock["components"]["interactive-surface"] == "intellij"
    assert "codex" in prepared.selected.lock["components"]
    assert "postgresql-client" in prepared.selected.lock["components"]
    if save:
        saved = record(project)["capabilities"]
        assert saved["providers"] == {"frontend-ide": "intellij"}
        assert saved["selected"] == ["codex-agent", "frontend-ide", "postgresql-client"]
    else:
        assert path.read_bytes() == before


def test_changed_resolution_keeps_component_consent(project, matrix):
    assert config(project, "ide", "frontend-ide") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    assert config(project, "add", "assistant") == 0
    assert config(project, "recommend", "assistant", "claude-code") == 0
    assert config(project, "use", "assistant", "default") == 0
    # Accept through the normal complete review, once. No acquisition occurs here.
    prepared = prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO("y\n"), output_stream=io.StringIO())
    assert "claude-code" in prepared.selected.lock["components"]
    before = deepcopy(record(project).get("authorization", {}))
    assert config(project, "recommend", "assistant", "codex") == 0
    assert config(project, "use", "assistant", "default") == 0
    assert config(project, "recommend", "assistant", "claude-code") == 0
    assert config(project, "use", "assistant", "default") == 0
    prompts = io.StringIO()
    prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO(""), output_stream=prompts)
    assert prompts.getvalue() == ""
    assert record(project).get("authorization", {}) == before


@pytest.mark.parametrize("field,value", [("providers", []), ("providers", {"frontend-ide": 1}), ("providers", {" frontend-ide": "codium"})])
def test_checkout_provider_table_rejects_malformed_values(field, value):
    with pytest.raises(ProjectConfigurationError):
        LocalCapabilities.read({"capabilities": {field: value}})


def test_rc4_shape_without_new_vocabulary_ignores_resolution(project):
    assert config(project, "require", "java") == 0
    assert config(project, "offer", "browser-automation") == 0
    assert config(project, "recommend", "ide", "frontend-ide") == 0
    assert config(project, "recommend", "frontend-ide", "codium") == 0
    manifest = load_toml(paths(project)[0])
    # The reviewer ran the rc4 executable. This fixture proves the promised
    # catalog-first result when that reader ignores the new capability table.
    ignored = deepcopy(manifest)
    del ignored["capabilities"]["resolution"]
    policy = CapabilityPolicy.read(manifest)
    assert generate_lock(policy, MATRICES[Platform.LINUX_AMD64], recommendations=resolution_recommendations(manifest)) == generate_lock(
        CapabilityPolicy.read(ignored), MATRICES[Platform.LINUX_AMD64])


def test_resolver_precedence_minimum_lock_and_errors(matrix):
    name = "assistant"
    assert matrix.resolve_provider(name) == "codex"
    assert matrix.resolve_provider(name, recommended="claude-code") == "claude-code"
    assert matrix.resolve_provider(name, choice="codex", recommended="claude-code") == "codex"
    assert matrix.resolve_provider(name, minimum="1") == "claude-code"
    with pytest.raises(ProjectConfigurationError, match="cannot supply"):
        matrix.resolve_provider(name, minimum="1", choice="codex")
    with pytest.raises(ProjectConfigurationError, match="cannot supply"):
        matrix.resolve_provider(name, minimum="1", recommended="codex")
    for choice in ("missing", "playwright"):
        with pytest.raises(ProjectConfigurationError, match="does not provide"):
            matrix.resolve_provider(name, choice=choice)
    assert matrix.resolve_provider("python") is None
    with pytest.raises(ProjectConfigurationError, match="the base"):
        matrix.resolve_provider("python", choice="codex")
    lock = generate_lock(CapabilityPolicy((name,)), matrix, recommendations={name: "claude-code"})
    assert matrix.resolve_provider(name, lock=lock) == "claude-code"
    with pytest.raises(ProjectConfigurationError, match="missing supported providers"):
        matrix.resolve_provider(name, minimum="999", lock=lock)
    lock["capability-providers"][name].append("codex")
    with pytest.raises(ProjectConfigurationError, match="multiple providers"):
        matrix.resolve_provider(name, lock=lock)


@pytest.mark.parametrize("saved_set", [False, True])
def test_required_provider_choice_and_default_preserve_selection_shape(project, matrix, saved_set):
    assert config(project, "require", "assistant") == 0
    assert config(project, "ide", "frontend-ide") == 0
    manifest = load_toml(paths(project)[0])
    state = load_state(project, manifest)
    if saved_set:
        document = deepcopy(state.checkout)
        document["version-set"] = {"format": 1, "lock": render_toml(state.composed_lock()),
                                   "recommendation-digest": canonical_digest(state.shared_lock)}
        assert state.input_path is not None
        state.input_path.write_text(render_toml(document))
    selected_before = record(project)["capabilities"]["selected"]
    assert config(project, "use", "assistant", "claude-code") == 0
    state = load_state(project, manifest)
    effective = selected_lock(manifest, state.shared_lock, state.checkout)
    assert "claude-code" in effective["components"] and "codex" not in effective["components"]
    assert record(project)["capabilities"]["selected"] == selected_before
    assert config(project, "use", "assistant", "default") == 0
    state = load_state(project, manifest)
    effective = selected_lock(manifest, state.shared_lock, state.checkout)
    assert "codex" in effective["components"] and "claude-code" not in effective["components"]
    assert record(project)["capabilities"]["selected"] == selected_before


@pytest.mark.parametrize("save", [False, True])
def test_cli_repeatable_capability_and_provider_flags(project, matrix, monkeypatch, capsys, save):
    from tests.test_upgrade_recovery import install_external_fakes, invoke
    assert config(project, "authorize", "base-image", "default") == 0
    launch = install_external_fakes(monkeypatch, [])
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    before = record(project)
    assert invoke(project, "run", "--ide", "frontend-ide", "--with", "postgresql-client", "--with", "codex-agent",
                  "--with", "codex", "--with", "codex", "--use", "frontend-ide=codium", "--use", "frontend-ide=intellij",
                  "--no-update-check", *(["--save"] if save else [])) == 0
    options = launch.call_args.args[0]
    assert options.runtime_plan.component.id == "intellij"
    assert {item.id for item in options.runtime_plan.ancillary_components} == {"codex", "postgresql-client"}
    if save:
        assert record(project)["capabilities"]["providers"] == {"frontend-ide": "intellij"}
    else:
        assert record(project) == before




def test_part_three_owner_fixture_and_developer_commands(project, matrix, monkeypatch):
    """The order's future catalog example, with explicit test-only providers.

    The displayed manifest precedes the final drop and omits reason tables.
    Preserve and check those reasons separately; then test the final drop.
    """
    class Clang(PostgresqlClientComponent):
        @property
        def id(self):
            return "clang"

    class WebStorm(IntelliJComponent):
        @property
        def id(self):
            return "webstorm"

    monkeypatch.setitem(COMPONENTS, "clang", Clang())
    monkeypatch.setitem(COMPONENTS, "webstorm", WebStorm())
    monkeypatch.setitem(INTERACTIVE_SURFACES, "webstorm", COMPONENTS["webstorm"])
    monkeypatch.setitem(SURFACE_MATERIALIZATIONS, "webstorm", replace(SURFACE_MATERIALIZATIONS["intellij"], component_id="webstorm"))
    monkeypatch.setattr(matrix, "_bases", tuple(replace(base, satisfies={**base.satisfies, "python": "3.15"}) for base in matrix._bases))
    components = dict(matrix._components)
    components["clang"] = tuple(replace(pin, component_id="clang") for pin in components["postgresql-client"])
    components["webstorm"] = tuple(replace(pin, component_id="webstorm") for pin in components["intellij"])
    monkeypatch.setattr(matrix, "_components", components)
    edges = dict(matrix._verified)
    for (name, version, family), edge in list(edges.items()):
        replacement = {"postgresql-client": "clang", "intellij": "webstorm"}.get(name)
        if replacement:
            edges[(replacement, version, family)] = replace(edge, component_id=replacement)
    monkeypatch.setattr(matrix, "_verified", edges)
    monkeypatch.setattr(matrix, "_materialization", {**matrix._materialization, "webstorm": matrix._materialization["intellij"]})
    matrix._capability_table["cpp-compiler"] = Capability(("clang",))
    matrix._capability_table["frontend-ide"] = Capability(("codium", "webstorm"), ide=True)
    assert config(project, "drop", "node") == 0
    commands = [
        ("require", "cpp-compiler", "--because", "the build"),
        ("require", "python>=3.14", "java>=21", "--because", "the build targets them"),
        ("require", "playwright>=1.21"),
        ("offer", "browser-automation", "--because", "npm run test:ui"),
        ("offer", "codex-agent", "--because", "the project's agent instructions assume it"),
        ("recommend", "ide", "frontend-ide"),
        ("recommend", "frontend-ide", "codium"),
        ("recommend", "cpp-compiler", "clang"),
    ]
    for command in commands:
        assert config(project, *command) == 0
    manifest = load_toml(paths(project)[0])
    assert manifest["capabilities"]["reasons"] == {
        "cpp-compiler": "the build", "python": "the build targets them", "java": "the build targets them",
        "browser-automation": "npm run test:ui", "codex-agent": "the project's agent instructions assume it",
    }
    # Compare the owner's displayed tables byte for byte, including bare
    # keys and ordering. Identity/schema and reasons are not in that excerpt.
    lines = paths(project)[0].read_text().splitlines(keepends=True)
    excerpt = []
    keep = False
    for line in lines:
        if line.startswith("["):
            keep = line.strip() in {"[capabilities]", "[capabilities.resolution]", "[recommendations]"}
        if keep:
            excerpt.append(line)
    assert "".join(excerpt).strip() + "\n" == '''[capabilities]
required = ["cpp-compiler", "python>=3.14", "java>=21", "playwright>=1.21"]
optional = ["browser-automation", "codex-agent"]

[capabilities.resolution]
frontend-ide = "codium"
cpp-compiler = "clang"

[recommendations]
ide = "frontend-ide"
'''
    for command in (("ide", "frontend-ide"), ("add", "claude-code-agent"), ("omit", "browser-automation"),
                    ("restore", "browser-automation"), ("use", "frontend-ide", "webstorm"), ("use", "frontend-ide", "default")):
        assert config(project, *command) == 0
    assert config(project, "authorize", "base-image", "default") == 0
    prepared = prepare_launch(project, RunFlags(ide="frontend-ide", capabilities=("codex-agent",),
                             providers=(("frontend-ide", "webstorm"),), trust=("claude-code",), save=True), interactive=False)
    assert prepared.selected.lock["components"]["interactive-surface"] == "webstorm"
    assert record(project)["capabilities"]["providers"] == {"frontend-ide": "webstorm"}
    assert config(project, "drop", "browser-automation") == 0
    assert "browser-automation" not in load_toml(paths(project)[0])["capabilities"].get("optional", [])


def test_switching_ide_discards_only_its_old_provider_choice(project, matrix):
    assert config(project, "ide", "frontend-ide") == 0
    assert config(project, "use", "frontend-ide", "intellij") == 0
    assert config(project, "authorize", "base-image", "default") == 0
    prepared = prepare_launch(project, RunFlags(ide="python-ide"), interactive=False)
    assert prepared.selected.lock["components"]["interactive-surface"] == "pycharm"
    assert record(project)["capabilities"]["providers"] == {"frontend-ide": "intellij"}
    assert config(project, "ide", "python-ide") == 0
    assert "providers" not in record(project)["capabilities"]
    assert load_state(project, load_toml(paths(project)[0])).composed_lock()["components"]["interactive-surface"] == "pycharm"


def test_owner_can_correct_a_broken_resolution_without_an_editor(project, matrix, capsys):
    manifest = load_toml(paths(project)[0])
    manifest["capabilities"]["resolution"] = {"frontend-ide": "missing"}
    paths(project)[0].write_text(render_manifest(manifest))
    assert config(project, "check") == 2
    assert "does not provide" in capsys.readouterr().err
    assert config(project, "recommend", "frontend-ide", "codium") == 0
    assert resolution_recommendations(load_toml(paths(project)[0])) == {"frontend-ide": "codium"}


def test_personal_provider_pin_survives_an_unrelated_checkout_edit(project, matrix):
    assert config(project, "require", "assistant") == 0
    assert config(project, "use", "assistant", "claude-code") == 0
    path = checkout_record_paths(load_toml(paths(project)[0]), project)[0]
    document = record(project)
    pins = tomllib.loads(document["capabilities"]["lock"])
    pins["components"]["claude-code"]["version"] = "2.0.0"
    document["capabilities"]["lock"] = render_toml(pins)
    path.write_text(render_toml(document))
    assert config(project, "add", "postgresql-client") == 0
    assert tomllib.loads(record(project)["capabilities"]["lock"])["components"]["claude-code"]["version"] == "2.0.0"


def test_offer_component_alias_keeps_its_spelling(project):
    assert config(project, "offer", "playwright") == 0
    assert load_toml(paths(project)[0])["capabilities"]["optional"] == ["playwright"]
    assert load_toml(paths(project)[1])["capability-providers"]["playwright"] == ["playwright"]


def test_minimum_alone_records_the_filtered_provider(matrix):
    policy = CapabilityPolicy(("assistant",), minimums=(("assistant", "1"),))
    formation = matrix.resolve(["assistant>=1"], project_only=True)
    assert formation.resolved == {"assistant": "claude-code"}
    assert "capability-providers" not in tomllib.loads(formation.render_lock())
    lock = generate_lock(policy, matrix)
    assert lock["capability-providers"]["assistant"] == ["claude-code"]
    assert set(lock["components"]) == {"claude-code"}
    assert matrix.supplied_version("assistant", lock) == lock["components"]["claude-code"]["version"]


def test_minimum_excludes_a_catalog_provider_without_pins(matrix, monkeypatch):
    monkeypatch.setattr(matrix, "_components", {name: pins for name, pins in matrix._components.items() if name != "claude-code"})
    with pytest.raises(ProjectConfigurationError, match="cannot supply assistant"):
        matrix.resolve_provider("assistant", minimum="1", recommended="claude-code")
    assert matrix.resolve_provider("assistant") == "codex"
    assert matrix.resolve_provider("assistant", recommended="claude-code") == "claude-code"


def test_deselection_keeps_a_dependency_of_the_chosen_provider(project, matrix):
    matrix._capability_table["frontend-ide"] = Capability(("codium", "rider"), ide=True)
    assert config(project, "ide", "frontend-ide") == 0
    assert config(project, "use", "frontend-ide", "rider") == 0
    assert config(project, "add", "dotnet") == 0
    manifest = load_toml(paths(project)[0])
    state = load_state(project, manifest)
    lock = state.composed_lock()
    lock["components"]["dotnet-sdk"]["version"] = "9.0.1"
    document = state.checkout
    document["version-set"] = {"format": 1, "lock": render_toml(lock),
                               "recommendation-digest": canonical_digest(state.shared_lock)}
    assert state.input_path is not None
    state.input_path.write_text(render_toml(document))
    assert config(project, "omit", "dotnet") == 0
    lock = load_state(project, manifest).composed_lock()
    assert lock["components"]["dotnet-sdk"]["version"] == "9.0.1"


def test_owner_can_remove_an_unknown_resolution(project):
    manifest = load_toml(paths(project)[0])
    manifest["capabilities"]["resolution"] = {"future-capability": "future-provider"}
    paths(project)[0].write_text(render_manifest(manifest))
    assert config(project, "check") == 2
    assert config(project, "recommend", "future-capability", "none") == 0
    assert not resolution_recommendations(load_toml(paths(project)[0]))


@pytest.mark.parametrize("component", ["intellij", "none"])
def test_resolution_refuses_because_before_writing(project, matrix, tmp_path, capsys, component):
    assert config(project, "recommend", "frontend-ide", "codium") == 0
    before = snapshot(tmp_path)
    assert config(project, "recommend", "frontend-ide", component, "--because", "debugger") == 2
    assert "takes no --because" in capsys.readouterr().err
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("damage", ["missing", "different"])
def test_composition_refuses_stale_choice_without_resolving_or_writing(project, matrix, monkeypatch, tmp_path, damage, capsys):
    assert config(project, "ide", "frontend-ide") == 0
    document = record(project)
    document["capabilities"]["providers"] = {"frontend-ide": "intellij"}
    if damage == "missing":
        del document["capabilities"]["lock"]
    path = checkout_record_paths(load_toml(paths(project)[0]), project)[0]
    path.write_text(render_toml(document))
    before = snapshot(tmp_path)
    def refuse_resolution(*args, **kwargs):
        pytest.fail("A reader must not derive new catalog pins")
    monkeypatch.setattr(matrix, "resolve", refuse_resolution)
    assert config(project, "show") == 2
    assert "config use frontend-ide intellij" in capsys.readouterr().err
    assert snapshot(tmp_path) == before


def test_composition_retains_shared_components_and_stored_personal_pins(project, matrix, monkeypatch):
    assert config(project, "require", "assistant") == 0
    assert config(project, "use", "assistant", "claude-code") == 0
    def refuse_resolution(*args, **kwargs):
        pytest.fail("A reader must not derive new catalog pins")
    monkeypatch.setattr(matrix, "resolve", refuse_resolution)
    state = load_state(project, load_toml(paths(project)[0]))
    composed = state.composed_lock()
    assert {"codex", "claude-code"} <= set(composed["components"])
    assert composed["capability-providers"]["assistant"] == ["claude-code"]


@pytest.mark.parametrize("arguments,provider", [
    ({}, "codex"), ({"choices": {"assistant": "claude-code"}}, "claude-code"),
    ({"recommendations": {"assistant": "claude-code"}}, "claude-code"),
])
def test_formation_exposes_resolved_providers_without_changing_lock_shape(matrix, arguments, provider):
    formation = matrix.resolve(["assistant"], project_only=True, **arguments)
    assert formation.resolved == {"assistant": provider}
    lock = tomllib.loads(formation.render_lock())
    assert "capability-providers" not in lock
    assert set(lock["components"]) == {provider}


def test_base_service_has_no_provider_cell_or_json_fields(project, capsys):
    from devcapsule.configuration.listing import Listing
    assert config(project, "require", "python") == 0
    assert config(project, "show", "--json") == 0
    output = capsys.readouterr().out
    document = json.loads(output[output.index('{\n'):])
    row = next(row for row in document["rows"] if row["name"] == "python")
    assert "provider" not in row and "provider-source" not in row
    listing = Listing.from_document(document)
    item = next(row for row in listing.rows if row.name == "python")
    assert item.provider == item.provider_source == ""
    rendered = listing.render().splitlines()
    provider_start = rendered[0].index("PROVIDER")
    pending_start = rendered[0].index("PENDING")
    row_text = next(line for line in rendered[1:] if "python" in line)
    assert not row_text[provider_start:pending_start].strip()


@pytest.mark.parametrize("arguments", [("add", "postgresql-client"), ("omit", "browser-automation"),
                                      ("restore", "browser-automation"), ("use", "frontend-ide", "intellij")])
def test_developer_edit_message_names_run(project, matrix, arguments, capsys):
    assert config(project, "offer", "browser-automation") == 0
    assert config(project, "ide", "frontend-ide") == 0
    capsys.readouterr()
    assert config(project, *arguments) == 0
    output = capsys.readouterr().out
    assert "The next 'devcapsule project run' uses it." in output
    assert "config resolve" not in output


@pytest.mark.parametrize("field", ["provider", "provider-source"])
def test_listing_rejects_nontext_provider_fields(field):
    from devcapsule.configuration.listing import Listing, LISTING_SCHEMA_VERSION
    with pytest.raises(ProjectConfigurationError, match="eight text columns"):
        Listing.from_document({"schema-version": LISTING_SCHEMA_VERSION, "rows": [{field: 1}]})
