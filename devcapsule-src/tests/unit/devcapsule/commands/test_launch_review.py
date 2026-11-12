"""Unit tests of ``devcapsule/commands/_launch_review.py``: what ``project run`` decides, from values.

Every test builds its checkout in memory: a manifest written out here, the
lock the product derives from it, and the record ``project init`` would
leave. No test has a project directory or a home. The paths below are names
that the decisions print; nothing opens them.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tomllib
from typing import Any

import pytest

from devcapsule.commands._launch_review import RunFlags, flags_after_upgrade, review_launch, stage_trust
from devcapsule.compat import DecisionPending
from devcapsule.configuration.authorization import authorization_declarations, normalize_authorization_value
from devcapsule.configuration.bindings import HostDirectory
from devcapsule.configuration.capabilities import (
    IDE_REQUIREMENT, CapabilityPolicy, LocalCapabilities, RequirementDeparture, resolution_recommendations,
)
from devcapsule.configuration.capability_selection import generate_lock
from devcapsule.configuration.derivation import CheckoutState, Host, Selection
from devcapsule.configuration.file_formats import ProjectConfigurationError, canonical_digest, render_checkout, render_toml
from devcapsule.configuration.listing import Decision
from devcapsule.configuration.manifest import current_manifest
from devcapsule.configuration.manifest_document import Recommendations
from devcapsule.configuration.operations import CheckoutRecord
from devcapsule.configuration.trust import BASE_CHANNEL, BASE_REPOSITORY, HomeTrust, base_channel, channels_for
from devcapsule.configuration.values import memory_size_bytes
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

ROOT = Path("/projects/order")
HOME = Path("/homes/developer")
RECORD = HOME / "projects" / "order" / "devcapsule.checkout.toml"

ACCEPTED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
"""The time the test's host tells."""

REQUIRING_PYCHARM = ("python", "python-ide", "codex-agent")
"""The work order's project: PyCharm required beside an unrelated mandatory tool."""
REQUIRING_NO_IDE = ("python",)


def no_local_image(reference: str) -> Any:
    """The daemon of a host that must not be asked for an image."""
    pytest.fail(f"the review asked the Docker daemon for {reference}")


def a_host(*, variables: tuple[str, ...] = (), directories: tuple[str, ...] = (), local_image: Any = no_local_image) -> Host:
    """A host whose shell sets ``variables``, on which ``directories`` exist, and whose clock shows ``ACCEPTED_AT``.

    A directory resolves to its name under ``/resolved``, so that a test can
    tell the resolved path from the name the developer gave. Asked for a local
    image, the host fails the test unless ``local_image`` is given.
    """
    def directory(name: str) -> HostDirectory:
        return HostDirectory(Path(name), Path("/resolved") / name.lstrip("~/"), name in directories)

    return Host(local_image=local_image, now=lambda: ACCEPTED_AT,
                environment={name: "a value no decision reads" for name in variables}, directory=directory)


def checkout_of(required: tuple[str, ...], *, ide: str | None = "python-ide", host: Host | None = None,
                manifest_tables: dict[str, Any] | None = None, offered: tuple[str, ...] = (),
                recommended: dict[str, str] | None = None, base_authorized: bool = True) -> CheckoutState:
    """A registered checkout of a project that requires ``required``, in a home that has accepted nothing.

    Its host is ``a_host()`` unless ``host`` is given. ``manifest_tables`` are
    further tables of the manifest, ``environment`` for instance. ``offered``
    are capabilities the project offers and does not require. ``recommended``
    are the components the project recommends, by capability, as ``config
    recommend`` records them.

    It is what ``project init --require ... --ide IDE --authorize base-image
    default`` leaves, built with the operations that command uses and no file:
    the lock derived from the policy, the IDE pinned on the record, the base
    image authorized for this checkout. With ``ide`` None the checkout has
    chosen no IDE. With ``base_authorized`` false the checkout has not
    authorized the base, which is then for the home's trust to answer.
    """
    manifest: dict[str, Any] = {
        "devcapsule-schema-version": 2,
        "project": {"name": "order", "slug": "order", "creator": "mailto:owner@example.test", "mount": "/workspace/order"},
        "capabilities": {"required": sorted(required), **({"optional": sorted(offered)} if offered else {}),
                         **({"resolution": dict(recommended)} if recommended else {})},
        **(manifest_tables or {}),
    }
    state = CheckoutState(
        root=ROOT, manifest=manifest, platform=Platform.LINUX_AMD64,
        lock_path=ROOT / ".devcapsule" / "devcapsule.linux-amd64.lock",
        shared_lock=generate_lock(CapabilityPolicy.read(manifest), MATRICES[Platform.LINUX_AMD64],
                                  recommendations=resolution_recommendations(manifest)),
        home={}, home_path=HOME, input_path=RECORD, registered=True,
        host=host or a_host(),
        checkout=tomllib.loads(render_checkout(manifest, ROOT, {}, {})),
    )
    selection = Selection(LocalCapabilities.read(state.checkout), state.surfaces)
    selection.ide = ide
    record = CheckoutRecord.staged(RECORD, state.with_selection(selection))
    if base_authorized:
        base_image = authorization_declarations(manifest, state.composed_lock(record.document))["base-image"]
        record.authorize(base_image, normalize_authorization_value(base_image, "default"))
    state.checkout = record.export()
    return state


