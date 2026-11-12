"""Laws of configuration admission/resolution, independent of launch machinery.

The predecessor is an external oracle: v0.2.11 produced both its inputs and
its resolved meaning. The current implementation must interpret that evidence.
It must not manufacture the expected plan with its own resolver.
"""
from copy import deepcopy
from pathlib import Path
import tomllib

import pytest

from devcapsule.configuration import Configuration, Resolution, HostAccess, ProjectConfigurationError
from devcapsule.configuration.file_formats import canonical_digest

pytestmark = pytest.mark.legacy


@pytest.fixture
def predecessor_documents():
    """Decode released evidence; only the fixture's path-derived digest is rebound.

    No checkout, home directory, environment, Docker or CLI is needed. The
    literal checkout-path placeholder is a valid identity for this unit test;
    physical path ownership belongs to the file adapter tests.
    """
    source = Path(__file__).parents[1] / "resources/compat/v0.2.11"
    def read(relative):
        return tomllib.loads((source / relative).read_text())
    manifest = read("project/.devcapsule/devcapsule.toml")
    lock = read("project/.devcapsule/devcapsule.linux-amd64.lock")
    checkout = read("checkout/devcapsule.checkout.toml")
    saved = read("checkout/devcapsule.resolved.toml")
    saved["sources"]["checkout-input"] = canonical_digest(checkout)
    return manifest, lock, checkout, saved


@pytest.fixture
def predecessor(predecessor_documents):
    manifest, lock, checkout, saved = predecessor_documents
    return Configuration(manifest, lock, checkout), Resolution(saved)


def test_supported_predecessor_needs_no_new_decisions(predecessor):
    configuration, saved_plan = predecessor

    assert configuration.review().ready
    assert configuration.accept(saved_plan) == ()


def test_resolving_supported_predecessor_preserves_its_meaning(predecessor):
    configuration, saved_plan = predecessor

    assert configuration.resolve().same_meaning_as(saved_plan)
    assert saved_plan.component == "pycharm"
    assert saved_plan.project_mount == "/workspace/project"
    assert saved_plan.base_reference == (
        "docker.io/mycodespaceai/devcapsule-base@sha256:"
        "4bb691b556a2cb9acffa4c0adddd9ada66864ee3c81f4f00ca35e9df9056bf9c"
    )
    # The old implicit X11 default is not a recorded grant. Display selection
    # belongs to a different ADT and must not be smuggled into configuration.
    assert saved_plan.host_access == HostAccess(host_browser=True, host_x11=None)


def test_resolution_is_repeatable_and_accepted_by_its_configuration(predecessor):
    configuration, saved_plan = predecessor
    resolved = configuration.resolve()

    assert configuration.accept(resolved) == ()
    assert configuration.resolve().same_meaning_as(resolved)
    assert configuration.accept(saved_plan) == ()


def test_observation_order_cannot_change_configuration(predecessor):
    configuration, saved_plan = predecessor
    before = configuration.review()

    configuration.accept(saved_plan)
    configuration.resolve()
    configuration.stale_inputs(saved_plan)

    assert configuration.review() == before
    assert configuration.resolve().same_meaning_as(saved_plan)


@pytest.mark.parametrize("change", ["workflow", "display-name"])
def test_metadata_changes_preserve_predecessor_meaning(predecessor_documents, change):
    manifest, lock, checkout, saved = predecessor_documents
    if change == "workflow":
        manifest["workflow"] = {"mode": "multiple-streams"}
    else:
        manifest["project"]["name"] = "A new display name"
    changed = Configuration(manifest, lock, checkout)
    saved_plan = Resolution(saved)

    assert changed.accept(saved_plan) == ()
    assert changed.resolve().same_meaning_as(saved_plan)


def test_ordinary_project_change_requires_resolution_but_not_renewed_consent(predecessor_documents):
    manifest, lock, checkout, saved = predecessor_documents
    original = Configuration(manifest, lock, checkout)
    manifest["project"]["mount"] = "/workspace/relocated"
    changed = Configuration(manifest, lock, checkout)
    saved_plan = Resolution(saved)

    assert changed.review().ready
    assert changed.stale_inputs(saved_plan) == ("manifest",)
    with pytest.raises(ProjectConfigurationError, match="stale"):
        changed.accept(saved_plan)
    resolved = changed.resolve()
    assert changed.accept(resolved) == ()
    assert resolved.project_mount == "/workspace/relocated"
    assert resolved.host_access == saved_plan.host_access
    assert resolved.base_reference == saved_plan.base_reference
    assert original.accept(saved_plan) == ()


@pytest.mark.parametrize("change_base,change_browser", [(True, False), (False, True), (True, True)])
def test_changed_security_questions_require_exactly_the_affected_decisions(
    predecessor_documents, change_base, change_browser,
):
    manifest, lock, checkout, saved = predecessor_documents
    if change_base:
        lock["base"]["reference"] = "docker.io/example/base@sha256:" + "c" * 64
    if change_browser:
        manifest["host"] = {"browser": {"host-open": {"recommended": {
            "value": True, "justification": "Changed browser requirement.",
        }}}}
    changed = Configuration(manifest, lock, checkout)
    # A moved base asks; a changed host recommendation does not: the recorded
    # host answer is kept and disclosed as superseded (D-0012, answer 23 of
    # the CLI UX work order).
    expected = {"base-image"} if change_base else set()

    reviews = {item.name: item for item in changed.review().authorizations}
    assert {name for name, item in reviews.items() if item.problem} == expected
    if change_browser:
        assert reviews["host-browser"].superseded and reviews["host-browser"].problem is None
    if change_base:
        with pytest.raises(ProjectConfigurationError, match="incomplete"):
            changed.resolve()
        with pytest.raises(ProjectConfigurationError, match="incomplete"):
            changed.accept(Resolution(saved), force=True)
    else:
        assert changed.resolve().host_access.host_browser is reviews["host-browser"].value


