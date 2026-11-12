"""Unit tests of ``scripts/validate_unittests_follow_conventions.py``, the gate's check of the unit-test conventions.

Each test builds the suite it checks under ``tmp_path``; the rules under
test are the ones *Unit Tests* in WORKFLOW-LOCAL.md states.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "validate_unittests_follow_conventions.py"


def _load(path: Path) -> Any:
    """The script as a module; registered in ``sys.modules`` so its dataclasses resolve their annotations."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


conventions = _load(_SCRIPT)


def _module(path: str, source: str) -> Any:
    return conventions.parse_module(Path(path), source)


DOCUMENTED = 'def test_one():\n    """It holds."""\n    assert True\n'
UNDOCUMENTED = "def test_one():\n    assert True\n"
GIT_DATE = "2026-11-08T12:00:00+00:00"


def test_module_markers_are_read_from_pytestmark_in_both_forms() -> None:
    """Precondition: a module assigns ``pytestmark`` a single marker or a list.
    Action: parse it. Postcondition: every marker name is reported."""
    single = _module("tests/a.py", "import pytest\npytestmark = pytest.mark.legacy\n")
    listed = _module("tests/b.py", "import pytest\npytestmark = [pytest.mark.e2e, pytest.mark.flaky(reason='x')]\n")
    assert single.markers == {"legacy"} and single.legacy
    assert listed.markers == {"e2e", "flaky"} and not listed.legacy


def test_a_test_function_is_recorded_with_its_decorators_and_without_trailing_whitespace() -> None:
    """Precondition: a test function with a decorator and trailing spaces.
    Action: parse it. Postcondition: its source starts at the decorator and
    carries no trailing whitespace, so a whitespace-only edit is not a change."""
    source = "import pytest\n\n@pytest.mark.parametrize('x', [1])\ndef test_one(x):   \n    assert x\n"
    module = _module("tests/a.py", source)
    assert module.functions == {"test_one": "@pytest.mark.parametrize('x', [1])\ndef test_one(x):\n    assert x"}


def test_methods_of_test_classes_are_qualified_by_their_class() -> None:
    """Precondition: a ``Test`` class holding a test method. Action: parse.
    Postcondition: the method is listed under ``Class.method``."""
    module = _module("tests/a.py", "class TestThing:\n    def test_one(self):\n        assert True\n")
    assert list(module.functions) == ["TestThing.test_one"]
    assert module.undocumented == (("TestThing.test_one", 2),)


def test_the_mirror_maps_a_test_file_to_its_public_or_private_module(tmp_path: Path) -> None:
    """Precondition: ``devcapsule/a/b.py`` and ``devcapsule/a/_c.py`` exist.
    Action: resolve the mirror for their test paths and for a stranger.
    Postcondition: both modules resolve, the stranger does not."""
    (tmp_path / "devcapsule" / "a").mkdir(parents=True)
    (tmp_path / "devcapsule" / "a" / "b.py").write_text("")
    (tmp_path / "devcapsule" / "a" / "_c.py").write_text("")
    assert conventions.mirrored_module(Path("tests/unit/devcapsule/a/test_b.py"), tmp_path) == Path("devcapsule/a/b.py")
    assert conventions.mirrored_module(Path("tests/unit/devcapsule/a/test_c.py"), tmp_path) == Path("devcapsule/a/_c.py")
    assert conventions.mirrored_module(Path("tests/unit/devcapsule/a/test_d.py"), tmp_path) is None
    assert conventions.mirrored_module(Path("tests/test_b.py"), tmp_path) is None


def test_a_documented_test_in_the_mirror_of_an_existing_module_passes(tmp_path: Path) -> None:
    """Precondition: a non-legacy, documented test file mirroring a real module.
    Action: check. Postcondition: no breach."""
    (tmp_path / "devcapsule").mkdir()
    (tmp_path / "devcapsule" / "thing.py").write_text("")
    module = _module("tests/unit/devcapsule/test_thing.py", DOCUMENTED)
    assert conventions.check([module], {}, tmp_path) == []


