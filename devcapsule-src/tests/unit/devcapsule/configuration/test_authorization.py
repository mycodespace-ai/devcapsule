"""Unit tests of ``devcapsule.configuration.authorization``: the decisions a checkout carries.

Every lock here is built by the test. The base-image declaration is derived
from the lock, so each expected value is computed from the inputs the test
chose, never read from a run or from this repository's own lock.
"""
from __future__ import annotations

from typing import Any

from devcapsule.components.claude_code import CLAUDE_CODE_AUTHORIZATION, CLAUDE_CODE_TERMS_URL
from devcapsule.configuration.authorization import AuthorizationReview, authorization_declarations, review_authorizations
from devcapsule.configuration.file_formats import canonical_digest
from devcapsule.configuration.trust import HomeTrust, channels_for
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


def _lock_with_claude_code() -> dict[str, Any]:
    """A platform lock that pins Claude Code, downloaded from its vendor, on the base at ``REFERENCE``."""
    lock = _lock()
    lock["platform"] = "linux-amd64"
    lock["components"]["claude-code"] = {
        "version": "2.1.227", "delivery-policy": "local-materialization",
        "acquisition-authorization": CLAUDE_CODE_AUTHORIZATION, "terms-url": CLAUDE_CODE_TERMS_URL,
        "artifacts": {"linux-amd64": {"url": "https://downloads.claude.ai/example/claude", "sha256": "c" * 64}},
    }
    return lock


def _checkout_answering(lock: dict[str, Any], download: bool | None) -> dict[str, Any]:
    """A checkout record that authorizes the lock's base, and answers the Claude Code download unless ``download`` is None."""
    authorization: dict[str, Any] = {"base-image": {"reference": REFERENCE, "lock-digest": canonical_digest(lock)}}
    if download is not None:
        digest = authorization_declarations({}, lock)[CLAUDE_CODE_AUTHORIZATION].recommendation_digest
        authorization[CLAUDE_CODE_AUTHORIZATION] = {"value": download, "recommendation-digest": digest}
    return {"authorization": authorization}


def _trusting_every_channel_of(lock: dict[str, Any]) -> HomeTrust:
    """The trust record of a home whose user accepted each channel the lock's software comes through."""
    trust = HomeTrust()
    for channel in channels_for(lock).values():
        trust = trust.with_channel(channel)
    return trust


def _download_review(lock: dict[str, Any], checkout: dict[str, Any], trust: HomeTrust) -> AuthorizationReview:
    """The review of the Claude Code download among all the reviews of the checkout."""
    (review,) = (item for item in review_authorizations({}, lock, checkout, trust) if item.name == CLAUDE_CODE_AUTHORIZATION)
    return review


def test_a_vendor_download_that_neither_the_home_nor_the_checkout_answered_stops_the_launch() -> None:
    """With Claude Code in the lock, a home that trusts no channel and a checkout that says nothing of the
    download, the review of the download is unanswered and carries a problem: the environment cannot run."""
    lock = _lock_with_claude_code()

    review = _download_review(lock, _checkout_answering(lock, download=None), HomeTrust())

    assert (review.status, review.recorded, review.trusted_channel) == ("missing-required", "unanswered", None)
    assert review.problem is not None and "An explicit decision is required" in review.problem


def test_a_vendor_download_is_answered_by_the_home_that_trusts_its_channel() -> None:
    """The same checkout under a home that accepted Anthropic's channel has the download answered by the
    home: no problem, and the review names the channel."""
    lock = _lock_with_claude_code()

    review = _download_review(lock, _checkout_answering(lock, download=None), _trusting_every_channel_of(lock))

    assert (review.status, review.recorded, review.trusted_channel, review.problem) == ("trusted", "home", "claude-code", None)


def test_a_checkouts_denial_of_a_vendor_download_outranks_the_homes_trust() -> None:
    """A checkout that recorded a denial of the download keeps it under a home that trusts the channel: the
    review is a denial with a problem, and the home's channel does not answer it."""
    lock = _lock_with_claude_code()

    review = _download_review(lock, _checkout_answering(lock, download=False), _trusting_every_channel_of(lock))

    assert (review.status, review.trusted_channel) == ("denied", None)
    assert review.problem is not None and "The selected Claude Code acquisition is denied" in review.problem


def test_a_checkouts_own_grant_answers_a_vendor_download_under_a_home_that_trusts_nothing() -> None:
    """A checkout that recorded its own grant of the download needs no channel accepted for the home: the
    review is authorized, with no problem."""
    lock = _lock_with_claude_code()

    review = _download_review(lock, _checkout_answering(lock, download=True), HomeTrust())

    assert (review.status, review.value, review.problem) == ("authorized", True, None)


def test_a_trusted_channel_does_not_cover_an_artifact_that_moved_to_another_origin() -> None:
    """A home accepted Claude Code's channel as one lock named it. Under a lock whose artifact comes from
    another origin the acceptance does not answer the download: it is unanswered again, with a problem."""
    accepted = _lock_with_claude_code()
    moved = _lock_with_claude_code()
    moved["components"]["claude-code"]["artifacts"]["linux-amd64"]["url"] = "https://mirror.example.test/claude"

    review = _download_review(moved, _checkout_answering(moved, download=None), _trusting_every_channel_of(accepted))

    assert (review.status, review.trusted_channel) == ("missing-required", None)
    assert review.problem is not None


def test_a_trusted_channel_covers_another_version_from_the_same_origin() -> None:
    """The same acceptance answers the download of a later version that comes from the origin accepted: trust
    is given to the channel, not to a version."""
    accepted = _lock_with_claude_code()
    later = _lock_with_claude_code()
    later["components"]["claude-code"]["version"] = "2.2.0"
    later["components"]["claude-code"]["artifacts"]["linux-amd64"] = {"url": "https://downloads.claude.ai/later/claude", "sha256": "d" * 64}

    review = _download_review(later, _checkout_answering(later, download=None), _trusting_every_channel_of(accepted))

    assert (review.status, review.trusted_channel, review.problem) == ("trusted", "claude-code", None)
