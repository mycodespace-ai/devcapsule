"""Build the locked Graphviz contribution offline and render as a capsule user."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tomllib
import xml.etree.ElementTree as ET

from devcapsule.components.graphviz import DEFINITION
from devcapsule.images.build import BuildxImageBuilder, EnvComponent, ImageBuildSpec
from devcapsule.materialization import ArtifactSpec, acquire_artifact, _ancillary_contributions
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES


def main() -> None:
    """Bind host inputs, build from exact pins, and check the resulting image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=[x.value for x in Platform])
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--image", default="devcapsule-graphviz:component-smoke")
    args = parser.parse_args()
    platform = Platform.parse(args.platform)
    formation = MATRICES[platform].resolve(["graphviz"], project_only=True, allow_unverified=True)
    lock = tomllib.loads(formation.render_lock())
    metadata = lock["components"]["graphviz"]
    declarations = DEFINITION.locked_artifacts(metadata, platform.value)
    files = tuple((acquire_artifact(ArtifactSpec(x.version, x.url, x.sha256, "graphviz"), args.cache).path, x)
                  for x in declarations)
    spec = ImageBuildSpec(args.image, lock["base"]["reference"], (
        *_ancillary_contributions(files, (), platform=platform.value),
        EnvComponent((("PATH", "/opt/graphviz/bin:${PATH}"),)),
    ))
    BuildxImageBuilder(args.cache / "build-context").build(spec, platform=platform, network="none")
    command = ["docker", "run", "--rm", "-i", "--network=none", "--platform=" + platform.docker_platform,
               "--user=1000:1000", "--entrypoint=sh", args.image, "-ec"]
    identity = subprocess.run(command + [
        "test ! -e /opt/graphviz/.build; test \"$(command -v dot)\" = /opt/graphviz/bin/dot; dot -V",
    ], capture_output=True, text=True, check=True)
    assert metadata["version"] in identity.stderr, identity.stderr
    checks = []
    diagram = b'digraph G { rankdir=LR; node [shape=box]; "Graphviz" -> "diagrams"; }\n'
    for engine, formats in [("dot", ["svg", "png", "pdf"]), ("neato", ["svg"]), ("sfdp", ["svg"])]:
        for fmt in formats:
            result = subprocess.run(command + [f"{engine} -T{fmt}"], input=diagram,
                                    capture_output=True, check=True)
            payload = result.stdout
            if fmt == "svg":
                assert ET.fromstring(payload).tag.endswith("svg")
            elif fmt == "png":
                assert payload.startswith(b"\x89PNG\r\n\x1a\n")
            else:
                assert payload.startswith(b"%PDF-")
            checks.append({"engine": engine, "format": fmt, "bytes": len(payload)})
    report = {
        "checked-at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.value, "base": lock["base"]["reference"],
        "graphviz": metadata["version"], "identity": identity.stderr.strip(),
        "source-sha256": metadata["artifacts"]["source"]["sha256"],
        "offline-build": True, "runtime-user": "1000:1000", "renders": checks,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
