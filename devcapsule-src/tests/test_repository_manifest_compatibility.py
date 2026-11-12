"""The repository's own manifest must stay readable by the latest released client.

Released clients validate ``runtime-effect`` by exact membership in the
vocabulary they shipped with, and refuse the whole manifest otherwise.
Locked components likewise need runtime templates in that released client. A
declaration added here therefore strands every contributor who installed the
release the guides point at, and the refusal cannot explain itself (bug
2026-09-24, released launchers reject the repository manifest). Move the
pinned vocabulary only when a final release ships with the new entry.
"""

from pathlib import Path
import tomllib

import pytest

from devcapsule.materialization import parse_locked_environment

pytestmark = pytest.mark.legacy


# Frozen from final v0.2.15, commit a15ff8b58f4af93845c17eaca22f9c9d29c8e000:
# configuration/values.py, resolution_matrix.py and components/catalog.py.
# Do not import the development catalog: that would accept the very additions
# this bootstrap guard must catch before they ship in a final release.
LATEST_RELEASED_CLIENT = "v0.2.15"
RELEASED_RUNTIME_EFFECTS = {"docker.memory-limit", "devcapsule.command-name"}
RELEASED_CAPABILITIES = {
    "antigravity-agent", "claude-code-agent", "codex-agent", "docker-cli",
    "frontend-ide", "java", "maven", "node", "postgresql-client", "python",
    "python-ide",
}
RELEASED_SURFACES = {"pycharm", "codium"}
RELEASED_COMPONENTS = RELEASED_SURFACES | {
    "antigravity-cli", "claude-code", "codex", "postgresql-client",
}

REPOSITORY_MANIFEST = Path(__file__).resolve().parents[2] / ".devcapsule" / "devcapsule.toml"


@pytest.mark.skipif(not REPOSITORY_MANIFEST.is_file(), reason="not a repository checkout")
def test_repository_manifest_declares_only_released_runtime_effects():
    manifest = tomllib.loads(REPOSITORY_MANIFEST.read_text(encoding="utf-8"))
    values = manifest.get("configuration", {}).get("values", {})
    assert values, "the repository manifest declares configuration values"
    for name, declaration in values.items():
        effect = declaration.get("runtime-effect")
        assert effect is None or effect in RELEASED_RUNTIME_EFFECTS, (
            f"{name} declares runtime-effect {effect!r}, which {LATEST_RELEASED_CLIENT} "
            "rejects; rely on a reserved name or wait for the release that knows it"
        )
