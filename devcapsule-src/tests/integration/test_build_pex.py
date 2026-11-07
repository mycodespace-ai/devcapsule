"""The build script on a clean revision: ``scripts/build-pex.sh`` stamps the version the tag derives.

The release backend relies on this rule: a tagged build reports the tag's
version, a build without a tag reports the authored version with a local
marker, and either embeds the source identity of the revision it was built
from. The fixture builds from a repository it constructs, so the test owns
every input the script reads: the sources, the metadata, the compatibility
policy the build embeds, the tag and the advertised remote.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

SOURCE_PROJECT = Path(__file__).resolve().parents[2]
FIXTURE_REPOSITORY_URL = "https://github.com/example/devcapsule-unpublished-test"


@dataclass(frozen=True)
class CleanBuild:
    """A build of a constructed clean revision and what the fixture knows about it."""

    release: str | None
    repository: Path
    project: Path
    revision: str
    output: Path
    completed: subprocess.CompletedProcess[str]

    @property
    def expected_version(self) -> str:
        """The package version the build must report: the tag's, or the authored one."""

        if self.release:
            return self.release[1:].replace("-rc", "rc")
        return tomllib.loads((self.project / "pyproject.toml").read_text())["project"]["version"]

    @property
    def expected_mnemonic(self) -> str:
        """The build mnemonic the build must report: the tag, or the local form."""

        if self.release:
            return self.release
        platform = os.environ.get("DEVCAPSULE_SCIE_PLATFORM", "linux-x86_64")
        return f"v{self.expected_version}-local-{platform}"


def _run(*command: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), check=True, text=True, capture_output=True, **kwargs)  # type: ignore[call-overload]


@pytest.fixture(scope="module", params=[None, "v98.7.6", "v98.7.6-rc0"], ids=["untagged", "final", "candidate"])
def clean_build(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> CleanBuild:
    """Build the executable from a fresh repository holding this tree's sources, with or without a tag.

    The repository is committed once and given a remote; for a release the
    tag is pushed to a local bare remote standing in for the advertised
    public revision, with enough extra refs to expose an early-exiting grep
    under pipefail. The version in the copied ``pyproject.toml`` deliberately
    differs from the tags.
    """

    release: str | None = request.param
    tmp_path = tmp_path_factory.mktemp("clean-build")
    repository = tmp_path / "repository"
    project = repository / "devcapsule-src"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    shutil.copytree(SOURCE_PROJECT / "devcapsule", project / "devcapsule",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("pyproject.toml", "README.md", "requirements.txt"):
        shutil.copy2(SOURCE_PROJECT / name, project / name)
    for name in ("build-pex.sh", "bump-version.py"):
        shutil.copy2(SOURCE_PROJECT / "scripts" / name, scripts / name)
    # The build embeds the compatibility snapshot from the authored policy
    # beside devcapsule-src, and refuses to build without it.
    policy = repository / "component-status" / "policy-v1.json"
    policy.parent.mkdir()
    shutil.copy2(SOURCE_PROJECT.parent / "component-status" / "policy-v1.json", policy)

    git = ("git", "-C", str(repository))
    _run("git", "init", "-q", str(repository))
    _run(*git, "config", "user.name", "DevCapsule Tests")
    _run(*git, "config", "user.email", "tests@devcapsule.invalid")
    _run(*git, "add", ".")
    _run(*git, "commit", "-q", "-m", "Test unpublished build")
    _run(*git, "remote", "add", "origin", f"{FIXTURE_REPOSITORY_URL}.git")
    revision = _run(*git, "rev-parse", "HEAD").stdout.strip()

    build_arguments = ["--allow-unpublished-revision"]
    if release:
        remote = tmp_path / "remote.git"
        _run("git", "init", "--bare", "-q", str(remote))
        _run(*git, "config", f"url.{remote}.insteadOf", f"{FIXTURE_REPOSITORY_URL}.git")
        _run(*git, "tag", "-a", "-m", "Candidate", release)
        _run(*git, "push", "origin", release)
        _run("git", "--git-dir", str(remote), "update-ref", "--stdin",
             input="".join(f"create refs/heads/fixture-{index} {revision}\n" for index in range(500)))
        build_arguments = ["--release-mnemonic", release, "--source-repository", FIXTURE_REPOSITORY_URL]

    environment = {name: value for name, value in os.environ.items()
                   if name not in {"DEVCAPSULE_SOURCE_REPOSITORY", "DEVCAPSULE_SOURCE_REVISION"}}
    environment["PYTHON"] = sys.executable
    completed = subprocess.run([str(scripts / "build-pex.sh"), *build_arguments], check=False, text=True,
                               capture_output=True, env=environment, cwd=project)
    return CleanBuild(release, repository, project, revision, project / "dist" / "devcapsule.pex", completed)


def test_a_clean_revision_builds_a_self_contained_executable(clean_build: CleanBuild) -> None:
    """The build exits 0 and writes dist/devcapsule.pex, an ELF scie that is also a zip."""

    assert clean_build.completed.returncode == 0, clean_build.completed.stderr
    assert clean_build.output.read_bytes().startswith(b"\x7fELF")
    assert zipfile.is_zipfile(clean_build.output)


def test_the_executable_embeds_the_pinned_python_and_an_executable_pex(clean_build: CleanBuild) -> None:
    """SCIE=inspect lists the pinned stripped CPython 3.12 distribution and marks the pex executable."""

    assert clean_build.completed.returncode == 0, clean_build.completed.stderr
    inspected = _run(str(clean_build.output), env={**os.environ, "SCIE": "inspect"})
    lift = json.loads(inspected.stdout)["scie"]["lift"]
    embedded = {item.get("key"): item for item in lift["files"]}
    assert embedded["python-distribution"]["name"].startswith("cpython-3.12.14+20260814-")
    assert embedded["python-distribution"]["name"].endswith("-install_only_stripped.tar.gz")
    assert embedded["pex"]["executable"] is True


def test_version_reports_the_tag_derived_version_and_the_source_identity(clean_build: CleanBuild) -> None:
    """``version --json`` names the version and mnemonic the tag derives and the revision built from."""

    assert clean_build.completed.returncode == 0, clean_build.completed.stderr
    value = json.loads(_run(str(clean_build.output), "version", "--json").stdout)
    assert value["version"] == clean_build.expected_version
    assert value["build_mnemonic"] == clean_build.expected_mnemonic
    assert value["source_revision"] == clean_build.revision
    assert value["source_repository"] == FIXTURE_REPOSITORY_URL
    assert value["source_url"].endswith(f"/commit/{clean_build.revision}")


def test_a_tagged_build_installs_the_tag_version_and_leaves_the_tree_clean(clean_build: CleanBuild, tmp_path: Path) -> None:
    """The embedded wheel's metadata carries the tag's version, stamped outside the source tree."""

    if not clean_build.release:
        pytest.skip("an untagged build keeps the authored version; the stamp is a tagged build's")
    assert clean_build.completed.returncode == 0, clean_build.completed.stderr
    # From an empty directory: PEX_INTERPRETER keeps an empty sys.path entry,
    # and from the source tree importlib.metadata would find the editable
    # install's egg-info before the embedded wheel.
    installed = _run(str(clean_build.output), "-c",
                     "from importlib.metadata import version; print(version('devcapsule'))",
                     env={**os.environ, "PEX_INTERPRETER": "1"}, cwd=tmp_path).stdout.strip()
    assert installed == clean_build.expected_version
    assert _run("git", "-C", str(clean_build.repository), "diff", "--exit-code").stdout == ""
