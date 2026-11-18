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
from devcapsule.materialization import (
    ArtifactSpec, acquire_artifact, validate_locked_artifact, _ancillary_contributions, _ancillary_environment,
)
from devcapsule.platforms import Platform
from devcapsule.resolution_matrix import MATRICES

BUILD_NETWORK = "none"

# What the final image must show to the capsule user, beyond a successful render.
# Each line fails the check on its own; the report names them in this order.
IMAGE_CHECKS = (
    ("build inputs are absent", "test ! -e /opt/graphviz/.build"),
    ("dot comes from the component through the declared PATH",
     'test "$(command -v dot)" = /opt/graphviz/bin/dot'),
    ("license notices are present",
     "for notice in graphviz libltdl gts; do test -s /opt/graphviz/share/licenses/$notice.txt; done"),
    ("bundled runtime libraries are present",
     "ls /opt/graphviz/lib/libltdl.so.7 /opt/graphviz/lib/libgts-0.7.so.5 >/dev/null"),
    # The five renders load only some plugins. ldd names any tool or plugin
    # linked against a library that the build stage had and the image lacks.
    # A script is not a dynamic executable and prints nothing that matches.
    ("every tool and plugin finds its shared libraries",
     "command -v ldd >/dev/null; "
     "for binary in /opt/graphviz/bin/* /opt/graphviz/lib/*.so.* /opt/graphviz/lib/graphviz/*.so.*; do "
     "if ldd \"$binary\" 2>/dev/null | grep -F 'not found'; then echo \"$binary\" >&2; exit 1; fi; done"),
    # libgts-dev is installed only by the recipe; the base never carries it.
    ("build-only packages did not reach the image",
     "! dpkg-query -W -f='${db:Status-Status}' libgts-dev 2>/dev/null | grep -q installed"),
)


def main() -> None:
    """Bind host inputs, build from exact pins, and check the resulting image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=[x.value for x in Platform])
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--image", default="devcapsule-graphviz:component-smoke")
    args = parser.parse_args()
    platform = Platform.parse(args.platform)
    # This check produces the evidence a verified edge is recorded from, so it
    # must also resolve a pin that has no edge yet.
    formation = MATRICES[platform].resolve(["graphviz"], project_only=True, allow_unverified=True)
    lock = tomllib.loads(formation.render_lock())
    metadata = lock["components"]["graphviz"]
    declarations = DEFINITION.locked_artifacts(metadata, platform.value)
    for declaration in declarations:
        validate_locked_artifact(declaration)
    files = tuple((acquire_artifact(ArtifactSpec(x.version, x.url, x.sha256, "graphviz"), args.cache).path, x)
                  for x in declarations)
    # The image gets the stage and the environment that a project's
    # materialization derives from the same declarations. Nothing is added by
    # hand, so a contribution the component stops declaring fails below.
    spec = ImageBuildSpec(args.image, lock["base"]["reference"], (
        *_ancillary_contributions(files, (), platform=platform.value),
        EnvComponent(_ancillary_environment(declarations)),
    ))
    BuildxImageBuilder(args.cache / "build-context").build(spec, platform=platform, network=BUILD_NETWORK)
    command = ["docker", "run", "--rm", "-i", "--network=none", "--platform=" + platform.docker_platform,
               "--user=1000:1000", "--entrypoint=sh", args.image, "-ec"]
    for name, check in IMAGE_CHECKS:
        checked = subprocess.run(command + [check], capture_output=True, text=True)
        assert checked.returncode == 0, f"{name}: {checked.stdout}{checked.stderr}"
    identity = subprocess.run(command + ["dot -V"], capture_output=True, text=True, check=True)
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
        "offline-build": BUILD_NETWORK == "none", "runtime-user": "1000:1000",
        "image-checks": [name for name, _check in IMAGE_CHECKS], "renders": checks,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
