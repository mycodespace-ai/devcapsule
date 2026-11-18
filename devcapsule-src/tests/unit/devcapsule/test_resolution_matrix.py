"""Resolution, normalization and lock rendering for the embedded and synthetic matrices."""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

import devcapsule.resolution_matrix as resolution_matrix_module
from devcapsule.platforms import Platform
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
    canonical_digest,
)
from devcapsule.resolution_matrix import (
    MATRICES,
    Formation,
    ResolutionError,
    ResolutionMatrix,
)
from devcapsule.resolution_matrix import (
    Capability,
    _BasePin,
    _ComponentPin,
    _Coupling,
    _VerifiedEdge,
)

from devcapsule.components.linux_arm64_pins import COMPONENT_LOCK_TABLES


MATRIX = MATRICES[Platform.LINUX_AMD64]
GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "resources" / "golden_locks"

# Byte-exact fixtures for the current matrix formation. Originally captured
# from the pre-D-0007 generator to prove the refactor byte-identical; on a
# deliberate pin advance they are regenerated in the same commit, so any
# other diff in generated locks is a regression.
GOLDEN_NEEDS = {
    "xfce4-terminal": ["xfce4-terminal"],
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


# ---------------------------------------------------------------------------
# The public surface


def test_public_surface_is_minimal() -> None:
    """Only the four supported names are exported and obsolete module attributes are absent."""
    assert resolution_matrix_module.__all__ == [
        "MATRICES",
        "Formation",
        "ResolutionError",
        "ResolutionMatrix",
    ]
    for retired in (
        "generate_platform_lock",
        "normalize_capability_need",
        "supported_capabilities",
        "GeneratedLock",
        "MATRIX_VERSION",
        "BASE_SATISFIED_CAPABILITIES",
        "INTERACTIVE_SURFACE_CAPABILITIES",
        "SUPPORTED_PLATFORMS",
    ):
        assert not hasattr(resolution_matrix_module, retired), retired


def test_matrices_is_total_over_platforms_and_read_only() -> None:
    """There is one read-only matrix entry per supported platform."""
    assert set(MATRICES) == set(Platform)
    with pytest.raises(TypeError):
        MATRICES[Platform.LINUX_AMD64] = MATRIX  # type: ignore[index]


def test_capability_vocabulary_unions_every_satisfaction_source() -> None:
    """The catalogue exposes all base, tool and interactive capabilities in sorted order."""
    assert MATRIX.capabilities() == (
        "antigravity-agent",
        "browser-automation",
        "claude-code-agent",
        "codex-agent",
        "docker-cli",
        "dotnet",
        "dotnet-ide",
        "eclipse-ide",
        "frontend-ide",
        "java",
        "java-ide",
        "maven",
        "node",
        "postgresql-client",
        "python",
        "python-ide",
        "vscode-ide",
        "xfce4-terminal",
    )


# ---------------------------------------------------------------------------
# Byte-identity with the pre-refactor generator, and dogfood reconstitution


@pytest.mark.parametrize("name", sorted(GOLDEN_NEEDS))
def test_resolution_matches_the_captured_golden_lock(name: str) -> None:
    """A composition renders the reviewed lock fixture byte for byte."""
    golden = (GOLDEN_ROOT / f"{name}.lock").read_text(encoding="utf-8")
    assert rendered(GOLDEN_NEEDS[name]) == golden


def test_minimal_need_generates_a_complete_pycharm_lock() -> None:
    """A Python IDE lock identifies its base, editor, installation recipe and scoped capability digest."""
    lock = parse(rendered(["python", "python-ide"]))

    assert lock["devcapsule-lock-format-version"] == 1
    assert lock["platform"] == "linux-amd64"
    assert lock["base"]["reference"].startswith(
        "docker.io/mycodespaceai/devcapsule-base@sha256:"
    )
    assert lock["base"]["build-mnemonic"] == MATRIX.base_images()[-1].built.builder
    assert lock["components"]["interactive-surface"] == "pycharm"
    assert lock["components"]["pycharm"]["version"] == MATRIX.component_pins()["pycharm"]["version"]
    assert lock["materialization"]["recipe"] == "jetbrains-local-materialization"
    assert set(lock["components"]) == {"interactive-surface", "pycharm"}
    # The scoped digest covers exactly the derivation input; the retired
    # whole-manifest digest is never written.
    assert lock["capabilities-digest"] == canonical_digest(
        {"need": ["python", "python-ide"]}
    )
    assert "manifest-digest" not in lock


def test_frontend_need_generates_a_complete_codium_lock() -> None:
    """The default frontend IDE lock selects Codium and records its pinned distribution."""
    lock = parse(rendered(["node", "frontend-ide"]))

    assert lock["components"]["interactive-surface"] == "codium"
    codium = lock["components"]["codium"]
    assert codium["version"] == MATRIX.component_pins()["codium"]["version"]
    assert codium["license"] == "MIT"
    assert codium["url"] == MATRIX.component_pins()["codium"]["url"]
    assert lock["materialization"]["recipe"] == "vscode-local-materialization"
    assert set(lock["components"]) == {"interactive-surface", "codium"}
    # The newest base in the validated family wins.
    assert lock["base"]["build-mnemonic"] == MATRIX.base_images()[-1].built.builder


def test_base_selection_follows_each_needs_verified_edges() -> None:
    """The sparse matrix in action: newest validated base per capability set.

    One base family remains (v026 and the validations recorded only against
    it retired 2026-09-06), so every composition rides its newest base; the
    synthetic matrices below cover the sparse case.
    """

    assert parse(rendered(["node", "frontend-ide"]))["base"]["build-mnemonic"] == MATRIX.base_images()[-1].built.builder
    assert parse(rendered(["python", "python-ide"]))["base"]["build-mnemonic"] == MATRIX.base_images()[-1].built.builder
    assert (
        parse(rendered(["node", "frontend-ide", "codex-agent"]))["base"]["build-mnemonic"]
        == MATRIX.base_images()[-1].built.builder
    )
    assert (
        parse(rendered(["python", "python-ide", "antigravity-agent", "codex-agent"]))["base"][
            "build-mnemonic"
        ]
        == MATRIX.base_images()[-1].built.builder
    )


def test_formation_reports_capabilities_and_provenance() -> None:
    """The formation reports the normalized need and identifies the selected base and editor."""
    formation = MATRIX.resolve(["python-ide", "python"])

    assert isinstance(formation, Formation)
    assert formation.capabilities == ("python", "python-ide")
    assert f"pycharm {MATRIX.component_pins()['pycharm']['version']}" in formation.provenance
    assert f"base {MATRIX.base_images()[-1].built.builder}" in formation.provenance


# ---------------------------------------------------------------------------
# Need validation and error explanations


def test_two_interactive_capabilities_are_rejected() -> None:
    """A project selects exactly one desktop surface."""
    with pytest.raises(ProjectConfigurationError, match="exactly one interactive surface"):
        MATRIX.resolve(["python-ide", "frontend-ide"])


def test_missing_interactive_capability_is_explained() -> None:
    """A missing interactive capability is reported with an actionable example."""
    with pytest.raises(ProjectConfigurationError, match="python-ide"):
        MATRIX.resolve(["python"])


def test_unknown_capability_lists_the_supported_vocabulary() -> None:
    """An unknown capability error lists the valid alternatives."""
    with pytest.raises(ResolutionError) as failure:
        MATRIX.resolve(["python-ide", "quantum-debugger"])
    assert "'quantum-debugger'" in str(failure.value)
    for name in MATRIX.capabilities():
        assert name in str(failure.value)


def test_canonical_name_resolves_sole_or_unique_provider_and_refuses_ambiguity() -> None:
    """A component name identifies its unique provider capability, and ambiguous names require clarification."""
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


def test_resolution_errors_are_project_configuration_errors() -> None:
    """Clients can catch a resolution failure as a project configuration error."""
    # Callers catching the established error hierarchy keep working.
    assert issubclass(ResolutionError, ProjectConfigurationError)


def test_need_is_normalized_to_a_sorted_unique_set() -> None:
    """Capability order and duplicates do not change the lock."""
    assert MATRIX.normalize(["python-ide", "python", "python-ide"]) == (
        "python",
        "python-ide",
    )
    assert rendered(["python-ide", "python", "python"]) == rendered(
        ["python", "python-ide"]
    )


def test_malformed_need_values_are_rejected() -> None:
    """Needs must be an array of nonempty strings."""
    with pytest.raises(ResolutionError, match="array"):
        MATRIX.normalize("python-ide")
    with pytest.raises(ResolutionError, match="non-empty strings"):
        MATRIX.normalize(["python-ide", 7])


def test_generation_is_deterministic() -> None:
    """The same capability request produces identical lock bytes."""
    assert rendered(["python-ide", "codex-agent"]) == rendered(
        ["python-ide", "codex-agent"]
    )


# ---------------------------------------------------------------------------
# The verified-combinations model: several versions per axis, sparse rows.
# These exercise the private model deliberately — the public surface hides
# it, and this is where its selection behavior is pinned down.


def _synthetic_matrix(
    edges: tuple[_VerifiedEdge, ...],
    couplings: tuple[_Coupling, ...] = (),
    bases: tuple[_BasePin, ...] | None = None,
) -> ResolutionMatrix:
    # The default bases sit in distinct families, so each is its own
    # validation target; edges name the family ("s1"/"s2").
    return ResolutionMatrix(
        platform=Platform.LINUX_AMD64,
        matrix_version="test-1",
        bases=bases
        or (
            _BasePin("v1", "s1", {"python": "3.12"}, {"reference": "example@sha256:aa", "build-mnemonic": "v1"}),
            _BasePin("v2", "s2", {"python": "3.12"}, {"reference": "example@sha256:bb", "build-mnemonic": "v2"}),
        ),
        components={
            "ide": (
                _ComponentPin("ide", "1.0", {"version": "1.0"}),
                _ComponentPin("ide", "2.0", {"version": "2.0"}),
            ),
            "agent": (_ComponentPin("agent", "0.5", {"version": "0.5"}),),
        },
        edges=edges,
        couplings=couplings,
        capability_table={"the-ide": Capability(("ide",), ide=True), "the-agent": Capability(("agent",)),
                          "python": Capability(), "java": Capability(), "node": Capability()},
        materialization={"ide": {"recipe": "r", "recipe-version": "1"}},
    )


def test_resolution_prefers_the_newest_verified_combination() -> None:
    """Resolution selects the newest combination with recorded evidence."""
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("ide", "2.0", "s2", "smoke"),
        )
    )
    lock = parse(matrix.resolve(["the-ide"]).render_lock())

    assert lock["base"]["build-mnemonic"] == "v2"
    assert lock["components"]["ide"]["version"] == "2.0"


