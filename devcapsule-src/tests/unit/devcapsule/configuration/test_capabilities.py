"""Unit tests of ``devcapsule/configuration/capabilities.py``: requirement grammar, version comparison, and launch departures."""
from __future__ import annotations

from typing import Any

import pytest

from devcapsule.configuration.capabilities import (
    IDE_REQUIREMENT,
    CapabilityPolicy,
    LocalCapabilities,
    RequirementDeparture,
    meets_minimum,
    version_parts,
)
from devcapsule.configuration.file_formats import ProjectConfigurationError

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


@pytest.mark.parametrize("actual,minimum,accepted", [
    ("25.0.4+7", "21", True), ("v22.23.1", "22.23.1", True),
    ("1.10", "1.9", True), ("1.9", "1.10", False),
    ("3.12", "3.12.0", True), ("3.12.0.0", "3.12", True),
    ("3.12", "3.14", False), ("25.0.4+7", "25.0.4+99", True),
])
def test_dotted_integer_comparison(actual: str, minimum: str, accepted: bool) -> None:
    """``meets_minimum`` compares dotted integer version components numerically and ignores build suffixes."""
    assert meets_minimum(actual, minimum) is accepted


@pytest.mark.parametrize("value", ["3.14rc1", "3.14-rc.1", "3.x", "3..1", "3.14.*", "", "3.14+beta"])
def test_unsupported_version_forms_are_explicit(value: str) -> None:
    """Prerelease, wildcard, and empty version strings are rejected by ``version_parts`` and ``CapabilityPolicy.read``."""
    with pytest.raises(ProjectConfigurationError, match="[Uu]nsupported"):
        version_parts(value)
    with pytest.raises(ProjectConfigurationError, match="[Uu]nsupported"):
        CapabilityPolicy.read({"capabilities": {"required": [f"python>={value}"]}})


@pytest.mark.parametrize("value", ["python=3", "python>3", "python<=3", "python>=3,<4", "python >=3"])
def test_only_minimum_relation_is_supported(value: str) -> None:
    """Only the ``>=`` minimum-version operator without whitespace is accepted in capability requirement entries."""
    with pytest.raises(ProjectConfigurationError, match="[Uu]nsupported"):
        CapabilityPolicy.read({"capabilities": {"required": [value]}})


@pytest.mark.parametrize("value", [{"python": 3}, {"python": True}, {"future": "opaque"}])
def test_old_table_is_ignored_and_never_written(value: dict[str, Any]) -> None:
    """Legacy ``sdk-major`` tables are ignored when reading a capability policy and omitted from ``document()``."""
    policy = CapabilityPolicy.read({"capabilities": {"required": ["python"], "sdk-major": value}})
    assert policy.document() == {"required": ["python"], "optional": []}


@pytest.mark.parametrize("value", [
    {"unknown": []}, {"selected": ["python"], "without": ["python"]},
    {"lock": 4}, {"selected": "python"}, {"without": [False]},
])
def test_invalid_local_selections_are_refused(value: dict[str, Any]) -> None:
    """Malformed or contradictory checkout capability selections raise ``ProjectConfigurationError``."""
    with pytest.raises(ProjectConfigurationError):
        LocalCapabilities.read({"capabilities": value})

