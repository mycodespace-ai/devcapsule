"""Optional, user-acquired Claude Code component contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from devcapsule.components.discovery import ClaudeDiscovery
from devcapsule.compat import CliError
from devcapsule.components import (
    AcquisitionContract,
    ComponentDefinition,
    LockedArtifactDeclaration,
    SecretInputDeclaration,
    StateEnvironmentDeclaration,
)
from devcapsule.components.interface import StateSeedDeclaration, resolved_state_environment
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate


CLAUDE_CODE_HOME = "/home/devcapsule/.claude"
CLAUDE_CODE_PREFIX = "/opt/claude"
CLAUDE_CODE_BIN = f"{CLAUDE_CODE_PREFIX}/bin"
CLAUDE_CODE_EXECUTABLE = f"{CLAUDE_CODE_BIN}/claude"
CLAUDE_CODE_AUTHORIZATION = "claude-code-download"
CLAUDE_CODE_TERMS_URL = "https://www.anthropic.com/legal/commercial-terms"


class ClaudeCodeComponent(ComponentDefinition):
    """Claude Code acquired directly from Anthropic during local materialization."""

    def discovery_channel(self) -> ClaudeDiscovery:
        return ClaudeDiscovery()

    def channel_omission_reason(self) -> str:
        return 'A checksum-pinned distribution adapter has not been implemented.'

    @property
    def id(self) -> str:
        return "claude-code"

    @property
    def capability(self) -> str:
        return "claude-code-agent"

    def acquisition(self) -> AcquisitionContract:
        return AcquisitionContract(
            authorization=CLAUDE_CODE_AUTHORIZATION,
            terms_url=CLAUDE_CODE_TERMS_URL,
            display_name="Claude Code",
            vendor="Anthropic",
        )

    def state_environment(self) -> tuple[StateEnvironmentDeclaration, ...]:
        return (StateEnvironmentDeclaration("CLAUDE_CONFIG_DIR", "home"),)

    def secret_inputs(self) -> tuple[SecretInputDeclaration, ...]:
        return ()

    def state_seeds(self, version: str | None = None) -> tuple[StateSeedDeclaration, ...]:
        return (
            StateSeedDeclaration(
                slot="home",
                relative_path="settings.json",
                content=(
                    '{"permissions": {"defaultMode": "bypassPermissions"}, '
                    '"skipDangerousModePermissionPrompt": true}\n'
                ),
                description="Run tools without approval prompts inside the capsule.",
                merge_missing_json=True,
            ),
        )

    def locked_artifacts(
        self, metadata: Mapping[str, object], platform: str
    ) -> tuple[LockedArtifactDeclaration, ...]:
        if metadata.get("delivery-policy") != "local-materialization":
            raise CliError(
                "components.claude-code.delivery-policy must be 'local-materialization'."
            )
        if metadata.get("acquisition-authorization") != CLAUDE_CODE_AUTHORIZATION:
            raise CliError(
                "components.claude-code.acquisition-authorization must be "
                f"{CLAUDE_CODE_AUTHORIZATION!r}."
            )
        if metadata.get("terms-url") != CLAUDE_CODE_TERMS_URL:
            raise CliError(
                f"components.claude-code.terms-url must be {CLAUDE_CODE_TERMS_URL!r}."
            )
        artifacts = metadata.get("artifacts")
        artifact = artifacts.get(platform) if isinstance(artifacts, Mapping) else None
        if not isinstance(artifact, Mapping):
            raise CliError(f"components.claude-code has no artifact for {platform!r}.")
        version = _string(metadata.get("version"), "components.claude-code.version")
        return (
            LockedArtifactDeclaration(
                component_id=self.id,
                version=version,
                url=_string(
                    artifact.get("url"),
                    f"components.claude-code.artifacts.{platform}.url",
                ),
                sha256=_string(
                    artifact.get("sha256"),
                    f"components.claude-code.artifacts.{platform}.sha256",
                ),
                destination=CLAUDE_CODE_EXECUTABLE,
                artifact_format="file",
                environment=(
                    ("PATH", f"{CLAUDE_CODE_BIN}:${{PATH}}"),
                    ("DISABLE_UPDATES", "1"),
                ),
            ),
        )

    def runtime_template(self) -> ComponentRuntimeTemplate:
        document = _runtime_template_mapping()
        template = ComponentRuntimeTemplate.from_mapping(document)
        environment = resolved_state_environment(template, self.state_environment())
        component = document["component"]
        if not isinstance(component, dict):  # pragma: no cover - trusted constant.
            raise AssertionError("Claude Code component mapping must be a table")
        component["environment"] = environment
        return ComponentRuntimeTemplate.from_mapping(document)


def runtime_template() -> ComponentRuntimeTemplate:
    return DEFINITION.runtime_template()


def _runtime_template_mapping() -> dict[str, Any]:
    return {
        "version": 1,
        "component": {
            "id": "claude-code",
            "adapter": "ancillary",
            "configuration": {},
            "persistence": {
                "home": "required",
                "xdg": "home-relative",
                "state_slots": [
                    {
                        "name": "home",
                        "container_path": CLAUDE_CODE_HOME,
                        "kind": "durable",
                        "sensitivity": "credentials",
                        "default_scope": "checkout",
                        "storage": "directory",
                        "concurrent": False,
                        "owner": "runtime-user",
                        "permissions": "0700",
                        "reconstructable": False,
                        "deletion_effect": (
                            "Removes Claude Code authentication, configuration, and session state."
                        ),
                        "home_overlay": True,
                    }
                ],
            },
        },
    }


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CliError(f"{field} must be a non-empty string.")
    return value


DEFINITION: ComponentDefinition = ClaudeCodeComponent()
