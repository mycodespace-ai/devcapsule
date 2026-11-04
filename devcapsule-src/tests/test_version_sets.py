"""Real CLI/configuration/acquisition/materialization paths; Docker/GUI are controlled.

The unrelated widget component exercises the same engine as the real npm
Codex adapter. Launch assertions inspect independently built formation labels.
"""
from __future__ import annotations

from tests.launch_preparation import run_until_prepared

import base64
from copy import deepcopy
import hashlib
import io
import json
import os
import shutil
import tomllib
from pathlib import Path
import tarfile
from types import SimpleNamespace

import pytest

from devcapsule import cli, version_sets
from devcapsule.compat import CliError
from devcapsule.components.catalog import COMPONENTS
from devcapsule.components.channels import ChannelReport, ChannelSelection, ChannelVersion
from devcapsule.components.codex import CodexComponent
from devcapsule.components.interface import LockedArtifactDeclaration, AcquisitionContract
from devcapsule.components.npm_channel import NpmChannel
from devcapsule.configuration.file_formats import canonical_digest, render_toml
from devcapsule.configuration.execution import ExecutionConfiguration
from devcapsule.configuration.storage import load_toml, lock_for, manifest_for
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate
from devcapsule.materialization import ImageDetails, cache_root
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

pytestmark = pytest.mark.legacy


def invoke(project, *args):
    return cli.main(["project", "--path", str(project), *map(str, args)])


def archive(path, members):
    with tarfile.open(path, "w:gz") as stream:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o755
            stream.addfile(info, io.BytesIO(data))
    return path


class Widget(CodexComponent):
    id = "widget"
    capability = "widget-tool"

    def runtime_template(self):
        return ComponentRuntimeTemplate.from_mapping({"version": 1, "component": {
            "id": self.id, "adapter": "ancillary", "configuration": {},
            "persistence": {"home": "required", "xdg": "home-relative", "state_slots": []}}})

    def state_environment(self):
        return ()

    def state_seeds(self):
        return ()

    def secret_inputs(self):
        return ()

    def locked_artifacts(self, metadata, platform):
        return (LockedArtifactDeclaration(self.id, metadata["version"], metadata["url"], metadata["sha256"],
                                         "/opt/widget/" + metadata["version"], artifact_format="file"),)


