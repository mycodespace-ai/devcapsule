"""Fail closed when routing or an applicable verification job did not succeed."""
from __future__ import annotations

import json
import os
import sys
from typing import Any


def check(needs: dict[str, Any]) -> None:
    changes = needs.get("changes", {})
    if changes.get("result") != "success":
        raise ValueError("Path detection did not succeed")
    outputs = changes.get("outputs", {})
    for route, job in (("python", "pytest"), ("docs", "docs-build")):
        selected = outputs.get(route)
        if selected not in ("true", "false"):
            raise ValueError(f"Missing or invalid {route} route")
        result = needs.get(job, {}).get("result")
        allowed = ("success",) if selected == "true" else ("success", "skipped")
        if result not in allowed:
            raise ValueError(f"{job}: {result!r} is invalid for route {selected}")


def main() -> int:
    try:
        needs = json.loads(os.environ["CI_NEEDS"])
        if not isinstance(needs, dict):
            raise ValueError("CI_NEEDS must be an object")
        check(needs)
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        print(f"CI gate failed: {error}", file=sys.stderr)
        return 1
    print("All applicable verification jobs passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
