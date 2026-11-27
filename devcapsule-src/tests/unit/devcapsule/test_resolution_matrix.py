"""Resolution decisions from explicit synthetic matrices; shipped catalog data is checked separately."""
from __future__ import annotations

import tomllib

import pytest

import devcapsule.resolution_matrix as resolution_matrix_module
from devcapsule.components.linux_arm64_pins import COMPONENT_LOCK_TABLES
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES, ResolutionError, ResolutionMatrix
from devcapsule.resolution_matrix import Capability, _BasePin, _ComponentPin, _Coupling, _VerifiedEdge

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

def parse(content: str) -> dict:
    return tomllib.loads(content)

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

def test_public_surface_is_minimal() -> None:
    """Public surface is minimal."""
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
    """Matrices is total over platforms and read only."""
    assert set(MATRICES) == set(Platform)
    with pytest.raises(TypeError):
        MATRICES[Platform.LINUX_AMD64] = AMD64  # type: ignore[index]

def test_resolution_errors_are_project_configuration_errors() -> None:
    """Resolution errors are project configuration errors."""
    # Callers catching the established error hierarchy keep working.
    assert issubclass(ResolutionError, ProjectConfigurationError)

def test_resolution_prefers_the_newest_verified_combination() -> None:
    """Resolution prefers the newest verified combination."""
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("ide", "2.0", "s2", "smoke"),
        )
    )
    lock = parse(matrix.resolve(["the-ide"]).render_lock())

    assert lock["base"]["build-mnemonic"] == "v2"
    assert lock["components"]["ide"]["version"] == "2.0"

def test_capability_vocabulary_includes_declared_base_and_component_capabilities() -> None:
    """The vocabulary includes both base-provided and component-provided capabilities."""
    matrix = _synthetic_matrix(edges=())
    assert matrix.capabilities() == ("java", "node", "python", "the-agent", "the-ide")

def test_a_base_in_an_unvalidated_family_is_not_selected() -> None:
    """A base in an unvalidated family is not selected."""
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
    """A new base in a validated family inherits its validations."""
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
    """An unverified newer component version falls back."""
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "1.0", "s2", "smoke"),)
    )
    lock = parse(matrix.resolve(["the-ide"]).render_lock())

    assert lock["base"]["build-mnemonic"] == "v2"
    assert lock["components"]["ide"]["version"] == "1.0"

def test_verification_of_older_combinations_does_not_expire() -> None:
    """Adding a newer verified combination preserves an older one required by a base capability."""
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("ide", "2.0", "s2", "smoke"),
        ),
        bases=(
            _BasePin("v1", "s1", {"java": "25"}, {"reference": "example@sha256:aa", "build-mnemonic": "v1"}),
            _BasePin("v2", "s2", {}, {"reference": "example@sha256:bb", "build-mnemonic": "v2"}),
        ),
    )
    lock = parse(matrix.resolve(["the-ide", "java"]).render_lock())
    assert lock["base"]["build-mnemonic"] == "v1"
    assert lock["components"]["ide"]["version"] == "1.0"

def test_allow_unverified_resolves_past_missing_edges_with_names() -> None:
    """Allow unverified resolves past missing edges with names."""
    # Owner ruling 2026-09-03: the matrix may be stale or wrong, so the
    # sophisticated user goes through with a gentle warning. The base picked
    # minimizes unverified pairs; every one is named in the formation and
    # the rendered lock.
    matrix = _synthetic_matrix(
        edges=(_VerifiedEdge("ide", "2.0", "s2", "smoke"),)
    )
    formation = matrix.resolve(["the-ide", "the-agent"], allow_unverified=True)

    assert formation.unverified == (
        "agent 0.5 on base v2",
    )
    lock = parse(formation.render_lock())
    assert lock["base"]["build-mnemonic"] == "v2"
    assert lock["unverified-combinations"] == "agent 0.5 on base v2"
    assert "WARNING" in formation.render_lock().splitlines()[2]

def test_allow_unverified_never_degrades_a_verified_resolution() -> None:
    """Allow unverified never degrades a verified resolution."""
    matrix = _synthetic_matrix(
        edges=(
            _VerifiedEdge("ide", "1.0", "s1", "smoke"),
            _VerifiedEdge("agent", "0.5", "s1", "smoke"),
        )
    )

    lock = parse(matrix.resolve(["the-ide", "the-agent"], allow_unverified=True).render_lock())
    assert lock["base"]["build-mnemonic"] == "v1"
    assert lock["components"]["ide"]["version"] == "1.0"
    assert lock["components"]["agent"]["version"] == "0.5"
    assert "unverified-combinations" not in lock

def test_allow_unverified_prefers_the_base_with_fewer_unverified_pairs() -> None:
    """Allow unverified prefers the base with fewer unverified pairs."""
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
    """Allow unverified keeps base capabilities a hard constraint."""
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
    """No verified combination is a complete explanation."""
    matrix = _synthetic_matrix(edges=())
    with pytest.raises(ResolutionError) as failure:
        matrix.resolve(["the-ide"])
    message = str(failure.value)
    assert message.startswith("Not yet validated: ide 2.0 on base v2.")
    assert "Run it as an experiment with --unverified" in message

def test_an_unverified_coupling_refuses_the_composition() -> None:
    """An unverified coupling refuses the composition."""
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
    """A verified coupling composes."""
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

def test_refusal_names_the_experiment_and_the_unverified_lever() -> None:
    """Refusal names the experiment and the unverified lever."""
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

def test_the_experiment_records_the_missing_verification_it_runs() -> None:
    """The experimental lock names the exact component/base pair that lacks verification."""
    matrix = _synthetic_matrix(edges=(
        _VerifiedEdge("ide", "2.0", "s2", "smoke"),
        _VerifiedEdge("agent", "0.5", "s1", "smoke"),
    ))
    formation = matrix.resolve(["the-ide", "the-agent"], allow_unverified=True)
    assert formation.unverified == ("agent 0.5 on base v2",)
    assert "# WARNING: an experiment. Not yet validated: agent 0.5 on base v2." in (
        formation.render_lock()
    )

def test_exhausted_unverified_refusal_does_not_recommend_the_flag_again() -> None:
    """Exhausted unverified refusal does not recommend the flag again."""
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
