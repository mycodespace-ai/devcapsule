"""Unit tests for ``tests.e2e.scenario_presentation``."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import pytest

from tests.e2e.scenario_presentation import (
    PresentationError,
    Script,
    ScriptStep,
    parse_script,
    plan_for_scenario,
    plan_presentation,
    write_presentation,
)

SCRIPT_TEXT = """\
# E2E Scenario Script: A Sample

Scenario `sample`. This line is not read.

## Goal

Show that the editor opens
and the stack runs.

## Stack And Capabilities

- **Editor:** VSCodium, the project's `frontend-ide`
- **Database:** PostgreSQL 17,
  on `127.0.0.1:15432`

## What It Illustrates

- The capsule provides the editor.
- The stack runs
  inside the capsule.

## Steps

1. **Open the editor.**
   - *User action:* Launch the capsule
     and wait.
   - *Expected observation:* The editor is open.

2. **Run the stack with `./run.sh`.**
   - *User action:* Run `./run.sh`.
   - *Expected observation:* It prints `READY`.
"""

SCRIPT = Script(
    goal="Show it.",
    stack=(("Editor", "VSCodium"),),
    illustrates=("One thing.",),
    steps=(
        ScriptStep(title="Open the editor", action="Launch it.", expected="It is open."),
        ScriptStep(title="Run the stack", action="Run it.", expected="It prints READY."),
    ),
)


def scenario(*actions: Any, **changes: Any) -> dict[str, Any]:
    """A scenario document for ``SCRIPT`` with the given actions."""
    return {"id": "sample", "title": "A sample", "description": "What happens.", "actions": list(actions), **changes}


def action(reason: str, **fields: Any) -> dict[str, Any]:
    return {"action": "wait", "ms": 150, "reason": reason, **fields}


def test_parse_script_reads_goal_stack_illustrations_and_steps() -> None:
    """``parse_script`` returns the goal as one paragraph, the stack rows, the illustrations and the steps, joining wrapped lines and dropping a title's closing period."""
    parsed = parse_script(SCRIPT_TEXT)

    assert parsed == Script(
        goal="Show that the editor opens and the stack runs.",
        stack=(("Editor", "VSCodium, the project's `frontend-ide`"), ("Database", "PostgreSQL 17, on `127.0.0.1:15432`")),
        illustrates=("The capsule provides the editor.", "The stack runs inside the capsule."),
        steps=(
            ScriptStep(title="Open the editor", action="Launch the capsule and wait.", expected="The editor is open."),
            ScriptStep(title="Run the stack with `./run.sh`", action="Run `./run.sh`.", expected="It prints `READY`."),
        ),
    )


def test_parse_script_accepts_a_script_without_the_optional_sections() -> None:
    """A script with only ``Goal`` and ``Steps`` parses, with an empty stack and no illustrations."""
    text = "## Goal\n\nShow it.\n\n## Steps\n\n1. **Open.**\n   - *User action:* Open it.\n   - *Expected observation:* It is open.\n"

    parsed = parse_script(text)

    assert (parsed.stack, parsed.illustrates, len(parsed.steps)) == ((), (), 1)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (("## Goal", "## Purpose"), "section 'Purpose' is not one of"),
        (("## Steps", "## Goal"), "section 'Goal' appears twice"),
        (("Show that the editor opens\nand the stack runs.\n", ""), "section 'Goal' is missing or empty"),
        (("- **Editor:** VSCodium", "- Editor: VSCodium"), "a stack bullet is '- **Name:** detail'"),
        (("- The capsule provides the editor.", "The capsule provides the editor."), "'What It Illustrates' takes bullets"),
        (("2. **Run the stack", "3. **Run the stack"), "expected step 2, found 3"),
        (("   - *Expected observation:* The editor is open.\n", ""), "step 1 has no 'Expected observation'"),
        (("   - *User action:* Run `./run.sh`.", "   - *User action:* Run `./run.sh`.\n   - *User action:* Again."), "step 2 states 'User action' twice"),
        (("1. **Open the editor.**", "1. Open the editor."), "a step is 'N. **Title.**'"),
        (("1. **Open the editor.**", "1. **.**"), "step 1 has no title"),
    ],
)
def test_parse_script_refuses_a_text_outside_the_form(change: tuple[str, str], message: str) -> None:
    """``parse_script`` raises ``PresentationError`` naming the fault for an unknown or repeated section, an empty goal, a malformed bullet, and a step out of order, incomplete, repeated, unmarked or untitled."""
    old, new = change
    assert old in SCRIPT_TEXT
    text = SCRIPT_TEXT.replace(old, new, 1)

    with pytest.raises(PresentationError, match=re.escape(message)):
        parse_script(text)


