"""Unit tests for ``tests.e2e.todo_demo_controller``."""
from __future__ import annotations

import pytest

from tests.e2e.todo_demo_controller import DemoStep


def test_demo_step_parse_accepts_launch_browser_with_url() -> None:
    """``DemoStep.parse`` accepts ``launch_browser`` when given a non-empty target URL."""
    step = DemoStep.parse(
        {
            "action": "launch_browser",
            "text": "http://127.0.0.1:15173",
            "reason": "Open web application",
        }
    )

    assert step.action == "launch_browser"
    assert step.text == "http://127.0.0.1:15173"
    assert step.reason == "Open web application"


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "unknown"},
        {"action": "click", "x": 1600, "y": 10},
        {"action": "click", "x": 10, "y": -1},
        {"action": "wait", "ms": -5},
        {"action": "type", "text": ""},
        {"action": "press"},
        {"action": "launch_browser", "text": ""},
    ],
)
def test_demo_step_parse_rejects_out_of_range_or_empty_inputs(payload: dict[str, object]) -> None:
    """``DemoStep.parse`` raises ``ValueError`` when action, coordinates, wait duration, or required text is invalid."""
    with pytest.raises(ValueError):
        DemoStep.parse(payload)
