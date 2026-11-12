"""Publish advisory diff-cover JSON as bounded native GitHub annotations.

Run from devcapsule-src, where coverage.xml and diff-cover were produced.
Diff-cover JSON paths are relative to the Git repository, not this directory.
No coverage percentage fails this bridge; malformed/missing reports do.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import sys
from typing import Any

MAX_ANNOTATIONS = 10  # GitHub's warning annotation limit per step.
MAX_SUMMARY_BYTES = 900_000  # Leave room below GitHub's 1 MiB per-step limit.


def escape(value: str, *, property_value: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def line_numbers(value: Any) -> list[int]:
    if not isinstance(value, list) or any(type(n) is not int or n < 1 for n in value):
        raise ValueError("Report lines must be positive integers")
    if len(set(value)) != len(value):
        raise ValueError("Report contains duplicate lines")
    return sorted(value)


def ranges(lines: list[int]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for line in lines:
        if result and line == result[-1][1] + 1:
            result[-1] = (result[-1][0], line)
        else:
            result.append((line, line))
    return result


def build_annotations(data: Any) -> tuple[list[str], int]:
    if not isinstance(data, dict) or not isinstance(data.get("src_stats"), dict):
        raise ValueError("Missing diff-cover src_stats object")
    for key in ("total_num_lines", "total_num_violations"):
        if type(data.get(key)) is not int or data[key] < 0:
            raise ValueError(f"Invalid diff-cover {key}")
    measured = uncovered = 0
    warnings: list[str] = []
    for filename, stats in sorted(data["src_stats"].items()):
        path = PurePosixPath(filename)
        if (path.is_absolute() or ".." in path.parts or "\\" in filename
                or str(path) != filename
                or not filename.startswith("devcapsule-src/devcapsule/")):
            raise ValueError(f"Unexpected runtime coverage path: {filename!r}")
        if not isinstance(stats, dict):
            raise ValueError("Invalid source statistics")
        missing = line_numbers(stats.get("violation_lines"))
        covered = line_numbers(stats.get("covered_lines"))
        if set(missing) & set(covered):
            raise ValueError("Covered and uncovered lines overlap")
        measured += len(missing) + len(covered)
        uncovered += len(missing)
        for start, end in ranges(missing):
            message = f"Changed executable lines {start}-{end} are not covered by tests (advisory)."
            warnings.append(
                f"::warning file={escape(filename, property_value=True)},line={start},"
                f"endLine={end},title=Uncovered changed lines::{escape(message)}"
            )
    if measured != data["total_num_lines"] or uncovered != data["total_num_violations"]:
        raise ValueError("Diff-cover totals disagree with source statistics")
    return warnings, measured


def publish(report: Path, markdown: Path, summary: Path) -> None:
    data = json.loads(report.read_text(encoding="utf-8"))
    warnings, measured = build_annotations(data)
    detail = markdown.read_text(encoding="utf-8")
    if not detail.strip():
        raise ValueError("Empty diff-cover Markdown report")
    header = "## Changed-line coverage (advisory)\n\n"
    header += "Runtime package only; web-console code is not measured in this report.\n\n"
    if not measured:
        header += "Not applicable: no measured executable lines in this diff.\n\n"
    if len(warnings) > MAX_ANNOTATIONS:
        header += (f"Showing {MAX_ANNOTATIONS} of {len(warnings)} uncovered ranges inline. "
                   "The uploaded reports contain every range.\n\n")
    if len(detail.encode("utf-8")) > MAX_SUMMARY_BYTES:
        detail = "Report exceeds the summary budget; download the complete coverage artifact.\n"
    with summary.open("a", encoding="utf-8") as output:
        output.write(header + detail + "\n")
    # Validate everything and write the summary before emitting any annotations.
    for warning in warnings[:MAX_ANNOTATIONS]:
        print(warning)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=Path("diff-cover.json"))
    parser.add_argument("--markdown", type=Path, default=Path("diff-cover.md"))
    args = parser.parse_args()
    try:
        publish(args.json, args.markdown, Path(os.environ["GITHUB_STEP_SUMMARY"]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Diff coverage reporting failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
