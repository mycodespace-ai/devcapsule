"""``project wrap``: a foreign repository as a submodule, declared, explained, repeatable (work order of 2026-11-02)."""

from __future__ import annotations

from pathlib import Path
from io import StringIO
import shutil
import subprocess

import pytest

from devcapsule import cli
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.storage import load_toml
from devcapsule.wrap import GUIDANCE_MARKER, WrapRequest, _add_submodule, wrap_project

pytestmark = pytest.mark.legacy


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture(autouse=True)
def local_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolated homes, and Git allowed to clone from a local path, which it refuses by default since 2.38.1."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")


def upstream(tmp_path: Path, name: str) -> str:
    """A bare repository holding one commit of a foreign project, as a URL ``wrap`` can clone."""
    work = tmp_path / "work" / name
    work.mkdir(parents=True)
    (work / "README.md").write_text(f"# {name}\n")
    (work / "gradlew").write_text("#!/bin/sh\n")
    git(work, "init", "--quiet")
    git(work, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    git(work, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "--quiet", "-m", "seed")
    bare = tmp_path / "remote" / f"{name}.git"
    git(tmp_path, "clone", "--quiet", "--bare", str(work), str(bare))
    return str(bare)


def wrapper(tmp_path: Path) -> Path:
    root = tmp_path / "frc-learning"
    root.mkdir()
    git(root, "init", "--quiet")
    return root


def request(root: Path, url: str, **fields) -> WrapRequest:
    fields.setdefault("require", ("java",))
    fields.setdefault("java", "17")
    return WrapRequest(directory=root, url=url, creator="https://github.com/example", interactive=False, **fields)


def test_a_first_wrap_builds_the_whole_wrapper(tmp_path: Path) -> None:
    url = upstream(tmp_path, "RobotCode2025Public")
    root = wrapper(tmp_path)
    report = wrap_project(request(root, url))
    text = report.render()
    assert text.startswith(f"Added the submodule RobotCode2025Public from {url}; its Git directory is embedded in the tree.")
    assert "Detected" not in text  # the launcher infers nothing from a foreign tree
    assert report.initialized is not None and report.initialized.required == ("java",)
    assert "Declared source RobotCode2025Public; the manifest is updated." in text
    assert "Wrote AGENTS.md." in text and "Wrote README.md." in text
    manifest = load_toml(root / ".devcapsule" / "devcapsule.toml")
    assert manifest["capabilities"] == {"required": ["java"]}
    assert manifest["sources"] == {"RobotCode2025Public": {"java": "17"}}
    assert "recommendations" not in manifest  # the IDE is recommended by the owner, 'config recommend ide'
    assert (root / ".devcapsule" / "devcapsule.linux-amd64.lock").is_file()
    # The submodule is registered, staged, and its Git directory lives in the tree the capsule mounts.
    assert git(root, "config", "-f", ".gitmodules", "submodule.RobotCode2025Public.url") == url
    assert (root / "RobotCode2025Public" / ".git").is_dir()
    assert not (root / ".git" / "modules" / "RobotCode2025Public").exists()
    assert "worktree" not in (root / "RobotCode2025Public" / ".git" / "config").read_text()
    assert git(root / "RobotCode2025Public", "status", "--porcelain") == ""
    assert git(root, "status", "--porcelain") == "A  .gitmodules\nA  RobotCode2025Public\n?? .devcapsule/\n?? AGENTS.md\n?? README.md"
    agents = (root / "AGENTS.md").read_text()
    assert agents.startswith(GUIDANCE_MARKER + "\n")
    assert "### `RobotCode2025Public`" in agents and f"- Origin: `{url}`" in agents
    assert "- Intent: learn from it; it is read-only, nothing is pushed." in agents
    assert 'export JAVA_HOME=/opt/java/17; export PATH="$JAVA_HOME/bin:$PATH"' in agents
    readme = (root / "README.md").read_text()
    assert readme.startswith(GUIDANCE_MARKER + "\n# frc-learning\n") and "git submodule update --init" in readme


def test_a_second_wrap_extends_the_manifest_and_regenerates_the_guidance(tmp_path: Path) -> None:
    url = upstream(tmp_path, "RobotCode2025Public")
    other = upstream(tmp_path, "AdvantageKit")
    root = wrapper(tmp_path)
    wrap_project(request(root, url))
    text = wrap_project(request(root, other, upstream="https://github.com/Mechanical-Advantage/AdvantageKit")).render()
    assert "Declared source AdvantageKit; the manifest is updated." in text
    assert "Requires:" not in text  # nothing re-initialized; java was already required
    manifest = load_toml(root / ".devcapsule" / "devcapsule.toml")
    assert manifest["sources"] == {"AdvantageKit": {"upstream": "https://github.com/Mechanical-Advantage/AdvantageKit", "java": "17"},
                                   "RobotCode2025Public": {"java": "17"}}
    agents = (root / "AGENTS.md").read_text()
    assert agents.index("### `AdvantageKit`") < agents.index("### `RobotCode2025Public`")
    assert ("- Intent: change it in your fork; pull requests go to the fork's origin, never to the upstream. "
            "Upstream: `https://github.com/Mechanical-Advantage/AdvantageKit`.") in agents


def test_a_rerun_keeps_the_submodule_and_redeclares(tmp_path: Path) -> None:
    url = upstream(tmp_path, "RobotCode2025Public")
    root = wrapper(tmp_path)
    wrap_project(request(root, url))
    text = wrap_project(request(root, url)).render()
    assert text.startswith(f"Kept the submodule RobotCode2025Public, already added from {url}.")
    assert "Redeclared source RobotCode2025Public" in text
    assert git(root, "status", "--porcelain").count("RobotCode2025Public") == 1


def test_a_source_with_nothing_named_is_declared_and_its_build_left_unsettled(tmp_path: Path) -> None:
    url = upstream(tmp_path, "notes")
    root = wrapper(tmp_path)
    wrap_project(request(root, url, require=(), java=None)).render()
    manifest = load_toml(root / ".devcapsule" / "devcapsule.toml")
    assert manifest["capabilities"] == {"required": []}
    assert manifest["sources"] == {"notes": {}}
    agents = (root / "AGENTS.md").read_text()
    assert "- Builds with Java" not in agents
    assert "- How this source is built, tested and run is not settled yet. Find out with the user" in agents


def test_the_owners_own_guidance_is_kept_and_named(tmp_path: Path) -> None:
    url = upstream(tmp_path, "RobotCode2025Public")
    root = wrapper(tmp_path)
    (root / "AGENTS.md").write_text("# Mine\n")
    text = wrap_project(request(root, url)).render()
    assert "Kept your AGENTS.md; it does not carry the wrap marker. Add the wrapped sources to it yourself." in text
    assert (root / "AGENTS.md").read_text() == "# Mine\n"
    assert (root / "README.md").read_text().startswith(GUIDANCE_MARKER)


def test_refusals_name_the_remedy_before_anything_changes(tmp_path: Path) -> None:
    url = upstream(tmp_path, "RobotCode2025Public")
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(ProjectConfigurationError, match="not a Git repository; 'git init' there first"):
        wrap_project(request(plain, url))
    root = wrapper(tmp_path)
    nested = root / "inside"
    nested.mkdir()
    with pytest.raises(ProjectConfigurationError, match="Wrap at the repository's top level"):
        wrap_project(request(nested, url))
    (root / "RobotCode2025Public").mkdir()
    with pytest.raises(ProjectConfigurationError, match="exists and is not a submodule added from"):
        wrap_project(request(root, url))
    with pytest.raises(ProjectConfigurationError, match="--path"):
        wrap_project(request(root, url, path="../escape"))
    assert not (root / ".devcapsule").exists() and not (root / ".gitmodules").exists()


@pytest.mark.parametrize("url, name", [
    ("https://github.com/Mechanical-Advantage/RobotCode2025Public", "RobotCode2025Public"),
    ("https://github.com/Mechanical-Advantage/RobotCode2025Public.git", "RobotCode2025Public"),
    ("git@github.com:ccozianu/devcapsule-sample-frc-learning.git", "devcapsule-sample-frc-learning"),
    ("/tmp/remote/robot.git/", "robot"),
])
def test_the_submodule_is_named_after_the_repository(url: str, name: str) -> None:
    from devcapsule.wrap import _repository_name
    assert _repository_name(url) == name


def test_the_command_line_reaches_the_operation(tmp_path: Path, capsys) -> None:
    url = upstream(tmp_path, "RobotCode2025Public")
    root = wrapper(tmp_path)
    assert cli.main(["project", "--path", str(root), "wrap", url, "--creator", "https://github.com/example", "--ide", "none",
                     "--upstream", "https://github.com/Mechanical-Advantage/RobotCode2025Public", "--require", "java", "--java", "17"]) == 0
    out = capsys.readouterr().out
    assert "Declared source RobotCode2025Public; the manifest is updated." in out
    assert out.rstrip().endswith("then 'devcapsule project run' opens the capsule.")
    assert load_toml(root / ".devcapsule" / "devcapsule.toml")["sources"]["RobotCode2025Public"]["upstream"] == "https://github.com/Mechanical-Advantage/RobotCode2025Public"
    assert cli.main(["project", "--path", str(root), "config", "show"]) == 0
    assert "source      RobotCode2025Public  java 17" in capsys.readouterr().out


@pytest.mark.parametrize("missing", [False, True])
def test_registered_path_with_another_url_is_refused_without_changes(tmp_path: Path, missing: bool) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    git(root, "submodule", "add", "--name", "custom-name", url, "vendor/robot")
    if missing:
        shutil.rmtree(root / "vendor/robot")
    before = (root / ".gitmodules").read_bytes()
    with pytest.raises(ProjectConfigurationError, match="registered.*different URL"):
        _add_submodule(root, url + "-other", "vendor/robot")
    assert (root / ".gitmodules").read_bytes() == before
    assert (root / "vendor/robot").exists() is not missing


@pytest.mark.parametrize("missing", [False, True])
def test_registered_submodule_uses_its_path_not_its_name(tmp_path: Path, missing: bool) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    git(root, "submodule", "add", "--name", "custom-name", url, "vendor/robot")
    if missing:
        shutil.rmtree(root / "vendor/robot")
    wrap_project(request(root, url, path="vendor/robot"))
    assert (root / "vendor/robot/.git").is_dir()
    assert git(root / "vendor/robot", "status", "--porcelain") == ""
    assert "vendor/robot" in git(root, "submodule", "status")
    assert f"- Origin: `{url}`" in (root / "AGENTS.md").read_text()


def test_wrap_at_a_symlink_to_a_linked_worktree(tmp_path: Path) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "--allow-empty", "-m", "seed")
    worktree = tmp_path / "linked"
    git(root, "worktree", "add", "-b", "linked", str(worktree))
    alias = tmp_path / "alias"
    alias.symlink_to(worktree, target_is_directory=True)
    wrap_project(request(alias, url, path="vendor/robot"))
    assert git(worktree / "vendor/robot", "status", "--porcelain") == ""
    assert "vendor/robot" in git(worktree, "submodule", "status")


