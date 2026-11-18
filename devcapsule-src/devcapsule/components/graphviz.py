"""Optional Graphviz command-line tools, built offline under /opt/graphviz.

Public operations: ``GraphvizComponent`` implements the component contract;
``DEFINITION`` is the catalog entry. Its build recipe uses the same verified
upstream source on both Linux capsule architectures.
"""
from __future__ import annotations

from collections.abc import Mapping
import re

from devcapsule.compat import CliError
from devcapsule.components import (
    ComponentBuildRecipe, ComponentDefinition, LockedArtifactDeclaration,
    SecretInputDeclaration, StateEnvironmentDeclaration,
)
from devcapsule.components.discovery import read_json
from devcapsule.components.graphviz_discovery import GraphvizDiscovery, SOURCE
from devcapsule.container_runtime.contract import ComponentRuntimeTemplate

__all__ = ["DEFINITION", "GraphvizComponent"]

PREFIX = "/opt/graphviz"
RECIPE = "graphviz-autotools-v1"


class GraphvizComponent(ComponentDefinition):
    """Add Graphviz without replacing an IDE or changing the published base."""

    @property
    def id(self) -> str:
        return "graphviz"

    @property
    def capability(self) -> str:
        return "graphviz"

    def discovery_channel(self) -> GraphvizDiscovery:
        return GraphvizDiscovery(lambda: read_json(SOURCE))

    def channel_omission_reason(self) -> str:
        return "New releases require reviewed source/dependency pins and rendering acceptance."

    def state_environment(self) -> tuple[StateEnvironmentDeclaration, ...]:
        return ()

    def secret_inputs(self) -> tuple[SecretInputDeclaration, ...]:
        return ()

    def runtime_template(self) -> ComponentRuntimeTemplate:
        return ComponentRuntimeTemplate.from_mapping({
            "version": 1,
            "component": {
                "id": self.id, "adapter": "ancillary", "configuration": {},
                "environment": {},
                "persistence": {"home": "required", "xdg": "home-relative", "state_slots": []},
            },
        })

    def locked_artifacts(self, metadata: Mapping[str, object], platform: str) -> tuple[LockedArtifactDeclaration, ...]:
        if (platform not in {"linux-amd64", "linux-arm64"}
                or metadata.get("platform") != platform
                or not isinstance(metadata.get("version"), str)
                or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(metadata.get("version"))) is None
                or metadata.get("delivery-policy") != "local-materialization"
                or metadata.get("build-recipe") != RECIPE):
            raise CliError("Graphviz requires its reviewed source-build pin for the selected platform.")
        artifacts = metadata.get("artifacts")
        if not isinstance(artifacts, Mapping) or "source" not in artifacts or len(artifacts) < 2:
            raise CliError("Graphviz pin must include source and offline build dependencies.")
        result = []
        for name, item in artifacts.items():
            if (not isinstance(name, str) or not name.replace("-", "").replace("_", "").isalnum()
                    or not isinstance(item, Mapping)
                    or any(not isinstance(item.get(key), str) or not item[key] for key in ("url", "sha256"))):
                raise CliError("Malformed Graphviz source or dependency artifact.")
            filename = "source.tar.gz" if name == "source" else name + ".deb"
            result.append(LockedArtifactDeclaration(
                self.id, str(metadata["version"]), str(item["url"]), str(item["sha256"]),
                f"{PREFIX}/.build/{filename}", artifact_format="file", permissions=0o644,
                environment=((("PATH", f"{PREFIX}/bin:${{PATH}}"),) if name == "source" else ()),
            ))
        return tuple(result)

    def build_recipe(self, version: str, platform: str) -> ComponentBuildRecipe:
        if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None or platform not in {"linux-amd64", "linux-arm64"}:
            raise CliError("Unsupported Graphviz source-build recipe.")
        command = " && ".join([
            "export DEBIAN_FRONTEND=noninteractive",
            "dpkg --install /opt/graphviz/.build/*.deb",
            "mkdir /opt/graphviz/.build/src",
            "tar -xzf /opt/graphviz/.build/source.tar.gz --strip-components=1 -C /opt/graphviz/.build/src",
            "cd /opt/graphviz/.build/src",
            "pkg-config --exists pangocairo pangoft2 expat gts",
            "./configure --prefix=/opt/graphviz --disable-swig --disable-gvedit "
            "--with-pangocairo=yes --with-gts=yes --without-gd --without-gdk --without-gdk-pixbuf "
            "--without-lasi --without-rsvg --without-gtk --without-qt "
            "LDFLAGS=-Wl,-rpath,/opt/graphviz/lib",
            "make -j2",
            "make install",
            "cp -a /usr/lib/$(gcc -print-multiarch)/libltdl.so.7* /opt/graphviz/lib/",
            "cp -a /usr/lib/$(gcc -print-multiarch)/libgts-0.7.so.5* /opt/graphviz/lib/",
            "mkdir -p /opt/graphviz/share/licenses",
            "cp COPYING /opt/graphviz/share/licenses/graphviz.txt",
            "cp /usr/share/doc/libltdl7/copyright /opt/graphviz/share/licenses/libltdl.txt",
            "cp /usr/share/doc/libgts-0.7-5t64/copyright /opt/graphviz/share/licenses/gts.txt",
            "cd /",
            "rm -rf /opt/graphviz/.build",
            "/opt/graphviz/bin/dot -c",
            "/opt/graphviz/bin/dot -V",
            f"/opt/graphviz/bin/dot -V 2>&1 | grep -F 'graphviz version {version} '",
            "printf 'digraph G { a -> b }' | /opt/graphviz/bin/dot -Tsvg -o /tmp/graphviz-check.svg",
            "printf 'digraph G { a -> b }' | /opt/graphviz/bin/dot -Tpng -o /tmp/graphviz-check.png",
            "printf 'digraph G { a -> b }' | /opt/graphviz/bin/dot -Tpdf -o /tmp/graphviz-check.pdf",
            "printf 'digraph G { a -> b }' | /opt/graphviz/bin/sfdp -Tsvg -o /tmp/graphviz-check-sfdp.svg",
            "rm /tmp/graphviz-check.svg /tmp/graphviz-check.png /tmp/graphviz-check.pdf /tmp/graphviz-check-sfdp.svg",
        ])
        return ComponentBuildRecipe((("sh", "-ec", command),), (PREFIX,))


DEFINITION: ComponentDefinition = GraphvizComponent()
