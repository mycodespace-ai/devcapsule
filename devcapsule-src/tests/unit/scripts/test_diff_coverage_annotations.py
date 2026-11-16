"""Unit tests of ``scripts/diff_coverage_annotations.py``: advisory annotations from a diff-cover report."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "diff_coverage_annotations.py"
_SOURCE = "devcapsule-src/devcapsule/a.py"


def _load(path: Path) -> Any:
    """The script as a module."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = _load(_SCRIPT)


def _report(lines: list[int], covered: list[int] | None = None, source: str = _SOURCE) -> dict[str, Any]:
    """A diff-cover JSON report of one source file with the given uncovered and covered lines."""
    covered = covered or []
    return {
        "src_stats": {source: {"violation_lines": lines, "covered_lines": covered}},
        "total_num_lines": len(lines) + len(covered),
        "total_num_violations": len(lines),
    }


def _files(directory: Path, report: dict[str, Any], markdown: str) -> tuple[Path, Path, Path]:
    """The report, its Markdown rendering and an empty step summary, in the test's directory."""
    source, rendered, summary = (directory / name for name in ("report.json", "report.md", "summary.md"))
    source.write_text(json.dumps(report), encoding="utf-8")
    rendered.write_text(markdown, encoding="utf-8")
    return source, rendered, summary


def test_uncovered_lines_become_one_warning_per_contiguous_range() -> None:
    """Precondition: a report with uncovered lines 5, 2 and 3. Action: build the annotations.
    Postcondition: three measured lines, and two warnings, for lines 2 to 3 and for line 5."""
    warnings, measured = bridge.build_annotations(_report([5, 2, 3]))
    assert measured == 3
    assert len(warnings) == 2
    assert "line=2,endLine=3" in warnings[0]
    assert "line=5,endLine=5" in warnings[1]
    assert all(warning.startswith("::warning ") for warning in warnings)


@pytest.mark.parametrize("report", [{}, {"src_stats": {}}, _report([0]), _report([True]), _report([2, 2])])
def test_a_malformed_report_is_refused_rather_than_read_as_covered(report: Any) -> None:
    """Precondition: a report with no statistics, or with a line number that is zero, a
    boolean, or repeated. Action: build the annotations. Postcondition: ``ValueError``."""
    with pytest.raises(ValueError):
        bridge.build_annotations(report)


def test_a_line_both_covered_and_uncovered_is_refused() -> None:
    """Precondition: a report naming line 2 as covered and as uncovered. Action: build the
    annotations. Postcondition: ``ValueError`` naming the overlap."""
    with pytest.raises(ValueError, match="overlap"):
        bridge.build_annotations(_report([2], [2]))


def test_totals_that_disagree_with_the_lines_are_refused() -> None:
    """Precondition: a report of one line whose total says ten. Action: build the annotations.
    Postcondition: ``ValueError`` naming the totals."""
    report = _report([2])
    report["total_num_lines"] = 10
    with pytest.raises(ValueError, match="totals"):
        bridge.build_annotations(report)


@pytest.mark.parametrize("source", ["../a.py", "/tmp/a.py", "devcapsule/a.py", "devcapsule-src/devcapsule/../a.py"])
def test_a_source_path_outside_the_package_is_refused(source: str) -> None:
    """Precondition: a report whose source path climbs out, is absolute, or is not under
    ``devcapsule-src/devcapsule``. Action: build the annotations. Postcondition: ``ValueError``
    naming the path."""
    with pytest.raises(ValueError, match="path"):
        bridge.build_annotations(_report([2], source=source))


def test_a_property_value_is_escaped_for_a_workflow_command() -> None:
    """Precondition: a file name holding a percent sign, a comma, a colon and a line break.
    Action: escape it as a property value. Postcondition: each is percent-encoded."""
    assert bridge.escape("a%,:\r\n.py", property_value=True) == "a%25%2C%3A%0D%0A.py"


def test_publishing_emits_at_most_ten_warnings_and_keeps_the_whole_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Precondition: a report of fourteen separate uncovered lines and its Markdown table.
    Action: publish. Postcondition: ten warnings on standard output, a summary that says ten
    of fourteen and carries the whole table, and the report file unchanged."""
    report = _report(list(range(1, 28, 2)))
    source, rendered, summary = _files(tmp_path, report, "Complete table\n")
    bridge.publish(source, rendered, summary)
    assert capsys.readouterr().out.count("::warning ") == 10
    assert "10 of 14" in summary.read_text(encoding="utf-8")
    assert "Complete table" in summary.read_text(encoding="utf-8")
    assert json.loads(source.read_text(encoding="utf-8")) == report


def test_a_diff_with_no_measured_line_is_published_as_not_applicable(tmp_path: Path) -> None:
    """Precondition: a report with no line at all. Action: publish. Postcondition: the summary
    says the report is not applicable."""
    source, rendered, summary = _files(tmp_path, _report([]), "No lines\n")
    bridge.publish(source, rendered, summary)
    assert "Not applicable" in summary.read_text(encoding="utf-8")


def test_the_program_fails_when_the_report_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Precondition: a current directory with no diff-cover report, no arguments, and a step
    summary path. Action: run ``main``. Postcondition: status 1 and the failure on standard
    error; a missing report never passes as covered."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    monkeypatch.setattr(sys, "argv", [_SCRIPT.name])
    assert bridge.main() == 1
    assert "reporting failed" in capsys.readouterr().err
