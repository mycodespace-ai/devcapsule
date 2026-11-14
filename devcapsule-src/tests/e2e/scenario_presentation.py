"""The presentation of a recorded scenario: ``presentation.json`` beside its recording.

The web console shows a folder that holds a ``presentation.json`` as slides
beside the recording: an overview, then one slide per step with the step's
text, its screenshot, and its part of the video with captions. The document's
contract is ``devcapsule-webconsole/PRESENTATIONS.md``. This module writes
that document from what a recorded scenario already has, so that a recording
needs no hand-made data to be presented:

- the scenario's JSON: ``id``, ``title``, ``description``, ``script`` (the
  path of its script below ``tests/e2e``) and ``actions``;
- the script, a Markdown file in the form
  ``engineering-docs/development/running-e2e-scenario-recordings.md`` gives:
  the goal, the stack, what the scenario illustrates, and the numbered steps
  with the user's action and the expected observation;
- the count of frames the recorder had taken after each action.

An action belongs to the step whose number starts its ``reason`` ("3. Save
the file"). A step's captions come from its actions: when none of them has a
``caption``, every action's reason, without the number, is its caption; when
some have, a caption starts at each action that has one and lasts until the
next, and the step's first action must have one.

Public operations: ``parse_script``, ``plan_presentation``,
``PresentationPlan.timed``, ``plan_for_scenario`` and ``write_presentation``.
They raise ``PresentationError`` for a script or a scenario that cannot be
presented; the message names what to correct.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

__all__ = [
    "E2E_ROOT",
    "PRESENTATION_FILE",
    "PresentationError",
    "PresentationPlan",
    "Script",
    "ScriptStep",
    "parse_script",
    "plan_for_scenario",
    "plan_presentation",
    "write_presentation",
]

E2E_ROOT = Path(__file__).resolve().parent
"""A scenario's ``script`` path is relative to this directory."""
PRESENTATION_FILE = "presentation.json"
SCHEMA_VERSION = 1

_SECTIONS = ("Goal", "Stack And Capabilities", "What It Illustrates", "Steps")
_HEADING = re.compile(r"^## (?P<name>.+?)\s*$")
_STEP = re.compile(r"^(?P<number>\d+)\. \*\*(?P<title>.+?)\*\*\s*$")
_FIELD = re.compile(r"^\s+- \*(?P<name>User action|Expected observation):\*\s+(?P<text>.+?)\s*$")
_STACK_ROW = re.compile(r"^- \*\*(?P<name>.+?):\*\*\s+(?P<detail>.+?)\s*$")
_BULLET = re.compile(r"^- (?P<text>.+?)\s*$")
_CONTINUATION = re.compile(r"^\s+(?P<text>\S.*?)\s*$")
_STEP_NUMBER = re.compile(r"^(?P<number>\d+)\.\s+(?P<text>\S.*)$", re.DOTALL)


class PresentationError(ValueError):
    """A script or a scenario cannot be presented; the message names what to correct."""


@dataclass(frozen=True)
class ScriptStep:
    """One numbered step of a script."""

    title: str
    action: str
    expected: str


@dataclass(frozen=True)
class Script:
    """What a scenario's script says, section by section."""

    goal: str
    stack: tuple[tuple[str, str], ...]
    illustrates: tuple[str, ...]
    steps: tuple[ScriptStep, ...]


def parse_script(text: str) -> Script:
    """The script a Markdown ``text`` in the script form states.

    The form: ``## Goal``, one paragraph; ``## Stack And Capabilities``,
    optional, bullets ``- **Name:** detail``; ``## What It Illustrates``,
    optional, bullets; ``## Steps``, items ``N. **Title.**`` numbered from 1,
    each with the sub-bullets ``- *User action:* …`` and
    ``- *Expected observation:* …``. A bullet may continue on indented lines.
    Text before the first ``##`` heading is not read. Any other ``##``
    heading, a missing ``Goal`` or ``Steps``, a step out of order or without
    both sub-bullets, and a line that fits nowhere are refused.
    """
    sections: dict[str, list[tuple[int, str]]] = {}
    current: list[tuple[int, str]] | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        heading = _HEADING.match(line)
        if heading is not None:
            name = heading.group("name")
            if name not in _SECTIONS:
                raise PresentationError(
                    f"script line {number}: section {name!r} is not one of {', '.join(_SECTIONS)}"
                )
            if name in sections:
                raise PresentationError(f"script line {number}: section {name!r} appears twice")
            current = sections[name] = []
        elif current is not None and line.strip():
            current.append((number, line))
    for required in ("Goal", "Steps"):
        if not sections.get(required):
            raise PresentationError(f"script: section {required!r} is missing or empty")
    goal = " ".join(line.strip() for _, line in sections["Goal"])
    stack = tuple(
        _stack_row(number, item) for number, item in _bullets(sections.get("Stack And Capabilities", []), "Stack And Capabilities")
    )
    illustrates = tuple(item for _, item in _bullets(sections.get("What It Illustrates", []), "What It Illustrates"))
    return Script(goal=goal, stack=stack, illustrates=illustrates, steps=_steps(sections["Steps"]))


