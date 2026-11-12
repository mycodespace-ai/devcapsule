"""Deterministic distribution contracts, including malformed external metadata."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import io
import json
from urllib.error import URLError

import pytest

from devcapsule.compat import CliError
from devcapsule.components.catalog import COMPONENTS
from devcapsule.components.npm_channel import NpmChannel
from devcapsule.materialization import ArtifactSpec, acquire_artifact

pytestmark = pytest.mark.legacy


@pytest.fixture
def channel(monkeypatch):
    channel = NpmChannel("@example/tool", {"linux-amd64": "@example/tool-linux-x64"})
    meta = {"name": "@example/tool", "version": "2.0.0", "engines": {"node": ">=16"},
            "optionalDependencies": {"@example/tool-linux-x64": "npm:@example/tool@2.0.0-linux-x64"},
            "dist": {"tarball": "https://registry.npmjs.org/tool.tgz", "integrity": "sha512-" + base64.b64encode(b"x" * 64).decode()}}
    binary = {"name": "@example/tool", "version": "2.0.0-linux-x64", "os": ["linux"], "cpu": ["x64"], "dist": deepcopy(meta["dist"])}
    docs = {"": {"dist-tags": {"latest": "2.0.0"}, "versions": {"2.0.0": meta}}, "latest": meta, "2.0.0-linux-x64": binary}
    monkeypatch.setattr(channel, "_metadata", lambda version="": deepcopy(docs[version]))
    return channel, docs


def test_every_curated_component_declares_channel_or_explains_omission():
    for definition in COMPONENTS.values():
        assert definition.distribution_channel() is not None or definition.channel_omission_reason(), (
            f"Contributor action: {definition.id} must declare distribution_channel() or document channel_omission_reason(). "
            "Older user locks need no migration.")


def test_labels_pin_exact_packages_and_status_is_independent_of_validation(channel):
    adapter, docs = channel
    checked = adapter.check("1.0.0", "linux-amd64")
    assert checked.current.status == "withdrawn"
    assert checked.candidates[0].status == "available"
    docs[""]["versions"]["2.0.0"]["deprecated"] = "vendor no longer supports this"
    current = adapter.check("2.0.0", "linux-amd64").current
    assert current.status == "unsupported"
    assert current.notices[0].kind == "end-of-support"
    assert current.notices[0].detail == "vendor no longer supports this"
    selected = adapter.select("latest", "linux-amd64")
    assert selected.metadata["version"] == "2.0.0"
    assert selected.metadata["artifacts"]["linux-amd64"]["npm-package"] == "@example/tool-linux-x64"
    assert selected.metadata["integrity"].startswith("sha512-")
    assert selected.status == "unsupported"
    assert not hasattr(selected, "validated")
    assert adapter.check("2.0.0", "other-platform").current.status == "unsupported"
    with pytest.raises(CliError, match="no distribution"):
        adapter.select("latest", "other-platform")


def test_npm_does_not_infer_security_or_support_notices_from_missing_versions(channel):
    adapter, docs = channel
    assert adapter.check("1.0.0", "linux-amd64").current.notices == ()
    assert adapter.check("2.0.0", "other-platform").current.notices == ()
    docs[""]["versions"]["2.0.0"]["deprecated"] = {"unexpected": "metadata"}
    with pytest.raises(CliError, match="Malformed npm deprecation"):
        adapter.check("2.0.0", "linux-amd64")


@pytest.mark.parametrize("change", ["engines", "version", "dependency", "url", "integrity", "binary", "dependencies", "platform"])
def test_malformed_or_new_structural_contract_refused(channel, change):
    adapter, docs = channel
    meta = docs["latest"]
    if change == "engines":
        meta["engines"] = ["bad"]
    elif change == "version":
        meta["version"] = "../../unsafe"
    elif change == "dependency":
        meta["optionalDependencies"]["@example/tool-linux-x64"] = "^2.0.0"
    elif change == "url":
        meta["dist"]["tarball"] = "https://elsewhere.test/tool.tgz"
    elif change == "integrity":
        meta["dist"]["integrity"] = "sha1-old"
    elif change == "binary":
        docs["2.0.0-linux-x64"]["version"] = "3.0.0"
    elif change == "platform":
        docs["2.0.0-linux-x64"]["cpu"] = ["arm64"]
    elif change == "dependencies":
        meta["dependencies"] = {"unexpected": "latest"}
    with pytest.raises(CliError):
        adapter.select("latest", "linux-amd64")


@pytest.mark.parametrize("payload", [b"not json", b"[]", b'{"dist-tags":{},"versions":[]}'])
def test_unavailable_or_malformed_metadata_is_not_current(monkeypatch, payload):
    adapter = NpmChannel("@example/tool", {"linux-amd64": "alias"})
    monkeypatch.setattr("devcapsule.components.npm_channel.urlopen", lambda *a, **k: io.BytesIO(payload))
    with pytest.raises(CliError, match="unavailable|Malformed"):
        adapter.check("1.0.0", "linux-amd64")
    def unavailable(*args, **kwargs):
        raise URLError("offline")
    monkeypatch.setattr("devcapsule.components.npm_channel.urlopen", unavailable)
    with pytest.raises(CliError, match="unavailable.*offline"):
        adapter.check("1.0.0", "linux-amd64")


def test_existing_acquisition_engine_verifies_sri_and_preserves_exact_cache(tmp_path):
    payload = tmp_path / "artifact"
    payload.write_bytes(b"exact vendor bytes")
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(payload.read_bytes()).digest()).decode()
    spec = ArtifactSpec("2.0.0", payload.as_uri(), "", integrity=integrity)
    acquired = acquire_artifact(spec, tmp_path / "cache")
    payload.unlink()
    assert acquire_artifact(spec, tmp_path / "cache").path == acquired.path
    acquired.path.write_bytes(b"corrupt")
    with pytest.raises(CliError, match="Cannot download"):
        acquire_artifact(spec, tmp_path / "cache")
    payload.write_bytes(b"not the accepted bytes")
    with pytest.raises(CliError, match="digest mismatch"):
        acquire_artifact(spec, tmp_path / "cache")
    assert not acquired.path.exists()
