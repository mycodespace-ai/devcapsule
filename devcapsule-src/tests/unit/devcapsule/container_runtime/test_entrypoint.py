"""Unit tests of ``devcapsule/container_runtime/entrypoint.py``: the command line of the runtime.

``run`` is the layer that reads the process and acts on the host; what it
decides is ``Session``'s, tested in ``test_session.py``, and what it does is
exercised by ``tests/integration/test_runtime_entrypoint_cli.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from devcapsule.container_runtime.entrypoint import USAGE, main


def test_main_prints_the_usage_for_help(capsys: pytest.CaptureFixture[str]) -> None:
    """``main(["--help"])`` prints the usage on stdout and returns 0."""
    status = main(["--help"])

    assert status == 0
    assert capsys.readouterr().out == USAGE + "\n"


@pytest.mark.parametrize(
    "arguments",
    [[], ["plan.json", "--"], ["plan.json", "other.json"]],
    ids=["no plan", "separator without a job", "two plans"],
)
def test_main_refuses_a_command_line_that_names_no_single_plan_or_an_empty_job(
    capsys: pytest.CaptureFixture[str], arguments: list[str],
) -> None:
    """Without exactly one plan, or with ``--`` and no command after it, ``main`` prints the usage on stderr and returns 2."""
    status = main(arguments)

    assert status == 2
    output = capsys.readouterr()
    assert output.err == USAGE + "\n"
    assert output.out == ""


@pytest.mark.parametrize("job", [[], ["--", "true"]], ids=["interactive", "headless"])
def test_main_reports_a_plan_it_cannot_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], job: list[str],
) -> None:
    """For a plan file that does not exist, ``main`` names the plan error on stderr and returns 2, with or without a job."""
    status = main([str(tmp_path / "missing.json"), *job])

    assert status == 2
    assert "devcapsule runtime plan error: cannot read runtime plan" in capsys.readouterr().err