def test_timed_places_steps_and_reason_captions_on_the_recording() -> None:
    """Without captions, each action's reason minus its number is a caption, and steps run from the video's start through each step's last action to the video's end."""
    plan = plan_presentation(scenario(action("1. Close the sidebar"), action("1. Trust the folder"), action("2. Type the command")), SCRIPT)

    document = plan.timed([12, 30, 48], 60, 12, video="video.webm", poster="poster.png", screenshots=["a.png", "b.png", "c.png"])

    assert document == {
        "schema_version": 1,
        "scenario_id": "sample",
        "title": "A sample",
        "overview": {
            "summary": "What happens.",
            "intent": "Show it.",
            "illustrates": ["One thing."],
            "stack": [{"name": "Editor", "detail": "VSCodium"}],
        },
        "video": {"file": "video.webm", "poster": "poster.png", "duration": 5.0},
        "steps": [
            {"title": "Open the editor", "action": "Launch it.", "expected": "It is open.", "screenshot": "b.png",
             "start": 0.0, "end": 2.5,
             "captions": [{"start": 0.0, "end": 1.0, "text": "Close the sidebar"}, {"start": 1.0, "end": 2.5, "text": "Trust the folder"}]},
            {"title": "Run the stack", "action": "Run it.", "expected": "It prints READY.", "screenshot": "c.png",
             "start": 2.5, "end": 5.0,
             "captions": [{"start": 2.5, "end": 5.0, "text": "Type the command"}]},
        ],
    }


def test_timed_makes_a_written_caption_last_until_the_next_one() -> None:
    """In a step with captions, a caption starts at the action that has it and lasts through the actions after it that have none."""
    plan = plan_presentation(scenario(
        action("1. Press the key", caption="Quick Open finds the file."), action("1. Wait"), action("1. Type the name"),
        action("1. Press Enter", caption="The file opens."), action("2. Run"),
    ), SCRIPT)

    document = plan.timed([6, 12, 18, 24, 30], 36, 12, video="v.webm", poster="p.png", screenshots=["1", "2", "3", "4", "5"])

    assert document["steps"][0]["captions"] == [
        {"start": 0.0, "end": 1.5, "text": "Quick Open finds the file."},
        {"start": 1.5, "end": 2.0, "text": "The file opens."},
    ]


def test_timed_omits_the_overview_parts_the_script_does_not_state() -> None:
    """A script without stack rows or illustrations gives an overview with the summary and the intent only."""
    bare = Script(goal="Show it.", stack=(), illustrates=(), steps=SCRIPT.steps[:1])
    plan = plan_presentation(scenario(action("1. Open")), bare)

    document = plan.timed([4], 8, 4, video="v.webm", poster="p.png", screenshots=["1.png"])

    assert document["overview"] == {"summary": "What happens.", "intent": "Show it."}


