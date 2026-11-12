"""Unit tests of ``devcapsule.configuration.authorization``: the decisions a checkout carries.

Every lock here is built by the test. The base-image declaration is derived
from the lock, so each expected value is computed from the inputs the test
chose, never read from a run or from this repository's own lock.
"""
from __future__ import annotations

from typing import Any

from devcapsule.configuration.authorization import authorization_declarations
from devcapsule.configuration.file_formats import canonical_digest
from devcapsule.images.contract import LEGACY_RECIPE_SOURCE_PATH, RECIPE_SOURCE_PATH, REPOSITORY

REFERENCE = "registry.example.test/devcapsule/base@sha256:" + "ab" * 32
"""A digest-pinned reference, as a committed lock must carry."""


def _lock(**base: Any) -> dict[str, Any]:
    """A platform lock whose only content is the given base table."""
    return {"base": {"reference": REFERENCE, **base}, "components": {}}


def test_the_base_declaration_names_the_contract_the_reference_and_the_builders_recipe() -> None:
    """Precondition: a lock recording the base's contract, build mnemonic and recipe source.
    Action: build the declarations. Postcondition: the base-image declaration asks to
    execute that contract at that reference, credits the builder, links the recipe at the
    builder's tag, recommends the reference and digests this very lock."""
    lock = _lock(contract="ubuntu-24.04@11", **{"build-mnemonic": "v9.9.9-test", "recipe-source": RECIPE_SOURCE_PATH})

    declaration = authorization_declarations({}, lock)["base-image"]

    assert declaration.description == (
        f"Execute base ubuntu-24.04@11 at {REFERENCE}, built by v9.9.9-test; "
        f"recipe source: {REPOSITORY}/blob/v9.9.9-test/{RECIPE_SOURCE_PATH}."
    )
    assert declaration.display_value == f"ubuntu-24.04@11 \u2014 {REFERENCE}"
    assert declaration.recommended_value == REFERENCE
    assert declaration.recommendation_digest == canonical_digest(lock)


def test_a_lock_without_a_builder_declares_the_contract_and_no_provenance() -> None:
    """Precondition: a lock with the contract but no build mnemonic. Action: build the
    declarations. Postcondition: the description is the contract at the reference and
    nothing more, and the display value still shows the contract."""
    declaration = authorization_declarations({}, _lock(contract="ubuntu-24.04@11"))["base-image"]

    assert declaration.description == f"Execute base ubuntu-24.04@11 at {REFERENCE}."
    assert declaration.display_value == f"ubuntu-24.04@11 \u2014 {REFERENCE}"


def test_a_lock_written_before_contracts_is_described_by_its_builder_and_the_legacy_recipe() -> None:
    """Precondition: a lock with a build mnemonic but neither contract nor recipe source,
    as locks predating recorded contracts are. Action: build the declarations.
    Postcondition: the base is described as selected by the lock, credited to the builder,
    with the recipe linked at its legacy path, and the display value shows the builder."""
    declaration = authorization_declarations({}, _lock(**{"build-mnemonic": "v0.2.7"}))["base-image"]

    assert declaration.description == (
        f"Execute the base at {REFERENCE}, selected by the platform lock, built by v0.2.7; "
        f"recipe source: {REPOSITORY}/blob/v0.2.7/{LEGACY_RECIPE_SOURCE_PATH}."
    )
    assert declaration.display_value == f"v0.2.7 \u2014 {REFERENCE}"


def test_a_lock_without_a_base_declares_no_base_image_decision() -> None:
    """Precondition: a lock with no base table. Action: build the declarations.
    Postcondition: there is no base-image declaration to answer."""
    assert "base-image" not in authorization_declarations({}, {"components": {}})
