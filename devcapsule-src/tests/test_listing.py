"""The truthful listing: effective value, source and pending, computed from documents, writing nothing."""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from devcapsule.configuration.capability_selection import compose_lock, generate_lock
from devcapsule.configuration.capabilities import CapabilityPolicy
from devcapsule.configuration.file_formats import render_toml
from devcapsule.configuration.listing import assess_checkout
from devcapsule.configuration.launcher_values import launcher_value_sources
from devcapsule.configuration.home import HomeDefaults
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy

MATRIX = MATRICES[Platform.LINUX_AMD64]

SURFACES = {name: MATRIX.resolve_provider(name) or name for name in MATRIX.ide_capabilities()}


def manifest(**extra) -> dict:
    return {"devcapsule-schema-version": 2,
            "project": {"creator": "mailto:owner@example.test", "slug": "sample", "name": "Sample", "mount": "/workspace/sample"},
            "capabilities": {"required": ["node"], "optional": ["browser-automation"]}, **extra}


def listing(document: dict, checkout: dict | None = None, *, home: dict | None = None, saved=None):
    shared = generate_lock(CapabilityPolicy.read(document), MATRIX)
    checkout = checkout or {"devcapsule-checkout-schema-version": 1}
    composed = compose_lock(document, shared, checkout)
    return assess_checkout(document, shared, composed, checkout, home=home, saved_environment=saved,
                           surfaces=SURFACES, project=Path("/p"), base_display="contained")


def rows(result, kind):
    return {row.name: row for row in result.rows if row.kind == kind}


def test_an_unchosen_ide_is_a_pending_row_not_a_refusal() -> None:
    result = listing(manifest())
    ide = rows(result, "ide")["(none)"]
    assert ide.pending.startswith("choose one:") and "config ide IDE" in ide.command
    assert "ide" in [row.kind for row in result.pending]
    assert any("once an IDE is chosen" in note for note in result.notes)


def test_a_recommended_ide_is_disclosed_with_its_reason_and_not_pending() -> None:
    result = listing(manifest(recommendations={"ide": "frontend-ide", "reasons": {"ide": "TypeScript"}}))
    ide = rows(result, "ide")["frontend-ide"]
    assert ide.pending == "" and ide.source.startswith("project recommendation: TypeScript")
    assert ide.command.endswith("config ide frontend-ide")


def test_capabilities_show_their_scope_and_omission() -> None:
    result = listing(manifest(), {"devcapsule-checkout-schema-version": 1, "capabilities": {"without": ["browser-automation"]}})
    tools = rows(result, "capability")
    assert tools["node"].source == "project (required)" and tools["node"].effective == "supplied by the base"
    assert tools["browser-automation"].effective == "omitted" and tools["browser-automation"].source == "checkout (omitted)"


def test_launcher_values_follow_the_precedence_and_name_their_source() -> None:
    document = manifest(recommendations={"memory": "6g"})
    home = {"defaults": {"memory": "4GiB", "cpus": 2}}
    result = listing(document, home=home)
    assert rows(result, "memory")["memory"].effective == "6GiB" and rows(result, "memory")["memory"].source == "project recommendation"
    assert rows(result, "cpus")["cpus"].effective == "2" and rows(result, "cpus")["cpus"].source == "home default"
    checkout = {"devcapsule-checkout-schema-version": 1, "configuration": {"values": {"memory": "8GiB"}}}
    result = listing(document, checkout, home=home)
    assert rows(result, "memory")["memory"].source == "checkout"
    assert rows(result, "memory")["memory"].effective == "8GiB"
    none = listing(manifest())
    assert rows(none, "memory")["memory"].effective == "no limit" and rows(none, "memory")["memory"].source == "none"


def test_a_legacy_memory_declaration_is_an_alias_of_memory() -> None:
    document = manifest(configuration={"values": {"runtime.memory-limit": {
        "type": "memory-size", "runtime-effect": "docker.memory-limit", "recommended": "2GiB"}}})
    assert launcher_value_sources(document, {}) == {"memory": ("2GiB", "project recommendation"), "cpus": (None, "none")}
    recorded = {"configuration": {"values": {"runtime.memory-limit": "3GiB"}}}
    assert launcher_value_sources(document, recorded)["memory"] == ("3GiB", "checkout")
    result = listing(document, {"devcapsule-checkout-schema-version": 1, **recorded})
    assert "runtime.memory-limit" not in rows(result, "value")
    assert rows(result, "memory")["memory"].effective == "3GiB"