def _bullets(lines: Sequence[tuple[int, str]], section: str) -> list[tuple[int, str]]:
    """The bullets of a section, each with its first line's number, continuations joined."""
    items: list[tuple[int, str]] = []
    for number, line in lines:
        bullet = _BULLET.match(line)
        continuation = _CONTINUATION.match(line)
        if bullet is not None:
            items.append((number, bullet.group("text")))
        elif continuation is not None and items:
            first, so_far = items[-1]
            items[-1] = (first, f"{so_far} {continuation.group('text')}")
        else:
            raise PresentationError(f"script line {number}: {section!r} takes bullets, '- text'")
    return items


def _stack_row(number: int, item: str) -> tuple[str, str]:
    row = _STACK_ROW.match(f"- {item}")
    if row is None:
        raise PresentationError(f"script line {number}: a stack bullet is '- **Name:** detail'")
    return row.group("name"), row.group("detail")


def _steps(lines: Sequence[tuple[int, str]]) -> tuple[ScriptStep, ...]:
    steps: list[dict[str, str]] = []
    field: str | None = None
    for number, line in lines:
        step = _STEP.match(line)
        named = _FIELD.match(line)
        continuation = _CONTINUATION.match(line)
        if step is not None:
            if int(step.group("number")) != len(steps) + 1:
                raise PresentationError(f"script line {number}: expected step {len(steps) + 1}, found {step.group('number')}")
            steps.append({"title": step.group("title").rstrip(".").strip()})
            field = None
        elif named is not None and steps:
            field = named.group("name")
            if field in steps[-1]:
                raise PresentationError(f"script line {number}: step {len(steps)} states {field!r} twice")
            steps[-1][field] = named.group("text")
        elif continuation is not None and steps and field is not None:
            steps[-1][field] = f"{steps[-1][field]} {continuation.group('text')}"
        else:
            raise PresentationError(
                f"script line {number}: a step is 'N. **Title.**' with '- *User action:* …' and '- *Expected observation:* …'"
            )
    for index, step_fields in enumerate(steps, start=1):
        for required in ("User action", "Expected observation"):
            if required not in step_fields:
                raise PresentationError(f"script: step {index} has no {required!r}")
        if not step_fields["title"]:
            raise PresentationError(f"script: step {index} has no title")
    return tuple(
        ScriptStep(title=item["title"], action=item["User action"], expected=item["Expected observation"]) for item in steps
    )


@dataclass(frozen=True)
class _Caption:
    """A caption and the actions it lasts for, as indexes into the scenario's actions."""

    first_action: int
    last_action: int
    text: str


@dataclass(frozen=True)
class _PlannedStep:
    step: ScriptStep
    first_action: int
    last_action: int
    captions: tuple[_Caption, ...]


@dataclass(frozen=True)
class PresentationPlan:
    """Everything of a presentation that is known before the scenario runs.

    ``plan_presentation`` makes it; ``timed`` adds what only a run knows.
    """

    scenario_id: str
    title: str
    summary: str
    script: Script
    action_count: int
    steps: tuple[_PlannedStep, ...]

    def timed(
        self,
        frames_after_actions: Sequence[int],
        total_frames: int,
        frames_per_second: int,
        *,
        video: str,
        poster: str,
        screenshots: Sequence[str],
    ) -> dict[str, Any]:
        """The presentation document of one recorded run of the planned scenario.

        ``frames_after_actions[i]`` is the count of frames recorded when
        action ``i`` had finished, ``total_frames`` the count in the video,
        which plays ``frames_per_second`` of them, and ``screenshots[i]`` the
        file taken after action ``i``. A step runs from the end of the step
        before it, the first from the start of the video, to the end of its
        last action, the last to the end of the video; its screenshot is its
        last action's. Refuses counts that do not match the plan, that
        decrease, that exceed the total, or that leave a step or a caption
        without a frame.
        """
        if len(frames_after_actions) != self.action_count or len(screenshots) != self.action_count:
            raise PresentationError(
                f"the run has {len(frames_after_actions)} frame counts and {len(screenshots)} screenshots "
                f"for {self.action_count} actions"
            )
        if frames_per_second <= 0:
            raise PresentationError(f"frames per second must be positive, not {frames_per_second}")
        counts = list(frames_after_actions)
        if any(later < earlier for earlier, later in zip([0, *counts], [*counts, total_frames])):
            raise PresentationError("the frame counts decrease or exceed the total number of frames")
        last_action = self.action_count - 1

        def seconds(frames: int) -> float:
            return round(frames / frames_per_second, 3)

        def starts(action: int) -> int:
            return 0 if action == 0 else counts[action - 1]

        def ends(action: int) -> int:
            return total_frames if action == last_action else counts[action]

        steps = []
        for number, planned in enumerate(self.steps, start=1):
            if any(starts(caption.first_action) >= ends(caption.last_action) for caption in planned.captions):
                raise PresentationError(f"step {number} has a caption that lasts no frame")
            captions = [
                {"start": seconds(starts(caption.first_action)), "end": seconds(ends(caption.last_action)), "text": caption.text}
                for caption in planned.captions
            ]
            steps.append({
                "title": planned.step.title,
                "action": planned.step.action,
                "expected": planned.step.expected,
                "screenshot": screenshots[planned.last_action],
                "start": seconds(starts(planned.first_action)),
                "end": seconds(ends(planned.last_action)),
                "captions": captions,
            })
        overview: dict[str, Any] = {"summary": self.summary, "intent": self.script.goal}
        if self.script.illustrates:
            overview["illustrates"] = list(self.script.illustrates)
        if self.script.stack:
            overview["stack"] = [{"name": name, "detail": detail} for name, detail in self.script.stack]
        return {
            "schema_version": SCHEMA_VERSION,
            "scenario_id": self.scenario_id,
            "title": self.title,
            "overview": overview,
            "video": {"file": video, "poster": poster, "duration": seconds(total_frames)},
            "steps": steps,
        }


