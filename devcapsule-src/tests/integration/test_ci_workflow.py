"""Integration tests of the hosted workflow's routing, against the repository's own workflow and filter files.

They read ``.github/workflows/tests.yml`` and the two filter files as they are, run the workflow's
route script under bash, and run git, coverage.py and diff-cover for the advisory report: real
files and real programs, so none of them is a unit test.
"""
from __future__ import annotations

import fnmatch
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.conftest import PYTHON_ROUTE_INPUTS, REPOSITORY_ROOT, RepositoryInputGuard, load_python_route_inputs

pytestmark = pytest.mark.integration

_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "tests.yml"
_WEBSITE_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "website.yml"
_DOCS_FILTER = REPOSITORY_ROOT / ".github" / "ci-paths.yml"
_ANNOTATIONS = REPOSITORY_ROOT / "devcapsule-src" / "scripts" / "diff_coverage_annotations.py"


def _job_step(workflow_path: Path, job: str, identifier: str) -> dict[str, Any]:
    """The step of ``job`` in ``workflow_path`` with the given ``id``."""
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    return next(step for step in workflow["jobs"][job]["steps"] if step.get("id") == identifier)


def _step(identifier: str) -> dict[str, Any]:
    """The step of the workflow's ``changes`` job with the given id."""
    return _job_step(_WORKFLOW, "changes", identifier)


def _picomatch_like(path: str, glob: str) -> bool:
    """Mirror picomatch with dot: true for the grammar ``.github/ci-paths.yml`` uses.

    Literal segments, ``*`` within one segment, and ``**`` for any number of
    segments including none, so ``a/**`` matches ``a`` itself. Checked against
    picomatch 2.3.1, the version paths-filter v3.0.4 bundles.
    """
    def match(parts: list[str], segments: list[str]) -> bool:
        if not segments:
            return not parts
        if segments[0] == "**":
            return any(match(parts[index:], segments[1:]) for index in range(len(parts) + 1))
        return bool(parts) and fnmatch.fnmatchcase(parts[0], segments[0]) and match(parts[1:], segments[1:])
    return match(path.split("/"), glob.split("/"))


@pytest.mark.parametrize(("path", "python"), [
    ("devcapsule-src/tests/a.py", True),
    ("devcapsule-src/pyproject.toml", True),
    ("devcapsule-src/dev-requirements.txt", True),
    ("devcapsule-src/devcapsule/assets/project_workflow/definition/WORKFLOW.md", True),
    ("devcapsule-webconsole/devcapsule_webconsole/app.py", True),
    (".github/workflows/tests.yml", True),
    (".github/ci-python-inputs.yml", True),
    (".devcapsule/devcapsule.toml", True),
    ("component-status/policy-v1.json", True),
    ("docs/versions.yaml", True),
    ("docs/guide.md", False),
    ("engineering-docs/releases/v0.2.14/notes.md", True),
    ("engineering-docs/releases/v0.3.1/bugs.md", False),
    ("engineering-docs/pile-of-ideas/an-idea.md", False),
    ("engineering-docs/bugs/devcapsule/a-bug.md", False),
    ("engineering-docs/wip/a/CURRENT-STATUS.md", False),
    ("engineering-docs/new-subtree/note.md", False),
    ("WORKFLOW.md", False),
    ("WORKFLOW-humane.md", False),
    ("README.md", False),
    ("CURRENT-STATUS.md", False),
    ("index.md", False),
    (".gitmodules", False),
    ("website", False),
    ("scripts/website.sh", False),
    ("unknown/new-input", False),
])
def test_the_python_route_is_selected_by_its_listed_inputs_alone(path: str, python: bool) -> None:
    """Precondition: the repository's list of Python-route inputs. Action: ask the guard, which
    reads an entry as the hosted filter does, whether a changed path is covered. Postcondition:
    the package, the console, the workflows and the named legacy inputs select the route; every
    other path, known or new, does not."""
    guard = RepositoryInputGuard(REPOSITORY_ROOT, load_python_route_inputs(PYTHON_ROUTE_INPUTS))
    assert (guard.unlisted(REPOSITORY_ROOT / path) is None) is python