def test_a_non_legacy_file_outside_the_mirror_needs_a_heavier_suite_marker(tmp_path: Path) -> None:
    """Precondition: two documented files outside the mirror, one marked e2e.
    Action: check. Postcondition: only the unmarked one is a breach, naming the mirror."""
    marked = _module("tests/test_flow.py", "import pytest\npytestmark = pytest.mark.e2e\n" + DOCUMENTED)
    unmarked = _module("tests/test_flow2.py", DOCUMENTED)
    breaches = conventions.check([marked, unmarked], {}, tmp_path)
    assert len(breaches) == 1 and breaches[0].startswith("tests/test_flow2.py: a unit test file lives under tests/unit")


def test_a_mirror_file_naming_no_module_is_a_breach(tmp_path: Path) -> None:
    """Precondition: a documented file in the mirror whose name matches no module.
    Action: check. Postcondition: one breach naming the file."""
    module = _module("tests/unit/devcapsule/test_nothing.py", DOCUMENTED)
    breaches = conventions.check([module], {}, tmp_path)
    assert breaches == ["tests/unit/devcapsule/test_nothing.py: no module under devcapsule-src is mirrored by this file name"]


def test_an_undocumented_test_in_a_non_legacy_file_is_a_breach_at_its_line(tmp_path: Path) -> None:
    """Precondition: a mirror file with one undocumented test on line 3.
    Action: check. Postcondition: the breach names the function and the line."""
    (tmp_path / "devcapsule").mkdir()
    (tmp_path / "devcapsule" / "thing.py").write_text("")
    module = _module("tests/unit/devcapsule/test_thing.py", "import pytest\n\n" + UNDOCUMENTED)
    assert conventions.check([module], {}, tmp_path) == [
        "tests/unit/devcapsule/test_thing.py:3: test_one has no docstring stating its contract"
    ]


def test_an_unchanged_legacy_file_is_exempt_from_placement_and_docstrings(tmp_path: Path) -> None:
    """Precondition: an undocumented legacy file outside the mirror, unchanged from base.
    Action: check against that base. Postcondition: no breach."""
    source = "import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED
    module = _module("tests/test_old.py", source)
    base = _module("tests/test_old.py", UNDOCUMENTED)
    assert conventions.check([module], {module.path: base}, tmp_path) == []


def test_a_legacy_file_cannot_gain_change_or_drop_individual_tests_in_place(tmp_path: Path) -> None:
    """Precondition: base holds tests a, b, c; the legacy file drops a, keeps b, changes c and adds d.
    Action: check. Postcondition: a, c and d are breaches requiring whole-file retirement; b is not."""
    base = _module("tests/test_old.py", "def test_a():\n    pass\ndef test_b():\n    pass\ndef test_c():\n    pass\n")
    module = _module("tests/test_old.py", "import pytest\npytestmark = pytest.mark.legacy\n"
                     "def test_b():\n    pass\ndef test_c():\n    assert 1\ndef test_d():\n    pass\n")
    breaches = conventions.check([module], {module.path: base}, tmp_path)
    assert breaches == [
        "tests/test_old.py: test_c changed in a legacy file; refurbish the whole legacy file into tests/unit and delete tests/test_old.py",
        "tests/test_old.py: test_d was added to a legacy file; refurbish the whole legacy file into tests/unit and delete tests/test_old.py",
        "tests/test_old.py: test_a was removed while the legacy file remains; refurbish the whole legacy file into tests/unit and delete tests/test_old.py",
    ]


