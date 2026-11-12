"""Focused tests for the one-elicitation engine's fixed order and batch mode."""

from __future__ import annotations

import io

import pytest

from devcapsule.elicitation import (
    FACET_JUSTIFICATION,
    SOURCE_COMMAND_LINE,
    SOURCE_DEFAULT,
    SOURCE_EXISTING_RECORD,
    SOURCE_PROMPT,
    ElicitationIncomplete,
    Elicitor,
)
from devcapsule.configuration.file_formats import (
    ProjectConfigurationError,
)

pytestmark = pytest.mark.legacy


def _validator(value: str) -> str:
    if value == "invalid":
        raise ProjectConfigurationError("The value 'invalid' is not accepted.")
    return value.lower()


def test_command_line_wins_over_every_other_source() -> None:
    elicitor = Elicitor({("node", "value"): "CLI"}, interactive=False)
    answer = elicitor.seek(
        "node",
        description="Example",
        remedy="--set node VALUE",
        existing="recorded",
        default="derived",
        validate=_validator,
    )
    assert answer is not None
    assert (answer.value, answer.source) == ("cli", SOURCE_COMMAND_LINE)
    elicitor.finish()


def test_invalid_command_line_answer_fails_immediately() -> None:
    elicitor = Elicitor({("node", "value"): "invalid"}, interactive=True)
    with pytest.raises(ProjectConfigurationError, match="not accepted"):
        elicitor.seek(
            "node", description="Example", remedy="--set node VALUE", validate=_validator
        )


def test_existing_record_beats_default_and_default_beats_prompt() -> None:
    would_fail_if_read = io.StringIO("")
    elicitor = Elicitor(interactive=True, input_stream=would_fail_if_read, output_stream=io.StringIO())

    recorded = elicitor.seek(
        "recorded-node",
        description="Example",
        remedy="--set recorded-node VALUE",
        existing="from-record",
        default="derived",
    )
    assert recorded is not None
    assert (recorded.value, recorded.source) == ("from-record", SOURCE_EXISTING_RECORD)

    derived = elicitor.seek(
        "derived-node",
        description="Example",
        remedy="--set derived-node VALUE",
        default="derived",
    )
    assert derived is not None
    assert (derived.value, derived.source) == ("derived", SOURCE_DEFAULT)
    elicitor.finish()


def test_a_repeated_seek_returns_the_first_answer_unchanged() -> None:
    elicitor = Elicitor(interactive=False)
    first = elicitor.seek(
        "node", description="Example", remedy="--set node VALUE", existing="one"
    )
    second = elicitor.seek(
        "node", description="Example", remedy="--set node VALUE", existing="two"
    )
    assert first is second


def test_optional_unanswered_node_is_not_an_error() -> None:
    elicitor = Elicitor(interactive=False)
    assert (
        elicitor.seek(
            "node", description="Example", remedy="--set node VALUE", mandatory=False
        )
        is None
    )
    elicitor.finish()


def test_noninteractive_batch_failure_lists_every_missing_answer() -> None:
    elicitor = Elicitor(interactive=False)
    assert (
        elicitor.seek("first", description="Example", remedy="--set first VALUE") is None
    )
    assert (
        elicitor.seek(
            "second",
            facet=FACET_JUSTIFICATION,
            description="Example",
            remedy="--authorize second VALUE JUSTIFICATION",
        )
        is None
    )
    assert elicitor.missing() == ("first", "second (justification)")
    with pytest.raises(ElicitationIncomplete) as failure:
        elicitor.finish()
    message = str(failure.value)
    assert "first: --set first VALUE" in message
    assert "second (justification): --authorize second VALUE JUSTIFICATION" in message


def test_an_answer_no_question_consumed_is_a_failure() -> None:
    elicitor = Elicitor({("typo-node", "value"): "x"}, interactive=False)
    with pytest.raises(ElicitationIncomplete, match="matched no question"):
        elicitor.finish()


def test_an_early_finish_does_not_misreport_unreached_answers() -> None:
    elicitor = Elicitor({("later-node", "value"): "x"}, interactive=False)
    assert elicitor.seek("first", description="Example", remedy="--set first VALUE") is None
    with pytest.raises(ElicitationIncomplete) as failure:
        elicitor.finish(require_all_consumed=False)
    assert "later-node" not in str(failure.value)


def test_noninteractive_omission_takes_the_declared_safe_answer() -> None:
    elicitor = Elicitor(interactive=False)
    answer = elicitor.seek(
        "docker-daemon",
        description="Recommend docker access",
        remedy="--authorize docker-daemon host-socket",
        empty_answer="none",
        omitted_answer="none",
    )
    assert answer is not None
    assert (answer.value, answer.source) == ("none", SOURCE_DEFAULT)
    elicitor.finish()


def test_prompt_reads_validates_and_normalizes() -> None:
    output = io.StringIO()
    elicitor = Elicitor(
        interactive=True, input_stream=io.StringIO("ANSWER\n"), output_stream=output
    )
    answer = elicitor.seek(
        "node", description="Pick a value", remedy="--set node VALUE", validate=_validator
    )
    assert answer is not None
    assert (answer.value, answer.source) == ("answer", SOURCE_PROMPT)
    assert output.getvalue() == "Pick a value: "


def test_empty_input_takes_the_displayed_empty_answer() -> None:
    output = io.StringIO()
    elicitor = Elicitor(
        interactive=True, input_stream=io.StringIO("\n"), output_stream=output
    )
    answer = elicitor.seek(
        "node",
        description="Recommend docker access",
        remedy="--authorize docker-daemon VALUE",
        empty_answer="none",
    )
    assert answer is not None
    assert (answer.value, answer.source) == ("none", SOURCE_PROMPT)
    assert "[none]" in output.getvalue()


def test_empty_input_without_empty_answer_re_asks() -> None:
    output = io.StringIO()
    elicitor = Elicitor(
        interactive=True, input_stream=io.StringIO("\nvalue\n"), output_stream=output
    )
    answer = elicitor.seek(
        "node", description="Pick a value", remedy="--set node VALUE"
    )
    assert answer is not None
    assert answer.value == "value"
    assert "A value is required." in output.getvalue()


def test_invalid_prompted_answer_re_asks_with_the_reason() -> None:
    output = io.StringIO()
    elicitor = Elicitor(
        interactive=True, input_stream=io.StringIO("invalid\nGOOD\n"), output_stream=output
    )
    answer = elicitor.seek(
        "node", description="Pick a value", remedy="--set node VALUE", validate=_validator
    )
    assert answer is not None
    assert answer.value == "good"
    assert "The value 'invalid' is not accepted." in output.getvalue()


def test_end_of_input_at_the_prompt_falls_back_to_batch_mode() -> None:
    elicitor = Elicitor(
        interactive=True, input_stream=io.StringIO(""), output_stream=io.StringIO()
    )
    assert (
        elicitor.seek("node", description="Pick a value", remedy="--set node VALUE")
        is None
    )
    with pytest.raises(ElicitationIncomplete, match="--set node VALUE"):
        elicitor.finish()