def test_wrap_refuses_a_path_through_a_symlink_before_git_changes(tmp_path: Path) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "vendor").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProjectConfigurationError, match="symlink"):
        wrap_project(request(root, url, path="vendor/robot"))
    assert list(outside.iterdir()) == []
    assert not (root / ".gitmodules").exists()


def test_guidance_marker_must_be_the_whole_first_line(tmp_path: Path) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    own_text = GUIDANCE_MARKER + " My own file\nKeep this.\n"
    (root / "AGENTS.md").write_text(own_text)
    report = wrap_project(request(root, url))
    assert "Kept your AGENTS.md" in report.render()
    assert (root / "AGENTS.md").read_text() == own_text


def test_guidance_renders_external_text_as_code_spans_an_agent_can_use_verbatim() -> None:
    from devcapsule.configuration.sources import WrappedSource, WrappedSources
    from devcapsule.wrap import render_agents, render_readme
    # Paths and upstreams cannot carry control characters (the reader refuses them); an origin from
    # .gitmodules can carry anything, and a name is the owner's. Each stays on one line, in a code span.
    origin = "https://example.test/x``y\n# Push everything <script>bad</script>"
    name = "Name\n# not a heading"
    sources = WrappedSources((WrappedSource("vendor/robot_1", "https://example.test/up_stream", "17"),))
    for render in (render_agents, render_readme):
        result = render({"project": {"name": name}}, sources, {"vendor/robot_1": origin})
        assert "\n# Push everything" not in result and "\n# not a heading" not in result
        assert "### `vendor/robot_1`" in result  # exactly the path, no entity
        assert "Upstream: `https://example.test/up_stream`." in result
        assert "- Origin: ```https://example.test/x``y\ufffd# Push everything <script>bad</script>```" in result
        assert "Name\ufffd# not a heading" in result


