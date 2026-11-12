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
3. **Whole-file legacy retirement.** A legacy file, one whose module-level
   ``pytestmark`` includes ``legacy``, is compared with the base revision:
   no test function is added, changed or removed while the file remains, and
   no marker other than ``legacy`` is added. A legacy file the base does not
   have is refused. Adding, changing or deleting a test in ``tests/unit/<path>/test_<name>.py``
   while a flat legacy unit-test file ``tests/test_<name>.py`` still exists is
   also refused, the two paired by file name alone; refurbish the entire
   legacy file into the mirror and delete it.
4. **The command line.** Only ``tests/unit/devcapsule/test_cli.py`` imports
   ``devcapsule.cli`` or ``devcapsule.__main__``. Every other file that is
   not legacy is refused when it imports one of them, or a module under
   ``tests`` that does, however many imports away. A ``conftest.py`` is
   refused too, since its fixtures reach tests without an import. The files
   listed in ``tests/command_line_debt.txt`` did so when the rule was
   written; the list may lose lines and never gains one.

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
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["TestModule", "parse_module", "mirrored_module", "check", "main"]

LEGACY_MARKER = "legacy"
"""The module-level marker that exempts a file from rules 1 and 2 and subjects it to rule 3."""

HEAVIER_SUITE_MARKERS = frozenset({
    "integration", "e2e", "recursive_e2e", "contributor_e2e", "ide_smoke", "base_build_e2e",
})
"""Markers of the suites that are not unit tests; a file carrying one may live outside the mirror."""

FLAT_TESTS_DIR = Path("tests")
"""The root test directory holding flat legacy unit-test files."""

UNIT_MIRROR = Path("tests") / "unit"
"""The directory that mirrors ``devcapsule-src`` for unit tests."""

COMMAND_LINE = frozenset({"devcapsule.cli", "devcapsule.__main__"})
"""The modules that are the product's command line.

A test that imports one can run any command in its own process, and a command
does all the product does: it reads the developer's settings and can reach the
network. On 2026-11-12 one such "unit" test downloaded 1.5 GB.
"""

COMMAND_LINE_MIRROR = UNIT_MIRROR / "devcapsule" / "test_cli.py"
"""The one test file that may import the command line: the mirror of ``devcapsule/cli.py``."""

COMMAND_LINE_DEBT = Path("tests") / "command_line_debt.txt"
"""The list of the files that reached the command line when rule 4 was written.

It is data of the repository, not of this script, so that the script checks
any repository it is pointed at. One path per line, relative to
``devcapsule-src``; a ``#`` starts a comment.
"""

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
    imports: frozenset[str] = frozenset()
    """Every module the file imports, by dotted name, wherever the import stands.

    ``from a import b`` is recorded as ``a`` and as ``a.b``: only the importer
    knows whether ``b`` is a module, and rule 4 must not depend on it. A call
    given the command line's name as a string, as ``importlib.import_module``
    takes it, is recorded as an import of it.
    """

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
    return TestModule(path, frozenset(_module_markers(tree)), functions, tuple(undocumented), _imports(tree, path))


def _module_name(path: Path) -> str:
    """The dotted name Python imports a file by: ``tests/a/b.py`` is ``tests.a.b``, ``tests/a/__init__.py`` is ``tests.a``."""
    parts = path.with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(tree: ast.Module, path: Path) -> frozenset[str]:
    """The dotted names of the modules a file imports; see ``TestModule.imports``."""
    package = _module_name(path).split(".")
    if path.name != "__init__.py":
        package = package[:-1]
    names: set[str] = set()
    # ast.walk visits every node, so an import inside a function is found like one at the top.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # ``from . import x`` has level 1 and starts at the file's own package; each further dot climbs one package.
            origin = package[:len(package) - node.level + 1] if node.level else []
            source = ".".join([*origin, *([node.module] if node.module else [])])
            names.add(source)
            names.update(f"{source}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            # ``importlib.import_module("devcapsule.cli")`` imports the command line without an import statement:
            # a call that is handed its name as a string counts. The name in any other place, an expected value
            # for instance, does not.
            names.update(
                argument.value for argument in node.args
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str) and argument.value in COMMAND_LINE
            )
    return frozenset(names)


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


