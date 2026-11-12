"""Unit tests of ``scripts/publish_coverage_numbers_to_pr.py``: the figures, the block, the upsert, the step."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "publish_coverage_numbers_to_pr.py"


def _load(path: Path) -> Any:
    """The script as a module; registered in ``sys.modules`` so its dataclasses resolve their annotations."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


publish = _load(_SCRIPT)

COVERAGE = {"totals": {"percent_covered": 82.456, "covered_lines": 16012, "num_statements": 19488}}
DIFF = {"total_percent_covered": 87, "total_num_lines": 150, "total_num_violations": 20}


def test_the_figures_are_read_from_both_reports() -> None:
    """Precondition: coverage.py totals and diff-cover totals as their JSON gives them.
    Action: read. Postcondition: the six figures, typed, with nothing derived yet."""
    numbers = publish.read_numbers(COVERAGE, DIFF)
    assert numbers == publish.Numbers(82.456, 16012, 19488, 87, 150, 20)


@pytest.mark.parametrize("coverage,diff,missing", [
    ({}, DIFF, "'totals'"),
    ({"totals": {"percent_covered": 1.0}}, DIFF, "'covered_lines'"),
    (COVERAGE, {"total_percent_covered": 1}, "'total_num_lines'"),
])
def test_a_report_lacking_a_figure_is_refused_by_name(coverage: dict, diff: dict, missing: str) -> None:
    """Precondition: one report lacks a key. Action: read. Postcondition: ValueError names that key."""
    with pytest.raises(ValueError, match=missing):
        publish.read_numbers(coverage, diff)


def test_the_block_carries_both_percentages_between_the_markers() -> None:
    """Precondition: the figures and a run URL. Action: render. Postcondition: the block
    starts and ends with the markers, links the run, and states 87% of changed lines
    with 130 of 150 covered, and 82.5% overall with the statement counts."""
    block = publish.render(publish.Numbers(82.456, 16012, 19488, 87, 150, 20), "https://ci/run/1")
    lines = block.splitlines()
    assert lines[0] == publish.BEGIN and lines[-1] == publish.END
    assert "[CI run](https://ci/run/1)" in block
    assert "**87%** (130 of 150 measured changed lines; 20 uncovered)" in block
    assert "**82.5%** (16,012 of 19,488 statements)" in block


def test_upsert_appends_the_block_after_the_authors_text() -> None:
    """Precondition: a description without markers. Action: upsert.
    Postcondition: the author's text is intact, one blank line, then the block."""
    block = f"{publish.BEGIN}\nnumbers\n{publish.END}"
    assert publish.upsert("## Why\n\nBecause.\n", block) == f"## Why\n\nBecause.\n\n{block}"


def test_upsert_replaces_only_the_block_between_the_markers() -> None:
    """Precondition: a description with an older block between text above and below.
    Action: upsert the new block. Postcondition: the text above and below is byte for
    byte what it was and the old block is gone."""
    old = f"{publish.BEGIN}\nold\n{publish.END}"
    new = f"{publish.BEGIN}\nnew\n{publish.END}"
    assert publish.upsert(f"above\n\n{old}\n\nbelow\n", new) == f"above\n\n{new}\n\nbelow\n"


def test_markers_quoted_in_the_authors_prose_are_not_the_block() -> None:
    """Precondition: a description that mentions both markers inside a sentence and has no block.
    Action: upsert. Postcondition: the sentence is intact and the block is appended after it."""
    prose = f"It renders a block between `{publish.BEGIN}` and `{publish.END}` with the figures.\n"
    block = f"{publish.BEGIN}\nnumbers\n{publish.END}"
    assert publish.upsert(prose, block) == f"{prose}\n{block}"


def test_a_change_outside_the_measured_package_says_so_instead_of_a_percentage() -> None:
    """Precondition: diff-cover measured no changed line. Action: render.
    Postcondition: the changed-lines cell says none measured and names the package; no percent sign in it."""
    block = publish.render(publish.Numbers(82.456, 16012, 19488, 100, 0, 0), "https://ci/run/1")
    cell = next(line for line in block.splitlines() if line.startswith("| Changed lines covered"))
    assert "none measured: the change touches no line of `devcapsule`" in cell and "%" not in cell


def test_upsert_on_an_empty_description_is_the_block_alone() -> None:
    """Precondition: the API returned no body. Action: upsert. Postcondition: the block alone."""
    block = f"{publish.BEGIN}\nnumbers\n{publish.END}"
    assert publish.upsert(None, block) == block


def _reports(tmp_path: Path) -> list[str]:
    (tmp_path / "coverage.json").write_text(json.dumps(COVERAGE))
    (tmp_path / "diff-cover.json").write_text(json.dumps(DIFF))
    return ["--coverage", str(tmp_path / "coverage.json"), "--diff", str(tmp_path / "diff-cover.json")]


def _environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in (("GITHUB_REPOSITORY", "o/r"), ("PR_NUMBER", "7"), ("GITHUB_TOKEN", "t"), ("RUN_URL", "https://ci/run/1")):
        monkeypatch.setenv(name, value)


def test_main_reads_the_description_and_patches_it_with_the_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Precondition: both reports on disk, the environment set, a description without the block.
    Action: run ``main`` with the API replaced by a recorder. Postcondition: one GET then one
    PATCH of ``/repos/o/r/pulls/7`` whose body is the description plus the block; exit 0."""
    calls: list[tuple[str, str, dict | None]] = []

    def api(method: str, url: str, token: str, payload: dict | None = None) -> dict:
        calls.append((method, url, payload))
        return {"body": "The PR.\n"} if method == "GET" else {}

    monkeypatch.setattr(publish, "_request", api)
    _environment(monkeypatch)
    assert publish.main(_reports(tmp_path)) == 0
    assert [(m, u) for m, u, _ in calls] == [("GET", "https://api.github.com/repos/o/r/pulls/7"),
                                            ("PATCH", "https://api.github.com/repos/o/r/pulls/7")]
    body = calls[1][2]["body"]  # type: ignore[index]
    assert body.startswith("The PR.\n\n" + publish.BEGIN) and body.endswith(publish.END)


def test_main_does_not_patch_a_description_that_already_carries_this_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Precondition: the description already holds exactly this run's block. Action: run ``main``.
    Postcondition: only the GET is made and the exit is 0."""
    block = publish.render(publish.read_numbers(COVERAGE, DIFF), "https://ci/run/1")
    calls: list[str] = []

    def api(method: str, url: str, token: str, payload: dict | None = None) -> dict:
        calls.append(method)
        return {"body": block}

    monkeypatch.setattr(publish, "_request", api)
    _environment(monkeypatch)
    assert publish.main(_reports(tmp_path)) == 0
    assert calls == ["GET"]


def test_main_fails_without_a_report_or_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Precondition: the reports exist but the token is absent; then the reports are absent.
    Action: run ``main`` twice. Postcondition: exit 1 each time with the cause on stderr, no API call."""
    monkeypatch.setattr(publish, "_request", lambda *a, **k: pytest.fail("no API call expected"))
    _environment(monkeypatch)
    monkeypatch.delenv("GITHUB_TOKEN")
    assert publish.main(_reports(tmp_path)) == 1
    assert "GITHUB_TOKEN" in capsys.readouterr().err
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    assert publish.main(["--coverage", str(tmp_path / "none.json"), "--diff", str(tmp_path / "diff-cover.json")]) == 1
    assert "none.json" in capsys.readouterr().err