def test_a_new_or_changed_mirror_cannot_leave_its_flat_legacy_twin_behind(tmp_path: Path) -> None:
    """Precondition: ``devcapsule/thing.py`` has a flat legacy file ``tests/test_thing.py`` and a new or changed mirror.
    Action: check both new-mirror and changed-mirror cases. Postcondition: each reports the surviving legacy file."""
    (tmp_path / "devcapsule").mkdir()
    (tmp_path / "devcapsule" / "thing.py").write_text("")
    legacy = _module("tests/test_thing.py", "import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    mirror = _module("tests/unit/devcapsule/test_thing.py", DOCUMENTED)

    new_breaches = conventions.check([legacy, mirror], {legacy.path: legacy, mirror.path: None}, tmp_path)
    assert new_breaches == [
        "tests/unit/devcapsule/test_thing.py: its tests changed while tests/test_thing.py, "
        "the legacy file of the same name, remains; "
        "refurbish the whole legacy file into the mirror and delete tests/test_thing.py"
    ]

    old_mirror = _module("tests/unit/devcapsule/test_thing.py", 'def test_zero():\n    """Prior."""\n    assert True\n')
    changed_breaches = conventions.check([legacy, mirror], {legacy.path: legacy, mirror.path: old_mirror}, tmp_path)
    assert changed_breaches == new_breaches


def test_an_untouched_preexisting_mirror_and_non_flat_legacy_files_do_not_breach(tmp_path: Path) -> None:
    """Precondition: an unchanged pre-existing mirror/legacy pair, plus a new mirror sharing a basename with ``tests/configuration/test_contract.py``.
    Action: check. Postcondition: no breach."""
    (tmp_path / "devcapsule" / "container_runtime").mkdir(parents=True)
    (tmp_path / "devcapsule" / "thing.py").write_text("")
    (tmp_path / "devcapsule" / "container_runtime" / "contract.py").write_text("")
    legacy_flat = _module("tests/test_thing.py", "import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    untouched_mirror = _module("tests/unit/devcapsule/test_thing.py", DOCUMENTED)
    legacy_nested = _module("tests/configuration/test_contract.py", "import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    new_contract_mirror = _module("tests/unit/devcapsule/container_runtime/test_contract.py", DOCUMENTED)

    base = {
        legacy_flat.path: legacy_flat,
        untouched_mirror.path: untouched_mirror,
        legacy_nested.path: legacy_nested,
        new_contract_mirror.path: None,
    }
    assert conventions.check([legacy_flat, untouched_mirror, legacy_nested, new_contract_mirror], base, tmp_path) == []


def test_deleting_a_test_from_a_mirror_with_a_flat_legacy_twin_is_a_breach(tmp_path: Path) -> None:
    """Precondition: ``tests/test_thing.py`` is legacy; the mirror's base holds tests one and two and the mirror keeps only one.
    Action: check. Postcondition: one breach naming the legacy file, as for an addition or a change."""
    (tmp_path / "devcapsule").mkdir()
    (tmp_path / "devcapsule" / "thing.py").write_text("")
    legacy = _module("tests/test_thing.py", "import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    base_mirror = _module("tests/unit/devcapsule/test_thing.py", DOCUMENTED + 'def test_two():\n    """Also."""\n    assert True\n')
    mirror = _module("tests/unit/devcapsule/test_thing.py", DOCUMENTED)

    breaches = conventions.check([legacy, mirror], {legacy.path: legacy, mirror.path: base_mirror}, tmp_path)

    assert breaches == [
        "tests/unit/devcapsule/test_thing.py: its tests changed while tests/test_thing.py, "
        "the legacy file of the same name, remains; "
        "refurbish the whole legacy file into the mirror and delete tests/test_thing.py"
    ]


def test_a_mirror_edit_outside_its_tests_leaves_a_flat_legacy_twin_alone(tmp_path: Path) -> None:
    """Precondition: ``tests/test_thing.py`` is legacy; the mirror gains a module constant and keeps its tests as in base.
    Action: check. Postcondition: no breach, since only test functions are compared."""
    (tmp_path / "devcapsule").mkdir()
    (tmp_path / "devcapsule" / "thing.py").write_text("")
    legacy = _module("tests/test_thing.py", "import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    base_mirror = _module("tests/unit/devcapsule/test_thing.py", DOCUMENTED)
    mirror = _module("tests/unit/devcapsule/test_thing.py", "HELPER = 1\n\n" + DOCUMENTED)

    assert conventions.check([legacy, mirror], {legacy.path: legacy, mirror.path: base_mirror}, tmp_path) == []


def test_a_flat_legacy_file_of_a_heavier_suite_is_not_a_mirror_twin(tmp_path: Path) -> None:
    """Precondition: ``tests/test_thing.py`` carries ``legacy`` and ``e2e``; a new documented mirror shares its name.
    Action: check. Postcondition: no breach, since the flat file is not a unit-test file."""
    (tmp_path / "devcapsule").mkdir()
    (tmp_path / "devcapsule" / "thing.py").write_text("")
    legacy_e2e = _module("tests/test_thing.py", "import pytest\npytestmark = [pytest.mark.legacy, pytest.mark.e2e]\n" + UNDOCUMENTED)
    mirror = _module("tests/unit/devcapsule/test_thing.py", DOCUMENTED)

    assert conventions.check([legacy_e2e, mirror], {legacy_e2e.path: legacy_e2e, mirror.path: None}, tmp_path) == []


def test_a_changed_decorator_on_a_legacy_class_method_is_a_breach(tmp_path: Path) -> None:
    """Precondition: base holds ``TestThing.test_one`` under one ``parametrize``; the legacy file changes only that decorator.
    Action: check. Postcondition: one breach naming the qualified method as changed."""
    body = "class TestThing:\n    @pytest.mark.parametrize('x', [{}])\n    def test_one(self, x):\n        assert x\n"
    base = _module("tests/test_old.py", "import pytest\npytestmark = pytest.mark.legacy\n" + body.format(1))
    module = _module("tests/test_old.py", "import pytest\npytestmark = pytest.mark.legacy\n" + body.format(2))

    breaches = conventions.check([module], {module.path: base}, tmp_path)

    assert breaches == [
        "tests/test_old.py: TestThing.test_one changed in a legacy file; "
        "refurbish the whole legacy file into tests/unit and delete tests/test_old.py"
    ]


def test_a_marker_other_than_legacy_cannot_be_added_to_a_legacy_file(tmp_path: Path) -> None:
    """Precondition: base has no module marker; the legacy file adds legacy and skip.
    Action: check. Postcondition: skip is a breach, legacy is not."""
    base = _module("tests/test_old.py", UNDOCUMENTED)
    module = _module("tests/test_old.py", "import pytest\npytestmark = [pytest.mark.legacy, pytest.mark.skip]\n" + UNDOCUMENTED)
    assert conventions.check([module], {module.path: base}, tmp_path) == [
        "tests/test_old.py: marker 'skip' was added to a legacy file"
    ]


def test_a_legacy_file_the_base_lacks_is_refused(tmp_path: Path) -> None:
    """Precondition: a legacy file with no base version. Action: check.
    Postcondition: one breach saying new tests follow the convention."""
    module = _module("tests/test_new.py", "import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    breaches = conventions.check([module], {module.path: None}, tmp_path)
    assert len(breaches) == 1 and breaches[0].endswith("new tests follow the convention")


def _git(root: Path, *arguments: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_DATE": GIT_DATE, "GIT_COMMITTER_DATE": GIT_DATE}
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.test", *arguments],
        cwd=root, check=True, capture_output=True, env=env,
    )


def test_main_compares_legacy_files_with_the_merge_base_and_exits_one_on_a_breach(tmp_path: Path) -> None:
    """Precondition: a repository whose base commit holds a legacy test, then a
    commit on a branch that changes that test's body. Action: run ``main`` with
    the base ref. Postcondition: exit 1, the breach on stderr, the summary on stdout."""
    root = tmp_path / "devcapsule-src"
    tests = root / "tests"
    tests.mkdir(parents=True)
    (tests / "test_old.py").write_text("import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "slice")
    (tests / "test_old.py").write_text("import pytest\npytestmark = pytest.mark.legacy\ndef test_one():\n    assert 1\n")
    _git(root, "commit", "-q", "-am", "change")
    status = conventions.main(["--base", "main", "--project-root", str(root)])
    assert status == 1


def test_main_passes_when_an_entire_legacy_file_is_retired_into_its_mirror(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Precondition: a repository whose branch deletes ``tests/test_thing.py`` and replaces it with
    ``tests/unit/devcapsule/test_thing.py``. Action: run ``main``.
    Postcondition: exit 0 and the summary counts 0 legacy files and 1 conforming file."""
    root = tmp_path / "devcapsule-src"
    (root / "devcapsule").mkdir(parents=True)
    (root / "devcapsule" / "thing.py").write_text("")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_thing.py").write_text("import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "slice")
    (tests / "test_thing.py").unlink()
    (tests / "unit" / "devcapsule").mkdir(parents=True)
    (tests / "unit" / "devcapsule" / "test_thing.py").write_text(DOCUMENTED)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "retire")
    status = conventions.main(["--base", "main", "--project-root", str(root)])
    assert status == 0
    assert "0 legacy files holding 0 legacy tests; 1 files follow the convention; 0 breaches" in capsys.readouterr().out


def test_main_fails_when_a_new_mirror_leaves_its_legacy_file_behind(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Precondition: a repository whose branch adds ``tests/unit/devcapsule/test_thing.py`` without
    deleting ``tests/test_thing.py``. Action: run ``main``.
    Postcondition: exit 1 and stderr names ``tests/test_thing.py``."""
    root = tmp_path / "devcapsule-src"
    (root / "devcapsule").mkdir(parents=True)
    (root / "devcapsule" / "thing.py").write_text("")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_thing.py").write_text("import pytest\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "slice")
    (tests / "unit" / "devcapsule").mkdir(parents=True)
    (tests / "unit" / "devcapsule" / "test_thing.py").write_text(DOCUMENTED)
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "split")
    assert conventions.main(["--base", "main", "--project-root", str(root)]) == 1
    assert "tests/test_thing.py, the legacy file of the same name, remains" in capsys.readouterr().err


def test_main_fails_when_the_base_cannot_be_resolved(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Precondition: a repository with no ref named ``nowhere``. Action: run ``main``
    with that base. Postcondition: exit 1 and a message naming the base."""
    root = tmp_path / "devcapsule-src"
    (root / "tests").mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "commit", "-q", "--allow-empty", "-m", "base")
    assert conventions.main(["--base", "nowhere", "--project-root", str(root)]) == 1
    assert "cannot resolve base 'nowhere'" in capsys.readouterr().err


# Rule 4, the command line. ``_mirror`` gives each case a mirror file that the
# other rules accept, so that a breach reported here is rule 4's.

DEBT_LIST = "tests/command_line_debt.txt"


def _mirror(root: Path, name: str, source: str) -> Any:
    """A documented test file ``tests/unit/devcapsule/test_<name>.py`` with the given imports, and the module it mirrors."""
    (root / "devcapsule").mkdir(exist_ok=True)
    (root / "devcapsule" / f"{name}.py").write_text("")
    return _module(f"tests/unit/devcapsule/test_{name}.py", source + DOCUMENTED)


@pytest.mark.parametrize(("source", "imported"), [
    ("import a.b\n", {"a.b"}),
    ("from a import b\n", {"a", "a.b"}),
    ("from a.b import c as d\n", {"a.b", "a.b.c"}),
    ("def helper():\n    import a.b\n", {"a.b"}),
    ("from . import b\n", {"tests.unit", "tests.unit.b"}),
    ("from ..c import d\n", {"tests.c", "tests.c.d"}),
    ("import importlib\nmodule = importlib.import_module('devcapsule.cli')\n", {"importlib", "devcapsule.cli"}),
    ("EXPECTED = {'devcapsule.cli'}\n", set()),
])
def test_a_files_imports_are_recorded_in_every_form(source: str, imported: set[str]) -> None:
    """``parse_module`` records an import statement at any depth, both readings of ``from a import b``, a relative
    import by its full name, and a call handed the command line's name as a string, as ``importlib`` takes it;
    the same string outside a call is no import."""
    assert _module("tests/unit/test_a.py", source).imports == imported


@pytest.mark.parametrize("source", [
    "from devcapsule import cli\n",
    "import devcapsule.cli\n",
    "from devcapsule.cli import main\n",
    "from devcapsule.__main__ import main\n",
    "def run():\n    from devcapsule import cli\n",
])
def test_a_file_that_imports_the_command_line_is_a_breach(tmp_path: Path, source: str) -> None:
    """A mirror file that imports ``devcapsule.cli`` or ``devcapsule.__main__``, in any form, is one breach
    naming the file and the one file that may."""
    breaches = conventions.check([_mirror(tmp_path, "thing", source)], {}, tmp_path)
    assert len(breaches) == 1
    assert breaches[0].startswith("tests/unit/devcapsule/test_thing.py: imports devcapsule.")
    assert "only tests/unit/devcapsule/test_cli.py invokes it" in breaches[0]


def test_the_mirror_of_the_command_line_and_a_legacy_file_may_import_it(tmp_path: Path) -> None:
    """``tests/unit/devcapsule/test_cli.py`` and an unchanged legacy file import ``devcapsule.cli`` without a breach."""
    mirror = _mirror(tmp_path, "cli", "from devcapsule import cli\n")
    legacy = _module("tests/test_old.py", "import pytest\nfrom devcapsule import cli\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    assert conventions.check([mirror, legacy], {legacy.path: legacy}, tmp_path) == []


def test_a_heavier_suites_file_that_imports_the_command_line_is_a_breach(tmp_path: Path) -> None:
    """An integration file is held to the rule as well: it starts the program, it does not import it."""
    module = _module("tests/integration/test_flow.py", "import pytest\nfrom devcapsule import cli\npytestmark = pytest.mark.integration\n" + DOCUMENTED)
    breaches = conventions.check([module], {}, tmp_path)
    assert len(breaches) == 1 and breaches[0].startswith("tests/integration/test_flow.py: imports devcapsule.cli")


def test_the_command_line_reached_through_helpers_is_a_breach(tmp_path: Path) -> None:
    """A mirror file that imports a helper, which imports a second helper, which imports the command line, is a
    breach naming the helper it imports; a mirror file that imports a helper outside that chain is none."""
    near = _module("tests/flows.py", "from tests import launch\n")
    far = _module("tests/launch.py", "from devcapsule import cli\n")
    plain = _module("tests/values.py", "import json\n")
    reaching = _mirror(tmp_path, "thing", "from tests.flows import prepared\n")
    clean = _mirror(tmp_path, "other", "from tests.values import sample\n")
    assert conventions.check([reaching, clean], {}, tmp_path, support=[near, far, plain]) == [
        "tests/unit/devcapsule/test_thing.py: imports tests.flows, which is or reaches the command line; "
        "only tests/unit/devcapsule/test_cli.py invokes it. Test the module that does the work, or start the "
        "program in an integration test"
    ]


def test_the_command_line_reached_through_a_legacy_test_file_is_a_breach(tmp_path: Path) -> None:
    """A mirror file that imports a fixture from a legacy test file which imports the command line is a breach."""
    legacy = _module("tests/test_old.py", "import pytest\nfrom devcapsule import cli\npytestmark = pytest.mark.legacy\n" + UNDOCUMENTED)
    mirror = _mirror(tmp_path, "thing", "from tests.test_old import project\n")
    breaches = conventions.check([legacy, mirror], {legacy.path: legacy}, tmp_path)
    assert len(breaches) == 1 and breaches[0].startswith("tests/unit/devcapsule/test_thing.py: imports tests.test_old,")


def test_a_conftest_that_reaches_the_command_line_is_a_breach(tmp_path: Path) -> None:
    """A ``conftest.py`` that imports the command line is a breach although no test imports the conftest;
    a helper that is not a conftest is none by itself."""
    conftest = _module("tests/unit/conftest.py", "from devcapsule import cli\n")
    helper = _module("tests/launch.py", "from devcapsule import cli\n")
    breaches = conventions.check([], {}, tmp_path, support=[conftest, helper])
    assert len(breaches) == 1 and breaches[0].startswith("tests/unit/conftest.py: imports devcapsule.cli")


def test_a_file_in_debt_is_exempt_while_it_reaches_the_command_line_and_refused_once_it_does_not(tmp_path: Path) -> None:
    """A listed file that imports the command line is no breach. A listed file that does not is one, asking for
    its line to be deleted, and so is a listed path that is no checked file."""
    reaching = _mirror(tmp_path, "thing", "from devcapsule import cli\n")
    fixed = _mirror(tmp_path, "other", "")
    debt = frozenset({reaching.path, fixed.path, Path("tests/unit/devcapsule/test_gone.py")})
    assert conventions.check([reaching, fixed], {}, tmp_path, debt=debt) == [
        f"tests/unit/devcapsule/test_other.py: no longer reaches the command line; delete its line from {DEBT_LIST}",
        f"tests/unit/devcapsule/test_gone.py: listed in {DEBT_LIST} but not a file rule 4 checks; delete its line",
    ]


def _repository_in_debt(tmp_path: Path) -> Path:
    """A committed repository on ``main`` with two mirror files that import the command line, the first one listed as debt."""
    root = tmp_path / "devcapsule-src"
    mirror = root / "tests" / "unit" / "devcapsule"
    mirror.mkdir(parents=True)
    for name in ("thing", "other"):
        (root / "devcapsule" / f"{name}.py").parent.mkdir(exist_ok=True)
        (root / "devcapsule" / f"{name}.py").write_text("")
        (mirror / f"test_{name}.py").write_text("from devcapsule import cli\n" + DOCUMENTED)
    (root / DEBT_LIST).write_text("# the debt\n\ntests/unit/devcapsule/test_thing.py  # the first\n")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "slice")
    return root


def test_main_reads_the_debt_list_of_the_repository_it_checks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With one of two reaching files listed in the repository's debt list, comments aside, ``main`` exits 1,
    names only the unlisted file, and counts one file in debt."""
    root = _repository_in_debt(tmp_path)
    assert conventions.main(["--base", "main", "--project-root", str(root)]) == 1
    captured = capsys.readouterr()
    assert "tests/unit/devcapsule/test_other.py: imports devcapsule.cli" in captured.err
    assert "test_thing.py" not in captured.err
    assert "1 breaches; 1 files in command-line debt" in captured.out


def test_main_refuses_a_line_added_to_the_debt_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """When a branch lists a second reaching file that the base's list does not have, ``main`` exits 1 and
    names the added line: the list loses lines and never gains one."""
    root = _repository_in_debt(tmp_path)
    with (root / DEBT_LIST).open("a") as listing:
        listing.write("tests/unit/devcapsule/test_other.py\n")
    assert conventions.main(["--base", "main", "--project-root", str(root)]) == 1
    captured = capsys.readouterr()
    assert captured.err == f"{DEBT_LIST}: tests/unit/devcapsule/test_other.py was added; the list loses lines and never gains one\n"