def never_asked(*arguments: Any) -> None:
    """An ``ask`` for a review that must not reach the developer."""
    pytest.fail("the review asked the developer")


def never_announced(line: str) -> None:
    """An ``announce`` for a review that has nothing to tell the developer."""
    pytest.fail(f"the review announced {line!r}")


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
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "pycharm"
    assert review.selected.departures == ()
    assert "departures" not in review.selected.resolution
    assert "codex" in review.selected.lock["components"]


@pytest.mark.parametrize("named", ["pycharm", "python-ide", " python-ide "])
def test_the_required_ide_can_be_named_by_component_or_capability(named: str) -> None:
    """``--ide`` given the required IDE's component or its capability, spaces aside, selects it with no departure."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide=named), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "pycharm"
    assert review.selected.departures == ()


def test_another_ide_than_the_required_one_is_refused_naming_the_override() -> None:
    """``--ide codium`` against a required PyCharm is refused with both IDEs and the ``--force`` command named,
    and leaves the state's documents and departures as they were."""
    state = checkout_of(REQUIRING_PYCHARM)
    before = deepcopy((state.checkout, state.home))

    with pytest.raises(ProjectConfigurationError) as refused:
        review_launch(state, RunFlags(ide="codium"), ask=None, announce=never_announced)

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
        review_launch(checkout_of(REQUIRING_PYCHARM), flags, ask=None, announce=never_announced)


def test_an_unknown_ide_is_refused_with_the_platforms_ides() -> None:
    """``--ide`` given a name no IDE has is refused, and the refusal lists the IDE capabilities to choose from."""
    with pytest.raises(ProjectConfigurationError, match="Unknown IDE 'emacs'; choose one of .*python-ide"):
        review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="emacs"), ask=None, announce=never_announced)


def test_a_forced_ide_still_waits_for_its_vendors_channel() -> None:
    """``--ide vscode --force`` without a terminal ends pending on Microsoft's channel: ``--force`` sets the IDE
    requirement aside and accepts nothing. The home's trust and the checkout's record are as they were."""
    state = checkout_of(REQUIRING_PYCHARM)
    before = deepcopy((state.checkout, state.home))

    with pytest.raises(DecisionPending) as pending:
        review_launch(state, RunFlags(ide="vscode", force=True), ask=None, announce=never_announced)

    message = str(pending.value)
    assert "trust vscode" in message and "--trust vscode" in message
    assert f"launched from this DevCapsule home, `{HOME}`" in message
    assert "Nothing was written" in message
    assert (state.checkout, state.home) == before


def test_a_forced_ide_is_planned_once_its_channel_is_accepted() -> None:
    """When the developer accepts the one channel asked, the forced launch plans Visual Studio Code with the IDE
    requirement recorded as this launch's departure. The acceptance is staged for the home with the time the
    host tells, and the record staged for writing still has PyCharm saved."""
    asked: list[Decision] = []

    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="vscode", force=True), ask=accepting(asked), announce=never_announced)

    assert [(decision.kind, decision.name) for decision in asked] == [("trust", "vscode")]
    assert review.selected.resolution["runtime"]["component"] == "vscode"
    assert review.selected.departures == (RequirementDeparture(IDE_REQUIREMENT, "python-ide", "vscode-ide"),)
    assert review.accepted == ["vscode"]
    assert review.state.home["trust"]["channels"]["vscode"]["accepted"] == "2026-01-02T03:04:05+00:00"
    assert LocalCapabilities.read(review.record.document).selected == ("python-ide",)
    assert review.record.document == review.original


