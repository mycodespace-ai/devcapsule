"""The shipped catalog and its byte-exact locks through the real file loaders.

These checks depend on release pins and repository fixtures; they are integration tests.
"""
from __future__ import annotations
from pathlib import Path
import tomllib
import pytest
import devcapsule.resolution_matrix as resolution_matrix_module
from devcapsule.configuration.nodes import build_node_registry
from devcapsule.platforms import Platform
from devcapsule.configuration.file_formats import ProjectConfigurationError, canonical_digest
from devcapsule.configuration.storage import lock_for
from devcapsule.resolution_matrix import MATRICES, Formation, ResolutionError, ResolutionMatrix
from devcapsule.resolution_matrix import Capability, _BasePin, _ComponentPin, _Coupling, _VerifiedEdge

pytestmark = pytest.mark.integration

MATRIX = MATRICES[Platform.LINUX_AMD64]

GOLDEN_ROOT = Path(__file__).parents[1] / "resources" / "golden_locks"

REPO_ROOT = Path(__file__).resolve().parents[2]

GOLDEN_NEEDS = {
    "eclipse-browser": ["eclipse-ide", "java", "browser-automation"],
    "pycharm-minimal": ["python", "python-ide"],
    "dogfood": ["antigravity-agent", "browser-automation", "claude-code-agent", "codex-agent", "docker-cli", "python", "python-ide"],
    "rider-dotnet": ["dotnet-ide", "browser-automation"],
    "codium-dotnet": ["frontend-ide", "dotnet"],
    "intellij-browser": ["java", "java-ide", "browser-automation"],
    "codium-node": ["node", "frontend-ide"],
    "vscode-node": ["node", "vscode-ide"],
    "pycharm-full": [
        "python",
        "python-ide",
        "codex-agent",
        "claude-code-agent",
        "postgresql-client",
    ],
    "codium-agents": ["node", "frontend-ide", "codex-agent", "claude-code-agent"],
    "codium-antigravity": ["node", "frontend-ide", "antigravity-agent"],
}

def parse(content: str) -> dict:
    return tomllib.loads(content)

def rendered(need: list[str]) -> str:
    return MATRIX.resolve(need).render_lock()

@pytest.mark.parametrize("name", sorted(GOLDEN_NEEDS))
def test_resolution_matches_the_captured_golden_lock(name: str) -> None:
    """Resolution matches the captured golden lock."""
    golden = (GOLDEN_ROOT / f"{name}.lock").read_text(encoding="utf-8")
    assert rendered(GOLDEN_NEEDS[name]) == golden

def test_minimal_need_generates_a_complete_pycharm_lock() -> None:
    """Minimal need generates a complete pycharm lock."""
    lock = parse(rendered(["python", "python-ide"]))

    assert lock["devcapsule-lock-format-version"] == 1
    assert lock["platform"] == "linux-amd64"
    assert lock["base"]["reference"].startswith(
        "docker.io/mycodespaceai/devcapsule-base@sha256:"
    )
    assert lock["base"]["build-mnemonic"] == "v0.3.0-local-linux-x86_64"
    assert lock["components"]["interactive-surface"] == "pycharm"
    assert lock["components"]["pycharm"]["version"] == "2026.2.4"
    assert lock["materialization"]["recipe"] == "jetbrains-local-materialization"
    assert set(lock["components"]) == {"interactive-surface", "pycharm"}
    # The scoped digest covers exactly the derivation input; the retired
    # whole-manifest digest is never written.
    assert lock["capabilities-digest"] == canonical_digest(
        {"need": ["python", "python-ide"]}
    )
    assert "manifest-digest" not in lock

def test_frontend_need_generates_a_complete_codium_lock() -> None:
    """Frontend need generates a complete codium lock."""
    lock = parse(rendered(["node", "frontend-ide"]))

    assert lock["components"]["interactive-surface"] == "codium"
    codium = lock["components"]["codium"]
    assert codium["version"] == "1.143.17232"
    assert codium["license"] == "MIT"
    assert codium["url"].endswith("VSCodium-linux-x64-1.143.17232.tar.gz")
    assert lock["materialization"]["recipe"] == "vscode-local-materialization"
    assert set(lock["components"]) == {"interactive-surface", "codium"}
    # The newest base in the validated family wins.
    assert lock["base"]["build-mnemonic"] == "v0.3.0-local-linux-x86_64"

def test_base_selection_follows_each_needs_verified_edges() -> None:
    """The sparse matrix in action: newest validated base per capability set.

    One base family remains (v026 and the validations recorded only against
    it retired 2026-09-06), so every composition rides its newest base; the
    synthetic matrices below cover the sparse case.
    """

    assert parse(rendered(["node", "frontend-ide"]))["base"]["build-mnemonic"] == "v0.3.0-local-linux-x86_64"
    assert parse(rendered(["python", "python-ide"]))["base"]["build-mnemonic"] == "v0.3.0-local-linux-x86_64"
    assert (
        parse(rendered(["node", "frontend-ide", "codex-agent"]))["base"]["build-mnemonic"]
        == "v0.3.0-local-linux-x86_64"
    )
    assert (
        parse(rendered(["python", "python-ide", "antigravity-agent", "codex-agent"]))["base"][
            "build-mnemonic"
        ]
        == "v0.3.0-local-linux-x86_64"
    )

