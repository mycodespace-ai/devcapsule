"""Check the unit-test conventions that *Unit Tests* in WORKFLOW-LOCAL.md states.

Run from ``devcapsule-src``::

    python scripts/validate_unittests_follow_conventions.py [--base REF]

The checks, in the order the section states its rules:

1. **Placement.** A test file that is not legacy mirrors the module it
   tests: ``tests/unit/<path>/test_<name>.py`` tests ``<path>/<name>.py`` or
   ``<path>/_<name>.py``, the path relative to ``devcapsule-src``. A file
   outside the mirror that is not legacy must carry the marker of a heavier
   suite at module level, since it is then not a unit test.
2. **Docstrings.** Every test function in a file that is not legacy has a
   docstring.
3. **Legacy files only shrink.** A legacy file, one whose module-level
   ``pytestmark`` includes ``legacy``, is compared with the base revision:
   no test function is added, no test function's source changes, and no
   marker is added. A legacy file the base does not have is refused.

The base revision is ``--base``, else ``DEVCAPSULE_DIFF_BASE``, else
``origin/main``, compared at its merge base with ``HEAD``. The exit status
is 1 when any rule is broken, with one line per breach, and the summary
names how many legacy files and functions remain.
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["TestModule", "parse_module", "mirrored_module", "check", "main"]

LEGACY_MARKER = "legacy"
"""The module-level marker that exempts a file from rules 1 and 2 and subjects it to rule 3."""

HEAVIER_SUITE_MARKERS = frozenset({
    "integration", "e2e", "recursive_e2e", "contributor_e2e", "ide_smoke", "base_build_e2e",
})
"""Markers of the suites that are not unit tests; a file carrying one may live outside the mirror."""

UNIT_MIRROR = Path("tests") / "unit"
"""The directory that mirrors ``devcapsule-src`` for unit tests."""

_EXCLUDED_PARTS = frozenset({"resources"})


@dataclass(frozen=True)
class TestModule:
    """What the checker needs to know about one test file."""

    path: Path
    """Relative to ``devcapsule-src``."""
    markers: frozenset[str]
    """Marker names in the module-level ``pytestmark``."""
    functions: dict[str, str] = field(default_factory=dict)
    """Qualified test function name to its source, decorators included, lines right-stripped."""
    undocumented: tuple[tuple[str, int], ...] = ()
    """Test functions without a docstring, with the line of their ``def``."""

    @property
    def legacy(self) -> bool:
        return LEGACY_MARKER in self.markers


def parse_module(path: Path, source: str) -> TestModule:
    """Read the markers and test functions of one test file from its source."""
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()
    functions: dict[str, str] = {}
    undocumented: list[tuple[str, int]] = []
    for qualified, node in _test_functions(tree):
        start = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
        end = node.end_lineno or node.lineno
        functions[qualified] = "\n".join(line.rstrip() for line in lines[start - 1:end])
        if not ast.get_docstring(node):
            undocumented.append((qualified, node.lineno))
    return TestModule(path, frozenset(_module_markers(tree)), functions, tuple(undocumented))


def _test_functions(tree: ast.Module) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            found.append((node.name, node))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name.startswith("test"):
                    found.append((f"{node.name}.{member.name}", member))
    return found


def _module_markers(tree: ast.Module) -> set[str]:
    """The names in ``pytestmark = pytest.mark.x`` or ``pytestmark = [pytest.mark.x, ...]``."""
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets):
            continue
        values = node.value.elts if isinstance(node.value, (ast.List, ast.Tuple)) else [node.value]
        for value in values:
            name = _marker_name(value)
            if name is not None:
                names.add(name)
    return names


def _marker_name(value: ast.expr) -> str | None:
    if isinstance(value, ast.Call):
        value = value.func
    if (isinstance(value, ast.Attribute) and isinstance(value.value, ast.Attribute)
            and value.value.attr == "mark" and isinstance(value.value.value, ast.Name)
            and value.value.value.id == "pytest"):
        return value.attr
    return None


def mirrored_module(test_path: Path, project_root: Path) -> Path | None:
    """The module ``tests/unit/<path>/test_<name>.py`` tests, or None when there is none.

    ``<path>/<name>.py`` is preferred; ``<path>/_<name>.py`` lets a private
    module keep its underscore without the test file doubling it.
    """
    try:
        relative = test_path.relative_to(UNIT_MIRROR)
    except ValueError:
        return None
    if not relative.name.startswith("test_"):
        return None
    name = relative.name[len("test_"):]
    for candidate in (relative.with_name(name), relative.with_name(f"_{name}")):
        if (project_root / candidate).is_file():
            return candidate
    return None


def check(modules: list[TestModule], base: dict[Path, TestModule | None], project_root: Path) -> list[str]:
    """All breaches, one line each, for the given files against their base versions.

    ``base`` maps each legacy file's path to its parsed base version, or to
    None when the base revision does not have the file.
    """
    breaches: list[str] = []
    for module in modules:
        if module.legacy:
            breaches.extend(_check_legacy(module, base.get(module.path)))
            continue
        breaches.extend(_check_placement(module, project_root))
        for name, line in module.undocumented:
            breaches.append(f"{module.path}:{line}: {name} has no docstring stating its contract")
    return breaches


def _check_placement(module: TestModule, project_root: Path) -> list[str]:
    if module.path.is_relative_to(UNIT_MIRROR):
        if mirrored_module(module.path, project_root) is None:
            return [f"{module.path}: no module under devcapsule-src is mirrored by this file name"]
        return []
    if module.markers & HEAVIER_SUITE_MARKERS:
        return []
    return [f"{module.path}: a unit test file lives under {UNIT_MIRROR}, named after its module; "
            "a heavier suite's file carries that suite's marker at module level"]


def _check_legacy(module: TestModule, base: TestModule | None) -> list[str]:
    if base is None:
        return [f"{module.path}: marked legacy but the base revision has no such file; new tests follow the convention"]
    breaches: list[str] = []
    for name, source in module.functions.items():
        if name not in base.functions:
            breaches.append(f"{module.path}: {name} was added to a legacy file; put it in the mirror")
        elif source != base.functions[name]:
            breaches.append(f"{module.path}: {name} changed in a legacy file; fix it to the convention and move it to the mirror")
    for marker in sorted(module.markers - base.markers - {LEGACY_MARKER}):
        breaches.append(f"{module.path}: marker {marker!r} was added to a legacy file")
    return breaches


def _test_files(project_root: Path) -> list[Path]:
    return sorted(
        path.relative_to(project_root)
        for path in (project_root / "tests").rglob("test_*.py")
        if not _EXCLUDED_PARTS & set(path.parts)
    )


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=project_root, check=True, capture_output=True, text=True).stdout


def _base_version(project_root: Path, merge_base: str, path: Path) -> TestModule | None:
    prefix = _git(project_root, "rev-parse", "--show-prefix").strip()
    completed = subprocess.run(
        ["git", "show", f"{merge_base}:{prefix}{path.as_posix()}"],
        cwd=project_root, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        return None
    return parse_module(path, completed.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--base", default=os.environ.get("DEVCAPSULE_DIFF_BASE") or "origin/main",
                        help="the revision legacy files are compared with, at its merge base with HEAD")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="devcapsule-src")
    arguments = parser.parse_args(argv)
    root: Path = arguments.project_root.resolve()
    try:
        merge_base = _git(root, "merge-base", arguments.base, "HEAD").strip()
    except subprocess.CalledProcessError as error:
        print(f"test conventions: cannot resolve base {arguments.base!r}: {error.stderr.strip()}", file=sys.stderr)
        return 1
    modules = [parse_module(path, (root / path).read_text(encoding="utf-8")) for path in _test_files(root)]
    base = {module.path: _base_version(root, merge_base, module.path) for module in modules if module.legacy}
    breaches = check(modules, base, root)
    for breach in breaches:
        print(breach, file=sys.stderr)
    legacy = [module for module in modules if module.legacy]
    print(f"test conventions: {len(legacy)} legacy files holding {sum(len(m.functions) for m in legacy)} legacy tests; "
          f"{len(modules) - len(legacy)} files follow the convention; {len(breaches)} breaches")
    return 1 if breaches else 0


if __name__ == "__main__":
    sys.exit(main())