def test_host_access_rows_show_secure_defaults_and_ask_only_what_the_project_recommends() -> None:
    document = manifest(host={"network": {"mode": {"recommended": {"value": "host", "justification": "ports"}}}})
    result = listing(document)
    access = rows(result, "access")
    assert access["docker-daemon"].effective == "none" and access["docker-daemon"].source == "secure default" and not access["docker-daemon"].pending
    assert access["host-x11"].effective == "contained desktop"
    assert access["network"].effective == "bridge"
    assert access["network"].pending == "the project asks for network host; allow or deny"
    assert "config authorize network host" in access["network"].command and "config deny network" in access["network"].command
    denied = {"devcapsule-checkout-schema-version": 1, "authorization": {"network": {
        "value": "bridge", "recommendation-digest": "stale"}}}
    result = listing(document, denied)
    # A recorded answer under an earlier recommendation is kept and disclosed, never asked again.
    row = rows(result, "access")["network"]
    assert row.effective == "bridge" and not row.pending and "kept" in row.source


def test_environment_rows_cover_required_offered_and_saved(monkeypatch) -> None:
    monkeypatch.setenv("EXTRA", "private")
    document = manifest(environment={"required": {"POSTGRES_HOST": {"reason": "db"}}, "optional": {"SMTP_HOST": {}}})
    result = listing(document, saved={"POSTGRES_HOST": "x", "EXTRA": None})
    env = rows(result, "env")
    assert env["POSTGRES_HOST"].effective == "set" and env["POSTGRES_HOST"].source == "checkout; project (required): db"
    assert env["SMTP_HOST"].effective == "unset" and not env["SMTP_HOST"].pending
    assert env["EXTRA"].effective == "from the host's variable" and env["EXTRA"].source == "checkout"
    result = listing(document)
    assert rows(result, "env")["POSTGRES_HOST"].pending == "the project needs a value from you"
    assert rows(result, "env")["POSTGRES_HOST"].command.endswith("config env set POSTGRES_HOST VALUE")


def test_bindings_and_secrets_appear_once_an_ide_is_chosen(tmp_path: Path) -> None:
    from devcapsule.configuration.capability_commands import pin_selection
    from devcapsule.configuration.capabilities import LocalCapabilities
    document = manifest()
    shared = generate_lock(CapabilityPolicy.read(document), MATRIX)
    local = LocalCapabilities(selected=("codex-agent", "frontend-ide"))
    pins = pin_selection(MATRIX, CapabilityPolicy.read(document), local, shared, LocalCapabilities(), {}, allow_unverified=True)
    checkout = {"devcapsule-checkout-schema-version": 1,
                "capabilities": {"selected": list(local.selected), "without": [], "lock": render_toml(pins)}}
    composed = compose_lock(document, shared, checkout)
    result = assess_checkout(document, shared, composed, checkout, surfaces=SURFACES, project=Path("/p"), base_display="contained")
    assert rows(result, "ide")["frontend-ide"].effective.startswith("codium ")
    assert rows(result, "capability")["codex-agent"].effective.startswith("codex ")
    assert rows(result, "binding")["home"].effective == "managed directory"
    assert rows(result, "secret")["codex/openai-api-key"].source == "component (optional)"
    assert not result.notes


def test_declared_values_rows_and_undeclared_answers() -> None:
    document = manifest(configuration={"values": {"db.url": {"type": "string", "required": True},
                                                  "theme": {"type": "string", "recommended": "dark"}}})
    result = listing(document, {"devcapsule-checkout-schema-version": 1, "configuration": {"values": {"stray": 1}}})
    values = rows(result, "value")
    assert values["db.url"].pending == "the project needs a value from you" and values["db.url"].command.endswith("config set db.url VALUE")
    assert values["theme"].effective == '"dark"' and values["theme"].source == "project recommendation"
    assert values["stray"].pending == "not declared by this project"


