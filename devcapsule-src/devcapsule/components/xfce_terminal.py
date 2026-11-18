"""Xfce Terminal as the supervised graphical surface of a capsule."""

from collections.abc import Mapping

from devcapsule.components import ComponentDefinition, LockedArtifactDeclaration, SecretInputDeclaration, StateEnvironmentDeclaration
from devcapsule.components.discovery import XfceTerminalDiscovery
from devcapsule.components.native_packages import native_dependencies
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate


class XfceTerminalComponent(ComponentDefinition):
    @property
    def id(self) -> str:
        return "xfce4-terminal"

    @property
    def capability(self) -> str:
        return self.id

    def discovery_channel(self) -> XfceTerminalDiscovery:
        return XfceTerminalDiscovery()

    def channel_omission_reason(self) -> str:
        return "Ubuntu terminal package updates require review of the pinned native dependencies."

    def runtime_template(self) -> ComponentRuntimeTemplate:
        return ComponentRuntimeTemplate.from_mapping({
            "version": 1,
            "component": {
                "id": self.id, "adapter": self.id, "configuration": {},
                "persistence": {"home": "required", "xdg": "home-relative", "state_slots": []},
            },
        })

    def state_environment(self) -> tuple[StateEnvironmentDeclaration, ...]:
        return ()

    def secret_inputs(self) -> tuple[SecretInputDeclaration, ...]:
        return ()

    def locked_artifacts(self, metadata: Mapping[str, object], platform: str) -> tuple[LockedArtifactDeclaration, ...]:
        return native_dependencies(self.id, metadata, platform)


DEFINITION: ComponentDefinition = XfceTerminalComponent()