def test_a_base_in_an_unvalidated_family_is_not_selected() -> None:
    """A newer base in another family requires its own verification."""
    # A newer base in a *new family* has inherited nothing: it earns no
    # edges until something is smoked on its generation, so resolution keeps
    # selecting the proven base. Verifying the new generation later is a
    # data addition, not an interface change.
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "2.0", "s1", "smoke"),)
    )
    lock = parse(matrix.resolve(["the-ide"]).render_lock())

    assert lock["base"]["build-mnemonic"] == "v1"
    assert lock["components"]["ide"]["version"] == "2.0"


def test_a_new_base_in_a_validated_family_inherits_its_validations() -> None:
    """A new release in the same base family inherits the verification."""
    # The ruling of 2026-09-02: what a smoke establishes is component-on-
    # family, so a base release that changes nothing substantial (same
    # generation) inherits its predecessor's edges and is selected as the
    # newest pin — no re-smoke per release of our own base.
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "1.0", "s1", "smoke"),),
        bases=(
            _BasePin("v1", "s1", {"python": "3.12"}, {"reference": "example@sha256:aa", "build-mnemonic": "v1"}),
            _BasePin("v2", "s1", {"python": "3.12"}, {"reference": "example@sha256:bb", "build-mnemonic": "v2"}),
        ),
    )
    lock = parse(matrix.resolve(["the-ide"]).render_lock())

    assert lock["base"]["build-mnemonic"] == "v2"
    assert lock["components"]["ide"]["version"] == "1.0"


