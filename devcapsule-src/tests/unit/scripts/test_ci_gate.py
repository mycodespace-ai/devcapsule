"""Unit tests of ``scripts/ci_gate.py``: the hosted gate fails closed on routing and on every selected job."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "ci_gate.py"


def _load(path: Path) -> Any:
    """The script as a module."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load(_SCRIPT)


def _needs(python: str = "true", docs: str = "true") -> dict[str, Any]:
    """The ``needs`` context of a run in which routing and both jobs succeeded."""
    return {
        "changes": {"result": "success", "outputs": {"python": python, "docs": docs}},
        "pytest": {"result": "success"},
        "docs-build": {"result": "success"},
    }


def test_the_gate_passes_when_every_selected_job_succeeded() -> None:
    """Precondition: both routes selected, routing and both jobs successful. Action: check.
    Postcondition: nothing is raised."""
    gate.check(_needs())


def test_the_gate_passes_when_an_unselected_job_was_skipped() -> None:
    """Precondition: neither route selected, and both jobs skipped. Action: check.
    Postcondition: nothing is raised; a skip is legitimate only for a job its route left out."""
    needs = _needs("false", "false")
    needs["pytest"]["result"] = needs["docs-build"]["result"] = "skipped"
    gate.check(needs)


@pytest.mark.parametrize("job", ["changes", "pytest", "docs-build"])
@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", None])
def test_a_selected_job_that_did_not_succeed_fails_the_gate(job: str, result: str | None) -> None:
    """Precondition: both routes selected, and one of routing or the two jobs failed, was
    cancelled, was skipped, or reported nothing. Action: check. Postcondition: ``ValueError``."""
    needs = _needs()
    needs[job]["result"] = result
    with pytest.raises(ValueError):
        gate.check(needs)


@pytest.mark.parametrize("route", ["python", "docs"])
@pytest.mark.parametrize("value", ["", None, True, "TRUE", "unknown"])
def test_a_route_that_is_not_true_or_false_fails_the_gate(route: str, value: Any) -> None:
    """Precondition: every job successful, and one route output that is not the string ``true``
    or ``false``. Action: check. Postcondition: ``ValueError``."""
    needs = _needs()
    needs["changes"]["outputs"][route] = value
    with pytest.raises(ValueError):
        gate.check(needs)


def test_failed_routing_fails_the_gate_although_both_jobs_were_skipped() -> None:
    """Precondition: routing failed after reporting neither route selected, so both jobs were
    skipped. Action: check. Postcondition: ``ValueError``; skipped children cannot pass a gate
    whose routing did not succeed."""
    needs = _needs("false", "false")
    needs["changes"]["result"] = "failure"
    needs["pytest"]["result"] = needs["docs-build"]["result"] = "skipped"
    with pytest.raises(ValueError):
        gate.check(needs)
