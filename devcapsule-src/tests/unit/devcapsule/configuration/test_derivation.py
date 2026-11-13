"""Unit tests of ``devcapsule/configuration/derivation.py``: reading a checkout into memory, and a checkout's selection.

Each test of the reading writes its project under ``tmp_path``: a manifest
and the lock the product derives from it. The home is the private one the
suite gives every test; a test that needs a settings file there writes it.
The tests of the selection use values alone.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from devcapsule.configuration.capabilities import CapabilityPolicy, LocalCapabilities
from devcapsule.configuration.capability_selection import generate_lock
from devcapsule.configuration.derivation import Selection, load_state
from devcapsule.configuration.file_formats import ProjectConfigurationError, render_toml
from devcapsule.configuration.manifest_document import Recommendations
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


# A checkout's selection: the IDE, the capabilities added and omitted, and the provider chosen where several
# can supply a capability. ``project config ide``, ``add``, ``omit``, ``restore`` and ``use`` edit one of these.

AMD64 = MATRICES[Platform.LINUX_AMD64]
SURFACES = {name: AMD64.resolve_provider(name) or name for name in AMD64.ide_capabilities()}
POLICY = CapabilityPolicy.read(MANIFEST)
NO_RECOMMENDATION = Recommendations.read(MANIFEST)


def choose_provider(selection: Selection, capability: str, component: str) -> None:
    """``project config use CAPABILITY COMPONENT`` on a selection of ``MANIFEST``'s project."""
    selection.use(AMD64, POLICY, NO_RECOMMENDATION, capability, component)


def test_a_provider_is_chosen_for_the_selected_ide_and_recorded_with_it() -> None:
    """With the front-end IDE selected, which VSCodium and Visual Studio Code both supply, choosing Visual Studio
    Code is recorded as that capability's provider, beside the IDE and an added agent."""
    selection = Selection(LocalCapabilities(), SURFACES)
    selection.ide = "frontend-ide"
    selection.extra.add("claude-code-agent")

    choose_provider(selection, "frontend-ide", "vscode")

    assert selection.local() == LocalCapabilities(("claude-code-agent", "frontend-ide"), (), {"frontend-ide": "vscode"})


@pytest.mark.parametrize(("capability", "component"), [("python-ide", "pycharm"), ("vscode-ide", "vscode")])
def test_a_capability_with_one_provider_offers_no_choice(capability: str, component: str) -> None:
    """Choosing a provider for a capability that one component supplies is refused, even when the component
    named is that one, and the selection is unchanged."""
    selection = Selection(LocalCapabilities((capability,)), SURFACES)

    with pytest.raises(ProjectConfigurationError, match=f"'{capability}' has no provider choice; supplied by {component}"):
        choose_provider(selection, capability, component)

    assert selection.local() == LocalCapabilities((capability,))


def test_a_provider_cannot_be_chosen_for_a_capability_that_is_not_selected() -> None:
    """Choosing a provider for the front-end IDE while no IDE is selected is refused, naming the commands that
    select it."""
    selection = Selection(LocalCapabilities(), SURFACES)

    with pytest.raises(ProjectConfigurationError, match="'frontend-ide' is not selected; use 'config add frontend-ide' or 'config ide frontend-ide' first"):
        choose_provider(selection, "frontend-ide", "vscode")


def test_the_default_provider_is_chosen_by_forgetting_the_choice() -> None:
    """``default`` as the component removes a recorded provider choice and leaves the capability selected."""
    selection = Selection(LocalCapabilities(("frontend-ide",), (), {"frontend-ide": "vscode"}), SURFACES)

    choose_provider(selection, "frontend-ide", "default")

    assert selection.local() == LocalCapabilities(("frontend-ide",))


def test_selecting_another_ide_forgets_the_provider_chosen_for_the_one_it_replaces() -> None:
    """Changing the IDE from the front-end IDE to PyCharm drops the provider chosen for the front-end IDE and
    keeps the capabilities that are not IDEs."""
    selection = Selection(LocalCapabilities(("claude-code-agent", "frontend-ide"), (), {"frontend-ide": "vscode"}), SURFACES)

    selection.ide = "python-ide"

    assert selection.local() == LocalCapabilities(("claude-code-agent", "python-ide"))