def test_formation_reports_capabilities_and_provenance() -> None:
    """Formation reports capabilities and provenance."""
    formation = MATRIX.resolve(["python-ide", "python"])

    assert isinstance(formation, Formation)
    assert formation.capabilities == ("python", "python-ide")
    assert "pycharm 2026.2.4" in formation.provenance
    assert "base v0.3.0-local-linux-x86_64" in formation.provenance

def test_two_interactive_capabilities_are_rejected() -> None:
    """Two interactive capabilities are rejected."""
    with pytest.raises(ProjectConfigurationError, match="exactly one interactive surface"):
        MATRIX.resolve(["python-ide", "frontend-ide"])

def test_missing_interactive_capability_is_explained() -> None:
    """Missing interactive capability is explained."""
    with pytest.raises(ProjectConfigurationError, match="python-ide"):
        MATRIX.resolve(["python"])

def test_unknown_capability_lists_the_supported_vocabulary() -> None:
    """Unknown capability lists the supported vocabulary."""
    with pytest.raises(ResolutionError) as failure:
        MATRIX.resolve(["python-ide", "quantum-debugger"])
    assert "'quantum-debugger'" in str(failure.value)
    for name in MATRIX.capabilities():
        assert name in str(failure.value)

def test_canonical_name_resolves_sole_or_unique_provider_and_refuses_ambiguity() -> None:
    """Canonical name resolves sole or unique provider and refuses ambiguity."""
    assert MATRIX.canonical_name("vscode") == "vscode-ide"
    assert MATRIX.canonical_name("codium") == "frontend-ide"
    matrix = ResolutionMatrix(
        platform=Platform.LINUX_AMD64,
        matrix_version="test-1",
        bases=(_BasePin("v1", "s1", {}, {"reference": "example@sha256:aa", "build-mnemonic": "v1"}),),
        components={
            "a": (_ComponentPin("a", "1.0", {"version": "1.0"}),),
            "b": (_ComponentPin("b", "1.0", {"version": "1.0"}),),
            "shared": (_ComponentPin("shared", "1.0", {"version": "1.0"}),),
        },
        edges=(),
        couplings=(),
        capability_table={
            "first-ide": Capability(("a", "shared"), ide=True),
            "second-ide": Capability(("b", "shared"), ide=True),
        },
        materialization={"a": {"recipe": "r", "recipe-version": "1"}},
    )
    assert matrix.canonical_name("a") == "first-ide"
    with pytest.raises(ResolutionError) as failure:
        matrix.canonical_name("shared")
    assert "'shared'" in str(failure.value)
    for name in matrix.capabilities():
        assert name in str(failure.value)

def test_need_is_normalized_to_a_sorted_unique_set() -> None:
    """Need is normalized to a sorted unique set."""
    assert MATRIX.normalize(["python-ide", "python", "python-ide"]) == (
        "python",
        "python-ide",
    )
    assert rendered(["python-ide", "python", "python"]) == rendered(
        ["python", "python-ide"]
    )

def test_malformed_need_values_are_rejected() -> None:
    """Malformed need values are rejected."""
    with pytest.raises(ResolutionError, match="array"):
        MATRIX.normalize("python-ide")
    with pytest.raises(ResolutionError, match="non-empty strings"):
        MATRIX.normalize(["python-ide", 7])

def test_generation_is_deterministic() -> None:
    """Generation is deterministic."""
    assert rendered(["python-ide", "codex-agent"]) == rendered(
        ["python-ide", "codex-agent"]
    )

def test_generated_lock_passes_the_real_loaders(tmp_path: Path) -> None:
    """Generated lock passes the real loaders."""
    project = tmp_path / "project"
    (project / ".devcapsule").mkdir(parents=True)
    need = ["python", "python-ide", "claude-code-agent", "codex-agent"]
    manifest = {
        "devcapsule-schema-version": 1,
        "capabilities": {"need": need},
        "project": {
            "name": "Example",
            "slug": "example",
            "creator": "https://github.com/example",
            "mount": "/workspace/example",
        },
    }
    (project / ".devcapsule" / "devcapsule.linux-amd64.lock").write_text(
        rendered(need), encoding="utf-8"
    )

    from devcapsule.configuration.manifest import current_manifest
    manifest = current_manifest(manifest, "manifest").document()
    lock_path, lock = lock_for(project, manifest)
    assert lock_path.name == "devcapsule.linux-amd64.lock"

    registry = build_node_registry(manifest, lock)
    assert registry.node("base-image").required is True
    assert registry.node("claude-code-download").family == "authorize"
    assert registry.node("codex/openai-api-key").providers == ("host-environment",)
    assert registry.node("pycharm/system").family == "bind"


def test_graphviz_is_an_additive_catalog_capability_on_both_platforms() -> None:
    """Both shipped matrices offer Graphviz alongside an independently selected IDE."""
    for platform, matrix in MATRICES.items():
        formation = matrix.resolve(["frontend-ide", "graphviz"])
        lock = tomllib.loads(formation.render_lock())
        assert lock["platform"] == platform.value
        assert lock["components"]["interactive-surface"] == "codium"
        graphviz = lock["components"]["graphviz"]
        assert graphviz["platform"] == platform.value
        assert graphviz["delivery-policy"] == "local-materialization"
        assert "source" in graphviz["artifacts"]