def test_force_waives_freshness_without_mutating_either_value(predecessor_documents):
    manifest, lock, checkout, saved = predecessor_documents
    manifest["project"]["mount"] = "/workspace/relocated"
    changed = Configuration(manifest, lock, checkout)
    saved_plan = Resolution(saved)

    assert changed.accept(saved_plan, force=True) == ("manifest",)
    assert saved_plan.project_mount == "/workspace/project"
    assert changed.resolve().project_mount == "/workspace/relocated"


# Representation boundary tests. These deliberately manipulate documents;
# the laws above observe the ADT, not hashes, file writes or collaborator calls.
def test_configuration_owns_its_inputs_and_review(predecessor_documents):
    manifest, lock, checkout, saved = predecessor_documents
    configuration = Configuration(manifest, lock, checkout)
    review = configuration.review()
    manifest["project"]["mount"] = "/changed"
    lock["base"]["reference"] = "invalid"
    checkout["authorization"].clear()
    review.values["intruder"] = True

    assert configuration.accept(Resolution(saved)) == ()
    assert configuration.resolve().same_meaning_as(Resolution(saved))
    assert "intruder" not in configuration.review().values


def test_resolution_owns_its_representation(predecessor_documents):
    saved = predecessor_documents[3]
    plan = Resolution(saved)
    exported = plan.document()
    round_trip = Resolution(exported)
    saved["runtime"]["component"] = "corrupted input"
    exported["runtime"]["component"] = "corrupted output"

    assert plan.same_meaning_as(round_trip)
    assert plan.component == "pycharm"


@pytest.mark.parametrize("base", ["not a table", {"reference": 1}, {"reference": ""}])
def test_base_observation_refuses_malformed_representations(predecessor_documents, base):
    saved = predecessor_documents[3]
    saved["authorization"]["base-image"] = base

    with pytest.raises(ProjectConfigurationError):
        Resolution(saved).base_reference


def test_a_plan_without_a_base_selection_reports_absence(predecessor_documents):
    saved = predecessor_documents[3]
    saved["authorization"].pop("base-image")

    assert Resolution(saved).base_reference is None


@pytest.mark.parametrize("artifact,key", [
    (0, "devcapsule-schema-version"), (1, "devcapsule-lock-format-version"),
    (2, "devcapsule-checkout-schema-version"), (3, "devcapsule-resolved-schema-version"),
])
def test_unknown_schema_is_refused_without_changing_the_evidence(predecessor_documents, artifact, key):
    documents = predecessor_documents
    documents[artifact][key] = 99
    before = deepcopy(documents)

    with pytest.raises(ProjectConfigurationError, match="unsupported"):
        Configuration(*documents[:3]).accept(Resolution(documents[3]))
    assert documents == before


def test_checkout_authority_cannot_be_transplanted_to_another_project(predecessor_documents):
    manifest, lock, checkout, _ = predecessor_documents
    manifest["project"]["creator"] = "mailto:another@example.test"

    with pytest.raises(ProjectConfigurationError, match="creator and slug"):
        Configuration(manifest, lock, checkout)


@pytest.mark.parametrize("field,value", [
    ("component", "unknown-surface"), ("project-mount", "/etc"),
    ("memory-limit-bytes", True), ("image", []),
])
def test_force_cannot_admit_an_invalid_runtime(predecessor_documents, field, value):
    manifest, lock, checkout, saved = predecessor_documents
    manifest["project"]["mount"] = "/workspace/changed"  # Actually stale.
    saved["runtime"][field] = value
    configuration = Configuration(manifest, lock, checkout)

    with pytest.raises(ProjectConfigurationError):
        configuration.accept(Resolution(saved), force=True)


@pytest.mark.parametrize("replacement", [False, 1])
def test_fresh_fingerprints_do_not_authorize_changed_meaning(predecessor_documents, replacement):
    manifest, lock, checkout, saved = predecessor_documents
    configuration = Configuration(manifest, lock, checkout)
    original = Resolution(saved)
    saved["authorization"]["host-browser"] = replacement
    changed = Resolution(saved)

    assert not changed.same_meaning_as(original)  # Boolean true also differs from integer 1.
    assert configuration.stale_inputs(changed) == ()
    with pytest.raises(ProjectConfigurationError, match="does not match"):
        configuration.accept(changed)


@pytest.mark.parametrize("missing", ["surface", "environment"])
def test_resolution_requires_an_executable_environment(predecessor_documents, missing):
    manifest, lock, checkout, _ = predecessor_documents
    if missing == "surface":
        lock["components"].pop("interactive-surface")
    else:
        lock.pop("base")
        lock.pop("materialization")
        checkout["authorization"].pop("base-image")
    with pytest.raises(ProjectConfigurationError, match="interactive (surface|component)"):
        Configuration(manifest, lock, checkout).resolve()