@pytest.fixture(params=["widget", "codex"])
def journey(tmp_path, monkeypatch, request):
    from devcapsule.components.discovery import JetBrainsDiscovery
    monkeypatch.setattr(JetBrainsDiscovery, "check", lambda self, current, platform:
                        ChannelReport(self.source, ChannelVersion(current, "available"), ()))
    def status_unavailable(*args, **kwargs):
        raise OSError("fixture status service offline")
    monkeypatch.setattr("devcapsule.component_status.read_metadata", status_unavailable)
    licensed = request.param == "licensed-widget"
    component = "widget" if licensed else request.param
    for key, name in (("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache"),
                      ("XDG_STATE_HOME", "state"), ("XDG_DATA_HOME", "data"), ("HOME", "home")):
        monkeypatch.setenv(key, str(tmp_path / name))
    root = tmp_path / "project"
    config = root / ".devcapsule"
    config.mkdir(parents=True)
    manifest = {"devcapsule-schema-version": 1, "project": {"creator": "mailto:unit@example.test", "slug": "upgrade", "name": "Upgrade fixture", "mount": "/workspace/project"},
                "capabilities": {"need": ["python", "python-ide", "codex-agent"]}}
    (config / "devcapsule.toml").write_text(render_toml(manifest))
    lock = tomllib.loads(MATRICES[Platform.current()].resolve(manifest["capabilities"]["need"], allow_unverified=True).render_lock())
    ide = archive(tmp_path / "ide.tgz", {"ide/bin/pycharm.sh": b"#!/bin/sh\nexit 0\n"})
    lock["components"]["pycharm"].update(url=ide.as_uri(), sha256=hashlib.sha256(ide.read_bytes()).hexdigest())
    metadata = {}
    for version in ("1.0.0", "2.0.0", "3.0.0"):
        if component == "widget":
            payload = tmp_path / f"widget-{version}"
            payload.write_bytes(version.encode())
            metadata[version] = {"version": version, "url": payload.as_uri(), "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(), "delivery-policy": "local-materialization"}
        else:
            for suffix in ("", "-linux-x64"):
                name = "@openai/codex"
                data = {"name": name, "version": version + suffix, "engines": {"node": ">=16"}}
                if suffix:
                    data.update(os=["linux"], cpu=["x64"])
                if not suffix:
                    data["optionalDependencies"] = {"@openai/codex-linux-x64": f"npm:@openai/codex@{version}-linux-x64"}
                payload = archive(tmp_path / f"codex-{version}{suffix}.tgz", {"package/package.json": json.dumps(data).encode()})
                data["dist"] = {"tarball": "https://registry.npmjs.org/@openai/codex/-/" + payload.name,
                                "integrity": "sha512-" + base64.b64encode(hashlib.sha512(payload.read_bytes()).digest()).decode()}
                metadata[version + suffix] = data
    if component == "widget":
        class Channel:
            def check(self, current, platform):
                return ChannelReport("fixture distribution", ChannelVersion(current, "available"), (ChannelVersion("2.0.0", "available"),))
            def select(self, version, platform):
                return ChannelSelection(metadata[version], (platform,))
        definition = Widget()
        if licensed:
            monkeypatch.setattr(definition, "acquisition", lambda: AcquisitionContract("widget-acquisition", "https://example.test/terms", "Widget", "Example"))
            for item in metadata.values():
                item.update({"acquisition-authorization": "widget-acquisition", "terms-url": "https://example.test/terms"})
        monkeypatch.setattr(definition, "distribution_channel", lambda: Channel())
        monkeypatch.setitem(COMPONENTS, "widget", definition)
        lock["components"].pop("codex")
        lock["components"][component] = deepcopy(metadata["1.0.0"])
    else:
        def fetch(self, version=""):
            if not version:
                return {"dist-tags": {"latest": "2.0.0"}, "versions": deepcopy(metadata)}
            return deepcopy(metadata["2.0.0" if version == "latest" else version])
        monkeypatch.setattr(NpmChannel, "_metadata", fetch)
        from urllib.request import urlopen as real_open
        def open_payload(url, **kwargs):
            return real_open((tmp_path / url.rsplit("/", 1)[1]).as_uri(), **kwargs)
        monkeypatch.setattr("devcapsule.materialization.urlopen", open_payload)
        lock["components"][component] = dict(COMPONENTS[component].distribution_channel().select("1.0.0", "linux-amd64").metadata)
        version_sets._pin_artifacts(lock["components"][component])
    path = config / "devcapsule.linux-amd64.lock"
    path.write_text(render_toml(lock))
    assert invoke(root, "config", "authorize", "base-image", "default") == 0
    if licensed:
        assert invoke(root, "config", "authorize", "widget-acquisition", "true") == 0
    assert invoke(root, "config", "authorize", "host-x11", "false") == 0
    assert run_until_prepared(root) == 0
    selected = ExecutionConfiguration.load(root).project
    runtime = tmp_path / "runtime.pex"
    runtime.write_bytes(b"fixture-runtime")
    monkeypatch.setattr("devcapsule.environment_realization.runtime_artifact", lambda _platform: runtime)
    monkeypatch.setattr("devcapsule.runtime_artifact.runtime_artifact", lambda _platform: runtime)
    monkeypatch.setattr("devcapsule.materialization.read_pex_build_info", lambda _: SimpleNamespace(
        build_mnemonic="fixture", source_repository="fixture", source_revision="fixture", source_url="fixture"))
    base = ImageDetails(lock["base"]["reference"], "sha256:" + "a" * 64, {
        "devcapsule.image.managed": "true", "devcapsule.metadata.version": "1", "devcapsule.image.kind": "base",
        "devcapsule.base.display": "contained"}, "linux", "amd64")
    images = {base.reference: base}
    state = SimpleNamespace(fail_build=False, exit_code=0, during_run=None, launched=[], built=[], images=images,
                            root=root, record=selected.checkout_path, resolution=selected.resolution_path, component=component,
                            lock=path, original=path.read_bytes(), metadata=metadata, base=base)
    def require(reference, platform=None):
        if reference not in images:
            raise CliError("local image missing")
        return images[reference]
    def build(self, spec, **kwargs):
        if state.fail_build:
            raise CliError("controlled build failure")
        plan = spec.build_plan()
        descriptor = json.loads(dict(plan.labels)["devcapsule.materialization.descriptor"])
        images[plan.image] = ImageDetails(plan.image, "sha256:" + hashlib.sha256(plan.image.encode()).hexdigest(), dict(plan.labels),
            "linux", "amd64", tuple(descriptor["runtime"]["entrypoint"]), tuple(descriptor["runtime"]["command"]))
        state.built.append(descriptor)
    monkeypatch.setattr("devcapsule.environment_realization.ensure_local_image", require)
    monkeypatch.setattr("devcapsule.environment_realization.required_local_image", require)
    monkeypatch.setattr("devcapsule.environment_realization.optional_local_image", images.get)
    monkeypatch.setattr("devcapsule.environment_realization.component_formations", lambda _: ())
    monkeypatch.setattr("devcapsule.images.build.BuildxImageBuilder.build", build)
    def launch(options):
        state.launched.append((options, json.loads(images[options.image].labels["devcapsule.materialization.descriptor"])))
        if state.during_run:
            state.during_run()
        return state.exit_code
    monkeypatch.setattr("devcapsule.commands.project.run_pycharm", launch)
    return state


def preview_select(state, capsys, version="2.0.0", *, select=True):
    capsys.readouterr()
    assert invoke(state.root, "versions", "preview", state.component, version) == 0
    identity = capsys.readouterr().out.split("Preview ", 1)[1].splitlines()[0]
    if select:
        assert invoke(state.root, "versions", "select", identity, "--unvalidated") == 0
    return identity


def launched_version(state):
    return next(c["version"] for c in state.launched[-1][1]["components"] if c["id"] == state.component)


def test_upgrade_failure_rollback_and_repeated_recovery_use_real_launch(journey, capsys):
    s = journey
    assert invoke(s.root, "config", "authorize", "docker-daemon", "host-socket") == 0
    assert run_until_prepared(s.root) == 0
    assert invoke(s.root, "run") == 0
    a = s.launched[-1][1]
    preview_select(s, capsys)
    assert s.lock.read_bytes() == s.original
    s.exit_code = 17
    assert invoke(s.root, "run") == 17
    assert launched_version(s) == "2.0.0"
    assert len(list((version_sets.state_directory(s.root) / "known-good").glob("*"))) == 1
    assert invoke(s.root, "config", "authorize", "docker-daemon", "none") == 0
    # Rollback resolves current permissions; it must not restore A's old grant.
    assert invoke(s.root, "versions", "rollback") == 0
    s.exit_code = 0
    assert invoke(s.root, "run") == 0
    assert s.launched[-1][1] == a
    assert s.launched[-1][0].docker_mode.value == "none"
    saved_a = version_sets.set_id(ExecutionConfiguration.load(s.root).project.lock)
    assert invoke(s.root, "versions", "rollback", saved_a) == 0
    assert invoke(s.root, "run") == 0
    assert s.launched[-1][1] == a
    assert s.lock.read_bytes() == s.original


def test_failed_and_interrupted_preparation_leave_old_choice(journey, capsys, monkeypatch):
    s = journey
    assert invoke(s.root, "run") == 0
    before = (s.record.read_bytes(), s.resolution.read_bytes())
    identity = preview_select(s, capsys, select=False)
    s.fail_build = True
    assert invoke(s.root, "versions", "select", identity, "--unvalidated") == 2
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before
    s.fail_build = False
    import devcapsule.configuration.storage as storage
    write = storage.atomic_write
    def interrupt(path, content, mode=0o600):
        if path == s.record:
            raise KeyboardInterrupt()
        write(path, content, mode)
    monkeypatch.setattr(storage, "atomic_write", interrupt)
    with pytest.raises(KeyboardInterrupt):
        invoke(s.root, "versions", "select", identity, "--unvalidated")
    monkeypatch.setattr(storage, "atomic_write", write)
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "1.0.0"
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before


def test_old_session_certifies_only_launched_set(journey, capsys):
    s = journey
    before = s.record.read_bytes()
    s.during_run = lambda: preview_select(s, capsys)
    assert invoke(s.root, "run") == 0
    s.during_run = None
    assert ExecutionConfiguration.load(s.root).project.lock["components"][s.component]["version"] == "2.0.0"
    entries = version_sets._known(version_sets.Workspace.load(s.root))
    assert len(entries) == 1 and entries[0][1]["components"][s.component]["version"] == "1.0.0"
    snapshots = list((Path(os.environ['XDG_STATE_HOME']) / "devcapsule/config-history").rglob("devcapsule.checkout.toml"))
    assert len(snapshots) == 1 and snapshots[0].read_bytes() == before
    assert invoke(s.root, "versions", "rollback") == 0
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "1.0.0"


def test_divergence_proposal_follow_and_offline_reminders(journey, capsys, monkeypatch, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    assert invoke(s.root, "versions", "check") == 0
    assert invoke(s.root, "versions", "dismiss") == 0
    assert version_sets.reminder(s.root) == ""
    preview_select(s, capsys)
    assert invoke(s.root, "versions", "propose", tmp_path / "too-early.patch") == 2
    assert invoke(s.root, "run") == 0
    upstream = load_toml(s.lock)
    upstream["components"]["pycharm"]["version"] = "upstream-new"
    s.lock.write_text(render_toml(upstream))
    assert invoke(s.root, "versions", "show") == 0
    assert "changed since selection" in capsys.readouterr().out
    assert invoke(s.root, "run") == 0
    assert s.launched[-1][1]["components"][0]["version"] != "upstream-new"
    patch = tmp_path / "upstream.patch"
    assert invoke(s.root, "versions", "propose", patch) == 0
    assert "Local zero-exit" in patch.read_text() and '"version" = "2.0.0"' in patch.read_text()
    assert invoke(s.root, "versions", "follow-project") == 0
    assert "version-set" in load_toml(s.record)
    assert invoke(s.root, "versions", "follow-project", "--apply") == 0
    assert invoke(s.root, "run") == 0
    assert s.launched[-1][1]["components"][0]["version"] == "upstream-new"
    # Returning to an unchanged recommendation is fully operational.
    s.lock.write_bytes(s.original)
    assert invoke(s.root, "versions", "follow-project", "--apply") == 0
    assert "version-set" not in load_toml(s.record)
    assert invoke(s.root, "run") == 0 and launched_version(s) == "1.0.0"


def test_missing_recovery_resources_preserve_current_set(journey, capsys):
    s = journey
    assert invoke(s.root, "run") == 0
    old_image = s.launched[-1][0].image
    preview_select(s, capsys)
    before = s.record.read_bytes()
    del s.images[old_image]
    shutil.rmtree(version_sets.state_directory(s.root) / "artifacts")
    shutil.rmtree(cache_root() / "artifacts")
    assert invoke(s.root, "versions", "rollback") == 2
    assert s.record.read_bytes() == before
    assert "--reacquire" in capsys.readouterr().err
    assert invoke(s.root, "versions", "rollback", "--reacquire") == 0
    assert invoke(s.root, "run") == 0 and launched_version(s) == "1.0.0"


def test_retained_artifacts_rebuild_predecessor_without_vendor_or_cache(journey, capsys, monkeypatch):
    s = journey
    assert invoke(s.root, "run") == 0
    old_image = s.launched[-1][0].image
    before = s.launched[-1][1]
    preview_select(s, capsys)
    del s.images[old_image]
    shutil.rmtree(cache_root() / "artifacts")
    def offline(*args, **kwargs):
        raise AssertionError("Rollback contacted a distribution server")
    monkeypatch.setattr("devcapsule.materialization.urlopen", offline)
    assert invoke(s.root, "versions", "rollback") == 0
    assert invoke(s.root, "run") == 0
    assert s.launched[-1][1] == before


def test_no_predecessor_and_declining_unvalidated_selection_are_nonmutating(journey, capsys):
    s = journey
    before = s.record.read_bytes(), s.resolution.read_bytes()
    assert invoke(s.root, "versions", "rollback") == 2
    assert "No known-good predecessor" in capsys.readouterr().err
    identity = preview_select(s, capsys, select=False)
    assert invoke(s.root, "versions", "select", identity) == 2
    assert not s.built
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before


def test_reminders_defer_new_candidate_and_offline_run(journey, monkeypatch, capsys):
    s = journey
    assert invoke(s.root, "run") == 0
    assert invoke(s.root, "versions", "check") == 0
    now = 2000000000.0
    monkeypatch.setattr(version_sets.time, "time", lambda: now)
    assert s.component + "@2.0.0" in version_sets.reminder(s.root)
    assert version_sets.reminder(s.root) == ""
    now += 7 * 86400 + 1
    assert s.component + "@2.0.0" in version_sets.reminder(s.root)
    assert invoke(s.root, "versions", "dismiss") == 0
    now += 8 * 86400
    assert version_sets.reminder(s.root) == ""
    path = version_sets.state_directory(s.root) / "check.toml"
    saved = load_toml(path)
    saved["candidates"] = [s.component + "@3.0.0"]
    path.write_text(render_toml(saved))
    assert s.component + "@3.0.0" in version_sets.reminder(s.root)
    def offline(*args, **kwargs):
        raise AssertionError("ordinary launch must not check a channel")
    monkeypatch.setattr(COMPONENTS[s.component], "distribution_channel", offline)
    assert invoke(s.root, "run") == 0


def test_committed_activation_recovery_and_personal_state_survive(journey, capsys, monkeypatch, tmp_path):
    s = journey
    home = tmp_path / "personal-state"
    home.mkdir()
    credential = home / "login-fixture"
    credential.write_text("test token must not be copied into selection")
    work = s.root / "work.txt"
    work.write_text("user work")
    assert invoke(s.root, "state", "adopt", "home", "--from", home) == 0
    assert run_until_prepared(s.root) == 0
    assert invoke(s.root, "run") == 0
    identity = preview_select(s, capsys, select=False)
    import devcapsule.configuration.storage as storage
    write = storage.atomic_write
    def interrupt(path, content, mode=0o600):
        write(path, content, mode)
        if path == s.record:
            raise KeyboardInterrupt()
    monkeypatch.setattr(storage, "atomic_write", interrupt)
    with pytest.raises(KeyboardInterrupt):
        invoke(s.root, "versions", "select", identity, "--unvalidated")
    monkeypatch.setattr(storage, "atomic_write", write)
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "2.0.0"
    assert invoke(s.root, "versions", "rollback") == 0
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "1.0.0"
    assert s.launched[-1][0].persistent_home == home
    assert credential.read_text() == "test token must not be copied into selection"
    assert work.read_text() == "user work"
    assert "test token" not in s.record.read_text()


def test_local_base_rollback_uses_recorded_identity_after_tag_moves(journey, capsys, monkeypatch):
    from dataclasses import replace
    s = journey
    old = replace(s.base, reference="local/base:chosen", identity="sha256:" + "b" * 64)
    s.images[old.reference] = old
    s.images[old.identity] = replace(old, reference=old.identity)
    monkeypatch.setattr("devcapsule.commands.project.required_local_image", s.images.__getitem__)
    monkeypatch.setattr("devcapsule.configuration.operations.required_local_image", s.images.__getitem__)
    assert invoke(s.root, "config", "authorize", "base-image", old.reference) == 0
    assert run_until_prepared(s.root) == 0
    assert invoke(s.root, "run") == 0
    preview_select(s, capsys)
    s.images[old.reference] = replace(old, identity="sha256:" + "c" * 64)
    assert invoke(s.root, "versions", "rollback") == 0
    assert invoke(s.root, "run") == 0
    assert s.launched[-1][1]["base"]["identity"] == old.identity
    assert load_toml(s.record)["authorization"]["base-image"]["reference"] == old.identity


def test_declared_companion_constraint_prevents_unrelated_silent_change(journey, monkeypatch, capsys):
    from dataclasses import replace
    s = journey
    channel = COMPONENTS[s.component].distribution_channel()
    original = channel.select
    monkeypatch.setattr(channel, "select", lambda v, p: replace(original(v, p), requires=(("pycharm", "requires-a-different-version"),)))
    monkeypatch.setattr(COMPONENTS[s.component], "distribution_channel", lambda: channel)
    before = s.record.read_bytes()
    assert invoke(s.root, "versions", "preview", s.component, "2.0.0") == 2
    assert "requires pycharm" in capsys.readouterr().err
    assert s.record.read_bytes() == before and not s.built


@pytest.mark.parametrize("journey", ["licensed-widget"], indirect=True)
def test_candidate_acquisition_answers_do_not_renew_host_permissions(journey, capsys):
    s = journey
    assert invoke(s.root, "run") == 0
    identity = preview_select(s, capsys, select=False)
    before = s.record.read_bytes()
    assert invoke(s.root, "versions", "select", identity, "--unvalidated") == 2
    assert s.record.read_bytes() == before
    assert invoke(s.root, "versions", "select", identity, "--unvalidated", "--authorize", "docker-daemon", "host-socket") == 2
    assert s.record.read_bytes() == before
    assert invoke(s.root, "versions", "select", identity, "--unvalidated", "--authorize", "widget-acquisition", "true") == 0
    assert invoke(s.root, "run") == 0 and launched_version(s) == "2.0.0"
    assert invoke(s.root, "config", "authorize", "widget-acquisition", "false") == 0
    assert invoke(s.root, "versions", "rollback") == 2
    assert load_toml(s.record)["authorization"]["widget-acquisition"]["value"] is False
    assert invoke(s.root, "versions", "rollback", "--authorize", "widget-acquisition", "true") == 0
    assert invoke(s.root, "run") == 0 and launched_version(s) == "1.0.0"
    upstream = load_toml(s.lock)
    upstream["components"]["widget"] = s.metadata["3.0.0"]
    s.lock.write_text(render_toml(upstream))
    assert invoke(s.root, "versions", "follow-project", "--apply") == 2
    assert invoke(s.root, "versions", "follow-project", "--apply", "--authorize", "widget-acquisition", "true") == 0
    assert invoke(s.root, "run") == 0 and launched_version(s) == "3.0.0"
    assert s.launched[-1][0].docker_mode.value == "none"


class TerminalInput(io.StringIO):
    def isatty(self):
        return True


def critical_channel(s, monkeypatch, *, kind="security", candidates=True):
    """An upstream fact, independent of the launch prompt implementation."""
    from devcapsule.components.channels import ChannelNotice
    original = COMPONENTS[s.component].distribution_channel()
    calls = []
    class Channel:
        def check(self, current, platform):
            calls.append((current, platform))
            notices = (ChannelNotice("vendor-issue-123", kind, "Vendor requires an upgrade of this version"),) if current == "1.0.0" else ()
            return ChannelReport("https://vendor.example/advisory/123", ChannelVersion(current, "unsupported", notices=notices),
                                 (ChannelVersion("2.0.0", "available"),) if candidates else ())
        def select(self, version, platform):
            return original.select(version, platform)
    monkeypatch.setattr(COMPONENTS[s.component], "distribution_channel", lambda: Channel())
    return calls


def test_critical_prompt_upgrades_same_launch_and_preserves_recovery(journey, monkeypatch, capsys):
    s = journey
    assert invoke(s.root, "run") == 0
    old = s.launched[-1][1]
    calls = critical_channel(s, monkeypatch)
    monkeypatch.setattr("sys.stdin", TerminalInput("upgrade\nyes\n"))
    assert invoke(s.root, "run") == 0
    assert calls == [("1.0.0", "linux-amd64")]
    assert launched_version(s) == "2.0.0"
    assert s.lock.read_bytes() == s.original
    out = capsys.readouterr().out
    assert "Security notice" in out and "Source: https://vendor.example/advisory/123" in out
    assert "Not yet validated:" in out
    assert "Prepare and launch this exact version set" in out
    known = version_sets.Workspace.load(s.root)
    assert (known.state / "known-good" / f"{known.identity}.toml").is_file()
    assert invoke(s.root, "versions", "rollback") == 0
    monkeypatch.setattr("sys.stdin", TerminalInput("later\n"))
    assert invoke(s.root, "run", "--no-update-check") == 0
    assert s.launched[-1][1] == old


@pytest.mark.parametrize("answer,days,due", [("later", 6, False), ("later", 8, True), ("keep", 8, False)])
def test_critical_decisions_remembered_across_launches(journey, monkeypatch, capsys, answer, days, due):
    s = journey
    critical_channel(s, monkeypatch, kind="end-of-support")
    now = 2000000000.0
    monkeypatch.setattr(version_sets.time, "time", lambda: now)
    monkeypatch.setattr("sys.stdin", TerminalInput(answer + "\n"))
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "1.0.0"
    assert "End-of-support" in capsys.readouterr().out
    now += days * 86400
    monkeypatch.setattr("sys.stdin", TerminalInput("later\n"))
    assert invoke(s.root, "run") == 0
    assert ("Choose upgrade" in capsys.readouterr().out) == due


@pytest.mark.parametrize("answer,exit_code", [("upgrade\nno\n", 0), ("upgrade\n\n", 0), ("stop\n", 1), ("", 1), ("upgrade\n", 1)])
def test_critical_decline_stop_and_eof_never_select(journey, monkeypatch, answer, exit_code):
    s = journey
    critical_channel(s, monkeypatch)
    before = s.record.read_bytes(), s.resolution.read_bytes()
    monkeypatch.setattr("sys.stdin", TerminalInput(answer))
    assert invoke(s.root, "run") == exit_code
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before
    if exit_code:
        assert not s.launched and not s.built
    else:
        assert launched_version(s) == "1.0.0"


def test_noninteractive_and_skip_check_never_query_channels(journey, monkeypatch, capsys):
    s = journey
    calls = critical_channel(s, monkeypatch)
    monkeypatch.setattr("sys.stdin", io.StringIO("upgrade\nyes\n"))
    assert invoke(s.root, "run") == 0
    assert not calls
    assert invoke(s.root, "versions", "check") == 0
    assert len(calls) == 1
    assert invoke(s.root, "run") == 0
    assert len(calls) == 1 and launched_version(s) == "1.0.0"
    assert "No interactive decision is possible" in capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", TerminalInput("upgrade\nyes\n"))
    assert invoke(s.root, "run", "--no-update-check") == 0
    assert len(calls) == 1 and launched_version(s) == "2.0.0"


def test_daily_refresh_and_unavailable_check_preserve_cached_notice(journey, monkeypatch, capsys):
    s = journey
    now = 2000000000.0
    monkeypatch.setattr(version_sets.time, "time", lambda: now)
    calls = critical_channel(s, monkeypatch)
    assert invoke(s.root, "versions", "check") == 0
    assert len(calls) == 1
    monkeypatch.setattr("sys.stdin", TerminalInput("stop\n"))
    assert invoke(s.root, "run") == 1
    assert len(calls) == 1
    now += 86401
    def offline(*args):
        calls.append("offline")
        raise CliError("network offline")
    channel = COMPONENTS[s.component].distribution_channel()
    monkeypatch.setattr(channel, "check", offline)
    monkeypatch.setattr(COMPONENTS[s.component], "distribution_channel", lambda: channel)
    monkeypatch.setattr("sys.stdin", TerminalInput("later\n"))
    assert invoke(s.root, "run") == 0
    assert len(calls) == 2
    out = capsys.readouterr().out
    assert "network offline" in out and "Security notice" in out
    assert "2033-05-18" in out  # The original check time, not the failed refresh.
    assert invoke(s.root, "run") == 0
    assert len(calls) == 2


def test_no_replacement_is_disclosed_and_launch_can_be_stopped(journey, monkeypatch, capsys):
    s = journey
    critical_channel(s, monkeypatch, candidates=False)
    monkeypatch.setattr("sys.stdin", TerminalInput("stop\n"))
    assert invoke(s.root, "run") == 1
    assert "No available replacement" in capsys.readouterr().out
    assert not s.launched


def test_failed_critical_upgrade_requires_decision_to_continue(journey, monkeypatch, capsys):
    s = journey
    assert invoke(s.root, "run") == 0  # Retained usable baseline.
    critical_channel(s, monkeypatch)
    s.fail_build = True
    monkeypatch.setattr("sys.stdin", TerminalInput("upgrade\nyes\nyes\n"))
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "1.0.0"
    assert "Upgrade could not finish" in capsys.readouterr().out
    assert s.lock.read_bytes() == s.original


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_real_npm_deprecation_drives_launch_prompt(journey, monkeypatch, capsys):
    s = journey
    s.metadata["1.0.0"]["deprecated"] = "This release is no longer maintained"
    monkeypatch.setattr("sys.stdin", TerminalInput("upgrade\nyes\n"))
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "2.0.0"
    assert "This release is no longer maintained" in capsys.readouterr().out


@pytest.mark.parametrize("journey", ["licensed-widget"], indirect=True)
@pytest.mark.parametrize("consent,version", [("yes", "2.0.0"), ("no", "1.0.0")])
def test_guided_upgrade_separately_elicits_changed_terms(journey, monkeypatch, capsys, consent, version):
    s = journey
    critical_channel(s, monkeypatch)
    monkeypatch.setattr("sys.stdin", TerminalInput(f"upgrade\nyes\n{consent}\nyes\n"))
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == version
    out = capsys.readouterr().out
    assert "https://example.test/terms" in out
    assert "Widget 2.0.0" in out
    assert "Authorize this candidate acquisition?" in out
    assert s.launched[-1][0].docker_mode.value == "none"
    assert s.lock.read_bytes() == s.original


def test_routine_dismissal_does_not_hide_new_critical_notice(journey, monkeypatch, capsys):
    s = journey
    assert invoke(s.root, "versions", "check") == 0
    assert invoke(s.root, "versions", "dismiss") == 0
    critical_channel(s, monkeypatch)
    assert invoke(s.root, "versions", "check") == 0
    monkeypatch.setattr("sys.stdin", TerminalInput("keep\n"))
    assert invoke(s.root, "run") == 0
    assert "Choose upgrade" in capsys.readouterr().out
    assert version_sets.reminder(s.root) == ""  # No second nag after deciding.
    path = version_sets.state_directory(s.root) / "check.toml"
    saved = load_toml(path)
    saved["notices"][0]["identity"] = "new-vendor-issue-456"
    path.write_text(render_toml(saved))
    monkeypatch.setattr("sys.stdin", TerminalInput("stop\n"))
    assert invoke(s.root, "run") == 1
    assert "Choose upgrade" in capsys.readouterr().out


def test_interactive_offline_first_launch_continues_without_assuming_current(journey, monkeypatch, capsys):
    s = journey
    critical_channel(s, monkeypatch)
    channel = COMPONENTS[s.component].distribution_channel()
    def offline(*args):
        raise CliError("offline fixture")
    monkeypatch.setattr(channel, "check", offline)
    monkeypatch.setattr(COMPONENTS[s.component], "distribution_channel", lambda: channel)
    monkeypatch.setattr("sys.stdin", TerminalInput(""))
    assert invoke(s.root, "run") == 0
    assert launched_version(s) == "1.0.0"
    out = capsys.readouterr().out
    assert "check unavailable" in out and "Choose upgrade" not in out


def test_cli_check_uses_maintained_diagnosis_and_preserves_selection_and_last_success(journey, monkeypatch, capsys):
    from datetime import datetime, timedelta, timezone
    from devcapsule.component_status import REPOSITORY
    s = journey
    before = s.record.read_bytes(), s.resolution.read_bytes(), s.lock.read_bytes()
    assert invoke(s.root, "versions", "check") == 0
    capsys.readouterr()
    saved = load_toml(version_sets.state_directory(s.root) / "check.toml")
    success = next(item for item in saved["successful-checks"] if item["component"] == s.component)
    channel = COMPONENTS[s.component].distribution_channel()
    def broken(*args):
        raise KeyError("vendor changed its schema")
    monkeypatch.setattr(channel, "check", broken)
    monkeypatch.setattr(COMPONENTS[s.component], "distribution_channel", lambda: channel)
    now = datetime.now(timezone.utc)
    feed = {"format": 1, "generated_at": now.isoformat(), "expires_at": (now + timedelta(days=2)).isoformat(),
            "advisories": [{"id": "fixture", "component": s.component,
                            "adapters": [COMPONENTS[s.component].discovery_adapter_id()], "cli_versions": ["*"],
                            "platforms": ["linux-amd64"], "status": "cli-update-required", "fixed_in": "0.2.15",
                            "message": "A reviewed fix restores discovery.", "issue_url": REPOSITORY + "/issues/123",
                            "reviewed_at": now.isoformat(), "expires_at": (now + timedelta(days=30)).isoformat()}]}
    monkeypatch.setattr("devcapsule.component_status.read_metadata", lambda *a, **k: json.dumps(feed).encode())
    assert invoke(s.root, "versions", "check") == 0
    output = capsys.readouterr().out
    assert "check unavailable" in output and "Update DevCapsule to 0.2.15" in output
    assert "Last successful check:" in output and "historical, not current" in output
    assert "2.0.0" in output and "/issues/123" in output
    saved = load_toml(version_sets.state_directory(s.root) / "check.toml")
    assert next(item for item in saved["successful-checks"] if item["component"] == s.component) == success
    assert before == (s.record.read_bytes(), s.resolution.read_bytes(), s.lock.read_bytes())


def test_discovery_only_candidate_does_not_offer_an_unimplemented_upgrade(journey, monkeypatch, capsys):
    from devcapsule.components.discovery import JetBrainsDiscovery
    monkeypatch.setattr(JetBrainsDiscovery, "check", lambda self, current, platform:
                        ChannelReport(self.source, ChannelVersion(current, "unknown"),
                                      (ChannelVersion("2026.2.3", "available"),)))
    assert invoke(journey.root, "versions", "check") == 0
    output = capsys.readouterr().out
    assert "Candidate 2026.2.3" in output and "Discovery only" in output
    assert "pycharm@2026.2.3" not in version_sets.reminder(journey.root)


def runtime_view(s, monkeypatch, tmp_path):
    """Model the two read-only mounts and a different in-container project path."""
    from devcapsule import runtime_configuration
    snapshot = deepcopy(s.launched[-1][0].launch_configuration.document)
    runtime_root = tmp_path / "inside" / "project"
    shutil.copytree(s.root, runtime_root)
    snapshot["runtime-root"] = str(runtime_root)
    context = tmp_path / "launch-context.json"
    context.write_text(json.dumps(snapshot))
    monkeypatch.setattr(runtime_configuration, "CONTEXT_PATH", context)
    monkeypatch.setattr(runtime_configuration, "CONFIGURATION_PATH", s.record.parent)
    monkeypatch.setattr(runtime_configuration, "CHANNEL_PATH", tmp_path / "absent-channel")
    monkeypatch.setenv("PROJECT_PATH", str(runtime_root))
    monkeypatch.setenv("DEVCAPSULE_CONTAINER_NAME", "runtime-fixture")
    return runtime_root, snapshot, context


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_runtime_info_from_anywhere_preserves_launch_facts_and_explicit_paths(journey, monkeypatch, capsys, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, snapshot, _ = runtime_view(s, monkeypatch, tmp_path)
    preview_select(s, capsys)
    monkeypatch.setenv("OPENAI_API_KEY", "never-disclose-this-value")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-runtime-config"))
    before = s.record.read_bytes(), s.resolution.read_bytes()
    capsys.readouterr()
    outside = tmp_path / "opt"
    outside.mkdir()
    monkeypatch.chdir(outside)
    assert cli.main(["project", "info", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["components"][s.component] == "1.0.0"
    assert report["next-launch-components"][s.component] == "2.0.0"
    assert report["selection-changed"]
    assert report["persistence"] == snapshot["info"]["persistence"]
    assert "never-disclose-this-value" not in json.dumps(report)
    assert invoke(runtime_root, "info", "--json") == 0
    assert json.loads(capsys.readouterr().out) == report
    # An explicit unrelated path must not silently select the hosting capsule.
    assert invoke(outside, "info") == 2
    capsys.readouterr()
    nested = runtime_root / "nested"
    shutil.copytree(s.root, nested)
    monkeypatch.chdir(nested)
    assert cli.main(["project", "info", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["context"] == "host selection (next launch)"
    assert not (tmp_path / "empty-runtime-config").exists()
    journal = s.record.with_suffix(".activation.toml")
    journal.write_text('"unfinished" = true\n')
    assert invoke(runtime_root, "info", "--json") == 0
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["components"][s.component] == "1.0.0"
    assert "never repairs" in blocked["next-launch-unavailable"]
    assert journal.read_text() == '"unfinished" = true\n'
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before


def show_document(project, capsys):
    capsys.readouterr()
    assert invoke(project, "versions", "show", "--json") == 0
    return json.loads(capsys.readouterr().out)


def test_show_json_reports_the_host_selection_and_agrees_with_the_text(journey, capsys):
    """``versions show --json`` is the contract the web console reads; the
    text report is rendered from the same document."""
    s = journey
    document = show_document(s.root, capsys)
    workspace = version_sets.Workspace.load(s.root)
    assert document["schema-version"] == 1
    assert document["context"] == "host selection (next launch)"
    assert document["selected"]["identity"] == workspace.identity
    assert document["selected"]["origin"] == "project recommendation"
    assert document["selected"]["components"][s.component] == "1.0.0"
    assert document["selected"]["local-base-override"] is None
    assert document["project-recommendation"] is None
    assert document["local-use"] == {"zero-exit-launch-recorded": False}
    assert set(document["validation"]) == {"evidence", "not-yet-validated"}
    assert invoke(s.root, "run") == 0
    assert show_document(s.root, capsys)["local-use"] == {"zero-exit-launch-recorded": True}
    preview_select(s, capsys)
    document = show_document(s.root, capsys)
    assert document["selected"]["origin"] == "local selection"
    assert document["selected"]["components"][s.component] == "2.0.0"
    assert document["project-recommendation"] == {"status": "unchanged", "detail": None}
    assert document["local-use"] == {"zero-exit-launch-recorded": False}
    upstream = load_toml(s.lock)
    upstream["components"]["pycharm"]["version"] = "upstream-new"
    s.lock.write_text(render_toml(upstream))
    document = show_document(s.root, capsys)
    assert document["project-recommendation"]["status"] == "changed"
    assert invoke(s.root, "versions", "show") == 0
    text = capsys.readouterr().out
    assert f"Version set {document['selected']['identity']}" in text
    assert "changed since selection" in text
    for name, version in document["selected"]["components"].items():
        assert f"{name}: {version}" in text


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_show_json_keeps_local_selection_when_recommendation_is_unavailable(journey, capsys):
    s = journey
    preview_select(s, capsys)
    identity = version_sets.Workspace.load(s.root).identity
    s.lock.unlink()
    document = show_document(s.root, capsys)
    assert document["selected"]["identity"] == identity
    assert document["selected"]["origin"] == "local selection"
    recommendation = document["project-recommendation"]
    assert recommendation["status"] == "unavailable"
    assert str(s.lock) in recommendation["detail"]
    assert invoke(s.root, "versions", "show") == 0
    assert f"Project recommendation unavailable: {recommendation['detail']}; local selection remains intact." in capsys.readouterr().out


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_show_json_and_text_preserve_local_base_and_validation(journey, monkeypatch, capsys):
    from dataclasses import replace

    s = journey
    local = replace(s.base, reference="local/base:chosen", identity="sha256:" + "b" * 64)
    monkeypatch.setattr("devcapsule.commands.project.required_local_image", lambda _: local)
    monkeypatch.setattr("devcapsule.configuration.operations.required_local_image", lambda _: local)
    assert invoke(s.root, "config", "authorize", "base-image", local.reference) == 0
    document = show_document(s.root, capsys)
    selected = document["selected"]
    assert selected["base"] == load_toml(s.lock)["base"]
    assert selected["local-base-override"] == local.identity
    missing = [f"{name} {version} on local base {local.identity}" for name, version in selected["components"].items()]
    assert document["validation"] == {"evidence": [], "not-yet-validated": missing}
    assert invoke(s.root, "versions", "show") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[:5] == [
        f"Version set {selected['identity']}", "Origin: project recommendation",
        f"Platform: {selected['platform']}", f"Base: {selected['base']}",
        f"Effective local base override: {local.identity} (project base above is a recommendation).",
    ]
    assert lines[5:5 + len(selected["components"])] == [
        f"{name}: {version}" for name, version in selected["components"].items()]
    assert [line for line in lines if line.startswith("Not yet validated: ")] == [
        f"Not yet validated: {item}" for item in missing]


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
@pytest.mark.parametrize("legacy_context", [False, True])
def test_runtime_json_reports_running_and_next_launch_sets(journey, monkeypatch, capsys, tmp_path, legacy_context):
    s = journey
    assert invoke(s.root, "run") == 0
    running_id = version_sets.Workspace.load(s.root).identity
    runtime_root, snapshot, context_path = runtime_view(s, monkeypatch, tmp_path)
    if legacy_context:
        snapshot.pop("checkout-name")
        context_path.write_text(json.dumps(snapshot))
    document = show_document(runtime_root, capsys)
    assert document["context"] == "running capsule"
    assert document["running"]["identity"] == running_id
    assert document["running"]["origin"] == "project recommendation"
    assert document["running"]["components"][s.component] == "1.0.0"
    assert document["next-launch"]["identity"] == running_id
    assert document["selection-changed"] is False
    assert document["launcher-command"].endswith("versions show") and str(s.root) in document["launcher-command"]
    preview_select(s, capsys)
    next_id = version_sets.Workspace.load(s.root).identity
    document = show_document(runtime_root, capsys)
    assert document["running"]["identity"] == running_id
    assert document["next-launch"]["identity"] == next_id
    assert document["next-launch"]["origin"] == "local selection"
    assert document["next-launch"]["components"][s.component] == "2.0.0"
    assert document["selection-changed"] is True
    # The configuration listing is the mounted record, without the selection.
    assert invoke(runtime_root, "config", "show", "--json") == 0
    listing = json.loads(capsys.readouterr().out)
    assert listing["schema-version"] == 1
    assert listing["context"] == "running capsule (next launch, read-only)"
    assert listing["project"] == {"creator": "mailto:unit@example.test", "slug": "upgrade"}
    assert listing["checkout"]["name"] == "default"
    assert listing["checkout"]["launcher-path"] == str(s.root)
    assert listing["checkout"]["runtime-path"] == str(runtime_root)
    assert "version-set" not in listing["checkout"]["record"]
    assert listing["checkout"]["record"]["checkout"]["path"] == str(s.root)
    assert "rows" not in listing
    assert listing["launcher-command"].endswith("config show") and str(s.root) in listing["launcher-command"]
    assert invoke(runtime_root, "config", "show") == 0
    text = capsys.readouterr().out
    record_text = text.split("\n\n", 1)[1].split("\nTo change configuration", 1)[0]
    assert tomllib.loads(record_text) == listing["checkout"]["record"]
    # A launcher activation in progress leaves the running facts intact.
    journal = s.record.with_suffix(".activation.toml")
    journal.write_text('"unfinished" = true\n')
    document = show_document(runtime_root, capsys)
    assert document["running"]["identity"] == running_id
    assert document["next-launch"] is None and document["selection-changed"] is None
    assert "never repairs" in document["next-launch-unavailable"]
    assert invoke(runtime_root, "versions", "show") == 0
    assert "Next-launch selection unavailable" in capsys.readouterr().out


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_runtime_show_preserves_running_set_when_next_identity_is_invalid(journey, monkeypatch, capsys, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, snapshot, _ = runtime_view(s, monkeypatch, tmp_path)
    # Valid TOML can still contain a scalar the version-set digest cannot encode.
    record = load_toml(s.record)
    record["version-set"] = {
        "format": 1,
        "lock": s.lock.read_text() + '\n[components.codex.metadata]\nbuilt = 2026-10-09T12:00:00Z\n',
        "recommendation-digest": canonical_digest(load_toml(s.lock)),
    }
    s.record.write_text(render_toml(record))
    before = s.record.read_bytes(), s.resolution.read_bytes()
    capsys.readouterr()
    assert invoke(runtime_root, "versions", "show") == 0
    text = capsys.readouterr().out
    assert f"Running session — version set {snapshot['running']['identity']}" in text
    assert "Next-launch selection unavailable: Configuration contains an unsupported scalar representation." in text
    assert "Selected for next launch" not in text
    document = show_document(runtime_root, capsys)
    assert document["running"]["identity"] == snapshot["running"]["identity"]
    assert document["next-launch"] is None
    assert document["selection-changed"] is None
    assert document["next-launch-unavailable"] == "Configuration contains an unsupported scalar representation."
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before


def test_runtime_show_tracks_running_and_next_sets_without_local_registration(journey, monkeypatch, capsys, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    running_id = version_sets.Workspace.load(s.root).identity
    runtime_root, snapshot, _ = runtime_view(s, monkeypatch, tmp_path)
    # A different root remains a launcher, even inside a capsule (nested use).
    preview_select(s, capsys)
    next_id = version_sets.Workspace.load(s.root).identity
    assert next_id != running_id
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-runtime-config"))
    before = s.record.read_bytes(), s.resolution.read_bytes()
    assert invoke(runtime_root, "versions", "show") == 0
    out = capsys.readouterr().out
    assert f"Running session — version set {running_id}" in out
    assert f"Selected for next launch — version set {next_id}" in out
    assert f"{s.component}: 1.0.0" in out and f"{s.component}: 2.0.0" in out
    assert "Selection has changed" in out
    assert str(s.root) in out  # Launcher remedy uses host identity, not runtime path.
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before
    assert not (tmp_path / "empty-runtime-config").exists()
    assert snapshot["running"]["lock"]["components"][s.component]["version"] == "1.0.0"
    # A directory mount follows atomic replacement; an individual file mount
    # would keep the old inode and continue reporting B here.
    from devcapsule.configuration.storage import atomic_write
    current = load_toml(s.record)
    current.pop("version-set")
    atomic_write(s.record, render_toml(current))
    assert invoke(runtime_root, "versions", "show") == 0
    out = capsys.readouterr().out
    assert f"Selected for next launch — version set {running_id}" in out
    assert f"{s.component}: 2.0.0" not in out


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_runtime_inspection_from_anywhere_selects_the_capsule_project(journey, monkeypatch, capsys, tmp_path):
    """Owner ruling of 2026-10-01: inside a capsule every project subcommand
    finds the capsule's project from any directory; read-only ones answer."""
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, snapshot, context = runtime_view(s, monkeypatch, tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty-runtime-config"))
    before = s.record.read_bytes(), s.resolution.read_bytes()
    outside = tmp_path / "opt"
    outside.mkdir()
    monkeypatch.chdir(outside)
    capsys.readouterr()
    for command in (["config", "show"], ["config", "show"], ["versions", "show"]):
        assert cli.main(["project", *command]) == 0, command
        out = capsys.readouterr().out
        assert ("Runtime context" in out) or ("Running session" in out), command
        assert str(s.root) in out  # the launcher remedy names the host checkout
    # An explicit unrelated path must not silently select the hosting capsule.
    assert invoke(outside, "config", "show") == 2
    assert "No .devcapsule/devcapsule.toml" in capsys.readouterr().err
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before
    assert not (tmp_path / "empty-runtime-config").exists()  # inspection wrote nothing
    # A project nested inside the capsule keeps its own identity: a launcher,
    # which initializes that project's own records as it would on a host.
    nested = runtime_root / "nested"
    shutil.copytree(s.root, nested)
    monkeypatch.chdir(nested)
    assert cli.main(["project", "config", "show"]) == 0
    assert "Runtime context" not in capsys.readouterr().out
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before
    # An older capsule without the mounted context is diagnosed, not guessed.
    context.unlink()
    monkeypatch.chdir(outside)
    assert cli.main(["project", "config", "show"]) == 2
    assert "no launcher configuration mount" in capsys.readouterr().err


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_runtime_mutation_from_anywhere_names_the_launcher(journey, monkeypatch, capsys, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_view(s, monkeypatch, tmp_path)
    before = s.record.read_bytes(), s.resolution.read_bytes(), s.lock.read_bytes()
    outside = tmp_path / "opt"
    outside.mkdir()
    monkeypatch.chdir(outside)
    capsys.readouterr()
    assert cli.main(["project", "config", "set", "anything", "value"]) == 2
    err = capsys.readouterr().err
    assert f"Run outside the capsule: devcapsule project --path {s.root} config set anything value" in err
    assert cli.main(["project", "run"]) == 2
    assert f"devcapsule project --path {s.root} run" in capsys.readouterr().err
    assert (s.record.read_bytes(), s.resolution.read_bytes(), s.lock.read_bytes()) == before


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_runtime_unknown_subcommand_is_unknown_not_launcher_only(journey, monkeypatch, capsys, tmp_path):
    """The 2026-09-26 record: `project --path $PWD bootstrap` inside a capsule
    was refused as launcher-only, and the remedy repeated the unknown name."""
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, _, _ = runtime_view(s, monkeypatch, tmp_path)
    capsys.readouterr()
    for arguments in (["project", "--path", str(runtime_root), "bootstrap"], ["project", "bootstrap"],
                      ["project", "config", "bogus"]):
        monkeypatch.chdir(runtime_root)
        assert cli.main(arguments) == 2, arguments
        err = capsys.readouterr().err
        assert "unknown command" in err and "launcher" not in err, arguments
    # Help for a mutating command is still help, inside the capsule.
    assert invoke(runtime_root, "config", "set", "--help") == 0
    assert "usage:" in capsys.readouterr().out


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_runtime_init_acts_where_it_is_invoked(journey, monkeypatch, tmp_path):
    """`init` creates a project in the working directory and never selects the
    capsule's project; the IDE smoke initializes a disposable project inside
    a capsule this way."""
    import argparse
    from devcapsule.commands.project import ProjectCommand
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, _, _ = runtime_view(s, monkeypatch, tmp_path)
    outside = tmp_path / "opt"
    outside.mkdir()
    monkeypatch.chdir(outside)
    selected = lambda *rest: ProjectCommand.make_context(argparse.Namespace(selected_path=None, rest=list(rest)), None)
    assert selected("init").capsule_root is None
    assert selected("list").capsule_root is None
    assert selected("recursive-e2e", "preflight").capsule_root is None
    assert selected("config", "show").capsule_root == runtime_root
    assert selected("info").capsule_root == runtime_root
    assert selected("config").capsule_root is None  # a bare group prints help


@pytest.mark.parametrize("operation", [
    ("versions", "check"), ("versions", "preview", "codex", "latest"),
    ("versions", "select", "a" * 64), ("versions", "rollback"),
    ("run",), ("config", "authorize", "host-x11", "true"),
    ("config", "set", "anything", "value"), ("init", "--regenerate"), ("run",),
    ("config", "docker-args", "set", "--", "--gpus", "all"), ("config", "docker-args", "list"), ("config", "docker-args", "clear"),
    ("config", "env", "set", "APP_SECRET", "value"), ("config", "env", "unset", "APP_SECRET"), ("config", "env", "list"),
])
@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_runtime_commands_requiring_launcher_are_refused_before_effects(journey, monkeypatch, capsys, tmp_path, operation):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, _, _ = runtime_view(s, monkeypatch, tmp_path)
    before = s.record.read_bytes(), s.resolution.read_bytes(), s.lock.read_bytes()
    assert invoke(runtime_root, *operation) == 2
    err = capsys.readouterr().err
    assert "configuration is read-only" in err and "Run outside the capsule:" in err
    assert str(s.root) in err
    assert (s.record.read_bytes(), s.resolution.read_bytes(), s.lock.read_bytes()) == before
    assert len(s.launched) == 1


def test_runtime_config_list_is_read_only_and_does_not_assess_host_paths(journey, monkeypatch, capsys, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, _, _ = runtime_view(s, monkeypatch, tmp_path)
    checkout = load_toml(s.record)
    checkout.setdefault("configuration", {})["bindings"] = {"host-directory": {"home": "/only/on/the/host"}}
    s.record.write_text(render_toml(checkout))
    before = s.record.read_bytes(), s.resolution.read_bytes()
    assert invoke(runtime_root, "config", "show") == 0
    out = capsys.readouterr().out
    assert "/only/on/the/host" in out
    assert "recorded choices" in out and "not an existing directory" not in out
    assert (s.record.read_bytes(), s.resolution.read_bytes()) == before


def test_runtime_never_repairs_activation_and_keeps_running_snapshot(journey, monkeypatch, capsys, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, snapshot, _ = runtime_view(s, monkeypatch, tmp_path)
    journal = s.record.with_suffix(".activation.toml")
    journal.write_text('"unfinished" = true\n')
    before = s.record.read_bytes(), s.resolution.read_bytes(), journal.read_bytes()
    assert invoke(runtime_root, "versions", "show") == 0
    out = capsys.readouterr().out
    assert snapshot["running"]["identity"] in out
    assert "Next-launch selection unavailable" in out and "never repairs host records" in out
    assert (s.record.read_bytes(), s.resolution.read_bytes(), journal.read_bytes()) == before
    assert invoke(runtime_root, "config", "show") == 2
    assert journal.exists()


def test_older_capsule_gets_relaunch_guidance_not_missing_xdg_file(journey, monkeypatch, capsys, tmp_path):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, _, context = runtime_view(s, monkeypatch, tmp_path)
    context.unlink()
    assert invoke(runtime_root, "versions", "show") == 2
    err = capsys.readouterr().err
    assert "Relaunch this project from outside" in err
    assert "No such file" not in err


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
@pytest.mark.parametrize("mismatch", ["path", "project"])
def test_runtime_rejects_another_checkout_without_hiding_running_versions(journey, monkeypatch, capsys, tmp_path, mismatch):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, _, _ = runtime_view(s, monkeypatch, tmp_path)
    record = load_toml(s.record)
    if mismatch == "path":
        record["checkout"]["path"] = "/another/checkout"
    else:
        record["project"]["slug"] = "another-project"
    s.record.write_text(render_toml(record))
    assert invoke(runtime_root, "versions", "show") == 0
    out = capsys.readouterr().out
    assert "Running session" in out and "does not match this launch" in out
    assert "Selected for next launch" not in out


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
@pytest.mark.parametrize("invalid_name", [5, None, "", "nested/name", "nested\\name"])
def test_runtime_rejects_invalid_checkout_name(journey, monkeypatch, capsys, tmp_path, invalid_name):
    s = journey
    assert invoke(s.root, "run") == 0
    runtime_root, snapshot, context_path = runtime_view(s, monkeypatch, tmp_path)
    snapshot["checkout-name"] = invalid_name
    context_path.write_text(json.dumps(snapshot))
    capsys.readouterr()
    assert invoke(runtime_root, "config", "show", "--json") == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Cannot read runtime launch context: invalid checkout name. Relaunch with the updated launcher." in captured.err


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
@pytest.mark.parametrize("name", ["dogfood", "devcapsule"])
def test_runtime_uses_exact_named_record_and_lists_its_identity(journey, monkeypatch, capsys, tmp_path, name):
    s = journey
    named = s.record.parent / "checkouts" / f"{name}.checkout.toml"
    named.parent.mkdir()
    s.record.rename(named)
    resolution = named.with_name(f"{name}.resolved.toml")
    s.resolution.rename(resolution)
    s.record, s.resolution = named, resolution
    assert invoke(s.root, "run") == 0
    runtime_root, snapshot, context_path = runtime_view(s, monkeypatch, tmp_path)
    # Check capture before the runtime override can conceal a wrong info name.
    assert snapshot["checkout-name"] == name
    assert snapshot["info"]["checkout"]["name"] == name
    # A sibling does not become the active selection merely by being visible.
    wrong = load_toml(named)
    wrong["checkout"]["path"] = "/another/checkout"
    (named.parent / "other.checkout.toml").write_text(render_toml(wrong))
    assert invoke(runtime_root, "versions", "show") == 0
    assert "Same software selection" in capsys.readouterr().out
    assert invoke(runtime_root, "list") == 0
    out = capsys.readouterr().out
    assert str(s.root) in out and "/another/checkout" not in out
    # The real mount loses the host directory's "checkouts" suffix.
    from devcapsule import runtime_configuration
    mounted = tmp_path / "mounted-checkout"
    shutil.copytree(named.parent, mounted)
    monkeypatch.setattr(runtime_configuration, "CONFIGURATION_PATH", mounted)
    assert invoke(runtime_root, "config", "show", "--json") == 0
    listing = json.loads(capsys.readouterr().out)
    assert listing["checkout"]["name"] == name
    assert listing["checkout"]["record"]["checkout"]["path"] == str(s.root)
    assert invoke(runtime_root, "info", "--json") == 0
    assert json.loads(capsys.readouterr().out)["checkout"]["name"] == name
    # Older launches have stale info or no info. Both reports use the context
    # name when present, and otherwise the mounted filename.
    for has_info in (True, False):
        for has_name in (True, False):
            legacy = deepcopy(snapshot)
            if has_info:
                legacy["info"]["checkout"]["name"] = "default"
            else:
                legacy.pop("info")
            if not has_name:
                legacy.pop("checkout-name")
            context_path.write_text(json.dumps(legacy))
            expected = "default" if name == "devcapsule" and not has_name else name
            for command in (("info",), ("config", "show")):
                assert invoke(runtime_root, *command, "--json") == 0
                assert json.loads(capsys.readouterr().out)["checkout"]["name"] == expected
            assert invoke(runtime_root, "info") == 0
            assert f"Checkout name: {expected}\n" in capsys.readouterr().out


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_version_selection_keeps_an_omitted_optional_pin_for_later_restoration(journey, capsys):
    from devcapsule.configuration.file_formats import selected_version_lock
    from devcapsule.configuration.storage import load_toml, lock_for
    manifest_path = journey.root / ".devcapsule/devcapsule.toml"
    manifest = load_toml(manifest_path)
    manifest["capabilities"] = {"required": ["python", "python-ide", "codex-agent"], "optional": ["browser-automation"]}
    manifest_path.write_text(render_toml(manifest))
    lock = load_toml(journey.lock)
    playwright = tomllib.loads(MATRICES[Platform.current()].resolve(["python", "browser-automation"], project_only=True).render_lock())["components"]["playwright"]
    lock["components"]["playwright"] = dict(playwright, version="fixture-shared-pin")
    journey.lock.write_text(render_toml(lock))
    assert invoke(journey.root, "config", "omit", "browser-automation") == 0
    assert "playwright" not in lock_for(journey.root, manifest)[1]["components"]
    def host_decisions():  # base-image is formation trust, renewed by an explicit selection
        return {name: value for name, value in load_toml(journey.record)["authorization"].items() if name != "base-image"}
    decisions = host_decisions()
    preview_select(journey, capsys)
    selected = selected_version_lock(load_toml(journey.record))
    assert selected is not None
    assert selected["components"]["playwright"]["version"] == "fixture-shared-pin"  # the omission is a run-time filter, not a loss
    assert selected["components"]["codex"]["version"] == "2.0.0"
    assert invoke(journey.root, "config", "restore", "browser-automation") == 0
    effective = lock_for(journey.root, manifest)[1]
    assert effective["components"]["playwright"]["version"] == "fixture-shared-pin"
    assert effective["components"]["codex"]["version"] == "2.0.0"
    assert host_decisions() == decisions


def omit_shared_optional(journey, capability, component):
    """Declare a shared optional capability with its provider, then omit it locally."""
    from devcapsule.configuration.storage import load_toml
    path = journey.root / ".devcapsule/devcapsule.toml"
    manifest = load_toml(path)
    manifest["capabilities"] = {"required": ["python", "python-ide", "codex-agent"], "optional": [capability]}
    path.write_text(render_toml(manifest))
    lock = load_toml(journey.lock)
    extra = tomllib.loads(MATRICES[Platform.current()].resolve(["python", capability], project_only=True).render_lock())
    lock["components"][component] = extra["components"][component]
    journey.lock.write_text(render_toml(lock))
    assert invoke(journey.root, "config", "omit", capability) == 0


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_select_ignores_an_omitted_acquisition(journey, capsys):
    from devcapsule.configuration.file_formats import selected_version_lock
    from devcapsule.configuration.storage import load_toml
    omit_shared_optional(journey, "antigravity-agent", "antigravity-cli")
    preview_select(journey, capsys)
    record = load_toml(journey.record)
    assert "antigravity-download" not in record.get("authorization", {})  # no consent inferred for an omitted tool
    selected = selected_version_lock(record)
    assert selected is not None and "antigravity-cli" in selected["components"]  # the hidden pin is still kept


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_select_keeps_retained_consent_inactive_for_an_omitted_acquisition(journey, capsys):
    from devcapsule.configuration.storage import load_toml
    omit_shared_optional(journey, "antigravity-agent", "antigravity-cli")
    assert invoke(journey.root, "config", "restore", "antigravity-agent") == 0
    assert invoke(journey.root, "config", "authorize", "antigravity-download", "true") == 0
    assert invoke(journey.root, "config", "omit", "antigravity-agent") == 0
    consent = load_toml(journey.record)["authorization"]["antigravity-download"]
    preview_select(journey, capsys)
    assert load_toml(journey.record)["authorization"]["antigravity-download"] == consent
    assert "antigravity-cli" not in ExecutionConfiguration.load(journey.root).project.lock["components"]


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_preview_is_stale_when_a_hidden_pin_changes(journey, capsys):
    from devcapsule.configuration.storage import load_toml
    omit_shared_optional(journey, "browser-automation", "playwright")
    identity = preview_select(journey, capsys, select=False)
    before = version_sets.Workspace.load(journey.root)
    shared = load_toml(journey.lock)
    shared["components"]["playwright"]["version"] = "new-hidden-pin"
    journey.lock.write_text(render_toml(shared))
    after = version_sets.Workspace.load(journey.root)
    assert before.composition != after.composition and before.identity == after.identity
    capsys.readouterr()
    assert invoke(journey.root, "versions", "select", identity, "--unvalidated") == 2
    assert "preview again" in capsys.readouterr().err
    assert "version-set" not in load_toml(journey.record)


@pytest.mark.parametrize("journey", ["codex"], indirect=True)
def test_select_does_not_acquire_an_unsupported_optional_provider(journey, capsys, monkeypatch):
    from devcapsule.configuration.file_formats import selected_version_lock
    from devcapsule.configuration.storage import load_toml
    path = journey.root / ".devcapsule/devcapsule.toml"
    manifest = load_toml(path)
    manifest["capabilities"] = {"required": ["python", "python-ide", "codex-agent"], "optional": ["future-tool"]}
    path.write_text(render_toml(manifest))
    shared = load_toml(journey.lock)
    # An opaque provider from a newer contributor; this reader cannot use its artifact.
    future = {"version": "1", "url": "https://example.invalid/future.tgz", "integrity": "sha512-ZmFrZQ=="}
    shared["components"]["future"] = dict(future)
    shared["capability-providers"] = {"future-tool": ["future"]}
    journey.lock.write_text(render_toml(shared))
    original = version_sets.acquire_artifact
    def acquire(spec, *args, **kwargs):
        assert spec.url != future["url"], "attempted acquisition of an unsupported optional provider"
        return original(spec, *args, **kwargs)
    monkeypatch.setattr(version_sets, "acquire_artifact", acquire)
    preview_select(journey, capsys)
    selected = selected_version_lock(load_toml(journey.record))
    assert selected is not None
    assert selected["components"]["future"] == future  # preserved untouched, not interpreted
    assert selected["components"]["codex"]["version"] == "2.0.0"
