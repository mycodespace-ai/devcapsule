"""Optional, user-acquired Google Antigravity CLI component contract.

Delivery follows the Claude Code pattern the 2026-09-02 license and
redistribution analysis confirmed: a proprietary binary the developer
acquires directly from Google behind an explicit acquisition
authorization, cached only in locally built environment images that are
never pushed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from devcapsule.components.discovery import AntigravityDiscovery
from devcapsule.compat import CliError
from devcapsule.components import (
    AcquisitionContract,
    ComponentDefinition,
    LockedArtifactDeclaration,
    SecretInputDeclaration,
    StateEnvironmentDeclaration,
)
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate
from devcapsule.components.interface import StateSeedDeclaration


# The CLI keeps settings and session state under ~/.gemini — the
# antigravity-cli/ subdirectory the license analysis recorded, plus a
# project registry at config/projects discovered in first use (see the
# 2026-09-02 antigravity-state bug record). The slot covers the whole
# directory: a slot nested deeper than one level beneath home would leave
# Docker's root-owned intermediate parent walling off the siblings. No
# documented environment variable relocates the path, so the slot pins it
# and declares no environment.
ANTIGRAVITY_HOME = "/home/devcapsule/.gemini"
ANTIGRAVITY_PREFIX = "/opt/antigravity-cli"
ANTIGRAVITY_BIN = f"{ANTIGRAVITY_PREFIX}/bin"
ANTIGRAVITY_EXECUTABLE = f"{ANTIGRAVITY_BIN}/antigravity"
ANTIGRAVITY_AUTHORIZATION = "antigravity-download"
ANTIGRAVITY_TERMS_URL = "https://antigravity.google/terms/"
ANTIGRAVITY_AUTO_MODE_MIN_VERSION = "1.4.12"
"""Minimum Antigravity CLI version for which DevCapsule seeds ``agentMode = "auto"``."""


class AntigravityCliComponent(ComponentDefinition):
    """Antigravity CLI acquired directly from Google during local materialization."""

    def discovery_channel(self) -> AntigravityDiscovery:
        return AntigravityDiscovery()

    def channel_omission_reason(self) -> str:
        return 'A checksum-pinned distribution adapter has not been implemented.'

    @property
    def id(self) -> str:
        return "antigravity-cli"

    @property
    def capability(self) -> str:
        return "antigravity-agent"

    def acquisition(self) -> AcquisitionContract:
        return AcquisitionContract(
            authorization=ANTIGRAVITY_AUTHORIZATION,
            terms_url=ANTIGRAVITY_TERMS_URL,
            display_name="Antigravity CLI",
            vendor="Google",
        )

    def state_environment(self) -> tuple[StateEnvironmentDeclaration, ...]:
        return ()

    def state_seeds(self, version: str | None = None) -> tuple[StateSeedDeclaration, ...]:
        include_auto_mode = version is not None and _version_at_least(
            version, ANTIGRAVITY_AUTO_MODE_MIN_VERSION
        )
        content = (
            '{"agentMode": "auto", "toolPermission": "always-proceed"}\n'
            if include_auto_mode
            else '{"toolPermission": "always-proceed"}\n'
        )
        return (
            StateSeedDeclaration(
                slot="home",
                relative_path="antigravity-cli/settings.json",
                content=content,
                description="Run tools without approval prompts inside the capsule.",
                merge_missing_json=True,
            ),
        )

    def secret_inputs(self) -> tuple[SecretInputDeclaration, ...]:
        return (
            SecretInputDeclaration(
                name="gemini-api-key",
                environment_variable="GEMINI_API_KEY",
                required=False,
                description=(
                    "Optional Gemini API key for the headless modelProvider = gemini "
                    "flow. It is visible to all processes in the capsule when "
                    "explicitly delivered through the container environment."
                ),
            ),
        )

    def locked_artifacts(
        self, metadata: Mapping[str, object], platform: str
    ) -> tuple[LockedArtifactDeclaration, ...]:
        if metadata.get("delivery-policy") != "local-materialization":
            raise CliError(
                "components.antigravity-cli.delivery-policy must be 'local-materialization'."
            )
        if metadata.get("acquisition-authorization") != ANTIGRAVITY_AUTHORIZATION:
            raise CliError(
                "components.antigravity-cli.acquisition-authorization must be "
                f"{ANTIGRAVITY_AUTHORIZATION!r}."
            )
        if metadata.get("terms-url") != ANTIGRAVITY_TERMS_URL:
            raise CliError(
                f"components.antigravity-cli.terms-url must be {ANTIGRAVITY_TERMS_URL!r}."
            )
        artifacts = metadata.get("artifacts")
        artifact = artifacts.get(platform) if isinstance(artifacts, Mapping) else None
        if not isinstance(artifact, Mapping):
            raise CliError(f"components.antigravity-cli has no artifact for {platform!r}.")
        version = _string(metadata.get("version"), "components.antigravity-cli.version")
        return (
            LockedArtifactDeclaration(
                component_id=self.id,
                version=version,
                url=_string(
                    artifact.get("url"),
                    f"components.antigravity-cli.artifacts.{platform}.url",
                ),
                sha256=_string(
                    artifact.get("sha256"),
                    f"components.antigravity-cli.artifacts.{platform}.sha256",
                ),
                archive_member=_string(
                    artifact.get("archive-member"),
                    f"components.antigravity-cli.artifacts.{platform}.archive-member",
                ),
                destination=ANTIGRAVITY_EXECUTABLE,
                environment=(("PATH", f"{ANTIGRAVITY_BIN}:${{PATH}}"),),
            ),
        )

    def runtime_template(self) -> ComponentRuntimeTemplate:
        return ComponentRuntimeTemplate.from_mapping(_runtime_template_mapping())


def runtime_template() -> ComponentRuntimeTemplate:
    return DEFINITION.runtime_template()


def _runtime_template_mapping() -> dict[str, Any]:
    return {
        "version": 1,
        "component": {
            "id": "antigravity-cli",
            "adapter": "ancillary",
            "configuration": {},
            "persistence": {
                "home": "required",
                "xdg": "home-relative",
                "state_slots": [
                    {
                        "name": "home",
                        "container_path": ANTIGRAVITY_HOME,
                        "kind": "durable",
                        "sensitivity": "credentials",
                        "default_scope": "checkout",
                        "storage": "directory",
                        "concurrent": False,
                        "owner": "runtime-user",
                        "permissions": "0700",
                        "reconstructable": False,
                        "deletion_effect": (
                            "Removes Antigravity CLI settings, its project registry, "
                            "and local session state; credentials live in the keyring "
                            "or arrive per run."
                        ),
                        "home_overlay": True,
                    }
                ],
            },
        },
    }


def _version_at_least(actual: str, minimum: str) -> bool:
    def _parts(text: str) -> tuple[int, ...] | None:
        head = text.split("-", 1)[0].split("+", 1)[0].strip()
        tokens = head.split(".")
        if not tokens or any(not token.isascii() or not token.isdigit() for token in tokens):
            return None
        return tuple(int(token) for token in tokens)

    actual_parts = _parts(actual)
    minimum_parts = _parts(minimum)
    if actual_parts is None or minimum_parts is None:
        return False
    width = max(len(actual_parts), len(minimum_parts))
    padded_actual = actual_parts + (0,) * (width - len(actual_parts))
    padded_minimum = minimum_parts + (0,) * (width - len(minimum_parts))
    return padded_actual >= padded_minimum


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CliError(f"{field} must be a non-empty string.")
    return value


DEFINITION: ComponentDefinition = AntigravityCliComponent()