def test_an_unverified_newer_component_version_falls_back() -> None:
    """A newer unverified component falls back to its verified predecessor."""
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "1.0", "s2", "smoke"),)
    )
    lock = parse(matrix.resolve(["the-ide"]).render_lock())

    assert lock["base"]["build-mnemonic"] == "v2"
    assert lock["components"]["ide"]["version"] == "1.0"


def test_verification_of_older_combinations_does_not_expire() -> None:
    """Adding a verified combination preserves the older combination in the original matrix."""
    # Adding a newer verified combination must not un-express the older one:
    # both remain resolvable facts; selection merely prefers the newest.
    sparse = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "1.0", "s1", "smoke"),)
    )
    grown = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("ide", "2.0", "s2", "smoke"),
        )
    )

    assert parse(sparse.resolve(["the-ide"]).render_lock())["base"]["build-mnemonic"] == "v1"
    assert parse(grown.resolve(["the-ide"]).render_lock())["base"]["build-mnemonic"] == "v2"


def test_allow_unverified_resolves_past_missing_edges_with_names() -> None:
    """An explicit experiment records each missing verification in the lock."""
    # Owner ruling 2026-09-03: the matrix may be stale or wrong, so the
    # sophisticated user goes through with a gentle warning. The base picked
    # minimizes unverified pairs; every one is named in the formation and
    # the rendered lock.
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "2.0", "s2", "smoke"),)
    )
    with pytest.raises(ResolutionError):
        matrix.resolve(["the-ide", "the-agent"])

    formation = matrix.resolve(["the-ide", "the-agent"], allow_unverified=True)

    assert formation.unverified == (
        "agent 0.5 on base v2",
    )
    lock = parse(formation.render_lock())
    assert lock["base"]["build-mnemonic"] == "v2"
    assert lock["unverified-combinations"] == "agent 0.5 on base v2"
    assert "WARNING" in formation.render_lock().splitlines()[2]