def test_render_and_document_carry_every_column() -> None:
    result = listing(manifest())
    text = result.render()
    assert text.splitlines()[0].split() == ["KIND", "NAME", "EFFECTIVE", "SOURCE", "PROVIDER", "PENDING"]
    document = result.document()
    assert document["schema-version"] == 2 and "(none)" in document["pending"]
    assert set(document["rows"][0]) == {"kind", "name", "effective", "source", "pending", "command"}
    assert result.render_pending().startswith("Pending decisions:")


def test_home_defaults_validate_and_render() -> None:
    defaults = HomeDefaults.read({"defaults": {"memory": "4g", "cpus": 2}})
    assert defaults.values == {"memory": "4GiB", "cpus": 2}
    assert tomllib.loads(render_toml(defaults.document())) == {"defaults": {"cpus": 2, "memory": "4GiB"}}
    assert defaults.with_value("cpus", None).values == {"memory": "4GiB"}
    with pytest.raises(ProjectConfigurationError, match="owns memory, cpus"):
        HomeDefaults.read({"defaults": {"swap": "1g"}})
    with pytest.raises(ProjectConfigurationError, match="positive integer"):
        HomeDefaults.read({"defaults": {"cpus": 0}})


@pytest.mark.parametrize("source,checkout,recommended,defaults,expected", [
    ("none", {}, {}, {}, (None, None)),
    ("home default", {}, {}, {"memory": "2g", "cpus": 2}, ("2GiB", 2)),
    ("project recommendation", {}, {"memory": "3g", "cpus": 3}, {"memory": "2g", "cpus": 2}, ("3GiB", 3)),
    ("checkout", {"memory": "4g", "cpus": 4}, {"memory": "3g", "cpus": 3}, {"memory": "2g", "cpus": 2}, ("4GiB", 4)),
])
def test_launcher_sources_and_runtime_effects_agree(source, checkout, recommended, defaults, expected):
    from devcapsule.configuration.launcher_values import resolve_launcher_values
    document = manifest(recommendations=recommended)
    local = {"configuration": {"values": checkout}}
    home = {"defaults": defaults}
    sources = launcher_value_sources(document, local, home)
    assert sources == {"memory": (expected[0], source), "cpus": (expected[1], source)}
    values, effects = resolve_launcher_values(document, local, home)
    if expected[0] is None:
        assert values == effects == {}
    else:
        assert values == {"memory": expected[0], "cpus": expected[1]}
        assert effects == {"memory-limit-bytes": expected[1] * 1024 ** 3, "cpus": expected[1]}


def test_required_legacy_memory_stays_required_and_resolves_from_each_source():
    from devcapsule.configuration.launcher_values import resolve_launcher_values
    document = manifest(configuration={"values": {"runtime.memory-limit": {
        "type": "memory-size", "runtime-effect": "docker.memory-limit", "required": True}}})
    with pytest.raises(ProjectConfigurationError, match="Required value memory"):
        resolve_launcher_values(document, {})
    result = listing(document)
    assert any(row.kind == "memory" and row.pending and "config set memory" in row.command for row in result.rows)
    for recorded in ({"memory": "3g"}, {"runtime.memory-limit": "3GiB"}):
        assert resolve_launcher_values(document, {"configuration": {"values": recorded}})[1] == {"memory-limit-bytes": 3 * 1024 ** 3}
    assert resolve_launcher_values(document, {}, {"defaults": {"memory": "2g"}})[1] == {"memory-limit-bytes": 2 * 1024 ** 3}
    document["configuration"]["values"]["runtime.memory-limit"]["recommended"] = "4GiB"
    assert resolve_launcher_values(document, {})[1] == {"memory-limit-bytes": 4 * 1024 ** 3}