@pytest.mark.parametrize(("path", "docs"), [
    ("engineering-docs/wip/a/CURRENT-STATUS.md", False),
    ("engineering-docs/work-orders/new.md", False),
    ("CURRENT-STATUS.md", False),
    ("README.md", True),
    ("docs/guide.md", True),
    ("docs/README.md", True),
    ("docs/getting-started/first-session.md", True),
    ("docs/versions.yaml", True),
    ("engineering-docs/blog/new.md", True),
    ("engineering-docs/blog/assets/demo/poster.png", True),
    ("engineering-docs/README.md", True),
    ("engineering-docs/releases/v0.2.14/notes.md", True),
    ("engineering-docs/design-notes/devcapsule/competitive-comparison.md", True),
    ("engineering-docs/new-subtree/note.md", True),
    ("website", True),
    ("website/README.md", True),
    ("scripts/website.sh", True),
    ("devcapsule-src/devcapsule/assets/project_workflow/definition/WORKFLOW.md", False),
    ("devcapsule-src/tests/a.py", False),
    ("devcapsule-src/pyproject.toml", True),
    ("devcapsule-src/dev-requirements.txt", False),
    ("devcapsule-webconsole/devcapsule_webconsole/app.py", False),
    (".gitmodules", True),
    (".github/workflows/tests.yml", True),
    (".github/ci-paths.yml", True),
    (".ast-grep/new.yml", True),
    ("WORKFLOW.md", True),
    ("unknown/new-input", True),
])
def test_the_docs_route_is_selected_unless_a_listed_non_input_covers_the_path(path: str, docs: bool) -> None:
    """Precondition: the repository's docs filter. Action: match a changed path against every
    pattern as picomatch would. Postcondition: every pattern is a negation in the mirrored
    grammar, and the route is selected exactly when no listed non-input covers the path, so an
    unclassified path builds the website."""
    patterns = yaml.safe_load(_DOCS_FILTER.read_text(encoding="utf-8"))["docs"]
    assert all(pattern.startswith("!") and not any(character in pattern[1:] for character in "?[]{}()!") for pattern in patterns)
    assert all(not _picomatch_like(path, pattern[1:]) for pattern in patterns) is docs


def test_each_filter_file_is_read_with_the_quantifier_its_patterns_assume() -> None:
    """Precondition: the workflow as committed. Action: read the two filter steps and the route
    step. Postcondition: the docs filter requires every negation to hold; the Python filter
    uses the default, any listed input; and the route step takes each route from its own
    filter."""
    docs, python, route = _step("filter"), _step("python-inputs"), _step("route")
    assert docs["with"] == {"predicate-quantifier": "every", "filters": ".github/ci-paths.yml"}
    assert python["with"] == {"filters": ".github/ci-python-inputs.yml"}
    assert route["env"]["DOCS_CHANGED"] == "${{ steps.filter.outputs.docs }}"
    assert route["env"]["PYTHON_CHANGED"] == "${{ steps.python-inputs.outputs.python }}"


def _route(tmp_path: Path, **env: str) -> tuple[int, dict[str, str]]:
    """Run the workflow's route script as GitHub's bash would, returning its status and outputs."""
    output = tmp_path / "github-output"
    output.touch()
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", _step("route")["run"]],
        env={"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output), **env},
        capture_output=True, text=True,
    )
    lines = output.read_text(encoding="utf-8").splitlines()
    return result.returncode, dict(line.split("=", 1) for line in lines)