def test_the_channel_can_be_accepted_on_the_command_line() -> None:
    """``--trust vscode`` beside the forced IDE settles the channel without a terminal."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="vscode", force=True, trust=("vscode",)), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "vscode"
    assert review.accepted == ["vscode"]


def test_print_only_never_asks() -> None:
    """Under ``print_only`` a pending channel ends the review as pending although a terminal is there to ask."""
    with pytest.raises(DecisionPending, match="trust vscode"):
        review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide="vscode", force=True), ask=never_asked, announce=never_announced, print_only=True)


@pytest.mark.parametrize(("flags", "refusal"), [
    (RunFlags(force=True), "--force names no departure"),
    (RunFlags(ide="codium", force=True, save=True), "cannot be combined with --save"),
])
def test_a_command_line_that_contradicts_itself_is_refused(flags: RunFlags, refusal: str) -> None:
    """``--force`` without ``--ide``, and ``--force`` with ``--save``, are refused whatever the project requires."""
    with pytest.raises(ProjectConfigurationError, match=refusal):
        review_launch(checkout_of(REQUIRING_PYCHARM), flags, ask=never_asked, announce=never_announced)


@pytest.mark.parametrize(("required", "ide", "refusal"), [
    (REQUIRING_PYCHARM, "pycharm", "--force has nothing to set aside: python-ide is the project's required IDE"),
    (REQUIRING_NO_IDE, "codium", "--force has nothing to set aside: the project requires no IDE; '--ide codium' alone launches frontend-ide"),
])
def test_force_with_no_requirement_to_set_aside_is_refused(required: tuple[str, ...], ide: str, refusal: str) -> None:
    """``--force`` is refused when the named IDE is the required one, and when the project requires none."""
    with pytest.raises(ProjectConfigurationError, match=refusal):
        review_launch(checkout_of(required), RunFlags(ide=ide, force=True), ask=never_asked, announce=never_announced)


def test_another_ide_needs_no_force_where_none_is_required() -> None:
    """In a project that requires no IDE, ``--ide codium`` plans VSCodium for this launch and leaves PyCharm saved."""
    review = review_launch(checkout_of(REQUIRING_NO_IDE), RunFlags(ide="codium"), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "codium"
    assert review.selected.departures == ()
    assert LocalCapabilities.read(review.record.document).selected == ("python-ide",)


def test_run_once_resources_are_overrides_of_the_launch_and_not_of_the_record() -> None:
    """``--memory`` and ``--cpus`` without ``--save`` come back as this launch's overrides; the record is unchanged."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(memory="8g", cpus="2"), ask=None, announce=never_announced)

    assert (review.memory_override, review.cpus_override) == (8 * 1024 ** 3, 2)
    assert review.saved is False
    assert review.record.document == review.original
    prepared = review.prepared()
    assert (prepared.memory_override, prepared.cpus_override) == (8 * 1024 ** 3, 2)
    assert prepared.selected is review.selected


def test_saved_resources_are_staged_on_the_record() -> None:
    """With ``--save``, ``--memory`` is staged on the checkout's record as its value, and the review says it is saved."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(memory="8g", save=True), ask=None, announce=never_announced)

    assert review.saved is True
    assert review.record.document != review.original
    assert memory_size_bytes(str(review.record.values["memory"])) == 8 * 1024 ** 3


def test_a_run_once_authorization_is_announced_and_overrides_this_launch_only() -> None:
    """``--authorize network host`` without ``--save`` is announced at once, comes back as this launch's host
    override, and is not staged on the record."""
    announced: list[str] = []

    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(authorize=(("network", "host"),)),
                           ask=None, announce=announced.append)

    assert announced == ["Run-once authorization: network = host"]
    assert review.host_overrides == {"network": "host"}
    assert review.record.document == review.original


def test_a_local_base_image_is_looked_up_on_the_host_by_its_reference() -> None:
    """A checkout whose base authorization names a local image has that reference looked up through the host;
    when the host has no such image, the review ends with the host's refusal."""
    asked: list[str] = []

    def no_such_image(reference: str) -> Any:
        asked.append(reference)
        raise ProjectConfigurationError(f"no local image {reference}")

    state = checkout_of(REQUIRING_PYCHARM, host=a_host(local_image=no_such_image))
    record = CheckoutRecord.staged(RECORD, state.checkout)
    base_image = authorization_declarations(state.manifest, state.composed_lock())["base-image"]
    record.authorize(base_image, "local/devcapsule-base:work", image_identity="sha256:" + "a" * 64)
    state.checkout = record.export()

    with pytest.raises(ProjectConfigurationError, match="no local image local/devcapsule-base:work"):
        review_launch(state, RunFlags(), ask=None, announce=never_announced)

    assert asked == ["local/devcapsule-base:work"]


