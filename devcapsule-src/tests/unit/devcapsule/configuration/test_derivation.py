"""Unit tests of ``devcapsule/configuration/derivation.py``: reading a checkout into memory.

Each test writes its project under ``tmp_path``: a manifest and the lock the
product derives from it. The home is the private one the suite gives every
test; a test that needs a settings file there writes it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from devcapsule.configuration.capabilities import CapabilityPolicy
from devcapsule.configuration.capability_selection import generate_lock
from devcapsule.configuration.derivation import load_state
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.storage import settings_path
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

MANIFEST: dict[str, Any] = {
    "devcapsule-schema-version": 2,
    "project": {"name": "order", "slug": "order", "creator": "mailto:owner@example.test", "mount": "/workspace/order"},
    "capabilities": {"required": ["python"]},
}

ADMITTED_BY_ANY_LAUNCHER = {"devcapsule-settings-schema-version": 1, "minimum-devcapsule": "0.1.0"}
"""The two header fields of a settings document that every launcher release admits."""


def project_in(directory: Path) -> Path:
    """A project directory with ``MANIFEST`` and its linux-amd64 lock, and no checkout record anywhere."""
    root = directory / "order"
    (root / ".devcapsule").mkdir(parents=True)
    (root / ".devcapsule" / "devcapsule.toml").write_text(render_toml(MANIFEST), encoding="utf-8")
    lock = generate_lock(CapabilityPolicy.read(MANIFEST), MATRICES[Platform.LINUX_AMD64])
    (root / ".devcapsule" / "devcapsule.linux-amd64.lock").write_text(render_toml(lock), encoding="utf-8")
    return root


def test_a_settings_document_handed_in_is_the_states_home(tmp_path: Path) -> None:
    """``load_state`` given a settings document holds that document as the home and reads no settings file:
    a file in the home that says otherwise is not consulted."""
    root = project_in(tmp_path)
    settings_path().parent.mkdir(parents=True)
    settings_path().write_text(render_toml({**ADMITTED_BY_ANY_LAUNCHER, "defaults": {"cpus": 4}}), encoding="utf-8")
    handed_in = {**ADMITTED_BY_ANY_LAUNCHER, "defaults": {"cpus": 2}}

    state = load_state(root, MANIFEST, home=handed_in)

    assert state.home == handed_in


def test_the_state_keeps_its_own_copy_of_a_document_handed_in(tmp_path: Path) -> None:
    """A change the caller makes to its document after the read does not reach the state's home."""
    handed_in: dict[str, Any] = {**ADMITTED_BY_ANY_LAUNCHER, "defaults": {"cpus": 2}}
    state = load_state(project_in(tmp_path), MANIFEST, home=handed_in)

    handed_in["defaults"]["cpus"] = 8

    assert state.home["defaults"] == {"cpus": 2}


def test_without_a_document_the_homes_settings_file_is_read(tmp_path: Path) -> None:
    """``load_state`` given no settings document reads the home's settings file."""
    root = project_in(tmp_path)
    settings_path().parent.mkdir(parents=True)
    settings_path().write_text(render_toml({**ADMITTED_BY_ANY_LAUNCHER, "defaults": {"cpus": 4}}), encoding="utf-8")

    state = load_state(root, MANIFEST)

    assert state.home["defaults"] == {"cpus": 4}


def test_an_empty_document_is_a_home_that_has_no_settings(tmp_path: Path) -> None:
    """An empty settings document is taken as it is, as a home without a settings file reads: no trust, no
    default, and no header to admit."""
    state = load_state(project_in(tmp_path), MANIFEST, home={})

    assert state.home == {}


def test_a_document_this_launcher_is_too_old_for_is_refused(tmp_path: Path) -> None:
    """A settings document handed in is admitted as a file is: one that requires a later launcher is refused,
    naming the release it requires."""
    too_new = {"devcapsule-settings-schema-version": 1, "minimum-devcapsule": "9999.0.0"}

    with pytest.raises(ProjectConfigurationError, match="requires DevCapsule 9999.0.0"):
        load_state(project_in(tmp_path), MANIFEST, home=too_new)


def test_an_unregistered_checkout_is_read_with_the_record_it_would_get(tmp_path: Path) -> None:
    """A project with no checkout record is read as unregistered, with the empty record of its own identity
    and the path of the default record in the home."""
    root = project_in(tmp_path)

    state = load_state(root, MANIFEST, home={})

    assert state.registered is False
    assert state.checkout["project"] == {"creator": "mailto:owner@example.test", "slug": "order"}
    assert state.input_path is not None and state.input_path.name == "devcapsule.checkout.toml"
    assert not state.input_path.exists()
    assert state.platform is Platform.LINUX_AMD64
    assert state.shared_lock["platform"] == "linux-amd64"
