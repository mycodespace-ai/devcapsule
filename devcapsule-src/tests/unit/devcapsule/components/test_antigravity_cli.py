"""Unit tests of ``devcapsule/components/antigravity_cli.py``: acquisition, runtime state, secrets, and settings seeds."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from devcapsule.commands.project import _seed_component_state
from devcapsule.components import ComponentDefinition
from devcapsule.components.antigravity_cli import (
    ANTIGRAVITY_AUTHORIZATION,
    ANTIGRAVITY_AUTO_MODE_MIN_VERSION,
    ANTIGRAVITY_EXECUTABLE,
    ANTIGRAVITY_HOME,
    ANTIGRAVITY_TERMS_URL,
    DEFINITION,
    AntigravityCliComponent,
    runtime_template,
)


def locked_metadata(version: str = "1.1.24") -> dict[str, object]:
    return {
        "version": version,
        "delivery-policy": "local-materialization",
        "acquisition-authorization": ANTIGRAVITY_AUTHORIZATION,
        "terms-url": ANTIGRAVITY_TERMS_URL,
        "artifacts": {
            "linux-amd64": {
                "url": "https://storage.googleapis.com/example/cli_linux_x64.tar.gz",
                "sha256": "a" * 64,
                "archive-member": "antigravity",
            }
        },
    }


def test_antigravity_declares_gated_archive_member_acquisition() -> None:
    """Antigravity CLI extracts the ``antigravity`` binary member into ``/opt/antigravity-cli/bin``."""
    assert issubclass(AntigravityCliComponent, ComponentDefinition)
    assert not inspect.isabstract(AntigravityCliComponent)
    artifact = DEFINITION.locked_artifacts(locked_metadata(), "linux-amd64")[0]

    assert DEFINITION.id == "antigravity-cli"
    assert DEFINITION.capability == "antigravity-agent"
    assert artifact.destination == ANTIGRAVITY_EXECUTABLE
    assert artifact.artifact_format == "tar-gz-member"
    assert artifact.archive_member == "antigravity"
    assert artifact.environment == (("PATH", "/opt/antigravity-cli/bin:${PATH}"),)


def test_antigravity_acquisition_contract_names_the_google_terms() -> None:
    """Acquisition requires explicit consent to Google's Antigravity terms."""
    contract = DEFINITION.acquisition()

    assert contract is not None
    assert contract.authorization == ANTIGRAVITY_AUTHORIZATION == "antigravity-download"
    assert contract.terms_url == ANTIGRAVITY_TERMS_URL == "https://antigravity.google/terms/"
    assert contract.display_name == "Antigravity CLI"
    assert contract.vendor == "Google"


def test_antigravity_state_is_persistent_and_credential_sensitive() -> None:
    """State persists across launches in a checkout-scoped ``~/.gemini`` home overlay slot."""
    template = runtime_template()
    slot = template.persistence.state_slots[0]

    assert template.component.environment == {}
    assert slot.container_path == ANTIGRAVITY_HOME == "/home/devcapsule/.gemini"
    assert slot.sensitivity == "credentials"
    assert slot.default_scope == "checkout"
    assert slot.home_overlay is True
    assert slot.permissions == "0700"


def test_antigravity_gemini_key_is_an_optional_explicit_secret() -> None:
    """The optional ``GEMINI_API_KEY`` secret is declared without mandatory binding."""
    (secret,) = DEFINITION.secret_inputs()

    assert secret.name == "gemini-api-key"
    assert secret.environment_variable == "GEMINI_API_KEY"
    assert secret.required is False


@pytest.mark.parametrize(
    "version,expected",
    [
        (None, {"toolPermission": "always-proceed"}),
        ("1.1.24", {"toolPermission": "always-proceed"}),
        ("1.4.2", {"toolPermission": "always-proceed"}),
        ("1.4.12", {"agentMode": "auto", "toolPermission": "always-proceed"}),
        ("1.5.17", {"agentMode": "auto", "toolPermission": "always-proceed"}),
    ],
)
def test_antigravity_settings_seed_sets_auto_agent_mode_from_1_4_12(
    tmp_path: Path, version: str | None, expected: dict[str, str]
) -> None:
    """Versions >= 1.4.12 seed ``agentMode = "auto"`` alongside ``toolPermission = "always-proceed"``."""
    assert ANTIGRAVITY_AUTO_MODE_MIN_VERSION == "1.4.12"
    (seed,) = DEFINITION.state_seeds(version=version)
    assert json.loads(seed.content) == expected

    slot = tmp_path / (version or "unversioned")
    slot.mkdir()
    declaration = SimpleNamespace(component_id="antigravity-cli", slot_name="home")
    _seed_component_state(slot, declaration, version=version)
    seeded = json.loads((slot / "antigravity-cli" / "settings.json").read_text(encoding="utf-8"))
    assert seeded == expected
