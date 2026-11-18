#!/usr/bin/env python3
"""Regenerate the golden lock fixtures from the embedded resolution matrix.

The fixtures under tests/resources/golden_locks/ are byte-exact captures of
the current matrix's generated locks; on a deliberate pin or model advance
they are regenerated in the same commit (see test_resolution_matrix.py).
Run from the repository root:

    .venv/bin/python scripts/regenerate-golden-locks.py

The need behind each fixture is owned by the test module — this tool imports
it so the two can never drift.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from devcapsule.platforms import Platform  # noqa: E402
from devcapsule.resolution_matrix import MATRICES  # noqa: E402
from tests.unit.devcapsule.test_resolution_matrix import GOLDEN_NEEDS, GOLDEN_ROOT  # noqa: E402


def main() -> int:
    matrix = MATRICES[Platform.LINUX_AMD64]
    for name, need in sorted(GOLDEN_NEEDS.items()):
        path = GOLDEN_ROOT / f"{name}.lock"
        content = matrix.resolve(need).render_lock()
        changed = not path.is_file() or path.read_text(encoding="utf-8") != content
        path.write_text(content, encoding="utf-8")
        print(f"{'regenerated' if changed else 'unchanged  '} {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
