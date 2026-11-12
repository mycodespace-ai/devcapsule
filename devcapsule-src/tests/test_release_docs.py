from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import subprocess

import pytest
import yaml

pytestmark = pytest.mark.legacy

SPEC = importlib.util.spec_from_file_location("release_docs", Path(__file__).parents[1] / "scripts/release-docs.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

# The mainline manifest when C20 was ordered. Two deprecated entries are
# intentional historical input; promotion demotes both in one pass.
MANIFEST = {
    "contract": 1,
    "current": "0.2.15",
    "notice": "We publish every release.\nPlease use the current release.\n",
    "versions": [
        {"version": "devel", "source": "main", "status": "development"},
        {"version": "0.2.15", "source": "docs-0.2.15", "status": "supported"},
        {"version": "0.2.14", "source": "v0.2.14", "status": "deprecated", "legacy": True,
         "note": "Follow the current guide."},
        {"version": "0.2.12", "source": "a" * 40, "source-version": "0.2.14.dev0",
         "status": "deprecated", "legacy": True, "note": "Guides written after the tag."},
    ],
}


def write_manifest(root, data):
    (root / "docs/versions.yaml").write_text(yaml.safe_dump(data, sort_keys=False))


def write_notes(root, text="# Release 0.3.0\n\nDocumentation now follows the release.\n"):
    path = root / "engineering-docs/releases/v0.3.0/notes.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "docs").mkdir()
    write_manifest(tmp_path, MANIFEST)
    (tmp_path / "devcapsule-src").mkdir()
    (tmp_path / "devcapsule-src/pyproject.toml").write_text('[project]\nversion = "0.3.0"\n')
    return tmp_path


def invoke(root, command, *args):
    return MODULE.main([command, *args, "--root", str(root)])


@pytest.mark.parametrize("hold", [False, True])
def test_promote_main_lifecycle_and_hold_refusal(checkout, capsys, hold):
    before = (checkout / "docs/versions.yaml").read_bytes()
    if hold:
        assert invoke(checkout, "promote", "0.3.0", "--hold", "0.2.15") == 1
        assert "two supported" in capsys.readouterr().err
        assert (checkout / "docs/versions.yaml").read_bytes() == before
        return
    assert invoke(checkout, "promote", "0.3.0") == 0
    output = capsys.readouterr().out
    for move in ("current: 0.2.15 -> 0.3.0", "0.2.15: supported -> deprecated",
                 "0.2.14: deprecated -> unsupported", "0.2.12: deprecated -> unsupported"):
        assert move in output
    expected = copy.deepcopy(MANIFEST)
    expected["current"] = "0.3.0"
    entries = expected["versions"]
    entries[0]["source-version"] = "0.3.0"
    entries[1]["status"] = "deprecated"
    entries[2]["status"] = entries[3]["status"] = "unsupported"
    entries.insert(1, {"version": "0.3.0", "source": "docs-0.3.0", "status": "supported"})
    result = (checkout / "docs/versions.yaml").read_text()
    assert yaml.safe_load(result) == expected
    assert "notice: >\n" in result
    assert result.startswith(MODULE.HEADER)
    assert invoke(checkout, "promote", "0.3.0") == 1
    assert "already listed" in capsys.readouterr().err
    assert (checkout / "docs/versions.yaml").read_text() == result


def test_promote_holds_multiple_deprecated_versions(checkout):
    assert invoke(checkout, "promote", "0.3.0", "--hold", "0.2.14", "--hold", "0.2.12") == 0
    entries = MODULE.read_manifest(checkout)["versions"]
    assert [entry["status"] for entry in entries] == [
        "development", "supported", "deprecated", "deprecated", "deprecated"]


def test_promote_handles_reordered_entries_and_no_supported_version(checkout):
    data = copy.deepcopy(MANIFEST)
    data["versions"][1]["status"] = "unsupported"
    data["versions"].append(data["versions"].pop(0))
    write_manifest(checkout, data)
    MODULE.promote(checkout, "0.3.0", [])
    entries = MODULE.read_manifest(checkout)["versions"]
    assert [entry["version"] for entry in entries] == ["0.2.15", "0.2.14", "0.2.12", "devel", "0.3.0"]
    assert entries[0]["status"] == "unsupported"
    assert all(entry["status"] == "unsupported" for entry in entries[1:3])


@pytest.mark.parametrize("case,message", [
    ("wrong_branch", "pyproject.toml must declare"), ("unknown_hold", "Unknown --hold"),
    ("two_supported", "more than one supported"), ("already_listed", "already listed"),
])
def test_promote_refuses_without_write(checkout, capsys, case, message):
    data = copy.deepcopy(MANIFEST)
    args = []
    if case == "wrong_branch":
        (checkout / "devcapsule-src/pyproject.toml").write_text('[project]\nversion = "0.3.1.dev0"\n')
    elif case == "unknown_hold":
        args = ["--hold", "0.1.0"]
    elif case == "two_supported":
        data["versions"][2]["status"] = "supported"
    else:
        data["versions"].append({"version": "0.3.0", "source": "docs-0.3.0", "status": "unsupported"})
    write_manifest(checkout, data)
    before = (checkout / "docs/versions.yaml").read_bytes()
    assert invoke(checkout, "promote", "0.3.0", *args) == 1
    assert message in capsys.readouterr().err
    assert (checkout / "docs/versions.yaml").read_bytes() == before


@pytest.mark.parametrize("command", ["promote", "check", "published"])
@pytest.mark.parametrize("bad,message", [
    ("[", "while parsing"), ("[]", "expected a mapping"),
    ("contract: 2", "contract must be 1"), ("contract: true", "contract must be 1"),
    ("contract: 1\ncontract: 1", "duplicate field"),
    ("contract: 1\ncurrent: 3", "current must be nonempty text"),
])
def test_malformed_yaml_refused_by_manifest_commands(checkout, monkeypatch, capsys, command, bad, message):
    path = checkout / "docs/versions.yaml"
    path.write_text(bad)
    def unexpected_release(tag):
        pytest.fail(f"release lookup on malformed input: {tag}")
    monkeypatch.setattr(MODULE, "github_release", unexpected_release)
    assert invoke(checkout, command, *([] if command == "published" else ["0.3.0"])) == 1
    assert message in capsys.readouterr().err
    assert path.read_text() == bad


@pytest.mark.parametrize("change,message", [
    (lambda d: d.update(versions=[]), "nonempty list"),
    (lambda d: d.update(notice=None), "notice"),
    (lambda d: d["versions"].append(None), "must be a mapping"),
    (lambda d: d["versions"].append(d["versions"][1].copy()), "duplicate version"),
    (lambda d: d["versions"].pop(0), "missing devel"),
    (lambda d: d["versions"][1].update(status="unknown"), "invalid status"),
    (lambda d: d["versions"][0].update(status="supported"), "devel must have status development"),
    (lambda d: d["versions"][0].update(source="branch"), "devel source"),
    (lambda d: d["versions"][1].update(source=""), "nonempty source"),
    (lambda d: d["versions"][1].update(note=[]), "nonempty note"),
    (lambda d: d["versions"][1].update(legacy="true"), "legacy must be boolean"),
    (lambda d: d["versions"][1].update(version="../bad"), "Expected X.Y.Z"),
])
def test_manifest_shape_refusals(checkout, change, message):
    data = copy.deepcopy(MANIFEST)
    change(data)
    write_manifest(checkout, data)
    with pytest.raises(ValueError, match=message):
        MODULE.read_manifest(checkout)


@pytest.fixture
def promoted(checkout):
    MODULE.promote(checkout, "0.3.0", [])
    write_notes(checkout)
    return checkout


@pytest.mark.parametrize("case,message", [
    ("current", "current must be 0.3.0"), ("missing", "Missing version 0.3.0"),
    ("status", "0.3.0 status must be supported"), ("source", "0.3.0 source must be docs-0.3.0"),
    ("other", "0.2.15 must not also be supported"),
    ("notes_missing", "notes.md"), ("notes_empty", "release body is empty"),
    ("placeholder", "placeholder"),
])
def test_check_each_obligation_alone(promoted, capsys, case, message):
    data = MODULE.read_manifest(promoted)
    if case == "current":
        data["current"] = "0.2.15"
    elif case == "missing":
        data["versions"].pop(1)
    elif case == "status":
        data["versions"][1]["status"] = "deprecated"
    elif case == "source":
        data["versions"][1]["source"] = "v0.3.0"
    elif case == "other":
        data["versions"][2]["status"] = "supported"
    elif case == "notes_missing":
        (promoted / "engineering-docs/releases/v0.3.0/notes.md").unlink()
    else:
        write_notes(promoted, "  \n" if case == "notes_empty" else "<write release notes>")
    write_manifest(promoted, data)
    errors = MODULE.check(promoted, "0.3.0")
    assert len(errors) == 1
    assert message in errors[0]
    assert invoke(promoted, "check", "0.3.0") == 1
    assert message in capsys.readouterr().err


def test_check_collects_all_conditions(checkout):
    errors = MODULE.check(checkout, "0.3.0")
    assert len(errors) == 4
    assert "current" in errors[0]
    assert "Missing version" in errors[1]
    assert "0.2.15" in errors[2]
    assert "notes.md" in errors[3]


def test_check_success(promoted, capsys):
    assert invoke(promoted, "check", "0.3.0") == 0
    assert "obligations satisfied" in capsys.readouterr().out


@pytest.mark.parametrize("front", ["", "---\ntitle: Release\n---\n", "---\ntitle: Release\n...\n"])
def test_notes_strips_only_front_matter_without_manifest(checkout, capsys, front):
    body = "\n# Release\n\nChanges.\n\n---\n\nMore details.\n"
    write_notes(checkout, front + body)
    (checkout / "docs/versions.yaml").write_text("[")
    assert invoke(checkout, "notes", "0.3.0") == 0
    assert capsys.readouterr().out == body


@pytest.mark.parametrize("text,message", [
    ("---\ntitle: Release\n", "unclosed front matter"),
    ("---\ntitle: Release\n---\n", "release body is empty"),
    ("---\ntitle: <title>\n---\nBody", "placeholder"),
    ("Body <todo>\n", "placeholder"),
])
def test_notes_refusals(checkout, capsys, text, message):
    write_notes(checkout, text)
    assert invoke(checkout, "notes", "0.3.0") == 1
    output = capsys.readouterr()
    assert message in output.err
    assert output.out == ""


@pytest.mark.parametrize("command", ["promote", "check", "notes"])
@pytest.mark.parametrize("version", ["../bad", "v0.3.0", "0.3.0-rc8", "00.3.0", "0.3.0\n"])
def test_invalid_version_arguments(checkout, capsys, command, version):
    assert invoke(checkout, command, version) == 1
    assert "Expected X.Y.Z" in capsys.readouterr().err


def final_release():
    return {"isDraft": False, "isPrerelease": False, "assets": [{"name": "devcapsule.pex"}]}


@pytest.mark.parametrize("failure,reason", [("draft", "draft"), ("prerelease", "prerelease"),
    ("asset", "missing devcapsule.pex"), ("missing", "release not found")])
def test_published_refuses_and_names_every_version(checkout, monkeypatch, capsys, failure, reason):
    seen = []
    def release(tag):
        seen.append(tag)
        if failure == "missing":
            raise ValueError("release not found")
        state = final_release()
        if failure == "draft":
            state["isDraft"] = True
        elif failure == "prerelease":
            state["isPrerelease"] = True
        else:
            state["assets"] = [{"name": "other.pex"}]
        return state
    monkeypatch.setattr(MODULE, "github_release", release)
    assert invoke(checkout, "published") == 1
    lines = capsys.readouterr().err.splitlines()
    assert seen == ["v0.2.15", "v0.2.14", "v0.2.12"]
    assert len(lines) == 3
    for version, line in zip(seen, lines):
        assert version[1:] in line
        assert reason in line


def test_published_success_and_devel_skipped(checkout, monkeypatch, capsys):
    seen = []
    def release(tag):
        seen.append(tag)
        return final_release()
    monkeypatch.setattr(MODULE, "github_release", release)
    assert invoke(checkout, "published") == 0
    assert seen == ["v0.2.15", "v0.2.14", "v0.2.12"]
    assert "obligations satisfied" in capsys.readouterr().out


@pytest.mark.parametrize("code,stdout,stderr", [
    (0, '{"isDraft":false,"isPrerelease":false,"assets":[{"name":"devcapsule.pex"}]}', ""),
    (1, "", "release not found"), (0, "invalid json", ""),
])
def test_github_release_adapter(monkeypatch, code, stdout, stderr):
    def run(args, **kwargs):
        assert args == ["gh", "release", "view", "v0.3.0", "--json", "isDraft,isPrerelease,assets"]
        assert kwargs == {"cwd": MODULE.ROOT, "text": True, "capture_output": True, "check": False}
        return subprocess.CompletedProcess(args, code, stdout, stderr)
    monkeypatch.setattr(MODULE.subprocess, "run", run)
    if code or stdout == "invalid json":
        with pytest.raises(ValueError):
            MODULE.github_release("v0.3.0")
    else:
        assert MODULE.github_release("v0.3.0") == final_release()


REPOSITORY = Path(__file__).parents[2]


def test_listed_candidate_may_be_development(checkout, monkeypatch, capsys):
    """The contract lets a candidate be listed as development; it has no download yet."""
    data = copy.deepcopy(MANIFEST)
    data["versions"].insert(1, {"version": "0.3.0", "source": "release-0.3.0", "status": "development"})
    write_manifest(checkout, data)
    seen = []
    def release(tag):
        seen.append(tag)
        return final_release()
    monkeypatch.setattr(MODULE, "github_release", release)
    assert invoke(checkout, "published") == 0
    assert seen == ["v0.2.15", "v0.2.14", "v0.2.12"]
    assert invoke(checkout, "promote", "0.3.0") == 1
    assert "already listed" in capsys.readouterr().err


def test_promote_reads_the_repository_manifest_as_written(checkout):
    """The real file, with its header comment and quoted versions, is admitted and promoted."""
    (checkout / "docs/versions.yaml").write_bytes((REPOSITORY / "docs/versions.yaml").read_bytes())
    previous = MODULE.read_manifest(checkout)["current"]
    # A synthetic future release keeps this real-file test valid after promotion.
    future = "999.0.0"
    (checkout / "devcapsule-src/pyproject.toml").write_text(f'[project]\nversion = "{future}"\n')
    moves = MODULE.promote(checkout, future, [])
    assert f"current: {previous} -> {future}" in moves
    data = MODULE.read_manifest(checkout)
    assert data["current"] == future
    assert data["versions"][0]["source-version"] == future
    assert [entry["version"] for entry in data["versions"]][:2] == ["devel", future]


@pytest.mark.parametrize("body", [
    "Run `devcapsule project --path <checkout> config show`.\n",
    "```sh\ndevcapsule project --path <checkout> run\n```\n",
    "~~~\n<not a placeholder>\n~~~\n",
    "See <https://devcapsule.mycodespace.ai/docs/current/>.\n",
    "Use ``a `<b>` span``.\n",
])
def test_notes_accepts_angle_brackets_in_code_and_autolinks(checkout, capsys, body):
    write_notes(checkout, body)
    assert invoke(checkout, "notes", "0.3.0") == 0
    assert capsys.readouterr().out == body


@pytest.mark.parametrize("body", [
    "Download <the asset> from GitHub.\n",
    "```sh\nunclosed fence\n\n<the placeholder> outside\n",
    "A `span` then <the placeholder>.\n",
    "# Release 0.3.0\n\n<Write the release summary\nand compatibility notes here>\n",
])
def test_notes_refuses_placeholders_in_prose(checkout, capsys, body):
    write_notes(checkout, body)
    assert invoke(checkout, "notes", "0.3.0") == 1
    assert "placeholder" in capsys.readouterr().err


def test_notes_accepts_the_0_2_14_notes_as_published(checkout):
    """The 0.2.14 notes carry ``--path <checkout>`` in code spans; a blanket rule refused them."""
    path = checkout / "engineering-docs/releases/v0.2.14/notes.md"
    path.parent.mkdir(parents=True)
    path.write_bytes((REPOSITORY / "engineering-docs/releases/v0.2.14/notes.md").read_bytes())
    assert "<checkout>" in MODULE.notes(checkout, "0.2.14")


def test_check_refuses_a_wrapped_placeholder_through_notes(promoted, capsys):
    """Round 1 of PR294.1: a placeholder wrapped across lines was accepted once; never again."""
    write_notes(promoted, "# Release 0.3.0\n\n<Write the release summary\nand compatibility notes here>\n")
    errors = MODULE.check(promoted, "0.3.0")
    assert len(errors) == 1 and "placeholder" in errors[0]
    assert invoke(promoted, "check", "0.3.0") == 1
    assert "placeholder" in capsys.readouterr().err


def test_a_less_than_sign_before_a_later_paragraph_is_not_a_placeholder(checkout, capsys):
    body = "Memory below 4 GiB is < the default.\n\nThe next paragraph ends with a word>\n"
    write_notes(checkout, body)
    assert invoke(checkout, "notes", "0.3.0") == 0
    assert capsys.readouterr().out == body
