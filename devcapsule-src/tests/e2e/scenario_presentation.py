"""Repository scenario adapter for the shipped presentation producer.

Public operations are the producer exports and ``plan_for_scenario`` with
this test harness's script root.
"""
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from devcapsule.presentation_tools.producer import (
    PRESENTATION_FILE as PRESENTATION_FILE,
    PresentationError as PresentationError,
    PresentationPlan as PresentationPlan,
    Script as Script,
    ScriptStep as ScriptStep,
    parse_script as parse_script,
    plan_for_scenario as _plan_for_scenario,
    plan_presentation as plan_presentation,
    write_presentation as write_presentation,
)

E2E_ROOT = Path(__file__).resolve().parent


def plan_for_scenario(scenario: Mapping[str, Any], root: Path = E2E_ROOT) -> PresentationPlan | None:
    """Read a repository scenario's script relative to its E2E directory."""
    return _plan_for_scenario(scenario, root)
