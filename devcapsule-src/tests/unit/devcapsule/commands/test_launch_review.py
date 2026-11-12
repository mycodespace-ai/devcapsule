"""Unit tests of ``devcapsule/commands/_launch_review.py``: what ``project run`` decides, from values.

Every test builds its checkout in memory: a manifest written out here, the
lock the product derives from it, and the record ``project init`` would
leave. No test has a project directory or a home. The paths below are names
that the decisions print; nothing opens them.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib
from typing import Any

import pytest

from devcapsule.commands._launch_review import RunFlags, review_launch, stage_trust
from devcapsule.compat import DecisionPending
from devcapsule.configuration.authorization import authorization_declarations, normalize_authorization_value
from devcapsule.configuration.capabilities import IDE_REQUIREMENT, CapabilityPolicy, LocalCapabilities, RequirementDeparture
from devcapsule.configuration.capability_selection import generate_lock
from devcapsule.configuration.derivation import CheckoutState, Selection
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_checkout
from devcapsule.configuration.listing import Decision
from devcapsule.configuration.operations import CheckoutRecord
from devcapsule.configuration.values import memory_size_bytes
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

ROOT = Path("/projects/order")
HOME = Path("/homes/developer")
RECORD = HOME / "projects" / "order" / "devcapsule.checkout.toml"

REQUIRING_PYCHARM = ("python", "python-ide", "codex-agent")
"""The work order's project: PyCharm required beside an unrelated mandatory tool."""
REQUIRING_NO_IDE = ("python",)


def checkout_of(required: tuple[str, ...], *, ide: str = "python-ide") -> CheckoutState:
    """A registered checkout of a project that requires ``required``, in a home that has accepted nothing.

    It is what ``project init --require ... --ide IDE --authorize base-image
    default`` leaves, built with the operations that command uses and no file:
    the lock derived from the policy, the IDE pinned on the record, the base
    image authorized for this checkout.
    """
    manifest: dict[str, Any] = {
        "devcapsule-schema-version": 2,
        "project": {"name": "order", "slug": "order", "creator": "mailto:owner@example.test", "mount": "/workspace/order"},
        "capabilities": {"required": sorted(required)},
    }
    state = CheckoutState(
        root=ROOT, manifest=manifest, platform=Platform.LINUX_AMD64,
        lock_path=ROOT / ".devcapsule" / "devcapsule.linux-amd64.lock",
        shared_lock=generate_lock(CapabilityPolicy.read(manifest), MATRICES[Platform.LINUX_AMD64]),
        home={}, home_path=HOME, input_path=RECORD, registered=True,
        checkout=tomllib.loads(render_checkout(manifest, ROOT, {}, {})),
    )
    selection = Selection(LocalCapabilities.read(state.checkout), state.surfaces)
    selection.ide = ide
    record = CheckoutRecord.staged(RECORD, state.with_selection(selection))
    base_image = authorization_declarations(manifest, state.composed_lock(record.document))["base-image"]
    record.authorize(base_image, normalize_authorization_value(base_image, "default"))
    state.checkout = record.export()
    return state


def never_asked(*arguments: Any) -> None:
    """An ``ask`` for a review that must not reach the developer."""
    pytest.fail("the review asked the developer")


def accepting(asked: list[Decision]) -> Any:
    """An ``ask`` that accepts every channel put to it, as a developer answering yes, and lists what was asked."""
    def ask(state: CheckoutState, record: CheckoutRecord, checkout: dict[str, Any], decision: Decision,
            host_overrides: dict[str, Any], environment: dict[str, str | None], accepted: list[str], flags: RunFlags) -> None:
        asked.append(decision)
        assert decision.kind == "trust", decision
        stage_trust(state, checkout, decision.name, accepted)
    return ask


def test_the_saved_required_ide_is_planned_without_a_question() -> None:
    """With PyCharm required and saved and the base authorized, the review derives a PyCharm plan with no departure."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(), ask=None)

    assert review.selected.resolution["runtime"]["component"] == "pycharm"
    assert review.selected.departures == ()
    assert "departures" not in review.selected.resolution
    assert "codex" in review.selected.lock["components"]


@pytest.mark.parametrize("named", ["pycharm", "python-ide", " python-ide "])
def test_the_required_ide_can_be_named_by_component_or_capability(named: str) -> None:
    """``--ide`` given the required IDE's component or its capability, spaces aside, selects it with no departure."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide=named), ask=None)

    assert review.selected.resolution["runtime"]["component"] == "pycharm"
    assert review.selected.departures == ()


def test_another_ide_than_the_required_one_is_refused_naming_the_override() -> None:
    """``--ide codium`` against a required PyCharm is refused with both IDEs and the ``--force`` command named,
    and leaves the state's documents and departures as they were."""
    state = checkout_of(REQUIRING_PYCHARM)
    before = deepcopy((state.checkout, state.home))

    with pytest.raises(ProjectConfigurationError) as refused:
        review_launch(state, RunFlags(ide="codium"), ask=None)

    message = str(refused.value)
    assert "The project requires python-ide (pycharm); frontend-ide (codium) is another IDE" in message
    assert f"devcapsule project --path {ROOT} run --ide codium --force" in message
    assert "saved IDE stay as they are" in message
    assert (state.checkout, state.home) == before
    assert state.departures == ()


def test_the_ide_request_is_judged_before_any_other_flag() -> None:
    """With another IDE than the required one and an authorization that cannot be answered for one run, both on
    the command line, the refusal is the IDE's: the request is judged before any approval is reviewed."""
    flags = RunFlags(ide="codium", authorize=(("no-such-access", "allow"),))

    with pytest.raises(ProjectConfigurationError, match="frontend-ide \\(codium\\) is another IDE"):
        review_launch(checkout_of(REQUIRING_PYCHARM), flags, ask=None)


