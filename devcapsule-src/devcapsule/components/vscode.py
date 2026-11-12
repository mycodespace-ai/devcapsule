"""Visual Studio Code component interface.

Visual Studio Code is proprietary Microsoft software acquired directly on the
user's machine during local materialization and never redistributed in published
DevCapsule images. Runtime planning reuses the generic ``vscode`` adapter and
state-slot contract shared with VSCodium.
"""

from __future__ import annotations

from collections.abc import Mapping

from devcapsule.compat import CliError
from devcapsule.components import (
    AcquisitionContract,
    ComponentDefinition,
    LockedArtifactDeclaration,
    SecretInputDeclaration,
    StateEnvironmentDeclaration,
)
from devcapsule.components.discovery import VscodeDiscovery
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate


VSCODE_INSTALLATION_PATH = "/opt/vscode"
VSCODE_AUTHORIZATION = "vscode-download"
VSCODE_TERMS_URL = "https://code.visualstudio.com/license"


class VscodeComponent(ComponentDefinition):
    """User-acquired Microsoft Visual Studio Code interactive surface."""

    def discovery_channel(self) -> VscodeDiscovery:
        return VscodeDiscovery()

    def channel_omission_reason(self) -> str:
        return "IDE upgrades are outside the component-upgrade slice."

    @property
    def id(self) -> str:
        return "vscode"

    @property
    def capability(self) -> str:
        return "vscode-ide"

    def acquisition(self) -> AcquisitionContract:
        return AcquisitionContract(
            authorization=VSCODE_AUTHORIZATION,
            terms_url=VSCODE_TERMS_URL,
            display_name="Visual Studio Code",
            vendor="Microsoft",
        )

    def runtime_template(self) -> ComponentRuntimeTemplate:
        return _runtime_template()

    def state_environment(self) -> tuple[StateEnvironmentDeclaration, ...]:
        return ()

    def secret_inputs(self) -> tuple[SecretInputDeclaration, ...]:
        return ()

    def locked_artifacts(
        self, metadata: Mapping[str, object], platform: str
    ) -> tuple[LockedArtifactDeclaration, ...]:
        del platform
        if metadata.get("delivery-policy") != "local-materialization":
            raise CliError(
                "components.vscode.delivery-policy must be 'local-materialization'."
            )
        if metadata.get("acquisition-authorization") != VSCODE_AUTHORIZATION:
            raise CliError(
                "components.vscode.acquisition-authorization must be "
                f"{VSCODE_AUTHORIZATION!r}."
            )
        if metadata.get("terms-url") != VSCODE_TERMS_URL:
            raise CliError(
                f"components.vscode.terms-url must be {VSCODE_TERMS_URL!r}."
            )
        _string(metadata.get("version"), "components.vscode.version")
        _string(metadata.get("url"), "components.vscode.url")
        _string(metadata.get("sha256"), "components.vscode.sha256")
        # Interactive surfaces materialize as a whole installation directory
        # under /opt/vscode via SURFACE_MATERIALIZATIONS, not per-file artifacts.
        return ()


def runtime_template() -> ComponentRuntimeTemplate:
    return DEFINITION.runtime_template()


def _runtime_template() -> ComponentRuntimeTemplate:
    return ComponentRuntimeTemplate.from_mapping(
        {
            "version": 1,
            "component": {
                "id": "vscode",
                "adapter": "vscode",
                "configuration": {
                    "installation_path": VSCODE_INSTALLATION_PATH,
                    # The Electron binary at /opt/vscode/code stays in the
                    # session's foreground; bin/code invokes the CLI wrapper
                    # with ELECTRON_RUN_AS_NODE=1 and exits immediately.
                    "launcher": "code",
                    "additional_arguments": ["--no-sandbox"],
                    "shared-memory-size": "640m",
                    "state_slot_mapping": {
                        "user-data": "user-data",
                        "extensions": "extensions",
                    },
                },
                "environment": {
                    # Suppress the interactive WSL extension prompt if bin/code
                    # is invoked from an integrated or headless shell on WSL2.
                    "DONT_PROMPT_WSL_INSTALL": "1",
                },
                "persistence": {
                    "home": "required",
                    "xdg": "home-relative",
                    "state_slots": [
                        _slot(
                            "user-data",
                            "/ide-user-data",
                            kind="durable",
                            sensitivity="personal",
                            reconstructable=False,
                            deletion_effect=(
                                "Removes editor settings, keybindings, snippets, "
                                "and per-workspace state."
                            ),
                        ),
                        _slot(
                            "extensions",
                            "/ide-extensions",
                            kind="durable",
                            sensitivity="personal",
                            reconstructable=False,
                            deletion_effect="Removes installed editor extensions.",
                        ),
                        _slot(
                            "cache",
                            "/home/devcapsule/.cache",
                            kind="cache",
                            sensitivity="ordinary",
                            reconstructable=True,
                            deletion_effect="Removes rebuildable user-tool caches.",
                            home_overlay=True,
                        ),
                    ],
                },
            },
        }
    )


def logical_state_slots() -> tuple[str, ...]:
    template = runtime_template()
    return tuple(template.logical_slot_name(slot.name) for slot in template.persistence.state_slots)


def _slot(
    name: str,
    container_path: str,
    *,
    kind: str,
    sensitivity: str,
    reconstructable: bool,
    deletion_effect: str,
    home_overlay: bool = False,
) -> dict[str, object]:
    value: dict[str, object] = {
        "name": name,
        "container_path": container_path,
        "kind": kind,
        "sensitivity": sensitivity,
        "default_scope": "checkout",
        "storage": "directory",
        "concurrent": False,
        "owner": "runtime-user",
        "permissions": "0700",
        "reconstructable": reconstructable,
        "deletion_effect": deletion_effect,
    }
    if home_overlay:
        value["home_overlay"] = True
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CliError(f"{field} must be a non-empty string.")
    return value


DEFINITION: ComponentDefinition = VscodeComponent()
