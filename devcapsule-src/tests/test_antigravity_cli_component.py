from __future__ import annotations

import inspect

from devcapsule.components import ComponentDefinition
from devcapsule.components.antigravity_cli import (
    ANTIGRAVITY_AUTHORIZATION,
    ANTIGRAVITY_EXECUTABLE,
    ANTIGRAVITY_HOME,
    ANTIGRAVITY_TERMS_URL,
    DEFINITION,
    AntigravityCliComponent,
    runtime_template,
)
import pytest

pytestmark = pytest.mark.legacy


def locked_metadata() -> dict[str, object]:
    return {
        "version": "1.1.24",
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
    contract = DEFINITION.acquisition()

    assert contract is not None
    assert contract.authorization == ANTIGRAVITY_AUTHORIZATION == "antigravity-download"
    assert contract.terms_url == ANTIGRAVITY_TERMS_URL == "https://antigravity.google/terms/"
    assert contract.display_name == "Antigravity CLI"
    assert contract.vendor == "Google"


def test_antigravity_state_is_persistent_and_credential_sensitive() -> None:
    template = runtime_template()
    slot = template.persistence.state_slots[0]

    # No environment variable relocates the CLI's state; the slot pins the
    # whole ~/.gemini directory — a direct child of home, so the mount point
    # is the user-owned state directory itself and the CLI can create its
    # config/projects registry beside antigravity-cli/ (2026-09-02 bug).
    assert template.component.environment == {}
    assert slot.container_path == ANTIGRAVITY_HOME == "/home/devcapsule/.gemini"
    assert slot.sensitivity == "credentials"
    assert slot.default_scope == "checkout"
    assert slot.home_overlay is True
    assert slot.permissions == "0700"


def test_antigravity_gemini_key_is_an_optional_explicit_secret() -> None:
    (secret,) = DEFINITION.secret_inputs()

    assert secret.name == "gemini-api-key"
    assert secret.environment_variable == "GEMINI_API_KEY"
    assert secret.required is False
