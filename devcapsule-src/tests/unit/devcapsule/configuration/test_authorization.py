"""Unit tests of ``devcapsule.configuration.authorization``: the decisions a checkout carries.

Every lock here is built by the test. The base-image declaration is derived
from the lock, so each expected value is computed from the inputs the test
chose, never read from a run or from this repository's own lock.
"""
from __future__ import annotations

from typing import Any

import pytest

from devcapsule.components.claude_code import CLAUDE_CODE_AUTHORIZATION, CLAUDE_CODE_TERMS_URL
from devcapsule.configuration.authorization import (
    AuthorizationReview, authorization_declarations, authorization_deny_value, current_authorization_name,
    normalize_authorization_value, retired_authorization_notice, review_authorizations,
)
from devcapsule.configuration.file_formats import ProjectConfigurationError, canonical_digest
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


NO_BASE_LOCK: dict[str, Any] = {"components": {}}
"""A lock that asks no base and no download, so that the host accesses are all it declares."""


def _home_default_digest(name: str) -> str:
    """The digest a launcher records with an answer to the home default ``name``."""
    return canonical_digest({"name": name, "recommendation": "home-default"})


def _ssh_proxy_review(authorization: dict[str, Any]) -> AuthorizationReview:
    """The review of ``ssh-proxy`` for a checkout that records ``authorization``, which must be the only
    review of either of its names and leave no entry unsupported."""
    reviews = review_authorizations({}, NO_BASE_LOCK, {"authorization": authorization})
    assert [item.name for item in reviews if item.status == "unsupported"] == []
    assert "github-ssh" not in {item.name for item in reviews}
    (review,) = (item for item in reviews if item.name == "ssh-proxy")
    return review


def test_the_ssh_proxy_is_available_but_never_recommended_by_omission() -> None:
    """A project without recommendations exposes the optional SSH proxy decision without granting it. Its
    grant of reference is the word ``default``, it denies with ``false``, and its retired name declares nothing."""
    declarations = authorization_declarations({}, NO_BASE_LOCK)
    declaration = declarations['ssh-proxy']

    assert declaration.recommended_value == "default"
    assert declaration.project_recommended is False
    assert declaration.required is False
    assert authorization_deny_value(declaration) is False
    assert 'github-ssh' not in declarations


@pytest.mark.parametrize("given,recorded", [
    ("default", "default"), ("DEFAULT", "default"), ("none", False), ("false", False), (False, False),
    ("true", True), (True, True), ("id_work", "id_work"), ("~/keys/deploy", "~/keys/deploy"), ("/keys/deploy", "/keys/deploy"),
])
def test_the_ssh_proxy_takes_a_denial_the_two_words_and_any_well_spelled_key(given: Any, recorded: Any) -> None:
    """``default`` records that word, ``none`` and ``false`` record the denial, ``true`` records true, and a
    key's name or path is recorded as given: the one authorization whose grant is not a single value."""
    declaration = authorization_declarations({}, NO_BASE_LOCK)['ssh-proxy']

    normalized = normalize_authorization_value(declaration, given)

    assert normalized == recorded and type(normalized) is type(recorded)


@pytest.mark.parametrize("given", ["keys/deploy", "id_%h", " id_work", ""])
def test_a_misspelled_ssh_proxy_key_is_refused_naming_the_authorization(given: str) -> None:
    """A relative path, a name OpenSSH would expand, a padded name and an empty one are refused as answers to ``ssh-proxy``."""
    declaration = authorization_declarations({}, NO_BASE_LOCK)['ssh-proxy']

    with pytest.raises(ProjectConfigurationError, match="^Authorization 'ssh-proxy': "):
        normalize_authorization_value(declaration, given)


def test_another_host_access_still_takes_its_grant_and_its_denial_only() -> None:
    """Opening the value of ``ssh-proxy`` opened no other node: ``host-browser`` refuses a key name."""
    declaration = authorization_declarations({}, NO_BASE_LOCK)['host-browser']

    with pytest.raises(ProjectConfigurationError, match="requires true or false"):
        normalize_authorization_value(declaration, "id_work")


