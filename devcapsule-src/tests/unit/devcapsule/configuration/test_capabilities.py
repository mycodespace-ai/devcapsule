"""Unit tests of ``devcapsule/configuration/capabilities.py``: a launch's departure from a project's requirement."""
from __future__ import annotations

from devcapsule.configuration.capabilities import IDE_REQUIREMENT, CapabilityPolicy, RequirementDeparture

REQUIRING_PYCHARM = CapabilityPolicy(
    ("python", "python-ide"), ("browser-automation",), (("python", "3.12"), ("python-ide", "2026")),
)
"""A policy that requires Python and PyCharm, each with a minimum version, and offers one optional capability."""


def test_departing_sets_aside_the_named_requirement_and_its_minimum() -> None:
    """A departure from the required IDE gives a policy without that requirement and without its minimum;
    the other requirement, its minimum and the optional capability stay."""
    departed = REQUIRING_PYCHARM.departing((RequirementDeparture(IDE_REQUIREMENT, "python-ide", "frontend-ide"),))

    assert departed == CapabilityPolicy(("python",), ("browser-automation",), (("python", "3.12"),))


def test_departing_from_a_capability_the_policy_does_not_require_changes_nothing() -> None:
    """A departure that names a capability the policy does not require returns the policy itself."""
    departure = RequirementDeparture(IDE_REQUIREMENT, "java-ide", "frontend-ide")

    assert REQUIRING_PYCHARM.departing((departure,)) is REQUIRING_PYCHARM


def test_departing_with_no_departure_changes_nothing() -> None:
    """With no departure the policy itself is returned."""
    assert REQUIRING_PYCHARM.departing(()) is REQUIRING_PYCHARM
