"""Eclipse IDE for Java Developers, using Eclipse's shared-installation model."""

from collections.abc import Mapping

from devcapsule.components.native_packages import native_dependencies
from devcapsule.components import ComponentDefinition, LockedArtifactDeclaration, SecretInputDeclaration, StateEnvironmentDeclaration
from devcapsule.components.discovery import EclipseDiscovery
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate


class EclipseComponent(ComponentDefinition):
    @property
    def id(self) -> str:
        return "eclipse"

    @property
    def capability(self) -> str:
        return "eclipse-ide"

    def channel_omission_reason(self) -> str:
        return "Eclipse Java package upgrades require a reviewed archive pin and graphical acceptance."

    def discovery_channel(self) -> EclipseDiscovery:
        return EclipseDiscovery()

    def runtime_template(self) -> ComponentRuntimeTemplate:
        return ComponentRuntimeTemplate.from_mapping({
            "version": 1,
            "component": {
                "id": self.id, "adapter": "eclipse",
                "configuration": {
                    "installation_path": "/opt/eclipse", "launcher": "eclipse",
                    "workspace_slot": "workspace",
                },
                "persistence": {
                    # The read-only installation redirects per-user configuration
                    # and p2 state into the persistent home using upstream logic.
                    "home": "required", "xdg": "home-relative",
                    "state_slots": [{
                        "name": "workspace", "container_path": "/ide-workspace",
                        "kind": "durable", "sensitivity": "personal",
                        "default_scope": "checkout", "storage": "directory",
                        "concurrent": False, "owner": "runtime-user",
                        "permissions": "0700", "reconstructable": False,
                        "deletion_effect": "Removes Eclipse workspace preferences, project references, local history and any files created inside the workspace. Imported project files remain in the mounted checkout.",
                    }],
                },
            },
        })

    def state_environment(self) -> tuple[StateEnvironmentDeclaration, ...]:
        return ()

    def secret_inputs(self) -> tuple[SecretInputDeclaration, ...]:
        return ()

    def locked_artifacts(self, metadata: Mapping[str, object], platform: str) -> tuple[LockedArtifactDeclaration, ...]:
        # The surface materializer handles the IDE archive; its native browser
        # dependencies use the same acquisition/hash verification before an
        # offline dpkg installation. The set is specific to the Ubuntu 24.04 base.
        return native_dependencies(self.id, metadata, platform)


DEFINITION: ComponentDefinition = EclipseComponent()