def test_legacy_memory_omission_is_preserved_until_reset():
    from devcapsule.configuration.launcher_values import resolve_launcher_values
    document = manifest(configuration={"values": {"runtime.memory-limit": {
        "type": "memory-size", "runtime-effect": "docker.memory-limit", "recommended": "2GiB"}}})
    local = {"configuration": {"omitted-values": ["runtime.memory-limit"]}}
    assert resolve_launcher_values(document, local) == ({}, {})
    assert rows(listing(document, local), "memory")["memory"].source == "checkout (omitted)"
    document["configuration"]["values"]["runtime.memory-limit"]["required"] = True
    with pytest.raises(ProjectConfigurationError, match="cannot be omitted"):
        resolve_launcher_values(document, local)


@pytest.mark.parametrize("answer,stale,effective,pending", [
    ("host", False, "host", False), ("bridge", False, "bridge", False),
    ("host", True, "host", False), ("wrong", False, "bridge", True),
])
def test_host_access_effective_and_pending_follow_record_validity(answer, stale, effective, pending):
    from devcapsule.configuration.authorization import authorization_declarations
    document = manifest(host={"network": {"mode": {"recommended": {"value": "host", "justification": "ports"}}}})
    shared = generate_lock(CapabilityPolicy.read(document), MATRIX)
    digest = authorization_declarations(document, shared)["network"].recommendation_digest
    local = {"authorization": {"network": {"value": answer, "recommendation-digest": "old" if stale else digest}}}
    row = rows(listing(document, local), "access")["network"]
    assert row.effective == effective and bool(row.pending) is pending
    assert ("kept" in row.source) if stale else ("project recommends host" in row.source)


def test_obsolete_authorization_is_pending_with_forget_remedy():
    row = rows(listing(manifest(), {"authorization": {"removed-node": {"value": True}}}), "access")["removed-node"]
    assert row.pending and row.command.endswith("config forget removed-node")


def test_invalid_cpu_answer_keeps_memory_row_and_names_cpu_remedy():
    result = listing(manifest(), {"configuration": {"values": {"memory": "2GiB", "cpus": 0}}})
    memory = rows(result, "memory")["memory"]
    cpu = rows(result, "cpus")["cpus"]
    assert memory.effective == "2GiB" and not memory.pending
    assert cpu.pending and cpu.command.endswith("config set cpus N")


@pytest.mark.parametrize("recommended", [False, True])
def test_legacy_host_answer_is_the_effective_value(recommended):
    host = {"network": {"mode": {"recommended": {"value": "host", "justification": "ports"}}}} if recommended else {}
    row = rows(listing(manifest(host=host), {"host": {"network": "host"}}), "access")["network"]
    assert row.effective == "host" and row.source.startswith("checkout (legacy)") and not row.pending


@pytest.mark.parametrize("scope", ["required", "optional", "checkout", "omitted"])
@pytest.mark.parametrize("provider", ["codex", "postgresql-client"])
def test_capability_kind_is_independent_of_provider_and_name_suffix(monkeypatch, scope, provider):
    from devcapsule.resolution_matrix import Capability
    monkeypatch.setitem(MATRIX._capability_table, "assistant", Capability((provider,)))
    document = manifest()
    checkout = {"devcapsule-checkout-schema-version": 1}
    if scope == "checkout":
        checkout["capabilities"] = {"selected": ["assistant"]}
    else:
        document["capabilities"]["optional" if scope == "omitted" else scope] = ["assistant"]
        if scope == "omitted":
            checkout["capabilities"] = {"without": ["assistant"]}
    shared = generate_lock(CapabilityPolicy.read(document), MATRIX)
    if scope == "checkout":
        from devcapsule.configuration.capability_commands import pin_selection
        from devcapsule.configuration.capabilities import LocalCapabilities
        pins = pin_selection(MATRIX, CapabilityPolicy.read(document), LocalCapabilities.read(checkout),
                             shared, LocalCapabilities(), {}, allow_unverified=True)
        checkout["capabilities"]["lock"] = render_toml(pins)
    composed = compose_lock(document, shared, checkout)
    result = assess_checkout(document, shared, composed, checkout,
                             surfaces=SURFACES)
    assert rows(result, "capability")["assistant"].effective == (
        "omitted" if scope == "omitted" else f"{provider} {composed['components'][provider]['version']}")
    assert not rows(result, "agent") and not rows(result, "tool")
