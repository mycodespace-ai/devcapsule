from __future__ import annotations

import inspect

from devcapsule.components import ComponentDefinition
from devcapsule.components.claude_code import (
    CLAUDE_CODE_AUTHORIZATION,
    CLAUDE_CODE_EXECUTABLE,
    CLAUDE_CODE_TERMS_URL,
    DEFINITION,
    ClaudeCodeComponent,
    runtime_template,
)
import pytest

pytestmark = pytest.mark.legacy


def locked_metadata() -> dict[str, object]:
    return {
        "version": "2.1.227",
        "delivery-policy": "local-materialization",
        "acquisition-authorization": CLAUDE_CODE_AUTHORIZATION,
        "terms-url": CLAUDE_CODE_TERMS_URL,
        "artifacts": {
            "linux-amd64": {
                "url": "https://downloads.claude.ai/example/claude",
                "sha256": "a" * 64,
            }
        },
    }


def test_claude_code_declares_direct_raw_local_acquisition() -> None:
    assert issubclass(ClaudeCodeComponent, ComponentDefinition)
    assert not inspect.isabstract(ClaudeCodeComponent)
    artifact = DEFINITION.locked_artifacts(locked_metadata(), "linux-amd64")[0]

    assert DEFINITION.id == "claude-code"
    assert DEFINITION.capability == "claude-code-agent"
    assert artifact.destination == CLAUDE_CODE_EXECUTABLE
    assert artifact.artifact_format == "file"
    assert artifact.archive_member is None
    assert ("PATH", "/opt/claude/bin:${PATH}") in artifact.environment
    assert ("DISABLE_UPDATES", "1") in artifact.environment


def test_claude_code_state_is_persistent_and_credential_sensitive() -> None:
    template = runtime_template()
    slot = template.persistence.state_slots[0]

    assert template.component.environment == {
        "CLAUDE_CONFIG_DIR": "/home/devcapsule/.claude"
    }
    assert slot.container_path == "/home/devcapsule/.claude"
    assert slot.sensitivity == "credentials"
    assert slot.home_overlay is True
    assert slot.permissions == "0700"
