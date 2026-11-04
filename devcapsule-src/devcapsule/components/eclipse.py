"""Eclipse IDE for Java Developers, using Eclipse's shared-installation model."""

from collections.abc import Mapping

from devcapsule.compat import CliError
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
        packages = metadata.get("native-packages")
        if platform not in ("linux-amd64", "linux-arm64") or not isinstance(packages, dict) or not packages:
            raise CliError(f"Eclipse requires pinned native-packages for {platform}.")
        artifacts = []
        for package, entry in packages.items():
            if not isinstance(entry, dict) or any(not isinstance(entry.get(key), str) or not entry[key]
                                                  for key in ("version", "url", "sha256")):
                raise CliError(f"Malformed Eclipse native package {package!r}.")
            artifacts.append(LockedArtifactDeclaration(
                self.id, entry["version"], entry["url"], entry["sha256"],
                f"/tmp/devcapsule-native-debs/{entry['sha256']}.deb", artifact_format="deb-package",
                permissions=0o644,
            ))
        return tuple(artifacts)


DEFINITION: ComponentDefinition = EclipseComponent()