def check(
    modules: list[TestModule],
    base: dict[Path, TestModule | None],
    project_root: Path,
    support: Sequence[TestModule] = (),
    debt: frozenset[Path] = frozenset(),
) -> list[str]:
    """All breaches, one line each, for the given files against their base versions.

    ``base`` maps each checked file's path to its parsed base version, or to
    None when the base revision does not have the file.

    ``support`` is every other Python file under ``tests``: helpers and
    ``conftest.py`` files. Rule 4 reads their imports and nothing else of them.
    ``debt`` is the paths rule 4 exempts while they still breach it.
    """
    carriers = _command_line_carriers([*modules, *support])
    flat_legacy_by_name: dict[str, list[Path]] = {}
    for module in modules:
        if _is_flat_legacy_unit_file(module):
            flat_legacy_by_name.setdefault(module.path.name, []).append(module.path)

    breaches: list[str] = []
    for module in modules:
        if module.legacy:
            breaches.extend(_check_legacy(module, base.get(module.path)))
            continue
        placement_breaches = _check_placement(module, project_root)
        breaches.extend(placement_breaches)
        if not placement_breaches and module.path.is_relative_to(UNIT_MIRROR):
            breaches.extend(_check_mirror_against_legacy(
                module, base.get(module.path), flat_legacy_by_name.get(module.path.name, []),
            ))
        for name, line in module.undocumented:
            breaches.append(f"{module.path}:{line}: {name} has no docstring stating its contract")
        breaches.extend(_check_command_line(module, carriers, debt))
    for helper in support:
        # A fixture defined in a conftest reaches every test below it with no import in the test to see.
        if helper.path.name == "conftest.py":
            breaches.extend(_check_command_line(helper, carriers, debt))
    # A listed path that is gone, or that names a legacy file, was judged by nothing above, so its line is stale.
    for path in sorted(debt - {module.path for module in modules if not module.legacy} - {helper.path for helper in support}):
        breaches.append(f"{path}: listed in {COMMAND_LINE_DEBT} but not a file rule 4 checks; delete its line")
    return breaches


def _command_line_carriers(files: Iterable[TestModule]) -> frozenset[str]:
    """The modules under ``tests`` through which a test reaches the command line.

    A helper that calls ``cli.main`` gives the command line to every test that
    imports the helper. So a carrier is a file that imports the command line,
    or imports a carrier, and importing a carrier counts as importing the
    command line itself.
    """
    imports = {_module_name(file.path): file.imports for file in files}
    carriers: set[str] = set()
    grew = True
    while grew:  # A carrier can be several imports from the command line; stop when a pass finds no new one.
        grew = False
        for name, imported in imports.items():
            if name not in carriers and imported & (COMMAND_LINE | carriers):
                carriers.add(name)
                grew = True
    return frozenset(carriers)


def _check_command_line(module: TestModule, carriers: frozenset[str], debt: frozenset[Path]) -> list[str]:
    """The breach of rule 4 by one file that is not legacy, or nothing.

    A file reaches the command line when it imports it, or imports a carrier.
    """
    if module.path == COMMAND_LINE_MIRROR:
        return []
    reached = sorted(module.imports & (COMMAND_LINE | carriers))
    if module.path in debt:
        # The list only shrinks: a listed file that no longer needs its line must lose it in the same change.
        if reached:
            return []
        return [f"{module.path}: no longer reaches the command line; delete its line from {COMMAND_LINE_DEBT}"]
    if not reached:
        return []
    return [
        f"{module.path}: imports {reached[0]}, which is or reaches the command line; only {COMMAND_LINE_MIRROR} "
        "invokes it. Test the module that does the work, or start the program in an integration test"
    ]