@pytest.mark.parametrize("value,status", [("id_work", "authorized"), ("default", "authorized"), (True, "authorized"), (False, "denied")])
def test_an_answer_recorded_under_the_current_name_is_reviewed_with_no_retired_name(value: Any, status: str) -> None:
    """A checkout that records ``ssh-proxy`` is authorized or denied by that value, with nothing to report."""
    review = _ssh_proxy_review({"ssh-proxy": {"value": value, "recommendation-digest": _home_default_digest("ssh-proxy")}})

    assert (review.status, review.value, review.problem, review.superseded, review.retired_name) == (status, value, None, None, None)


@pytest.mark.parametrize("value,status", [(True, "authorized"), (False, "denied")])
def test_an_answer_recorded_as_github_ssh_keeps_its_meaning_and_is_reported(value: bool, status: str) -> None:
    """A checkout as the launcher before the rename left it, ``github-ssh`` bound to that name's home
    default, is reviewed as ``ssh-proxy`` with the same value: no problem, not superseded by the rename,
    and the retired name it was found under is told."""
    review = _ssh_proxy_review({"github-ssh": {"value": value, "recommendation-digest": _home_default_digest("github-ssh")}})

    assert (review.status, review.value, review.problem, review.superseded) == (status, value, None, None)
    assert review.recorded == str(value).lower()
    assert review.retired_name == "github-ssh"


def test_the_current_name_outranks_the_retired_one_in_the_same_checkout() -> None:
    """A checkout that holds both names is answered by ``ssh-proxy``; the retired entry is still reported, to be removed."""
    review = _ssh_proxy_review({
        "github-ssh": {"value": True, "recommendation-digest": _home_default_digest("github-ssh")},
        "ssh-proxy": {"value": "id_work", "recommendation-digest": _home_default_digest("ssh-proxy")},
    })

    assert (review.status, review.value, review.problem, review.retired_name) == ("authorized", "id_work", None, "github-ssh")


def test_a_retired_answer_bound_to_another_digest_than_its_home_default_stays_superseded() -> None:
    """Only the rename is forgiven: a ``github-ssh`` answer bound to some other recommendation is kept and
    disclosed as superseded, as any host answer whose question changed."""
    review = _ssh_proxy_review({"github-ssh": {"value": True, "recommendation-digest": "another recommendation"}})

    assert (review.status, review.value, review.problem, review.retired_name) == ("authorized", True, None, "github-ssh")
    assert review.superseded == "the project no longer recommends it"


def test_an_invalid_answer_under_the_retired_name_is_a_problem_of_the_current_node() -> None:
    """A ``github-ssh`` entry that is no answer is reported as invalid on ``ssh-proxy``, with choices that
    name ``ssh-proxy``: recording any of them replaces the retired entry."""
    review = _ssh_proxy_review({"github-ssh": {"value": "keys/deploy", "recommendation-digest": _home_default_digest("github-ssh")}})

    assert review.status == "invalid" and review.problem is not None and "ssh-proxy" in review.problem
    assert [(choice.name, choice.value) for choice in review.choices] == [("ssh-proxy", "default"), ("ssh-proxy", "false")]


def test_a_retired_name_on_a_command_line_is_taken_with_a_note_that_it_will_be_removed() -> None:
    """``github-ssh`` stands for ``ssh-proxy`` and has a notice that names both and the removal; a current
    name stands for itself and has none."""
    assert current_authorization_name("github-ssh") == "ssh-proxy"
    assert retired_authorization_notice("github-ssh") == (
        "Note: authorization 'github-ssh' is 'ssh-proxy' now. The old name still works "
        "and will be removed in a later release."
    )
    for name in ("ssh-proxy", "network", "no-such-access"):
        assert current_authorization_name(name) == name
        assert retired_authorization_notice(name) is None


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
