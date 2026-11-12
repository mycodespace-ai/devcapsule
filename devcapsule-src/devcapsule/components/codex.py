"""Optional Codex component contract exposed to DevCapsule orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from devcapsule.compat import CliError
from devcapsule.components.npm_channel import NpmChannel
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate
from devcapsule.components import (
    ComponentDefinition,
    LockedArtifactDeclaration,
    SecretInputDeclaration,
    StateEnvironmentDeclaration,
)
from devcapsule.components.interface import StateSeedDeclaration, resolved_state_environment


CODEX_HOME = "/home/devcapsule/.codex"
# Codex is delivered the way its vendor tests it: as the npm package, installed
# by npm into a versioned prefix (product-owner direction 2026-09-05). The
# meta package @openai/codex carries the node launcher; the per-platform
# package carries the binary beside the helpers it resolves relative to
# itself (bundled bubblewrap, ripgrep, zsh, the code-mode host). Extracting
# the binary alone left every sandboxed command failing — see the 2026-09-05
# bug record.
CODEX_PREFIX = "/opt/codex"
CODEX_PACKAGE = "@openai/codex"


def codex_installation(version: str) -> str:
    """The npm project directory holding one Codex version."""

    return f"{CODEX_PREFIX}/{version}"


def codex_bin(version: str) -> str:
    """The directory npm links `codex` into; it goes on the image PATH."""

    return f"{codex_installation(version)}/node_modules/.bin"


# The configuration a fresh checkout's ~/.codex starts with (product-owner
# ruling 2026-09-05). The capsule is the sandbox: Docker's isolation is the
# boundary DevCapsule enforces, so inside it codex runs with approvals off
# and no inner sandbox — the posture codex itself describes as "intended
# solely for running in environments that are externally sandboxed". The
# inner sandbox could not work anyway: codex's bubblewrap needs unprivileged
# user namespaces, which capsule hardening denies. use_legacy_landlock keeps
# a sandboxed mode functional should the developer switch one on; codex
# 0.153 lists the flag as deprecated, so it may need revisiting.
#
# Top-level keys must precede any table, and codex appends tables such as
# [tui.model_availability_nux] to this file on its own, so the seed is the
# whole initial file and a developer adding keys later must add them above
# the first table header.
CODEX_CONFIG_SEED = """\
# Seeded by DevCapsule when this checkout's codex state was created; edit or
# delete freely, DevCapsule never rewrites it. The capsule is the sandbox:
# codex runs here with approvals off and without its inner sandbox, which
# needs user namespaces the capsule denies. Top-level keys stay above the
# first [table]; codex appends tables below on its own.
approval_policy = "never"
sandbox_mode = "danger-full-access"
use_legacy_landlock = true
"""


class CodexComponent(ComponentDefinition):
    """Trusted Codex component implementation."""

    def distribution_channel(self) -> NpmChannel:
        return NpmChannel(CODEX_PACKAGE, {"linux-amd64": "@openai/codex-linux-x64",
                                          "linux-arm64": "@openai/codex-linux-arm64"})

    @property
    def id(self) -> str:
        return "codex"

    @property
    def capability(self) -> str:
        return "codex-agent"

    def state_environment(self) -> tuple[StateEnvironmentDeclaration, ...]:
        return (StateEnvironmentDeclaration("CODEX_HOME", "home"),)

    def state_seeds(self) -> tuple[StateSeedDeclaration, ...]:
        return (
            StateSeedDeclaration(
                slot="home",
                relative_path="config.toml",
                content=CODEX_CONFIG_SEED,
                description=(
                    "Codex configuration: approvals off and no inner sandbox, because "
                    "the capsule is the sandbox."
                ),
            ),
        )

    def secret_inputs(self) -> tuple[SecretInputDeclaration, ...]:
        return (
            SecretInputDeclaration(
                name="openai-api-key",
                environment_variable="OPENAI_API_KEY",
                required=False,
                description=(
                    "Optional OpenAI Platform API key. It is visible to all processes in the "
                    "capsule when explicitly delivered through the container environment."
                ),
            ),
        )

    def locked_artifacts(
        self, metadata: Mapping[str, object], platform: str
    ) -> tuple[LockedArtifactDeclaration, ...]:
        if metadata.get("delivery-policy") != "local-materialization":
            raise CliError("components.codex.delivery-policy must be 'local-materialization'.")
        if metadata.get("npm-package") != CODEX_PACKAGE:
            raise CliError(f"components.codex.npm-package must be {CODEX_PACKAGE!r}.")
        artifacts = metadata.get("artifacts")
        artifact = artifacts.get(platform) if isinstance(artifacts, Mapping) else None
        if not isinstance(artifact, Mapping):
            raise CliError(f"components.codex has no artifact for {platform!r}.")
        version = _string(metadata.get("version"), "components.codex.version")
        installation = codex_installation(version)
        platform_field = f"components.codex.artifacts.{platform}"
        return (
            # The meta package: the `codex` launcher npm links into
            # node_modules/.bin, which resolves the platform package below.
            LockedArtifactDeclaration(
                component_id=self.id,
                version=version,
                url=_string(metadata.get("url"), "components.codex.url"),
                sha256=_string(metadata.get("sha256"), "components.codex.sha256"),
                destination=installation,
                artifact_format="npm-package",
                npm_package=CODEX_PACKAGE,
                permissions=0o644,
                environment=(("PATH", f"{codex_bin(version)}:${{PATH}}"),),
            ),
            # The platform package, installed under the alias the meta
            # package's optionalDependencies name for this platform; the lock
            # records that alias rather than deriving it from the platform.
            LockedArtifactDeclaration(
                component_id=self.id,
                version=version,
                url=_string(artifact.get("url"), f"{platform_field}.url"),
                sha256=_string(artifact.get("sha256"), f"{platform_field}.sha256"),
                destination=installation,
                artifact_format="npm-package",
                npm_package=_string(artifact.get("npm-package"), f"{platform_field}.npm-package"),
                permissions=0o644,
            ),
        )

    def runtime_template(self) -> ComponentRuntimeTemplate:
        document = _runtime_template_mapping()
        template = ComponentRuntimeTemplate.from_mapping(document)
        environment = resolved_state_environment(template, self.state_environment())
        component = document["component"]
        if not isinstance(component, dict):  # pragma: no cover - local constant is trusted.
            raise AssertionError("Codex component mapping must be a table")
        component["environment"] = environment
        return ComponentRuntimeTemplate.from_mapping(document)


def runtime_template() -> ComponentRuntimeTemplate:
    return DEFINITION.runtime_template()


def _runtime_template_mapping() -> dict[str, Any]:
    return {
        "version": 1,
        "component": {
            "id": "codex",
            "adapter": "ancillary",
            "configuration": {},
            "persistence": {
                "home": "required",
                "xdg": "home-relative",
                "state_slots": [
                    {
                        "name": "home",
                        "container_path": CODEX_HOME,
                        "kind": "durable",
                        "sensitivity": "credentials",
                        "default_scope": "checkout",
                        "storage": "directory",
                        "concurrent": False,
                        "owner": "runtime-user",
                        "permissions": "0700",
                        "reconstructable": False,
                        "deletion_effect": (
                            "Removes Codex authentication, configuration, and local session state."
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


DEFINITION: ComponentDefinition = CodexComponent()