def plan_presentation(scenario: Mapping[str, Any], script: Script) -> PresentationPlan:
    """Join a scenario's JSON document to its parsed script, or say why they do not join.

    The scenario needs a non-empty ``id``, ``title`` and ``description``. Each
    action's ``reason`` starts with the number of its step and a period; the
    numbers never decrease and every step of the script has at least one
    action. ``caption``, where an action has it, is a non-empty string, and a
    step with any caption has one on its first action.
    """
    texts = {}
    for key in ("id", "title", "description"):
        value = scenario.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PresentationError(f"the scenario has no {key}")
        texts[key] = value.strip()
    actions = scenario.get("actions")
    if not isinstance(actions, list) or not actions:
        raise PresentationError("the scenario has no actions")
    numbers: list[int] = []
    reasons: list[str] = []
    captions: list[str | None] = []
    for position, action in enumerate(actions, start=1):
        if not isinstance(action, Mapping):
            raise PresentationError(f"action {position} is not an object")
        reason = action.get("reason")
        numbered = _STEP_NUMBER.match(reason) if isinstance(reason, str) else None
        if numbered is None:
            raise PresentationError(f"action {position}: its reason must start with the number of its step, as in '3. Save the file'")
        number = int(numbered.group("number"))
        if not 1 <= number <= len(script.steps):
            raise PresentationError(f"action {position} names step {number}; the script has steps 1 to {len(script.steps)}")
        if numbers and number < numbers[-1]:
            raise PresentationError(f"action {position} names step {number} after an action of step {numbers[-1]}")
        caption = action.get("caption")
        if caption is not None and (not isinstance(caption, str) or not caption.strip()):
            raise PresentationError(f"action {position}: its caption must be a non-empty text")
        numbers.append(number)
        reasons.append(numbered.group("text").strip())
        captions.append(caption.strip() if isinstance(caption, str) else None)
    planned: list[_PlannedStep] = []
    for number, step in enumerate(script.steps, start=1):
        members = [index for index, owner in enumerate(numbers) if owner == number]
        if not members:
            raise PresentationError(f"step {number} of the script has no action")
        planned.append(_PlannedStep(
            step=step, first_action=members[0], last_action=members[-1], captions=_captions(number, members, reasons, captions),
        ))
    return PresentationPlan(
        scenario_id=texts["id"], title=texts["title"], summary=texts["description"], script=script,
        action_count=len(actions), steps=tuple(planned),
    )


def _captions(number: int, members: Sequence[int], reasons: Sequence[str], captions: Sequence[str | None]) -> tuple[_Caption, ...]:
    """The captions of one step's actions, by the rule in the module's documentation."""
    written = [index for index in members if captions[index] is not None]
    if not written:
        return tuple(_Caption(first_action=index, last_action=index, text=reasons[index]) for index in members)
    if written[0] != members[0]:
        raise PresentationError(
            f"step {number} has captions, so its first action, action {members[0] + 1}, needs one"
        )
    ends = [*(index - 1 for index in written[1:]), members[-1]]
    return tuple(
        _Caption(first_action=first, last_action=last, text=str(captions[first])) for first, last in zip(written, ends)
    )


def plan_for_scenario(scenario: Mapping[str, Any], root: Path = E2E_ROOT) -> PresentationPlan | None:
    """The plan of a scenario that names its ``script``, read below ``root``; None for one that names none.

    A scenario without a script is recorded without a presentation. A script
    that is named and cannot be read, or that does not join the scenario, is
    an error: call this before the scenario runs, so the recording is not
    made in vain.
    """
    named = scenario.get("script")
    if named is None:
        return None
    if not isinstance(named, str) or not named.strip() or Path(named).is_absolute() or ".." in Path(named).parts:
        raise PresentationError(f"the scenario's script {named!r} is not a path below {root}")
    try:
        text = (root / named).read_text(encoding="utf-8")
    except OSError as error:
        raise PresentationError(f"the scenario's script {named!r} cannot be read below {root}: {error}") from error
    return plan_presentation(scenario, parse_script(text))


def write_presentation(evidence: Path, document: Mapping[str, Any]) -> Path:
    """Write ``document`` as ``presentation.json`` in the ``evidence`` folder and return its path."""
    path = evidence / PRESENTATION_FILE
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