def test_allow_unverified_never_degrades_a_verified_resolution() -> None:
    """Allowing experiments preserves a fully verified selection."""
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("agent", "0.5", "s1", "smoke"),
        )
    )

    strict = matrix.resolve(["the-ide", "the-agent"]).render_lock()
    relaxed = matrix.resolve(["the-ide", "the-agent"], allow_unverified=True).render_lock()

    assert strict == relaxed
    assert "unverified-combinations" not in strict


def test_allow_unverified_prefers_the_base_with_fewer_unverified_pairs() -> None:
    """An experiment chooses the base with the fewest unverified pairs."""
    # v1 (s1) verifies both components; v2 (s2) verifies neither. With the
    # ide edge only on s1, forcing the agent through picks v1 — one
    # unverified pair beats two, even though v2 is newer.
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "1.0", "s1", "smoke"),)
    )

    formation = matrix.resolve(["the-ide", "the-agent"], allow_unverified=True)

    lock = parse(formation.render_lock())
    assert lock["base"]["build-mnemonic"] == "v1"
    assert formation.unverified == ("agent 0.5 on base v1",)


def test_allow_unverified_keeps_base_capabilities_a_hard_constraint() -> None:
    """Even an experiment must find a base with every required toolchain."""
    # A base that does not ship a needed toolchain cannot be forced: the
    # newer capability-lacking base is skipped even though verification is
    # relaxed everywhere.
    matrix = _synthetic_matrix(
        edges=(),
        bases=(
            _BasePin("v1", "s1", {"python": "3.12"}, {"reference": "example@sha256:aa", "build-mnemonic": "v1"}),
            _BasePin("v2", "s2", {}, {"reference": "example@sha256:bb", "build-mnemonic": "v2"}),
        ),
    )

    formation = matrix.resolve(["the-ide", "python"], allow_unverified=True)

    assert parse(formation.render_lock())["base"]["build-mnemonic"] == "v1"


def test_no_verified_combination_is_a_complete_explanation() -> None:
    """A refusal names the unverified combination and how to try it."""
    matrix = _synthetic_matrix(edges=())
    with pytest.raises(ResolutionError) as failure:
        matrix.resolve(["the-ide"])
    message = str(failure.value)
    assert message.startswith("Not yet validated: ide 2.0 on base v2.")
    assert "Run it as an experiment with --unverified" in message


def test_an_unverified_coupling_refuses_the_composition() -> None:
    """A coupled component pair must have a verified version pairing."""
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("ide", "2.0", "s1", "smoke"),
            _VerifiedEdge("agent", "0.5", "s1", "smoke"),
        ),
        couplings=(
            _Coupling("agent", "ide", frozenset({("0.5", "1.0")}), "smoke"),
        ),
    )
    with pytest.raises(ResolutionError, match="agent 0.5 with ide 2.0 \\(integration not validated\\)"):
        matrix.resolve(["the-ide", "the-agent"])


