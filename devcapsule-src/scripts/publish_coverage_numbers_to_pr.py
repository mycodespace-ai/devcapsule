"""Publish a pull request's coverage numbers into its description.

Run from ``devcapsule-src`` after the tests and diff-cover steps, on a
``pull_request`` event only::

    python -m coverage json -o coverage.json
    python scripts/publish_coverage_numbers_to_pr.py

The step reads ``coverage.json``, coverage.py's report of the whole
``devcapsule`` package, and ``diff-cover.json``, the report over the lines
the pull request changed. It renders one Markdown block between two marker
comments and replaces that block in the pull request's description, or
appends it when the description has none. The text outside the block is the
author's and is never touched. With the repository set to take the pull
request's description as the merge commit message, the numbers reach
``main``'s history unchanged.

Environment: ``GITHUB_REPOSITORY``, ``PR_NUMBER``, ``GITHUB_TOKEN`` with
``pull-requests: write``, and ``RUN_URL`` for the link. No percentage fails
this step. A missing or malformed report, or a refused API call, does.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["Numbers", "read_numbers", "render", "upsert", "main"]

BEGIN = "<!-- coverage-numbers:begin -->"
END = "<!-- coverage-numbers:end -->"
"""The markers that bound the block; each stands alone on its line, so a marker quoted in prose is not a block."""

_BLOCK = re.compile(rf"^{re.escape(BEGIN)}\n.*?^{re.escape(END)}$", re.MULTILINE | re.DOTALL)

_API_VERSION = "2022-11-28"


@dataclass(frozen=True)
class Numbers:
    """The two figures and what they are made of."""

    overall_percent: float
    """Statements of the ``devcapsule`` package covered, branch-aware as coverage.py reports it."""
    covered_statements: int
    statements: int
    diff_percent: int
    """Changed measured lines covered, as diff-cover reports it."""
    diff_lines: int
    """Changed lines the coverage report measures; test files and unmeasured lines are not among them."""
    diff_uncovered: int


def read_numbers(coverage: Mapping[str, Any], diff: Mapping[str, Any]) -> Numbers:
    """The figures from coverage.py's JSON ``totals`` and diff-cover's JSON totals.

    Raises ``ValueError`` naming the first key a report lacks or mistypes.
    """
    totals = coverage.get("totals")
    if not isinstance(totals, Mapping):
        raise ValueError("coverage.json: no 'totals' table")
    try:
        return Numbers(
            overall_percent=float(totals["percent_covered"]),
            covered_statements=int(totals["covered_lines"]),
            statements=int(totals["num_statements"]),
            diff_percent=int(diff["total_percent_covered"]),
            diff_lines=int(diff["total_num_lines"]),
            diff_uncovered=int(diff["total_num_violations"]),
        )
    except KeyError as missing:
        raise ValueError(f"report lacks {missing.args[0]!r}") from None
    except (TypeError, ValueError) as wrong:
        raise ValueError(f"report value is not a number: {wrong}") from None


def render(numbers: Numbers, run_url: str) -> str:
    """The Markdown block, markers included, for one run."""
    return "\n".join([
        BEGIN,
        f"### Test coverage, from [CI run]({run_url})",
        "",
        "| | |",
        "|---|---|",
        "| Changed lines covered | " + _changed_lines(numbers) + " |",
        f"| Overall `devcapsule` | **{numbers.overall_percent:.1f}%** "
        f"({numbers.covered_statements:,} of {numbers.statements:,} statements) |",
        END,
    ])


def _changed_lines(numbers: Numbers) -> str:
    """The changed-lines cell; a change outside the measured package says so instead of claiming 100% of nothing."""
    if numbers.diff_lines == 0:
        return "none measured: the change touches no line of `devcapsule`"
    return (f"**{numbers.diff_percent}%** ({numbers.diff_lines - numbers.diff_uncovered} of {numbers.diff_lines} "
            f"measured changed lines; {numbers.diff_uncovered} uncovered)")


def upsert(body: str | None, block: str) -> str:
    """The description with its block replaced, or the block appended after a blank line.

    Only a block whose markers each stand alone on a line is replaced; the
    markers quoted inside the author's prose are prose.
    """
    text = body or ""
    found = _BLOCK.search(text)
    if found:
        return text[:found.start()] + block + text[found.end():]
    return block if not text.strip() else text.rstrip("\n") + "\n\n" + block


def _request(method: str, url: str, token: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": _API_VERSION,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(request) as response:  # noqa: S310 - the URL is api.github.com, built here
        return json.load(response)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--coverage", type=Path, default=Path("coverage.json"))
    parser.add_argument("--diff", type=Path, default=Path("diff-cover.json"))
    arguments = parser.parse_args(argv)
    try:
        numbers = read_numbers(
            json.loads(arguments.coverage.read_text(encoding="utf-8")),
            json.loads(arguments.diff.read_text(encoding="utf-8")),
        )
        repository, number, token = (os.environ[name] for name in ("GITHUB_REPOSITORY", "PR_NUMBER", "GITHUB_TOKEN"))
        run_url = os.environ.get("RUN_URL", "")
    except (OSError, ValueError, KeyError) as problem:
        print(f"coverage numbers: {problem}", file=sys.stderr)
        return 1
    block = render(numbers, run_url)
    url = f"https://api.github.com/repos/{repository}/pulls/{number}"
    current = _request("GET", url, token).get("body")
    updated = upsert(current, block)
    if updated == current:
        print("coverage numbers: the description already carries this run's numbers")
        return 0
    try:
        _request("PATCH", url, token, {"body": updated})
    except OSError as refused:
        print(f"coverage numbers: the API refused the update: {refused}", file=sys.stderr)
        return 1
    print(f"coverage numbers: changed lines {numbers.diff_percent}%, overall {numbers.overall_percent:.1f}%, published to #{number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
