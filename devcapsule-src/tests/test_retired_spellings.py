"""Every retired spelling refuses before it can write or prepare a launch."""
from pathlib import Path

import pytest

from devcapsule import cli
from tests.test_checkout_commands import project, runtime_project  # noqa: F401

pytestmark = pytest.mark.legacy


SPELLINGS = [
    (("config", "capabilities", "--local", "python-ide"), "config ide"),
    (("config", "capabilities", "--without", "browser-automation"), "config omit"),
    (("config", "capabilities", "--required", "python"), "config require"),
    (("config", "capabilities", "--optional", "browser-automation"), "config offer"),
    (("config", "capabilities", "--sdk-major", "python=3"), "NAME>=VERSION"),
    (("config", "need", "python"), "config require"),
    (("init", "--need", "python"), "init --require"),
    (("init", "--required", "python"), "init --require"),
    (("init", "--optional", "browser-automation"), "init --offer"),
    (("init", "--local", "python-ide"), "config ide"),
    (("init", "--less-pedantic"), "config authorize base-image"),
    (("init", "--sdk-major", "python=3"), "NAME>=VERSION"),
    (("init", "--agent", "codex-agent"), "init --with"),
    (("config", "set-env", "TOKEN", "value"), "config env set"),
    (("config", "unset-env", "TOKEN"), "config env unset"),
    (("config", "list-env"), "config env list"),
    (("config", "set-extra-docker-args", "--", "--gpus", "all"), "config docker-args set"),
    (("config", "list-extra-docker-args"), "config docker-args list"),
    (("config", "remove-extra-docker-args"), "config docker-args clear"),
    (("config", "unset", "memory"), "config set NAME default"),
    (("config", "list"), "config show"),
    (("config", "resolve"), "project run"),
    # ``run --force`` is a live flag since 2026-10-29: the explicit departure
    # from a required IDE (work order of 2026-10-28), tested in
    # test_ide_requirement_override.py.
    (("run", "--force-config"), "project run"),
    (("config", "agent", "add", "codex"), "config add"),
    (("config", "agent", "remove", "codex"), "config omit"),
    (("config", "tool", "omit", "browser-automation"), "config omit"),
    (("config", "tool", "restore", "browser-automation"), "config restore"),
    (("config", "require", "tool", "python"), "config require CAPABILITY"),
    (("config", "offer", "tool", "browser-automation"), "config offer CAPABILITY"),
    (("config", "drop", "tool", "python"), "config drop CAPABILITY"),
    (("run", "--agent", "codex"), "run --with"),
]


def snapshot(root: Path):
    return {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns) if p.is_file() else None
            for p in root.rglob("*")}


@pytest.mark.parametrize("arguments,replacement", SPELLINGS, ids=[" ".join(a) for a, _ in SPELLINGS])
@pytest.mark.parametrize("initialized", [False, True])
def test_retired_spelling_refuses_without_writes(tmp_path, monkeypatch, capsys, arguments, replacement, initialized):
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    project = tmp_path / "project"
    project.mkdir()
    prefix = ["project", "--path", str(project)]
    if initialized:
        assert cli.main([*prefix, "init", "--require", "node", "--creator", "mailto:test@example.org"]) == 0
    capsys.readouterr()
    before = snapshot(tmp_path)
    assert cli.main([*prefix, *arguments]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert len(output.err.splitlines()) == 1
    assert replacement in output.err
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("arguments,replacement", SPELLINGS)
def test_retired_spellings_name_replacement_inside_capsule(runtime_project, tmp_path, capsys, arguments, replacement):
    capsys.readouterr()
    before = snapshot(tmp_path)
    assert cli.main(["project", "--path", str(runtime_project), *arguments]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert len(output.err.splitlines()) == 1
    assert replacement in output.err
    assert snapshot(tmp_path) == before
