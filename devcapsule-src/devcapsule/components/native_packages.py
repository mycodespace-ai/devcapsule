"""Pinned Debian packages installed offline alongside an interactive surface."""

from collections.abc import Mapping

from devcapsule.compat import CliError
from devcapsule.components import LockedArtifactDeclaration


def native_dependencies(
    component_id: str, metadata: Mapping[str, object], platform: str,
) -> tuple[LockedArtifactDeclaration, ...]:
    """Read the surface’s pinned package declarations for offline installation."""
    packages = metadata.get("native-packages")
    if platform not in ("linux-amd64", "linux-arm64") or not isinstance(packages, dict) or not packages:
        raise CliError(f"{component_id} requires pinned native-packages for {platform}.")
    artifacts = []
    for package, entry in packages.items():
        if not isinstance(entry, dict) or any(not isinstance(entry.get(key), str) or not entry[key]
                                              for key in ("version", "url", "sha256")):
            raise CliError(f"Malformed {component_id} native package {package!r}.")
        artifacts.append(LockedArtifactDeclaration(
            component_id, entry["version"], entry["url"], entry["sha256"],
            f"/tmp/devcapsule-native-debs/{entry['sha256']}.deb", artifact_format="deb-package",
            permissions=0o644,
        ))
    return tuple(artifacts)