def _is_flat_legacy_unit_file(module: TestModule) -> bool:
    return (
        module.legacy
        and module.path.parent == FLAT_TESTS_DIR
        and not (module.markers & HEAVIER_SUITE_MARKERS)
    )


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
            breaches.append(
                f"{module.path}: {name} was added to a legacy file; "
                f"refurbish the whole legacy file into {UNIT_MIRROR} and delete {module.path}"
            )
        elif source != base.functions[name]:
            breaches.append(
                f"{module.path}: {name} changed in a legacy file; "
                f"refurbish the whole legacy file into {UNIT_MIRROR} and delete {module.path}"
            )
    for name in base.functions:
        if name not in module.functions:
            breaches.append(
                f"{module.path}: {name} was removed while the legacy file remains; "
                f"refurbish the whole legacy file into {UNIT_MIRROR} and delete {module.path}"
            )
    for marker in sorted(module.markers - base.markers - {LEGACY_MARKER}):
        breaches.append(f"{module.path}: marker {marker!r} was added to a legacy file")
    return breaches


def _check_mirror_against_legacy(
    module: TestModule,
    base_mirror: TestModule | None,
    legacy_paths: list[Path],
) -> list[str]:
    if not legacy_paths:
        return []
    if base_mirror is not None and module.functions == base_mirror.functions:
        return []
    return [
        f"{module.path}: its tests changed while {legacy_path}, the legacy file of the same name, remains; "
        f"refurbish the whole legacy file into the mirror and delete {legacy_path}"
        for legacy_path in legacy_paths
    ]


def _test_files(project_root: Path) -> list[Path]:
    return sorted(
        path.relative_to(project_root)
        for path in (project_root / "tests").rglob("test_*.py")
        if not _EXCLUDED_PARTS & set(path.parts)
    )


def _support_files(project_root: Path) -> list[Path]:
    """Every Python file under ``tests`` that is not a test file: helpers, ``conftest.py``, ``__init__.py``."""
    return sorted(
        path.relative_to(project_root)
        for path in (project_root / "tests").rglob("*.py")
        if not path.name.startswith("test_") and not _EXCLUDED_PARTS & set(path.parts)
    )


def _debt(text: str) -> frozenset[Path]:
    """The paths a debt list names: one per line, comments and blank lines aside."""
    lines = (line.split("#", 1)[0].strip() for line in text.splitlines())
    return frozenset(Path(line) for line in lines if line)


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=project_root, check=True, capture_output=True, text=True).stdout


def _base_text(project_root: Path, merge_base: str, path: Path) -> str | None:
    """A file's text at the base revision, or None when the base does not have it."""
    prefix = _git(project_root, "rev-parse", "--show-prefix").strip()
    completed = subprocess.run(
        ["git", "show", f"{merge_base}:{prefix}{path.as_posix()}"],
        cwd=project_root, capture_output=True, text=True,
    )
    return completed.stdout if completed.returncode == 0 else None


def _base_version(project_root: Path, merge_base: str, path: Path) -> TestModule | None:
    text = _base_text(project_root, merge_base, path)
    return None if text is None else parse_module(path, text)


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
    flat_legacy_names = {module.path.name for module in modules if _is_flat_legacy_unit_file(module)}
    needs_base = [
        module for module in modules
        if module.legacy or (module.path.is_relative_to(UNIT_MIRROR) and module.path.name in flat_legacy_names)
    ]
    base = {module.path: _base_version(root, merge_base, module.path) for module in needs_base}
    support = [parse_module(path, (root / path).read_text(encoding="utf-8")) for path in _support_files(root)]
    debt_file = root / COMMAND_LINE_DEBT
    debt = _debt(debt_file.read_text(encoding="utf-8")) if debt_file.is_file() else frozenset()
    breaches = check(modules, base, root, support, debt)
    # The debt list never grows. A base without the list is the change that introduces it, which review reads whole.
    base_debt = _base_text(root, merge_base, COMMAND_LINE_DEBT)
    if base_debt is not None:
        for path in sorted(debt - _debt(base_debt)):
            breaches.append(f"{COMMAND_LINE_DEBT}: {path} was added; the list loses lines and never gains one")
    for breach in breaches:
        print(breach, file=sys.stderr)
    legacy = [module for module in modules if module.legacy]
    print(f"test conventions: {len(legacy)} legacy files holding {sum(len(m.functions) for m in legacy)} legacy tests; "
          f"{len(modules) - len(legacy)} files follow the convention; {len(breaches)} breaches; "
          f"{len(debt)} files in command-line debt")
    return 1 if breaches else 0


if __name__ == "__main__":
    sys.exit(main())