@pytest.mark.parametrize(("env", "routes"), [
    ({"EVENT_NAME": "pull_request", "PYTHON_CHANGED": "false", "CHANGED_FILES": "17", "DOCS_CHANGED": "true"},
     {"python": "false", "docs": "true"}),
    ({"EVENT_NAME": "pull_request", "PYTHON_CHANGED": "false", "CHANGED_FILES": "3000", "DOCS_CHANGED": "false"},
     {"python": "false", "docs": "false"}),
    # The filters never see files beyond GitHub's 3000-file listing.
    ({"EVENT_NAME": "pull_request", "PYTHON_CHANGED": "false", "CHANGED_FILES": "3001", "DOCS_CHANGED": "false"},
     {"python": "true", "docs": "true"}),
    ({"EVENT_NAME": "push", "PYTHON_CHANGED": "", "DOCS_CHANGED": ""}, {"python": "true", "docs": "true"}),
    ({"EVENT_NAME": "merge_group", "PYTHON_CHANGED": "", "DOCS_CHANGED": ""}, {"python": "true", "docs": "true"}),
    ({"EVENT_NAME": "workflow_dispatch", "PYTHON_CHANGED": "", "DOCS_CHANGED": ""}, {"python": "true", "docs": "true"}),
])
def test_the_route_step_passes_the_filters_through_and_runs_everything_otherwise(
    tmp_path: Path, env: dict[str, str], routes: dict[str, str],
) -> None:
    """Precondition: the workflow's route script and one event. Action: run it under bash.
    Postcondition: a pull request within GitHub's file listing gets the filters' routes; a
    larger one, and every push, merge-queue check and manual run, gets both."""
    assert _route(tmp_path, **env) == (0, routes)


@pytest.mark.parametrize("env", [
    {"PYTHON_CHANGED": "", "DOCS_CHANGED": "true"},
    {"PYTHON_CHANGED": "true", "DOCS_CHANGED": "TRUE"},
    {"PYTHON_CHANGED": "true"},
    {"PYTHON_CHANGED": "true", "DOCS_CHANGED": "true", "CHANGED_FILES": ""},
    {"PYTHON_CHANGED": "true", "DOCS_CHANGED": "true", "CHANGED_FILES": "many"},
])
def test_the_route_step_fails_without_valid_filter_outputs(tmp_path: Path, env: dict[str, str]) -> None:
    """Precondition: a pull request whose filter outputs or changed-file count are missing or
    malformed. Action: run the route script under bash. Postcondition: status 1 and no route
    written, so the gate cannot read a route that was never decided."""
    code, outputs = _route(tmp_path, **{"EVENT_NAME": "pull_request", "CHANGED_FILES": "17", **env})
    assert code == 1
    assert outputs == {}