def test_a_verified_coupling_composes() -> None:
    """A verified paired composition records both selected component versions."""
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("agent", "0.5", "s1", "smoke"),
        ),
        couplings=(
            _Coupling("agent", "ide", frozenset({("0.5", "1.0")}), "smoke"),
        ),
    )
    lock = parse(matrix.resolve(["the-ide", "the-agent"]).render_lock())

    assert lock["components"]["ide"]["version"] == "1.0"
    assert lock["components"]["agent"]["version"] == "0.5"


# ---------------------------------------------------------------------------
# The refusal message (2026-09-03 bug record; owner rulings 2026-09-05 and
# 2026-09-06): a missing validation is not a refusal on grounds. The message
# names the exact elements the experiment would run — component, version,
# base, never the model's vocabulary — and offers --unverified. Only a base
# that does not ship a needed toolchain refuses outright.


def test_refusal_names_the_experiment_and_the_unverified_lever() -> None:
    """The refusal describes the same experiment that opting in will actually run."""
    # ide is verified only on the newer base, the agent only on the older.
    # The experiment picks the base with the fewest unvalidated pairs
    # (newest on ties): v2, running the agent unvalidated.
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "2.0", "s2", "smoke"),
            _VerifiedEdge("agent", "0.5", "s1", "smoke"),
        )
    )
    with pytest.raises(ResolutionError) as refusal:
        matrix.resolve(["the-ide", "the-agent"])
    message = str(refusal.value)
    assert message.splitlines() == [
        "Not yet validated: agent 0.5 on base v2.",
        "Run it as an experiment with --unverified; the lock will record what is "
        "unvalidated for everyone who uses it.",
    ]
    assert "substrate" not in message and "edge" not in message
    # The experiment runs exactly what the refusal named.
    formation = matrix.resolve(["the-ide", "the-agent"], allow_unverified=True)
    assert formation.unverified == ("agent 0.5 on base v2",)
    assert "# WARNING: an experiment. Not yet validated: agent 0.5 on base v2." in (
        formation.render_lock()
    )


def test_exhausted_unverified_refusal_does_not_recommend_the_flag_again() -> None:
    """A missing base capability is explained even when an experiment is allowed."""
    # java and node are each shipped by one base but by no single base, so
    # even the unverified fallback has nothing to offer.
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "1.0", "s1", "smoke"),),
        bases=(
            _BasePin("v1", "s1", {"python": "3.12", "java": "25"}, {"reference": "example@sha256:aa", "build-mnemonic": "v1"}),
            _BasePin("v2", "s2", {"python": "3.12", "node": "22"}, {"reference": "example@sha256:bb", "build-mnemonic": "v2"}),
        ),
    )
    with pytest.raises(ResolutionError) as refusal:
        matrix.resolve(["the-ide", "java", "node"], allow_unverified=True)
    message = str(refusal.value)
    assert message.startswith("No base ships everything this project needs:")
    assert message.index("v2: does not ship java") < message.index("v1: does not ship node")
    assert "Run it as an experiment" not in message
    assert "--unverified cannot help here" in message


AMD64 = MATRICES[Platform.LINUX_AMD64]
ARM64 = MATRICES[Platform.LINUX_ARM64]


def test_the_arm64_matrix_serves_each_arm64_pin_at_its_version() -> None:
    """The arm64 matrix's pin for each component version is that version's arm64 table."""
    assert all(ARM64.component_pin(component, version) == table
               for (component, version), table in COMPONENT_LOCK_TABLES.items())


def test_the_arm64_base_is_its_own_recipe_11_pin() -> None:
    """The arm64 matrix pins one recipe-11 base of DevCapsule's repository, not an amd64 one."""
    (base,) = ARM64.base_images()
    assert base.contract.recipe == 11
    assert base.reference.startswith("docker.io/mycodespaceai/devcapsule-base@sha256:")
    assert base.reference not in {image.reference for image in AMD64.base_images()}


@pytest.mark.parametrize("ide", ["frontend-ide", "vscode-ide", "eclipse-ide", "python-ide", "java-ide"])
def test_each_ide_smoked_natively_on_arm64_resolves_verified(ide: str) -> None:
    """An IDE with a native arm64 smoke resolves on the arm64 matrix without an unverified combination."""
    assert ARM64.resolve([ide]).unverified == ()
