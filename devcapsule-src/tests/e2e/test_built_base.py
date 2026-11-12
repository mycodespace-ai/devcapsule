"""Validate the full base made by the selected release's own CLI."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

pytestmark = pytest.mark.legacy


@pytest.mark.e2e
@pytest.mark.base_build_e2e
def test_release_built_base_has_tools_and_no_embedded_runtime() -> None:
    image = os.environ["DEVCAPSULE_E2E_BUILT_BASE"]
    inspection = json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]
    assert image == inspection["Id"]  # Subsequent tests use this same immutable ID.
    labels = inspection["Config"]["Labels"]
    assert labels["devcapsule.image.kind"] == "base"
    assert labels["devcapsule.base.recipe"] == "ubuntu-24.04"
    assert labels["devcapsule.base.recipe-version"] == "11"
    assert labels["devcapsule.base.webconsole"] == "/opt/devcapsule-webconsole"
    assert labels["devcapsule.base.display"] == "contained"
    assert labels["devcapsule.base.runtime"] == "launcher-supplied"
    assert labels["devcapsule.source.revision"] == os.environ["DEVCAPSULE_EXPECTED_BASE_SOURCE"]
    assert labels["org.opencontainers.image.version"] == os.environ["DEVCAPSULE_EXPECTED_BUILD_MNEMONIC"]
    assert not inspection["Config"]["Entrypoint"]
    # Verify the actual exported tools, symlinks and runtime-free filesystem;
    # labels alone would also pass for a broken/incomplete installation.
    script = r"""
set -eu
test ! -e /opt/devcapsule/bin/devcapsule.pex
for agent in claude codex agy gemini; do
  if command -v "$agent" >/dev/null 2>&1; then exit 1; fi
done
test -L /opt/node/current
test -L /opt/java/current
test -L /opt/maven/current
node --version
npm --version
java -version 2>&1
javac -version
mvn --version
python3.12 --version
git --version
psql --version
Xvnc -version 2>&1
websockify --help >/dev/null
openbox --version | head -1
tint2 --version 2>&1 | head -1
test -r /usr/share/novnc/vnc.html
# Recipe 10: the web console in its own hash-pinned venv, importable offline.
/opt/devcapsule-webconsole/venv/bin/python -c "import devcapsule_webconsole, fastapi, uvicorn, psutil; print('webconsole', devcapsule_webconsole.__version__)"
/opt/devcapsule-webconsole/venv/bin/python -m devcapsule_webconsole --help >/dev/null
"""
    result = subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "/bin/sh",
                             image, "-c", script], capture_output=True, text=True, check=True)
    assert "v22.23.1" in result.stdout
    assert "webconsole 0.1.0" in result.stdout
    assert labels["devcapsule.component.temurin.version"] in result.stdout
    assert "Apache Maven " + labels["devcapsule.component.maven.version"] in result.stdout
    print(result.stdout)