def test_real_diff_cover_output_yields_an_annotation_for_the_unexecuted_changed_line(tmp_path: Path) -> None:
    """Precondition: a git repository with a nested package whose second commit adds a line
    that is never executed. Action: run coverage.py and diff-cover on it, then build the
    annotations from their JSON. Postcondition: a warning at the repository-relative path and
    line of the unexecuted statement, and a changed-line percentage that would fail a
    threshold while the bridge stays advisory."""
    spec = importlib.util.spec_from_file_location(_ANNOTATIONS.stem, _ANNOTATIONS)
    assert spec and spec.loader
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    root = tmp_path / "repo"
    package = root / "devcapsule-src" / "devcapsule" / "nested"
    package.mkdir(parents=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_COMMITTER_NAME": "Test",
           "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_EMAIL": "test@example.invalid"}

    def run(*arguments: str, cwd: Path = root) -> subprocess.CompletedProcess[str]:
        return subprocess.run(arguments, cwd=cwd, env=env, text=True, capture_output=True, check=True)

    run("git", "init", "-b", "main")
    (package.parent / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    source = package / "sample.py"
    source.write_text("x = 0\n", encoding="utf-8")
    run("git", "add", ".")
    run("git", "commit", "-m", "base")
    base = run("git", "rev-parse", "HEAD").stdout.strip()
    source.write_text('x = 0\nif x:\n    print("not run")\n', encoding="utf-8")
    run("git", "add", ".")
    run("git", "commit", "-m", "change")
    working = root / "devcapsule-src"
    run(sys.executable, "-m", "coverage", "run", "--branch", "--source=devcapsule", "devcapsule/nested/sample.py", cwd=working)
    run(sys.executable, "-m", "coverage", "xml", cwd=working)
    run(sys.executable, "-m", "diff_cover.diff_cover_tool", "coverage.xml",
        f"--compare-branch={base}", "--format=json:diff-cover.json,markdown:diff-cover.md", cwd=working)
    report = json.loads((working / "diff-cover.json").read_text(encoding="utf-8"))
    warnings, _ = bridge.build_annotations(report)
    assert any("file=devcapsule-src/devcapsule/nested/sample.py,line=3,endLine=3" in warning for warning in warnings)
    assert report["total_percent_covered"] < 85


def _run_git(env: dict[str, str], *arguments: str, cwd: Path) -> str:
    """Run git with the isolated test environment and return trimmed stdout."""
    return subprocess.run(arguments, cwd=cwd, env=env, text=True, capture_output=True, check=True).stdout.strip()


def _create_raw_website_gitlink_fixtures(
    tmp_path: Path,
) -> tuple[dict[str, str], Path, Path, Path, Path, str, str]:
    """Create local git origins modeling a raw ``website`` gitlink with a nested SSH submodule."""
    gitconfig = tmp_path / "gitconfig"
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }

    nested_origin = tmp_path / "nested.git"
    nested_origin.mkdir()
    _run_git(env, "git", "init", "-q", "-b", "main", cwd=nested_origin)
    (nested_origin / "nested.txt").write_text("nested\n", encoding="utf-8")
    _run_git(env, "git", "add", "nested.txt", cwd=nested_origin)
    _run_git(env, "git", "commit", "-q", "-m", "nested", cwd=nested_origin)
    nested_sha = _run_git(env, "git", "rev-parse", "HEAD", cwd=nested_origin)

    website_origin = tmp_path / "website.git"
    website_origin.mkdir()
    _run_git(env, "git", "init", "-q", "-b", "main", cwd=website_origin)
    _run_git(env, "git", "config", "uploadpack.allowReachableSHA1InWant", "true", cwd=website_origin)
    (website_origin / "package.json").write_text('{"name":"devcapsule-website"}\n', encoding="utf-8")
    (website_origin / ".gitmodules").write_text(
        '[submodule "sub"]\n\tpath = sub\n\turl = git@github.com:mycodespace-ai/nested.git\n',
        encoding="utf-8",
    )
    _run_git(env, "git", "update-index", "--add", "--cacheinfo", f"160000,{nested_sha},sub", cwd=website_origin)
    _run_git(env, "git", "add", "package.json", ".gitmodules", cwd=website_origin)
    _run_git(env, "git", "commit", "-q", "-m", "pinned website", cwd=website_origin)
    pinned_website_sha = _run_git(env, "git", "rev-parse", "HEAD", cwd=website_origin)
    (website_origin / "package.json").write_text('{"name":"newer-unpinned"}\n', encoding="utf-8")
    _run_git(env, "git", "add", "package.json", cwd=website_origin)
    _run_git(env, "git", "commit", "-q", "-m", "advance main past pin", cwd=website_origin)

    parent_origin = tmp_path / "parent.git"
    parent_origin.mkdir()
    _run_git(env, "git", "init", "-q", "-b", "main", cwd=parent_origin)
    _run_git(env, "git", "config", "uploadpack.allowReachableSHA1InWant", "true", cwd=parent_origin)
    (parent_origin / ".gitmodules").write_text("", encoding="utf-8")
    (parent_origin / "README.md").write_text("# DevCapsule\n", encoding="utf-8")
    _run_git(env, "git", "update-index", "--add", "--cacheinfo", f"160000,{pinned_website_sha},website", cwd=parent_origin)
    _run_git(env, "git", "add", ".gitmodules", "README.md", cwd=parent_origin)
    _run_git(env, "git", "commit", "-q", "-m", "raw website gitlink", cwd=parent_origin)
    parent_sha = _run_git(env, "git", "rev-parse", "HEAD", cwd=parent_origin)
    _run_git(env, "git", "branch", "docs-0.3.0", cwd=parent_origin)

    _run_git(env, "git", "config", "--file", str(gitconfig), "protocol.file.allow", "always", cwd=tmp_path)
    for prefix in ("https://github.com/mycodespace-ai/", "git@github.com:mycodespace-ai/"):
        _run_git(env, "git", "config", "--file", str(gitconfig), "--add", f"url.{website_origin}.insteadOf", f"{prefix}devcapsule-website.git", cwd=tmp_path)
        _run_git(env, "git", "config", "--file", str(gitconfig), "--add", f"url.{nested_origin}.insteadOf", f"{prefix}nested.git", cwd=tmp_path)

    return env, gitconfig, parent_origin, website_origin, nested_origin, parent_sha, pinned_website_sha