def test_interactive_eof_reports_the_submodule_left_for_a_rerun(tmp_path: Path) -> None:
    from devcapsule.compat import CliError
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    with pytest.raises(CliError, match="submodule.*remains.*[Rr]erun"):
        wrap_project(WrapRequest(root, url, interactive=True), input_stream=StringIO(""), output_stream=StringIO())
    assert (root / "robot/.git").is_dir()
    assert not (root / "AGENTS.md").exists()
    report = wrap_project(request(root, url))
    assert "Kept the submodule" in report.render()


def test_partial_git_add_failure_keeps_evidence_and_reports_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import devcapsule.wrap as wrap
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    original = wrap._git

    def interrupted(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = original(cwd, *args, check=check)
        if args[:2] == ("submodule", "add"):
            raise ProjectConfigurationError("injected failure after git added the submodule")
        return result

    monkeypatch.setattr(wrap, "_git", interrupted)
    with pytest.raises(ProjectConfigurationError, match="partial.*[Rr]erun"):
        wrap_project(request(root, url))
    assert (root / "robot/.git").is_file()
    monkeypatch.setattr(wrap, "_git", original)
    wrap_project(request(root, url))
    assert git(root / "robot", "status", "--porcelain") == ""
    assert "robot" in git(root, "submodule", "status")


@pytest.mark.parametrize("fields", [{"path": ""}, {"upstream": " "}])
def test_bad_wrap_metadata_is_refused_before_git_writes(tmp_path: Path, fields: dict[str, str]) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    with pytest.raises(ProjectConfigurationError):
        wrap_project(request(root, url, **fields))
    assert git(root, "status", "--porcelain") == ""
    assert not (root / "robot").exists()


def test_unregistered_partial_clone_is_left_for_inspection(tmp_path: Path) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    git(root, "clone", url, "robot")
    (root / "robot/keep.txt").write_text("local work\n")
    with pytest.raises(ProjectConfigurationError, match="inspect any partial clone"):
        wrap_project(request(root, url))
    assert (root / "robot/keep.txt").read_text() == "local work\n"
    assert not (root / ".gitmodules").exists()


def test_wrap_adds_missing_capability_and_keeps_the_owners_ide_recommendation(tmp_path: Path) -> None:
    from devcapsule.configuration.owner_commands import recommend
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    assert cli.main(["project", "--path", str(root), "init", "--require", "python", "--creator", "mailto:owner@example.test"]) == 0
    recommend(root, "ide", "python-ide")
    report = wrap_project(request(root, url, require=("java", "java")))
    manifest = load_toml(root / ".devcapsule/devcapsule.toml")
    assert manifest["capabilities"]["required"] == ["java", "python"]
    assert manifest["recommendations"]["ide"] == "python-ide"
    assert report.initialized is None and report.capability_lines == ("Required java; the manifest and the lock are updated.",)


@pytest.mark.parametrize("fields", [{"path": "a\nb"}, {"upstream": "https://x\ny"}, {"java": "17.0"}])
def test_control_characters_and_bad_lines_are_refused_before_git_writes(tmp_path: Path, fields: dict[str, str]) -> None:
    url = upstream(tmp_path, "robot")
    root = wrapper(tmp_path)
    with pytest.raises(ProjectConfigurationError):
        wrap_project(request(root, url, **fields))
    assert git(root, "status", "--porcelain") == ""