def test_an_unknown_ide_is_refused_with_the_platforms_ides() -> None:
    """``--ide`` given a name no IDE has is refused, and the refusal lists the IDE capabilities to choose from."""
    with pytest.raises(ProjectConfigurationError, match="Unknown IDE 'emacs'; choose one of .*python-ide"):
        review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="emacs"), ask=None)


def test_a_forced_ide_still_waits_for_its_vendors_channel() -> None:
    """``--ide vscode --force`` without a terminal ends pending on Microsoft's channel: ``--force`` sets the IDE
    requirement aside and accepts nothing. The home's trust and the checkout's record are as they were."""
    state = checkout_of(REQUIRING_PYCHARM)
    before = deepcopy((state.checkout, state.home))

    with pytest.raises(DecisionPending) as pending:
        review_launch(state, RunFlags(ide="vscode", force=True), ask=None)

    message = str(pending.value)
    assert "trust vscode" in message and "--trust vscode" in message
    assert f"launched from this DevCapsule home, `{HOME}`" in message
    assert "Nothing was written" in message
    assert (state.checkout, state.home) == before


def test_a_forced_ide_is_planned_once_its_channel_is_accepted() -> None:
    """When the developer accepts the one channel asked, the forced launch plans Visual Studio Code with the IDE
    requirement recorded as this launch's departure. The acceptance is staged for the home, and the record
    staged for writing still has PyCharm saved."""
    asked: list[Decision] = []

    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="vscode", force=True), ask=accepting(asked))

    assert [(decision.kind, decision.name) for decision in asked] == [("trust", "vscode")]
    assert review.selected.resolution["runtime"]["component"] == "vscode"
    assert review.selected.departures == (RequirementDeparture(IDE_REQUIREMENT, "python-ide", "vscode-ide"),)
    assert review.accepted == ["vscode"]
    assert "vscode" in review.state.home["trust"]["channels"]
    assert LocalCapabilities.read(review.record.document).selected == ("python-ide",)
    assert review.record.document == review.original


def test_the_channel_can_be_accepted_on_the_command_line() -> None:
    """``--trust vscode`` beside the forced IDE settles the channel without a terminal."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="vscode", force=True, trust=("vscode",)), ask=None)

    assert review.selected.resolution["runtime"]["component"] == "vscode"
    assert review.accepted == ["vscode"]


def test_print_only_never_asks() -> None:
    """Under ``print_only`` a pending channel ends the review as pending although a terminal is there to ask."""
    with pytest.raises(DecisionPending, match="trust vscode"):
        review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="vscode", force=True), ask=never_asked, print_only=True)


@pytest.mark.parametrize(("flags", "refusal"), [
    (RunFlags(force=True), "--force names no departure"),
    (RunFlags(ide="codium", force=True, save=True), "cannot be combined with --save"),
])
def test_a_command_line_that_contradicts_itself_is_refused(flags: RunFlags, refusal: str) -> None:
    """``--force`` without ``--ide``, and ``--force`` with ``--save``, are refused whatever the project requires."""
    with pytest.raises(ProjectConfigurationError, match=refusal):
        review_launch(checkout_of(REQUIRING_PYCHARM), flags, ask=never_asked)


@pytest.mark.parametrize(("required", "ide", "refusal"), [
    (REQUIRING_PYCHARM, "pycharm", "--force has nothing to set aside: python-ide is the project's required IDE"),
    (REQUIRING_NO_IDE, "codium", "--force has nothing to set aside: the project requires no IDE; '--ide codium' alone launches frontend-ide"),
])
def test_force_with_no_requirement_to_set_aside_is_refused(required: tuple[str, ...], ide: str, refusal: str) -> None:
    """``--force`` is refused when the named IDE is the required one, and when the project requires none."""
    with pytest.raises(ProjectConfigurationError, match=refusal):
        review_launch(checkout_of(required), RunFlags(ide=ide, force=True), ask=never_asked)


def test_another_ide_needs_no_force_where_none_is_required() -> None:
    """In a project that requires no IDE, ``--ide codium`` plans VSCodium for this launch and leaves PyCharm saved."""
    review = review_launch(checkout_of(REQUIRING_NO_IDE), RunFlags(ide="codium"), ask=None)

    assert review.selected.resolution["runtime"]["component"] == "codium"
    assert review.selected.departures == ()
    assert LocalCapabilities.read(review.record.document).selected == ("python-ide",)


def test_run_once_resources_are_overrides_of_the_launch_and_not_of_the_record() -> None:
    """``--memory`` and ``--cpus`` without ``--save`` come back as this launch's overrides; the record is unchanged."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(memory="8g", cpus="2"), ask=None)

    assert (review.memory_override, review.cpus_override) == (8 * 1024 ** 3, 2)
    assert review.saved is False
    assert review.record.document == review.original
    prepared = review.prepared()
    assert (prepared.memory_override, prepared.cpus_override) == (8 * 1024 ** 3, 2)
    assert prepared.selected is review.selected


def test_saved_resources_are_staged_on_the_record() -> None:
    """With ``--save``, ``--memory`` is staged on the checkout's record as its value, and the review says it is saved."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(memory="8g", save=True), ask=None)

    assert review.saved is True
    assert review.record.document != review.original
    assert memory_size_bytes(str(review.record.values["memory"])) == 8 * 1024 ** 3