@pytest.mark.parametrize(("workflow_path", "job"), [
    (_WORKFLOW, "docs-build"),
    (_WEBSITE_WORKFLOW, "build"),
    (_WEBSITE_WORKFLOW, "candidate"),
])
def test_website_workflows_instantiate_a_raw_website_gitlink_recursively(
    tmp_path: Path, workflow_path: Path, job: str,
) -> None:
    """Precondition: a parent checkout whose ``website`` entry is a raw gitlink with no
    ``.gitmodules`` mapping, pointing at a non-tip commit of ``devcapsule-website`` that itself
    declares a nested submodule over SSH. Action: run the job's ``fetch-website`` step under
    bash. Postcondition: ``website`` is checked out at the exact gitlink commit, its nested
    submodule is materialized recursively, and both checkouts report clean ``git status``."""
    env, _, parent_origin, _, _, _, pinned_website_sha = _create_raw_website_gitlink_fixtures(tmp_path)

    checkout = tmp_path / "checkout"
    _run_git(env, "git", "clone", "-q", str(parent_origin), str(checkout), cwd=tmp_path)

    step = _job_step(workflow_path, job, "fetch-website")
    subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]],
        cwd=checkout,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert _run_git(env, "git", "rev-parse", "HEAD", cwd=checkout / "website") == pinned_website_sha
    assert (checkout / "website" / "sub" / "nested.txt").read_text(encoding="utf-8") == "nested\n"
    assert _run_git(env, "git", "status", "--porcelain", "--untracked-files=normal", cwd=checkout) == ""
    assert _run_git(env, "git", "status", "--porcelain", "--untracked-files=normal", cwd=checkout / "website") == ""


def test_website_candidate_checks_out_raw_gitlink_without_persisting_credentials(tmp_path: Path) -> None:
    """Precondition: a ``candidate`` job checkout step for a repository whose ``website`` entry
    is a raw gitlink with an empty ``.gitmodules``. Action: run ``checkout-candidate`` then
    ``fetch-website`` in an empty workspace under bash. Postcondition: the parent commit and pinned
    website commit materialize cleanly without invoking ``actions/checkout`` credential cleanup on
    unmapped gitlinks, and local git config holds no authorization header."""
    workflow = yaml.safe_load(_WEBSITE_WORKFLOW.read_text(encoding="utf-8"))
    candidate_steps = workflow["jobs"]["candidate"]["steps"]
    assert not any(
        str(step.get("uses", "")).startswith("actions/checkout")
        and step.get("with", {}).get("persist-credentials") is False
        for step in candidate_steps
    )

    env, _, parent_origin, _, _, parent_sha, pinned_website_sha = _create_raw_website_gitlink_fixtures(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    checkout_step = _job_step(_WEBSITE_WORKFLOW, "candidate", "checkout-candidate")
    subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", checkout_step["run"]],
        cwd=workspace,
        env={**env, "REPOSITORY_URL": str(parent_origin), "TARGET_SHA": parent_sha},
        text=True,
        capture_output=True,
        check=True,
    )

    fetch_step = _job_step(_WEBSITE_WORKFLOW, "candidate", "fetch-website")
    subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", fetch_step["run"]],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert _run_git(env, "git", "rev-parse", "HEAD", cwd=workspace) == parent_sha
    assert _run_git(env, "git", "rev-parse", "HEAD:website", cwd=workspace) == pinned_website_sha
    assert _run_git(env, "git", "rev-parse", "HEAD", cwd=workspace / "website") == pinned_website_sha
    assert (workspace / "website" / "sub" / "nested.txt").read_text(encoding="utf-8") == "nested\n"
    assert "extraheader" not in _run_git(env, "git", "config", "--local", "--list", cwd=workspace).lower()
    assert _run_git(env, "git", "status", "--porcelain", "--untracked-files=normal", cwd=workspace) == ""
