"""The console's configuration channel on the launcher's side: results, deferral, the in-capsule listing, the commands."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from devcapsule import cli
from devcapsule.commands._console_channel import ChannelWatcher, handle_request, read_channel, run_config, sweep
from devcapsule.commands._run_flow import RunFlags, launch_listing_document, prepare_launch
from devcapsule.configuration.capability_commands import paths
from devcapsule.configuration.console_channel import (
    Disposition, classify, listing_document, parse_request, read_document, request_id, write_complete,
)
from devcapsule.configuration.console_requests import console_requests_path, deferred_requests
from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.storage import checkout_record_paths, load_toml
from devcapsule import runtime_configuration

pytestmark = pytest.mark.legacy


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    root = tmp_path / "project"
    root.mkdir()
    assert cli.main(["project", "--path", str(root), "init", "--require", "node", "--creator", "mailto:owner@example.test"]) == 0
    return root


def config(root: Path, *arguments: str) -> int:
    return cli.main(["project", "--path", str(root), "config", *arguments])


def record_path(root: Path) -> Path:
    return checkout_record_paths(load_toml(paths(root)[0]), root)[0]


def request(directory: Path, identifier: str, *arguments: str) -> Path:
    path = directory / f"{identifier}.request.json"
    write_complete(path, {"format": 1, "requested": "2026-10-24T10:00:00+00:00", "arguments": list(arguments)})
    return path


def result(directory: Path, identifier: str) -> dict:
    return read_document(directory / f"{identifier}.result.json")


@pytest.mark.parametrize("arguments, expected", [
    (["ide", "python-ide"], Disposition.APPLY), (["env", "set", "X", "1"], Disposition.APPLY),
    (["deny", "network"], Disposition.APPLY), (["trust", "withdraw", "x"], Disposition.APPLY),
    (["docker-args", "clear"], Disposition.APPLY),
    (["authorize", "network", "host"], Disposition.DEFER), (["trust", "accept", "x"], Disposition.DEFER),
    (["bind", "x", "y"], Disposition.DEFER), (["docker-args", "set", "--privileged"], Disposition.DEFER),
    (["show"], Disposition.REFUSE), (["env", "list"], Disposition.REFUSE), (["default", "memory", "8G"], Disposition.REFUSE),
    (["require", "x"], Disposition.REFUSE), (["run"], Disposition.REFUSE), ([], Disposition.REFUSE),
])
def test_classification(arguments: list[str], expected: Disposition) -> None:
    disposition, reason = classify(arguments)
    assert disposition is expected and bool(reason) == (expected is Disposition.REFUSE)


def test_request_documents_are_validated(tmp_path: Path) -> None:
    assert request_id(Path("000001-ide.request.json")) == "000001-ide"
    for name in ("x.json", "1-ide.request.json", "000001-Ide.request.json"):
        with pytest.raises(ProjectConfigurationError):
            request_id(Path(name))
    assert parse_request({"format": 1, "arguments": ["ide", "x"]}) == ["ide", "x"]
    documents: list[object] = [{"format": 2, "arguments": ["ide"]}, {"format": 1, "arguments": []}, {"format": 1, "arguments": ["a\nb"]},
                               {"format": 1, "arguments": ["ide", "--path", "/x"]}, {"format": 1, "arguments": ["x" * 5000]}, {"format": 1, "arguments": ["ide", "\ud800"]}, []]
    for document in documents:
        with pytest.raises(ProjectConfigurationError):
            parse_request(document)
    (tmp_path / "link.json").symlink_to(tmp_path / "missing")
    with pytest.raises(ProjectConfigurationError, match="cannot open"):
        read_document(tmp_path / "link.json")
    big = tmp_path / "big.json"
    big.write_text("[" + "1," * 200000 + "1]")
    with pytest.raises(ProjectConfigurationError, match="larger than"):
        read_document(big)
    path = write_complete(tmp_path / "doc.json", {"a": 1})
    assert read_document(path) == {"a": 1} and not list(tmp_path.glob(".doc.json.*"))


def test_an_applied_request_runs_the_config_command_and_reports_its_output(project: Path, tmp_path: Path) -> None:
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-ide", "ide", "python-ide")
    request(channel, "000002-ide", "ide", "no-such-ide")
    assert sweep(channel, project, record_path(project)) == 2
    recorded = result(channel, "000001-ide")
    assert recorded["status"] == "recorded" and "python-ide" in recorded["text"]
    assert load_toml(record_path(project))["capabilities"]["selected"] == ["python-ide"]
    refused = result(channel, "000002-ide")
    assert refused["status"] == "refused" and "no-such-ide" in refused["text"]
    assert sweep(channel, project, record_path(project)) == 0  # answered requests are never run twice


def test_a_widening_is_deferred_until_confirmed_on_the_host(project: Path, tmp_path: Path, capsys) -> None:
    assert config(project, "ide", "python-ide") == 0
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-authorize", "authorize", "network", "host")
    request(channel, "000002-ide", "ide")  # malformed: refused by the command, not by the launcher
    request(channel, "000003-show", "show")
    assert sweep(channel, project, record_path(project)) == 3
    deferred = result(channel, "000001-authorize")
    assert deferred["status"] == "deferred" and "console apply 000001-authorize" in deferred["text"]
    assert result(channel, "000003-show")["status"] == "refused"
    assert "network" not in load_toml(record_path(project)).get("authorization", {})
    kept = deferred_requests(record_path(project))
    assert [item.id for item in kept] == ["000001-authorize"] and kept[0].statement == "config authorize network host"
    assert not str(console_requests_path(record_path(project))).startswith(str(record_path(project).parent))
    capsys.readouterr()
    # The host's listing shows it, pending and soft; check does not block on it, run asks.
    assert config(project, "show") == 0
    shown = capsys.readouterr().out
    assert "000001-authorize" in shown and "confirm or discard: config authorize network host" in shown
    assert config(project, "check") == 3
    assert config(project, "console", "list") == 0
    assert "000001-authorize  asked 2026-10-24T10:00:00+00:00: config authorize network host" in capsys.readouterr().out
    prompts = io.StringIO()
    prepared = prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO("\n"), output_stream=prompts)
    assert "The console asked at 2026-10-24T10:00:00+00:00: config authorize network host" in prompts.getvalue()
    assert deferred_requests(record_path(project))  # kept
    prepared = prepare_launch(project, RunFlags(), interactive=False)
    assert any("000001-authorize" in note and "console apply" in note for note in prepared.notes)
    prompts = io.StringIO()
    prepare_launch(project, RunFlags(), interactive=True, input_stream=io.StringIO("a\n"), output_stream=prompts)
    assert load_toml(record_path(project))["authorization"]["network"]["value"] == "host"
    assert deferred_requests(record_path(project)) == []
    request(channel, "000004-bind", "bind", "x", "y")
    sweep(channel, project, record_path(project))
    assert config(project, "console", "discard", "000004-bind") == 0
    assert deferred_requests(record_path(project)) == []
    assert config(project, "console", "discard", "000004-bind") == 2
    assert config(project, "console", "apply", "000009-x") == 2


def test_console_apply_runs_the_command_and_forgets_the_request(project: Path, tmp_path: Path, capsys) -> None:
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-authorize", "authorize", "network", "host")
    sweep(channel, project, record_path(project))
    assert config(project, "console", "apply", "000001-authorize") == 0
    out = capsys.readouterr().out
    assert "Authorized network for this checkout: host" in out and "Applied and forgot" in out
    assert deferred_requests(record_path(project)) == []
    request(channel, "000002-authorize", "authorize", "quantum", "x")
    sweep(channel, project, record_path(project))
    assert config(project, "console", "apply", "000002-authorize") == 2
    assert [item.id for item in deferred_requests(record_path(project))] == ["000002-authorize"]  # kept after a refusal


def test_the_watcher_answers_while_running_and_once_more_on_stop(project: Path, tmp_path: Path) -> None:
    channel = tmp_path / "channel"
    channel.mkdir()
    watcher = ChannelWatcher(channel, project, record_path(project), interval=0.05)
    watcher.start()
    request(channel, "000001-deny", "deny", "network")
    for _ in range(200):
        if (channel / "000001-deny.result.json").exists():
            break
        import time
        time.sleep(0.05)
    assert result(channel, "000001-deny")["status"] == "recorded"
    watcher.stop()
    request(channel, "000002-forget", "forget", "network")
    assert sweep(channel, project, record_path(project)) == 1


def test_inside_a_capsule_show_prints_the_launch_listing_and_the_requests(project: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    assert config(project, "ide", "python-ide") == 0
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    prepared = prepare_launch(project, RunFlags(), interactive=False)
    listing = launch_listing_document(prepared.selected)
    assert listing["context"] == "at launch" and listing["checkout"]["name"] == "default"
    assert any(row["kind"] == "ide" and row["name"] == "python-ide" for row in listing["rows"])
    channel = tmp_path / "channel"
    channel.mkdir()
    write_complete(channel / "listing.json", listing_document(listing, "2026-10-24T12:00:00+00:00"))
    request(channel, "000001-ide", "ide", "frontend-ide")
    write_complete(channel / "000001-ide.result.json", {"format": 1, "status": "recorded", "text": "done", "at": "t"})
    request(channel, "000002-authorize", "authorize", "network", "host")
    view = read_channel(channel)
    assert view is not None and view.at == "2026-10-24T12:00:00+00:00" and len(view.requests) == 2
    assert view.requests[1]["result"] is None
    # The in-capsule command reads the channel through the runtime context.
    monkeypatch.setattr(runtime_configuration, "CHANNEL_PATH", channel)
    context = runtime_configuration.RuntimeConfiguration({"format": 1, "project": listing["project"], "launcher-root": str(project),
                                                          "runtime-root": "/workspace/project", "checkout-file": "devcapsule.checkout.toml",
                                                          "checkout-name": "default"})
    from devcapsule.commands.project import _show_inside_capsule
    assert _show_inside_capsule(context, False) == 0
    out = capsys.readouterr().out
    assert "At launch, 2026-10-24T12:00:00+00:00:" in out and "python-ide" in out
    assert "000001-ide: config ide frontend-ide" in out and "recorded: done" in out
    assert "000002-authorize: config authorize network host" in out and "waiting for the launcher" in out
    assert "config show" in out
    assert _show_inside_capsule(context, True) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["at"] == "2026-10-24T12:00:00+00:00" and len(document["console-requests"]) == 2
    assert document["rows"] == listing["rows"]
    # A valid listing from another checkout cannot stand in for this run.
    foreign = {**listing, "checkout": {**listing["checkout"], "launcher-path": "/other"}}
    write_complete(channel / "listing.json", listing_document(foreign))
    with pytest.raises(ProjectConfigurationError, match="another checkout"):
        _show_inside_capsule(context, True)
    (channel / "listing.json").unlink()
    with pytest.raises(ProjectConfigurationError, match="no launch listing"):
        _show_inside_capsule(context, False)
    # Without the launcher's listing, the older read-only report stays.
    monkeypatch.setattr(runtime_configuration, "CHANNEL_PATH", tmp_path / "absent")
    with patch.object(runtime_configuration.RuntimeConfiguration, "configuration_report", return_value="legacy report"):
        assert _show_inside_capsule(context, False) == 0
    assert "legacy report" in capsys.readouterr().out


@pytest.mark.parametrize("tokens", [
    ["forget", "docker-daemon"], ["env", "set", "HOST_SECRET", "--from-host"],
    ["env", "set", "HOST_SECRET", "--from-h"],
])
def test_indirect_widenings_never_run_in_the_watcher(project, tmp_path, tokens):
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-change", *tokens)
    with patch("devcapsule.commands._console_channel.run_config") as run:
        assert sweep(channel, project, record_path(project)) == 1
    run.assert_not_called()
    assert deferred_requests(record_path(project))[0].arguments == tuple(tokens)
    assert result(channel, "000001-change")["status"] == "deferred"


def test_same_request_name_in_later_run_preserves_both_requests(project, tmp_path):
    for name, node in (("first", "network"), ("second", "docker-daemon")):
        channel = tmp_path / name
        channel.mkdir()
        request(channel, "000001-authorize", "authorize", node, "host" if node == "network" else "host-socket")
        sweep(channel, project, record_path(project))
    kept = deferred_requests(record_path(project))
    assert len(kept) == 2 and kept[0].id != kept[1].id
    assert [item.arguments[1] for item in kept] == ["network", "docker-daemon"]
    assert kept[1].id in result(channel, "000001-authorize")["text"]


def test_store_follows_checkout_path_not_registration_name(project, tmp_path):
    import shutil
    from devcapsule.configuration.storage import named_checkout_record_paths
    channel = tmp_path / "channel"
    channel.mkdir()
    assert config(project, "deny", "network") == 0
    request(channel, "000001-authorize", "authorize", "network", "host")
    sweep(channel, project, record_path(project))
    original = record_path(project)
    stored = console_requests_path(original)
    assert config(project, "forget", "network") == 0
    assert len(deferred_requests(original)) == 1
    renamed, _ = named_checkout_record_paths(load_toml(paths(project)[0]), "renamed")
    renamed.parent.mkdir(parents=True, exist_ok=True)
    original.rename(renamed)
    assert console_requests_path(renamed) == stored and len(deferred_requests(renamed)) == 1
    second = tmp_path / "second"
    shutil.copytree(project, second)
    assert cli.main(["project", "--path", str(second), "checkout", "register", "second"]) == 0
    other = record_path(second)
    other.rename(original)  # Reuse the first checkout's old registration slot.
    other = original
    assert console_requests_path(other) != stored and deferred_requests(other) == []
    request(channel, "000002-authorize", "authorize", "docker-daemon", "host-socket")
    sweep(channel, second, other)
    assert [item.arguments[1] for item in deferred_requests(other)] == ["docker-daemon"]
    assert [item.arguments[1] for item in deferred_requests(renamed)] == ["network"]


@pytest.mark.parametrize("kind", ["link", "fifo", "huge", "partial"])
def test_bad_request_cannot_block_other_requests(project, tmp_path, kind):
    import os
    channel = tmp_path / "channel"
    channel.mkdir()
    bad = channel / "000001-ide.request.json"
    if kind == "link":
        bad.symlink_to(record_path(project))
    elif kind == "fifo":
        os.mkfifo(bad)
    elif kind == "huge":
        bad.write_bytes(b" " * (256 * 1024 + 1))
    else:
        bad.write_text('{"format":')
    (channel / "outside.request.json").write_text("{}")
    request(channel, "000002-deny", "deny", "network")
    assert sweep(channel, project, record_path(project)) == 2
    assert result(channel, "000001-ide")["status"] == "refused"
    assert result(channel, "000002-deny")["status"] == "recorded"
    assert not (channel / "outside.result.json").exists()


def test_stop_keeps_pending_requests_without_running_more_children(project, tmp_path):
    channel = tmp_path / "channel"
    channel.mkdir()
    watcher = ChannelWatcher(channel, project, record_path(project), interval=3600)
    watcher.start()
    request(channel, "000001-ide", "ide", "frontend-ide")
    request(channel, "000002-authorize", "authorize", "docker-daemon", "host-socket")
    with patch("devcapsule.commands._console_channel.run_config") as run:
        watcher.stop()
    run.assert_not_called()
    assert not watcher._thread.is_alive()
    assert [item.arguments[0] for item in deferred_requests(record_path(project))] == ["ide", "authorize"]
    assert result(channel, "000001-ide")["status"] == "deferred"
    assert "stopping" in result(channel, "000001-ide")["text"]


def test_child_has_no_host_secret_python_injection_or_terminal(project, tmp_path, monkeypatch):
    import os
    import sys
    from devcapsule.commands import _console_channel as adapter
    monkeypatch.setenv("HOST_SECRET", "never expose")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    script = "import os,sys,json; print(json.dumps([dict(os.environ),os.getsid(0),os.getpid(),sys.stdin.read()]))"
    monkeypatch.setattr(adapter, "_config_command", lambda root, args: [sys.executable, "-c", script])
    status, output = adapter.run_config(project, [])
    environment, session, pid, stdin = json.loads(output)
    assert status == 0 and session == pid and session != os.getsid(0) and stdin == ""
    assert "HOST_SECRET" not in environment and "PYTHONPATH" not in environment
    assert environment["XDG_CONFIG_HOME"] == os.environ["XDG_CONFIG_HOME"]
    monkeypatch.setenv("DOCKER_HOST", "ssh://host-context.example")
    status, output = adapter.run_config(project, [], host_confirmed=True)
    confirmed_environment = json.loads(output)[0]
    assert status == 0 and confirmed_environment["DOCKER_HOST"] == "ssh://host-context.example"
    assert confirmed_environment["HOST_SECRET"] == "never expose"
    # A descendant inherits the output pipe. Killing only its parent would
    # let it finish its write and keep communicate() waiting for that pipe.
    import time
    started, escaped = tmp_path / "started", tmp_path / "escaped"
    descendant = (f"from pathlib import Path; import time; Path({str(started)!r}).touch(); "
                  f"time.sleep(0.8); Path({str(escaped)!r}).touch()")
    parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', {descendant!r}]); time.sleep(30)"
    monkeypatch.setattr(adapter, "COMMAND_TIMEOUT_SECONDS", 0.3)
    monkeypatch.setattr(adapter, "_config_command", lambda root, args: [sys.executable, "-c", parent])
    assert adapter.run_config(project, []) == (1, "the command did not finish within 0.3 seconds")
    assert started.exists()
    time.sleep(0.9)
    assert not escaped.exists()


def test_apply_preserves_exact_tokens(project):
    from devcapsule.commands._console_channel import apply_deferred
    from devcapsule.configuration.console_channel import DeferredRequest
    from devcapsule.configuration.console_requests import write_deferred
    tokens = ("docker-args", "set", "--env", "TEXT=a b;$(false)")
    write_deferred(record_path(project), [DeferredRequest("000001-docker-args", "now", tokens)])
    with patch("devcapsule.commands._console_channel.run_config", return_value=(0, "done")) as run:
        assert apply_deferred(project, record_path(project), "000001-docker-args") == (0, "done")
    run.assert_called_once_with(project, tokens, host_confirmed=True)
    assert deferred_requests(record_path(project)) == []


def test_launch_listing_includes_run_once_selection_and_earlier_requests(project, tmp_path):
    assert config(project, "ide", "python-ide") == 0
    assert config(project, "recommend", "docker-daemon", "host-socket", "--because", "Project build containers") == 0
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-authorize", "authorize", "network", "host")
    sweep(channel, project, record_path(project))
    prepared = prepare_launch(project, RunFlags(ide="frontend-ide", capabilities=("codex",)), interactive=False)
    listing = launch_listing_document(prepared.selected)
    assert any(row["kind"] == "ide" and row["name"] == "frontend-ide" for row in listing["rows"])
    assert any(row["kind"] == "console" and row["name"] == "000001-authorize" for row in listing["rows"])
    exposure = next(row for row in listing["rows"] if row["name"] == "docker-daemon")
    assert "broad control of the host" in exposure["exposure"]
    assert exposure["reason"] == "Project build containers"
    assert "codex" in prepared.selected.lock["components"]
    assert any(row["kind"] == "capability" and "codex" in row["name"] for row in listing["rows"])
    assert load_toml(record_path(project))["capabilities"]["selected"] == ["python-ide"]


def test_channel_requires_its_listing_and_contains_unreadable_results(tmp_path):
    import os
    with pytest.raises(ProjectConfigurationError, match="no launch listing"):
        read_channel(tmp_path)
    write_complete(tmp_path / "listing.json", listing_document({"rows": []}))
    request(tmp_path, "000001-ide", "ide", "python-ide")
    result_path = tmp_path / "000001-ide.result.json"
    for document in ({}, {"format": 1, "status": "recorded"}):
        write_complete(result_path, document)
        view = read_channel(tmp_path)
        assert view is not None and "Cannot read" in view.requests[0]["result"]["text"]
        assert view.requests[0]["result"]["status"] == "unknown"
    result_path.unlink()
    os.mkfifo(result_path)
    view = read_channel(tmp_path)
    assert view is not None and "not a regular file" in view.requests[0]["result"]["text"]


@pytest.mark.parametrize("save", [False, True])
def test_confirmed_console_request_is_used_this_launch_and_not_overwritten(project, tmp_path, save):
    assert config(project, "ide", "python-ide") == 0
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-authorize", "authorize", "docker-daemon", "host-socket")
    sweep(channel, project, record_path(project))
    prepared = prepare_launch(project, RunFlags(memory="6g", save=save), interactive=True,
                              input_stream=io.StringIO("a\n"), output_stream=io.StringIO())
    assert prepared.selected.checkout["authorization"]["docker-daemon"]["value"] == "host-socket"
    saved = load_toml(record_path(project))
    assert saved["authorization"]["docker-daemon"]["value"] == "host-socket"
    if save:
        assert saved["configuration"]["values"]["memory"] == "6GiB"
    assert deferred_requests(record_path(project)) == []


def test_forgetting_vendor_denial_requires_confirmation_despite_home_trust(project, tmp_path):
    from devcapsule.configuration.authorization import review_authorizations
    from devcapsule.configuration.file_formats import render_toml
    from devcapsule.configuration.storage import load_trust
    from devcapsule.configuration.trust import HomeTrust
    manifest = load_toml(paths(project)[0])
    lock_path = project / ".devcapsule" / "devcapsule.linux-amd64.lock"
    lock = load_toml(lock_path)
    lock["components"]["claude-code"] = {
        "version": "1.0.0", "acquisition-authorization": "claude-code-download",
        "terms-url": "https://www.anthropic.com/legal/commercial-terms", "delivery-policy": "local-materialization",
        "artifacts": {"linux-amd64": {"url": "https://downloads.example.test/claude", "sha256": "e" * 64}},
    }
    lock_path.write_text(render_toml(lock))
    def reviews(root):
        return {item.name: item for item in review_authorizations(
            manifest, lock, load_toml(record_path(root)), HomeTrust.read(load_trust()))}
    from tests.test_trust import accept
    assert accept(project, "claude-code") == 0
    assert config(project, "authorize", "claude-code-download", "false") == 0
    assert reviews(project)["claude-code-download"].trusted_channel is None
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-forget", "forget", "claude-code-download")
    sweep(channel, project, record_path(project))
    assert reviews(project)["claude-code-download"].trusted_channel is None
    assert result(channel, "000001-forget")["status"] == "deferred"
    assert config(project, "console", "apply", "000001-forget") == 0
    assert reviews(project)["claude-code-download"].trusted_channel == "claude-code"


@pytest.mark.parametrize("node,value", [("network", "bridge"), ("docker-daemon", "none"), ("host-browser", "false")])
def test_explicit_secure_authorizations_are_applied_without_confirmation(project, tmp_path, node, value):
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-authorize", "authorize", node, value)
    assert sweep(channel, project, record_path(project)) == 1
    assert result(channel, "000001-authorize")["status"] == "recorded"
    assert deferred_requests(record_path(project)) == []
    assert load_toml(record_path(project))["authorization"][node]["value"] == (False if value == "false" else value)


def test_full_deferred_queue_preserves_previous_requests(project):
    from devcapsule.configuration.console_channel import DeferredRequest, result_document
    from devcapsule.configuration.console_requests import write_deferred
    first = DeferredRequest("000001-authorize", "now", ("authorize", "network", "host"))
    write_deferred(record_path(project), [first])
    huge = DeferredRequest("000002-bind", "now", ("bind", *(["x" * 4096] * 63)))
    with pytest.raises(ProjectConfigurationError, match="queue is full"):
        write_deferred(record_path(project), [first, huge, DeferredRequest("000003-bind", "now", huge.arguments)])
    assert deferred_requests(record_path(project)) == [first]
    document = result_document("refused", "x" * (256 * 1024))
    assert "Output truncated" in document["text"]
    assert len(json.dumps(document).encode()) < 256 * 1024


def test_launcher_publication_replaces_links_only_after_document_is_complete(tmp_path, monkeypatch):
    import os
    destination = tmp_path / "000001-ide.result.json"
    outside = tmp_path / "outside"
    outside.write_text("unchanged")
    destination.symlink_to(outside)
    planted = tmp_path / f".{destination.name}.{os.getpid()}.tmp"
    planted.symlink_to(outside)
    original = Path.replace
    observed = []
    def publish(source, target):
        observed.append(json.loads(source.read_text()))
        assert destination.is_symlink() and outside.read_text() == "unchanged"
        return original(source, target)
    monkeypatch.setattr(Path, "replace", publish)
    write_complete(destination, {"format": 1, "text": "done"})
    assert observed == [{"format": 1, "text": "done"}]
    assert read_document(destination) == observed[0] and outside.read_text() == "unchanged"
    assert planted.is_symlink()


def test_request_timestamp_cannot_inject_terminal_controls_or_overflow_results():
    for value in ("\x1b[2J", "x" * 100000, 4, "2026-10-24"):
        with pytest.raises(ProjectConfigurationError, match="ISO time"):
            parse_request({"format": 1, "arguments": ["authorize", "network", "host"], "requested": value})


def test_console_forget_during_run_removes_stale_grant_but_keeps_saved_flags(project, tmp_path):
    assert config(project, "ide", "python-ide") == 0
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    assert config(project, "authorize", "network", "host") == 0
    channel = tmp_path / "channel"
    channel.mkdir()
    request(channel, "000001-forget", "forget", "network")
    sweep(channel, project, record_path(project))
    prepared = prepare_launch(project, RunFlags(memory="6g", save=True), interactive=True,
                              input_stream=io.StringIO("a\n"), output_stream=io.StringIO())
    assert "network" not in prepared.selected.checkout.get("authorization", {})
    assert "network" not in load_toml(record_path(project)).get("authorization", {})
    assert load_toml(record_path(project))["configuration"]["values"]["memory"] == "6GiB"


def test_console_set_during_run_preserves_other_staged_values(project, tmp_path):
    assert config(project, "ide", "python-ide") == 0
    assert cli.main(["home", "trust", "accept", "devcapsule-base", "--yes"]) == 0
    channel = tmp_path / "channel"
    channel.mkdir()
    # A command retained at shutdown is confirmed during the next launch.
    path = request(channel, "000001-set", "set", "cpus", "2")
    handle_request(project, record_path(project), path, stopping=True)
    prepared = prepare_launch(project, RunFlags(memory="6g", save=True), interactive=True,
                              input_stream=io.StringIO("a\n"), output_stream=io.StringIO())
    assert prepared.selected.checkout["configuration"]["values"] == {"memory": "6GiB", "cpus": 2}
    assert load_toml(record_path(project))["configuration"]["values"] == {"memory": "6GiB", "cpus": 2}


@pytest.mark.parametrize("arguments", [
    ["add", "claude-code-agent"], ["omit", "browser-automation"],
    ["restore", "browser-automation"], ["use", "frontend-ide", "codium"],
])
def test_capability_requests_apply_without_host_confirmation(arguments):
    assert classify(arguments) == (Disposition.APPLY, "")


@pytest.mark.parametrize("arguments", [["agent", "add", "codex"], ["tool", "omit", "browser-automation"]])
def test_deleted_channel_verbs_are_refused(arguments):
    assert classify(arguments)[0] is Disposition.REFUSE