NEEDING_A_TOKEN: dict[str, Any] = {"environment": {"required": {"SERVICE_TOKEN": {"reason": "the service's API"}}}}
"""A manifest table that makes the project need the variable ``SERVICE_TOKEN``."""


def test_a_variable_taken_from_the_host_must_be_set_in_the_developers_shell() -> None:
    """A required variable that the checkout takes from the host, on a host whose shell does not set it, leaves
    the review pending on that variable."""
    state = checkout_of(REQUIRING_PYCHARM, host=a_host(variables=()), manifest_tables=NEEDING_A_TOKEN)
    state.saved_environment = {"SERVICE_TOKEN": None}

    with pytest.raises(DecisionPending, match="env SERVICE_TOKEN: The bound host variable is missing in this shell"):
        review_launch(state, RunFlags(), ask=None, announce=never_announced)


def test_a_variable_taken_from_the_host_is_settled_when_the_shell_sets_it() -> None:
    """The same checkout on a host whose shell sets the variable is planned without a question."""
    state = checkout_of(REQUIRING_PYCHARM, host=a_host(variables=("SERVICE_TOKEN",)), manifest_tables=NEEDING_A_TOKEN)
    state.saved_environment = {"SERVICE_TOKEN": None}

    review = review_launch(state, RunFlags(), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "pycharm"


def bound_home(directory: str, host: Host) -> CheckoutState:
    """The order's checkout with its ``home`` state bound to a directory of the host, as ``config bind`` records it."""
    state = checkout_of(REQUIRING_PYCHARM, host=host)
    record = CheckoutRecord.staged(RECORD, state.checkout)
    record.directory_bindings["home"] = directory
    state.checkout = record.export()
    return state


def test_a_bound_directory_the_host_does_not_have_refuses_the_plan() -> None:
    """A checkout bound to a directory that does not exist on the host is refused, naming the path as the host
    resolved it."""
    state = bound_home("~/capsule-home", a_host(directories=()))

    with pytest.raises(ProjectConfigurationError, match="binding 'home' is not an existing directory: /resolved/capsule-home"):
        review_launch(state, RunFlags(), ask=None, announce=never_announced)


def test_a_bound_directory_the_host_has_is_planned_by_its_resolved_path() -> None:
    """A checkout bound to a directory that exists on the host is planned with the path as the host resolved it,
    and the launch's checkout keeps the name the developer gave."""
    state = bound_home("~/capsule-home", a_host(directories=("~/capsule-home",)))

    review = review_launch(state, RunFlags(), ask=None, announce=never_announced)

    assert review.selected.resolution["state"]["bindings"] == {"home": "/resolved/capsule-home"}
    assert review.selected.checkout["configuration"]["bindings"]["host-directory"] == {"home": "~/capsule-home"}


@pytest.mark.parametrize("named", ["codium", "frontend-ide"])
def test_a_forced_ide_replaces_the_required_one_and_keeps_every_other_requirement(named: str) -> None:
    """``--ide codium --force`` against a required PyCharm plans VSCodium, by component or capability name, with
    the departure in the plan. PyCharm is not in the launch's lock; the unrelated mandatory tool is. The
    project's policy and the record staged for writing are as they were; only the launch's own copy of the
    checkout selects the other IDE."""
    review = review_launch(checkout_of(REQUIRING_PYCHARM), RunFlags(ide=named, force=True), ask=None, announce=never_announced)

    selected = review.selected
    assert selected.departures == (RequirementDeparture(IDE_REQUIREMENT, "python-ide", "frontend-ide"),)
    assert selected.resolution["runtime"]["component"] == "codium"
    assert selected.resolution["departures"] == {IDE_REQUIREMENT: {"required": "python-ide", "launched": "frontend-ide"}}
    components = selected.lock["components"]
    assert components["interactive-surface"] == "codium" and "codium" in components
    assert "pycharm" not in components
    assert "codex" in components
    assert CapabilityPolicy.read(selected.manifest).required == ("codex-agent", "python", "python-ide")
    assert review.record.document == review.original
    assert LocalCapabilities.read(review.record.document).selected == ("python-ide",)
    assert "frontend-ide" in LocalCapabilities.read(selected.checkout).selected


def test_a_forced_ide_is_planned_from_a_saved_version_set() -> None:
    """A checkout that saved its version set, PyCharm's, is still planned with VSCodium under ``--force``: the
    departure is in the plan, PyCharm is not in the launch's lock, and the saved set is not staged for change."""
    state = checkout_of(REQUIRING_PYCHARM)
    state.checkout["version-set"] = {"format": 1, "lock": render_toml(state.composed_lock()),
                                     "recommendation-digest": canonical_digest(state.shared_lock)}

    review = review_launch(state, RunFlags(ide="codium", force=True), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "codium"
    assert review.selected.resolution["departures"][IDE_REQUIREMENT]["required"] == "python-ide"
    assert "pycharm" not in review.selected.lock["components"]
    assert "codex" in review.selected.lock["components"]
    assert review.record.document == review.original


def requiring_minimums(*requirements: str) -> CheckoutState:
    """The order's checkout after its owner rewrote the requirements with minimum versions; lock and record are older."""
    state = checkout_of(REQUIRING_PYCHARM)
    state.manifest["capabilities"]["required"] = list(requirements)
    return state


@pytest.mark.parametrize("required_ide", ["python-ide", "pycharm"])
def test_force_has_nothing_to_set_aside_when_the_required_ide_is_named_by_another_spelling(required_ide: str) -> None:
    """Whether the project requires the IDE by capability or by component name, ``--ide python-ide --force`` is
    refused: the two names are the same IDE."""
    state = requiring_minimums("python>=3", f"{required_ide}>=9999", "codex-agent")

    with pytest.raises(ProjectConfigurationError, match="nothing to set aside"):
        review_launch(state, RunFlags(ide="python-ide", force=True), ask=None, announce=never_announced)


@pytest.mark.parametrize("required_ide", ["python-ide", "pycharm"])
def test_a_departure_waives_the_minimum_of_the_ide_it_sets_aside(required_ide: str) -> None:
    """With a minimum on the required IDE that no version meets, a forced VSCodium is planned, and the plan
    names the requirement as the project declared it."""
    state = requiring_minimums("python>=3", f"{required_ide}>=9999", "codex-agent")

    review = review_launch(state, RunFlags(ide="codium", force=True), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "codium"
    assert review.selected.resolution["departures"][IDE_REQUIREMENT]["required"] == required_ide


def test_a_departure_waives_no_other_minimum() -> None:
    """A minimum on Python that no version meets still refuses the forced launch: only the IDE's is waived."""
    state = requiring_minimums("python>=9999", "python-ide>=9999", "codex-agent")

    with pytest.raises(ProjectConfigurationError, match="python.*9999"):
        review_launch(state, RunFlags(ide="codium", force=True), ask=None, announce=never_announced)


def test_a_schema_one_manifest_recommends_its_ide_and_another_needs_no_force() -> None:
    """A schema-1 manifest's ``need`` list, read as this launcher reads it, requires no IDE: ``--ide codium``
    without ``--force`` plans VSCodium with no departure and stages no change to the record."""
    state = checkout_of(REQUIRING_PYCHARM)
    state.manifest = current_manifest({
        "devcapsule-schema-version": 1,
        "project": dict(state.manifest["project"]),
        "capabilities": {"need": ["python", "python-ide", "codex-agent"]},
    }, "the project's manifest").document()

    review = review_launch(state, RunFlags(ide="codium"), ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "codium"
    assert review.selected.departures == () and "departures" not in review.selected.resolution
    assert review.record.document == review.original


def offering_claude_code() -> CheckoutState:
    """A checkout of a project that requires Python and offers the Claude Code agent, with VSCodium saved."""
    return checkout_of(("python",), ide="frontend-ide", offered=("claude-code-agent",))


def test_an_offered_agent_still_waits_for_its_vendors_channel() -> None:
    """An agent the project only offers is in the launch unless the checkout omits it, so printing the launch's
    command ends pending on its vendor's channel, and the state's documents are as they were."""
    state = offering_claude_code()
    before = deepcopy((state.checkout, state.home))

    with pytest.raises(DecisionPending, match="trust claude-code"):
        review_launch(state, RunFlags(), ask=None, announce=never_announced, print_only=True)

    assert (state.checkout, state.home) == before


def test_an_offered_agent_the_checkout_omits_is_not_in_the_plan() -> None:
    """When the checkout omits the offered agent, the launch is planned without a question and the agent's
    component is not in its lock."""
    state = offering_claude_code()
    selection = Selection(LocalCapabilities.read(state.checkout), state.surfaces)
    selection.without.add("claude-code-agent")
    state.checkout = state.with_selection(selection)

    review = review_launch(state, RunFlags(), ask=None, announce=never_announced, print_only=True)

    assert review.selected.resolution["runtime"]["component"] == "codium"
    assert "claude-code" not in review.selected.lock["components"]


def test_choosing_an_agent_and_a_vendors_ide_accepts_neither_vendors_channel() -> None:
    """A checkout that adds the Claude Code agent and chooses Visual Studio Code for its IDE, in a home that has
    accepted nothing, ends pending on Anthropic's channel and on Microsoft's: a selection is not a consent."""
    state = checkout_of(("node",), ide="frontend-ide")
    selection = Selection(LocalCapabilities.read(state.checkout), state.surfaces)
    selection.extra.add("claude-code-agent")
    selection.use(state.matrix, CapabilityPolicy.read(state.manifest), Recommendations.read(state.manifest), "frontend-ide", "vscode")
    state.checkout = state.with_selection(selection)

    with pytest.raises(DecisionPending) as pending:
        review_launch(state, RunFlags(), ask=None, announce=never_announced)

    assert "trust claude-code: Trust Anthropic to supply Claude Code" in str(pending.value)
    assert "trust vscode: Trust Microsoft to supply Visual Studio Code" in str(pending.value)



def recommended_by_the_project() -> tuple[CheckoutState, RunFlags]:
    """The project recommends Visual Studio Code for ``frontend-ide``; the checkout selects that IDE and chooses nothing."""
    return checkout_of(("python",), ide="frontend-ide", recommended={"frontend-ide": "vscode"}), RunFlags(memory="6g", save=True)


def chosen_on_the_checkout() -> tuple[CheckoutState, RunFlags]:
    """The checkout's record chooses Visual Studio Code for ``frontend-ide``, as ``config use`` leaves it."""
    state = checkout_of(("python",), ide="frontend-ide")
    selection = Selection(LocalCapabilities.read(state.checkout), state.surfaces)
    selection.use(state.matrix, CapabilityPolicy.read(state.manifest), Recommendations.read(state.manifest), "frontend-ide", "vscode")
    state.checkout = state.with_selection(selection)
    return state, RunFlags(memory="6g", save=True)


def named_for_this_run() -> tuple[CheckoutState, RunFlags]:
    """Neither the project nor the checkout chooses; ``--provider frontend-ide=vscode`` does, on the command line."""
    return checkout_of(("python",), ide="frontend-ide"), RunFlags(providers=(("frontend-ide", "vscode"),), memory="6g", save=True)


@pytest.mark.parametrize("chosen", [recommended_by_the_project, chosen_on_the_checkout, named_for_this_run])
def test_a_provider_choice_accepts_no_channel_and_a_pending_save_stages_nothing(chosen: Any) -> None:
    """Visual Studio Code, whether the project recommends it, the checkout chose it or the command line names it,
    leaves a launch with ``--memory 6g --save`` pending on Microsoft's channel: choosing a provider accepts
    nothing. The state's record and home are as they were, the memory included, so there is no part of the save
    to write."""
    state, flags = chosen()
    before = deepcopy((state.checkout, state.home))

    with pytest.raises(DecisionPending, match="trust vscode: Trust Microsoft to supply Visual Studio Code"):
        review_launch(state, flags, ask=None, announce=never_announced)

    assert (state.checkout, state.home) == before


def test_with_no_provider_chosen_the_same_saving_launch_is_planned_with_the_default_one() -> None:
    """With no recommendation, choice or flag, ``frontend-ide`` is VSCodium, which waits for no channel: the
    launch with ``--memory 6g --save`` is planned and the memory is staged on the record."""
    review = review_launch(checkout_of(("python",), ide="frontend-ide"), RunFlags(memory="6g", save=True),
                           ask=None, announce=never_announced)

    assert review.selected.resolution["runtime"]["component"] == "codium"
    assert memory_size_bytes(str(review.record.values["memory"])) == 6 * 1024 ** 3


def adding_claude_code() -> CheckoutState:
    """The order's checkout after its developer added the Claude Code agent, which the project neither requires nor offers."""
    state = checkout_of(REQUIRING_PYCHARM)
    selection = Selection(LocalCapabilities.read(state.checkout), state.surfaces)
    selection.extra.add("claude-code-agent")
    state.checkout = state.with_selection(selection)
    return state


def test_an_agent_the_developer_added_waits_for_its_vendors_channel_and_names_both_ways_to_accept() -> None:
    """An agent added on the checkout brings its vendor's channel with it: the launch ends pending on Anthropic's,
    and the message names the flag for this launch and the ``home trust accept`` command."""
    with pytest.raises(DecisionPending) as pending:
        review_launch(adding_claude_code(), RunFlags(), ask=None, announce=never_announced)

    message = str(pending.value)
    assert "trust claude-code: Trust Anthropic to supply Claude Code" in message
    assert "--trust claude-code  |  devcapsule home trust accept claude-code" in message


def test_the_checkouts_own_authorization_of_a_vendors_download_settles_it_without_the_home() -> None:
    """When the checkout's record authorizes the Claude Code download itself, the launch is planned with Claude
    Code in its lock. No channel is accepted for the home, and the home's settings are as they were."""
    state = adding_claude_code()
    record = CheckoutRecord.staged(RECORD, state.checkout)
    download = authorization_declarations(state.manifest, state.composed_lock())["claude-code-download"]
    record.authorize(download, normalize_authorization_value(download, "true"))
    state.checkout = record.export()

    review = review_launch(state, RunFlags(), ask=None, announce=never_announced)

    assert review.selected.lock["components"]["claude-code"]["version"]
    assert review.accepted == []
    assert review.state.home == {}


def leaving_the_base_to_the_home(*, ide: str | None = "python-ide") -> CheckoutState:
    """A checkout of a project that requires Node, which has not authorized its base image: DevCapsule's
    published base, for the home's trust of the channel ``devcapsule-base`` to answer."""
    return checkout_of(("node",), ide=ide, base_authorized=False)


def test_a_base_channel_the_home_has_not_accepted_leaves_the_launch_pending_naming_the_trust_flag() -> None:
    """With the base neither authorized on the checkout nor trusted by the home, the launch ends pending on
    DevCapsule's channel and names ``--trust devcapsule-base``. The home's settings are as they were."""
    state = leaving_the_base_to_the_home()

    with pytest.raises(DecisionPending, match="--trust devcapsule-base"):
        review_launch(state, RunFlags(), ask=None, announce=never_announced)

    assert state.home == {}


def test_the_trust_flag_accepts_the_channel_for_the_home_and_the_published_base_is_planned() -> None:
    """``--trust devcapsule-base`` settles the base without a terminal: the plan authorizes DevCapsule's
    published base, the acceptance is staged for the home with the time the host tells, and nothing about the
    base is staged on the checkout's record."""
    review = review_launch(leaving_the_base_to_the_home(), RunFlags(trust=(BASE_CHANNEL,)), ask=None, announce=never_announced)

    assert review.selected.resolution["authorization"]["base-image"]["reference"].startswith(BASE_REPOSITORY + "@")
    assert review.accepted == [BASE_CHANNEL]
    assert review.state.home["trust"]["channels"][BASE_CHANNEL]["accepted"] == "2026-01-02T03:04:05+00:00"
    assert "base-image" not in review.record.document.get("authorization", {})
    assert review.record.document == review.original


def test_a_home_that_trusts_the_base_channel_plans_the_launch_without_a_question() -> None:
    """In a home that has accepted DevCapsule's channel, the same checkout is planned with nothing asked and
    nothing newly accepted."""
    state = leaving_the_base_to_the_home()
    state.home = {"trust": HomeTrust().with_channel(base_channel(), accepted_at=ACCEPTED_AT).document()}

    review = review_launch(state, RunFlags(), ask=never_asked, announce=never_announced)

    assert review.selected.resolution["authorization"]["base-image"]["reference"].startswith(BASE_REPOSITORY + "@")
    assert review.accepted == []


def test_a_trust_flag_beside_another_unanswered_decision_still_ends_pending() -> None:
    """With no IDE chosen and no terminal, ``--trust devcapsule-base`` answers the channel and the launch
    still ends pending on the IDE alone: the message says nothing was written."""
    state = leaving_the_base_to_the_home(ide=None)

    with pytest.raises(DecisionPending) as pending:
        review_launch(state, RunFlags(trust=(BASE_CHANNEL,)), ask=None, announce=never_announced)

    message = str(pending.value)
    assert "ide ide: Your IDE for this checkout" in message
    assert "trust devcapsule-base" not in message
    assert "Nothing was written" in message


def test_trusting_a_channel_the_project_does_not_use_is_refused_naming_its_channels() -> None:
    """``--trust codex`` on a project whose only channel is DevCapsule's base is refused, and the refusal lists
    the project's channels."""
    with pytest.raises(ProjectConfigurationError, match="No channel 'codex' on this project; its channels: devcapsule-base"):
        review_launch(leaving_the_base_to_the_home(), RunFlags(trust=("codex",)), ask=None, announce=never_announced)


SAVED_ORIGIN = "https://selected.example.test"
"""Where the checkout's saved version set takes Claude Code from, which is not where the project's lock does."""


def with_a_saved_set_from_another_origin() -> CheckoutState:
    """A checkout of a project that requires the Claude Code agent, with a saved version set whose Claude Code
    comes from ``SAVED_ORIGIN``."""
    state = checkout_of(("python", "python-ide", "claude-code-agent"))
    saved = state.composed_lock()
    for artifact in saved["components"]["claude-code"]["artifacts"].values():
        artifact["url"] = f"{SAVED_ORIGIN}/claude"
    state.checkout["version-set"] = {"format": 1, "lock": render_toml(saved),
                                     "recommendation-digest": canonical_digest(state.shared_lock)}
    return state


def test_the_trust_flag_accepts_the_channel_as_the_checkouts_saved_version_set_names_it() -> None:
    """``--trust claude-code`` accepts the channel of the checkout's saved version set: the origin staged for
    the home is the saved set's, not the project lock's, and the download is authorized in the plan."""
    state = with_a_saved_set_from_another_origin()
    assert SAVED_ORIGIN not in channels_for(state.shared_lock)["claude-code"].origins

    review = review_launch(state, RunFlags(trust=("claude-code",)), ask=None, announce=never_announced)

    assert review.state.home["trust"]["channels"]["claude-code"]["origins"] == [SAVED_ORIGIN]
    assert review.selected.resolution["authorization"]["claude-code-download"] is True


def test_the_question_put_to_the_developer_names_the_channel_of_the_saved_version_set() -> None:
    """Without the flag, the one decision put to the developer describes Claude Code's channel with the saved
    set's origin and not the project lock's; accepted, that origin is what is staged for the home."""
    state = with_a_saved_set_from_another_origin()
    (shared_origin,) = channels_for(state.shared_lock)["claude-code"].origins
    asked: list[Decision] = []

    review = review_launch(state, RunFlags(), ask=accepting(asked), announce=never_announced)

    assert [(decision.kind, decision.name) for decision in asked] == [("trust", "claude-code")]
    assert SAVED_ORIGIN in asked[0].description and shared_origin not in asked[0].description
    assert review.state.home["trust"]["channels"]["claude-code"]["origins"] == [SAVED_ORIGIN]


def test_the_second_review_is_given_this_launchs_flags_without_trust_and_without_save() -> None:
    """After an upgrade, flags that were for this launch only are given again, but for ``--trust``; a host
    access allowed once at the terminal is given as its ``--authorize`` flag."""
    flags = RunFlags(ide="codium", memory="6g", environment=("A=1",), trust=("claude-code",), allow_unverified=True)

    again = flags_after_upgrade(flags, {"network": "host"})

    assert again == RunFlags(ide="codium", memory="6g", environment=("A=1",), authorize=(("network", "host"),), allow_unverified=True)


def test_the_second_review_is_given_none_of_the_flags_that_were_saved() -> None:
    """With ``--save`` the flags are the checkout's answers by the second review: none is given again, except
    the permission for unverified combinations, which is never saved."""
    flags = RunFlags(ide="codium", memory="6g", authorize=(("network", "host"),), trust=("claude-code",), save=True, allow_unverified=True)

    assert flags_after_upgrade(flags, {}) == RunFlags(allow_unverified=True)


def test_a_channel_that_an_upgrade_moved_is_pending_in_the_second_review_and_the_acceptance_is_not_widened() -> None:
    """The first review accepted Claude Code's channel by flag. An upgrade then moves Claude Code to another
    origin. The second review, given the flags that remain, ends pending on the channel, and the home still
    holds the origin that was accepted and no other."""
    flags = RunFlags(trust=("claude-code",))
    state = checkout_of(("python", "python-ide", "claude-code-agent"))
    first = review_launch(state, flags, ask=None, announce=never_announced)
    accepted_origins = list(first.state.home["trust"]["channels"]["claude-code"]["origins"])
    upgraded = first.state.composed_lock()
    for artifact in upgraded["components"]["claude-code"]["artifacts"].values():
        artifact["url"] = "https://unaccepted.example.test/claude"
    state.checkout["version-set"] = {"format": 1, "lock": render_toml(upgraded),
                                     "recommendation-digest": canonical_digest(state.shared_lock)}

    with pytest.raises(DecisionPending, match="trust claude-code"):
        review_launch(state, flags_after_upgrade(flags, first.host_overrides), ask=None, announce=never_announced)

    assert state.home["trust"]["channels"]["claude-code"]["origins"] == accepted_origins