@pytest.mark.parametrize(
    ("frames", "total", "rate", "screenshots", "message"),
    [
        ([12, 30], 60, 12, ["a", "b", "c"], "2 frame counts and 3 screenshots for 3 actions"),
        ([12, 30, 48], 60, 12, ["a", "b"], "3 frame counts and 2 screenshots for 3 actions"),
        ([30, 12, 48], 60, 12, ["a", "b", "c"], "decrease or exceed the total"),
        ([12, 30, 72], 60, 12, ["a", "b", "c"], "decrease or exceed the total"),
        ([12, 30, 48], 60, 0, ["a", "b", "c"], "frames per second must be positive"),
        ([12, 12, 48], 60, 12, ["a", "b", "c"], "step 1 has a caption that lasts no frame"),
    ],
)
def test_timed_refuses_a_run_that_does_not_match_the_plan(
    frames: list[int], total: int, rate: int, screenshots: list[str], message: str,
) -> None:
    """``timed`` raises ``PresentationError`` for counts or screenshots of another length, counts that decrease or pass the total, a rate that is not positive, and a caption without a frame."""
    plan = plan_presentation(scenario(action("1. One"), action("1. Two"), action("2. Three")), SCRIPT)

    with pytest.raises(PresentationError, match=re.escape(message)):
        plan.timed(frames, total, rate, video="v.webm", poster="p.png", screenshots=screenshots)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (scenario(action("1. One"), action("2. Two"), id=" "), "the scenario has no id"),
        (scenario(action("1. One"), action("2. Two"), description=""), "the scenario has no description"),
        (scenario(), "the scenario has no actions"),
        (scenario("press Enter"), "action 1 is not an object"),
        (scenario(action("Close the sidebar"), action("2. Two")), "action 1: its reason must start with the number of its step"),
        (scenario(action("1. One"), action("3. Three")), "action 2 names step 3; the script has steps 1 to 2"),
        (scenario(action("2. Two"), action("1. One")), "action 2 names step 1 after an action of step 2"),
        (scenario(action("1. One"), action("1. More")), "step 2 of the script has no action"),
        (scenario(action("1. One", caption=" "), action("2. Two")), "action 1: its caption must be a non-empty text"),
        (scenario(action("1. One"), action("1. More", caption="Late."), action("2. Two")), "step 1 has captions, so its first action, action 1, needs one"),
    ],
)
def test_plan_presentation_refuses_a_scenario_that_does_not_join_its_script(document: dict[str, Any], message: str) -> None:
    """``plan_presentation`` raises ``PresentationError`` naming a missing id or description, missing or malformed actions, an unnumbered, unknown, backward or absent step, an empty caption, and a captioned step whose first action has none."""
    with pytest.raises(PresentationError, match=re.escape(message)):
        plan_presentation(document, SCRIPT)


def test_plan_for_scenario_reads_the_named_script_below_the_root(tmp_path: Path) -> None:
    """A scenario that names its script is planned from the file at that path below the root."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "sample.md").write_text(SCRIPT_TEXT, encoding="utf-8")

    plan = plan_for_scenario(scenario(action("1. One"), action("2. Two"), script="scripts/sample.md"), tmp_path)

    assert plan is not None
    assert plan.script == parse_script(SCRIPT_TEXT)


def test_plan_for_scenario_plans_nothing_for_a_scenario_without_a_script(tmp_path: Path) -> None:
    """A scenario that names no script has no presentation plan, whatever its actions say."""
    assert plan_for_scenario(scenario(action("Unnumbered")), tmp_path) is None


@pytest.mark.parametrize("named", ["scripts/absent.md", "../outside.md", "/etc/hostname", "", 7])
def test_plan_for_scenario_refuses_a_script_it_cannot_read_below_the_root(tmp_path: Path, named: object) -> None:
    """A named script that is absent, leaves the root, is absolute, or is not a path is a ``PresentationError``, not a missing presentation."""
    with pytest.raises(PresentationError, match="the scenario's script"):
        plan_for_scenario(scenario(action("1. One"), action("2. Two"), script=named), tmp_path)


def test_write_presentation_writes_the_document_as_presentation_json(tmp_path: Path) -> None:
    """``write_presentation`` writes the document as UTF-8 JSON named ``presentation.json`` in the evidence folder and returns that path."""
    document = {"schema_version": 1, "title": "Café · 1600×1000"}

    path = write_presentation(tmp_path, document)

    assert path == tmp_path / "presentation.json"
    assert json.loads(path.read_text(encoding="utf-8")) == document
    assert "Café · 1600×1000" in path.read_text(encoding="utf-8")
